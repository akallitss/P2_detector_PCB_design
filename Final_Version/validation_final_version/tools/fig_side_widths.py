#!/usr/bin/env python3
"""
Frame wall width on the straight sides and the inner arc: frame V3 vs what the revision asked
(+1.5 mm outward past the PCB edge), with the room around the screws (M3 head Ø5.5, nut AF 5.5).

Every distance is MEASURED along the normal to the edge, from the window edge (= inner wall of
the frame) outward, in the final files (frame V3 DXF, final PCB Edge_Cuts).  The requested edge
comes from P2_Revision_2026/mechanics/tools/rev_geometry.py (frame_outline()).

Each edge is drawn unrolled: edge horizontal, window at the top, outside at the bottom, true scale.
Writes ../figures/6_side_widths.png
Run with  (ulimit -v 2500000; python3 fig_side_widths.py)
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
from shapely.geometry import LineString

import final_geometry as G
sys.path.insert(0, os.path.join(G.FINAL, "..", "P2_Revision_2026", "mechanics", "tools"))
import rev_geometry as rg                                            # noqa: E402

C_BOARD, C_BOARD_EC = "#e8f3e4", "#2e7d32"
C_V3, C_V3_EC = "#9aa3b0", "#3c4350"
C_REQ = "#e3742b"
C_DIM = "#1a3d8f"
HEAD_D = 5.5            # M3 socket head (ISO 4762)
NUT_AF = 5.5            # M3 nut across flats (ISO 4032); across corners = AF / cos 30


def cut(geom, p0, n, L=80):
    """Distance along p0 + t n where the line crosses geom's boundary (first crossing, t > -L)."""
    x = LineString([tuple(p0 - L * n), tuple(p0 + L * n)]).intersection(geom.boundary)
    pts = [x] if x.geom_type == "Point" else list(getattr(x, "geoms", []))
    return min((float((np.array(q.coords[0]) - p0) @ n) for q in pts), key=abs)


def measure():
    F = G.frame()
    outer, window = G.frame_shapes(F)
    pcb, req = G.board(), rg.frame_outline()
    u60 = np.array([math.cos(math.radians(60)), math.sin(math.radians(60))])
    n60 = np.array([-math.sin(math.radians(60)), math.cos(math.radians(60))])
    cases = {
        "bottom side": (np.array([300.0, 0.0]), np.array([0.0, -1.0]), "y = −7.5"),
        "top side": (300.0 * u60, n60, "7.5 mm from the 60° line"),
        "inner arc": (110 * np.array([math.cos(math.radians(30)), math.sin(math.radians(30))]),
                      -np.array([math.cos(math.radians(30)), math.sin(math.radians(30))]), "r = 99.5"),
    }
    out = {}
    for e, (p0, n, hole_txt) in cases.items():
        w0 = cut(window, p0 - 5 * n, n) - 5            # window edge (should be at 0)
        m = dict(window=0.0, pcb=cut(pcb, p0 + 5 * n, n) + 5 - w0, v3=cut(outer, p0 + 5 * n, n) + 5 - w0,
                 req=cut(req, p0 + 5 * n, n) + 5 - w0, hole_txt=hole_txt)
        m["hole"] = 7.5 if e != "inner arc" else 110.0 - 99.5
        out[e] = m
    return out


def hexagon(cx, cy, af):
    r = af / 2 / math.cos(math.radians(30))
    return [(cx + r * math.cos(math.radians(30 + 60 * k)), cy + r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


def dim(ax, x, y0, y1, text, color=C_DIM, fs=10):
    ax.annotate("", (x, -y0), (x, -y1), arrowprops=dict(arrowstyle="<->", color=color, lw=1.3, shrinkA=0, shrinkB=0))
    ax.text(x + 0.5, -(y0 + y1) / 2, text, color=color, fontsize=fs, va="center", ha="left",
            bbox=dict(fc="white", ec="none", alpha=.85, pad=.4), zorder=12)


def panel(ax, e, m, L=60):
    """Unrolled view: s along the edge (0..L), n downward = outward from the window edge."""
    ax.add_patch(Rectangle((0, -m["pcb"]), L, m["pcb"] + 3, fc=C_BOARD, ec="none", zorder=1))
    ax.plot([0, L], [-m["pcb"]] * 2, color=C_BOARD_EC, lw=1.8, zorder=6)
    ax.add_patch(Rectangle((0, -m["v3"]), L, m["v3"], fc=C_V3, ec=C_V3_EC, lw=1, alpha=.8, zorder=3))
    ax.plot([-2, L + 2], [-m["req"]] * 2, color=C_REQ, lw=2.2, ls="--", zorder=7)
    cx, cy = 12, -m["hole"]
    ax.add_patch(MPoly(hexagon(cx, cy, NUT_AF), closed=True, fc="none", ec="0.2", lw=1.1, ls=":", zorder=8))
    ax.add_patch(Circle((cx, cy), HEAD_D / 2, fc="white", ec="black", lw=1.3, alpha=.9, zorder=8))
    ax.add_patch(Circle((cx, cy), 1.75, fc=C_BOARD, ec="black", lw=1, zorder=9))
    ax.plot([0, L], [cy, cy], color="0.35", lw=.8, ls="-.", zorder=5)
    ax.text(17, cy + .3, f"screw line ({m['hole_txt']})", fontsize=9, color="0.25", va="bottom", zorder=10)
    ax.text(0.5, 0.5, "window (active area)", fontsize=9.5, color="0.3", va="bottom")
    ax.text(L - 12, -m["pcb"] + .3, "PCB / carbon-back edge", fontsize=9.5, color=C_BOARD_EC, ha="right",
            va="bottom", zorder=10)
    ax.text(L + 2.5, -m["req"], "edge asked", fontsize=9.5, color=C_REQ, va="center")
    head_out = m["hole"] + HEAD_D / 2
    dim(ax, 30, 0, m["v3"], f"V3 wall {m['v3']:.1f}")
    dim(ax, 41, 0, m["req"], f"asked {m['req']:.1f}", color=C_REQ)
    past = m["v3"] - m["pcb"]
    if abs(past) < 0.1:
        ax.text(52, -m["v3"] + .5, f"V3 flush with the PCB edge  (asked +{m['req'] - m['pcb']:.1f} past it)",
                fontsize=9.5, color=C_DIM, va="bottom", bbox=dict(fc="white", ec="none", alpha=.85, pad=.4), zorder=12)
    else:
        dim(ax, 52, m["pcb"], m["v3"], f"V3 past PCB {past:+.1f}  (asked {m['req'] - m['pcb']:+.1f})", fs=9.5)
    ax.annotate("", (cx + 4.2, -head_out), (cx + 4.2, -m["v3"]),
                arrowprops=dict(arrowstyle="<->", color=C_DIM, lw=1.1, shrinkA=0, shrinkB=0))
    ax.plot([cx, cx + 5], [-head_out] * 2, color=C_DIM, lw=.6)
    ax.text(cx + 4.8, -max(m["v3"], m["req"]) - .9,
            f"wall left past the M3 head: V3 {m['v3'] - head_out:.2f} mm, asked {m['req'] - head_out:.2f} mm",
            fontsize=9.5, color=C_DIM, va="top")
    ax.set_xlim(-2, L + 13)
    ax.set_ylim(-max(m["v3"], m["req"]) - 3.5, 2.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ticks = sorted({0.0, round(m["hole"], 1), round(m["pcb"], 1), round(m["v3"], 1), round(m["req"], 1)})
    ticks = [t for i, t in enumerate(ticks) if i == 0 or t - ticks[i - 1] > 0.3]
    ax.set_yticks([-t for t in ticks])
    ax.set_yticklabels([f"{t:g}" for t in ticks], fontsize=9)
    verdict = ("V3 is wider than asked" if m["v3"] > m["req"] + .05 else
               "V3 is NARROWER than asked" if m["v3"] < m["req"] - .05 else "V3 as asked")
    ax.set_title(f"{e}:  {verdict}", fontsize=12, loc="left", weight="bold",
                 color=C_REQ if m["v3"] < m["req"] - .05 else "black")
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)


def main():
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    M = measure()
    for e, m in M.items():
        print(e, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()})
    fig, axs = plt.subplots(3, 1, figsize=(15, 14))
    for ax, (e, m) in zip(axs, M.items()):
        panel(ax, e, m)
    fig.legend(handles=[Patch(fc=C_BOARD, ec=C_BOARD_EC, label="final PCB"),
                        Patch(fc=C_V3, ec=C_V3_EC, alpha=.8, label="frame V3 wall"),
                        Line2D([], [], color=C_REQ, ls="--", lw=2, label="frame edge asked in the revision"),
                        Line2D([], [], marker="o", ls="none", mfc="white", mec="k", ms=10, label=f"M3 head Ø{HEAD_D}"),
                        Line2D([], [], marker="h", ls="none", mfc="none", mec="0.25", ms=10,
                               label=f"M3 nut AF {NUT_AF} (dotted)")],
               loc="lower center", ncol=5, fontsize=10.5, frameon=False)
    fig.suptitle("Frame wall width on the sides: frame V3 vs the revision\n"
                 "(edge unrolled: window at the top, outside at the bottom; true scale; "
                 "mm measured in the final files from the window edge)", fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .94), h_pad=3)
    fig.savefig(os.path.join(G.FIG, "6_side_widths.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
