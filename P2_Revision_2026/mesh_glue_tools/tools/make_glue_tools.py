# Builds the P2 mesh-gluing tools as solids and writes STEP + STL (one file per part).
#
#   OUT=/path/to/output  freecadcmd make_glue_tools.py      (FreeCAD 1.0; not plain python)
#
# Parts (dimensions in glue_params.py):
#   shoe_straight   reach 11.84  bottom edge and 60 deg side
#   shoe_inner_arc  reach 16.85  inner arc
#   shoe_outer_arc  reach 51.98  outer arc
#   rail_straight   one third of a straight side (print 6)
#   rail_inner_arc  the whole inner arc (print 1)
#   rail_outer_arc  a quarter of the outer arc (print 4)
#
# The shoe is modelled in its working position (Z = 0 = PCB top, see glue_params.py);
# the STL keeps that frame, so turn it in the slicer (print it upside down: the top face on the plate,
# runners up). Rails are modelled lying on the table; print them upside down too (top face on the
# plate), so the narrow contact strip at the bottom of the inner face is not spoiled by the first layer.
import math
import os
import sys

import FreeCAD as App
import Mesh
import Part

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
sys.path.insert(0, HERE)
import glue_params as P   # noqa: E402

OUT = os.environ.get("OUT", os.path.normpath(os.path.join(HERE, "..", "out")))
os.makedirs(OUT, exist_ok=True)
V = App.Vector


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def shoe(reach):
    L = P.SHOE_L / 2
    zw = P.lip_z()                      # wall top: runner / scraper bottoms
    zb = P.body_z0()                    # body bottom
    yo, yi = 0.0, P.WALL_W              # outer / inner border of the wall
    y_line0 = P.WALL_W / 2 - P.LINE_W / 2
    y_line1 = P.WALL_W / 2 + P.LINE_W / 2
    yr0, yr1 = yo + P.RUN_W, yi - P.RUN_W          # inside faces of the runners
    edge = -reach
    rail_top = P.RAIL_ABOVE

    body = box(-L, L, -P.BODY_OUT, yi + P.BODY_IN, zb, P.TOP_Z)
    # runners on the two borders of the wall
    s = body.fuse(box(-L, L, yo, yr0, zw, zb))
    s = s.fuse(box(-L, L, yr1, yi, zw, zb))
    # front wall and rear scraper, touching the wall between the runners
    s = s.fuse(box(L - P.END_T, L, yr0, yr1, zw, zb))
    rear = box(-L, -L + P.END_T, yr0, yr1, zw, zb)
    rear = rear.cut(box(-L - 1, -L + P.END_T + 1, y_line0, y_line1, zw - 1, zw + P.LAID_H))   # the lip notch
    s = s.fuse(rear)
    # overflow channels: up into the body, beside the line, between the end walls
    for a, b in ((yr0, y_line0), (y_line1, yr1)):
        s = s.cut(box(-L + P.END_T, L - P.END_T, a, b, zb - 0.01, zb + P.CHAN_D))
    # feed: boss + bore for an 18 G blunt needle, down into the cavity
    yc = P.WALL_W / 2
    boss = Part.makeCylinder(P.BOSS_D / 2, P.BOSS_H, V(0, yc, P.TOP_Z))
    s = s.fuse(boss)
    s = s.cut(Part.makeCylinder(P.FEED_D / 2, P.TOP_Z + P.BOSS_H + 1, V(0, yc, zb - 0.5)))

    # arm: from the body out over the rail (its bottom is the skid on the rail top)
    A = P.ARM_L / 2
    arm = box(-A, A, edge - P.SKID_W, -P.BODY_OUT + 0.01, rail_top, P.TOP_Z)
    s = s.fuse(arm)
    # fence foot, hanging just inside the PCB edge, with two M2 set screws pushing on the rail face
    yf0 = edge + P.FENCE_SET
    foot = box(-A, A, yf0, yf0 + P.FOOT_T, P.FOOT_GAP, rail_top + 0.01)
    for x in (-P.SCREW_X, P.SCREW_X):
        hole = Part.makeCylinder(P.SCREW_TAP / 2, P.FOOT_T + 2, V(x, yf0 - 1, P.SCREW_Z), V(0, 1, 0))
        foot = foot.cut(hole)
    s = s.fuse(foot)
    return s.removeSplitter()


def rail_straight(length):
    # PCB edge along X at Y = 0, PCB on +Y; rail on -Y, sitting on the table (Z = -PCB_T)
    return box(0, length, -P.RAIL_W, 0, -P.PCB_T, P.RAIL_ABOVE)


def rail_arc(r_edge, deg, outside):
    """Annular sector. outside=True: rail beyond the PCB edge (outer arc, r_edge..r_edge+W);
    False: rail inside the edge circle (inner arc, r_edge-W..r_edge)."""
    r0, r1 = (r_edge, r_edge + P.RAIL_W) if outside else (r_edge - P.RAIL_W, r_edge)
    h = P.RAIL_H
    outer = Part.makeCylinder(r1, h, V(0, 0, -P.PCB_T), V(0, 0, 1), deg)
    inner = Part.makeCylinder(r0, h + 2, V(0, 0, -P.PCB_T - 1), V(0, 0, 1), 360)
    sec = outer.cut(inner)
    # move the piece next to the origin (keeps the STL small in coordinates)
    a = math.radians(deg / 2)
    sec.translate(V(-r0 * math.cos(a), -r0 * math.sin(a), 0))
    return sec.removeSplitter()


def write(name, shape):
    assert shape.isValid(), name
    step = os.path.join(OUT, name + ".step")
    stl = os.path.join(OUT, name + ".stl")
    shape.exportStep(step)
    m = Mesh.Mesh()
    m.addFacets(shape.tessellate(0.01))
    assert m.isSolid() and not m.hasNonManifolds(), name + ": STL not a closed manifold"
    m.write(stl)
    bb = shape.BoundBox
    print(f"{name:16s} vol {shape.Volume:9.1f} mm3   bbox {bb.XLength:7.2f} x {bb.YLength:7.2f} x {bb.ZLength:5.2f}")


def sections(shape, cuts):
    """Outlines of the solid in a few planes, for the drawings (fig_glue_tools.py)."""
    res = {}
    for name, (normal, d) in cuts.items():
        wires = shape.slice(V(*normal), d)
        res[name] = [[[round(p.x, 4), round(p.y, 4), round(p.z, 4)] for p in w.discretize(Deflection=0.005)]
                     for w in wires]
    return res


import json  # noqa: E402
SEC = {}
for k, r in P.REACH.items():
    sh = shoe(r)
    write("shoe_" + k, sh)
    L = P.SHOE_L / 2
    SEC["shoe_" + k] = sections(sh, {
        "yz_mid": ((1, 0, 0), -2.0),                     # across, through the cavity (behind the feed bore)
        "yz_rear": ((1, 0, 0), -L + P.END_T / 2),        # across, through the rear scraper and its notch
        "yz_screw": ((1, 0, 0), P.SCREW_X),              # across, through a set screw
        "xy_skirt": ((0, 0, 1), P.lip_z() + 0.05),       # just above the wall: runners, end walls, notch
        "xy_chan": ((0, 0, 1), P.body_z0() + 0.6),       # through the overflow channels
        "xz_line": ((0, 1, 0), P.WALL_W / 2),            # along, through the line / notch / feed
    })
write("rail_straight", rail_straight(P.STRAIGHT_LEN / P.STRAIGHT_PIECES))
write("rail_inner_arc", rail_arc(P.INNER_R, P.INNER_DEG, outside=False))
write("rail_outer_arc", rail_arc(P.OUTER_R, P.OUTER_DEG / P.OUTER_PIECES, outside=True))
json.dump(SEC, open(os.path.join(OUT, "sections.json"), "w"))
print("written to", OUT)
