#!/usr/bin/env python3
"""
Drift frame cross-sections NOW vs NEW for the three kinds of side:
straight side (STL section at x = 350, cache of drift_contact_study.py), outer arc and
inner arc (STEP radial section at 27 deg, export_radial_section.FCpy).
NEW: +1.5 mm outward on the straight sides and the inner arc (overhangs the unchanged PCB); extension on
the outer arc; hole positions.

Coordinate across a side: t = 0 at the wall facing the active area, negative towards the outside.
Writes ../figures/frame_side_section.png
"""
import json
import os
import pickle

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

import rev_geometry as rg
from fig_frame_corners import C_DIM, C_EXT, C_EXT_EC, C_FRAME, C_FRAME_EC, C_WIDE, dim, poly_patch

CACHE = os.path.join(rg.ROOT, "P2_Revision_2026", "drift_contact", "data", "cache.pkl")
RADIAL = os.path.join(rg.OUT, "data", "frame_section_r27.json")
FIG = os.path.join(rg.OUT, "figures")
XLIM = (-38, 16)


def straight_profile():
    segs = np.round(np.asarray(pickle.load(open(CACHE, "rb"))["sec_x350"]), 3)   # snap so the ends join
    lines = unary_union([LineString(s) for s in segs if np.ptp(s, 0).max() > 1e-6])
    return unary_union([P for P in polygonize(lines) if P.area > 1]).buffer(0.01).buffer(-0.01)


def arc_profiles():
    """Outer arc (r 600-615) and inner arc (r 95-110), mapped to t."""
    loops = [np.array(w) for w in json.load(open(RADIAL))]
    out, inn = [], []
    for L in loops:
        (out if L[:, 0].mean() > 300 else inn).append(L)
    def to_poly(Ls, f):
        polys = sorted((Polygon(np.c_[f(L[:, 0]), L[:, 1]]).buffer(0) for L in Ls), key=lambda P: -P.area)
        P = polys[0]
        for q in polys[1:]:
            P = P.difference(q)                    # internal gas channel
        return P
    return to_poly(out, lambda r: rg.R_OUT_WALL - r), to_poly(inn, lambda r: r - rg.R_IN_WALL)


def features(P, W):
    """O-ring groove (open to z = 0) and internal channel(s) of a profile of width W."""
    g = box(-W, 0, 0, rg.FRAME_H).difference(P)
    parts = [q for q in getattr(g, "geoms", [g]) if q.area > 0.5]
    groove = [q for q in parts if q.bounds[1] < 0.05 and q.bounds[3] < 3]
    chan = [Polygon(i) for i in getattr(P, "interiors", [])]
    return unary_union(groove), unary_union(chan) if chan else None


def panel(ax, P, W, t_hole, d_hole, new, ext=False, wide=False):
    """One side in section. t_hole / d_hole: screw hole position and Ø. wide: the frame grows
    outward by rg.OVERHANG past the (unchanged) PCB edge."""
    ax.add_patch(poly_patch(P, fc=C_FRAME, ec=C_FRAME_EC, lw=1.0, zorder=2))
    if new and wide:
        o = rg.OVERHANG
        ax.add_patch(poly_patch(box(-W - o, 0, -W, rg.FRAME_H), fc=C_WIDE, ec=C_EXT_EC, lw=.8, zorder=2))
        ax.plot([-W] * 2, [-0.5, rg.FRAME_H], color=C_FRAME_EC, lw=.8, ls=":", zorder=3)
        dim(ax, (-W - o, 0), (-W, 0), (0, -2.6), f"{o:g}", fs=8, color=C_EXT_EC)
        ax.annotate(f"NEW: +{o:g} mm outward,\noverhangs the PCB edge", (-W - o / 2, 6.0), (-31, 6.0), fontsize=7.5,
                    color=C_EXT_EC, va="center", arrowprops=dict(arrowstyle="->", color=C_EXT_EC, lw=.7))
        dim(ax, (-W - o, rg.FRAME_H), (0, rg.FRAME_H), (0, 2.8), f"{W + o:g}")
    if new and ext:
        x0 = XLIM[0] + 1
        ax.add_patch(poly_patch(box(x0, 0, -W, rg.FRAME_H), fc=C_EXT, ec=C_EXT_EC, lw=.8, zorder=2, alpha=.8))
        ax.plot([-W] * 2, [0, rg.FRAME_H], color=C_FRAME_EC, lw=.8, ls=":", zorder=3)
        ax.text((x0 - W) / 2, 4.6, "extension\n→ PCB edge\n(r = 650)", ha="center", va="center", fontsize=7.5,
                color=C_EXT_EC, zorder=6)
    ax.add_patch(plt.Rectangle((t_hole - d_hole / 2, 0), d_hole, rg.FRAME_H, fc="white", ec="black",
                               lw=1.0, ls="--", zorder=4, alpha=.85))
    ax.plot([t_hole, t_hole], [-0.8, rg.FRAME_H + 0.8], color="black", lw=.6, ls="-.", zorder=5)
    pcb_x0 = XLIM[0] + 1 if (new and ext) else -W
    ax.add_patch(plt.Rectangle((pcb_x0, -0.5), XLIM[1] - 1 - pcb_x0, 0.5, fc="0.35", zorder=1))
    groove, chan = features(P, W)
    if not (new and wide):
        dim(ax, (-W, rg.FRAME_H), (0, rg.FRAME_H), (0, 2.8), f"{W:g}")
    dim(ax, (-W, rg.FRAME_H), (t_hole, rg.FRAME_H), (0, 1.3), f"{t_hole + W:g}", fs=8)
    hole = box(t_hole - d_hole / 2, 0, t_hole + d_hole / 2, rg.FRAME_H)
    near = min((f for f in (groove, chan) if f is not None and not f.is_empty), key=lambda f: f.distance(hole))
    d = near.distance(hole)
    zf = near.centroid.y
    dim(ax, (t_hole + d_hole / 2, zf), (near.bounds[0], zf), (0, -zf - 1.6), f"{d:.2f}", fs=8,
        color="#c0392b" if d < 1.0 else C_DIM)
    if not groove.is_empty:
        ax.annotate("O-ring groove (unchanged)", (groove.centroid.x, 1.2), (4, 1.2), fontsize=7.5, va="center",
                    arrowprops=dict(arrowstyle="->", lw=.6))
    if chan is not None:
        ax.annotate("Ø2 bore in the STEP", (chan.centroid.x, chan.centroid.y), (4, 3.2), fontsize=7.5, va="center",
                    arrowprops=dict(arrowstyle="->", lw=.6))
    ax.annotate("mylar step", (-1.2, 4.0), (4, 5.6), fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=.6))
    ax.text(XLIM[1] - .5, 7.4, "active side →", fontsize=8, color="0.45", ha="right")
    ax.text(XLIM[0] + .5, 10.6, "← outside", fontsize=8, color="0.45", ha="left")
    ax.set_xlim(*XLIM)
    ax.set_ylim(-4.2, 12)
    ax.set_aspect("equal")
    ax.set_yticks([0, 4, 8])
    ax.tick_params(labelsize=7)
    ax.grid(lw=.25, alpha=.5)
    return d


def main():
    S = straight_profile()
    Po, Pi = arc_profiles()
    t_out_now, t_out_new = rg.R_OUT_WALL - rg.R_OUT_NOW, rg.R_OUT_WALL - rg.R_OUT
    t_in = rg.R_IN_NOW - rg.R_IN_WALL
    o = rg.OVERHANG
    rows = [("straight sides (both)", S, rg.SIDE_NOW, rg.Y_SIDE_NOW, rg.Y_SIDE, "Ø3.0 / Ø3.5", False,
             f"+{o:g} mm outward, hole line unchanged (O-ring), Ø3.5"),
            ("outer arc", Po, rg.ARC_NOW, t_out_now, t_out_new, "Ø3.0 / Ø3.5", True,
             f"extension added, holes at r = {rg.R_OUT:g} (today's), Ø3.5"),
            ("inner arc", Pi, rg.ARC_NOW, t_in, t_in, "Ø3.0 / Ø3.5", False,
             f"+{o:g} mm outward, hole line unchanged, Ø3.5")]
    fig, axs = plt.subplots(3, 2, figsize=(15, 10.5))
    for (name, P, W, th0, th1, _, ext, note), (a0, a1) in zip(rows, axs):
        d0 = panel(a0, P, W, th0, 3.0, False)
        d1 = panel(a1, P, W, th1, rg.SCREW_D, True, ext, wide=not ext)
        a0.set_title(f"{name} – NOW: Ø3.0 hole, {d0:.2f} mm to groove/bore",
                     fontsize=9.5, loc="left", weight="bold")
        a1.set_title(f"{name} – NEW: {note}; {d1:.2f} mm",
                     fontsize=9.5, loc="left", weight="bold", color=C_EXT_EC)
    for ax in axs[-1]:
        ax.set_xlabel("distance across the side [mm]  (0 = wall facing the active area)", fontsize=8)
    for ax in axs[:, 0]:
        ax.set_ylabel("z [mm]", fontsize=8)
    fig.suptitle(f"Drift frame – cross-sections: +{rg.OVERHANG:g} mm outward on the straight sides and the inner arc (PCB outline unchanged); dashed = screw hole (drawn projected)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(os.path.join(FIG, "frame_side_section.png"), dpi=130)
    plt.close(fig)
    print("written frame_side_section.png")


if __name__ == "__main__":
    main()
