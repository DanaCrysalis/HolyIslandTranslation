#!/usr/bin/env python3
"""
make_pstat_en.py -- write the English status panel into PStat.GRP.

THE FORMAT
    GRP header = [u16 width][u16 height][u16 cel_count][u8 flag]   (7 bytes)

    PStat.GRP is the simple case: 196 x 314, one cel, flag 0, followed by
    w*h*n bytes of 8-bit palette indices. 7 + 1*196*314 == 61551 exactly.

    (flag is NOT padding. Tile sheets such as map035.grp carry flag 2 and a
    different body layout -- see docs/FINDINGS.md. This tool only handles the
    flag-0 raw case, which is all PStat needs.)

THE OVERLAY
    The English lettering was drawn by hand over the Chinese labels. Rather
    than re-render it from a font this tool stores the result as a pixel
    delta in data/pstat_en.bin: zlib over a sequence of

        [u32 file offset][u16 length][length bytes]

    516 runs, 4453 changed pixels, confined to rows 38..272. Only pixels the
    translator drew are in there -- no part of the untouched original art.

    The tool writes the overlay onto a pristine PStat.GRP and verifies the
    result against a stored SHA-256, so a wrong source file or a double
    application fails loudly instead of producing a corrupted panel.

    python3 make_pstat_en.py <gamedir> [out.grp]
    python3 make_pstat_en.py --file <PStat.GRP> [-o out.grp]
    python3 make_pstat_en.py --file <PStat.GRP> --check

MUST overwrite PStat.GRP under that exact name -- it is the only name the exe
loads. Writing PStatEN.GRP alongside it does nothing.
"""

import argparse
import hashlib
import os
import struct
import sys
import zlib

HDR = 7
EXPECT_W, EXPECT_H, EXPECT_N = 196, 314, 1
EXPECT_SIZE = HDR + EXPECT_N * EXPECT_W * EXPECT_H     # 61551

SRC_SHA = "3619dd10c94524f3aa8eeb84a7eafe9887c21b100265de7006c6d511694e6b9c"
DST_SHA = "4761dc4239931f542af2b4f1cb4071c5949360f0d907c52731318b70c309a67a"

DEFAULT_DELTA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir,
    "data", "pstat_en.bin")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def find_pstat(gamedir):
    for p in os.listdir(gamedir):
        if p.lower() == "pstat.grp":
            return os.path.join(gamedir, p)
    sys.exit(f"PStat.GRP not found in {gamedir}")


def check_header(d, path):
    if len(d) < HDR:
        sys.exit(f"{path}: too short for a GRP header")
    w, h, n = struct.unpack_from("<HHH", d, 0)
    flag = d[6]
    if (w, h, n) != (EXPECT_W, EXPECT_H, EXPECT_N):
        sys.exit(f"{path}: header is {w}x{h} n={n}, expected "
                 f"{EXPECT_W}x{EXPECT_H} n={EXPECT_N}")
    if flag != 0:
        sys.exit(f"{path}: flag byte is {flag}, expected 0 (raw). This tool "
                 f"only handles the raw case.")
    if len(d) != EXPECT_SIZE:
        sys.exit(f"{path}: {len(d)} bytes, expected {EXPECT_SIZE}")


def apply(src, delta_path):
    d = bytearray(src)
    blob = zlib.decompress(open(delta_path, "rb").read())
    p, runs = 0, 0
    while p < len(blob):
        off, ln = struct.unpack_from("<IH", blob, p)
        p += 6
        if off + ln > len(d):
            sys.exit(f"delta run at 0x{off:X}+{ln} falls outside the file")
        d[off:off + ln] = blob[p:p + ln]
        p += ln
        runs += 1
    assert len(d) == len(src), "length changed"
    return bytes(d), runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gamedir", nargs="?", help="game directory holding PStat.GRP")
    ap.add_argument("out", nargs="?", help="output path (default: in place)")
    ap.add_argument("--file", help="operate on this PStat.GRP directly")
    ap.add_argument("-o", "--out-file", help="output path when using --file")
    ap.add_argument("--delta", default=DEFAULT_DELTA)
    ap.add_argument("--check", action="store_true",
                    help="report state, write nothing")
    a = ap.parse_args()

    if a.file:
        path, out = a.file, (a.out_file or a.file)
    elif a.gamedir:
        path = find_pstat(a.gamedir)
        out = a.out or path
    else:
        ap.error("give a gamedir or --file")

    src = open(path, "rb").read()
    check_header(src, path)
    h = sha(src)

    if h == DST_SHA:
        print(f"{path} is already the English panel; nothing to do.")
        return 0
    if SRC_SHA != "PRISTINE_SHA_PLACEHOLDER" and h != SRC_SHA:
        sys.exit(f"{path} is neither the pristine nor the patched panel "
                 f"(sha256 {h[:16]}...). Refusing to overlay onto unknown art.")

    if a.check:
        print(f"{path}: pristine, ready to overlay")
        return 0

    if not os.path.exists(a.delta):
        sys.exit(f"overlay not found: {a.delta}")
    new, runs = apply(src, a.delta)

    if DST_SHA != "PATCHED_SHA_PLACEHOLDER" and sha(new) != DST_SHA:
        sys.exit("post-overlay checksum mismatch -- the delta does not match "
                 "this source file")

    open(out, "wb").write(new)
    print(f"applied {runs} pixel run(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
