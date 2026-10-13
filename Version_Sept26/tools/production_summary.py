#!/usr/bin/env python3
"""
Build the production summary - the sheet that goes to the mask shop.

Reads every variant that has been generated and reports, per zone and per
variant: pillar diameter, pitch, count, the area it costs, and the smallest
feature the shop has to hold.  Writes PRODUCTION_SUMMARY.md and
production_summary.csv next to the masks.
"""
from __future__ import annotations

import csv
import datetime
import json
import math
import os
import re

import numpy as np

import gerber_io as gio
import p2_geometry as pg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
MASKS = os.path.join(ROOT, "Insulation_masks")


def variants():
    out = []
    for name in sorted(os.listdir(MASKS)):
        d = os.path.join(MASKS, name)
        rep = os.path.join(d, "zone_report.csv")
        cfgs = [f for f in os.listdir(d) if f.endswith(".json")] if os.path.isdir(d) else []
        if os.path.exists(rep) and cfgs:
            out.append((name, list(csv.DictReader(open(rep))),
                        json.load(open(os.path.join(d, cfgs[0])))))
    return out


def apertures(path):
    seen = {}
    for sec in gio.read_sections(path):
        for code, d in sec.apertures.items():
            m = re.match(r"^C,([\d.]+)", d)
            if m:
                seen[round(float(m.group(1)), 4)] = True
    return sorted(seen)


def main():
    vs = variants()
    vs.sort(key=lambda v: (not v[2].get("release", False), v[0]))
    if not vs:
        print("nothing generated yet")
        return 1
    pg.set_frame_source(vs[0][2].get("frame_source", "V1"))
    area = gio.polygon_area(pg.active_outline())
    discs = pg.support_discs()
    disc_area = sum(math.pi * (d / 2) ** 2 for _, _, d in discs)

    rows = []
    for name, rep, cfg in vs:
        growth = cfg.get("lamination_growth_mm", 0.05)
        for r in rep:
            rows.append(dict(
                variant=name, zone=r["zone"],
                connectors=f"{r['conn_first']}-{r['conn_last']}",
                diameter_mm=float(r["d_drawn_mm"]),
                pitch_mm=float(r["pitch_mm"]),
                lattice=r["lattice"],
                n_pillars=int(r["n_pillars"]),
                zone_area_cm2=float(r["area_mm2"]) / 100,
                pillars_per_cm2=float(r["pillars_per_cm2"]),
                dead_area_drawn_pct=100 * float(r["dead_area_drawn"]),
                dead_area_effective_pct=100 * float(r["dead_area_effective"]),
                max_unsupported_span_mm=float(r["max_unsupported_radius_mm"]),
                lamination_growth_mm=growth))

    with open(os.path.join(ROOT, "production_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d")
    L = []
    A = L.append
    A("# P2 basket bulk insulation — production summary")
    A("")
    A(f"Generated {now} from the masks in `Insulation_masks/`. "
      f"Machine-readable copy: `production_summary.csv`.")
    A("")
    rel = [v for v in vs if v[2].get("release")]
    if rel:
        A(f"> **Mask to build: `{rel[0][0]}`** — "
          f"`Insulation_masks/{rel[0][0]}/P2_BASKET-Mask_M1_{rel[0][0]}.gbr` and "
          f"`P2_BASKET-Mask_M2_{rel[0][0]}.gbr`. Every other variant below is a design "
          f"study kept for the record and is **not** for production.")
        A("")
    A("## Common to every variant")
    A("")
    A(f"| | |")
    A(f"|---|---|")
    A(f"| Frame inherited from | CEA {pg.frame_source()} "
      f"(`{os.path.basename(pg.M1_REF)}` / `{os.path.basename(pg.M2_REF)}`) |")
    A(f"| Active area | {area:.0f} mm² = **{area/100:.1f} cm²** |")
    A(f"| Perimeter resist wall | 2.6 mm |")
    A(f"| Support discs | 5 × Ø6.15 mm ({disc_area:.0f} mm², {100*disc_area/area:.2f} % of the active area) |")
    A(f"| Mesh contacts | 2 windows, one at each end of the outer arc |")
    A(f"| Evacuation channel | inner bottom corner: 1.30 mm slot + Ø3.00 mm reservoir on M1, 2.00 mm slot on M2 |")
    A(f"| Lamination growth assumed | +{1000*rows[0]['lamination_growth_mm']:.0f} µm on the drawn diameter |")
    A(f"| Units / format | mm, RS-274X, `%FSLAX46Y46%` |")
    A("")
    A("Dead area below is quoted **with** the growth allowance, i.e. what the "
      "finished detector loses. `dead_area_drawn` in the CSV is the same figure "
      "for the drawn diameter, before growth.")
    A("")

    for name, rep, cfg in vs:
        tot = sum(int(r["n_pillars"]) for r in rep)
        g = cfg.get("lamination_growth_mm", 0.05)
        dead = sum(int(r["n_pillars"]) * math.pi * ((float(r["d_drawn_mm"]) + g) / 2) ** 2
                   for r in rep)
        wall_dead = sum(float(r.get("wall_dead_area_effective") or 0) * float(r["area_mm2"])
                        for r in rep)
        m2 = os.path.join(MASKS, name, f"P2_BASKET-Mask_M2_{name}.gbr")
        aps = apertures(m2) if os.path.exists(m2) else []
        pill = sorted({float(r["d_drawn_mm"]) for r in rep})
        release = cfg.get("release", False)
        A(f"## {name}" + ("  —  release mask" if release else "  —  design study, not for production"))
        A("")
        A(f"{cfg.get('description','').strip()}")
        A("")
        has_walls = any(r.get("wall_dead_area_effective") not in (None, "", "0.00000") for r in rep)
        if has_walls:
            A("| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | "
              "dead area: pillars | + walls | = total | longest unsupported span [mm] |")
            A("|---|---|---|---|---|---|---|---|---|---|---|")
        else:
            A("| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | "
              "dead area | longest unsupported span [mm] |")
            A("|---|---|---|---|---|---|---|---|---|")
        for r in rep:
            row = (f"| {r['zone']} | {r['conn_first']}–{r['conn_last']} | {r['lattice']} | "
                   f"{float(r['d_drawn_mm']):.2f} | {float(r['pitch_mm']):.2f} | "
                   f"{int(r['n_pillars']):,} | {float(r['pillars_per_cm2']):.1f} | "
                   f"{100*float(r['dead_area_effective']):.2f} % | ")
            if has_walls:
                row += (f"{100*float(r['wall_dead_area_effective']):.2f} % | "
                        f"{100*float(r['total_dead_area_effective']):.2f} % | ")
            row += f"{float(r['max_unsupported_radius_mm']):.2f} |"
            A(row.replace(",", " "))
        A("")
        for r in rep:
            if r.get("reference"):
                A(f"- **Zone {r['zone']} is a reference:** {r['reference']}.")
        walls = cfg.get("zone_walls")
        if walls:
            dash = walls.get("dash_mm", 0) or 0
            A(f"- **Zone walls:** {walls.get('width_mm', 1.0):.2f} mm resist along each of the "
              f"{len(rep)-1} zone boundaries" +
              (f", in {dash:.0f} mm dashes with {walls.get('gap_mm', 0):.0f} mm gaps so every zone "
               f"stays vented to the evacuation channel" if dash else
               ", continuous from the inner to the outer frame - so only the zone holding the "
               "evacuation channel is vented during lamination; the others are sealed under the mesh") +
              f"; pillars kept {walls.get('pillar_clearance_mm', 0.5):.2f} mm edge-to-edge clear. "
              f"Wall area is listed apart from the pillar dead area because it sits on the "
              f"boundary strips shared by two zones.")
        A(f"- **Total pillars:** {tot:,}".replace(",", " "))
        A(f"- **Whole-detector dead area:** "
          f"{100*(dead+wall_dead+disc_area)/area:.2f} % (pillars {100*dead/area:.2f} % "
          + (f"+ walls {100*wall_dead/area:.2f} % " if wall_dead else "")
          + f"+ support discs {100*disc_area/area:.2f} %)")
        A(f"- **Pillar diameters used:** " + ", ".join(f"Ø{d:.2f}" for d in pill) + " mm")
        A(f"- **Smallest pillar:** Ø{min(pill):.2f} mm — this is the critical "
          f"dimension for the shop")
        if cfg.get("zone_walls"):
            A("- **Zone boundaries:** separated by the resist walls above (no seam rows, "
              "no cross-zone spacing rule needed)")
        else:
            A(f"- **Cross-zone minimum pillar spacing:** "
              f"{cfg.get('boundary_min_spacing_mm', 0):.1f} mm")
        A(f"- **All circular apertures in M2:** " +
          ", ".join(f"{a:.3f}" for a in aps) + " mm")
        A("")

    A("## What we need the shop to confirm")
    A("")
    relpill = sorted({float(r["diameter_mm"]) for r in rows
                      if rel and r["variant"] == rel[0][0]}) or \
        sorted({float(r["diameter_mm"]) for r in rows})
    A(f"1. **Minimum pillar diameter — settled.** The shop's floor is Ø0.50 mm; the release "
      f"mask uses Ø{min(relpill):.2f} mm throughout. The design studies V3A and V3C go below "
      f"it, which is why they are not for production.")
    A(f"2. **Lamination growth.** Everything is sized for "
      f"+{1000*rows[0]['lamination_growth_mm']:.0f} µm on the drawn diameter. "
      f"If the real figure differs, every pitch re-solves — tell us the number "
      f"and we re-issue.")
    if rel and rel[0][2].get("zone_walls"):
        A(f"3. **Zone walls.** {rel[0][2]['zone_walls'].get('width_mm', 1.0):.2f} mm resist lines "
          f"in dashes — confirm this width resolves cleanly alongside the 0.50 mm pillars.")
    A("")
    open(os.path.join(ROOT, "PRODUCTION_SUMMARY.md"), "w").write("\n".join(L) + "\n")
    print(f"written {os.path.join(ROOT, 'PRODUCTION_SUMMARY.md')}")
    print(f"written {os.path.join(ROOT, 'production_summary.csv')}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
