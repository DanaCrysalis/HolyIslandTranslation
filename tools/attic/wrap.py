#!/usr/bin/env python3
"""
SUPERSEDED -- use `textflow.py reflow` instead.

wrap.py predates two findings and will damage a current tree:

  * its --capacity default was 236, the whole text field. The last 36 bytes
    are the option table; a 236-byte prompt erases the choice rows in every
    shop, inn and the slave auction. The real prompt cap is 199. The default
    below has been corrected, but the tool is still not the one to use.
  * it is not marker-aware in the way textflow.py's wrap() is, and it was the
    pass that ate the spaces after moved words (`theworld`, `thinka`) which
    textflow.py unmerge then had to repair.

Kept only so the historical output can be understood. Do not run it on a tree
you care about.

wrap.py -- fit English dialogue to Holy Island's fixed line grid.

The engine does not word-wrap. It emits a fixed number of BYTES per line and
drops to the next line mid-word if it has to ("breakfas" / "t!"). The line
width is 30 bytes, which is 15 Chinese characters or 30 ASCII characters.

The fix is to wrap the text yourself and pad each line out to exactly the
line width with spaces, so the engine's hard break always lands where you
chose. This needs no patching of the executable.

Byte accounting:
    ASCII char        = 1 byte  = 1 cell
    Big5 char         = 2 bytes = 2 cells
    name token (Ａ-Ｆ) = 2 bytes = 2 cells   (preserved verbatim)

Usage:
    python wrap.py translate.csv -o wrapped.csv
    python wrap.py translate.csv -o wrapped.csv --width 30 --capacity 236
    python wrap.py translate.csv --preview          # show, don't write
"""

import argparse
import csv
import sys


# Runtime name placeholders. The engine swaps these for the character's
# actual name, which is LONGER than the token: Ａ (2 bytes) becomes 凡提
# (4 bytes). Padding computed against the token is therefore 2 bytes short
# per token, which shifts every following line.
TOKENS = set("ＡＢＣＤＥＦａｂｃｄｅｆ")
TOKEN_BYTES = 4


def blen(s, encoding="cp950"):
    """Byte length as the engine will RENDER it, not as stored.

    Placeholders are counted at their substituted width so that wrapping
    survives name substitution.
    """
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


def wrap_line(text, width, encoding="cp950"):
    """Word-wrap to `width` bytes per line. Returns a list of lines.

    Words longer than the line width are hard-split rather than dropped.
    """
    words = text.split()
    lines, cur = [], ""
    for w in words:
        wb = blen(w, encoding)
        if wb > width:
            # oversized word: flush, then hard-split it
            if cur:
                lines.append(cur)
                cur = ""
            piece = ""
            for ch in w:
                if blen(piece + ch, encoding) > width:
                    lines.append(piece)
                    piece = ch
                else:
                    piece += ch
            cur = piece
            continue
        cand = w if not cur else cur + " " + w
        if blen(cand, encoding) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def pad_lines(lines, width, encoding="cp950"):
    """Pad every line except the last out to exactly `width` bytes."""
    out = []
    for i, ln in enumerate(lines):
        if i == len(lines) - 1:
            out.append(ln)
        else:
            out.append(ln + " " * (width - blen(ln, encoding)))
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_in")
    ap.add_argument("-o", "--out")
    ap.add_argument("--width", type=int, default=30,
                    help="bytes per rendered line (default 30)")
    ap.add_argument("--max-lines", type=int, default=7,
                    help="max rendered lines the engine survives (default 7; "
                         "the original Chinese never exceeds this)")
    ap.add_argument("--token-bytes", type=int, default=4,
                    help="rendered width of a name placeholder (default 4, "
                         "for the default name)")
    ap.add_argument("--capacity", type=int, default=199,
                    help="prompt cap in bytes (199 main; the last 36 bytes of the "
                         "236-byte field are the option table)")
    ap.add_argument("--encoding", default="cp950")
    ap.add_argument("--preview", action="store_true",
                    help="print results instead of writing")
    ap.add_argument("--column", default="english")
    args = ap.parse_args()

    global TOKEN_BYTES
    TOKEN_BYTES = args.token_bytes
    line_cap = args.max_lines * args.width

    rows = list(csv.DictReader(open(args.csv_in, encoding="utf-8-sig")))
    if not rows:
        sys.exit("empty input")
    if args.column not in rows[0]:
        sys.exit(f"no '{args.column}' column in {args.csv_in}")

    done = over = untouched = 0
    padded_n = tight_n = 0
    problems = []

    for r in rows:
        text = (r.get(args.column) or "").strip()
        if not text:
            untouched += 1
            continue
        lines = wrap_line(text, args.width, args.encoding)

        # Preferred: pad each line so the engine's hard break lands on a word
        # boundary. Costs up to width-1 bytes per line, which on a long record
        # can push it past the render limit.
        packed = pad_lines(lines, args.width, args.encoding)
        nb = blen(packed, args.encoding)
        nl = len(lines)

        if nl <= args.max_lines and nb <= min(args.capacity, line_cap):
            mode = "padded"
            padded_n += 1
        else:
            # Fall back to unpadded: the engine wraps mid-word, which is ugly
            # but costs nothing and is what the original Chinese did anyway.
            flat = " ".join(lines)
            nbf = blen(flat, args.encoding)
            nlf = -(-nbf // args.width)
            if nlf <= args.max_lines and nbf <= min(args.capacity, line_cap):
                packed, nb, nl, mode = flat, nbf, nlf, "unpadded"
                tight_n += 1
            else:
                packed, nb, nl, mode = flat, nbf, nlf, "OVERFLOW"
                over += 1
                problems.append((r, nbf, nlf))

        r[args.column] = packed
        r["lines"] = nl
        r["packed_bytes"] = nb
        r["fit"] = mode
        done += 1

    print(f"wrapped {done} rows at {args.width} bytes/line, "
          f"max {args.max_lines} lines, token width {TOKEN_BYTES}")
    print(f"  {padded_n:>5} padded    (clean word breaks)")
    print(f"  {tight_n:>5} unpadded  (too tight to pad; breaks mid-word)")
    print(f"  {over:>5} OVERFLOW  (will not fit -- must be shortened)")
    print(f"  {untouched:>5} rows had no {args.column} text")
    if over:
        print(f"\n  !! {over} row(s) EXCEED THE RENDER LIMIT "
              f"({args.max_lines} lines):")
        for r, nb, nl in problems[:20]:
            print(f"    {r['file']} rec {r['record']}: "
                  f"{nb}B in {nl} lines -- SHORTEN, this may crash the game")
        if over > 20:
            print(f"    ... and {over-20} more")
        print("    (padding stripped for these, but they still need cutting)")

    if args.preview:
        print("\n--- preview ---")
        shown = 0
        for r in rows:
            t = r.get(args.column) or ""
            if not t.strip():
                continue
            print(f"\n{r['file']} rec {r['record']}  "
                  f"({r.get('packed_bytes','?')}B, {r.get('lines','?')} lines)")
            # slice by BYTES, exactly as the engine does -- slicing by Python
            # characters misreports any line holding a full-width token
            # Render as the ENGINE will: substitute each placeholder for a
            # name of the configured width, so the preview matches reality.
            shown_t = t
            for tok in TOKENS:
                if tok in shown_t:
                    shown_t = shown_t.replace(tok, "凡提"
                                              if TOKEN_BYTES == 4 else
                                              "N" * TOKEN_BYTES)
            enc = shown_t.encode(args.encoding, errors="replace")
            for i in range(0, len(enc), args.width):
                chunk = enc[i:i + args.width].decode(args.encoding,
                                                     errors="replace")
                print(f"  |{chunk}|")
            shown += 1
            if shown >= 8:
                break
        return

    if not args.out:
        sys.exit("\ngive -o OUTPUT.csv to write, or use --preview")

    fields = list(rows[0].keys())
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
