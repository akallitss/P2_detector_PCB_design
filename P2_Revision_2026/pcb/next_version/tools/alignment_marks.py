#!/usr/bin/env python3
"""
Alignment crosses of the P2 basket PCB (F.Cu + B.Cu) and the insulation masks:
find them, and measure how large each can grow without touching anything.

Obstacles (all layers that matter for a cross on the board):
  F.Cu and B.Cu copper (the crosses themselves excluded), drill holes, the
  board outline.  The frame footprint and the masks are reported, not used
  as limits.

    python3 alignment_marks.py      -> ../data/alignment_marks.json, ../figures/alignment_*.png
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", "..", ".."))   # Detector_Drawings/
FAB = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2")
MASKS = os.path.join(ROOT, "Version_Sept26", "Insulation_masks", "V3B_final")
sys.path.insert(0, os.path.join(ROOT, "P2_Revision_2026", "pcb", "drift_pad_B2", "tools"))
import qc_b2 as q                          # noqa: E402  (polarity-aware rasteriser + loader)

CROSSES = [(70.80, 66.19), (93.67, 28.50), (635.63, 83.91), (391.22, 507.00)]
HALF = 22.0                                 # window half-size, mm
PX = 0.02
CLEAR = 1.0                                 # wanted gap from any copper / hole / edge, mm


def is_cross_line(p, c):
    if type(p).__name__ != "Line":
        return False
    return (abs(p.x1 - c[0]) < 0.01 and abs(p.y1 - c[1]) < 0.01 and
            math.hypot(p.x2 - p.x1, p.y2 - p.y1) < 1.6 and abs(p.width - 0.12) < 0.01)


def drills():
    out, tools, cur = [], {}, None
    for l in open(os.path.join(FAB, "NCDrill", "P2_BASKET.drl")):
        l = l.strip()
        m = re.match(r"^T(\d+)C([\d.]+)$", l)
        if m:
            tools[m.group(1)] = float(m.group(2)); continue
        m = re.match(r"^T(\d+)$", l)
        if m:
            cur = m.group(1); continue
        m = re.match(r"^X([-\d.]+)Y([-\d.]+)$", l)
        if m and cur:
            out.append((float(m.group(1)), float(m.group(2)), tools[cur]))
    return np.array(out)


def main():
    F = q.load(os.path.join(FAB, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(FAB, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    M1 = q.load(os.path.join(MASKS, "P2_BASKET-Mask_M1_V3B_final.gbr"))
    M2 = q.load(os.path.join(MASKS, "P2_BASKET-Mask_M2_V3B_final.gbr"))
    D = drills()
    res = []
    for c in CROSSES:
        win = (c[0] - HALF, c[0] + HALF, c[1] - HALF, c[1] + HALF)
        GX, GY = q.grid(win, PX)
        hatch = lambda p: type(p).__name__ == "ArcPoly" and len(list(p.outline)) > 5000
        # hard copper: everything except the crosses and the GND hatch pour (which can be re-poured
        # round a bigger mark); the hatch is drawn separately for the picture
        f = q.raster([p for p in F if not is_cross_line(p, c) and not hatch(p)], win, PX)
        b = q.raster([p for p in B if not is_cross_line(p, c) and not hatch(p)], win, PX)
        fh = q.raster([p for p in F if hatch(p)], win, PX)
        bh = q.raster([p for p in B if hatch(p)], win, PX)
        edge = q.raster(E, win, PX)
        # board = the region of the window connected to the cross, bounded by the outline
        inside = ndimage.label(~ndimage.binary_dilation(edge, iterations=2))[0]
        iy, ix = int((win[3] - c[1]) / PX), int((c[0] - win[0]) / PX)
        board = inside == inside[iy, ix]
        hole = np.zeros_like(f)
        for x, y, dia in D:
            if abs(x - c[0]) < HALF + 3 and abs(y - c[1]) < HALF + 3:
                hole |= np.hypot(GX - x, GY - y) <= dia / 2
        obst = f | b | hole | ~board
        dist = ndimage.distance_transform_edt(~obst) * PX       # mm to the nearest obstacle
        # largest arm length along each axis, keeping CLEAR from the arm's centreline band
        arms = {}
        for name, (dx, dy) in {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}.items():
            L = 0.0
            for s in np.arange(0, HALF - 1, PX):
                x, y = c[0] + dx * s, c[1] + dy * s
                if dist[int((win[3] - y) / PX), int((x - win[0]) / PX)] < CLEAR:
                    break
                L = s
            arms[name] = round(L, 2)
        free_r = float(dist[iy, ix])                            # free circle round the centre
        m1 = q.raster(M1, win, PX); m2 = q.raster(M2, win, PX)
        res.append({"centre": c, "r_mm": round(math.hypot(*c), 1),
                    "theta_deg": round(math.degrees(math.atan2(c[1], c[0])), 2),
                    "free_radius_mm": round(free_r, 2), "max_arm_mm": arms,
                    "symmetric_max_arm_mm": min(arms.values()),
                    "mask_M1_dark_at_centre": bool(m1[iy, ix]), "mask_M2_dark_at_centre": bool(m2[iy, ix])})
        print(res[-1])
        # picture
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 7))
        img = np.zeros(f.shape + (3,)); img[...] = (0.93, 0.93, 0.9)
        img[fh | bh] = (0.88, 0.82, 0.72); img[~board] = (0.75, 0.75, 0.78); img[b] = (0.55, 0.7, 0.9); img[f] = (0.85, 0.6, 0.3); img[hole] = (0.2, 0.2, 0.2)
        ax.imshow(img, extent=win)
        a = res[-1]["max_arm_mm"]
        ax.plot([c[0] - a["-x"], c[0] + a["+x"]], [c[1], c[1]], "r-", lw=2)
        ax.plot([c[0], c[0]], [c[1] - a["-y"], c[1] + a["+y"]], "r-", lw=2)
        ax.plot([c[0] - 1.5, c[0] + 1.5], [c[1], c[1]], "k-", lw=1); ax.plot([c[0], c[0]], [c[1] - 1.5, c[1] + 1.5], "k-", lw=1)
        ax.set_title(f"cross at {c}: max arms {a}", fontsize=8)
        fig.savefig(os.path.join(OUT, "figures", f"alignment_{c[0]:.0f}_{c[1]:.0f}.png"), dpi=90, bbox_inches="tight")
        plt.close(fig)
    json.dump(res, open(os.path.join(OUT, "data", "alignment_marks.json"), "w"), indent=2)


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    main()
