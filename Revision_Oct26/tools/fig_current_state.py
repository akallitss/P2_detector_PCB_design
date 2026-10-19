#!/usr/bin/env python3
"""
Figures of the CURRENT parts (drift frame, PCB, carbon back, carbon drift piece)
overlaid in the common PCB coordinate system (fan apex at the origin, mm).

Inputs (read only):
  ../../Drift_Contact_Oct26/data/cache.pkl     frame slices + PCB Gerbers (from drift_contact_study.py)
  ../../Version_Apr26/FABRICATION_P2/NCDrill/P2_BASKET.drl
  ../data/carbon_registered.json                carbon DXF blocks SE1 (back) / SE2 (drift piece),
                                                SE1 registered on the PCB holes (max residual 0.04 mm)
Writes ../figures/cur_*.png

Memory: the PCB copper is cropped to each zoom window before drawing.
Run with  (ulimit -v 3000000; python3 fig_current_state.py)
"""
import collections
import gc
import json
import math
import os
import pickle
import re

import numpy as np
from rev_geometry import arc_points
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(OUT, ".."))
CACHE = os.path.join(ROOT, "Drift_Contact_Oct26", "data", "cache.pkl")
DRL = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2", "NCDrill", "P2_BASKET.drl")
CARBON = os.path.join(OUT, "data", "carbon_registered.json")
FIG = os.path.join(OUT, "figures")

COL = {"frame": "#1f5fbf", "frame_base": "#7fb2e5", "pcb": "black", "back": "#2e8b57",
       "drift": "#d2691e", "hv": "#e8a33d", "b2": "#c0392b"}

# HV solder-pad groups (F.Cu, measured) and the B2 drift pad / mesh cut (B2_DriftPad_Oct26)
HV_BOX = {"bottom-right": (620.4, 1.0, 635.6, 23.2), "top": (313.1, 532.0, 327.9, 540.5)}
B2_PAD = (590.5, 10.0, 3.0)
B2_CUT = (585.5, 5.0, 595.5, 15.0)


def read_drill():
    D, H, cur = {}, collections.defaultdict(list), None
    for line in open(DRL).read().splitlines():
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            D[int(m.group(1))] = float(m.group(2))
        m = re.match(r"^T(\d+)$", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"X([-\d.]+)Y([-\d.]+)", line)
        if m and cur:
            H[cur].append((float(m.group(1)), float(m.group(2))))
    return D, H


def drift_piece(segs):
    """SE2 sits elsewhere on the cutting sheet: its arcs are centred on (351.61, 637.5)
    and it spans 180-240 deg there. Move the apex to the origin and turn it 180 deg."""
    c = np.array([351.61, 637.5])
    return [(-(np.asarray(s) - c)).tolist() for s in segs]


def load():
    C = pickle.load(open(CACHE, "rb"))
    car = json.load(open(CARBON))
    D, H = read_drill()
    from gerbonara.graphic_primitives import Arc, ArcPoly, Line
    edges = []
    for p in C["gerb"]["Edge_Cuts"]:
        if isinstance(p, Line):
            edges.append([(p.x1, p.y1), (p.x2, p.y2)])
        elif isinstance(p, Arc):
            edges.append(arc_points(p))
    cu = {}
    for layer in ("F_Cu", "F_ENIG_Finition"):
        cu[layer] = [np.array(list(p.outline)) for p in C["gerb"][layer]
                     if isinstance(p, ArcPoly) and len(p.outline) > 2]
    M = {"z7": [np.asarray(s) for s in C["z7.0"]], "z1": [np.asarray(s) for s in C["z1.0"]],
         "sec": np.asarray(C["sec_x350"]), "edges": edges, "cu": cu,
         "back": car["SE1"], "back_holes": car["holes"], "drift": drift_piece(car["SE2"]),
         "D": D, "H": H}
    del C
    gc.collect()
    return M


def crop(polys, win):
    x0, x1, y0, y1 = win
    return [p for p in polys if p[:, 0].max() > x0 and p[:, 0].min() < x1
            and p[:, 1].max() > y0 and p[:, 1].min() < y1]


def base(ax, M, win=None, copper=False, labels=True):
    if copper and win:
        ax.add_collection(PolyCollection(crop(M["cu"]["F_Cu"], win), fc="#f3c98b", ec="none", alpha=.55, zorder=1))
    ax.add_collection(LineCollection(M["edges"], colors=COL["pcb"], lw=.7, zorder=2))
    ax.add_collection(LineCollection(M["z1"], colors=COL["frame_base"], lw=.6, zorder=3))
    ax.add_collection(LineCollection(M["z7"], colors=COL["frame"], lw=1.1, zorder=3))
    ax.add_collection(LineCollection(M["back"], colors=COL["back"], lw=1.2, ls="--", zorder=4))
    ax.add_collection(LineCollection(M["drift"], colors=COL["drift"], lw=1.2, zorder=4))
    D, H = M["D"], M["H"]
    hole_sets = [(3, "#1f5fbf", "PCB Ø3.5 plated (frame Ø3.0)"), (6, "#8e44ad", "PCB Ø3.5 (frame Ø3.5)"),
                 (4, "#c2185b", "PCB Ø2.2 connector holes"), (5, "#6d4c41", "PCB Ø3.2 connector-support holes")]
    for k, c, _ in hole_sets:
        ax.add_collection(PatchCollection([Circle(xy, D[k] / 2) for xy in H[k]], fc="none", ec=c, lw=1.0, zorder=5))
    bh = M["back_holes"]
    ax.add_collection(PatchCollection([Circle(xy, 1.6) for xy in bh["3.2"]], fc="none", ec=COL["back"],
                                      lw=1.6, zorder=6))
    ax.set_aspect("equal")
    ax.grid(lw=.3, alpha=.6)
    if win:
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
    else:
        ax.autoscale()
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    return hole_sets


def legend(ax, hole_sets, extra=()):
    h = [Line2D([], [], color=COL["pcb"], lw=.8, label="PCB outline (Edge.Cuts)"),
         Line2D([], [], color=COL["frame"], lw=1.2, label="drift frame, top (z 4–8)"),
         Line2D([], [], color=COL["frame_base"], lw=.8, label="drift frame, base (z 0–4)"),
         Line2D([], [], color=COL["back"], lw=1.2, ls="--", label="carbon back (strongback)"),
         Line2D([], [], color=COL["drift"], lw=1.2, label="carbon drift piece (5 mm strip)")]
    h += [Line2D([], [], marker="o", ls="none", mfc="none", mec=c, label=l) for _, c, l in hole_sets]
    h += [Line2D([], [], marker="o", ls="none", mfc="none", mec=COL["back"], label="carbon back Ø3.2 holes")]
    h += list(extra)
    ax.legend(handles=h, loc="upper left", fontsize=7.5, framealpha=.92)


def fig_overview(M):
    fig, ax = plt.subplots(figsize=(11, 10))
    hs = base(ax, M)
    ax.set_xlim(20, 670)
    ax.set_ylim(-25, 600)
    for name, (x0, y0, x1, y1) in HV_BOX.items():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=COL["hv"], ec="none", alpha=.6, zorder=7))
    ax.add_patch(Rectangle(B2_CUT[:2], B2_CUT[2] - B2_CUT[0], B2_CUT[3] - B2_CUT[1], fc=COL["b2"], alpha=.6, zorder=7))
    # zoom windows
    for (x0, x1, y0, y1), t in (((570, 660, -20, 55), "A"), ((280, 360, 495, 565), "B"), ((540, 665, 180, 300), "C"),
                                ((300, 420, -22, 22), "D")):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="0.35", lw=.8, ls="-.", zorder=8))
        ax.text(x0 + 1, y1 + 1, t, fontsize=11, weight="bold", color="0.25")
    ax.annotate("extension zone\n(r 615 → 650)", (590, 340), (420, 300), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="0.3"))
    legend(ax, hs, [Patch(fc=COL["hv"], alpha=.6, label="HV solder pads (stay uncovered)"),
                    Patch(fc=COL["b2"], alpha=.6, label="B2 drift pad cut (foam corner)")])
    ax.set_title("Current parts, all in PCB coordinates (apex = origin).  Boxes A–D = zooms", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "cur_0_overview.png"), dpi=110)
    plt.close(fig)


def fig_zoom(M, name, win, title, notes=(), figsize=(10, 9)):
    fig, ax = plt.subplots(figsize=figsize)
    hs = base(ax, M, win, copper=True)
    for (x0, y0, x1, y1) in HV_BOX.values():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec=COL["hv"], lw=2, zorder=7))
    ax.add_patch(Rectangle(B2_CUT[:2], B2_CUT[2] - B2_CUT[0], B2_CUT[3] - B2_CUT[1], fc="none", ec=COL["b2"], lw=2, zorder=7))
    x, y, s = B2_PAD
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc=COL["b2"], alpha=.7, zorder=7))
    for xy, xyt, txt in notes:
        ax.annotate(txt, xy, xyt, fontsize=9, zorder=9,
                    bbox=dict(boxstyle="round,pad=.25", fc="white", ec="0.6", alpha=.95),
                    arrowprops=dict(arrowstyle="->", color="0.2", lw=.9))
    legend(ax, hs, [Patch(fc="#f3c98b", alpha=.6, label="PCB copper (front)"),
                    Patch(fc="none", ec=COL["hv"], lw=2, label="HV solder-pad group"),
                    Patch(fc=COL["b2"], alpha=.7, label="B2 drift pad / mesh cut")])
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"cur_{name}.png"), dpi=110)
    plt.close(fig)
    gc.collect()


def fig_section(M):
    s = M["sec"]                                   # segments in (y, z) at x = 350
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.add_collection(LineCollection(s, colors=COL["frame"], lw=1.3))
    ax.add_patch(Rectangle((-10, -1.6), 11, 1.6, fc=COL["back"], alpha=.25, ec=COL["back"]))
    ax.add_patch(Rectangle((-12, -0.2), 30, 0.2, fc="0.3"))
    ax.add_patch(Rectangle((-2.5, 4.0), 5, 1.0, fc=COL["drift"], alpha=.35, ec=COL["drift"]))
    ax.plot([-3, 18], [4.0, 4.0], color="0.4", lw=.6, ls=":")
    for xy, xyt, t in (((-10, 8), (-11.5, 9.3), "outer edge y = −10"), ((-3, 6), (-2.5, 9.3), "top: 7 mm wide"),
                       ((-1.5, 4), (3.5, 6.2), "mylar ledge z = 4 (3 mm)"), ((-7.5, 4), (-9, 1.2), "Ø screw axis y = −7.5"),
                       ((0, 2), (6, 1.0), "base: 10 mm wide, inner wall y = 0"),
                       ((0, 4.5), (8, 4.6), "carbon drift strip ±2.5 (position to confirm)")):
        ax.annotate(t, xy, xyt, fontsize=8, arrowprops=dict(arrowstyle="->", lw=.7, color="0.3"))
    ax.axvline(-7.5, color="0.5", lw=.6, ls="--")
    ax.text(5, -1.2, "PCB (0.2 mm) on carbon back (thickness schematic)", fontsize=8, color="0.3")
    ax.set_xlim(-13, 20)
    ax.set_ylim(-2.5, 10.5)
    ax.set_aspect("equal")
    ax.grid(lw=.3)
    ax.set_xlabel("y [mm]  (section across the straight side at x = 350)")
    ax.set_ylabel("z [mm]")
    ax.set_title("Drift frame cross-section, straight side (STL slice). Arcs: 15 mm base / 12 mm top", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "cur_E_section_straight_side.png"), dpi=120)
    plt.close(fig)


def main():
    M = load()
    fig_overview(M)
    fig_zoom(M, "A_bottom_right_corner", (570, 660, -20, 55),
             "A – bottom-right corner: HV pads, B2 drift pad, frame / carbon edges",
             [((628, 12), (640, -14), "HV pads GND/M/D/GND\nmust stay accessible"),
              ((590.5, 10), (572, 30), "B2 drift pad 3×3\n(foam / carbon tab here)"),
              ((615, 30), (622, 45), "frame outer edge r = 615")])
    fig_zoom(M, "B_top_corner", (280, 360, 495, 565),
             "B – top corner: second HV pad group",
             [((320, 536), (330, 552), "HV pads (top)")])
    fig_zoom(M, "C_extension_holes", (500, 565, 315, 380),
             "C – extension zone, upper half: PCB Ø3.2 holes sit ~1 mm off the (symmetric) carbon back",
             [((511.3, 372.3), (520, 352), "Ø2.2 pair (connector ends), r = 632.5"),
              ((549.6, 338.8), (528, 323), "PCB Ø3.2 (brown) vs carbon back Ø3.2 (green):\n0.98 mm apart; upper 10 PCB holes\nare rotated +0.09° vs the mirror of the lower 10")])
    fig_zoom(M, "D_straight_side_holes", (300, 420, -22, 22),
             "D – bottom straight side: wall 10 mm, holes on y = −7.5, PCB edge y = −10",
             [((354.8, -7.5), (330, 12), "Ø3.5 (not threaded)"), ((318.3, -7.5), (300.5, 12), "Ø3.0 (threaded)")],
             figsize=(13, 5.5))
    fig_section(M)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
