#!/usr/bin/env python3
"""
findnames.py -- locate (and patch) the default party names in Holy Island.

The default hero name is NOT in game.exe -- an exhaustive search for Big5
A4 5A (fan) returns zero hits in the whole 622929-byte image.  It is loaded
from the data tree, so this walks the game directory.

Commands:
    scan    <gamedir> [--name X]     search every encoding variant
    dump    <gamedir> [--max 4]      list every short Big5 string in every file
    fields  <file>                   dump the 20-byte field table at the head
    field   <file> <offset>          show the fields around an offset
    patch   <file> <offset> <text>   write ASCII, zero-padded, with .bak

`scan` tries the plain Big5 bytes, the space-separated form the engine uses
for UI labels (A4 5A 20 B4 A3), and GBK, because a naive search for the bare
four bytes is exactly the thing FINDINGS.md warns will silently return nothing.

`dump` is the fallback when you do not know what you are looking for: it
reports every 1-4 character Big5 run in every file, flagged by whether it sits
on a 20-byte boundary.  Name fields should stand out as aligned 2-char runs.
"""

import argparse
import os
import re
import shutil
import sys

DEFAULT_NAME = "\u51e1\u63d0"  # the hero's default name
FIELD = 20

B5CHAR = rb"[\xa1-\xf9][\x40-\x7e\xa1-\xfe]"
BIG5_RUN = re.compile(b"(?:" + B5CHAR + b"){1,8}")


def variants(name):
    """Every byte form the name might plausibly be stored in."""
    out = []
    try:
        b = name.encode("big5")
        out.append(("big5", b))
        chars = [b[i:i + 2] for i in range(0, len(b), 2)]
        if len(chars) > 1:
            out.append(("big5+spaces", b"\x20".join(chars)))
    except UnicodeEncodeError:
        pass
    try:
        out.append(("gbk", name.encode("gbk")))
    except UnicodeEncodeError:
        pass
    return out


def walk(gamedir):
    for root, _, files in os.walk(gamedir):
        for fn in sorted(files):
            path = os.path.join(root, fn)
            try:
                with open(path, "rb") as fh:
                    yield path, fh.read()
            except OSError as exc:
                print("  !! %s: %s" % (path, exc), file=sys.stderr)


def decode_field(buf, start, size=FIELD):
    raw = bytes(buf[start:start + size])
    body = raw.split(b"\x00", 1)[0]
    try:
        txt = body.decode("big5")
    except UnicodeDecodeError:
        txt = body.decode("latin-1", "replace")
    return raw, txt


def cmd_scan(args):
    vs = variants(args.name)
    print("searching for %s" % args.name)
    for label, pat in vs:
        print("  %-12s %s" % (label, pat.hex(" ")))
    print()
    hits = 0
    for path, buf in walk(args.gamedir):
        rel = os.path.relpath(path, args.gamedir)
        for label, pat in vs:
            start = buf.find(pat)
            while start >= 0:
                hits += 1
                base = start - (start % FIELD)
                _, txt = decode_field(buf, base)
                print("  %-28s 0x%06X  %-12s aligned=%-5s %r"
                      % (rel, start, label, start % FIELD == 0, txt))
                start = buf.find(pat, start + 1)
    print("\n%d hit(s)" % hits)
    if not hits:
        print("Nothing. Run `dump` on the same directory and look for aligned "
              "2-character runs -- the default name may not be what you think.")


def cmd_dump(args):
    for path, buf in walk(args.gamedir):
        rel = os.path.relpath(path, args.gamedir)
        rows = []
        for m in BIG5_RUN.finditer(buf):
            b = m.group()
            if len(b) // 2 > args.max:
                continue
            try:
                s = b.decode("big5")
            except UnicodeDecodeError:
                continue
            off = m.start()
            aligned = off % FIELD == 0
            if args.aligned_only and not aligned:
                continue
            rows.append((off, aligned, s))
        if not rows:
            continue
        print("=== %s (%d bytes, %d run(s))" % (rel, len(buf), len(rows)))
        for off, aligned, s in rows[:args.limit]:
            print("    0x%06X %s %s" % (off, "*" if aligned else " ", s))
        if len(rows) > args.limit:
            print("    ... %d more" % (len(rows) - args.limit))


def cmd_fields(args):
    with open(args.file, "rb") as fh:
        buf = fh.read()
    n = min(args.count, len(buf) // FIELD)
    for i in range(n):
        raw, txt = decode_field(buf, i * FIELD)
        print("0x%04X [%2d] %-22r %s" % (i * FIELD, i, txt, raw.hex(" ")))


def cmd_field(args):
    with open(args.file, "rb") as fh:
        buf = fh.read()
    base = args.offset - (args.offset % FIELD)
    for k in range(-3, 4):
        start = base + k * FIELD
        if start < 0 or start >= len(buf):
            continue
        raw, txt = decode_field(buf, start)
        print("0x%06X %s %-16r %s"
              % (start, "<--" if k == 0 else "   ", txt, raw.hex(" ")))


def cmd_patch(args):
    new = args.text.encode("ascii")
    if len(new) >= args.len:
        sys.exit("replacement is %d bytes, field holds %d incl. terminator"
                 % (len(new), args.len))
    with open(args.file, "rb") as fh:
        buf = bytearray(fh.read())
    end = args.offset + args.len
    if end > len(buf):
        sys.exit("field runs past end of file")
    _, oldtxt = decode_field(buf, args.offset, args.len)
    bak = args.file + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(args.file, bak)
        print("backup -> %s" % bak)
    # exact-length assignment only; anything else shifts the whole file
    buf[args.offset:end] = new + b"\x00" * (args.len - len(new))
    with open(args.file, "wb") as fh:
        fh.write(buf)
    print("0x%06X  %r -> %r" % (args.offset, oldtxt, args.text))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan")
    s.add_argument("gamedir")
    s.add_argument("--name", default=DEFAULT_NAME)
    s.set_defaults(func=cmd_scan)

    d = sub.add_parser("dump")
    d.add_argument("gamedir")
    d.add_argument("--max", type=int, default=4)
    d.add_argument("--limit", type=int, default=40)
    d.add_argument("--aligned-only", action="store_true")
    d.set_defaults(func=cmd_dump)

    fs = sub.add_parser("fields")
    fs.add_argument("file")
    fs.add_argument("--count", type=int, default=16)
    fs.set_defaults(func=cmd_fields)

    f = sub.add_parser("field")
    f.add_argument("file")
    f.add_argument("offset", type=lambda x: int(x, 0))
    f.set_defaults(func=cmd_field)

    p = sub.add_parser("patch")
    p.add_argument("file")
    p.add_argument("offset", type=lambda x: int(x, 0))
    p.add_argument("text")
    p.add_argument("--len", type=int, default=FIELD)
    p.set_defaults(func=cmd_patch)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
