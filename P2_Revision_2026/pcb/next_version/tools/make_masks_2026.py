#!/usr/bin/env python3
"""
Insulation masks (M1, M2) for the 2026 PCB, from V3B_final + B2 drift pad
(../../drift_pad_B2/Insulation_masks/V3B_final_B2). Polarity: dark = open (no resist),
clear = resist.

Changes:
  * screw holes (M1): today's 40 openings removed; 39 new Ø4.0 openings at the new pattern
    (P2_Revision_2026/mechanics, same positions as frame and carbon back)
  * alignment crosses (M1, M2): old 3 mm outlines removed; new 10 mm outlines (1.3 mm arms)
    in a 12.5 x 12.5 mm resist square at the new positions (crosses 1, 2 moved, 3, 4 in place);
    in M2 the old resist squares of crosses 1, 2 are opened again
  * corner A (M1, M2): the window over the mesh-contact pad is closed (that pad is removed;
    the mesh is contacted at the top corner only)
  * drift pad (M1, M2): its window moves from the first B2 pad (590.5, 10.0) to the centre of the
    cleared corner (592.75, 7.5), inside the unchanged B2 resist island; the mesh-cut template's
    pad marker moves with it (decided 2026-10-26)
  * unchanged: B2 resist island, pillars, everything else

Old objects are deleted by their exact line ranges; new ones are appended before M02 (later
objects override earlier ones). Writes ../Insulation_masks/V3B_final_2026/ and a change log.
Run with (ulimit -v 3000000; python3 make_masks_2026.py)
"""
import datetime
import math
import os
import re
import sys

import numpy as np
from scipy import ndimage
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
REV = os.path.normpath(os.path.join(OUT, "..", ".."))
B2 = os.path.join(REV, "pcb", "drift_pad_B2")
sys.path.insert(0, os.path.join(B2, "tools"))
sys.path.insert(0, os.path.join(REV, "mechanics", "tools"))
import make_b2_files as mk        # noqa: E402  (Gerber read/write helpers, same conventions as B2)
import qc_b2 as qc                # noqa: E402  (polarity-aware rasteriser)
import rev_geometry as rg         # noqa: E402
import fig_pcb as fp              # noqa: E402  (new cross positions and sizes)

SRC = os.path.join(B2, "Insulation_masks", "V3B_final_B2")
DST = os.path.join(OUT, "Insulation_masks", "V3B_final_2026")
STAMP = datetime.date.today().isoformat()

HOLE_OPEN_D = 4.0          # opening round a new screw hole (today's non-plated openings are Ø4.0)
CROSS_OUT = 10.0           # mask cross outline: across
CROSS_ARM = 1.3            # mask cross outline: arm width
OUTLINE_W = 0.135          # today's outline line width (aperture D10)
MESH_WIN_A = (594.0, 0.0, 600.0, 6.0)   # search box for the corner-A mesh-contact windows
PAD_OLD, PAD_NEW = rg.B2_PAD_OLD[:2], rg.B2_PAD[:2]   # drift pad: first B2 patch -> corner centre (2026-10-26)


def drift_window(c):
    return (c[0] - mk.WIN_H, c[1] - mk.WIN_H, c[0] + mk.WIN_H, c[1] + mk.WIN_H)


def drift_windows_old(objs):
    return [o for o in objs if o["kind"] == "region" and o["pol"] == "D"
            and math.hypot(o["c"][0] - PAD_OLD[0], o["c"][1] - PAD_OLD[1]) < 0.05
            and max(o["bbox"][2] - o["bbox"][0], o["bbox"][3] - o["bbox"][1]) < 2 * mk.WIN_H + 0.01]


def parse(L):
    """Drawing objects of an RS-274X file: tracks (D02 + D01 runs), flashes, regions; with
    polarity, aperture, line indices and bounding box of their points."""
    objs, pol, ap, cur, reg = [], "D", None, None, None

    def close():
        nonlocal cur
        if cur:
            objs.append(cur)
            cur = None
    for i, l in enumerate(L):
        s = l.strip()
        if s.startswith("%LPD"):
            close(); pol = "D"; continue
        if s.startswith("%LPC"):
            close(); pol = "C"; continue
        m = re.match(r"^D(\d{2,})\*$", s)
        if m and int(m.group(1)) >= 10 and reg is None:
            close(); ap = int(m.group(1)); continue
        if s.startswith("G36"):
            close(); reg = {"kind": "region", "pol": pol, "ap": None, "lines": [i], "pts": []}; continue
        if s.startswith("G37"):
            reg["lines"].append(i); objs.append(reg); reg = None; continue
        m = re.match(r"^(?:G0?[123])?X(-?\d+)Y(-?\d+)(?:I-?\d+J-?\d+)?D0([123])\*$", s)
        if m:
            p, d = (int(m.group(1)) / 1e6, int(m.group(2)) / 1e6), m.group(3)
            if reg is not None:
                reg["lines"].append(i); reg["pts"].append(p)
            elif d == "3":
                close(); objs.append({"kind": "flash", "pol": pol, "ap": ap, "lines": [i], "pts": [p]})
            elif d == "2":
                close(); cur = {"kind": "track", "pol": pol, "ap": ap, "lines": [i], "pts": [p]}
            else:
                if cur is None:
                    cur = {"kind": "track", "pol": pol, "ap": ap, "lines": [], "pts": []}
                cur["lines"].append(i); cur["pts"].append(p)
            continue
        if reg is not None and s:
            reg["lines"].append(i)
    close()
    for o in objs:
        xs, ys = zip(*o["pts"])
        o["bbox"] = (min(xs), min(ys), max(xs), max(ys))
        o["c"] = ((o["bbox"][0] + o["bbox"][2]) / 2, (o["bbox"][1] + o["bbox"][3]) / 2)
    return objs


def apertures(L):
    return {int(m.group(1)): float(m.group(2)) for l in L for m in [re.match(r"^%ADD(\d+)C,([\d.]+)\*%", l)] if m}


def old_screw_openings(objs):
    D, H = rg.read_drill()
    holes = [(x, y) for k in (3, 6) for x, y in H[k]]
    out = []
    for o in objs:
        b = o["bbox"]
        if o["kind"] == "region" and o["pol"] == "D" and max(b[2] - b[0], b[3] - b[1]) < 6.0:
            if min(math.hypot(o["c"][0] - x, o["c"][1] - y) for x, y in holes) < 1.0:
                out.append(o)
    return out, len(holes)


def cross_outlines(objs, aps):
    out = []
    for o in objs:
        if o["kind"] == "track" and abs(aps.get(o["ap"], 0) - OUTLINE_W) < 1e-6:
            if any(abs(o["c"][0] - c[0]) < 3 and abs(o["c"][1] - c[1]) < 3 for c in fp.MARKS_NOW.values()):
                out.append(o)
    return out


def mesh_windows_A(objs):
    x0, y0, x1, y1 = MESH_WIN_A
    return [o for o in objs if o["kind"] == "region" and o["pol"] == "D" and x0 < o["c"][0] < x1 and y0 < o["c"][1] < y1
            and max(o["bbox"][2] - o["bbox"][0], o["bbox"][3] - o["bbox"][1]) < 4]


def ring_region(ring):
    xy = list(ring.coords)
    return ["G36*", f"X{mk.q(xy[0][0])}Y{mk.q(xy[0][1])}D02*", "G01*"] + \
           [f"X{mk.q(x)}Y{mk.q(y)}D01*" for x, y in xy[1:]] + ["G37*"]


def poly_region(g):
    out = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "Polygon" and not p.is_empty:
            out += ring_region(p.exterior)
    return out


def cross_shape(c):
    h, a = CROSS_OUT / 2 - CROSS_ARM / 2, CROSS_ARM / 2
    x, y = c
    return unary_union([LineString([(x - h, y), (x + h, y)]).buffer(a, 16),
                        LineString([(x, y - h), (x, y + h)]).buffer(a, 16)])


def track(ring, ap):
    xy = list(ring.coords)
    return [f"D{ap}*", f"X{mk.q(xy[0][0])}Y{mk.q(xy[0][1])}D02*"] + [f"X{mk.q(x)}Y{mk.q(y)}D01*" for x, y in xy[1:]]


def m2_old_square_patch(path, c):
    """Dark patch that removes today's resist square round an inner cross in M2: the white
    pixels round the cross (outside the outline) that are on the board, measured on the mask."""
    win = (c[0] - 7, c[0] + 7, c[1] - 7, c[1] + 7)
    px = 0.02
    img = qc.raster(qc.load(path), win, px)            # True = dark (open)
    GX, GY = qc.grid(win, px)
    r_c = math.hypot(*c)
    a = math.atan2(c[1], c[0]) + math.radians(4.5)     # a ray beside the square: where the board starts
    rr = np.arange(r_c - 6, r_c + 6, px)
    ix = ((rr * math.cos(a) - win[0]) / px).astype(int)
    iy = ((win[3] - rr * math.sin(a)) / px).astype(int)
    ok = (ix >= 0) & (ix < img.shape[1]) & (iy >= 0) & (iy < img.shape[0])
    R_b = float(rr[ok][np.argmax(img[iy[ok], ix[ok]])])
    white = (~img) & (np.hypot(GX, GY) >= R_b + 0.05)
    lab = ndimage.label(white)[0]
    seed = lab[int((win[3] - (c[1] + 2.0)) / px), int((c[0] + 2.0 - win[0]) / px)]
    ys, xs = np.nonzero(lab == seed)
    bx = tuple(float(v) for v in (win[0] + xs.min() * px, win[3] - ys.max() * px,
                                  win[0] + (xs.max() + 1) * px, win[3] - ys.min() * px))
    ann = Point(0, 0).buffer(r_c + 20, 2048).difference(Point(0, 0).buffer(R_b, 2048))
    return box(*bx).intersection(ann), R_b, bx


def make(layer, log):
    name_in = f"P2_BASKET-Mask_{layer}_V3B_final_B2.gbr"
    L = mk.read(os.path.join(SRC, name_in))
    objs = parse(L)
    aps = apertures(L)
    drop = []
    if layer == "M1":
        sc, n = old_screw_openings(objs)
        drop += sc
        log.append(f"{layer}: removed {len(sc)} of {n} old screw-hole openings")
        assert len(sc) == n, (len(sc), n)
    co = cross_outlines(objs, aps)
    drop += co
    log.append(f"{layer}: removed {len(co)} outline tracks of the 4 old alignment crosses")
    mw = mesh_windows_A(objs)
    assert len(mw) == 1, mw
    drop += mw
    log.append(f"{layer}: removed the corner-A mesh-contact window {tuple(round(v, 2) for v in mw[0]['bbox'])}")
    dw = drift_windows_old(objs)
    assert len(dw) == 1, dw
    drop += dw
    log.append(f"{layer}: removed the drift-pad window at the first B2 pad {tuple(round(v, 2) for v in dw[0]['bbox'])}")
    kill = sorted({i for o in drop for i in o["lines"]})
    kill = set(kill)
    L = [l for i, l in enumerate(L) if i not in kill]

    marks, _ = fp.marks_new()
    ap_out = next(k for k, v in aps.items() if abs(v - OUTLINE_W) < 1e-6)
    block = [f"G04 ==== P2 revision 2026, added {STAMP} (make_masks_2026.py) ====*"]
    if layer == "M2":
        block += ["G04 open again the old resist squares of crosses 1 and 2*", "%LPD*%"]
        for i in (1, 2):
            g, R_b, bx = m2_old_square_patch(os.path.join(SRC, name_in), fp.MARKS_NOW[i])
            block += poly_region(g)
            log.append(f"{layer}: old resist square of cross {i} {tuple(round(v, 2) for v in bx)} opened (board edge r = {R_b:.2f})")
    block += ["G04 alignment crosses: 12.5 mm resist squares*", "%LPC*%"]
    for i in (1, 2, 3, 4):
        x, y = marks[i]
        s = fp.SQUARE_NEW / 2
        block += mk.rect_region(x - s, y - s, x + s, y + s)
    block += ["G04 alignment crosses: 10 mm outlines*", "%LPD*%"]
    for i in (1, 2, 3, 4):
        block += track(cross_shape(marks[i]).exterior, ap_out)
    log.append(f"{layer}: 4 crosses, {CROSS_OUT:g} mm outline / {CROSS_ARM:g} mm arms in "
               f"{fp.SQUARE_NEW:g} mm resist squares at {[tuple(round(v, 2) for v in marks[i]) for i in (1, 2, 3, 4)]}")
    if layer == "M1":
        block += [f"G04 new screw-hole openings, diameter {HOLE_OPEN_D:g} mm*", "%LPD*%"]
        for _, x, y, _ in rg.new_frame_holes()[0]:
            block += ring_region(Point(x, y).buffer(HOLE_OPEN_D / 2, 32).exterior)
        log.append(f"{layer}: {len(rg.new_frame_holes()[0])} new screw-hole openings Ø{HOLE_OPEN_D:g}")
    w = drift_window(PAD_NEW)
    block += ["G04 drift pad at the corner centre: window over the pad*", "%LPD*%"] + mk.rect_region(*w)
    log.append(f"{layer}: {2 * mk.WIN_H:.1f} x {2 * mk.WIN_H:.1f} mm window over the drift pad at {PAD_NEW} "
               f"(inside the B2 resist island {mk.ISLAND})")
    block += ["%LPD*%"]
    L = mk.insert_before_m02(L, block)
    i = next(k for k, l in enumerate(L) if l.startswith("%FS"))
    L = L[:i] + [f"G04 P2 revision 2026 mask, {STAMP}: V3B_final + B2 + 2026 changes (P2_Revision_2026/pcb/next_version/tools/make_masks_2026.py)*"] + L[i:]
    mk.write(os.path.join(DST, f"P2_BASKET-Mask_{layer}_2026.gbr"), L)


def main():
    log = []
    for layer in ("M1", "M2"):
        make(layer, log)
    L = open(os.path.join(SRC, "P2_BASKET-MeshCut_B2.gbr")).read()
    for (ox, oy), (nx, ny) in (((PAD_OLD[0] + dx, PAD_OLD[1] + dy), (PAD_NEW[0] + dx, PAD_NEW[1] + dy))
                               for dx, dy in ((-0.5, 0), (0.5, 0), (0, -0.5), (0, 0.5))):
        old = f"X{mk.q(ox)}Y{mk.q(oy)}"
        assert L.count(old) == 1, old
        L = L.replace(old, f"X{mk.q(nx)}Y{mk.q(ny)}")
    open(os.path.join(DST, "P2_BASKET-MeshCut_2026.gbr"), "w", newline="").write(L)
    log.append("mesh cut template: from B2 (whole corner x >= 585.5, y <= 15 cleared), pad marker moved to "
               f"{PAD_NEW}")
    open(os.path.join(DST, "CHANGES_masks_2026.txt"), "w").write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
