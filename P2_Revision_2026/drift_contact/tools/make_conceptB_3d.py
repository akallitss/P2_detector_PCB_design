#!/usr/bin/env python3
"""
Interactive 3D view of the P2 HV contacts with concept B (PCB drift pad +
spring): the whole sector, the bottom-right HV corner (mesh contact, M and D
pads), the inner-left drift pad, and the inner-bottom corner that does not
work.  Built from the real frame STL, PCB Gerbers and V3B_final M2 mask.

Writes  ../conceptB_3d.html  (three.js page, everything embedded) and, with
--step, the proposed new parts as  ../cad/conceptB_inner_left_parts.step
(needs FreeCAD), all in the frame/PCB coordinate system (mm).

    python3 drift_contact_study.py     # once, builds data/cache.pkl
    python3 make_conceptB_3d.py [--step]
"""
from __future__ import annotations

import base64
import io
import json
import math
import os
import pickle
import re
import subprocess
import sys

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.path import Path
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

import drift_contact_study as d

sys.path.insert(0, os.path.join(d.ROOT, "Version_Sept26", "tools"))
import render_gerber as rg          # noqa: E402  (mask rasteriser, honours polarity)

OUT = d.OUT
C = pickle.load(open(d.CACHE, "rb"))
R = json.load(open(os.path.join(OUT, "data", "results.json")))
M2 = os.path.join(d.ROOT, "Version_Sept26", "Insulation_masks", "V3B_final", "P2_BASKET-Mask_M2_V3B_final.gbr")
M2_PAINT = rg.interpret(M2)["paint"]

PX = 0.035                      # detail texture resolution, mm per pixel
PX_OV = 0.5                     # overview texture resolution
GRID = 0.05                     # frame mesh vertex clustering, mm

# ---- proposal (concept B) -----------------------------------------------
PAD_R = d.PAD_R                 # Ø2 gold pad
RESIST_WIN_R = 1.3              # M1/M2 window around the pad
MESH_CUT_R = 4.0                # mesh cut-out round the pad: its edge 3 mm from the pad edge
CU_CLEAR = 3.0                  # GND copper pulled back this far from drift copper
TRACE_W = 0.3
VIA_DRILL, VIA_PAD = 0.4, 1.0   # same drill as the board's existing vias
ROUTE_OFFSET = 3.0              # B.Cu drift route: this far outside the frame opening
RESIST_T, MESH_Z = 0.15, 0.15   # resist under the mesh (amplification gap); mesh on top
COVER_T = 0.0                   # the mesh is laminated last: no resist above it
MESH_BORDER = 2.75              # mesh ends at the outer edge of the 2.6 mm M2 border (confirmed by the user)
MYLAR_Z, MYLAR_T = 4.0, 0.05

# frame loops at z = 0.2: outer face, O-ring groove (2), opening
Z02 = sorted([l for l in d.loops(C["z0.2"]) if d.area(l) > 1e5], key=d.area, reverse=True)
OUTER, GROOVE_OUT, GROOVE_IN, OPEN = Z02
LEDGE_EDGE = sorted([l for l in d.loops(C["z4.2"]) if d.area(l) > 1e5], key=d.area)[0]
ACT = C["A_v3b"]
ACT_T = cKDTree(d.dense(ACT, 0.1))

# HV pads at the bottom-right corner (F.Cu, read from the copper text M / D / GND)
M_PADS = [np.array([623.6, 11.0]), np.array([627.0, 9.0])]
D_PADS = [np.array([626.3, 15.8]), np.array([629.7, 13.7])]
GND_PADS = [np.array([622.2, 2.5]), np.array([632.9, 18.6])]
MESH_PAD = np.array([(d.MESH_PADS["bottom"][0] + d.MESH_PADS["bottom"][2]) / 2,
                     (d.MESH_PADS["bottom"][1] + d.MESH_PADS["bottom"][3]) / 2])
TOP_MESH_PAD = np.array([300.98, 515.97])
TOP_HV = np.array([324.0, 536.5])


def unit(v):
    v = np.asarray(v, float)
    return v / np.hypot(*v)


# inner-left corner: pad from the clearance study, via just outside the O-ring
IL_PAD = np.array(R["conceptB"]["inner-left corner"]["best_centre"])
IL_OUT = unit(unit([math.cos(math.radians(150)), math.sin(math.radians(150))]) - unit(IL_PAD))
IL_VIA = IL_PAD + 8.5 * IL_OUT          # 1.7 mm outside the groove, 6.5 mm from the nearest screw
IB_PAD = np.array(R["conceptB"]["inner-bottom corner"]["best_centre"])
D_VIA = D_PADS[0]                       # the drift route comes up in the D pad, outside the frame


def drift_route():
    """B.Cu route: via at the inner-left pad -> along the inner arc and the bottom wall,
    ROUTE_OFFSET outside the opening -> up the bottom-right corner -> via in the D pad."""
    P = d.dense(OPEN, 0.5)
    P = P[np.r_[True, np.hypot(*np.diff(P, axis=0).T) > 1e-6]]
    t = np.roll(P, -6, 0) - np.roll(P, 6, 0)            # tangent over ±3 mm: the STL cut is jittery
    t /= np.hypot(*t.T)[:, None]
    n = np.c_[-t[:, 1], t[:, 0]]
    flip = Path(OPEN).contains_points(P + 0.5 * n)       # make every normal point out of the opening
    n[flip] *= -1
    Q = P + ROUTE_OFFSET * n
    Q = Q[Path(OPEN).contains_points(Q) == False]       # noqa: E712
    start = IL_PAD + 2.0 * IL_OUT                        # route leaves the via towards the wall
    end = np.array([603.0, 6.0])
    i0 = int(np.argmin(np.hypot(*(Q - start).T)))
    i1 = int(np.argmin(np.hypot(*(Q - end).T)))
    a = Q[i0:i1 + 1] if i0 <= i1 else np.r_[Q[i0:], Q[:i1 + 1]]
    b = Q[i1:i0 + 1][::-1] if i1 <= i0 else np.r_[Q[i1:], Q[:i0 + 1]][::-1]
    L = lambda S: np.hypot(*np.diff(S, axis=0).T).sum()
    path = a if L(a) < L(b) else b
    if np.hypot(*(path[0] - start)) > np.hypot(*(path[-1] - start)):
        path = path[::-1]
    # keep it simple: decimate to ~2 mm, then add the two ends
    keep = [0]
    for i in range(1, len(path)):
        if np.hypot(*(path[i] - path[keep[-1]])) >= 2.0:
            keep.append(i)
    path = path[keep]
    route = np.r_[[IL_VIA], path, [[603.0, 6.0], [616.0, 8.5], D_VIA]]   # passes the screw at (610.3, 14.5) 7 mm away
    return route


ROUTE = drift_route()
ROUTE_LEN = float(np.hypot(*np.diff(ROUTE, axis=0).T).sum())

# ---- variant B2: the corner readout pad next to the HV pads is given up for the drift pad
B2_PAD = np.array([590.5, 10.0])          # square pad in the old readout pad, island meets the corner border
B2_VIA = np.array([590.5, 7.6])          # next to it, under the resist island
B2_SQ = {"pad": 1.5, "win": 1.8, "cut": 5.0, "island_box": (584.6, 4.4, 595.4, 16.0)}   # half-sizes (mm) of the square pad, M1/M2 window,
                                                               # mesh cut (3 mm from the pad edge) and island (+1 mm)
B2_ROUTE = np.array([B2_VIA, [600.0, 7.0], [616.0, 8.5], D_VIA])
B2_ROUTE_LEN = float(np.hypot(*np.diff(B2_ROUTE, axis=0).T).sum())
SIG1_VIA = np.array([589.183, 10.999])


def b2_removed():
    """ids of the primitives removed in B2: the corner readout pad (F.Cu) and its signal trace (B.Cu)."""
    f, b = set(), set()
    for p in C["gerb"]["F_Cu"]:
        t = type(p).__name__
        if t == "ArcPoly":
            P = np.array(list(p.outline))
            if np.ptp(P[:, 0]) > 5 and np.hypot(*(P.mean(0) - [590.5, 11.3])) < 0.5:
                f.add(id(p)); box = (P.min(0), P.max(0))
    for p in C["gerb"]["F_Cu"]:
        if type(p).__name__ == "Circle" and box[0][0] < p.x < box[1][0] and box[0][1] < p.y < box[1][1]:
            f.add(id(p))
    segs = [p for p in C["gerb"]["B_Cu"] if type(p).__name__ == "Line"]
    cur, todo = [SIG1_VIA], True
    while todo:
        todo = False
        for p in segs:
            if id(p) in b:
                continue
            a, c = np.array([p.x1, p.y1]), np.array([p.x2, p.y2])
            for q in list(cur):
                if np.hypot(*(a - q)) < 0.01 or np.hypot(*(c - q)) < 0.01:
                    b.add(id(p)); cur += [a, c]; todo = True
                    break
    for p in C["gerb"]["B_Cu"]:
        if type(p).__name__ == "Circle" and np.hypot(p.x - SIG1_VIA[0], p.y - SIG1_VIA[1]) < 0.05:
            b.add(id(p))
    return f, b


B2_SKIP_F, B2_SKIP_B = b2_removed()


# --------------------------------------------------------------------------
class Win:
    def __init__(self, x0, x1, y0, y1, px):
        self.x0, self.x1, self.y0, self.y1, self.px = x0, x1, y0, y1, px
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.nx, self.ny = int(round((x1 - x0) / px)), int(round((y1 - y0) / px))
        xs = x0 + (np.arange(self.nx) + 0.5) * px
        ys = y1 - (np.arange(self.ny) + 0.5) * px          # row 0 = top
        self.X, self.Y = np.meshgrid(xs, ys)
        self.P = np.c_[self.X.ravel(), self.Y.ravel()]

    def inside(self, loop):
        return Path(loop).contains_points(self.P).reshape(self.ny, self.nx)

    def dist_seg(self, a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        ab = b - a
        t = np.clip(((self.X - a[0]) * ab[0] + (self.Y - a[1]) * ab[1]) / max(ab @ ab, 1e-12), 0, 1)
        return np.hypot(self.X - a[0] - t * ab[0], self.Y - a[1] - t * ab[1])

    def dist_poly(self, pts):
        out = np.full(self.X.shape, np.inf)
        for a, b in zip(pts[:-1], pts[1:]):
            if max(a[0], b[0]) < self.x0 - 5 or min(a[0], b[0]) > self.x1 + 5 or \
                    max(a[1], b[1]) < self.y0 - 5 or min(a[1], b[1]) > self.y1 + 5:
                continue
            out = np.minimum(out, self.dist_seg(a, b))
        return out

    def dist_pt(self, p):
        return np.hypot(self.X - p[0], self.Y - p[1])

    def draw(self, fn):
        """Coverage (0..1) of whatever `fn(ax)` draws in black, antialiased."""
        fig = Figure(figsize=(self.nx / 100, self.ny / 100), dpi=100)
        FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(self.x0, self.x1); ax.set_ylim(self.y0, self.y1)
        ax.axis("off")
        fn(ax)
        fig.canvas.draw()
        a = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].astype(float)
        return 1 - a.mean(2) / 255

    def lw(self, mm):   # mm -> points for this figure
        return max(mm, self.px) / self.px * 72 / 100


def copper(w, layer, skip=frozenset()):
    """Coverage of a copper layer in the window."""
    def fn(ax):
        from matplotlib.patches import Polygon as Pg, Circle as Ci
        for p in C["gerb"][layer]:
            if id(p) in skip:
                continue
            t = type(p).__name__
            if t == "ArcPoly":
                P = np.array(list(p.outline))
                if len(P) > 2 and P[:, 0].max() > w.x0 and P[:, 0].min() < w.x1 \
                        and P[:, 1].max() > w.y0 and P[:, 1].min() < w.y1:
                    ax.add_patch(Pg(P, closed=True, fc="k", ec="none"))
            elif t == "Line":
                if max(p.x1, p.x2) > w.x0 - 1 and min(p.x1, p.x2) < w.x1 + 1 and \
                        max(p.y1, p.y2) > w.y0 - 1 and min(p.y1, p.y2) < w.y1 + 1:
                    ax.plot([p.x1, p.x2], [p.y1, p.y2], color="k", lw=w.lw(p.width), solid_capstyle="round")
            elif t == "Circle":
                if w.x0 - 2 < p.x < w.x1 + 2 and w.y0 - 2 < p.y < w.y1 + 2:
                    ax.add_patch(Ci((p.x, p.y), p.r, fc="k", ec="none"))
    return w.draw(fn)


def board_mask(w):
    """Inside the board outline: Edge_Cuts drawn as walls, flood-filled from the opening."""
    img = Image.new("L", (w.nx, w.ny), 0)
    dr = ImageDraw.Draw(img)
    X = lambda x: (x - w.x0) / w.px
    Y = lambda y: (w.y1 - y) / w.px
    for p in C["gerb"]["Edge_Cuts"]:
        if type(p).__name__ == "Line":
            dr.line([(X(p.x1), Y(p.y1)), (X(p.x2), Y(p.y2))], fill=255, width=2)
        else:
            r = math.hypot(p.x1 - p.cx, p.y1 - p.cy)
            a0 = math.atan2(p.y1 - p.cy, p.x1 - p.cx); a1 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
            da = (a1 - a0) % (2 * math.pi)
            if p.clockwise:
                da -= 2 * math.pi
            t = np.linspace(a0, a0 + da, 60)
            dr.line([(X(p.cx + r * math.cos(u)), Y(p.cy + r * math.sin(u))) for u in t], fill=255, width=2)
    ins = np.argwhere(w.inside(OPEN))
    iy, ix = ins[len(ins) // 2]
    ImageDraw.floodfill(img, (int(ix), int(iy)), 128)
    return (np.asarray(img) > 0).astype(float)


def png_b64(rgba):
    im = Image.fromarray(np.clip(rgba * 255, 0, 255).astype(np.uint8), "RGBA")
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode()


def rgba(mask, color, alpha=1.0):
    c = np.array([int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    out = np.zeros(np.shape(mask) + (4,))
    out[..., :3] = c
    out[..., 3] = mask * alpha
    return out


def over(dst, src):
    a = src[..., 3:4]
    dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    dst[..., 3:4] = a + dst[..., 3:4] * (1 - a)
    return dst


# --------------------------------------------------------------------------
def _clip_poly(P, axis, val, keep_below):
    """Sutherland-Hodgman: keep the part of polygon P with P[axis] <= val (or >=)."""
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        ina = a[axis] <= val if keep_below else a[axis] >= val
        inb = b[axis] <= val if keep_below else b[axis] >= val
        if ina:
            out.append(a)
        if ina != inb:
            t = (val - a[axis]) / (b[axis] - a[axis])
            out.append(a + t * (b - a))
    return out


_TRI = None


def frame_mesh(w):
    """Frame triangles clipped to the window box, then simplified on a grid."""
    global _TRI
    if _TRI is None:
        _TRI = d.load_stl(d.STL)
    tri = _TRI
    x0, x1, y0, y1 = w.x0, w.x1, w.y0, w.y1
    lo, hi = tri.min(1), tri.max(1)
    near = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > y0) & (lo[:, 1] < y1)
    inside = near & (lo[:, 0] >= x0) & (hi[:, 0] <= x1) & (lo[:, 1] >= y0) & (hi[:, 1] <= y1)
    T = [tri[inside]]
    extra = []
    for t in tri[near & ~inside]:
        P = list(t)
        for axis, val, below in ((0, x1, True), (0, x0, False), (1, y1, True), (1, y0, False)):
            if len(P) < 3:
                break
            P = _clip_poly(P, axis, val, below)
        for k in range(1, len(P) - 1):
            extra.append([P[0], P[k], P[k + 1]])
    if extra:
        T.append(np.array(extra))
    T = np.concatenate(T)
    V = np.round(T.reshape(-1, 3) / GRID).astype(np.int64)
    u, inv = np.unique(V, axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    F = F[ok]
    _, keep = np.unique(np.sort(F, 1), axis=0, return_index=True)
    F = F[np.sort(keep)]
    P = (u * GRID - [w.cx, w.cy, 0]).astype(np.float32)
    return {"pos": base64.b64encode(P.tobytes()).decode(),
            "idx": base64.b64encode(F.astype(np.uint32).tobytes()).decode(),
            "ntri": int(len(F))}


def loc(w, p, z):
    return [float(p[0] - w.cx), float(p[1] - w.cy), float(z)]


def detail(name, cx, cy, half, out, verdict, pad=None, labels=(), cables=(), proposal=True, ghost=False,
           feed=IL_VIA, route=ROUTE, skip_f=frozenset(), skip_b=frozenset(), sq=None):
    """One corner at full detail.  `pad` is the concept-B drift pad, if the corner has one."""
    w = Win(cx - half, cx + half, cy - half, cy + half, PX)
    board = board_mask(w)
    if pad is not None:
        ax_, ay_ = np.abs(w.X - pad[0]), np.abs(w.Y - pad[1])
        cheb = np.maximum(ax_, ay_)                          # square shapes
        if sq:   # distance to a square pad
            dpad = np.hypot(np.maximum(ax_ - sq["pad"], 0), np.maximum(ay_ - sq["pad"], 0)) - 0.0
            pad_in = cheb <= sq["pad"]
        else:
            dpad = w.dist_pt(pad) - PAD_R
            pad_in = dpad <= 0
    fcu, bcu = copper(w, "F_Cu", skip_f), copper(w, "B_Cu", skip_b)
    dvia = w.dist_pt(D_VIA)
    dilv = w.dist_pt(feed)
    droute = w.dist_poly(route)

    # --- top (F.Cu): drift pad + trace to the via, GND pulled back round them
    drift_top = np.zeros_like(board, bool)
    keep = np.ones_like(board, bool)
    if pad is not None and proposal:
        dtr = w.dist_seg(pad, feed)
        drift_top |= pad_in | (dtr <= TRACE_W / 2) | (dilv <= VIA_PAD / 2)
        keep &= (dpad > CU_CLEAR) & (dtr > TRACE_W / 2 + CU_CLEAR) & (dilv > VIA_PAD / 2 + CU_CLEAR)
    elif pad is not None:
        drift_top |= pad_in
    top = rgba(board, "#cfd8a8")
    top = over(top, rgba(fcu * board * keep, "#c98a4b"))
    top = over(top, rgba(drift_top * board, "#e2b82a"))
    for p in (feed, D_VIA):
        top = over(top, rgba((w.dist_pt(p) <= VIA_DRILL / 2) * 1.0, "#3a3f46"))

    # --- bottom (B.Cu): the drift route, GND hatch cut back along it
    bot = rgba(board, "#cfd8a8")
    rkeep = (droute > TRACE_W / 2 + CU_CLEAR) & (dvia > VIA_PAD / 2 + CU_CLEAR) & (dilv > VIA_PAD / 2 + CU_CLEAR)
    if not proposal:
        rkeep = np.ones_like(board, bool)
    bot = over(bot, rgba(bcu * board * rkeep, "#c98a4b"))
    if proposal:
        drift_bot = (droute <= TRACE_W / 2) | (dvia <= VIA_PAD / 2) | (dilv <= VIA_PAD / 2)
        bot = over(bot, rgba(drift_bot * board, "#d0452b"))
        for p in (feed, D_VIA):
            bot = over(bot, rgba((w.dist_pt(p) <= VIA_DRILL / 2) * 1.0, "#3a3f46"))

    # --- resist: V3B_final M2 clear (= resist) inside the frame opening
    dark = rg.rasterise(M2_PAINT, (w.x0, w.y0), (w.x1, w.y1), PX)
    dark = np.array(Image.fromarray(dark).resize((w.nx, w.ny), Image.NEAREST))
    opening = w.inside(OPEN)
    active = w.inside(ACT)
    resist = (~dark) & opening
    win = np.zeros_like(opening)
    if pad is not None and proposal:
        win = (cheb <= sq["win"]) if sq else (w.dist_pt(pad) <= RESIST_WIN_R)
    island = np.zeros_like(opening)
    if sq:
        bx = sq["island_box"]
        island = opening & (w.X >= bx[0]) & (w.X <= bx[2]) & (w.Y >= bx[1]) & (w.Y <= bx[3])
        resist |= island & ~win
    resist_border = resist & (~active | island) & ~win
    pillars = resist & active & ~island
    dact = ACT_T.query(w.P)[0].reshape(w.ny, w.nx)
    mesh = opening & (active | (dact <= MESH_BORDER))
    if pad is not None and proposal:
        mesh &= (cheb > sq["cut"]) if sq else (w.dist_pt(pad) > MESH_CUT_R)
    bare = mesh & ~resist          # pillar gaps, the mesh-contact window, any channel through the border
    meshtex = rgba(mesh * 1.0, "#6f7f92", 0.55)
    gridpat = ((np.floor(w.X / 0.25) + np.floor(w.Y / 0.25)) % 2 == 0)
    meshtex[..., 3] *= np.where(gridpat, 1.0, 0.7)
    meshtex = over(meshtex, rgba(bare * 1.0, "#2c6bb3", 0.55))

    keepout = np.zeros_like(board)
    if pad is not None:
        keepout = (np.abs(dpad - 3.0) < 0.06) * 1.0

    return {
        "kind": "detail", "name": name, "ghost": ghost, "w": w.x1 - w.x0, "h": w.y1 - w.y0,
        "out": unit(out).tolist(), "verdict": verdict,
        "frame": frame_mesh(w),
        "tex": {
            "top": png_b64(top), "bot": png_b64(bot),
            "resist": png_b64(rgba(resist_border * 1.0, "#5c9c7f", 0.92)),
            "pillars": png_b64(rgba(pillars * 1.0, "#5c9c7f", 1.0)),
            "mesh": png_b64(meshtex),
            "mylar": png_b64(rgba(w.inside(LEDGE_EDGE) * 1.0, "#d8e4ee", 0.35)),
            "keepout": png_b64(rgba(keepout, "#d0452b", 1.0)),
        },
        "act": [[float(x - w.cx), float(y - w.cy)] for x, y in
                ACT[(ACT[:, 0] > w.x0 - 3) & (ACT[:, 0] < w.x1 + 3) & (ACT[:, 1] > w.y0 - 3) & (ACT[:, 1] < w.y1 + 3)]],
        "pad": None if pad is None else loc(w, pad, 0)[:2],
        "spring": bool(pad is not None and proposal), "padsq": sq["pad"] if sq else None,
        "vias": [loc(w, p, 0)[:2] for p in (feed, D_VIA)
                 if proposal and w.x0 < p[0] < w.x1 and w.y0 < p[1] < w.y1],
        "cables": [{"c": c, "pts": [loc(w, p[:2], p[2]) for p in pts]} for c, pts in cables],
        "labels": [{"n": n, "p": loc(w, p[:2], p[2]), "t": t, "l": l} for n, p, t, l in labels],
        "dims": {"resist_t": RESIST_T, "mesh_z": MESH_Z, "cover_t": COVER_T, "mylar_z": MYLAR_Z,
                 "mylar_t": MYLAR_T, "pad_r": PAD_R},
    }


def simplify(loop, step=1.0):
    keep = [0]
    for i in range(1, len(loop)):
        if np.hypot(*(loop[i] - loop[keep[-1]])) >= step:
            keep.append(i)
    return loop[keep]


def overview(labels, route=ROUTE, drift=IL_PAD, name="Whole sector", verdict=""):
    x0, x1, y0, y1 = 30.0, 646.0, -16.0, 546.0
    w = Win(x0, x1, y0, y1, PX_OV)
    board = board_mask(w)
    top = over(rgba(board, "#cfd8a8"), rgba(copper(w, "F_Cu") * board, "#c98a4b"))
    bot = over(rgba(board, "#cfd8a8"), rgba(copper(w, "B_Cu") * board, "#c98a4b", 0.6))
    S = lambda L: [[float(x - w.cx), float(y - w.cy)] for x, y in simplify(L)]
    return {
        "kind": "overview", "name": "Whole sector", "w": x1 - x0, "h": y1 - y0, "out": [0, -1],
        "verdict": "", "tex": {"top": png_b64(top), "bot": png_b64(bot)},
        "outer": S(OUTER), "open": S(OPEN), "ledge": S(LEDGE_EDGE), "act": S(ACT),
        "route": [[float(x - w.cx), float(y - w.cy)] for x, y in route],
        "pads": {"drift": loc(w, drift, 0)[:2], "mesh": [loc(w, MESH_PAD, 0)[:2], loc(w, TOP_MESH_PAD, 0)[:2]]},
        "labels": [{"n": n, "p": loc(w, p[:2], p[2]), "t": t, "l": l} for n, p, t, l in labels],
        "dims": {"mylar_z": MYLAR_Z},
    }


# --------------------------------------------------------------------------
def parts_step(path, pad=IL_PAD, via_p=IL_VIA, route=ROUTE, sq=None):
    """Proposed new parts as solids in the frame coordinate system (FreeCAD)."""
    s = f"""
import FreeCAD as App, Part, math
doc = App.newDocument("conceptB")
V = App.Vector
SQ = {sq!r}
def box(h, z0, t):
    return Part.makeBox(2 * h, 2 * h, t, V({pad[0]} - h, {pad[1]} - h, z0))
pad = box(SQ["pad"], 0, 0.035) if SQ else Part.makeCylinder({PAD_R}, 0.035, V({pad[0]}, {pad[1]}, 0))
via = Part.makeCylinder({VIA_PAD / 2}, 0.2, V({via_p[0]}, {via_p[1]}, -0.2)).cut(
      Part.makeCylinder({VIA_DRILL / 2}, 0.2, V({via_p[0]}, {via_p[1]}, -0.2)))
L = math.hypot({via_p[0] - pad[0]}, {via_p[1] - pad[1]})
tr = Part.makeBox(L, {TRACE_W}, 0.035, V(0, -{TRACE_W / 2}, 0))
tr.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(math.atan2({via_p[1] - pad[1]}, {via_p[0] - pad[0]})))
tr.translate(V({pad[0]}, {pad[1]}, 0))
tip = {MYLAR_Z} - 0.035
barrel = Part.makeCylinder(0.75, 2.6 - 0.035, V({pad[0]}, {pad[1]}, 0.035)).fuse(
         Part.makeCylinder(0.95, 0.25 - 0.035, V({pad[0]}, {pad[1]}, 0.035)))
plunger = Part.makeCylinder(0.4, tip - 0.4 - 2.6, V({pad[0]}, {pad[1]}, 2.6)).fuse(
          Part.makeSphere(0.4, V({pad[0]}, {pad[1]}, tip - 0.4)))
spring = barrel.fuse(plunger)
tab = Part.makeCylinder(2.5, 0.035, V({pad[0]}, {pad[1]}, tip))
rwin = box(SQ["win"], 0, {RESIST_T + COVER_T}) if SQ else Part.makeCylinder({RESIST_WIN_R}, {RESIST_T + COVER_T}, V({pad[0]}, {pad[1]}, 0))
pad_x, pad_y = {pad[0]}, {pad[1]}
mcut = box(SQ["cut"], {MESH_Z - 0.01}, 0.02) if SQ else Part.makeCylinder({MESH_CUT_R}, 0.02, V({pad[0]}, {pad[1]}, {MESH_Z - 0.01}))
pts = {[[float(x), float(y)] for x, y in route]}
segs = []
for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
    l = math.hypot(bx - ax, by - ay)
    if l < 1e-6:
        continue
    b = Part.makeBox(l, {TRACE_W}, 0.035, V(0, -{TRACE_W / 2}, 0))
    b.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(math.atan2(by - ay, bx - ax)))
    b.translate(V(ax, ay, -0.235))
    segs.append(b)
route = Part.makeCompound(segs)
dvia = Part.makeCylinder({VIA_PAD / 2}, 0.2, V({D_VIA[0]}, {D_VIA[1]}, -0.2)).cut(
      Part.makeCylinder({VIA_DRILL / 2}, 0.2, V({D_VIA[0]}, {D_VIA[1]}, -0.2)))
extra = []
if SQ:
    bx_ = SQ["island_box"]
    isl = Part.makeBox(bx_[2] - bx_[0], bx_[3] - bx_[1], {RESIST_T + COVER_T}, V(bx_[0], bx_[1], 0)).cut(rwin)
    extra = [("resist_island_M1_M2", isl)]
for n, sh in [("drift_pad_F_Cu", pad), ("drift_trace_F_Cu", tr), ("via_next_to_pad", via), ("pogo_pin_envelope", spring), ("landing_tab_on_window", tab),
              ("resist_window_M1_M2", rwin), ("mesh_cut_out", mcut), ("drift_route_B_Cu", route),
              ("via_in_D_pad", dvia)] + extra:
    o = doc.addObject("Part::Feature", n); o.Shape = sh
doc.recompute()
import Import
Import.export(doc.Objects, r"{path}")
print("STEP written")
"""
    tmp = os.path.join(os.path.dirname(path), "_make_step.py")
    open(tmp, "w").write(s)
    try:
        if os.path.exists(path):
            os.remove(path)
        r = subprocess.run(["snap", "run", "freecad.cmd", tmp], capture_output=True, text=True, timeout=300)
        ok = os.path.exists(path)
        print("STEP:", "written" if ok else "FAILED\n" + r.stdout[-800:] + r.stderr[-800:])
    except Exception as e:                                   # FreeCAD missing: page still builds
        print("STEP skipped:", e)
    finally:
        for f in (tmp, os.path.join(os.path.dirname(path), "__pycache__")):
            if os.path.isfile(f):
                os.remove(f)
            elif os.path.isdir(f):
                import shutil; shutil.rmtree(f)


# --------------------------------------------------------------------------
def main():
    mz = MYLAR_Z
    rl = f"{ROUTE_LEN:.0f} mm"

    ov = overview([
        (1, (*MESH_PAD, 0.2), "Mesh contact: gold pad, mesh laminated onto it", "pcb"),
        (2, (625.0, 12.5, 0.2), "HV pads M and D: both cables solder here", "pcb"),
        (3, (*IL_PAD, 0.2), "Drift contact: gold pad + pogo pin up to the window", "pcb"),
        (4, (*ROUTE[len(ROUTE) // 3], -0.2), f"Drift route on the back (B.Cu), about {rl}", "pcb"),
        (5, (*TOP_MESH_PAD, 0.2), "Second mesh contact (top corner)", "pcb"),
        (6, (*TOP_HV, 0.2), "Second HV pad cluster (top corner), unused here", "pcb"),
        (7, (330.0, 250.0, MESH_Z), "Active area: bare mesh at 450 V", "pcb"),
        (8, (200.0, 300.0, mz), "Mylar window at 800 V, 4 mm above the mesh", "mylar"),
    ])

    br_c = np.array([611.0, 6.0])
    br = detail("Bottom-right: HV pads and mesh contact", *br_c, 18.0, (1.0, -0.4),
                '<b class="ok">Both HV cables land here, side by side.</b> The mesh reaches M through the front copper; '
                'the drift voltage reaches D through the back copper.',
                labels=[
                    (1, (*MESH_PAD, MESH_Z), "Gold mesh-contact pad: the mesh is laminated straight onto it", "mesh"),
                    (2, (608.0, 6.4, 0.04), "M trace on the front (F.Cu), under the frame and O-ring", "pcb"),
                    (3, (*M_PADS[0], 0.05), "M solder pad: mesh HV cable (450 V)", "pcb"),
                    (4, (*D_PADS[0], 0.05), "D solder pad: drift HV cable (800 V); the via in it comes from the back", "pcb"),
                    (5, (603.0, -2.0, -0.2), f"Drift route on the back (B.Cu), from the inner-left pad, about {rl}", "pcb"),
                    (6, (*GND_PADS[0], 0.05), "GND pads", "pcb"),
                    (7, (612.0, 3.55, 3.2), "Today's wire slot: not needed with B (fill it with epoxy)", "frame"),
                    (8, (592.0, 12.0, MESH_Z), "Active area: bare mesh", "mesh"),
                    (9, (594.0, 2.0, mz), "Mylar window", "mylar"),
                ],
                cables=[("mesh", [(*M_PADS[0], 0.05), (*M_PADS[0], 0.8), (629.0, 4.0, 1.2)]),
                        ("drift", [(*D_PADS[0], 0.05), (*D_PADS[0], 0.8), (629.0, 22.0, 1.2)])], ghost=True)

    il_c = (IL_PAD + IL_VIA) / 2 + np.array([2.0, 1.5])
    il = detail("Inner-left: drift pad and spring", *il_c, 14.0, IL_OUT,
                f'<b class="ok">Fits the 1 kV rule.</b> Pad edge to nearest bare mesh: '
                f'{R["conceptB"]["inner-left corner"]["pad_edge_to_bare_mesh_mm"]} mm. '
                'The red ring is the 3 mm keep-out; it never reaches bare mesh.',
                pad=IL_PAD,
                labels=[
                    (1, (*IL_PAD, 0.05), "Ø2 gold drift pad on the PCB", "pcb"),
                    (2, (*IL_PAD, 2.0), "Pogo pin soldered on the pad after the bulk; tip on a copper tab glued to the window coating", "spring"),
                    (3, (*(IL_PAD + 1.2 * unit(IL_PAD - IL_VIA)), RESIST_T), "Window in M1/M2 where the pad overlaps the resist border", "resist"),
                    (4, (*(IL_PAD + 4.0 * unit([1, -1.2])), MESH_Z), "Mesh cut-out Ø8: every mesh edge stays 3 mm from the pad", "mesh"),
                    (5, (*(IL_PAD + 4.0 * unit([1, 0.3])), 0.2), "3 mm keep-out from the pad edge: clear of bare mesh", "mesh"),
                    (6, (*((IL_PAD + IL_VIA) / 2), 0.04), "F.Cu trace under the frame wall and O-ring", "pcb"),
                    (7, (*IL_VIA, -0.2), "Via outside the O-ring, so no gas leak path", "pcb"),
                    (8, (*ROUTE[3], -0.2), f"B.Cu drift route to the D pad at the bottom-right corner, about {rl}", "pcb"),
                    (9, (*(IL_PAD + 3.0 * unit([0.7, 0.5])), mz), "Mylar window, coating facing down", "mylar"),
                    (10, (*(IL_PAD + 0.9 * IL_OUT + 3.5 * unit([0.5, 0.866])), 0.02),
                     "Strip at the wall: resist under the frame, no mesh", "pcb"),
                ])

    b2l = f"{B2_ROUTE_LEN:.0f} mm"
    b2 = detail("B2: corner readout pad given up", 607.0, 7.0, 22.0, (1.0, -0.4),
                '<b class="ok">Fits the 1 kV rule, all HV in one corner.</b> Costs one readout channel. '
                'The red ring (3 mm from the pad edge) stays on the resist island.',
                pad=B2_PAD, feed=B2_VIA, route=B2_ROUTE, skip_f=B2_SKIP_F, skip_b=B2_SKIP_B,
                sq=B2_SQ, ghost=True,
                labels=[
                    (1, (*B2_PAD, 0.05), "3 × 3 mm gold drift pad where the corner readout pad was (pad removed)", "pcb"),
                    (2, (*B2_PAD, 2.0), "Pogo pin soldered on the pad after the bulk; tip on a copper tab glued to the window coating", "spring"),
                    (3, (*(B2_PAD + [-5.4, 3.0]), RESIST_T + COVER_T), "Resist island (about 10.8 × 11.6 mm) in M1/M2, with a 3.6 × 3.6 mm window over the pad", "resist"),
                    (4, (*(B2_PAD + [-5.0, -1.0]), MESH_Z), "Mesh cut 10 × 10 mm at the final trim: 3.5 mm from the pad edge, resting on the island", "mesh"),
                    (5, (*(B2_PAD + [0.0, 4.5]), 0.2), "3 mm keep-out from the pad edge (rounded square): no mesh inside it", "mesh"),
                    (6, (*B2_VIA, -0.2), "Via next to the pad (inside the gas volume, like every readout via)", "pcb"),
                    (7, (608.0, 7.8, -0.2), f"Drift route on the back (B.Cu), about {b2l}, gap cut in the GND hatch", "pcb"),
                    (8, (*SIG1_VIA, -0.2), "Old signal trace and via of that pad removed: nothing at 800 V reaches the readout connector", "pcb"),
                    (9, (*MESH_PAD, MESH_Z), "Mesh-contact pad, 5.8 mm from the drift pad", "mesh"),
                    (10, (*M_PADS[0], 0.05), "M pad: mesh cable", "pcb"),
                    (11, (*D_PADS[0], 0.05), "D pad: drift cable; the via in it comes from the back", "pcb"),
                    (12, (590.1, 19.0, 0.05), "Next readout pad, 5.4 mm away (the one to the left is 5.6 mm away)", "pcb"),
                ],
                cables=[("mesh", [(*M_PADS[0], 0.05), (*M_PADS[0], 0.8), (629.0, 4.0, 1.2)]),
                        ("drift", [(*D_PADS[0], 0.05), (*D_PADS[0], 0.8), (629.0, 24.0, 1.2)])])

    ov2 = {"ref": 0, "name": "B2 whole sector",
           "route": [[float(x - 338.0), float(y - 265.0)] for x, y in B2_ROUTE],
           "pads": {"drift": [float(B2_PAD[0] - 338.0), float(B2_PAD[1] - 265.0)], "mesh": ov["pads"]["mesh"]},
           "verdict": "<b>B2, whole sector.</b> Everything sits in the bottom-right corner; the rest of the sector is unchanged.",
           "labels": [{"n": n, "p": [p[0] - 338.0, p[1] - 265.0, p[2]], "t": t, "l": "pcb"} for n, p, t in [
               (1, (*MESH_PAD, 0.2), "Mesh contact: gold pad, mesh laminated onto it"),
               (2, (625.0, 12.5, 0.2), "HV pads M and D: both cables solder here"),
               (3, (*B2_PAD, 0.2), "Drift contact: gold pad + pogo pin, on the corner readout pad"),
               (4, (608.0, 7.8, -0.2), f"Drift route on the back (B.Cu), about {B2_ROUTE_LEN:.0f} mm"),
               (5, (*TOP_MESH_PAD, 0.2), "Second mesh contact (top corner)"),
               (6, (*TOP_HV, 0.2), "Second HV pad cluster (top corner), unused here"),
               (7, (330.0, 250.0, MESH_Z), "Active area: bare mesh at 450 V"),
               (8, (200.0, 300.0, MYLAR_Z), "Mylar window at 800 V, 4 mm above the mesh")]]}
    assert abs(ov["w"] / 2 + 30.0 - 338.0) < 1e-6 and abs(ov["h"] / 2 - 16.0 - 265.0) < 1e-6
    data = json.dumps({"scenes": [ov, br, il, ov2, b2]})
    tpl = open(os.path.join(d.HERE, "conceptB_3d_template.html")).read()
    tpl = tpl.replace("/*DATA*/null", data)
    for k, v in {"pad": f"({IL_PAD[0]:.1f}, {IL_PAD[1]:.1f})", "via": f"({IL_VIA[0]:.1f}, {IL_VIA[1]:.1f})",
                 "clear": f"{R['conceptB']['inner-left corner']['pad_edge_to_bare_mesh_mm']}",
                 "routelen": f"{ROUTE_LEN:.0f}", "b2len": f"{B2_ROUTE_LEN:.0f}"}.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    out = os.path.join(OUT, "conceptB_3d.html")
    open(out, "w").write(tpl)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB | route {ROUTE_LEN:.0f} mm")
    # B2-only page for the PCB designers: same viewer, two views, its own text
    full = open(os.path.join(d.HERE, "conceptB_3d_template.html")).read()
    head = full[:full.index('<div class="wrap">')].replace("<title>P2 HV Contacts 3D</title>", "<title>P2 B2 Drift Contact</title>")
    script = full[full.index('<script src="https://cdn.jsdelivr.net/npm/three'):]
    body = open(os.path.join(d.HERE, "b2_cern_body.html")).read().replace("{{b2len}}", f"{B2_ROUTE_LEN:.0f}")
    ov2_full = dict(ov); ov2_full.update({k: v for k, v in ov2.items() if k != "ref"})
    page = head + body + "\n" + script.replace("/*DATA*/null", json.dumps({"scenes": [ov2_full, b2]}))
    out2 = os.path.join(d.ROOT, "P2_Revision_2026", "pcb", "drift_pad_B2", "B2_drift_contact.html")
    open(out2, "w").write(page)
    print("wrote", out2, f"{os.path.getsize(out2) / 1e6:.1f} MB")
    # stand-alone copy for a plain web page: full document, three.js inlined (no CDN needed)
    v = os.path.join(d.HERE, "vendor")
    libs = "".join(f"<script>\n{open(os.path.join(v, f)).read()}\n</script>\n"
                   for f in ("three-0.147.0.min.js", "OrbitControls-0.147.0.js"))
    script_sa = re.sub(r'<script src="https://cdn\.jsdelivr\.net/npm/three@0\.147\.0/[^"]+"></script>\n?', "",
                       script.replace("/*DATA*/null", json.dumps({"scenes": [ov2_full, b2]})))
    sa = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
          '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
          + head + '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
          + body + "\n" + libs + script_sa + "\n</body>\n</html>\n")
    out3 = os.path.join(d.ROOT, "P2_Revision_2026", "pcb", "drift_pad_B2", "B2_drift_contact_standalone.html")
    open(out3, "w").write(sa)
    print("wrote", out3, f"{os.path.getsize(out3) / 1e6:.1f} MB")
    os.makedirs(os.path.join(OUT, "cad"), exist_ok=True)
    if "--step" in sys.argv:
        parts_step(os.path.join(OUT, "cad", "conceptB_inner_left_parts.step"))
        parts_step(os.path.join(OUT, "cad", "conceptB2_corner_pad_parts.step"), B2_PAD, B2_VIA, B2_ROUTE, B2_SQ)


if __name__ == "__main__":
    main()
