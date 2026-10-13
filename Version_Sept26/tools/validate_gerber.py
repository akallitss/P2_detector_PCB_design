#!/usr/bin/env python3
"""Strict-ish RS-274X syntax check for the generated masks.

Catches the mistakes that actually bite in a mask shop: a redefined or
undefined aperture, a missing or duplicated format spec, a stray token, an
interpolation before any aperture was selected, an unterminated region.
"""
from __future__ import annotations

import re
import sys

OK_PARAM = re.compile(r"^%(FSLAX\d\dY\d\d|MOMM|MOIN|LPD|LPC|TF\.[^*]*|TA\.[^*]*|TD|AM.*|SR.*)\*%$")
AD = re.compile(r"^%ADD(\d+)([A-Z][A-Za-z]*),([\d.X-]+)\*%$")
DSEL = re.compile(r"^D(\d+)\*$")
OP = re.compile(r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0([123])\*$")
GCODE = re.compile(r"^G(0[1234]|3[67]|7[45]|04.*)\*?$")


def check(path):
    errs, warns = [], []
    ap, sel, region, fs, mo = set(), None, False, 0, 0
    nflash = nop = 0
    pol, npol = "D", {"D": 0, "C": 0}
    for n, raw in enumerate(open(path), 1):
        l = raw.rstrip("\n")
        if not l:
            continue
        if l == "M02*":
            continue
        if l.startswith("G04"):
            if not l.endswith("*"):
                errs.append(f"{n}: comment not terminated by '*'")
            inner = l[:-1] if l.endswith("*") else l
            if "%" in inner:
                errs.append(f"{n}: '%' inside a comment - a viewer reads it as the "
                            f"start of a parameter block and drops the rest of the "
                            f"file: {l!r}")
            if "*" in inner:
                errs.append(f"{n}: '*' inside a comment: {l!r}")
            if any(ord(c) < 32 or ord(c) > 126 for c in inner):
                errs.append(f"{n}: non-printable-ASCII character in a comment")
            continue
        m = AD.match(l)
        if m:
            code = int(m.group(1))
            if code < 10:
                errs.append(f"{n}: aperture number {code} is reserved")
            if code in ap:
                errs.append(f"{n}: aperture D{code} redefined")
            ap.add(code)
            continue
        if l.startswith("%"):
            if l.count("%") != 2 or not l.endswith("*%"):
                errs.append(f"{n}: malformed parameter block {l!r}")
                continue
            if OK_PARAM.match(l):
                fs += l.startswith("%FS")
                mo += l.startswith("%MO")
                if l in ("%LPD*%", "%LPC*%"):
                    pol = l[3]
            else:
                errs.append(f"{n}: unrecognised parameter {l!r}")
            continue
        m = DSEL.match(l)
        if m:
            code = int(m.group(1))
            if code not in ap:
                errs.append(f"{n}: D{code} selected but never defined")
            sel = code
            continue
        if GCODE.match(l):
            if l.startswith("G36"):
                if region:
                    errs.append(f"{n}: G36 inside a region")
                region = True
            if l.startswith("G37"):
                if not region:
                    errs.append(f"{n}: G37 without G36")
                region = False
            continue
        m = OP.match(l)
        if m:
            op = m.group(5)
            npol[pol] += 1
            if op == "3":
                nflash += 1
                if region:
                    errs.append(f"{n}: flash inside a region")
                if sel is None:
                    errs.append(f"{n}: flash with no aperture selected")
            elif op == "1":
                nop += 1
                if sel is None and not region:
                    errs.append(f"{n}: interpolation with no aperture selected")
            continue
        errs.append(f"{n}: cannot parse {l!r}")
    if fs != 1:
        errs.append(f"{fs} format specifications (expected exactly 1)")
    if mo != 1:
        errs.append(f"{mo} unit statements (expected exactly 1)")
    if region:
        errs.append("file ends inside a region")
    if not open(path).read().rstrip().endswith("M02*"):
        errs.append("file does not end with M02*")
    if npol["C"] == 0 and nflash > 1000:
        warns.append("a large flash field with no clear-polarity graphics - if "
                     "these are pillars meant to be knocked out of a dark "
                     "region they will be invisible; qc_mask.py rasterises the "
                     "file and checks this exactly")
    return errs, warns, dict(apertures=len(ap), flashes=nflash, draws=nop,
                             dark=npol["D"], clear=npol["C"])


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        errs, warns, st = check(p)
        print(f"{p}\n   {st['apertures']} apertures, {st['flashes']} flashes, "
              f"{st['draws']} interpolations, "
              f"{st['dark']} dark / {st['clear']} clear operations")
        for w_ in warns:
            print("   WARN  " + w_)
        for e in errs[:20]:
            print("   ERROR " + e)
        if len(errs) > 20:
            print(f"   ... and {len(errs)-20} more")
        print("   " + ("OK" if not errs else f"{len(errs)} ERRORS"))
        bad += len(errs)
    sys.exit(1 if bad else 0)
