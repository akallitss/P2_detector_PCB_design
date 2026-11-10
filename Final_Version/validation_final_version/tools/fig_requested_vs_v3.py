#!/usr/bin/env python3
"""
Requested frame (our 2026 revision, P2_Revision_2026/mechanics, rev_geometry.py) vs the frame
delivered (Final_Version/drift_frame/P2_Frame_V3.dxf), both on the final PCB outline.

Whole part + 4 zooms with dimensions MEASURED in the files along the normal to each edge, from
the window edge: PCB edge, V3 edge, edge asked, and the wall left past an M3 head (Ø5.5).

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
from matplotlib.patches import Circle, Patch
from shapely.geometry import LineString
from shapely.ops import unary_union

import final_geometry as G
sys.path.insert(0, os.path.join(G.FINAL, "..", "P2_Revision_2026", "mechanics", "tools"))
import rev_geometry as rg                                            # noqa: E402
from fig_validation import C_BOARD, C_BOARD_EC, crop, poly_patch      # noqa: E402

C_V3, C_V3_EC = "#9aa3b0", "#3c4350"
C_REQ = "#e3742b"
C_MISS = "#f4a742"
C_DIM = "#1a3d8f"
HEAD_D = 5.5


def cut(geom, p0, n, L=80):
    """Signed distance along p0 + t n to the nearest crossing of geom's boundary."""
    x = LineString([tuple(p0 - L * n), tuple(p0 + L * n)]).intersection(geom.boundary)
    pts = [x] if x.geom_type == "Point" else list(getattr(x, "geoms", []))
    return min((float((np.array(q.coords[0]) - p0) @ n) for q in pts), key=abs)


def dim_n(ax, p0, n, d0, d1, text, t_off, color=C_DIM, fs=9, ha="left"):
    """Dimension arrow from p0 + d0 n to p0 + d1 n, shifted by t_off along the edge."""
    t = np.array([-n[1], n[0]])
    a, b = p0 + d0 * n + t_off * t, p0 + d1 * n + t_off * t
    ax.annotate("", tuple(a), tuple(b), arrowprops=dict(arrowstyle="<->", color=color, lw=1.2, shrinkA=0, shrinkB=0),
                zorder=12)
    m = (a + b) / 2 + (0.8 if ha == "left" else -0.8) * t
    ax.text(*m, text, color=color, fontsize=fs, ha=ha, va="center", zorder=13,
            bbox=dict(fc="white", ec="none", alpha=.85, pad=.3))


def side_dims(ax, q, n, M, hole_d, step=7.0):
    """q on the window edge, on the normal through a real screw hole.  Arrows window -> PCB edge,
    -> V3 edge, -> asked edge beside the hole; head room (head edge -> V3 edge) at the hole."""
    dim_n(ax, q, n, 0, M["pcb"], f"PCB {M['pcb']:.1f}", step, color=C_BOARD_EC)
    dim_n(ax, q, n, 0, M["v3"], f"V3 {M['v3']:.1f}", 2 * step)
    dim_n(ax, q, n, 0, M["req"], f"asked {M['req']:.1f}", 3 * step, color=C_REQ)
    head = hole_d + HEAD_D / 2
    hc = q + hole_d * n
    ax.add_patch(Circle(tuple(hc), HEAD_D / 2, fc="none", ec="black", lw=1.2, ls="--", zorder=8))
    ax.annotate("", tuple(q + head * n), tuple(q + M["v3"] * n),
                arrowprops=dict(arrowstyle="<->", color=C_DIM, lw=1.1, shrinkA=0, shrinkB=0), zorder=12)
    ax.text(0.02, 0.03, f"wall past the M3 head (dashed): V3 {M['v3'] - head:.2f} mm, asked {M['req'] - head:.2f} mm",
            color=C_DIM, fontsize=9, ha="left", va="bottom", zorder=13, transform=ax.transAxes,
            bbox=dict(fc="white", ec="none", alpha=.85, pad=.3))


def measure(window, outer, pcb, req, p0, n):
    w0 = cut(window, p0, n)
    q = p0 + w0 * n                                   # point on the window edge
    return q, dict(pcb=cut(pcb, q + 5 * n, n) + 5, v3=cut(outer, q + 5 * n, n) + 5, req=cut(req, q + 5 * n, n) + 5)


def main():
    F = G.frame()
    outer, window = G.frame_shapes(F)
    v3 = G.frame_solid(F, outer, window)
    R = rg.build()
    req_outer = unary_union([R["outer_new"], R["ext"]])        # requested contour (HV openings cut)
    missing = req_outer.difference(outer).difference(R["window"])
    holes_req = R["holes"]                                     # connector-support holes in the extension
    pcb = G.board()
    req_line = rg.frame_outline()

    a30 = np.array([math.cos(math.radians(30)), math.sin(math.radians(30))])
    a8 = np.array([math.cos(math.radians(9.5)), math.sin(math.radians(9.5))])
    # (title, window, (p0 inside the window, outward normal), screw-line distance from the window edge)
    hb = min(F["holes"], key=lambda h: abs(h[0] - 327.6) + abs(h[1] + 7.5))          # a bottom-side V3 hole
    hi = min(F["holes"], key=lambda h: abs(math.degrees(math.atan2(h[1], h[0])) - 41.2) + abs(math.hypot(h[0], h[1]) - 99.5))
    ai = math.atan2(hi[1], hi[0])
    ui = np.array([math.cos(ai), math.sin(ai)])
    zc = 103 * np.array([math.cos(ai - math.radians(6)), math.sin(ai - math.radians(6))])  # hole + dims clockwise of it
    zooms = [("outer arc: extension behind the connectors (missing)", (570, 662, 52, 118), (585 * a8, a8), 10.5),
             ("corner A (bottom right)", (575, 660, -22, 38), None, None),
             ("bottom side (top side the same): V3 wider than asked", (hb[0] - 8, hb[0] + 34, -19, 3),
              (np.array([hb[0], 5.0]), np.array([0.0, -1.0])), 7.5),
             ("inner arc: V3 narrower than asked (no overhang)",
              (zc[0] - 21, zc[0] + 21, zc[1] - 21, zc[1] + 21),
              (120 * ui, -ui), 10.5)]
    fig = plt.figure(figsize=(20, 11))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.35, 1, 1])
    axs = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2]),
           fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[1, 2])]
    panels = [("whole part", (25, 665, -30, 560), None, None)] + zooms
    for ax, (t, w, norm, hole_d) in zip(axs, panels):
        W = None if t == "whole part" else w
        ax.add_patch(poly_patch(crop(pcb, W), fc=C_BOARD, ec=C_BOARD_EC, lw=1, zorder=1))
        ax.add_patch(poly_patch(crop(v3, W), fc=C_V3, ec=C_V3_EC, lw=.7, alpha=.85, zorder=3))
        ax.add_patch(poly_patch(crop(missing, W), fc=C_MISS, ec=C_REQ, lw=.8, alpha=.8, hatch="///", zorder=4))
        ax.plot(*np.asarray(req_outer.exterior.coords).T, color=C_REQ, lw=1.4, ls="--", zorder=5)
        for x, y, d in holes_req:
            ax.plot(x, y, "o", ms=3 if t == "whole part" else 6, mfc="white", mec="#5a2d00", mew=1, zorder=6)
        if t != "whole part":
            for x, y, d in F["holes"]:
                ax.add_patch(Circle((x, y), d / 2, fc="white", ec=C_V3_EC, lw=1, zorder=6))
        if norm is not None:
            q, M = measure(window, outer, pcb, req_line, *norm)
            if t.startswith("outer arc"):
                n = norm[1]
                dim_n(ax, q, n, 0, M["v3"], f"V3 {M['v3']:.1f}\n(ends at R615)", -4)
                dim_n(ax, q, n, M["v3"], M["req"], f"missing {M['req'] - M['v3']:.1f}\n(asked: out to\nthe PCB edge R650)",
                      -4, color=C_REQ)
            else:
                side_dims(ax, q, norm[1], M, hole_d, step=7.0)
                head = hole_d + HEAD_D / 2
                print(t, {k: round(v, 2) for k, v in M.items()}, "past head V3 %.2f asked %.2f" % (M["v3"] - head, M["req"] - head))
        ax.set_xlim(w[0], w[1])
        ax.set_ylim(w[2], w[3])
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=10.5, loc="left")
        if t == "whole part":
            ax.axis("off")
        else:
            ax.tick_params(labelsize=7)
    fig.legend(handles=[Patch(fc=C_BOARD, ec=C_BOARD_EC, label="final PCB"),
                        Patch(fc=C_V3, ec=C_V3_EC, alpha=.85, label="frame V3 (delivered)"),
                        Patch(fc=C_MISS, ec=C_REQ, hatch="///", alpha=.8, label="asked in the revision, not in V3"),
                        Line2D([], [], color=C_REQ, ls="--", lw=1.4, label="outer contour asked (HV openings cut out)"),
                        Line2D([], [], marker="o", ls="none", mfc="white", mec="#5a2d00", label="connector-support holes asked"),
                        Line2D([], [], color="black", ls="--", lw=1.1, label=f"M3 head Ø{HEAD_D} on the screw line")],
               loc="lower center", ncol=6, fontsize=9.5, frameon=False)
    fig.suptitle("Frame: what the revision asked for vs frame V3, on the final PCB  "
                 "(top view; dimensions in mm, measured from the window edge)", fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .96))
    fig.savefig(os.path.join(G.FIG, "5_requested_vs_v3.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
