# P2 basket — drift (window) HV contact: design options (Oct 2026)

How to replace the copper-tape-and-wire drift contact with a robust one,
without losing active area and without bringing drift potential close to the
mesh.

**Easier to read:** open `drift_contact.html` in a browser. It has the same
content with vector drawings (built by `tools/make_page.py`).
`conceptB_3d.html` is an interactive 3D model of concept B at the inner corners
(`tools/make_conceptB_3d.py`). The proposed new parts are in
`cad/conceptB_inner_left_parts.step`, in frame coordinates.

Nothing in the original drawing folders is modified. Everything here is
measured from them by `tools/drift_contact_study.py` (numbers in
`data/results.json`, figures in `figures/`).

| input | file |
|---|---|
| drift frame | `DRIFT_P2_261124/DRIFT_P2_261124/FRAME_4mm/P2_Frame_V2.0.stl` (+ `.stp` for hole axes) |
| PCB | `Version_Apr26/FABRICATION_P2/Gerber/*.gbr`, `NCDrill/P2_BASKET.drl` |
| insulation mask | `Version_Sept26/Insulation_masks/V3B_final` (V1 frame) |
| resist | `Dynamask+5000+Preliminary+TDS(840+E)+2024.pdf` |

The frame and the PCB share one coordinate system (fan apex at the origin, mm).
z = 0 is the frame face that sits on the PCB.

---

## 1. Constraints

* **Voltages:** mesh ≈ 450 V and drift ≈ 800 V, so about 350 V between them in
  normal running. **Clearances are sized for 1 kV.** That covers drift on with
  the mesh tripped, and HV ramps.
* **Clearance rule used here:** at least **3 mm** between any bare
  drift-potential metal and any bare mesh, through gas or along a surface.
  Resist-covered mesh does not count. Cured Dynamask is rated **1.8 kV/mil**
  (≈ 5 kV across 75 µm D5030), so the mesh under the frame resist is
  insulated with a wide margin.
* **Active area is fixed:** 1738.5 cm² (V3B_final, V1 frame). Nothing may move
  the pillar-field edge.
* **Process:** the 0.2 mm PCB goes through the laminator on a metal carrier
  plate, then gets a 150 °C / 1 h cure. Anything that stands proud of the
  board (springs, pins) can only be fitted **after** the bulk is finished.

## 2. What the drawings say

![overview](figures/fig1_overview.png)

**Frame (8 mm tall)**
* 10 mm wide wall with an O-ring dovetail on the bottom face (z 0–2.4).
* On the inner top edge: a **3 mm wide ledge at z = 4.0**, where the mylar is
  glued. That gives the 4 mm drift gap.
* **Gas** is already distributed by the frame. There are Ø4.4 mm ports at the
  top corner (302, 529) and the inner-bottom corner (92, 0), internal channels
  along both arcs, and **26 Ø0.6 mm nozzles at z = 3** (17 on the outer arc,
  9 on the inner arc).
* **Wire slot:** a single 2.5 × 1.2 mm slot through the outer-arc wall at the
  bottom-right corner (x 600–615, y 2.3–4.8, z 2.6–3.8). It runs directly
  under the ledge; **the roof between slot and ledge is only 0.2 mm thick**.

**PCB**
* Each outer corner carries **GND / M / D / GND** HV solder pads. M is routed
  to the gold mesh pad: 2.9 × 2.8 mm at the bottom, 3.9 × 3.9 mm at the top.
* **D has no via and no trace.** It is a solder pad only, and it sits outside
  the frame.
* The first readout pad is **5.0 mm** from the frame inner wall on every edge.

**Mask**

| | V3B_final (V1 frame) | V2 (in use now) |
|---|---|---|
| frame inner wall → active edge | 4.79 – 5.00 mm | 12.3 mm |
| active area | 1738.5 cm² | 1615.3 cm² |

**Today's contact:** where the drift wire leaves the slot it is **2.82 mm**
from the bare mesh pad, which is already below the 3 mm rule.

---

## 3. Options

### A — Contact inside the glue joint, fed through the existing slot  ★ recommended

No PCB change, no mask change. One Ø1.2 hole in the frame.

![concept A](figures/fig2_conceptA_bottom_right.png)

1. Drill **Ø1.2 mm** vertically from the ledge into the slot at
   **(601.5, 3.55)**, through the 0.2 mm roof. Deburr.
2. Run the HV wire through the slot from the outside, as today. Strip it so
   only the bare conductor goes up the hole; the insulation ends inside the
   slot.
3. Solder the conductor to a **copper foil tab, 2 × 6 mm, 35–50 µm thick**,
   laid along the ledge (x 600.4–602.4, y 1–7). Fill the hole with
   room-temperature-curing silver epoxy.
   - Keep the tab at most 2 mm wide so ≥ 1 mm of the 3 mm glue land stays
     continuous.
   - Keep every cure step ≤ 60 °C, because of the frame plastic.
4. Glue the mylar as usual, with a dab of silver epoxy on the tab only. The
   coated face goes down, onto the tab.
5. **Pot the slot with epoxy** from the outside. This buries the wire, closes
   the leak path, and raises the 2.82 mm bare-wire spacing to "no bare metal
   below the window".
6. Solder the wire to **D** as today.
7. QC:
   - Resistance from the D pad to the window surface.
   - 1 kV drift-to-mesh hold test before the detector is closed.
   - Leak test.

**Why A:**
* The contact sits at z = 4, where the window already sits, so it adds no new
  field near the mesh.
* It is clamped and sealed, nothing in the active area moves, and it works on
  the frames that already exist.

**Limits:**
* There is still one contact per detector. Redundancy needs A2.
* The coated face of the mylar must face the PCB.

### A2 — Second drift feed (redundancy, frame revision)

![second feed](figures/fig4_second_drift_feed.png)

* **Top corner: not possible.** A slot mirrored from the bottom one would cut
  the outer-arc gas channel that starts at the top gas port. The study finds
  8 frame surfaces inside it; the existing slot has 0.
* **Bottom straight wall at x = 575: clean.**
  - The slot cuts solid frame only.
  - It sits between the screws at x = 537.3 and 592.3.
  - Its mouth is **5.41 mm** from bare mesh.
  - Same section as today's slot (z 2.6–3.8, above the dovetail with a
    0.2 mm web), plus a Ø1.2 hole up to the ledge at (575, −1.5).
  - Along the bottom the frame is flush with the board edge, so the wire runs
    along the frame's outer face to the same D pad.
  - On existing frames, a Ø1.2 mm horizontal hole at z = 3.2 does the same job.

### B — Drift pad on the PCB + spring contact (PCB re-spin)

![concept B](figures/fig3_conceptB_inner_corners.png)

A Ø2 mm gold pad pushes a ~4 mm spring or pogo contact up onto the window,
next to the wall.

**Where it fits under the 1 kV rule** (pad edge to nearest bare mesh, with the
pad centre at least 1.5 mm from the wall):

| place | best pad edge → bare mesh |
|---|---|
| straight edges, arcs, both outer corners | 2.2 – 2.5 mm ✗ |
| inner-bottom corner (111.6, 1.6) | 3.49 mm ✓ (but sits in front of the Ø4.4 gas port) |
| inner-left corner (57.2, 95.8) | 3.54 mm ✓ |

**What B needs:**
* A new pad, and a way to feed it. Either route D on B.Cu from the
  outer-corner HV pads (about 0.5 m), or add a separate HV entry pad near the
  inner arc. There the board extends 0–11 mm beyond the frame (polygonal board
  edge against the round frame), so local room has to be checked.
* A window in M1/M2 and a hole in the mesh cut *before* M2, so the mesh edge
  ends up buried in resist.
* The spring fitted after the bulk is finished.
* The spring presses on the window about 2 mm from the glue line, which is
  harmless.

**Verdict:** feasible only at the two inner corners, and it costs a PCB
re-spin plus a process step. Keep it as the fallback if A gives trouble.

### C — Conductive elastomer instead of the spring in B

Gentler on the window. But silicone outgassing is an ageing risk in gas
detectors, so use it only with a low-outgassing grade, and only together
with B.

### D — Gas through a hole in the PCB

Not recommended:
* The frame already feeds gas through 2 ports and 26 nozzles.
* In the bulk process, Dynamask tents the hole on the carrier plate, the mesh
  lies over it, and developer or rinse water gets trapped. The hole would
  then need its own mesh cut-out and a sealed fitting through the board
  support.
* Combining the gas hole with the HV contact creates a leak path and a
  creepage path in one.
* If a dead flow region shows up, add a nozzle to the frame instead.

---

## 4. Mask impact

**A and A2 need no mask change:** V3B_final is used as it is, with whatever
pillar diameter is chosen after the test. **B** would need a drift window in
M1/M2 at the chosen inner corner; that can be generated from the V3B_final
config once the PCB pad position is fixed.

## 5. Still to check

* The window's conductive coating faces the PCB (concept A relies on it).
* The frame material and the highest temperature it tolerates, for the
  silver-epoxy cure.
* Whether new frames get the A2 slot, or the A2 Ø1.2 horizontal hole is
  drilled in existing frames.

## Reproduce

```
cd tools && python3 drift_contact_study.py     # ~1 min
python3 make_page.py                           # rewrites ../drift_contact.html
python3 make_conceptB_3d.py --step             # 3D page + STEP (STEP needs FreeCAD)
```

The script reads the originals, caches the frame cuts in `data/cache.pkl`
(about 20 MB; safe to delete), and rewrites `data/results.json` and
`figures/`.
