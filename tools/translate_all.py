#!/usr/bin/env python3
"""
translate_all.py -- write the English string tables into game.exe.

Reconstructed from a byte diff of the pristine and patched executables, so the
offsets here are observed, not inferred. Three tables are covered:

    ui      63 strings referenced by the LE relocation fixup table. Field size
            is the distance to the next referenced offset -- anything past that
            is linker alignment padding nothing can reach.
    item    316 names. base 0x08CD68, stride 0x54, 20-byte name field at
            offset 0 of each record => 19 usable bytes.
    spell   57 spell / status / monster names. base 0x093768, stride 0x40,
            same 20-byte field.

Both strides were confirmed empirically against the patched exe: stride 0x54
decodes 316/316 item slots as ASCII, and no other candidate stride comes close.

VERIFIES ORIGINAL BYTES. Every row's `chinese` column must match what is on
disk, so this refuses an already-patched exe and must run FIRST, on pristine
input. That is why build_english.py always works on a throwaway copy.

    python3 translate_all.py <game.exe> [-o out.exe] [--csv strings_worksheet.csv]
    python3 translate_all.py <game.exe> -n          check only, write nothing
    python3 translate_all.py <game.exe> --force     patch what matches, skip the rest

By default the full field is rewritten and NUL-padded -- never string+NUL --
so no stale tail survives. The file length never changes either way.

--preserve-tail zeroes only as far as the original string ran, which gets
close to the shipped BUILD but does not reproduce it exactly: the original
patcher was inconsistent about how far it padded, so a rebuild differs from
the current BUILD in about 30 bytes of linker alignment. Those bytes are
provably unreachable -- each sits past a NUL and before the next fixup
target, so no pointer in the image can reach it -- and the game cannot tell
the difference. Use the default (full-field zeroing) unless you specifically
want a low-noise diff against the existing BUILD.

LEADING SPACES ARE SIGNIFICANT. The title menu is aligned by padding its
strings ('  EXIT', '  AUDIO'), not by a code patch -- which is why there is no
patch_menu.py in the diff. Do not strip the english column, in this tool or in
a spreadsheet that might helpfully trim it for you.
"""

import argparse
import csv
import os
import sys

EXE_SIZE = 622929
ENGINE_STR = b"RPG Game System ver7.00"
ENGINE_OFF = 0x89B81

DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir,
    "data", "strings_worksheet.csv")


def load(path):
    if not os.path.exists(path):
        sys.exit(f"worksheet not found: {path}")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    need = {"kind", "offset", "max_bytes", "chinese", "english"}
    if not rows or not need <= set(rows[0]):
        sys.exit(f"{path} needs columns {sorted(need)}")
    return rows


def encode(s):
    """Bytes as the engine stores them. ASCII where possible, else Big5."""
    try:
        return s.encode("ascii")
    except UnicodeEncodeError:
        return s.encode("cp950")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("-o", "--out", help="output file (default: patch in place)")
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("-n", "--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="patch rows that verify, skip and report the rest")
    ap.add_argument("--preserve-tail", action="store_true",
                    help="zero only as far as the original string ran, "
                         "reproducing the shipped BUILD byte for byte")
    a = ap.parse_args()

    d = bytearray(open(a.exe, "rb").read())
    if len(d) != EXE_SIZE:
        sys.exit(f"{a.exe} is {len(d)} bytes, expected {EXE_SIZE}")
    if bytes(d[ENGINE_OFF:ENGINE_OFF + len(ENGINE_STR)]) != ENGINE_STR:
        sys.exit("engine version string missing -- not the expected build")

    rows = load(a.csv)
    mismatch, toolong, written, skipped = [], [], 0, 0

    for r in rows:
        # NEVER strip. Leading spaces in the title-menu strings ('  EXIT',
        # '  AUDIO') ARE the alignment -- there is no separate menu patch.
        eng = r["english"] or ""
        if not eng.strip():
            continue
        off = int(r["offset"], 16)
        cap = int(r["max_bytes"])
        field = cap + 1

        want = encode(r["chinese"])
        have = bytes(d[off:off + field]).split(b"\x00")[0]
        if have != want:
            mismatch.append((r, have))
            continue

        enc = encode(eng)
        if len(enc) > cap:
            toolong.append((r, len(enc)))
            continue

        if not a.dry_run:
            # Never a slice of a different length -- that would shift the file.
            n = (len(want) + 1) if a.preserve_tail else field
            n = max(n, len(enc) + 1)
            d[off:off + n] = enc.ljust(n, b"\x00")
        written += 1

    if mismatch and not a.force:
        print(f"{len(mismatch)} row(s) do not match the bytes on disk. "
              f"This exe is not pristine, or the worksheet is for another "
              f"build. Nothing was written.")
        for r, have in mismatch[:8]:
            print(f"  {r['kind']} {r['offset']}: expected {r['chinese']!r}, "
                  f"found {have.decode('cp950', 'replace')!r}")
        if len(mismatch) > 8:
            print(f"  ... and {len(mismatch) - 8} more")
        return 1
    skipped = len(mismatch)

    if toolong:
        print(f"{len(toolong)} name(s) do not fit their field. Nothing was written.")
        for r, n in toolong:
            print(f"  {r['kind']} {r['offset']}: {r['english']!r} is {n}B, "
                  f"field allows {r['max_bytes']}")
        return 1

    assert len(d) == EXE_SIZE, "length changed -- refusing to write"

    if a.dry_run:
        print(f"would write {written} string(s); {skipped} skipped")
        return 0

    out = a.out or a.exe
    open(out, "wb").write(d)
    print(f"wrote {written} string(s) -> {out}")
    if skipped:
        print(f"{skipped} row(s) skipped (--force); they did not verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
