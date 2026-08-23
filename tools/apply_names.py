#!/usr/bin/env python3
"""
apply_names.py - write English area names into every map###.dat.

The area name is a 20-byte null-padded Big5 field at offset 0x3C.
Budget is 19 bytes plus a terminator; a longer name runs into the linked
sub-map filename at 0x50.

Names are keyed by the ORIGINAL Big5 string, not by filename, so the
map###b.dat night/interior variants that share a name are patched from the
same row automatically. This is why this tool, not `mapnames.py apply`, is
the one the build calls.

Usage:
    python3 apply_names.py <mapdir>                  patch
    python3 apply_names.py <mapdir> --dry            report only, write nothing
    python3 apply_names.py <mapdir> --revert         restore from .bak
    python3 apply_names.py <mapdir> --csv path.csv   use a different table

The table defaults to ../data/map_names.csv relative to this file. Columns:
big5, english, and any others (bytes, area) which are ignored.

Every file gets a .bak on first touch, once only, so re-running never
overwrites a pristine backup with a patched one.
"""

import csv
import glob
import os
import shutil
import sys

NAME_OFF = 0x3C
NAME_LEN = 20

DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "data", "map_names.csv")


def load_names(path):
    """{original Big5 -> English}. Rows with an empty english cell are skipped."""
    if not os.path.exists(path):
        sys.exit(f"name table not found: {path}\n"
                 f"Pass one with --csv, or run `mapnames.py dump` to make a start.")
    names = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            big5 = (row.get("big5") or row.get("original") or "").strip()
            eng = (row.get("english") or row.get("translation") or "").strip()
            if big5 and eng:
                names[big5] = eng
    if not names:
        sys.exit(f"no usable rows in {path} (need a `big5` and an `english` column)")
    return names


def find_dats(directory):
    """Every .dat in the directory, case-insensitive, no duplicates."""
    seen = {}
    for p in glob.glob(os.path.join(directory, "*")):
        if p.lower().endswith(".dat"):
            seen.setdefault(os.path.basename(p).lower(), p)
    return [seen[k] for k in sorted(seen)]


def revert(directory):
    n = 0
    for p in find_dats(directory):
        if os.path.exists(p + ".bak"):
            shutil.copy2(p + ".bak", p)
            n += 1
    print(f"restored {n} files from .bak")


def main(directory, csv_path, dry=False):
    names = load_names(csv_path)

    # Table sanity check before touching anything on disk.
    bad = []
    for k, v in names.items():
        try:
            n = len(v.encode("ascii"))
        except UnicodeEncodeError:
            bad.append((k, v, "not ASCII"))
            continue
        if n > NAME_LEN - 1:
            bad.append((k, v, f"{n}B over the {NAME_LEN - 1}B budget"))
    if bad:
        for _, v, why in bad:
            print(f"  !! {v!r}: {why}")
        return 1

    patched = untranslated = 0
    missing = set()

    for path in find_dats(directory):
        name = os.path.basename(path)
        with open(path, "rb") as f:
            f.seek(NAME_OFF)
            field = f.read(NAME_LEN)

        raw = field.split(b"\x00")[0]
        if not raw:
            continue

        # Already patched on a previous run: field is plain ASCII.
        if all(0x20 <= b < 0x7F for b in raw):
            continue

        try:
            original = raw.decode("big5")
        except UnicodeDecodeError:
            print(f"  !! {name}: field is not valid Big5, skipped")
            continue

        english = names.get(original)
        if english is None:
            missing.add(original)
            untranslated += 1
            continue

        enc = english.encode("ascii").ljust(NAME_LEN, b"\x00")

        print(f"  {name:16s} -> {english}")
        if not dry:
            if not os.path.exists(path + ".bak"):
                shutil.copy2(path, path + ".bak")
            with open(path, "r+b") as f:
                f.seek(NAME_OFF)
                f.write(enc)
        patched += 1

    verb = "would patch" if dry else "patched"
    print(f"\n{verb} {patched} files from {len(names)} table entries")
    if missing:
        # Printed as hex so a cp1252 console cannot choke on it.
        print(f"{untranslated} files had names not in the table:")
        for m in sorted(missing):
            print("  " + m.encode("big5").hex())
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 1)
    d = sys.argv[1]
    args = sys.argv[2:]
    flags = [a.lower() for a in args]
    csv_path = DEFAULT_CSV
    if "--csv" in flags:
        i = flags.index("--csv")
        if i + 1 >= len(args):
            sys.exit("--csv needs a path")
        csv_path = args[i + 1]
    if "--revert" in flags:
        revert(d)
    else:
        sys.exit(main(d, csv_path, dry="--dry" in flags))
