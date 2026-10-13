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
| `Drift_Contact_Oct26/` | Study of drift (mylar window) HV contact concepts: clearance analysis, 3D models of the concepts, the explainer pages. |
| `B2_DriftPad_Oct26/` | Variant B2: `make_b2_files.py` writes the patched Gerbers and masks (3 × 3 mm drift pad on the former `/Sector0/Sig1` corner pad); `qc_b2.py` is the polarity-aware rasteriser and clearance checker reused by the other folders. |
| `PCB_NextVersion_Oct26/` | Items for the next PCB version: space available for bigger alignment crosses, and a bigger mesh-contact pad next to the B2 drift pad. |

## Running

The scripts locate their inputs relative to this folder, so they expect the
untracked drawings next to them, as on the original machine:

```
Version_Apr26/FABRICATION_P2/            fabrication Gerbers + drill
Version_Sept26/Insulation_masks/         generated masks (V3B_final, ...)
DRIFT_P2_261124/                         drift frame
```

Python 3 with `numpy`, `scipy`, `matplotlib`, `gerbonara`.
`Drift_Contact_Oct26/tools/vendor/` must hold `three-0.147.0.min.js` and
`OrbitControls-0.147.0.js` (three.js r147, MIT) for the stand-alone 3D page.

Each folder's README has the numbers and the design decisions.
