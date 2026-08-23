#!/usr/bin/env python3
"""
translate_batch.py -- fill the english column of a Holy Island script CSV.

Sends the script to the Anthropic API in batches, with the proper-noun
glossary and per-line speaker IDs supplied as context so names stay
consistent and pronouns stay attached to the right character.

Design notes:
  * Rows typed 'command' are never sent -- those are asset cues.
  * Batches keep neighbouring records together so the model sees the
    conversation, not isolated lines. Dialogue depends on what precedes it.
  * The byte budget is stated per line so the model self-limits; wrap.py
    enforces it afterwards regardless.
  * Output is written incrementally, so an interrupted run is resumable.
    Re-running only translates rows whose english cell is still empty.

Setup:
    pip install anthropic
    set ANTHROPIC_API_KEY=sk-ant-...        (Windows)
    export ANTHROPIC_API_KEY=sk-ant-...     (macOS/Linux)

Usage:
    python translate_batch.py translate.csv glossary.csv -o translated.csv
    python translate_batch.py translate.csv glossary.csv -o translated.csv --limit 40
    python translate_batch.py translate.csv glossary.csv -o translated.csv --resume
"""

import argparse
import csv
import json
import os
import sys
import time

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

MODEL = "claude-sonnet-4-6"

SYSTEM = """You are translating the script of 聖光島 (Holy Island), a 1997 \
Taiwanese DOS role-playing game, from Traditional Chinese into English.

Register and tone:
- This is a fantasy RPG with a serious, often bleak story: poverty, tyranny, \
grief, abuse. Translate plainly and with feeling. Do not sanitise it, and do \
not inflate it into mock-Shakespearean "thee/thou" fantasy diction.
- 1997 Taiwanese RPG dialogue is direct and exclamatory. Keep that energy, \
but write natural modern English. Avoid translationese.
- The Chinese uses ！ very heavily. English does not. Convert most of them to \
full stops; keep exclamation marks only where there is real force.

Hard rules:
- Output ASCII only. No curly quotes, em dashes, ellipsis characters, or \
accented letters. Use ' and " and ... and -.
- EXCEPTION: full-width letters Ａ Ｂ Ｃ Ｄ Ｅ Ｆ are runtime name \
placeholders. Copy them through EXACTLY as they appear. Never translate, \
romanise, or drop them.
- The character ‧ is used as an ellipsis. Render it as ... (do not stack them).
- Use the supplied glossary for every proper noun, without exception.
- Stay within the stated byte budget for each line. Shorter is better.
- Translate only. Never add commentary, and never merge or split records.

Speaker IDs identify who is talking. The same ID is the same character \
throughout, so keep each character's voice and gender consistent. ID 01 is \
the player character, 65 is his mother, 00 is generic NPCs/narration."""


def build_glossary(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    seen, lines = set(), []
    for r in rows:
        zh = r["chinese"].strip()
        if not zh or zh in seen:
            continue
        seen.add(zh)
        note = (r.get("notes") or "").strip()
        lines.append(f"  {zh} = {r['english']}" + (f"   [{note}]" if note else ""))
    return "GLOSSARY (use these renderings exactly):\n" + "\n".join(lines)


def batches(rows, size):
    """Group rows into batches, keeping each .msg file contiguous."""
    cur, cur_file = [], None
    for r in rows:
        if cur and (r["file"] != cur_file or len(cur) >= size):
            yield cur
            cur = []
        cur.append(r)
        cur_file = r["file"]
    if cur:
        yield cur


def translate(client, glossary, batch, capacity, retries=3):
    payload = [{"id": i,
                "speaker": r.get("speaker", "??"),
                "budget": capacity,
                "zh": r["chinese"]}
               for i, r in enumerate(batch)]

    prompt = (
        f"{glossary}\n\n"
        f"Translate every line below. These are consecutive records from "
        f"{batch[0]['file']}, in order, so read them as a conversation.\n\n"
        f"Return ONLY a JSON array, one object per line, of the form "
        f'{{"id": <id>, "en": "<translation>"}}. No prose, no code fences.\n\n'
        + json.dumps(payload, ensure_ascii=False, indent=1)
    )

    for attempt in range(retries):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text")
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            out = {int(d["id"]): d["en"] for d in data}
            if len(out) != len(batch):
                print(f"    ! got {len(out)} of {len(batch)} lines")
            return out
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"    ! parse failure ({e}), retry {attempt+1}/{retries}")
        except Exception as e:
            print(f"    ! API error ({e}), retry {attempt+1}/{retries}")
            time.sleep(2 * (attempt + 1))
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_csv")
    ap.add_argument("glossary_csv")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--capacity", type=int, default=236)
    ap.add_argument("--limit", type=int, help="only process N rows (dry run)")
    ap.add_argument("--resume", action="store_true",
                    help="read --out and skip rows already translated")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.script_csv, encoding="utf-8-sig")))
    fields = list(rows[0].keys())

    if args.resume and os.path.exists(args.out):
        done = {(r["file"], r["record"]): r.get("english", "")
                for r in csv.DictReader(open(args.out, encoding="utf-8-sig"))}
        n = 0
        for r in rows:
            prev = done.get((r["file"], r["record"]), "")
            if prev.strip():
                r["english"] = prev
                n += 1
        print(f"resumed: {n} rows already translated")

    todo = [r for r in rows
            if r.get("type") != "command"
            and r["chinese"].strip()
            and not (r.get("english") or "").strip()]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} rows to translate\n")
    if not todo:
        sys.exit("nothing to do")

    client = anthropic.Anthropic()
    glossary = build_glossary(args.glossary_csv)
    index = {(r["file"], r["record"]): r for r in rows}

    def flush():
        with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    total = 0
    for bi, batch in enumerate(batches(todo, args.batch), 1):
        print(f"batch {bi}: {batch[0]['file']} x{len(batch)}", flush=True)
        result = translate(client, glossary, batch, args.capacity)
        for i, r in enumerate(batch):
            if i in result:
                index[(r["file"], r["record"])]["english"] = result[i]
                total += 1
        flush()

    print(f"\ntranslated {total} rows -> {args.out}")
    print("next: python wrap.py "
          f"{args.out} -o wrapped.csv   then msgtool2.py import")


if __name__ == "__main__":
    main()
