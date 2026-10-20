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
(MECF-010P, 5 × 1 mm sheets) in an insulating guide ring.

**Carbon back** (`mechanics/`) – 3 mm; extension removed, edge 10 mm before the
connectors (r 616.9); same 39-hole pattern; "#" ribs as principle; M3 × 16,
head on the frame, washer + nut on the carbon side.

**PCB and insulation masks** – the next step. From the PDF and the work above:

| # | item | state |
|---|---|---|
| 1 | Homogenised screw holes: the 39 × Ø3.5 of `mechanics/data/frame_holes_new.csv` replace today's 40 (26 plated + 14 not) | defined; plated or not? |
| 2 | Sacrificed pad for the drift: B2 pad at (590.5, 10.0) | done in `pcb/drift_pad_B2`; Sig1 pin to GND or floating? (question for Irakli) |
| 3 | Bigger mesh-contact pad | proposal in `pcb/next_version` sits in the bottom corner, which is now cleared of mesh: needs a new place |
| 4 | Bigger alignment marks | crosses 1 and 2 come 3.6–4.2 mm from new screw holes 38/39 (need ≥ 7.2 mm) |
| 5 | Drift pad connected to the D contact | done in B2 (back copper); its insulation under the carbon back is a placeholder |
| 6 | Connectors moved to the back side (same FX20-60P, same positions) | to do |
| 7 | Connector-support holes Ø2.2 / Ø3.2: upper Ø3.2 holes are rotated 0.09° (≈ 1 mm) from symmetric | make symmetric? |
| 8 | 4 Ø2.2 holes next to the HV pads, purpose unknown (inside the HV openings) | keep or remove? |
| 9 | Mesh cut: the B2 template is a closed 10 × 10 square; the decision is to clear the whole corner (x ≥ 585.5, y ≤ 15) | to update |
| 10 | PCB outline | unchanged |
| – | Masks: drift pad (done), mesh-pad window, alignment-mark outlines | follow items 2–4 |

## Running

Every folder's README lists its scripts. Always run them with a memory cap,
one at a time, e.g. `(ulimit -v 3000000; python3 script.py)`:
`drift_contact/tools/make_conceptB_3d.py` loads the 282 MB frame STL and peaks
at about 1.9 GB (use `ulimit -v 3500000` for it); everything else stays under
1.2 GB. Never draw all PCB copper uncropped.

`drift_contact_study.py` rebuilds its cache from the STL when the script is
newer than `data/cache.pkl`; `touch` the cache after editing the script if the
inputs did not change.
