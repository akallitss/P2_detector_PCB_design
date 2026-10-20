"""Largest square resist patch and cross that fit at each alignment-mark position (hard copper, holes, edge)."""
import os, sys, math, json, numpy as np
from scipy import ndimage
import alignment_marks as am
q = am.q
F = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-F_Cu.gbr"))
B = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-B_Cu.gbr"))
E = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
D = am.drills()
hatch = lambda p: type(p).__name__ == "ArcPoly" and len(list(p.outline)) > 5000
SHIFT_INNER = 4.0          # move the inner crosses this far radially outwards, away from the board-edge slot
CLEAR = 0.5                # patch / cross to the nearest pad, trace, hole or board edge
out = []
for c0 in am.CROSSES:
    r0 = math.hypot(*c0)
    c = tuple(np.array(c0) + (np.array(c0) / r0 * SHIFT_INNER if r0 < 200 else 0))
    win = (c[0] - am.HALF, c[0] + am.HALF, c[1] - am.HALF, c[1] + am.HALF)
    GX, GY = q.grid(win, am.PX)
    hard = q.raster([p for p in F + B if not am.is_cross_line(p, c0) and not hatch(p)], win, am.PX)
    edge = q.raster(E, win, am.PX)
    lab = ndimage.label(~ndimage.binary_dilation(edge, iterations=2))[0]
    iy, ix = int((win[3] - c[1]) / am.PX), int((c[0] - win[0]) / am.PX)
    obst = hard | (lab != lab[iy, ix])
    for x, y, dd in D:
        if abs(x - c[0]) < am.HALF + 3 and abs(y - c[1]) < am.HALF + 3:
            obst |= np.hypot(GX - x, GY - y) <= dd / 2
    # Chebyshev distance from the centre to the nearest obstacle = largest square half-size
    cheb = np.maximum(np.abs(GX - c[0]), np.abs(GY - c[1]))
    P = float(cheb[obst].min()) - CLEAR
    out.append({"original_centre": c0, "proposed_centre": [round(v, 2) for v in c],
                "moved_mm": SHIFT_INNER if r0 < 200 else 0.0,
                "max_square_patch_half_mm": round(P, 2),
                "max_cross_arm_mm_in_patch": round(P - 1.5, 2)})
    print(out[-1])
json.dump(out, open(os.path.join(am.OUT, "data", "alignment_fit.json"), "w"), indent=2)
