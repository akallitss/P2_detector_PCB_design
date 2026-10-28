#!/usr/bin/env python3
"""
Corner B (top): the only mesh contact of the 2026 board (decided 2026-10-28).

HV solder pads (outside the frame), along x: GND (x 315), two M pads, two D pads, GND (x 332.6).
  * the two D pads and the GND pad at x 315 go, with the copper texts "D" and that "GND";
  * the 2 M + 2 D pads merge into ONE pad, label M (the envelope of the four), for the mesh cable.
Mesh-contact pad (active area, at the corner apex; today a 2.75 mm square rotated 30 deg, ~5 mm2 under the mesh):
  * the largest square that stays inside the frame opening and 1.5 mm from every readout pad (as today):
    4.07 mm, same 30 deg orientation, moved 0.75 mm into the apex ("option 2", chosen 2026-10-28 from
    pcb_corner_B_pad_options.png; a band along the walls was tried first and dropped);
  * M1 / M2 windows: the new square, 0.3 / 0.45 mm inside (make_masks_2026.py).

Writes ../figures/pcb_corner_B.png, ../data/pcb_corner_B_mesh.csv, ../data/pcb_corner_B_mesh_pad.csv
(with --options also ../figures/pcb_corner_B_pad_options.png, the search behind MESH_PAD_NEW)
Run with (ulimit -v 3500000; python3 fig_pcb_corner_B.py)
"""
import csv
import math
import os
import pickle

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

import fig_pcb as fp

rg = fp.rg
CLEAR_RO = 1.5                       # mesh pad <-> readout pads (as today)
MESH_PAD_NEW = ((300.72, 516.72), 4.07, -30.0)   # centre, side, angle: square_options() 'largest' (option 2)
WIN_M1, WIN_M2 = 0.3, 0.45           # mask windows: the pad, shrunk by this
MESH_PAD_NOW = (299.04, 514.02, 302.92, 517.92)    # bounds of today's (rotated) mesh pad
HV_LABELS_B = {"GND left": (311.6, 530.33, 316.8, 533.03), "M": (319.7, 526.68, 321.9, 529.38),
               "D": (325.87, 526.58, 327.93, 529.28), "GND right": (330.79, 530.4, 335.99, 533.1)}
LABELS_GONE_B = ("GND left", "D")
WIN = (284, 340, 494, 546)


def hv_pads_B():
    p = sorted(rg.hv_pads()["B"], key=lambda g: g.centroid.x)
    return {"gnd_left": p[0], "m": p[1:3], "d": p[3:5], "gnd_right": p[5],
            "m_new": unary_union(p[1:5]).minimum_rotated_rectangle}


def geometry():
    C = pickle.load(open(fp.CACHE, "rb"))
    w = (WIN[0], WIN[1], WIN[2], WIN[3])
    Fq, Bq = fp.copper_polys(C["gerb"]["F_Cu"], w), fp.copper_polys(C["gerb"]["B_Cu"], w)
    del C
    F = [Polygon(q).buffer(0) for q in Fq]
    pad_now = [g for g in F if box(*MESH_PAD_NOW).buffer(0.05).contains(g) and g.area > 5][0]
    trace = [g for g in F if g.area < 30 and g.distance(pad_now) < 0.05 and not g.equals(pad_now)]
    hv = hv_pads_B()
    hv_all = unary_union(list(hv["m"]) + list(hv["d"]) + [hv["gnd_left"], hv["gnd_right"]])
    readout = [g for g in F if 100 < g.area < 300]                       # readout pads (~133 mm2)
    others = unary_union([g for g in F if g.area < 300 and not g.equals(pad_now)
                          and not any(g.equals(t) for t in trace) and not g.intersects(hv_all.buffer(0.05))])
    _, window, _ = rg.frame_top()
    base = window.buffer(-3.0, join_style=2)
    mesh = base.buffer(-rg.MESH_TRIM, join_style=2)
    corner_ro = min(readout, key=lambda g: g.distance(pad_now))
    pad_new = square(*MESH_PAD_NEW)
    assert pad_new.distance(others) >= CLEAR_RO - 1e-3 and base.buffer(1e-3).contains(pad_new)
    return dict(Fq=Fq, Bq=Bq, F=F, pad_now=pad_now, trace=unary_union(trace), hv=hv, others=others, base=base,
                mesh=mesh, corner_ro=corner_ro, pad_new=pad_new)


def windows(G):
    """New M1 / M2 windows over the mesh pad (as today: about the pad itself), shrunk a little."""
    P = G["pad_new"]
    return P.buffer(-WIN_M1, join_style=2), P.buffer(-WIN_M2, join_style=2)


def is_label_gone_B(q):
    a = np.asarray(q)
    return len(a) == 4 and any(box(*HV_LABELS_B[k]).contains(Point(*a.mean(0))) for k in LABELS_GONE_B)


def figure(G):
    hv, pn, pnow = G["hv"], G["pad_new"], G["pad_now"]
    gone = list(hv["d"]) + [hv["gnd_left"]]
    F_new = [q for q in G["Fq"] if not fp.in_pads(q, list(hv["m"]) + gone) and not is_label_gone_B(q)
             and not Polygon(q).buffer(0).equals(pnow)]
    w1, w2 = windows(G)
    fig, axs = plt.subplots(1, 3, figsize=(20, 8.4), gridspec_kw=dict(width_ratios=[1, 1, 1.05]))
    for ax, F, new in ((axs[0], G["Fq"], False), (axs[1], F_new, True), (axs[2], F_new, True)):
        fp.board(ax)
        ax.add_collection(PolyCollection(G["Bq"], fc=fp.C_BCU, ec="none", alpha=.45, zorder=1))
        ax.add_collection(PolyCollection(F, fc=fp.C_FCU, ec="none", alpha=.75, zorder=2))
        ax.plot(*np.asarray(G["base"].exterior.coords).T, color="0.35", lw=.7, ls=":", zorder=4)
        ax.add_patch(fp.poly_patch(G["mesh"], fc=fp.C_MESH, ec="0.5", lw=.5, hatch="....", alpha=.35, zorder=3))
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
        if new:
            ax.add_patch(fp.poly_patch(pn, fc=C_MESHPAD, ec="#1b7a2e", lw=1.5, zorder=6))
            ax.add_patch(fp.poly_patch(hv["m_new"], fc=C_MESHPAD, ec="#1b7a2e", lw=1.5, zorder=6))
            mc = hv["m_new"].centroid
            ax.text(mc.x, mc.y, "M", fontsize=13, weight="bold", ha="center", va="center", color="#11461d", zorder=9,
                    clip_on=True)
            ax.add_patch(fp.poly_patch(hv["gnd_left"], fc="none", ec=fp.C_OPEN, lw=1.3, hatch="xxxx", zorder=7))
            for P in list(hv["m"]) + list(hv["d"]):
                ax.add_patch(fp.poly_patch(P, fc="none", ec="0.3", lw=.6, ls="--", zorder=7))
            for k in LABELS_GONE_B:
                b = HV_LABELS_B[k]
                ax.add_patch(Rectangle(b[:2], b[2] - b[0], b[3] - b[1], fc="none", ec=fp.C_OPEN, lw=1.0, ls="--", zorder=7))
    a0, a1, a2 = axs
    for ax in (a0, a1):
        ax.set_xlim(WIN[0], WIN[1])
        ax.set_ylim(WIN[2], WIN[3])
    a0.add_patch(fp.poly_patch(pnow, fc="none", ec="#1f5fbf", lw=1.4, zorder=6))
    fp.callout(a0, pnow.centroid.coords[0], (286, 529), "mesh-contact pad 2.75 × 2.75 mm\n(only ~5 mm² under the mesh)", color="#1f5fbf")
    fp.callout(a0, (304, 505), (306, 497), "readout pads (/Sector9/...)")
    fp.callout(a0, (323.9, 536.4), (318, 543.5), "HV pads GND / M M / D D / GND", color="0.2")
    gl, gr = hv["gnd_left"].centroid, hv["gnd_right"].centroid
    fp.callout(a1, (gl.x, gl.y), (287, 541), "REMOVE this GND pad\n(+ its GND text)", color=fp.C_OPEN)
    fp.callout(a1, (326.7, 534.4), (321, 520), "M M + D D (dashed) merged into ONE\nM pad (mesh cable); D text removed", color="#1b7a2e")
    fp.callout(a1, (gr.x, gr.y), (328, 544), "GND pad stays", color="0.2")
    fp.callout(a1, (301.5, 516.5), (305, 506), "NEW mesh-contact pad: largest\nsquare, 4.07 mm (zoom →)", color="#1b7a2e")
    # zoom on the mesh pad with clearances and mask windows
    zx = (290, 313, 503, 522)
    a2.set_xlim(zx[0], zx[1])
    a2.set_ylim(zx[2], zx[3])
    a2.add_patch(fp.poly_patch(w1, fc="none", ec="#1f5fbf", lw=1.0, ls="--", zorder=8))
    a2.add_patch(fp.poly_patch(pnow, fc="none", ec="0.2", lw=1.0, ls=":", zorder=8))
    ro = G["others"].intersection(box(*[zx[0], zx[2], zx[1], zx[3]]))
    a2.add_patch(fp.poly_patch(pn.buffer(CLEAR_RO).difference(pn.buffer(0.05)), fc="none", ec="#c0392b", lw=.7,
                               ls=(0, (2, 2)), zorder=7))
    d = pn.distance(G["others"])
    fp.callout(a2, (301.6, 512.6), (304.5, 509.5), f"{d:.2f} mm to the nearest readout pad\n(red dashed: {CLEAR_RO:g} mm)", color="#c0392b")
    fp.callout(a2, (pnow.centroid.x - .6, pnow.centroid.y - .3), (290.5, 520.5), "today's pad (dotted)", color="0.2")
    under_now, under_new = pnow.intersection(G["mesh"]).area, pn.intersection(G["mesh"]).area
    a2.text(zx[0] + .4, zx[2] + .4,
            f"NEW mesh-contact pad: square {MESH_PAD_NEW[1]:.2f} mm, rotated 30° as today,\n"
            f"centre ({MESH_PAD_NEW[0][0]:.2f}, {MESH_PAD_NEW[0][1]:.2f}) (corners in pcb_corner_B_mesh_pad.csv)\n"
            f"copper {pn.area:.1f} mm² (today {pnow.area:.1f}), under the mesh {under_new:.1f} mm² (today {under_now:.1f})\n"
            f"M1 window (blue dashed): the pad, {WIN_M1:g} mm inside; M2: {WIN_M2:g} mm inside.\n"
            "The F.Cu GND hatch near the wall is re-poured round the pad (as today)",
            fontsize=8.5, va="bottom", bbox=dict(fc="white", ec=fp.C_EXT_EC, alpha=.92, boxstyle="round,pad=.4"), zorder=9)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=fp.C_EXT_EC)
    a2.set_title("NEW – zoom on the mesh-contact pad", fontsize=12, weight="bold", loc="left", color=fp.C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    h = [Patch(fc=fp.C_FCU, alpha=.75, label="F.Cu"), Patch(fc=fp.C_BCU, alpha=.45, label="B.Cu"),
         Patch(fc=C_MESHPAD, ec="#1b7a2e", label="NEW mesh copper (pads gold)"),
         Patch(fc="none", ec=fp.C_OPEN, hatch="xxxx", label="REMOVE"),
         Patch(fc=fp.C_MESH, ec="0.5", hatch="....", alpha=.4, label="mesh (laminated last)"),
         Line2D([], [], color="#c0392b", ls=(0, (2, 2)), label=f"{CLEAR_RO:g} mm round the mesh pad"),
         Line2D([], [], color="#1f5fbf", ls="--", label="M1 window"),
         Line2D([], [], color="0.35", ls=":", label="frame inner wall")]
    fig.legend(handles=h, loc="lower center", ncol=8, fontsize=8.5, frameon=False)
    fig.suptitle("PCB – corner B (top): the only mesh contact; one big M solder pad, bigger mesh-contact pad",
                 fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(fp.FIG, "pcb_corner_B.png"), dpi=130)
    plt.close(fig)
    return d, under_now, under_new


C_MESHPAD = "#9fd48a"


def tables(G, d):
    hv, pn = G["hv"], G["pad_new"]
    mn = hv["m_new"]
    corners = " ".join(f"({a:.2f}, {b:.2f})" for a, b in list(mn.exterior.coords)[:4])
    xy = np.asarray(mn.exterior.coords)
    sides = sorted((float(np.hypot(*(xy[1] - xy[0]))), float(np.hypot(*(xy[2] - xy[1])))), reverse=True)
    rows = [
        ["remove", "the two D solder pads (gold)", "F.Cu + ENIG", *[f"{v:.2f}" for v in unary_union(hv["d"]).bounds],
         "no drift at corner B (the drift contact is at corner A)"],
        ["remove", "GND solder pad at x 315 (gold)", "F.Cu + ENIG", *[f"{v:.2f}" for v in hv["gnd_left"].bounds],
         "the GND pad at x 332.6 stays"],
        ["remove", "copper text 'D'", "F.Cu", *[f"{v:.2f}" for v in HV_LABELS_B["D"]], ""],
        ["remove", "copper text 'GND' next to the removed GND pad", "F.Cu", *[f"{v:.2f}" for v in HV_LABELS_B["GND left"]], ""],
        ["change", "the 2 M + 2 D solder pads -> ONE pad, silkscreen M, net mesh (gold)", "F.Cu + ENIG",
         *[f"{v:.2f}" for v in mn.bounds],
         f"rotated rectangle {sides[0]:.2f} x {sides[1]:.2f} mm; corners {corners}; envelope of the 4 old pads; "
         f"{mn.distance(hv['gnd_right']):.2f} mm from the remaining GND pad; mesh cable here; the 'M' text stays"],
        ["change", f"mesh-contact pad (active area) -> square {MESH_PAD_NEW[1]:.2f} mm rotated 30 deg (as today), net mesh (gold)",
         "F.Cu + ENIG", *[f"{v:.2f}" for v in pn.bounds],
         f"centre ({MESH_PAD_NEW[0][0]:.2f}, {MESH_PAD_NEW[0][1]:.2f}); corners in pcb_corner_B_mesh_pad.csv; "
         f"{pn.area:.1f} mm2 (today 7.6); {d:.2f} mm from the nearest readout pad (today 1.59); inside the frame opening; "
         f"its trace to the M pad stays connected; re-pour the F.Cu GND hatch round it (keep-out as today)"],
        ["mask", "M1, M2: today's window over the mesh pad -> window over the new square", "M1 + M2",
         *[f"{v:.2f}" for v in pn.bounds], f"{WIN_M1:g} mm (M1) / {WIN_M2:g} mm (M2) inside the pad; made by make_masks_2026.py"],
    ]
    with open(os.path.join(fp.DATA, "pcb_corner_B_mesh.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["action", "item", "layer", "x0_mm", "y0_mm", "x1_mm", "y1_mm", "note"])
        w.writerows(rows)
    with open(os.path.join(fp.DATA, "pcb_corner_B_mesh_pad.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["vertex", "x_mm", "y_mm"])
        for i, (x, y) in enumerate(list(pn.exterior.coords)[:-1], 1):
            w.writerow([i, f"{x:.3f}", f"{y:.3f}"])


def square(c, s, th):
    from shapely import affinity
    P = Polygon([(-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2)])
    return affinity.translate(affinity.rotate(P, th), *c)


def square_options(G):
    """Square mesh pads inside the frame opening, CLEAR_RO from every readout pad (2026-10-28: the
    user went back to a square pad). Search over centre (±4 mm round today's) and angle:
    'largest' = biggest side, 'contact' = most area under the mesh."""
    free, others, mesh, pn = G["base"].buffer(1e-3), G["others"], G["mesh"], G["pad_now"]
    ok = lambda P: free.contains(P) and P.distance(others) >= CLEAR_RO
    cx0, cy0 = pn.centroid.coords[0]
    res = []
    for th in np.arange(-60, 31, 5):
        for dx in np.arange(-4, 4.01, 0.25):
            for dy in np.arange(-4, 4.01, 0.25):
                c = (cx0 + dx, cy0 + dy)
                if not ok(square(c, 0.5, th)):
                    continue
                lo, hi = 0.0, 12.0
                for _ in range(16):
                    m = (lo + hi) / 2
                    lo, hi = (m, hi) if ok(square(c, m, th)) else (lo, m)
                lo = math.floor(lo * 100) / 100                          # 0.01 mm grid, stays inside
                res.append((lo, square(c, lo, th).intersection(mesh).area, c, th))
    big = max(res, key=lambda r: (r[0], r[1]))
    con = max(res, key=lambda r: (round(r[1], 2), r[0]))
    xy = np.asarray(pn.exterior.coords)[:4]
    th_now = math.degrees(math.atan2(*(xy[1] - xy[0])[::-1]))
    out = {"today": (float(np.hypot(*(xy[1] - xy[0]))), pn, pn.centroid.coords[0], th_now)}
    for k, (s, u, c, th) in (("contact", con), ("largest", big)):
        out[k] = (s, square(c, s, th), c, th)
    return out


def options_figure(G, O):
    zx = (290, 313, 503, 522)
    fig, axs = plt.subplots(1, 3, figsize=(19, 7.4))
    names = {"today": "TODAY", "contact": "OPTION 1 – most contact with the mesh",
             "largest": "OPTION 2 – largest square"}
    for ax, k in zip(axs, ("today", "contact", "largest")):
        s, P, c, th = O[k]
        fp.board(ax)
        ax.add_collection(PolyCollection([q for q in G["Fq"] if not Polygon(q).buffer(0).equals(G["pad_now"])],
                                         fc=fp.C_FCU, ec="none", alpha=.75, zorder=2))
        ax.add_patch(fp.poly_patch(G["mesh"], fc=fp.C_MESH, ec="0.4", lw=.6, hatch="....", alpha=.45, zorder=3))
        ax.plot(*np.asarray(G["base"].exterior.coords).T, color="0.3", lw=.9, ls=":", zorder=4)
        ax.add_patch(fp.poly_patch(P, fc=C_MESHPAD if k != "today" else "#e2b82a", ec="#1b7a2e", lw=1.6, alpha=.9, zorder=6))
        ax.add_patch(fp.poly_patch(P.intersection(G["mesh"]), fc="none", ec="#11461d", lw=0, hatch="////", zorder=7))
        ax.add_patch(fp.poly_patch(P.buffer(CLEAR_RO).difference(P.buffer(.02)), fc="none", ec="#c0392b", lw=.8,
                                   ls=(0, (2, 2)), zorder=7))
        if k != "today":
            ax.add_patch(fp.poly_patch(G["pad_now"], fc="none", ec="0.15", lw=1.0, ls=":", zorder=8))
        d = P.distance(G["others"])
        u = P.intersection(G["mesh"]).area
        ax.text(zx[0] + .3, zx[2] + .3,
                f"side {s:.2f} mm, rotated {th:.0f}°, centre ({c[0]:.2f}, {c[1]:.2f})\n"
                f"copper {P.area:.1f} mm², under the mesh {u:.1f} mm² (hatched)\n"
                f"{d:.2f} mm to the nearest readout pad",
                fontsize=9, va="bottom", bbox=dict(fc="white", ec=fp.C_EXT_EC, alpha=.92, boxstyle="round,pad=.4"), zorder=9)
        ax.set_xlim(zx[0], zx[1])
        ax.set_ylim(zx[2], zx[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
        ax.set_title(names[k], fontsize=12, weight="bold", loc="left", color="black" if k == "today" else fp.C_EXT_EC)
    axs[0].set_ylabel("y [mm]", fontsize=8)
    fp.callout(axs[0], (304, 508), (305.5, 505.5), "readout pads", color="0.2")
    fp.callout(axs[0], (296.5, 512.5), (291, 519.5), "mesh: stops 1.9 mm\nbefore the frame wall", color="0.3")
    h = [Patch(fc=C_MESHPAD, ec="#1b7a2e", label="mesh-contact pad (square)"),
         Patch(fc="none", ec="#11461d", hatch="////", label="part of the pad under the mesh (the contact)"),
         Patch(fc=fp.C_MESH, ec="0.4", hatch="....", alpha=.45, label="mesh"),
         Line2D([], [], color="#c0392b", ls=(0, (2, 2)), label=f"{CLEAR_RO:g} mm round the pad"),
         Line2D([], [], color="0.15", ls=":", label="today's pad (dotted)"),
         Line2D([], [], color="0.3", ls=":", label="frame inner wall"),
         Patch(fc=fp.C_FCU, alpha=.75, label="F.Cu")]
    fig.legend(handles=h, loc="lower center", ncol=7, fontsize=9, frameon=False)
    fig.suptitle(f"PCB – corner B: square mesh-contact pad, {CLEAR_RO:g} mm from the readout pads, inside the frame "
                 "opening – two options", fontsize=13.5, y=.98)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(fp.FIG, "pcb_corner_B_pad_options.png"), dpi=130)
    plt.close(fig)


def main():
    import sys
    G = geometry()
    if "--options" in sys.argv:                  # the search behind MESH_PAD_NEW (slow, ~1 min)
        O = square_options(G)
        options_figure(G, O)
        for k, (s, P, c, th) in O.items():
            print(f"{k}: side {s:.2f}, angle {th:.0f}, centre ({c[0]:.2f}, {c[1]:.2f}), copper {P.area:.1f}, "
                  f"under mesh {P.intersection(G['mesh']).area:.1f}, to readout {P.distance(G['others']):.2f}")
    d, a_now, a_new = figure(G)
    tables(G, d)
    print(f"mesh pad: {G['pad_new'].area:.1f} mm2, trace connected {G['pad_new'].intersects(G['trace'])}, "
          f"{d:.2f} mm to readout, under mesh {a_now:.1f} -> {a_new:.1f} mm2; "
          f"M pad to GND {G['hv']['m_new'].distance(G['hv']['gnd_right']):.2f} mm")


if __name__ == "__main__":
    import i18n
    i18n.setup()
    main()
    i18n.finish()
