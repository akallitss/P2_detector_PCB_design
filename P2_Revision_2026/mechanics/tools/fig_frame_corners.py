#!/usr/bin/env python3
"""
Drift frame, change at the two outer corners (A = bottom right, B = top):
NOW (current frame) next to NEW (extension + HV opening + new holes), with dimensions.

Writes ../figures/frame_A_corner.png and ../figures/frame_B_corner.png
Run with  (ulimit -v 3000000; python3 fig_frame_corners.py)
"""
import gc
import os
import pickle

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, PathPatch, Rectangle
from matplotlib.path import Path
from shapely.geometry import box

import rev_geometry as rg

FIG = os.path.join(rg.OUT, "figures")
CACHE = os.path.join(rg.ROOT, "P2_Revision_2026", "drift_contact", "data", "cache.pkl")

C_FRAME, C_FRAME_EC = "#c9cdd4", "#5b6170"
C_EXT, C_EXT_EC = "#f4a742", "#b8650a"
C_WIDE = "#e3742b"
C_OPEN = "#d62728"
C_PAD = "#d4a017"
C_DIM = "#1a3d8f"


def pcb_edges():
    from gerbonara.graphic_primitives import Arc, Line
    C = pickle.load(open(CACHE, "rb"))
    segs = []
    for p in C["gerb"]["Edge_Cuts"]:
        if isinstance(p, Line):
            segs.append([(p.x1, p.y1), (p.x2, p.y2)])
        elif isinstance(p, Arc):
            segs.append(rg.arc_points(p))
    del C
    gc.collect()
    return segs


def poly_patch(geom, **kw):
    """shapely (Multi)Polygon -> one PathPatch, holes included."""
    if geom.is_empty:
        return Rectangle((0, 0), 0, 0, visible=False)
    verts, codes = [], []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon":
            continue
        for ring in [g.exterior, *g.interiors]:
            xy = np.asarray(ring.coords)
            verts += xy.tolist()
            codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
    return PathPatch(Path(verts, codes), **kw)


def dim(ax, p1, p2, off, text, fs=9, color=C_DIM, tpos=0.5, zorder=10):
    """Dimension line between p1 and p2, drawn shifted by the vector off."""
    p1, p2, off = map(np.asarray, (p1, p2, off))
    a, b = p1 + off, p2 + off
    n = off / (np.linalg.norm(off) + 1e-9)
    for p, q in ((p1, a), (p2, b)):
        ax.plot(*np.c_[p + 0.3 * n, q + 0.8 * n], color=color, lw=.6, zorder=zorder)
    ax.annotate("", b, a, arrowprops=dict(arrowstyle="<|-|>", color=color, lw=.9, shrinkA=0, shrinkB=0,
                                          mutation_scale=9), zorder=zorder)
    m = a + tpos * (b - a)
    ang = np.degrees(np.arctan2(*(b - a)[::-1]))
    if ang > 90 or ang < -90:
        ang += 180
    ax.text(*(m + 1.2 * n), text, color=color, fontsize=fs, ha="center", va="center", rotation=ang,
            rotation_mode="anchor", bbox=dict(fc="white", ec="none", pad=.5, alpha=.9), zorder=zorder)


def callout(ax, xy, xyt, text, color="0.15", fs=8.5):
    ax.annotate(text, xy, xyt, fontsize=fs, color=color, zorder=20,
                bbox=dict(boxstyle="round,pad=.3", fc="white", ec=color, lw=.6, alpha=.95),
                arrowprops=dict(arrowstyle="->", color=color, lw=.8))


def base(ax, G, edges, win, new):
    clip = box(win[0] - 5, win[2] - 5, win[1] + 5, win[3] + 5)
    frame = G["outer"].difference(G["window"])
    if new:
        screws = [rg.Point(x, y).buffer(rg.SCREW_D / 2, 64) for _, x, y, _ in rg.new_frame_holes()[0]]
        for h in screws:
            frame = frame.difference(h)
        band = G["band"]
        for h in screws:
            band = band.difference(h)
        ax.add_patch(poly_patch(band.intersection(clip), fc=C_WIDE, ec=C_EXT_EC, lw=1.0, zorder=3))
        ax.plot(*np.asarray(rg.pcb_outline().exterior.coords).T, color="0.25", lw=.9, ls="--", zorder=1)
    else:
        for h in G["fholes"]:
            frame = frame.difference(h)
        for s in edges:
            ax.plot(*np.asarray(s).T, color="0.25", lw=.6, zorder=1)
    ax.add_patch(poly_patch(frame.intersection(clip), fc=C_FRAME, ec=C_FRAME_EC, lw=.8, zorder=2))
    for k in ("A", "B"):
        for P in G["pads"][k]:
            ax.add_patch(poly_patch(P, fc=C_PAD, ec="#8a6a00", lw=.4, zorder=6, alpha=.9))
    if new:
        ext = G["ext"].intersection(clip)
        for h in G["holes"]:
            ext = ext.difference(rg.Point(h[0], h[1]).buffer(h[2] / 2, 64))
        ax.add_patch(poly_patch(ext, fc=C_EXT, ec=C_EXT_EC, lw=1.0, zorder=3))
        op = G["ext_full"].intersection(G["op"]["A"].union(G["op"]["B"])).intersection(clip)
        ax.add_patch(poly_patch(op, fc="none", ec=C_OPEN, lw=1.6, ls="--", hatch="////", zorder=4))
        for x, y, d in G["holes"]:
            ax.add_patch(Circle((x, y), d / 2, fc="white", ec="black", lw=1.0, zorder=7))
    # PCB holes that end up inside an opening (no action on the frame)
    for k in (4, 5):
        for x, y in G["H"][k]:
            if G["op"]["A"].contains(rg.Point(x, y)) or G["op"]["B"].contains(rg.Point(x, y)):
                ax.add_patch(Circle((x, y), G["D"][k] / 2, fc="none", ec="0.45", lw=.7, ls=":", zorder=7))
    ax.set_xlim(win[0], win[1])
    ax.set_ylim(win[2], win[3])
    ax.set_aspect("equal")
    ax.grid(lw=.25, alpha=.5)
    ax.tick_params(labelsize=7)
    ax.set_xlabel("x [mm]", fontsize=8)


def key_plan(fig, rect, G, win):
    ax = fig.add_axes(rect)
    frame = G["outer"].difference(G["window"])
    ax.add_patch(poly_patch(frame, fc=C_FRAME, ec=C_FRAME_EC, lw=.4))
    ax.add_patch(poly_patch(G["ext"], fc=C_EXT, ec="none"))
    ax.add_patch(poly_patch(G["band"], fc=C_WIDE, ec="none"))
    ax.add_patch(Rectangle((win[0], win[2]), win[1] - win[0], win[3] - win[2], fc="none", ec=C_OPEN, lw=1.4))
    ax.set_xlim(20, 670)
    ax.set_ylim(-30, 570)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("where", fontsize=7, pad=1)


def legend(fig):
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    h = [Patch(fc=C_FRAME, ec=C_FRAME_EC, label="existing frame (top face)"),
         Patch(fc=C_EXT, ec=C_EXT_EC, label="NEW: extension to the PCB edge, 8 mm high"),
         Patch(fc="none", ec=C_OPEN, ls="--", hatch="////", label="NEW: HV opening, no material"),
         Patch(fc=C_PAD, ec="#8a6a00", label="PCB HV solder pads (for reference)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="black", label="NEW: through hole in the extension"),
         Line2D([], [], marker="o", ls="none", mfc="none", mec="0.45", label="PCB hole inside the opening: nothing to do"),
         Line2D([], [], color="0.25", lw=.8, label="PCB outline (NOW)"),
         Line2D([], [], color="0.25", lw=.9, ls="--", label="PCB edge (unchanged)")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=8, frameon=False)


def fig_A(G, edges):
    win = (588, 660, -24, 52)
    op = G["op"]
    u0, u1 = op["A_u"]
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 8.2))
    base(a0, G, edges, win, new=False)
    base(a1, G, edges, win, new=True)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    SLOT = (600.0, 2.3, 615.0, 4.7)                 # hidden in the wall, z 2.6-3.8 (STEP)
    for ax in (a0, a1):
        ax.add_patch(Rectangle(SLOT[:2], SLOT[2] - SLOT[0], SLOT[3] - SLOT[1], fc="none", ec="0.2", lw=1.0, ls="--", zorder=8))
    a1.plot([SLOT[0], SLOT[2]], [SLOT[1], SLOT[3]], color=C_OPEN, lw=1.6, zorder=9)
    a1.plot([SLOT[0], SLOT[2]], [SLOT[3], SLOT[1]], color=C_OPEN, lw=1.6, zorder=9)
    callout(a0, (607, 3.5), (592, 22), "old drift-wire slot\n(inside the wall, z 2.6–3.8)")
    callout(a0, (628, 12), (636, -12), "HV solder pads\nGND / M / D / GND")
    callout(a0, (640, 30), (632, 45), "today the frame stops at r = 615;\nthe PCB is unsupported out here")
    # dimensions along the chamfer (drawn just outside the PCB edge)
    out = -rg.CH_N * 4.5
    dim(a1, rg.CH0, rg.from_uv(u0, 0), out, f"{u0:.1f}")
    dim(a1, rg.from_uv(u0, 0), rg.from_uv(u1, 0), out, f"{u1 - u0:.1f}")
    a1.plot(*rg.CH0, "o", ms=4, color=C_DIM, zorder=9)
    callout(a1, rg.CH0, (626, -21), f"reference: start of the chamfer\n({rg.CH0[0]:.1f}, {rg.CH0[1]:.1f})", color=C_DIM)
    callout(a1, (600, -10), (589, -21), "frame flush with the PCB edge\n(PCB outline unchanged)", color=C_DIM)
    callout(a1, rg.from_uv((u0 + u1) / 2, 12), (589, 30.5),
            f"HV opening: {u1 - u0:.1f} mm along the chamfer,\nfrom the PCB edge down to the frame wall (r = 615)\n"
            f"(pads + {rg.HV_MARGIN:g} mm on each side)", color=C_OPEN)
    callout(a1, (607, 3.5), (590, 12), "REMOVE the old wire slot:\nfill it with frame material\n(not used in this version)", color=C_OPEN)
    for x, y, d in G["holes"]:
        if win[0] < x < win[1] and win[2] < y < win[3]:
            callout(a1, (x, y), (619, 51.5) if d > 3 else (589, 45), f"Ø{d:g} at ({x:.1f}, {y:.1f})")
    for no, x, y, e in rg.new_frame_holes()[0]:
        if win[0] < x < win[1] and win[2] < y < win[3] and e != "corner":
            callout(a1, (x, y), (626, 33), f"frame screw hole {no}, Ø{rg.SCREW_D:g}\n(today's position, r = {rg.R_OUT:g})")
    callout(a1, (645, 47), (648, 22), "outer edge =\nPCB edge (R650)", color=C_EXT_EC)
    key_plan(fig, [0.005, 0.70, 0.11, 0.23], G, win)
    legend(fig)
    fig.suptitle("Drift frame – corner A (bottom right): extension + HV opening", fontsize=14, y=.985)
    fig.tight_layout(rect=(0.08, 0.06, 1, 0.96))
    fig.savefig(os.path.join(FIG, "frame_A_corner.png"), dpi=130)
    plt.close(fig)


def fig_B(G, edges):
    win = (283, 372, 505, 552)
    op = G["op"]
    xb = op["B_x"]
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 6.8))
    base(a0, G, edges, win, new=False)
    base(a1, G, edges, win, new=True)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    gx, gy = G["gas"]
    for ax in (a0, a1):
        ax.annotate("", (gx + 2.5, gy + 4.3), (gx - 1, gy - 1.7),
                    arrowprops=dict(arrowstyle="-|>", color="#2a7f2a", lw=2, mutation_scale=14), zorder=12)
    callout(a0, (gx, gy), (291, 545), "gas inlet Ø4.4\n(leaves the frame here)", color="#2a7f2a")
    callout(a0, (324, 536), (338, 547), "HV solder pads")
    callout(a0, (350, 530), (345, 512), "today the frame stops at r = 615;\nthe PCB is unsupported out here")
    # opening edge: vertical line at x = xb, dimension from the pad group and to the PCB corner
    pad_x1 = op["B_pad_x"][1]
    dim(a1, (pad_x1, 541.5), (xb, 541.5), (0, 4.5), f"{rg.HV_MARGIN:g}", tpos=.5)
    tc = rg.top_corner(rg.SIDE_NEW)
    dim(a1, tc, (xb, 540), (0, 9.5), f"{xb - tc[0]:.1f}")
    a1.plot(*tc, "o", ms=4, color=C_DIM, zorder=9)
    callout(a1, tc, (289, 529), f"reference: PCB top corner\n({tc[0]:.1f}, {tc[1]:.1f})", color=C_DIM)
    callout(a1, (xb, 522), (340, 512), f"HV opening edge: straight cut at x = {xb:.1f}\n"
            f"(pads + {rg.HV_MARGIN:g} mm); everything left of it stays open,\nso the gas inlet stays reachable",
            color=C_OPEN)
    for x, y, d in G["holes"]:
        if win[0] < x < win[1] and win[2] < y < win[3]:
            callout(a1, (x, y), (x + 4, y - 11), f"Ø{d:g} at ({x:.1f}, {y:.1f})")
    key_plan(fig, [0.005, 0.66, 0.11, 0.26], G, win)
    legend(fig)
    fig.suptitle("Drift frame – corner B (top): extension + HV opening (also clears the gas inlet)", fontsize=14, y=.985)
    fig.tight_layout(rect=(0.08, 0.07, 1, 0.95))
    fig.savefig(os.path.join(FIG, "frame_B_corner.png"), dpi=130)
    plt.close(fig)


def main():
    G = rg.build()
    edges = pcb_edges()
    fig_A(G, edges)
    fig_B(G, edges)
    print("written frame_A_corner.png, frame_B_corner.png in", FIG)


if __name__ == "__main__":
    main()
