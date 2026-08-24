# translated_updated.csv — three rows trimmed

`textflow.py reflow` reported 3 rows it could not pad to the 30-byte line grid:
they sat at 181–184 bytes flat, and padding pushed them 1–5 bytes past the
199-byte prompt cap. The tool wrote them unpadded rather than drop them, which
works but lets the engine break a word mid-line.

Each is trimmed by a few words. Meaning is unchanged and the glossary terms
(Kanon, Pafa Moro, Great Charter of Rank and Order, Jialu City, Dread Cavern)
are untouched.

| Row | Was | Now (padded) |
|---|---|---|
| game31.msg:44 | 181B → 203B padded | 177B → 188B |
| game5.msg:5 | 184B → 200B padded | 175B → 194B |
| game72.msg:19 | 184B → 204B padded | 180B → 189B |

Edits:

- **game31:44** — "let alone ordinary people" → "let alone anyone else"
- **game5:5** — "joining the privileged to grind down the poor and set class
  against class" → "setting the privileged to grind the poor and class against
  class"
- **game72:19** — "change beyond following" → "change past following";
  "though I've never been" → "though I've not been"

## After re-running the pipeline

```
0 rows fixed by markerfix (marker spacing was already correct)
916 rows re-wrapped
27 rows contain Ｅ/Ｆ
0 rows unpadded
0 rows over the cap
```

**The 27 marker rows are permanent and expected.** `Ｅ` expands at runtime to an
item name and `Ｆ` to a price, so their final width is not knowable when packing.
Checked against the worst case — the longest item name in the table (18 bytes)
and a six-digit price — and none can overflow the 199-byte cap. Nothing to do.
