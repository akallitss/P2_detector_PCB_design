# P2_detector_PCB_design

Analysis and generation scripts for the P2 basket Micromegas readout PCB and
its insulation (Dynamask) masks.

**This repository holds code and text only.** The drawings these scripts read
or write (fabrication Gerbers, drill files, insulation masks, STEP/STL models,
KiCad files, rendered figures and pages) are deliberately not tracked; see
`.gitignore`, which is a whitelist.

| folder | what the code does |
|---|---|
| `Version_Sept26/` | Zoned insulation-mask generator (`make_zoned_mask.py`) and QC/validation/rendering of masks; zone configs in `config/` (V3B_final is the one in use). `tools/run_all.sh` regenerates everything. |
| `P2_Revision_2026/` | Everything for the 2026 revision (start with its README): `drift_contact/` (the drift HV-contact study and 3D pages), `mechanics/` (NOW → NEW figures for the drift frame, carbon drift piece and carbon back), `pcb/drift_pad_B2/` (patched Gerbers and masks for the B2 drift pad; `qc_b2.py` is the polarity-aware rasteriser reused elsewhere), `pcb/next_version/` (alignment crosses, mesh-contact pad). |

## Running

The scripts locate their inputs relative to this folder, so they expect the
untracked drawings next to them, as on the original machine:

```
Version_Apr26/FABRICATION_P2/            fabrication Gerbers + drill
Version_Sept26/Insulation_masks/         generated masks (V3B_final, ...)
DRIFT_P2_261124/                         drift frame
```

Python 3 with `numpy`, `scipy`, `matplotlib`, `gerbonara`, `shapely`, `ezdxf`.
Run scripts one at a time under a memory cap (see `P2_Revision_2026/README.md`).
`P2_Revision_2026/drift_contact/tools/vendor/` must hold `three-0.147.0.min.js` and
`OrbitControls-0.147.0.js` (three.js r147, MIT) for the stand-alone 3D page.

Each folder's README has the numbers and the design decisions.
