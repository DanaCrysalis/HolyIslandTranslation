#!/usr/bin/env python3
"""
mapnames.py - dump / patch area-name strings in map###.dat files.

The area name lives in a 20-byte null-padded Big5 field at offset 0x3C.

Usage:
    python3 mapnames.py dump  <dir> [names.csv]  -> writes a CSV of every map name
    python3 mapnames.py apply <dir> names.csv    -> writes translations back

The CSV is always UTF-8 with a BOM, so Excel opens it with the Chinese intact.
""" 

import sys, os, csv, glob, shutil

NAME_OFF = 0x3C
NAME_LEN = 20


def read_name(path):
    with open(path, "rb") as f:
        f.seek(NAME_OFF)
        raw = f.read(NAME_LEN)
    return raw.split(b"\x00")[0]


def find_dats(directory):
    """Every .dat in the directory, case-insensitive, no duplicates."""
    seen = {}
    for p in glob.glob(os.path.join(directory, "*")):
        if p.lower().endswith(".dat"):
            seen.setdefault(os.path.basename(p).lower(), p)
    return [seen[k] for k in sorted(seen)]


def dump(directory, csvpath="names.csv"):
    rows = []
    for p in find_dats(directory):
        raw = read_name(p)
        if not raw:
            continue
        try:
            txt = raw.decode("big5")
        except UnicodeDecodeError:
            txt = raw.decode("big5", errors="replace")
        rows.append([os.path.basename(p), raw.hex(), txt, ""])

    with open(csvpath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["file", "hex", "original", "translation"])
        w.writerows(rows)

    print(f"{len(rows)} names written to {csvpath}")


def apply(directory, csvpath):
    with open(csvpath, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        new = (row.get("translation") or "").strip()
        if not new:
            continue

        path = os.path.join(directory, row["file"])
        if not os.path.exists(path):
            print(f"  !! missing: {row['file']}")
            continue

        # Encode: plain ASCII if possible, else Big5 for Chinese.
        try:
            enc = new.encode("ascii")
        except UnicodeEncodeError:
            enc = new.encode("big5")

        if len(enc) > NAME_LEN - 1:
            print(f"  !! too long ({len(enc)}B, max {NAME_LEN - 1}): {new}")
            continue

        if not os.path.exists(path + ".bak"):
            shutil.copy2(path, path + ".bak")

        with open(path, "r+b") as f:
            f.seek(NAME_OFF)
            f.write(enc.ljust(NAME_LEN, b"\x00"))

        print(f"  {row['file']}: {row.get('original','')} -> {new}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "dump":
        dump(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "names.csv")
    elif cmd == "apply":
        apply(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
