#!/usr/bin/env python3
"""
PCB + insulation-mask changes for the 2026 revision: NOW vs NEW figures and coordinate tables
for the KiCad designer (they insert the changes in the project; we deliver no Gerbers here).

Reads (never modifies):
  ../../../drift_contact/data/cache.pkl                today's Gerber primitives (drift_contact_study.py)
  ../../drift_pad_B2/FABRICATION_P2_B2/Gerber            B2 drift-pad patch (copper NEW at corner A)
  ../../../mechanics/tools/rev_geometry.py              new screw-hole pattern, mesh corner, outlines
  ../data/inner_marks_search.json                      new positions of alignment crosses 1, 2

Writes ../figures/pcb_*.png and ../data/pcb_*.csv
Run with (ulimit -v 3000000; python3 fig_pcb.py)
"""
import csv
import gc
import json
import math
import os
import pickle
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon as MPoly, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
REV = os.path.normpath(os.path.join(OUT, "..", ".."))
sys.path.insert(0, os.path.join(REV, "mechanics", "tools"))
import rev_geometry as rg                                       # noqa: E402
from fig_frame_corners import C_DIM, C_EXT_EC, C_OPEN, C_PAD, callout, dim, poly_patch   # noqa: E402

FIG = os.path.join(OUT, "figures")
DATA = os.path.join(OUT, "data")
CACHE = os.path.join(REV, "drift_contact", "data", "cache.pkl")
B2_GERB = os.path.join(REV, "pcb", "drift_pad_B2", "FABRICATION_P2_B2", "Gerber")

C_PCB, C_FCU, C_BCU, C_CONN, C_MESH = "#eaf3e6", "#f0b46a", "#b39ddb", "#8e44ad", "#d9dde3"
C_DRIFT = "#e8c547"

# alignment crosses: today 3 x 3 mm (0.12 mm lines); NEW 9 mm across, 0.3 mm lines, 12.5 mm resist square
MARKS_NOW = {1: (70.80, 66.19), 2: (93.67, 28.50), 3: (635.63, 83.91), 4: (391.22, 507.00)}
CROSS_NOW, CROSS_NEW, LINE_NEW, SQUARE_NEW = 3.0, 9.0, 0.3, 12.5
CONN_LEN, CONN_W = 47.4, 8.7          # FX20-140P header body (Hirose catalog)


def marks_new():
    best = json.load(open(os.path.join(DATA, "inner_marks_search.json")))["best"][0]
    m = dict(MARKS_NOW)
    m[1], m[2] = tuple(best["cross_1"]), tuple(best["cross_2"])
    return m, best


def connectors(C):
    """The 10 FX20-140P footprints: centre and mid angle, from their pads on today's F.Cu."""
    pts = []
    for p in C["gerb"]["F_Cu"]:
        if type(p).__name__ == "Rectangle":
            (x0, y0), (x1, y1) = p.bounding_box()
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if 626 < math.hypot(cx, cy) < 638:
                pts.append((math.degrees(math.atan2(cy, cx)), cx, cy))
    a = np.array(sorted(pts))
    out = []
    for g in np.split(a, np.where(np.diff(a[:, 0]) > 1.0)[0] + 1):
        c = g[:, 1:].mean(0)
        out.append((tuple(c), math.degrees(math.atan2(c[1], c[0])), len(g)))
    return out


def conn_box(c, ang):
    t = math.radians(ang)
    u = np.array([-math.sin(t), math.cos(t)])          # along the connector (tangential)
    n = np.array([math.cos(t), math.sin(t)])           # radial
    c = np.asarray(c)
    return [tuple(c + su * CONN_LEN / 2 * u + sn * CONN_W / 2 * n) for su, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def cross(ax, c, size, lw, color, square=None, **kw):
    x, y = c
    h = size / 2
    ax.plot([x - h, x + h], [y, y], color=color, lw=lw, solid_capstyle="butt", **kw)
    ax.plot([x, x], [y - h, y + h], color=color, lw=lw, solid_capstyle="butt", **kw)
    if square:
        s = square / 2
        ax.add_patch(Rectangle((x - s, y - s), square, square, fc="none", ec=color, lw=.8, ls="--", zorder=7))


OLD_SCREW = None


def in_new_pattern(x, y):
    """A position of the new screw-hole pattern."""
    return any(math.hypot(x - a, y - b) < 0.05 for _, a, b, _ in rg.new_frame_holes()[0])


def is_kept_hole(x, y):
    """A new screw hole that is today's hole (same position): the outer arc and the inner corners."""
    _, H = rg.read_drill()
    return any(math.hypot(x - a, y - b) < 0.05 for k in (3, 6) for a, b in H[k])


def copper_polys(prims, win, drop_old_screw_pads=False):
    """Gerber primitives -> polygons cropped to win (keeps memory low). Clear-polarity primitives
    (clearances cut into the GND hatch) are not copper and are skipped."""
    from gerbonara.graphic_primitives import ArcPoly, Circle as GC, Line as GL, Rectangle as GR
    global OLD_SCREW
    if OLD_SCREW is None:                    # today's screw holes that go (the outer arc and corners stay)
        D, H = rg.read_drill()
        OLD_SCREW = [(x, y) for k in (3, 6) for x, y in H[k] if not in_new_pattern(x, y)]
    x0, x1, y0, y1 = win
    out = []
    for p in prims:
        if not getattr(p, "polarity_dark", True):
            continue
        if drop_old_screw_pads and isinstance(p, GC) and any(math.hypot(p.x - a, p.y - b) < 0.05 for a, b in OLD_SCREW):
            continue
        try:
            (a, b), (c, d) = p.bounding_box()
        except Exception:
            continue
        if c < x0 or a > x1 or d < y0 or b > y1:
            continue
        if isinstance(p, ArcPoly):
            o = np.array(list(p.outline))
            if len(o) > 2:
                out.append(o)
        elif isinstance(p, GC):
            t = np.linspace(0, 2 * np.pi, 24)
            out.append(np.c_[p.x + p.r * np.cos(t), p.y + p.r * np.sin(t)])
        elif isinstance(p, GR):
            cx, cy, w, h, r = p.x, p.y, p.w, p.h, getattr(p, "rotation", 0.0)
            R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
            q = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) @ R.T
            out.append(q + [cx, cy])
        elif isinstance(p, GL):
            d = np.array([p.x2 - p.x1, p.y2 - p.y1])
            L = np.hypot(*d)
            if L < 1e-9:
                continue
            n = np.array([-d[1], d[0]]) / L * p.width / 2
            out.append(np.array([[p.x1, p.y1] + n, [p.x2, p.y2] + n, [p.x2, p.y2] - n, [p.x1, p.y1] - n]))
    return out


def load_b2(win):
    from gerbonara import GerberFile
    from gerbonara.utils import MM
    res = {}
    for layer in ("F_Cu", "B_Cu"):
        g = GerberFile.open(os.path.join(B2_GERB, f"P2_BASKET-{layer}.gbr"))
        prims = []
        for o in g.objects:
            try:
                prims += list(o.to_primitives(MM))
            except Exception:
                pass
        res[layer] = copper_polys(prims, win, drop_old_screw_pads=True)
        del g, prims
        gc.collect()
    return res


M_WIN_M2 = (595.82, 2.15, 597.82, 4.15)     # mask M2 window over the corner-A mesh pad (to close)


def m_net_A(C):
    """Copper of the mesh-contact net at corner A (mesh pad, trace, two M solder pads): the
    F.Cu shapes connected to the mesh pad. Removed in the revision: corner A keeps only the
    drift contact; the mesh is contacted at corner B."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    shapes = []
    for p in C["gerb"]["F_Cu"]:
        if type(p).__name__ != "ArcPoly" or not getattr(p, "polarity_dark", True):
            continue
        o = list(p.outline)
        if len(o) < 3:
            continue
        (a, b), (c, d) = p.bounding_box()
        if c < 590 or a > 640 or d < -5 or b > 30:
            continue
        g = Polygon(o).buffer(0)
        if 0 < g.area < 200:
            shapes.append(g)
    comp = [g for g in shapes if g.distance(Point(597.2, 2.7)) < 0.05]
    grown = True
    while grown:
        U = unary_union(comp).buffer(0.01)
        new = [g for g in shapes if g not in comp and g.intersects(U)]
        comp += new
        grown = bool(new)
    return unary_union(comp), comp


def board(ax):
    ax.add_patch(poly_patch(rg.pcb_outline(), fc=C_PCB, ec="0.3", lw=.8, zorder=0))


def overview(C, conns, mk):
    D, H = rg.read_drill()
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 9.6))
    for ax in (a0, a1):
        board(ax)
        ax.add_patch(poly_patch(rg.frame_top()[1].buffer(-3.0, join_style=2), fc="white", ec="0.6", lw=.5, ls=":", zorder=0))
        for k in (4, 5):
            for x, y in H[k]:
                ax.plot(x, y, "o", ms=2.5, color="0.4", zorder=3)
        ax.set_xlim(20, 665)
        ax.set_ylim(-30, 560)
        ax.set_aspect("equal")
        ax.axis("off")
    for c, a, _ in conns:
        a0.add_patch(MPoly(conn_box(c, a), fc=C_FCU, ec="#a0522d", lw=.8, zorder=4))
        a1.add_patch(MPoly(conn_box(c, a), fc="none", ec=C_CONN, lw=1.2, ls="--", zorder=4))
    for x, y, d in rg.old_frame_holes(H):
        a0.plot(x, y, "o", ms=6, **({"mfc": "#1f5fbf", "mec": "#1f5fbf"} if d < 3.2 else {"mfc": "white", "mec": "#8e44ad", "mew": 1.8}), zorder=5)
    for no, x, y, _ in rg.new_frame_holes()[0]:
        a1.plot(x, y, "o", ms=6, mfc="0.6" if is_kept_hole(x, y) else "white", mec="black", mew=1.4, zorder=5)
    new, _ = mk
    for i, c in MARKS_NOW.items():
        a0.plot(*c, "+", ms=9, mew=1.6, color="#c0392b", zorder=6)
        a0.annotate(f"{i}", c, (c[0] + 8, c[1] + 8), fontsize=9, color="#c0392b")
    for i, c in new.items():
        a1.plot(*c, "P", ms=11, mfc="#c0392b", mec="white", zorder=6)
        a1.annotate(f"{i}", c, (c[0] + 9, c[1] + 9), fontsize=9, color="#c0392b", weight="bold")
    for ax in (a0, a1):
        ax.add_patch(Rectangle((578, -14), 72, 50, fc="none", ec=C_DIM, lw=1.2, ls="-."))
        ax.text(580, 38, "zoom A", color=C_DIM, fontsize=9)
        ax.add_patch(Rectangle((50, 5), 70, 90, fc="none", ec=C_DIM, lw=1.2, ls="-."))
        ax.text(52, 97, "zoom marks", color=C_DIM, fontsize=9)
    a0.set_title("NOW", fontsize=14, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=14, weight="bold", loc="left", color=C_EXT_EC)
    holes = rg.new_frame_holes()[0]
    n_new, n_kept = len(holes), sum(1 for _, x, y, _ in holes if is_kept_hole(x, y))
    fig.text(0.04, 0.2, "today\n• connectors FX20-140P on the front (F.Cu)\n"
             "• 40 screw holes: 26 Ø3.5 plated + 14 Ø3.5 not plated,\n   irregular spacing\n"
             "• alignment crosses 3 × 3 mm\n• Sig1 readout pad in the bottom-right corner",
             fontsize=9.5, va="top", bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.5"))
    fig.text(0.52, 0.2, "1. outline UNCHANGED\n"
             f"2. {n_new} screw holes Ø3.5 (table pcb_screw_holes.csv): {n_kept} stay as today (grey: the outer\n"
             "    arc, between the signal lines, and the 2 inner corners), the rest at equal pitch on the\n"
             "    straight sides and the inner arc\n"
             "3. connectors move to the BACK (B.Cu), same positions (dashed)\n"
             "4. alignment crosses 9 mm / 12.5 mm resist square; crosses 1, 2 move (zoom marks)\n"
             "5. corner A: drift pad at the corner centre, fed by today's mesh line; mesh cleared (zoom A)\n"
             "6. connector-support holes (grey dots): unchanged",
             fontsize=9.5, va="top", bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    h = [Patch(fc=C_PCB, ec="0.3", label="PCB (outline unchanged)"),
         Patch(fc=C_FCU, ec="#a0522d", label="connector on the front"),
         Patch(fc="none", ec=C_CONN, ls="--", label="connector on the BACK"),
         Line2D([], [], marker="o", ls="none", mfc="#1f5fbf", mec="#1f5fbf", label="Ø3.5 plated (today)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="#8e44ad", mew=1.8, label="Ø3.5 not plated (today)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="black", label="NEW Ø3.5 screw hole"),
         Line2D([], [], marker="o", ls="none", mfc="0.6", mec="black", label="screw hole kept as today"),
         Line2D([], [], marker="P", ls="none", mfc="#c0392b", mec="white", ms=10, label="alignment cross"),
         Line2D([], [], marker="o", ls="none", color="0.4", ms=3, label="connector-support hole")]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("PCB – what changes (symbols enlarged)", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.21, 1, 0.88))
    fig.savefig(os.path.join(FIG, "pcb_overview.png"), dpi=130)
    plt.close(fig)


def hv_pads_A():
    """Corner-A HV solder pads (ENIG), along the chamfer from the board corner: GND (bottom), the
    two M pads, the two D pads, GND (top). 2026: the top GND goes and the M + D pads merge into one
    D pad (decided 2026-10-28), 3.26 mm from the remaining GND."""
    p = sorted(rg.hv_pads()["A"], key=lambda g: g.centroid.y)
    from shapely.ops import unary_union
    return {"gnd_bottom": p[0], "m": p[1:3], "d": p[3:5], "gnd_top": p[5],
            "d_new": unary_union(p[1:5]).minimum_rotated_rectangle}


def drift_net_A(mparts):
    """Corner A drift contact (decided 2026-10-26, pads 2026-10-28): today's mesh line carries the
    drift into one D pad that replaces the two M and the two D solder pads; the mesh pad and the
    line's first stub go, and so does the top GND pad; a 3 x 3 mm pad at the centre of the cleared
    corner is joined to the line's bend by a straight segment of the same width.
    Returns (added, removed, kept, hv) as shapely geometries + the pad dict."""
    from shapely.geometry import LineString, Point, box
    from shapely.ops import unary_union
    hv = hv_pads_A()
    x, y, s = rg.B2_PAD
    pad = box(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    ext = LineString([(x, y), rg.M_TRACE_BEND]).buffer(rg.M_TRACE_W / 2, cap_style=2)
    parts = sorted(mparts, key=lambda g: g.bounds[0])
    mesh_pad, trace = parts[0], max(parts, key=lambda g: g.area)
    stub = LineString(rg.M_TRACE_STUB).buffer(rg.M_TRACE_W, cap_style=2).difference(Point(rg.M_TRACE_BEND).buffer(rg.M_TRACE_W / 2))
    removed = unary_union([mesh_pad, trace.intersection(stub), hv["gnd_top"]])
    kept = trace.difference(stub).difference(hv["d_new"])
    added = unary_union([pad, ext, Point(rg.M_TRACE_BEND).buffer(rg.M_TRACE_W / 2), hv["d_new"]])
    return added, removed, kept, hv


# copper text (F.Cu, 0.3 mm strokes) next to the corner-A HV pads, from today's Gerber
HV_LABELS_A = {"GND bottom": (615.37, 3.74, 619.46, 8.69), "M": (615.98, 12.86, 618.97, 15.68),
               "D": (618.75, 17.99, 621.47, 20.45), "GND top": (624.97, 20.47, 629.06, 25.42)}
LABELS_GONE = ("M", "GND top")             # the D text stays and now labels the merged pad


def is_label_gone(q):
    """Quad of a removed copper-text stroke (M, top GND)."""
    from shapely.geometry import Point, box
    a = np.asarray(q)
    return len(a) == 4 and any(box(*HV_LABELS_A[k]).contains(Point(*a.mean(0))) for k in LABELS_GONE)


def in_pads(q, pads):
    """F.Cu polygon q belongs to one of the pads (same copper)."""
    from shapely.geometry import Point
    c = Point(*np.asarray(q).mean(0))
    return any(P.buffer(0.1).contains(c) for P in pads)


def sig1_polys(F_now, B_now, b2):
    """Today's Sig1 copper that the B2 patch removed (pad zone, pad via, B.Cu trace)."""
    from shapely.geometry import Point, box
    zone = box(575, 3, 622, 27.5)

    def keys(L):
        return {tuple(np.round(np.asarray(q).mean(0), 2)) for q in L}
    out = []
    for L, L2 in ((F_now, b2["F_Cu"]), (B_now, b2["B_Cu"])):
        k2 = keys(L2)
        out.append([q for q in L if zone.contains(Point(*np.asarray(q).mean(0)))
                    and tuple(np.round(np.asarray(q).mean(0), 2)) not in k2])
    return out


def is_b2_patch(q):
    """Copper the first B2 patch added and the 2026 board does not use: pad on Sig1, its F.Cu
    stub to the via, the two vias and the B.Cu route."""
    from shapely.geometry import LineString, Point, Polygon
    g = Polygon(q).buffer(0)
    c = g.centroid
    ox, oy, _ = rg.B2_PAD_OLD
    return (abs(c.x - ox) < 1.6 and abs(c.y - oy) < 1.6 and g.area < 9.5) or (abs(c.x - 590.5) < 0.3 and 7.3 < c.y < 8.6) \
        or Point(590.5, 7.6).distance(c) < 0.1 or Point(626.3, 15.8).distance(c) < 0.1 \
        or LineString(rg.B2_TRACE_BCU).buffer(0.7).contains(g)


def corner_A(C, conns):
    win = (578, 650, -14, 36)
    D, H = rg.read_drill()
    now_f, now_b = copper_polys(C["gerb"]["F_Cu"], win), copper_polys(C["gerb"]["B_Cu"], win)
    new = load_b2(win)
    mnet, mparts = m_net_A(C)
    added, removed, kept, hv = drift_net_A(mparts)
    gone = list(hv["d"]) + [hv["gnd_top"]]
    new["F_Cu"] = [q for q in new["F_Cu"] if not is_b2_patch(q) and not in_pads(q, gone) and not is_label_gone(q)
                   and not mnet.buffer(0.05).contains(rg.Point(*np.asarray(q).mean(0)))]
    new["B_Cu"] = [q for q in new["B_Cu"] if not is_b2_patch(q)]
    _, window, _ = rg.frame_top()
    base = window.buffer(-3.0, join_style=2)
    mesh_now = base.buffer(-rg.MESH_TRIM, join_style=2)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 8.0))
    for ax, F, B, mesh in ((a0, now_f, now_b, mesh_now), (a1, new["F_Cu"], new["B_Cu"], rg.mesh_area())):
        board(ax)
        ax.add_collection(PolyCollection(B, fc=C_BCU, ec="none", alpha=.45, zorder=1))
        ax.add_collection(PolyCollection(F, fc=C_FCU, ec="none", alpha=.75, zorder=2))
        ax.add_patch(poly_patch(mesh, fc=C_MESH, ec="0.5", lw=.5, hatch="....", alpha=.55, zorder=3))
        ax.plot(*np.asarray(base.exterior.coords).T, color="0.35", lw=.7, ls=":", zorder=4)
        for k in (4, 5):
            for x, y in H[k]:
                ax.add_patch(Circle((x, y), D[k] / 2, fc="white", ec="0.4", lw=.7, zorder=5))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    for x, y, d in rg.old_frame_holes(H):
        a0.add_patch(Circle((x, y), d / 2, fc="white", ec="#1f5fbf" if d < 3.2 else "#8e44ad", lw=1.4, zorder=6))
    for no, x, y, _ in rg.new_frame_holes()[0]:
        a1.add_patch(Circle((x, y), rg.SCREW_D / 2, fc="white", ec="black", lw=1.2, zorder=6))
    for c, a, _ in conns:
        a1.add_patch(MPoly(conn_box(c, a), fc="none", ec=C_CONN, lw=1.4, ls="--", zorder=6))
    c = rg.B2_CUT
    a1.plot([c[0], c[0], 600.5], [-1, c[3], c[3]], color=C_OPEN, lw=1.6, ls="--", zorder=7)
    net = kept.union(added)
    a1.add_patch(poly_patch(net.buffer(rg.CLEAR_HV).difference(net.buffer(0.05)), fc="none", ec="#1b7a2e", lw=.8,
                            ls=(0, (2, 2)), zorder=8))
    a1.add_patch(poly_patch(kept, fc=C_DRIFT, ec="#8a6a00", lw=.8, zorder=8))
    a1.add_patch(poly_patch(added, fc=C_DRIFT, ec="#1b7a2e", lw=1.6, zorder=8))
    a1.add_patch(poly_patch(removed, fc="none", ec=C_OPEN, lw=1.4, hatch="xxxx", zorder=8))
    dc = hv["d_new"].centroid
    a1.text(dc.x, dc.y, "D", fontsize=13, weight="bold", ha="center", va="center", color="#5a3d00", zorder=9)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (589.2, 11.0), (579, 27), "readout pad /Sector0/Sig1")
    callout(a0, (628, 12), (633, -11), "HV pads GND / M / D / GND")
    callout(a0, (632, 33), (612, 32.5), "connector (front)")
    callout(a0, (597.2, 2.7), (581, -9), "mesh-contact pad M (corner A)")
    callout(a0, (592.3, -7.5), (601, -12.5), "screw holes: Ø3.5 plated / not plated")
    x, y, s = rg.B2_PAD
    callout(a1, (x, y), (579, 27), f"NEW drift pad {s:g} × {s:g} mm at ({x:g}, {y:g}),\n"
            "centre of the cleared corner (Sig1 removed)", color="#1b7a2e")
    callout(a1, (597, 6.6), (603, 21), f"NEW {rg.M_TRACE_W:g} mm segment pad → bend ({rg.M_TRACE_BEND[0]:g}, {rg.M_TRACE_BEND[1]:g})\n"
            "of today's mesh line (F.Cu)", color="#1b7a2e")
    callout(a1, (597.2, 2.7), (579, -9), "REMOVE the mesh pad and the\nline's first stub (pad → bend)", color=C_OPEN)
    callout(a1, (612, 9.7), (603, -12.5), "KEEP today's mesh line → now DRIFT\n(dashed: 3 mm keep-out in the GND pour)",
            color="#8a6a00")
    callout(a1, (dc.x + 2.2, dc.y - 1.0), (636, 3), "NEW D pad = the 2 M + 2 D pads\nmerged (6.9 × 8.4 mm), drift HV",
            color="#1b7a2e")
    gt = hv["gnd_top"].centroid
    callout(a1, (gt.x, gt.y), (636, 26), "REMOVE the top GND pad", color=C_OPEN)
    callout(a1, (586.5, 13.5), (612, 31.5), "mesh cut: no mesh for x ≥ 585.5, y ≤ 15", color=C_OPEN)
    h = [Patch(fc=C_FCU, alpha=.75, label="F.Cu"), Patch(fc=C_BCU, alpha=.45, label="B.Cu"),
         Patch(fc=C_DRIFT, ec="#1b7a2e", lw=1.6, label="NEW drift copper (pads gold)"),
         Patch(fc=C_DRIFT, ec="#8a6a00", label="kept: today's mesh line, now drift"),
         Patch(fc="none", ec=C_OPEN, hatch="xxxx", label="REMOVE"),
         Patch(fc=C_MESH, ec="0.5", hatch="....", alpha=.55, label="mesh (laminated last)"),
         Line2D([], [], color=C_OPEN, ls="--", label="mesh cut lines"),
         Line2D([], [], color="#1b7a2e", ls=(0, (2, 2)), label=f"{rg.CLEAR_HV:g} mm keep-out round the drift net"),
         Patch(fc="none", ec=C_CONN, ls="--", label="connector on the back"),
         Line2D([], [], color="0.35", ls=":", label="frame inner wall")]
    fig.legend(handles=h, loc="lower center", ncol=5, fontsize=8.5, frameon=False)
    fig.suptitle("PCB – corner A (bottom right): drift pad at the corner centre, fed by today's mesh line into one "
                 "big D pad; mesh corner cleared", fontsize=13, y=.985)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_corner_A.png"), dpi=130)
    plt.close(fig)
    corner_A_steps(now_f, now_b, new_b2=load_b2(win), mparts=mparts, mnet=mnet, hv=hv,
                   added=added, removed=removed, kept=kept)
    return added, removed, kept, hv


def corner_A_steps(now_f, now_b, new_b2, mparts, mnet, hv, added, removed, kept):
    """The corner-A edits one at a time, each panel showing the board after the previous steps."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    win = (582, 640, -11, 30)
    sig_f, sig_b = sig1_polys(now_f, now_b, new_b2)
    ids = {id(q) for q in sig_f + sig_b}
    F1 = [q for q in now_f if id(q) not in ids]
    B1 = [q for q in now_b if id(q) not in ids]
    F2 = [q for q in F1 if not mnet.buffer(0.05).contains(Point(*np.asarray(q).mean(0)))]
    F3 = [q for q in F2 if not in_pads(q, list(hv["d"]) + [hv["gnd_top"]]) and not is_label_gone(q)]
    parts = sorted(mparts, key=lambda g: g.bounds[0])
    trace = max(parts, key=lambda g: g.area)
    stub = LineString(rg.M_TRACE_STUB).buffer(rg.M_TRACE_W, cap_style=2).difference(
        Point(rg.M_TRACE_BEND).buffer(rg.M_TRACE_W / 2))
    line_kept = trace.difference(stub)
    _, window, _ = rg.frame_top()
    base = window.buffer(-3.0, join_style=2)
    x, y, s = rg.B2_PAD
    dn = hv["d_new"]
    poly = lambda L: unary_union([rg.Polygon(q).buffer(0) for q in L])
    steps = [
        ("1 · Sig1: remove the readout pad (zone), its via and its B.Cu trace.\n"
         "The connector pin stays, with nothing connected to it (floating).", now_f, now_b),
        ("2 · Mesh contact: remove the mesh pad and the first stub of its line.\n"
         "The mesh is cleared from the corner (x ≥ 585.5, y ≤ 15); mesh contact at corner B only.", F1, B1),
        ("3 · HV pads: remove the top GND pad and the M / top GND texts; merge the 2 M + 2 D\n"
         f"pads into ONE pad, label D (8.4 × 6.9 mm), {dn.distance(hv['gnd_bottom']):.2f} mm from the remaining GND pad.", F2, B1),
        (f"4 · Drift contact: {s:g} × {s:g} mm pad at the corner centre ({x:g}, {y:g}), {rg.M_TRACE_W:g} mm segment to\n"
         "the line's bend; the line carries the drift into the D pad. GND pour 3 mm away (dashed).", F3, B1),
    ]
    fig, axs = plt.subplots(2, 2, figsize=(16, 12.5))
    for i, (ax, (title, F, B)) in enumerate(zip(axs.flat, steps)):
        board(ax)
        ax.add_collection(PolyCollection(B, fc=C_BCU, ec="none", alpha=.45, zorder=1))
        ax.add_collection(PolyCollection(F, fc=C_FCU, ec="none", alpha=.75, zorder=2))
        ax.plot(*np.asarray(base.exterior.coords).T, color="0.35", lw=.7, ls=":", zorder=4)
        if i == 0:
            ax.add_patch(poly_patch(poly(sig_f + sig_b), fc="none", ec=C_OPEN, lw=1.2, hatch="xxxx", zorder=8))
            callout(ax, (589.2, 11.0), (584, 26), "Sig1 pad zone + via (F.Cu)", color=C_OPEN)
            callout(ax, (612, 21.5), (606, 27.5), "its B.Cu trace", color=C_OPEN)
        if i == 1:
            ax.add_patch(poly_patch(removed.difference(hv["gnd_top"]), fc="none", ec=C_OPEN, lw=1.4, hatch="xxxx", zorder=8))
            c = rg.B2_CUT
            ax.plot([c[0], c[0], 600.5], [win[2], c[3], c[3]], color=C_OPEN, lw=1.6, ls="--", zorder=7)
            ax.add_patch(poly_patch(line_kept, fc=C_FCU, ec="#a0522d", lw=.6, zorder=6))
            callout(ax, (597.2, 2.7), (584, -8), "mesh pad + first stub", color=C_OPEN)
            callout(ax, (586, 13), (584, 24), "mesh cut lines", color=C_OPEN)
        if i == 2:
            ax.add_patch(poly_patch(line_kept, fc=C_FCU, ec="#a0522d", lw=.6, zorder=6))
            ax.add_patch(poly_patch(hv["gnd_top"], fc="none", ec=C_OPEN, lw=1.4, hatch="xxxx", zorder=8))
            for k in LABELS_GONE:
                ax.add_patch(Rectangle(HV_LABELS_A[k][:2], HV_LABELS_A[k][2] - HV_LABELS_A[k][0],
                                       HV_LABELS_A[k][3] - HV_LABELS_A[k][1], fc="none", ec=C_OPEN, lw=1.2, ls="--", zorder=9))
            callout(ax, (617.5, 14.3), (603, 21), "copper text M and GND (top):\nremove; the D text stays", color=C_OPEN)
            for P in list(hv["m"]) + list(hv["d"]):
                ax.add_patch(poly_patch(P, fc="none", ec="0.3", lw=.7, ls="--", zorder=9))
            ax.add_patch(poly_patch(dn, fc=C_DRIFT, ec="#1b7a2e", lw=1.8, alpha=.85, zorder=8))
            dc = dn.centroid
            ax.text(dc.x, dc.y, "D", fontsize=16, weight="bold", ha="center", va="center", color="#5a3d00", zorder=10)
            a, b = [np.asarray(p.coords[0]) for p in __import__("shapely.ops", fromlist=["x"]).nearest_points(dn, hv["gnd_bottom"])]
            dim(ax, tuple(a), tuple(b), (-1.2, 0.7), f"{dn.distance(hv['gnd_bottom']):.2f}", fs=8)
            gt = hv["gnd_top"].centroid
            callout(ax, (gt.x, gt.y), (618, 27), "top GND pad: remove", color=C_OPEN)
            callout(ax, (dc.x + 2.5, dc.y - 1.5), (632, 0.5), "M M + D D (dashed)\n→ one D pad", color="#1b7a2e")
            gb = hv["gnd_bottom"].centroid
            callout(ax, (gb.x, gb.y), (606, -8), "bottom GND pad: stays", color="0.2")
        if i == 3:
            net = kept.union(added)
            ax.add_patch(poly_patch(net.buffer(rg.CLEAR_HV).difference(net.buffer(0.05)), fc="none", ec="#1b7a2e",
                                    lw=.8, ls=(0, (2, 2)), zorder=8))
            ax.add_patch(poly_patch(kept, fc=C_DRIFT, ec="#8a6a00", lw=.8, zorder=8))
            ax.add_patch(poly_patch(added, fc=C_DRIFT, ec="#1b7a2e", lw=1.6, zorder=8))
            dc = dn.centroid
            ax.text(dc.x, dc.y, "D", fontsize=16, weight="bold", ha="center", va="center", color="#5a3d00", zorder=10)
            ax.add_patch(poly_patch(rg.mesh_area(), fc=C_MESH, ec="0.5", lw=.5, hatch="....", alpha=.55, zorder=3))
            callout(ax, (x, y), (584, 24), f"drift pad {s:g} × {s:g}", color="#1b7a2e")
            callout(ax, (597, 6.6), (600, 25), f"{rg.M_TRACE_W:g} mm segment", color="#1b7a2e")
            callout(ax, (612, 9.7), (604, -8), "today's mesh line = drift line", color="#8a6a00")
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_title(title, fontsize=10.5, loc="left", weight="bold", color="0.1")
    h = [Patch(fc=C_FCU, alpha=.75, label="F.Cu"), Patch(fc=C_BCU, alpha=.45, label="B.Cu"),
         Patch(fc="none", ec=C_OPEN, hatch="xxxx", label="REMOVE (this step)"),
         Patch(fc=C_DRIFT, ec="#1b7a2e", lw=1.6, label="NEW drift copper"),
         Patch(fc=C_DRIFT, ec="#8a6a00", label="kept line, now drift"),
         Line2D([], [], color="#1b7a2e", ls=(0, (2, 2)), label=f"{rg.CLEAR_HV:g} mm keep-out"),
         Line2D([], [], color="0.35", ls=":", label="frame inner wall")]
    fig.legend(handles=h, loc="lower center", ncol=7, fontsize=9, frameon=False)
    fig.suptitle("PCB – corner A step by step (each panel = the board after the previous steps; "
                 "coordinates in pcb_corner_A_drift.csv)", fontsize=13.5, y=.99)
    fig.tight_layout(rect=(0, 0.035, 1, 0.97), h_pad=3.5)
    fig.savefig(os.path.join(FIG, "pcb_corner_A_steps.png"), dpi=130)
    plt.close(fig)


def marks_fig(mk):
    new, best = mk
    win = (52, 118, 5, 93)
    D, H = rg.read_drill()
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 9.2))
    for ax in (a0, a1):
        board(ax)
        ax.add_patch(poly_patch(rg.frame_top()[0].difference(rg.frame_top()[1]), fc="none", ec="0.55", lw=.7, ls=":", zorder=1))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    for x, y, d in rg.old_frame_holes(H):
        a0.add_patch(Circle((x, y), d / 2, fc="white", ec="#1f5fbf" if d < 3.2 else "#8e44ad", lw=1.4, zorder=5))
    newh = rg.new_frame_holes()[0]
    for no, x, y, _ in newh:
        a1.add_patch(Circle((x, y), rg.SCREW_D / 2, fc="white", ec="black", lw=1.2, zorder=5))
        if win[0] < x < win[1] and win[2] < y < win[3]:
            a1.annotate(f"hole {no}", (x, y), (x - 9, y + 4), fontsize=8)
    for i in (1, 2):
        cross(a0, MARKS_NOW[i], CROSS_NOW, 1.2, "#c0392b", zorder=6)
        a0.annotate(f"cross {i}: 3 × 3 mm\n({MARKS_NOW[i][0]:.2f}, {MARKS_NOW[i][1]:.2f})", MARKS_NOW[i],
                    (MARKS_NOW[i][0] + 5, MARKS_NOW[i][1] - 9), fontsize=8.5, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=.7))
        cross(a1, MARKS_NOW[i], CROSS_NEW, 1.0, "0.6", zorder=4, alpha=.6)
        d_old = min(math.hypot(x - MARKS_NOW[i][0], y - MARKS_NOW[i][1]) for _, x, y, _ in newh)
        a1.annotate(f"today's position: only {d_old:.1f} mm\nto a new screw hole – moved", MARKS_NOW[i],
                    (MARKS_NOW[i][0] - 17, MARKS_NOW[i][1] - 12), fontsize=8, color="0.4",
                    arrowprops=dict(arrowstyle="->", color="0.5", lw=.7))
        cross(a1, new[i], CROSS_NEW, 2.0, "#c0392b", square=SQUARE_NEW, zorder=6)
        a1.annotate("", new[i], MARKS_NOW[i], arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.3, ls="--"))
        a1.annotate(f"cross {i} NEW\n({new[i][0]:.2f}, {new[i][1]:.2f})", new[i], (new[i][0] + 7.5, new[i][1] + 3),
                    fontsize=9, color="#c0392b", weight="bold")
    a0.set_title("NOW (inner arc, crosses 1 and 2)", fontsize=12, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    fig.text(0.06, 0.09,
             f"All 4 crosses: copper cross {CROSS_NEW:g} mm across, {LINE_NEW:g} mm lines, on F.Cu and B.Cu; masks: cross outline 10 mm / 1.3 mm arms\n"
             f"in a {SQUARE_NEW:g} × {SQUARE_NEW:g} mm resist square (dashed).  Crosses 1 and 2 move to r = {best['r_mm']:g} mm, at {60 - best['angle_deg']:g}° and "
             f"{best['angle_deg']:g}° (mirror pair):\n{best['patch_half_mm']:.1f} mm free round the centre (6.25 needed).  "
             "Crosses 3 and 4 stay where they are (table pcb_alignment_marks.csv).",
             fontsize=9, va="top", bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    fig.suptitle("PCB – alignment crosses: bigger, and crosses 1, 2 moved clear of the new screw holes", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.11, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_alignment_marks.png"), dpi=130)
    plt.close(fig)


def cross_shape(c, size, w):
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    x, y = c
    h = size / 2
    return unary_union([LineString([(x - h, y), (x + h, y)]).buffer(w / 2, cap_style=2),
                        LineString([(x, y - h), (x, y + h)]).buffer(w / 2, cap_style=2)])


def marks_outer_fig(C, conns):
    """Crosses 3 and 4 (outer arc, between connectors 1-2 and 9-10): they stay where they are and
    become bigger. NOW vs NEW per cross, on today's copper, with the clearances of the new cross."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    D, H = rg.read_drill()
    half = 10.0
    fig, axs = plt.subplots(2, 2, figsize=(14.5, 14.2))
    notes = []
    for row, i in zip(axs, (3, 4)):
        c = MARKS_NOW[i]
        win = (c[0] - half, c[0] + half, c[1] - half, c[1] + half)
        F, B = copper_polys(C["gerb"]["F_Cu"], win), copper_polys(C["gerb"]["B_Cu"], win)
        is_old_cross = lambda q: Point(*np.asarray(q).mean(0)).distance(Point(c)) < 1.6 and Polygon(q).area < 1.0
        F = [q for q in F if not is_old_cross(q)]
        B = [q for q in B if not is_old_cross(q)]
        hatch = lambda q: len(q) > 200 or Polygon(q).buffer(0).area > 150
        holes = [Point(x, y).buffer(D[k] / 2, 32) for k in H for x, y in H[k]
                 if win[0] - 3 < x < win[1] + 3 and win[2] - 3 < y < win[3] + 3]
        cu_new = cross_shape(c, CROSS_NEW, LINE_NEW)
        sq = box(c[0] - SQUARE_NEW / 2, c[1] - SQUARE_NEW / 2, c[0] + SQUARE_NEW / 2, c[1] + SQUARE_NEW / 2)
        d_f = min(cu_new.distance(Polygon(q).buffer(0)) for q in F if not hatch(q))
        d_b = min(cu_new.distance(Polygon(q).buffer(0)) for q in B if not hatch(q))
        d_h = min(cu_new.distance(hg) for hg in holes)
        d_sq_h = min(sq.distance(hg) for hg in holes)
        d_sq_pad = min((sq.distance(Polygon(q).buffer(0)) for q in F if not hatch(q) and Polygon(q).buffer(0).area > 0.05
                        and any(Point(*np.asarray(q).mean(0)).within(Polygon(conn_box(cc, a)).buffer(1)) for cc, a, _ in conns)),
                       default=float("inf"))
        notes.append((i, d_f, d_b, d_h, d_sq_h, d_sq_pad))
        for ax, new in zip(row, (False, True)):
            board(ax)
            ax.add_collection(PolyCollection(B, fc=C_BCU, ec="none", alpha=.45, zorder=1))
            ax.add_collection(PolyCollection(F, fc=C_FCU, ec="none", alpha=.75, zorder=2))
            if new:
                ax.annotate("today's GND-hatch cut-out round the\nsmall cross: re-poured round the new one",
                            (c[0] + 1.6, c[1] + 1.2), (c[0] + 1.0, c[1] + 6.3), fontsize=7.5, color="0.3",
                            arrowprops=dict(arrowstyle="->", color="0.4", lw=.6),
                            bbox=dict(fc="white", ec="none", alpha=.85), zorder=9)
            for hg in holes:
                ax.add_patch(poly_patch(hg, fc="white", ec="0.35", lw=.7, zorder=3))
            if not new:
                cross(ax, c, CROSS_NOW, 1.4, "#c0392b", zorder=6)
                # today's mask: rounded cross outline 2.9 mm / 1.16 mm arms in a 10 x 10 mm resist square
                ax.add_patch(poly_patch(cross_shape(c, 2.9, 1.16), fc="none", ec="#1f5fbf", lw=1.0, ls="--", zorder=6))
                ax.add_patch(Rectangle((c[0] - 5, c[1] - 5), 10, 10, fc="#1f5fbf", alpha=.08, ec="#1f5fbf", lw=1.0, zorder=5))
                ax.annotate(f"cross {i} today: 3 × 3 mm, 0.12 mm lines\n({c[0]:.2f}, {c[1]:.2f})", c,
                            (c[0] - 9.5, c[1] + 7.6), fontsize=8.5, color="#c0392b",
                            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=.7),
                            bbox=dict(fc="white", ec="none", alpha=.85))
                ax.text(c[0] + 5.2, c[1] - 6.5, "mask today: 2.9 mm outline\nin a 10 × 10 resist square", fontsize=8,
                        color="#1f5fbf", bbox=dict(fc="white", ec="none", alpha=.85))
            else:
                for cc, a, _ in conns:
                    ax.add_patch(MPoly(conn_box(cc, a), fc="none", ec=C_CONN, lw=1.4, ls="--", zorder=6))
                ax.add_patch(poly_patch(cu_new, fc="#c0392b", ec="none", zorder=7))
                ax.add_patch(poly_patch(cross_shape(c, 10.0, 1.3), fc="none", ec="#1f5fbf", lw=1.2, ls="--", zorder=7))
                ax.add_patch(Rectangle((c[0] - SQUARE_NEW / 2, c[1] - SQUARE_NEW / 2), SQUARE_NEW, SQUARE_NEW,
                                       fc="#1f5fbf", alpha=.08, ec="#1f5fbf", lw=1.2, zorder=5))
                dim(ax, (c[0] - CROSS_NEW / 2, c[1] - CROSS_NEW / 2 - .8), (c[0] + CROSS_NEW / 2, c[1] - CROSS_NEW / 2 - .8),
                    (0, 0), f"{CROSS_NEW:g} mm", fs=8, color="#c0392b")
                dim(ax, (c[0] - SQUARE_NEW / 2, c[1] + SQUARE_NEW / 2), (c[0] + SQUARE_NEW / 2, c[1] + SQUARE_NEW / 2),
                    (0, .9), f"{SQUARE_NEW:g} mm resist square", fs=8, color="#1f5fbf")
                ax.text(win[0] + .4, win[2] + .4,
                        f"same centre ({c[0]:.2f}, {c[1]:.2f})\n"
                        f"new copper cross → nearest copper: F.Cu {d_f:.1f} mm, B.Cu {d_b:.1f} mm\n"
                        f"                         → nearest hole: {d_h:.1f} mm\n"
                        f"resist square → nearest hole: {d_sq_h:.1f} mm; connector pads: "
                        f"{'none in view' if d_sq_pad == float('inf') else ('none under it, %.1f mm' % d_sq_pad if d_sq_pad > 0 else 'OVERLAP')}\n"
                        "(GND hatch not counted: it is re-poured round the cross)",
                        fontsize=8, va="bottom", bbox=dict(fc="white", ec=C_EXT_EC, alpha=.92, boxstyle="round,pad=.4"),
                        zorder=9)
            ax.set_xlim(win[0], win[1])
            ax.set_ylim(win[2], win[3])
            ax.set_aspect("equal")
            ax.grid(lw=.25, alpha=.4)
            ax.tick_params(labelsize=7)
            ax.set_xlabel("x [mm]", fontsize=8)
            ax.set_ylabel("y [mm]", fontsize=8)
            where = "between connectors 1 and 2" if i == 3 else "between connectors 9 and 10"
            ax.set_title(f"cross {i} – {'NOW' if not new else 'NEW'}  ({where})", fontsize=11.5, weight="bold", loc="left",
                         color=C_EXT_EC if new else "black")
    h = [Line2D([], [], color="#c0392b", lw=3, label=f"copper cross (F.Cu + B.Cu): NEW {CROSS_NEW:g} mm, {LINE_NEW:g} mm lines"),
         Line2D([], [], color="#1f5fbf", ls="--", label="mask cross outline (M1, M2): NEW 10 mm, 1.3 mm arms"),
         Patch(fc="#1f5fbf", alpha=.15, ec="#1f5fbf", label=f"mask resist square: NEW {SQUARE_NEW:g} mm"),
         Patch(fc="none", ec=C_CONN, ls="--", label="connector footprint (moves to the BACK)"),
         Patch(fc=C_FCU, alpha=.75, label="F.Cu"), Patch(fc=C_BCU, alpha=.45, label="B.Cu"),
         Patch(fc="white", ec="0.35", label="holes")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("PCB – alignment crosses 3 and 4 (outer arc): same place, bigger cross and mask outline", fontsize=14, y=.99)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(os.path.join(FIG, "pcb_alignment_marks_outer.png"), dpi=130)
    plt.close(fig)
    return notes


def connector_side():
    """Radial section through a connector: NOW on the front, NEW on the back."""
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(13, 8.4))
    for ax, new in ((a0, False), (a1, True)):
        ax.add_patch(Rectangle((585, -0.2), 65, 0.2, fc="#2e7d32", alpha=.6))
        ax.add_patch(Rectangle((585, 0), 615 - 585, 8, fc="#c9cdd4", ec="#5b6170"))
        if new:
            ax.add_patch(Rectangle((615, 0), 650 - 615, 8, fc="#f4a742", ec="#b8650a"))
            ax.add_patch(Rectangle((585, -3.2), rg.CB_R_OUT - 585, 3.0, fc="#4a4f57"))
            ax.add_patch(Rectangle((rg.CONN_R_IN, -6.2), rg.CONN_R_OUT - rg.CONN_R_IN, 6.0, fc=C_FCU, ec="#a0522d"))
            dim(ax, (rg.CB_R_OUT, -3.2), (rg.CONN_R_IN, -3.2), (0, -1.6), f"{rg.CONN_R_IN - rg.CB_R_OUT:.1f}", fs=8)
            ax.text(632.1, -3.3, "connector\n(back, B.Cu)", ha="center", va="center", fontsize=8)
            ax.text(600, -1.7, "carbon back", color="white", ha="center", va="center", fontsize=8)
            ax.text(632, 4, "frame extension (front)", ha="center", va="center", fontsize=8)
        else:
            ax.add_patch(Rectangle((585, -3.2), 650 - 585, 3.0, fc="#4a4f57"))
            ax.add_patch(Rectangle((rg.CONN_R_IN, 0), rg.CONN_R_OUT - rg.CONN_R_IN, 6.0, fc=C_FCU, ec="#a0522d"))
            ax.text(632.1, 3, "connector\n(front, F.Cu)", ha="center", va="center", fontsize=8)
            ax.text(615, -1.7, "carbon back (to R650)", color="white", ha="center", va="center", fontsize=8)
        ax.text(600, 4, "drift frame", ha="center", va="center", fontsize=8)
        ax.text(646, 0.4, "PCB", fontsize=8, color="#1b4d1e")
        ax.set_xlim(585, 652)
        ax.set_ylim(-9, 10)
        ax.set_aspect("equal")
        ax.set_yticks([])
        ax.tick_params(labelsize=7)
        ax.set_xlabel("r [mm]  (radial section through a connector)", fontsize=8)
    a0.set_title("NOW – connectors on the front, carbon back under them", fontsize=11, loc="left", weight="bold")
    a1.set_title("NEW – connectors on the back; frame extension supports the front", fontsize=11, loc="left",
                 weight="bold", color=C_EXT_EC)
    fig.text(0.5, 0.02, "Flipping a footprint to the other side mirrors its pin order: check the mating side "
             "(adapter card / channel mapping) before routing.", ha="center", fontsize=10, color="#c0392b")
    fig.suptitle("PCB – FX20-140P connectors move to the back side (schematic, heights not to scale)", fontsize=13, y=.985)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_connectors_back.png"), dpi=130)
    plt.close(fig)


def tables(conns, mk):
    new, best = mk                          # screw holes: fig_pcb_holes.py (pcb_screw_holes.csv)
    with open(os.path.join(DATA, "pcb_alignment_marks.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cross", "x_now", "y_now", "x_new", "y_new", "copper_cross_mm", "line_mm", "mask_resist_square_mm", "layers"])
        for i in (1, 2, 3, 4):
            w.writerow([i, *MARKS_NOW[i], f"{new[i][0]:.2f}", f"{new[i][1]:.2f}", CROSS_NEW, LINE_NEW, SQUARE_NEW,
                        "F.Cu, B.Cu, M1, M2"])
    with open(os.path.join(DATA, "pcb_connectors.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["connector", "x_centre", "y_centre", "angle_deg", "pads_today", "side_now", "side_new"])
        for i, (c, a, n) in enumerate(conns, 1):
            w.writerow([i, f"{c[0]:.2f}", f"{c[1]:.2f}", f"{a:.2f}", n, "F.Cu", "B.Cu (same position)"])
    with open(os.path.join(DATA, "pcb_mesh_cut.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["point", "x_mm", "y_mm", "note"])
        y1 = rg.B2_CUT[3]
        for k, (x, y, t) in enumerate(((rg.B2_CUT[0], 0.0, "start at the bottom frame wall"),
                                       (rg.B2_CUT[0], y1, "corner"),
                                       (math.sqrt(600 ** 2 - y1 ** 2), y1, "end at the outer-arc frame wall")), 1):
            w.writerow([k, f"{x:.2f}", f"{y:.2f}", t])


def drift_table(added, removed, kept, hv):
    """Corner A changes for the KiCad designer (pcb_corner_A_drift.csv), in the order of the steps."""
    x, y, sd = rg.B2_PAD
    dn = hv["d_new"]
    corners = " ".join(f"({a:.2f}, {b:.2f})" for a, b in list(dn.exterior.coords)[:4])
    b = rg.M_TRACE_BEND
    rows = [
        ["remove", "step 1: readout pad /Sector0/Sig1: zone, pad via, B.Cu trace to the via at (619.97, 26.00)",
         "F.Cu + B.Cu + drill", "", "", "", "",
         "as in drift_pad_B2/CHANGES.txt; the connector pin stays, nothing connected (floating)"],
        ["remove", "step 2: mesh-contact pad (gold)", "F.Cu + ENIG", *[f"{v:.2f}" for v in rg.M_PAD_A],
         "no mesh in this corner any more; mesh contact at corner B only"],
        ["remove", f"step 2: first stub of the mesh line ({rg.M_TRACE_W:g} mm), mesh pad -> bend", "F.Cu",
         *[f"{v:.2f}" for p in rg.M_TRACE_STUB for v in p], "start and end points (not a box); the rest of the line is kept"],
        ["remove", "step 3: copper text 'M' (0.3 mm strokes)", "F.Cu", *[f"{v:.2f}" for v in HV_LABELS_A["M"]],
         "the 'D' text stays and labels the new pad"],
        ["remove", "step 3: copper text 'GND' next to the top GND pad", "F.Cu", *[f"{v:.2f}" for v in HV_LABELS_A["GND top"]],
         "goes with its pad"],
        ["remove", "step 3: top GND solder pad (gold), the one towards the connector", "F.Cu + ENIG",
         *[f"{v:.2f}" for v in hv["gnd_top"].bounds], "the bottom GND pad stays"],
        ["change", "step 3: the 2 M + 2 D solder pads -> ONE pad, silkscreen D, net DRIFT_A (gold)", "F.Cu + ENIG",
         *[f"{v:.2f}" for v in dn.bounds],
         f"rotated rectangle 8.38 x 6.86 mm (sides along / across the chamfer), corners {corners}; "
         f"= envelope of the 4 old pads; {dn.distance(hv['gnd_bottom']):.2f} mm from the bottom GND pad; drift cable here"],
        ["add", f"step 4: drift pad {sd:g} x {sd:g} mm, net DRIFT_A (SMD, gold)", "F.Cu + ENIG",
         f"{x - sd / 2:.2f}", f"{y - sd / 2:.2f}", f"{x + sd / 2:.2f}", f"{y + sd / 2:.2f}",
         f"centre ({x:g}, {y:g}) = centre of the cleared corner"],
        ["add", f"step 4: trace {rg.M_TRACE_W:g} mm, pad centre -> bend of today's mesh line", "F.Cu",
         f"{x:.2f}", f"{y:.2f}", f"{b[0]:.2f}", f"{b[1]:.2f}", "start and end points (not a box); same width as the mesh line"],
        ["keep", "step 4: today's mesh line from the bend to the new D pad, renamed net DRIFT_A", "F.Cu",
         *[f"{v:.2f}" for v in kept.bounds], "now carries the drift HV"],
    ]
    rows += [
        ["change", f"GND pour (F.Cu): {rg.CLEAR_HV:g} mm keep-out round the whole DRIFT_A net", "F.Cu", "", "", "", "",
         "today the mesh line is 0.5 mm from the GND pour"],
        ["check", "screw hole 13 (610.30, 14.50), kept on the outer arc, plated today (pad Ø4.56)", "F.Cu + B.Cu",
         "607.98", "12.18", "612.62", "16.82",
         "pad 2.65 mm from the drift line (< 3 mm); non-plated, no pad: 3.2 mm to the hole edge"],
        ["mask", "M1, M2: window over the drift pad moves with the pad (resist island unchanged)", "M1 + M2",
         f"{x - 1.8:.2f}", f"{y - 1.8:.2f}", f"{x + 1.8:.2f}", f"{y + 1.8:.2f}", "3.6 x 3.6 mm, as for the first B2 pad"],
        ["mask", "window over the mesh pad: closed (resist)", "M2", *[f"{v:.2f}" for v in M_WIN_M2], "the pad is gone"],
        ["not used", "first B2 patch: pad at (590.5, 10.0), vias (590.5, 7.6) and (626.3, 15.8), B.Cu drift route",
         "F.Cu + B.Cu + drill", "", "", "", "", "replaced by the F.Cu feed above: no via, no back copper"],
    ]
    with open(os.path.join(DATA, "pcb_corner_A_drift.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["action", "item", "layer", "x0_mm", "y0_mm", "x1_mm", "y1_mm", "note"])
        w.writerows(rows)


def main():
    C = pickle.load(open(CACHE, "rb"))
    conns = connectors(C)
    mk = marks_new()
    overview(C, conns, mk)
    drift_table(*corner_A(C, conns))
    print('outer crosses (no, F.Cu, B.Cu, hole, square-hole, square-pads):',
          [tuple(round(v, 2) for v in n) for n in marks_outer_fig(C, conns)])
    del C
    gc.collect()
    marks_fig(mk)
    connector_side()
    tables(conns, mk)
    print("written pcb_overview, pcb_corner_A(_steps), pcb_alignment_marks(_outer), pcb_connectors_back + data/pcb_*.csv")


if __name__ == "__main__":
    main()
