"""
Geometry of the P2 basket taken straight out of the Apr-26 fabrication data.

Everything below is *measured*, not assumed:
  * the fan apex, the connector radius and the 10 connector angles come from the
    rotated-rectangle apertures of P2_BASKET-F_ENIG_Finition.gbr,
  * the active-area outline comes from the inner closed loop of the M1 mask,
  * the 5 large support discs come from the pillar section of the M2 mask.
"""
from __future__ import annotations

import math
import os
import re

import numpy as np

import gerber_io as gio

HERE = os.path.dirname(os.path.abspath(__file__))
APR26 = os.path.normpath(os.path.join(HERE, "..", "..", "Version_Apr26"))

# Which CEA mask the frame is inherited from.
#
# V1 is the one actually used to build all the detectors so far, and it is the
# one CERN adapted: its perimeter wall is 2.6 mm where V2's is 9.8 mm, so its
# active area is 173 849 mm^2 against V2's 161 531 mm^2 (+7.6 %).  V1 also
# lacks the two stray off-panel arcs that V2 carries.  Everything downstream -
# the active outline, the dead-area denominator, the solved pitches, the
# pillar keep-outs and the evacuation anchor - is derived from this choice.
FRAME_SOURCES = {"V1": "V1", "V2": "V2"}
_FRAME = "V1"


def _ref(layer, version=None):
    v = version or _FRAME
    return os.path.join(APR26, "Insulation_masks", v, f"P2_BASKET-Mask_{layer}_{v}.gbr")


def set_frame_source(name):
    """Choose which CEA mask the frame is inherited from ('V1' or 'V2')."""
    global _FRAME, M1_REF, M2_REF
    if name not in FRAME_SOURCES:
        raise ValueError(f"frame_source must be one of {sorted(FRAME_SOURCES)}, "
                         f"not {name!r}")
    _FRAME = name
    M1_REF = _ref("M1")
    M2_REF = _ref("M2")
    _cache.clear()
    return M1_REF, M2_REF


def frame_source():
    return _FRAME


_cache = {}

M1_REF = _ref("M1")
M2_REF = _ref("M2")
ENIG = os.path.join(APR26, "FABRICATION_P2", "Gerber", "P2_BASKET-F_ENIG_Finition.gbr")
CERN_M2 = os.path.join(APR26, "Bulk_CERN", "P2_Mask2.gbr")

N_CONNECTORS = 10


# --------------------------------------------------------------------------
def connectors():
    """(apex_xy, radius_mm, sorted array of connector centre angles in degrees)."""
    if "conn" in _cache:
        return _cache["conn"]
    lines = open(ENIG).read().splitlines()
    rot = {}
    for l in lines:
        m = re.match(r"^%ADD(\d+)RotRect,0\.300000X1\.800000X([\d.]+)\*%$", l)
        if m:
            rot["D" + m.group(1)] = float(m.group(2))
    cur, x, y = None, 0, 0
    cen = {}
    for l in lines:
        m = re.match(r"^D(\d+)\*$", l)
        if m:
            cur = m.group(0)[:-1]
            continue
        m = re.match(r"^(?:X(-?\d+))?(?:Y(-?\d+))?D03\*$", l)
        if m:
            if m.group(1):
                x = int(m.group(1))
            if m.group(2):
                y = int(m.group(2))
            if cur in rot:
                cen.setdefault(cur, []).append((x / gio.SCALE, y / gio.SCALE))
    pts = np.array([np.mean(v, axis=0) for v in cen.values()])
    A = np.c_[2 * pts[:, 0], 2 * pts[:, 1], np.ones(len(pts))]
    sol, *_ = np.linalg.lstsq(A, (pts ** 2).sum(1), rcond=None)
    apex = np.array([sol[0], sol[1]])
    R = math.sqrt(sol[2] + apex @ apex)
    th = np.sort(np.degrees(np.arctan2(pts[:, 1] - apex[1], pts[:, 0] - apex[0])))
    _cache["conn"] = (apex, R, th)
    return apex, R, th


def connector_sector_edges():
    """The 11 angles (deg) that separate the 10 per-connector wedges."""
    _, _, th = connectors()
    step = float(np.mean(np.diff(th)))
    return np.concatenate([th - step / 2, [th[-1] + step / 2]]), step


def active_outline():
    """Closed polyline of the inner edge of the bulk frame = the mesh/active area."""
    if ("outline", M1_REF) in _cache:
        return _cache[("outline", M1_REF)]
    sec = gio.read_sections(M1_REF)[0]
    paths = gio.section_paths(sec)
    # the frame is drawn with the 0.5 mm pen
    pen = next(c for c, d in sec.apertures.items() if d.startswith("C,0.500"))
    loops = gio.chain_loops(paths[pen])
    loops.sort(key=gio.polygon_area, reverse=True)
    # largest simple loop that contains the pillar field
    out = np.array(loops[0] if gio.polygon_area(loops[0]) > 1e5 else
                   max(loops, key=gio.polygon_area))
    _cache[("outline", M1_REF)] = out
    return out


def support_discs():
    """The 5 large discs (centre_x, centre_y, diameter) kept in every version."""
    if ("discs", M2_REF) in _cache:
        return _cache[("discs", M2_REF)]
    sec = gio.read_sections(M2_REF)[-1]
    paths = gio.section_paths(sec)
    pen = next(c for c, d in sec.apertures.items() if d.startswith("C,3.075"))
    out = []
    for p in paths[pen]:
        p = np.array(p)
        c = (p[0] + p[-1]) / 2          # half arc: endpoints are diametrically opposite
        r = np.hypot(*(p[0] - c))
        out.append((c[0], c[1], 2 * (r + 3.075 / 2)))
    # two half arcs per disc
    uniq = {}
    for x, y, d in out:
        uniq[(round(x, 3), round(y, 3))] = d
    out = np.array([[x, y, d] for (x, y), d in sorted(uniq.items())])
    _cache[("discs", M2_REF)] = out
    return out


# --------------------------------------------------------------------------
def inner_bottom_corner():
    """The inner bottom corner of the active area.

    Where the bottom edge of the mesh meets the inner arc (r = 122.31 mm) at
    theta = 5.8 deg.  This is the low point of the detector when it stands on
    its long edge, so it is where the CERN masks put the evacuation channel.
    """
    poly = active_outline()
    r = np.hypot(poly[:, 0], poly[:, 1])
    t = np.degrees(np.arctan2(poly[:, 1], poly[:, 0]))
    sel = np.where(t < 15)[0]
    return poly[sel[np.argmin(r[sel])]]


def cea_pillars():
    """Centres and drawn diameter of the CEA V2 pillar field."""
    sec = gio.read_sections(M2_REF)[-1]
    paths = gio.section_paths(sec)
    pen = next(c for c, d in sec.apertures.items() if d.startswith("C,0.400"))
    cen = {}
    for p in paths[pen]:
        p = np.array(p)
        c = (p[0] + p[-1]) / 2          # half arc: endpoints are diametrically opposite
        cen[(round(c[0], 3), round(c[1], 3))] = True
    return np.array(sorted(cen)), 0.800


def cern_pillars():
    """Centres and diameter of the CERN pillar field (inch file)."""
    cur, x, y = None, 0, 0
    ap, pts = {}, []
    for l in open(CERN_M2):
        l = l.strip()
        m = re.match(r"^%ADD(\d+)C,([\d.]+)\*%$", l)
        if m:
            ap["D" + m.group(1)] = float(m.group(2)) * 25.4
            continue
        m = re.match(r"^D(\d+)\*$", l)
        if m:
            cur = m.group(0)[:-1]
            continue
        m = re.match(r"^(?:X(-?\d+))?(?:Y(-?\d+))?D03\*$", l)
        if m:
            if m.group(1):
                x = int(m.group(1))
            if m.group(2):
                y = int(m.group(2))
            if cur in ap and abs(ap[cur] - 0.5) < 0.01:
                pts.append((x / gio.SCALE * 25.4, y / gio.SCALE * 25.4))
    return np.array(pts), 0.500


# --------------------------------------------------------------------------
def point_in_polygon(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    from matplotlib.path import Path
    return Path(poly).contains_points(pts)


def distance_to_polygon(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Unsigned distance from each point to the polygon boundary (vectorised)."""
    a = poly[:-1]
    b = poly[1:]
    ab = b - a
    L2 = (ab ** 2).sum(1)
    L2[L2 == 0] = 1e-12
    best = np.full(len(pts), np.inf)
    chunk = max(1, int(4e6 // max(1, len(a))))
    for s in range(0, len(pts), chunk):
        p = pts[s:s + chunk][:, None, :]
        t = np.clip(((p - a) * ab).sum(2) / L2, 0, 1)
        proj = a + t[:, :, None] * ab
        best[s:s + chunk] = np.sqrt(((p - proj) ** 2).sum(2)).min(1)
    return best
