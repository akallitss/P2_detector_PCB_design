#!/usr/bin/env python3
"""
QC of the 2026 masks against their input (V3B_final_B2): rasterise both over the whole board
(polarity-aware), list every connected area that changed, and check that each one belongs to an
intended change. Also checks that the files parse and writes a NOW / NEW detail figure.

Writes ../Insulation_masks/V3B_final_2026/QC_masks_2026.txt and ../figures/masks_2026.png
Run with (ulimit -v 3000000; python3 qc_masks_2026.py)
"""
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

import make_masks_2026 as mm
from shapely.geometry import box

qc, rg, fp = mm.qc, mm.rg, mm.fp
WIN = (30.0, 655.0, -15.0, 545.0)
PX = 0.1


def expected_boxes():
    D, H = rg.read_drill()
    marks, _ = fp.marks_new()
    out = []
    for k in (3, 6):                         # kept holes are not listed: their openings must not change
        for x, y in H[k]:
            if not fp.in_new_pattern(x, y):
                out.append(("old screw opening", (x - 3, y - 3, x + 3, y + 3)))
    for _, x, y, _ in rg.new_frame_holes()[0]:
        if not fp.is_kept_hole(x, y):
            out.append(("new screw opening", (x - 2.2, y - 2.2, x + 2.2, y + 2.2)))
    for i, c in fp.MARKS_NOW.items():
        out.append((f"old cross {i}", (c[0] - 7.5, c[1] - 7.5, c[0] + 7.5, c[1] + 7.5)))
    for i, c in marks.items():
        s = fp.SQUARE_NEW / 2 + 0.3
        out.append((f"new cross {i}", (c[0] - s, c[1] - s, c[0] + s, c[1] + s)))
    out.append(("corner-A mesh window", mm.MESH_WIN_A))
    out.append(("drift-pad window old", mm.drift_window(mm.PAD_OLD)))
    out.append(("drift-pad window new", mm.drift_window(mm.PAD_NEW)))
    pad_b = mm.corner_B()[0]
    out.append(("corner-B mesh-pad window", pad_b.union(box(299.5, 513.5, 302.8, 516.8)).bounds))   # old + new
    return out


def inside(b, e):
    return b[0] >= e[0] - 0.15 and b[1] >= e[1] - 0.15 and b[2] <= e[2] + 0.15 and b[3] <= e[3] + 0.15


def main():
    rep = []
    exp = expected_boxes()
    for layer in ("M1", "M2"):
        old = qc.raster(qc.load(os.path.join(mm.SRC, f"P2_BASKET-Mask_{layer}_V3B_final_B2.gbr")), WIN, PX)
        new = qc.raster(qc.load(os.path.join(mm.DST, f"P2_BASKET-Mask_{layer}_2026.gbr")), WIN, PX)
        diff = old ^ new
        lab, n = ndimage.label(diff)
        objs = ndimage.find_objects(lab)
        bad, used = [], {}
        for k, sl in enumerate(objs, 1):
            ys, xs = sl
            b = (WIN[0] + xs.start * PX, WIN[3] - ys.stop * PX, WIN[0] + xs.stop * PX, WIN[3] - ys.start * PX)
            hit = [name for name, e in exp if inside(b, e)]
            if not hit:          # an old and a new screw opening next to each other merge into one area
                hit = [f"{n1} + {n2}" for n1, e1 in exp for n2, e2 in exp if n1 < n2 and
                       inside(b, (min(e1[0], e2[0]), min(e1[1], e2[1]), max(e1[2], e2[2]), max(e1[3], e2[3])))
                       and (min(e1[2], e2[2]) >= max(e1[0], e2[0]) - 0.5)][:1]
            if hit:
                used[hit[0]] = used.get(hit[0], 0) + 1
            else:
                bad.append((b, int((lab[sl] == k).sum())))
        rep.append(f"[{layer}] changed areas: {n}, all inside an intended change: {not bad}")
        for name in sorted({e[0].rsplit(' ', 1)[0] if e[0][-1].isdigit() else e[0] for e in exp}):
            cnt = sum(v for kk, v in used.items() if kk.startswith(name) and "+" not in kk)
            rep.append(f"   {name:24s}: {cnt} changed area(s)")
        for kk, v in used.items():
            if "+" in kk:
                rep.append(f"   merged {kk}: {v} area(s)")
        for b, a in bad:
            rep.append(f"   UNEXPECTED change at {tuple(round(v, 1) for v in b)} ({a} px)")
        opened = int((new & ~old).sum()) * PX * PX
        closed = int((old & ~new).sum()) * PX * PX
        rep.append(f"   area opened {opened:.1f} mm2, closed {closed:.1f} mm2")
        del old, new, diff, lab
    print("\n".join(rep))
    open(os.path.join(mm.DST, "QC_masks_2026.txt"), "w").write("\n".join(rep) + "\n")
    figure()


def figure():
    marks, _ = fp.marks_new()
    wins = {"cross 1": (63, 79, 58, 84), "cross 2": (86, 109, 15, 37), "cross 3": (627, 644, 75, 93),
            "corner A": (582, 612, -12, 20), "corner B": (286, 320, 496, 522),
            "screw holes (bottom side)": (130, 165, -14, 4)}
    fig, axs = plt.subplots(4, len(wins), figsize=(3.4 * len(wins), 13))
    for j, (name, w) in enumerate(wins.items()):
        for i, (layer, tag) in enumerate((("M1", "NOW"), ("M1", "NEW"), ("M2", "NOW"), ("M2", "NEW"))):
            path = (os.path.join(mm.SRC, f"P2_BASKET-Mask_{layer}_V3B_final_B2.gbr") if tag == "NOW"
                    else os.path.join(mm.DST, f"P2_BASKET-Mask_{layer}_2026.gbr"))
            img = qc.raster(qc.load(path), w, 0.04)
            ax = axs[i, j]
            ax.imshow(img, extent=w, cmap="gray_r", interpolation="nearest")
            ax.set_title(f"{layer} {tag} – {name}", fontsize=8.5, color="#b8650a" if tag == "NEW" else "black",
                         weight="bold")
            ax.tick_params(labelsize=6)
    fig.suptitle("Insulation masks 2026 – black = open (no resist), white = resist", fontsize=13, y=.995)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(os.path.join(mm.OUT, "figures", "masks_2026.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
