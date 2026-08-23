#!/usr/bin/env python3
"""
msgtool2.py -- Holy Island (聖光島) .msg dialogue extractor / reinserter.

CORRECTED FORMAT (derived from game31.msg: 32 + 134*253 == 33934 exactly)

    [ 32-byte file header ][ record 0 ][ record 1 ] ...

    record      = 253 bytes
    layout      = [ 17-byte record header ][ 236-byte text field ]
    text        = Big5 / CP950, NUL-terminated, NUL-padded
    file offset of record N's text = 32 + N*253 + 17  ==  49 + N*253

THE TEXT FIELD IS NOT 236 BYTES OF TEXT

    text field +0   ..+199   prompt, NUL-terminated   <-- 199 usable bytes
    text field +200 ..+211   option slot 0
    text field +212 ..+223   option slot 1
    text field +224 ..+235   option slot 2

    slot = [ 10-byte label, Big5, NUL-padded ][ u16 value, little-endian ]

The last 36 bytes are a fixed option table used by choice prompts -- shops,
inns, yes/no questions, the slave auction. `value` is the branch target: a
dialogue node number, or 999 for "open shop transaction" paired with 0 to
exit. 84 records across the shipping script carry one.

Import therefore writes and pads ONLY bytes 0..199 of the field. Padding the
full 236 erases every option table in the game: the prompt still renders, but
the options never appear. Use optfix.py to inspect or repair the tables.

Record header fields identified so far:
    byte  1  : speaker / portrait ID   (few distinct values)
    byte 15  : dialogue node pointer   (high variance -- it's a tree)
    bytes 4,6,8,9,10,11,13 : condition flags / branch triggers
    no length field -- text length is free within the 236-byte field

Subcommands
-----------
    verify   <dir>            check (size-32) % 253 == 0 across all files
    analyse  <file|dir>       header column stats + sample record dumps
    export   <dir> -o f.csv   dump all records to a translation CSV
    import   <dir> f.csv      write the 'english' column back in place

Everything is bytes. Big5 trail bytes include 0x5C and 0x7C; any tool that
handles this data as text will corrupt it.
"""

import argparse
import csv
import glob
import os
import shutil
import sys
from collections import Counter, defaultdict

FILE_HDR = 32
REC = 253
HDR = 17
TEXT_CAP = REC - HDR              # 236 -- the whole field, tables included

# Option table geometry, inside the text field.
OPT_TABLE = 200                   # first byte of slot 0
OPT_SLOT = 12                     # [10-byte label][u16 value]
OPT_SLOTS = 3                     # 200 + 3*12 == 236 exactly
OPT_LABEL = 10
PROMPT_CAP = OPT_TABLE - 1        # 199 usable bytes of prompt

TRAIL = set(range(0x40, 0x7F)) | set(range(0xA1, 0xFF))

LINE_WIDTH = 30
MAX_LINES = 7
# Rendered-byte ceiling. Measured in DOSBox on game1.msg record 0:
#   189B -> renders fine      195B -> renders fine
#   200B -> CRASHES           (all five tests were 7 rendered lines)
# That bracket is now EXPLAINED rather than empirical: the option table
# begins at byte 200 of the text field, so a 200-byte prompt overruns slot 0.
# It was a struct boundary, not an untested engine buffer -- which is also
# why the shipping script never exceeds 194 bytes, and why the "8 lines
# crashes" result was the same overrun measured a different way.
# 194 is kept as the default because the whole shipping game proves it safe;
# PROMPT_CAP (199) is the hard structural limit and is enforced separately.
MAX_BYTES = 194
TOKENS = set("ＡＢＣＤＥＦａｂｃｄｅｆ")
TOKEN_BYTES = 4


def rendered_bytes(s, encoding="cp950"):
    """Byte length as DRAWN: name placeholders expand at runtime."""
    n = 0
    for ch in s:
        if ch in TOKENS:
            n += TOKEN_BYTES
        else:
            try:
                n += len(ch.encode(encoding))
            except UnicodeEncodeError:
                n += 1
    return n


def rendered_lines(s, encoding="cp950"):
    return -(-rendered_bytes(s, encoding) // LINE_WIDTH)


def is_lead(b):
    return 0x81 <= b <= 0xFE


def load(path):
    with open(path, "rb") as fh:
        data = fh.read()
    body = len(data) - FILE_HDR
    n, rem = divmod(body, REC) if body > 0 else (0, 0)
    return data, n, rem


def rec_slice(data, i):
    base = FILE_HDR + i * REC
    return data[base:base + REC], base


def prompt_cap():
    """Usable prompt bytes for the geometry currently configured.

    The option table sits at a known offset only in the standard 236-byte
    field. If --rec/--hdr have been used (demo.msg), its position is unknown,
    so the whole field is treated as prompt.
    """
    return PROMPT_CAP if TEXT_CAP == 236 else TEXT_CAP


def option_table(rec):
    """Raw 36-byte option table, or None if this geometry has no known one."""
    if TEXT_CAP != 236:
        return None
    return rec[HDR + OPT_TABLE:HDR + TEXT_CAP]


def has_option_table(rec):
    tbl = option_table(rec)
    return tbl is not None and tbl.strip(b"\x00") != b""


def option_labels(rec):
    """[(label, value), ...] for the slots that are filled."""
    tbl = option_table(rec)
    if not tbl:
        return []
    out = []
    for k in range(OPT_SLOTS):
        p = k * OPT_SLOT
        label = bytes(tbl[p:p + OPT_LABEL]).split(b"\x00")[0]
        if not label:
            continue
        value = int.from_bytes(tbl[p + OPT_LABEL:p + OPT_SLOT], "little")
        try:
            out.append((label.decode("cp950"), value))
        except UnicodeDecodeError:
            out.append((repr(label), value))
    return out


def extract_text(rec):
    """Decode the Big5 prompt from a record's text field.

    Returns (text, raw_bytes). Stops at the first byte that cannot continue
    a Big5 or ASCII string -- normally 0x00 -- and never reads into the
    option table.
    """
    field = rec[HDR:HDR + prompt_cap()]
    i = 0
    while i < len(field) - 1:
        if is_lead(field[i]) and field[i + 1] in TRAIL:
            i += 2
        elif 0x20 <= field[i] <= 0x7E:
            i += 1
        else:
            break
    raw = field[:i]
    try:
        return raw.decode("cp950"), raw
    except UnicodeDecodeError:
        return raw.decode("cp950", errors="replace"), raw


def fits(path):
    """True if the file matches the currently configured geometry."""
    return (os.path.getsize(path) - FILE_HDR) % REC == 0


def filter_fitting(paths, force, verb):
    """Drop files whose size contradicts the geometry.

    Without this, a file with a different record size decodes into
    plausible-looking garbage and a later import would corrupt it.
    """
    good, bad = [], []
    for p in paths:
        (good if fits(p) else bad).append(p)
    if bad:
        print(f"  ! {len(bad)} file(s) do not fit geometry "
              f"(file_hdr={FILE_HDR}, rec={REC}):")
        for p in bad[:8]:
            sz = os.path.getsize(p)
            print(f"      {os.path.basename(p)}  {sz} bytes, "
                  f"remainder {(sz-FILE_HDR) % REC}")
        if force:
            print(f"    --force given: {verb} anyway (output may be garbage)")
            return paths
        print(f"    skipped. Re-run with --rec/--hdr for these, "
              f"or --force to override.\n")
    return good


def collect(target, pattern="*.msg"):
    if os.path.isfile(target):
        return [target]
    paths = sorted(glob.glob(os.path.join(target, pattern)))
    if not paths:
        sys.exit(f"no {pattern} files in {target}")
    return paths


# --------------------------------------------------------------------------
def cmd_verify(args):
    """The decisive test: every file should be 32 + k*253 bytes."""
    paths = collect(args.target)
    ok = bad = 0
    print(f"{'file':<18} {'size':>9} {'(size-32)%253':>14} {'records':>8}")
    for p in paths:
        sz = os.path.getsize(p)
        rem = (sz - FILE_HDR) % REC
        n = (sz - FILE_HDR) // REC
        flag = "" if rem == 0 else "  <-- MISMATCH"
        if rem == 0:
            ok += 1
        else:
            bad += 1
        if rem or args.all:
            print(f"{os.path.basename(p):<18} {sz:>9} {rem:>14} {n:>8}{flag}")
    print(f"\n{ok}/{len(paths)} files fit the 32 + k*253 model")
    if bad == 0:
        print("Format confirmed across the whole set.")
    else:
        print(f"{bad} file(s) do not fit -- inspect those before bulk editing.")


def cmd_analyse(args):
    paths = collect(args.target)
    cols = [Counter() for _ in range(HDR)]
    pads = Counter()
    total = 0
    tables = 0
    lengths = []

    for path in paths:
        data, n, rem = load(path)
        if rem:
            print(f"  ! {os.path.basename(path)}: {rem} trailing bytes")
        for i in range(n):
            rec, _ = rec_slice(data, i)
            if len(rec) < REC:
                continue
            text, raw = extract_text(rec)
            total += 1
            lengths.append(len(raw))
            for k in range(HDR):
                cols[k][rec[k]] += 1
            if has_option_table(rec):
                tables += 1
            tail = rec[HDR + len(raw):]
            if tail:
                pads[tail[0]] += 1

    print(f"\nrecords: {total}   files: {len(paths)}")
    print("\n--- RECORD HEADER COLUMNS (0..16) ---")
    print(f"{'byte':>4} {'distinct':>9}  {'top values':<40} guess")
    for k in range(HDR):
        c = cols[k]
        top = "  ".join(f"{v:02X}:{n}" for v, n in c.most_common(4))
        if len(c) == 1:
            guess = "constant"
        elif len(c) > total * 0.4:
            guess = "pointer / id (high variance)"
        elif len(c) <= 12:
            guess = "enum: speaker / flag"
        else:
            guess = ""
        print(f"{k:>4} {len(c):>9}  {top:<40} {guess}")

    print("\n--- TEXT FIELD ---")
    if lengths:
        print(f"  field size    : {TEXT_CAP} bytes")
        print(f"  prompt capacity: {prompt_cap()} bytes "
              f"({'option table occupies 200..235' if TEXT_CAP == 236 else 'table offset unknown for this geometry'})")
        print(f"  longest used  : {max(lengths)} bytes "
              f"({max(lengths)//2} chars), {TEXT_CAP-max(lengths)} spare")
        print(f"  mean used     : {sum(lengths)/len(lengths):.1f} bytes")
        print(f"  empty records : {sum(1 for x in lengths if x == 0)}")
        print(f"  option tables : {tables}")
    print(f"  pad byte      : "
          f"{', '.join(f'{v:02X} x{n}' for v, n in pads.most_common(3))}")

    data, n, _ = load(paths[0])
    print(f"\n--- SAMPLES ({os.path.basename(paths[0])}) ---")
    print(f"file header: {' '.join(f'{b:02X}' for b in data[:FILE_HDR])}")
    for i in range(min(args.samples, n)):
        rec, base = rec_slice(data, i)
        text, raw = extract_text(rec)
        print(f"\n  record {i} @ 0x{base:06X}")
        print(f"    hdr : {' '.join(f'{b:02X}' for b in rec[:HDR])}")
        print(f"    spk={rec[1]:02X}  node={rec[15]:02X}  "
              f"{len(raw)} bytes / {len(text)} chars")
        print(f"    text: {text}")
        for lab, val in option_labels(rec):
            print(f"    opt : {lab}  -> {val}")


def cmd_export(args):
    paths = filter_fitting(collect(args.target), args.force, "exporting")
    if not paths:
        sys.exit("no files match the configured geometry")
    rows = []
    for path in paths:
        data, n, _ = load(path)
        for i in range(n):
            rec, base = rec_slice(data, i)
            if len(rec) < REC:
                continue
            text, raw = extract_text(rec)
            if not text.strip() and args.skip_empty:
                continue
            rows.append({
                "file": os.path.basename(path),
                "record": i,
                "offset": f"0x{base + HDR:08X}",
                "speaker": f"{rec[1]:02X}",
                "node": f"{rec[15]:02X}",
                "bytes_used": len(raw),
                "bytes_free": prompt_cap() - len(raw),
                "options": "|".join(l for l, _v in option_labels(rec)),
                "chinese": text,
                "english": "",
            })
    fields = ["file", "record", "offset", "speaker", "node",
              "bytes_used", "bytes_free", "options", "chinese", "english"]
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    ntab = sum(1 for r in rows if r["options"])
    print(f"exported {len(rows)} records from {len(paths)} files -> {args.out}")
    print(f"prompt capacity per record: {prompt_cap()} bytes")
    if ntab:
        print(f"{ntab} record(s) carry an option table (see the 'options' "
              f"column); translate those labels with optfix.py")


def cmd_import(args):
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    pad = int(args.pad, 0)
    by_file = defaultdict(list)
    for r in rows:
        if r.get("english", "").strip():
            by_file[r["file"]].append(r)
    if not by_file:
        sys.exit("no rows carry an 'english' value")

    written, skipped, tables_kept = 0, [], 0
    for fname, items in by_file.items():
        path = os.path.join(args.target, fname)
        if not os.path.isfile(path):
            print(f"  ! missing {fname}")
            continue
        if not fits(path) and not args.force:
            print(f"  ! {fname} does not fit geometry -- skipped "
                  f"(use --rec/--hdr, or --force)")
            continue
        if args.backup and not os.path.exists(path + ".bak"):
            shutil.copy2(path, path + ".bak")
        with open(path, "rb") as fh:
            data = bytearray(fh.read())

        for r in items:
            i = int(r["record"])
            try:
                enc = r["english"].encode(args.encoding)
            except UnicodeEncodeError as e:
                skipped.append((fname, i, f"encode: {e}"))
                continue
            cap = prompt_cap()
            if len(enc) > cap:
                extra = (" -- the option table starts at byte 200 and this "
                         "would overwrite it" if cap == PROMPT_CAP else "")
                skipped.append((fname, i,
                                f"{len(enc)}B exceeds the {cap}B prompt "
                                f"field{extra}"))
                continue
            nl = rendered_lines(r["english"], args.encoding)
            if nl > args.max_lines and not args.force_lines:
                skipped.append((fname, i,
                                f"{nl} rendered lines exceeds {args.max_lines} "
                                f"-- WOULD CRASH THE GAME"))
                continue
            rb = rendered_bytes(r["english"], args.encoding)
            if rb > args.max_bytes and not args.force_lines:
                skipped.append((fname, i,
                                f"{rb} rendered bytes exceeds "
                                f"{args.max_bytes} -- WOULD CRASH THE GAME"))
                continue
            base = FILE_HDR + i * REC + HDR
            if base + TEXT_CAP > len(data):
                skipped.append((fname, i, "past EOF"))
                continue

            # Write and pad ONLY the prompt region. Bytes 200..235 hold the
            # option table for choice prompts; padding across them wipes the
            # options while leaving the prompt looking perfectly fine.
            table_before = bytes(data[base + OPT_TABLE:base + TEXT_CAP]) \
                if cap == PROMPT_CAP else None
            data[base:base + cap] = enc + bytes([pad]) * (cap - len(enc))
            if table_before is not None:
                assert bytes(data[base + OPT_TABLE:base + TEXT_CAP]) \
                    == table_before, "option table clobbered"
                if table_before.strip(b"\x00") != b"":
                    tables_kept += 1
            written += 1

        with open(path, "wb") as fh:
            fh.write(data)

    print(f"wrote {written} records across {len(by_file)} file(s)")
    if tables_kept:
        print(f"{tables_kept} option table(s) preserved")
    if skipped:
        print(f"\n{len(skipped)} skipped:")
        for f, i, why in skipped[:25]:
            print(f"  {f} #{i}: {why}")
        if len(skipped) > 25:
            print(f"  ... {len(skipped)-25} more")


def main():
    global REC, HDR, FILE_HDR, TEXT_CAP
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify")
    v.add_argument("target")
    v.add_argument("--all", action="store_true", help="list every file")
    v.set_defaults(func=cmd_verify)

    a = sub.add_parser("analyse")
    a.add_argument("target")
    a.add_argument("--samples", type=int, default=4)
    a.set_defaults(func=cmd_analyse)

    e = sub.add_parser("export")
    e.add_argument("target")
    e.add_argument("-o", "--out", default="script.csv")
    e.add_argument("--keep-empty", dest="skip_empty",
                   action="store_false", default=True)
    e.add_argument("--force", action="store_true",
                   help="process files that do not fit the geometry")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import")
    i.add_argument("target")
    i.add_argument("csv")
    i.add_argument("--pad", default="0x00")
    i.add_argument("--encoding", default="cp950",
                   help="output encoding (default cp950: a superset of ASCII "
                        "that also encodes the full-width name tokens)")
    i.add_argument("--backup", action="store_true")
    i.add_argument("--force", action="store_true",
                   help="write to files that do not fit the geometry")
    i.add_argument("--max-lines", type=int, default=MAX_LINES,
                   help=f"max rendered lines (default {MAX_LINES}; 8 crashes)")
    i.add_argument("--max-bytes", type=int, default=MAX_BYTES,
                   help=f"max rendered bytes (default {MAX_BYTES}: the "
                        f"original script's maximum; 195 tested safe, "
                        f"200 crashes)")
    i.add_argument("--force-lines", action="store_true",
                   help="write records that exceed the render limit (unsafe)")
    i.set_defaults(func=cmd_import)

    for p in (v, a, e, i):
        p.add_argument("--rec", type=int, default=REC,
                       help=f"record size (default {REC}; demo.msg is 243)")
        p.add_argument("--hdr", type=int, default=HDR,
                       help=f"record header size (default {HDR}; "
                            f"demo.msg is 10)")
        p.add_argument("--file-hdr", type=int, default=FILE_HDR,
                       help=f"file header size (default {FILE_HDR})")

    args = ap.parse_args()

    REC, HDR, FILE_HDR = args.rec, args.hdr, args.file_hdr
    TEXT_CAP = REC - HDR

    args.func(args)


if __name__ == "__main__":
    main()
