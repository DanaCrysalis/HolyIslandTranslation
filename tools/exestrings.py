#!/usr/bin/env python3
"""
exestrings.py - report / patch the game.exe UI strings that translate_all.py missed.

Field boundaries are derived from the LE relocation table, not guessed. The loader
patches every pointer into the data object from a fixup record, so the set of fixup
targets with object==2 IS the complete set of string starts; anything between one
target and the next is linker alignment padding that nothing can reach.

    python3 exestrings.py fields <game.exe>          # every referenced obj2 string
    python3 exestrings.py report <game.exe>
    python3 exestrings.py apply  <game.exe> [-o out.exe]

Does not verify prior contents, so it is safe on an already-patched exe and is
idempotent. Writes the full field zero-filled, never string+NUL, so stale tail
bytes cannot survive.
"""

import bisect
import shutil
import struct
import sys

LE_HDR = 0x28B8
DATA_BASE = 0x89A00  # file offset of obj2 page 1; ds+N -> file DATA_BASE + N


def fixup_targets(d):
    """Every obj2 offset that something points at, sorted."""
    u32 = lambda o: struct.unpack("<I", d[LE_HDR + o:LE_HDR + o + 4])[0]
    fpt, frt, pages = LE_HDR + u32(0x68), LE_HDR + u32(0x6C), u32(0x14)
    out = set()
    for page in range(1, pages + 1):
        s = struct.unpack("<I", d[fpt + 4 * (page - 1):fpt + 4 * page])[0]
        e = struct.unpack("<I", d[fpt + 4 * page:fpt + 4 * page + 4])[0]
        p, end = frt + s, frt + e
        while p < end:
            src, flags = d[p], d[p + 1]
            stype, ttype = src & 0x0F, flags & 0x03
            q = p + 2
            if src & 0x20:                      # source list
                cnt = d[q]; q += 1 + 2 * cnt
            else:
                q += 2
            if ttype != 0:                      # not an internal reference
                break
            if flags & 0x40:
                obj = struct.unpack("<H", d[q:q + 2])[0]; q += 2
            else:
                obj = d[q]; q += 1
            tgt = None
            if stype != 2:
                if flags & 0x10:
                    tgt = struct.unpack("<I", d[q:q + 4])[0]; q += 4
                else:
                    tgt = struct.unpack("<H", d[q:q + 2])[0]; q += 2
            if obj == 2 and tgt is not None:
                out.add(tgt)
            p = q
    return sorted(out)


def field_of(tg, ds):
    """Bytes available to the string at ds, i.e. distance to the next target."""
    if ds not in tg:
        return None                             # nothing points here: dead tail
    k = bisect.bisect_right(tg, ds)
    return (tg[k] - ds) if k < len(tg) else None


# ds_offset -> (replacement or None, note)
PLAN = {
    0x2CC: ("No",             "demo quit: cancel"),
    0x2D0: ("Yes",            "demo quit: confirm"),
    0x440: ("Got 10000 gold", "GET MONEY cheat feedback"),
    0x4CC: ("ON",             "debug toggle, pairs with the existing 'OFF'"),
    0x4F4: ("Retype",         "name entry: cancel - currently reads 'More'"),
    0x4FC: ("OK",             "name entry: confirm"),
    0x60C: (None,             "more-text arrow glyph, leave alone"),
    0x610: ("Use %s",         "item use"),
    0x798: ("Got %s",         "spell learned"),
    0x7A0: ("%s up!",         "level up"),
    0x7A8: ("%s -> %s: %s",   "combat log; args are actor, target, item"),
    0xAF4: ("Cancel",         "shared cancel: main menu AND quit dialogs"),
    0xAFC: ("Open",           "main menu: confirm"),
}


def _cur(d, off):
    e = d.find(b"\x00", off)
    s = d[off:e]
    try:
        return s, s.decode("big5")
    except UnicodeDecodeError:
        return s, repr(s)


def fields(path):
    d = open(path, "rb").read()
    tg = fixup_targets(d)
    print(f"{len(tg)} distinct obj2 targets\n")
    print(f"{'file':>8} {'ds':>6} {'len':>3} {'field':>5}  text")
    for ds in tg:
        off = DATA_BASE + ds
        if off >= len(d):
            continue
        raw, shown = _cur(d, off)
        if not raw or len(raw) > 60:
            continue
        if not any(0xA1 <= b <= 0xF9 for b in raw):
            continue
        f = field_of(tg, ds)
        print(f"{off:08X} {ds:6X} {len(raw):3d} {str(f):>5}  {shown}")


def report(path):
    d = open(path, "rb").read()
    tg = fixup_targets(d)
    print(f"{'file':>8} {'ds':>6} {'field':>5}  current -> replacement")
    for ds, (repl, note) in sorted(PLAN.items()):
        off = DATA_BASE + ds
        f = field_of(tg, ds)
        raw, shown = _cur(d, off)
        if f is None:
            print(f"{off:08X} {ds:6X}   DEAD  {shown!r}  # unreferenced, skipping")
            continue
        tgt = repl if repl is not None else "(leave)"
        bad = "  !! TOO LONG" if repl and len(repl) >= f else ""
        print(f"{off:08X} {ds:6X} {f:5d}  {shown!r} -> {tgt!r}{bad}   # {note}")


def apply(path, out):
    d = bytearray(open(path, "rb").read())
    tg = fixup_targets(bytes(d))
    if out == path:
        shutil.copyfile(path, path + ".bak")
    n = 0
    for ds, (repl, note) in sorted(PLAN.items()):
        if repl is None:
            continue
        f = field_of(tg, ds)
        if f is None:
            sys.exit(f"ERROR ds+{ds:04X}: nothing references this offset")
        b = repl.encode("ascii")
        if len(b) >= f:
            sys.exit(f"ERROR ds+{ds:04X}: {repl!r} needs {len(b)+1}, field is {f}")
        off = DATA_BASE + ds
        d[off:off + f] = b + b"\x00" * (f - len(b))
        n += 1
    open(out, "wb").write(d)
    print(f"patched {n} strings -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, exe = sys.argv[1], sys.argv[2]
    if cmd == "fields":
        fields(exe)
    elif cmd == "report":
        report(exe)
    elif cmd == "apply":
        o = exe                       # default: patch in place
        if "-o" in sys.argv:
            i = sys.argv.index("-o")
            if i + 1 >= len(sys.argv):
                sys.exit("-o needs a path")
            o = sys.argv[i + 1]
        apply(exe, o)
    else:
        sys.exit(__doc__)
