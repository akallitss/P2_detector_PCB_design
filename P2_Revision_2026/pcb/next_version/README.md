# P2 basket PCB: items for the next version (Oct 2026)

These are placeholders for the people finalising the next PCB and mask design.
Everything was measured on:
- the current fabrication Gerbers (`Version_Apr26/FABRICATION_P2`);
- the V3B_final masks;
- the drift-frame STL;
- the B2 drift-contact patch (`../drift_pad_B2`).

The page to share is `next_pcb_items.html` (state of 2026-10-26: the bigger
crosses at their final positions, and the corner-A drift contact with its edit
table), made by `tools/make_page.py` after `tools/fig_pcb.py`.
Nothing in the original folders is modified.

## 0. For the KiCad designer (revision 2026) – start here

Figures and tables only; the changes go into the KiCad project. Made by
`tools/fig_pcb.py`, `tools/fig_pcb_holes.py` (screw holes) and
`tools/search_inner_marks.py` (cross positions).

| figure (`figures/`) | what |
|---|---|
| `pcb_overview.png` | the whole board NOW vs NEW: screw holes, connectors to the back, crosses |
| `pcb_screw_holes.png` | screw holes NOW → NEW: today's holes (plated / not) with the 25 that go crossed out; the new 37, KEEP (15, grey) and ADD (22, white), numbered as the frame and carbon back |
| `pcb_screw_holes_unrolled.png` | the same, edge by edge: today's holes (plated / not) above, the new pattern below, with spacings |
| `pcb_corner_A.png` | bottom-right corner NOW → NEW: Sig1 removed, drift pad at the corner centre fed by today's mesh line into one big D pad (the old M + D pads), top GND pad removed, mesh corner cleared |
| `pcb_corner_A_steps.png` | the same, step by step: 1 Sig1, 2 mesh contact, 3 HV pads (top GND and the M / top GND texts removed, M + D merged into one D pad), 4 drift pad and line |
| `pcb_alignment_marks.png` | crosses 1 and 2 (inner arc), NOW → NEW: bigger, moved clear of the new screw holes |
| `pcb_alignment_marks_outer.png` | crosses 3 and 4 (outer arc), NOW → NEW: same place, 9 mm copper cross, 10 mm mask outline in a 12.5 mm resist square, with the clearances |
| `pcb_connectors_back.png` | FX20-140P connectors move to the back side (pin order mirrors!) |

| table (`data/`) | what |
|---|---|
| `pcb_screw_holes.csv` | every screw hole with its action: KEEP 15 (today's hole, unchanged: the 13 on the outer arc, which sit between the signal lines, and the 2 inner corners), REMOVE 25, ADD 22 (Ø3.5, equal pitch between the corners: bottom side 46.5 mm, top side 46.0 mm, inner arc 38.7 mm; plating to decide). 37 holes in the end, same positions as the frame and carbon back |
| `pcb_alignment_marks.csv` | 4 crosses, now / new centres and sizes |
| `pcb_connectors.csv` | the 10 connector centres and angles (same position, now on B.Cu) |
| `pcb_mesh_cut.csv` | the two mesh cut lines of the cleared corner |
| `pcb_corner_A_drift.csv` | corner A, every edit in the order of the steps: remove Sig1 (connector pin left floating), the mesh pad and the line's first stub, the top GND pad and the M / top GND copper texts; merge the 2 M + 2 D pads into one D pad (corners given); add the drift pad (592.75, 7.5) and a 0.8 mm segment to the line's bend; 3 mm GND keep-out; mask windows |
| `../drift_pad_B2/CHANGES.txt` | the Sig1 removal (the rest of that first B2 patch is not used, see below) |

**Insulation masks (made here, not in KiCad):** `Insulation_masks/V3B_final_2026/`
(`P2_BASKET-Mask_M1_2026.gbr`, `..._M2_2026.gbr`, mesh-cut template), made by
`tools/make_masks_2026.py` from V3B_final + B2:
- M1: the openings of the 25 screw holes that go are closed, 22 new Ø4.0
  openings; the 15 kept holes keep today's openings (QC: unchanged);
- M1, M2: alignment crosses 10 mm outline / 1.3 mm arms in 12.5 mm resist
  squares at the new positions (old outlines removed; in M2 the old squares of
  crosses 1, 2 opened again);
- M1, M2: corner-A mesh-contact window closed; the 3.6 × 3.6 mm drift-pad window
  moved to the new pad (592.75, 7.5), inside the unchanged B2 resist island;
  pillars and everything else unchanged. Mesh-cut template: same cut lines, pad
  marker moved.

`tools/qc_masks_2026.py` compares old and new masks over the whole board: every
changed area is one of these (`QC_masks_2026.txt`, figure `figures/masks_2026.png`);
both files pass `Version_Sept26/tools/validate_gerber.py`. To check: the
12.5 mm squares of crosses 1 and 2 reach r ≈ 113, 3 mm past the frame inner
wall (r 110) but before the pillar field (r ≈ 115).

Decisions (2026-10-20): PCB outline unchanged; the mesh is contacted only at the
top corner (B); mesh corner x ≥ 585.5, y ≤ 15 cleared.

Decision (2026-10-26), corner A drift contact: the drift pad (3 × 3 mm) sits at
the centre of the cleared corner, (592.75, 7.5), and is fed on F.Cu by today's
mesh line: a 0.8 mm segment from the pad to the line's bend (599.58, 6.13), then
the line as it is to the HV solder pads. Removed: Sig1 (pad, via, B.Cu trace; its
connector pin stays, floating), the mesh pad and the line's first stub.

Decision (2026-10-28), HV solder pads: the two M and the two D pads merge into
one bigger pad, labelled D (8.38 × 6.86 mm, the envelope of the four; outer side
at the board edge as today), for the drift cable. The top GND pad and its copper
text go, and the copper text "M" goes; the "D" text stays. The bottom GND pad
stays, 3.26 mm from the D pad. The masks have nothing over these pads. The
first B2 patch's pad at (590.5, 10.0), its two vias and the B.Cu route are not
used: no drift copper on the back, so nothing to insulate under the carbon back.
Clearances: 5.75 mm to the bare mesh, 7.8 mm to the nearest readout pad, 2.9 mm
in plan to the B.Cu readout traces (was 0.24 mm). Today the mesh line is only
0.5 mm from the F.Cu GND pour: pull the pour back to 3 mm round the whole drift
net. The foam slot of the frame is centred on the new pad
(`../../mechanics/figures/foam_slot_*.png`). Open: plating of the new screw holes; symmetric Ø3.2
support holes; the 4 Ø2.2 holes next to the HV pads.

## 1. Bigger alignment crosses

**Today:**
- 4 crosses, each 3 × 3 mm with 0.12 mm lines, on F.Cu and B.Cu at the same
  positions.
- The M1/M2 masks have a rounded cross outline at the same positions (2.9 mm
  across, 1.16 mm arms), inside a resist square: 10 × 10 mm (outer) or about
  6 × 6 mm (inner).

| # | centre (mm) | where | max copper arms (1 mm clear) | max resist square | limited by |
|---|---|---|---|---|---|
| 1 | (70.80, 66.19) | inner arc, under the frame | 1.3 mm towards the board-edge slot, 17–21 mm otherwise | – | board-edge slot, 2 mm away |
| 2 | (93.67, 28.50) | inner arc, under the frame | 1.9 mm towards the slot, 7–21 mm otherwise | – | board-edge slot, 2.9 mm away |
| 3 | (635.63, 83.91) | outer arc, between connectors 1 and 2 | 9.2–10.4 mm | 12.9 mm | slot, connector vias and pads |
| 4 | (391.22, 507.00) | outer arc, between connectors 9 and 10 | 7.5–13.8 mm | 12.6 mm | a via below, the board edge |

The GND hatch is not counted as a limit, because it can be re-poured around a
bigger cross.

**Proposal, the same at all four positions:**
- **Copper:** a cross 9 mm across (4.5 mm arms) with 0.3 mm lines.
- **Masks:** a cross outline 10 mm across with 1.3 mm arms, in a
  12.5 × 12.5 mm resist square.
- **Crosses 3 and 4** stay where they are.
- **Crosses 1 and 2** (superseded 2026-10-20): with the new screw-hole pattern
  their positions are 3.7–4.2 mm from the new inner-arc holes. They move to r = 104.25 mm
  at 47.5° and 12.5° (mirror pair): (70.43, 76.86) and (101.78, 22.56), with
  7.1 mm free round the centre (`data/inner_marks_search.json`). The earlier
  proposal ((73.72, 68.92), (97.50, 29.66)) is dropped.
- **Alternative** if they can't move: an asymmetric cross, with short arms
  towards the slot.

## 2. Bigger mesh-contact pad (bottom corner) – superseded

**2026-10-20:** the whole bottom corner is cleared of mesh (B2 decision), so this
pad would get no mesh: it is removed altogether, with its trace and the two M
solder pads. **2026-10-26:** the line and the M pads are kept as the drift feed
(`data/pcb_corner_A_drift.csv`). The mesh is contacted through the
existing pad at the top corner; no bigger pad is needed. The study below is kept for reference.

**Today:**
- The gold pad is 2.93 × 2.81 mm, from (595.77, 1.29) to (598.70, 4.10).
- The mesh touches it only through the 2.0 × 2.0 mm M2 window,
  (595.82, 2.15)–(597.82, 4.15). V3B_final did not enlarge this window.
- The mesh is trimmed about 1.9 mm from the frame wall, so it covers the pad
  only at x ≤ 598.1 and y ≥ 1.9.

**Next to the B2 drift pad** (3 × 3 mm at (590.5, 10.0)):
- **Rule:** 3 mm from bare mesh potential to bare drift potential.
- **Placement:** the pad must stay outside the B2 mesh cut (585.5–595.5,
  5.0–15.0) and the resist island (584.6–595.4, 4.4–16.0).

| option | corners (mm) | to drift pad | pad area the mesh can reach | masks |
|---|---|---|---|---|
| today | (595.77, 1.29)–(598.70, 4.10) | 5.8 mm | 5.1 mm² | window 2 × 2 |
| **A 5.0 × 3.0** | (593.70, 1.29)–(598.70, 4.29) | 4.5 mm (4.2 mm vertically) | 10.5 mm² | window ≈ (593.9, 2.0)–(598.0, 4.2); B2 island untouched |
| B 3.7 × 3.7 | (595.00, 1.29)–(598.70, 5.00) | 4.6 mm | 9.6 mm² | 0.4 × 0.6 mm notch in the B2 island |
| largest | (594.50, 1.29)–(598.70, 5.50) | 3.9 mm | ≈ 12.5 mm² | overlaps the B2 mesh cut; not recommended |

**Proposal: option A.**
- The nearest other front copper stays the GND hatch beyond the wall, at
  1.25 mm, the same as today.
- **Without B2**, readout pad `/Sector0/Sig1` is only 0.9 mm away, so the mesh
  pad can't grow.
- **Top corner:** its pad is already 3.9 × 3.9 mm, but it is 1.6 mm from
  `/Sector9/Sig128` and 1.3 mm from the active edge, so it can't grow there.

## Files

```
next_pcb_items.html        the page to share (self-contained)
data/alignment_marks.json  per-cross limits at today's positions
data/alignment_fit.json    proposed centres and the largest resist square
figures/alignment_*.png    QC pictures of the free space round each cross
tools/alignment_marks.py   finds the crosses, measures the free space
tools/fit_marks.py         largest square / cross at the proposed centres
tools/make_page.py         builds the page (uses page_template.html)
```
