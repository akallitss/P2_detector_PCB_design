# P2 basket: drift contact variant B2 (Oct 2026)

The drift (window) HV contact moves onto the PCB. The corner readout pad next
to the bottom-right HV pads (`/Sector0/Sig1`) is given up. In its place:

- a 3 × 3 mm gold **drift pad**, with a soldered pogo pin up to a copper tab glued on the
  mylar window's aluminium coating, which faces the PCB;
- a via next to the pad;
- a 38 mm **back-side trace** to the **D** solder pad, so both HV cables (M and
  D) stay at the same corner as today.

This folder holds patched copies of the fabrication files and of the V3B_final
insulation masks. **The originals are not modified.**

| | source (read only) | patched copy |
|---|---|---|
| PCB | `Version_Apr26/FABRICATION_P2/` | `FABRICATION_P2_B2/` |
| masks | `Version_Sept26/Insulation_masks/V3B_final/` | `Insulation_masks/V3B_final_B2/` |

3D model of this variant:
- `B2_drift_contact.html` in this folder: the page for the PCB designers;
- `../../drift_contact/conceptB_3d.html`: all variants.

Draft email to the PCB designers: `email_draft.txt`.

## Files

```
FABRICATION_P2_B2/
  Gerber/P2_BASKET-F_Cu.gbr             patched
  Gerber/P2_BASKET-B_Cu.gbr             patched
  Gerber/P2_BASKET-F_ENIG_Finition.gbr  patched (drift pad gold)
  Gerber/P2_BASKET-Edge_Cuts.gbr        unchanged copy
  Gerber/P2_BASKET-User_Drawings.gbr    unchanged copy
  NCDrill/P2_BASKET.drl                 patched
  Stack_Up_P2..txt                      unchanged copy
Insulation_masks/V3B_final_B2/
  P2_BASKET-Mask_M1_V3B_final_B2.gbr    patched
  P2_BASKET-Mask_M2_V3B_final_B2.gbr    patched
  P2_BASKET-MeshCut_B2.gbr              new: mesh cut template (whole corner cleared)
QC/qc_report.txt, QC/b2_before_after.png
CHANGES.txt                             the exact edits, one line each
tools/make_b2_files.py                  rebuilds everything above from the originals
tools/qc_b2.py                          checks it
```

**Not copied, because they no longer match the board:**
- the netlists `DummySector0.d356` and `.net`;
- the drill map (`P2_BASKET-drl_map.*`);
- the `Artworks/` PDFs.

If the board house runs an electrical test from the IPC-356 netlist, that file
has to be regenerated: `/Sector0/Sig1` loses its pad, and a new net
`DRIFT_B2` appears.

## Changes (coordinates in mm, board origin = fan apex)

### PCB

| layer | removed | added |
|---|---|---|
| F.Cu | `/Sector0/Sig1` readout pad: its 11.5 × 12 mm zone and its two flashes (Ø0.8, Ø5.0) at (589.183, 10.999) | 3 × 3 mm pad at **(590.5, 10.0)**; 0.3 mm trace from the pad's lower edge to the via; Ø1.0 via pads at (590.5, 7.6) and (626.3, 15.8). Net `DRIFT_B2`. |
| B.Cu | `/Sector0/Sig1`: via pad at (589.183, 10.999), its trace (4 segments up to the via at (619.97, 26.00)), and the teardrop at the pad via | 0.3 mm drift trace (590.5, 7.6) → (600.0, 7.0) → (616.0, 8.5) → (626.3, 15.8); Ø1.0 via pads; GND hatch removed 3.1 mm round the trace and vias (clear polarity) |
| ENIG | – | the 3 × 3 mm drift pad |
| drill | Sig1 pad hole, T2 Ø0.4, at (589.183, 10.999) | two vias, T1 Ø0.4, at (590.5, 7.6) and (626.3, 15.8) |

- **The via at (626.3, 15.8)** sits inside the existing D solder pad, which is
  outside the frame. The drift cable is soldered to D as today.
- **Sig1's connector-side copper stays** (the via at (619.97, 26.00) and the
  short F.Cu trace to the connector). That channel's connector pin is now
  unconnected; check that the readout side is happy with that.

### Insulation masks (dark = open, clear = resist)

| layer | change |
|---|---|
| M1, M2 | Resist island (clear) from (584.6, 4.4) to (595.4, 16.0), with a 3.6 × 3.6 mm window (dark) over the pad. It joins the existing corner border, overlaps the M2 border (which ends at y 4.5) so no open slit is left, and stays clear of the M1 mesh-contact window at x ≥ 595.46. |
| M1, M2 | 2.6 × 2.6 mm window (dark) over the drift pad |

Everything outside the island is identical to V3B_final. That includes the
pillar grid, so the pillar diameter can still be chosen after the test as
planned.

### Mesh

The mesh is laminated last and trimmed at the end. At that trim, **clear the
whole corner** (decided 2026-10-20): no mesh for x ≥ 585.5 and y ≤ 15.0, out to
both frame walls. Two cut lines, see `P2_BASKET-MeshCut_B2.gbr`: up x = 585.5
from the bottom wall to y = 15.0, then along y = 15.0 to the outer-arc wall.

- The two cut edges stay bare. They are **3.5 mm** from the pad edge, which
  keeps 0.5 mm of margin on the 3 mm rule for hand cutting. On the other two
  sides there is no mesh any more.
- The island extends 0.9–1.0 mm beyond the cut lines, so the mesh edge rests on
  resist.
- The mesh-contact pad of this corner, at (595.77, 1.29)–(598.70, 4.10), then
  has **no mesh**, so the whole mesh contact of this corner (pad, trace and
  the two M solder pads) is **removed** in the next PCB: this corner keeps only
  the drift contact. The mesh is contacted at the top corner only. The patched
  Gerbers here still contain it (see `../next_version/data/pcb_corner_A_remove.csv`).
- (Earlier version: a closed 10 × 10 mm square round the pad.)

### Contact to the window, after the bulk process

The choices below follow the CERN outgassing and aging studies (Capeans), and
the CMS GE1/1 GEM chambers, which use spring-loaded pins soldered on the
drift board, inside the gas, to feed their HV.

1. **Pogo pin**, SMT, gold-plated plunger and barrel. Pick a working height
   of 4.0 mm at about mid-stroke, so the pin follows the window when it
   moves with gas overpressure. Use a light force (a few tenths of a newton)
   so it doesn't bulge the window. A rounded plunger tip is better for the
   field than an open coil spring.
2. **Solder it** to the gold pad after the final cure. Dynamask 5000 is a
   solder mask rated for wave, IR and vapour-phase soldering. Use a no-clean
   or rosin flux sparingly, clean the residue with isopropanol, and bake.
   Flux vapours are a known aging source, so don't solder near other open
   detectors.
3. **Landing tab on the window:** about Ø5 mm of 18–35 µm copper (gold-flashed
   if possible), glued onto the aluminium coating with a conductive epoxy
   that was validated in CERN aging tests (Trabond 2902, Silber Leitkleber
   3025, Traduct 2922). This is what the pin presses on. It avoids a pressure
   contact on bare, oxidised aluminium, which risks contact resistance,
   fretting and micro-discharges. It also replaces the adhesive copper tape,
   since adhesive tapes outgas in the CERN tests.
   - Glue it on the mylar sheet before the window goes onto the frame. The
     cure then never involves the frame.
   - Cure fully as the datasheet says. Under-cured epoxy is the main
     outgassing risk.
4. **Avoid:** silicone in any form (conductive elastomers, RTV, grease),
   adhesive tapes, and room-temperature epoxies with known pollutants
   (Araldite AW106 and similar).
5. **First prototype:** keep today's slot wire as a test lead. With the window
   on, measure the resistance from the D pad through the pogo pin and tab to
   the window. Then do a 1 kV hold test and pot the slot.

## Clearances (1 kV rule: at least 3 mm from drift copper to anything else)

Measured by `tools/qc_b2.py` on the patched Gerbers, rendered with their real
polarity:

| from | to | distance |
|---|---|---|
| drift pad / trace / via (F.Cu) | nearest other front copper (the readout pad above) | 5.46 mm |
| drift pad edge | neighbouring readout pads | 5.4 and 5.6 mm |
| drift pad edge | mesh-contact pad | 5.8 mm |
| drift trace / vias (B.Cu) | nearest other back copper | 3.07 mm |
| drift pad edge | bare mesh (the cut edge) | 3.5 mm |

Other QC results:

- The 3.1 mm cut removes GND hatch only: 0 mm² of anything else.
- Both masks pass the strict Gerber syntax check used for V3B_final.
- The island leaves no open slit against the existing resist on either layer.

**Through-board, not through gas:** the 3 × 3 mm pad's top edge is only
**0.24 mm (in plan)** from the readout traces that run on B.Cu under that
corner (Sig2 and its neighbours, from y ≈ 11.7). They are separated by
0.2 mm of FR4. That holds 800 V easily as a dielectric, but it is a
capacitive path from the drift HV into those channels.
- The PCB designers can move those few B.Cu traces 2–3 mm further up under
  the given-up pad, which is easy in KiCad.
- An earlier version of this README gave 2.9 mm here. That figure came from
  an older pad position and was wrong for the 2 × 2 mm pad at (590.5, 9.5),
  which was really about 1.2 mm.

## What this costs

- **One readout channel**, `/Sector0/Sig1`: about 1.4 cm² of the 1738 cm²
  active area. Of that, about 1.2 cm² becomes resist.
- **A bent drift field** around the pogo pin in that corner. It should stay
  mostly inside the given-up pad, but test it.

## For the KiCad project

These Gerbers are a direct edit of the KiCad output, made without the KiCad
source. **Please make the same change in the KiCad project** so that the design
and the board stay in step:

1. Delete pad P1 (`/Sector0/Sig1`): its zone, its via, and the B.Cu trace up
   to the via at (619.97, 26.00).
2. Add net `DRIFT_B2`: the SMD pad (to be matched to the chosen pogo-pin footprint), trace and two vias listed above.
3. Add the B.Cu trace and a 3 mm keep-out in the GND zone along it.
4. Add the pad to the ENIG layer.

## Rebuild

```
cd tools
python3 make_b2_files.py     # writes FABRICATION_P2_B2/, Insulation_masks/V3B_final_B2/, CHANGES.txt
python3 qc_b2.py             # writes QC/
```
