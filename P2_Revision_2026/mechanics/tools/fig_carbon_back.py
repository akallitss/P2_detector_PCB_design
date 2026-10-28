#!/usr/bin/env python3
"""
Carbon back (strongback, behind the PCB): NOW vs NEW, and the screw assembly
(head on the frame, washer + nut on the carbon side).

Writes ../figures/carbon_back_overview.png, carbon_back_corner_A.png, screw_assembly.png
and    ../data/carbon_back_holes_new.csv
Run with  (ulimit -v 3000000; python3 fig_carbon_back.py)
"""
import csv
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon as MPoly, Rectangle
from shapely.geometry import Point, box

import rev_geometry as rg
from fig_frame_corners import C_DIM, C_EXT, C_EXT_EC, C_FRAME, C_FRAME_EC, C_OPEN, C_WIDE, callout, dim, poly_patch
from fig_frame_section import straight_profile

FIG = os.path.join(rg.OUT, "figures")
C_CB, C_CB_EC = "#4a4f57", "black"
C_CONN = "#9b59b6"


def view(ax, new, win=None):
    if new:
        P = rg.cb_new()
        old_outline = rg.pcb_outline(rg.SIDE_NOW, rg.R_IN_EDGE_NOW)
        removed = old_outline.difference(P.union(rg.cb_window()).buffer(0.01)).difference(
            rg.pcb_outline().difference(old_outline))
        removed = removed.difference(rg.Point(0, 0).buffer(rg.CB_R_OUT, 2048))
        ax.add_patch(poly_patch(removed, fc="none", ec=C_OPEN, lw=1.0, ls="--", hatch="\\\\\\", zorder=1))
        ax.add_patch(poly_patch(rg.connector_band(), fc=C_CONN, ec="none", alpha=.25, zorder=1))
        ax.add_patch(poly_patch(P, fc=C_CB, ec=C_CB_EC, lw=.5, alpha=.85, zorder=2))
        ax.add_patch(poly_patch(rg.cb_ribs(), fc=C_EXT, ec=C_EXT_EC, lw=.6, alpha=.9, zorder=3))
        ax.plot(*np.asarray(rg.pcb_outline().exterior.coords).T, color="0.3", lw=.8, ls="--", zorder=4)
        for _, x, y, _ in rg.new_frame_holes()[0]:
            ax.add_patch(Circle((x, y), rg.SCREW_D / 2 if win else 3.2, fc="white", ec="black", lw=.9, zorder=5))
    else:
        P, holes = rg.cb_now()
        ax.add_patch(poly_patch(P, fc=C_CB, ec=C_CB_EC, lw=.5, alpha=.85, zorder=2))
        for d, pts in holes.items():
            for x, y in pts:
                ax.add_patch(Circle((x, y), float(d) / 2 if win else 2.6, fc="white", ec="black", lw=.7, zorder=5))
    ax.set_aspect("equal")
    if win:
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.grid(lw=.25, alpha=.5)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    else:
        ax.set_xlim(20, 665)
        ax.set_ylim(-30, 560)
        ax.axis("off")


def overview():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 9.6))
    view(a0, False)
    view(a1, True)
    a0.set_title("NOW", fontsize=14, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=14, weight="bold", loc="left", color=C_EXT_EC)
    fig.text(0.04, 0.205, "frame-shaped carbon plate behind the PCB\n"
            "• goes out to R650 (under the connectors,\n   which are on the front today)\n"
            "• 80 holes, 3 kinds (Ø3.5, Ø3.2, Ø2.5)\n• open in the middle", fontsize=9.5, va="top",
            bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.5"))
    fig.text(0.52, 0.205, f"1. thickness {rg.CB_T:g} mm\n"
            f"2. extension REMOVED: outer edge at r = {rg.CB_R_OUT:g},\n"
            f"    {rg.CONN_MARGIN:g} mm before the connectors (now on this side)\n"
            "3. outline = PCB outline (unchanged), window unchanged\n"
            f"4. {len(rg.new_frame_holes()[0])} × Ø{rg.SCREW_D:g} = same pattern as the frame\n"
            f"    (M3 × {rg.screw_length()[0]}: head on the frame, washer + nut on this side)\n"
            "5. \"#\" ribs across the opening to stop the PCB\n"
            f"    bending – PRINCIPLE ONLY ({len(rg.RIBS_RADIAL_DEG)} radial + {len(rg.RIBS_ARC_R)} arcs,\n"
            f"    {rg.RIB_W:g} mm): number and width free to the designer",
            fontsize=9.5, va="top", bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    h = [Patch(fc=C_CB, ec=C_CB_EC, alpha=.85, label="carbon back"),
         Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: \"#\" ribs (principle)"),
         Patch(fc="none", ec=C_OPEN, ls="--", hatch="\\\\\\", label="REMOVED: extension"),
         Patch(fc=C_CONN, alpha=.25, label="connectors (now on the back of the PCB)"),
         Line2D([], [], color="0.3", ls="--", label="PCB outline (unchanged)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="black", label="holes (symbols enlarged)")]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=6, fontsize=8.5, frameon=False)
    fig.suptitle("Carbon back (strongback behind the PCB) – what changes", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.21, 1, 0.92))
    fig.savefig(os.path.join(FIG, "carbon_back_overview.png"), dpi=130)
    plt.close(fig)


def corner():
    win = (585, 662, -22, 55)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 7.8))
    view(a0, False, win)
    view(a1, True, win)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (640, 40), (600, 45), "extension to R650\n(today: connectors on the front)")
    callout(a0, (632, 28), (628, -17), "connector holes Ø2.5 / Ø3.2\n(go away)")
    # 6 mm margin to the connectors, measured radially at 15 deg
    t = math.radians(15)
    u = np.array([math.cos(t), math.sin(t)])
    dim(a1, tuple(rg.CB_R_OUT * u), tuple(rg.CONN_R_IN * u), (-3 * u[1] * 0 - 4.5 * math.sin(t), 4.5 * math.cos(t)),
        f"{rg.CONN_R_IN - rg.CB_R_OUT:.1f}", fs=8)
    callout(a1, tuple(rg.CB_R_OUT * np.array([math.cos(math.radians(4)), math.sin(math.radians(4))])), (593, 38),
            f"new outer edge r = {rg.CB_R_OUT:g}\n({rg.CONN_MARGIN:g} mm before the connector pads)", color=C_DIM)
    callout(a1, (632, 25), (636, 47), "connectors FX20-140P\n(back side, r 627–637)", color=C_CONN)
    callout(a1, (645, 30), (643, 5), "extension removed", color=C_OPEN)
    tr = np.array(rg.DRIFT_FEED)
    a1.plot(*tr.T, color="#c0392b", lw=2.2, ls=(0, (3, 1.5)), zorder=6)
    callout(a1, tuple(tr[2]), (589, -17), "drift feed on the FRONT copper (today's mesh line):\n"
            "no drift HV on the back any more, nothing to insulate\nunder the carbon", color="#c0392b")
    h = [Patch(fc=C_CB, ec=C_CB_EC, alpha=.85, label="carbon back"),
         Patch(fc="none", ec=C_OPEN, ls="--", hatch="\\\\\\", label="REMOVED: extension"),
         Patch(fc=C_CONN, alpha=.25, label="connectors (back of the PCB)"),
         Line2D([], [], color="#c0392b", lw=2.2, ls=(0, (3, 1.5)), label="drift feed (front copper, other side of the PCB)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="black", label="Ø3.5 screw holes (frame pattern)")]
    fig.legend(handles=h, loc="lower center", ncol=5, fontsize=8.5, frameon=False)
    fig.suptitle(f"Carbon back – corner A: extension removed, {rg.CONN_MARGIN:g} mm margin to the connectors", fontsize=14, y=.98)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(FIG, "carbon_back_corner_A.png"), dpi=130)
    plt.close(fig)


def screw_assembly():
    """Section across a straight side through a screw: head on the frame top, washer + nut under
    the carbon back. The frame now overhangs the PCB / carbon back by rg.OVERHANG on this side."""
    P = straight_profile()
    th = rg.Y_SIDE
    hole = box(th - rg.SCREW_D / 2, -1, th + rg.SCREW_D / 2, rg.FRAME_H + 1)
    L, need = rg.screw_length()
    fig = plt.figure(figsize=(15, 7.2))
    ax = fig.add_axes([0.05, 0.1, 0.58, 0.8])
    ax.add_patch(poly_patch(P.difference(hole), fc=C_FRAME, ec=C_FRAME_EC, lw=1.0, zorder=2))
    ax.add_patch(Rectangle((-rg.SIDE_NEW, 0), rg.OVERHANG, rg.FRAME_H, fc=C_WIDE, ec=C_EXT_EC, lw=.8, zorder=2))
    zc = -rg.PCB_T - rg.CB_T
    ax.add_patch(Rectangle((-rg.SIDE_NOW, -rg.PCB_T), 25, rg.PCB_T, fc="#2e7d32", alpha=.5, zorder=2))
    ax.add_patch(Rectangle((-rg.SIDE_NOW, zc), 25, rg.CB_T, fc=C_CB, alpha=.85, zorder=2))
    ax.add_patch(Rectangle((th - rg.SCREW_D / 2, zc), rg.SCREW_D, rg.CB_T + rg.PCB_T, fc="white", ec="none", zorder=3))
    head_t = 3.0
    zt = rg.FRAME_H
    ax.add_patch(Rectangle((th - rg.HEAD_D / 2, zt), rg.HEAD_D, head_t, fc="#b0b6bf", ec="black", lw=.8, zorder=4))
    ax.add_patch(Rectangle((th - 1.5, zt - L), 3.0, L, fc="#b0b6bf", ec="black", lw=.8, zorder=4))
    zw = zc - rg.WASHER_T
    ax.add_patch(Rectangle((th - rg.WASHER_OD / 2, zw), rg.WASHER_OD, rg.WASHER_T, fc="#f1c40f", ec="black", lw=.8, zorder=5))
    ax.add_patch(Rectangle((th - rg.NUT_AF / 2, zw - rg.NUT_T), rg.NUT_AF, rg.NUT_T, fc="#7f8c8d", ec="black", lw=.8, zorder=5))
    ax.axvline(-rg.SIDE_NEW, color="#c0392b", lw=1.2, ls="--", zorder=6)
    ax.text(-rg.SIDE_NEW - 0.3, 12.3, "NEW frame edge\n(outermost part)", color="#c0392b", fontsize=8.5, ha="right", va="top")
    ax.axvline(-rg.SIDE_NOW, color="0.4", lw=1.0, ls=":", zorder=6)
    ax.text(-rg.SIDE_NOW + 0.3, -8.6, "PCB / carbon-back edge (unchanged)", color="0.3", fontsize=8, ha="left")
    head_in = (th + rg.SIDE_NEW) - rg.HEAD_D / 2              # head inside the new frame edge
    nut_over = rg.NUT_AF / 2 - (th + rg.SIDE_NOW)             # nut past the carbon-back edge
    dim(ax, (th - rg.HEAD_D / 2, zt + head_t / 2), (-rg.SIDE_NEW, zt + head_t / 2), (0, 0), "", fs=8, color=C_DIM)
    dim(ax, (th - rg.NUT_AF / 2, zw - rg.NUT_T / 2), (-rg.SIDE_NOW, zw - rg.NUT_T / 2), (0, 0), "", fs=8, color="#c0392b")
    dim(ax, (-rg.SIDE_NEW, rg.FRAME_H), (th, rg.FRAME_H), (0, 3.6), f"{th + rg.SIDE_NEW:g}", fs=8)
    for xy, xyt, t, c in (((th + 2.75, zt + 1.5), (-1.5, 11.4), f"M3 head Ø{rg.HEAD_D:g} on the frame top: {head_in:.2f} mm inside the new edge  ✓", C_DIM),
                          ((th + 2.75, zw - 1.2), (-1.5, -7.6), f"M3 nut (AF {rg.NUT_AF:g}, flats parallel to the edge): {nut_over:.2f} mm past the\n"
                                                                 f"carbon back, still {rg.OVERHANG - nut_over:.2f} mm inside the frame edge", "#c0392b"),
                          ((-rg.SIDE_NEW + .75, 6.5), (-15.5, 9.8), f"NEW +{rg.OVERHANG:g} mm", C_EXT_EC),
                          ((th + 1.5, 2.0), (2.0, 6.6), f"Ø{rg.SCREW_D:g} hole, {rg.Y_SIDE_NOW:g} from the axis: cannot move,\n"
                                                        "already 0.26 mm from the O-ring groove", "black"),
                          ((4.0, zc + 1.5), (6.0, -2.6), f"carbon back {rg.CB_T:g} mm", "black"),
                          ((5.0, -0.1), (8.0, 0.9), "PCB", "black")):
        ax.annotate(t, xy, xyt, fontsize=8.5, color=c, arrowprops=dict(arrowstyle="->", lw=.7, color=c))
    ax.set_xlim(-16, 15)
    ax.set_ylim(-9, 13)
    ax.set_aspect("equal")
    ax.grid(lw=.25, alpha=.4)
    ax.tick_params(labelsize=7)
    ax.set_xlabel("distance across the straight side [mm]  (0 = wall facing the active area)", fontsize=8)
    ax.set_ylabel("z [mm]", fontsize=8)
    ax.set_title(f"Straight side, section through a screw (M3 × {L}: needs {need:.1f} mm)", fontsize=11, loc="left", weight="bold")
    bx = fig.add_axes([0.66, 0.12, 0.33, 0.76])
    bx.axis("off")
    txt = ("Where the hardware fits\n\n"
           f"Outer arc (today's holes kept, r = {rg.R_OUT:g}):\n"
           f"  washer + nut on the carbon back, edge r = {rg.CB_R_OUT:g}\n"
           f"  ({rg.CONN_MARGIN:g} mm before the connectors)  ✓\n\n"
           f"Inner arc (r = {rg.R_IN:g}, frame edge now R{rg.R_IN_EDGE_NEW:g}):  ✓\n\n"
           f"Straight sides (y = {rg.Y_SIDE:g}): the frame now goes to\n"
           f"  y = −{rg.SIDE_NEW:g}, {rg.OVERHANG:g} mm past the PCB (y = −{rg.SIDE_NOW:g}):\n"
           f"  • M3 head on the frame: {head_in:.2f} mm inside  ✓\n"
           f"  • M3 nut on the carbon back: {nut_over:.2f} mm past the\n"
           f"    carbon edge (corners 0.68 mm), but inside the\n"
           f"    frame's outline, so nothing sticks out of the\n"
           f"    detector any more  ✓\n"
           "  • a smaller nut (M2.5, AF 5.0) would be flush")
    bx.text(0, 1, txt, va="top", fontsize=10, family="DejaVu Sans",
            bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.6"))
    fig.suptitle("Screws: head on the frame top, washer + nut on the carbon-back side", fontsize=13, y=.985)
    fig.savefig(os.path.join(FIG, "screw_assembly.png"), dpi=130)
    plt.close(fig)


def write_csv():
    with open(os.path.join(rg.OUT, "data", "carbon_back_holes_new.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["no", "x_mm", "y_mm", "diameter_mm", "note"])
        for no, x, y, e in rg.new_frame_holes()[0]:
            w.writerow([no, f"{x:.2f}", f"{y:.2f}", rg.SCREW_D, f"same as frame hole {no} ({e})"])


def main():
    overview()
    corner()
    screw_assembly()
    write_csv()
    print("written carbon_back_overview.png, carbon_back_corner_A.png, screw_assembly.png, data/carbon_back_holes_new.csv")


if __name__ == "__main__":
    main()
