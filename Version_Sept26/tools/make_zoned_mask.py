#!/usr/bin/env python3
"""
Build a P2 basket bulk-insulation mask (M1 + M2) whose pillar field is split
into azimuthal zones, one zone per group of connectors, each zone with its own
pillar diameter and pitch.

The frame (everything that is not a pillar) is taken verbatim from the CEA
Apr-26 V2 masks, so M1 is unchanged and M2 differs from V2 only in the pillar
field.  The 5 large 6.15 mm support discs are kept.

    python3 make_zoned_mask.py ../config/zones_C_2factor.json

Every zone is checked against the dead-area budget before anything is written.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import re
import shutil
import sys

import numpy as np
from scipy.spatial import cKDTree

import gerber_io as gio
import p2_geometry as pg
import strokefont as sf

# The V2 masks carry an etched title block in the bottom-left corner reading
#   P2_2026 / Mask_M2_V2 / D0.800mm-P4mm / D6mm_Derive
# Its inner frame is the 0.2 mm rectangle below; everything strictly inside is
# lettering that no longer describes this mask, so it is replaced.
LABEL_BOX = (-4.48, -29.92, 51.67, -3.77)      # x0, y0, x1, y1

# The CEA M2 carries a second, much larger mesh-contact pad at the outer bottom
# corner - a 7.0 x 7.0 mm filled opening at (585.7, 7.5)..(592.7, 14.5), well
# inside the active area.  CERN's masks have only the small 2 mm pad on the
# very corner, at (596.0, 2.0)..(597.9, 3.8), which is outside the active
# outline.  The box below covers the large pad and the 0.5 mm outline stroked
# round it, with margin, and contains nothing else.
MESH_CONTACT_PAD_BOX = (584.4, 6.2, 594.0, 15.8)

# Taking that pad out leaves a hole in the story: the M2 frame region was
# stepped back around it, so the corner it occupied is not dark, and the 28
# pillars the lattice puts there are painted clear on clear - invisible.
# Re-filling the active area inside this box restores it to ordinary pillar
# surface.  Measured: the only place the M2 frame leaves the active area
# unpainted is that corner, 147.3 mm^2.
FRAME_GAP_FILL_BOXES = [(578.0, 0.0, 600.0, 22.0)]

# The mesh is contacted through small openings at the two ends of the outer
# arc.  CEA draws only the bottom one; CERN draws both, and the PCB carries a
# 3.88 x 3.90 mm copper pad at (300.98, 515.97) for the top one, so the
# opening has somewhere to land.  Sizes follow our own bottom contact.
# The top window is the bottom one mirrored through the fan axis, which is at
# exactly 30 deg (the ten connector angles average to 30.000).  Mirroring
# rather than translating matters: at the bottom corner the two edges of the
# detector run at 0 and 90 deg, at the top corner they run at 60 and 150, so
# an axis-aligned copy sits askew to the corner.  CERN does the same - their
# top contact is their bottom 1.93 x 1.81 pad with its edges at 59.96 and
# 150.00 deg.  Mirroring the source polygon also carries the rounded corners
# across, so the two windows really are the same shape.
MESH_CONTACT_MIRROR_AXIS_DEG = 30.0
# The bottom contact is the only filled region smaller than 3 mm that sits
# beyond r = 500 mm below the fan axis.  The mounting-hole openings out there
# are 3.10, 4.00 and 5.30 mm, so the size cut separates them cleanly.
MESH_CONTACT_SOURCE_MIN_R = 500.0
MESH_CONTACT_SOURCE_MAX_T = 30.0
MESH_CONTACT_SOURCE_MAX_SIZE = 3.0

# The V2 pillar layer carries two stray 0.075 mm arcs at x = 1287 mm, far off
# the panel.  Anything outside this box is dropped when the layer is copied.
PANEL = (-60.0, -60.0, 760.0, 620.0)

# --------------------------------------------------------------------------
# Evacuation channel, taken from the CERN bulk masks.
#
# Both CERN masks cut a notch through the resist border at the inner bottom
# corner of the active area - the low point of the detector - so gas and
# excess resin can escape during lamination instead of being trapped:
#
#   Mask1 (frame)   a 1.30 mm channel ending in a 3.00 mm round reservoir
#                   at (110.844, 0.875)      <- the "droplet"
#   Mask2 (pillars) a 2.00 mm channel, slightly longer, to (110.186, 0.183)
#
# Both run from (119.464, 9.949) outwards at -133.5 deg.  On the V1 frame -
# the one CERN actually worked from - that start sits 6.9 mm inside the active
# area and V1's own inner bottom corner (114.685, 4.909) lies on the very same
# ray (-133.59 deg against CERN's -133.53), so CERN's coordinates are used
# verbatim.  On V2 the active area starts further in and CERN's start would
# fall outside it, so there the channel is re-anchored to V2's corner instead;
# "auto" below picks whichever applies.
CERN_EVACUATION_START = [119.464, 9.949]
CERN_EVACUATION = {
    "m1": {"width_mm": 1.30, "end": [110.844, 0.875], "droplet_mm": 3.00},
    "m2": {"width_mm": 2.00, "end": [110.186, 0.183], "droplet_mm": 0.0},
}
# The slot starts 1 mm inside OUR active-area corner, not at CERN's start.
# CERN's start (119.464, 9.949) is their corner, but on the V1 frame it lies
# 6.9 mm inside the active area: that stretch of slot is open space on open
# space and does nothing, while its pillar keep-out cut a diagonal lane of
# seven pillars out of the grid.  Our corner sits on CERN's line (-133.59 vs
# -133.53 deg), so keeping CERN's end points keeps the same slot direction.
DEFAULT_EVACUATION = [dict(name="inner bottom corner", anchor="inner_bottom_corner",
                           anchor_inset_mm=1.0, pillar_clearance_mm=0.5,
                           **CERN_EVACUATION)]

HERE = os.path.dirname(os.path.abspath(__file__))
OUTROOT = os.path.normpath(os.path.join(HERE, ".."))


# --------------------------------------------------------------------------
# lattices
# --------------------------------------------------------------------------
def lattice(kind: str, pitch: float, bbox, rot_deg: float, centre):
    """Points of an infinite lattice clipped to `bbox`, rotated by `rot_deg`
    about `centre`.

    `pitch` is the nearest-neighbour distance for 'hex' and the row/column
    spacing for 'square'.
    """
    (x0, y0), (x1, y1) = bbox
    cx, cy = centre
    # radius of the bbox seen from the rotation centre, so the rotated lattice
    # certainly covers it
    R = max(math.hypot(x - cx, y - cy) for x in (x0, x1) for y in (y0, y1)) + 2 * pitch
    if kind == "hex":
        dx, dy = pitch, pitch * math.sqrt(3) / 2
    elif kind == "square":
        dx = dy = pitch
    else:
        raise ValueError(f"unknown lattice {kind!r}")
    nx = int(R / dx) + 2
    ny = int(R / dy) + 2
    i = np.arange(-nx, nx + 1)
    j = np.arange(-ny, ny + 1)
    I, J = np.meshgrid(i, j)
    X = I * dx + (J % 2) * (dx / 2 if kind == "hex" else 0.0)
    Y = J * dy
    p = np.c_[X.ravel(), Y.ravel()]
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = np.c_[cx + ca * p[:, 0] - sa * p[:, 1], cy + sa * p[:, 0] + ca * p[:, 1]]
    m = (out[:, 0] >= x0 - pitch) & (out[:, 0] <= x1 + pitch) & \
        (out[:, 1] >= y0 - pitch) & (out[:, 1] <= y1 + pitch)
    return out[m]


def cell_area(kind: str, pitch: float) -> float:
    return pitch * pitch * (math.sqrt(3) / 2 if kind == "hex" else 1.0)


# --------------------------------------------------------------------------
# area bookkeeping
# --------------------------------------------------------------------------
def raster(poly, step=0.25):
    """Boolean raster of the active polygon + the grid coordinates."""
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    gx = np.arange(x0, x1 + step, step)
    gy = np.arange(y0, y1 + step, step)
    X, Y = np.meshgrid(gx, gy)
    P = np.c_[X.ravel(), Y.ravel()]
    inside = pg.point_in_polygon(P, poly).reshape(Y.shape)
    return gx, gy, inside, step


def support_distance_map(centres, shape, gx, gy, step):
    """Distance from every raster cell to the nearest pillar centre (mm).

    Computed from *all* pillars at once: close to a zone boundary the mesh is
    held by the neighbouring zone's pillars too, so a per-zone map would be
    pessimistic.
    """
    from scipy.ndimage import distance_transform_edt
    occ = np.ones(shape, dtype=bool)
    ix = np.clip(np.round((centres[:, 0] - gx[0]) / step).astype(int), 0, len(gx) - 1)
    iy = np.clip(np.round((centres[:, 1] - gy[0]) / step).astype(int), 0, len(gy) - 1)
    occ[iy, ix] = False
    return distance_transform_edt(occ, sampling=step)


# --------------------------------------------------------------------------
def build(cfg):
    pg.set_frame_source(cfg.get("frame_source", "V1"))
    poly = pg.active_outline()
    area_total = gio.polygon_area(poly)
    edges, step_deg = pg.connector_sector_edges()
    apex, _, th_conn = pg.connectors()
    discs = pg.support_discs()

    growth = cfg.get("lamination_growth_mm", 0.05)
    budget = cfg.get("dead_area_budget", 0.03)
    frame_clear = cfg.get("frame_clearance_mm", 0.0)
    disc_clear = cfg.get("disc_clearance_mm", 1.0)
    edge_clear = cfg.get("zone_boundary_clearance_mm", 0.5)

    gx, gy, inside, rstep = raster(poly, cfg.get("raster_step_mm", 0.25))
    chans = evacuation_channels(cfg)
    walls = zone_walls(cfg)

    # the mesh area is ~1 deg wider than the connector fan on each side; the
    # outermost zones are stretched over it so no strip is left unsupported
    tpoly = np.degrees(np.arctan2(poly[:, 1] - apex[1], poly[:, 0] - apex[0]))
    t_lo, t_hi = tpoly.min() - 1.0, tpoly.max() + 1.0
    stretch = cfg.get("extend_outer_zones_to_frame", True)

    zones = []
    for k, z in enumerate(cfg["zones"]):
        c0, c1 = z["connectors"]           # 1-based, inclusive
        t0, t1 = float(edges[c0 - 1]), float(edges[c1])
        if stretch and k == 0:
            t0 = min(t0, t_lo)
        if stretch and k == len(cfg["zones"]) - 1:
            t1 = max(t1, t_hi)
        # a zone can pin its lattice to absolute coordinates - zone 1 of the
        # release mask sits on CERN's grid, whose pillars are at even mm
        origin = np.asarray(z.get("lattice_origin", apex), dtype=float)
        pts = lattice(z["lattice"], z["pitch_mm"], (poly.min(0), poly.max(0)),
                      _rotation(z, th_conn, c0, c1), origin)
        t = np.degrees(np.arctan2(pts[:, 1] - apex[1], pts[:, 0] - apex[0]))
        keep = (t >= t0) & (t < t1)
        pts = pts[keep]
        pts = pts[pg.point_in_polygon(pts, poly)]
        if frame_clear > 0:
            pts = pts[pg.distance_to_polygon(pts, poly) >= frame_clear + z["diameter_mm"] / 2]
        # keep clear of the big support discs
        for dx, dy, dd in discs:
            r = dd / 2 + disc_clear + z["diameter_mm"] / 2
            pts = pts[np.hypot(pts[:, 0] - dx, pts[:, 1] - dy) > r]
        # and off the evacuation channels, which would otherwise bite into them
        for c in chans:
            if c["layer"] != "m2":
                continue
            keep = c["width"] / 2 + c["clearance"] + z["diameter_mm"] / 2
            pts = pts[_channel_distance(pts, c) > keep]
        # and back from the zone walls
        for wl in walls:
            need = wl["width"] / 2 + wl["clearance"] + z["diameter_mm"] / 2
            pts = pts[_wall_distance(pts, wl, apex) >= need]
        zones.append(dict(z, t0=t0, t1=t1, pts=pts))

    # ---- seam rows on the internal zone boundaries
    #      Two unrelated lattices meeting at a boundary leave a poorly
    #      supported strip (up to ~one pitch wide).  A row of pillars sitting
    #      exactly on the boundary ray removes it, costs almost no area, and
    #      makes the zone edge visible on the finished detector.
    seams = []
    if cfg.get("seam_rows", True) and not walls:      # a wall replaces the seam
        for za, zb in zip(zones[:-1], zones[1:]):
            sm = _seam(za, zb, poly, discs, apex, disc_clear)
            for c in chans:
                if c["layer"] == "m2" and len(sm["pts"]):
                    keep = c["width"] / 2 + c["clearance"] + sm["diameter_mm"] / 2
                    sm["pts"] = sm["pts"][_channel_distance(sm["pts"], c) > keep]
            seams.append(sm)

    # ---- no two pillars may come closer than edge_clear edge-to-edge.
    #      Losers are taken from the denser zone; seam pillars are never cut.
    thin = _deconflict(zones, seams, edge_clear,
                       cfg.get("boundary_min_spacing_mm", 3.0))

    # ---- areas and report
    t = np.degrees(np.arctan2(
        np.repeat(gy, len(gx)).reshape(len(gy), len(gx)).T.ravel() * 0, 1))  # placeholder
    X, Y = np.meshgrid(gx, gy)
    tgrid = np.degrees(np.arctan2(Y - apex[1], X - apex[0]))
    cell = rstep * rstep

    # the mesh is also held by the frame, so the band next to it is excluded
    # from the "largest unsupported span" figure of merit
    from scipy.ndimage import distance_transform_edt
    frame_dist = distance_transform_edt(inside, sampling=rstep)
    dmap = support_distance_map(
        np.vstack([z["pts"] for z in zones] + [sm["pts"] for sm in seams if len(sm["pts"])]),
        inside.shape, gx, gy, rstep)
    # the big discs hold the mesh too
    for dx, dy, dd in discs:
        dmap = np.minimum(dmap, np.hypot(X - dx, Y - dy) - dd / 2)

    # seam pillars straddle a boundary: half of each one belongs to either side
    seam_of = {}
    for k, sm in enumerate(seams):
        seam_of.setdefault(zones[k]["zone"], []).append(sm)
        seam_of.setdefault(zones[k + 1]["zone"], []).append(sm)

    report = []
    for z in zones:
        m = inside & (tgrid >= z["t0"]) & (tgrid < z["t1"])
        a = m.sum() * cell
        d0 = z["diameter_mm"]
        n = len(z["pts"])
        area0 = n * math.pi * (d0 / 2) ** 2
        area1 = n * math.pi * ((d0 + growth) / 2) ** 2
        n_seam = 0.0
        for sm in seam_of.get(z["zone"], []):
            n_seam += len(sm["pts"]) / 2
            area0 += len(sm["pts"]) / 2 * math.pi * (sm["diameter_mm"] / 2) ** 2
            area1 += len(sm["pts"]) / 2 * math.pi * ((sm["diameter_mm"] + growth) / 2) ** 2
        cov0 = area0 / a
        cov1 = area1 / a
        # a wall sits on the boundary: half of its area belongs to either side.
        # It is reported apart from the pillars - the pillar figure is the
        # experimental variable the zone is solved for.
        wall0 = wall1 = 0.0
        for wl in walls:
            if z["zone"] in wl["between"]:
                wall0 += wl["length"] * wl["width"] / 2
                wall1 += wl["length"] * (wl["width"] + growth) / 2
        # the evacuation channel is a deliberate pillar-free slot and the mesh
        # over it is carried by the border, so it is not an unsupported span
        core = m & (frame_dist > z["pitch_mm"])
        for c in chans:
            if c["layer"] == "m2":
                dch = _channel_distance(np.c_[X.ravel(), Y.ravel()], c).reshape(X.shape)
                core &= dch > c["width"] / 2 + c["clearance"] + z["pitch_mm"]
        # likewise the walls: the mesh is carried along them
        for wl in walls:
            dw = _wall_distance(np.c_[X.ravel(), Y.ravel()], wl, apex).reshape(X.shape)
            core &= dw > wl["width"] / 2 + wl["clearance"] + z["pitch_mm"]
        lec = float(dmap[core].max()) if core.any() else float("nan")
        if core.any():
            k = int(np.argmax(np.where(core, dmap, -1)))
            z["worst_gap_at"] = (float(X.flat[k]), float(Y.flat[k]))
        nn = _min_nn(z["pts"])
        report.append(dict(zone=z["zone"], connectors=z["connectors"],
                           theta=(z["t0"], z["t1"]), area_mm2=a, n=n,
                           n_seam=n_seam,
                           d_draw=d0, d_eff=d0 + growth, lattice=z["lattice"],
                           pitch=z["pitch_mm"], cov_draw=cov0, cov_eff=cov1,
                           nn_min=nn, max_unsupported_radius=lec,
                           n_dropped=z.get("n_dropped", 0),
                           budget=z.get("dead_area_budget", budget),
                           wall_mm2=wall1, cov_wall_draw=wall0 / a, cov_wall_eff=wall1 / a,
                           cov_total_eff=cov1 + wall1 / a,
                           reference=z.get("reference", ""),
                           worst_gap_at=z.get("worst_gap_at"),
                           pillars_per_cm2=n / (a / 100)))
    return dict(poly=poly, area_total=area_total, zones=zones, seams=seams,
                channels=chans, walls=walls, report=report, thin=thin,
                min_spacing=cfg.get("boundary_min_spacing_mm", 3.0),
                discs=discs, growth=growth, budget=budget,
                raster=(gx, gy, inside, rstep), apex=apex)


def zone_walls(cfg):
    """Resist walls along the internal zone boundaries, as dash segments.

    Each wall runs along the ray between two neighbouring zones, clipped to
    the active outline.  With `dash_mm` and `gap_mm` set it is broken into
    dashes: a wall running unbroken from the inner to the outer frame would
    seal every zone into its own compartment under the mesh, and only the zone
    that holds the evacuation channel could vent during lamination.
    """
    spec = cfg.get("zone_walls")
    if not spec:
        return []
    poly = pg.active_outline()
    edges, _ = pg.connector_sector_edges()
    apex, _, _ = pg.connectors()
    width = float(spec.get("width_mm", 1.0))
    clear = float(spec.get("pillar_clearance_mm", 0.5))
    dash = float(spec.get("dash_mm", 0.0))
    gap = float(spec.get("gap_mm", 0.0))
    # run each wall this far past the active outline into the resist frame: a
    # wall stopping exactly at the outline leaves a hairline of open area along
    # the frame, and the zones leak round its ends
    overlap = float(spec.get("frame_overlap_mm", 0.5))
    rmax = float(np.hypot(*(poly - apex).T).max()) + 5.0
    rr = np.arange(0.0, rmax, 0.02)
    out = []
    zs = cfg["zones"]
    for za, zb in zip(zs[:-1], zs[1:]):
        th = float(edges[za["connectors"][1]])
        u = np.array([math.cos(math.radians(th)), math.sin(math.radians(th))])
        ins = pg.point_in_polygon(apex + rr[:, None] * u, poly).astype(int)
        idx = np.where(np.diff(np.r_[0, ins, 0]))[0]
        segs, inside_len = [], 0.0
        for i0, i1 in zip(idx[::2], idx[1::2]):
            r0, r1 = rr[i0], rr[i1 - 1]
            e0, e1 = max(0.0, r0 - overlap), r1 + overlap
            L = e1 - e0
            if dash > 0 and gap > 0:
                # an integer number of dashes, stretched so both ends of the
                # wall are anchored in the frame and every gap is exactly `gap`
                n = max(1, int(round((L + gap) / (dash + gap))))
                dl = (L - (n - 1) * gap) / n
                spans = [(e0 + k * (dl + gap), e0 + k * (dl + gap) + dl) for k in range(n)]
            else:
                spans = [(e0, e1)]
            for p0, p1 in spans:
                segs.append((apex + p0 * u, apex + p1 * u))
                inside_len += max(0.0, min(p1, r1) - max(p0, r0))
        out.append(dict(theta=th, u=u, width=width, clearance=clear, segments=segs,
                        between=(za["zone"], zb["zone"]),
                        length=float(inside_len),      # inside the active area only
                        length_drawn=float(sum(np.hypot(*(b - a)) for a, b in segs))))
    return out


def _wall_distance(pts, wl, apex):
    """Perpendicular distance to the wall's ray (inf behind the apex)."""
    rel = np.asarray(pts) - apex
    u = wl["u"]
    perp = np.abs(rel[:, 0] * u[1] - rel[:, 1] * u[0])
    return np.where(rel @ u > 0, perp, np.inf)


def evacuation_channels(cfg):
    """The channels to cut, resolved to absolute coordinates."""
    spec = cfg.get("evacuation_channels", DEFAULT_EVACUATION)
    out = []
    poly = pg.active_outline()
    for ch in spec:
        a = ch.get("anchor", "auto")
        inset = ch.get("anchor_inset_mm", 1.0)
        if a == "auto":
            # CERN's own start if this frame's active area reaches it, else
            # this frame's inner bottom corner
            cern = np.asarray(CERN_EVACUATION_START, dtype=float)
            if pg.point_in_polygon(cern[None, :], poly)[0]:
                start, inset = cern, 0.0
            else:
                start = np.asarray(pg.inner_bottom_corner(), dtype=float)
        elif a == "inner_bottom_corner":
            start = np.asarray(pg.inner_bottom_corner(), dtype=float)
        else:
            start = np.asarray(a, dtype=float)
        for layer in ("m1", "m2"):
            if layer not in ch:
                continue
            end = np.asarray(ch[layer]["end"], dtype=float)
            u = end - start
            u = u / np.hypot(*u)
            out.append(dict(name=ch.get("name", ""), layer=layer,
                            start=start - inset * u,
                            end=end, u=u,
                            width=float(ch[layer]["width_mm"]),
                            droplet=float(ch[layer].get("droplet_mm", 0.0)),
                            clearance=float(ch.get("pillar_clearance_mm", 0.5))))
    return out


def _emit_evacuation(chans, layer, tab):
    """Gerber for the evacuation channels of one layer, in dark polarity.

    Dark removes resist, so the channel is an open slot through the border -
    the same thing CERN drew, and the reason it has to be emitted *after* the
    pillar field rather than before it.
    """
    ch = [c for c in chans if c["layer"] == layer]
    if not ch:
        return []
    out = [gio.comment("--- evacuation channel(s), after the CERN bulk masks"),
           "%LPD*%"]
    for c in ch:
        out.append(gio.comment(
            f"{c['name']}: {c['width']:.2f} mm slot "
            f"({c['start'][0]:.3f},{c['start'][1]:.3f}) -> "
            f"({c['end'][0]:.3f},{c['end'][1]:.3f})"
            + (f" ending in a {c['droplet']:.2f} mm reservoir" if c["droplet"] else "")))
        out.append(tab.circle(c["width"]) + "*")
        out.append(f"X{gio.q(c['start'][0])}Y{gio.q(c['start'][1])}D02*")
        out.append(f"X{gio.q(c['end'][0])}Y{gio.q(c['end'][1])}D01*")
        if c["droplet"] > 0:
            out.append(tab.circle(c["droplet"]) + "*")
            out.append(gio.flash(c["end"][0], c["end"][1]))
    return out


def _channel_distance(pts, c):
    """Distance from each point to the channel centreline (segment + droplet)."""
    a, b = c["start"], c["end"]
    ab = b - a
    t = np.clip(((pts - a) @ ab) / (ab @ ab), 0, 1)
    d = np.hypot(*(pts - (a + t[:, None] * ab)).T)
    if c["droplet"] > 0:
        d = np.minimum(d, np.hypot(*(pts - b).T) - (c["droplet"] - c["width"]) / 2)
    return d


def _seam(za, zb, poly, discs, apex, disc_clear):
    """A row of pillars along the ray shared by two neighbouring zones."""
    d = min(za["diameter_mm"], zb["diameter_mm"])
    step = min(za["pitch_mm"], zb["pitch_mm"])
    t = math.radians(za["t1"])
    u = np.array([math.cos(t), math.sin(t)])
    rmax = np.hypot(*(poly - apex).T).max()
    r = np.arange(0.0, rmax + step, step)
    p = apex + r[:, None] * u
    p = p[pg.point_in_polygon(p, poly)]
    for dx, dy, dd in discs:
        p = p[np.hypot(p[:, 0] - dx, p[:, 1] - dy) > dd / 2 + disc_clear + d / 2]
    return dict(theta=za["t1"], pts=p, diameter_mm=d, pitch_mm=step,
                between=(za["zone"], zb["zone"]))


def _rotation(z, th_conn, c0, c1):
    r = z.get("rotation", "wedge")
    if r == "wedge":                      # lattice aligned to the zone bisector
        return float((th_conn[c0 - 1] + th_conn[c1 - 1]) / 2)
    if r == "global":
        return 0.0
    return float(r)


def _min_nn(p):
    if len(p) < 2:
        return float("inf")
    d, _ = cKDTree(p).query(p, k=2)
    return float(d[:, 1].min())


def _deconflict(zones, seams, edge_clear, min_spacing=0.0):
    """Resolve pillar crowding where two zones meet.

    Two unrelated lattices meeting at a boundary, plus the seam row on the
    boundary itself, leave the population locally much denser than either zone
    asks for: without a rule the closest pair on the whole detector is 0.73 mm
    centre to centre, against a 2.50 mm lattice pitch.

    A pair of pillars from *different* groups must therefore be at least

        max( (d_i + d_j)/2 + edge_clear ,  min_spacing )

    apart, centre to centre.  Pairs inside one zone are never touched - there
    the spacing is the lattice and is deliberate.  When a pair is too close
    the pillar from the denser (smaller-pitch) group is the one dropped, so
    the sparser side keeps its support; seam pillars are treated as the
    densest group and yield first, which is the "check before placing a new
    pillar at the interconnection" rule.
    """
    for z in zones:
        z["n_dropped"] = 0
    for sm in seams:
        sm["zone"] = None
        sm["n_dropped"] = 0
        sm["_pitch_keep"] = sm["pitch_mm"]
        sm["pitch_mm"] = 0.0          # lowest priority: dropped first
    groups = list(zones) + list(seams)

    for _ in range(12):
        live = [g for g in groups if len(g["pts"])]
        if not live:
            break
        allp = np.vstack([g["pts"] for g in live])
        owner = np.concatenate([np.full(len(g["pts"]), i) for i, g in enumerate(live)])
        dia = np.concatenate([np.full(len(g["pts"]), g["diameter_mm"]) for g in live])
        reach = max(dia.max() + edge_clear, min_spacing)
        pairs = cKDTree(allp).query_pairs(reach, output_type="ndarray")
        if len(pairs) == 0:
            break
        i, j = pairs[:, 0], pairs[:, 1]
        cross = owner[i] != owner[j]
        i, j = i[cross], j[cross]
        if len(i) == 0:
            break
        need = np.maximum((dia[i] + dia[j]) / 2 + edge_clear, min_spacing)
        got = np.hypot(*(allp[i] - allp[j]).T)
        bad = got < need
        i, j = i[bad], j[bad]
        if len(i) == 0:
            break
        pitches = np.array([g["pitch_mm"] for g in live])
        loser = np.where(pitches[owner[i]] <= pitches[owner[j]], i, j)
        drop = set(loser.tolist())
        off = 0
        for g in live:
            n = len(g["pts"])
            local = np.array([d - off for d in drop if off <= d < off + n], dtype=int)
            if len(local):
                keep = np.ones(n, dtype=bool)
                keep[local] = False
                g["pts"] = g["pts"][keep]
                g["n_dropped"] = g.get("n_dropped", 0) + len(local)
            off += n

    for sm in seams:
        sm["pitch_mm"] = sm.pop("_pitch_keep", sm["pitch_mm"])
    return dict(seam_skipped=sum(sm["n_dropped"] for sm in seams),
                zone_skipped=sum(z["n_dropped"] for z in zones))


# --------------------------------------------------------------------------
# gerber emission
# --------------------------------------------------------------------------
def emit_m2(res, cfg, path):
    src = gio.read_sections(pg.M2_REF)
    frame_secs = src[:-1]           # ECO1 (frame) + User (board outline / text)
    pillar_sec = src[-1]            # ECO2: pillars + big discs + markers
    tab = gio.ApertureTable()
    body = []
    drop_boxes = _drop_boxes(cfg)

    for sec in frame_secs:
        m = {c: tab.get(d) for c, d in sec.apertures.items()}
        body.append(gio.comment(f"--- frame, copied from {os.path.basename(pg.M2_REF)}"))
        body.append(f"%LP{sec.polarity}*%")
        body += _drop_inside(gio.remap(sec, m), drop_boxes)

    if cfg.get("relabel", True):
        body.append(gio.comment("--- title block and zone legend"))
        body.append("%LPD*%")
        body += _lettering(res, cfg, tab)

    # everything of the original pillar section except the 0.4 mm pillar pen
    keep = {c: d for c, d in pillar_sec.apertures.items() if not d.startswith("C,0.400")}
    probe = _filter_pillar_section(pillar_sec, keep, None)
    used = {l[:-1] for l in probe if gio._DSEL.match(l)}
    keep = {c: d for c, d in keep.items() if c in used}
    body += _fill_frame_gaps(cfg)
    body += _mesh_contacts(cfg, "m2")

    body.append(gio.comment("--- support discs and markers, copied from the V2 pillar layer"))
    body.append(f"%LP{pillar_sec.polarity}*%")
    body += _filter_pillar_section(pillar_sec, keep, tab)

    style = cfg.get("pillar_style", "flash")
    if style not in ("flash", "stroke"):
        raise ValueError("pillar_style must be 'flash' or 'stroke'")

    # Both reference masks paint the active area as one dark region and knock
    # the pillars out of it in CLEAR polarity.  Emitting them dark would put
    # them in the same colour as the region they sit on - the file would parse
    # and measure correctly and show nothing.  Default to the reference.
    pol = {"clear": "C", "dark": "D"}[cfg.get("pillar_polarity", "clear")]
    if pol != pillar_sec.polarity:
        print(f"warning: pillar_polarity gives %LP{pol}% but the reference "
              f"pillar layer is %LP{pillar_sec.polarity}%", file=sys.stderr)
    body.append(f"%LP{pol}*%")

    def pillars(code, pts, dia):
        """Emit a pillar field, either as flashes or in CEA's stroked-arc style.

        A stroked disc is two half arcs of radius d/4 drawn with a d/2 pen, so
        the painted area is a disc of diameter d - the convention the V2 mask
        used, and the one a viewer still draws in outline mode.
        """
        out = [code + "*"]
        if style == "flash":
            out += [gio.flash(x, y) for x, y in pts]
        else:
            for x, y in pts:
                out += gio.stroked_disc(x, y, dia / 2)
        return out

    for sm in res["seams"]:
        if not len(sm["pts"]):
            continue
        code = tab.circle(sm["diameter_mm"] if style == "flash"
                          else sm["diameter_mm"] / 2)
        body.append(gio.comment(
            f"--- seam between zones {sm['between'][0]} and {sm['between'][1]} "
            f"at {sm['theta']:.4f} deg, {len(sm['pts'])} pillars of "
            f"{sm['diameter_mm']:.3f} mm"))
        body += pillars(code, sm["pts"], sm["diameter_mm"])

    for z, rep in zip(res["zones"], res["report"]):
        code = tab.circle(z["diameter_mm"] if style == "flash"
                          else z["diameter_mm"] / 2)
        body.append(gio.comment(
            f"--- zone {z['zone']}: connectors {z['connectors'][0]}-"
            f"{z['connectors'][1]}, {z['lattice']} pitch {z['pitch_mm']:.3f} mm, "
            f"pillar dia {z['diameter_mm']:.3f} mm, {len(z['pts'])} pillars, "
            f"dead area {100*rep['cov_eff']:.3f} pct, drawn as "
            f"{'flashes' if style == 'flash' else 'stroked arcs'}"))
        body += pillars(code, z["pts"], z["diameter_mm"])

    if res.get("walls"):
        wl0 = res["walls"][0]
        body.append(gio.comment(
            f"--- resist walls along the zone boundaries: {wl0['width']:.2f} mm wide, "
            f"dashed so every zone stays vented to the evacuation channel"))
        body.append(f"%LP{pol}*%")          # resist, like the pillars
        for wl in res["walls"]:
            nrm = np.array([-wl["u"][1], wl["u"][0]]) * wl["width"] / 2
            for a, b in wl["segments"]:
                body += _emit_region([tuple(a + nrm), tuple(b + nrm),
                                      tuple(b - nrm), tuple(a - nrm)])

    # last, so it cuts through the pillar field as well as the border
    body += _emit_evacuation(res["channels"], "m2", tab)

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    head = [
        gio.comment("P2 BASKET - bulk insulation mask M2 (frame + pillars)"),
        gio.comment(f"zoned pillar layout {cfg['name']}"),
        gio.comment(f"pillars drawn as {cfg.get('pillar_style', 'flash')}"),
        gio.comment(f"generated {now} by make_zoned_mask.py"),
        gio.comment(f"frame geometry inherited from {os.path.basename(pg.M2_REF)}"),
        "%FSLAX46Y46*%",
        gio.comment("Gerber Fmt 4.6, leading zero omitted, absolute, unit mm"),
        "%MOMM*%",
        "%LPD*%",
        "G01*",
    ]
    open(path, "w").write("\n".join(head + tab.emit() + body + ["M02*"]) + "\n")


def _clip_polygon(poly, box):
    """Sutherland-Hodgman clip of a polygon to an axis-aligned box."""
    x0, y0, x1, y1 = box
    edges = [(lambda p: p[0] >= x0, lambda a, b: _cut(a, b, 0, x0)),
             (lambda p: p[0] <= x1, lambda a, b: _cut(a, b, 0, x1)),
             (lambda p: p[1] >= y0, lambda a, b: _cut(a, b, 1, y0)),
             (lambda p: p[1] <= y1, lambda a, b: _cut(a, b, 1, y1))]
    out = [tuple(q) for q in poly]
    for keep, cut in edges:
        if not out:
            break
        inp, out = out, []
        for i, b in enumerate(inp):
            a = inp[i - 1]
            if keep(b):
                if not keep(a):
                    out.append(cut(a, b))
                out.append(b)
            elif keep(a):
                out.append(cut(a, b))
    return out


def _cut(a, b, axis, value):
    other = 1 - axis
    t = (value - a[axis]) / (b[axis] - a[axis])
    q = [0.0, 0.0]
    q[axis] = value
    q[other] = a[other] + t * (b[other] - a[other])
    return (q[0], q[1])


def _emit_region(pts, comment=None):
    """A filled G36 region through the given points."""
    out = ([gio.comment(comment)] if comment else []) + ["G36*"]
    out.append(f"X{gio.q(pts[0][0])}Y{gio.q(pts[0][1])}D02*")
    for x, y in pts[1:]:
        out.append(f"X{gio.q(x)}Y{gio.q(y)}D01*")
    out.append(f"X{gio.q(pts[0][0])}Y{gio.q(pts[0][1])}D01*")
    out.append("G37*")
    return out


def _m2_frame_edges():
    """Where the M2 frame's dark region meets the resist wall next to the old pad.

    Returns (y of the bottom edge, radius of the outer arc), read from the
    region's own vertices on either side of the pad.  These sit ~0.3 mm
    further out than M1's centreline outline, so a fill cut to the M1 outline
    leaves the wall 0.3 mm thicker along the old pad's span - a visible step
    in the wall, ~12 mm long on the bottom edge and on the arc.
    """
    import render_gerber as rg
    for kind, pts, pol in rg.interpret(pg.M2_REF)["paint"]:
        if kind != "region" or pol != "D":
            continue
        p = np.asarray(pts)
        if p[:, 0].max() > 560 and p[:, 1].min() < 10 and len(p) > 100:
            bot = p[(p[:, 0] > 540) & (p[:, 0] < 583) & (p[:, 1] < 6), 1]
            arc = p[(p[:, 1] > 17.5) & (p[:, 1] < 80) & (p[:, 0] > 580)]
            if len(bot) and len(arc):
                return float(bot.min()), float(np.median(np.hypot(arc[:, 0], arc[:, 1])))
    return None


def _fill_frame_gaps(cfg):
    """Dark patches that restore the active area where the frame left it clear."""
    if not cfg.get("fill_frame_gaps", True):
        return []
    boxes = [tuple(b) for b in cfg.get("frame_gap_fill_boxes", FRAME_GAP_FILL_BOXES)]
    edges = _m2_frame_edges()
    out = ["%LPD*%"]
    for b in boxes:
        x0, y0, x1, y1 = b
        if edges is None:                       # no reference edges: old behaviour
            pts = _clip_polygon(pg.active_outline(), b)
        else:
            y_bot, R = edges
            ya, yb = max(y_bot, y0), min(y1, R - 1e-6)
            ta, tb = math.asin(ya / R), math.asin(yb / R)
            arc = [(R * math.cos(t), R * math.sin(t))
                   for t in np.linspace(ta, tb, max(8, int(math.degrees(tb - ta) / 0.05)))]
            pts = [(x0, ya)] + arc + [(x0, yb)]
        if len(pts) > 2:
            out += _emit_region(pts,
                                f"--- active area restored where the inherited frame "
                                f"stepped round the removed pad: filled out to the M2 wall "
                                f"edges (bottom y {edges[0]:.3f}, arc r {edges[1]:.3f})"
                                if edges else f"--- active area restored, box {b}")
    return out if len(out) > 1 else []


def _bottom_mesh_contact(ref):
    """The inherited mesh-contact window at the bottom end of the outer arc.

    It is a filled G36 region, not a stroked outline, so it has to come from
    the region list rather than from the stroked paths.
    """
    import render_gerber as rg
    hits = []
    for kind, pts, pol in rg.interpret(ref)["paint"]:
        if kind != "region" or pol != "D":
            continue
        p = np.asarray(pts)
        w = p[:, 0].max() - p[:, 0].min()
        h = p[:, 1].max() - p[:, 1].min()
        if not (0.5 < w < MESH_CONTACT_SOURCE_MAX_SIZE
                and 0.5 < h < MESH_CONTACT_SOURCE_MAX_SIZE):
            continue
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        if (math.hypot(cx, cy) > MESH_CONTACT_SOURCE_MIN_R
                and math.degrees(math.atan2(cy, cx)) < MESH_CONTACT_SOURCE_MAX_T):
            hits.append(p)
    if len(hits) != 1:
        print(f"warning: expected exactly one bottom mesh contact on "
              f"{os.path.basename(ref)}, found {len(hits)}", file=sys.stderr)
    return hits[0] if hits else None


def _mirror(pts, axis_deg):
    """Reflect points through a line through the origin at `axis_deg`."""
    a = math.radians(2 * axis_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(x * ca + y * sa, x * sa - y * ca) for x, y in pts]


def _mesh_contacts(cfg, layer):
    """The mesh-contact window added at the top end of the outer arc."""
    if not cfg.get("mirror_mesh_contact", True):
        return []
    ref = pg.M1_REF if layer == "m1" else pg.M2_REF
    src = _bottom_mesh_contact(ref)
    if src is None:
        print(f"warning: no bottom mesh contact found on {os.path.basename(ref)}",
              file=sys.stderr)
        return []
    axis = cfg.get("mesh_contact_mirror_axis_deg", MESH_CONTACT_MIRROR_AXIS_DEG)
    pts = _mirror([tuple(q) for q in src], axis)
    # drop the duplicated closing vertex if the source polyline carried one
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
        pts = pts[:-1]
    sx, sy = np.asarray(src)[:, 0].mean(), np.asarray(src)[:, 1].mean()
    mx = sum(q[0] for q in pts) / len(pts)
    my = sum(q[1] for q in pts) / len(pts)
    return ["%LPD*%"] + _emit_region(
        pts, f"--- mesh contact, top end of the outer arc: the bottom contact at "
             f"({sx:.2f},{sy:.2f}) mirrored through the {axis:.1f} deg fan axis "
             f"to ({mx:.2f},{my:.2f}), so its edges follow that corner")


def _drop_boxes(cfg):
    """Regions of the inherited frame to delete.

    The title block, whenever it is going to be re-lettered, plus the large
    mesh-contact pad unless the config keeps it, plus anything the config
    lists explicitly in `remove_frame_boxes`.
    """
    boxes = []
    if cfg.get("relabel", True):
        boxes.append(LABEL_BOX)
    if cfg.get("remove_large_mesh_pad", True):
        boxes.append(MESH_CONTACT_PAD_BOX)
    boxes += [tuple(b) for b in cfg.get("remove_frame_boxes", [])]
    return boxes


def _inside_boxes(pts, boxes, inset=0.0):
    """True if every point lies strictly inside one of the boxes."""
    for x0, y0, x1, y1 in boxes:
        if all(x0 + inset < x < x1 - inset and y0 + inset < y < y1 - inset
               for x, y in pts):
            return True
    return False


_COORD = re.compile(
    r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0([123])\*$")


def _drop_inside(lines, boxes):
    """Remove the graphics that fall entirely inside any of `boxes`.

    Understands both stroked runs (a D02 move followed by D01 draws) and
    filled G36/G37 regions, so it takes out a pad - a filled region plus the
    outline stroked round it - as cleanly as a line of text.  Anything that
    only partly overlaps a box is left untouched.
    """
    if not boxes:
        return list(lines)

    out = []
    x = y = 0.0
    run, run_pts = [], []          # a buffered stroked run
    region, reg_pts = None, []     # a buffered G36..G37 block

    def flush_run():
        nonlocal run, run_pts
        if run and not (run_pts and _inside_boxes(run_pts, boxes)):
            out.extend(run)
        run, run_pts = [], []

    for l in lines:
        if region is not None:
            region.append(l)
            m = _COORD.match(l)
            if m:
                x = int(m.group(1)) / gio.SCALE if m.group(1) else x
                y = int(m.group(2)) / gio.SCALE if m.group(2) else y
                reg_pts.append((x, y))
            if l.startswith("G37"):
                if not _inside_boxes(reg_pts, boxes):
                    out.extend(region)
                region, reg_pts = None, []
            continue

        if l.startswith("G36"):
            flush_run()
            region, reg_pts = [l], []
            continue

        m = _COORD.match(l)
        if not m:
            flush_run()
            out.append(l)
            continue

        nx = int(m.group(1)) / gio.SCALE if m.group(1) else x
        ny = int(m.group(2)) / gio.SCALE if m.group(2) else y
        if m.group(5) == "2":          # a move starts a new run
            flush_run()
            run, run_pts = [l], [(nx, ny)]
        else:                          # a draw or a flash extends it
            if not run:
                run, run_pts = [], [(x, y)]
            run.append(l)
            run_pts.append((nx, ny))
        x, y = nx, ny

    flush_run()
    if region is not None:             # unterminated region: keep it
        out.extend(region)
    return out


def _lettering(res, cfg, tab):
    """New title block plus a one-line-per-zone legend along the bottom border."""
    pen = cfg.get("label_pen_mm", 0.35)
    code = tab.circle(pen)
    out = [code + "*"]

    def draw(strokes):
        for st in strokes:
            out.append(f"X{gio.q(st[0][0])}Y{gio.q(st[0][1])}D02*")
            for x, y in st[1:]:
                out.append(f"X{gio.q(x)}Y{gio.q(y)}D01*")

    x0, y0, x1, y1 = LABEL_BOX
    h = 3.0
    lines = [
        "P2_2026",
        f"MASK_M2_{cfg['name']}",
        "ZONED PILLARS",
        f"D{min(r['d_draw'] for r in res['report']):.2f}-{max(r['d_draw'] for r in res['report']):.2f}MM",
        f"P{min(r['pitch'] for r in res['report']):.2f}-{max(r['pitch'] for r in res['report']):.2f}MM",
        "D6MM_DERIVE",
    ]
    gap = (abs(y1 - y0) - 2.0 - len(lines) * h) / max(1, len(lines) - 1)
    ytop = y1 - 1.0 - h
    for i, t in enumerate(lines):
        draw(sf.text(t, x0 + 1.2, ytop - i * (h + gap), h))

    # legend along the free border strip under the detector
    hh = cfg.get("legend_height_mm", 3.5)
    xs = cfg.get("legend_x_mm", 120.0)
    for r in res["report"]:
        t = (f"Z{r['zone']} C{r['connectors'][0]}-{r['connectors'][1]} "
             f"D{r['d_draw']:.2f} P{r['pitch']:.2f} {100*r['cov_eff']:.2f}%")
        draw(sf.text(t, xs, cfg.get("legend_y_mm", -17.0), hh))
        xs += sf.text_width(t, hh) + 8.0
    if xs > 600:
        print(f"warning: the zone legend runs to x={xs:.0f} mm", file=sys.stderr)
    return out


def _filter_pillar_section(sec, keep_defs, tab):
    """Re-emit the pillar section keeping only `keep_defs`, on-panel only.

    Graphics that fall outside the panel (the V2 layer has two stray arcs at
    x = 1287 mm) and aperture blocks left with nothing to draw are dropped.
    """
    m = {c: (tab.get(d) if tab else c) for c, d in keep_defs.items()}
    coord = re.compile(r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0([123])\*$")
    x0, y0, x1, y1 = PANEL

    out, block, run, emitting, x, y = [], None, [], False, 0.0, 0.0

    def flush_run():
        """Add the buffered move+draw run to the current block if it is on-panel."""
        nonlocal run
        if run and all(x0 <= px <= x1 and y0 <= py <= y1 for _, px, py in run):
            block["lines"] += [r[0] for r in run]
            block["drew"] = True
        run = []

    def flush_block():
        nonlocal block
        if block and block["drew"]:
            out.append(block["sel"])
            out.extend(block["lines"])
        block = None

    for l in gio.remap(sec, {**m, **{c: c for c in sec.apertures if c not in m}}):
        sm = gio._DSEL.match(l)
        if sm and int(sm.group(1)) >= 10:
            flush_run()
            flush_block()
            emitting = l[:-1] in m.values()
            block = dict(sel=l, lines=[], drew=False) if emitting else None
            continue
        cm = coord.match(l)
        if cm:
            if cm.group(1):
                x = int(cm.group(1)) / gio.SCALE
            if cm.group(2):
                y = int(cm.group(2)) / gio.SCALE
            if not emitting:
                continue
            if cm.group(5) == "2":
                flush_run()
                run = [(l, x, y)]
            else:
                run.append((l, x, y))
            continue
        if l.startswith("%LP"):          # a polarity switch is never optional
            flush_run()
            flush_block()
            out.append(l)
            emitting = False
            continue
        if emitting:
            flush_run()
            block["lines"].append(l)
    flush_run()
    flush_block()
    return out


def emit_m1(path, cfg, channels):
    """M1 (frame only) is geometrically unchanged; only the title block is
    re-lettered so the two files of a set carry the same name."""
    src = gio.read_sections(pg.M1_REF)
    tab = gio.ApertureTable()
    body = []
    drop_boxes = _drop_boxes(cfg)
    for sec in src:
        m = {c: tab.get(d) for c, d in sec.apertures.items()}
        body.append(f"%LP{sec.polarity}*%")
        body += _drop_inside(gio.remap(sec, m), drop_boxes)
    if cfg.get("relabel", True):
        body.append("%LPD*%")
        code = tab.circle(cfg.get("label_pen_mm", 0.35))
        body.append(code + "*")
        x0, y0, x1, y1 = LABEL_BOX
        h = 4.0
        txt = ["P2_2026", f"MASK_M1_{cfg['name']}", "FRAME ONLY",
               "NO PILLARS"]
        gap = (abs(y1 - y0) - 2.0 - len(txt) * h) / max(1, len(txt) - 1)
        for i, t in enumerate(txt):
            for st in sf.text(t, x0 + 1.2, y1 - 1.0 - h - i * (h + gap), h):
                body.append(f"X{gio.q(st[0][0])}Y{gio.q(st[0][1])}D02*")
                for x, y in st[1:]:
                    body.append(f"X{gio.q(x)}Y{gio.q(y)}D01*")
    body += _mesh_contacts(cfg, "m1")
    body += _emit_evacuation(channels, "m1", tab)

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    head = [
        gio.comment("P2 BASKET - bulk insulation mask M1 (frame only)"),
        gio.comment(f"frame geometry identical to {os.path.basename(pg.M1_REF)}"),
        gio.comment(f"re-emitted {now} by make_zoned_mask.py"),
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "G01*",
    ]
    open(path, "w").write("\n".join(head + tab.emit() + body + ["M02*"]) + "\n")


# --------------------------------------------------------------------------
def print_report(res, cfg):
    g = res["growth"]
    b = res["budget"]
    print(f"\nlayout '{cfg['name']}' - {cfg.get('description','')}")
    print(f"frame inherited from CEA {pg.frame_source()} "
          f"({os.path.basename(pg.M2_REF)})")
    print(f"active area {res['area_total']:.0f} mm^2 = {res['area_total']/100:.1f} cm^2, "
          f"lamination growth allowance {1000*g:.0f} um, "
          f"dead-area budget {100*b:.2f} %\n")
    hdr = (f"{'zn':>2s} {'conn':>6s} {'lat':>6s} {'pitch':>6s} {'dia':>5s} {'N':>6s} "
           f"{'p/cm2':>6s} {'dead(draw)':>10s} {'dead(eff)':>10s} {'maxgap':>7s} {'minNN':>6s}")
    print(hdr)
    print("-" * len(hdr))
    ntot = 0
    dead_eff = 0.0
    ok = True
    for r in res["report"]:
        ntot += r["n"]
        dead_eff += r["n"] * math.pi * (r["d_eff"] / 2) ** 2
        flag = "" if r["cov_eff"] <= r["budget"] + 1e-9 else "  <-- OVER BUDGET"
        ok &= r["cov_eff"] <= r["budget"] + 1e-9
        if r["budget"] != b:
            flag += f"  (zone budget {100*r['budget']:.1f} %)"
        print(f"{r['zone']:2d} {r['connectors'][0]:2d}-{r['connectors'][1]:<3d} "
              f"{r['lattice']:>6s} {r['pitch']:6.3f} {r['d_draw']:5.2f} {r['n']:6d} "
              f"{r['pillars_per_cm2']:6.2f} {100*r['cov_draw']:9.3f}% {100*r['cov_eff']:9.3f}% "
              f"{r['max_unsupported_radius']:7.2f} {r['nn_min']:6.3f}"
              f"{'' if not r['n_dropped'] else '  (-%d at boundary)' % r['n_dropped']}{flag}")
    disc_a = sum(math.pi * (d / 2) ** 2 for _, _, d in res["discs"])
    nseam = sum(len(sm["pts"]) for sm in res["seams"])
    for sm in res["seams"]:
        dead_eff += len(sm["pts"]) * math.pi * ((sm["diameter_mm"] + g) / 2) ** 2
    print("-" * len(hdr))
    for sm in res["seams"]:
        print(f"   seam {sm['between'][0]}|{sm['between'][1]} at {sm['theta']:.3f} deg: "
              f"{len(sm['pts'])} pillars of {sm['diameter_mm']:.2f} mm every "
              f"{sm['pitch_mm']:.2f} mm (counted half to each side)")
    wall_a = sum(wl["length"] * (wl["width"] + g) for wl in res.get("walls", []))
    for wl in res.get("walls", []):
        print(f"   wall {wl['between'][0]}|{wl['between'][1]} at {wl['theta']:.3f} deg: "
              f"{wl['width']:.2f} mm, {len(wl['segments'])} dashes, "
              f"{wl['length']:.1f} mm of wall, {wl['length']*(wl['width']+g):.0f} mm^2 "
              f"(counted half to each side)")
    for r in res["report"]:
        if r.get("cov_wall_eff"):
            print(f"   zone {r['zone']}: pillars {100*r['cov_eff']:.2f} % + walls "
                  f"{100*r['cov_wall_eff']:.2f} % = {100*r['cov_total_eff']:.2f} %"
                  + (f"   [{r['reference']}]" if r.get("reference") else ""))
    dead_eff += wall_a
    print(f"total {ntot + nseam} pillars ({nseam} on seams), whole-detector dead area "
          f"{100*(dead_eff+disc_a)/res['area_total']:.3f} % "
          f"(incl. {100*disc_a/res['area_total']:.2f} % from the 5 support discs)")
    for c in res.get("channels", []):
        print(f"   evacuation {c['layer'].upper()} '{c['name']}': {c['width']:.2f} mm slot "
              f"({c['start'][0]:.2f},{c['start'][1]:.2f}) -> "
              f"({c['end'][0]:.2f},{c['end'][1]:.2f}), "
              f"{np.hypot(*(c['end']-c['start'])):.2f} mm long"
              + (f", {c['droplet']:.2f} mm reservoir" if c["droplet"] else ""))
    print("maxgap = radius of the largest pillar-free disc in the zone (mesh span proxy)")
    print("minNN  = smallest centre-to-centre distance inside the zone")
    return ok


def solve_pitches(cfg, tol=2e-4, maxit=12, verbose=True):
    pg.set_frame_source(cfg.get("frame_source", "V1"))
    """Find the pitch of every zone that carries a `target_dead_area`.

    Coverage falls as 1/pitch^2, so one rescaling per iteration converges in a
    handful of passes even with the seam rows and the disc keep-outs folded in.
    """
    cfg = json.loads(json.dumps(cfg))
    targets = {z["zone"]: z["target_dead_area"] for z in cfg["zones"]
               if "target_dead_area" in z}
    for z in cfg["zones"]:
        if z["zone"] in targets and "pitch_mm" not in z:
            d = z["diameter_mm"] + cfg.get("lamination_growth_mm", 0.05)
            k = 0.9069 if z["lattice"] == "hex" else math.pi / 4
            z["pitch_mm"] = round(d * math.sqrt(k / targets[z["zone"]]), 3)
    if not targets:
        return cfg, build(cfg)
    for it in range(maxit):
        res = build(cfg)
        worst = 0.0
        for z, r in zip(cfg["zones"], res["report"]):
            if z["zone"] not in targets:
                continue
            t = targets[z["zone"]]
            worst = max(worst, abs(r["cov_eff"] - t))
            z["pitch_mm"] = round(z["pitch_mm"] * math.sqrt(r["cov_eff"] / t), 3)
        if verbose:
            print(f"  pitch solve iteration {it+1}: worst |cov - target| = "
                  f"{100*worst:.4f} %")
        if worst < tol:
            break
    # settle on the 0.01 mm grid a mask shop can work with, then re-evaluate
    for z in cfg["zones"]:
        if z["zone"] in targets:
            z["pitch_mm"] = math.ceil(z["pitch_mm"] * 100) / 100
    return cfg, build(cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--force", action="store_true",
                    help="write the gerbers even if a zone is over budget")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    cfg, res = solve_pitches(cfg)
    ok = print_report(res, cfg)
    if a.no_write:
        return 0 if ok else 1
    if not ok and not a.force:
        print("\nnothing written: a zone exceeds the dead-area budget", file=sys.stderr)
        return 1

    out = a.outdir or os.path.join(OUTROOT, "Insulation_masks", cfg["name"])
    os.makedirs(out, exist_ok=True)
    m1 = os.path.join(out, f"P2_BASKET-Mask_M1_{cfg['name']}.gbr")
    m2 = os.path.join(out, f"P2_BASKET-Mask_M2_{cfg['name']}.gbr")
    emit_m1(m1, cfg, res["channels"])
    emit_m2(res, cfg, m2)
    json.dump(cfg, open(os.path.join(out, os.path.basename(a.config)), "w"), indent=2)
    with open(os.path.join(out, "zone_report.csv"), "w") as f:
        f.write("zone,conn_first,conn_last,theta_min_deg,theta_max_deg,lattice,pitch_mm,"
                "d_drawn_mm,d_effective_mm,n_pillars,area_mm2,pillars_per_cm2,"
                "dead_area_drawn,dead_area_effective,max_unsupported_radius_mm,min_nn_mm,"
                "wall_dead_area_effective,total_dead_area_effective,reference\n")
        for r in res["report"]:
            f.write(f"{r['zone']},{r['connectors'][0]},{r['connectors'][1]},"
                    f"{r['theta'][0]:.4f},{r['theta'][1]:.4f},{r['lattice']},{r['pitch']},"
                    f"{r['d_draw']},{r['d_eff']:.3f},{r['n']},{r['area_mm2']:.1f},"
                    f"{r['pillars_per_cm2']:.3f},{r['cov_draw']:.5f},{r['cov_eff']:.5f},"
                    f"{r['max_unsupported_radius']:.3f},{r['nn_min']:.3f},"
                    f"{r['cov_wall_eff']:.5f},{r['cov_total_eff']:.5f},"
                    f"\"{r['reference']}\"\n")
    print(f"\nwritten:\n  {m1}\n  {m2}\n  {os.path.join(out,'zone_report.csv')}")
    np.save(os.path.join(out, "pillars.npy"),
            np.vstack([np.c_[g["pts"], np.full(len(g["pts"]), g["zone"] or 0),
                             np.full(len(g["pts"]), g["diameter_mm"])]
                       for g in res["zones"] + res["seams"] if len(g["pts"])]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
