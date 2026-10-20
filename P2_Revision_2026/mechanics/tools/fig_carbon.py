#!/usr/bin/env python3
"""
Carbon drift piece (sits on the frame's z = 4 step, mylar glued under it):
NOW vs NEW = 2 mm thick + a flap at the B2 drift-pad corner pressing a conductive-foam
column (5 x 1 mm sheets, 4 x 4 mm) held by an insulating guide ring on the PCB.

Writes ../figures/carbon_overview.png, carbon_corner_B2.png, carbon_stack_section.png
Run with  (ulimit -v 3000000; python3 fig_carbon.py)
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import Polygon, box

import rev_geometry as rg
from fig_frame_corners import C_DIM, C_EXT, C_EXT_EC, C_FRAME, C_FRAME_EC, C_OPEN, C_PAD, callout, dim, poly_patch

FIG = os.path.join(rg.OUT, "figures")
C_CARB, C_LEDGE = "#3b3f46", "#e4e6ea"
C_FOAM, C_RING, C_MYLAR = "#7fb04a", "#5b9bd5", "#8e44ad"


def frame_parts():
    outer, window, _ = rg.frame_top()                    # window = upper opening (z 4-8)
    base_open = window.buffer(-3.0, join_style=2)        # opening below the 3 mm step
    return outer.difference(window), window.difference(base_open), base_open


def top_view(ax, new, win=None, detail=False):
    wall, ledge, _ = frame_parts()
    ax.add_patch(poly_patch(wall, fc=C_FRAME, ec=C_FRAME_EC, lw=.6, zorder=1))
    ax.add_patch(poly_patch(ledge, fc=C_LEDGE, ec=C_FRAME_EC, lw=.4, zorder=1))
    strip = rg.carbon_strip()
    if detail:
        x, y, s = rg.B2_PAD
        ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc=C_PAD, ec="#8a6a00", lw=.6, zorder=2))
        ax.add_patch(poly_patch(rg.mesh_area(), fc="#d9dde3", ec="0.55", lw=.5, hatch="....", zorder=1.5))
        c = rg.B2_CUT
        ax.plot([c[0], c[0], 620], [-10, c[3], c[3]], color=C_OPEN, lw=1.4, ls="--", zorder=6)
        m = rg.M_PAD_A
        ax.add_patch(Rectangle(m[:2], m[2] - m[0], m[3] - m[1], fc=C_PAD, ec="#8a6a00", lw=.6, zorder=2))
    ax.add_patch(poly_patch(strip, fc=C_CARB, ec="black", lw=.6, alpha=.85, zorder=3))
    if new:
        flap = rg.carbon_flap().difference(strip)
        ax.add_patch(poly_patch(flap, fc=C_EXT, ec=C_EXT_EC, lw=1.2, alpha=.6, zorder=4))
        if detail:
            ax.add_patch(poly_patch(rg.guide_ring(), fc=C_RING, ec="#2c5f8a", lw=.8, alpha=.85, zorder=5))
            ax.add_patch(poly_patch(rg.foam_square(), fc=C_FOAM, ec="#3d6b1a", lw=.8, hatch="xx", zorder=5))
    ax.set_aspect("equal")
    if win:
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.grid(lw=.25, alpha=.5)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    else:
        ax.set_xlim(20, 640)
        ax.set_ylim(-30, 560)
        ax.axis("off")


def overview():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 8))
    top_view(a0, False)
    top_view(a1, True)
    a0.set_title("NOW", fontsize=14, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=14, weight="bold", loc="left", color=C_EXT_EC)
    a0.text(200, 280, "carbon strip, 5 mm wide, sits on the\n3 mm step of the frame at z = 4;\n"
            "the mylar is glued under it\n\nthickness today: not in the DXF", fontsize=10, va="top",
            bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.5"))
    a1.text(200, 280, f"1. thickness → {rg.CARBON_T_NEW:g} mm\n"
            "2. NEW flap at the B2 drift-pad corner,\n    pressing the conductive foam (zoom)\n"
            "3. outline unchanged", fontsize=10, va="top",
            bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    for ax in (a0, a1):
        ax.add_patch(Rectangle((575, -8), 35, 30, fc="none", ec=C_OPEN, lw=1.3))
    a1.annotate("flap (see zoom)", (586, 14), (470, 80), fontsize=10, color=C_EXT_EC,
                arrowprops=dict(arrowstyle="->", color=C_EXT_EC))
    h = [Patch(fc=C_CARB, ec="black", label="carbon drift piece"),
         Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: flap (same 2 mm carbon, one piece with the strip)"),
         Patch(fc=C_FRAME, ec=C_FRAME_EC, label="drift frame, upper wall (z 4–8)"),
         Patch(fc=C_LEDGE, ec=C_FRAME_EC, label="frame step at z = 4 (3 mm wide)")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("Carbon drift piece (sets the drift gap, carries the mylar) – what changes", fontsize=14, y=.98)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(FIG, "carbon_overview.png"), dpi=130)
    plt.close(fig)


def corner():
    win = (576, 608, -6, 21)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 7.4))
    top_view(a0, False, win, detail=True)
    top_view(a1, True, win, detail=True)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (590.5, 10), (578, 18.5), "B2 drift pad 3 × 3 (PCB)")
    callout(a0, (585.5, 6), (577, 1), "mesh cut: whole corner cleared\n(no mesh for x ≥ 585.5, y ≤ 15)", color=C_OPEN)
    callout(a0, (597.2, 2.7), (589, -4.5), "mesh-contact pad M", color="#8a6a00")
    callout(a0, (600, 0), (601, -4.5), "carbon strip (5 mm)")
    callout(a0, (601.5, 8), (601, 16), "frame step\nat z = 4")
    fx0, fy0, fx1, fy1 = rg.carbon_flap().bounds
    fx1 = 597.5
    dim(a1, (fx0, fy1), (fx1, fy1), (0, 2.0), f"{fx1 - fx0:.1f}")
    dim(a1, (fx0, fy0), (fx0, fy1), (-2.6, 0), f"{fy1 - fy0:.1f}")
    callout(a1, (fx1, fy0), (600.5, -4.5), f"flap starts at the strip's\ninner corner ({fx1:g}, {fy0:g})", color=C_DIM)
    callout(a1, (586.5, 14.2), (577.5, 19.3), "flap edges = the mesh cut lines\n(x = 585.5, y = 15)", color=C_EXT_EC)
    callout(a1, (597.2, 2.7), (588, -4.5), "M pad: no mesh on it any more\n→ mesh contact for the PCB step", color="#8a6a00")
    f = rg.foam_square()
    x0, y0, x1, y1 = f.bounds
    dim(a1, (x0 + 1.2, y1), (x0 + 1.2, rg.B2_CUT[3]), (0, 0), f"{rg.B2_CUT[3] - y1:g} mm", fs=8, color=C_OPEN)
    dim(a1, (rg.B2_CUT[0], y0 + 1.2), (x0, y0 + 1.2), (0, 0), f"{x0 - rg.B2_CUT[0]:g} mm", fs=8, color=C_OPEN)
    callout(a1, (x0 + .5, y0 + .5), (577, 1), f"foam {rg.FOAM_SIDE:g} × {rg.FOAM_SIDE:g} mm, centred on the pad\n"
            f"{rg.CLEAR_HV:g} mm from the bare mesh", color="#3d6b1a")
    r = rg.guide_ring().bounds
    callout(a1, (r[2] - .4, (r[1] + r[3]) / 2), (599.5, 11), f"insulating guide ring\n(on the PCB, {rg.RING_H:g} mm high)",
            color="#2c5f8a")
    h = [Patch(fc=C_CARB, ec="black", label="carbon strip"),
         Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: carbon flap"),
         Patch(fc=C_FOAM, ec="#3d6b1a", hatch="xx", label=f"NEW: conductive foam, {rg.foam_sheets(rg.STEP_Z)[0]} × 1 mm sheets"),
         Patch(fc=C_RING, ec="#2c5f8a", label="NEW: insulating guide ring"),
         Patch(fc=C_PAD, ec="#8a6a00", label="B2 drift pad (PCB)"),
         Patch(fc="#d9dde3", ec="0.55", hatch="....", label="mesh (none in the corner)"),
         Line2D([], [], color=C_OPEN, ls="--", label="mesh cut lines"),
         Patch(fc=C_LEDGE, ec=C_FRAME_EC, label="frame step (z = 4)"),
         Patch(fc=C_FRAME, ec=C_FRAME_EC, label="frame upper wall")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("Carbon drift piece – flap at the B2 drift-pad corner (top view)", fontsize=14, y=.98)
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    fig.savefig(os.path.join(FIG, "carbon_corner_B2.png"), dpi=130)
    plt.close(fig)


def outer_arc_profile():
    """Outer-arc wall profile (r, z) from the STEP radial section; x ~ r at y = 10."""
    loops = [np.array(w) for w in json.load(open(os.path.join(rg.OUT, "data", "frame_section_r27.json")))]
    P = sorted((Polygon(L).buffer(0) for L in loops if L[:, 0].mean() > 300), key=lambda q: -q.area)
    return Polygon(P[0].exterior)          # outline only (schematic; internal features not relevant here)


def section_panel(ax, gap, n_sheets, compression, placeholder=False):
    """Section along y = 10 through pad, foam, flap and the outer-arc wall."""
    dz = gap - rg.STEP_Z
    wall = outer_arc_profile()
    if dz:
        # placeholder: the step (and everything above it) raised by dz
        from shapely import affinity
        lower = wall.intersection(box(590, 0, 630, rg.STEP_Z))
        upper = affinity.translate(wall.intersection(box(590, rg.STEP_Z, 630, 20)), 0, dz)
        wall = lower.union(upper).union(box(600, rg.STEP_Z, 615, rg.STEP_Z + dz))
    ax.add_patch(poly_patch(wall, fc=C_FRAME, ec=C_FRAME_EC, lw=.8, zorder=2))
    ax.add_patch(Rectangle((574, -1.6), 50, 1.6, fc="#2e7d32", alpha=.25, ec="none", zorder=1))
    ax.text(576, -1.05, "PCB", fontsize=8, color="#1b4d1e")
    x, y, s = rg.B2_PAD
    ax.add_patch(Rectangle((x - s / 2, 0), s, 0.12, fc=C_PAD, ec="#8a6a00", lw=.5, zorder=3))
    # mesh: bare in the active area, absent in the cut
    ax.plot([574, rg.B2_CUT[0]], [0.13, 0.13], color="0.2", lw=1.2, ls=(0, (1, 1)), zorder=3)
    # foam column
    f = rg.foam_square().bounds
    ax.add_patch(Rectangle((f[0], 0.12), f[2] - f[0], gap - 0.12, fc=C_FOAM, ec="#3d6b1a", lw=.8, hatch="xx", zorder=3))
    ax.add_patch(Rectangle((f[0], 0.12), f[2] - f[0], n_sheets * rg.FOAM_SHEET, fc="none", ec="#3d6b1a", lw=.8, ls="--", zorder=3))
    for k in range(1, n_sheets):
        zk = 0.12 + k * (gap - 0.12) / n_sheets
        ax.plot([f[0], f[2]], [zk, zk], color="#3d6b1a", lw=.5, zorder=4)
    r = rg.guide_ring().bounds
    for xa in (r[0], f[2] + rg.RING_GAP):
        ax.add_patch(Rectangle((xa, 0.12), rg.RING_WALL, rg.RING_H, fc=C_RING, ec="#2c5f8a", lw=.7, zorder=4))
    # mylar (glued under the carbon) and carbon strip + flap
    ax.plot([574, 602.5], [gap, gap], color=C_MYLAR, lw=2.2, zorder=6)
    ax.add_patch(Rectangle((597.5, gap), 5.0, rg.CARBON_T_NEW, fc=C_CARB, ec="black", lw=.6, zorder=5))
    ax.add_patch(Rectangle((rg.B2_CUT[0], gap), 597.5 - rg.B2_CUT[0], rg.CARBON_T_NEW, fc=C_EXT, ec=C_EXT_EC, lw=1.0, zorder=5))
    # dimensions / notes
    dim(ax, (f[2] + 2.6, 0.12), (f[2] + 2.6, gap), (0, 0), "", fs=8)
    ax.text(f[2] + 3.0, gap / 2, f"{gap:g} mm\ndrift gap", fontsize=8, va="center", color=C_DIM)
    ax.annotate(f"foam: {n_sheets} × 1 mm = {n_sheets:g} mm free\n→ squeezed to {gap:g} mm ({compression * 100:.0f} %)",
                (f[0] + .3, gap * .55), (575, gap * .62), fontsize=8.5, color="#3d6b1a",
                arrowprops=dict(arrowstyle="->", color="#3d6b1a", lw=.7))
    ax.annotate(f"guide ring, insulating, {rg.RING_H:g} mm high", (r[0] + .4, 1.8), (575, 1.3), fontsize=8,
                color="#2c5f8a", arrowprops=dict(arrowstyle="->", color="#2c5f8a", lw=.7))
    ax.annotate("mylar, glued under the carbon\n(aluminium side towards the PCB)", (582, gap), (575, gap + 3.4),
                fontsize=8, color=C_MYLAR, arrowprops=dict(arrowstyle="->", color=C_MYLAR, lw=.7))
    ax.annotate(f"carbon flap, {rg.CARBON_T_NEW:g} mm: pushes the mylar onto the foam", (590, gap + 1.4), (588, gap + 4.6),
                fontsize=8, color=C_EXT_EC, arrowprops=dict(arrowstyle="->", color=C_EXT_EC, lw=.7))
    ax.annotate("frame step", (601.2, gap), (606, gap - 1.6), fontsize=8, arrowprops=dict(arrowstyle="->", lw=.6))
    ax.annotate("mesh ends at x = 585.5 (corner cleared to the wall)", (583, 0.13), (575, -3.3), fontsize=7.5,
                arrowprops=dict(arrowstyle="->", lw=.6))
    ax.set_xlim(574, 618)
    ax.set_ylim(-4, gap + 6.2)
    ax.set_aspect("equal")
    ax.grid(lw=.25, alpha=.4)
    ax.tick_params(labelsize=7)
    ax.set_xlabel("x [mm]  (section along y = 10 through the pad)", fontsize=8)
    ax.set_ylabel("z [mm]", fontsize=8)
    t = (f"PLACEHOLDER – {gap:g} mm drift gap: step at z = {gap:g}, {n_sheets} sheets" if placeholder
         else f"{gap:g} mm drift gap (baseline)")
    ax.set_title(t, fontsize=11, loc="left", weight="bold", color=("0.4" if placeholder else "black"))


def stack():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(16, 5.0))
    n4, c4 = rg.foam_sheets(rg.STEP_Z)
    n5, c5 = rg.foam_sheets(rg.STEP_Z_5MM)
    section_panel(a0, rg.STEP_Z, n4, c4)
    section_panel(a1, rg.STEP_Z_5MM, n5, c5, placeholder=True)
    fig.suptitle("HV contact to the mylar at the B2 corner – cross-section of the stack "
                 "(foam MECF-010P, 1 mm sheets; recommended compression 15–30 %; frame drawn as outline)",
                 fontsize=12, y=.985)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(os.path.join(FIG, "carbon_stack_section.png"), dpi=130)
    plt.close(fig)


def main():
    overview()
    corner()
    stack()
    print("written carbon_overview.png, carbon_corner_B2.png, carbon_stack_section.png")


if __name__ == "__main__":
    main()
