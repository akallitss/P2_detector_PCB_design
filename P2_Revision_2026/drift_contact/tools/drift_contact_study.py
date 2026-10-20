#!/usr/bin/env python3
"""
Drift-contact study for the P2 basket: frame x PCB x insulation mask.

Reads only the original drawings (nothing is written outside this folder):

  * drift frame      DRIFT_P2_261124/.../FRAME_4mm/P2_Frame_V2.0.stl
  * PCB              Version_Apr26/FABRICATION_P2/Gerber/*.gbr
  * active outline   Version_Sept26/Insulation_masks/V3B_final (M1, V1 frame)

and writes  ../data/results.json  and  ../figures/*.png.

The frame STL and the PCB Gerbers share one coordinate system (fan apex at the
origin, mm); z = 0 is the frame face that sits on the PCB.

    python3 drift_contact_study.py            # ~2 min, most of it the STL
"""
from __future__ import annotations

import json
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.path import Path
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", ".."))   # Detector_Drawings/
STL = os.path.join(ROOT, "DRIFT_P2_261124", "DRIFT_P2_261124", "FRAME_4mm", "P2_Frame_V2.0.stl")
GERB = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2", "Gerber")
M1_V3B = os.path.join(ROOT, "Version_Sept26", "Insulation_masks", "V3B_final",
                      "P2_BASKET-Mask_M1_V3B_final.gbr")
M1_V2 = os.path.join(ROOT, "Version_Apr26", "Insulation_masks", "V2", "P2_BASKET-Mask_M1_V2.gbr")
CACHE = os.path.join(OUT, "data", "cache.pkl")

sys.path.insert(0, os.path.join(ROOT, "Version_Sept26", "tools"))
import p2_geometry as pg          # noqa: E402  (reused: active outline from an M1 mask)

# --------------------------------------------------------------------------
# design inputs
V_MESH, V_DRIFT = 450.0, 800.0    # typical operating point [V]
V_DESIGN = 1000.0                 # clearances are sized for this
CLEARANCE_MM = 3.0                # bare drift metal <-> bare mesh, gas or surface
PAD_R = 1.0                       # radius of a PCB drift pad (concept B)

SLOT2_X = 575.0                   # second drift feed through the bottom straight wall
TOP_MIRROR = ((303.07, 517.84), (310.57, 530.83))   # bottom slot mirrored through the 30 deg axis

MESH_PADS = {                     # gold mesh-contact pads on F.Cu (measured)
    "bottom": (595.77, 1.29, 598.70, 4.10),
    "top":    (300.98 - 1.95, 515.97 - 1.95, 300.98 + 1.95, 515.97 + 1.95),
}


# --------------------------------------------------------------------------
def load_stl(path):
    with open(path, "rb") as fh:
        fh.seek(80)
        n = int(np.frombuffer(fh.read(4), "<u4")[0])
        dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        return np.frombuffer(fh.read(n * 50), dt)["v"].astype(np.float64)


def hslice(tri, zc, win=None):
    """Segments of the frame cut by the plane z = zc (optionally windowed)."""
    z = tri[:, :, 2]
    m = (z.min(1) < zc) & (z.max(1) > zc)
    if win is not None:
        x0, y0, x1, y1 = win
        m &= (tri[:, :, 0].max(1) > x0) & (tri[:, :, 0].min(1) < x1)
        m &= (tri[:, :, 1].max(1) > y0) & (tri[:, :, 1].min(1) < y1)
    return _cut(tri[m], 2, zc, (0, 1))


def vslice(tri, axis, val, lo, hi):
    """Segments in the (other horizontal coordinate, z) plane at x or y = val."""
    o = 1 - axis
    c = tri[:, :, axis]
    m = (c.min(1) < val) & (c.max(1) > val) & (tri[:, :, o].max(1) > lo) & (tri[:, :, o].min(1) < hi)
    return _cut(tri[m], axis, val, (o, 2))


def _cut(tris, axis, val, keep):
    out = []
    for t in tris:
        p = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = t[i], t[j]
            if (a[axis] - val) * (b[axis] - val) < 0:
                u = (val - a[axis]) / (b[axis] - a[axis])
                q = a + u * (b - a)
                p.append((q[keep[0]], q[keep[1]]))
        if len(p) == 2:
            out.append(p)
    return np.array(out).reshape(-1, 2, 2)


def slot_hits(tri, a, b, half, trim=0.6, z=3.2):
    """Frame surfaces crossed by a slot a->b of the given half-width at mid-slot height.

    0 means the slot only cuts solid material.  The ends are trimmed so the two
    wall faces it opens through are not counted."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a))
    n = np.array([-u[1], u[0]])
    a2, b2 = a + trim * u, b - trim * u
    poly = Path(np.array([a2 + half * n, b2 + half * n, b2 - half * n, a2 - half * n, a2 + half * n]))
    win = (min(a[0], b[0]) - 5, min(a[1], b[1]) - 5, max(a[0], b[0]) + 5, max(a[1], b[1]) + 5)
    seg = hslice(tri, z, win)
    P = np.vstack([seg[:, 0], seg[:, 1]])
    m = poly.contains_points(P)
    return {"surfaces_crossed": int(m.sum()), "points": P[m].round(2).tolist()}


def loops(seg, tol=1e-3):
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    adj = defaultdict(list)
    for i, (a, b) in enumerate(seg):
        adj[key(a)].append(i)
        adj[key(b)].append(i)
    used = np.zeros(len(seg), bool)
    out = []
    for s in range(len(seg)):
        if used[s]:
            continue
        used[s] = True
        a, b = seg[s]
        L, cur = [a, b], key(b)
        while True:
            nxt = [j for j in adj[cur] if not used[j]]
            if not nxt:
                break
            j = nxt[0]
            used[j] = True
            p, q = seg[j]
            if key(p) == cur:
                L.append(q); cur = key(q)
            else:
                L.append(p); cur = key(p)
        out.append(np.array(L))
    return out


def area(P):
    return 0.5 * abs(np.sum(P[:-1, 0] * P[1:, 1] - P[1:, 0] * P[:-1, 1]))


def dense(P, step=0.2):
    o = []
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.hypot(*(b - a)) / step))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        o.append(a + t * (b - a))
    return np.vstack(o)


def load_gerbers():
    from gerbonara import GerberFile
    from gerbonara.utils import MM
    out = {}
    for name in ["F_Cu", "B_Cu", "Edge_Cuts", "F_ENIG_Finition"]:
        g = GerberFile.open(os.path.join(GERB, f"P2_BASKET-{name}.gbr"))
        prims = []
        for o in g.objects:
            try:
                prims += list(o.to_primitives(MM))
            except Exception:
                pass
        out[name] = prims
    return out


def active_outline(m1):
    pg.M1_REF = m1
    pg._cache.clear()
    return np.asarray(pg.active_outline())


# --------------------------------------------------------------------------
def build():
    if os.path.exists(CACHE) and os.path.getmtime(CACHE) > os.path.getmtime(__file__):
        return pickle.load(open(CACHE, "rb"))
    print("reading STL ...", flush=True)
    tri = load_stl(STL)
    C = {"bounds": [tri.reshape(-1, 3).min(0).tolist(), tri.reshape(-1, 3).max(0).tolist()]}
    C["flats"] = sorted(set(np.round(tri[:, 0, 2][np.ptp(tri[:, :, 2], 1) < 1e-6], 3).tolist()))
    for zc in (0.2, 1.0, 3.0, 4.2, 7.0):
        C[f"z{zc}"] = hslice(tri, zc)
    C["sec_x350"] = vslice(tri, 0, 350.0, -12, 8)
    C["sec_y3.5"] = vslice(tri, 1, 3.5, 590, 618)
    C["sec_x604"] = vslice(tri, 0, 604.0, -12, 26)
    C["sec_x575"] = vslice(tri, 0, SLOT2_X, -12, 8)
    C["slot_tests"] = {
        "existing bottom-right slot (control)": slot_hits(tri, (600, 3.55), (615, 3.55), 1.0),
        "top corner, mirror of the bottom slot": slot_hits(tri, *TOP_MIRROR, 1.0),
        f"bottom straight wall at x = {SLOT2_X:g}": slot_hits(tri, (SLOT2_X, 0), (SLOT2_X, -10), 2.25),
    }
    print("reading Gerbers ...", flush=True)
    C["gerb"] = load_gerbers()
    C["A_v3b"] = active_outline(M1_V3B)
    C["A_v2"] = active_outline(M1_V2)
    pickle.dump(C, open(CACHE, "wb"))
    return C


def copper_polys(prims):
    from gerbonara.graphic_primitives import ArcPoly
    out = []
    for p in prims:
        if isinstance(p, ArcPoly):
            o = np.array(list(p.outline))
            if len(o) > 2:
                out.append(o)
    return out


# --------------------------------------------------------------------------
def analyse(C):
    R = {"inputs": {"V_mesh": V_MESH, "V_drift": V_DRIFT, "V_design": V_DESIGN,
                    "clearance_rule_mm": CLEARANCE_MM, "pad_radius_mm": PAD_R},
         "frame": {"bounds_mm": C["bounds"], "horizontal_faces_z_mm": C["flats"]}}

    # opening of the frame at PCB level = smallest closed loop of the z = 0.2 cut
    L = sorted(loops(C["z0.2"]), key=area, reverse=True)
    big = [l for l in L if area(l) > 1e5]
    O = big[-1]
    A, A2 = C["A_v3b"], C["A_v2"]
    R["frame"]["opening_area_mm2"] = round(area(O))
    R["mask"] = {"active_area_V3B_final_mm2": round(area(A)), "active_area_V2_mm2": round(area(A2))}

    to, ta, ta2 = cKDTree(dense(O)), cKDTree(dense(A)), cKDTree(dense(A2))
    s = dense(A, 1.0)
    R["mask"]["wall_to_active_V3B_mm"] = [round(float(x), 2) for x in
                                          np.percentile(to.query(s)[0], [0, 50, 100])]
    R["mask"]["wall_to_active_V2_mm"] = [round(float(x), 2) for x in
                                         np.percentile(to.query(dense(A2, 1.0))[0], [0, 50, 100])]

    # readout copper: first pad edge from the frame wall
    # readout pads lie wholly inside the opening; the M traces cross the wall and are left out
    inside = Path(O)
    polys = [p for p in copper_polys(C["gerb"]["F_Cu"])
             if np.ptp(p[:, 0]) < 30 and np.ptp(p[:, 1]) < 30 and inside.contains_points(p).all()]
    pts = np.vstack(polys)
    for x0, y0, x1, y1 in MESH_PADS.values():          # not readout copper
        pts = pts[~((pts[:, 0] > x0 - .5) & (pts[:, 0] < x1 + .5) & (pts[:, 1] > y0 - .5) & (pts[:, 1] < y1 + .5))]
    d = to.query(pts)[0]
    R["pcb"] = {"wall_to_first_readout_copper_mm": round(float(d.min()), 2)}

    # the wire slot at the bottom-right corner
    sec = C["sec_y3.5"]
    R["slot"] = {"where": "bottom-right corner, through the outer-arc wall",
                 "x_mm": [600.0, 615.0], "y_mm": [2.3, 4.8], "z_mm": [2.6, 3.8],
                 "ledge_z_mm": 4.0, "roof_over_slot_mm": 0.2,
                 "ledge_width_mm": 3.0}
    bx = MESH_PADS["bottom"]
    dx = 600.0 - bx[2]
    R["slot"]["mouth_to_bottom_mesh_pad_mm"] = round(math.hypot(dx, 2.6 - 0.1), 2)

    # a second drift feed: where can a slot go without cutting the gas system?
    R["second_slot"] = {name: {"surfaces_crossed": v["surfaces_crossed"]}
                        for name, v in C["slot_tests"].items()}
    R["second_slot"]["note"] = ("0 = the slot only cuts solid frame. The top-corner mirror crosses the "
                                "outer-arc gas channel that starts at the top gas port.")
    R["second_slot"]["bottom_wall_mouth_to_bare_mesh_mm"] = round(
        math.hypot(float(ta.query([[SLOT2_X, 0.0]])[0][0]), 2.6 - 0.1), 2)

    # concept B: where can a PCB drift pad sit, 1 kV rule
    xs, ys = np.arange(40, 620, 0.2), np.arange(-5, 545, 0.2)
    X, Y = np.meshgrid(xs, ys)
    P = np.c_[X.ravel(), Y.ravel()]
    P = P[Path(O).contains_points(P) & ~Path(A).contains_points(P)]
    dw, da = to.query(P)[0], ta.query(P)[0]
    mp = np.array([[(v[0] + v[2]) / 2, (v[1] + v[3]) / 2] for v in MESH_PADS.values()])
    dm = np.min(np.hypot(*(P[:, None, :] - mp[None]).transpose(2, 0, 1)), axis=1) - 2.0
    clear = np.minimum(da, dm) - PAD_R                # pad EDGE to nearest bare mesh
    th = np.degrees(np.arctan2(P[:, 1], P[:, 0]))
    r = np.hypot(*P.T)
    regions = {
        "bottom straight": (th < 3) & (r > 150) & (r < 570),
        "outer arc": (r > 570) & (th > 3) & (th < 57),
        "top straight": (th > 57) & (r > 150) & (r < 570),
        "inner arc": (r < 140) & (th > 8) & (th < 52),
        "bottom-right corner": (r > 570) & (th < 3),
        "top corner": (r > 570) & (th > 57),
        "inner-bottom corner": (r < 150) & (th < 8),
        "inner-left corner": (r < 150) & (th > 52),
    }
    R["conceptB"] = {}
    for name, m in regions.items():
        k = m & (dw >= 1.5)
        j = int(np.argmax(np.where(k, clear, -9)))
        R["conceptB"][name] = {"best_centre": P[j].round(1).tolist(),
                               "pad_edge_to_bare_mesh_mm": round(float(clear[j]), 2),
                               "meets_rule": bool(clear[j] >= CLEARANCE_MM)}
    return R, O, (P, clear, dw)


# --------------------------------------------------------------------------
def fig_overview(C, O, R, path):
    fig, ax = plt.subplots(figsize=(11, 10))
    for p in C["gerb"]["Edge_Cuts"]:
        try:
            ax.plot([p.x1, p.x2], [p.y1, p.y2], color="0.3", lw=.6)
        except AttributeError:
            pass
    for zc, c in (("z0.2", "0.55"), ("z7.0", "tab:blue")):
        ax.add_collection(LineCollection(C[zc], colors=c, lw=.6))
    ax.plot(*O.T, color="k", lw=1.2, label="frame inner wall (z = 0–4)")
    ax.plot(*C["A_v3b"].T, "g--", lw=1, label="active edge V3B_final (V1 frame)")
    for nm, (x0, y0, x1, y1) in MESH_PADS.items():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="gold", zorder=4))
    ax.annotate("mesh pad + GND/M/D/GND\nHV pads, wire slot", (600, 4), (470, 40), fontsize=9,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("mesh pad + GND/M/D/GND\nHV pads, gas port", (302, 520), (360, 530), fontsize=9,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("gas port Ø4.4", (92, 0), (20, 30), fontsize=9, arrowprops=dict(arrowstyle="->"))
    for name, v in R["conceptB"].items():
        if name in ("inner-bottom corner", "inner-left corner"):
            ax.plot(*v["best_centre"], "o", ms=9, mfc="none", mec="tab:red", mew=2)
    ax.plot([], [], "o", mfc="none", mec="tab:red", mew=2, label="only places a PCB drift pad meets 1 kV")
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend(loc="upper left", fontsize=8)
    ax.set_title("P2 basket: drift frame on PCB, contacts and gas ports (mm)")
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def fig_corner(C, R, path):
    win = (560, -11, 632, 26)
    fig = plt.figure(figsize=(15, 9.5))
    ax = fig.add_axes([0.04, 0.32, 0.62, 0.64])
    bx = fig.add_axes([0.70, 0.56, 0.28, 0.38])
    cx = fig.add_axes([0.70, 0.12, 0.28, 0.38])
    dx = fig.add_axes([0.04, 0.03, 0.62, 0.22])
    for p in copper_polys(C["gerb"]["F_Cu"]):
        if p[:, 0].max() > win[0] and p[:, 1].min() < win[3] and np.ptp(p[:, 0]) < 80:
            ax.add_patch(Polygon(p, color="#d9a066", alpha=.7, lw=0))
    x0, y0, x1, y1 = MESH_PADS["bottom"]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="gold", zorder=3))
    ax.text((x0 + x1) / 2, y0 - .6, "mesh pad", ha="center", va="top", fontsize=8)
    for zc, c, lab in (("z1.0", "0.6", "frame z=1 (O-ring dovetail)"), ("z3.0", "k", "frame z=3 (wall + slot)"),
                       ("z4.2", "tab:blue", "frame z=4.2 (above the mylar ledge)")):
        s = C[zc]
        m = (s[:, :, 0].max(1) > win[0]) & (s[:, :, 1].min(1) < win[3])
        ax.add_collection(LineCollection(s[m], colors=c, lw=1.2, label=lab))
    ax.plot(*C["A_v3b"].T, "g--", lw=1.2, label="active edge V3B_final")
    ax.add_patch(Circle((601.5, 3.55), 0.6, color="red", zorder=6))
    ax.annotate("A: Ø1.2 hole, ledge → slot\n(through the 0.2 mm roof)", (601.5, 3.55), (604, -7.5),
                color="red", fontsize=9, arrowprops=dict(arrowstyle="->", color="red"))
    ax.add_patch(Rectangle((600.4, 1.0), 2.0, 6.0, fill=False, ec="red", ls="--", lw=1.2, zorder=6))
    ax.text(602.7, 6.4, "Cu tab 2×6\non ledge", color="red", fontsize=8)
    ax.annotate("slot z 2.6–3.8:\npot with epoxy", (610, 3.55), (613, 10), fontsize=8,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("D pad", (627.5, 15.2), (628, 20.5), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3]); ax.set_aspect("equal"); ax.grid(alpha=.3)
    ax.legend(loc="upper left", fontsize=7.5, framealpha=.9)
    ax.set_title("Concept A — bottom-right corner, plan view (PCB F.Cu + frame cuts), mm")

    def section(a, segs, lo, hi, title):
        a.add_collection(LineCollection(segs, colors="k", lw=1.2))
        a.fill_between([lo, hi], -0.24, 0, color="#d9a066")
        a.set_xlim(lo, hi); a.set_ylim(-0.6, 8.6); a.set_aspect("equal"); a.grid(alpha=.3)
        a.set_title(title, fontsize=9)

    section(bx, C["sec_y3.5"], 592, 617, "today: section y = 3.5 through the slot")
    bx.plot([592, 603], [4.05, 4.05], color="tab:blue", lw=2.5)
    bx.add_patch(Rectangle((x0, 0), x1 - x0, 0.15, color="gold"))
    bx.plot([618, 606, 601.5, 600.5], [3.2, 3.2, 3.2, 3.2], color="tab:red", lw=2)
    bx.annotate(f"wire mouth ↔ mesh pad {R['slot']['mouth_to_bottom_mesh_pad_mm']} mm",
                (599, 1.5), (592.5, 6.6), fontsize=7.5, arrowprops=dict(arrowstyle="->"))

    section(cx, C["sec_y3.5"], 592, 617, "concept A: same section")
    cx.add_patch(Rectangle((600.0, 2.6), 15.0, 1.2, color="0.75", zorder=1))
    cx.text(607, 3.0, "epoxy potting", fontsize=7, ha="center")
    cx.plot([617, 601.5, 601.5], [3.2, 3.2, 4.0], color="tab:red", lw=2, zorder=3)
    cx.plot([600.4, 602.4], [4.03, 4.03], color="tab:red", lw=4, zorder=3)
    cx.plot([592, 603], [4.1, 4.1], color="tab:blue", lw=2.5)
    cx.text(592.5, 4.5, "mylar, Al face down, Ag-epoxy on tab", fontsize=7, color="tab:blue")
    cx.add_patch(Rectangle((x0, 0), x1 - x0, 0.15, color="gold"))

    section(dx, C["sec_x350"], -12, 8, "section x = 350 across the bottom edge: what a PCB spring contact (concept B) has to fit in")
    dx.plot([-3, 8], [4.05, 4.05], color="tab:blue", lw=2.5)
    dx.add_patch(Rectangle((1.0, 0), 2, 0.15, color="tab:red"))
    dx.plot([2, 2], [0.15, 4.0], color="tab:red", lw=3)
    dx.axvline(4.79, color="g", ls="--"); dx.text(4.95, 6.5, "bare mesh\n(active edge)", color="g", fontsize=8)
    dx.text(-9.5, 6.5, "frame", fontsize=8)
    fig.savefig(path, dpi=115); plt.close(fig)


def fig_conceptB(R, O, band, C, path):
    P, clear, dw = band
    fig, axs = plt.subplots(1, 2, figsize=(14, 6.2))
    for ax, (cx_, cy_), title in zip(axs, ((111, 6), (60, 98)), ("inner-bottom corner", "inner-left corner")):
        w = 14
        m = (abs(P[:, 0] - cx_) < w) & (abs(P[:, 1] - cy_) < w)
        sc = ax.scatter(P[m, 0], P[m, 1], c=clear[m], s=6, cmap="RdYlGn", vmin=0, vmax=5, marker="s")
        ax.plot(*O.T, "k", lw=1.2)
        ax.plot(*C["A_v3b"].T, "g--", lw=1.2)
        for zc in ("z3.0",):
            s = C[zc]
            mm = (abs(s[:, :, 0].mean(1) - cx_) < w) & (abs(s[:, :, 1].mean(1) - cy_) < w)
            ax.add_collection(LineCollection(s[mm], colors="0.4", lw=.8))
        v = R["conceptB"][title]
        ax.add_patch(Circle(v["best_centre"], PAD_R, color="tab:red", zorder=5))
        ax.add_patch(Circle(v["best_centre"], PAD_R + CLEARANCE_MM, fill=False, ec="tab:red", ls="--", zorder=5))
        ax.set_xlim(cx_ - w, cx_ + w); ax.set_ylim(cy_ - w, cy_ + w); ax.set_aspect("equal"); ax.grid(alpha=.3)
        ax.set_title(f"{title}: best pad {v['best_centre']}, edge→bare mesh {v['pad_edge_to_bare_mesh_mm']} mm", fontsize=9)
    fig.colorbar(sc, ax=axs, label="Ø2 pad edge → nearest bare mesh [mm]  (rule: ≥ 3 mm)")
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def _slot_patch(ax, a, b, half, **kw):
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]])
    ax.add_patch(Polygon(np.array([a + half * n, b + half * n, b - half * n, a - half * n]), **kw))


def _cuts(ax, C, win, which=(("z3.0", "k"), ("z4.2", "tab:blue"), ("z1.0", "0.6"))):
    for zc, c in which:
        s = C[zc]
        m = (s[:, :, 0].max(1) > win[0]) & (s[:, :, 0].min(1) < win[2]) & \
            (s[:, :, 1].max(1) > win[1]) & (s[:, :, 1].min(1) < win[3])
        ax.add_collection(LineCollection(s[m], colors=c, lw=1))


def fig_second_feed(C, R, path):
    fig = plt.figure(figsize=(15, 8.5))
    ax = fig.add_axes([0.03, 0.30, 0.42, 0.65])
    bx = fig.add_axes([0.50, 0.30, 0.48, 0.65])
    cx = fig.add_axes([0.55, 0.03, 0.40, 0.22])

    win = (282, 497, 345, 545)
    _cuts(ax, C, win)
    _slot_patch(ax, *TOP_MIRROR, 1.25, color="tab:red", alpha=.45, zorder=5)
    hits = np.array(C["slot_tests"]["top corner, mirror of the bottom slot"]["points"])
    if len(hits):
        ax.plot(hits[:, 0], hits[:, 1], "x", color="tab:red", ms=8, mew=2, zorder=6)
    x0, y0, x1, y1 = MESH_PADS["top"]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="gold", zorder=4))
    ax.text(306, 541, "✗ mirror of the bottom slot:\ncuts the outer-arc gas channel (×)", color="tab:red", fontsize=9)
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3]); ax.set_aspect("equal"); ax.grid(alpha=.3)
    ax.set_title("Top corner — no room for a slot (frame cuts at z = 1 / 3 / 4.2)", fontsize=10)

    win = (545, -14, 632, 22)
    for p in copper_polys(C["gerb"]["F_Cu"]):
        if p[:, 0].max() > win[0] and p[:, 1].min() < win[3] and np.ptp(p[:, 0]) < 80:
            bx.add_patch(Polygon(p, color="#d9a066", alpha=.6, lw=0))
    for p in C["gerb"]["Edge_Cuts"]:
        try:
            bx.plot([p.x1, p.x2], [p.y1, p.y2], color="0.3", lw=.8)
        except AttributeError:
            pass
    _cuts(bx, C, win)
    bx.plot(*C["A_v3b"].T, "g--", lw=1.2)
    _slot_patch(bx, (SLOT2_X, 0), (SLOT2_X, -10), 1.25, color="tab:red", alpha=.45, zorder=5)
    _slot_patch(bx, (600, 3.55), (615, 3.55), 1.25, color="0.5", alpha=.45, zorder=5)
    bx.add_patch(Circle((SLOT2_X, -1.5), 0.6, color="red", zorder=6))
    bx.add_patch(Circle((601.5, 3.55), 0.6, color="red", zorder=6))
    x0, y0, x1, y1 = MESH_PADS["bottom"]
    bx.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="gold", zorder=4))
    bx.annotate(f"✓ 2nd slot, x = {SLOT2_X:g}: solid frame only\nmouth ↔ bare mesh "
                f"{R['second_slot']['bottom_wall_mouth_to_bare_mesh_mm']} mm", (SLOT2_X + 1.3, -6),
                (547, 12), fontsize=9, color="tab:red", arrowprops=dict(arrowstyle="->", color="tab:red"))
    bx.annotate(f"existing slot: mouth ↔ mesh pad {R['slot']['mouth_to_bottom_mesh_pad_mm']} mm",
                (607, 3.55), (590, 15), fontsize=9, arrowprops=dict(arrowstyle="->"))
    bx.annotate("frame flush with board edge:\nwire runs along its outer face to D", (600, -11), (596, -13.5), fontsize=8)
    bx.set_xlim(win[0], win[2]); bx.set_ylim(win[1], win[3]); bx.set_aspect("equal"); bx.grid(alpha=.3)
    bx.set_title("Bottom-right — second drift feed through the bottom straight wall", fontsize=10)

    cx.add_collection(LineCollection(C["sec_x575"], colors="k", lw=1.2))
    cx.fill_between([-12, 8], -0.24, 0, color="#d9a066")
    cx.add_patch(Rectangle((-10, 2.6), 10, 1.2, color="tab:red", alpha=.45))
    cx.add_patch(Rectangle((-2.1, 3.8), 1.2, 0.2, color="red"))
    cx.plot([-3, 8], [4.05, 4.05], color="tab:blue", lw=2.5)
    cx.axvline(4.79, color="g", ls="--")
    cx.set_xlim(-12, 8); cx.set_ylim(-0.6, 8.6); cx.set_aspect("equal"); cx.grid(alpha=.3)
    cx.set_title(f"section x = {SLOT2_X:g}: new slot z 2.6–3.8 above the O-ring dovetail, hole up to the ledge", fontsize=9)
    fig.savefig(path, dpi=110); plt.close(fig)


def main():
    C = build()
    R, O, band = analyse(C)
    fig_overview(C, O, R, os.path.join(OUT, "figures", "fig1_overview.png"))
    fig_corner(C, R, os.path.join(OUT, "figures", "fig2_conceptA_bottom_right.png"))
    fig_conceptB(R, O, band, C, os.path.join(OUT, "figures", "fig3_conceptB_inner_corners.png"))
    fig_second_feed(C, R, os.path.join(OUT, "figures", "fig4_second_drift_feed.png"))
    json.dump(R, open(os.path.join(OUT, "data", "results.json"), "w"), indent=2)
    print(json.dumps(R, indent=2))


if __name__ == "__main__":
    main()
