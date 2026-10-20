# P2 basket PCB: items for the next version (Oct 2026)

These are placeholders for the people finalising the next PCB and mask design.
Everything was measured on:
- the current fabrication Gerbers (`Version_Apr26/FABRICATION_P2`);
- the V3B_final masks;
- the drift-frame STL;
- the B2 drift-contact patch (`../drift_pad_B2`).

The page to share is `next_pcb_items.html`, which has drawings for every item.
Nothing in the original folders is modified.

## 0. For the KiCad designer (revision 2026) – start here

Figures and tables only; the changes go into the KiCad project. Made by
`tools/fig_pcb.py` (and `tools/search_inner_marks.py` for the cross positions).

| figure (`figures/`) | what |
|---|---|
| `pcb_overview.png` | the whole board NOW vs NEW: screw holes, connectors to the back, crosses |
| `pcb_corner_A.png` | bottom-right corner: Sig1 → B2 drift pad + trace, mesh corner cleared, M pad |
| `pcb_alignment_marks.png` | bigger crosses; crosses 1 and 2 moved clear of the new screw holes |
| `pcb_connectors_back.png` | FX20-140P connectors move to the back side (pin order mirrors!) |

| table (`data/`) | what |
|---|---|
| `pcb_screw_holes_new.csv` | 39 × Ø3.5, same positions as the frame and carbon back (plated: to decide) |
| `pcb_screw_holes_remove.csv` | today's 40 screw holes; 37 go, 3 corner holes stay |
| `pcb_alignment_marks.csv` | 4 crosses, now / new centres and sizes |
| `pcb_connectors.csv` | the 10 connector centres and angles (same position, now on B.Cu) |
| `pcb_mesh_cut.csv` | the two mesh cut lines of the cleared corner |
| `pcb_corner_A_remove.csv` | corner A mesh contact to remove: mesh pad, trace, 2 M solder pads (F.Cu + ENIG), M2 window |
| `../drift_pad_B2/CHANGES.txt` | every copper / drill / mask edit for the B2 drift pad |

**Insulation masks (made here, not in KiCad):** `Insulation_masks/V3B_final_2026/`
(`P2_BASKET-Mask_M1_2026.gbr`, `..._M2_2026.gbr`, mesh-cut template), made by
`tools/make_masks_2026.py` from V3B_final + B2:
- M1: today's 40 screw-hole openings closed, 39 new Ø4.0 openings;
- M1, M2: alignment crosses 10 mm outline / 1.3 mm arms in 12.5 mm resist
  squares at the new positions (old outlines removed; in M2 the old squares of
  crosses 1, 2 opened again);
- M1, M2: corner-A mesh-contact window closed; B2 drift-pad island and window,
  pillars and everything else unchanged.

`tools/qc_masks_2026.py` compares old and new masks over the whole board: every
changed area is one of these (`QC_masks_2026.txt`, figure `figures/masks_2026.png`);
both files pass `Version_Sept26/tools/validate_gerber.py`. To check: the
12.5 mm squares of crosses 1 and 2 reach r ≈ 113, 3 mm past the frame inner
wall (r 110) but before the pillar field (r ≈ 115).

Decisions (2026-10-20): PCB outline unchanged; corner A keeps only the drift
contact: its mesh contact (mesh pad, trace, the two M solder pads) is removed and
the mesh is contacted only at the top corner (B); mesh corner x ≥ 585.5, y ≤ 15
cleared. Open: plating of the screw holes; Sig1 pin to GND or
floating; symmetric Ø3.2 support holes; the 4 Ø2.2 holes next to the HV pads.

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
  their positions are 3.7–4.2 mm from holes 38 / 39. They move to r = 104.25 mm
  at 47.5° and 12.5° (mirror pair): (70.43, 76.86) and (101.78, 22.56), with
  7.1 mm free round the centre (`data/inner_marks_search.json`). The earlier
  proposal ((73.72, 68.92), (97.50, 29.66)) is dropped.
- **Alternative** if they can't move: an asymmetric cross, with short arms
  towards the slot.

## 2. Bigger mesh-contact pad (bottom corner) – superseded

**2026-10-20:** the whole bottom corner is cleared of mesh (B2 decision), so this
pad would get no mesh: it is removed altogether, with its trace and the two M
solder pads (`data/pcb_corner_A_remove.csv`). The mesh is contacted through the
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
