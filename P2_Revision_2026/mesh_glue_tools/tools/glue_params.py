"""
Dimensions of the P2 mesh-gluing tools (option C of the 3D note): one short shoe
that lays the glue line on the rim wall, guided by loose rails laid against the
PCB edge.  Shared by make_glue_tools.FCpy (STEP/STL) and fig_glue_tools.py (drawings).

All lengths in mm.

Shoe coordinates (local):
  X  along the travel, +X = forward (the lip notch is at the rear, -X)
  Y  across the wall: Y = 0 is the OUTER border of the rim wall, +Y towards the
     active area; the PCB edge is at Y = -REACH
  Z  up; Z = 0 is the top of the bare PCB (FR4), the table is at Z = -PCB_T

Measured (Apr26 Edge_Cuts + V1 M1/M2 films + stack-up), see the README:
  rim wall 2.66 mm wide, 200 um tall (Dynamask), flat top (no insulation under it, t1 = 0)
  pillars on 18 um copper, so their tops are 18 um above the wall top
  PCB 0.2 mm FR4 + 2 x 18 um Cu
  board edge -> outer border of the wall: 11.84 (bottom and 60 deg side),
  16.85 (inner arc, edge r 95), 51.98 (outer arc, edge r 650)
"""

# ---------------------------------------------------------------- board
PCB_T = 0.236          # FR4 0.2 + 2 x Cu 0.018
WALL_W = 2.66          # rim wall width
WALL_H = 0.200         # Dynamask height
CU = 0.018             # pillar copper

# edge -> outer border of the wall, per stretch
REACH = {
    "straight": 11.84,  # bottom edge (y = -10) and 60 deg side
    "inner_arc": 16.85,  # PCB edge r = 95, wall outer border r ~ 111.85
    "outer_arc": 51.98,  # PCB edge r = 650, wall outer border r ~ 598.02
}

# ---------------------------------------------------------------- the shoe
LAID_H = 0.100         # height of the line left by the lip notch (100 um, agreed)
LINE_W = 1.00          # width of the lip notch = width of the laid line
RUN_W = 0.35           # runner width (sits on each border of the wall)
SKIRT_H = 0.60         # runners / scrapers stand this far below the body
SHOE_L = 10.0          # length of the glue head along the travel
END_T = 1.2            # thickness (X) of the front wall and of the rear scraper
CHAN_D = 1.2           # overflow channels go this far up into the body
BODY_OUT = 1.0         # body overhang outside the wall (towards the edge)
BODY_IN = 1.0          # body overhang inside the wall (over the pillars, 0.58 clear)
TOP_Z = 8.4            # top of body and arm (Z)
FEED_D = 1.30          # bore for an 18 G blunt dispensing needle (OD 1.27)
BOSS_D, BOSS_H = 5.0, 3.0  # needle boss on top

# guidance
RAIL_W = 20.0          # rail width (away from the PCB)
RAIL_ABOVE = 4.364     # rail top above the PCB top  -> rail height = PCB_T + RAIL_ABOVE = 4.60
RAIL_H = round(PCB_T + RAIL_ABOVE, 3)
ARM_L = 30.0           # length of arm + fence along the travel (X)
SKID_W = 12.0          # arm overlap on the rail top (the skid)
FOOT_T = 3.0           # fence foot thickness (Y)
FOOT_GAP = 0.40        # foot bottom above the PCB
FENCE_SET = 1.0        # foot face sits this far inside the edge; the set screws make up the rest
SCREW_X = 12.0         # set screws at X = +-SCREW_X
SCREW_Z = 2.40         # set-screw axis height above the PCB
SCREW_TAP = 1.60       # tap drill for M2

# ---------------------------------------------------------------- rails (loose, placed against the PCB edge)
# straight: bottom edge from the inner-arc corner (94.47, -10) to the chamfer (617.77, -10) = 523.3 mm;
# the 60 deg side is the same length.  3 pieces per side.
STRAIGHT_LEN = 523.30
STRAIGHT_PIECES = 3
# inner arc: PCB edge r = 95, from -6.04 deg to 66.04 deg (72.08 deg, 119.5 mm), one piece
INNER_R, INNER_DEG = 95.0, 72.08
# outer arc: PCB edge r = 650, from 3.82 deg to 56.18 deg (52.36 deg, 594 mm), 4 pieces
OUTER_R, OUTER_DEG, OUTER_PIECES = 650.0, 52.36, 4


def lip_z():
    """Z of the runner / scraper bottoms = top of the wall."""
    return WALL_H


def body_z0():
    return WALL_H + SKIRT_H


def summary():
    return {
        "rail height": RAIL_H,
        "straight rail piece": STRAIGHT_LEN / STRAIGHT_PIECES,
        "inner arc rail deg": INNER_DEG,
        "outer arc rail piece deg": OUTER_DEG / OUTER_PIECES,
    }
