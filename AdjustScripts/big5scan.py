#!/usr/bin/env python3
"""
big5scan.py -- locate Big5/CP950 text inside binary game files.

Written for Taiwanese DOS-era games (Holy Island / 聖光島 and friends), but it
works on any pile of unknown binaries.

Usage:
    python big5scan.py <directory-or-file> [-o report.txt] [-m 4] [--csv strings.csv]

What it does:
  1. Walks the tree and inventories every file (size, extension, first bytes).
  2. Scans each file for runs of valid CP950 double-byte sequences.
  3. Ranks files by how much plausible Chinese text they contain, so you can
     tell the script archive from the sprite sheet in one glance.
  4. Dumps every hit with its byte offset, ready for repointing work.

Everything is done in `bytes`. Big5 trail bytes include 0x5C ("\\") and 0x7C
("|"), so anything that touches this data as text will silently corrupt it.
"""

import argparse
import csv
import os
import sys
from collections import defaultdict

# Big5 lead bytes. 0xA1-0xF9 is the standard plane; 0x81-0xA0 and 0xFA-0xFE
# are the ETen / user-defined extension areas, which games did sometimes use
# for custom glyphs, so we accept them but track them separately.
STD_LEAD = range(0xA1, 0xFA)
EXT_LEAD = list(range(0x81, 0xA1)) + list(range(0xFA, 0xFF))
TRAIL = set(range(0x40, 0x7F)) | set(range(0xA1, 0xFF))


def is_lead(b):
    return 0x81 <= b <= 0xFE


def plausible(text):
    """Reject runs that decode but are obviously not prose.

    Random graphics data throws off valid-looking Big5 pairs fairly often. Real
    text is dominated by CJK ideographs and full-width punctuation, so we
    require most of the run to fall in those ranges.
    """
    if not text:
        return False
    good = 0
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF:          # CJK unified ideographs
            good += 1
        elif 0x3000 <= o <= 0x303F:        # CJK punctuation
            good += 1
        elif 0xFF00 <= o <= 0xFFEF:        # full-width forms
            good += 1
        elif 0x2000 <= o <= 0x206F:        # general punctuation (— … “ ”)
            good += 1
    return good / len(text) >= 0.75


def scan(data, min_chars):
    """Yield (offset, text, used_ext_plane) for each plausible Big5 run."""
    i = 0
    n = len(data)
    while i < n - 1:
        if is_lead(data[i]) and data[i + 1] in TRAIL:
            start = i
            ext = False
            while i < n - 1 and is_lead(data[i]) and data[i + 1] in TRAIL:
                if data[i] in EXT_LEAD:
                    ext = True
                i += 2
            raw = data[start:i]
            if len(raw) // 2 >= min_chars:
                try:
                    text = raw.decode("cp950")
                except UnicodeDecodeError:
                    i = start + 2
                    continue
                if plausible(text):
                    yield start, text, ext
        else:
            i += 1


def ascii_runs(data, min_len=6):
    """Printable ASCII runs -- catches filenames, format strings, menu labels."""
    out, cur, start = [], bytearray(), 0
    for idx, b in enumerate(data):
        if 0x20 <= b <= 0x7E:
            if not cur:
                start = idx
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append((start, cur.decode("ascii")))
            cur = bytearray()
    if len(cur) >= min_len:
        out.append((start, cur.decode("ascii")))
    return out


def main():
    ap = argparse.ArgumentParser(description="Find Big5 text in binary files.")
    ap.add_argument("target", help="directory or single file to scan")
    ap.add_argument("-o", "--out", default="big5_report.txt", help="report path")
    ap.add_argument("-m", "--min-chars", type=int, default=4,
                    help="minimum consecutive Chinese characters (default 4)")
    ap.add_argument("--csv", help="also write every hit to this CSV")
    ap.add_argument("--max-show", type=int, default=40,
                    help="max sample lines printed per file (default 40)")
    ap.add_argument("--ascii", action="store_true",
                    help="also report ASCII strings")
    args = ap.parse_args()

    paths = []
    if os.path.isfile(args.target):
        paths = [args.target]
    else:
        for root, _, files in os.walk(args.target):
            for f in sorted(files):
                paths.append(os.path.join(root, f))

    if not paths:
        sys.exit(f"nothing found at {args.target}")

    results = []
    by_ext = defaultdict(list)
    csv_rows = []

    for path in paths:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as e:
            print(f"  ! skipping {path}: {e}", file=sys.stderr)
            continue

        hits = list(scan(data, args.min_chars))
        chars = sum(len(t) for _, t, _ in hits)
        coverage = (chars * 2 / len(data) * 100) if data else 0.0
        ext = os.path.splitext(path)[1].lower() or "(none)"
        by_ext[ext].append((path, data[:16]))

        results.append({
            "path": path,
            "size": len(data),
            "hits": hits,
            "chars": chars,
            "coverage": coverage,
            "header": data[:16],
            "ascii": ascii_runs(data) if args.ascii else [],
        })

        if args.csv:
            for off, text, ext_plane in hits:
                csv_rows.append([path, f"0x{off:08X}", off, len(text),
                                 "ext" if ext_plane else "std", text])

    results.sort(key=lambda r: r["chars"], reverse=True)

    with open(args.out, "w", encoding="utf-8") as rep:
        rep.write("=" * 72 + "\n")
        rep.write("BIG5 SCAN REPORT\n")
        rep.write(f"root: {os.path.abspath(args.target)}\n")
        rep.write(f"files scanned: {len(results)}   min run: {args.min_chars} chars\n")
        rep.write("=" * 72 + "\n\n")

        rep.write("--- RANKED BY CHINESE CHARACTER COUNT ---\n")
        rep.write(f"{'chars':>9}  {'cover':>6}  {'size':>10}  file\n")
        for r in results:
            if r["chars"] == 0:
                continue
            rep.write(f"{r['chars']:>9}  {r['coverage']:>5.1f}%  "
                      f"{r['size']:>10}  {r['path']}\n")
        rep.write("\n")

        rep.write("--- FILE HEADERS BY EXTENSION (spot the archive format) ---\n")
        for ext in sorted(by_ext):
            rep.write(f"\n[{ext}]  {len(by_ext[ext])} file(s)\n")
            for path, head in by_ext[ext][:8]:
                hexs = " ".join(f"{b:02X}" for b in head)
                asc = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in head)
                rep.write(f"  {hexs}  |{asc}|  {os.path.basename(path)}\n")
        rep.write("\n")

        rep.write("--- SAMPLES ---\n")
        for r in results:
            if r["chars"] == 0 and not r["ascii"]:
                continue
            rep.write(f"\n### {r['path']}  ({r['size']} bytes, "
                      f"{r['chars']} chars, {r['coverage']:.1f}% coverage)\n")
            for off, text, ext_plane in r["hits"][:args.max_show]:
                mark = " *EXT*" if ext_plane else ""
                rep.write(f"  0x{off:08X}{mark}  {text}\n")
            if len(r["hits"]) > args.max_show:
                rep.write(f"  ... and {len(r['hits']) - args.max_show} more\n")
            if r["ascii"]:
                rep.write("  -- ascii --\n")
                for off, s in r["ascii"][:15]:
                    rep.write(f"  0x{off:08X}  {s}\n")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["file", "offset_hex", "offset_dec", "length",
                        "plane", "text"])
            w.writerows(csv_rows)

    top = [r for r in results if r["chars"] > 0][:12]
    print(f"\nScanned {len(results)} files. Report: {args.out}")
    if args.csv:
        print(f"Strings CSV: {args.csv} ({len(csv_rows)} hits)")
    if top:
        print("\nMost text-dense files:")
        for r in top:
            print(f"  {r['chars']:>8} chars  {r['coverage']:>5.1f}%  {r['path']}")
    else:
        print("\nNo plausible Big5 found -- the data is likely compressed.")


if __name__ == "__main__":
    main()
