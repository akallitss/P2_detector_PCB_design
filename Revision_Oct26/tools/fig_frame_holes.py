#!/usr/bin/env python3
"""
Drift frame screw holes: NOW (two diameters, irregular pitch) vs NEW (one diameter Ø3.5,
equal pitch, both straight sides mirror images).

Writes ../figures/frame_holes_overview.png, ../figures/frame_holes_unrolled.png
and    ../data/frame_holes_new.csv
Run with  (ulimit -v 3000000; python3 fig_frame_holes.py)
"""
import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import rev_geometry as rg
from fig_frame_corners import C_EXT, C_EXT_EC, C_FRAME, C_FRAME_EC, C_OPEN, C_WIDE, pcb_edges, poly_patch
from matplotlib.collections import LineCollection
from shapely.ops import unary_union

FIG = os.path.join(rg.OUT, "figures")
C_THR, C_CLR, C_NEW = "#1f5fbf", "#8e44ad", "black"
EDGES = ["bottom side", "outer arc", "top side", "inner arc"]


def frame_poly(G):
    f = G["outer"].difference(G["window"])
    return f


def overview(G, old, new, pitch, edges):
    """Master plan of the part: NOW (frame + PCB outline) vs NEW (whole new part)."""
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 8.6))
    board = rg.pcb_outline(rg.SIDE_NOW, rg.R_IN_EDGE_NOW).buffer(4)      # drop the production-panel border
    edges = [e for e in edges if all(board.contains(rg.Point(*q)) for q in e)]
    a0.add_collection(LineCollection(edges, colors="0.35", lw=.6))
    a0.annotate("today: PCB not supported\nbehind the connectors", (628, 230), (470, 120), fontsize=9, color="0.3",
                arrowprops=dict(arrowstyle="->", color="0.3"))
    a1.plot(*np.asarray(rg.pcb_outline().exterior.coords).T, color="0.35", lw=.8, ls="--")
    a1.add_patch(poly_patch(G["ext"], fc=C_EXT, ec=C_EXT_EC, lw=.5, alpha=.85))
    opn = G["ext_full"].intersection(unary_union([G["op"]["A"], G["op"]["B"]]))
    a1.add_patch(poly_patch(opn, fc="none", ec=C_OPEN, lw=1.2, ls="--", hatch="////"))
    for x, y, d in G["holes"]:
        a1.plot(x, y, "o", ms=3.2, mfc="white", mec="#5a2d00", mew=.9)
    a1.add_patch(poly_patch(G["band"], fc=C_WIDE, ec=C_EXT_EC, lw=.5))
    for ax in (a0, a1):
        ax.add_patch(poly_patch(frame_poly(G), fc=C_FRAME, ec=C_FRAME_EC, lw=.5))
        ax.set_xlim(20, 665)
        ax.set_ylim(-30, 560)
        ax.set_aspect("equal")
        ax.axis("off")
        a = np.radians(30)
        ax.plot([0, 640 * np.cos(a)], [0, 640 * np.sin(a)], color="0.6", lw=.8, ls="-.")
        ax.text(560 * np.cos(a) - 30, 560 * np.sin(a) + 8, "symmetry axis (30°)", rotation=30, fontsize=8, color="0.45")
    for x, y, d in old:
        if d < 3.2:
            a0.plot(x, y, "o", ms=7, mfc=C_THR, mec=C_THR)
        else:
            a0.plot(x, y, "o", ms=7, mfc="white", mec=C_CLR, mew=2)
    for no, x, y, e in new:
        a1.plot(x, y, "o", ms=7, mfc="white", mec=C_NEW, mew=1.6)
        # number outside the frame
        r = np.hypot(x, y)
        if e == "bottom side" or (e == "corner" and y < 0):
            t = (x, y - 13)
        elif e == "top side" or (e == "corner" and x < 300 and y > 80):
            t = (x - 12 * np.sin(np.radians(60)) - 4, y + 12 * np.cos(np.radians(60)))
        elif r > 300:
            t = (x * (r - 17) / r, y * (r - 17) / r)      # inside the arc: the extension holes are outside
        else:
            t = (x * (r - 16) / r, y * (r - 16) / r)
        a1.text(*t, str(no), fontsize=7, ha="center", va="center", color="0.15")
    br = rg.CORNERS["bottom-right"]
    a1.plot(*br, "o", ms=12, mfc="none", mec=C_EXT_EC, mew=2)
    a1.annotate(f"corner hole moved {rg.CORNERS_NOW['bottom-right'][0] - br[0]:.1f} mm inward\n"
                "= mirror of the top corner hole", br, (430, 45), fontsize=9, color=C_EXT_EC,
                arrowprops=dict(arrowstyle="->", color=C_EXT_EC))
    n3 = sum(1 for h in old if h[2] < 3.2)
    a0.set_title("NOW", fontsize=14, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=14, weight="bold", loc="left", color="#b8650a")
    a0.text(215, 265, f"{len(old)} holes, 2 kinds:\n"
            f"  • {n3} × Ø3.0 (threaded)\n  • {len(old) - n3} × Ø3.5 (not threaded)\n"
            "spacing irregular: 18 – 73 mm", fontsize=10, va="top",
            bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.5"))
    a1.text(185, 265, f"{len(new)} holes, all Ø{rg.SCREW_D:g} (not threaded)\n"
            f"equal spacing on each edge:\n"
            f"  • straight sides: {pitch['straight sides']:.1f} mm\n"
            f"  • outer arc: {pitch['outer arc']:.1f} mm\n"
            f"  • inner arc: {pitch['inner arc']:.1f} mm\n"
            "the whole pattern is mirror-symmetric (30° axis)\n"
            "frame and PCB outline unchanged (flush, no widening)\n"
            f"hole lines: straight sides y = {rg.Y_SIDE:g}, inner arc r = {rg.R_IN:g}\n"
            f"  (unchanged, set by the O-ring); outer arc r = {rg.R_OUT_NOW:g} → {rg.R_OUT:g}\n"
            "  (nut + washer must sit on the cut-back carbon back)",
            fontsize=10, va="top", bbox=dict(fc="white", ec="#b8650a", boxstyle="round,pad=.5"))
    h = [Line2D([], [], marker="o", ls="none", ms=7, mfc=C_THR, mec=C_THR, label="Ø3.0 threaded (removed)"),
         Line2D([], [], marker="o", ls="none", ms=7, mfc="white", mec=C_CLR, mew=2, label="Ø3.5 not threaded (today)"),
         Line2D([], [], marker="o", ls="none", ms=7, mfc="white", mec=C_NEW, mew=1.6, label="NEW Ø3.5 not threaded (numbered, see table)"),
         Patch(fc=C_FRAME, ec=C_FRAME_EC, label="drift frame (top face)"),
         Patch(fc=C_EXT, ec=C_EXT_EC, alpha=.85, label="NEW: extension to the PCB edge (8 mm high)"),
         Patch(fc="none", ec=C_OPEN, ls="--", hatch="////", label="NEW: HV openings (see corners A, B)"),
         Line2D([], [], marker="o", ls="none", ms=4, mfc="white", mec="#5a2d00", label=f"NEW: {len(G['holes'])} connector-support holes (PCB pattern, table)"),
         Line2D([], [], color="0.35", lw=.8, label="PCB outline (NOW: solid, NEW: dashed)")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("Drift frame – whole part: extension, HV openings, screw holes; outline flush with the unchanged PCB  (hole symbols enlarged)",
                 fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.075, 1, 0.95))
    fig.savefig(os.path.join(FIG, "frame_overview.png"), dpi=130)
    plt.close(fig)


def unrolled(old, new, pitch):
    """Each edge drawn as a straight line: old holes above, new below."""
    starts = {"bottom side": "inner-bottom corner", "outer arc": "bottom-right corner",
              "top side": "inner-top corner", "inner arc": "inner-bottom corner"}
    ends = {"bottom side": "bottom-right corner", "outer arc": "top corner",
            "top side": "top corner", "inner arc": "inner-top corner"}
    pk = {"bottom side": "straight sides", "top side": "straight sides", "outer arc": "outer arc", "inner arc": "inner arc"}
    fig, axs = plt.subplots(4, 1, figsize=(15, 10.5))
    for ax, e in zip(axs, EDGES):
        o = sorted((rg.s_on(e, (x, y), now=True), d) for x, y, d in old if e in rg.edge_of((x, y)))
        n = sorted(rg.s_on(e, (x, y)) for _, x, y, ee in new if ee == e or (ee == "corner" and e in rg.edge_of((x, y))))
        L = max(n[-1], o[-1][0])
        ax.plot([0, L], [1, 1], color="0.75", lw=6, solid_capstyle="butt", zorder=0)
        ax.plot([0, L], [-1, -1], color="#f6d3a3", lw=6, solid_capstyle="butt", zorder=0)
        for s, d in o:
            if d < 3.2:
                ax.plot(s, 1, "o", ms=9, mfc=C_THR, mec=C_THR, zorder=3)
            else:
                ax.plot(s, 1, "o", ms=9, mfc="white", mec=C_CLR, mew=2, zorder=3)
        for (s0, _), (s1, _) in zip(o[:-1], o[1:]):
            ax.text((s0 + s1) / 2, 1.55, f"{s1 - s0:.0f}", ha="center", fontsize=7.5, color="0.35")
        for s in n:
            ax.plot(s, -1, "o", ms=9, mfc="white", mec=C_NEW, mew=1.6, zorder=3)
        for s0, s1 in zip(n[:-1], n[1:]):
            ax.text((s0 + s1) / 2, -1.75, f"{s1 - s0:.1f}", ha="center", fontsize=7.5, color="#b8650a")
        ax.text(-0.012 * L, 1, "NOW", ha="right", va="center", fontsize=10, weight="bold")
        ax.text(-0.012 * L, -1, "NEW", ha="right", va="center", fontsize=10, weight="bold", color="#b8650a")
        ax.set_xlim(-0.07 * L, 1.03 * L)
        ax.set_ylim(-3.0, 2.2)
        ax.set_yticks([])
        for sp in ("left", "right", "top"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=7)
        ax.set_title(f"{e}  —  from the {starts[e]} to the {ends[e]}   (new pitch {pitch[pk[e]]:.1f} mm)",
                     fontsize=10, loc="left")
        ax.set_xlabel("position along the edge [mm]", fontsize=8)
        if e == "bottom side":
            ax.annotate("corner hole moved 5 mm inward (mirror of the top corner hole,\nwhich must stay clear of the gas inlet): both sides now 506 mm",
                        (n[-1], -1.3), (0.40 * L, -2.55), fontsize=8, color="#b8650a", va="center",
                        arrowprops=dict(arrowstyle="->", color="#b8650a", lw=.8))
    h = [Line2D([], [], marker="o", ls="none", ms=8, mfc=C_THR, mec=C_THR, label="Ø3.0 threaded (removed)"),
         Line2D([], [], marker="o", ls="none", ms=8, mfc="white", mec=C_CLR, mew=2, label="Ø3.5 not threaded (today)"),
         Line2D([], [], marker="o", ls="none", ms=8, mfc="white", mec=C_NEW, mew=1.6, label="NEW Ø3.5 not threaded")]
    fig.legend(handles=h, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Drift frame – screw holes edge by edge (each edge unrolled into a straight line; numbers = spacing in mm)",
                 fontsize=13, y=.99)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(os.path.join(FIG, "frame_holes_unrolled.png"), dpi=130)
    plt.close(fig)


def write_ext_csv(G):
    with open(os.path.join(rg.OUT, "data", "extension_holes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x_mm", "y_mm", "diameter_mm", "note"])
        for x, y, d in sorted(G["holes"], key=lambda h: rg.deg(h[:2])):
            w.writerow([f"{x:.2f}", f"{y:.2f}", d, "connector-support hole, same position and Ø as the PCB"])


def write_csv(new):
    with open(os.path.join(rg.OUT, "data", "frame_holes_new.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["no", "x_mm", "y_mm", "diameter_mm", "edge", "note"])
        for no, x, y, e in new:
            if e != "corner":
                note = "new position"
            elif (round(x, 2), round(y, 2)) == rg.CORNERS["bottom-right"]:
                note = "corner hole moved 5.0 mm inward (mirror of the top corner hole)"
            else:
                note = "kept (existing corner hole)"
            w.writerow([no, f"{x:.2f}", f"{y:.2f}", rg.SCREW_D, e, note])


def main():
    G = rg.build()
    old = rg.old_frame_holes(G["H"])
    new, pitch = rg.new_frame_holes()
    overview(G, old, new, pitch, pcb_edges())
    unrolled(old, new, pitch)
    write_csv(new)
    write_ext_csv(G)
    print("written frame_overview.png, frame_holes_unrolled.png, data/frame_holes_new.csv, data/extension_holes.csv")


if __name__ == "__main__":
    main()
