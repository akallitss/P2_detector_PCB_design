"""
Geometry of the proposed drift-frame changes, in PCB coordinates (fan apex = origin, mm).

Everything is derived from the existing drawings:
  frame top face     ../data/frame_slices.json        (export_frame_slices.FCpy, STEP slice at z = 7.5)
  frame sections     ../data/frame_section_r27.json   (export_radial_section.FCpy, radial plane at 27 deg)
  PCB holes          Version_Apr26/FABRICATION_P2/NCDrill/P2_BASKET.drl
  PCB HV pads        Version_Apr26/FABRICATION_P2/Gerber/P2_BASKET-F_ENIG_Finition.gbr
  carbon back        ../data/carbon_registered.json   (its outer contour = today's PCB outline)

Changes modelled (NEW):
  * PCB outline UNCHANGED; the frame stays flush with it on the straight sides and the inner arc
    (it must not stick out in the basket), so only the outer side grows:
  * extension behind the connectors, out to the PCB edge (R650), full frame height
  * HV openings at both outer corners (pads + margin), down to today's outer wall
  * screw holes: one diameter (Ø3.5, not threaded), equal pitch, mirror-symmetric,
    straight sides / inner arc on today's lines (O-ring), outer arc moved for the carbon-back washer
"""
import collections
import json
import math
import os
import re

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", ".."))   # Detector_Drawings/
DRL = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2", "NCDrill", "P2_BASKET.drl")
ENIG = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2", "Gerber", "P2_BASKET-F_ENIG_Finition.gbr")
SLICES = os.path.join(OUT, "data", "frame_slices.json")

# ---------------------------------------------------------------- design inputs
FRAME_H = 8.0          # frame / extension height (4 mm drift gap; 9.0 for the 5 mm option)
HV_MARGIN = 3.0        # free space kept around the HV solder pads [mm]
WIDEN = 1.0            # PCB outline fixed: no widening of the straight sides / inner arc (option B)
R_EXT = 650.0          # outer radius of the extension (= today's PCB / carbon back)

# today's frame (STEP): straight sides 10 mm, both arcs 15 mm
SIDE_NOW, ARC_NOW = 10.0, 15.0
R_OUT_EDGE_NOW, R_IN_EDGE_NOW = 615.0, 95.0      # outer edge of the outer arc / of the inner arc
R_OUT_WALL, R_IN_WALL = 600.0, 110.0             # walls facing the active area (unchanged)
SIDE_NEW, ARC_NEW = SIDE_NOW * WIDEN, ARC_NOW * WIDEN
R_OUT_EDGE_NEW = R_OUT_WALL + ARC_NEW            # 615 (outside it: the extension)
R_IN_EDGE_NEW = R_IN_WALL - ARC_NEW              # 95

# screw-hole lines
Y_SIDE_NOW, R_OUT_NOW, R_IN_NOW = -7.5, 610.5, 99.5
Y_SIDE = Y_SIDE_NOW                              # cannot move: 0.26 mm from the O-ring groove
R_IN = R_IN_NOW                                  # unchanged
R_OUT = 613.0                                    # moved in, so the nut + washer sit on the carbon back
                                                 # (its edge is 10 mm before the connectors)

# chamfer at the bottom-right corner of the PCB / carbon back (today it starts at y = -10)
_CH0_NOW, CH1 = np.array([617.77, -10.0]), np.array([648.56, 43.33])
CH_U = (CH1 - _CH0_NOW) / np.linalg.norm(CH1 - _CH0_NOW)   # along the chamfer (60 deg)
CH_N = np.array([-CH_U[1], CH_U[0]])                        # inward normal (towards the frame)
U60, N150 = np.array([0.5, math.sqrt(3) / 2]), np.array([-math.sqrt(3) / 2, 0.5])

# gas inlets of the frame (STEP: Ø4.4 horizontal bores, z 1.3-5.7)
GAS_TOP_PT, GAS_TOP_DIR = np.array([303.5, 531.7]), np.array([0.5, 0.866])   # leaves the outer arc
GAS_IN_PT, GAS_IN_DIR = np.array([97.7, 0.0]), np.array([-1.0, 0.0])         # leaves the inner arc
GAS_D = 4.4


def chamfer_start(off):
    """Where the chamfer line meets the straight bottom edge y = -off."""
    return _CH0_NOW + (-off - _CH0_NOW[1]) / CH_U[1] * CH_U


CH0 = chamfer_start(SIDE_NEW)


def arc(r, a0, a1, n=400):
    t = np.radians(np.linspace(a0, a1, n))
    return list(zip(r * np.cos(t), r * np.sin(t)))


def deg(p):
    return math.degrees(math.atan2(p[1], p[0]))


def mirror30(p):
    """Mirror through the 30 deg symmetry axis of the sector."""
    a = math.radians(60)
    x, y = p
    return (x * math.cos(a) + y * math.sin(a), x * math.sin(a) - y * math.cos(a))


def mirror_poly(P):
    return Polygon([mirror30(q) for q in P.exterior.coords])


def top_corner(off):
    """PCB top corner: the 60 deg side line (offset off) meets the top edge y = 540."""
    t = (540.0 - off * N150[1]) / U60[1]
    return tuple(t * U60 + off * N150)


def pcb_outline(off=SIDE_NEW, r_in=R_IN_EDGE_NEW):
    """PCB = carbon-back outline. off = 10, r_in = 95 reproduce today's parts."""
    xb = math.sqrt(r_in ** 2 - off ** 2)
    pin = tuple(math.sqrt(r_in ** 2 - off ** 2) * U60 + off * N150)
    p = [(xb, -off), tuple(chamfer_start(off)), tuple(CH1)]
    p += arc(R_EXT, deg(CH1), deg((361.81, 540.0)))
    p += [(361.81, 540.0), top_corner(off), pin]
    p += arc(r_in, deg(pin), deg((xb, -off)))
    return Polygon(p).buffer(0)


def frame_top():
    """Top face of today's frame (z = 7.5): outer outline, window and holes."""
    loops = [np.array(L) for L in json.load(open(SLICES))["7.5"] if len(L) > 3]
    polys = sorted((Polygon(L).buffer(0) for L in loops), key=lambda P: -P.area)
    outer, window = polys[0], polys[1]
    holes = [P for P in polys[2:] if P.area < 50]
    return outer, window, holes


def frame_outer_new(outer_now):
    """Today's outline grown outward on every side, clipped to the new PCB outline."""
    half = box(-1000, -SIDE_NEW, 1000, 1000)
    wedge = half.intersection(mirror_poly(half))
    ann = Point(0, 0).buffer(R_OUT_EDGE_NEW, 4096).difference(Point(0, 0).buffer(R_IN_EDGE_NEW, 1024))
    return outer_now.union(wedge.intersection(ann)).intersection(pcb_outline()).buffer(0)


def read_drill():
    D, H, cur = {}, collections.defaultdict(list), None
    for line in open(DRL).read().splitlines():
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            D[int(m.group(1))] = float(m.group(2))
        m = re.match(r"^T(\d+)$", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"X([-\d.]+)Y([-\d.]+)", line)
        if m and cur:
            H[cur].append((float(m.group(1)), float(m.group(2))))
    return D, H


def hv_pads():
    """ENIG (gold) pads of the two HV groups, as polygons."""
    from gerbonara import GerberFile
    from gerbonara.graphic_primitives import ArcPoly
    from gerbonara.utils import MM
    g = GerberFile.open(ENIG)
    out = {"A": [], "B": []}
    for o in g.objects:
        for p in o.to_primitives(MM):
            if isinstance(p, ArcPoly) and len(p.outline) > 2:
                P = Polygon(list(p.outline))
                c = P.centroid
                if 612 < c.x < 650 and -12 < c.y < 35:
                    out["A"].append(P)
                elif 300 < c.x < 335 and 525 < c.y < 545:
                    out["B"].append(P)
    return out


def to_uv(xy):
    d = np.asarray(xy) - CH0
    return np.array([d @ CH_U, d @ CH_N])


def from_uv(u, v):
    return tuple(CH0 + u * CH_U + v * CH_N)


def hv_openings(pads):
    """A: band aligned with the chamfer, pads ± margin along it.  B: everything left of
    (pads x_max + margin), which also clears the top gas inlet.  Both only cut material
    outside today's outer arc (r > 615): the frame itself is not touched."""
    keep_out = Point(0, 0).buffer(R_OUT_EDGE_NOW, 4096)
    uv = np.array([to_uv(c) for P in pads["A"] for c in P.exterior.coords])
    u0, u1 = uv[:, 0].min() - HV_MARGIN, uv[:, 0].max() + HV_MARGIN
    A = Polygon([from_uv(u0, -5), from_uv(u1, -5), from_uv(u1, 60), from_uv(u0, 60)]).difference(keep_out)
    xy = np.array([c for P in pads["B"] for c in P.exterior.coords])
    xb = xy[:, 0].max() + HV_MARGIN
    B = box(280, 500, xb, 560).difference(keep_out)
    return {"A": A, "B": B, "A_u": (u0, u1), "B_x": xb,
            "A_pad_u": (uv[:, 0].min(), uv[:, 0].max()), "B_pad_x": (xy[:, 0].min(), xy[:, 0].max())}


def clean(g, min_area=1.0):
    g = g.buffer(-0.02).buffer(0.02)
    return unary_union([q for q in getattr(g, "geoms", [g]) if q.area > min_area])


def new_holes(material, D, H):
    """PCB connector-support holes (T4 Ø2.2, T5 Ø3.2) that land in the new material."""
    out = []
    for k in (4, 5):
        for x, y in H[k]:
            if material.buffer(-D[k] / 2 + 0.01).contains(Point(x, y)):
                out.append((x, y, D[k]))
    return out


def ray_exit(shape, p0, d):
    """First point along p0 + t d that is outside shape."""
    for t in np.arange(0, 40, 0.05):
        p = p0 + t * d
        if not shape.contains(Point(*p)):
            return tuple(p)


def build():
    outer, window, fholes = frame_top()
    D, H = read_drill()
    pads = hv_pads()
    op = hv_openings(pads)
    outer_new = frame_outer_new(outer)
    openings = unary_union([op["A"], op["B"]])
    band = clean(outer_new.difference(outer).difference(openings))          # wider frame
    ext = clean(pcb_outline().difference(outer_new).difference(openings), 20)  # extension
    ext_full = clean(pcb_outline().difference(outer), 20)
    holes = new_holes(band.union(ext), D, H)
    return dict(outer=outer, outer_new=outer_new, band=band, window=window, fholes=fholes, D=D, H=H,
                pads=pads, op=op, ext_full=ext_full, ext=ext, holes=holes,
                gas=ray_exit(outer, GAS_TOP_PT, GAS_TOP_DIR),
                gas_in=ray_exit(outer, GAS_IN_PT, GAS_IN_DIR),
                gas_in_new=ray_exit(outer_new, GAS_IN_PT, GAS_IN_DIR))


def arc_points(p, step_deg=0.2):
    """Points along a gerbonara Arc (cx, cy absolute); full circle if start == end."""
    r = math.hypot(p.x1 - p.cx, p.y1 - p.cy)
    a0 = math.atan2(p.y1 - p.cy, p.x1 - p.cx)
    a1 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
    if p.clockwise:
        while a1 >= a0:
            a1 -= 2 * math.pi
    else:
        while a1 <= a0:
            a1 += 2 * math.pi
    n = max(2, int(abs(a1 - a0) / math.radians(step_deg)) + 1)
    t = np.linspace(a0, a1, n)
    return np.c_[p.cx + r * np.cos(t), p.cy + r * np.sin(t)].tolist()


# ---------------------------------------------------------------- frame screw holes
SCREW_D = 3.5                       # the existing non-threaded frame hole
TARGET_PITCH = 46.5                 # [mm] common pitch aimed for on every edge
PITCH_TOL = 1.015                   # accept up to 1.5 % above the target
CORNERS_NOW = {                     # existing corner holes (Ø3.5)
    "inner-bottom": (99.31, -6.00), "bottom-right": (610.44, -6.00),
    "top": (297.52, 527.32), "inner-top": (44.46, 89.00)}
CORNERS = dict(CORNERS_NOW)
# the top corner hole sits 5 mm inside its mirror position (the gas inlet is there): move the
# bottom-right one to the mirror of the top one, so both straight sides have the same length
CORNERS["bottom-right"] = tuple(round(v, 2) for v in mirror30(CORNERS["top"]))


def old_frame_holes(H):
    """Existing frame holes = PCB T3 (frame Ø3.0, threaded) + T6 (frame Ø3.5)."""
    return [(x, y, 3.0) for x, y in H[3]] + [(x, y, 3.5) for x, y in H[6]]


def edge_of(p):
    x, y = p
    r = math.hypot(x, y)
    out = []
    if y < -4 and 90 < x < 615:
        out.append("bottom side")
    if r > 603:
        out.append("outer arc")
    if r < 102:
        out.append("inner arc")
    d60 = -x * math.sin(math.radians(60)) + y * math.cos(math.radians(60))
    if d60 > 4 and r < 608:
        out.append("top side")
    return out


def s_on(edge, p, now=False):
    """Position along an edge [mm] from its first corner, measured on the edge's NEW hole line
    (straight sides: along the line; arcs: arc length on the new hole radius)."""
    if edge == "bottom side":
        return p[0] - CORNERS["inner-bottom"][0]
    if edge == "top side":
        c = np.array(CORNERS["inner-top"])
        return float((np.asarray(p) - c) @ U60)
    if edge == "outer arc":
        return (R_OUT_NOW if now else R_OUT) * math.radians(deg(p) - deg(CORNERS["bottom-right"]))
    if edge == "inner arc":
        return (R_IN_NOW if now else R_IN) * math.radians(deg(p) - deg(CORNERS["inner-bottom"]))


def n_segments(length):
    """Fewest equal segments whose pitch is not wider than the target (+ tolerance)."""
    return max(1, math.ceil(length / (TARGET_PITCH * PITCH_TOL)))


def new_frame_holes():
    """Equal pitch on every edge, corners fixed, mirror-symmetric.
    Returns ([(no, x, y, edge)], pitch) numbered round the frame."""
    cb, cr, ct, ci = (CORNERS[k] for k in ("inner-bottom", "bottom-right", "top", "inner-top"))
    L = cr[0] - cb[0]
    n = n_segments(L)
    side = [(cb[0] + k * L / n, Y_SIDE) for k in range(1, n)]
    a0, a1 = deg(cr), deg(ct)
    m = n_segments(R_OUT * math.radians(a1 - a0))
    outer = [(R_OUT * math.cos(math.radians(a0 + k * (a1 - a0) / m)), R_OUT * math.sin(math.radians(a0 + k * (a1 - a0) / m)))
             for k in range(1, m)]
    b0, b1 = deg(cb), deg(ci)
    q = n_segments(R_IN * math.radians(b1 - b0))
    inner = [(R_IN * math.cos(math.radians(b0 + k * (b1 - b0) / q)), R_IN * math.sin(math.radians(b0 + k * (b1 - b0) / q)))
             for k in range(1, q)]
    seq = [(cb, "corner")] + [(p, "bottom side") for p in side] + [(cr, "corner")] \
        + [(p, "outer arc") for p in outer] + [(ct, "corner")] \
        + [(mirror30(p), "top side") for p in reversed(side)] + [(ci, "corner")] \
        + [(p, "inner arc") for p in reversed(inner)]
    pitch = {"straight sides": L / n, "outer arc": R_OUT * math.radians(a1 - a0) / m,
             "inner arc": R_IN * math.radians(b1 - b0) / q}
    return [(i + 1, p[0], p[1], e) for i, (p, e) in enumerate(seq)], pitch


def symmetry_error(xy):
    """Largest distance between a hole's mirror image and the nearest hole."""
    P = np.array(xy)
    return max(np.hypot(*(P - np.array(mirror30(p))).T).min() for p in P)


if __name__ == "__main__":
    G = build()
    op = G["op"]
    new, pitch = new_frame_holes()
    print(f"sides: straight {SIDE_NOW:g} -> {SIDE_NEW:g}, arcs {ARC_NOW:g} -> {ARC_NEW:g}; "
          f"outer edge r {R_OUT_EDGE_NOW:g} -> {R_OUT_EDGE_NEW:g}, inner edge r {R_IN_EDGE_NOW:g} -> {R_IN_EDGE_NEW:g}")
    print("hole lines: y", Y_SIDE, " r_out", R_OUT, " r_in", R_IN)
    print("areas cm2: wider frame", round(G["band"].area / 100, 1), " extension", round(G["ext"].area / 100, 1))
    print("A opening u", [round(v, 2) for v in op["A_u"]], " B x <=", round(op["B_x"], 2), " CH0", CH0.round(2),
          " top corner", np.round(top_corner(SIDE_NEW), 2))
    print("gas top exit", np.round(G["gas"], 2), "in opening B:", op["B"].buffer(0.5).contains(Point(G["gas"])))
    print("gas inner exit now", np.round(G["gas_in"], 2), " new", np.round(G["gas_in_new"], 2))
    print("frame holes", len(new), {k: round(v, 2) for k, v in pitch.items()},
          "sym err", round(symmetry_error([h[1:3] for h in new]), 3))
    print("connector-support holes in new material:", len(G["holes"]))


# ---------------------------------------------------------------- carbon drift piece (sits on the z = 4 step)
CARBON_JSON = os.path.join(OUT, "data", "carbon_registered.json")
CARBON_T_NEW = 2.0                    # new thickness [mm]
STEP_Z, STEP_Z_5MM = 4.0, 5.0         # step height = drift gap (5 mm = placeholder)
B2_PAD = (590.5, 10.0, 3.0)           # B2 drift pad on the PCB: centre x, y and side (pcb/drift_pad_B2)
B2_CUT = (585.5, 5.0, 595.5, 15.0)    # mesh cut round the pad
CLEAR_HV = 3.0                        # bare drift-potential metal <-> bare mesh
FOAM_SIDE = 4.0                       # foam column: 4 x 4 mm, keeps CLEAR_HV to the cut edge
FOAM_SHEET = 1.0                      # MECF-010P, 1.0 mm sheets (15-30 % compression recommended)
RING_GAP, RING_WALL, RING_H = 0.2, 1.0, 3.0   # insulating guide ring round the foam, glued on the PCB


def foam_sheets(gap):
    """Number of 1 mm sheets giving a compression closest to the middle of 15-30 %."""
    best = min(range(1, 12), key=lambda n: abs((1 - gap / (n * FOAM_SHEET)) - 0.225))
    return best, 1 - gap / (best * FOAM_SHEET)


def carbon_strip():
    """Carbon drift piece today (DXF block SE2): a 5 mm strip centred on the frame's inner wall.
    On the cutting sheet its arcs are centred on (351.61, 637.5) and it spans 180-240 deg:
    move the apex to the origin and turn it 180 deg."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize
    c = np.array([351.61, 637.5])
    segs = json.load(open(CARBON_JSON))["SE2"]
    lines = unary_union([LineString(np.round(-(np.asarray(s) - c), 3)) for s in segs])
    return sorted(polygonize(lines), key=lambda p: p.area)[0]          # the strip (smallest face)


def carbon_flap():
    """Square flap pressing the foam: from the strip's inner corner to the far edges of the mesh cut."""
    inner_x, inner_y = 597.5, 2.5
    return box(B2_CUT[0], inner_y, inner_x + 0.5, B2_CUT[3])           # overlaps the strip by 0.5 to join


def foam_square():
    x, y, _ = B2_PAD
    h = FOAM_SIDE / 2
    return box(x - h, y - h, x + h, y + h)


def guide_ring():
    f = foam_square()
    return f.buffer(RING_GAP + RING_WALL, join_style=2).difference(f.buffer(RING_GAP, join_style=2))


# ---------------------------------------------------------------- screws: M3, head on the frame top,
# washer + nut on the carbon-back side
SCREW_D_NOM = 3.0
HEAD_D = 5.5                          # ISO 4762 / ISO 7984 head
NUT_AF, NUT_T = 5.5, 2.4              # ISO 4032 M3 nut
WASHER_OD, WASHER_T = 6.0, 0.5        # DIN 433 small washer
PCB_T = 0.2


def screw_length(frame_h=FRAME_H):
    """Shortest standard length reaching through the nut."""
    need = frame_h + PCB_T + CB_T + WASHER_T + NUT_T
    return next(L for L in (10, 12, 14, 16, 18, 20, 25) if L >= need), need


# ---------------------------------------------------------------- carbon back (strongback)
CB_T = 3.0                            # new thickness
CONN_R_IN, CONN_R_OUT = 626.95, 637.26    # FX20-140P pads on the PCB (now on the back side)
CONN_MARGIN = 10.0
CB_R_OUT = math.floor((CONN_R_IN - CONN_MARGIN) * 10) / 10   # 616.9
RIB_W = 10.0
RIBS_RADIAL_DEG = (20.0, 40.0)        # principle only: number and width free to the designer
RIBS_ARC_R = (270.0, 430.0)


def _wedge(off):
    half = box(-1000, -off, 1000, 1000)
    return half.intersection(mirror_poly(half))


def cb_window():
    """Opening of today's carbon back (DXF SE1): R111 / R599 / 1 mm inside the side lines."""
    inside = box(-1000, 1.0, 1000, 1000)
    inside = inside.intersection(mirror_poly(inside))
    ann = Point(0, 0).buffer(599.0, 4096).difference(Point(0, 0).buffer(111.0, 1024))
    return inside.intersection(ann).buffer(-0.75, join_style=1).buffer(0.75, join_style=1)


def cb_now():
    holes = json.load(open(CARBON_JSON))["holes"]
    P = pcb_outline(SIDE_NOW, R_IN_EDGE_NOW).difference(cb_window())
    for d, pts in holes.items():
        for x, y in pts:
            P = P.difference(Point(x, y).buffer(float(d) / 2, 32))
    return P, holes


def cb_ribs():
    w = cb_window()
    ribs = []
    for a in RIBS_RADIAL_DEG:
        t = math.radians(a)
        d, n = np.array([math.cos(t), math.sin(t)]), np.array([-math.sin(t), math.cos(t)])
        h = RIB_W / 2
        ribs.append(Polygon([tuple(h * n), tuple(700 * d + h * n), tuple(700 * d - h * n), tuple(-h * n)]))
    for r in RIBS_ARC_R:
        ribs.append(Point(0, 0).buffer(r + RIB_W / 2, 2048).difference(Point(0, 0).buffer(r - RIB_W / 2, 2048)))
    return unary_union(ribs).intersection(w.buffer(0.5))


def cb_new():
    ann = Point(0, 0).buffer(CB_R_OUT, 4096).difference(Point(0, 0).buffer(R_IN_EDGE_NEW, 1024))
    P = _wedge(SIDE_NEW).intersection(ann).intersection(pcb_outline()).difference(cb_window()).union(cb_ribs())
    for _, x, y, _ in new_frame_holes()[0]:
        P = P.difference(Point(x, y).buffer(SCREW_D / 2, 32))
    return P.buffer(0)


def connector_band():
    """Where the FX20 connectors sit (now on the back of the PCB), between the first and last
    Ø2.2 connector-end holes."""
    a0, a1 = 2.53, 57.47
    sector = Polygon([(0, 0)] + arc(800, a0, a1, 200))
    ann = Point(0, 0).buffer(CONN_R_OUT, 4096).difference(Point(0, 0).buffer(CONN_R_IN, 4096))
    return ann.intersection(sector)


B2_TRACE_BCU = [(590.5, 7.6), (600.0, 7.0), (616.0, 8.5), (626.3, 15.8)]   # drift HV trace, back copper


# mesh at the B2 corner: the whole corner is cleared (no mesh for x >= 585.5 and y <= 15.0,
# out to both frame walls). The mesh is trimmed ~1.9 mm from the frame wall elsewhere.
MESH_TRIM = 1.9
M_PAD_A = (595.77, 1.29, 598.70, 4.10)     # mesh-contact pad at this corner (gets no mesh any more)


def mesh_area():
    _, window, _ = frame_top()
    base_open = window.buffer(-3.0, join_style=2)
    corner = box(B2_CUT[0], -100, 1000, B2_CUT[3])
    return base_open.buffer(-MESH_TRIM, join_style=2).difference(corner)


# ---------------------------------------------------------------- foam slot in the frame (replaces the guide ring)
# The frame's lower level (z 0 - STEP_Z, below the mylar step) is filled in the cleared B2 corner and a
# slot through it holds the foam; the carbon flap has the same outline and rests on it.
SLOT_GAP = 0.2                        # foam -> slot wall, each side
SLOT_R = 0.5                          # slot corner radius (end mill Ø1); designer's choice


def foam_slot():
    s = foam_square().buffer(SLOT_GAP, join_style=2)
    return s.buffer(-SLOT_R, join_style=2).buffer(SLOT_R, join_style=1)


def foam_block():
    """New frame material at the lower level: the cleared corner (x >= 585.5, y <= 15) out to
    today's lower walls (y = 0 and r = 600), minus the foam slot."""
    _, window, _ = frame_top()
    base_open = window.buffer(-3.0, join_style=2)
    return base_open.intersection(box(B2_CUT[0], -1, 700, B2_CUT[3])).difference(foam_slot())


def carbon_flap_slot():
    """Flap with the block's outline (x = 585.5, y = 15) out to the lower walls; the strip covers
    part of it, the rest is the flap. Rests on the block over its whole area."""
    return box(B2_CUT[0], 0, 700, B2_CUT[3]).intersection(Point(0, 0).buffer(R_OUT_WALL, 4096))
