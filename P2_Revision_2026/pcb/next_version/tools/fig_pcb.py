#!/usr/bin/env python3
"""
PCB + insulation-mask changes for the 2026 revision: NOW vs NEW figures and coordinate tables
for the KiCad designer (they insert the changes in the project; we deliver no Gerbers here).

Reads (never modifies):
  ../../../drift_contact/data/cache.pkl                today's Gerber primitives (drift_contact_study.py)
  ../../drift_pad_B2/FABRICATION_P2_B2/Gerber            B2 drift-pad patch (copper NEW at corner A)
  ../../../mechanics/tools/rev_geometry.py              new screw-hole pattern, mesh corner, outlines
  ../data/inner_marks_search.json                      new positions of alignment crosses 1, 2

Writes ../figures/pcb_*.png and ../data/pcb_*.csv
Run with (ulimit -v 3000000; python3 fig_pcb.py)
"""
import csv
import gc
import json
import math
import os
import pickle
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon as MPoly, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
REV = os.path.normpath(os.path.join(OUT, "..", ".."))
sys.path.insert(0, os.path.join(REV, "mechanics", "tools"))
import rev_geometry as rg                                       # noqa: E402
from fig_frame_corners import C_DIM, C_EXT_EC, C_OPEN, C_PAD, callout, dim, poly_patch   # noqa: E402

FIG = os.path.join(OUT, "figures")
DATA = os.path.join(OUT, "data")
CACHE = os.path.join(REV, "drift_contact", "data", "cache.pkl")
B2_GERB = os.path.join(REV, "pcb", "drift_pad_B2", "FABRICATION_P2_B2", "Gerber")

C_PCB, C_FCU, C_BCU, C_CONN, C_MESH = "#eaf3e6", "#f0b46a", "#b39ddb", "#8e44ad", "#d9dde3"

# alignment crosses: today 3 x 3 mm (0.12 mm lines); NEW 9 mm across, 0.3 mm lines, 12.5 mm resist square
MARKS_NOW = {1: (70.80, 66.19), 2: (93.67, 28.50), 3: (635.63, 83.91), 4: (391.22, 507.00)}
CROSS_NOW, CROSS_NEW, LINE_NEW, SQUARE_NEW = 3.0, 9.0, 0.3, 12.5
CONN_LEN, CONN_W = 47.4, 8.7          # FX20-140P header body (Hirose catalog)


def marks_new():
    best = json.load(open(os.path.join(DATA, "inner_marks_search.json")))["best"][0]
    m = dict(MARKS_NOW)
    m[1], m[2] = tuple(best["cross_1"]), tuple(best["cross_2"])
    return m, best


def connectors(C):
    """The 10 FX20-140P footprints: centre and mid angle, from their pads on today's F.Cu."""
    pts = []
    for p in C["gerb"]["F_Cu"]:
        if type(p).__name__ == "Rectangle":
            (x0, y0), (x1, y1) = p.bounding_box()
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if 626 < math.hypot(cx, cy) < 638:
                pts.append((math.degrees(math.atan2(cy, cx)), cx, cy))
    a = np.array(sorted(pts))
    out = []
    for g in np.split(a, np.where(np.diff(a[:, 0]) > 1.0)[0] + 1):
        c = g[:, 1:].mean(0)
        out.append((tuple(c), math.degrees(math.atan2(c[1], c[0])), len(g)))
    return out


def conn_box(c, ang):
    t = math.radians(ang)
    u = np.array([-math.sin(t), math.cos(t)])          # along the connector (tangential)
    n = np.array([math.cos(t), math.sin(t)])           # radial
    c = np.asarray(c)
    return [tuple(c + su * CONN_LEN / 2 * u + sn * CONN_W / 2 * n) for su, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def cross(ax, c, size, lw, color, square=None, **kw):
    x, y = c
    h = size / 2
    ax.plot([x - h, x + h], [y, y], color=color, lw=lw, solid_capstyle="butt", **kw)
    ax.plot([x, x], [y - h, y + h], color=color, lw=lw, solid_capstyle="butt", **kw)
    if square:
        s = square / 2
        ax.add_patch(Rectangle((x - s, y - s), square, square, fc="none", ec=color, lw=.8, ls="--", zorder=7))


OLD_SCREW = None


def copper_polys(prims, win, drop_old_screw_pads=False):
    """Gerber primitives -> polygons cropped to win (keeps memory low). Clear-polarity primitives
    (clearances cut into the GND hatch) are not copper and are skipped."""
    from gerbonara.graphic_primitives import ArcPoly, Circle as GC, Line as GL, Rectangle as GR
    global OLD_SCREW
    if OLD_SCREW is None:
        D, H = rg.read_drill()
        OLD_SCREW = [(x, y) for k in (3, 6) for x, y in H[k]]
    x0, x1, y0, y1 = win
    out = []
    for p in prims:
        if not getattr(p, "polarity_dark", True):
            continue
        if drop_old_screw_pads and isinstance(p, GC) and any(math.hypot(p.x - a, p.y - b) < 0.05 for a, b in OLD_SCREW):
            continue
        try:
            (a, b), (c, d) = p.bounding_box()
        except Exception:
            continue
        if c < x0 or a > x1 or d < y0 or b > y1:
            continue
        if isinstance(p, ArcPoly):
            o = np.array(list(p.outline))
            if len(o) > 2:
                out.append(o)
        elif isinstance(p, GC):
            t = np.linspace(0, 2 * np.pi, 24)
            out.append(np.c_[p.x + p.r * np.cos(t), p.y + p.r * np.sin(t)])
        elif isinstance(p, GR):
            cx, cy, w, h, r = p.x, p.y, p.w, p.h, getattr(p, "rotation", 0.0)
            R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
            q = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) @ R.T
            out.append(q + [cx, cy])
        elif isinstance(p, GL):
            d = np.array([p.x2 - p.x1, p.y2 - p.y1])
            L = np.hypot(*d)
            if L < 1e-9:
                continue
            n = np.array([-d[1], d[0]]) / L * p.width / 2
            out.append(np.array([[p.x1, p.y1] + n, [p.x2, p.y2] + n, [p.x2, p.y2] - n, [p.x1, p.y1] - n]))
    return out


def load_b2(win):
    from gerbonara import GerberFile
    from gerbonara.utils import MM
    res = {}
    for layer in ("F_Cu", "B_Cu"):
        g = GerberFile.open(os.path.join(B2_GERB, f"P2_BASKET-{layer}.gbr"))
        prims = []
        for o in g.objects:
            try:
                prims += list(o.to_primitives(MM))
            except Exception:
                pass
        res[layer] = copper_polys(prims, win, drop_old_screw_pads=True)
        del g, prims
        gc.collect()
    return res


def board(ax):
    ax.add_patch(poly_patch(rg.pcb_outline(), fc=C_PCB, ec="0.3", lw=.8, zorder=0))


def overview(C, conns, mk):
    D, H = rg.read_drill()
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 9.6))
    for ax in (a0, a1):
        board(ax)
        ax.add_patch(poly_patch(rg.frame_top()[1].buffer(-3.0, join_style=2), fc="white", ec="0.6", lw=.5, ls=":", zorder=0))
        for k in (4, 5):
            for x, y in H[k]:
                ax.plot(x, y, "o", ms=2.5, color="0.4", zorder=3)
        ax.set_xlim(20, 665)
        ax.set_ylim(-30, 560)
        ax.set_aspect("equal")
        ax.axis("off")
    for c, a, _ in conns:
        a0.add_patch(MPoly(conn_box(c, a), fc=C_FCU, ec="#a0522d", lw=.8, zorder=4))
        a1.add_patch(MPoly(conn_box(c, a), fc="none", ec=C_CONN, lw=1.2, ls="--", zorder=4))
    for x, y, d in rg.old_frame_holes(H):
        a0.plot(x, y, "o", ms=6, **({"mfc": "#1f5fbf", "mec": "#1f5fbf"} if d < 3.2 else {"mfc": "white", "mec": "#8e44ad", "mew": 1.8}), zorder=5)
    for no, x, y, _ in rg.new_frame_holes()[0]:
        a1.plot(x, y, "o", ms=6, mfc="white", mec="black", mew=1.4, zorder=5)
    new, _ = mk
    for i, c in MARKS_NOW.items():
        a0.plot(*c, "+", ms=9, mew=1.6, color="#c0392b", zorder=6)
        a0.annotate(f"{i}", c, (c[0] + 8, c[1] + 8), fontsize=9, color="#c0392b")
    for i, c in new.items():
        a1.plot(*c, "P", ms=11, mfc="#c0392b", mec="white", zorder=6)
        a1.annotate(f"{i}", c, (c[0] + 9, c[1] + 9), fontsize=9, color="#c0392b", weight="bold")
    for ax in (a0, a1):
        ax.add_patch(Rectangle((578, -14), 72, 50, fc="none", ec=C_DIM, lw=1.2, ls="-."))
        ax.text(580, 38, "zoom A", color=C_DIM, fontsize=9)
        ax.add_patch(Rectangle((50, 5), 70, 90, fc="none", ec=C_DIM, lw=1.2, ls="-."))
        ax.text(52, 97, "zoom marks", color=C_DIM, fontsize=9)
    a0.set_title("NOW", fontsize=14, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=14, weight="bold", loc="left", color=C_EXT_EC)
    fig.text(0.04, 0.2, "today\n• connectors FX20-140P on the front (F.Cu)\n"
             "• 40 screw holes: 26 Ø3.5 plated + 14 Ø3.5 not plated,\n   irregular spacing\n"
             "• alignment crosses 3 × 3 mm\n• Sig1 readout pad in the bottom-right corner",
             fontsize=9.5, va="top", bbox=dict(fc="white", ec="0.6", boxstyle="round,pad=.5"))
    fig.text(0.52, 0.2, "1. outline UNCHANGED\n"
             "2. 39 screw holes Ø3.5, equal pitch, mirror-symmetric (table pcb_screw_holes_new.csv)\n"
             "3. connectors move to the BACK (B.Cu), same positions (dashed)\n"
             "4. alignment crosses 9 mm / 12.5 mm resist square; crosses 1, 2 move (zoom marks)\n"
             "5. corner A: B2 drift pad replaces Sig1; mesh cleared in the corner (zoom A)\n"
             "6. connector-support holes (grey dots): unchanged",
             fontsize=9.5, va="top", bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    h = [Patch(fc=C_PCB, ec="0.3", label="PCB (outline unchanged)"),
         Patch(fc=C_FCU, ec="#a0522d", label="connector on the front"),
         Patch(fc="none", ec=C_CONN, ls="--", label="connector on the BACK"),
         Line2D([], [], marker="o", ls="none", mfc="#1f5fbf", mec="#1f5fbf", label="Ø3.5 plated (today)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="#8e44ad", mew=1.8, label="Ø3.5 not plated (today)"),
         Line2D([], [], marker="o", ls="none", mfc="white", mec="black", label="NEW Ø3.5 screw hole"),
         Line2D([], [], marker="P", ls="none", mfc="#c0392b", mec="white", ms=10, label="alignment cross"),
         Line2D([], [], marker="o", ls="none", color="0.4", ms=3, label="connector-support hole")]
    fig.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 0.94), ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("PCB – what changes (symbols enlarged)", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.21, 1, 0.88))
    fig.savefig(os.path.join(FIG, "pcb_overview.png"), dpi=130)
    plt.close(fig)


def corner_A(C, conns):
    win = (578, 650, -14, 36)
    D, H = rg.read_drill()
    now_f, now_b = copper_polys(C["gerb"]["F_Cu"], win), copper_polys(C["gerb"]["B_Cu"], win)
    new = load_b2(win)
    _, window, _ = rg.frame_top()
    base = window.buffer(-3.0, join_style=2)
    mesh_now = base.buffer(-rg.MESH_TRIM, join_style=2)
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 8.0))
    for ax, F, B, mesh in ((a0, now_f, now_b, mesh_now), (a1, new["F_Cu"], new["B_Cu"], rg.mesh_area())):
        board(ax)
        ax.add_collection(PolyCollection(B, fc=C_BCU, ec="none", alpha=.45, zorder=1))
        ax.add_collection(PolyCollection(F, fc=C_FCU, ec="none", alpha=.75, zorder=2))
        ax.add_patch(poly_patch(mesh, fc=C_MESH, ec="0.5", lw=.5, hatch="....", alpha=.55, zorder=3))
        ax.plot(*np.asarray(base.exterior.coords).T, color="0.35", lw=.7, ls=":", zorder=4)
        for k in (4, 5):
            for x, y in H[k]:
                ax.add_patch(Circle((x, y), D[k] / 2, fc="white", ec="0.4", lw=.7, zorder=5))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    for x, y, d in rg.old_frame_holes(H):
        a0.add_patch(Circle((x, y), d / 2, fc="white", ec="#1f5fbf" if d < 3.2 else "#8e44ad", lw=1.4, zorder=6))
    for no, x, y, _ in rg.new_frame_holes()[0]:
        a1.add_patch(Circle((x, y), rg.SCREW_D / 2, fc="white", ec="black", lw=1.2, zorder=6))
    for c, a, _ in conns:
        a1.add_patch(MPoly(conn_box(c, a), fc="none", ec=C_CONN, lw=1.4, ls="--", zorder=6))
    c = rg.B2_CUT
    a1.plot([c[0], c[0], 600.5], [-1, c[3], c[3]], color=C_OPEN, lw=1.6, ls="--", zorder=7)
    a0.set_title("NOW", fontsize=13, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    callout(a0, (589.2, 11.0), (579, 27), "readout pad /Sector0/Sig1")
    callout(a0, (628, 12), (633, -11), "HV pads GND / M / D / GND")
    callout(a0, (632, 33), (612, 32.5), "connector (front)")
    callout(a0, (597.2, 2.7), (581, -9), "mesh-contact pad M (corner A)")
    callout(a0, (592.3, -7.5), (601, -12.5), "screw holes: Ø3.5 plated / not plated")
    callout(a1, (590.5, 10.0), (579, 27), "B2 drift pad 3 × 3 mm at (590.5, 10.0)\n(details: drift_pad_B2/CHANGES.txt)", color="#8a6a00")
    callout(a1, (608, 7.7), (603, 21), "drift trace on B.Cu → via in the D pad\n(626.3, 15.8)", color="#6a1b9a")
    callout(a1, (597.2, 2.7), (581, -9), "M pad: no mesh on it any more.\nMesh contact = the pad at corner B (top)", color="#8a6a00")
    callout(a1, (586.5, 13.5), (612, 31.5), "mesh cut: no mesh for x ≥ 585.5, y ≤ 15", color=C_OPEN)
    callout(a1, (632, 30), (634, -11.5), "connector moves to the BACK\n(same position)", color=C_CONN)
    h = [Patch(fc=C_FCU, alpha=.75, label="F.Cu"), Patch(fc=C_BCU, alpha=.45, label="B.Cu"),
         Patch(fc=C_MESH, ec="0.5", hatch="....", alpha=.55, label="mesh (laminated last)"),
         Line2D([], [], color=C_OPEN, ls="--", label="mesh cut lines"),
         Patch(fc="none", ec=C_CONN, ls="--", label="connector on the back"),
         Line2D([], [], color="0.35", ls=":", label="frame inner wall")]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=8.5, frameon=False)
    fig.suptitle("PCB – corner A (bottom right): drift pad B2, mesh corner, connectors to the back", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_corner_A.png"), dpi=130)
    plt.close(fig)


def marks_fig(mk):
    new, best = mk
    win = (52, 118, 5, 93)
    D, H = rg.read_drill()
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 9.2))
    for ax in (a0, a1):
        board(ax)
        ax.add_patch(poly_patch(rg.frame_top()[0].difference(rg.frame_top()[1]), fc="none", ec="0.55", lw=.7, ls=":", zorder=1))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect("equal")
        ax.grid(lw=.25, alpha=.4)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x [mm]", fontsize=8)
    for x, y, d in rg.old_frame_holes(H):
        a0.add_patch(Circle((x, y), d / 2, fc="white", ec="#1f5fbf" if d < 3.2 else "#8e44ad", lw=1.4, zorder=5))
    newh = rg.new_frame_holes()[0]
    for no, x, y, _ in newh:
        a1.add_patch(Circle((x, y), rg.SCREW_D / 2, fc="white", ec="black", lw=1.2, zorder=5))
        if win[0] < x < win[1] and win[2] < y < win[3]:
            a1.annotate(f"hole {no}", (x, y), (x - 9, y + 4), fontsize=8)
    for i in (1, 2):
        cross(a0, MARKS_NOW[i], CROSS_NOW, 1.2, "#c0392b", zorder=6)
        a0.annotate(f"cross {i}: 3 × 3 mm\n({MARKS_NOW[i][0]:.2f}, {MARKS_NOW[i][1]:.2f})", MARKS_NOW[i],
                    (MARKS_NOW[i][0] + 5, MARKS_NOW[i][1] - 9), fontsize=8.5, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=.7))
        cross(a1, MARKS_NOW[i], CROSS_NEW, 1.0, "0.6", zorder=4, alpha=.6)
        d_old = min(math.hypot(x - MARKS_NOW[i][0], y - MARKS_NOW[i][1]) for _, x, y, _ in newh)
        a1.annotate(f"today's position: only {d_old:.1f} mm\nto a new screw hole – moved", MARKS_NOW[i],
                    (MARKS_NOW[i][0] - 17, MARKS_NOW[i][1] - 12), fontsize=8, color="0.4",
                    arrowprops=dict(arrowstyle="->", color="0.5", lw=.7))
        cross(a1, new[i], CROSS_NEW, 2.0, "#c0392b", square=SQUARE_NEW, zorder=6)
        a1.annotate("", new[i], MARKS_NOW[i], arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.3, ls="--"))
        a1.annotate(f"cross {i} NEW\n({new[i][0]:.2f}, {new[i][1]:.2f})", new[i], (new[i][0] + 7.5, new[i][1] + 3),
                    fontsize=9, color="#c0392b", weight="bold")
    a0.set_title("NOW (inner arc, crosses 1 and 2)", fontsize=12, weight="bold", loc="left")
    a1.set_title("NEW", fontsize=13, weight="bold", loc="left", color=C_EXT_EC)
    a0.set_ylabel("y [mm]", fontsize=8)
    fig.text(0.06, 0.09,
             f"All 4 crosses: copper cross {CROSS_NEW:g} mm across, {LINE_NEW:g} mm lines, on F.Cu and B.Cu; masks: cross outline 10 mm / 1.3 mm arms\n"
             f"in a {SQUARE_NEW:g} × {SQUARE_NEW:g} mm resist square (dashed).  Crosses 1 and 2 move to r = {best['r_mm']:g} mm, at {60 - best['angle_deg']:g}° and "
             f"{best['angle_deg']:g}° (mirror pair):\n{best['patch_half_mm']:.1f} mm free round the centre (6.25 needed).  "
             "Crosses 3 and 4 stay where they are (table pcb_alignment_marks.csv).",
             fontsize=9, va="top", bbox=dict(fc="white", ec=C_EXT_EC, boxstyle="round,pad=.5"))
    fig.suptitle("PCB – alignment crosses: bigger, and crosses 1, 2 moved clear of the new screw holes", fontsize=14, y=.985)
    fig.tight_layout(rect=(0, 0.11, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_alignment_marks.png"), dpi=130)
    plt.close(fig)


def connector_side():
    """Radial section through a connector: NOW on the front, NEW on the back."""
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(13, 8.4))
    for ax, new in ((a0, False), (a1, True)):
        ax.add_patch(Rectangle((585, -0.2), 65, 0.2, fc="#2e7d32", alpha=.6))
        ax.add_patch(Rectangle((585, 0), 615 - 585, 8, fc="#c9cdd4", ec="#5b6170"))
        if new:
            ax.add_patch(Rectangle((615, 0), 650 - 615, 8, fc="#f4a742", ec="#b8650a"))
            ax.add_patch(Rectangle((585, -3.2), rg.CB_R_OUT - 585, 3.0, fc="#4a4f57"))
            ax.add_patch(Rectangle((rg.CONN_R_IN, -6.2), rg.CONN_R_OUT - rg.CONN_R_IN, 6.0, fc=C_FCU, ec="#a0522d"))
            dim(ax, (rg.CB_R_OUT, -3.2), (rg.CONN_R_IN, -3.2), (0, -1.6), f"{rg.CONN_R_IN - rg.CB_R_OUT:.1f}", fs=8)
            ax.text(632.1, -3.3, "connector\n(back, B.Cu)", ha="center", va="center", fontsize=8)
            ax.text(600, -1.7, "carbon back", color="white", ha="center", va="center", fontsize=8)
            ax.text(632, 4, "frame extension (front)", ha="center", va="center", fontsize=8)
        else:
            ax.add_patch(Rectangle((585, -3.2), 650 - 585, 3.0, fc="#4a4f57"))
            ax.add_patch(Rectangle((rg.CONN_R_IN, 0), rg.CONN_R_OUT - rg.CONN_R_IN, 6.0, fc=C_FCU, ec="#a0522d"))
            ax.text(632.1, 3, "connector\n(front, F.Cu)", ha="center", va="center", fontsize=8)
            ax.text(615, -1.7, "carbon back (to R650)", color="white", ha="center", va="center", fontsize=8)
        ax.text(600, 4, "drift frame", ha="center", va="center", fontsize=8)
        ax.text(646, 0.4, "PCB", fontsize=8, color="#1b4d1e")
        ax.set_xlim(585, 652)
        ax.set_ylim(-9, 10)
        ax.set_aspect("equal")
        ax.set_yticks([])
        ax.tick_params(labelsize=7)
        ax.set_xlabel("r [mm]  (radial section through a connector)", fontsize=8)
    a0.set_title("NOW – connectors on the front, carbon back under them", fontsize=11, loc="left", weight="bold")
    a1.set_title("NEW – connectors on the back; frame extension supports the front", fontsize=11, loc="left",
                 weight="bold", color=C_EXT_EC)
    fig.text(0.5, 0.02, "Flipping a footprint to the other side mirrors its pin order: check the mating side "
             "(adapter card / channel mapping) before routing.", ha="center", fontsize=10, color="#c0392b")
    fig.suptitle("PCB – FX20-140P connectors move to the back side (schematic, heights not to scale)", fontsize=13, y=.985)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(FIG, "pcb_connectors_back.png"), dpi=130)
    plt.close(fig)


def tables(conns, mk):
    D, H = rg.read_drill()
    new, best = mk
    with open(os.path.join(DATA, "pcb_screw_holes_new.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["no", "x_mm", "y_mm", "diameter_mm", "edge", "plated", "note"])
        for no, x, y, e in rg.new_frame_holes()[0]:
            w.writerow([no, f"{x:.2f}", f"{y:.2f}", rg.SCREW_D, e, "TO DECIDE", "same position in frame and carbon back"])
    with open(os.path.join(DATA, "pcb_screw_holes_remove.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x_mm", "y_mm", "diameter_mm", "plating", "kept_in_new_pattern"])
        newp = [(round(x, 2), round(y, 2)) for _, x, y, _ in rg.new_frame_holes()[0]]
        for k, pl in ((3, "PTH"), (6, "NPTH")):
            for x, y in H[k]:
                kept = any(math.hypot(x - a, y - b) < 0.05 for a, b in newp)
                w.writerow([f"{x:.2f}", f"{y:.2f}", D[k], pl, "yes (same place)" if kept else "no – remove"])
    with open(os.path.join(DATA, "pcb_alignment_marks.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cross", "x_now", "y_now", "x_new", "y_new", "copper_cross_mm", "line_mm", "mask_resist_square_mm", "layers"])
        for i in (1, 2, 3, 4):
            w.writerow([i, *MARKS_NOW[i], f"{new[i][0]:.2f}", f"{new[i][1]:.2f}", CROSS_NEW, LINE_NEW, SQUARE_NEW,
                        "F.Cu, B.Cu, M1, M2"])
    with open(os.path.join(DATA, "pcb_connectors.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["connector", "x_centre", "y_centre", "angle_deg", "pads_today", "side_now", "side_new"])
        for i, (c, a, n) in enumerate(conns, 1):
            w.writerow([i, f"{c[0]:.2f}", f"{c[1]:.2f}", f"{a:.2f}", n, "F.Cu", "B.Cu (same position)"])
    with open(os.path.join(DATA, "pcb_mesh_cut.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["point", "x_mm", "y_mm", "note"])
        y1 = rg.B2_CUT[3]
        for k, (x, y, t) in enumerate(((rg.B2_CUT[0], 0.0, "start at the bottom frame wall"),
                                       (rg.B2_CUT[0], y1, "corner"),
                                       (math.sqrt(600 ** 2 - y1 ** 2), y1, "end at the outer-arc frame wall")), 1):
            w.writerow([k, f"{x:.2f}", f"{y:.2f}", t])


def main():
    C = pickle.load(open(CACHE, "rb"))
    conns = connectors(C)
    mk = marks_new()
    overview(C, conns, mk)
    corner_A(C, conns)
    del C
    gc.collect()
    marks_fig(mk)
    connector_side()
    tables(conns, mk)
    print("written pcb_overview, pcb_corner_A, pcb_alignment_marks, pcb_connectors_back + data/pcb_*.csv")


if __name__ == "__main__":
    main()
