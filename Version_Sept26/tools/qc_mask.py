#!/usr/bin/env python3
"""
Independent check + drawings for a generated P2 insulation mask.

The generated M2 is re-parsed from disk (not from the generator's memory) and
compared against the reference CEA V2 mask:

  * every stroked path that is not a pillar must be identical to V2  ->  the
    frame, the board outline and the 5 support discs are untouched,
  * the pillar flashes are re-measured and the dead area recomputed,
  * plots: full view, per-boundary zooms, mesh-support map.

    python3 qc_mask.py ../Insulation_masks/V3C/P2_BASKET-Mask_M2_V3C.gbr
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Circle

import gerber_io as gio
import make_zoned_mask as mz
import p2_geometry as pg
import render_gerber as rg


def read_pillars(path):
    """{diameter_mm: array of centres} for every painted disc in the file.

    A disc is either a D03 flash, or - the convention the CEA masks use, and
    the one a viewer still draws in outline mode - two half arcs swept with a
    pen of twice the arc radius.  Counting only flashes would silently skip
    every check on a stroke-style mask.
    """
    out = {}
    for d, c in read_flashes(path).items():
        out.setdefault(d, []).extend(map(tuple, c))
    seen = {}
    for sec in gio.read_sections(path):        # the CEA masks are 3 exports in one file
        dia = {}
        for code, defn in sec.apertures.items():
            m = re.match(r"^C,([\d.]+)", defn)
            if m:
                dia[code] = float(m.group(1))
        for code, paths in gio.section_paths(sec).items():
            w = dia.get(code)
            if w is None:
                continue
            for p in paths:
                p = np.asarray(p)
                if len(p) < 3:
                    continue
                c = (p[0] + p[-1]) / 2
                r = float(np.hypot(*(p[0] - c)))
                if abs(w - 2 * r) < 1e-6:      # the filled-disc signature
                    seen[(round(float(c[0]), 6), round(float(c[1]), 6))] = 2 * (r + w / 2)
    for (x, y), d in seen.items():
        out.setdefault(round(d, 4), []).append((x, y))
    return {k: np.array(v) for k, v in out.items() if len(v)}


def read_flashes(path):
    """{diameter_mm: array of centres} for every D03 in the file."""
    out = {}
    for sec in gio.read_sections(path):
        _flashes_of(sec, out)
    return {k: np.array(v) for k, v in out.items()}


def _flashes_of(sec, out):
    dia = {}
    for c, d in sec.apertures.items():
        m = re.match(r"^C,([\d.]+)", d)
        if m:
            dia[c] = float(m.group(1))
    cur, x, y = None, 0, 0
    for l in sec.body:
        m = re.match(r"^D(\d+)\*$", l)
        if m and int(m.group(1)) >= 10:
            cur = m.group(0)[:-1]
            continue
        m = re.match(r"^(?:X(-?\d+))?(?:Y(-?\d+))?D03\*$", l)
        if m:
            if m.group(1):
                x = int(m.group(1))
            if m.group(2):
                y = int(m.group(2))
            out.setdefault(dia.get(cur, -1.0), []).append((x / gio.SCALE, y / gio.SCALE))


def stroke_signature(path_or_sections):
    """Multiset of stroked segments, aperture-diameter-tagged, rounded to 1 um."""
    secs = (gio.read_sections(path_or_sections)
            if isinstance(path_or_sections, str) else path_or_sections)
    sig = {}
    for sec in secs:
        dia = {}
        for c, d in sec.apertures.items():
            m = re.match(r"^C,([\d.]+)", d)
            dia[c] = float(m.group(1)) if m else -1.0
        for code, paths in gio.section_paths(sec).items():
            d = dia.get(code, -1.0)
            for p in paths:
                for a, b in zip(p[:-1], p[1:]):
                    k = (round(d, 4), round(a[0], 3), round(a[1], 3),
                         round(b[0], 3), round(b[1], 3))
                    sig[k] = sig.get(k, 0) + 1
    return sig


def sample_points(allp, apex, edges, n_zones=5):
    """One representative (x, y, local pitch) inside each connector zone."""
    t = np.degrees(np.arctan2(allp[:, 1] - apex[1], allp[:, 0] - apex[0]))
    out = {}
    zedges = edges[::2]
    from scipy.spatial import cKDTree
    for z in range(len(zedges) - 1):
        sel = (t >= zedges[z]) & (t < zedges[z + 1])
        p = allp[sel]
        if len(p) < 10:
            continue
        c = p.mean(axis=0)
        i = int(np.argmin(np.hypot(*(p - c).T)))
        d, _ = cKDTree(p).query(p[i:i + 1], k=2)
        out[z + 1] = (float(p[i][0]), float(p[i][1]), float(d[0][1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mask")
    ap.add_argument("--outdir", default=None)
    a = ap.parse_args()

    out = a.outdir or os.path.join(os.path.dirname(os.path.abspath(a.mask)), "QC")
    os.makedirs(out, exist_ok=True)
    name = os.path.basename(a.mask).replace(".gbr", "")

    cfgdir = os.path.dirname(os.path.abspath(a.mask))
    cfgp = [f for f in os.listdir(cfgdir) if f.endswith(".json")]
    cfg = json.load(open(os.path.join(cfgdir, cfgp[0]))) if cfgp else {}
    pg.set_frame_source(cfg.get("frame_source", "V1"))
    print(f"checked against the CEA {pg.frame_source()} frame")

    poly = pg.active_outline()
    area = gio.polygon_area(poly)
    apex, _, th_conn = pg.connectors()
    edges, _ = pg.connector_sector_edges()
    discs = pg.support_discs()

    flashes = read_pillars(a.mask)
    n_flash = sum(len(v) for v in read_flashes(a.mask).values())
    n_tot = sum(len(v) for v in flashes.values())
    print(f"{name}: {n_tot} painted discs "
          f"({n_flash} as flashes, {n_tot - n_flash} as stroked arcs) in "
          f"{len(flashes)} sizes")
    for d in sorted(flashes):
        print(f"   dia {d:.3f} mm : {len(flashes[d]):6d}")

    # ---- 1. the frame must be untouched -----------------------------------
    # "frame only" means no pillar field, not "no flashes" - the stroke style
    # uses no flashes at all
    frame_only = not any(d < 3.0 for d in flashes)
    layer = "m1" if frame_only else "m2"
    ref = gio.read_sections(pg.M1_REF if frame_only else pg.M2_REF)
    ref_sig = stroke_signature(ref if frame_only else ref[:-1])
    new_sig = stroke_signature(a.mask)
    missing = {k: v for k, v in ref_sig.items() if new_sig.get(k, 0) < v}
    # the generator deletes exactly these boxes: the title block (re-lettered)
    # and the large mesh-contact pad.  Anything else going missing is a bug.
    boxes = mz._drop_boxes(cfg)
    intended = {k for k in missing
                if mz._inside_boxes([(k[1], k[2]), (k[3], k[4])], boxes)}
    stray = {k: v for k, v in missing.items() if k not in intended}
    print(f"\nframe check: {len(ref_sig)} reference stroke segments; "
          f"{len(intended)} removed inside the {len(boxes)} intended box(es) "
          f"(title block, large mesh pad), {len(stray)} removed elsewhere "
          f"{'-> OK' if not stray else '-> MISMATCH'}")
    missing = stray

    # the 5 support discs must still be there (drawn as stroked circles)
    ref_discs = pg.support_discs()
    got = set()
    for nsec in gio.read_sections(a.mask):
        pen = next((c for c, d in nsec.apertures.items()
                    if d.startswith("C,3.075")), None)
        if not pen:
            continue
        for pth in gio.section_paths(nsec)[pen]:
            pth = np.array(pth)
            c = (pth[0] + pth[-1]) / 2
            got.add((round(c[0], 3), round(c[1], 3)))
    hit = sum(1 for dx, dy, _ in ref_discs if (round(dx, 3), round(dy, 3)) in got)
    if frame_only:
        print("support discs: not applicable, they live on M2 only")
    else:
        print(f"support discs found in the new mask: {hit}/{len(ref_discs)}")
        if hit != len(ref_discs):
            missing = missing or {"discs": hit}
    disc_area = sum(math.pi * (d / 2) ** 2 for _, _, d in ref_discs)

    # ---- 2. dead area, re-measured ----------------------------------------
    paint = rg.interpret(a.mask)["paint"]
    growth = cfg.get("lamination_growth_mm", 0.05)
    pill = {d: c for d, c in flashes.items() if d < 3.0}
    allp = np.vstack(list(pill.values())) if pill else np.zeros((0, 2))
    ad = sum(len(c) * math.pi * (d / 2) ** 2 for d, c in pill.items())
    ae = sum(len(c) * math.pi * ((d + growth) / 2) ** 2 for d, c in pill.items())
    bigd = disc_area
    print(f"\npillars {len(allp)}, dead area {100*ad/area:.3f} % drawn / "
          f"{100*ae/area:.3f} % with +{1000*growth:.0f} um growth "
          f"(+{100*bigd/area:.2f} % from the big discs)")
    outside = (~pg.point_in_polygon(allp, poly)).sum()
    print(f"pillars outside the active outline: {outside}")

    # ---- 2b. are the pillars actually VISIBLE? -----------------------------
    if frame_only:
        print("\nframe-only mask: no pillar field to check")
    #
    # Geometry being right is not enough.  Both reference masks paint the
    # active area as one dark region and knock the pillars out of it in clear
    # polarity (%LPC%); emitting the same coordinates dark paints every pillar
    # in the colour of the region underneath it, and the mask renders blank
    # where it matters.  Rasterise a patch per zone and require contrast.
    print()
    if not frame_only:
      print()
      print("visibility (pillar interior vs the gap between pillars, rasterised "
            "with polarity):")
      bad = 0
      for zone, (zx, zy, zp) in sorted(sample_points(allp, apex, edges).items()):
        half = max(3.0, 2.5 * zp)
        img = rg.rasterise(paint, np.array([zx - half, zy - half]),
                           np.array([zx + half, zy + half]), 0.02)
        sel = ((np.abs(allp[:, 0] - zx) < half * 0.8) &
               (np.abs(allp[:, 1] - zy) < half * 0.8))
        near = allp[sel]
        if len(near) < 3:
            continue
        h, w = img.shape
        def at(px, py):
            ix = int((px - (zx - half)) / (2 * half) * w)
            iy = int(h - (py - (zy - half)) / (2 * half) * h)
            return img[min(max(iy, 0), h - 1), min(max(ix, 0), w - 1)]
        centres = np.array([at(px, py) for px, py in near])
        # midpoints between neighbouring pillars = the gap
        from scipy.spatial import cKDTree
        d, idx = cKDTree(near).query(near, k=2)
        mids = (near + near[idx[:, 1]]) / 2
        gaps = np.array([at(px, py) for px, py in mids])
        ok = (centres.mean() < 0.1) and (gaps.mean() > 0.9)
        bad += not ok
        print(f"   zone {zone}: pillar interiors {100*(1-centres.mean()):5.1f} pct clear, "
              f"gaps {100*gaps.mean():5.1f} pct dark   "
              f"{'OK' if ok else '<-- PILLARS NOT VISIBLE'}")
      if bad:
        print("   ERROR: a pillar field is painted in the same polarity as what "
              "is underneath it - a viewer will show nothing there")
        missing = missing or {"visibility": bad}

    # ---- 2b2. pillar spacing ----------------------------------------------
    #
    # Where two zones meet, two unrelated lattices plus the seam row can leave
    # pillars far closer than either zone's pitch.  The generator holds any
    # cross-zone pair at `boundary_min_spacing_mm`, so on the finished mask no
    # two pillars anywhere should be closer than the finest lattice pitch.
    if not frame_only and len(allp) > 1:
        from scipy.spatial import cKDTree
        tree = cKDTree(allp)
        d, _ = tree.query(allp, k=2)
        nn = d[:, 1]
        pitches = [z["pitch_mm"] for z in cfg.get("zones", []) if "pitch_mm" in z]
        lattice = min(pitches) if pitches else 0.0
        ms = cfg.get("boundary_min_spacing_mm", 0.0)
        # inside a zone the floor is its lattice pitch; across zones it is the
        # requested minimum spacing - so the floor for the whole mask is the
        # smaller of the two, and equals the lattice pitch only when the
        # cross-zone rule is set at least that wide
        floor = min(lattice, ms) if (lattice and ms) else lattice
        print()
        print(f"pillar spacing: closest pair anywhere {nn.min():.3f} mm; "
              f"finest lattice pitch {lattice:.3f} mm; "
              f"cross-zone minimum requested {ms:.2f} mm; "
              f"expected floor {floor:.3f} mm")
        if floor and nn.min() < floor - 0.02:
            print(f"   {int((nn < floor - 0.02).sum())} pillars sit closer than that "
                  f"-> boundary crowding not cleaned up")
            missing = missing or {"spacing": 1}
        else:
            print("   no pair closer than the expected floor -> OK")

    # ---- 2b3. walls between zones ----------------------------------------
    #
    # A resist wall along each zone boundary must (1) really be resist along
    # its dashes, (2) keep every pillar at its clearance, and (3) leave every
    # zone's open space connected to the evacuation channel.  A solid wall
    # from the inner to the outer frame would seal each zone off during
    # lamination; only the zone holding the channel could vent.
    walls = mz.zone_walls(cfg) if layer == "m2" else []
    if walls:
        from scipy.ndimage import label as _label
        wlo = poly.min(0) - 2.0
        whi = poly.max(0) + 2.0
        wpx = 0.2
        wimg = rg.rasterise(paint, wlo, whi, wpx)        # True = open (no resist)
        wh, ww = wimg.shape

        def wat(x, y):
            ix = int((x - wlo[0]) / (whi[0] - wlo[0]) * ww)
            iy = int(wh - (y - wlo[1]) / (whi[1] - wlo[1]) * wh)
            return int(wimg[min(max(iy, 0), wh - 1), min(max(ix, 0), ww - 1)])

        print()
        print(f"zone walls: {len(walls)} boundaries, {walls[0]['width']:.2f} mm wide, "
              f"{sum(len(wl['segments']) for wl in walls)} dashes")
        wall_bad = 0
        for wl in walls:
            u = wl["u"]
            on = hits = gaps = gap_open = 0
            for seg_a, seg_b in wl["segments"]:      # not a/b: `a` holds the CLI args
                L = float(np.hypot(*(seg_b - seg_a)))
                for t_ in np.arange(0.6, max(0.6, L - 0.6), 1.0):
                    q = seg_a + t_ * u
                    on += 1
                    hits += wat(*q) == 0
            wall_bad += on - hits
            for (a0, b0), (a1, b1) in zip(wl["segments"][:-1], wl["segments"][1:]):
                q = (b0 + a1) / 2
                gaps += 1
                gap_open += wat(*q) == 1
            # pillar clearance from this boundary
            need_min = np.inf
            for d_, cc in pill.items():
                along = cc @ u
                perp = np.abs(cc[:, 0] * u[1] - cc[:, 1] * u[0])
                sel = (along > 0)
                if sel.any():
                    need = wl["width"] / 2 + wl["clearance"] + d_ / 2
                    need_min = min(need_min, float((perp[sel] - need).min()))
            print(f"   {wl['between'][0]}|{wl['between'][1]} at {wl['theta']:.3f} deg: "
                  f"dashes resist at {hits}/{on} samples, "
                  f"{gap_open}/{gaps} gaps open, "
                  f"closest pillar {need_min:+.3f} mm beyond its clearance")
            wall_bad += (gaps - gap_open) + (need_min < -0.01)
        # venting: every zone's open space must reach the evacuation channel
        wlab, _ = _label(wimg)

        def wlabel(q, rad):
            vals = []
            for aa in np.linspace(0, 2 * math.pi, 36, endpoint=False):
                x_, y_ = q[0] + rad * math.cos(aa), q[1] + rad * math.sin(aa)
                ix = int((x_ - wlo[0]) / (whi[0] - wlo[0]) * ww)
                iy = int(wh - (y_ - wlo[1]) / (whi[1] - wlo[1]) * wh)
                v_ = int(wlab[min(max(iy, 0), wh - 1), min(max(ix, 0), ww - 1)])
                if v_:
                    vals.append(v_)
            return max(set(vals), key=vals.count) if vals else 0

        chs = [c for c in mz.evacuation_channels(cfg) if c["layer"] == "m2"]
        if chs:
            vent = wlabel(chs[0]["start"] - 4.0 * chs[0]["u"], 1.5)
            need_vent = cfg.get("zone_walls", {}).get("require_venting", True)
            unvented = []
            for zone, (zx, zy, zp) in sorted(sample_points(allp, apex, edges).items()):
                lz = wlabel(np.array([zx, zy]), zp / 2)
                ok_ = bool(lz) and lz == vent
                if not ok_:
                    unvented.append(zone)
                if need_vent:
                    wall_bad += not ok_
                print(f"   zone {zone}: open space connected to the evacuation channel: "
                      + ("yes" if ok_ else
                         "NO - sealed off" if need_vent else
                         "no (accepted in the config: continuous walls)"))
            if unvented and not need_vent:
                print(f"   NOTE: zones {unvented} cannot vent to the evacuation channel during "
                      f"lamination - accepted because the config sets require_venting false")
        if wall_bad:
            print("   ERROR: a wall is broken, crowds a pillar, or seals a zone")
            missing = missing or {"walls": wall_bad}

    # ---- 2c. the evacuation channel ----------------------------------------
    #
    # Three things have to hold, and "the slot is drawn" is none of them:
    #   1. the channel is continuous - every point on its centreline is dark
    #      (no resist), so there is an open path along it;
    #   2. it actually cuts *through* something - a line running parallel to it
    #      just outside its edge still shows the resist border it crosses;
    #   3. the active volume and the far end of the channel are one connected
    #      dark region.
    chans = [c for c in mz.evacuation_channels(cfg) if c["layer"] == layer]
    print()
    if not chans:
        print("evacuation: none defined for this layer")
    for c in chans:
        lo = np.minimum(c["start"], c["end"]) - 22.0
        hi = np.maximum(c["start"], c["end"]) + 22.0
        img = rg.rasterise(paint, lo, hi, 0.04)
        h, w = img.shape

        def at(q):
            ix = int((q[0] - lo[0]) / (hi[0] - lo[0]) * w)
            iy = int(h - (q[1] - lo[1]) / (hi[1] - lo[1]) * h)
            return int(img[min(max(iy, 0), h - 1), min(max(ix, 0), w - 1)])

        u = c["u"]
        n = np.array([-u[1], u[0]])
        L = float(np.hypot(*(c["end"] - c["start"])))
        ts = np.linspace(0, L, 400)
        centre = np.array([at(c["start"] + t * u) for t in ts])
        off = c["width"] / 2 + 1.5
        side = np.array([min(at(c["start"] + t * u + off * n),
                             at(c["start"] + t * u - off * n)) for t in ts])

        from scipy.ndimage import label
        lab, _ = label(img)

        def lb(q, radius=0.0):
            """The connected-region label at q.

            Sampled over a small disc and reduced to the most common non-zero
            label: a single point is unreliable here because a pillar is a
            clear hole, so a probe inside the active volume lands on one about
            a tenth of the time and reads as "not the dark region".
            """
            qs = [q] if radius <= 0 else [
                q + radius * np.array([math.cos(t), math.sin(t)])
                for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)] + [q]
            vals = []
            for p_ in qs:
                ix = int((p_[0] - lo[0]) / (hi[0] - lo[0]) * w)
                iy = int(h - (p_[1] - lo[1]) / (hi[1] - lo[1]) * h)
                v = int(lab[min(max(iy, 0), h - 1), min(max(ix, 0), w - 1)])
                if v:
                    vals.append(v)
            return max(set(vals), key=vals.count) if vals else 0

        inside = c["start"] - 6.0 * u          # back inside the active volume
        l_in, l_end = lb(inside, 2.0), lb(c["end"], 0.4)
        cont = centre.all()
        cuts = (side == 0).any()
        conn = bool(l_in) and l_in == l_end
        ok = cont and cuts and conn
        print(f"evacuation '{c['name']}' ({layer.upper()}, {c['width']:.2f} mm, "
              f"{L:.1f} mm long):")
        print(f"   centreline open along its whole length : "
              f"{'yes' if cont else 'NO - %d%% blocked' % (100*(1-centre.mean()))}")
        print(f"   crosses a resist border                : "
              f"{'yes, %.1f mm of it' % (L*(side==0).mean()) if cuts else 'NO - nothing to cut'}")
        print(f"   active volume connected to the far end : "
              f"{'yes' if conn else 'NO'}")
        if not ok:
            missing = missing or {"evacuation": True}

    # ---- 3. drawings -------------------------------------------------------
    zone_of = np.digitize(np.degrees(np.arctan2(allp[:, 1] - apex[1],
                                                allp[:, 0] - apex[0])), edges[::2][1:-1])
    cmap = plt.get_cmap("viridis", 5)

    fig, ax = plt.subplots(figsize=(13, 12))
    ax.add_collection(LineCollection(
        [np.asarray(p) for ps in gio.section_paths(gio.read_sections(a.mask)[0]).values()
         for p in ps], colors="0.25", linewidths=0.3))
    ax.scatter(allp[:, 0], allp[:, 1], s=0.6, c=zone_of, cmap=cmap, vmin=-0.5, vmax=4.5)
    for k in range(len(edges)):
        t = math.radians(edges[k])
        ax.plot([110 * math.cos(t), 600 * math.cos(t)],
                [110 * math.sin(t), 600 * math.sin(t)],
                color="crimson" if k % 2 == 0 else "0.7",
                lw=1.0 if k % 2 == 0 else 0.4, ls="--", zorder=5)
    for i, t in enumerate(th_conn):
        r = 610
        ax.text(r * math.cos(math.radians(t)), r * math.sin(math.radians(t)),
                f"C{i+1}", ha="center", va="center", fontsize=8, color="crimson")
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(f"{name} - zoned pillar field (red dashed = zone boundaries)")
    ax.autoscale_view()
    fig.savefig(os.path.join(out, f"{name}_overview.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)

    # zoom on every zone boundary, at mid radius
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.4))
    for k, ax in enumerate(axs):
        t = math.radians(edges[2 * (k + 1)])
        r = 380
        cx, cy = r * math.cos(t), r * math.sin(t)
        w = 16
        sel = (np.abs(allp[:, 0] - cx) < w) & (np.abs(allp[:, 1] - cy) < w)
        pc = []
        for d, c in pill.items():
            s = (np.abs(c[:, 0] - cx) < w) & (np.abs(c[:, 1] - cy) < w)
            pc += [Circle(p, d / 2) for p in c[s]]
            pc += [Circle(p, (d + growth) / 2) for p in c[s]]
        ax.add_collection(PatchCollection(pc, facecolor="tab:blue", alpha=0.35,
                                          edgecolor="tab:blue", lw=0.3))
        ax.plot([cx - 2 * w * math.cos(t + math.pi / 2), cx + 2 * w * math.cos(t + math.pi / 2)],
                [cy - 2 * w * math.sin(t + math.pi / 2), cy + 2 * w * math.sin(t + math.pi / 2)],
                "r--", lw=0.8)
        ax.set_xlim(cx - w, cx + w)
        ax.set_ylim(cy - w, cy + w)
        ax.set_aspect("equal")
        ax.set_title(f"zones {k+1} | {k+2}  @ r={r} mm, {edges[2*(k+1)]:.2f} deg", fontsize=10)
    fig.suptitle(f"{name} - zone boundaries, pillars drawn at nominal and "
                 f"+{1000*growth:.0f} um")
    fig.savefig(os.path.join(out, f"{name}_boundaries.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)

    # mesh-support map
    from scipy.ndimage import distance_transform_edt
    step = 0.5
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    gx = np.arange(x0, x1 + step, step)
    gy = np.arange(y0, y1 + step, step)
    X, Y = np.meshgrid(gx, gy)
    inside = pg.point_in_polygon(np.c_[X.ravel(), Y.ravel()], poly).reshape(X.shape)
    occ = np.ones(X.shape, dtype=bool)
    ix = np.clip(np.round((allp[:, 0] - gx[0]) / step).astype(int), 0, len(gx) - 1)
    iy = np.clip(np.round((allp[:, 1] - gy[0]) / step).astype(int), 0, len(gy) - 1)
    occ[iy, ix] = False
    dmap = distance_transform_edt(occ, sampling=step)
    for dx, dy, dd in discs:
        dmap = np.minimum(dmap, np.hypot(X - dx, Y - dy) - dd / 2)
    dmap = np.where(inside, dmap, np.nan)
    fig, ax = plt.subplots(figsize=(13, 11))
    im = ax.imshow(dmap, origin="lower", extent=[x0, x1, y0, y1], cmap="magma")
    fig.colorbar(im, ax=ax, label="distance to the nearest pillar edge-of-support [mm]")
    ax.set_aspect("equal")
    ax.set_title(f"{name} - mesh support map (bright = longest unsupported span)")
    fig.savefig(os.path.join(out, f"{name}_support.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)

    print(f"\nplots written to {out}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
