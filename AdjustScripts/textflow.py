#!/usr/bin/env python3
"""
textflow.py -- repair merged words and re-wrap English .MSG dialogue.

THE DAMAGE
    The renderer does a hard 30-byte wrap with no word logic (proven by the
    original font test: "breakfas" / "t!"). So merged words like `theworld`
    or `thinka` are not a rendering artifact -- they are in the stored bytes,
    left by a line-breaking pass that moved a word to the next line and ate
    the space that followed it.

    check    list every row containing a merged word, with a suggested split
    unmerge  apply the splits
    reflow   collapse the old padding and re-wrap cleanly at 30 bytes

Run them in that order, reading `check` before trusting `unmerge`.

    python3 textflow.py check   translate.csv
    python3 textflow.py unmerge translate.csv -o step1.csv
    python3 textflow.py reflow  step1.csv     -o translate_fixed.csv

reflow pads each line to the 30-byte boundary so the next line starts where
you intend. Padding the LAST line of a choice prompt puts its options on a
line of their own.

Lines containing Ｅ or Ｆ cannot be wrapped exactly: the marker is 2 stored
bytes but draws as a whole item name or price at runtime. Those rows are
wrapped on their stored length and flagged.
"""

import argparse
import csv
import re
import sys

import wordsegment
from wordfreq import zipf_frequency

LINE = 30
PROMPT_CAP = 199
MARKERS = "ＡＢＣＤＥＦ"
COL = "english"

# Proper nouns from the glossary. wordsegment will happily cut these into
# plausible-looking English fragments, so they are never split.
PROTECTED = {
    "holy", "island", "tajira", "mengjun", "dejia", "jialu", "xuanen",
    "hamanu", "sugeli", "jielisha", "shiban", "xili", "rhapsody", "moro",
    "pafa", "sius", "rosa", "kanon", "meia", "mandela", "lian", "ali",
    "das", "xiaomei", "zhuzhu", "lily", "cao", "xiaoan", "zhuang",
    "xiaojun", "aju", "aqi", "kurt", "xiong", "dading", "lin", "vanilla",
    "jiayi", "benlong", "gusha", "panneroia", "joshua", "claudie", "vanti",
    "nirvana", "cranberries", "cranberry", "michael", "jackson",
    "windrift", "chillfrost", "benlong", "shiban", "monody",
    # ordinary vocabulary the segmenter also gets wrong
    "petrification", "stonelands", "hardworking",
}

MIN_MERGE = 5          # do not touch short tokens; too many false positives
# Every piece of a split must be at least this common. Proper nouns segment
# into rare fragments (meng/jun, panner/oia, ji/elisha) and are rejected here;
# genuine merges split into ordinary words. Calibrated against the glossary:
# the rarest true merge seen is this/dynasty at 3.4M, the commonest false one
# is Zhuzhu at 1.1M.
FREQ_FLOOR = 3_000_000
# A token this common in real English is a word, not a merge. Closed compounds
# (cannot, someone, throughout, landslide) all sit at 3.5+; the merges seen in
# this script (theworld 1.9, tothe 2.2, thinka 0.0) sit well below.
WORD_ZIPF = 3.4
TOKEN = re.compile(r"[A-Za-z]+")


def freq(w):
    return wordsegment.UNIGRAMS.get(w.lower(), 0)


def plausible(parts):
    """A split is only trusted if every piece is a real, common word.

    Note this deliberately does NOT check whether the merged token itself is
    in the corpus: `theworld` is (web-scraped junk), and checking membership
    was what let it through in the first place. A multi-part segmentation is
    the signal; real words like `breakfast` segment to a single part.
    """
    if not 2 <= len(parts) <= 3:
        return False
    for p in parts:
        if p in ("a", "i"):
            continue
        if len(p) < 2 or freq(p) < FREQ_FLOOR:
            return False
    return True


def seam_on_boundary(text, start, parts):
    """True if the join sits exactly on a 30-byte line boundary.

    Reflowed text stores its lines concatenated and padded to 30 bytes. When a
    line ends on a word with no padding left over, the next line's first word
    butts straight up against it: `...are black the` + `world over...` reads as
    `theworld` but DRAWS as two words on two lines. Splitting it would insert a
    byte and shift every later line break in the record.
    """
    off = blen(text[:start])
    for k in range(1, len(parts)):
        if (off + blen("".join(parts[:k]))) % LINE == 0:
            return True
    return False


def find_merges(text):
    """[(token, split), ...] for tokens that look like two words run together."""
    out = []
    for m in TOKEN.finditer(text):
        tok = m.group(0)
        low = tok.lower()
        if len(tok) < MIN_MERGE or low in PROTECTED:
            continue
        if len(set(low)) == 1:
            continue        # placeholder junk (xxxxxxxx), copied through as-is
        if zipf_frequency(low, "en") >= WORD_ZIPF:
            continue        # a real word, however odd it looks
        parts = wordsegment.segment(low)
        if len(parts) < 2 or not plausible(parts):
            continue
        if seam_on_boundary(text, m.start(), parts):
            continue        # a reflow seam, not damage
        # preserve the original capitalisation of the first character
        fixed = " ".join(parts)
        if tok[0].isupper():
            fixed = fixed[0].upper() + fixed[1:]
        out.append((tok, fixed))
    return out


def blen(s):
    try:
        return len(s.encode("cp950"))
    except UnicodeEncodeError:
        return len(s)


def wrap(text):
    """Greedy 30-byte word wrap, marker-aware.

    A marker (Ｅ item name, Ｆ price) is 2 stored bytes but draws as whatever
    it substitutes -- an item name can be 19 characters. Everything after it
    on the same line therefore slides right by an unpredictable amount and the
    wrap lands mid-word. Nothing can pad around that.

    What CAN be controlled is where the marker starts. So when the text
    contains one, the run before it is padded out to a line boundary, putting
    the substituted text at the left margin, and the rest is left unpadded --
    padding after a marker only adds bytes without aligning anything.
    """
    first = min((text.index(c) for c in MARKERS if c in text), default=-1)
    if first < 0:
        return wrap_plain(text)
    # No padding from the first marker onward. Padding placed after a marker
    # does not align anything -- the substitution shifts it by an unknown
    # amount at runtime, and the surplus spills onto the next line as a
    # leading indent that every later line inherits.
    head, tail = text[:first].strip(), text[first:].strip()
    if not head:
        return tail
    padded = wrap_plain(head)
    padded += " " * ((-blen(padded)) % LINE)
    return padded + tail


def wrap_plain(text):
    """Greedy 30-byte word wrap. Every line but the last is padded to 30."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if blen(trial) <= LINE:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # a single word longer than a line has to be broken by the engine
            while blen(w) > LINE:
                lines.append(w[:LINE])
                w = w[LINE:]
            cur = w
    if cur:
        lines.append(cur)
    padded = [ln + " " * (LINE - blen(ln)) for ln in lines[:-1]]
    return "".join(padded) + (lines[-1] if lines else "")


def rows_of(path, col):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if rows and col not in rows[0]:
        sys.exit(f"no '{col}' column in {path}")
    if col != COL and rows and COL not in rows[0]:
        for r in rows:
            r[COL] = ""
    return rows


def write(rows, out):
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def cmd_check(path, col=COL):
    rows = rows_of(path, col)
    hits = 0
    for r in rows:
        text = r.get(col, "")
        merges = find_merges(text)
        if not merges:
            continue
        hits += 1
        print(f"\n{r.get('file','?')}:{r.get('record','?')}")
        for tok, fixed in merges:
            print(f"    {tok}  ->  {fixed}")
    print(f"\n{hits} of {len(rows)} row(s) contain a merged word.")


def cmd_unmerge(path, out, col=COL):
    rows = rows_of(path, col)
    changed = 0
    for r in rows:
        text = r.get(col, "")
        merges = find_merges(text)
        for tok, fixed in merges:
            text = re.sub(r"\b" + re.escape(tok) + r"\b", fixed, text)
        # always carry the text through, or rows without merges drop out of
        # the pipeline when reading from a non-default column
        r[COL] = text
        if merges:
            changed += 1
    write(rows, out)
    print(f"{changed} row(s) unmerged -> {out}")


def cmd_reflow(path, out, col=COL):
    rows = rows_of(path, col)
    changed = flagged = toolong = nopad = 0
    for r in rows:
        text = r.get(col, "")
        if not text.strip():
            continue
        flat = " ".join(text.split())
        new = wrap(flat)
        if blen(new) > PROMPT_CAP and blen(flat) <= PROMPT_CAP:
            # padding to the 30-byte boundary costs up to 29 bytes a line.
            # Rather than lose the record, drop the padding and let the engine
            # wrap where it likes -- a mid-word break beats a skipped import.
            new = flat
            nopad += 1
        if blen(new) > PROMPT_CAP:
            toolong += 1
            print(f"  ! {r.get('file','?')}:{r.get('record','?')} is "
                  f"{blen(new)}B after reflow, over the {PROMPT_CAP}B cap")
        if any(c in text for c in MARKERS):
            flagged += 1
        if new != text:
            r[COL] = new
            changed += 1
    write(rows, out)
    print(f"{changed} row(s) re-wrapped -> {out}")
    if flagged:
        print(f"{flagged} row(s) contain Ｅ/Ｆ and cannot be wrapped exactly; "
              f"check those in game")
    if nopad:
        print(f"{nopad} row(s) were too long to pad; written unpadded, so the "
              f"engine may break a word mid-line")
    if toolong:
        print(f"{toolong} row(s) exceed the prompt cap and need cutting")


def main():
    wordsegment.load()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("csv")
    u = sub.add_parser("unmerge")
    u.add_argument("csv"); u.add_argument("-o", "--out", default="unmerged.csv")
    f = sub.add_parser("reflow")
    f.add_argument("csv"); f.add_argument("-o", "--out", default="reflowed.csv")
    for p in (c, u, f):
        p.add_argument("--col", default=COL,
                       help="source column (use --col chinese for a "
                            "msgtool2 export of an already-translated tree; "
                            "the result is always written to 'english')")
    a = ap.parse_args()
    if a.cmd == "check":
        cmd_check(a.csv, a.col)
    elif a.cmd == "unmerge":
        cmd_unmerge(a.csv, a.out, a.col)
    else:
        cmd_reflow(a.csv, a.out, a.col)


if __name__ == "__main__":
    main()
