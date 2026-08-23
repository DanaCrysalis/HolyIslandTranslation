#!/usr/bin/env python3
"""
msgtool.py -- analyse, export and reimport Holy Island (聖光島) .msg files.

Format established from the scan data:

    record size : 253 bytes, fixed
    layout      : [ 49-byte header ][ 204-byte text field ]
    text        : Big5 / CP950, starts at +49
    record N    : file offset N * 253

Fixed-size records mean NO pointer table: translated text is written in place
and padded back out to 204 bytes. Nothing needs repointing.

Subcommands
-----------
  analyse <file|dir>       work out the header layout; column stats, length-
                           field detection, padding byte, sample dumps
  export  <dir> -o f.csv   dump every record to a translation CSV
  import  <dir> f.csv      write the 'english' column back into the files

Typical run:
    python msgtool.py analyse game/map/game31.msg
    python msgtool.py export game/map -o script.csv
    ... translate the 'english' column ...
    python msgtool.py import game/map script.csv --backup

Everything is bytes. Big5 trail bytes include 0x5C and 0x7C, so any tool that
treats this data as text will corrupt it.
"""

import argparse
import csv
import glob
import os
import shutil
import sys
from collections import Counter, defaultdict

REC = 253
TEXT_OFF = 49
TEXT_CAP = REC - TEXT_OFF          # 204

TRAIL = set(range(0x40, 0x7F)) | set(range(0xA1, 0xFF))


def is_lead(b):
    return 0x81 <= b <= 0xFE


# --------------------------------------------------------------------------
def read_records(path):
    with open(path, "rb") as fh:
        data = fh.read()
    n, rem = divmod(len(data), REC)
    return data, n, rem


def extract_text(rec):
    """Pull the Big5 string out of a record's text field.

    Stops at the first byte that can't continue a Big5 string (usually 0x00).
    Returns (text, raw_bytes, terminator_byte).
    """
    field = rec[TEXT_OFF:]
    i = 0
    while i < len(field) - 1:
        if is_lead(field[i]) and field[i + 1] in TRAIL:
            i += 2
        elif 0x20 <= field[i] <= 0x7E:      # allow embedded ASCII
            i += 1
        else:
            break
    raw = field[:i]
    term = field[i] if i < len(field) else None
    try:
        text = raw.decode("cp950")
    except UnicodeDecodeError:
        text = raw.decode("cp950", errors="replace")
    return text, raw, term


# --------------------------------------------------------------------------
def cmd_analyse(args):
    paths = collect(args.target)
    print(f"analysing {len(paths)} file(s)\n")

    col_vals = [Counter() for _ in range(TEXT_OFF)]
    pad_bytes = Counter()
    terminators = Counter()
    len_pairs = []            # (header_byte_index, value) vs text length
    total_recs = 0
    ragged = []

    for path in paths:
        data, n, rem = read_records(path)
        if rem:
            ragged.append((path, len(data), rem))
        for r in range(n):
            rec = data[r * REC:(r + 1) * REC]
            text, raw, term = extract_text(rec)
            total_recs += 1
            for i in range(TEXT_OFF):
                col_vals[i][rec[i]] += 1
            if term is not None:
                terminators[term] += 1
            # padding after the string
            tail = rec[TEXT_OFF + len(raw):]
            if tail:
                pad_bytes[tail[0]] += 1
            len_pairs.append((tuple(rec[:TEXT_OFF]), len(raw), len(text)))

    print(f"records: {total_recs}")
    if ragged:
        print(f"\n!! {len(ragged)} file(s) are not a whole multiple of {REC}:")
        for p, sz, rem in ragged[:8]:
            print(f"   {os.path.basename(p)}: {sz} bytes, {rem} left over")
        print("   (could mean a file header before record 0 -- check below)")

    print("\n--- HEADER COLUMN STATS (offset 0..48) ---")
    print(f"{'off':>4} {'distinct':>9} {'top values (value:count)':<44} note")
    for i in range(TEXT_OFF):
        c = col_vals[i]
        top = "  ".join(f"{v:02X}:{n}" for v, n in c.most_common(3))
        note = ""
        if len(c) == 1:
            note = "CONSTANT"
        elif len(c) > total_recs * 0.5:
            note = "high-variance (id/pointer?)"
        print(f"{i:>4} {len(c):>9} {top:<44} {note}")

    # look for a byte (or 16-bit LE pair) that tracks text length
    print("\n--- LENGTH FIELD DETECTION ---")
    found = False
    for i in range(TEXT_OFF):
        ok8 = ok16 = 0
        for hdr, nbytes, nchars in len_pairs:
            if hdr[i] == nbytes:
                ok8 += 1
            if hdr[i] == nchars:
                ok16 += 1
        if ok8 > total_recs * 0.9:
            print(f"  offset {i}: matches text BYTE length in {ok8}/{total_recs} "
                  f"records  <-- MUST be updated on write")
            found = True
        elif ok16 > total_recs * 0.9:
            print(f"  offset {i}: matches text CHAR length in {ok16}/{total_recs} "
                  f"records  <-- MUST be updated on write")
            found = True
    for i in range(TEXT_OFF - 1):
        ok = sum(1 for hdr, nb, nc in len_pairs
                 if hdr[i] | (hdr[i + 1] << 8) == nb)
        if ok > total_recs * 0.9:
            print(f"  offset {i}-{i+1} (16-bit LE): matches BYTE length in "
                  f"{ok}/{total_recs}  <-- MUST be updated on write")
            found = True
    if not found:
        print("  none found -- header appears not to store the string length.")
        print("  Good news: you can write shorter or longer text freely, so")
        print("  long as it stays inside the 204-byte field.")

    print("\n--- TERMINATOR / PADDING ---")
    print(f"  byte immediately after string: "
          f"{', '.join(f'{v:02X} x{n}' for v, n in terminators.most_common(4))}")
    print(f"  first padding byte           : "
          f"{', '.join(f'{v:02X} x{n}' for v, n in pad_bytes.most_common(4))}")
    print("  -> use the dominant value as the pad byte when reimporting")

    # sample records
    print(f"\n--- SAMPLE RECORDS ({paths[0]}) ---")
    data, n, _ = read_records(paths[0])
    for r in range(min(args.samples, n)):
        rec = data[r * REC:(r + 1) * REC]
        text, raw, _ = extract_text(rec)
        hdr = " ".join(f"{b:02X}" for b in rec[:TEXT_OFF])
        print(f"\n  record {r}  (file offset 0x{r*REC:06X})")
        for k in range(0, TEXT_OFF, 16):
            chunk = rec[k:k + 16]
            hexs = " ".join(f"{b:02X}" for b in chunk)
            print(f"    +{k:02d}  {hexs}")
        print(f"    text ({len(raw)} bytes / {len(text)} chars): {text}")


def cmd_export(args):
    paths = collect(args.target)
    rows = []
    for path in sorted(paths):
        data, n, _ = read_records(path)
        for r in range(n):
            rec = data[r * REC:(r + 1) * REC]
            text, raw, _ = extract_text(rec)
            if not text.strip() and args.skip_empty:
                continue
            rows.append({
                "file": os.path.basename(path),
                "record": r,
                "offset": f"0x{r*REC + TEXT_OFF:08X}",
                "bytes_used": len(raw),
                "bytes_free": TEXT_CAP - len(raw),
                "chinese": text,
                "english": "",
            })
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "record", "offset",
                                           "bytes_used", "bytes_free",
                                           "chinese", "english"])
        w.writeheader()
        w.writerows(rows)
    print(f"exported {len(rows)} records from {len(paths)} files -> {args.out}")
    print(f"text field capacity is {TEXT_CAP} bytes per record")


def cmd_import(args):
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    pad = int(args.pad, 16) if args.pad.startswith("0x") else int(args.pad)

    by_file = defaultdict(list)
    for r in rows:
        if r.get("english", "").strip():
            by_file[r["file"]].append(r)

    if not by_file:
        sys.exit("no rows have an 'english' value -- nothing to do")

    total, skipped = 0, []
    for fname, items in by_file.items():
        path = os.path.join(args.target, fname)
        if not os.path.isfile(path):
            print(f"  ! missing {path}, skipping")
            continue
        if args.backup and not os.path.exists(path + ".bak"):
            shutil.copy2(path, path + ".bak")
        with open(path, "rb") as fh:
            data = bytearray(fh.read())

        for r in items:
            rec_i = int(r["record"])
            eng = r["english"]
            try:
                enc = eng.encode(args.encoding)
            except UnicodeEncodeError as e:
                skipped.append((fname, rec_i, f"encode error: {e}"))
                continue
            if len(enc) > TEXT_CAP:
                skipped.append((fname, rec_i,
                                f"{len(enc)} bytes > {TEXT_CAP} capacity"))
                continue
            base = rec_i * REC + TEXT_OFF
            if base + TEXT_CAP > len(data):
                skipped.append((fname, rec_i, "record beyond EOF"))
                continue
            data[base:base + TEXT_CAP] = enc + bytes([pad]) * (TEXT_CAP - len(enc))
            total += 1

        with open(path, "wb") as fh:
            fh.write(data)

    print(f"wrote {total} records across {len(by_file)} files")
    if skipped:
        print(f"\n{len(skipped)} record(s) SKIPPED:")
        for f, r, why in skipped[:25]:
            print(f"  {f} #{r}: {why}")
        if len(skipped) > 25:
            print(f"  ... and {len(skipped)-25} more")


def collect(target):
    if os.path.isfile(target):
        return [target]
    paths = sorted(glob.glob(os.path.join(target, "*.msg")))
    if not paths:
        sys.exit(f"no .msg files found in {target}")
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyse", help="work out the header layout")
    a.add_argument("target")
    a.add_argument("--samples", type=int, default=3)
    a.set_defaults(func=cmd_analyse)

    e = sub.add_parser("export", help="dump records to a translation CSV")
    e.add_argument("target")
    e.add_argument("-o", "--out", default="script.csv")
    e.add_argument("--skip-empty", action="store_true", default=True)
    e.add_argument("--keep-empty", dest="skip_empty", action="store_false")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import", help="write translations back")
    i.add_argument("target", help="directory holding the .msg files")
    i.add_argument("csv")
    i.add_argument("--pad", default="0x00", help="padding byte (default 0x00)")
    i.add_argument("--encoding", default="ascii",
                   help="output encoding: ascii, cp950, latin-1 (default ascii)")
    i.add_argument("--backup", action="store_true", help="write .bak first")
    i.set_defaults(func=cmd_import)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
