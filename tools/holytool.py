#!/usr/bin/env python3
"""
holytool.py -- inspect and export Holy Island sprite containers.

BOTH FORMATS SHARE A 7-BYTE HEADER
    [u16 width][u16 height][u16 cel_count][u8 flag]

The seventh byte is a FORMAT FLAG, not padding. That was the thing that made
these files look inconsistent:

    GRP flag 0   raw. 7 + count*w*h bytes of 8-bit palette indices.
                 PStat.GRP is 196x314 n=1 flag=0 -> 61551 bytes exactly.
    GRP flag 2   SOLVED. 768-byte palette at +7, then (count + 256) cels:

                     size == 7 + 768 + (count + 256) * w * h

                 Exact on all five samples: demo01/02/03/05.grp (n=304, 575,
                 382, 991) and map035.grp (n=317). The +256 is presumably a
                 shared base tile bank that `count` does not include.
                 The palette is 8-bit RGB, not 6-bit VGA -- components reach
                 255, so do NOT scale it.
    VCT          SOLVED. Sparse sprite with a cel directory:

                     [7-byte header]
                     count * [u32 offset][u32 size]      cel directory
                     per cel: [u16 run_count]
                              run_count * [u16 x][u16 y][u16 len][len bytes]

                 Each run is a horizontal span of palette indices at (x, y);
                 everything not covered by a run is transparent. Verified on
                 menu01.vct: 16x16, 8 cels, directory offsets chain exactly
                 from 0x47 to the 795-byte file end with no slack.

    python3 holytool.py info   <file|dir>
    python3 holytool.py export <file.vct|file.grp> [outdir] [--pal game.pal]
    python3 holytool.py runs   <file.vct> [--cel N]

Export writes PNG if Pillow is present, otherwise a raw indexed .data plus a
.json describing geometry. Import is NOT implemented -- the translation does
not repaint sprites, and writing a format back that is only partly understood
would be a good way to corrupt art silently.
"""

import argparse
import json
import os
import struct
import sys

HDR = 7
PAL = 768        # flag-2 files carry a 256-entry RGB palette at +7
BASE_CELS = 256  # flag-2 `count` excludes a shared base bank of this size


def header(d):
    if len(d) < HDR:
        return None
    w, h, n = struct.unpack_from("<HHH", d, 0)
    return w, h, n, d[6]


def vct_directory(d, n):
    """[(offset, size)] and whether the chain is self-consistent."""
    if len(d) < HDR + 8 * n:
        return None, False
    ents = [struct.unpack_from("<II", d, HDR + 8 * i) for i in range(n)]
    ok = ents[0][0] == HDR + 8 * n
    for i in range(n - 1):
        ok &= ents[i][0] + ents[i][1] == ents[i + 1][0]
    ok &= ents[-1][0] + ents[-1][1] == len(d)
    return ents, ok


def vct_runs(d, off, size):
    """[(x, y, pixels)] for one cel."""
    p = off
    cnt = struct.unpack_from("<H", d, p)[0]
    p += 2
    out = []
    for _ in range(cnt):
        if p + 6 > off + size:
            break
        x, y, ln = struct.unpack_from("<HHH", d, p)
        p += 6
        out.append((x, y, d[p:p + ln]))
        p += ln
    return out


def classify(path):
    d = open(path, "rb").read()
    hd = header(d)
    if not hd:
        return d, None, "too short"
    w, h, n, flag = hd
    ext = os.path.splitext(path)[1].lower()
    if ext == ".vct":
        ents, ok = vct_directory(d, n)
        return d, hd, ("vct, directory consistent" if ok
                       else "vct, DIRECTORY DOES NOT CHAIN")
    raw = HDR + n * w * h
    if flag == 0 and raw == len(d):
        return d, hd, "grp raw"
    pal = HDR + PAL + (n + 256) * w * h
    if flag == 2 and pal == len(d):
        return d, hd, f"grp flag2, palette + {n + 256} cels"
    return d, hd, (f"grp flag{flag} UNKNOWN (raw {raw}, pal-form {pal}, "
                   f"file {len(d)})")


def cmd_info(a):
    targets = []
    if os.path.isdir(a.target):
        for f in sorted(os.listdir(a.target)):
            if os.path.splitext(f)[1].lower() in (".grp", ".vct"):
                targets.append(os.path.join(a.target, f))
    else:
        targets = [a.target]
    for p in targets:
        d, hd, note = classify(p)
        if not hd:
            print(f"{os.path.basename(p):20} {note}")
            continue
        w, h, n, flag = hd
        print(f"{os.path.basename(p):20} {w:4d}x{h:<4d} n={n:<5d} flag={flag}  "
              f"{len(d):8d}B  {note}")


def cmd_runs(a):
    d = open(a.target, "rb").read()
    w, h, n, flag = header(d)
    ents, ok = vct_directory(d, n)
    if not ok:
        print("warning: cel directory does not chain cleanly", file=sys.stderr)
    cels = range(n) if a.cel is None else [a.cel]
    for i in cels:
        off, size = ents[i]
        runs = vct_runs(d, off, size)
        px = sum(len(r[2]) for r in runs)
        print(f"cel {i}: offset 0x{off:X} size {size} -- {len(runs)} run(s), "
              f"{px} pixel(s) of {w * h}")
        for x, y, pix in runs[:a.limit]:
            print(f"    ({x:3d},{y:3d}) len {len(pix):3d}  {pix[:12].hex(' ')}")
        if len(runs) > a.limit:
            print(f"    ... {len(runs) - a.limit} more")


def load_pal(path):
    p = open(path, "rb").read()
    if len(p) < 768:
        sys.exit(f"{path} is {len(p)}B, expected at least 768")
    # DOS VGA palettes are 6-bit; scale if nothing exceeds 63.
    six = max(p[:768]) < 64
    return [tuple(c * 255 // 63 if six else c for c in p[i * 3:i * 3 + 3])
            for i in range(256)]


def cmd_export(a):
    d = open(a.target, "rb").read()
    w, h, n, flag = header(d)
    ext = os.path.splitext(a.target)[1].lower()
    outdir = a.outdir or os.path.splitext(a.target)[0] + "_out"
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(a.target))[0]

    pal = load_pal(a.pal) if a.pal else None
    frames = []
    if ext == ".vct":
        ents, ok = vct_directory(d, n)
        if not ok:
            sys.exit("cel directory does not chain; refusing to export")
        for i in range(n):
            buf = bytearray([a.transparent]) * (w * h)
            for x, y, pix in vct_runs(d, *ents[i]):
                if y < h:
                    s = y * w + x
                    buf[s:s + len(pix)] = pix[:max(0, w - x)]
            frames.append(bytes(buf))
    elif flag == 0 and HDR + n * w * h == len(d):
        for i in range(n):
            s = HDR + i * w * h
            frames.append(d[s:s + w * h])
    elif flag == 2 and HDR + PAL + (n + BASE_CELS) * w * h == len(d):
        if not pal:
            pal = [tuple(d[HDR + i * 3:HDR + i * 3 + 3]) for i in range(256)]
        for i in range(n + BASE_CELS):
            s = HDR + PAL + i * w * h
            frames.append(d[s:s + w * h])
    else:
        sys.exit(f"{a.target}: flag {flag} body layout is not decoded "
                 f"(see the module docstring). Nothing exported.")

    try:
        from PIL import Image
    except ImportError:
        Image = None

    for i, buf in enumerate(frames):
        base = os.path.join(outdir, f"{stem}_{i:03d}")
        if Image and pal:
            im = Image.frombytes("P", (w, h), buf)
            flat = [c for rgb in pal for c in rgb]
            im.putpalette(flat)
            im.save(base + ".png")
        else:
            open(base + ".data", "wb").write(buf)
    meta = dict(source=os.path.basename(a.target), width=w, height=h,
                cels=n, flag=flag, format=ext.lstrip("."),
                transparent_index=a.transparent)
    json.dump(meta, open(os.path.join(outdir, stem + ".json"), "w"), indent=2)
    how = "png" if (Image and pal) else "raw indexed .data"
    print(f"exported {len(frames)} cel(s) as {how} -> {outdir}")
    if not pal:
        print("  (no --pal given, so no colour was applied; "
              "try --pal animate/game.pal)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("info")
    i.add_argument("target")
    i.set_defaults(func=cmd_info)
    r = sub.add_parser("runs")
    r.add_argument("target")
    r.add_argument("--cel", type=int)
    r.add_argument("--limit", type=int, default=8)
    r.set_defaults(func=cmd_runs)
    e = sub.add_parser("export")
    e.add_argument("target")
    e.add_argument("outdir", nargs="?")
    e.add_argument("--pal", help="palette file, e.g. animate/game.pal")
    e.add_argument("--transparent", type=int, default=0)
    e.set_defaults(func=cmd_export)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
