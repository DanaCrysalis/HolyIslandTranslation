#!/usr/bin/env python3
"""audit.py -- report rendered size of every record as it sits on disk."""
import argparse, glob, os
from collections import Counter

FILE_HDR, REC, HDR, W = 32, 253, 17, 30
TRAIL = set(range(0x40,0x7F)) | set(range(0xA1,0xFF))
TOKENS = set("ＡＢＣＤＥＦ")

def extract(rec):
    f = rec[HDR:]; i = 0
    while i < len(f)-1:
        if 0x81 <= f[i] <= 0xFE and f[i+1] in TRAIL: i += 2
        elif 0x20 <= f[i] <= 0x7E: i += 1
        else: break
    return f[:i].decode("cp950", errors="replace"), f[:i]

def rendered(t):
    return sum(4 if c in TOKENS else len(c.encode("cp950","replace")) for c in t)

def scan(path):
    d = open(path,"rb").read()
    out = []
    for i in range((len(d)-FILE_HDR)//REC):
        b = FILE_HDR + i*REC
        rec = d[b:b+REC]
        if len(rec) < REC: break
        t, raw = extract(rec)
        rb = rendered(t)
        out.append(dict(record=i, text=t, bytes=rb, lines=-(-rb//W),
                        spk=rec[1],
                        en=(sum(1 for x in raw if 0x20<=x<=0x7E)/len(raw) > .8)
                            if raw else None))
    return out

ap = argparse.ArgumentParser()
ap.add_argument("mapdir"); ap.add_argument("--file")
ap.add_argument("--min-lines", type=int, default=7)
a = ap.parse_args()

if a.file:
    for r in scan(os.path.join(a.mapdir, a.file)):
        if not r["text"]: continue
        flag = "!!" if r["lines"] > 7 else ("* " if r["lines"] == 7 else "  ")
        print(f'{r["record"]:>4} spk={r["spk"]:02X} {r["bytes"]:>4}B '
              f'{r["lines"]}ln {flag}{r["text"][:64]}')
    raise SystemExit

hist, bad = Counter(), []
for p in sorted(glob.glob(os.path.join(a.mapdir,"*.msg"))):
    for r in scan(p):
        if not r["text"]: continue
        hist[r["lines"]] += 1
        if r["lines"] >= a.min_lines:
            bad.append((os.path.basename(p), r))
for k in sorted(hist):
    mark = "  <-- OVER" if k > 7 else ("  <-- at limit" if k == 7 else "")
    print(f"  {k:>2} lines: {hist[k]:>5}{mark}")
print(f"\n{len(bad)} record(s) at/over {a.min_lines} lines:")
for f, r in bad[:40]:
    print(f'  {f} #{r["record"]}: {r["bytes"]}B / {r["lines"]}ln  {r["text"][:56]}')