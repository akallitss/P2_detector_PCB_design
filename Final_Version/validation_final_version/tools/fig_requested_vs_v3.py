#!/usr/bin/env python3
"""
Requested frame (our 2026 revision, P2_Revision_2026/mechanics, rev_geometry.py) vs the frame
delivered (Final_Version/drift_frame/P2_Frame_V3.dxf), both on the final PCB outline.

Writes ../figures/5_requested_vs_v3.png
Run with  (ulimit -v 2500000; python3 fig_requested_vs_v3.py)
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.ops import unary_union

import final_geometry as G
sys.path.insert(0, os.path.join(G.FINAL, "..", "P2_Revision_2026", "mechanics", "tools"))
import rev_geometry as rg                                            # noqa: E402
from fig_validation import C_BOARD, C_BOARD_EC, crop, poly_patch      # noqa: E402

C_V3, C_V3_EC = "#9aa3b0", "#3c4350"
C_REQ = "#e3742b"
C_MISS = "#f4a742"


def main():
    F = G.frame()
    outer, window = G.frame_shapes(F)
    v3 = G.frame_solid(F, outer, window)
    R = rg.build()
    req_outer = unary_union([R["outer_new"], R["ext"]])        # requested contour (HV openings cut)
    missing = req_outer.difference(outer).difference(R["window"])
    holes_req = R["holes"]                                     # connector-support holes in the extension
    pcb = G.board()

    wins = [("whole part", (25, 665, -30, 560)),
            ("outer arc: extension behind the connectors", (560, 660, 40, 140)),
            ("corner A (bottom right)", (575, 660, -20, 40)),
            ("inner arc + bottom side: +1.5 mm outward", (80, 140, -20, 30))]
    fig = plt.figure(figsize=(19, 10.5))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.25, 1])
    axs = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[2, 1])]
    for ax, (t, w) in zip(axs, wins):
        W = None if t == "whole part" else w
        ax.add_patch(poly_patch(crop(pcb, W), fc=C_BOARD, ec=C_BOARD_EC, lw=1, zorder=1))
        ax.add_patch(poly_patch(crop(v3, W), fc=C_V3, ec=C_V3_EC, lw=.7, alpha=.85, zorder=3))
        ax.add_patch(poly_patch(crop(missing, W), fc=C_MISS, ec=C_REQ, lw=.8, alpha=.8, hatch="///", zorder=4))
        ax.plot(*np.asarray(req_outer.exterior.coords).T, color=C_REQ, lw=1.4, ls="--", zorder=5)
        for x, y, d in holes_req:
            ax.plot(x, y, "o", ms=3 if t == "whole part" else 6, mfc="white", mec="#5a2d00", mew=1, zorder=6)
        for x, y, d in F["holes"]:
            if t != "whole part":
                ax.add_patch(plt.Circle((x, y), d / 2, fc="white", ec=C_V3_EC, lw=1, zorder=6))
        ax.set_xlim(w[0], w[1])
        ax.set_ylim(w[2], w[3])
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=11, loc="left")
        if t == "whole part":
            ax.axis("off")
        else:
            ax.tick_params(labelsize=7)
    xy = np.asarray(outer.exterior.coords)
    txt = ("requested (revision)        frame V3 (delivered)\n"
           f"extension to R650           ends at R{np.hypot(*xy.T).max():.0f}   MISSING\n"
           f"{len(holes_req)} connector-support holes    none              MISSING\n"
           "HV openings (corners A, B)  none (no extension, so not needed)\n"
           f"straight sides edge 11.5    {-xy[:, 1].min():.1f} mm            +0.5 more\n"
           f"inner arc edge r 93.5       r {np.hypot(*xy.T).min():.1f} (= PCB edge)  MISSING\n"
           f"missing material: {missing.area / 100:.0f} cm² (top view)")
    axs[0].text(140, 160, txt, fontsize=10, family="monospace", zorder=10,
                bbox=dict(fc="white", ec="0.5", boxstyle="round,pad=.6"))
    fig.legend(handles=[Patch(fc=C_BOARD, ec=C_BOARD_EC, label="final PCB"),
                        Patch(fc=C_V3, ec=C_V3_EC, alpha=.85, label="frame V3 (delivered)"),
                        Patch(fc=C_MISS, ec=C_REQ, hatch="///", alpha=.8, label="requested but not in V3"),
                        Line2D([], [], color=C_REQ, ls="--", lw=1.4, label="requested outer contour (HV openings cut out)"),
                        Line2D([], [], marker="o", ls="none", mfc="white", mec="#5a2d00", label="requested connector-support holes")],
               loc="lower center", ncol=5, fontsize=10, frameon=False)
    fig.suptitle("Frame: what the revision asked for vs what V3 contains (top view, on the final PCB)",
                 fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .96))
    fig.savefig(os.path.join(G.FIG, "5_requested_vs_v3.png"), dpi=120)
    plt.close(fig)
    print(txt)


if __name__ == "__main__":
    main()
