#!/usr/bin/env python3
"""
chatprep.py -- translate the Holy Island script using the Claude chat
interface instead of the API. No key, no billing, no extra cost.

Workflow
--------
1.  python chatprep.py split translate.csv glossary.csv -o chunks/

    Produces:
      chunks/00_INSTRUCTIONS.txt   paste ONCE at the start of a new chat
      chunks/01.txt, 02.txt, ...   paste one per message

2.  Open a new Claude conversation. Paste 00_INSTRUCTIONS.txt and send.
    Then paste 01.txt, send, and save the reply as chunks/01_reply.txt.
    Repeat. Any text editor works; the parser ignores surrounding prose.

    If the conversation gets long or starts drifting, start a fresh one
    and paste 00_INSTRUCTIONS.txt again.

3.  python chatprep.py merge translate.csv chunks/ -o translated.csv

    Reads every *_reply.txt, matches lines back by their [file:record]
    tag, and fills the english column.

Then continue as normal:
    python wrap.py translated.csv -o wrapped.csv
    python msgtool2.py import <mapdir> wrapped.csv --backup
"""

import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict

LINE_RE = re.compile(r'^\s*\[([^\]:]+):(\d+)\]\s*(.+?)\s*$')

RENDER_CAP = 210        # 7 lines x 30 bytes -- measured hard limit
TOKENS = set("ＡＢＣＤＥＦａｂｃｄｅｆ")
TOKEN_BYTES = 4         # Ａ renders as 凡提, which is 4 bytes

INSTRUCTIONS = """I am fan-translating 聖光島 (Holy Island), a 1997 Taiwanese \
DOS role-playing game, from Traditional Chinese into English. I will paste \
the script to you in numbered chunks. Please translate each chunk and return \
it in exactly the format described below.

TONE
- The story is serious and often bleak: poverty, tyranny, grief, abuse. \
Translate plainly and with feeling. Do not sanitise it.
- Do not use mock-archaic fantasy diction (no "thee", "thou", "'tis").
- 1997 Taiwanese RPG dialogue is direct and exclamatory, but Chinese uses ！ \
far more than English uses "!". Convert most of them to full stops and keep \
exclamation marks only where there is real force.
- Write natural modern English. Avoid translationese.

HARD RULES
- ASCII only. No curly quotes, em dashes, ellipsis characters, or accented \
letters. Use ' and " and ... and -.
- EXCEPTION: the full-width letters Ａ Ｂ Ｃ Ｄ Ｅ Ｆ are runtime name \
placeholders. Copy them through EXACTLY as they appear. Never translate, \
romanise, or delete them.
- The character ‧ is used as an ellipsis. Render it as ... (never stacked).
- Each translation must be at most {cap} characters. Shorter is better. \
Lines marked (TIGHT) are close to the limit -- be concise there.
- Use the glossary below for every proper noun, without exception.
- Translate only. No commentary, no notes, no merging or splitting of lines.

OUTPUT FORMAT
Return one line per input line, in the same order, exactly like this:

[game1.msg:0] Wake up! Come and eat breakfast.
[game1.msg:1] We have been eating food like this for so long.

Keep the [file:record] tag byte-for-byte identical to the input. Do not add \
blank lines between entries, and do not wrap the output in a code block.

SPEAKERS
Each line is tagged with a speaker ID. The same ID is the same character \
throughout, so keep voice and gender consistent for each. ID 01 is the player \
character, 65 is his mother, 00 is generic NPCs and narration.

{glossary}

Reply "Ready" and I will start pasting chunks."""


def build_glossary(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    seen, out = set(), []
    for r in rows:
        zh = r["chinese"].strip()
        if not zh or zh in seen:
            continue
        seen.add(zh)
        note = (r.get("notes") or "").strip()
        out.append(f"  {zh} = {r['english']}" + (f"   [{note}]" if note else ""))
    return "GLOSSARY (use these renderings exactly):\n" + "\n".join(out)


def est_english(zh):
    """Rough English byte need: ~2.2 ASCII chars per Chinese character."""
    return len(zh) * 2.2


def cmd_split(args):
    rows = [r for r in csv.DictReader(open(args.script, encoding="utf-8-sig"))
            if r.get("type") != "command" and r["chinese"].strip()
            and not (r.get("english") or "").strip()]
    if not rows:
        sys.exit("nothing to translate (all rows done, or all are commands)")

    os.makedirs(args.out, exist_ok=True)
    glossary = build_glossary(args.glossary)

    with open(os.path.join(args.out, "00_INSTRUCTIONS.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(INSTRUCTIONS.format(cap=RENDER_CAP, glossary=glossary))

    # Rows are already grouped by file, so packing straight through keeps each
    # file contiguous. Breaking on every file change would produce ~90 tiny
    # chunks, since the average .msg holds only ~13 lines.
    chunks = [rows[i:i + args.size] for i in range(0, len(rows), args.size)]

    for i, chunk in enumerate(chunks, 1):
        path = os.path.join(args.out, f"{i:02d}.txt")
        files = sorted({r["file"] for r in chunk})
        label = files[0] if len(files) == 1 else f"{files[0]}..{files[-1]}"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"Chunk {i} of {len(chunks)} "
                     f"({label}, {len(chunk)} lines)\n\n")
            for r in chunk:
                tight = " (TIGHT)" if est_english(r["chinese"]) > RENDER_CAP*0.75 else ""
                fh.write(f"[{r['file']}:{r['record']}] "
                         f"(speaker {r.get('speaker','??')}){tight} "
                         f"{r['chinese']}\n")

    print(f"{len(rows)} lines -> {len(chunks)} chunks in {args.out}/")
    print(f"  00_INSTRUCTIONS.txt   paste once per conversation")
    print(f"  01.txt .. {len(chunks):02d}.txt        paste one per message")
    print(f"\nSave each reply as {args.out}/NN_reply.txt "
          f"(e.g. 01_reply.txt), then run merge.")


TIGHTEN_HEADER = """These lines from my Holy Island translation are TOO LONG \
and will crash the game. The dialogue box renders 30 characters per line and \
survives at most 7 lines, so each translation must be at most {cap} \
characters INCLUDING spaces.

For each line below you have the original Chinese and my current English, \
with its length. Rewrite the English so it is under the limit. Keep the \
meaning and the tone. Cut filler, redundant clauses, and repeated pronouns \
rather than dropping content. Chinese is compact and often repeats an idea \
twice for emphasis -- in English, saying it once is usually enough.

Same rules as before: ASCII only, keep the full-width Ａ Ｂ Ｃ Ｄ Ｅ Ｆ name \
placeholders exactly as they appear, use ... for the ellipsis, and follow the \
glossary.

Return one line per entry in exactly this format, nothing else:

[game1.msg:0] The shortened English goes here.

"""


def cmd_tighten(args):
    """Extract over-limit rows for a compression pass."""
    rows = list(csv.DictReader(open(args.script, encoding="utf-8-sig")))
    cap = args.cap
    bad = []
    for r in rows:
        en = (r.get("english") or "").strip()
        if not en:
            continue
        n = sum(TOKEN_BYTES if c in TOKENS else len(c.encode("cp950",
                errors="replace")) for c in en)
        if n > cap:
            bad.append((r, n))

    if not bad:
        print(f"nothing over {cap} bytes -- all rows fit")
        return

    os.makedirs(args.out, exist_ok=True)
    glossary = build_glossary(args.glossary)
    path = os.path.join(args.out, "tighten.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(TIGHTEN_HEADER.format(cap=cap))
        fh.write(glossary + "\n\n")
        for r, n in bad:
            fh.write(f"[{r['file']}:{r['record']}]\n")
            fh.write(f"  Chinese: {r['chinese']}\n")
            fh.write(f"  Current ({n} chars, need under {cap}): "
                     f"{r['english']}\n\n")

    print(f"{len(bad)} row(s) over {cap} bytes -> {path}")
    print("Paste that into Claude, save the reply as "
          f"{args.out}/tighten_reply.txt, then run:")
    print(f"  python chatprep.py merge {args.script} {args.out} -o fixed.csv")


def cmd_merge(args):
    rows = list(csv.DictReader(open(args.script, encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    index = {(r["file"], r["record"]): r for r in rows}

    replies = sorted(glob.glob(os.path.join(args.chunks, "*_reply.txt")))
    if not replies:
        sys.exit(f"no *_reply.txt files in {args.chunks}/")

    filled, unknown, dupes = 0, [], 0
    seen = set()
    for path in replies:
        for raw in open(path, encoding="utf-8"):
            m = LINE_RE.match(raw)
            if not m:
                continue                      # ignore prose, blank lines, fences
            fname, rec, text = m.group(1), m.group(2), m.group(3)
            key = (fname, rec)
            if key not in index:
                unknown.append((os.path.basename(path), fname, rec))
                continue
            if key in seen:
                dupes += 1
            seen.add(key)
            index[key]["english"] = text
            filled += 1

    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    todo = [r for r in rows
            if r.get("type") != "command" and r["chinese"].strip()
            and not (r.get("english") or "").strip()]

    print(f"read {len(replies)} reply file(s)")
    print(f"  filled     {filled}")
    if dupes:
        print(f"  duplicates {dupes} (later value won)")
    if unknown:
        print(f"  unmatched  {len(unknown)} tag(s) not in the script:")
        for f, n, r in unknown[:10]:
            print(f"     {f}: [{n}:{r}]")
    print(f"  still to do {len(todo)}")
    print(f"\nwrote {args.out}")
    if todo:
        by = defaultdict(int)
        for r in todo:
            by[r["file"]] += 1
        top = sorted(by.items(), key=lambda kv: -kv[1])[:5]
        print("  missing most from: " +
              ", ".join(f"{k} x{v}" for k, v in top))
        print("  (re-run split on this output to regenerate only what is left)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("split", help="make paste-ready chunks")
    s.add_argument("script")
    s.add_argument("glossary")
    s.add_argument("-o", "--out", default="chunks")
    s.add_argument("--size", type=int, default=80,
                   help="lines per chunk (default 80)")
    s.set_defaults(func=cmd_split)

    t = sub.add_parser("tighten", help="extract over-limit rows for shortening")
    t.add_argument("script")
    t.add_argument("glossary")
    t.add_argument("-o", "--out", default="tighten")
    t.add_argument("--cap", type=int, default=200,
                   help="max rendered bytes (default 200, safely under 210)")
    t.set_defaults(func=cmd_tighten)

    m = sub.add_parser("merge", help="fold replies back into the CSV")
    m.add_argument("script")
    m.add_argument("chunks")
    m.add_argument("-o", "--out", default="translated.csv")
    m.set_defaults(func=cmd_merge)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
