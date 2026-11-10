"""
Figures in French without touching the drawing code (same idea as P2_Revision_2026/pcb/next_version/
tools/i18n.py): every matplotlib text is translated at draw time and the figure is saved as
<name>_fr.png next to the English one.

    P2_LANG=fr       python3 fig_validation.py     -> *_fr.png
    P2_LANG=collect  python3 fig_validation.py     -> i18n_strings.json (every text drawn)

Translation, in order: exact string in i18n_fr.json "exact"; else the regex rules in "rules"
(applied one after the other, so generated labels with numbers are covered); then decimal
points between digits become commas (3.5 -> 3,5).  Texts with letters that no rule changed are
listed at the end ("without translation").
"""
import json
import os
import re

import matplotlib.figure
import matplotlib.text

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.environ.get("P2_LANG", "en")
SEEN, MISSING = [], []
_DEC = re.compile(r"(?<=\d)\.(?=\d)")


def translate(s, table):
    if s in table["exact"]:
        out = table["exact"][s]
    else:
        out, hit = s, False
        for pat, rep in table["rules"]:
            hit = hit or re.search(pat, out) is not None
            out = re.sub(pat, rep, out)
        if not hit and any(c.isalpha() for c in s) and s not in MISSING and s not in table["keep_list"]:
            MISSING.append(s)
    return _DEC.sub(",", out)


def setup():
    if LANG == "en":
        return
    table = {"exact": {}, "rules": [], "keep_list": []}
    if LANG != "collect":
        table.update(json.load(open(os.path.join(HERE, f"i18n_{LANG}.json"), encoding="utf-8")))
    draw0, save0 = matplotlib.text.Text.draw, matplotlib.figure.Figure.savefig
    done = {}

    def draw(self, renderer):
        s = self.get_text()
        if s.strip():
            if LANG == "collect":
                SEEN.append(s)
            elif id(self) not in done or done[id(self)] != s:
                t = translate(s, table)
                self.set_text(t)
                done[id(self)] = t
        return draw0(self, renderer)

    def savefig(self, fname, *a, **k):
        base, ext = os.path.splitext(os.path.basename(fname))
        if LANG == "collect":
            self.canvas.draw()
            return None
        return save0(self, os.path.join(os.path.dirname(fname), f"{base}_{LANG}{ext}"), *a, **k)
    matplotlib.text.Text.draw = draw
    matplotlib.figure.Figure.savefig = savefig


def finish():
    if LANG == "collect":
        out = os.path.join(HERE, "i18n_strings.json")
        old = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else []
        keep = list(dict.fromkeys(old + [s for s in SEEN if any(c.isalpha() for c in s)]))
        json.dump(keep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"i18n: {len(keep)} strings in {out}")
    elif LANG != "en" and MISSING:
        print(f"i18n: {len(MISSING)} texts without translation:", *MISSING, sep="\n  ")
