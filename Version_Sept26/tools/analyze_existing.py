#!/usr/bin/env python3
"""Quantify the two existing P2 pillar layouts (CEA V2 and CERN)."""
import math

import numpy as np

import gerber_io as gio
import p2_geometry as pg


def coverage(centres, d_eff, area):
    return len(centres) * math.pi * (d_eff / 2) ** 2 / area


def nn_stats(c):
    """Nearest-neighbour distance of a point cloud, on a grid-bucketed search."""
    from scipy.spatial import cKDTree
    t = cKDTree(c)
    d, _ = t.query(c, k=2)
    return d[:, 1]


def main():
    print("CEA frame versions (the perimeter wall differs):")
    for v in ("V1", "V2"):
        pg.set_frame_source(v)
        a = gio.polygon_area(pg.active_outline())
        print(f"   {v}: active area {a:9.1f} mm^2 = {a/100:7.1f} cm^2")
    pg.set_frame_source("V1")
    print("   V1 is the mask all the detectors so far were built with, and the "
          "one CERN adapted;\n   it is the frame these new masks inherit.\n")

    poly = pg.active_outline()
    area = gio.polygon_area(poly)
    edges, step = pg.connector_sector_edges()
    discs = pg.support_discs()
    disc_area = sum(math.pi * (d / 2) ** 2 for _, _, d in discs)

    print(f"Active area (inner edge of the bulk frame) : {area:9.1f} mm^2 = {area/100:.1f} cm^2")
    print(f"Fan apex {pg.connectors()[0].round(3)}   connector radius {pg.connectors()[1]:.2f} mm")
    print(f"Connector wedge width {step:.4f} deg, full span "
          f"{edges[0]:.3f} .. {edges[-1]:.3f} deg")
    print(f"{len(discs)} large support discs of {discs[0,2]:.2f} mm "
          f"-> {disc_area:.1f} mm^2 = {100*disc_area/area:.3f} % of the active area")
    print()

    hdr = f"{'design':10s} {'N':>7s} {'d_draw':>7s} {'lattice':>22s} " \
          f"{'cov(draw)':>10s} {'cov(+50um)':>11s} {'cov(+100um)':>12s} {'min NN':>7s}"
    print(hdr)
    print("-" * len(hdr))
    for name, (c, d) in [(f"CEA {pg.frame_source()}", pg.cea_pillars()),
                         ("CERN", pg.cern_pillars())]:
        nn = nn_stats(c)
        c = c[pg.point_in_polygon(c, poly)]      # count only what lands in the active area
        lat = f"NN {np.median(nn):.3f} mm"
        row = (f"{name:10s} {len(c):7d} {d:7.3f} {lat:>22s} "
               f"{100*coverage(c, d, area):9.3f}% {100*coverage(c, d+0.05, area):10.3f}% "
               f"{100*coverage(c, d+0.10, area):11.3f}% {nn.min():7.3f}")
        print(row)
    print()
    print("(cov = pillar area / active area; the 5 big discs add "
          f"{100*disc_area/area:.2f} % on top for both designs)")
    print()

    # clearance actually used against the frame
    for name, (c, d) in [(f"CEA {pg.frame_source()}", pg.cea_pillars()),
                         ("CERN", pg.cern_pillars())]:
        dist = pg.distance_to_polygon(c, poly)
        inside = pg.point_in_polygon(c, poly)
        print(f"{name:8s}: pillars inside the frame outline {inside.sum()}/{len(c)}, "
              f"closest centre-to-frame {dist.min():.3f} mm "
              f"(edge-to-edge {dist.min()-d/2:.3f} mm)")

    # per connector-pair breakdown of the existing designs
    print()
    print("Dead area per 2-connector zone (drawn diameter, no growth):")
    print(f"{'zone':>4s} {'theta [deg]':>16s} {'area [cm2]':>11s} "
          f"{'N CEA':>7s} {'cov CEA':>9s} {'N CERN':>7s} {'cov CERN':>9s}")
    zedges = edges[::2]
    zone_area = sector_areas(poly, zedges)
    cea_c, cea_d = pg.cea_pillars()
    cern_c, cern_d = pg.cern_pillars()
    cea_in = cea_c[pg.point_in_polygon(cea_c, poly)]
    cern_in = cern_c[pg.point_in_polygon(cern_c, poly)]
    for j in range(len(zedges) - 1):
        sel = lambda c: in_wedge(c, zedges[j], zedges[j + 1])
        nc, nn_ = sel(cea_in).sum(), sel(cern_in).sum()
        a = zone_area[j]
        print(f"{j+1:4d} {zedges[j]:7.3f}..{zedges[j+1]:6.3f} {a/100:11.1f} "
              f"{nc:7d} {100*nc*math.pi*(cea_d/2)**2/a:8.3f}% "
              f"{nn_:7d} {100*nn_*math.pi*(cern_d/2)**2/a:8.3f}%")


def in_wedge(c, t0, t1, apex=(0.0, 0.0)):
    t = np.degrees(np.arctan2(c[:, 1] - apex[1], c[:, 0] - apex[0]))
    return (t >= t0) & (t < t1)


def sector_areas(poly, zedges, apex=(0.0, 0.0), n=4000):
    """Monte-Carlo-free area split: rasterise the active polygon once."""
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    gx = np.linspace(x0, x1, n)
    gy = np.linspace(y0, y1, n)
    cell = (gx[1] - gx[0]) * (gy[1] - gy[0])
    X, Y = np.meshgrid(gx, gy)
    P = np.c_[X.ravel(), Y.ravel()]
    inside = pg.point_in_polygon(P, poly)
    P = P[inside]
    t = np.degrees(np.arctan2(P[:, 1] - apex[1], P[:, 0] - apex[0]))
    return np.array([((t >= zedges[j]) & (t < zedges[j + 1])).sum() * cell
                     for j in range(len(zedges) - 1)])


if __name__ == "__main__":
    main()
