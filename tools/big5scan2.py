#!/usr/bin/env python3
"""
big5scan2.py -- locate real Big5/CP950 prose inside binary game files.

Replaces big5scan.py, whose filter was useless: it demanded that decoded runs
be mostly CJK ideographs, but the Big5 standard plane IS mostly CJK
ideographs, so random 256-colour VGA data passed at ~100%.

The discriminator here is character FREQUENCY, not character class. Real
Chinese prose draws heavily on a few hundred characters (的是不了在我你...);
random bytes draw uniformly across ~13,000. Measured over a whole file:

    graphics / sprite / animation data ....  0.5% -  3% common
    real dialogue or script data .......... 20%  - 55% common

Files are ranked by that ratio, so the sort is right before any strings are
written out.

Usage:
    python big5scan2.py <dir> --csv strings.csv
    python big5scan2.py <dir> --signal 0.10 --top 25
    python big5scan2.py game/map/somefile.dat -v      # single-file detail

All I/O is in `bytes`. Big5 trail bytes include 0x5C ("\\") and 0x7C ("|"),
so any tool that handles this data as text will silently corrupt it.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

# --------------------------------------------------------------------------
# Big5 structure
# --------------------------------------------------------------------------
TRAIL = set(range(0x40, 0x7F)) | set(range(0xA1, 0xFF))
EXT_LEAD = set(range(0x81, 0xA1)) | set(range(0xFA, 0xFF))


def is_lead(b):
    return 0x81 <= b <= 0xFE


# --------------------------------------------------------------------------
# Frequency data: the ~500 most common Traditional Chinese characters.
# Membership in this set is the entire trick.
# --------------------------------------------------------------------------
COMMON = set(
    "的一是不了在人有我他這個們中來上大為和國地到以說時要就出會可也你對生"
    "能而子那得於著下自之年過發後作裡用道行所然家種事成方多經麼去法學如都"
    "同現當沒動面起看定天分還進好小部其些主樣理心她本前開但因只從想實日軍"
    "者意無力它與長把機十民第公此已工使情明性知全三又關點正業外將兩高間由"
    "問很最重並物手應戰向頭文體政美相見被利什二等產或新己制身果加西斯月話"
    "合回特代內信表化老給世位次度門任常先海通教兒原東聲提立及比員解水名真"
    "論處走義各入幾口認條平系氣題活爾更別打女變四神總何電數安少報才結反受"
    "目太量再感建務做接必場件計管期市直德資命山金指克許統區保至隊形社便空"
    "決治展馬科司五基眼書非則聽白卻界達光放強即像難且權思王象完設式色路記"
    "南品住告類求據程北邊死張該交規萬取拉格望覺術領共確傳師觀清今切院讓識"
    "候帶導爭運笑飛風步改收根幹造言聯持組每濟車親極林服快辦議往元英士證近"
    "失轉夫令準布始怎呢存未遠叫台單影具羅字愛流備兵連呼男微陽幫站錢province"
    "師父母兄弟姐妹村城鎮王子公主劍刀盾甲藥草店買賣攻擊防禦魔法經驗等級狀態"
)
# strip the accidental latin from the block above
COMMON = {c for c in COMMON if ord(c) > 0x2000}

# Full-width punctuation. Its presence is a very strong positive signal --
# dialogue is full of 「」，。！？ and noise essentially never produces them
# in clusters.
PUNCT = set("，。！？；：、「」『』（）《》〈〉…—～·【】")


def classify(text):
    """Return (common_ratio, punct_ratio, distinct_ratio) for a decoded run."""
    if not text:
        return 0.0, 0.0, 1.0
    n = len(text)
    common = sum(1 for c in text if c in COMMON)
    punct = sum(1 for c in text if c in PUNCT)
    distinct = len(set(text))
    return common / n, punct / n, distinct / n


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------
def raw_runs(data, min_chars=3):
    """Yield (offset, decoded_text, used_ext_plane) for structurally valid runs.

    No quality filtering here -- this is the raw candidate pool, which the
    file-level statistics are computed over.
    """
    i, n = 0, len(data)
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
                    yield start, raw.decode("cp950"), ext
                except UnicodeDecodeError:
                    pass
        else:
            i += 1


def file_signal(runs):
    """Fraction of all decoded characters in a file that are common ones."""
    total = 0
    common = 0
    punct = 0
    for _, text, _ in runs:
        total += len(text)
        common += sum(1 for c in text if c in COMMON)
        punct += sum(1 for c in text if c in PUNCT)
    if not total:
        return 0.0, 0.0, 0
    return common / total, punct / total, total


def keep_run(text, min_common, max_len):
    """Per-run filter, applied only inside files that already look texty."""
    n = len(text)
    if n > max_len:
        # Real script is chopped up by terminators and control bytes. A
        # 400-character unbroken run is graphics data.
        return False
    cr, pr, dr = classify(text)
    if pr >= 0.08:            # dialogue punctuation present -> accept
        return True
    if cr < min_common:
        return False
    if n >= 12 and dr > 0.95:  # long run, every char unique -> noise
        return False
    return True


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Find real Big5 prose in binary files (frequency-filtered).")
    ap.add_argument("target", help="directory or single file")
    ap.add_argument("-o", "--out", default="big5_report2.txt")
    ap.add_argument("--csv", help="write filtered hits to this CSV")
    ap.add_argument("--signal", type=float, default=0.08,
                    help="min file-level common-char ratio to treat a file as "
                         "text-bearing (default 0.08; graphics sit near 0.02)")
    ap.add_argument("--min-common", type=float, default=0.20,
                    help="min per-run common-char ratio (default 0.20)")
    ap.add_argument("--min-chars", type=int, default=3)
    ap.add_argument("--max-run", type=int, default=80,
                    help="runs longer than this are rejected as noise")
    ap.add_argument("--min-total", type=int, default=100,
                    help="ignore files with fewer than this many decoded chars")
    ap.add_argument("--top", type=int, default=30, help="files to detail")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print every kept hit to stdout")
    args = ap.parse_args()

    if os.path.isfile(args.target):
        paths = [args.target]
    else:
        paths = [os.path.join(r, f)
                 for r, _, fs in os.walk(args.target) for f in sorted(fs)]
    if not paths:
        sys.exit(f"nothing found at {args.target}")

    records = []
    for path in paths:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as e:
            print(f"  ! {path}: {e}", file=sys.stderr)
            continue
        if not data:
            continue

        runs = list(raw_runs(data, args.min_chars))
        sig, punct_sig, total = file_signal(runs)

        kept = []
        if sig >= args.signal and total >= args.min_total:
            seen = set()
            for off, text, ext in runs:
                if keep_run(text, args.min_common, args.max_run):
                    kept.append((off, text, ext))
                    seen.add(text)

        records.append({
            "path": path,
            "size": len(data),
            "signal": sig,
            "punct": punct_sig,
            "total": total,
            "kept": kept,
            "header": data[:16],
        })

    records.sort(key=lambda r: (r["signal"], len(r["kept"])), reverse=True)
    texty = [r for r in records if r["kept"]]

    # ---------------- report ----------------
    with open(args.out, "w", encoding="utf-8") as rep:
        rep.write("BIG5 SCAN v2 -- frequency filtered\n")
        rep.write(f"root: {os.path.abspath(args.target)}\n")
        rep.write(f"files: {len(records)}   text-bearing: {len(texty)}\n")
        rep.write(f"file signal threshold: {args.signal:.2%}\n\n")

        rep.write("--- ALL FILES BY SIGNAL (common-char ratio) ---\n")
        rep.write(f"{'signal':>7} {'punct':>7} {'chars':>9} {'kept':>7}  file\n")
        for r in records:
            if r["total"] < args.min_total:
                continue
            rep.write(f"{r['signal']:>6.1%} {r['punct']:>6.1%} "
                      f"{r['total']:>9} {len(r['kept']):>7}  {r['path']}\n")

        rep.write("\n--- EXTRACTED TEXT ---\n")
        for r in texty[:args.top]:
            rep.write(f"\n### {r['path']}\n")
            rep.write(f"    {r['size']} bytes | signal {r['signal']:.1%} | "
                      f"punct {r['punct']:.1%} | {len(r['kept'])} strings\n")
            hexs = " ".join(f"{b:02X}" for b in r["header"])
            rep.write(f"    header: {hexs}\n")
            for off, text, ext in r["kept"]:
                mark = " *EXT*" if ext else ""
                rep.write(f"  0x{off:08X}{mark}  {text}\n")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["file", "offset_hex", "offset_dec", "length", "text"])
            for r in texty:
                for off, text, _ in r["kept"]:
                    w.writerow([r["path"], f"0x{off:08X}", off, len(text), text])

    # ---------------- console ----------------
    print(f"\nScanned {len(records)} files -> {args.out}")
    if not texty:
        print("\nNo file cleared the signal threshold.")
        print("Either the script is compressed, or lower --signal (try 0.05)")
        print("and re-check. Highest signals seen:")
        for r in records[:8]:
            if r["total"] >= args.min_total:
                print(f"  {r['signal']:>6.1%}  {r['path']}")
        return

    print("\nText-bearing files (ranked by common-char signal):")
    print(f"{'signal':>7} {'punct':>7} {'strings':>8}  file")
    for r in texty[:args.top]:
        print(f"{r['signal']:>6.1%} {r['punct']:>6.1%} "
              f"{len(r['kept']):>8}  {r['path']}")

    rejected = [r for r in records
                if r["total"] >= args.min_total and not r["kept"]]
    print(f"\n{len(rejected)} files rejected as noise "
          f"(median signal ~{sorted(x['signal'] for x in rejected)[len(rejected)//2]:.1%})"
          if rejected else "")

    if args.verbose:
        for r in texty[:args.top]:
            print(f"\n### {r['path']}")
            for off, text, _ in r["kept"][:60]:
                print(f"  0x{off:08X}  {text}")


if __name__ == "__main__":
    main()
