#!/usr/bin/env python3
"""
Corner A, "ground jump" across the drift line.

The drift line (F.Cu, today's mesh line) with its 3 mm keep-out cuts the F.Cu GND hatch of the
corner in two: the part towards the connectors and the part round the remaining bottom GND pad. To
keep GND continuous on both sides, each jump puts GND vias on both sides of the line (outside the
keep-out) and joins them with a GND strip on B.Cu that crosses under the line.

Positions are searched along the line, clear of other copper, the drill holes and screw hole 13.
Writes ../figures/pcb_corner_A_gnd_jump.png and appends the jumps to ../data/pcb_corner_A_drift.csv
(run fig_pcb.py first, it rewrites that table).
Run with (ulimit -v 3500000; python3 fig_pcb_gnd_jump.py)
"""
import csv
import math
import os
import pickle

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Rectangle
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import fig_pcb as fp

rg = fp.rg
VIA_D, VIA_PAD = 0.4, 0.8           # GND stitching via: drill, pad
VIA_OFF = 4.0                       # via centre from the line centre (line 0.4 + keep-out 3 + pad 0.4 + 0.2)
VIA_PITCH = 1.6                     # two vias per side, along the line
STRIP_W = 1.5                       # B.Cu GND strip under the line
CLEAR = 0.5                         # via / strip to other copper and holes
SEG = (rg.M_TRACE_BEND, (621.76, 12.06))   # the straight run of the drift line under the frame
C_GND_UP, C_GND_LO = "#9fd3a8", "#a9c8ee"


def geometry():
    C = pickle.load(open(fp.CACHE, "rb"))
    win = (590, 640, -12, 30)
    mnet, mparts = fp.m_net_A(C)
    added, removed, kept, hv = fp.drift_net_A(mparts)
    net = kept.union(added)
    F = [Polygon(q).buffer(0) for q in fp.copper_polys(C["gerb"]["F_Cu"], win)]
    B = [Polygon(q).buffer(0) for q in fp.copper_polys(C["gerb"]["B_Cu"], win)]
    del C
    sig = lambda g: g.distance(mnet) < 0.05 or g.distance(Point(589.18, 11.0)) < 7 and g.area > 50   # mesh net, Sig1 zone
    F_hatch = unary_union([g for g in F if g.area > 150])
    F_area = F_hatch.buffer(3.0).buffer(-3.0).union(hv["gnd_bottom"])   # hatched area (lattice holes closed) + GND pad
    gnd = lambda g: g.intersects(F_hatch.buffer(0.05)) or g.intersects(hv["gnd_bottom"].buffer(0.05))  # GND copper: a via may touch it
    gone = lambda g: fp.is_label_gone(np.asarray(g.exterior.coords)[:4]) or box(*fp.HV_LABELS_A["M"]).contains(g.centroid)
    F_other = [g for g in F if g.area <= 150 and not sig(g) and not gnd(g) and not gone(g)
               and not any(g.intersects(P) for P in list(hv["d"]) + list(hv["m"]) + [hv["gnd_top"]])]
    B_hatch = unary_union([g for g in B if g.area > 150])
    B_other = [g for g in B if g.area <= 150 and not fp.is_b2_patch(np.asarray(g.exterior.coords))
               and g.distance(Point(589.18, 11.0)) > 1.0]
    D, H = rg.read_drill()
    holes = [Point(x, y).buffer(D[k] / 2 + (0.6 if k in (3, 6) else 0.3)) for k in H for x, y in H[k]
             if 590 < x < 640 and -12 < y < 30 and not (k in (3, 6) and not fp.in_new_pattern(x, y))]
    holes += [Point(x, y).buffer(rg.SCREW_D / 2 + 0.6) for _, x, y, _ in rg.new_frame_holes()[0] if 590 < x < 640 and -12 < y < 30]
    hole13 = Point(610.30, 14.50).buffer(2.28)                # plated pad of kept screw hole 13
    holes.append(hole13)
    return dict(hole13=hole13, net=net, kept=kept, added=added, hv=hv, F_hatch=F_hatch, F_area=F_area, F_other=F_other, B_hatch=B_hatch,
                B_other=B_other, holes=holes, win=win)


def jump(t):
    """Jump at fraction t of the straight run: 2 vias each side + the B.Cu strip between them."""
    a, b = np.asarray(SEG[0]), np.asarray(SEG[1])
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([-u[1], u[0]])
    p = a + t * (b - a)
    vias = [tuple(p + s * VIA_OFF * n + k * VIA_PITCH / 2 * u) for s in (1, -1) for k in (-1, 1)]
    strip = LineString([tuple(p + VIA_OFF * n), tuple(p - VIA_OFF * n)]).buffer(STRIP_W / 2 + VIA_PITCH / 2, cap_style=2)
    strip = strip.union(unary_union([Point(v).buffer(VIA_PAD / 2) for v in vias])).convex_hull
    return dict(p=tuple(p), u=u, n=n, vias=vias, strip=strip)


def clearance(j, G):
    """(clearance to other copper and holes, ok): ok = vias in the GND area and outside the keep-out."""
    pads = [Point(v).buffer(VIA_PAD / 2) for v in j["vias"]]
    d = [min(P.distance(g) for g in G["F_other"] + G["holes"]) for P in pads]
    d += [min((j["strip"].distance(g) for g in G["B_other"]), default=9)]
    outside = min(P.distance(G["net"]) for P in pads) >= 3.0
    on_gnd = all(G["F_area"].contains(Point(v)) for v in j["vias"])  # inside the hatched GND area
    return min(d), on_gnd and outside


def why(j, G):
    """Which copper / hole limits a jump (for the printout)."""
    pads = [Point(v).buffer(VIA_PAD / 2) for v in j["vias"]]
    f = min(min(P.distance(g) for g in G["F_other"]) for P in pads)
    h = min(min(P.distance(g) for g in G["holes"]) for P in pads)
    b = min((j["strip"].distance(g) for g in G["B_other"]), default=9)
    return f"F.Cu {f:.2f}, holes {h:.2f}, B.Cu under strip {b:.2f}"


T_OPTION = 0.80                     # second jump, nearer the D pad: needs the bottom "GND" copper text moved


def choose(G):
    """The jump with the largest clearance along the run (the hole-13 pad blocks the middle, the
    bottom "GND" copper text and the D-pad keep-out the end), + the optional second one."""
    best = None
    for t in np.linspace(0.08, 0.95, 120):
        j = jump(t)
        c, ok = clearance(j, G)
        if ok and c >= CLEAR and (best is None or c > best[0]):
            best = (c, t, j)
    J = [best] if best else []
    jo = jump(T_OPTION)
    return J, (clearance(jo, G)[0], T_OPTION, jo)


def figure(G, J, opt):
    win = (594, 630, -6, 22)
    fig = plt.figure(figsize=(17, 8.6))
    ax = fig.add_axes([0.03, 0.12, 0.56, 0.8])
    fp.board(ax)
    W = box(win[0], win[2], win[1], win[3])
    keep = G["net"].buffer(3.0)
    isl = G["F_hatch"].intersection(W).difference(keep)
    parts = sorted([g for g in getattr(isl, "geoms", [isl]) if g.area > 5], key=lambda g: -g.centroid.y)
    ax.add_patch(fp.poly_patch(G["B_hatch"].intersection(W), fc=fp.C_BCU, ec="none", alpha=.3, zorder=1))
    for g, col in zip(parts, (C_GND_UP, C_GND_LO)):
        ax.add_patch(fp.poly_patch(g, fc=col, ec="0.4", lw=.4, alpha=.85, zorder=2))
    ax.add_collection(PolyCollection([np.asarray(g.exterior.coords) for g in G["F_other"] if g.intersects(W)],
                                     fc=fp.C_FCU, ec="none", alpha=.75, zorder=3))
    ax.add_patch(fp.poly_patch(G["hv"]["gnd_bottom"], fc=fp.C_FCU, ec="#a0522d", lw=.6, zorder=3))
    for h in G["holes"]:
        if h.intersects(W):
            ax.add_patch(fp.poly_patch(h, fc="white", ec="0.4", lw=.6, zorder=4))
    ax.add_patch(fp.poly_patch(keep.difference(G["net"].buffer(0.05)), fc="none", ec="#1b7a2e", lw=.8, ls=(0, (2, 2)), zorder=5))
    ax.add_patch(fp.poly_patch(G["kept"], fc=fp.C_DRIFT, ec="#8a6a00", lw=.8, zorder=6))
    ax.add_patch(fp.poly_patch(G["added"], fc=fp.C_DRIFT, ec="#1b7a2e", lw=1.4, zorder=6))
    for k, (c, t, j) in enumerate(J, 1):
        ax.add_patch(fp.poly_patch(j["strip"], fc="#6a3fb5", ec="#3d2275", lw=1.0, alpha=.55, zorder=7))
        for v in j["vias"]:
            ax.add_patch(Circle(v, VIA_PAD / 2, fc="#3d2275", ec="white", lw=.6, zorder=8))
        ax.annotate(f"GND jump {k}", j["vias"][0], (j["vias"][0][0] - 6, j["vias"][0][1] + 5.5), fontsize=9.5,
                    weight="bold", color="#3d2275", arrowprops=dict(arrowstyle="->", color="#3d2275", lw=.8),
                    bbox=dict(fc="white", ec="none", alpha=.85))
    c, t, j = opt
    ax.add_patch(fp.poly_patch(j["strip"], fc="none", ec="#3d2275", lw=1.2, ls="--", zorder=7))
    for v in j["vias"]:
        ax.add_patch(Circle(v, VIA_PAD / 2, fc="none", ec="#3d2275", lw=1.0, ls="--", zorder=8))
    ax.annotate("optional 2nd jump: only if the bottom\n\"GND\" copper text moves ~2 mm (it sits there)",
                j["vias"][2], (j["vias"][2][0] - 13, j["vias"][2][1] - 7.5), fontsize=8.5, color="#3d2275",
                arrowprops=dict(arrowstyle="->", color="#3d2275", lw=.8), bbox=dict(fc="white", ec="none", alpha=.85))
    for k in ("GND bottom",):
        b = fp.HV_LABELS_A[k]
        ax.add_patch(Rectangle(b[:2], b[2] - b[0], b[3] - b[1], fc="none", ec="0.35", lw=.8, ls=":", zorder=8))
    ax.add_patch(fp.poly_patch(G["hole13"], fc="none", ec="#c0392b", lw=1.0, ls="--", zorder=8))
    ax.annotate("hole 13 pad: blocks the middle of the line", (610.3, 16.8), (603.5, 20.3), fontsize=8, color="#c0392b",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=.7), bbox=dict(fc="white", ec="none", alpha=.85))
    up, lo = (parts + [None, None])[:2]
    if up is not None:
        ax.text(601, 17.5, "F.Cu GND, connector side", fontsize=9, color="#1e6b2c", weight="bold")
    if lo is not None:
        ax.text(601, -4.4, "F.Cu GND, bottom-GND-pad side", fontsize=9, color="#1f4f8a", weight="bold")
    fp.callout(ax, (614, 10.2), (617.5, 3.0), "drift line (HV) + 3 mm keep-out:\ncuts the F.Cu GND in two",
               color="#8a6a00")
    dc = G["hv"]["d_new"].centroid
    ax.text(dc.x, dc.y, "D", fontsize=13, weight="bold", ha="center", va="center", color="#5a3d00", zorder=9)
    gb = G["hv"]["gnd_bottom"].centroid
    ax.text(gb.x, gb.y, "GND", fontsize=8, weight="bold", ha="center", va="center", rotation=60, color="#5a2d00", zorder=9)
    ax.set_xlim(win[0], win[1])
    ax.set_ylim(win[2], win[3])
    ax.set_aspect("equal")
    ax.grid(lw=.25, alpha=.4)
    ax.tick_params(labelsize=7)
    ax.set_xlabel("x [mm]", fontsize=8)
    ax.set_ylabel("y [mm]", fontsize=8)
    ax.set_title("Top view (corner A): GND on both sides of the drift line, joined by GND jumps",
                 fontsize=11.5, loc="left", weight="bold")

    # section across the line at a jump (schematic, z not to scale)
    bx = fig.add_axes([0.62, 0.42, 0.37, 0.48])
    T = 0.9                                       # drawn board thickness (real 0.2 mm FR4 + resist)
    bx.add_patch(Rectangle((-8, -T), 16, T, fc="#e9efe2", ec="0.5", lw=.6))
    for x0, x1, col in ((-8, -3.4, C_GND_LO), (3.4, 8, C_GND_UP)):
        bx.add_patch(Rectangle((x0, 0), x1 - x0, .18, fc=col, ec="0.3", lw=.5))
    bx.add_patch(Rectangle((-.4, 0), .8, .18, fc=fp.C_DRIFT, ec="#8a6a00", lw=.7))
    bx.add_patch(Rectangle((-5, -T - .18), 10, .18, fc="#6a3fb5", ec="#3d2275", lw=.7, alpha=.75))
    for xv in (-VIA_OFF, VIA_OFF):
        bx.add_patch(Rectangle((xv - .2, -T - .18), .4, T + .36, fc="#3d2275", ec="none"))
    for x0, x1 in ((-3.4, -0.4), (0.4, 3.4)):
        bx.annotate("", (x1, .55), (x0, .55), arrowprops=dict(arrowstyle="<->", color="#1b7a2e", lw=.8))
        bx.text((x0 + x1) / 2, .75, "3 mm", ha="center", fontsize=8, color="#1b7a2e")
    bx.text(0, 1.25, "drift line (HV), F.Cu", ha="center", fontsize=8.5, color="#8a6a00")
    bx.text(-6, .35, "F.Cu GND", ha="center", fontsize=8, color="#1f4f8a")
    bx.text(6, .35, "F.Cu GND", ha="center", fontsize=8, color="#1e6b2c")
    bx.text(0, -T - .7, "B.Cu GND strip (the jump) under the line", ha="center", fontsize=8.5, color="#3d2275")
    bx.text(VIA_OFF + .4, -T / 2, "GND vias", fontsize=8, color="#3d2275", va="center")
    bx.text(-7.8, -T / 2, "PCB", fontsize=8, color="0.35", va="center")
    bx.set_xlim(-8.5, 8.5)
    bx.set_ylim(-2.2, 1.8)
    bx.axis("off")
    bx.set_title("Section across the line at a jump (thickness not to scale)", fontsize=10.5, loc="left", weight="bold")

    lines = [f"GND jump {k}: vias at " + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in j["vias"][:2]) + "\n    and "
             + ", ".join(f"({x:.2f}, {y:.2f})" for x, y in j["vias"][2:]) +
             f"; {c:.1f} mm clear of other copper / holes" for k, (c, t, j) in enumerate(J, 1)]
    fig.text(0.62, 0.36,
             "Why: with the 3 mm keep-out, the drift line splits the F.Cu GND of the corner\n"
             "in two (green / blue); the connector side reaches the GND pad only the long\n"
             "way round the board. A jump joins the two sides locally:\n"
             f"  • 2 GND vias on each side (drill Ø{VIA_D:g}, pad Ø{VIA_PAD:g}), {VIA_OFF:g} mm from the line centre,\n"
             f"     outside the 3 mm keep-out\n"
             f"  • a B.Cu GND strip ({STRIP_W:g} mm + pads) between them, under the line\n"
             "  • the B.Cu GND hatch also runs under the line today, so the vias alone\n"
             "     already join both sides; the strip keeps the jump if that hatch is\n"
             "     pulled back from the line\n"
             "Under the line the HV is separated from the B.Cu GND by the PCB itself\n"
             f"(≈{rg.PCB_T:g} mm FR4): fine as a dielectric, but it adds capacitance.\n\n" + "\n".join(lines),
             fontsize=8.6, va="top", bbox=dict(fc="white", ec=fp.C_EXT_EC, boxstyle="round,pad=.5"))
    h = [Patch(fc=C_GND_UP, ec="0.4", label="F.Cu GND, connector side"),
         Patch(fc=C_GND_LO, ec="0.4", label="F.Cu GND, bottom-GND-pad side"),
         Patch(fc="#6a3fb5", alpha=.55, ec="#3d2275", label="NEW: GND jump (B.Cu strip + vias)"),
         Patch(fc=fp.C_DRIFT, ec="#8a6a00", label="drift net (line, pads)"),
         Line2D([], [], color="#1b7a2e", ls=(0, (2, 2)), label="3 mm keep-out"),
         Patch(fc=fp.C_BCU, alpha=.3, label="B.Cu GND hatch"),
         Patch(fc="white", ec="0.4", label="holes (+ pad of hole 13)")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("PCB – corner A: GND jumps across the drift line (GND continuous on both sides)", fontsize=14, y=.985)
    fig.savefig(os.path.join(fp.FIG, "pcb_corner_A_gnd_jump.png"), dpi=130)
    plt.close(fig)


def table(J, opt):
    path = os.path.join(fp.DATA, "pcb_corner_A_drift.csv")
    rows = [r for r in csv.reader(open(path)) if not r[1].startswith("GND jump")]
    for k, (c, t, j) in enumerate(J, 1):
        for v in j["vias"]:
            rows.append(["add", f"GND jump {k}: GND via (drill {VIA_D:g}, pad {VIA_PAD:g})", "F.Cu + B.Cu + drill",
                         f"{v[0]:.2f}", f"{v[1]:.2f}", "", "", "via centre; in the F.Cu GND, outside the 3 mm keep-out"])
        a, b = (tuple(np.asarray(j["p"]) + VIA_OFF * j["n"]), tuple(np.asarray(j["p"]) - VIA_OFF * j["n"]))
        rows.append(["add", f"GND jump {k}: GND strip {STRIP_W:g} mm (+ via pads) under the drift line", "B.Cu",
                     f"{a[0]:.2f}", f"{a[1]:.2f}", f"{b[0]:.2f}", f"{b[1]:.2f}",
                     "start and end points (not a box); joins the F.Cu GND on both sides of the line"])
    c, t, j = opt
    rows.append(["optional", "GND jump 2 (optional): same as jump 1, vias " + " ".join(f"({x:.2f}, {y:.2f})" for x, y in j["vias"]),
                 "F.Cu + B.Cu + drill", "", "", "", "",
                 "only if the bottom 'GND' copper text (615.37, 3.74)-(619.46, 8.69) moves ~2 mm away from the vias"])
    with open(path, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)


def main():
    G = geometry()
    J, opt = choose(G)
    figure(G, J, opt)
    table(J, opt)
    for k, (c, t, j) in enumerate(J, 1):
        print(f"jump {k}: t={t:.2f} at ({j['p'][0]:.2f}, {j['p'][1]:.2f}), clearance {c:.2f} mm, vias",
              [tuple(round(v, 2) for v in p) for p in j["vias"]])
    print("written pcb_corner_A_gnd_jump.png, rows in data/pcb_corner_A_drift.csv")


if __name__ == "__main__":
    main()
