#!/usr/bin/env python3
"""
Corner B (top): the only mesh contact of the 2026 board (decided 2026-10-28).

HV solder pads (outside the frame), along x: GND (x 315), two M pads, two D pads, GND (x 332.6).
  * the two D pads and the GND pad at x 315 go, with the copper texts "D" and that "GND";
  * the 2 M + 2 D pads merge into ONE pad, label M (the envelope of the four), for the mesh cable.
Mesh-contact pad (active area, at the corner apex, today 3.9 x 3.9 mm, only ~8 mm2 under the mesh):
  * grown into the free band along both frame walls, keeping 1.5 mm from every readout pad (as today),
    along the two sides of the corner readout pad /Sector9/Sig128; polygon pad (custom shape);
  * M1 / M2 windows follow the new pad (make_masks_2026.py).

Writes ../figures/pcb_corner_B.png, ../data/pcb_corner_B_mesh.csv, ../data/pcb_corner_B_mesh_pad.csv
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
ARM = 5.0                            # band kept within this distance of the corner readout pad (+ clearance)
OPEN_R = 1.0                         # thin slivers (< 2 mm) dropped
SIMPLIFY = 0.05                      # polygon simplification for the table [mm]
WIN_M1, WIN_M2 = 0.3, 0.45           # mask windows: the pad part under the mesh, shrunk by this
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
    R = base.difference(others.buffer(CLEAR_RO + SIMPLIFY)).intersection(corner_ro.buffer(CLEAR_RO + ARM))
    O = R.buffer(-OPEN_R).buffer(OPEN_R)
    pad_new = unary_union([g for g in getattr(O, "geoms", [O]) if g.intersects(pad_now)] + [pad_now.intersection(base)])
    pad_new = pad_new.simplify(SIMPLIFY).buffer(0)
    return dict(Fq=Fq, Bq=Bq, F=F, pad_now=pad_now, trace=unary_union(trace), hv=hv, others=others, base=base,
                mesh=mesh, corner_ro=corner_ro, pad_new=pad_new)


def windows(G):
    """New M1 / M2 windows over the mesh pad: its part under the mesh, shrunk a little."""
    under = G["pad_new"].intersection(G["mesh"].buffer(0.3))
    return under.buffer(-WIN_M1).buffer(0), under.buffer(-WIN_M2).buffer(0)


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
    fp.callout(a0, pnow.centroid.coords[0], (286, 529), "mesh-contact pad 3.9 × 3.9 mm\n(only ~8 mm² under the mesh)", color="#1f5fbf")
    fp.callout(a0, (304, 505), (306, 497), "readout pads (/Sector9/...)")
    fp.callout(a0, (323.9, 536.4), (318, 543.5), "HV pads GND / M M / D D / GND", color="0.2")
    gl, gr = hv["gnd_left"].centroid, hv["gnd_right"].centroid
    fp.callout(a1, (gl.x, gl.y), (287, 541), "REMOVE this GND pad\n(+ its GND text)", color=fp.C_OPEN)
    fp.callout(a1, (326.7, 534.4), (321, 520), "M M + D D (dashed) merged into ONE\nM pad (mesh cable); D text removed", color="#1b7a2e")
    fp.callout(a1, (gr.x, gr.y), (328, 544), "GND pad stays", color="0.2")
    fp.callout(a1, (305, 516.6), (305, 506), "NEW mesh-contact pad: band along\nboth walls (zoom →)", color="#1b7a2e")
    # zoom on the mesh pad with clearances and mask windows
    zx = (286.5, 318.5, 495.5, 521.5)
    a2.set_xlim(zx[0], zx[1])
    a2.set_ylim(zx[2], zx[3])
    a2.add_patch(fp.poly_patch(w1, fc="none", ec="#1f5fbf", lw=1.0, ls="--", zorder=8))
    a2.add_patch(fp.poly_patch(pnow, fc="none", ec="0.2", lw=1.0, ls=":", zorder=8))
    ro = G["others"].intersection(box(*[zx[0], zx[2], zx[1], zx[3]]))
    a2.add_patch(fp.poly_patch(pn.buffer(CLEAR_RO).difference(pn.buffer(0.05)), fc="none", ec="#c0392b", lw=.7,
                               ls=(0, (2, 2)), zorder=7))
    d = pn.distance(G["others"])
    fp.callout(a2, (300.0, 512.3), (305.5, 518.6), f"{d:.2f} mm to the nearest readout pad\n(red dashed: {CLEAR_RO:g} mm)", color="#c0392b")
    fp.callout(a2, (pnow.centroid.x, pnow.centroid.y), (288, 519.5), "today's pad (dotted)", color="0.2")
    under_now, under_new = pnow.intersection(G["mesh"]).area, pn.intersection(G["mesh"]).area
    a2.text(zx[0] + .4, zx[2] + .4,
            f"NEW mesh-contact pad (polygon, table pcb_corner_B_mesh_pad.csv)\n"
            f"area {pn.area:.0f} mm², under the mesh {under_new:.0f} mm² (today {under_now:.0f} mm²)\n"
            f"M1 window (blue dashed): the part under the mesh, {WIN_M1:g} mm inside;\nM2 the same, {WIN_M2:g} mm inside. "
            "The F.Cu GND hatch near the wall is re-poured\nround the pad (keep-out, as round today's pad)",
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
        ["change", "mesh-contact pad (active area) -> polygon pad, net mesh (gold)", "F.Cu + ENIG",
         *[f"{v:.2f}" for v in pn.bounds],
         f"vertices in pcb_corner_B_mesh_pad.csv; area {pn.area:.1f} mm2; {d:.2f} mm from the nearest readout pad "
         f"(today 1.50); its trace to the M pad is unchanged; re-pour the F.Cu GND hatch round it (keep-out as today)"],
        ["mask", "M1, M2: today's window over the mesh pad -> windows over the new pad (part under the mesh)", "M1 + M2",
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


def main():
    G = geometry()
    d, a_now, a_new = figure(G)
    tables(G, d)
    print(f"mesh pad: {G['pad_new'].area:.1f} mm2, {len(G['pad_new'].exterior.coords) - 1} vertices, "
          f"{d:.2f} mm to readout, under mesh {a_now:.1f} -> {a_new:.1f} mm2; "
          f"M pad to GND {G['hv']['m_new'].distance(G['hv']['gnd_right']):.2f} mm")


if __name__ == "__main__":
    import i18n
    i18n.setup()
    main()
    i18n.finish()
