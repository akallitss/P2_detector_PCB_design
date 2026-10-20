# P2 basket PCB: items for the next version (Oct 2026)

These are placeholders for the people finalising the next PCB and mask design.
Everything was measured on:
- the current fabrication Gerbers (`Version_Apr26/FABRICATION_P2`);
- the V3B_final masks;
- the drift-frame STL;
- the B2 drift-contact patch (`../drift_pad_B2`).

The page to share is `next_pcb_items.html`, which has drawings for every item.
Nothing in the original folders is modified.

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
- **Crosses 1 and 2** move 4 mm radially outward, away from the slot:
  (70.80, 66.19) → (73.72, 68.92) and (93.67, 28.50) → (97.50, 29.66).
- **Alternative** if they can't move: an asymmetric cross, with short arms
  towards the slot.

## 2. Bigger mesh-contact pad (bottom corner)

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
