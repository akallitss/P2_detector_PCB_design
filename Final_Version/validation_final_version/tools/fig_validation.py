#!/usr/bin/env python3
"""
Validation of the FINAL files: final PCB (PCB-Nov2026/K55V1) laid on the final drift frame
(drift_frame/P2_Frame_V3.dxf).  Only Final_Version/ is read (see final_geometry.py).

Writes ../figures/
  0_steps.png          4 steps: PCB alone -> frame alone -> frame on the PCB -> what lines up
  1_holes_unrolled.png every screw hole along each edge, PCB above / frame below, offsets in mm
  2_holes_zoom.png     true-size zooms (8 places)
  3_signal_lines.png   signal lines (F.Cu / B.Cu) under the frame walls and holes
  4_hv_corners.png     HV / mesh / drift contacts at the two corners vs the frame
and ../data/holes_pcb_vs_frame.csv, ../data/frame_holes_vs_signal.csv

Run with  (ulimit -v 2500000; python3 fig_validation.py)      peak ~0.4 GB
"""
import csv
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, PathPatch, Rectangle
from matplotlib.path import Path
from shapely.geometry import Point, box
from shapely.strtree import STRtree

import final_geometry as G
import i18n

C_BOARD, C_BOARD_EC = "#e8f3e4", "#2e7d32"
C_FRAME, C_FRAME_EC = "#9aa3b0", "#3c4350"
C_TOP, C_BOT, C_ZONE = "#e8892b", "#7e57c2", "#f6d7b5"
C_PCB_H, C_FR_H, C_OK = "#1565c0", "#c62828", "#2e7d32"
C_PAD = "#d4a017"
MATCH = 0.1                                   # [mm] centres closer than this = aligned
HOLE_R_LINE = {"bottom side": -7.5, "outer arc": 610.5, "top side": -7.5, "inner arc": 99.5}


# ---------------------------------------------------------------- data
def load():
    H = G.pcb_holes()
    F = G.frame()
    outer, window = G.frame_shapes(F)
    D = dict(H=H, F=F, outer=outer, window=window, board=G.board(), Cu=G.copper())
    D["solid"] = G.frame_solid(F, outer, window)
    D["pcb35"] = H[4]["xy"]                                      # Ø3.5 screw holes (plated)
    D["pcb_conn"] = [(x, y, H[k]["d"]) for k in (5, 6) for x, y in H[k]["xy"]]   # connector supports
    D["fr"] = [(x, y) for x, y, d in F["holes"]]
    D["fr_d"] = sorted({round(d, 2) for *_, d in F["holes"]})
    D["pairs"], D["pcb_only"], D["fr_only"] = pair(D["pcb35"], D["fr"])
    pads = {}
    for name, pt in (("D pad (drift HV)", (626.0, 12.5)), ("M pad (mesh HV)", (324.0, 536.0)),
                     ("drift contact pad", (589.18, 11.0)), ("mesh contact pad", (300.72, 516.72))):
        hits = [P for P in D["Cu"]["Top"]["other"] if P.contains(Point(pt)) and P.area > 2]
        pads[name] = max(hits, key=lambda P: P.area)
    D["pads"] = pads
    return D


def pair(A, B):
    """Greedy nearest pairing within MATCH: (pairs [(a, b, dist)], A-only, B-only)."""
    B = list(B)
    pairs, a_only, used = [], [], set()
    for a in A:
        d = [math.dist(a, b) for b in B]
        i = int(np.argmin(d))
        if d[i] < MATCH and i not in used:
            pairs.append((a, B[i], d[i]))
            used.add(i)
        else:
            a_only.append(a)
    return pairs, a_only, [b for i, b in enumerate(B) if i not in used]


def edge_of(p):
    """Which edge a hole is on (corners: both) + its position along that edge [mm]."""
    x, y = p
    r, a = math.hypot(x, y), math.atan2(y, x)
    dist = {"bottom side": abs(y + 7.5) if 90 < x < 615 else 99,
            "outer arc": abs(r - 610.5),
            "top side": abs(-x * math.sin(math.radians(60)) + y * math.cos(math.radians(60)) - 7.5) if 40 < x < 310 else 99,
            "inner arc": abs(r - 99.5) if r < 110 else 99}
    return [e for e, v in dist.items() if v < 2.6]


def s_along(edge, p):
    x, y = p
    if edge == "bottom side":
        return x
    if edge == "top side":
        return x * math.cos(math.radians(60)) + y * math.sin(math.radians(60))
    if edge == "outer arc":
        return 610.5 * math.atan2(y, x)
    return 99.5 * math.atan2(y, x)


# ---------------------------------------------------------------- drawing helpers
def poly_patch(geom, **kw):
    verts, codes = [], []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.is_empty:
            continue
        for ring in [g.exterior, *g.interiors]:
            xy = np.asarray(ring.coords)
            verts += xy.tolist()
            codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
    if not verts:
        return Rectangle((0, 0), 0, 0, visible=False)
    return PathPatch(Path(verts, codes), **kw)


def crop(geom, win):
    return geom if win is None else geom.intersection(box(win[0], win[2], win[1], win[3]).buffer(1))


def copper(ax, D, win, layers=("Bottom", "Top"), kinds=("signal",), alpha=.85, zorder=2):
    W = box(win[0], win[2], win[1], win[3])
    for lay in layers:
        col = C_TOP if lay == "Top" else C_BOT
        for k in kinds:
            vs = []
            for P in D["Cu"][lay][k]:
                if not P.intersects(W):
                    continue
                Q = P.intersection(W.buffer(1)) if k == "zone" else P
                for g in getattr(Q, "geoms", [Q]):
                    if g.geom_type == "Polygon" and not g.is_empty:
                        vs.append(np.asarray(g.exterior.coords))
            if vs:
                fc = C_ZONE if k == "zone" else col
                ax.add_collection(PolyCollection(vs, fc=fc, ec="none", alpha=alpha if k != "zone" else .5,
                                                 zorder=zorder - (1 if k == "zone" else 0)))


def board(ax, D, win=None, zorder=1):
    ax.add_patch(poly_patch(crop(D["board"], win), fc=C_BOARD, ec=C_BOARD_EC, lw=1, zorder=zorder))


def frame(ax, D, win=None, alpha=.55, lines=True, zorder=4):
    ax.add_patch(poly_patch(crop(D["solid"], win), fc=C_FRAME, ec=C_FRAME_EC, lw=.8, alpha=alpha, zorder=zorder))
    if lines:
        for s in D["F"]["lines"]:
            a = np.asarray(s.coords)
            if win is None or ((a[:, 0] > win[0] - 5) & (a[:, 0] < win[1] + 5) & (a[:, 1] > win[2] - 5) & (a[:, 1] < win[3] + 5)).any():
                ax.plot(*a.T, color=C_FRAME_EC, lw=.45, zorder=zorder + .1)


def true_holes(ax, D, win):
    inwin = lambda p: win[0] - 3 < p[0] < win[1] + 3 and win[2] - 3 < p[1] < win[3] + 3
    for x, y in D["pcb35"]:
        if inwin((x, y)):
            ax.add_patch(Circle((x, y), 1.75, fc="none", ec=C_PCB_H, lw=2.0, ls="--", zorder=8))
    for x, y, d in D["pcb_conn"]:
        if inwin((x, y)):
            ax.add_patch(Circle((x, y), d / 2, fc="none", ec=C_PCB_H, lw=1.0, ls=":", zorder=8))
    for x, y, d in D["F"]["holes"]:
        if inwin((x, y)):
            ax.add_patch(Circle((x, y), d / 2, fc="none", ec=C_FR_H, lw=1.4, zorder=9))


def tidy(ax, win, title, fs=10):
    ax.set_xlim(win[0], win[1])
    ax.set_ylim(win[2], win[3])
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=fs, loc="left")
    ax.tick_params(labelsize=7)


def scalebar(ax, win, L=10):
    x1, y0 = win[1] - 0.04 * (win[1] - win[0]), win[2] + 0.05 * (win[3] - win[2])
    ax.plot([x1 - L, x1], [y0, y0], color="k", lw=3, zorder=20)
    ax.text(x1 - L / 2, y0 + 0.015 * (win[3] - win[2]), f"{L} mm", ha="center", va="bottom", fontsize=8, zorder=20)


FULL = (25, 665, -30, 560)


def full(ax):
    ax.set_xlim(*FULL[:2])
    ax.set_ylim(*FULL[2:])
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------- figure 0: the four steps
def fig_steps(D):
    fig, axs = plt.subplots(2, 2, figsize=(17, 16.5))
    a1, a2, a3, a4 = axs.flat
    W = FULL
    # 1 PCB
    board(a1, D)
    copper(a1, D, W, kinds=("signal",), alpha=.6)
    for x, y in D["pcb35"]:
        a1.plot(x, y, "o", ms=7, mfc=C_PCB_H, mec="white", mew=.8, zorder=6)
    for x, y, d in D["pcb_conn"]:
        a1.plot(x, y, "o", ms=3.5, mfc="white", mec=C_PCB_H, mew=1, zorder=6)
    for n, P in D["pads"].items():
        a1.add_patch(poly_patch(P.buffer(2.5), fc=C_PAD, ec="k", lw=.8, zorder=7))
    a1.annotate("corner B: mesh contact\n+ M pad", (322, 532), (400, 505), fontsize=9, arrowprops=dict(arrowstyle="->"))
    a1.annotate("corner A: drift contact\n+ D pad", (615, 10), (450, 40), fontsize=9, arrowprops=dict(arrowstyle="->"))
    full(a1)
    a1.set_title(f"STEP 1 – the final PCB (PCB-Nov2026 / K55V1)\n{len(D['pcb35'])} screw holes Ø3.5 (plated), "
                 f"{len(D['pcb_conn'])} connector-support holes, signal lines (orange F.Cu, purple B.Cu)",
                 fontsize=11, loc="left")
    # 2 frame
    frame(a2, D, alpha=.9)
    for x, y in D["fr"]:
        a2.plot(x, y, "o", ms=7, mfc=C_FR_H, mec="white", mew=.8, zorder=6)
    full(a2)
    a2.set_title(f"STEP 2 – the final drift frame (P2_Frame_V3.dxf)\n{len(D['fr'])} screw holes "
                 f"Ø{'/'.join(map(str, D['fr_d']))}, outer edge R{max(math.hypot(*q) for q in D['outer'].exterior.coords):.0f}, "
                 f"thin lines = O-ring groove, glue channels", fontsize=11, loc="left")
    # 3 overlay
    board(a3, D)
    frame(a3, D, alpha=.6)
    for x, y in D["pcb35"]:
        a3.plot(x, y, "o", ms=7, mfc=C_PCB_H, mec="white", mew=.8, zorder=6)
    for x, y in D["fr"]:
        a3.plot(x, y, "o", ms=4, mfc=C_FR_H, mec="none", zorder=7)
    full(a3)
    a3.set_title("STEP 3 – frame laid on the PCB (same origin: centre of the arcs)\n"
                 "blue = PCB hole, red = frame hole: a red dot inside a blue one = aligned", fontsize=11, loc="left")
    # 4 verdict
    board(a4, D)
    frame(a4, D, alpha=.35, lines=False)
    for a, b, d in D["pairs"]:
        a4.plot(*a, "o", ms=10, mfc=C_OK, mec="white", mew=.8, zorder=6)
    for p in D["pcb_only"]:
        a4.plot(*p, "o", ms=9, mfc="white", mec=C_PCB_H, mew=2, zorder=6)
    for p in D["fr_only"]:
        a4.plot(*p, "x", ms=9, mew=2.4, color=C_FR_H, zorder=7)
    for x, y, d in D["pcb_conn"]:
        a4.plot(x, y, "o", ms=3, mfc="0.6", mec="none", zorder=5)
    full(a4)
    n = len(D["pcb35"])
    txt = (f"screw holes aligned (< {MATCH} mm): {len(D['pairs'])} of {n} PCB / {len(D['fr'])} frame\n"
           f"PCB hole with no frame hole:  {len(D['pcb_only'])}\n"
           f"frame hole with no PCB hole: {len(D['fr_only'])}\n"
           f"connector-support holes: frame ends at R615,\n  no frame under them ({len(D['pcb_conn'])})\n"
           f"HV pads D and M: outside the frame (r > 615)")
    a4.text(150, 170, txt, fontsize=10.5, family="monospace",
            bbox=dict(fc="white", ec="0.5", boxstyle="round,pad=.6"), zorder=10)
    a4.set_title("STEP 4 – result: which holes line up", fontsize=11, loc="left", weight="bold")
    a4.legend(handles=[Line2D([], [], marker="o", ls="none", mfc=C_OK, mec="white", ms=10, label="aligned: PCB + frame hole"),
                       Line2D([], [], marker="o", ls="none", mfc="white", mec=C_PCB_H, mew=2, ms=9, label="PCB hole only"),
                       Line2D([], [], marker="x", ls="none", color=C_FR_H, mew=2.4, ms=9, label="frame hole only")],
              loc="upper right", fontsize=10, frameon=True)
    fig.suptitle("Final PCB on the final drift frame – step by step (top view, mm)", fontsize=15, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, .97))
    fig.savefig(os.path.join(G.FIG, "0_steps.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- figure 1: holes along each edge
def fig_unrolled(D):
    edges = ["bottom side", "outer arc", "top side", "inner arc"]
    fig, axs = plt.subplots(4, 1, figsize=(17, 13))
    rows = []
    for ax, e in zip(axs, edges):
        P = sorted((s_along(e, p), p) for p in D["pcb35"] if e in edge_of(p))
        Fh = sorted((s_along(e, p), p) for p in D["fr"] if e in edge_of(p))
        matched = {tuple(a): (b, d) for a, b, d in D["pairs"]}
        for s, p in P:
            ok = tuple(p) in matched
            ax.plot(s, 1, "o", ms=11, mfc=C_OK if ok else "white", mec=C_PCB_H, mew=2, zorder=5)
        for s, p in Fh:
            ok = any(tuple(b) == tuple(p) for b, _ in matched.values())
            ax.plot(s, 0, "o", ms=11, mfc=C_OK if ok else "white", mec=C_FR_H, mew=2, zorder=5)
        # nearest frame hole for each PCB hole: offset along the edge
        for s, p in P:
            if not Fh:
                continue
            j = int(np.argmin([abs(t - s) for t, _ in Fh]))
            t, q = Fh[j]
            dd = math.dist(p, q)
            ok = dd < MATCH
            ax.plot([s, t], [0.9, 0.1], color=C_OK if ok else "0.55", lw=1.2 if ok else .8, ls="-" if ok else ":")
            ax.text(s, 1.22, "0" if ok else f"{t - s:+.1f}", ha="center", fontsize=7.5,
                    color=C_OK if ok else C_FR_H, rotation=0)
            rows.append([e, f"{p[0]:.2f}", f"{p[1]:.2f}", f"{q[0]:.2f}", f"{q[1]:.2f}", f"{dd:.3f}",
                         "aligned" if ok else "NOT aligned"])
        sp = np.diff([s for s, _ in P])
        sf = np.diff([s for s, _ in Fh])
        unit = "arc length on r 610.5" if e == "outer arc" else ("arc length on r 99.5" if e == "inner arc" else "")
        ax.set_title(f"{e}:  PCB {len(P)} holes (pitch {sp.min():.1f}–{sp.max():.1f} mm)   |   frame {len(Fh)} holes "
                     f"(pitch {sf.min():.1f}–{sf.max():.1f} mm)   |   aligned "
                     f"{sum(1 for s, p in P if tuple(p) in matched)}  {unit}", fontsize=10.5, loc="left")
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["frame V3", "PCB"], fontsize=10)
        ax.set_ylim(-.4, 1.5)
        ax.grid(axis="x", alpha=.3)
        ax.set_xlabel("position along the edge [mm]  (bottom: x; top side: distance from the centre along 60°; arcs: arc length)",
                      fontsize=8)
        for sp_ in ("top", "right"):
            ax.spines[sp_].set_visible(False)
    fig.legend(handles=[Line2D([], [], marker="o", ls="none", mfc=C_OK, mec="k", ms=10, label=f"aligned (centres < {MATCH} mm)"),
                        Line2D([], [], marker="o", ls="none", mfc="white", mec=C_PCB_H, mew=2, ms=10, label="PCB hole, no frame hole on it"),
                        Line2D([], [], marker="o", ls="none", mfc="white", mec=C_FR_H, mew=2, ms=10, label="frame hole, no PCB hole on it"),
                        Line2D([], [], color="0.55", ls=":", label="to the nearest frame hole; number = shift along the edge [mm]")],
               loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.suptitle("Screw holes along each edge – final PCB (top row) vs final frame V3 (bottom row)", fontsize=14, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .96))
    fig.savefig(os.path.join(G.FIG, "1_holes_unrolled.png"), dpi=120)
    plt.close(fig)
    with open(os.path.join(G.DATA, "holes_pcb_vs_frame.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["edge", "pcb_x", "pcb_y", "nearest_frame_x", "nearest_frame_y", "distance_mm", "status"])
        w.writerows(rows)
        for p in D["fr_only"]:
            w.writerow([" / ".join(edge_of(p)), "", "", f"{p[0]:.2f}", f"{p[1]:.2f}", "", "frame hole, no PCB hole"])


# ---------------------------------------------------------------- figure 2: true-size zooms
ZW, ZH = 44, 32
ZOOMS = [("inner-bottom corner", (99.3, -2)), ("bottom side", (180, -3)), ("bottom-right corner", (604, 2)),
         ("outer arc", (602, 92)), ("outer arc, 30°", (530, 300)), ("top corner", (300, 524)),
         ("top side", (178, 322)), ("inner arc", (82, 52))]


def zwin(c):
    return (c[0] - ZW / 2, c[0] + ZW / 2, c[1] - ZH / 2, c[1] + ZH / 2)


def label_holes(ax, D, win):
    inwin = lambda p: win[0] < p[0] < win[1] and win[2] < p[1] < win[3]
    for a, b, d in D["pairs"]:
        if inwin(a):
            ax.text(a[0], a[1] - 2.6, f"Δ {d:.2f}", ha="center", va="top", fontsize=7.5, color=C_OK, zorder=12,
                    bbox=dict(fc="white", ec="none", alpha=.8, pad=.5))
    for p in D["pcb_only"]:
        if inwin(p):
            q = min(D["fr"], key=lambda f: math.dist(f, p))
            ax.text(p[0], p[1] + 2.4, f"PCB only\nframe hole {math.dist(p, q):.1f} away", ha="center", va="bottom",
                    fontsize=7, color=C_PCB_H, zorder=12, bbox=dict(fc="white", ec="none", alpha=.8, pad=.5))
    for p in D["fr_only"]:
        if inwin(p):
            ax.text(p[0], p[1] - 2.6, "frame only", ha="center", va="top", fontsize=7, color=C_FR_H, zorder=12,
                    bbox=dict(fc="white", ec="none", alpha=.8, pad=.5))


def fig_zoom(D):
    fig, axs = plt.subplots(2, 4, figsize=(19, 9.6))
    for ax, (t, c) in zip(axs.flat, ZOOMS):
        w = zwin(c)
        board(ax, D, w)
        frame(ax, D, w)
        true_holes(ax, D, w)
        label_holes(ax, D, w)
        tidy(ax, w, t)
        scalebar(ax, w)
    fig.legend(handles=[Patch(fc=C_BOARD, ec=C_BOARD_EC, label="PCB"),
                        Patch(fc=C_FRAME, ec=C_FRAME_EC, alpha=.55, label="frame V3 (semi-transparent, on top)"),
                        Line2D([], [], color=C_PCB_H, ls="--", lw=2, label="PCB Ø3.5 hole"),
                        Line2D([], [], color=C_PCB_H, ls=":", lw=1, label="PCB connector-support hole"),
                        Line2D([], [], color=C_FR_H, lw=1.4, label="frame hole")],
               loc="lower center", ncol=5, fontsize=10, frameon=False)
    fig.suptitle("True-size zooms – a hole is clear only where a dashed blue and a red circle coincide "
                 "(Δ = centre distance, mm)", fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .95), h_pad=2)
    fig.savefig(os.path.join(G.FIG, "2_holes_zoom.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- figure 3: signal lines
def signal_clearance(D):
    """Edge-to-edge distance from every frame hole and every PCB hole to the nearest signal track."""
    tracks = D["Cu"]["Top"]["signal"] + D["Cu"]["Bottom"]["signal"]
    layer = ["F.Cu"] * len(D["Cu"]["Top"]["signal"]) + ["B.Cu"] * len(D["Cu"]["Bottom"]["signal"])
    tree = STRtree(tracks)
    out = []
    for kind, pts in (("frame hole", D["fr"]), ("PCB hole", D["pcb35"])):
        for p in pts:
            c = Point(p).buffer(1.75, 32)
            i = tree.nearest(c)
            out.append((kind, p, c.distance(tracks[i]) if not c.intersects(tracks[i]) else -1.0, layer[i],
                        sum(1 for j in tree.query(c) if tracks[j].intersects(c))))
    return out


def fig_signal(D, clr):
    cut = [r for r in clr if r[0] == "frame hole" and r[4] > 0]
    worst = sorted(cut, key=lambda r: -r[4])
    places = [("outer arc – frame hole on the signal lines", worst[0][1] if worst else (602, 92)),
              ("outer arc – PCB hole between the signal lines", (605.08, 81.14)),
              ("outer arc, near 30°", (530, 300)),
              ("bottom-right corner", (604, 6)),
              ("top corner", (305, 522)),
              ("inner arc", (82, 52))]
    fig, axs = plt.subplots(2, 3, figsize=(19, 12.5))
    for ax, (t, c) in zip(axs.flat, places):
        w = zwin(c)
        board(ax, D, w)
        copper(ax, D, w, kinds=("signal",), alpha=.9)
        frame(ax, D, w, alpha=.35)
        true_holes(ax, D, w)
        for kind, p, d, lay, n in clr:
            if w[0] < p[0] < w[1] and w[2] < p[1] < w[3]:
                col = C_FR_H if kind == "frame hole" else C_PCB_H
                s = f"cuts {n} track{'s' if n > 1 else ''}" if n else f"{d:.2f} mm to nearest track ({lay})"
                ax.text(p[0], p[1] + (2.4 if kind == "frame hole" else -2.6), f"{kind}: {s}", ha="center",
                        va="bottom" if kind == "frame hole" else "top", fontsize=7, color=col, zorder=12,
                        bbox=dict(fc="white", ec="none", alpha=.85, pad=.5))
        tidy(ax, w, t)
        scalebar(ax, w)
    nf = len(cut)
    fig.legend(handles=[Patch(fc=C_TOP, label="signal lines F.Cu (top)"), Patch(fc=C_BOT, label="signal lines B.Cu (bottom)"),
                        Patch(fc=C_FRAME, ec=C_FRAME_EC, alpha=.35, label="frame V3 (walls, O-ring groove lines)"),
                        Line2D([], [], color=C_PCB_H, ls="--", lw=2, label="PCB Ø3.5 hole"),
                        Line2D([], [], color=C_FR_H, lw=1.4, label="frame hole")],
               loc="lower center", ncol=5, fontsize=10, frameon=False)
    fig.suptitle(f"Signal lines under the frame – {nf} of the {len(D['fr'])} frame holes sit on signal tracks "
                 f"(a PCB hole there would cut them)", fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, .04, 1, .95), h_pad=2)
    fig.savefig(os.path.join(G.FIG, "3_signal_lines.png"), dpi=120)
    plt.close(fig)
    with open(os.path.join(G.DATA, "frame_holes_vs_signal.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hole", "x", "y", "edge", "tracks_cut_if_drilled", "clearance_to_nearest_track_mm", "layer"])
        for kind, p, d, lay, n in clr:
            w.writerow([kind, f"{p[0]:.2f}", f"{p[1]:.2f}", " / ".join(edge_of(p)), n, f"{d:.2f}" if d >= 0 else "", lay])


# ---------------------------------------------------------------- figure 4: HV corners
HV_LABEL = {"D pad (drift HV)": (628, 24), "drift contact pad": (575, -6),
            "M pad (mesh HV)": (330, 520), "mesh contact pad": (284, 504)}


def fig_hv(D):
    wins = [("corner A (bottom right): drift contact pad → D pad (drift HV)", (572, 652, -16, 34)),
            ("corner B (top): mesh contact pad, M pad (mesh HV)", (282, 348, 500, 546))]
    fig, axs = plt.subplots(1, 2, figsize=(19, 8.4))
    edge = D["outer"].exterior
    win_edge = D["window"].exterior
    for ax, (t, w) in zip(axs, wins):
        board(ax, D, w)
        copper(ax, D, w, kinds=("zone", "other", "signal"), alpha=.75)
        frame(ax, D, w, alpha=.5)
        true_holes(ax, D, w)
        for n, P in D["pads"].items():
            c = P.centroid
            if not (w[0] < c.x < w[1] and w[2] < c.y < w[3]):
                continue
            ax.add_patch(poly_patch(P, fc=C_PAD, ec="k", lw=1.2, zorder=10))
            cov = P.difference(D["window"]).intersection(D["outer"]).area
            if D["window"].contains(P):
                where = f"in the frame window, {win_edge.distance(P):.1f} mm from the wall"
            elif cov > 0 and P.intersects(D["window"]):
                where = f"in the window, but {cov:.2f} mm² ({100 * cov / P.area:.0f} %)\nunder the wall corner"
            elif cov > 0:
                where = "UNDER the frame wall"
            else:
                where = f"outside the frame, {edge.distance(P):.1f} mm from its outer edge"
            b = P.bounds
            ax.annotate(f"{n}\n{b[2] - b[0]:.1f} × {b[3] - b[1]:.1f} mm (bbox)\n{where}", (c.x, c.y),
                        HV_LABEL[n],
                        fontsize=8.5, zorder=14, arrowprops=dict(arrowstyle="->", lw=.8),
                        bbox=dict(fc="white", ec="0.5", alpha=.9))
        tidy(ax, w, t, fs=11)
        scalebar(ax, w)
    fig.legend(handles=[Patch(fc=C_PAD, ec="k", label="HV / contact pads (F.Cu)"),
                        Patch(fc=C_ZONE, alpha=.5, label="GND zone"), Patch(fc=C_TOP, label="F.Cu"), Patch(fc=C_BOT, label="B.Cu"),
                        Patch(fc=C_FRAME, ec=C_FRAME_EC, alpha=.5, label="frame V3")],
               loc="lower center", ncol=5, fontsize=10, frameon=False)
    fig.suptitle("HV connections at the two corners – final PCB vs final frame V3 (frame outer edge R615, no extension, "
                 "no HV openings needed there)", fontsize=12.5, weight="bold")
    fig.tight_layout(rect=(0, .05, 1, .95))
    fig.savefig(os.path.join(G.FIG, "4_hv_corners.png"), dpi=120)
    plt.close(fig)


def main():
    os.makedirs(G.FIG, exist_ok=True)
    D = load()
    print(f"PCB Ø3.5: {len(D['pcb35'])}, frame holes: {len(D['fr'])} Ø{D['fr_d']}, aligned {len(D['pairs'])}, "
          f"PCB only {len(D['pcb_only'])}, frame only {len(D['fr_only'])}")
    for a, b, d in D["pairs"]:
        print("  aligned", a, round(d, 3), edge_of(a))
    fig_steps(D)
    fig_unrolled(D)
    fig_zoom(D)
    clr = signal_clearance(D)
    fig_signal(D, clr)
    fig_hv(D)
    for kind in ("frame hole", "PCB hole"):
        r = [x for x in clr if x[0] == kind]
        print(f"{kind}s on signal tracks: {sum(1 for x in r if x[4])} / {len(r)}; "
              f"min clearance of the others {min(x[2] for x in r if not x[4]):.2f} mm")
    for n, P in D["pads"].items():
        print(n, [round(v, 2) for v in P.bounds])


if __name__ == "__main__":
    i18n.setup()
    main()
    i18n.finish()
