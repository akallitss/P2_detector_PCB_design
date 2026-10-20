#!/usr/bin/env python3
"""
Concept B2: drift contact on the corner readout pad (/Sector0/Sig1) of the P2 basket.

Copies the fabrication Gerbers, drill file and V3B_final insulation masks into
../ and patches them.  The originals are only read.

PCB (Version_Apr26/FABRICATION_P2):
  F.Cu    remove the Sig1 readout pad (zone + its two flashes at the pad via),
          add a 3 x 3 mm drift pad, a 0.3 mm trace and two via pads
  B.Cu    remove the Sig1 trace from the pad via to the via at (619.97, 26.00)
          and the teardrop at the pad via; cut the GND hatch 3 mm round the new
          drift copper; add the drift route and two via pads
  ENIG    add the drift pad
  drill   remove the Sig1 pad hole, add two 0.4 mm vias
Masks (Version_Sept26/Insulation_masks/V3B_final):
  M1, M2  10 x 10 mm resist island (clear) round the pad, 2.6 x 2.6 mm window (dark)
New:
  mesh-cut template, 10 x 10 mm, for trimming the mesh at the end

    python3 make_b2_files.py
"""
from __future__ import annotations

import datetime
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(OUT, "..", "..", ".."))   # Detector_Drawings/
FAB = os.path.join(ROOT, "Version_Apr26", "FABRICATION_P2")
MASKS = os.path.join(ROOT, "Version_Sept26", "Insulation_masks", "V3B_final")
FAB_OUT = os.path.join(OUT, "FABRICATION_P2_B2")
MASK_OUT = os.path.join(OUT, "Insulation_masks", "V3B_final_B2")

STAMP = datetime.date.today().isoformat()

# ---- geometry (mm, board coordinates, fan apex at the origin) ---------------
PAD = (590.5, 10.0)                # 3 x 3 mm drift pad, in the old Sig1 pad
PAD_H = 1.5                        # half-size of the pad
VIA = (590.5, 7.6)                 # next to the pad, under the resist island
D_VIA = (626.3, 15.8)              # in the D solder pad at the bottom-right HV corner
ROUTE = [VIA, (600.0, 7.0), (616.0, 8.5), D_VIA]     # B.Cu drift route
TRACE_W = 0.3
VIA_PAD = 1.0
VIA_DRILL = 0.4
CU_CLEAR = 3.0                     # GND hatch pulled back this far from drift copper
CUT_MARGIN = 0.1                   # extra on the cut so the 3 mm survives fab tolerances
WIN_H = 1.8                        # M1/M2 window half-size (pad + 0.3)
CUT_H = 5.0                        # mesh cut half-size: pad edge + 3.5 (the mesh is laminated last and cut
                                   # at the end, so the cut edge stays bare; 0.5 mm margin for hand cutting)
ISLAND = (584.6, 4.4, 595.4, 16.0)  # resist island under the mesh edge: 1 mm beyond the cut on the open sides;
                                    # the bottom overlaps the M2 border (ends at y 4.5), the right side stays
                                    # clear of the M1 mesh-contact window (x >= 595.46)

SIG1_VIA = "X589183026Y10999014"   # Sig1 pad via, as written by KiCad
SIG1_DRILL = "X589.183Y10.999"


def q(v):
    return int(round(v * 1e6))


def xy(p):
    return f"X{q(p[0])}Y{q(p[1])}"


def rect_region(x0, y0, x1, y1):
    return ["G36*", f"X{q(x0)}Y{q(y0)}D02*", "G01*", f"X{q(x1)}Y{q(y0)}D01*", f"X{q(x1)}Y{q(y1)}D01*",
            f"X{q(x0)}Y{q(y1)}D01*", f"X{q(x0)}Y{q(y0)}D01*", "G37*"]


def max_aperture(lines):
    return max(int(m.group(1)) for l in lines for m in [re.match(r"^%ADD(\d+)", l)] if m)


_EOL = {"eol": "\n"}


def read(path):
    """Lines of a file; remembers its line ending (KiCad writes CRLF) for the next write()."""
    data = open(path, newline="").read()
    _EOL["eol"] = "\r\n" if "\r\n" in data else "\n"
    return data.split(_EOL["eol"])


def write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", newline="").write(_EOL["eol"].join(lines))


def insert_before_m02(lines, block):
    i = max(k for k, l in enumerate(lines) if l.strip() == "M02*")
    return lines[:i] + block + lines[i:]


def header_note(lines, text):
    """Put a G04 note right after the KiCad attribute header."""
    i = next(k for k, l in enumerate(lines) if l.startswith("%FS"))
    return lines[:i] + [f"G04 {text}*"] + lines[i:]


def drop_region(lines, net, near):
    """Delete the G36..G37 region that follows %TO.N,<net>*% and has a vertex within 1 mm of `near`."""
    hits = []
    for k, l in enumerate(lines):
        if l == f"%TO.N,{net}*%" and k + 1 < len(lines) and lines[k + 1] == "G36*":
            e = next(j for j in range(k + 1, len(lines)) if lines[j] == "G37*")
            pts = [(int(m.group(1)) / 1e6, int(m.group(2)) / 1e6)
                   for l2 in lines[k + 1:e] for m in [re.match(r"^X(-?\d+)Y(-?\d+)D0[12]\*$", l2)] if m]
            if any(abs(x - near[0]) < 1 and abs(y - near[1]) < 1 for x, y in pts):
                hits.append((k + 1, e))
    assert len(hits) == 1, f"expected one {net} region near {near}, found {len(hits)}"
    s, e = hits[0]
    return lines[:s] + lines[e + 1:], e - s + 1


def drop_lines(lines, exact, count):
    idx = [k for k, l in enumerate(lines) if l == exact]
    assert len(idx) == count, f"{exact}: expected {count}, found {len(idx)}"
    return [l for k, l in enumerate(lines) if k not in set(idx)]


# --------------------------------------------------------------------------
def patch_fcu(log):
    src = os.path.join(FAB, "Gerber", "P2_BASKET-F_Cu.gbr")
    L = read(src)
    L, n = drop_region(L, "/Sector0/Sig1", (594.6, 16.97))            # the 11.5 x 12 mm pad zone
    log.append(f"F.Cu: removed the /Sector0/Sig1 pad zone ({n} lines)")
    L = drop_lines(L, f"{SIG1_VIA}D03*", 2)                            # Ø0.8 and Ø5 pad flashes
    log.append("F.Cu: removed the two /Sector0/Sig1 pad flashes (Ø0.8, Ø5.0) at (589.183, 10.999)")
    a = max_aperture(L) + 1
    block = ["G04 ==== B2 drift contact, added " + STAMP + " (see P2_Revision_2026/pcb/drift_pad_B2/README.md) ====*",
             "%LPD*%",
             f"%TA.AperFunction,SMDPad,CuDef*%", f"%ADD{a}R,{2 * PAD_H:.6f}X{2 * PAD_H:.6f}*%", "%TD*%",
             f"%TA.AperFunction,ViaPad*%", f"%ADD{a + 1}C,{VIA_PAD:.6f}*%", "%TD*%",
             f"%TA.AperFunction,Conductor*%", f"%ADD{a + 2}C,{TRACE_W:.6f}*%", "%TD*%",
             "%TO.N,DRIFT_B2*%",
             f"D{a}*", f"{xy(PAD)}D03*",
             f"D{a + 1}*", f"{xy(VIA)}D03*", f"{xy(D_VIA)}D03*",
             f"D{a + 2}*", f"{xy((PAD[0], PAD[1] - PAD_H))}D02*", f"{xy(VIA)}D01*",
             "%TD*%"]
    L = insert_before_m02(header_note(L, "B2 drift contact: modified copy of the KiCad output, " + STAMP), block)
    log.append(f"F.Cu: added 3 x 3 mm drift pad at {PAD}, via pads at {VIA} and {D_VIA}, 0.3 mm trace pad -> via")
    write(os.path.join(FAB_OUT, "Gerber", "P2_BASKET-F_Cu.gbr"), L)


def patch_bcu(log):
    src = os.path.join(FAB, "Gerber", "P2_BASKET-B_Cu.gbr")
    L = read(src)
    L = drop_lines(L, f"{SIG1_VIA}D03*", 1)
    log.append("B.Cu: removed the /Sector0/Sig1 via pad at (589.183, 10.999)")
    # the Sig1 trace: the D02/D01 pairs right after its %TO.N line that run from the pad via
    k = next(k for k, l in enumerate(L) if l == "%TO.N,/Sector0/Sig1*%"
             and L[k + 1].endswith("D02*") and any(SIG1_VIA in L[j] for j in range(k + 1, k + 12)))
    e = next(j for j in range(k + 1, len(L)) if not re.match(r"^X-?\d+Y-?\d+D0[12]\*$", L[j]))
    seg = L[k + 1:e]
    assert len(seg) == 8 and all(re.match(r"^X-?\d+Y-?\d+D0[12]\*$", s) for s in seg), seg
    L = L[:k + 1] + L[e:]
    log.append("B.Cu: removed the /Sector0/Sig1 trace, 4 segments from the pad via to the via at (619.97, 26.00)")
    L, n = drop_region(L, "/Sector0/Sig1", (589.18, 11.0))            # teardrop at the pad via
    log.append(f"B.Cu: removed the /Sector0/Sig1 teardrop at the pad via ({n} lines)")
    a = max_aperture(L) + 1
    clr_w = TRACE_W + 2 * (CU_CLEAR + CUT_MARGIN)
    clr_v = VIA_PAD + 2 * (CU_CLEAR + CUT_MARGIN)
    block = ["G04 ==== B2 drift contact, added " + STAMP + " (see P2_Revision_2026/pcb/drift_pad_B2/README.md) ====*",
             "G04 clearance: GND hatch removed 3 mm round the drift route and vias*",
             f"%ADD{a}C,{clr_w:.6f}*%", f"%ADD{a + 1}C,{clr_v:.6f}*%",
             f"%TA.AperFunction,ViaPad*%", f"%ADD{a + 2}C,{VIA_PAD:.6f}*%", "%TD*%",
             f"%TA.AperFunction,Conductor*%", f"%ADD{a + 3}C,{TRACE_W:.6f}*%", "%TD*%",
             "%LPC*%", f"D{a}*", f"{xy(ROUTE[0])}D02*"] + [f"{xy(p)}D01*" for p in ROUTE[1:]] + \
            [f"D{a + 1}*", f"{xy(VIA)}D03*", f"{xy(D_VIA)}D03*",
             "%LPD*%", "%TO.N,DRIFT_B2*%",
             f"D{a + 3}*", f"{xy(ROUTE[0])}D02*"] + [f"{xy(p)}D01*" for p in ROUTE[1:]] + \
            [f"D{a + 2}*", f"{xy(VIA)}D03*", f"{xy(D_VIA)}D03*", "%TD*%"]
    L = insert_before_m02(header_note(L, "B2 drift contact: modified copy of the KiCad output, " + STAMP), block)
    log.append(f"B.Cu: added drift route {' -> '.join(str(p) for p in ROUTE)} (0.3 mm) and via pads; "
               f"GND hatch cleared {CU_CLEAR + CUT_MARGIN:.1f} mm round it (clear polarity)")
    write(os.path.join(FAB_OUT, "Gerber", "P2_BASKET-B_Cu.gbr"), L)


def patch_enig(log):
    src = os.path.join(FAB, "Gerber", "P2_BASKET-F_ENIG_Finition.gbr")
    L = read(src)
    a = max_aperture(L) + 1
    block = ["G04 ==== B2 drift pad, added " + STAMP + " ====*", "%LPD*%",
             f"%ADD{a}R,{2 * PAD_H:.6f}X{2 * PAD_H:.6f}*%", f"D{a}*", f"{xy(PAD)}D03*"]
    L = insert_before_m02(header_note(L, "B2 drift contact: modified copy of the KiCad output, " + STAMP), block)
    log.append(f"ENIG: added the 3 x 3 mm drift pad at {PAD}")
    write(os.path.join(FAB_OUT, "Gerber", "P2_BASKET-F_ENIG_Finition.gbr"), L)


def patch_drill(log):
    src = os.path.join(FAB, "NCDrill", "P2_BASKET.drl")
    L = read(src)
    tools = [k for k, l in enumerate(L) if re.match(r"^T\d+$", l)]
    t2 = next(k for k in tools if L[k] == "T2")
    t3 = next(k for k in tools if L[k] == "T3")
    idx = [k for k in range(t2, t3) if L[k] == SIG1_DRILL]
    assert len(idx) == 1, idx
    L = L[:idx[0]] + L[idx[0] + 1:]
    log.append("drill: removed the /Sector0/Sig1 pad hole (T2, Ø0.4) at (589.183, 10.999)")
    t1 = next(k for k, l in enumerate(L) if l == "T1")
    L = L[:t1 + 1] + [f"X{VIA[0]:g}Y{VIA[1]:g}", f"X{D_VIA[0]:g}Y{D_VIA[1]:g}"] + L[t1 + 1:]
    i = next(k for k, l in enumerate(L) if l.startswith("; FORMAT"))
    L = L[:i + 1] + [f"; B2 drift contact: modified copy of the KiCad output, {STAMP}"] + L[i + 1:]
    log.append(f"drill: added vias (T1, Ø0.4) at {VIA} and {D_VIA}")
    write(os.path.join(FAB_OUT, "NCDrill", "P2_BASKET.drl"), L)


def patch_mask(layer, log):
    src = os.path.join(MASKS, f"P2_BASKET-Mask_{layer}_V3B_final.gbr")
    L = read(src)
    block = [f"G04 ==== B2 drift pad, added {STAMP}: resist island (clear) + window over the pad (dark) ====*",
             "%LPC*%"] + rect_region(*ISLAND) + \
            ["%LPD*%"] + rect_region(PAD[0] - WIN_H, PAD[1] - WIN_H, PAD[0] + WIN_H, PAD[1] + WIN_H)
    L = insert_before_m02(L, block)
    i = next(k for k, l in enumerate(L) if l.startswith("%FS"))
    L = L[:i] + [f"G04 B2 drift pad variant of V3B_final, {STAMP} (P2_Revision_2026/pcb/drift_pad_B2/tools/make_b2_files.py)*"] + L[i:]
    write(os.path.join(MASK_OUT, f"P2_BASKET-Mask_{layer}_V3B_final_B2.gbr"), L)
    log.append(f"{layer}: resist island {ISLAND} and {2 * WIN_H:.1f} x {2 * WIN_H:.1f} mm window over the pad")


def mesh_cut(log):
    x0, y0, x1, y1 = PAD[0] - CUT_H, PAD[1] - CUT_H, PAD[0] + CUT_H, PAD[1] + CUT_H
    L = ["G04 P2 BASKET - B2 drift pad: mesh cut-out template*",
         f"G04 cut the mesh along this square when the mesh is trimmed, {STAMP}*",
         "G04 square 10 x 10 mm centred on the drift pad, 3.5 mm from the pad edge*",
         "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*", "%ADD10C,0.100000*%", "D10*",
         f"X{q(x0)}Y{q(y0)}D02*", f"X{q(x1)}Y{q(y0)}D01*", f"X{q(x1)}Y{q(y1)}D01*",
         f"X{q(x0)}Y{q(y1)}D01*", f"X{q(x0)}Y{q(y0)}D01*",
         f"X{q(PAD[0] - 0.5)}Y{q(PAD[1])}D02*", f"X{q(PAD[0] + 0.5)}Y{q(PAD[1])}D01*",
         f"X{q(PAD[0])}Y{q(PAD[1] - 0.5)}D02*", f"X{q(PAD[0])}Y{q(PAD[1] + 0.5)}D01*", "M02*", ""]
    _EOL["eol"] = "\n"
    write(os.path.join(MASK_OUT, "P2_BASKET-MeshCut_B2.gbr"), L)
    log.append(f"mesh cut: {2 * CUT_H:g} x {2 * CUT_H:g} mm square ({x0}, {y0}) - ({x1}, {y1})")


def copy_unchanged(log):
    for rel in ["Gerber/P2_BASKET-Edge_Cuts.gbr", "Gerber/P2_BASKET-User_Drawings.gbr", "Stack_Up_P2..txt"]:
        dst = os.path.join(FAB_OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(FAB, rel), dst)
    log.append("copied unchanged: Edge_Cuts, User_Drawings, Stack_Up")


def main():
    log = []
    patch_fcu(log)
    patch_bcu(log)
    patch_enig(log)
    patch_drill(log)
    patch_mask("M1", log)
    patch_mask("M2", log)
    mesh_cut(log)
    copy_unchanged(log)
    open(os.path.join(OUT, "CHANGES.txt"), "w").write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
