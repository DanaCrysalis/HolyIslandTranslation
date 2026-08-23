#!/usr/bin/env python3
"""
prep.py -- classify an exported Holy Island script before translation.

A .msg record's payload is not always dialogue. Roughly 13% of records hold
an asset filename that the engine loads (MStg85.ANM, Map034.DAT, Ship.FTC).
Translating one of those breaks the game. This pass sorts every row into:

    command      pure asset cue -- MUST NOT be translated
    dialogue     ordinary text
    placeholder  dialogue containing a runtime name token (full-width A-F)
    mixed        dialogue with embedded ASCII -- inspect by hand
    empty        no payload

Adds a `max_bytes` budget column and, for commands, blanks the english cell
so msgtool2's import skips them entirely.

Usage:
    python prep.py script.csv -o translate.csv
    python prep.py script.csv -o translate.csv --capacity 236
"""

import argparse
import csv
import re
import sys
from collections import Counter

# Asset cue: a bare filename, optionally with the extensions this engine uses.
CUE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*\.(ANM|DAT|FTC|VCT|GRP|MSG|FAV|PIV|WAV)$',
                 re.IGNORECASE)
ASCII_RUN = re.compile(r'[A-Za-z][A-Za-z0-9_.]{1,}')

def is_placeholder(ch):
    o = ord(ch)
    return 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A


def classify(text):
    t = text.strip()
    if not t:
        return "empty"
    if CUE.match(t):
        return "command"
    if any(is_placeholder(c) for c in t):
        return "placeholder"
    if ASCII_RUN.search(t):
        return "mixed"
    return "dialogue"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_in")
    ap.add_argument("-o", "--out", default="translate.csv")
    ap.add_argument("--capacity", type=int, default=236,
                    help="text field size in bytes (236 main, 233 demo)")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv_in, encoding="utf-8-sig")))
    if not rows:
        sys.exit("empty input")

    counts = Counter()
    out = []
    for r in rows:
        kind = classify(r["chinese"])
        counts[kind] += 1
        r["type"] = kind
        r["max_bytes"] = args.capacity
        r["tokens"] = "".join(sorted({c for c in r["chinese"]
                                      if is_placeholder(c)}))
        # commands: leave english blank so import skips the record
        if kind == "command":
            r["english"] = ""
        out.append(r)

    fields = ["file", "record", "offset", "type", "speaker", "node",
              "tokens", "bytes_used", "max_bytes", "chinese", "english"]
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    print(f"{len(rows)} rows -> {args.out}\n")
    for k in ("dialogue", "placeholder", "mixed", "command", "empty"):
        if counts[k]:
            print(f"  {k:<12} {counts[k]:>5}")
    trans = counts["dialogue"] + counts["placeholder"] + counts["mixed"]
    print(f"\n  translatable  {trans}")
    print(f"  protected     {counts['command'] + counts['empty']}")

    if counts["mixed"]:
        print("\n'mixed' rows (check these by hand):")
        for r in out:
            if r["type"] == "mixed":
                print(f"  {r['file']} rec {r['record']}: {r['chinese'][:70]}")

    if counts["placeholder"]:
        toks = Counter()
        for r in out:
            for c in r["tokens"]:
                toks[c] += 1
        print(f"\nname tokens in use: "
              f"{', '.join(f'{c} x{n}' for c, n in toks.most_common())}")
        print("  -> copy these characters verbatim into the English text")


if __name__ == "__main__":
    main()
