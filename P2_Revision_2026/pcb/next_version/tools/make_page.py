#!/usr/bin/env python3
"""
P2 basket PCB, next version: page for the PCB designers on two items (state of 2026-10-26).

  1. Alignment crosses (PCB F.Cu/B.Cu + insulation masks): bigger, inner crosses 1, 2
     moved clear of the new screw holes (r = 104.25 at 47.5 / 12.5 deg).
  2. Corner A drift contact: drift pad at the centre of the cleared corner, fed by
     today's mesh line and M pads (the mesh is contacted at corner B only).

Everything is measured on the real files:
  PCB       Version_Apr26/FABRICATION_P2 (and the B2 patched copy for the Sig1 removal)
  masks     Version_Sept26/Insulation_masks/V3B_final
  frame     DRIFT_P2_261124 STL (via P2_Revision_2026/drift_contact/data/cache.pkl)
  layout    P2_Revision_2026/mechanics/tools/rev_geometry.py, fig_pcb.py (+ its CSV tables)

    python3 alignment_marks.py && python3 fit_marks.py && python3 fig_pcb.py && python3 make_page.py
writes ../next_pcb_items.html
"""
from __future__ import annotations

import base64
import csv
import html
import io
import json
import math
import os
import pickle
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

import alignment_marks as am

q = am.q
OUT = am.OUT
ROOT = am.ROOT
sys.path.insert(0, os.path.join(ROOT, "P2_Revision_2026", "drift_contact", "tools"))
import drift_contact_study as d                       # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "P2_Revision_2026", "pcb", "drift_pad_B2", "tools"))
import make_b2_files as b2                            # noqa: E402
import fig_pcb as fp                                  # noqa: E402  (new cross positions, corner-A drift net)
rg = fp.rg

C = pickle.load(open(os.path.join(ROOT, "P2_Revision_2026", "drift_contact", "data", "cache.pkl"), "rb"))
Z = sorted([l for l in d.loops(C["z0.2"]) if d.area(l) > 1e5], key=d.area, reverse=True)
OUTER, OPEN = Z[0], Z[3]
ACT = C["A_v3b"]
FIT = json.load(open(os.path.join(OUT, "data", "alignment_fit.json")))
MARKS_NEW = fp.marks_new()[0]           # {1..4: centre}; 1, 2 moved for the new screw holes
ARM = 4.5                 # proposed copper arm length (9 mm span)
LINE = 0.3                # proposed copper line width
MASK_ARM_W = LINE + 2 * 0.5
PATCH = 12.5              # proposed resist square in the masks

hatch = lambda p: type(p).__name__ == "ArcPoly" and len(list(p.outline)) > 5000


# --------------------------------------------------------------------------
class View:
    def __init__(self, x0, x1, y0, y1, s, label=""):
        self.x0, self.x1, self.y0, self.y1, self.s = x0, x1, y0, y1, s
        self.W, self.H = (x1 - x0) * s, (y1 - y0) * s
        self.el, self.top, self.label = [], [], label

    def X(self, x): return (x - self.x0) * self.s
    def Y(self, y): return (self.y1 - y) * self.s

    def image(self, rgba):
        im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
        b = io.BytesIO(); im.save(b, "PNG", optimize=True)
        self.el.append(f'<image href="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}" x="0" y="0" '
                       f'width="{self.W:.1f}" height="{self.H:.1f}" preserveAspectRatio="none"/>')

    def pline(self, P, cls, closed=False):
        pts = " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}" for x, y in P)
        tag = "polygon" if closed else "polyline"
        self.el.append(f'<{tag} class="{cls}" points="{pts}"/>')

    def rect(self, x0, y0, x1, y1, cls):
        self.el.append(f'<rect class="{cls}" x="{self.X(x0):.1f}" y="{self.Y(y1):.1f}" '
                       f'width="{(x1 - x0) * self.s:.1f}" height="{(y1 - y0) * self.s:.1f}"/>')

    def circle(self, c, r, cls):
        self.el.append(f'<circle class="{cls}" cx="{self.X(c[0]):.1f}" cy="{self.Y(c[1]):.1f}" r="{r * self.s:.1f}"/>')

    def geom(self, g, cls):
        """shapely (Multi)Polygon, outer rings only."""
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and not p.is_empty:
                self.pline(list(p.exterior.coords), cls, closed=True)

    def line(self, a, b, cls):
        self.el.append(f'<line class="{cls}" x1="{self.X(a[0]):.1f}" y1="{self.Y(a[1]):.1f}" '
                       f'x2="{self.X(b[0]):.1f}" y2="{self.Y(b[1]):.1f}"/>')

    def cross(self, c, arm, cls):
        self.line((c[0] - arm, c[1]), (c[0] + arm, c[1]), cls)
        self.line((c[0], c[1] - arm), (c[0], c[1] + arm), cls)

    def badge(self, x, y, n, dx=0, dy=0):
        px, py = self.X(x), self.Y(y)
        bx, by = px + dx, py + dy
        if dx or dy:
            self.top.append(f'<line class="lead" x1="{px:.1f}" y1="{py:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>')
        self.top.append(f'<g class="badge"><circle cx="{bx:.1f}" cy="{by:.1f}" r="10"/>'
                        f'<text x="{bx:.1f}" y="{by + 4:.1f}" text-anchor="middle">{n}</text></g>')

    def dim(self, a, b, txt, side=1, off=12):
        ax, ay, bx, by = self.X(a[0]), self.Y(a[1]), self.X(b[0]), self.Y(b[1])
        L = math.hypot(bx - ax, by - ay); nx, ny = -(by - ay) / L * side, (bx - ax) / L * side
        ax2, ay2, bx2, by2 = ax + nx * off, ay + ny * off, bx + nx * off, by + ny * off
        k = 9 if off >= 0 else -9
        mx, my = (ax2 + bx2) / 2 + nx * k, (ay2 + by2) / 2 + ny * k
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        if ang > 90 or ang < -90:
            ang += 180
        self.top.append(f'<g class="dim"><line x1="{ax2:.1f}" y1="{ay2:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" '
                        f'marker-start="url(#ar)" marker-end="url(#ar)"/><text x="{mx:.1f}" y="{my + 3.5:.1f}" '
                        f'text-anchor="middle" transform="rotate({ang:.1f} {mx:.1f} {my:.1f})">{html.escape(txt)}</text></g>')

    def scalebar(self, mm):
        x, y = self.W - mm * self.s - 12, self.H - 10
        self.top.append(f'<g class="scale"><line x1="{x:.1f}" y1="{y:.1f}" x2="{x + mm * self.s:.1f}" y2="{y:.1f}"/>'
                        f'<text x="{x + mm * self.s / 2:.1f}" y="{y - 5:.1f}" text-anchor="middle">{mm:g} mm</text></g>')

    def svg(self):
        return (f'<svg viewBox="0 0 {self.W:.0f} {self.H:.0f}" role="img" aria-label="{html.escape(self.label)}">'
                '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                'orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="arh"/></marker></defs>'
                + "".join(self.el) + "".join(self.top) + "</svg>")


def copper_bg(win, px, F, B, E, skip=lambda p: False, keep_hole=lambda x, y, dd: True):
    """Coloured raster of the board: hatch, F.Cu, B.Cu, holes (today's drill file), outside the board."""
    GX, GY = q.grid(win, px)
    f = q.raster([p for p in F if not skip(p) and not hatch(p)], win, px)
    b = q.raster([p for p in B if not skip(p) and not hatch(p)], win, px)
    h = q.raster([p for p in F + B if hatch(p)], win, px)
    edge = q.raster(E, win, px)
    lab = ndimage.label(~ndimage.binary_dilation(edge, iterations=2))[0]
    cy, cx = lab.shape[0] // 2, lab.shape[1] // 2
    board = lab == lab[cy, cx]
    hole = np.zeros_like(f)
    for x, y, dd in am.drills():
        if win[0] - 3 < x < win[1] + 3 and win[2] - 3 < y < win[3] + 3 and keep_hole(x, y, dd):
            hole |= np.hypot(GX - x, GY - y) <= dd / 2
    img = np.zeros(f.shape + (4,)); img[...] = (0.95, 0.95, 0.92, 1)
    img[h] = (0.90, 0.86, 0.78, 1)
    img[b] = (0.62, 0.74, 0.90, 1)
    img[f] = (0.86, 0.62, 0.36, 1)
    img[hole] = (0.25, 0.25, 0.28, 1)
    img[~board] = (0.80, 0.80, 0.83, 1)
    return img


# --------------------------------------------------------------------------
def fig_overview():
    v = View(30, 650, -18, 552, 1.25, "P2 basket PCB: alignment crosses and the mesh-contact corner")
    v.pline(OUTER[::4], "frame", closed=True)
    v.pline(OPEN[::4], "open", closed=True)
    v.pline(ACT, "act", closed=True)
    board_edges(v)
    offs = [(-30, -20), (-34, 6), (-34, -24), (24, -16)]
    for k, o in enumerate(offs, 1):
        c = MARKS_NEW[k]
        v.cross(c, 6, "mark")
        v.badge(*c, k, *o)
    for _, x, y, _ in rg.new_frame_holes()[0]:
        v.circle((x, y), 2.4, "holedot")
    v.badge(*rg.B2_PAD[:2], 5, -32, -28)
    v.top.append(f'<text class="lab" x="{v.X(330):.0f}" y="{v.Y(250):.0f}" text-anchor="middle">active area</text>')
    return v.svg()


def fig_holes():
    """Screw holes on the board: KEEP / REMOVE / ADD, numbered as the frame and carbon back."""
    import fig_pcb_holes as ph
    v = View(30, 655, -34, 552, 1.5, "P2 basket PCB: screw holes to keep, remove and add")
    v.pline(OPEN[::4], "open", closed=True)
    board_edges(v)
    for act, no, x, y, e, pl in ph.plan():
        if act == "REMOVE":
            v.line((x - 2.2, y - 2.2), (x + 2.2, y + 2.2), "hrem")
            v.line((x - 2.2, y + 2.2), (x + 2.2, y - 2.2), "hrem")
            continue
        v.circle((x, y), 2.6, "hkeep" if act == "KEEP" else "hadd")
        tx, ty = ph.edge_label(no, x, y, e)
        cls = "hnum hnumadd" if act == "ADD" else "hnum"
        v.top.append(f'<text class="{cls}" x="{v.X(tx):.1f}" y="{v.Y(ty) + 4:.1f}" text-anchor="middle">{no}</text>')
    v.top.append(f'<text class="lab" x="{v.X(330):.0f}" y="{v.Y(250):.0f}" text-anchor="middle">active area</text>')
    return v.svg()


def hole_rows():
    """Rows of pcb_screw_holes.csv (written by fig_pcb_holes.py) as HTML."""
    rows = list(csv.reader(open(os.path.join(OUT, "data", "pcb_screw_holes.csv"))))
    out = []
    for act, no, x, y, d, e, pl_now, pl_new, note in rows[1:]:
        out.append(f'<tr><td class="act-{act.lower()}">{act}</td><td>{no}</td><td>({x}, {y})</td><td>{html.escape(e)}</td>'
                   f'<td>{html.escape(pl_now)}</td><td>{html.escape(pl_new)}</td><td>{html.escape(note)}</td></tr>')
    return "\n  ".join(out)


def board_edges(v):
    for p in C["gerb"]["Edge_Cuts"]:
        if type(p).__name__ == "Line":
            v.line((p.x1, p.y1), (p.x2, p.y2), "edge")
        else:
            r = math.hypot(p.x1 - p.cx, p.y1 - p.cy)
            a0 = math.atan2(p.y1 - p.cy, p.x1 - p.cx); a1 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
            da = (a1 - a0) % (2 * math.pi)
            if p.clockwise:
                da -= 2 * math.pi
            t = np.linspace(a0, a0 + da, 30)
            v.pline(np.c_[p.cx + r * np.cos(t), p.cy + r * np.sin(t)], "edge")


def fig_cross(k, F, B, E, M2):
    c0 = tuple(am.CROSSES[k]); c = tuple(MARKS_NEW[k + 1])
    m = ((c0[0] + c[0]) / 2, (c0[1] + c[1]) / 2)
    half = max(8.5, math.hypot(c[0] - c0[0], c[1] - c0[1]) / 2 + 7.5)   # today's and the new cross both in view
    win = (m[0] - half, m[0] + half, m[1] - half, m[1] + half)
    v = View(*win, 22 * 8.5 / half, f"Alignment cross {k + 1}")
    v.image(copper_bg(win, 0.03, F, B, E, skip=lambda p: am.is_cross_line(p, c0)))
    for _, x, y, _ in rg.new_frame_holes()[0]:
        if win[0] - 3 < x < win[1] + 3 and win[2] - 3 < y < win[3] + 3:
            v.circle((x, y), rg.SCREW_D / 2, "newhole")
    # today: copper cross (3 mm) and the mask outline square
    v.cross(c0, 1.5, "now")
    v.rect(c0[0] - 0.58, c0[1] - 1.47, c0[0] + 0.58, c0[1] + 1.47, "nowmask")
    v.rect(c0[0] - 1.47, c0[1] - 0.58, c0[0] + 1.47, c0[1] + 0.58, "nowmask")
    # proposal
    if c != c0:
        v.line(c0, c, "move")
    P = PATCH / 2
    v.rect(c[0] - P, c[1] - P, c[0] + P, c[1] + P, "patch")
    a, w = ARM + 0.5, MASK_ARM_W / 2
    v.rect(c[0] - a, c[1] - w, c[0] + a, c[1] + w, "newmask")
    v.rect(c[0] - w, c[1] - a, c[0] + w, c[1] + a, "newmask")
    v.cross(c, ARM, "new")
    v.dim((c[0] - ARM, c[1] - ARM - 0.9), (c[0] + ARM, c[1] - ARM - 0.9), f"{2 * ARM:g} mm", side=-1, off=0)
    v.scalebar(5)
    return v.svg()


def corner_skip(mparts, hv):
    """Copper not on the 2026 board, in the B2 patched Gerbers: today's mesh net (drawn as vectors
    instead), the old D pads and the top GND pad, the first B2 pad, its F.Cu stub, the two vias and
    the B.Cu route with its GND cut."""
    from shapely.geometry import LineString, box
    route = LineString(rg.B2_TRACE_BCU).buffer(0.8)
    mb = [g.bounds for g in mparts] + [g.bounds for g in list(hv["d"]) + [hv["gnd_top"]]]
    ox, oy, _ = rg.B2_PAD_OLD
    _, H = rg.read_drill()
    screws = [(x, y) for k in (3, 6) for x, y in H[k]]

    def skip(p):
        try:
            (a, b), (c, d) = p.bounding_box()
        except Exception:
            return False
        cx, cy, w = (a + c) / 2, (b + d) / 2, c - a
        bb = box(a, b, c, d)
        if any(max(abs(a - m[0]), abs(b - m[1]), abs(c - m[2]), abs(d - m[3])) < 0.1 for m in mb):
            return True
        if (abs(cx - ox) < 0.2 and abs(cy - oy) < 0.2 and w < 3.2) or (abs(cx - 590.5) < 0.3 and 7.2 < cy < 8.7 and w < 0.6):
            return True
        if any(math.hypot(cx - x, cy - y) < 0.1 and w < 1.1 for x, y in ((590.5, 7.6), (626.3, 15.8))):
            return True
        if type(p).__name__ == "Line" and route.contains(LineString([(p.x1, p.y1), (p.x2, p.y2)])):
            return True
        if type(p).__name__ == "Circle" and any(math.hypot(p.x - x, p.y - y) < 0.05 for x, y in screws):
            return True                       # pad of a screw hole that goes away
        if type(p).__name__ == "Line" and abs(p.width - 0.3) < 1e-3 and any(
                box(*fp.HV_LABELS_A[k]).contains(bb.centroid) for k in fp.LABELS_GONE):
            return True                       # copper text M / top GND
        return route.contains(bb) or (not getattr(p, "polarity_dark", True) and bb.intersects(route))
    return skip


def fig_corner():
    win = (583.0, 638.0, -1.5, 24.5)
    v = View(*win, 20, "Corner A: drift pad at the corner centre, fed by today's mesh line")
    mnet, mparts = fp.m_net_A(C)
    added, removed, kept, hv = fp.drift_net_A(mparts)
    F = q.load(os.path.join(b2.FAB_OUT, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(b2.FAB_OUT, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(b2.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    sig1_hole = (589.183, 10.999)
    D, H = rg.read_drill()
    screws = [(x, y) for k in (3, 6) for x, y in H[k]]            # today's screw holes: replaced
    keep = lambda x, y, dd: (math.hypot(x - sig1_hole[0], y - sig1_hole[1]) > 0.05
                             and min(math.hypot(x - a, y - b) for a, b in screws) > 0.05)
    v.image(copper_bg(win, 0.025, F, B, E, skip=corner_skip(mparts, hv), keep_hole=keep))
    del F, B
    for _, hx, hy, _ in rg.new_frame_holes()[0]:
        if win[0] - 3 < hx < win[1] + 3 and win[2] - 3 < hy < win[3] + 3:
            v.circle((hx, hy), rg.SCREW_D / 2, "newhole")
    v.pline(OPEN, "wall", closed=False)
    v.rect(*b2.ISLAND, "island")
    x, y, s = rg.B2_PAD
    net = kept.union(added)
    v.geom(net.buffer(rg.CLEAR_HV), "keepout")
    v.geom(kept, "kept")
    v.geom(added, "driftpad")
    v.rect(x - b2.WIN_H, y - b2.WIN_H, x + b2.WIN_H, y + b2.WIN_H, "winnew")
    v.geom(removed, "removed")
    ox, oy, _ = rg.B2_PAD_OLD
    v.rect(ox - 1.5, oy - 1.5, ox + 1.5, oy + 1.5, "unused")
    y1 = rg.B2_CUT[3]
    v.pline([(rg.B2_CUT[0], win[2]), (rg.B2_CUT[0], y1), (math.sqrt(600 ** 2 - y1 ** 2), y1)], "cutline")
    v.pline([(win[0], 1.9), (rg.B2_CUT[0], 1.9)], "meshedge")
    v.pline([(598.1, y1), (598.1, win[3])], "meshedge")
    v.dim((rg.B2_CUT[0], y), (x - s / 2, y), f"{x - s / 2 - rg.B2_CUT[0]:.2f}", side=1, off=-16)
    v.dim((x, y + s / 2), (x, y1), f"{y1 - y - s / 2:.1f}", side=-1, off=-16)
    dc = hv["d_new"].centroid
    v.badge(x, y, 1, -40, -40)
    v.badge(596.5, 6.8, 2, 10, 40)
    v.badge(611.0, 9.2, 3, 0, 40)
    v.top.append(f'<text class="dlabel" x="{v.X(dc.x):.1f}" y="{v.Y(dc.y) + 7:.1f}" text-anchor="middle">D</text>')
    v.badge(dc.x + 2.0, dc.y - 2.5, 4, 40, 34)
    gt = hv["gnd_top"].centroid
    v.badge(gt.x, gt.y, 5, 30, -24)
    v.badge(597.2, 2.7, 5, 26, 34)
    v.badge(rg.B2_CUT[0], 15.0, 6, -24, -16)
    v.badge(589.0, 14.0, 7, 0, -26)
    v.badge(606.0, 13.6, 8, 0, -26)
    v.badge(ox - 1.5, oy + 1.5, 9, -26, -20)
    v.scalebar(5)
    return v.svg()


def png_uri(name, width=1600):
    """A figure of ../figures (written by fig_pcb.py) as an inline data URI, scaled down."""
    im = Image.open(os.path.join(OUT, "figures", name)).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def corner_rows():
    """Rows of pcb_corner_A_drift.csv (written by fig_pcb.py) as HTML."""
    rows = list(csv.reader(open(os.path.join(OUT, "data", "pcb_corner_A_drift.csv"))))
    out = []
    for r in rows[1:]:
        act, item, layer, x0, y0, x1, y1, note = r
        where = f"({x0}, {y0}) – ({x1}, {y1})" if x0 else "–"
        if "start and end" in note:
            where = f"({x0}, {y0}) → ({x1}, {y1})"
        out.append(f'<tr><td class="act-{html.escape(act.split()[0])}">{html.escape(act)}</td><td>{html.escape(item)}</td>'
                   f'<td>{html.escape(layer)}</td><td>{where}</td><td>{html.escape(note)}</td></tr>')
    return "\n  ".join(out)


# --------------------------------------------------------------------------
def main():
    F = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    M2 = None
    figs = {"overview": fig_overview(), "corner": fig_corner(), "corner_rows": corner_rows(),
            "holes": fig_holes(), "hole_rows": hole_rows(), "steps_png": png_uri("pcb_corner_A_steps.png")}
    for k in range(4):
        figs[f"cross{k + 1}"] = fig_cross(k, F, B, E, M2)
    tpl = open(os.path.join(am.HERE, "page_template.html")).read()
    for kk, vv in figs.items():
        tpl = tpl.replace("{{" + kk + "}}", vv)
    for k, f in enumerate(FIT, 1):
        tpl = tpl.replace("{{c%d}}" % k, "(%.2f, %.2f)" % tuple(f["original_centre"]))
        tpl = tpl.replace("{{p%d}}" % k, "(%.2f, %.2f)" % tuple(MARKS_NEW[k]))
    x, y, s = rg.B2_PAD
    for kk, vv in {"pad": f"({x:g}, {y:g})", "bend": "(%g, %g)" % rg.M_TRACE_BEND, "trace_w": f"{rg.M_TRACE_W:g}",
                   "pad_old": "(%g, %g)" % rg.B2_PAD_OLD[:2]}.items():
        tpl = tpl.replace("{{" + kk + "}}", vv)
    assert "{{" not in tpl, tpl[tpl.index("{{"):tpl.index("{{") + 40]
    out = os.path.join(OUT, "next_pcb_items.html")
    open(out, "w").write(tpl)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
