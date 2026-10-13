# P2 basket bulk insulation — production summary

Generated 2026-09-15 from the masks in `Insulation_masks/`. Machine-readable copy: `production_summary.csv`.

> **Mask to build: `V3B_final`** — `Insulation_masks/V3B_final/P2_BASKET-Mask_M1_V3B_final.gbr` and `P2_BASKET-Mask_M2_V3B_final.gbr`. Every other variant below is a design study kept for the record and is **not** for production.

## Common to every variant

| | |
|---|---|
| Frame inherited from | CEA V1 (`P2_BASKET-Mask_M1_V1.gbr` / `P2_BASKET-Mask_M2_V1.gbr`) |
| Active area | 173849 mm² = **1738.5 cm²** |
| Perimeter resist wall | 2.6 mm |
| Support discs | 5 × Ø6.15 mm (149 mm², 0.09 % of the active area) |
| Mesh contacts | 2 windows, one at each end of the outer arc |
| Evacuation channel | inner bottom corner: 1.30 mm slot + Ø3.00 mm reservoir on M1, 2.00 mm slot on M2 |
| Lamination growth assumed | +50 µm on the drawn diameter |
| Units / format | mm, RS-274X, `%FSLAX46Y46%` |

Dead area below is quoted **with** the growth allowance, i.e. what the finished detector loses. `dead_area_drawn` in the CSV is the same figure for the drawn diameter, before growth.

## V3B_final  —  release mask

Production mask. Pillar diameter 0.50 mm everywhere - the smallest the shop can make. Zone 1 carries the CERN bulk layout as the reference: 0.50 mm pillars on the same 2.00 x 2.00 mm grid, at the same coordinates as CERN's P2_Mask2. Zones 2-5 are hexagonal with the least dense support in the centre: 2.20 % (zone 2), 0.75 % (zone 3, centre), 1.10 % (zone 4), 1.60 % (zone 5) dead area. A continuous 1.00 mm resist wall runs along each zone boundary so the zones are physically separated; as a consequence only zone 1 is vented by the evacuation channel during lamination.

| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | dead area: pillars | + walls | = total | longest unsupported span [mm] |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1–2 | square | 0.50 | 2.00 | 9 103 | 24.6 | 5.84 % | 0.68 % | 6.52 % | 1.41 |
| 2 | 3–4 | hex | 0.50 | 3.47 | 3 069 | 9.2 | 2.19 % | 1.51 % | 3.70 % | 2.36 |
| 3 | 5–6 | hex | 0.50 | 5.93 | 1 044 | 3.2 | 0.75 % | 1.52 % | 2.27 % | 3.47 |
| 4 | 7–8 | hex | 0.50 | 4.91 | 1 537 | 4.6 | 1.10 % | 1.51 % | 2.61 % | 2.91 |
| 5 | 9–10 | hex | 0.50 | 4.11 | 2 489 | 6.7 | 1.60 % | 0.68 % | 2.28 % | 2.46 |

- **Zone 1 is a reference:** CERN bulk 3717-A (P2_Mask2): 0.50 mm on a 2.00 x 2.00 mm grid, identical coordinates; deliberately over the 3 % budget.
- **Zone walls:** 1.00 mm resist along each of the 4 zone boundaries, continuous from the inner to the outer frame - so only the zone holding the evacuation channel is vented during lamination; the others are sealed under the mesh; pillars kept 0.50 mm edge-to-edge clear. Wall area is listed apart from the pillar dead area because it sits on the boundary strips shared by two zones.
- **Total pillars:** 17 242
- **Whole-detector dead area:** 3.60 % (pillars 2.36 % + walls 1.16 % + support discs 0.09 %)
- **Pillar diameters used:** Ø0.50 mm
- **Smallest pillar:** Ø0.50 mm — this is the critical dimension for the shop
- **Zone boundaries:** separated by the resist walls above (no seam rows, no cross-zone spacing rule needed)
- **All circular apertures in M2:** 0.135, 0.150, 0.200, 0.225, 0.350, 0.500, 2.000, 3.075 mm

## V3A  —  design study, not for production

iso dead-area sweep. Every zone is tuned to 2.95 % effective dead area; only the pillar diameter changes (0.35 -> 0.80 mm) and the pitch follows. Asks: at a fixed efficiency budget, are many small pillars better or worse than few large ones?

| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | dead area | longest unsupported span [mm] |
|---|---|---|---|---|---|---|---|---|
| 1 | 1–2 | hex | 0.35 | 2.20 | 8 619 | 23.3 | 2.93 % | 2.66 |
| 2 | 3–4 | hex | 0.40 | 2.47 | 6 143 | 18.4 | 2.93 % | 2.75 |
| 3 | 5–6 | hex | 0.50 | 3.02 | 4 101 | 12.4 | 2.94 % | 3.00 |
| 4 | 7–8 | hex | 0.65 | 3.86 | 2 541 | 7.6 | 2.94 % | 3.40 |
| 5 | 9–10 | hex | 0.80 | 4.71 | 1 923 | 5.2 | 2.95 % | 3.82 |

- **Total pillars:** 23 327
- **Whole-detector dead area:** 3.02 % (pillars 2.94 % + support discs 0.09 %)
- **Pillar diameters used:** Ø0.35, Ø0.40, Ø0.50, Ø0.65, Ø0.80 mm
- **Smallest pillar:** Ø0.35 mm — this is the critical dimension for the shop
- **Cross-zone minimum pillar spacing:** 3.0 mm
- **All circular apertures in M2:** 0.135, 0.150, 0.200, 0.225, 0.350, 0.400, 0.500, 0.650, 0.800, 2.000, 3.075 mm

## V3B  —  design study, not for production

support-density sweep at the CERN pillar diameter (0.50 mm). Dead area graded 2.95 -> 0.75 %, pitch 3.0 -> 6.0 mm. Asks: how sparse can the mesh support get before the mesh sags, the gain becomes non-uniform, or the detector sparks?

| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | dead area | longest unsupported span [mm] |
|---|---|---|---|---|---|---|---|---|
| 1 | 1–2 | hex | 0.50 | 3.03 | 4 581 | 12.4 | 2.94 % | 3.01 |
| 2 | 3–4 | hex | 0.50 | 3.50 | 3 082 | 9.2 | 2.20 % | 3.33 |
| 3 | 5–6 | hex | 0.50 | 4.12 | 2 212 | 6.7 | 1.59 % | 3.76 |
| 4 | 7–8 | hex | 0.50 | 5.00 | 1 522 | 4.6 | 1.10 % | 4.19 |
| 5 | 9–10 | hex | 0.50 | 6.09 | 1 155 | 3.1 | 0.75 % | 4.28 |

- **Total pillars:** 12 552
- **Whole-detector dead area:** 1.80 % (pillars 1.72 % + support discs 0.09 %)
- **Pillar diameters used:** Ø0.50 mm
- **Smallest pillar:** Ø0.50 mm — this is the critical dimension for the shop
- **Cross-zone minimum pillar spacing:** 3.0 mm
- **All circular apertures in M2:** 0.135, 0.150, 0.200, 0.225, 0.350, 0.500, 2.000, 3.075 mm

## V3C  —  design study, not for production

two-factor design. Three dead-area levels - 2.95 / 2.00 / 1.50 % effective - crossed with three pillar diameters. Zones 1 and 4 sit at 2.95 % with the widest size contrast available (0.40 vs 0.80 mm); zones 3 and 5 repeat 0.50 and 0.80 mm at 1.50 %; zone 2 adds the intermediate 2.00 % point at 0.50 mm. The pitch still grows monotonically from zone 1 to zone 5, which keeps the zone boundaries mild.

| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | dead area | longest unsupported span [mm] |
|---|---|---|---|---|---|---|---|---|
| 1 | 1–2 | hex | 0.40 | 2.48 | 6 849 | 18.5 | 2.94 % | 2.69 |
| 2 | 3–4 | hex | 0.50 | 3.67 | 2 805 | 8.4 | 2.00 % | 3.36 |
| 3 | 5–6 | hex | 0.50 | 4.25 | 2 081 | 6.3 | 1.50 % | 3.76 |
| 4 | 7–8 | hex | 0.80 | 4.72 | 1 716 | 5.2 | 2.94 % | 3.91 |
| 5 | 9–10 | hex | 0.80 | 6.64 | 968 | 2.6 | 1.50 % | 4.61 |

- **Total pillars:** 14 419
- **Whole-detector dead area:** 2.26 % (pillars 2.17 % + support discs 0.09 %)
- **Pillar diameters used:** Ø0.40, Ø0.50, Ø0.80 mm
- **Smallest pillar:** Ø0.40 mm — this is the critical dimension for the shop
- **Cross-zone minimum pillar spacing:** 3.0 mm
- **All circular apertures in M2:** 0.135, 0.150, 0.200, 0.225, 0.350, 0.400, 0.500, 0.800, 2.000, 3.075 mm

## V3C-stroke  —  design study, not for production

two-factor design. Three dead-area levels - 2.95 / 2.00 / 1.50 % effective - crossed with three pillar diameters. Zones 1 and 4 sit at 2.95 % with the widest size contrast available (0.40 vs 0.80 mm); zones 3 and 5 repeat 0.50 and 0.80 mm at 1.50 %; zone 2 adds the intermediate 2.00 % point at 0.50 mm. The pitch still grows monotonically from zone 1 to zone 5, which keeps the zone boundaries mild. Pillar field written in the CEA stroked-arc convention instead of flashes; the geometry is identical to V3C.

| zone | connectors | lattice | Ø drawn [mm] | pitch [mm] | pillars | per cm² | dead area | longest unsupported span [mm] |
|---|---|---|---|---|---|---|---|---|
| 1 | 1–2 | hex | 0.40 | 2.48 | 6 849 | 18.5 | 2.94 % | 2.69 |
| 2 | 3–4 | hex | 0.50 | 3.67 | 2 805 | 8.4 | 2.00 % | 3.36 |
| 3 | 5–6 | hex | 0.50 | 4.25 | 2 081 | 6.3 | 1.50 % | 3.76 |
| 4 | 7–8 | hex | 0.80 | 4.72 | 1 716 | 5.2 | 2.94 % | 3.91 |
| 5 | 9–10 | hex | 0.80 | 6.64 | 968 | 2.6 | 1.50 % | 4.61 |

- **Total pillars:** 14 419
- **Whole-detector dead area:** 2.26 % (pillars 2.17 % + support discs 0.09 %)
- **Pillar diameters used:** Ø0.40, Ø0.50, Ø0.80 mm
- **Smallest pillar:** Ø0.40 mm — this is the critical dimension for the shop
- **Cross-zone minimum pillar spacing:** 3.0 mm
- **All circular apertures in M2:** 0.135, 0.150, 0.200, 0.225, 0.250, 0.350, 0.400, 0.500, 2.000, 3.075 mm

## What we need the shop to confirm

1. **Minimum pillar diameter — settled.** The shop's floor is Ø0.50 mm; the release mask uses Ø0.50 mm throughout. The design studies V3A and V3C go below it, which is why they are not for production.
2. **Lamination growth.** Everything is sized for +50 µm on the drawn diameter. If the real figure differs, every pitch re-solves — tell us the number and we re-issue.
3. **Zone walls.** 1.00 mm resist lines in dashes — confirm this width resolves cleanly alongside the 0.50 mm pillars.

