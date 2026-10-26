#!/usr/bin/env python3
"""
Foam slot at the B2 drift-pad corner (colleague's comment on the drawings: "add slot in 3D at lower
drift level for conductive foam + matching size on carbon frame").

The guide ring on the PCB is replaced by frame material: the frame's lower level (z 0-4, below the
mylar step) is filled in the cleared corner (x >= 585.5, y <= 15) and a slot through it holds the foam.
The carbon flap gets the same outline and rests on that block over its whole area.

Writes ../figures/foam_slot_1_frame_B2.png, foam_slot_2_3d.png, foam_slot_3_section.png,
foam_slot_4_carbon_flap.png
Run with  (ulimit -v 3000000; python3 fig_foam_slot.py)
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import box

import rev_geometry as rg
from fig_carbon import C_CARB, C_FOAM, C_LEDGE, C_MYLAR, C_RING, frame_parts, outer_arc_profile
from fig_frame_corners import C_DIM, C_EXT, C_EXT_EC, C_FRAME, C_FRAME_EC, C_OPEN, C_PAD, callout, dim, poly_patch
from fig_frame_section import straight_profile

FIG = os.path.join(rg.OUT, "figures")
WIN = (576, 608, -6, 21)
C_FOAM_EC, C_PAD_EC = "#3d6b1a", "#8a6a00"


def base(ax, mesh=True):
    """Frame corner (top view), B2 pad, mesh and the mesh-cut lines."""
    wall, ledge, _ = frame_parts()
    ax.add_patch(poly_patch(wall, fc=C_FRAME, ec=C_FRAME_EC, lw=.6, zorder=1))
    ax.add_patch(poly_patch(ledge, fc=C_LEDGE, ec=C_FRAME_EC, lw=.4, zorder=1))
    if mesh:
        ax.add_patch(poly_patch(rg.mesh_area(), fc="#d9dde3", ec="0.55", lw=.5, hatch="....", zorder=1.5))
    x, y, s = rg.B2_PAD
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc=C_PAD, ec=C_PAD_EC, lw=.6, zorder=2))
    c = rg.B2_CUT
    ax.plot([c[0], c[0], 620], [-10, c[3], c[3]], color=C_OPEN, lw=1.4, ls="--", zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(WIN[0], WIN[1])
    ax.set_ylim(WIN[2], WIN[3])
    ax.grid(lw=.25, alpha=.5)
    ax.tick_params(labelsize=7)
    ax.set_xlabel("x [mm]", fontsize=8)


def draw_block(ax, foam=True, alpha=1.0):
    ax.add_patch(poly_patch(rg.foam_block(), fc=C_EXT, ec=C_EXT_EC, lw=1.2, alpha=alpha, zorder=3))
    ax.add_patch(poly_patch(rg.foam_slot(), fc="white", ec=C_EXT_EC, lw=1.0, zorder=3))
    x, y, s = rg.B2_PAD
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc=C_PAD, ec=C_PAD_EC, lw=.6, zorder=3.5))
    if foam:
        ax.add_patch(poly_patch(rg.foam_square(), fc=C_FOAM, ec=C_FOAM_EC, lw=.8, hatch="xx", alpha=.55, zorder=4))


# ---------------------------------------------------------------- 1. frame, top view
def frame_top_view():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 7.6))
    base(a0)
    base(a1)
    draw_block(a1)
    a0.set_title("NOW (frame, lower level z 0–4)", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW – lower level filled in the corner, slot for the foam", fontsize=13, weight="bold",
                 loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (590.5, 10), (578, 18.5), "B2 drift pad 3 × 3 (PCB)")
    callout(a0, (585.5, 6), (577, 1), "mesh cut: whole corner cleared\n(no mesh for x ≥ 585.5, y ≤ 15)", color=C_OPEN)
    callout(a0, (601.5, 8), (601.5, 16), "frame step\nat z = 4\n(mylar on it)")
    callout(a0, (604.5, -4.5), (589, -4.5), "frame upper wall (z 4–8)")
    callout(a0, (593, 5), (599.5, -1.5), "empty corner,\nno mesh, no use", color="0.4")

    s = rg.foam_slot().bounds
    b = rg.foam_block().bounds
    # block outline
    dim(a1, (b[0], b[3]), (600.0, b[3]), (0, 2.6), f"{600.0 - b[0]:.1f} (to the lower wall)", fs=8.5)
    dim(a1, (b[0], 0), (b[0], b[3]), (-3.4, 0), f"{b[3]:.1f}", fs=8.5)
    # slot
    dim(a1, (s[0], s[3]), (s[2], s[3]), (0, 1.2), f"{s[2] - s[0]:.1f}", fs=8)
    dim(a1, (s[2], s[1]), (s[2], s[3]), (1.3, 0), f"{s[3] - s[1]:.1f}", fs=8)
    dim(a1, (b[0], 9.0), (s[0], 9.0), (0, 0), f"{s[0] - b[0]:.1f}", fs=8, color=C_OPEN)
    dim(a1, (589.3, s[3]), (589.3, b[3]), (0, 0), f"{b[3] - s[3]:.1f}", fs=8, color=C_OPEN)
    dim(a1, (594.5, 0), (594.5, s[1]), (0, 0), f"{s[1]:.1f}", fs=8)
    callout(a1, (s[0] + .3, s[1] + .3), (577, 2.5),
            f"slot {s[2] - s[0]:.1f} × {s[3] - s[1]:.1f}, through the block (z 0–4),\n"
            f"centred on the pad ({rg.B2_PAD[0]:g}, {rg.B2_PAD[1]:g}); corners R{rg.SLOT_R:g}", color=C_EXT_EC)
    callout(a1, (592, 9), (599.8, 12.0), f"foam {rg.FOAM_SIDE:g} × {rg.FOAM_SIDE:g}\n(not frame)", color=C_FOAM_EC)
    callout(a1, (596, 3), (598.5, -4.3), "NEW frame material, lower level only:\nz 0 → 4, flush with the step",
            color=C_EXT_EC)
    callout(a1, (586.5, 14.2), (577.5, 19.3), "block edges = mesh cut lines (x = 585.5, y = 15)", color=C_OPEN)
    h = [Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: frame material, z 0–4 (one piece with the frame)"),
         Patch(fc="white", ec=C_EXT_EC, label="NEW: slot (through)"),
         Patch(fc=C_FOAM, ec=C_FOAM_EC, hatch="xx", label="conductive foam in the slot"),
         Patch(fc=C_PAD, ec=C_PAD_EC, label="B2 drift pad (PCB)"),
         Patch(fc="#d9dde3", ec="0.55", hatch="....", label="mesh"),
         Line2D([], [], color=C_OPEN, ls="--", label="mesh cut lines"),
         Patch(fc=C_LEDGE, ec=C_FRAME_EC, label="frame step (z = 4)"),
         Patch(fc=C_FRAME, ec=C_FRAME_EC, label="frame upper wall")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("Drift frame – foam slot at the B2 drift-pad corner (top view, PCB coordinates)", fontsize=14, y=.98)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    fig.savefig(os.path.join(FIG, "foam_slot_1_frame_B2.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 2. 3D view (schematic, straight walls)
def cuboid(x0, y0, z0, x1, y1, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return [v[i] for i in f]


class Scene:
    """All faces in one collection, so matplotlib depth-sorts them face by face."""
    def __init__(self):
        self.faces, self.fc, self.ec = [], [], []

    def add(self, boxes, fc, ec="k", alpha=1.0):
        from matplotlib.colors import to_rgba
        for b in boxes:
            for f in cuboid(*b):
                self.faces.append(f)
                self.fc.append(to_rgba(fc, alpha))
                self.ec.append(to_rgba(ec, min(1.0, alpha + .3)))

    def draw(self, ax):
        ax.add_collection3d(Poly3DCollection(self.faces, facecolors=self.fc, edgecolors=self.ec, linewidths=.5))


X0, Y1 = 576.0, 22.0


def frame_boxes():
    """Corner of the frame, straight walls (the outer arc is r 600: 0.4 mm off at y = 22)."""
    z = rg.STEP_Z
    return [(X0, -10, 0, 600, 0, z), (600, -10, 0, 615, Y1, z),               # lower level (to the walls)
            (X0, -10, z, 603, -3, rg.FRAME_H), (603, -10, z, 615, Y1, rg.FRAME_H)]   # upper wall


def block_boxes():
    (b0, _, _, b3), (s0, s1, s2, s3) = rg.foam_block().bounds, rg.foam_slot().bounds
    z = rg.STEP_Z
    return [(b0, 0, 0, s0, b3, z), (s2, 0, 0, 600, b3, z), (s0, 0, 0, s2, s1, z), (s0, s3, 0, s2, b3, z)]


def foam_box(h):
    f = rg.foam_square().bounds
    return (f[0], f[1], 0.05, f[2], f[3], h)


def view3d(ax, exploded):
    S = Scene()
    x, y, s = rg.B2_PAD
    S.add([(X0, -10, -1.6, 615, Y1, 0)], "#a5c9a7", ec="#5b8a5d", alpha=.5)            # PCB
    S.add([(x - s / 2, y - s / 2, 0, x + s / 2, y + s / 2, 0.05)], C_PAD, ec=C_PAD_EC)
    S.add(frame_boxes(), C_FRAME, ec=C_FRAME_EC)
    S.add(block_boxes(), C_EXT, ec=C_EXT_EC)
    n = rg.foam_sheets(rg.STEP_Z)[0]
    if exploded:
        S.add([foam_box(n * rg.FOAM_SHEET)], C_FOAM, ec=C_FOAM_EC)
        dz = 15.0
        z0, z1 = rg.STEP_Z + dz, rg.STEP_Z + dz + rg.CARBON_T_NEW
        S.add([(X0, -2.5, z0 - .1, 602.5, Y1, z0)], C_MYLAR, ec=C_MYLAR, alpha=.3)
        S.add([(X0, -2.5, z0, 602.5, 2.5, z1), (597.5, 2.5, z0, 602.5, Y1, z1)], C_CARB, ec="k")
        S.add([(rg.B2_CUT[0], 2.5, z0, 597.5, rg.B2_CUT[3], z1)], C_EXT, ec=C_EXT_EC, alpha=.85)
    S.draw(ax)
    ax.set_xlim(X0, 615)
    ax.set_ylim(-10, Y1)
    ax.set_zlim(-2, 22 if exploded else 9)
    ax.set_box_aspect((39, 32, 24 if exploded else 11))
    ax.view_init(elev=38, azim=128)
    ax.set_xlabel("x [mm]", fontsize=8)
    ax.set_ylabel("y [mm]", fontsize=8)
    ax.set_zlabel("z", fontsize=8)
    ax.tick_params(labelsize=6)


def three_d():
    fig = plt.figure(figsize=(16, 8))
    a0 = fig.add_subplot(1, 2, 1, projection="3d")
    a1 = fig.add_subplot(1, 2, 2, projection="3d")
    view3d(a0, False)
    view3d(a1, True)
    a0.set_title("drift frame NEW, B2 corner seen from the active area: empty slot, pad at the bottom", fontsize=11.5, loc="left",
                 weight="bold")
    a1.set_title("exploded: mylar + carbon lifted, foam before compression", fontsize=11.5, loc="left",
                 weight="bold")
    n = rg.foam_sheets(rg.STEP_Z)[0]
    fig.text(.04, .075, "orange = NEW frame material at the lower level (z 0–4), flush with the mylar step;\n"
             f"slot {rg.foam_slot().bounds[2] - rg.foam_slot().bounds[0]:.1f} × 4.4 through it, open onto the B2 pad", fontsize=9.5, color=C_EXT_EC)
    fig.text(.53, .075, f"foam {n} × 1 mm sheets stands {n * rg.FOAM_SHEET - rg.STEP_Z:g} mm above the block; "
             "the carbon (strip + flap,\nflap = block outline) with the mylar glued under it squeezes it to 4 mm "
             "and rests on the block", fontsize=9.5, color="0.15")
    h = [Patch(fc=C_FRAME, ec=C_FRAME_EC, label="drift frame (schematic)"),
         Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: frame block with slot / carbon flap"),
         Patch(fc=C_FOAM, ec=C_FOAM_EC, label="conductive foam"),
         Patch(fc=C_CARB, ec="k", label="carbon strip"),
         Patch(fc=C_MYLAR, alpha=.4, label="mylar"),
         Patch(fc=C_PAD, ec=C_PAD_EC, label="B2 drift pad"),
         Patch(fc="#a5c9a7", alpha=.6, label="PCB")]
    fig.legend(handles=h, loc="lower center", ncol=7, fontsize=8.5, frameon=False)
    fig.suptitle("Foam slot at the B2 corner – 3D view (schematic: walls drawn straight, O-ring groove not shown)",
                 fontsize=13, y=.985)
    fig.subplots_adjust(left=0, right=1, top=.9, bottom=.13, wspace=0)
    fig.savefig(os.path.join(FIG, "foam_slot_2_3d.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 3. sections A-A (y = 10) and B-B (x = 590.5)
def section(ax, along_x):
    gap = rg.STEP_Z
    n, comp = rg.foam_sheets(gap)
    f, s = rg.foam_square().bounds, rg.foam_slot().bounds
    if along_x:                       # A-A: x across, wall = outer arc at x 600-615
        wall = outer_arc_profile()
        lo, hi, w_in = 576, 618, 600.0
        f0, f1, s0, s1, b0, b1 = f[0], f[2], s[0], s[2], rg.B2_CUT[0], 600.0
        c0, c1 = 597.5, 602.5         # strip
        pad = rg.B2_PAD[0]
    else:                             # B-B: y across, wall = straight side at y -10..0
        from shapely import affinity
        wall = straight_profile()     # t = y
        lo, hi, w_in = -12, 24, 0.0
        f0, f1, s0, s1, b0, b1 = f[1], f[3], s[1], s[3], 0.0, rg.B2_CUT[3]
        c0, c1 = -2.5, 2.5
        pad = rg.B2_PAD[1]
    ax.add_patch(poly_patch(wall, fc=C_FRAME, ec=C_FRAME_EC, lw=.8, zorder=2))
    ax.add_patch(Rectangle((lo, -1.6), hi - lo, 1.6, fc="#2e7d32", alpha=.25, ec="none", zorder=1))
    ax.text(lo + 1, -1.05, "PCB", fontsize=8, color="#1b4d1e")
    ax.add_patch(Rectangle((pad - 1.5, 0), 3, 0.12, fc=C_PAD, ec=C_PAD_EC, lw=.5, zorder=4))
    # new block, cut by the slot
    for a, b in ((b0, s0), (s1, b1)):
        ax.add_patch(Rectangle((a, 0), b - a, gap, fc=C_EXT, ec=C_EXT_EC, lw=1.0, zorder=3, hatch="///"))
    # mesh outside the cleared corner
    m_end = rg.B2_CUT[0] if along_x else rg.B2_CUT[3]
    if along_x:
        ax.plot([lo, m_end], [0.13, 0.13], color="0.2", lw=1.2, ls=(0, (1, 1)), zorder=3)
    else:
        ax.plot([m_end, hi], [0.13, 0.13], color="0.2", lw=1.2, ls=(0, (1, 1)), zorder=3)
    # foam
    ax.add_patch(Rectangle((f0, 0.12), f1 - f0, gap - 0.12, fc=C_FOAM, ec=C_FOAM_EC, lw=.8, hatch="xx", zorder=4))
    for k in range(1, n):
        zk = 0.12 + k * (gap - 0.12) / n
        ax.plot([f0, f1], [zk, zk], color=C_FOAM_EC, lw=.5, zorder=5)
    # mylar + carbon (strip + flap), both resting on the block
    my = [lo, w_in + 2.5] if along_x else [w_in - 2.5, hi]
    ax.plot(my, [gap, gap], color=C_MYLAR, lw=2.2, zorder=6)
    ax.add_patch(Rectangle((c0, gap), c1 - c0, rg.CARBON_T_NEW, fc=C_CARB, ec="black", lw=.6, zorder=5))
    if along_x:
        ax.add_patch(Rectangle((b0, gap), c0 - b0, rg.CARBON_T_NEW, fc=C_EXT, ec=C_EXT_EC, lw=1.0, zorder=5))
    else:
        ax.add_patch(Rectangle((c1, gap), b1 - c1, rg.CARBON_T_NEW, fc=C_EXT, ec=C_EXT_EC, lw=1.0, zorder=5))
    # dimensions
    dim(ax, (s0, 0), (s1, 0), (0, -2.4), f"slot {s1 - s0:.1f}", fs=8)
    dim(ax, (b0, 0), (b1, 0), (0, -3.6), f"block {abs(b1 - b0):.1f}", fs=8)
    xr = (b1 + 1.3) if along_x else (b0 - 1.3)
    ax.annotate(f"foam {n} × 1 mm → {gap:g} mm ({comp * 100:.0f} %)", ((f0 + f1) / 2, gap * .6),
                (lo + 1 if along_x else hi - 1, gap + 3.4), fontsize=8.5, color=C_FOAM_EC,
                arrowprops=dict(arrowstyle="->", color=C_FOAM_EC, lw=.7))
    ax.annotate("NEW frame block (z 0–4)\nfilled, flush with the step", (s1 + .8 if along_x else b1 - .8, 2.0),
                (hi - 14, gap + 4.6) if along_x else (b1 + 2.5, gap + 4.6), fontsize=8, color=C_EXT_EC,
                arrowprops=dict(arrowstyle="->", color=C_EXT_EC, lw=.7))
    ax.annotate("carbon flap rests on the block\n(mylar clamped in between)", ((b0 + c0) / 2 if along_x else (c1 + b1) / 2,
                gap + rg.CARBON_T_NEW), ((b0 + c0) / 2 - 4 if along_x else (c1 + b1) / 2 - 2, gap + 6.4),
                fontsize=8, color=C_EXT_EC, arrowprops=dict(arrowstyle="->", color=C_EXT_EC, lw=.7))
    ax.set_xlim(lo, hi)
    ax.set_ylim(-5, gap + 8)
    ax.set_aspect("equal")
    ax.grid(lw=.25, alpha=.4)
    ax.tick_params(labelsize=7)
    ax.set_ylabel("z [mm]", fontsize=8)
    if along_x:
        ax.set_xlabel("x [mm]", fontsize=8)
        ax.set_title(f"A–A: along y = {rg.B2_PAD[1]:g} (through the pad), towards the outer arc", fontsize=11,
                     loc="left", weight="bold")
    else:
        ax.set_xlabel("y [mm]", fontsize=8)
        ax.set_title(f"B–B: along x = {rg.B2_PAD[0]:g} (through the pad), towards the straight side", fontsize=11,
                     loc="left", weight="bold")
        ax.invert_xaxis()


def sections():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(17, 5.4))
    section(a0, True)
    section(a1, False)
    n5, c5 = rg.foam_sheets(rg.STEP_Z_5MM)
    fig.suptitle("Foam slot – cross-sections, 4 mm drift gap (5 mm placeholder: block 5 mm high, "
                 f"{n5} sheets, {c5 * 100:.0f} %). Frame drawn from the STEP outline.", fontsize=12, y=.985)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(FIG, "foam_slot_3_section.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 4. carbon flap matching the block
def carbon_flap():
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 7.4))
    strip = rg.carbon_strip()
    for ax, new in ((a0, False), (a1, True)):
        base(ax)
        if new:
            draw_block(ax, alpha=.35)
            flap = rg.carbon_flap_slot().difference(strip)
        else:
            ax.add_patch(poly_patch(rg.guide_ring(), fc=C_RING, ec="#2c5f8a", lw=.8, alpha=.85, zorder=3))
            ax.add_patch(poly_patch(rg.foam_square(), fc=C_FOAM, ec=C_FOAM_EC, lw=.8, hatch="xx", zorder=3))
            flap = rg.carbon_flap().difference(strip)
        ax.add_patch(poly_patch(strip, fc=C_CARB, ec="black", lw=.6, alpha=.85, zorder=5))
        ax.add_patch(poly_patch(flap, fc=C_EXT, ec=C_EXT_EC, lw=1.2, alpha=.45, zorder=6))
    blk = rg.foam_block().union(rg.foam_slot())
    a1.add_patch(poly_patch(blk, fc="none", ec=C_DIM, lw=1.6, ls=(0, (4, 2)), zorder=7))
    a0.set_title("BEFORE (proposal of 20 Oct): flap hanging over a guide ring", fontsize=12, weight="bold", loc="left")
    a1.set_title("NEW: flap = outline of the frame block", fontsize=12, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (rg.guide_ring().bounds[0] + .4, 10), (577, 18.5), "guide ring glued on the PCB\n(dropped)", color="#2c5f8a")
    callout(a0, (590, 3.5), (578, -4.3), "flap supported only by the strip:\nthe foam pushes it up", color=C_EXT_EC)
    fx0, fy0, fx1, fy1 = rg.carbon_flap_slot().difference(strip).bounds
    dim(a1, (fx0, fy1), (597.5, fy1), (0, 2.0), f"{597.5 - fx0:.1f}")
    dim(a1, (fx0, fy0), (fx0, fy1), (-2.6, 0), f"{fy1 - fy0:.1f}")
    callout(a1, (586, 7), (577, 1.0), "block outline (dashed) = flap outline:\nx = 585.5 and y = 15, out to the strip",
            color=C_DIM)
    callout(a1, (593, 4), (589, -4.4), "flap rests on the block everywhere:\nthe foam is held by the slot, no ring",
            color=C_EXT_EC)
    callout(a1, (601.5, 8), (601, 16), "strip unchanged\n(5 mm, 2 mm thick)")
    h = [Patch(fc=C_CARB, ec="black", label="carbon strip"),
         Patch(fc=C_EXT, ec=C_EXT_EC, alpha=.6, label="carbon flap (one piece with the strip, 2 mm)"),
         Line2D([], [], color=C_DIM, ls="--", lw=1.6, label="NEW frame block + slot underneath"),
         Patch(fc=C_FOAM, ec=C_FOAM_EC, hatch="xx", label="conductive foam"),
         Patch(fc=C_RING, ec="#2c5f8a", label="guide ring (before)"),
         Patch(fc=C_PAD, ec=C_PAD_EC, label="B2 drift pad"),
         Line2D([], [], color=C_OPEN, ls="--", label="mesh cut lines")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("Carbon drift piece – flap matching the frame foam block (top view)", fontsize=14, y=.98)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    fig.savefig(os.path.join(FIG, "foam_slot_4_carbon_flap.png"), dpi=130)
    plt.close(fig)


def main():
    frame_top_view()
    three_d()
    sections()
    carbon_flap()
    print("written foam_slot_1_frame_B2.png, foam_slot_2_3d.png, foam_slot_3_section.png, foam_slot_4_carbon_flap.png")


if __name__ == "__main__":
    main()
