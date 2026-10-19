# P2 Micromegas revision (Oct 2026): drawings for the technicians

Schematic NOW → NEW figures explaining the changes listed in
`P2_detector_PCB_design/P2 Micromegas Revision.pdf`, for the technicians who
will redraw the real parts (Solid Edge). The figures are explanations, not
manufacturing drawings: the designer checks the final positions.

All geometry is in the shared PCB / frame coordinates (fan apex at the origin,
mm; z = 0 is the frame face on the PCB). Everything is measured from the
original files, nothing in them is modified.

| input | file |
|---|---|
| drift frame | `DRIFT_P2_261124/DRIFT_P2_261124/FRAME_4mm/P2_Frame_V2.0.stp` |
| carbon parts | `carbon-frame/DECOUPE_CARBON_07_24.dxf` (blocks SE1 = carbon back, SE2 = carbon drift piece) |
| PCB | `Version_Apr26/FABRICATION_P2/Gerber`, `NCDrill/P2_BASKET.drl` |
| B2 drift pad / mesh cut | `B2_DriftPad_Oct26/README.md` |
| connector | `Version_Apr26/FX20-60P-0.5SV15_..._Catalog_D49373_en.pdf` |

## Decisions (agreed with the physicist)

**PCB outline unchanged.** The frame stays flush with the PCB on the straight
sides and the inner arc (nothing may stick out in the basket).

**Drift frame**
- Extension behind the connectors, full frame height (8 mm), out to the PCB
  edge (R650). The connectors move to the back of the PCB.
- 40 connector-support holes in the extension, at the PCB positions
  (Ø2.2 / Ø3.2 as on the PCB; final Ø for the clips: designer).
- HV openings at both outer corners: HV pads + 3 mm, from the PCB edge down to
  the frame wall (r 615). Opening B (top) also keeps the top gas inlet free.
- Old drift-wire slot (bottom-right) removed: filled with frame material.
- Screw holes: 39 × Ø3.5 (not threaded), equal pitch, mirror-symmetric about
  30° (straight sides 46.0 mm, outer arc 46.7 mm, inner arc 38.7 mm). The
  bottom-right corner hole moves 5 mm inward to mirror the top one (the top one
  is fixed by the gas inlet). Straight sides y = −7.5 and inner arc r = 99.5 stay
  on today's lines (O-ring groove); outer arc r 610.5 → 613.
- O-ring groove untouched. HV filter box: no room on the extension, placed
  elsewhere. 5 mm drift gap: placeholder (step at z = 5, frame 9 mm).

**Carbon drift piece** (5 mm strip on the z = 4 step, mylar glued under it)
- Thickness 2 mm; outline unchanged.
- Flap at the B2 drift-pad corner, x 585.5–597.5, y 2.5–15.0, pressing the
  mylar onto a conductive-foam column.
- Foam MECF-010P (1 mm sheets): 4 × 4 mm, 5 sheets for 4 mm (20 %), 6 sheets
  for the 5 mm placeholder (17 %); recommended 15–30 %. Held by an insulating
  guide ring glued on the PCB (1 mm wall, 3 mm high).
- Mesh: the whole corner is cleared (no mesh for x ≥ 585.5, y ≤ 15). The
  bottom-corner mesh-contact pad then has no mesh: to solve in the PCB step.

**Carbon back**
- Thickness 3 mm; outline = PCB outline; window unchanged.
- Extension removed: outer edge r = 616.9, 10 mm before the connector pads.
- 39 × Ø3.5, same pattern as the frame. Screws M3 × 16: head on the frame,
  washer + nut on the carbon side.
- "#" ribs across the window: principle only (designer chooses).
- Placeholders: insulation of the B2 drift trace (back copper) under the
  carbon; straight-side hardware (an M3 head/nut is 0.25 mm wider than the
  2.5 mm strip to the PCB edge, as today).

## Running

```
cd tools
(ulimit -v 3000000; python3 fig_current_state.py)   # today's parts
(ulimit -v 3000000; python3 fig_frame_corners.py)   # frame corners A, B
(ulimit -v 3000000; python3 fig_frame_holes.py)     # frame overview, holes, CSVs
(ulimit -v 3000000; python3 fig_frame_section.py)   # frame cross-sections
(ulimit -v 3000000; python3 fig_carbon.py)          # carbon drift piece
(ulimit -v 3000000; python3 fig_carbon_back.py)     # carbon back, screws
python3 check_holes.py                              # hole clearances
```

All design parameters are in `tools/rev_geometry.py`. The figures go to
`figures/` (not tracked), the hole tables to `data/`.

The scripts read `Drift_Contact_Oct26/data/cache.pkl` (made by
`drift_contact_study.py`). `data/frame_slices.json` and
`data/frame_section_r27.json` are extracted from the STEP with FreeCAD:

```
freecad.cmd -c "$(cat export_frame_slices.FCpy)" | grep '^JSON' | cut -c5- > ../data/frame_slices.json
freecad.cmd -c "$(cat export_radial_section.FCpy)" | grep '^JSON' | cut -c5- > ../data/frame_section_r27.json
```

**Keep the `ulimit`:** drawing every PCB copper polygon uncropped needs more
RAM than the 14 GB machine has. The scripts crop the copper to each zoom window.
Python 3 with `numpy`, `matplotlib`, `shapely`, `gerbonara`, `ezdxf`.
