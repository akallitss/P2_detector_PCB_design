# Mesh gluing tools: glue shoe + loose rails (option C)

Printable tools for laying the glue line on the P2 rim wall before the mesh is put down
(option C of the note "P2 mesh wall: glue holder in 3D"). The glue bead is laid on the wall first. One short shoe then passes over it and leaves a
1.0 × 0.10 mm line in the middle of the 2.66 mm Dynamask wall, and the excess goes up into two
overflow channels. A fence foot on the shoe rides against loose rails laid on the table
against the PCB edge, and a skid on the arm slides on the rail top. There are no pins or screws
in the board.

| part | file (`out/`, STEP + STL) | qty | print |
|---|---|---|---|
| shoe, straight sides (reach 11.84) | `shoe_straight` | 1 | resin (SLA/MSLA) |
| shoe, inner arc (reach 16.85) | `shoe_inner_arc` | 1 | resin |
| shoe, outer arc (reach 51.98, over the bare connector pads) | `shoe_outer_arc` | 1 | resin |
| rail, ⅓ of a straight side (174.43 × 20 × 4.60) | `rail_straight` | 6 | FDM |
| rail, inner arc (R75–R95, 72.08°) | `rail_inner_arc` | 1 | FDM |
| rail, ¼ of the outer arc (R650–R670, 13.09°) | `rail_outer_arc` | 4 | FDM |

Workshop sheets: `out/glue_tools_sheets.pdf` (A3, 2 pages; also `sheet1_shoe.png`, `sheet2_rails.png`).
Reach = distance from the PCB edge to the outer border of the wall.

```
cd tools
OUT=../out freecadcmd make_glue_tools.py        # solids → STEP, STL, sections.json  (FreeCAD 1.0)
OUT=../out python3 fig_glue_tools.py            # sheets (needs sections.json)
```

All dimensions are in `tools/glue_params.py`. Change them there and re-run both scripts. For example,
`LAID_H` is the notch depth (the laid line height) and `REACH` holds the three reaches.

## Where the numbers come from

- **Wall:** 2.66 mm wide and 200 µm tall, with a flat top. There is no insulation under it, so t₁ = 0
  (confirmed 2026-11-05). The pillars stand on 18 µm copper, so they are 18 µm
  above the wall top. The mesh lands on the pillars.
- **Laid line:** 100 µm (agreed). 1.0 × 0.10 = 0.10 mm³/mm spreads to about 1.7 mm under the mesh,
  assuming a 40 µm mesh-wetting film. That is 0.17 mL for the 1684 mm perimeter.
- **Reaches:** measured on `Version_Apr26/FABRICATION_P2/Gerber/P2_BASKET-Edge_Cuts.gbr` against the
  V1 M1 active outline (`Version_Sept26/tools/p2_geometry.active_outline`), sampled every
  0.5 mm along the wall, then referred to the wall border with the bottom-edge values of the 3D note
  (edge y = −10, wall 1.84–4.50).
  - Bottom edge: parallel to the wall to 0.01 mm.
  - 60° side: drifts 0.10 mm end to end.
  - Inner arc and outer arc: concentric with the wall.
  - Not parallel to the wall: the chamfer and the top flat (about 50 mm each) and the four
    corners. Those stretches are guided by hand.
  - The routed edge has a break-out tab every 75 mm. File the tab stubs flush before laying the rails.
- **PCB thickness:** 0.236 mm (stack-up: 0.2 FR4 + 2 × 18 µm Cu). The bare edge is too thin to
  steer against, which is why the rails exist.
- **Connectors:** not soldered when the mesh is glued (confirmed 2026-11-05). So the
  outer-arc shoe's 63 mm arm can pass over the connector pads. It hovers 4.36 mm above them.

## Set-up and use

1. Lay the PCB mesh side up on a flat plate. Push the rail pieces against the PCB edge. Hold them
   with thin double-sided tape or weights.
2. Put the shoe on the wall. Turn the two M2 set screws (nylon tip) in the fence foot until the tips
   touch the rail inner face and both runners sit on the wall borders; check with a loupe. Lock the
   screws with a drop of varnish. The screws take up the PCB routing tolerance (±0.1–0.2 typical)
   and the sagitta of the arcs: on the inner arc the screws stick out about 0.76 mm more than on a
   straight side.
3. Lay a bead of glue along the middle of the wall ahead of the shoe (syringe by hand); the shoe
   has no feed. Its front is open, with an entry pocket 1.96 wide × 1.8 tall above the wall, so
   the bead runs into the cavity instead of being pushed along. Keep the bead lower than that.
   Lay about the volume of the line: 0.10 mm³ per mm, which is a bead about 0.4 mm across. The shoe only
   meters the height. Its two channels hold about 15 mm³ in all; a larger excess rides ahead in the
   entry pocket and eventually spills.
   Push the shoe forward and slightly outwards, with the rail on your right, which is counter-clockwise seen from
   above. Change shoe at the corners.

## Known limits

- The runners are 0.35 mm wide on a 2.66 mm wall. The shoe can wander about 0.3 mm sideways
  before a runner leaves the wall.
- On the inner arc (wall r ≈ 112–114.5) the straight 10 mm runners deviate 0.11 mm from the arc
  at their ends.
- Not yet tried on a board: the notch depth as printed, the glue viscosity, and the real mesh-wetting
  film thickness, which sets the 1.7 mm.
