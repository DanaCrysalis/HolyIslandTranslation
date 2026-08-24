#!/usr/bin/env python3
"""
demotool.py -- export and import demo.msg.

demo.msg is the attract-mode prologue and does NOT share the main .msg layout.
msgtool2.py will corrupt it; use this instead.

    GEOMETRY (solved, exact: 32 + 21*243 == 5135 with no remainder)

        32-byte file header
        21 records of 243 bytes:
            [10-byte record header]        byte 1 is the speaker id
            [233-byte text field]
                bytes   0..199   prompt text, NUL-terminated  (199 usable)
                bytes 200..232   3 option slots of 11 bytes

    Compare the main files: 253-byte records of [17][236], with the option
    table also at field offset 200 but in 12-byte slots. Both formats reserve
    the same 200-byte prompt region; only the header and slot widths differ.

    The option slots in every one of the 21 records contain the placeholder
    labels "test", "test2", "test3" -- developer leftovers, identical
    throughout. This tool preserves bytes 200..232 untouched, exactly as
    msgtool2 preserves the main option table, because a writer that pads the
    full 233-byte field would overwrite them.

    python3 demotool.py info   <demo.msg>
    python3 demotool.py export <demo.msg> -o demo_script.csv
    python3 demotool.py import <demo.msg> <csv> [-o out.msg] [--backup]

SPEAKER IDS observed: 1 hero, 2/3 hero narration, 7 boy, 8 guard, 9 old woman.
"""

import argparse
import csv
import os
import shutil
import struct
import sys

FILE_HDR = 32
REC = 243
REC_HDR = 10
FIELD = REC - REC_HDR          # 233
PROMPT_CAP = 199               # bytes 0..199; 200.. is the option table
OPT_BASE = 200
OPT_SLOT = 11
OPT_SLOTS = 3

SPEAKERS = {1: "Hero", 2: "Hero (narration)", 3: "Hero (narration)",
            7: "Boy", 8: "Guard", 9: "Old woman"}


def check(d, path):
    body = len(d) - FILE_HDR
    if body < 0 or body % REC:
        sys.exit(f"{path}: {len(d)} bytes does not fit 32 + k*243")
    return body // REC


def decode(b):
    b = b.split(b"\x00")[0]
    for enc in ("cp950", "ascii"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return "0x" + b.hex()


def blen(s):
    try:
        return len(s.encode("ascii"))
    except UnicodeEncodeError:
        return len(s.encode("cp950"))


def encode(s):
    try:
        return s.encode("ascii")
    except UnicodeEncodeError:
        return s.encode("cp950")


def cmd_info(a):
    d = open(a.msg, "rb").read()
    n = check(d, a.msg)
    print(f"{a.msg}: {len(d)} bytes, {n} records of {REC}")
    print(f"  record header {REC_HDR}B, text field {FIELD}B, "
          f"prompt cap {PROMPT_CAP}B, {OPT_SLOTS} option slots of {OPT_SLOT}B")
    tails = {d[FILE_HDR + i * REC + REC_HDR + OPT_BASE:
               FILE_HDR + i * REC + REC] for i in range(n)}
    print(f"  option-table blocks: {len(tails)} distinct across {n} records")
    for i in range(n):
        b = FILE_HDR + i * REC
        spk = d[b + 1]
        txt = decode(d[b + REC_HDR:b + REC])
        print(f"  {i:2d} spk={spk:02d} {SPEAKERS.get(spk,'?'):16} "
              f"{blen(txt):3d}B  {txt[:40]}")


def cmd_export(a):
    d = open(a.msg, "rb").read()
    n = check(d, a.msg)
    rows = []
    for i in range(n):
        b = FILE_HDR + i * REC
        f = d[b + REC_HDR:b + REC]
        opts = []
        for s in range(OPT_SLOTS):
            o = OPT_BASE + s * OPT_SLOT
            lbl = decode(f[o:o + OPT_SLOT])
            if lbl:
                opts.append(lbl)
        rows.append(dict(file=os.path.basename(a.msg), record=i,
                         speaker=f"{d[b+1]:02d}",
                         who=SPEAKERS.get(d[b + 1], "?"),
                         bytes_used=blen(decode(f)),
                         max_bytes=PROMPT_CAP,
                         options=" | ".join(opts),
                         chinese=decode(f), english=""))
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"exported {len(rows)} records -> {a.out}")
    print(f"prompt capacity per record: {PROMPT_CAP} bytes")


def cmd_import(a):
    d = bytearray(open(a.msg, "rb").read())
    n = check(d, a.msg)
    orig = bytes(d)
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig", newline="")))

    over = []
    for r in rows:
        en = r.get("english") or ""
        if not en.strip():
            continue
        if blen(en) > PROMPT_CAP:
            over.append((r["record"], blen(en)))
    if over:
        print(f"{len(over)} row(s) exceed the {PROMPT_CAP}-byte prompt cap. "
              f"Nothing written.")
        for rec, nb in over:
            print(f"  record {rec}: {nb}B")
        return 1

    written = 0
    for r in rows:
        en = r.get("english") or ""
        if not en.strip():
            continue
        i = int(r["record"])
        if not 0 <= i < n:
            sys.exit(f"record {i} out of range (file has {n})")
        base = FILE_HDR + i * REC + REC_HDR
        enc = encode(en)
        # Write and pad ONLY bytes 0..199. Bytes 200..232 are the option
        # table and must survive untouched.
        d[base:base + PROMPT_CAP + 1] = enc.ljust(PROMPT_CAP + 1, b"\x00")
        written += 1

    assert len(d) == len(orig), "length changed"
    for i in range(n):
        o = FILE_HDR + i * REC + REC_HDR + OPT_BASE
        e = FILE_HDR + i * REC + REC
        assert bytes(d[o:e]) == orig[o:e], f"record {i}: option table changed"
        h = FILE_HDR + i * REC
        assert bytes(d[h:h + REC_HDR]) == orig[h:h + REC_HDR], \
            f"record {i}: record header changed"

    out = a.out or a.msg
    if a.backup and not os.path.exists(out + ".bak") and os.path.exists(out):
        shutil.copy2(out, out + ".bak")
    open(out, "wb").write(bytes(d))
    print(f"wrote {written} record(s) -> {out}")
    print("option tables and record headers verified unchanged")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("info")
    i.add_argument("msg")
    i.set_defaults(func=cmd_info)
    e = sub.add_parser("export")
    e.add_argument("msg")
    e.add_argument("-o", "--out", default="demo_script.csv")
    e.set_defaults(func=cmd_export)
    m = sub.add_parser("import")
    m.add_argument("msg")
    m.add_argument("csv")
    m.add_argument("-o", "--out")
    m.add_argument("--backup", action="store_true")
    m.set_defaults(func=cmd_import)
    a = ap.parse_args()
    sys.exit(a.func(a) or 0)


if __name__ == "__main__":
    main()
