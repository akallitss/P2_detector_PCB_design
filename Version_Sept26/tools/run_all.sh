#!/bin/bash
# Regenerate every zoned mask from scratch and check it.
set -e
set -o pipefail
cd "$(dirname "$0")"

echo "=== reference designs ==="
python3 analyze_existing.py

for v in V3B_final V3A V3B V3C V3C-stroke; do
    echo
    echo "=== $v ==="
    python3 make_zoned_mask.py "../config/zones_$v.json"
    python3 qc_mask.py "../Insulation_masks/$v/P2_BASKET-Mask_M1_$v.gbr"
    python3 qc_mask.py "../Insulation_masks/$v/P2_BASKET-Mask_M2_$v.gbr"
    python3 validate_gerber.py "../Insulation_masks/$v"/*.gbr
    python3 render_gerber.py "../Insulation_masks/$v/P2_BASKET-Mask_M2_$v.gbr"
done

echo
echo "=== design space figure ==="
python3 design_space.py

echo
echo "=== production summary ==="
python3 production_summary.py
