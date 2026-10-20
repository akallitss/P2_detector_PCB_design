#!/usr/bin/env python3
"""
Where can the two inner alignment crosses (1, 2) go once the PCB gets the NEW screw-hole
pattern (P2_Revision_2026/mechanics, 39 x Ø3.5)?

Obstacles: F.Cu + B.Cu copper (not the GND hatch, not the crosses themselves, not the pads of
today's screw holes, which disappear), the board edge, every drill hole except today's
screw holes, and the new screw holes. For each candidate centre the largest square patch is the
Chebyshev distance to the nearest obstacle, minus CLEAR. Crosses stay mirror-symmetric about
30 deg and under the frame's inner arc (r 96-109).

Writes ../data/inner_marks_search.json.  Run with (ulimit -v 3000000; python3 search_inner_marks.py)
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage

import alignment_marks as am

sys.path.insert(0, os.path.join(am.ROOT, "P2_Revision_2026", "mechanics", "tools"))
import rev_geometry as rg          # noqa: E402  (new screw-hole pattern)

q = am.q
PX = 0.05
CLEAR = 0.5
WIN = (25.0, 120.0, -14.0, 112.0)          # covers the inner arc band
R_RANGE = np.arange(97.0, 108.51, 0.25)
A_RANGE = np.arange(-1.0, 30.01, 0.25)     # the mirror partner is at 60 - angle


def main():
    F = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    D = am.drills()
    old_screw = [(x, y) for x, y, d in D if abs(d - 3.5) < 0.01]

    def keep(p):
        t = type(p).__name__
        if t == "ArcPoly" and len(list(p.outline)) > 5000:          # GND hatch: re-poured anyway
            return False
        if any(am.is_cross_line(p, c) for c in am.CROSSES[:2]):
            return False
        if t == "Circle" and any(math.hypot(p.x - x, p.y - y) < 0.05 for x, y in old_screw):
            return False                                            # pad of a screw hole that goes away
        (x0, y0), (x1, y1) = p.bounding_box()
        return x1 > WIN[0] and x0 < WIN[1] and y1 > WIN[2] and y0 < WIN[3]

    prims = [p for p in F + B if keep(p)]
    print(f"{len(prims)} copper primitives in the window", flush=True)
    obst = q.raster(prims, WIN, PX)
    GX, GY = q.grid(WIN, PX)
    edge = q.raster(E, WIN, PX)
    lab = ndimage.label(~ndimage.binary_dilation(edge, iterations=2))[0]
    seed = lab[int((WIN[3] - 60) / PX), int((100 - WIN[0]) / PX)]   # (100, 60) is on the board
    obst |= lab != seed
    for x, y, d in D:
        if abs(d - 3.5) > 0.01:
            obst |= np.hypot(GX - x, GY - y) <= d / 2
    for _, x, y, _ in rg.new_frame_holes()[0]:
        obst |= np.hypot(GX - x, GY - y) <= rg.SCREW_D / 2
    cheb = ndimage.distance_transform_cdt(~obst, metric="chessboard") * PX - CLEAR
    del GX, GY, obst, edge, lab

    def half_at(x, y):
        return float(cheb[int(round((WIN[3] - y) / PX)), int(round((x - WIN[0]) / PX))])

    best = []
    for r in R_RANGE:
        for a in A_RANGE:
            t1, t2 = math.radians(a), math.radians(60 - a)
            p1, p2 = (r * math.cos(t1), r * math.sin(t1)), (r * math.cos(t2), r * math.sin(t2))
            h = min(half_at(*p1), half_at(*p2))
            best.append((h, r, a, p1, p2))
    best.sort(reverse=True)
    today = [half_at(*c) for c in am.CROSSES[:2]]
    prop = [half_at(73.72, 68.92), half_at(97.50, 29.66)]
    res = {"rule": f"largest square patch half-size, {CLEAR} mm from copper/holes/edge, with the NEW screw holes",
           "today_positions_half_mm": [round(v, 2) for v in today],
           "earlier_proposal_half_mm": [round(v, 2) for v in prop],
           "best": [{"patch_half_mm": round(h, 2), "r_mm": round(r, 2), "angle_deg": round(a, 2),
                     "cross_2": [round(v, 2) for v in p1], "cross_1": [round(v, 2) for v in p2]}
                    for h, r, a, p1, p2 in best[:10]]}
    json.dump(res, open(os.path.join(am.OUT, "data", "inner_marks_search.json"), "w"), indent=2)
    print(json.dumps(res, indent=1)[:1800])


if __name__ == "__main__":
    main()
