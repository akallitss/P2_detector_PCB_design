# P2 Micromegas revision (Oct 2026): drawings for the technicians

Schematic NOW → NEW figures explaining the changes listed in
`../P2 Micromegas Revision.pdf` (untracked, like all PDFs), for the technicians who
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
| B2 drift pad / mesh cut | `../pcb/drift_pad_B2/README.md` |
| connector | `Version_Apr26/FX20-60P-0.5SV15_..._Catalog_D49373_en.pdf` |

## Decisions (agreed with the physicist)

**PCB outline unchanged.** The carbon back keeps the PCB outline.

**Drift frame**
- Wider by 1.5 mm outward on both straight sides and the inner arc (decided
  2026-10-28): straight sides 10 → 11.5 mm (edge y = −11.5), inner arc
  15 → 16.5 mm (edge r = 93.5). The PCB outline does not change, so the frame
  overhangs the PCB (and the carbon back) by 1.5 mm on these three sides; it is
  the outermost part there. At corner A the chamfer line is simply continued
  down to y = −11.5. Screw-hole lines unchanged. The inner gas-inlet bore gets
  1.5 mm longer (it now leaves the frame at x = 93.5). M3 heads on the straight
  sides now sit 1.25 mm inside the frame edge; the nuts stay 0.25 mm past the
  carbon-back edge but inside the frame outline.
- Extension behind the connectors, full frame height (8 mm), out to the PCB
  edge (R650). The connectors move to the back of the PCB.
- 40 connector-support holes in the extension, at the PCB positions
  (Ø2.2 / Ø3.2 as on the PCB; final Ø for the clips: designer).
- HV openings at both outer corners: HV pads + 3 mm, from the PCB edge down to
  the frame wall (r 615). Opening B (top) also keeps the top gas inlet free.
- Old drift-wire slot (bottom-right) removed: filled with frame material.
- Screw holes: 37 × Ø3.5, all not threaded (one kind everywhere).
  - Outer arc: today's 13 positions are kept, corners included (decided
    2026-10-28): they sit between the signal lines on the PCB. No holes are
    added there. The 6 that are Ø3.0 threaded today become Ø3.5 not threaded.
  - Straight sides and inner arc: equal pitch between the 4 corner holes, which
    all stay where they are. Bottom side 46.5 mm, top side 46.0 mm (the top
    corner is 5 mm in for the gas inlet, so the two sides are not mirror images
    any more), inner arc 38.7 mm.
  - Hole lines unchanged: straight sides y = −7.5, inner arc r = 99.5 (O-ring
    groove), outer arc r = 610.5. Outer arc hole to the Ø2 bore in the STEP:
    1.25 mm (1.50 mm today with Ø3.0).
- O-ring groove untouched. HV filter box: no room on the extension, placed
  elsewhere. 5 mm drift gap: placeholder (step at z = 5, frame 9 mm).

**Carbon drift piece** (5 mm strip on the z = 4 step, mylar glued under it)
- Thickness 2 mm; outline unchanged.
- Flap at the B2 drift-pad corner, x 585.5–597.5, y 2.5–15.0, pressing the
  mylar onto a conductive-foam column.
- Foam MECF-010P (1 mm sheets): 4 × 4 mm, 5 sheets for 4 mm (20 %), 6 sheets
  for the 5 mm placeholder (17 %); recommended 15–30 %.
- Mesh: the whole corner is cleared (no mesh for x ≥ 585.5, y ≤ 15). The
  bottom-corner mesh-contact pad then has no mesh: to solve in the PCB step.

**Foam slot in the frame** (proposed 26 Oct after a colleague's comment on the
drawings: "add slot in 3D at lower drift level for conductive foam + matching
size on carbon frame"; replaces the guide ring of the 20 Oct figures if agreed)
- Drift frame: the lower level (z 0–4, below the mylar step) is filled in the
  cleared corner, x 585.5 → lower wall (14.5 mm), y 0 → 15, top flush with the
  step. One piece with the frame.
- Slot 4.4 × 4.4 through it (z 0–4), centred on the drift pad, which moves to
  the centre of the corner (592.75, 7.5) (decided 26 Oct, see
  `pcb/next_version`); corners R0.5 (tool); walls 5.05 mm (x) and 5.3 mm (y)
  on every side.
  The foam (4 × 4, 5 sheets) stands 1 mm above the block before assembly.
- Carbon flap: same outline as the block (x = 585.5, y = 15, out to the
  strip), so it rests on the block everywhere with the mylar clamped in
  between; it is no longer pushed up by the foam.
- Figures `foam_slot_1_frame_B2` (top view, dimensions), `foam_slot_2_3d`,
  `foam_slot_3_section` (A–A, B–B), `foam_slot_4_carbon_flap` (before/new).
- To check: frame glue must not run into the slot (it would insulate the
  pad); the block edges sit on the mesh-cut lines, while elsewhere the mesh
  stops 1.9 mm from the walls (enlarge the cut to x ≥ 583.6, y ≤ 16.9?).

**Carbon back**
- Thickness 3 mm; outline = PCB outline; window unchanged.
- Extension removed: outer edge r = 616.9, 10 mm before the connector pads.
- 37 × Ø3.5, same pattern as the frame (outer arc: today's positions). Screws M3 × 16: head on the frame,
  washer + nut on the carbon side.
- "#" ribs across the window: principle only (designer chooses).
- No drift copper on the back any more (26 Oct: the drift is fed on the front
  by today's mesh line), so nothing to insulate under the carbon.
- Straight-side hardware: the M3 nut (AF 5.5) is 0.25 mm wider than the
  2.5 mm strip to the carbon-back edge, but stays 1.25 mm inside the widened
  frame's outline; an M2.5 nut would be flush.

## Running

```
cd tools
(ulimit -v 3000000; python3 fig_current_state.py)   # today's parts
(ulimit -v 3000000; python3 fig_frame_corners.py)   # frame corners A, B
(ulimit -v 3000000; python3 fig_frame_holes.py)     # frame overview, holes, CSVs
(ulimit -v 3000000; python3 fig_frame_section.py)   # frame cross-sections
(ulimit -v 3000000; python3 fig_carbon.py)          # carbon drift piece
(ulimit -v 3000000; python3 fig_carbon_back.py)     # carbon back, screws
(ulimit -v 3000000; python3 fig_foam_slot.py)       # foam slot in the frame + matching flap
python3 check_holes.py                              # hole clearances
```

All design parameters are in `tools/rev_geometry.py`. The figures go to
`figures/` (not tracked), the hole tables to `data/`.

The scripts read `../drift_contact/data/cache.pkl` (made by
`drift_contact_study.py`). `data/frame_slices.json` and
`data/frame_section_r27.json` are extracted from the STEP with FreeCAD:

```
freecad.cmd -c "$(cat export_frame_slices.FCpy)" | grep '^JSON' | cut -c5- > ../data/frame_slices.json
freecad.cmd -c "$(cat export_radial_section.FCpy)" | grep '^JSON' | cut -c5- > ../data/frame_section_r27.json
```

**Keep the `ulimit`:** drawing every PCB copper polygon uncropped needs more
RAM than the 14 GB machine has. The scripts crop the copper to each zoom window.
Python 3 with `numpy`, `matplotlib`, `shapely`, `gerbonara`, `ezdxf`.
