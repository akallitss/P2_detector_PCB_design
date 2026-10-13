#!/usr/bin/env python3
"""
Rasterise a Gerber the way a viewer does, as a last check before sending a mask
out.

Unlike `gerber_io`, this does not read the file line by line: it tokenises the
character stream the way the spec says - `%` opens and closes a parameter
block, `*` ends a data block - so a file that is fine line-by-line but broken
as a stream (a stray `%` inside a comment swallowing the rest of the file, say)
renders wrong here, exactly as it does in GerbView or gerbv.

    python3 render_gerber.py ../Insulation_masks/V3C/P2_BASKET-Mask_M2_V3C.gbr
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def tokenise(text):
    """Yield ('param', body) and ('data', body) in stream order."""
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "%":
            j = text.find("%", i + 1)
            if j < 0:
                yield ("unterminated", text[i + 1:])
                return
            for part in text[i + 1:j].split("*"):
                if part.strip():
                    yield ("param", part.strip())
            i = j + 1
        else:
            j = text.find("*", i)
            if j < 0:
                yield ("unterminated", text[i:])
                return
            body = text[i:j].strip()
            if body:
                yield ("data", body)
            i = j + 1


COORD = re.compile(r"^(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?"
                   r"(?:D0?([123]))?$")


def interpret(path):
    text = open(path).read()
    scale = 1e6
    unit = 1.0            # multiplier to millimetres (%MOIN% -> 25.4)
    ap = {}
    cur = None
    x = y = 0.0
    mode = "lin"
    region = False
    pol = "D"
    ops_by_pol = {"D": 0, "C": 0}
    paint = []            # ('flash'|'stroke'|'region', payload, polarity) in file order
    poly = []
    unterminated = None
    ops = 0

    for kind, body in tokenise(text):
        if kind == "unterminated":
            unterminated = body[:60]
            break
        if kind == "param":
            m = re.match(r"^FSLAX(\d)(\d)Y\d\d$", body)
            if m:
                scale = 10 ** int(m.group(2))
                continue
            if body == "MOIN":
                unit = 25.4          # an inch file: every coordinate and every
                continue             # aperture size is in inches
            if body == "MOMM":
                unit = 1.0
                continue
            m = re.match(r"^ADD(\d+)C,([\d.]+)", body)
            if m:
                ap["D" + m.group(1)] = float(m.group(2)) * unit
                continue
            m = re.match(r"^ADD(\d+)R,([\d.]+)X([\d.]+)", body)
            if m:   # a rectangle; approximated by its smaller side for strokes
                ap["D" + m.group(1)] = min(float(m.group(2)),
                                           float(m.group(3))) * unit
                continue
            if body in ("LPD", "LPC"):
                pol = body[2]
            continue
        if body.startswith("G04"):
            continue
        if body in ("G36", "G37"):
            if body == "G37" and len(poly) > 2:
                paint.append(("region", poly, pol))
            region = body == "G36"
            poly = []
            continue
        if body.startswith("G75"):
            mode = "arc"
            continue
        if body in ("G01", "G1"):
            mode = "lin"
            continue
        if body in ("G02", "G2"):
            mode = "cw"
            continue
        if body in ("G03", "G3"):
            mode = "ccw"
            continue
        m = re.match(r"^D(\d+)$", body)
        if m and int(m.group(1)) >= 10:
            cur = body
            continue
        m = COORD.match(body)
        if not m or m.group(5) is None:
            continue
        ops += 1
        nx = int(m.group(1)) / scale * unit if m.group(1) else x
        ny = int(m.group(2)) / scale * unit if m.group(2) else y
        op = m.group(5)
        ops_by_pol[pol] += 1
        if op == "3":
            paint.append(("flash", (nx, ny, ap.get(cur, 0.1)), pol))
        elif op == "1":
            if m.group(3) is not None and mode in ("cw", "ccw"):
                i0 = int(m.group(3)) / scale * unit
                j0 = int(m.group(4)) / scale * unit
                cx, cy = x + i0, y + j0
                r = math.hypot(i0, j0)
                a0 = math.atan2(y - cy, x - cx)
                a1 = math.atan2(ny - cy, nx - cx)
                if mode == "cw":
                    while a1 > a0:
                        a1 -= 2 * math.pi
                else:
                    while a1 < a0:
                        a1 += 2 * math.pi
                k = max(2, int(abs(a1 - a0) / 0.05))
                pts = [(cx + r * math.cos(a0 + (a1 - a0) * t / k),
                        cy + r * math.sin(a0 + (a1 - a0) * t / k)) for t in range(k + 1)]
            else:
                pts = [(x, y), (nx, ny)]
            if region:
                poly += pts if not poly else pts[1:]
            else:
                paint.append(("stroke", (pts, ap.get(cur, 0.1)), pol))
        elif op == "2" and region:
            if len(poly) > 2:
                paint.append(("region", poly, pol))
            poly = [(nx, ny)]
        x, y = nx, ny
    if region and len(poly) > 2:
        paint.append(("region", poly, pol))
    return dict(paint=paint, apertures=ap, unterminated=unterminated, ops=ops,
                ops_by_pol=ops_by_pol,
                flashes=[p for k, p, _ in paint if k == "flash"],
                strokes=[p for k, p, _ in paint if k == "stroke"],
                regions=[p for k, p, _ in paint if k == "region"])


def cross_check(path, n_flashes, n_discs):
    """If gerbonara is installed, confirm it agrees on the painted geometry."""
    try:
        from gerbonara import GerberFile
        from gerbonara.graphic_objects import Arc, Flash
    except ImportError:
        return "gerbonara not installed - cross-check skipped"
    g = GerberFile.open(path)
    flashes, discs = [], set()
    for o in g.objects:
        if isinstance(o, Flash):
            flashes.append((float(o.x), float(o.y)))
        elif isinstance(o, Arc):
            r = math.hypot(float(o.cx), float(o.cy))
            w = float(o.aperture.diameter)
            if abs(w - 2 * r) < 1e-6:        # the filled-disc signature
                discs.add((round(float(o.x1) + float(o.cx), 6),
                           round(float(o.y1) + float(o.cy), 6)))
    ok = len(flashes) == n_flashes and len(discs) == n_discs
    return (f"gerbonara agrees: {len(flashes)} flashes, {len(discs)} stroked discs"
            if ok else
            f"gerbonara DISAGREES: it sees {len(flashes)} flashes and "
            f"{len(discs)} stroked discs, this reader saw {n_flashes} and {n_discs}")


def rasterise(paint, lo, hi, px):
    """Paint the objects in file order at `px` mm per pixel, honouring polarity.

    Dark adds to the image, clear erases from it - which is the only way to see
    that a pillar knocked out of a dark region is actually visible.  Returns a
    boolean array, True where the mask is dark.
    """
    from PIL import Image, ImageDraw
    w = max(1, int((hi[0] - lo[0]) / px))
    h = max(1, int((hi[1] - lo[1]) / px))
    img = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(img)

    def X(v):
        return (v - lo[0]) / px

    def Y(v):
        return h - (v - lo[1]) / px

    for kind, payload, pol in paint:
        col = 1 if pol == "D" else 0
        if kind == "flash":
            cx, cy, dia = payload
            r = dia / 2 / px
            d.ellipse([X(cx) - r, Y(cy) - r, X(cx) + r, Y(cy) + r], fill=col)
        elif kind == "region":
            d.polygon([(X(a), Y(b)) for a, b in payload], fill=col)
        else:
            pts, width = payload
            lw = max(1, int(round(width / px)))
            d.line([(X(a), Y(b)) for a, b in pts], fill=col, width=lw,
                   joint="curve")
            r = width / 2 / px      # round caps
            for a, b in (pts[0], pts[-1]):
                d.ellipse([X(a) - r, Y(b) - r, X(a) + r, Y(b) + r], fill=col)
    import numpy as np
    return np.array(img, dtype=bool)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("gerber")
    a.add_argument("--out", default=None, help="output basename (no extension)")
    a.add_argument("--dpi", type=int, default=300)
    a.add_argument("--zoom", nargs=2, type=float, metavar=("X", "Y"),
                   default=[330.0, 200.0], help="centre of the detail inset [mm]")
    a.add_argument("--zoom-size", type=float, default=30.0)
    a.add_argument("--px", type=float, default=0.08,
                   help="raster resolution of the detail inset [mm/pixel]")
    args = a.parse_args()

    r = interpret(args.gerber)
    name = os.path.basename(args.gerber).replace(".gbr", "")

    # a stroked disc (pen == 2 x arc radius) is the CEA way of painting a pillar
    discs, strokes = [], []
    for pts, width in r["strokes"]:
        p = np.asarray(pts)
        if len(p) > 2:
            c = (p[0] + p[-1]) / 2
            rad = np.hypot(*(p[0] - c))
            if abs(width - 2 * rad) < 1e-6:
                discs.append((c[0], c[1], 2 * (rad + width / 2)))
                continue
        strokes.append((pts, width))
    uniq = {(round(x, 6), round(y, 6)): d for x, y, d in discs}
    pill = list(r["flashes"]) + [(x, y, d) for (x, y), d in uniq.items()]

    print(f"{name}: stream-tokenised -> {len(r['flashes'])} flashes, "
          f"{len(uniq)} stroked discs, {len(strokes)} other stroked segments, "
          f"{len(r['regions'])} filled regions, {len(r['apertures'])} apertures")
    by_d = {}
    for _, _, d in pill:
        by_d[round(d, 4)] = by_d.get(round(d, 4), 0) + 1
    for d in sorted(by_d):
        print(f"   dia {d:.3f} mm : {by_d[d]:6d}")
    print(f"   drawing operations: {r['ops_by_pol']['D']} dark, "
          f"{r['ops_by_pol']['C']} clear")
    if r["unterminated"]:
        print(f"   ERROR: the stream ends inside an unterminated block near "
              f"{r['unterminated']!r}; a viewer discards everything from there on")
    print("   " + cross_check(args.gerber, len(r["flashes"]), len(uniq)))

    allp = np.array([(px_, py) for px_, py, _ in pill] +
                    [q for pts, _ in strokes for q in pts] +
                    [q for reg in r["regions"] for q in reg])
    lo, hi = allp.min(0) - 8, allp.max(0) + 8

    base = args.out or os.path.join(os.path.dirname(os.path.abspath(args.gerber)),
                                    "QC", f"{name}_rendered")
    os.makedirs(os.path.dirname(base), exist_ok=True)

    fig = plt.figure(figsize=(15, 10.5))
    ax = fig.add_axes([0.05, 0.06, 0.60, 0.88])
    axz = fig.add_axes([0.69, 0.30, 0.29, 0.40])

    # full view: coarse raster, enough to see the zone densities
    full = rasterise(r["paint"], lo, hi, max(0.12, (hi[0] - lo[0]) / 2600))
    ax.imshow(full, extent=[lo[0], hi[0], lo[1], hi[1]], origin="upper",
              cmap="binary", interpolation="nearest")
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(f"{name}\n{len(pill)} pillars, rendered with polarity "
                 f"(black = dark / opaque)", fontsize=11, loc="left")

    zx, zy = args.zoom
    hh = args.zoom_size / 2
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((zx - hh, zy - hh), 2 * hh, 2 * hh, fill=False,
                           edgecolor="#b3261e", lw=1.2, zorder=10))
    zlo = np.array([zx - hh, zy - hh])
    zhi = np.array([zx + hh, zy + hh])
    zoom = rasterise(r["paint"], zlo, zhi, args.px)
    axz.imshow(zoom, extent=[zlo[0], zhi[0], zlo[1], zhi[1]], origin="upper",
               cmap="binary", interpolation="nearest")
    axz.set_aspect("equal")
    axz.set_title(f"detail at ({zx:.0f}, {zy:.0f}) mm, {2*hh:.0f} mm across",
                  fontsize=10, color="#b3261e")
    for sp in axz.spines.values():
        sp.set_color("#b3261e")

    dark_frac = full.mean()
    print(f"   rendered image is {100*dark_frac:.1f} pct dark")

    fig.savefig(base + ".png", dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {base}.png")
    return 1 if r["unterminated"] else 0


if __name__ == "__main__":
    sys.exit(main())
