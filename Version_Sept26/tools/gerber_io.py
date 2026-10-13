"""
Minimal Gerber (RS-274X) reader/writer for the P2 basket insulation masks.

Only the subset used by the KiCad-exported P2_BASKET mask files is handled:
  %FSLAX46Y46%, %MOMM%, %LPD/%LPC%, circular apertures, G01/G02/G03 + G75 arcs,
  G36/G37 regions, D01/D02/D03.

The CEA mask files are *concatenations* of several independent Gerber exports
(ECO1 / User / ECO2), each re-declaring the format spec and re-using the
aperture numbers D10, D11, ...  That is not legal RS-274X (an aperture number
may not be redefined), so when we re-emit we merge everything into a single
spec-compliant file with a globally unique aperture table.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

SCALE = 1_000_000  # 4.6 format, mm  ->  file integer units


@dataclass
class Section:
    """One concatenated Gerber export inside a mask file."""
    header: list[str] = field(default_factory=list)   # G04/%TF lines before the aperture list
    apertures: dict[str, str] = field(default_factory=dict)  # 'D10' -> 'C,0.400000'
    body: list[str] = field(default_factory=list)     # everything after the aperture list
    polarity: str = "D"                               # in effect when the body starts

    # `polarity` matters as much as the coordinates.  The CEA and CERN masks
    # both paint the active area as one dark region and then switch to CLEAR
    # (%LPC%) so the pillars are knocked *out* of it.  Re-emitting those
    # coordinates under DARK polarity paints the pillars in the same colour as
    # the region they sit on: the file parses, the geometry is right, and a
    # viewer shows nothing.


_AD = re.compile(r"^%ADD(\d+)([A-Za-z]+,[^*]*)\*%$")
_DSEL = re.compile(r"^D(\d+)\*$")


def read_sections(path: str) -> list[Section]:
    lines = open(path).read().splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith("%TF.GenerationSoftware")]
    if not starts:
        starts = [0]
    bounds = starts + [len(lines)]
    out = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        chunk = [l for l in lines[a:b] if l.strip() and l.strip() != "M02*"]
        sec = Section()
        state = "head"
        for l in chunk:
            if l in ("%LPD*%", "%LPC*%"):
                # a polarity switch before any drawing sets the body's initial
                # polarity; one in the middle of the body is a real operation
                if state == "body":
                    sec.body.append(l)
                else:
                    sec.polarity = l[3]
                continue
            m = _AD.match(l)
            if m:
                sec.apertures["D" + m.group(1)] = m.group(2)
                state = "ap"
                continue
            if state == "head" and (l.startswith("%") or l.startswith("G04")):
                sec.header.append(l)
                continue
            if l.startswith("G04 APERTURE"):
                state = "ap"
                continue
            state = "body"
            sec.body.append(l)
        out.append(sec)
    return out


def remap(sec: Section, table: dict[str, str]) -> list[str]:
    """Return the section body with its aperture selects rewritten to global D-codes.

    `table` maps the section-local code ('D10') to the global code ('D23').
    Only bare `Dnn*` select lines are touched; D01/D02/D03 operation codes and
    coordinate lines pass through untouched.
    """
    out = []
    for l in sec.body:
        m = _DSEL.match(l)
        if m and int(m.group(1)) >= 10:
            out.append(table[m.group(0)[:-1]] + "*")
        elif l.startswith("G04"):
            out.append(comment(l[4:].rstrip("*")))
        else:
            out.append(l)
    return out


class ApertureTable:
    """Global, collision-free aperture table starting at D10."""

    def __init__(self, start: int = 10):
        self._next = start
        self._by_def: dict[str, str] = {}
        self.order: list[tuple[str, str]] = []

    def get(self, definition: str) -> str:
        """definition e.g. 'C,0.400000' -> 'D10' (reused if already present)."""
        if definition not in self._by_def:
            code = f"D{self._next}"
            self._next += 1
            self._by_def[definition] = code
            self.order.append((code, definition))
        return self._by_def[definition]

    def circle(self, diameter_mm: float) -> str:
        return self.get(f"C,{diameter_mm:.6f}")

    def emit(self) -> list[str]:
        return ["G04 APERTURE LIST*"] + [f"%ADD{c[1:]}{d}*%" for c, d in self.order] + \
               ["G04 APERTURE END LIST*"]


def comment(text: str) -> str:
    """A G04 comment line.

    RS-274X allows printable ASCII in a comment except `*` (the end-of-block
    character) and `%` (the parameter delimiter).  A stray `%` makes a viewer
    open a parameter block that never closes and silently discard the rest of
    the file, so they are substituted here rather than trusted to the caller.
    """
    safe = (text.replace("%", "pct").replace("*", "x")
                .encode("ascii", "replace").decode("ascii"))
    return "G04 " + safe + "*"


def q(v_mm: float) -> int:
    """mm -> 4.6 integer, rounded to the nearest 1 nm."""
    return int(round(v_mm * SCALE))


def flash(x_mm: float, y_mm: float) -> str:
    return f"X{q(x_mm)}Y{q(y_mm)}D03*"


def stroked_disc(x_mm: float, y_mm: float, pen_mm: float) -> list[str]:
    """A filled disc of diameter 2*pen, drawn as two half arcs with a `pen`-wide
    circular aperture on a circle of radius pen/2 - the convention CEA used in
    the V1/V2 masks.  Kept for compatibility; `flash` is preferred."""
    r = pen_mm / 2.0
    return [
        f"X{q(x_mm + r)}Y{q(y_mm)}D02*", "G75*", "G02*",
        f"X{q(x_mm - r)}Y{q(y_mm)}I{q(-r)}J0D01*", "G01*",
        f"X{q(x_mm - r)}Y{q(y_mm)}D02*", "G75*", "G02*",
        f"X{q(x_mm + r)}Y{q(y_mm)}I{q(r)}J0D01*", "G01*",
    ]


# --------------------------------------------------------------------------
# geometry extraction
# --------------------------------------------------------------------------

def section_paths(sec: Section, arc_step_rad: float = 0.02) -> dict[str, list]:
    """Stroked paths of a section, grouped by aperture code, arcs flattened."""
    x = y = 0.0
    cur = None
    g75 = False
    quadrant = "ccw"
    paths: dict[str, list] = {}
    coord = re.compile(
        r"^(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0([123])\*$")
    for l in sec.body:
        m = _DSEL.match(l)
        if m:
            cur = m.group(0)[:-1]
            continue
        if l.startswith("G75"):
            g75 = True
            continue
        if l.startswith("G01"):
            g75 = False
            continue
        if l.startswith("G02"):
            quadrant = "cw"
            continue
        if l.startswith("G03"):
            quadrant = "ccw"
            continue
        m = coord.match(l)
        if not m:
            continue
        nx = int(m.group(1)) / SCALE if m.group(1) else x
        ny = int(m.group(2)) / SCALE if m.group(2) else y
        if m.group(5) == "1":
            if g75 and m.group(3) is not None:
                i = int(m.group(3)) / SCALE
                j = int(m.group(4)) / SCALE
                cx, cy = x + i, y + j
                r = math.hypot(i, j)
                a0 = math.atan2(y - cy, x - cx)
                a1 = math.atan2(ny - cy, nx - cx)
                if quadrant == "cw":
                    while a1 > a0:
                        a1 -= 2 * math.pi
                else:
                    while a1 < a0:
                        a1 += 2 * math.pi
                n = max(2, int(abs(a1 - a0) / arc_step_rad))
                pts = [(cx + r * math.cos(a0 + (a1 - a0) * k / n),
                        cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
            else:
                pts = [(x, y), (nx, ny)]
            paths.setdefault(cur, []).append(pts)
        x, y = nx, ny
    return paths


def chain_loops(segments: list[list[tuple[float, float]]], tol: int = 3):
    """Join polyline fragments that share endpoints into maximal chains."""
    from collections import defaultdict
    key = lambda p: (round(p[0], tol), round(p[1], tol))
    adj = defaultdict(list)
    for i, s in enumerate(segments):
        adj[key(s[0])].append(i)
        adj[key(s[-1])].append(i)
    used = [False] * len(segments)
    loops = []
    for i in range(len(segments)):
        if used[i]:
            continue
        used[i] = True
        path = list(segments[i])
        for _ in range(2):
            while True:
                k = key(path[-1])
                nxt = next((j for j in adj[k] if not used[j]), None)
                if nxt is None:
                    break
                used[nxt] = True
                s = segments[nxt]
                path += (s if key(s[0]) == k else s[::-1])[1:]
            path = path[::-1]
        loops.append(path)
    return loops


def polygon_area(poly) -> float:
    x = [p[0] for p in poly]
    y = [p[1] for p in poly]
    return 0.5 * abs(sum(x[i] * y[i + 1] - x[i + 1] * y[i] for i in range(len(poly) - 1)))
