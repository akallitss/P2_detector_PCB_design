#!/usr/bin/env python3
"""
Vector (SVG/HTML) version of the drift-contact study figures.

Reads the geometry cached by drift_contact_study.py (data/cache.pkl) and the
numbers in data/results.json, and writes  ../drift_contact.html : one page
with all drawings as SVG, labels as numbered callouts so nothing overlaps.

    python3 drift_contact_study.py   # once, builds the cache
    python3 make_page.py
"""
from __future__ import annotations

import html
import json
import math
import os
import pickle

import numpy as np

import drift_contact_study as d

OUT = d.OUT
C = pickle.load(open(d.CACHE, "rb"))
R = json.load(open(os.path.join(OUT, "data", "results.json")))


# --------------------------------------------------------------------------
class View:
    """World (mm, y up) -> SVG (px, y down) for one drawing."""

    def __init__(self, x0, x1, y0, y1, s, pad=(14, 14, 14, 14), label=""):
        self.x0, self.x1, self.y0, self.y1, self.s = x0, x1, y0, y1, s
        self.pl, self.pt, self.pr, self.pb = pad
        self.W = (x1 - x0) * s + self.pl + self.pr
        self.H = (y1 - y0) * s + self.pt + self.pb
        self.el, self.top, self.label = [], [], label

    def X(self, x): return self.pl + (x - self.x0) * self.s
    def Y(self, y): return self.pt + (self.y1 - y) * self.s

    def _pts(self, P):
        return " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}" for x, y in P)

    def inwin(self, P, m=2.0):
        P = np.asarray(P)
        return (P[:, 0].max() > self.x0 - m and P[:, 0].min() < self.x1 + m and
                P[:, 1].max() > self.y0 - m and P[:, 1].min() < self.y1 + m)

    def path(self, loops_, cls, closed=True):
        d_ = []
        for P in loops_:
            P = np.asarray(P)
            if len(P) < 2 or not self.inwin(P):
                continue
            d_.append("M" + " L".join(f"{self.X(x):.1f},{self.Y(y):.1f}" for x, y in P) + (" Z" if closed else ""))
        if d_:
            self.el.append(f'<path class="{cls}" d="{" ".join(d_)}"/>')

    def segs(self, seg, cls):
        """Raw cut segments -> chained polylines inside the window."""
        seg = np.asarray(seg)
        m = ((seg[:, :, 0].max(1) > self.x0 - 1) & (seg[:, :, 0].min(1) < self.x1 + 1) &
             (seg[:, :, 1].max(1) > self.y0 - 1) & (seg[:, :, 1].min(1) < self.y1 + 1))
        self.path(d.loops(seg[m]), cls, closed=False)

    def line(self, a, b, cls):
        self.el.append(f'<line class="{cls}" x1="{self.X(a[0]):.1f}" y1="{self.Y(a[1]):.1f}" '
                       f'x2="{self.X(b[0]):.1f}" y2="{self.Y(b[1]):.1f}"/>')

    def poly(self, P, cls):
        self.el.append(f'<polygon class="{cls}" points="{self._pts(P)}"/>')

    def pline(self, P, cls):
        self.el.append(f'<polyline class="{cls}" points="{self._pts(P)}"/>')

    def rect(self, x0, y0, x1, y1, cls):
        self.el.append(f'<rect class="{cls}" x="{self.X(min(x0, x1)):.1f}" y="{self.Y(max(y0, y1)):.1f}" '
                       f'width="{abs(x1 - x0) * self.s:.1f}" height="{abs(y1 - y0) * self.s:.1f}"/>')

    def circle(self, x, y, r, cls):
        self.el.append(f'<circle class="{cls}" cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" r="{r * self.s:.1f}"/>')

    def text(self, x, y, s, cls="lab", anchor="start", dx=0, dy=0, top=True):
        e = (f'<text class="{cls}" x="{self.X(x) + dx:.1f}" y="{self.Y(y) + dy:.1f}" '
             f'text-anchor="{anchor}">{html.escape(s)}</text>')
        (self.top if top else self.el).append(e)

    def callout(self, x, y, n, dx, dy, cls=""):
        """Numbered badge at (dx, dy) px from the world point, with a leader."""
        px, py = self.X(x), self.Y(y)
        bx, by = px + dx, py + dy
        if dx or dy:
            self.top.append(f'<line class="lead" x1="{px:.1f}" y1="{py:.1f}" x2="{bx:.1f}" y2="{by:.1f}"/>'
                            f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="2.2"/>')
        self.top.append(f'<g class="badge {cls}"><circle cx="{bx:.1f}" cy="{by:.1f}" r="10"/>'
                        f'<text x="{bx:.1f}" y="{by + 4.2:.1f}" text-anchor="middle">{n}</text></g>')

    def dim(self, a, b, txt, side=1, off=14, cls="dim"):
        """Dimension line between world points a, b, offset `off` px to one side."""
        ax, ay, bx, by = self.X(a[0]), self.Y(a[1]), self.X(b[0]), self.Y(b[1])
        L = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / L * side, (bx - ax) / L * side
        ax2, ay2, bx2, by2 = ax + nx * off, ay + ny * off, bx + nx * off, by + ny * off
        k = 9 if off >= 0 else -9
        mx, my = (ax2 + bx2) / 2 + nx * k, (ay2 + by2) / 2 + ny * k
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        if ang > 90 or ang < -90:
            ang += 180
        self.top.append(
            f'<g class="{cls}"><line class="ext" x1="{ax:.1f}" y1="{ay:.1f}" x2="{ax2 + nx * 3:.1f}" y2="{ay2 + ny * 3:.1f}"/>'
            f'<line class="ext" x1="{bx:.1f}" y1="{by:.1f}" x2="{bx2 + nx * 3:.1f}" y2="{by2 + ny * 3:.1f}"/>'
            f'<line x1="{ax2:.1f}" y1="{ay2:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" marker-start="url(#ar)" marker-end="url(#ar)"/>'
            f'<text x="{mx:.1f}" y="{my + 3.5:.1f}" text-anchor="middle" '
            f'transform="rotate({ang:.1f} {mx:.1f} {my:.1f})">{html.escape(txt)}</text></g>')

    def scalebar(self, mm, x=None, y=None):
        x = self.W - self.pr - mm * self.s if x is None else x
        y = self.H - 8 if y is None else y
        self.top.append(f'<g class="scale"><line x1="{x:.1f}" y1="{y:.1f}" x2="{x + mm * self.s:.1f}" y2="{y:.1f}"/>'
                        f'<line x1="{x:.1f}" y1="{y - 4:.1f}" x2="{x:.1f}" y2="{y + 1:.1f}"/>'
                        f'<line x1="{x + mm * self.s:.1f}" y1="{y - 4:.1f}" x2="{x + mm * self.s:.1f}" y2="{y + 1:.1f}"/>'
                        f'<text x="{x + mm * self.s / 2:.1f}" y="{y - 5:.1f}" text-anchor="middle">{mm:g} mm</text></g>')

    def svg(self):
        return (f'<svg viewBox="0 0 {self.W:.0f} {self.H:.0f}" role="img" aria-label="{html.escape(self.label)}">'
                f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="arh"/></marker></defs>'
                + "".join(self.el) + "".join(self.top) + "</svg>")


# --------------------------------------------------------------------------
# shared geometry
def big_loops(key, amin=1e5):
    return [l for l in d.loops(C[key]) if d.area(l) > amin]


Z02 = sorted(big_loops("z0.2"), key=d.area, reverse=True)       # outer, groove x2, opening
OPEN = Z02[-1]
Z42 = sorted(big_loops("z4.2"), key=d.area, reverse=True)       # outer, ledge edge
LEDGE_EDGE = Z42[-1]
HOLES = [l for l in d.loops(C["z4.2"]) if 5 < d.area(l) < 20]   # screw holes (through)
ACT = C["A_v3b"]
MP = d.MESH_PADS


def copper(v, cls="cu"):
    g = C["gerb"]["F_Cu"]
    for p in g:
        t = type(p).__name__
        if t == "ArcPoly":
            P = np.array(list(p.outline))
            if len(P) > 2 and v.inwin(P, 0) and np.ptp(P[:, 0]) < 60:
                v.poly(P, cls)
        elif t == "Line":
            P = np.array([[p.x1, p.y1], [p.x2, p.y2]])
            if v.inwin(P, 0) and p.width > 0.1:
                v.el.append(f'<line class="{cls}-tr" x1="{v.X(p.x1):.1f}" y1="{v.Y(p.y1):.1f}" x2="{v.X(p.x2):.1f}" '
                            f'y2="{v.Y(p.y2):.1f}" stroke-width="{p.width * v.s:.1f}"/>')
        elif t == "Circle":
            if v.inwin(np.array([[p.x, p.y]]), 0) and p.r > 0.3:
                v.circle(p.x, p.y, p.r, cls)


def frame_plan(v, groove=True):
    """Frame in plan: footprint (z = 0.2), ledge band (z = 4 → opening), groove, screws."""
    v.path(Z02[:1] + ([OPEN] if not groove else Z02[1:]), "frame", closed=True)
    v.path([LEDGE_EDGE, OPEN], "ledge", closed=True)
    v.path(HOLES, "hole", closed=True)


def mesh_pad(v, k):
    x0, y0, x1, y1 = MP[k]
    v.rect(x0, y0, x1, y1, "meshpad")


def section(v, key):
    L = [l for l in d.loops(C[key]) if d.area(l) > 0.5]
    v.path(L, "frame-s", closed=True)


# --------------------------------------------------------------------------
# Fig 1 — the stack, real section across the bottom edge (x = 350)
def fig_stack():
    v = View(-12.5, 9.5, -1.2, 9.2, 46, pad=(10, 10, 10, 30), label="Section across the bottom edge")
    th = 0.22                                         # thin layers drawn this thick
    v.rect(-10.33, -th * 2, 9.5, 0, "pcb")             # PCB (0.2 mm)
    for y in np.arange(5.0, 9.5, 2.0):                # readout pads
        v.rect(y, -0.02, min(y + 1.8, 9.5), 0.07, "cu")
    v.rect(-10.0, 0.0, 4.79, th, "resist")            # resist frame (M1+M2), mesh inside
    v.line((-10.0, th / 2), (4.79, th / 2), "mesh-in")
    v.line((4.79, th), (9.5, th), "mesh")             # mesh over the active area
    for y in np.arange(5.6, 9.5, 1.3):                # pillars
        v.rect(y - 0.15, 0, y + 0.15, th, "resist")
    section(v, "sec_x350")
    v.rect(-3.0, 4.0, 9.5, 4.0 + 0.12, "mylar")       # mylar on the ledge
    v.line((-3.0, 3.99), (9.5, 3.99), "drift")        # conductive coating, faces the PCB
    v.line((4.79, -1.0), (4.79, 8.9), "active")
    v.text(4.79, 8.9, "active edge", "lab act", "start", dx=4, dy=10)
    v.dim((7.5, th), (7.5, 4.0), "4 mm drift gap", side=1, off=-20)
    v.dim((-3.0, 4.12), (0.0, 4.12), "3 mm ledge", side=1, off=-26)
    v.dim((0.0, -0.45), (4.79, -0.45), "4.8 mm wall → active", side=1, off=22)
    v.callout(-6.0, 6.0, 1, 0, 0)
    v.callout(-3.4, 1.2, 2, 0, 0)
    v.callout(1.6, 4.06, 3, 0, -34)
    v.callout(-7.5, th / 2, 4, -10, -44)
    v.callout(6.5, th, 5, 0, -30)
    v.callout(8.0, -0.2, 6, 0, 30)
    return v.svg()


# --------------------------------------------------------------------------
# Fig 2 — where things are, whole sector
def fig_overview():
    v = View(30, 650, -18, 552, 1.35, pad=(8, 8, 8, 8), label="Plan of the whole sector")
    frame_plan(v, groove=False)
    v.path([ACT], "act-fill", closed=True)
    for k in MP:
        x0, y0, x1, y1 = MP[k]
        v.circle((x0 + x1) / 2, (y0 + y1) / 2, 4, "meshpad")
    v.text(330, 250, "active area", "lab big", "middle")
    v.text(330, 250, f"{R['mask']['active_area_V3B_final_mm2'] / 100:.0f} cm² (V3B_final)", "lab", "middle", dy=18)
    v.callout(607, 4, 1, -30, -46)
    v.callout(305, 522, 2, 34, 18)
    v.callout(92.3, -5, 3, -36, -14)
    v.callout(57.2, 95.8, 4, -26, -6)
    v.callout(111.6, 1.6, 5, 0, -40)
    v.callout(575, -5, 6, -34, -40)
    v.scalebar(100, x=60, y=40)
    return v.svg()


# --------------------------------------------------------------------------
# Fig 3 — concept A, plan of the bottom-right corner
def fig_corner_plan():
    v = View(584, 636, -12.5, 24, 15, pad=(8, 8, 8, 8), label="Plan of the bottom-right corner")
    v.rect(584, -12.5, 636, 24, "pcb")
    copper(v)
    frame_plan(v)
    v.segs(C["z3.0"], "cut3")
    v.path([ACT], "act-line", closed=True)
    mesh_pad(v, "bottom")
    v.rect(600.0, 2.3, 615.0, 4.8, "slot")
    v.rect(600.4, 1.0, 602.4, 7.0, "tab")
    v.circle(601.5, 3.55, 0.6, "holeA")
    v.pline([(618, 3.55), (601.5, 3.55)], "wire")
    v.callout(597.2, 2.7, 1, -26, 34)
    v.callout(610, 3.55, 2, 0, -44)
    v.callout(601.5, 3.55, 3, -30, -44)
    v.callout(602.4, 6.5, 4, 26, -34)
    v.callout(627.5, 13.0, 5, -34, 40)
    v.callout(589, 8, 6, 0, 0)
    v.callout(592.3, -7.5, 7, 0, 30)
    v.callout(601.6, 15, 8, -40, 0)
    v.scalebar(5, x=v.W - 100, y=v.H - 14)
    return v.svg()


# Fig 4 — concept A, section y = 3.5 through the slot: today vs. A
def fig_slot_section(which):
    v = View(591.5, 618, -0.9, 8.8, 34, pad=(10, 8, 10, 10), label=f"Section through the wire slot, {which}")
    v.rect(591.5, -0.2, 618, 0, "pcb")
    v.rect(591.5, 0, 600.0, 0.15, "resist")
    x0, _, x1, _ = MP["bottom"]
    v.rect(x0, 0, x1, 0.15, "meshpad")
    section(v, "sec_y3.5")
    v.rect(591.5, 4.0, 603.0, 4.12, "mylar")
    v.line((591.5, 3.99), (603.0, 3.99), "drift")
    if which == "today":
        v.pline([(618, 3.2), (600.0, 3.2)], "wire")
        v.pline([(600.0, 3.2), (599.2, 3.6), (598.8, 3.97)], "wire")
        v.dim((x1, 0.15), (600.0, 3.2), f"{R['slot']['mouth_to_bottom_mesh_pad_mm']} mm", side=-1, off=16, cls="dim bad")
        v.callout(598.8, 3.97, 1, -40, -26)
        v.callout(609, 3.2, 2, 0, 36)
        v.callout(597.2, 0.15, 3, -30, 22)
    else:
        v.rect(600.0, 2.6, 615.0, 3.8, "pot")
        v.rect(600.9, 3.8, 602.1, 4.0, "agepoxy")
        v.pline([(618, 3.2), (601.5, 3.2), (601.5, 4.0)], "wire")
        v.rect(600.4, 3.99, 602.4, 4.06, "tab")
        v.dim((600.0, 4.12), (603.0, 4.12), "3 mm ledge", side=-1, off=30)
        v.callout(601.5, 3.9, 1, -44, 34)
        v.callout(601.0, 4.04, 2, -64, -26)
        v.callout(609, 3.2, 3, 0, 36)
        v.callout(597.2, 0.15, 4, -30, 22)
    v.scalebar(2, x=v.W - 90, y=v.H - 10)
    return v.svg()


# --------------------------------------------------------------------------
# Fig 5 — A2: second feed
def fig_a2_plan():
    v = View(560, 622, -13, 12, 12.5, pad=(8, 8, 8, 8), label="Second drift feed at x = 575")
    v.rect(560, -13, 622, 12, "pcb")
    copper(v)
    frame_plan(v)
    v.segs(C["z3.0"], "cut3")
    v.path([ACT], "act-line", closed=True)
    mesh_pad(v, "bottom")
    v.rect(600.0, 2.3, 615.0, 4.8, "slot")
    v.rect(573.75, -10.0, 576.25, 0.0, "slot new")
    v.circle(575.0, -1.5, 0.6, "holeA")
    v.circle(601.5, 3.55, 0.6, "holeA")
    v.dim((575.0, 0.0), (575.0, 4.8), "", side=1, off=0, cls="dim ok")
    v.callout(575, -6, 1, -40, 0)
    v.callout(575, -1.5, 2, 34, -36)
    v.callout(575, 2.4, 3, -36, -26)
    v.callout(607, 3.55, 4, 0, 40)
    v.scalebar(5, x=v.W - 100, y=v.H - 12)
    return v.svg()


def fig_a2_section():
    v = View(-12.5, 7.5, -0.9, 8.8, 34, pad=(10, 8, 10, 10), label="Section at x = 575")
    v.rect(-10.33, -0.2, 7.5, 0, "pcb")
    v.rect(-10.0, 0, 4.79, 0.15, "resist")
    section(v, "sec_x575")
    v.rect(-10.0, 2.6, 0.0, 3.8, "slot new")
    v.rect(-2.1, 3.8, -0.9, 4.0, "holeA")
    v.rect(-3.0, 4.0, 7.5, 4.12, "mylar")
    v.line((-3.0, 3.99), (7.5, 3.99), "drift")
    v.line((4.79, -0.6), (4.79, 8.6), "active")
    v.dim((0.0, 3.2), (4.79, 0.15), f"{R['second_slot']['bottom_wall_mouth_to_bare_mesh_mm']} mm", side=1, off=12,
          cls="dim ok")
    v.callout(-5, 3.2, 1, 0, -54)
    v.callout(-1.5, 3.9, 2, 20, -64)
    v.callout(-3.5, 1.2, 3, 0, 0)
    v.scalebar(2, x=v.W - 70, y=v.H - 10)
    return v.svg()


def fig_top_corner():
    v = View(284, 343, 500, 545, 9, pad=(8, 8, 8, 8), label="Top corner")
    v.rect(284, 500, 343, 545, "pcb")
    copper(v)
    frame_plan(v)
    v.segs(C["z3.0"], "cut3")
    v.path([ACT], "act-line", closed=True)
    mesh_pad(v, "top")
    a, b = np.array(d.TOP_MIRROR[0]), np.array(d.TOP_MIRROR[1])
    u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]]) * 1.25
    v.poly([a + n, b + n, b - n, a - n], "slot bad")
    hits = np.array(C["slot_tests"]["top corner, mirror of the bottom slot"]["points"])
    for x, y in hits:
        v.circle(x, y, 0.35, "hit")
    v.callout(*(a + b) / 2, 1, 40, 30)
    v.callout(302.15, 529.34, 2, -36, 10)
    v.callout(*MP["top"][:2], 3, -30, -20)
    v.scalebar(10, x=24, y=26)
    return v.svg()


# --------------------------------------------------------------------------
# Fig 6 — concept B: best clearance per place
def fig_b_bars():
    order = ["inner-left corner", "inner-bottom corner", "bottom-right corner", "top corner",
             "top straight", "outer arc", "inner arc", "bottom straight"]
    rows = [(k, R["conceptB"][k]["pad_edge_to_bare_mesh_mm"]) for k in order]
    W, rowh, l, r = 760, 34, 170, 60
    H = rowh * len(rows) + 46
    s = (W - l - r) / 4.0
    el = []
    for t in range(5):
        x = l + t * s
        el.append(f'<line class="grid" x1="{x:.1f}" y1="10" x2="{x:.1f}" y2="{H - 30}"/>'
                  f'<text class="tick" x="{x:.1f}" y="{H - 14}" text-anchor="middle">{t} mm</text>')
    for i, (k, val) in enumerate(rows):
        y = 14 + i * rowh
        ok = val >= d.CLEARANCE_MM
        el.append(f'<text class="lab" x="{l - 10}" y="{y + 15}" text-anchor="end">{k}</text>'
                  f'<rect class="bar {"ok" if ok else "bad"}" x="{l}" y="{y + 3}" width="{val * s:.1f}" height="{rowh - 10}"/>'
                  f'<text class="num" x="{l + val * s + 6:.1f}" y="{y + 15}">{val:.2f}</text>')
    xr = l + d.CLEARANCE_MM * s
    el.append(f'<line class="rule" x1="{xr:.1f}" y1="6" x2="{xr:.1f}" y2="{H - 30}"/>'
              f'<text class="rulet" x="{xr + 4:.1f}" y="{H - 34}">1 kV rule, 3 mm</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Pad edge to bare mesh, by place">'
            + "".join(el) + "</svg>")


def fig_b_section():
    v = View(-12.5, 7.5, -0.9, 8.8, 34, pad=(10, 8, 10, 30), label="Spring contact section")
    v.rect(-10.33, -0.2, 7.5, 0, "pcb")
    v.rect(-10.0, 0, 0.5, 0.15, "resist")
    v.rect(3.5, 0, 4.79, 0.15, "resist")
    v.line((4.79, 0.15), (7.5, 0.15), "mesh")
    section(v, "sec_x350")
    v.rect(-3.0, 4.0, 7.5, 4.12, "mylar")
    v.line((-3.0, 3.99), (7.5, 3.99), "drift")
    v.rect(1.0, -0.02, 3.0, 0.08, "drift-pad")
    v.pline([(2, 0.1), (1.6, 0.6), (2.4, 1.1), (1.6, 1.6), (2.4, 2.1), (1.6, 2.6), (2.4, 3.1), (1.6, 3.6), (2, 3.98)],
            "spring")
    v.line((4.79, -0.6), (4.79, 8.6), "active")
    v.dim((3.0, -0.2), (4.79, -0.2), "2.2–2.5 mm", side=1, off=20, cls="dim bad")
    v.callout(2.0, 0.05, 1, -44, 34)
    v.callout(2.0, 2.0, 2, -50, -20)
    v.callout(0.4, 0.1, 3, -30, -50)
    v.scalebar(2, x=v.W - 70, y=v.H - 10)
    return v.svg()


# --------------------------------------------------------------------------
def main():
    figs = {
        "stack": fig_stack(), "overview": fig_overview(),
        "corner": fig_corner_plan(), "today": fig_slot_section("today"), "conceptA": fig_slot_section("concept A"),
        "a2plan": fig_a2_plan(), "a2sec": fig_a2_section(), "top": fig_top_corner(),
        "bbars": fig_b_bars(), "bsec": fig_b_section(),
    }
    tpl = open(os.path.join(d.HERE, "page_template.html")).read()
    for k, s in figs.items():
        tpl = tpl.replace("{{" + k + "}}", s)
    for k, val in {
        "act_v3b": f"{R['mask']['active_area_V3B_final_mm2'] / 100:.0f}",
        "act_v2": f"{R['mask']['active_area_V2_mm2'] / 100:.0f}",
        "mouth": R["slot"]["mouth_to_bottom_mesh_pad_mm"],
        "mouth2": R["second_slot"]["bottom_wall_mouth_to_bare_mesh_mm"],
        "hits": R["second_slot"]["top corner, mirror of the bottom slot"]["surfaces_crossed"],
        "b_il": R["conceptB"]["inner-left corner"]["pad_edge_to_bare_mesh_mm"],
        "b_ib": R["conceptB"]["inner-bottom corner"]["pad_edge_to_bare_mesh_mm"],
    }.items():
        tpl = tpl.replace("{{" + k + "}}", str(val))
    out = os.path.join(OUT, "drift_contact.html")
    open(out, "w").write(tpl)
    print("wrote", out, f"{os.path.getsize(out) / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
