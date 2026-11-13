#!/usr/bin/env python3
"""
Readers for the FINAL files only (Final_Version/), all brought into one coordinate system:
origin = centre of the arcs, x along the bottom straight side, mm, top view.

  PCB    Final_Version/PCB-Nov2026/K55V1/_FABRICATION/
           NCDRILL/P2_V1.drl            holes (KiCad page coordinates -> shifted by the Gerber origin)
           GERBER/P2_V1-Edge_Cuts.gbr   outline
           GERBER/P2_V1-Top.gbr, -Bottom.gbr   copper (signal lines, pads)
           GERBER/P2_V1-ENIG.gbr        gold pads (HV pads)
  PCB    (P2_PCB=nov12) Final_Version/PCB-12Nov2026/GERBER/P2-V1_*.gbr: holes moved, no drill file
  frame  Final_Version/drift_frame/P2_Frame_V3.dxf   (block SE, arc centre at (80.572, 41.301))

Copper is converted once to shapely polygons and cached in ../data/copper_cache.pkl (small).
Keep every script that imports this under  ulimit -v 2500000.
"""
import collections
import math
import os
import pickle
import re

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import polygonize, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
VAL = os.path.normpath(os.path.join(HERE, ".."))                 # validation_final_version/
FINAL = os.path.normpath(os.path.join(VAL, ".."))               # Final_Version/
# Which PCB delivery: P2_PCB=nov09 (default, PCB-Nov2026/K55V1, with drill file) or
# P2_PCB=nov12 (PCB-12Nov2026/GERBER, holes moved by the designer; Gerbers only, no drill file).
PCB = os.environ.get("P2_PCB", "nov09")
FRAME_DXF = os.path.join(FINAL, "drift_frame", "P2_Frame_V3.dxf")
if PCB == "nov12":
    FAB = os.path.join(FINAL, "PCB-12Nov2026")
    GBR_FILES = {"Top": "P2-V1_Top.gbr", "Bottom": "P2-V1_Bottom.gbr", "Edge_Cuts": "P2-V1_Bottom-Edge_Cuts.gbr",
                 "ENIG": "P2-V1_ENIG-Bottom.gbr", "drl_map": "P2-V1_drl_map.gbr"}
    GBR = os.path.join(FAB, "GERBER", "%s")
    FIG = os.path.join(VAL, "figures", "PCB-12Nov2026")
    DATA = os.path.join(VAL, "data", "PCB-12Nov2026")
else:
    FAB = os.path.join(FINAL, "PCB-Nov2026", "K55V1", "_FABRICATION")
    GBR_FILES = {k: f"P2_V1-{k}.gbr" for k in ("Top", "Bottom", "Edge_Cuts", "ENIG", "drl_map")}
    GBR = os.path.join(FAB, "GERBER", "%s")
    FIG = os.path.join(VAL, "figures")
    DATA = os.path.join(VAL, "data")
DRL = os.path.join(FINAL, "PCB-Nov2026", "K55V1", "_FABRICATION", "NCDRILL", "P2_V1.drl")
CACHE = os.path.join(VAL, "data", f"copper_cache_{PCB}.pkl")
SCREW_PAD_D = 4.56          # copper pad round each plated Ø3.5 screw hole (F.Cu and B.Cu)

# Gerber header "%TF.SameCoordinates,PXe1e70c6PY26a226f6*%": the Gerbers are written relative to
# this origin (nm), the drill file is not.  Checked: the shifted drill holes sit on the arc centre.
GERBER_ORIGIN = (0xE1E70C6 / 1e6, 0x26A226F6 / 1e6)            # (236.876, 648.163) mm
FRAME_CENTRE = (80.572, 41.301)                                 # centre of all frame arcs in the DXF


# ---------------------------------------------------------------- PCB
def _drill_file():
    """{tool: dict(d=, plated=, xy=[(x, y)])} from the 9 Nov drill file."""
    tools, cur, plated = {}, None, None
    for line in open(DRL):
        if "TA.AperFunction" in line:
            plated = "NonPlated" not in line
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            tools[int(m.group(1))] = dict(d=float(m.group(2)), plated=plated, xy=[])
            continue
        m = re.match(r"^T(\d+)\s*$", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"^X([-\d.]+)Y([-\d.]+)", line)
        if m and cur:
            tools[cur]["xy"].append((float(m.group(1)) - GERBER_ORIGIN[0], float(m.group(2)) + GERBER_ORIGIN[1]))
    return tools


def screw_pads(name="Top"):
    """Centres of the Ø4.56 copper pads = the plated Ø3.5 screw holes."""
    from gerbonara.graphic_objects import Flash
    from gerbonara.utils import MM
    out = []
    for o in _gerber(name).objects:
        if isinstance(o, Flash) and abs(getattr(o.aperture, "diameter", 0) - SCREW_PAD_D) < 1e-3:
            out.append((round(o.x, 4), round(o.y, 4)))
    return sorted(set(out))


def pcb_holes():
    """{tool: dict(d=, plated=, xy=[(x, y)])} in the common coordinates.  Tool 4 = Ø3.5 screw holes,
    5 = Ø2.2 and 6 = Ø3.2 connector supports.  nov12 has no drill file: the screw holes are the
    centres of their Ø4.56 pads (F.Cu = B.Cu checked in check_nov12.py); the connector-support holes
    are taken from the 9 Nov drill file (check_nov12.py compares them with the 12 Nov drill map)."""
    tools = _drill_file()
    if PCB == "nov12":
        tools[4] = dict(d=3.5, plated=True, xy=screw_pads("Top"))
    return tools


def _gerber(name):
    from gerbonara import GerberFile
    return GerberFile.open(GBR % GBR_FILES[name])


def _prim_polys(obj):
    from gerbonara.graphic_primitives import ArcPoly, Circle, Line, Rectangle
    from gerbonara.utils import MM
    out = []
    for p in obj.to_primitives(MM):
        if isinstance(p, Line):
            out.append(LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, 8))
        elif isinstance(p, Circle):
            out.append(Point(p.x, p.y).buffer(p.r, 16))
        elif isinstance(p, Rectangle):
            w, h = p.w / 2, p.h / 2
            c, s = math.cos(p.rotation), math.sin(p.rotation)
            out.append(Polygon([(p.x + c * a - s * b, p.y + s * a + c * b) for a, b in ((-w, -h), (w, -h), (w, h), (-w, h))]))
        elif isinstance(p, ArcPoly) and len(p.outline) > 2:
            out.append(Polygon(list(p.outline)).buffer(0))
    return out


def pcb_outline():
    """Board outline from Edge_Cuts, without the production-panel border (the largest loop)."""
    from gerbonara.graphic_objects import Arc, Line
    from gerbonara.utils import MM
    segs = []
    for o in _gerber("Edge_Cuts").objects:
        if isinstance(o, Line):
            segs.append(LineString([(o.x1, o.y1), (o.x2, o.y2)]))
        elif isinstance(o, Arc):
            ls = o.approximate(max_error=0.005, unit=MM)
            segs.append(LineString([(l.x1, l.y1) for l in ls] + [(ls[-1].x2, ls[-1].y2)]))
    polys = sorted(polygonize(unary_union(segs)), key=lambda P: -P.area)
    return polys


SIGNAL_W = (0.125, 0.188)       # track widths of the signal lines (strip -> connector)
PROFILE_W = 0.1                 # board outline repeated on the copper layers: dropped
ZONE_MIN_VERTICES = 5000        # GND hatch zones (one huge region per layer)


def copper():
    """{'Top': {'signal', 'zone', 'other'}, 'Bottom': {...}, 'ENIG': {'other'}}: lists of Polygons.
    Cached in ../data/copper_cache.pkl."""
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    from gerbonara.graphic_objects import Arc, Line, Region
    out = {}
    for name in ("Top", "Bottom", "ENIG"):
        d = {"signal": [], "zone": [], "other": []}
        for o in _gerber(name).objects:
            if getattr(o, "polarity_dark", True) is False:
                continue
            if isinstance(o, (Line, Arc)):
                w = round(o.aperture.diameter, 3)
                if w == PROFILE_W:
                    continue
                key = "signal" if w in SIGNAL_W else "other"
            elif isinstance(o, Region) and len(o.outline) > ZONE_MIN_VERTICES:
                key = "zone"
            else:
                key = "other"
            d[key] += [P for P in _prim_polys(o) if not P.is_empty]
        out[name] = d
    pickle.dump(out, open(CACHE, "wb"))
    return out


# ---------------------------------------------------------------- frame
def _frame_block():
    import ezdxf
    return ezdxf.readfile(FRAME_DXF).blocks["SE"]


def frame():
    """dict(holes=[(x, y, d)], lines=[LineString], loops=[Polygon] by decreasing area, solid=Polygon)
    solid = frame material seen from the top: outer contour minus window (holes punched)."""
    from ezdxf import path as ep
    b = _frame_block()
    cx, cy = FRAME_CENTRE
    holes, lines = [], []
    for e in b:
        if e.dxftype() == "CIRCLE":
            holes.append((e.dxf.center[0] - cx, e.dxf.center[1] - cy, 2 * e.dxf.radius))
        else:
            lines.append(LineString([(q[0] - cx, q[1] - cy) for q in ep.make_path(e).flattening(0.01)]))
    loops = sorted(polygonize(unary_union(lines)), key=lambda P: -P.area)
    return dict(holes=holes, lines=lines, loops=loops)


def frame_solid(F, outer, window):
    s = outer.difference(window)
    return s.difference(unary_union([Point(x, y).buffer(d / 2, 32) for x, y, d in F["holes"]]))


# ---------------------------------------------------------------- closed shapes from line work
def _edge_cut_segments():
    from gerbonara.graphic_objects import Arc, Line
    from gerbonara.utils import MM
    segs = []
    for o in _gerber("Edge_Cuts").objects:
        if isinstance(o, Line):
            segs.append(LineString([(o.x1, o.y1), (o.x2, o.y2)]))
        elif isinstance(o, Arc):
            ls = o.approximate(max_error=0.005, unit=MM)
            segs.append(LineString([(l.x1, l.y1) for l in ls] + [(ls[-1].x2, ls[-1].y2)]))
    return segs


def _filled_loops(segs, tol=0.03):
    """Line work -> filled closed loops (endpoints that miss by < 2 tol are joined)."""
    ink = unary_union(segs).buffer(tol, 4)
    out = []
    for g in getattr(ink, "geoms", [ink]):
        out.append(Polygon(g.exterior).buffer(-tol, 4))          # undo the tolerance: exact line position
        out += [Polygon(r).buffer(tol, 4) for r in g.interiors]
    return ink, out


def board(close=12.0, tab=1.0):
    """The PCB itself.  Edge_Cuts = panel rectangle + routing slots with break-off tabs (gaps up
    to ~20 mm).  The slots are closed morphologically only to find which piece is the board; the
    board edge itself is the exact inner edge of the slots (the tabs keep a `tab` mm stub)."""
    ink, loops = _filled_loops(_edge_cut_segments())
    rect = max(loops, key=lambda P: P.area)
    slots = unary_union([P for P in loops if P.area < 0.5 * rect.area]).union(ink)
    closed = slots.buffer(close, 16).buffer(-close, 16)
    rest = rect.difference(closed.union(slots))
    centre = Point(300, 200)
    piece = next(g for g in getattr(rest, "geoms", [rest]) if g.contains(centre))
    exact = rect.difference(slots).intersection(piece.buffer(tab, 16))
    b = next(g for g in getattr(exact, "geoms", [exact]) if g.contains(centre))
    return b.buffer(0.03, 4, join_style=2)      # the slot line work was thickened by 0.03 (see _filled_loops)


def frame_shapes(F):
    """(outer, window): outer contour filled, and the window (the loop around the active area)."""
    ink, loops = _filled_loops(F["lines"], 0.02)
    outer = max(loops, key=lambda P: P.area)
    centre = Point(300, 200)
    window = min((P for P in loops if P.contains(centre) and P.area < outer.area - 1), key=lambda P: P.area)
    return outer, window
