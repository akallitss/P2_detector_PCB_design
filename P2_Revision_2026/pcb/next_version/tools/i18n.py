"""
Figures in another language without touching the drawing code: every matplotlib text is replaced
at draw time by its translation (exact-string table in i18n_fr.json), and the figures are saved as
<name>_fr.png next to the English ones.

    P2_LANG=fr       python3 fig_pcb.py         -> the French figures listed in WANTED
    P2_LANG=collect  python3 fig_pcb.py         -> i18n_strings.json: every text drawn (for the table)

Only the figures in WANTED are written in these modes; the CSV tables are written as usual.
"""
import json
import os

import matplotlib.figure
import matplotlib.text

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.environ.get("P2_LANG", "en")
WANTED = {"pcb_overview", "pcb_corner_A", "pcb_corner_A_steps", "pcb_alignment_marks",
          "pcb_alignment_marks_outer", "pcb_screw_holes"}
SEEN = []


def setup():
    if LANG == "en":
        return
    table = {}
    if LANG != "collect":
        table = json.load(open(os.path.join(HERE, f"i18n_{LANG}.json"), encoding="utf-8"))
    done = set(table.values())                # already translated (texts are drawn more than once)
    draw0, save0 = matplotlib.text.Text.draw, matplotlib.figure.Figure.savefig

    def draw(self, renderer):
        s = self.get_text()
        if s.strip():
            if LANG == "collect":
                SEEN.append(s)
            elif s in table:
                self.set_text(table[s])
            elif any(c.isalpha() for c in s) and s not in MISSING and s not in done:
                MISSING.append(s)
        return draw0(self, renderer)

    def savefig(self, fname, *a, **k):
        base = os.path.splitext(os.path.basename(fname))[0]
        if base not in WANTED:
            return None
        if LANG == "collect":
            self.canvas.draw()               # renders the texts (records them), writes nothing
            return None
        return save0(self, os.path.join(os.path.dirname(fname), f"{base}_{LANG}.png"), *a, **k)
    matplotlib.text.Text.draw = draw
    matplotlib.figure.Figure.savefig = savefig


MISSING = []


def finish():
    if LANG == "collect":
        out = os.path.join(HERE, "i18n_strings.json")
        old = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else []
        keep = list(dict.fromkeys(old + [s for s in SEEN if any(c.isalpha() for c in s)]))
        json.dump(keep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"i18n: {len(keep)} strings in {out}")
    elif LANG != "en" and MISSING:
        print(f"i18n: {len(MISSING)} texts without translation:", *MISSING, sep="\n  ")
