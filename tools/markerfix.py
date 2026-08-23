#!/usr/bin/env python3
"""
markerfix.py -- find runtime substitution markers that will run into the
words around them.

The fullwidth letters Ａ-Ｆ inside .MSG text are control markers, not text:

    Ａ Ｂ Ｃ Ｄ  (A2CF-A2D2)  party member 0-3
    Ｅ          (A2D3)       item name
    Ｆ          (A2D4)       price

The engine substitutes them with NO surrounding whitespace, so whatever sits
next to the marker in the stored text sits directly against the substituted
value at runtime. `Ｅsells` renders as `Iron Swordsells`. Equally, a space
that should not be there is just as wrong: `Ａ 's sword` renders as
`Fanti 's sword`.

The rule this encodes:

    marker followed by a letter or digit  -> insert a space
    marker preceded by a letter or digit  -> insert a space
    marker followed by SPACE + closing punctuation, a possessive, or a
        contraction  -> remove the space

Nothing else is touched. Deliberate double spaces (used in the shop lines to
push the price onto its own visual column) survive, because a space is not a
letter or digit.

    python3 markerfix.py report <csv> [--col english]
    python3 markerfix.py fix    <csv> [-o out.csv] [--col english]

Run this BEFORE `textflow.py reflow`: reflow pads to the 30-byte line grid and
inserting a space afterwards shifts every later break in the record.
"""

import argparse
import csv
import re
import sys

MARKERS = "ＡＢＣＤＥＦ"
COL = "english"

# A marker followed immediately by a word character.
AFTER = re.compile(f"([{MARKERS}])(?=[A-Za-z0-9])")
# A word character followed immediately by a marker.
BEFORE = re.compile(f"(?<=[A-Za-z0-9])(?=[{MARKERS}])")
# Marker, then a space that should not be there: before closing punctuation,
# a possessive/contraction, or a closing bracket.
TIGHTEN = re.compile(f"([{MARKERS}]) +(?=(?:'[a-z]|[.,!?;:)\\]}}]))")


def fix_text(t):
    """Return (fixed, [descriptions of what changed])."""
    notes = []
    out = TIGHTEN.sub(r"\1", t)
    if out != t:
        notes.append("removed a space before punctuation or a possessive")
    t2 = AFTER.sub(r"\1 ", out)
    if t2 != out:
        notes.append("added a space after a marker")
    out = t2
    t2 = BEFORE.sub(" ", out)
    if t2 != out:
        notes.append("added a space before a marker")
    return t2, notes


def rows_of(path, col):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    if col not in rows[0]:
        sys.exit(f"no `{col}` column in {path}; columns are {list(rows[0])}")
    return rows


def show(t):
    """Make the marker visible in a terminal that may not have the font."""
    for i, ch in enumerate(MARKERS):
        t = t.replace(ch, f"<{chr(ord('A') + i)}>")
    return t


def cmd_report(a):
    rows = rows_of(a.csv, a.col)
    hits = 0
    for r in rows:
        t = r[a.col] or ""
        if not any(c in t for c in MARKERS):
            continue
        new, notes = fix_text(t)
        if new == t:
            continue
        hits += 1
        print(f"{r.get('file', '?')}:{r.get('record', '?')}  {'; '.join(notes)}")
        print(f"    - {show(t)}")
        print(f"    + {show(new)}")
    total = sum(1 for r in rows if any(c in (r[a.col] or "") for c in MARKERS))
    print(f"\n{hits} row(s) need fixing, out of {total} carrying a marker")
    return 1 if hits else 0


def cmd_fix(a):
    rows = rows_of(a.csv, a.col)
    changed = 0
    for r in rows:
        t = r[a.col] or ""
        if not any(c in t for c in MARKERS):
            continue
        new, _ = fix_text(t)
        if new != t:
            r[a.col] = new
            changed += 1
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{changed} row(s) fixed -> {a.out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("csv")
    r.set_defaults(func=cmd_report)
    f = sub.add_parser("fix")
    f.add_argument("csv")
    f.add_argument("-o", "--out", default="markerfixed.csv")
    f.set_defaults(func=cmd_fix)
    for p in (r, f):
        p.add_argument("--col", default=COL,
                       help=f"column to operate on (default {COL}; use "
                            f"`chinese` on a fresh msgtool2 export)")
    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
