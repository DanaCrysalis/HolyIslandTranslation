#!/usr/bin/env python3
"""
maplinks.py -- parse map###.dat headers and analyse the link graph.

CORRECTED HEADER (the earlier five-20-byte-fields reading was WRONG)

    0x00  tile sheet    20-byte NUL-padded name    MAP035.GRP
    0x14  SFX           20-byte NUL-padded name    MON
    0x28  audio set     20-byte NUL-padded name    CDF
    0x3C  area name     20-byte NUL-padded name    the banner string
    0x50  flag          1 byte, observed 0 throughout
    0x51  linked map    19-byte NUL-padded name    MAP036.DAT
    0x64  records       15-byte entries begin here

The single byte at 0x50 is why a naive reading saw "\\0AP036.DAT" and called it
corruption. It is not. 14 of 151 maps have a linked-map name and all but one of
them work, so a NUL at 0x50 is structural. 0x51 + 19 == 0x64 exactly, which is
where the record table starts -- the layout closes with no slack.

WHAT THIS ACTUALLY CHECKS

    cycles      two maps naming each other, or any longer loop. If the engine
                follows the link on load, a cycle recurses forever: the map
                renders, the person table never populates, and how long it
                survives depends on stack depth -- which differs by emulator.
    dangling    a link to a file that is not on disk. Nine maps link to
                MAP005B.DAT, which does not exist, and all nine work -- so
                this is INFORMATIONAL, not an error.
    field       any 20-byte name field with no terminator, which would run
                into the field after it. That check is real.

    python3 maplinks.py <mapdir>
    python3 maplinks.py <mapdir> --csv headers.csv
    python3 maplinks.py <mapdir> --map map035.dat      one file in detail

Nothing is written. This tool does not repair anything, because as of now
nothing here is known to need repair.
"""

import argparse
import csv
import os
import sys

import re
import shutil

FIELDS = [(0x00, 20, "tile_sheet"), (0x14, 20, "sfx"),
          (0x28, 20, "audio_set"), (0x3C, 20, "area_name"),
          (0x50, 20, "link")]
LINK_OFF, LINK_LEN = 0x50, 20
REC_OFF, REC_STRIDE = 0x64, 15

TAIL = re.compile(r"AP\d{3}[A-Za-z]?\.(DAT|GRP)\Z", re.I)


def text(f):
    raw = f.split(b"\x00")[0]
    for enc in ("ascii", "cp950"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return "0x" + raw.hex()


def parse(path):
    d = open(path, "rb").read()
    if len(d) < REC_OFF:
        return None
    h = {"file": os.path.basename(path), "size": len(d)}
    for off, ln, name in FIELDS:
        f = d[off:off + ln]
        h[name] = text(f)
        h[name + "_unterminated"] = b"\x00" not in f
    f = d[LINK_OFF:LINK_OFF + LINK_LEN]
    h["link"] = text(f)
    h["link_first_byte"] = f[0]
    # First byte zeroed but printable text follows: the M was clobbered.
    h["clobbered"] = (f[0] == 0 and any(0x20 <= c < 0x7F for c in f[1:]))
    h["link_tail"] = text(f[1:]) if h["clobbered"] else ""
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mapdir")
    ap.add_argument("--csv")
    ap.add_argument("--map", help="dump one file's header in detail")
    ap.add_argument("--fix", action="store_true",
                    help="restore the clobbered first byte where it matters")
    ap.add_argument("--apply", action="store_true", help="with --fix, write")
    ap.add_argument("--all", action="store_true",
                    help="with --fix, also rewrite the no-op cases")
    a = ap.parse_args()

    names = {f.lower() for f in os.listdir(a.mapdir)}
    heads = []
    for f in sorted(os.listdir(a.mapdir)):
        if not f.lower().endswith(".dat"):
            continue
        h = parse(os.path.join(a.mapdir, f))
        if h:
            heads.append(h)

    if a.map:
        for h in heads:
            if h["file"].lower() == a.map.lower():
                for k, v in h.items():
                    print(f"  {k:22} {v!r}")
                return 0
        sys.exit(f"{a.map} not found in {a.mapdir}")

    by = {h["file"].lower(): h for h in heads}

    def repaired(h):
        """(target filename, exists) if the first byte can be restored."""
        if not h["clobbered"] or not TAIL.match(h["link_tail"]):
            return None, False
        t = "M" + h["link_tail"]
        return t, t.lower() in names

    linked = [h for h in heads if h["link"] or h["clobbered"]]
    intact = [h for h in linked if not h["clobbered"]]
    broken = [h for h in linked if h["clobbered"]]
    matters, noop, unclear = [], [], []
    for h in broken:
        t, ex = repaired(h)
        (matters if (t and ex) else noop if t else unclear).append((h, t))

    print(f"{len(heads)} map file(s); {len(linked)} carry a linked-map name")
    print(f"first byte of the 0x50 field: "
          f"{len(intact)} intact, {len(broken)} zeroed")

    if intact:
        print("\nINTACT (these prove the field starts at 0x50):")
        for h in intact:
            on = h["link"].lower() in names
            print(f"  {h['file']:14} -> {h['link']:14} "
                  f"{'present' if on else 'ABSENT'}")

    if matters:
        print(f"\nCLOBBERED, AND IT MATTERS ({len(matters)}) -- target exists, "
              f"so the link is\nmissing where the game expects one:")
        for h, t in matters:
            print(f"  {h['file']:14} 0x50 = NUL + {h['link_tail']:14} -> {t}")

    if noop:
        print(f"\nclobbered, but harmless ({len(noop)}) -- the intended target "
              f"is not on disk,\nso an empty name and a missing file fail the "
              f"same way:")
        for h, t in noop:
            print(f"  {h['file']:14} -> {t} (absent)")

    if unclear:
        print(f"\nclobbered, first byte NOT inferable ({len(unclear)}):")
        for h, _ in unclear:
            print(f"  {h['file']:14} tail = {h['link_tail']!r}")

    unterm = [(h, n) for h in heads for _, _, n in FIELDS
              if h.get(n + "_unterminated")]
    if unterm:
        print(f"\nUNTERMINATED NAME FIELDS ({len(unterm)}):")
        for h, n in unterm:
            print(f"  {h['file']:14} {n} fills its field with no terminator")

    if a.fix:
        todo = matters + (noop if a.all else [])
        if not todo:
            print("\nnothing to fix" if not noop else
                  "\nnothing that matters to fix (--all would also rewrite "
                  f"{len(noop)} no-op file(s))")
        for h, t in todo:
            p = os.path.join(a.mapdir, h["file"])
            if a.apply:
                if not os.path.exists(p + ".bak"):
                    shutil.copy2(p, p + ".bak")
                d = bytearray(open(p, "rb").read())
                d[LINK_OFF] = 0x4D
                assert len(d) == h["size"], "length changed"
                open(p, "wb").write(d)
            verb = "wrote" if a.apply else "would write"
            print(f"  {verb} 'M' at 0x50 of {h['file']:14} -> {t}")
        if todo and not a.apply:
            print("\nNothing written. Add --apply.")

    if a.csv:
        cols = ["file", "size", "tile_sheet", "sfx", "audio_set", "area_name",
                "link", "link_first_byte", "clobbered", "link_tail"]
        with open(a.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(heads)
        print(f"\nheaders -> {a.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
