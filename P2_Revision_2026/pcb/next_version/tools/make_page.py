#!/usr/bin/env python3
"""
P2 basket PCB, next version: placeholder page for two open items.

  1. Alignment crosses (PCB F.Cu/B.Cu + insulation masks): where they are and
     how big they can become.
  2. Bottom mesh-contact pad: how big it can become next to the B2 drift pad.

Everything is measured on the real files:
  PCB       Version_Apr26/FABRICATION_P2 (and the B2 patched copy for item 2)
  masks     Version_Sept26/Insulation_masks/V3B_final
  frame     DRIFT_P2_261124 STL (via P2_Revision_2026/drift_contact/data/cache.pkl)

    python3 alignment_marks.py && python3 fit_marks.py && python3 make_page.py
writes ../next_pcb_items.html
"""
from __future__ import annotations

import base64
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

C = pickle.load(open(os.path.join(ROOT, "P2_Revision_2026", "drift_contact", "data", "cache.pkl"), "rb"))
Z = sorted([l for l in d.loops(C["z0.2"]) if d.area(l) > 1e5], key=d.area, reverse=True)
OUTER, OPEN = Z[0], Z[3]
ACT = C["A_v3b"]
FIT = json.load(open(os.path.join(OUT, "data", "alignment_fit.json")))
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


def copper_bg(win, px, F, B, E, skip=lambda p: False):
    """Coloured raster of the board: hatch, F.Cu, B.Cu, holes, outside the board."""
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
        if win[0] - 3 < x < win[1] + 3 and win[2] - 3 < y < win[3] + 3:
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
    offs = [(-30, -20), (-34, 6), (-34, -24), (24, -16)]
    for k, (c, o) in enumerate(zip(am.CROSSES, offs), 1):
        v.cross(c, 6, "mark")
        v.badge(*c, k, *o)
    v.badge(597.0, 3.0, 5, -32, -28)
    v.top.append(f'<text class="lab" x="{v.X(330):.0f}" y="{v.Y(250):.0f}" text-anchor="middle">active area</text>')
    return v.svg()


def fig_cross(k, F, B, E, M2):
    c0 = tuple(am.CROSSES[k]); fit = FIT[k]; c = tuple(fit["proposed_centre"])
    half = 8.5                                     # proposal centred; today's cross is within 4 mm
    win = (c[0] - half, c[0] + half, c[1] - half, c[1] + half)
    v = View(*win, 22, f"Alignment cross {k + 1}")
    v.image(copper_bg(win, 0.03, F, B, E, skip=lambda p: am.is_cross_line(p, c0)))
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


def fig_meshpad():
    win = (583.0, 602.0, -2.0, 17.0)
    v = View(*win, 34, "Bottom mesh-contact corner with the B2 drift pad")
    F = q.load(os.path.join(b2.FAB_OUT, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(b2.FAB_OUT, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(b2.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    v.image(copper_bg(win, 0.02, F, B, E))
    v.pline(OPEN, "wall", closed=False)
    # B2 items
    px, py, h = b2.PAD[0], b2.PAD[1], b2.PAD_H
    v.rect(*b2.ISLAND[:2], *b2.ISLAND[2:], "island")
    v.rect(px - b2.CUT_H, py - b2.CUT_H, px + b2.CUT_H, py + b2.CUT_H, "cut")
    v.rect(px - h, py - h, px + h, py + h, "driftpad")
    # mesh extent (mesh trimmed at the outer edge of the resist border)
    v.pline([(583.0, 1.9), (598.1, 1.9), (598.1, 13.0)], "meshedge")
    # today: copper pad and M2 window
    v.rect(595.77, 1.29, 598.70, 4.10, "padnow")
    v.rect(595.82, 2.15, 597.82, 4.15, "winnow")
    # options
    v.rect(593.70, 1.29, 598.70, 4.29, "optA")
    v.rect(595.00, 1.29, 598.70, 5.00, "optB")
    v.dim((593.7, 4.29), (593.7, 8.5), "4.2", side=1, off=-14)
    v.badge(px, py, 1, -46, -30)
    v.badge(585.5, 15.0, 2, -24, -14)
    v.badge(585.0, 9.0, 3, -18, 0)
    v.badge(597.2, 3.1, 4, 30, 34)
    v.badge(594.2, 2.6, 5, -40, 30)
    v.badge(596.0, 4.7, 6, 34, -30)
    v.badge(598.1, 9.0, 7, 30, 0)
    v.scalebar(2)
    return v.svg()


# --------------------------------------------------------------------------
def main():
    F = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-F_Cu.gbr"))
    B = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-B_Cu.gbr"))
    E = q.load(os.path.join(am.FAB, "Gerber", "P2_BASKET-Edge_Cuts.gbr"))
    M2 = None
    figs = {"overview": fig_overview(), "meshpad": fig_meshpad()}
    for k in range(4):
        figs[f"cross{k + 1}"] = fig_cross(k, F, B, E, M2)
    tpl = open(os.path.join(am.HERE, "page_template.html")).read()
    for kk, vv in figs.items():
        tpl = tpl.replace("{{" + kk + "}}", vv)
    for k, f in enumerate(FIT, 1):
        tpl = tpl.replace("{{c%d}}" % k, "(%.2f, %.2f)" % tuple(f["original_centre"]))
        tpl = tpl.replace("{{p%d}}" % k, "(%.2f, %.2f)" % tuple(f["proposed_centre"]))
    out = os.path.join(OUT, "next_pcb_items.html")
    open(out, "w").write(tpl)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
