#!/usr/bin/env python3
"""
QC of the B2 files: parse every patched file, render the corner before/after
(honouring Gerber polarity), and check the 1 kV clearances on the result.

Writes ../QC/qc_report.txt and ../QC/*.png.

    python3 qc_b2.py
"""
from __future__ import annotations

import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

import make_b2_files as mk

sys.path.insert(0, os.path.join(mk.ROOT, "Version_Sept26", "tools"))
import validate_gerber as vg          # noqa: E402

QC = os.path.join(mk.OUT, "QC")
WIN = (580.0, 632.0, -6.0, 24.0)       # corner window, mm
PX = 0.02
REPORT = []


def say(s):
    print(s)
    REPORT.append(s)


def load(path):
    from gerbonara import GerberFile
    from gerbonara.utils import MM
    g = GerberFile.open(path)
    prims = []
    for o in g.objects:
        try:
            prims += list(o.to_primitives(MM))
        except Exception:
            pass
    return prims


def raster(prims, win=WIN, px=PX):
    """Paint primitives in file order, dark adds and clear removes."""
    x0, x1, y0, y1 = win
    w, h = int((x1 - x0) / px), int((y1 - y0) / px)
    img = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(img)
    X = lambda x: (x - x0) / px
    Y = lambda y: (y1 - y) / px
    for p in prims:
        col = 1 if getattr(p, "polarity_dark", True) else 0
        t = type(p).__name__
        if t == "ArcPoly":
            P = list(p.outline)
            if len(P) < 3:
                continue
            P = np.array(P)
            if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
                continue
            d.polygon([(X(a), Y(b)) for a, b in P], fill=col)
        elif t in ("Line", "Arc"):
            if t == "Arc":
                r = math.hypot(p.x1 - p.cx, p.y1 - p.cy)
                a0 = math.atan2(p.y1 - p.cy, p.x1 - p.cx); a1 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
                da = (a1 - a0) % (2 * math.pi)
                if p.clockwise:
                    da -= 2 * math.pi
                if abs(da) < 1e-9:
                    da = -2 * math.pi if p.clockwise else 2 * math.pi
                pts = [(p.cx + r * math.cos(a0 + da * k / 48), p.cy + r * math.sin(a0 + da * k / 48)) for k in range(49)]
            else:
                pts = [(p.x1, p.y1), (p.x2, p.y2)]
            P = np.array(pts)
            if P[:, 0].max() < x0 - 5 or P[:, 0].min() > x1 + 5 or P[:, 1].max() < y0 - 5 or P[:, 1].min() > y1 + 5:
                continue
            lw = max(1, int(round(p.width / px)))
            d.line([(X(a), Y(b)) for a, b in pts], fill=col, width=lw)
            r = p.width / 2 / px
            for a, b in (pts[0], pts[-1]):
                d.ellipse([X(a) - r, Y(b) - r, X(a) + r, Y(b) + r], fill=col)
        elif t == "Circle":
            if x0 - 5 < p.x < x1 + 5 and y0 - 5 < p.y < y1 + 5:
                r = p.r / px
                d.ellipse([X(p.x) - r, Y(p.y) - r, X(p.x) + r, Y(p.y) + r], fill=col)
        elif t == "Rectangle":
            if x0 - 5 < p.x < x1 + 5 and y0 - 5 < p.y < y1 + 5:
                c, s = math.cos(p.rotation), math.sin(p.rotation)
                pts = [(p.x + c * u - s * v, p.y + s * u + c * v)
                       for u, v in ((-p.w / 2, -p.h / 2), (p.w / 2, -p.h / 2), (p.w / 2, p.h / 2), (-p.w / 2, p.h / 2))]
                d.polygon([(X(a), Y(b)) for a, b in pts], fill=col)
    return np.array(img, dtype=bool)


def grid(win=WIN, px=PX):
    x0, x1, y0, y1 = win
    w, h = int((x1 - x0) / px), int((y1 - y0) / px)
    xs = x0 + (np.arange(w) + 0.5) * px
    ys = y1 - (np.arange(h) + 0.5) * px
    return np.meshgrid(xs, ys)


GX, GY = grid()


def dseg(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((GX - a[0]) * ab[0] + (GY - a[1]) * ab[1]) / (ab @ ab), 0, 1)
    return np.hypot(GX - a[0] - t * ab[0], GY - a[1] - t * ab[1])


def dpoly(pts):
    return np.min([dseg(a, b) for a, b in zip(pts[:-1], pts[1:])], axis=0)


def min_gap(copper, drift):
    """Smallest distance from drift copper to any other copper (mm), edge to edge."""
    other = copper & ~ndimage.binary_dilation(drift, iterations=2)
    if not other.any():
        return float("inf"), None
    dt, ind = ndimage.distance_transform_edt(~drift, return_indices=True)
    k = np.argmin(np.where(other, dt, np.inf))
    iy, ix = np.unravel_index(k, other.shape)
    return dt[iy, ix] * PX, (GX[iy, ix], GY[iy, ix])


def show(ax, img, title, cmap):
    x0, x1, y0, y1 = WIN
    ax.imshow(img, extent=(x0, x1, y0, y1), cmap=cmap, interpolation="nearest")
    ax.set_title(title, fontsize=10)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)


def main():
    os.makedirs(QC, exist_ok=True)
    G0 = os.path.join(mk.FAB, "Gerber")
    G1 = os.path.join(mk.FAB_OUT, "Gerber")

    # ---- 1. every patched file parses; masks pass the strict checker
    files = {k: (os.path.join(G0, f"P2_BASKET-{k}.gbr"), os.path.join(G1, f"P2_BASKET-{k}.gbr"))
             for k in ("F_Cu", "B_Cu", "F_ENIG_Finition")}
    for L in ("M1", "M2"):
        files[L] = (os.path.join(mk.MASKS, f"P2_BASKET-Mask_{L}_V3B_final.gbr"),
                    os.path.join(mk.MASK_OUT, f"P2_BASKET-Mask_{L}_V3B_final_B2.gbr"))
    P = {}
    for k, (a, b) in files.items():
        P[k] = (load(a), load(b))
        say(f"[parse] {k}: original {len(P[k][0])} primitives, B2 {len(P[k][1])} primitives")
    for L in ("M1", "M2"):
        r = vg.check(files[L][1])
        errs = r[0] if isinstance(r, tuple) else r
        say(f"[syntax] {L}: {'OK' if not errs else 'ERRORS ' + str(errs)[:300]}")
    mc = os.path.join(mk.MASK_OUT, "P2_BASKET-MeshCut_B2.gbr")
    r = vg.check(mc)
    errs = r[0] if isinstance(r, tuple) else r
    say(f"[syntax] mesh cut: {'OK' if not errs else 'ERRORS ' + str(errs)[:300]}")

    R = {k: (raster(v[0]), raster(v[1])) for k, v in P.items()}

    # ---- 2. drift copper and clearances
    pad = (np.abs(GX - mk.PAD[0]) <= mk.PAD_H) & (np.abs(GY - mk.PAD[1]) <= mk.PAD_H)
    via = np.hypot(GX - mk.VIA[0], GY - mk.VIA[1]) <= mk.VIA_PAD / 2
    dvia = np.hypot(GX - mk.D_VIA[0], GY - mk.D_VIA[1]) <= mk.VIA_PAD / 2
    tr_top = dseg((mk.PAD[0], mk.PAD[1] - mk.PAD_H), mk.VIA) <= mk.TRACE_W / 2
    route = dpoly(mk.ROUTE) <= mk.TRACE_W / 2
    corner = GX < 600.0           # the drift pad end; the D-pad end joins the D net on purpose

    f0, f1 = R["F_Cu"]
    drift_f = (pad | via | tr_top) & corner
    g, at = min_gap(f1 & corner, drift_f)
    say(f"[F.Cu] drift pad/trace/via -> nearest other front copper: {g:.2f} mm at {np.round(at, 1)}"
        f"  {'PASS' if g >= mk.CU_CLEAR else 'FAIL'} (rule {mk.CU_CLEAR} mm)")
    say(f"[F.Cu] drift pad present: {bool((f1 & pad).sum() > 0.95 * pad.sum())}; "
        f"old Sig1 pad gone: {not (f1 & (np.abs(GX - 590.5) < 4) & (GY > mk.PAD[1] + mk.PAD_H + 0.5) & (GY < 16.5)).any()}")

    b0, b1 = R["B_Cu"]
    drift_b = route | via | dvia
    near_d = np.hypot(GX - mk.D_VIA[0], GY - mk.D_VIA[1]) < 4.0
    g, at = min_gap(b1, drift_b)
    say(f"[B.Cu] drift route/vias -> nearest other back copper: {g:.2f} mm at {np.round(at, 1)}"
        f"  {'PASS' if g >= mk.CU_CLEAR - PX else 'FAIL'} (rule {mk.CU_CLEAR} mm, raster step {PX} mm)")
    sig1 = (np.abs(GX - 594.0) < 0.1) & (np.abs(GY - 11.62) < 0.1)        # on the old Sig1 segment
    say(f"[B.Cu] old Sig1 trace gone at (594.0, 11.62): {not (b1 & sig1).any()} (was there: {(b0 & sig1).any()})")
    # what the clear-polarity cut removed: must be GND hatch only
    c = mk.CU_CLEAR + mk.CUT_MARGIN
    zone = (dpoly(mk.ROUTE) <= mk.TRACE_W / 2 + c) | \
           (np.hypot(GX - mk.VIA[0], GY - mk.VIA[1]) <= mk.VIA_PAD / 2 + c) | \
           (np.hypot(GX - mk.D_VIA[0], GY - mk.D_VIA[1]) <= mk.VIA_PAD / 2 + c)
    hatch = [p for p in P["B_Cu"][0] if type(p).__name__ == "ArcPoly" and len(list(p.outline)) > 5000]
    def sig(p):          # geometric signature, to tell kept primitives from deliberately removed ones
        t = type(p).__name__
        if t == "ArcPoly":
            o = np.array(list(p.outline))
            return (t, len(o), tuple(np.round(o.mean(0), 3)))
        return (t,) + tuple(round(float(v), 4) for k, v in sorted(vars(p).items()) if isinstance(v, (int, float)))
    kept = {sig(p) for p in P["B_Cu"][1]}
    # non-hatch copper that is still in the B2 file: the cut must not have touched any of it
    nonhatch = [p for p in P["B_Cu"][0] if not (type(p).__name__ == "ArcPoly" and len(list(p.outline)) > 5000)
                and sig(p) in kept]
    removed = b0 & ~b1 & zone
    nh = raster(nonhatch) & zone
    say(f"[B.Cu] copper removed by the 3 mm cut: {removed.sum() * PX * PX:.1f} mm²; "
        f"of which not GND hatch: {(removed & nh).sum() * PX * PX:.2f} mm²  "
        f"{'PASS' if (removed & nh).sum() == 0 else 'CHECK'}")

    e0, e1 = R["F_ENIG_Finition"]
    say(f"[ENIG] drift pad gold: {bool((e1 & pad).sum() > 0.95 * pad.sum())}")

    # ---- 3. masks: dark = open (no resist), clear = resist
    isl = (GX >= mk.ISLAND[0]) & (GX <= mk.ISLAND[2]) & (GY >= mk.ISLAND[1]) & (GY <= mk.ISLAND[3])
    win = (np.abs(GX - mk.PAD[0]) <= mk.WIN_H) & (np.abs(GY - mk.PAD[1]) <= mk.WIN_H)
    for L in ("M1", "M2"):
        m0, m1 = R[L]
        inner = ndimage.binary_erosion(isl & ~win, iterations=3)
        say(f"[{L}] island is resist: {not (m1 & inner).any()}; window over the pad open: "
            f"{bool(m1[ndimage.binary_erosion(win, iterations=3)].all())}; "
            f"unchanged outside the island: {bool((m0 == m1)[~ndimage.binary_dilation(isl, iterations=3)].all())}")

        # no thin open slit between the island and the existing resist: just outside each side,
        # a dark pixel followed by resist further out would be a sliver of bare mesh
        x0, y0, x1, y1 = mk.ISLAND
        slits = 0
        for t in np.linspace(0.05, 0.95, 40):
            for (px_, py_, dx, dy) in ((x0 + t * (x1 - x0), y0, 0, -1), (x0 + t * (x1 - x0), y1, 0, 1),
                                       (x0, y0 + t * (y1 - y0), -1, 0), (x1, y0 + t * (y1 - y0), 1, 0)):
                # profile outward from the island edge: True = dark (open)
                prof = [m1[int((WIN[3] - (py_ + dy * e)) / PX), int((px_ + dx * e - WIN[0]) / PX)]
                        for e in np.arange(0.02, 1.5, 0.02)]
                # a slit: an open run under 0.3 mm wide, then at least 0.7 mm of resist (wider than a pillar)
                if prof[0]:
                    k = prof.index(False) if False in prof else len(prof)
                    if k * 0.02 < 0.3 and len(prof) - k >= 35 and not any(prof[k:k + 35]):
                        slits += 1
        say(f"[{L}] open slits between the island and the existing resist: {slits}  {'PASS' if slits == 0 else 'FAIL'}")

    # ---- 4. drill
    d0 = open(os.path.join(mk.FAB, "NCDrill", "P2_BASKET.drl")).read()
    d1 = open(os.path.join(mk.FAB_OUT, "NCDrill", "P2_BASKET.drl")).read()
    n0 = len(re.findall(r"^X", d0, re.M)); n1 = len(re.findall(r"^X", d1, re.M))
    say(f"[drill] holes: original {n0}, B2 {n1} (−1 Sig1 pad hole, +2 vias); "
        f"Sig1 hole gone: {mk.SIG1_DRILL not in d1}")
    for v in (mk.VIA, mk.D_VIA):
        r0 = np.hypot(GX - v[0], GY - v[1]) <= mk.VIA_DRILL / 2
        say(f"[drill] via {v}: copper round it on F.Cu {bool(f1[r0].all())}, on B.Cu {bool(b1[r0].all())}")

    # ---- 5. pictures
    fig, axs = plt.subplots(5, 2, figsize=(14, 22))
    for row, (k, title) in enumerate([("F_Cu", "F.Cu"), ("B_Cu", "B.Cu"), ("F_ENIG_Finition", "ENIG"),
                                      ("M1", "M1 (dark = open, white = resist)"), ("M2", "M2 (dark = open, white = resist)")]):
        a, b = R[k]
        cmap = "copper" if "Cu" in k or "ENIG" in k else "Greys"
        show(axs[row, 0], a, f"{title}: original", cmap)
        show(axs[row, 1], b, f"{title}: B2", cmap)
        for ax in axs[row]:
            ax.plot(*np.array(mk.ROUTE).T, "c-", lw=.6)
            ax.plot(*mk.PAD, "c+", ms=10)
    fig.tight_layout()
    fig.savefig(os.path.join(QC, "b2_before_after.png"), dpi=70)
    plt.close(fig)

    open(os.path.join(QC, "qc_report.txt"), "w").write("\n".join(REPORT) + "\n")


if __name__ == "__main__":
    main()
