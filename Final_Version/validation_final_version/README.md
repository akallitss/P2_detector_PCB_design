# Validation of the final version: final PCB on the final drift frame

Only the files in `Final_Version/` are used:

| part | file |
|---|---|
| PCB (Nov 2026, designer) | `PCB-Nov2026/K55V1/_FABRICATION/` — `NCDRILL/P2_V1.drl`, `GERBER/P2_V1-{Edge_Cuts,Top,Bottom,ENIG}.gbr` |
| drift frame | `drift_frame/P2_Frame_V3.dxf` |

How the two are put on top of each other (no fit, no adjustment):
- PCB: the Gerbers are relative to the origin in their header (`TF.SameCoordinates`,
  236.876 / 648.163 mm). The drill file is in KiCad page coordinates and is shifted by that origin.
  The centre of the arcs is then at (0, 0).
- Frame: all arcs in the DXF share the centre (80.572, 41.301). It is moved to (0, 0), with no rotation.
- The 4 inner-arc holes then coincide within 0.02 mm, which confirms the registration.

## Figures (`figures/`)

| file | what it shows |
|---|---|
| `0_steps.png` | 4 steps: 1 the PCB alone → 2 the frame alone → 3 frame laid on the PCB → 4 which holes line up |
| `1_holes_unrolled.png` | every screw hole along each edge, PCB row above the frame row, with the shift to the nearest frame hole in mm |
| `2_holes_zoom.png` | 8 true-size zooms (corners, sides, arcs) |
| `3_signal_lines.png` | signal lines (F.Cu orange, B.Cu purple) under the frame walls and holes |
| `4_hv_corners.png` | corner A (drift contact → D pad) and corner B (mesh contact, M pad) against the frame |
| `5_requested_vs_v3.png` | frame V3 on the final PCB: the missing extension, and the side wall widths measured |

Each figure also exists in French: `*_fr.png`.

Tables (`data/`): `holes_pcb_vs_frame.csv` (every PCB hole and its nearest frame hole),
`frame_holes_vs_signal.csv` (for every hole: the signal tracks it would cut, or its clearance to them).

## Result (10 Nov 2026)

**Screw holes do NOT match.** PCB: 38 × Ø3.5 (plated). Frame V3: 39 × Ø3.5.
Only 8 line up (centres < 0.1 mm apart):

- the 4 inner-arc holes (inner corners included): OK.
- 3 outer-arc holes: (317.71, 521.29), (528.71, 305.25), (610.30, 14.50).
- 1 on the top side, (182.14, 330.45), at 0.09 mm. This is a coincidence where the two patterns cross.

The rest of the pattern differs:
- Each part is symmetric about the 30° axis, but they start from different corner holes.
  - PCB: keeps the bottom-right corner (610.43, −6) and mirrors it to the top, at (300.02, 531.67).
  - Frame: keeps today's top corner (297.52, 527.32) and mirrors it to the bottom right, at (605.44, −6).
  - The corner holes are therefore 5 mm apart.
- Straight sides: the PCB has an equal pitch of 42.6 mm (bottom) and 45.6–47.3 mm (top). The frame
  has 49.6 mm, with a 30 mm first gap. Shifts go up to 22 mm.
- Outer arc: the PCB keeps today's 13 holes, which sit between the signal lines (pitch 20.5–66.9 mm).
  The frame has 13 holes at an equal 50.9 mm pitch. **10 of the 39 frame holes sit on signal
  tracks** (up to 16 tracks per hole), so the PCB cannot be drilled there. All 38 PCB holes are
  ≥ 0.82 mm from any track.

**Frame outline:** outer edge R615, no extension behind the connectors (the PCB goes to R650).
The 44 connector-support holes (Ø2.2 / Ø3.2) have no frame under them. The frame overhangs the PCB
by 2 mm on the bottom side (frame y = −12, PCB edge y = −10).

**Extension missing** (`5_requested_vs_v3.png`, script `fig_requested_vs_v3.py`; the extension
asked for comes from `P2_Revision_2026/mechanics/tools/rev_geometry.py`):

| asked in the revision | frame V3 |
|---|---|
| extension behind the connectors, 8 mm high, out to the PCB edge R650 | **missing**: ends at R615 (35 mm short) |
| 40 connector-support holes in the extension | **missing** |
| HV openings at corners A and B | none; not needed without the extension |
| 37 screw holes (pattern above) | 39 holes, a different pattern (see above) |

Side walls (for information; the +1.5 mm in the revision was only an illustration, not a
requirement). Measured from the window edge:
- straight sides: PCB edge 10.0, V3 12.0, so V3 is 2.0 mm past the PCB edge;
- inner arc: PCB edge 15.0–15.1 (the PCB arc is not quite concentric), V3 15.0, so flush with it.

The wall left past an M3 head (Ø5.5) on the screw line is 1.75 mm on all three sides.

Not checkable in the 2D DXF: the removed drift-wire slot, the foam slot at corner A, gas bores, the
8 mm height.

**HV / contacts:**
- D pad (drift HV, corner A) and M pad (mesh HV, corner B): outside the frame, 6.0 / 6.2 mm from
  its outer edge. No opening is needed in V3.
- Drift contact pad 3 × 3: at (589.18, 11.0), not at (592.75, 7.5) as in our instructions. It is
  inside the window, 9.2 mm from the wall.
- Mesh contact pad (4.07 square, centre (300.72, 516.72)): in the window, but its top tip
  (0.19 mm², 1 %) is under the corner of the frame window.

## Running

```
cd tools
(ulimit -v 2500000; ~/miniconda3/bin/python3 fig_validation.py)        # figures 0-4, ~0.3 GB peak, 5 s
(ulimit -v 2500000; ~/miniconda3/bin/python3 fig_requested_vs_v3.py)    # figure 5
```
French figures (`*_fr.png`, next to the English ones): run the same two lines with `P2_LANG=fr`
in front. The texts are in `tools/i18n_fr.json`: exact strings, plus regex rules for the labels
with numbers; decimal points become commas. `P2_LANG=collect` lists every text drawn
(`i18n_strings.json`). When a text changes, update the table; the run prints any text left
without a translation.
`final_geometry.py` reads the files. The copper is cached once in `data/copper_cache.pkl`
(35 MB, not tracked); delete it if the Gerbers change.
