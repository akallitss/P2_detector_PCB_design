# P2 Micromegas revision 2026 (production end of 2026)

The single place for the revision described in `P2 Micromegas Revision.pdf`
(this folder, untracked like all PDFs). Each part has its own subfolder, with
its scripts in `tools/` and the numbers in its README.

| folder | what | status |
|---|---|---|
| `drift_contact/` | The study that explains the drift (mylar) HV-contact problem and the concepts, with the 3D pages. Also builds `data/cache.pkl` (frame slices + PCB Gerbers) that the other folders read. | done |
| `mechanics/` | NOW → NEW figures for the technicians: drift frame, carbon drift piece, carbon back, screws. | done |
| `pcb/drift_pad_B2/` | Patched Gerbers + masks for the B2 drift pad (3 × 3 mm on the former `/Sector0/Sig1`), QC report, proposal mail. | done (mesh cut to update, see below) |
| `pcb/next_version/` | Next-PCB items: bigger alignment crosses, bigger mesh-contact pad. | to revise (see below) |

All folders use the shared PCB / frame coordinates (fan apex = origin, mm;
z = 0 is the frame face on the PCB) and read the original drawings next to this
folder (`../Version_Apr26`, `../Version_Sept26`, `../DRIFT_P2_261124`,
`../carbon-frame`), which they never modify.

## What changes, per part

**Drift frame** (`mechanics/`) – extension behind the connectors (full height,
to the PCB edge R650) with 40 connector-support holes; HV openings at both outer
corners (also frees the top gas inlet); old wire slot removed; 39 × Ø3.5 screw
holes, equal pitch, mirror-symmetric; outline flush with the unchanged PCB;
O-ring untouched. HV filter box: no room on the extension. 5 mm drift gap:
placeholder.

**Carbon drift piece** (`mechanics/`) – 2 mm thick, outline unchanged; flap at
the B2 corner pressing the mylar onto a 4 × 4 mm conductive-foam column
(MECF-010P, 5 × 1 mm sheets). Proposed 26 Oct (to agree): the foam sits in
a 4.4 × 4.4 slot of a frame block that fills the corner at the lower level
(z 0–4), and the flap has the block's outline and rests on it; this replaces
the guide ring (`mechanics/figures/foam_slot_*.png`). The slot is centred on
the drift pad, now at the centre of the corner (592.75, 7.5).

**Carbon back** (`mechanics/`) – 3 mm; extension removed, edge 10 mm before the
connectors (r 616.9); same 39-hole pattern; "#" ribs as principle; M3 × 16,
head on the frame, washer + nut on the carbon side.

**PCB and insulation masks** – the next step. From the PDF and the work above:

Figures and tables for the KiCad designer: `pcb/next_version/` (start with
section 0 of its README).

| # | item | state |
|---|---|---|
| 1 | Homogenised screw holes: 39 × Ø3.5 (`pcb_screw_holes_new.csv`), 37 of today's 40 removed | drawn; plated or not? |
| 2 | Sacrificed pad for the drift: Sig1 removed, drift pad 3 × 3 mm at the centre of the cleared corner (592.75, 7.5) (26 Oct; first B2 patch: (590.5, 10.0)) | drawn (`pcb_corner_A_drift.csv`); Sig1 pin to GND or floating? (question for Irakli) |
| 3 | Mesh-contact pad | corner A: mesh pad removed; its line and the 2 M pads become the drift feed; the top-corner pad is the only mesh contact |
| 4 | Bigger alignment marks (9 mm, 12.5 mm resist square) | drawn; crosses 1, 2 moved to r = 104.25 (47.5°, 12.5°) |
| 5 | Drift pad connected to the HV pads | 26 Oct: on F.Cu through today's mesh line (0.8 mm segment pad → bend) to the old M pads (relabel D); no via, no back copper; GND pour 3 mm away (today 0.5 mm) |
| 6 | Connectors to the back side (same FX20-140P, same positions) | drawn; pin order mirrors: check the mating side |
| 7 | Connector-support holes: upper Ø3.2 rotated 0.09° from symmetric | open: make symmetric? |
| 8 | 4 Ø2.2 holes next to the HV pads (inside the HV openings) | open: keep or remove? |
| 9 | Mesh cut: whole corner x ≥ 585.5, y ≤ 15 | done (`P2_BASKET-MeshCut_B2.gbr`, `pcb_mesh_cut.csv`) |
| 10 | PCB outline | unchanged |
| – | Insulation masks M1, M2: new screw-hole openings, new crosses, corner-A mesh window closed, drift-pad window at the new pad | done: `pcb/next_version/Insulation_masks/V3B_final_2026/` (QC: only intended changes) |

## Running

Every folder's README lists its scripts. Always run them with a memory cap,
one at a time, e.g. `(ulimit -v 3000000; python3 script.py)`:
`drift_contact/tools/make_conceptB_3d.py` loads the 282 MB frame STL and peaks
at about 1.9 GB (use `ulimit -v 3500000` for it); everything else stays under
1.2 GB. Never draw all PCB copper uncropped.

`drift_contact_study.py` rebuilds its cache from the STL when the script is
newer than `data/cache.pkl`; `touch` the cache after editing the script if the
inputs did not change.
