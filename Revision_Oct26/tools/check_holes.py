#!/usr/bin/env python3
"""Clearance check of the NEW frame screw holes (edge-to-edge distances, mm)."""
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
import numpy as np
import rev_geometry as rg

G = rg.build()
new, _ = rg.new_frame_holes()
r = rg.SCREW_D / 2
pads = unary_union(G["pads"]["A"] + G["pads"]["B"])
opn = unary_union([G["op"]["A"], G["op"]["B"]])
pcb = rg.pcb_outline()
ext_holes = [(Point(x, y), d) for x, y, d in G["holes"]]
gas = [LineString([tuple(rg.GAS_TOP_PT), tuple(rg.GAS_TOP_PT + 15 * rg.GAS_TOP_DIR)]),
       LineString([tuple(rg.GAS_IN_PT + 3 * rg.GAS_IN_DIR * -1), tuple(rg.GAS_IN_PT + 15 * rg.GAS_IN_DIR)])]
rows = []
for no, x, y, e in new:
    p = Point(x, y)
    rows.append((no, e,
                 pads.distance(p) - r, opn.distance(p) - r if not opn.contains(p) else -1,
                 pcb.exterior.distance(p) - r,
                 min(q.distance(p) - r - d / 2 for q, d in ext_holes),
                 min(g.distance(p) - r - rg.GAS_D / 2 for g in gas)))
names = ["HV pads", "HV opening", "PCB edge", "conn. hole", "gas bore"]
mins = np.array([r[2:] for r in rows]).min(0)
for nm, v in zip(names, mins):
    worst = min(rows, key=lambda r: r[2 + names.index(nm)])
    print(f"min to {nm:11s}: {v:6.2f} mm   (hole {worst[0]}, {worst[1]})")
