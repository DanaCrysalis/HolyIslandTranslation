#!/usr/bin/env python3
"""Structural sanity check on a Holy Island tree, English or pristine.

Checks only things that are decidable from the documented file formats -- it
does not know what the text should say, only that the structures around it are
intact. It is meant to run at the end of build_english.py and to catch the
failure modes that have actually bitten this project:

  * a tool that shifted game.exe's length (inserting instead of overwriting)
  * an option table zeroed by a writer that padded all 236 bytes
  * a .MSG prompt with no NUL inside its 199 usable bytes
  * a map area name running past 0x4F into the linked-map field
  * the banner imul left at 12 px/byte, which clips English banners
  * a .GRP whose header no longer matches its size

    python3 verify_tree.py GAMEDIR [--json]

Exit status is 1 if any ERROR was raised; warnings alone exit 0.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

# --- documented constants (docs/FINDINGS.md sections 3, 4, 6, 7) --------------
EXE_SIZE = 622929
ENGINE_STR = b"RPG Game System ver7.00"
ENGINE_OFF = 0x89B81
BANNER_IMUL = 0x28FAF          # 6B C0 0C  ->  6B C0 10
BANNER_ORIG = bytes((0x6B, 0xC0, 0x0C))
BANNER_PATCHED = bytes((0x6B, 0xC0, 0x10))

MAP_NAME_OFF = 0x3C            # 20-byte Big5 area name
MAP_FIELD = 20

MSG_FILE_HDR = 32
MSG_REC = 253
MSG_REC_HDR = 17
MSG_TEXT = 236
PROMPT_CAP = 199               # bytes 0..199; +200 is the option table
OPT_BASE = 200
OPT_SLOT = 12                  # 10-byte label + u16 branch value
OPT_SLOTS = 3

DEMO_REC = 243
DEMO_REC_HDR = 10
DEMO_RECORDS = 21
DEMO_SIZE = MSG_FILE_HDR + DEMO_RECORDS * DEMO_REC   # 5135

GRP_HDR = 7                    # u16 w, u16 h, u16 cel_count, u8 pad


class Report:
    def __init__(self):
        self.errors, self.warnings, self.info = [], [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.info.append(msg)


def find(d: Path, name: str):
    for p in d.iterdir():
        if p.name.lower() == name.lower():
            return p
    return None


# --- game.exe ----------------------------------------------------------------
def check_exe(path: Path, r: Report):
    d = path.read_bytes()
    if len(d) != EXE_SIZE:
        r.error(f"game.exe is {len(d)} bytes, expected {EXE_SIZE}. A tool "
                f"inserted or deleted rather than overwriting; every offset "
                f"downstream is now wrong.")
        return
    if d[ENGINE_OFF:ENGINE_OFF + len(ENGINE_STR)] != ENGINE_STR:
        r.error(f"engine version string missing at 0x{ENGINE_OFF:X} -- this is "
                f"not the expected build of game.exe")
        return
    r.note(f"game.exe {len(d)} bytes, engine string present")

    window = d[BANNER_IMUL:BANNER_IMUL + 3]
    if window == BANNER_PATCHED:
        r.note("banner width patched (imul 16) -- English banners will not clip")
    elif window == BANNER_ORIG:
        r.warn(f"banner still at 12 px/byte (0x{BANNER_IMUL:X}). Correct for "
               f"Big5, wrong for the 16x24 Latin block: run patch_banner.py or "
               f"English area names will overflow their frame.")
    else:
        r.error(f"unexpected bytes at 0x{BANNER_IMUL:X}: {window.hex()} -- "
                f"expected the banner imul instruction")


# --- map###.dat --------------------------------------------------------------
def check_maps(mapdir: Path, r: Report):
    dats = sorted(p for p in mapdir.iterdir()
                  if p.suffix.lower() == ".dat" and p.is_file())
    if not dats:
        r.error(f"no .dat files in {mapdir}")
        return
    chinese = translated = 0
    longest = ("", 0)
    for p in dats:
        d = p.read_bytes()
        if len(d) < MAP_NAME_OFF + MAP_FIELD:
            r.error(f"{p.name}: shorter than the 5-field header")
            continue
        field = d[MAP_NAME_OFF:MAP_NAME_OFF + MAP_FIELD]
        if b"\x00" not in field:
            r.error(f"{p.name}: area name fills all {MAP_FIELD} bytes with no "
                    f"terminator -- it runs past 0x4F into the linked-map field")
            continue
        name = field.split(b"\x00")[0]
        if len(name) > longest[1]:
            longest = (p.name, len(name))
        if not name:
            continue
        if any(b >= 0x80 for b in name):
            chinese += 1
        else:
            translated += 1
    r.note(f"{len(dats)} map .dat files: {translated} with an ASCII area name, "
           f"{chinese} still Big5; longest name {longest[1]} bytes "
           f"({longest[0]})")
    if chinese and translated:
        r.warn(f"{chinese} map(s) still carry a Chinese area name. Remember "
               f"map###b.dat variants carry the same name and both need "
               f"patching, or the banner reverts on re-entry.")
    for stray in mapdir.rglob("*.bak"):
        r.warn(f"{stray.name} left behind by mapnames.py -- delete before "
               f"cutting a patch or it enters the diff")


# --- .msg --------------------------------------------------------------------
def slots(text: bytes):
    out = []
    for i in range(OPT_SLOTS):
        o = OPT_BASE + i * OPT_SLOT
        raw = text[o:o + OPT_SLOT]
        if len(raw) < OPT_SLOT:
            break
        label = raw[:10].split(b"\x00")[0]
        value = struct.unpack_from("<H", raw, 10)[0]
        out.append((label, value))
    return out


def check_msgs(mapdir: Path, r: Report):
    files = sorted(p for p in mapdir.iterdir()
                   if p.suffix.lower() == ".msg" and p.is_file())
    if not files:
        r.error(f"no .msg files in {mapdir}")
        return

    tables = records = nofiles = 0
    for p in files:
        d = p.read_bytes()
        if p.name.lower() == "demo.msg":
            if len(d) != DEMO_SIZE:
                r.error(f"demo.msg is {len(d)} bytes, expected {DEMO_SIZE} "
                        f"(32 + {DEMO_RECORDS}*{DEMO_REC})")
            else:
                r.note(f"demo.msg: {DEMO_RECORDS} records on the 243-byte "
                       f"stride (untranslated content -- see FINDINGS 11)")
            continue

        body = len(d) - MSG_FILE_HDR
        if body < 0 or body % MSG_REC:
            r.error(f"{p.name}: {len(d)} bytes does not fit 32 + k*253")
            nofiles += 1
            continue
        n = body // MSG_REC
        records += n
        for i in range(n):
            base = MSG_FILE_HDR + i * MSG_REC + MSG_REC_HDR
            text = d[base:base + MSG_TEXT]
            if b"\x00" not in text[:PROMPT_CAP + 1]:
                r.error(f"{p.name}:{i} prompt has no terminator inside its "
                        f"{PROMPT_CAP} usable bytes -- it runs into option "
                        f"slot 0")
            st = slots(text)
            if any(lbl or val for lbl, val in st):
                tables += 1
                for j, (lbl, val) in enumerate(st):
                    if val and not lbl:
                        r.error(f"{p.name}:{i} option slot {j} has branch "
                                f"value {val} but an empty label -- the table "
                                f"was zeroed by a writer padding all 236 bytes")

    r.note(f"{len(files)} .msg files, {records} records, "
           f"{tables} carrying an option table")
    if not nofiles and tables == 0:
        r.error("no option tables found anywhere. Every choice prompt in the "
                "game -- shops, inns, the slave auction -- has been erased. "
                "Run optfix.py restore --pristine.")
    elif tables < 80:
        r.warn(f"only {tables} option tables; the shipping script has 84. "
               f"Some were erased. Run optfix.py scan for the list.")


# --- .grp --------------------------------------------------------------------
def check_grp(path: Path, r: Report):
    d = path.read_bytes()
    if len(d) < GRP_HDR:
        r.error(f"{path.name}: too short to hold a GRP header")
        return
    w, h, n = struct.unpack_from("<HHH", d, 0)
    expect = GRP_HDR + n * w * h
    if expect != len(d):
        r.error(f"{path.name}: header says {w}x{h} x{n} cels = {expect} bytes, "
                f"file is {len(d)}")
    else:
        r.note(f"{path.name}: {w}x{h}, {n} cel(s), size consistent")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gamedir", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    r = Report()
    if not a.gamedir.is_dir():
        sys.exit(f"not a directory: {a.gamedir}")

    exe = find(a.gamedir, "game.exe")
    if exe:
        check_exe(exe, r)
    else:
        r.error("game.exe not found")

    pstat = find(a.gamedir, "pstat.grp")
    if pstat:
        check_grp(pstat, r)
    else:
        r.error("PStat.GRP not found -- the exe loads this name and no other")

    mapdir = find(a.gamedir, "map")
    if mapdir and mapdir.is_dir():
        check_maps(mapdir, r)
        check_msgs(mapdir, r)
    else:
        r.error("map/ directory not found")

    if a.json:
        print(json.dumps({"errors": r.errors, "warnings": r.warnings,
                          "info": r.info}, indent=2))
    else:
        for m in r.info:
            print(f"  ok    {m}")
        for m in r.warnings:
            print(f"  WARN  {m}")
        for m in r.errors:
            print(f"  ERROR {m}")
        print(f"\n{len(r.errors)} error(s), {len(r.warnings)} warning(s)")
    sys.exit(1 if r.errors else 0)


if __name__ == "__main__":
    main()
