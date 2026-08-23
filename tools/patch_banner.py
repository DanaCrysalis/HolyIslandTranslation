#!/usr/bin/env python3
"""
patch_banner.py -- Holy Island (1997, YOKI) area-name banner width fix.

The banner routine at VA 0x12558 (file 0x28F58) measures the string with
strlen() and then allots 12 px per BYTE:

    e8 0c d5 03 00     call    strlen
    83 c4 04           add     esp, 4
    6b c0 0c           imul    eax, eax, 12      <-- file 0x28FAF
    bb 80 02 00 00     mov     ebx, 640
    29 c3              sub     ebx, eax
    d1 eb              shr     ebx, 1            ; text x = (640 - 12n)/2
    01 d8              add     eax, ebx
    8d 73 dc           lea     esi, [ebx - 36]   ; frame left
    8d 78 24           lea     edi, [eax + 36]   ; frame right

12 px/byte is right for Big5 (2 bytes -> one 24 px FONT24 glyph) but wrong
for the 16x24 Latin block, which advances 16 px per byte.  Changing the
immediate 12 -> 16 fixes both the frame width and the centring, and keeps
the instruction length identical (3 bytes) so nothing downstream shifts.

Usage:
    python3 patch_banner.py game.exe [-o game_patched.exe] [-n] [--revert]
"""

import argparse
import shutil
import sys

# --- the patch -------------------------------------------------------------

OFFSET = 0x28FAF          # file offset of the imul
VA     = 0x125AF          # virtual address (code base 0x10000, delta 0x16A00)
ORIG   = bytes.fromhex("6bc00c")   # imul eax, eax, 12
NEW    = bytes.fromhex("6bc010")   # imul eax, eax, 16

# Wider context, checked to prove we are looking at a pristine, correct build.
# Covers the strlen call, the imul, and the 640/shr centring that follows.
CTX_OFFSET  = 0x28FA7
CTX_ORIG    = bytes.fromhex(
    "e80cd50300"        # call strlen
    "83c404"            # add  esp, 4
    "6bc00c"            # imul eax, eax, 12      <-- target
    "bb80020000"        # mov  ebx, 0x280 (640)
    "29c3"              # sub  ebx, eax
    "d1eb"              # shr  ebx, 1
    "01d8"              # add  eax, ebx
    "8d73dc"            # lea  esi, [ebx - 0x24]
    "8d7824"            # lea  edi, [eax + 0x24]
)
CTX_PATCHED = CTX_ORIG.replace(ORIG, NEW, 1)

SIG_OFFSET = 0x89B81      # engine version string, sanity check on the file
SIG        = b"RPG Game System ver7.00 (c)Copyright 1997/09/02 by YOKI"


def fail(msg):
    sys.stderr.write("REFUSING TO WRITE: %s\n" % msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exe")
    ap.add_argument("-o", "--out", help="output file (default: patch in place)")
    ap.add_argument("-n", "--dry-run", action="store_true",
                    help="verify only, write nothing")
    ap.add_argument("--revert", action="store_true",
                    help="put the original 12 back")
    args = ap.parse_args()

    with open(args.exe, "rb") as fh:
        data = bytearray(fh.read())

    want_ctx, make_ctx = (CTX_PATCHED, CTX_ORIG) if args.revert else (CTX_ORIG, CTX_PATCHED)
    want_ins, make_ins = (NEW, ORIG) if args.revert else (ORIG, NEW)

    # 1. right game?
    if data[SIG_OFFSET:SIG_OFFSET + len(SIG)] != SIG:
        found = data.find(SIG)
        if found == -1:
            fail("engine version string not found -- this is not Holy Island's game.exe")
        fail("engine version string is at 0x%X, expected 0x%X -- unexpected build"
             % (found, SIG_OFFSET))

    # 2. right bytes at the target?
    have = bytes(data[CTX_OFFSET:CTX_OFFSET + len(want_ctx)])
    if have != want_ctx:
        if have == make_ctx:
            print("Already %s -- nothing to do."
                  % ("reverted" if args.revert else "patched"))
            return
        fail("bytes at 0x%X do not match the expected sequence.\n"
             "  expected %s\n  found    %s"
             % (CTX_OFFSET, want_ctx.hex(), have.hex()))

    print("game.exe verified pristine at the patch site.")
    print("  file offset  0x%05X   (VA 0x%05X)" % (OFFSET, VA))
    print("  original     %s   imul eax, eax, %d" % (want_ins.hex(), want_ins[2]))
    print("  replacement  %s   imul eax, eax, %d" % (make_ins.hex(), make_ins[2]))
    print("  length unchanged (3 bytes), nothing downstream shifts.")

    if args.dry_run:
        print("\nDry run -- no bytes written.")
        return

    # 3. write, length-preserving (never slice-assign a different length)
    assert len(make_ins) == len(want_ins) == 3
    data[OFFSET:OFFSET + 3] = make_ins
    assert len(data) == len(bytes(data))

    out = args.out or args.exe
    if out == args.exe:
        shutil.copyfile(args.exe, args.exe + ".bak")
        print("\nbackup written to %s.bak" % args.exe)
    with open(out, "wb") as fh:
        fh.write(data)
    print("wrote %s" % out)

    # 4. read back
    with open(out, "rb") as fh:
        check = fh.read()
    if check[OFFSET:OFFSET + 3] != make_ins or len(check) != len(data):
        fail("read-back verification failed")
    print("read-back verified.")


if __name__ == "__main__":
    main()
