#!/usr/bin/env python3
"""
Checks of the 12 Nov PCB (P2_PCB=nov12) before the figures:
  1. the Ø4.56 screw pads are the same on F.Cu and B.Cu
  2. the drill map (P2-V1_drl_map.gbr) symbols sit on the screw pads + the 9 Nov connector holes
  3. which screw holes moved since 9 Nov
  4. alignment with the frame V3 holes, clearance to the O-ring groove and the gas channel
Run with  (ulimit -v 2500000; P2_PCB=nov12 python3 check_nov12.py)
"""
import math
import os

os.environ.setdefault("P2_PCB", "nov12")
import numpy as np
from gerbonara.graphic_objects import Arc

import final_geometry as G
import frame_features as FF

top, bot = G.screw_pads("Top"), G.screw_pads("Bottom")
print(f"1. screw pads: F.Cu {len(top)}, B.Cu {len(bot)}, identical: {top == bot}")

# 2. drill map: one symbol per hole, its shape and line width depend on the tool.  Ø3.5: square of
# 0.35 lines; Ø2.2: 0.22 lines; Ø3.2: circle r 1.6 (two arcs, 0.32).  The 0.1 lines/arcs are the outline.
from collections import defaultdict
from gerbonara.graphic_objects import Line
cent = {}
segs = defaultdict(list)
for o in G._gerber("drl_map").objects:
    w = round(o.aperture.diameter, 2) if hasattr(o.aperture, "diameter") else None
    if isinstance(o, Arc) and w == 0.32:
        cent.setdefault("circle r1.6 (0.32)", set()).add((round(o.x1 + o.cx, 2), round(o.y1 + o.cy, 2)))
    elif isinstance(o, Line) and w in (0.35, 0.22):
        segs[w].append(((o.x1 + o.x2) / 2, (o.y1 + o.y2) / 2))
for w, mids in segs.items():
    mids = np.array(mids)
    used, groups = np.zeros(len(mids), bool), []
    for i in range(len(mids)):                         # group line midpoints of one symbol (< 2.5 mm apart)
        if used[i]:
            continue
        g = np.hypot(*(mids - mids[i]).T) < 2.5
        used |= g
        groups.append(mids[g].mean(0))
    cent[f"lines {w}"] = {(round(x, 2), round(y, 2)) for x, y in groups}
H = G.pcb_holes()
known = {"screw Ø3.5 (pads)": top, "Ø2.2 (9 Nov)": H[5]["xy"], "Ø3.2 (9 Nov)": H[6]["xy"],
         "vias/pins 0.3-0.4": H[1]["xy"] + H[2]["xy"] + H[3]["xy"]}
for r, pts in cent.items():
    pts = np.array(sorted(pts))
    best = {}
    for k, ref in known.items():
        ref = np.array(ref)
        d = np.array([np.hypot(*(ref - p).T).min() for p in pts])
        best[k] = (int((d < 0.05).sum()), len(pts))
    print(f"2. drill-map symbol {r}: {len(pts)} centres; on:", {k: v[0] for k, v in best.items() if v[0]})
unmatched = []
allref = np.array([q for v in known.values() for q in v])
for r, pts in cent.items():
    for p in pts:
        if np.hypot(*(allref - p).T).min() > 0.05:
            unmatched.append((r, p))
print("   drill-map centres on none of these:", len(unmatched), unmatched[:10])

# 3. moved holes
old = G._drill_file()[4]["xy"]
moved = [p for p in top if min(math.dist(p, q) for q in old) > 0.05]
gone = [q for q in old if min(math.dist(p, q) for p in top) > 0.05]
print(f"3. screw holes: 9 Nov {len(old)} -> 12 Nov {len(top)}; new/moved {len(moved)}, removed/moved {len(gone)}")

# 4. frame
F = G.frame()
outer, window = G.frame_shapes(F)
fr = [(x, y) for x, y, d in F["holes"]]
feat = FF.features(window)
print("   gas channel angle spans:", feat["gas_spans"])
al = [p for p in top if min(math.dist(p, q) for q in fr) < 0.1]
print(f"4. aligned with a frame hole: {len(al)} / {len(top)} PCB; frame holes {len(fr)}; "
      f"frame holes without PCB hole: {sum(1 for q in fr if min(math.dist(p, q) for p in top) > 0.1)}")
worst = sorted(((min(math.dist(p, q) for q in fr), p) for p in top), reverse=True)[:5]
print("   largest PCB-to-nearest-frame-hole distances:", [(round(d, 3), p) for d, p in worst])
for name in ("groove", "gas"):
    c = sorted((FF.clearance(p, 3.5, feat[name]), p) for p in top)
    print(f"   {name}: min clearance {c[0][0]:.2f} mm at {c[0][1]}; holes < 0.5 mm: {sum(1 for v, _ in c if v < 0.5)}")
cf = sorted((FF.clearance(q, 3.5, feat['groove']), q) for q in fr)
print(f"   frame holes to groove: min {cf[0][0]:.2f}; to gas: {min(FF.clearance(q, 3.5, feat['gas']) for q in fr):.2f}")
