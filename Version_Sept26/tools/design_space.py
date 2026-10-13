#!/usr/bin/env python3
"""The pillar design space for the P2 basket, with the reference designs and
the proposed zones placed on it."""
from __future__ import annotations

import csv
import json
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import gerber_io as gio
import p2_geometry as pg

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QC"))
MASKS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                      "Insulation_masks"))
GROWTH = 0.05
BUDGET = 3.0

INK = "#1f2328"
MUTED = "#6b7280"
GRID = "#e5e7eb"
# one hue, light -> dark: the curves are ordered by pillar diameter
RAMP = ["#9ec5fe", "#6ea8fe", "#3d8bfd", "#0d6efd", "#0a58ca", "#084298"]


def hex_cov(d_eff, pitch):
    return 100 * 0.9069 * (d_eff / pitch) ** 2


def sq_cov(d_eff, pitch):
    return 100 * (math.pi / 4) * (d_eff / pitch) ** 2


def load(variant):
    p = os.path.join(MASKS, variant, "zone_report.csv")
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p)))


def main():
    os.makedirs(OUT, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "text.color": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.spines.top": False, "axes.spines.right": False})

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.6))

    # ---------------- left: dead area vs pitch ----------------------------
    pitch = np.linspace(1.6, 8.0, 400)
    dias = [0.35, 0.40, 0.50, 0.65, 0.80]
    label_x = [2.4, 3.3, 4.3, 5.4, 6.6]
    for c, d, xl in zip(RAMP[1:], dias, label_x):
        y = hex_cov(d + GROWTH, pitch)
        axL.plot(pitch, y, color=c, lw=2)
        axL.annotate(f"Ø{d:.2f} mm", (xl, hex_cov(d + GROWTH, xl)), color=c,
                     fontsize=9, xytext=(5, 5 if d > 0.35 else -13),
                     textcoords="offset points")

    axL.axhline(BUDGET, color="#b3261e", lw=1.4, ls="--")
    axL.annotate("3 % dead-area budget", (7.9, BUDGET), ha="right", va="bottom",
                 color="#b3261e", fontsize=9)

    # the two existing designs, re-measured from their gerbers
    poly = pg.active_outline()
    area = gio.polygon_area(poly)
    for label, (c, d), cov_fn, marker in [
            ("CERN bulk (square 2.0 mm)", pg.cern_pillars(), sq_cov, "s"),
            ("CEA V2 (hex 4.0 mm)", pg.cea_pillars(), hex_cov, "D")]:
        n = pg.point_in_polygon(c, poly).sum()
        cov = 100 * n * math.pi * ((d + GROWTH) / 2) ** 2 / area
        p = 2.0 if marker == "s" else 4.0
        axL.plot([p], [cov], marker, ms=9, mfc="white", mec=INK, mew=1.6, zorder=6)
        axL.annotate(f"{label}\n{cov:.2f} %", (p, cov), xytext=(8, 8),
                     textcoords="offset points", fontsize=9, color=INK)

    for v, mk in [("V3A", "o"), ("V3B", "^"), ("V3C", "*")]:
        rows = load(v)
        if not rows:
            continue
        axL.plot([float(r["pitch_mm"]) for r in rows],
                 [100 * float(r["dead_area_effective"]) for r in rows],
                 mk, ms=9 if mk != "*" else 13, mfc="#0d6efd", mec="white",
                 mew=1.0, ls="none", label=f"{v} zones", zorder=5)

    axL.set_xlabel("pillar pitch (hexagonal nearest-neighbour) [mm]")
    axL.set_ylabel("dead area [%]")
    axL.set_ylim(0, 8)
    axL.set_xlim(1.6, 8)
    axL.grid(color=GRID, lw=0.8)
    axL.set_axisbelow(True)
    axL.legend(frameon=False, loc="upper right", fontsize=9)
    axL.set_title("Dead area vs pitch, pillars grown by 50 µm", loc="left",
                  fontsize=11, color=INK)

    # ---------------- right: what you buy with that dead area -------------
    poly = pg.active_outline()
    area = gio.polygon_area(poly)
    for v, mk, lab in [("V3A", "o", "V3A iso-3 %"), ("V3B", "^", "V3B graded"),
                       ("V3C", "*", "V3C two-factor")]:
        rows = load(v)
        if not rows:
            continue
        x = [float(r["max_unsupported_radius_mm"]) for r in rows]
        y = [100 * float(r["dead_area_effective"]) for r in rows]
        axR.plot(x, y, mk, ms=9 if mk != "*" else 13, mfc="#0d6efd", mec="white",
                 ls="none", label=lab, zorder=5)
        dy = {"V3A": 9, "V3B": -12, "V3C": -2}[v]
        for r, xx, yy in zip(rows, x, y):
            axR.annotate(f"{v[-1]}{r['zone']}", (xx, yy), xytext=(6, dy),
                         textcoords="offset points", fontsize=8, color=MUTED)

    # references, re-measured
    refs = []
    for label, (c, d), mk, lat, pitchmm in [
            ("CERN", pg.cern_pillars(), "s", "sq", 2.0),
            ("CEA V2", pg.cea_pillars(), "D", "hex", 4.0)]:
        n = pg.point_in_polygon(c, poly).sum()
        refs.append((label, pitchmm,
                     100 * n * math.pi * ((d + GROWTH) / 2) ** 2 / area, mk, lat))
    for label, pitchmm, cov, mk, lat in refs:
        span = pitchmm / 2 if lat == "sq" else pitchmm / math.sqrt(3)
        axR.plot([span], [cov], mk, ms=9, mfc="white", mec=INK, mew=1.6, zorder=6)
        axR.annotate(label, (span, cov), xytext=(8, 4), textcoords="offset points",
                     fontsize=9, color=INK)
    axR.axhline(BUDGET, color="#b3261e", lw=1.4, ls="--")
    axR.set_xlabel("largest unsupported mesh span (radius) [mm]")
    axR.set_ylabel("dead area [%]")
    axR.grid(color=GRID, lw=0.8)
    axR.set_axisbelow(True)
    axR.legend(frameon=False, loc="upper right", fontsize=9)
    axR.set_title("The trade-off: efficiency loss vs mesh support", loc="left",
                  fontsize=11, color=INK)

    fig.suptitle("P2 basket bulk insulation - pillar design space", x=0.005,
                 ha="left", fontsize=13)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"design_space.{ext}"), dpi=160,
                    bbox_inches="tight")
    print("written", os.path.join(OUT, "design_space.png"))


if __name__ == "__main__":
    main()
