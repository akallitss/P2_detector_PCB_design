# P2 basket — zoned bulk-insulation masks (Sept 2026)

Insulation masks for the bulk of the P2 basket detector in which the **pillar
diameter and pitch change from one pair of connectors to the next**, every zone
staying inside a 3 % dead-area budget.

Everything here is derived from `../Version_Apr26`. The frame is not
redesigned: the new M2 is the **CEA V1** mask with its pillar field replaced.

**V1, not V2.** V1 is the mask all the detectors so far were actually built
with, and it is the one CERN adapted. Its perimeter wall is **2.6 mm** where
V2's is **9.8 mm**, so its active area is **1738.5 cm²** against V2's
1615.3 cm² — 7.6 % more. Three independent things confirm V1 is the right
reference: every one of CERN's 41 366 pillars falls inside V1's outline (1 130
fall outside V2's); the closest CERN pillar clears V1's frame by 4.66 mm,
while against V2 it overlaps by 0.25 mm; and V1's inner bottom corner lies on
CERN's own evacuation-channel line to within 0.06°. Set `"frame_source": "V2"`
in a config to go back.

---

## 1. What the two existing designs actually are

Measured directly from the Gerbers (`tools/analyze_existing.py`), not from memory.

Active area — the inner edge of the bulk frame taken from the V1 M1 mask —
is **173 849 mm² = 1738.5 cm²**, an annular sector from r ≈ 115 mm to
r ≈ 595 mm spanning θ ≈ 0.5° … 59.5° about the fan apex, which sits exactly at
the Gerber origin (0, 0). The 10 connectors sit on a circle of
**R = 632.00 mm** at θ = 4.839°, 10.439°, … 55.161°, i.e. one connector every
**5.591°**.

| | pillars | Ø drawn | lattice | dead area (drawn) | +50 µm | +100 µm |
|---|---|---|---|---|---|---|
| **CEA V1** | 12 477 | 0.800 mm | hexagonal, NN 4.000 mm | 3.61 % | 4.07 % | 4.57 % |
| **CERN**   | 41 366 | 0.500 mm | square, 2.000 × 2.000 mm | 4.67 % | **5.65 %** | 6.73 % |

Both also carry the same 5 large Ø 6.15 mm discs (+0.09 %).

Two cross-checks that this reading is right:

* the CEA mask letters its own geometry in the title block —
  `P2_2026 / Mask_M2_V1 / D0.800mm-P4mm / D6mm_Derive`;
* CEA draws a filled disc as a stroked circle (a 0.400 mm pen run round a
  0.200 mm radius ⇒ a 0.800 mm disc). CERN converted the 5 big ones into plain
  Ø 6.15 mm flashes at *identical* centres, so that is how their CAM read them
  too.

So the numbers you quoted line up as: **CERN ≈ 6 %** is the 0.5 mm pillar with a
50 µm lamination growth, and **CEA ≈ 3 %** is the 0.8 mm pillar taken as drawn
(4.1 % if you also allow it 50 µm). `lamination_growth_mm` in the configs is
the knob for that — the whole design scales with it, so it is worth pinning
down with the workshop.

## 2. Answer to the question

Yes. At a 3 % ceiling, a hexagonal lattice needs

    pitch ≥ 5.50 × (pillar diameter + growth)

which leaves a usable range of roughly **Ø 0.35 mm on a 2.2 mm pitch** (23
pillars/cm², the best-supported mesh you can have at 3 %) through **Ø 0.80 mm on
a 4.7 mm pitch** (5 pillars/cm²). Below 3 % the pitch opens further — Ø 0.50 mm
at 6.2 mm is 0.75 %. All of it is comfortably inside the CERN layout, which is
the densest point of the space.

`QC/design_space.png` is that space with both reference designs and the proposed
zones on it.

## 3. The three proposed layouts

Five zones, two connectors each, split on the connector-wedge boundaries
(θ = 2.04°, 13.24°, 24.44°, 35.57°, 46.77°, 57.96°). The outermost zones are
stretched to the frame so the ~1° of mesh outside the connector fan is covered.
Each zone's hexagonal lattice is rotated onto its own wedge bisector, so the
pillar-to-strip geometry is the same in every zone and only the pillars change.

### V3C — two-factor (recommended)

| zone | conn. | Ø [mm] | pitch [mm] | pillars | /cm² | dead area (+50 µm) |
|---|---|---|---|---|---|---|
| 1 | 1–2  | 0.40 | 2.48 | 6 845 | 18.5 | **2.94 %** |
| 2 | 3–4  | 0.50 | 3.67 | 2 805 |  8.4 | **2.00 %** |
| 3 | 5–6  | 0.50 | 4.25 | 2 081 |  6.3 | **1.50 %** |
| 4 | 7–8  | 0.80 | 4.72 | 1 716 |  5.2 | **2.94 %** |
| 5 | 9–10 | 0.80 | 6.64 |   968 |  2.6 | **1.50 %** |

Three dead-area levels — 2.94 / 2.00 / 1.50 % — crossed with three pillar
diameters, in five wedges:

* **size at a fixed budget**: zones 1 and 4 are both at 2.94 % with the widest
  size contrast available, Ø0.40 against Ø0.80;
* **size again, lower down**: zones 3 and 5 repeat Ø0.50 against Ø0.80 at
  1.50 %, so the size question is asked twice at two different budgets;
* **how far the budget can fall**: Ø0.50 appears at 2.00 % and 1.50 %, Ø0.80 at
  2.94 % and 1.50 %.

The pitch still grows monotonically from zone 1 to zone 5, which keeps the
zone boundaries mild. Whole detector **2.26 %** over 14 415 pillars — below
the CEA design it replaces.

Zone 2 was originally a third point at 2.95 %; it was moved to 2.00 % so the
dead-area axis has three levels rather than a cluster at 3 % and a pair at
1.5 %. Putting the 2 % point on zone 1 instead was rejected: it would give
zones 1 and 2 pitches of 3.00 and 3.03 mm, a boundary you could not see or
measure.

### V3A — iso dead area

Every zone at ~2.94 %, Ø 0.35 → 0.80 mm, pitch 2.20 → 4.71 mm. Isolates one
question: at a fixed efficiency budget, many small pillars or few large ones?
23 327 pillars, 3.03 % overall.

### V3B — support-density sweep

Ø 0.50 mm everywhere, dead area graded 2.94 → 0.75 %, pitch 3.03 → 6.09 mm.
Isolates the other question: how sparse can the support get before the mesh
sags, the gain goes non-uniform, or it starts sparking? 12 587 pillars, 1.81 %
overall.

## 3b. Polarity — why the first version of these files looked empty

Both reference masks paint the active area as **one dark region** and then
switch to **clear polarity** (`%LPC%`) so the pillars are *knocked out* of it:

| | dark ops | clear ops |
|---|---|---|
| CEA V2 M2 | 1 927 (frame, regions, title block) | 46 736 (pillars + support discs) |
| CERN M2 | 163 (frame) | 41 465 (pillars + support discs) |
| **new M2** | 2 333 | 14 602 |

The first version of these masks dropped the `%LPC%` command, so the pillars
were painted **dark on top of the dark region** — same colour as their
background. The files parsed, measured and validated correctly and showed
nothing where it mattered. Fixed, and now checked directly: `qc_mask.py`
rasterises a patch in every zone honouring polarity and requires the pillar
interiors to come out clear and the gaps between them dark. A mask whose
pillars are invisible is now rejected, not written.

`render_gerber.py` renders any of these files the way a viewer does — it
tokenises the character stream (`%` opens a parameter block, `*` ends a data
block) rather than reading it line by line, applies polarity with a painter's
algorithm, and cross-checks its object count against `gerbonara` if that is
installed. Use it if a viewer ever shows you something unexpected:

```bash
python3 tools/render_gerber.py Insulation_masks/V3C/P2_BASKET-Mask_M2_V3C.gbr \
        --zoom 420 300 --zoom-size 40
```

Two further notes on how the pillars are written:

* **Flashes vs stroked arcs.** CEA drew each pillar as two half arcs swept with
  a pen (a 0.4 mm pen on a 0.2 mm radius = a 0.8 mm disc); the default here is
  a plain `D03` flash, which is what CERN's CAM produced. Both paint the same
  disc. `V3C-stroke` is V3C written in CEA's stroked-arc convention instead —
  identical geometry, verified centre by centre to 1e-13 mm. Use it if a viewer
  in outline/sketch mode hides the flashes.
* **One file, one aperture table.** The CEA masks are three Gerber exports
  concatenated, each re-declaring `%FSLAX46Y46%` and re-using `D10`, `D11`, …
  for different apertures. That is not legal RS-274X. These are re-emitted as a
  single spec-compliant file with one format spec and one collision-free
  aperture table.

## 3c. Evacuation channel (adopted from the CERN masks)

Both CERN masks cut a notch through the resist border at the **inner bottom
corner** of the active area — the low point of the detector — so gas and
excess resin can escape during lamination instead of being trapped. The CEA
masks have no such feature; it is now on all of these.

| | CERN | new masks |
|---|---|---|
| M1 (frame) | 1.30 mm slot → Ø3.00 mm reservoir at (110.844, 0.875) | same, started from the CEA corner |
| M2 (pillars) | 2.00 mm slot → (110.186, 0.183) | same, started from the CEA corner |

Both CERN slots start at **(119.464, 9.949)** — CERN's own active-area corner —
and run outward at −133.53°. V1's inner bottom corner (114.685, 4.909) lies on
that same line (−133.59°), so the slot keeps **CERN's end points and
direction** but starts **1 mm inside our corner**, at (115.374, 5.633): 6.57 mm
on M1, 7.52 mm on M2.

It first started at CERN's point verbatim. On the V1 frame that point is
6.9 mm *inside* the active area, so that stretch of slot was open space on open
space — no effect on the mask — while its pillar keep-out cut a diagonal lane
of **seven pillars** out of the grid, which is what made the pattern look
broken at the corner. Starting at our own corner leaves only the one pillar
that sits at the corner itself. Drawn dark, emitted last, so it cuts
the border and the pillar field alike; pillars are held 0.5 mm clear of it,
and that pillar-free corridor is excluded from the unsupported-span figure
since the mesh over it is carried by the border.

It is verified functionally, not just drawn — `qc_mask.py` rasterises the
corner and requires three things:

1. the centreline is open (dark) along its whole length,
2. it actually crosses a resist border — a line parallel to it, just outside
   its edge, still shows the border it cuts,
3. the active volume and the far end of the channel are one connected
   dark region.

Run against the unmodified CEA V2 mask the same check reports the centreline
76 % blocked and no connection, which is what it should say for a mask with no
channel.

To move, resize or add channels, put an `evacuation_channels` block in the
config (the built-in default is the CERN one above):

```json
"evacuation_channels": [
  {"name": "inner bottom corner",
   "anchor": "auto",                     // "inner_bottom_corner", or [x, y]
   "anchor_inset_mm": 1.0,
   "pillar_clearance_mm": 0.5,
   "m1": {"width_mm": 1.30, "end": [110.844, 0.875], "droplet_mm": 3.0},
   "m2": {"width_mm": 2.00, "end": [110.186, 0.183]}}
]
```

Omit the `m1` or `m2` key to leave that layer untouched; `"evacuation_channels": []`
removes the feature entirely.

## 3d. Mesh contact: the large pad removed

The CEA M2 carries **two** mesh-contact openings at the outer bottom corner: a
small 2.0 × 2.0 mm one on the very corner at (595.8, 2.1)–(597.8, 4.1), which
sits *outside* the active outline, and a large **7.0 × 7.0 mm** one at
(585.7, 7.5)–(592.7, 14.5), which sits well *inside* the active area. CERN's
masks have only the small one.

The large pad is now removed and the small one kept, matching CERN. It was a
filled `G36` region plus a 0.5 mm outline stroked round it; both go, and the
pillar lattice simply continues across the vacated area. M1 never had the
large pad, so it is unchanged. Set `"remove_large_mesh_pad": false` to keep it,
or list further boxes in `remove_frame_boxes` to delete other frame features.

## 3d2. Mesh contacts at both ends of the outer arc

CEA draws a mesh-contact window only at the **bottom** end of the outer arc.
CERN draws one at each end, and the PCB carries a **3.88 × 3.90 mm copper pad
at (300.98, 515.97)** for the top one — so the opening has somewhere to land.
Both masks now carry both windows, at our own bottom-contact size:

The top window is the bottom one **mirrored through the fan axis**, which is
at exactly 30° — the ten connector angles average to 30.000°. Mirroring, not
translating, is what matters: at the bottom corner the two edges of the
detector run at 0° and 90°, at the top corner they run at 60° and 150°, so an
axis-aligned copy sits askew to the corner. CERN does exactly the same — their
top contact is their bottom 1.93 × 1.81 mm pad with its edges at 59.96° and
150.00°.

| | bottom (inherited) | top (mirrored) | |
|---|---|---|---|
| M1 | (596.46, 3.53), r 596.47, θ 0.34°, edges 0°/90° | (301.29, 514.78), r 596.47, θ 59.66°, edges 60°/150° | |
| M2 | (596.82, 3.15), r 596.83, θ 0.30°, edges 0°/90° | (301.14, 515.29), r 596.83, θ 59.70°, edges 60°/150° | |

Radii match to **0 µm** and the two angles sum to exactly **60.000°** on both
layers, so the pair really is symmetric. The M2 top window lands on the
Ø3.88 × 3.90 mm PCB copper pad at (300.98, 515.97) to within 74 µm.

Because the *source polygon* is mirrored rather than a rectangle redrawn, the
rounded corners of the inherited window come across too — the two windows are
the same shape, not just the same size. Switch it off with
`"mirror_mesh_contact": false`.

## 3d3. The corner the removed pad left behind

Deleting the large pad (§3d) exposed a second problem: the M2 frame region was
**stepped back** around that pad, so the 147.3 mm² corner it occupied was not
dark, and the 28 pillars the lattice placed there were painted clear-on-clear —
drawn in the file, invisible on the mask. The active area inside that corner is
now re-filled dark before the pillar field goes down, so it is ordinary pillar
surface. Verified: clear area left inside the active outline is **0.0 mm²**
(was 147.3), and all 28 pillars now read as clear on dark.

The fill is cut to **M2's own wall edges** — the bottom edge at y = 4.490 and
the outer arc at r = 595.369, read from the M2 frame region on either side of
the old pad. It was first cut to M1's centreline outline, which sits about
0.3 mm further in; that left the resist wall 0.31 mm thicker along the old
pad's span, a visible ~12 mm step on the bottom edge and on the arc.

That 147.3 mm² was the *only* place the inherited frame left the active area
unpainted — the whole rest of the perimeter agrees to better than the 0.25 mm
raster used to check it.

## 3d4. Mounting holes on M1 — left as V1 has them

Of the 60 drilled holes ≥ 3.2 mm, the M1 mask marks **40** as distinct
openings. The other 20 are the Ø3.20 mm row on the outer arc at r = 645.6 mm:
V1 leaves that entire strip open with no resist, so there is nothing to punch
through. CERN instead covers the strip with resist and punches all 60.

**Decision: keep V1's arrangement.** Our M1 is identical to
`P2_BASKET-Mask_M1_V1.gbr` here. Adopting CERN's would mean adding resist
where V1 has none, which is a change to the frame rather than to the hole
marking.

## 3e. Pillar spacing where two zones meet

Two unrelated lattices meeting at a boundary, plus the seam row sitting on the
boundary itself, leave the pillar population locally far denser than either
zone asks for. Measured on the unthinned V3C: the closest pair on the whole
detector was **0.73 mm** centre-to-centre against a 2.50 mm lattice pitch, and
569 pairs were closer than 2 mm.

A pair of pillars from *different* groups (zone A / zone B / the seam row) is
now required to be at least

    max( (Ø_i + Ø_j)/2 + 0.30 mm ,  boundary_min_spacing_mm )

apart. Pairs *inside* one zone are never touched — there the spacing is the
lattice and is deliberate. When a pair is too close the pillar from the denser
group is dropped, so the sparser side keeps its support; the seam row counts
as the densest group and yields first, which is exactly "before placing a new
pillar at an interconnection, check whether one is already within 3 mm".

The default is **3.0 mm**. What it costs, on V3C:

| min spacing | seam pillars left | closest pair | pairs < 2 mm | largest unsupported span, zones 1–5 [mm] | dead area |
|---|---|---|---|---|---|
| off  | 455 | 0.73 mm | 569 | 1.77 2.24 2.81 3.25 4.01 | 2.445 % |
| 1.5 mm | 261 | 1.51 mm | 196 | 2.02 2.36 3.04 3.55 4.12 | 2.445 % |
| 2.0 mm | 136 | 2.00 mm | 0 | 2.24 2.66 3.26 3.35 4.14 | 2.443 % |
| **3.0 mm** | **29** | **2.48 mm** | **0** | 2.85 3.01 3.69 3.91 4.61 | 2.439 % |

Dead area is unaffected — the seam pillars were always a negligible fraction.
What you trade is boundary support: at 3 mm the seam row is effectively gone
and the two lattices simply abut, so the span at a boundary grows to about the
coarser zone's own pitch. The pitches above are the ones the solver settles on
*with* the rule active; they shift by a few hundredths if you change it. 2.0 mm already removes every sub-2 mm pair while
keeping the boundaries tighter, if that matters more than the clean look.

With the rule on, the closest pair anywhere on the mask equals the finest
lattice pitch — `qc_mask.py` checks exactly that, and reports 1 062 offending
pillars if the rule is switched off.

## 3f. Release mask: V3B_final

**Decision (2026-09-15):** the shop cannot make pillars below Ø0.50 mm. V3B is
the only layout built entirely from Ø0.50 pillars, so it was chosen and
finalized as `Insulation_masks/V3B_final/`. The original `V3B/` is kept as the
record of the layout that was discussed; it is not for production.

| zone | conn. | lattice | pitch [mm] | pillars | pillars | + walls | = total |
|---|---|---|---|---|---|---|---|
| 1 | 1–2  | square | 2.00 | 9 103 | 5.84 % | 0.68 % | 6.52 % |
| 2 | 3–4  | hex | 3.47 | 3 069 | 2.19 % | 1.51 % | 3.70 % |
| 3 | 5–6  | hex | **5.93** | 1 044 | **0.75 %** | 1.52 % | 2.27 % |
| 4 | 7–8  | hex | 4.91 | 1 537 | 1.10 % | 1.51 % | 2.61 % |
| 5 | 9–10 | hex | **4.11** | 2 489 | **1.60 %** | 0.68 % | 2.28 % |

Whole detector 3.60 % (pillars 2.36 + walls 1.16 + support discs 0.09),
17 242 pillars. Dead area with +50 µm growth.

**Least dense support in the centre.** Zones 3 and 5 swapped densities at the
user's request, so the sparsest pillars sit on the centre wedge (connectors
5–6). Three of the five Ø6.15 mm support discs are in that wedge, on the
detector's centre line (θ = 30°, at r = 238, 361 and 475 mm), so it also
carries the most extra mesh support.

**Zone 1 is CERN's layout, as the reference.** Ø0.50 mm on a 2.00 × 2.00 mm
square grid, pinned to absolute coordinates (`lattice_origin: [0, 0]`) so it
lands on CERN's own points: when checked, 8 431 of its pillars were within
1 µm of a pillar in `Bulk_CERN/P2_Mask2.gbr` (worst 17.7 nm); the rest are
rows CERN never had, because V1's thinner wall gives more active area. Of
CERN's 8 581 pillars in this wedge, the only ones absent are those inside the
wall and evacuation-channel keep-outs. The zone is deliberately over the 3 %
budget (`dead_area_budget: 0.06` on that zone only).

**Walls between zones — continuous.** A 1.00 mm resist wall runs the full
length of each of the four zone boundaries (480 mm each, 0.5 mm into the frame
at both ends), replacing the seam rows and the cross-zone spacing rule;
pillars keep 0.50 mm edge-to-edge from it.

The walls were first built as dashes with 2 mm gaps, and were made continuous
at the user's request. The consequence is recorded here on purpose: a
continuous wall seals each zone into its own compartment under the mesh, so
**only zone 1, which holds the evacuation channel, is vented during
lamination**; zones 2–5 have no path to it. This was tested on the rendered
mask, not assumed — with the dashed walls all five zones connected to the
channel; with continuous walls zones 2–5 do not. `qc_mask.py` still reports
it on every build, as accepted (`require_venting: false` in the config),
rather than failing. If trapped air turns out to matter, the options are a
short gap in each wall again, or an evacuation channel per zone.

What the walls cost: 504 mm² each, about 1.5 % on top of the pillars in zones
2–4 and 0.7 % in zones 1 and 5. It is concentrated in a 1 mm band on the
boundary shared by two zones, so it is listed apart from the pillar dead area,
which remains the variable each zone is solved for. A 0.5 mm wall would halve
it.

**Mesh-contact window size: left as is for now.** The PCB gold pads are
2.93 × 2.81 mm (bottom) and 3.90 × 3.94 mm (top), with readout copper close
beside them — `SECTOR0/SIG1` about 0.9 mm from the bottom pad and
`SECTOR9/SIG128` about 1.5 mm below the top one. A 5 × 5 mm window would
overrun both pads onto that copper; growing the windows up to the pad size
needs no PCB change, a true 5 × 5 mm contact does.

## 4. Things to settle before ordering

* **Minimum pillar diameter.** V3A zone 1 asks for Ø 0.35 mm and V3C zone 1 for
  Ø 0.40 mm in a 150 µm Dynamask 5030 gap. CERN's quote only commits to 0.5 mm.
  Confirm with the workshop; if 0.5 mm is the floor, V3B needs no change and
  V3A/V3C want their small-pillar zones re-cut at 0.50 mm.
* **Lamination growth.** Everything is sized for +50 µm. Measure it on a
  previous bulk and re-run — the pitches re-solve automatically.
* **One mesh, one HV.** The zones share a mesh and (presumably) a single HV
  line, so a zone that sags or sparks takes the whole detector with it. The
  sparse end of V3B (6.09 mm) and of V3C (6.64 mm) is the exploratory part and
  is well beyond the 4 mm that the lab has already bulked successfully. If that
  risk is not acceptable on this detector, cap the sparsest zone at ~5 mm — the
  configs are one number each.
* **Zone boundaries.** A row of pillars is placed on each internal boundary at
  the finer of the two pitches, otherwise two unrelated lattices meeting leave a
  strip supported only every ~1 pitch. It costs ~0.07 % dead area per zone
  (already in the numbers above) and is what makes the zone edge visible on the
  finished detector.

## 5. Layout

```
config/zones_V3A.json          the zone definitions; edit these, not the code
config/zones_V3B.json
config/zones_V3C.json
config/zones_V3C-stroke.json   V3C in CEA's stroked-arc convention
config/zones_V3B_final.json    THE RELEASE MASK

Insulation_masks/V3x/
    P2_BASKET-Mask_M1_V3x.gbr   frame only - geometrically identical to V2 M1
    P2_BASKET-Mask_M2_V3x.gbr   frame + zoned pillars
    zones_V3x.json              the solved configuration, pitches included
    zone_report.csv             per-zone numbers
    pillars.npy                 x, y, zone, diameter
    QC/                         overview, boundary zooms, mesh-support map,
                                and the polarity-correct render of the mask

QC/design_space.png/.pdf        the design space with everything placed on it
PRODUCTION_SUMMARY.md           the sheet for the mask shop: every zone, every
production_summary.csv          area, the critical dimensions and the open questions

tools/gerber_io.py        RS-274X reader/writer for the subset used here
tools/p2_geometry.py      active outline, connector fan, support discs, both
                          reference pillar fields - all read from Version_Apr26
tools/strokefont.py       single-stroke font for the etched title block
tools/analyze_existing.py the table in section 1
tools/make_zoned_mask.py  the generator
tools/qc_mask.py          independent re-read of a produced mask + drawings
tools/validate_gerber.py  strict RS-274X syntax check
tools/render_gerber.py    renders a mask the way a viewer does (stream
                          tokenisation + polarity), cross-checked against
                          gerbonara when available
tools/design_space.py     the figure in section 2
tools/production_summary.py  builds PRODUCTION_SUMMARY.md + the CSV
tools/run_all.sh          everything, from scratch
```

## 6. Running it

```bash
cd tools
python3 analyze_existing.py                      # the reference measurements
python3 make_zoned_mask.py ../config/zones_V3C.json
python3 qc_mask.py ../Insulation_masks/V3C/P2_BASKET-Mask_M2_V3C.gbr
python3 validate_gerber.py ../Insulation_masks/V3C/*.gbr
python3 render_gerber.py ../Insulation_masks/V3C/P2_BASKET-Mask_M2_V3C.gbr
./run_all.sh                                     # or just this
```

To change a zone, edit its entry in the config:

```json
{"zone": 5, "connectors": [9, 10], "lattice": "hex",
 "diameter_mm": 0.80, "target_dead_area": 0.0150, "rotation": "wedge"}
```

Give it either `target_dead_area` (the generator solves the pitch, seam rows and
keep-outs included) or a fixed `pitch_mm`. `lattice` takes `hex` or `square`;
`rotation` takes `wedge`, `global`, or an angle in degrees. `connectors` is
inclusive and 1-based, counting anticlockwise from θ = 4.84°, so zones do not
have to be two connectors wide. Nothing is written if any zone ends up over
`dead_area_budget`.

File-level keys: `frame_source` (`V1`, the default and what the detectors are
built with, or `V2`), `boundary_min_spacing_mm` (3.0), `remove_large_mesh_pad`
(true), `remove_frame_boxes` ([]), `pillar_style` (`flash` or `stroke`),
`pillar_polarity`
(`clear`, matching both reference masks, or `dark`), `lamination_growth_mm`,
`dead_area_budget`, `zone_boundary_clearance_mm`, `disc_clearance_mm`,
`seam_rows`, `extend_outer_zones_to_frame`, `relabel`.

## 7. What is checked before a mask is written

* every zone's dead area against the budget, with the growth allowance applied;
* the frame: every stroke of the source frame must still be present in the new M2.
  The only permitted difference is the title-block lettering, which now reads
  the new geometry instead of `D0.800mm-P4mm`;
* the 5 support discs, by position;
* no pillar closer than 0.30 mm edge-to-edge to any other, across zone
  boundaries included;
* no pillar centre outside the active outline, none within 1 mm of a support
  disc;
* the largest pillar-free disc in each zone, as a mesh-span proxy;
* **pillar spacing**: no two pillars anywhere closer than the finest lattice
  pitch, i.e. the boundary crowding really was cleaned up;
* **that the evacuation channel works**: open along its length, crossing a
  real border, and connecting the active volume to the outside;
* **that the pillars are actually visible**: a patch in every zone is
  rasterised with polarity applied, and the pillar interiors must come out
  clear against dark gaps;
* RS-274X syntax: one format spec, no redefined or undefined aperture, no
  unterminated region, no `%` or `*` inside a comment (a `%` there opens a
  parameter block a viewer never closes), nothing off-panel (the V2 pillar
  layer carries two stray arcs at x = 1287 mm — they are dropped).
