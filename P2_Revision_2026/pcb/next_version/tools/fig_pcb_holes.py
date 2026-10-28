#!/usr/bin/env python3
"""
PCB screw holes, 2026 revision: which of today's holes are kept, which go, and where the new ones
come (same numbering as the frame and the carbon back, P2_Revision_2026/mechanics).

  KEEP    today's hole, unchanged (position, Ø, plating): the 13 on the outer arc, which sit
          between the signal lines, and the 2 inner corners
  REMOVE  today's hole that goes
  ADD     new hole, equal pitch between the corners on the straight sides and the inner arc

Writes ../figures/pcb_screw_holes.png, pcb_screw_holes_unrolled.png and ../data/pcb_screw_holes.csv
Run with (ulimit -v 3000000; python3 fig_pcb_holes.py)
"""
import csv
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import fig_pcb as fp

rg = fp.rg
EDGES = ["bottom side", "outer arc", "top side", "inner arc"]
C_KEEP, C_ADD, C_REM = "0.55", "white", "#c0392b"
C_PTH, C_NPTH = "#1f5fbf", "#8e44ad"


def plan():
    """[(action, no, x, y, edge, plating_today)]: the 37 holes of the new pattern, then the removed ones."""
    _, H = rg.read_drill()
    today = {(round(x, 2), round(y, 2)): ("PTH" if k == 3 else "NPTH") for k in (3, 6) for x, y in H[k]}

    def plating(x, y):
        return next(v for (a, b), v in today.items() if math.hypot(x - a, y - b) < 0.05)
    out = []
    for no, x, y, e in rg.new_frame_holes()[0]:
        if fp.is_kept_hole(x, y):
            out.append(("KEEP", no, x, y, e, plating(x, y)))
        else:
            out.append(("ADD", no, x, y, e, "–"))
    for (x, y), pl in today.items():
        if not fp.in_new_pattern(x, y):
            out.append(("REMOVE", None, x, y, " / ".join(rg.edge_of((x, y))), pl))
    return out


def edge_label(no, x, y, e):
    """Where to write a hole number: outside the board edge."""
    r = math.hypot(x, y)
    if e == "bottom side" or (e == "corner" and y < 0):
        return x, y - 14
    if e == "top side" or (e == "corner" and x < 300 and y > 80):
        return x - 13 * math.sin(math.radians(60)), y + 13 * math.cos(math.radians(60))
    k = (r + 14) / r if r > 300 else (r - 14) / r
    return x * k, y * k


def hole_map(P):
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(19, 10.5))
    for ax in (a0, a1):
        fp.board(ax)
        ax.add_patch(fp.poly_patch(rg.frame_top()[1].buffer(-3.0, join_style=2), fc="white", ec="0.6", lw=.5, ls=":",
                                   zorder=0))
        ax.set_xlim(15, 675)
        ax.set_ylim(-35, 570)
        ax.set_aspect("equal")
        ax.axis("off")
    # NOW: today's 40 holes, plated / not plated; the ones that go crossed out
    for act, no, x, y, e, pl in P:
        if act == "ADD":
            continue
        ax_kw = dict(mfc=C_PTH, mec=C_PTH) if pl == "PTH" else dict(mfc="white", mec=C_NPTH)
        a0.plot(x, y, "o", ms=10, mew=2, zorder=5, **ax_kw)
        if act == "REMOVE":
            a0.plot(x, y, "x", ms=13, mew=2.4, color=C_REM, zorder=6)
    # NEW: the 37 holes, kept (grey) or new (white), numbered
    for act, no, x, y, e, pl in P:
        if act == "REMOVE":
            continue
        a1.plot(x, y, "o", ms=10, mfc=C_KEEP if act == "KEEP" else C_ADD, mec="black", mew=1.6, zorder=5)
        a1.text(*edge_label(no, x, y, e), str(no), fontsize=8, ha="center", va="center", zorder=7,
                weight="bold" if act == "ADD" else "normal")
    new, pitch = rg.new_frame_holes()
    n = {a: sum(1 for p in P if p[0] == a) for a in ("KEEP", "REMOVE", "ADD")}
    n_pth = sum(1 for p in P if p[0] != "ADD" and p[5] == "PTH")
    a0.set_title("NOW", fontsize=15, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=15, weight="bold", loc="left", color="#b8650a")
    a0.text(215, 300, f"today: {n['KEEP'] + n['REMOVE']} holes, all Ø3.5\n"
            f"  • {n_pth} plated, {n['KEEP'] + n['REMOVE'] - n_pth} not plated\n"
            "  • spacing irregular (18 – 73 mm)\n\n"
            f"REMOVE {n['REMOVE']} (red ×): the straight sides\n"
            "and the inner arc, except the corners\n\n"
            f"KEEP {n['KEEP']} (not crossed): the outer arc\n"
            "and the 2 inner corners",
            fontsize=10.5, va="top", bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.6"))
    a1.text(200, 300, f"{len(new)} holes Ø3.5, same positions as\nthe frame and the carbon back\n\n"
            f"• KEEP {n['KEEP']} (grey): unchanged, plating as today\n"
            "    – outer arc: all 13 of today's holes; they sit\n"
            "      between the signal lines, none are added\n"
            "    – the 2 inner corners\n"
            f"• ADD {n['ADD']} (white, bold numbers): equal pitch\n"
            "  between the corner holes\n"
            f"    – bottom side {pitch['bottom side']:.1f} mm, top side {pitch['top side']:.1f} mm\n"
            f"    – inner arc {pitch['inner arc']:.1f} mm (mirror pair about 30°)\n"
            "    plating of the new holes: to decide",
            fontsize=10.5, va="top", bbox=dict(fc="white", ec="#b8650a", boxstyle="round,pad=.6"))
    a1.annotate("hole 13: plated pad 2.65 mm from the\ncorner-A drift line (pcb_corner_A_drift.csv)",
                (610.30, 14.50), (420, 45), fontsize=9, color=C_REM, arrowprops=dict(arrowstyle="->", color=C_REM))
    h = [Line2D([], [], marker="o", ls="none", ms=10, mfc=C_PTH, mec=C_PTH, mew=2, label="today: plated (PTH)"),
         Line2D([], [], marker="o", ls="none", ms=10, mfc="white", mec=C_NPTH, mew=2, label="today: not plated (NPTH)"),
         Line2D([], [], marker="x", ls="none", ms=11, mew=2.4, color=C_REM, label="REMOVE"),
         Line2D([], [], marker="o", ls="none", ms=10, mfc=C_KEEP, mec="black", mew=1.6, label="NEW: kept, unchanged"),
         Line2D([], [], marker="o", ls="none", ms=10, mfc=C_ADD, mec="black", mew=1.6, label="NEW: added, Ø3.5"),
         Patch(fc=fp.C_PCB, ec="0.3", label="PCB (outline unchanged)")]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=10, frameon=False)
    fig.suptitle("PCB – screw holes, NOW → NEW (numbers = frame and carbon-back numbering; symbols enlarged)",
                 fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(os.path.join(fp.FIG, "pcb_screw_holes.png"), dpi=130)
    plt.close(fig)


def unrolled(P):
    _, pitch = rg.new_frame_holes()
    pk = {"bottom side": f"new pitch {pitch['bottom side']:.1f} mm", "top side": f"new pitch {pitch['top side']:.1f} mm",
          "outer arc": "all of today's holes kept (between the signal lines), none added",
          "inner arc": f"new pitch {pitch['inner arc']:.1f} mm"}
    fig, axs = plt.subplots(4, 1, figsize=(15, 11))
    for ax, e in zip(axs, EDGES):
        on = [p for p in P if e in rg.edge_of(p[2:4])]
        today = sorted((rg.s_on(e, p[2:4], now=True), p) for p in on if p[0] in ("KEEP", "REMOVE"))
        new = sorted((rg.s_on(e, p[2:4]), p) for p in on if p[0] in ("KEEP", "ADD"))
        L = max(today[-1][0], new[-1][0])
        ax.plot([0, L], [1, 1], color="0.8", lw=6, solid_capstyle="butt", zorder=0)
        ax.plot([0, L], [-1, -1], color="#f6d3a3", lw=6, solid_capstyle="butt", zorder=0)
        for s, p in today:
            pl = p[5]
            ax.plot(s, 1, "o", ms=10, mfc=C_PTH if pl == "PTH" else "white", mec=C_PTH if pl == "PTH" else C_NPTH,
                    mew=2, zorder=3)
            if p[0] == "REMOVE":
                ax.plot(s, 1, "x", ms=13, mew=2.4, color=C_REM, zorder=4)
        for s, p in new:
            ax.plot(s, -1, "o", ms=10, mfc=C_KEEP if p[0] == "KEEP" else C_ADD, mec="black", mew=1.6, zorder=3)
            ax.text(s, -1.75, str(p[1]), ha="center", fontsize=8, weight="bold" if p[0] == "ADD" else "normal")
            if p[0] == "KEEP":
                ax.plot([s, s], [-0.75, 0.75], color="0.55", lw=.8, ls=":", zorder=1)
        for (s0, _), (s1, _) in zip(new[:-1], new[1:]):
            ax.text((s0 + s1) / 2, -0.45, f"{s1 - s0:.1f}", ha="center", fontsize=7.5, color="#b8650a")
        ax.text(-0.012 * L, 1, "TODAY", ha="right", va="center", fontsize=10, weight="bold")
        ax.text(-0.012 * L, -1, "NEW", ha="right", va="center", fontsize=10, weight="bold", color="#b8650a")
        ax.set_xlim(-0.08 * L, 1.03 * L)
        ax.set_ylim(-2.4, 1.9)
        ax.set_yticks([])
        for sp in ("left", "right", "top"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("position along the edge [mm]", fontsize=8)
        ax.set_title(f"{e}  —  {pk[e]}", fontsize=10.5, loc="left")
    h = [Line2D([], [], marker="o", ls="none", ms=9, mfc=C_PTH, mec=C_PTH, label="today: plated (PTH)"),
         Line2D([], [], marker="o", ls="none", ms=9, mfc="white", mec=C_NPTH, mew=2, label="today: not plated (NPTH)"),
         Line2D([], [], marker="x", ls="none", ms=11, mew=2.4, color=C_REM, label="REMOVE"),
         Line2D([], [], marker="o", ls="none", ms=9, mfc=C_KEEP, mec="black", label="KEEP (dotted line: same hole)"),
         Line2D([], [], marker="o", ls="none", ms=9, mfc=C_ADD, mec="black", label="ADD (new, Ø3.5)")]
    fig.legend(handles=h, loc="lower center", ncol=5, fontsize=9, frameon=False)
    fig.suptitle("PCB – screw holes edge by edge (each edge unrolled; orange numbers = new spacing in mm, "
                 "black = hole number)", fontsize=13, y=.99)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(os.path.join(fp.FIG, "pcb_screw_holes_unrolled.png"), dpi=130)
    plt.close(fig)


def table(P):
    notes = {"KEEP": "today's hole: keep as it is", "ADD": "new hole; same position in frame and carbon back",
             "REMOVE": "remove (pad, hole, mask opening)"}
    with open(os.path.join(fp.DATA, "pcb_screw_holes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["action", "no", "x_mm", "y_mm", "diameter_mm", "edge", "plating_today", "plating_new", "note"])
        for act, no, x, y, e, pl in P:
            note = notes[act]
            if act == "KEEP" and "outer arc" in rg.edge_of((x, y)):
                note += " (outer arc: between the signal lines)"
            if no == 13:
                note += "; plated pad 2.65 mm from the corner-A drift line (non-plated: 3.2 mm)"
            w.writerow([act, no or "", f"{x:.2f}", f"{y:.2f}", rg.SCREW_D, e, pl,
                        {"KEEP": pl, "ADD": "TO DECIDE", "REMOVE": ""}[act], note])


def main():
    P = plan()
    hole_map(P)
    unrolled(P)
    table(P)
    n = {a: sum(1 for p in P if p[0] == a) for a in ("KEEP", "REMOVE", "ADD")}
    print("written pcb_screw_holes.png, pcb_screw_holes_unrolled.png, data/pcb_screw_holes.csv", n)


if __name__ == "__main__":
    import i18n                     # P2_LANG=fr: French figures (*_fr.png), see i18n.py
    i18n.setup()
    main()
    i18n.finish()
