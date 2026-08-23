#!/usr/bin/env python3
"""
probe.py -- derive record geometry from the positions of Big5 strings.

Given any unknown binary that holds fixed-length records containing Big5
text, this works out the record size and header size instead of assuming
them. Use it on demo.msg, gameobj.dat, mapinfo, map*.dat -- anything whose
layout you don't know yet.

Method:
  1. find every plausible Big5 run and note its byte offset
  2. take the differences between consecutive offsets
  3. the record size is the GCD of those differences (most deltas will be
     the stride itself, the rest small multiples of it)
  4. offset % stride is then constant -- that constant is
     header_size + intra_record_text_offset
  5. file_size == header + N*stride pins down the split

Usage:
    python probe.py demo.msg
    python probe.py gameobj.dat --min-chars 2
    python probe.py "game/map" --glob "*.dat"
"""

import argparse
import glob
import os
import sys
from collections import Counter
from math import gcd
from functools import reduce

TRAIL = set(range(0x40, 0x7F)) | set(range(0xA1, 0xFF))
COMMON = set("的一是不了在人有我他這個們中來上大為和國地到以說時要就出會可"
             "也你對生能而子那得於著下自之年過發後作裡用道行所然家種事成方"
             "多經麼去法學如都同現當沒動面起看定天分還進好小部其些主樣理心"
             "她本前開但因只從想實日者意無力與把民第公此已工使情明性知全三"
             "又關點正外將兩高間由問很最重並物手應向頭文體相見被利什二等或"
             "新己果加月話合回特代內信表化老給世位次度門任常先海通教兒原東"
             "聲提立及比員解水名真論處走義各入幾口認條平系氣題活更別打女變"
             "四神總何數安少才結反受目太量再感建務做接必場件計管期市直資命"
             "山金指許統區保至隊形便空決治展馬科司五基眼書非則聽白卻界達光"
             "放強即像難且權思王象完設式色路記南品住告類求據程北邊死張該交"
             "規萬取格望覺術領共確傳師觀清今切院讓識候帶導爭運笑飛風步改收"
             "根造言聯持組每車親極林服快辦議往元英士證近失轉夫令準始怎呢存"
             "未遠叫台單影具字愛流備兵連呼男微陽幫站錢劍刀藥店買賣魔法經驗")
PUNCT = set("，。！？；：、「」『』（）《》…—～")


def runs(data, min_chars):
    """Yield (offset, text) for plausible Big5 runs."""
    i, n = 0, len(data)
    while i < n - 1:
        if 0x81 <= data[i] <= 0xFE and data[i + 1] in TRAIL:
            s = i
            while i < n - 1 and 0x81 <= data[i] <= 0xFE and data[i + 1] in TRAIL:
                i += 2
            raw = data[s:i]
            if len(raw) // 2 >= min_chars:
                try:
                    t = raw.decode("cp950")
                except UnicodeDecodeError:
                    i = s + 2
                    continue
                score = sum(1 for c in t if c in COMMON or c in PUNCT) / len(t)
                if score >= 0.20:
                    yield s, t
        else:
            i += 1


def analyse(path, min_chars, samples):
    with open(path, "rb") as fh:
        data = fh.read()
    hits = list(runs(data, min_chars))
    size = len(data)

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"size: {size} bytes   text runs found: {len(hits)}")
    if len(hits) < 3:
        print("too few strings to infer geometry")
        return

    offs = [o for o, _ in hits]
    deltas = [b - a for a, b in zip(offs, offs[1:]) if b > a]
    dc = Counter(deltas)
    print("\ncommon deltas:")
    for d, c in dc.most_common(6):
        print(f"   {d:>7}  x{c}")

    stride = reduce(gcd, deltas)
    # GCD can collapse to 1 if a few strings sit mid-record; fall back to the
    # most common delta, which is nearly always the true stride.
    if stride < 8:
        stride = dc.most_common(1)[0][0]
        print(f"\nGCD unreliable ({reduce(gcd, deltas)}); "
              f"using most common delta")
    print(f"\ninferred record size: {stride}")

    mods = Counter(o % stride for o in offs)
    base, hits_at_base = mods.most_common(1)[0]
    print(f"text offset (mod {stride}): {base}  "
          f"({hits_at_base}/{len(offs)} strings agree)")

    if len(mods) > 1:
        print(f"  other residues: "
              f"{', '.join(f'{k}x{v}' for k, v in mods.most_common()[1:5])}")

    print("\nsolving  size == header + N*stride:")
    solved = False
    for n in range(size // stride, 0, -1):
        hdr = size - n * stride
        if 0 <= hdr < stride:
            print(f"   {size} == {hdr} + {n}*{stride}")
            intra = base - hdr
            if intra < 0:
                intra += stride
            print(f"   -> file header {hdr} bytes, {n} records")
            print(f"   -> record header {intra} bytes, "
                  f"text field {stride - intra} bytes")
            solved = True
            break
    if not solved:
        print("   no clean split -- records may be variable length")

    print(f"\nfirst {samples} strings:")
    for o, t in hits[:samples]:
        print(f"   0x{o:06X}  ({o//stride:>4})  {t}")

    print(f"\nfile header bytes: "
          f"{' '.join(f'{b:02X}' for b in data[:min(48, size)])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--glob", default="*.msg")
    ap.add_argument("--min-chars", type=int, default=3)
    ap.add_argument("--samples", type=int, default=8)
    args = ap.parse_args()

    if os.path.isfile(args.target):
        paths = [args.target]
    else:
        paths = sorted(glob.glob(os.path.join(args.target, args.glob)))
    if not paths:
        sys.exit("nothing to probe")
    for p in paths:
        analyse(p, args.min_chars, args.samples)


if __name__ == "__main__":
    main()
