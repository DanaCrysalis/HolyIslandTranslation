#!/usr/bin/env python3
"""
itemfit.py -- check item names against their field, and reconcile the
main-quest names against the canonical table.

THE FIELD
    item table  base 0x8CD68, stride 0x54, 316 entries
    name        offset 0 of each entry, 20-byte NUL-padded Big5 field
                => 19 usable bytes plus a terminator

A name that fills all 20 bytes leaves no terminator and runs into the rest of
the item record. The tools that write here always pad the full field, so the
only real failure mode is an over-long English name.

    python3 itemfit.py <game.exe>                      dump and check the table
    python3 itemfit.py <worksheet.csv>                 check a CSV instead
    python3 itemfit.py <game.exe> --against <csv>      reconcile against the
                                                       canonical item names

The reconcile mode answers the question the playtest raised: for each row of
data/item_names.csv, is the exe's item table already showing the canonical
string, still showing the old inventory string, or something else entirely?
"""

import argparse
import csv
import os
import sys

ITEM_BASE = 0x8CD68
ITEM_STRIDE = 0x54
ITEM_COUNT = 316
NAME_FIELD = 20
NAME_CAP = NAME_FIELD - 1          # 19 usable bytes

EXE_SIZE = 622929


def read_table(path):
    """[(index, file_offset, raw_bytes, decoded_or_None)] for every item."""
    d = open(path, "rb").read()
    if len(d) != EXE_SIZE:
        print(f"  note: {os.path.basename(path)} is {len(d)} bytes, not the "
              f"expected {EXE_SIZE}. Offsets may not line up.", file=sys.stderr)
    out = []
    for i in range(ITEM_COUNT):
        off = ITEM_BASE + i * ITEM_STRIDE
        field = d[off:off + NAME_FIELD]
        if len(field) < NAME_FIELD:
            break
        raw = field.split(b"\x00")[0]
        text = None
        for enc in ("ascii", "cp950"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        out.append((i, off, raw, text))
    return out


def read_csv_names(path):
    """[(label, name)] from any CSV with a name-ish column."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    cols = list(rows[0])
    for c in ("canonical", "english", "translation", "name"):
        if c in cols:
            col = c
            break
    else:
        sys.exit(f"no name column in {path}; columns are {cols}")
    key = "big5" if "big5" in cols else ("chinese" if "chinese" in cols
                                         else ("kind" if "kind" in cols else col))
    return [(r.get(key, ""), (r[col] or "").strip()) for r in rows if (r[col] or "").strip()]


def check(pairs):
    """pairs = [(label, name)]. Returns the number over budget."""
    over = 0
    for label, name in pairs:
        try:
            n = len(name.encode("cp950"))
        except UnicodeEncodeError:
            print(f"  !! {label}: {name!r} is not encodable in cp950")
            over += 1
            continue
        if n > NAME_CAP:
            print(f"  !! {label}: {name!r} is {n}B, over the {NAME_CAP}B field "
                  f"by {n - NAME_CAP}")
            over += 1
    return over


def cmd_exe(path, against):
    table = read_table(path)
    ascii_n = big5_n = empty = 0
    longest = ("", 0)
    bad = []
    for i, off, raw, text in table:
        if not raw:
            empty += 1
            continue
        if len(raw) > NAME_CAP:
            bad.append((i, off, raw))
        if len(raw) > longest[1]:
            longest = (text or raw.hex(), len(raw))
        if all(b < 0x80 for b in raw):
            ascii_n += 1
        else:
            big5_n += 1

    print(f"{len(table)} item slots: {ascii_n} English, {big5_n} still Big5, "
          f"{empty} empty")
    print(f"longest name {longest[1]}B: {longest[0]!r}  (field allows {NAME_CAP})")
    for i, off, raw in bad:
        print(f"  !! item {i} at 0x{off:06X}: {len(raw)}B with no terminator")

    if not against:
        return 1 if bad else 0

    print()
    have = {}
    for i, off, raw, text in table:
        if text:
            have.setdefault(text, []).append(i)

    rows = list(csv.DictReader(open(against, encoding="utf-8-sig", newline="")))
    done = todo = unseen = 0
    for r in rows:
        canon = (r.get("canonical") or "").strip()
        old = (r.get("inventory_old") or "").strip()
        big5 = (r.get("big5") or "").strip()
        if not canon:
            continue
        if canon in have:
            done += 1
            continue
        if old and old in have:
            print(f"  TODO  {big5}  item {have[old][0]}: {old!r} -> {canon!r}")
            todo += 1
        elif big5 and big5 in have:
            print(f"  TODO  {big5}  item {have[big5][0]}: still Big5 -> {canon!r}")
            todo += 1
        else:
            print(f"  ??    {big5}  neither {canon!r} nor {old!r} is in the table")
            unseen += 1
    print(f"\n{done} canonical, {todo} to change, {unseen} not found")
    over = check([(r.get("big5", ""), (r.get("canonical") or "").strip())
                  for r in rows if (r.get("canonical") or "").strip()])
    if over:
        print(f"{over} canonical name(s) do not fit the field")
    return 1 if (bad or over or unseen) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="game.exe, or a CSV of names")
    ap.add_argument("--against", help="canonical item name CSV "
                                      "(e.g. data/item_names.csv)")
    a = ap.parse_args()

    if not os.path.exists(a.target):
        sys.exit(f"not found: {a.target}")

    if a.target.lower().endswith(".csv"):
        if a.against:
            sys.exit("--against only makes sense with an exe")
        pairs = read_csv_names(a.target)
        over = check(pairs)
        print(f"{len(pairs)} name(s) checked, {over} over the {NAME_CAP}B field")
        sys.exit(1 if over else 0)

    sys.exit(cmd_exe(a.target, a.against))


if __name__ == "__main__":
    main()
