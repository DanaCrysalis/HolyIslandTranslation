#!/usr/bin/env python3
"""
optfix.py -- Holy Island (聖光島) .msg choice-option table repair & translation.

THE FORMAT
    record = 253 bytes = [17-byte header][236-byte text field]

    The text field is NOT 236 bytes of text. Its last 36 bytes are a fixed
    option table used by choice prompts (shops, yes/no questions, the slave
    auction):

        text field +0   ..+199   prompt, NUL-terminated  (199 usable bytes)
        text field +200 ..+211   option slot 0
        text field +212 ..+223   option slot 1
        text field +224 ..+235   option slot 2

        slot = [10-byte label, Big5, NUL-padded][u16 value, little-endian]

    `value` is the branch target: a dialogue node number for ordinary
    choices, or 999 for the "open shop transaction" action with 0 for exit.

    msgtool2 treats the whole 236 bytes as text, so importing a translation
    zero-fills the option table and the options vanish in game while the
    prompt still renders. That is what this repairs.

USAGE
    optfix.py scan    <dir>                     list every option table
    optfix.py restore <dir> [--pristine DIR] --apply
                                                copy tables back from pristine
    optfix.py export  <dir> -o options.csv      dump labels for translation
    optfix.py import  <dir> options.csv --apply write the english column back

    Without --pristine, `restore` uses the .bak files msgtool2 left in <dir>.
    Every command is a dry run unless --apply is given.
"""

import argparse
import csv
import os
import sys

# Windows encodes stdout as cp1252, which cannot represent Chinese labels and
# throws UnicodeEncodeError the moment output is redirected to a file.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:      # Python < 3.7
    pass

FILE_HDR, REC, HDR = 32, 253, 17
TEXT = REC - HDR          # 236
TABLE = 200               # option table starts here, inside the text field
SLOT, NSLOTS = 12, 3
LABEL = 10                # bytes of label per slot; leave room for a NUL
PROMPT_MAX = TABLE - 1    # 199


def read_records(path):
    data = bytearray(open(path, "rb").read())
    n = (len(data) - FILE_HDR) // REC
    if (len(data) - FILE_HDR) % REC:
        return None, 0
    return data, n


def field_span(i):
    b = FILE_HDR + i * REC + HDR
    return b, b + TEXT


def get_slots(data, i):
    b, _ = field_span(i)
    out = []
    for k in range(NSLOTS):
        p = b + TABLE + k * SLOT
        label = bytes(data[p:p + LABEL]).split(b"\x00")[0]
        value = int.from_bytes(data[p + LABEL:p + SLOT], "little")
        out.append((label, value))
    return out


def prompt_len(data, i):
    b, e = field_span(i)
    blob = bytes(data[b:e])
    z = blob.find(b"\x00")
    return len(blob) if z < 0 else z


def has_table(data, i):
    b, _ = field_span(i)
    return bytes(data[b + TABLE:b + TEXT]).strip(b"\x00") != b""


def show(b):
    try:
        return b.decode("cp950")
    except UnicodeDecodeError:
        return repr(b)


def msgfiles(d):
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".msg"))


def cmd_scan(d):
    total = 0
    for fn in msgfiles(d):
        data, n = read_records(os.path.join(d, fn))
        if data is None:
            print(f"  ! {fn}: not 32 + k*253, skipped", file=sys.stderr)
            continue
        for i in range(n):
            if not has_table(data, i):
                continue
            total += 1
            labels = " | ".join(
                f"{(show(l) if l else '-'):<10} val={v:>5}"
                for l, v in get_slots(data, i))
            print(f"{fn}:{i:<4} prompt {prompt_len(data, i):>3}b   {labels}")
    print(f"\n{total} record(s) carry an option table.")


def cmd_restore(d, pristine, apply_):
    same = pristine is None
    fixed_files = fixed_recs = 0
    for fn in msgfiles(d):
        live_path = os.path.join(d, fn)
        src = live_path + ".bak" if same else os.path.join(pristine, fn)
        if not os.path.exists(src):
            print(f"  ~ {fn}: no pristine source, skipped")
            continue
        live, n = read_records(live_path)
        orig, m = read_records(src)
        if live is None or orig is None or n != m:
            print(f"  ! {fn}: geometry mismatch, skipped", file=sys.stderr)
            continue
        touched = 0
        for i in range(n):
            b, _ = field_span(i)
            table = orig[b + TABLE:b + TEXT]
            if table.strip(b"\x00") == b"":
                continue
            if live[b + TABLE:b + TEXT] == table:
                continue
            plen = prompt_len(live, i)
            if plen > PROMPT_MAX:
                print(f"  ! {fn}:{i}: translated prompt is {plen}b and runs "
                      f"into the option table -- shorten it to {PROMPT_MAX} "
                      f"or less, then re-run")
                continue
            live[b + TABLE:b + TEXT] = table
            touched += 1
        if touched:
            fixed_files += 1
            fixed_recs += touched
            print(f"  {fn}: {touched} option table(s) "
                  f"{'restored' if apply_ else 'would be restored'}")
            if apply_:
                open(live_path, "wb").write(bytes(live))
    verb = "restored" if apply_ else "would be restored (dry run; pass --apply)"
    print(f"\n{fixed_recs} table(s) across {fixed_files} file(s) {verb}.")


def cmd_export(d, out):
    rows = []
    for fn in msgfiles(d):
        data, n = read_records(os.path.join(d, fn))
        if data is None:
            continue
        for i in range(n):
            if not has_table(data, i):
                continue
            for k, (label, value) in enumerate(get_slots(data, i)):
                if not label:
                    continue
                rows.append(dict(file=fn, record=i, slot=k,
                                 chinese=show(label), value=value,
                                 max_bytes=LABEL - 1, english=""))
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "record", "slot", "chinese",
                                           "value", "max_bytes", "english"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} option label(s) to {out}")


def cmd_import(d, csvpath, apply_):
    rows = [r for r in csv.DictReader(open(csvpath, encoding="utf-8-sig"))
            if r["english"].strip()]
    by_file = {}
    for r in rows:
        by_file.setdefault(r["file"], []).append(r)
    written = 0
    for fn, rs in sorted(by_file.items()):
        path = os.path.join(d, fn)
        if not os.path.exists(path):
            print(f"  ! {fn}: not found, skipped", file=sys.stderr)
            continue
        data, n = read_records(path)
        if data is None:
            print(f"  ! {fn}: geometry mismatch, skipped", file=sys.stderr)
            continue
        for r in rs:
            i, k = int(r["record"]), int(r["slot"])
            enc = r["english"].strip().encode("cp950")
            if len(enc) > LABEL - 1:
                print(f"  ! {fn}:{i} slot {k}: '{r['english']}' is "
                      f"{len(enc)}b, max {LABEL-1} -- skipped", file=sys.stderr)
                continue
            b, _ = field_span(i)
            p = b + TABLE + k * SLOT
            # label only; the u16 value is a branch target and is never touched
            data[p:p + LABEL] = enc.ljust(LABEL, b"\x00")
            written += 1
        if apply_:
            open(path, "wb").write(bytes(data))
    verb = "written" if apply_ else "would be written (dry run; pass --apply)"
    print(f"{written} label(s) {verb}.")


def cmd_labels(d, csvpath, apply_):
    """Apply a chinese->english label map to every matching slot everywhere."""
    table = {}
    for r in csv.DictReader(open(csvpath, encoding="utf-8-sig")):
        eng = r["english"].strip()
        if not eng:
            continue
        enc = eng.encode("cp950")
        if len(enc) > LABEL - 1:
            print(f"  ! '{eng}' is {len(enc)}b, max {LABEL-1} -- skipped",
                  file=sys.stderr)
            continue
        # match on the label with spacing removed; the source pads some labels
        # with ASCII/fullwidth spaces for centring (買 了, 我   有)
        table[r["chinese"].replace(" ", "").replace("\u3000", "")] = enc

    written = unmatched = 0
    seen = set()
    for fn in msgfiles(d):
        path = os.path.join(d, fn)
        data, n = read_records(path)
        if data is None:
            continue
        dirty = False
        for i in range(n):
            if not has_table(data, i):
                continue
            b, _ = field_span(i)
            for k, (label, _v) in enumerate(get_slots(data, i)):
                if not label:
                    continue
                key = show(label).replace(" ", "").replace("\u3000", "")
                seen.add(key)
                enc = table.get(key)
                if enc is None:
                    unmatched += 1
                    continue
                p = b + TABLE + k * SLOT
                data[p:p + LABEL] = enc.ljust(LABEL, b"\x00")
                written += 1
                dirty = True
        if dirty and apply_:
            open(path, "wb").write(bytes(data))

    missing = sorted(seen - set(table))
    if missing:
        print("no translation for: " + ", ".join(missing))
    verb = "written" if apply_ else "would be written (dry run; pass --apply)"
    print(f"{written} slot(s) {verb}; {unmatched} slot(s) left in Chinese.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("dir")
    r = sub.add_parser("restore")
    r.add_argument("dir"); r.add_argument("--pristine")
    r.add_argument("--apply", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("dir"); e.add_argument("-o", default="options.csv")
    m = sub.add_parser("import")
    m.add_argument("dir"); m.add_argument("csv")
    m.add_argument("--apply", action="store_true")
    l = sub.add_parser("labels")
    l.add_argument("dir"); l.add_argument("csv")
    l.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.cmd == "scan":
        cmd_scan(a.dir)
    elif a.cmd == "restore":
        cmd_restore(a.dir, a.pristine, a.apply)
    elif a.cmd == "export":
        cmd_export(a.dir, a.o)
    elif a.cmd == "labels":
        cmd_labels(a.dir, a.csv, a.apply)
    else:
        cmd_import(a.dir, a.csv, a.apply)


if __name__ == "__main__":
    main()
