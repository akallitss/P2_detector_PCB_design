"""
Frame V3 features that a screw hole must not reach, built from the DXF line work (same offsets as
today's frame STEP, P2_Revision_2026/mechanics/data/frame_section_r27.json):

  O-ring groove   band 4.58 – 5.49 mm outside the window edge, all round (DXF lines + corner arcs
                  r 4.58 / 5.49 round the window corners)
  gas channel     internal channel (z 2.5 – 4.5 in the STEP) along both arcs only:
                  outer arc r 605.5 – 607.5, inner arc r 102.5 – 104.5 (DXF arcs, their angle range)
"""
import math

from shapely.geometry import Point, Polygon

import final_geometry as G

GROOVE = (4.58, 5.49)


def _arcs():
    b = G._frame_block()
    cx, cy = G.FRAME_CENTRE
    out = []
    for e in b.query("ARC"):
        out.append((round(e.dxf.radius, 2), e.dxf.center[0] - cx, e.dxf.center[1] - cy, e.dxf.start_angle, e.dxf.end_angle))
    return out


def _sector(r0, r1, a0, a1, n=600):
    a = [math.radians(a0 + (a1 - a0) * k / n) for k in range(n + 1)]
    return Polygon([(r1 * math.cos(t), r1 * math.sin(t)) for t in a] +
                   [(r0 * math.cos(t), r0 * math.sin(t)) for t in reversed(a)])


def features(window):
    groove = window.buffer(GROOVE[1], 64).difference(window.buffer(GROOVE[0], 64))
    arcs = _arcs()

    def span(r):
        A = [(a0 if a0 < 180 else a0 - 360, a1) for rr, x, y, a0, a1 in arcs if abs(rr - r) < 0.02 and math.hypot(x, y) < 0.01]
        return min(a for a, _ in A), max(b for _, b in A)
    oa, ia = span(607.5), span(102.5)
    gas = _sector(605.5, 607.5, *oa).union(_sector(102.5, 104.5, *ia))
    return dict(groove=groove, gas=gas, gas_spans=dict(outer=oa, inner=ia))


def clearance(xy, d, feat):
    """Edge-to-edge distance [mm] from a hole of diameter d to the feature (negative: they overlap)."""
    c = Point(xy).buffer(d / 2, 64)
    if c.intersects(feat):
        return -c.intersection(feat).area                      # overlap area as a negative number
    return c.distance(feat)
