# Contributing

## Ground rules

**No game data in this repository.** No `game.exe`, no `.msg`, no `.grp`, no extracted
art, no audio. `.gitignore` blocks the obvious extensions; if you find yourself
overriding it, stop and ask why.

**Work in `bytes`, never `str`.** Big5 trail bytes include `0x5C` (`\`) and `0x7C` (`|`).
Any code path that treats this data as text, or shell-escapes it, corrupts the dump
silently. Decode at the last possible moment.

**Write full fields, zero-padded.** Never `string + NUL`. Assigning a slice of a
different length to a Python `bytearray` inserts or deletes bytes and shifts the entire
file, which silently corrupts everything downstream. Writing the full field also cleans
up the linker alignment junk sitting in the gaps.

**Run `verify_tree.py` before opening a PR** that touches any tool in the build path.

## Translating

Paste `docs/TRANSLATION_BRIEF.md` verbatim at the start of a session. It carries the
tone rules, the hard constraints and the full glossary, and the glossary is not optional
— a proper noun rendered two ways is a bug, and an item name rendered two ways is a
soft-lock.

Edit `data/translated_updated.csv`. Never edit `translated_final.csv`.

```
textflow.py unmerge     # only on text recovered from disk
markerfix.py fix        # spaces around the Ａ-Ｆ runtime markers
textflow.py reflow      # line breaks and 30-byte padding
msgtool2.py import --max-bytes 199
```

## Reporting a bug

`docs/PLAYTEST.md` is the log. A useful report names the emulator and its config, since
at least one open bug is emulator-dependent, and says whether it reproduces on a
**pristine Chinese tree** — that single A/B decides whether a bug is ours at all, and
the `JUMP <mapname>` cheat (F1) makes it a one-minute test.

## Changing a documented offset or format

`docs/FINDINGS.md` is the single reference and several numbers in it were wrong once
before. If you correct one, say what the old value was and what disproved it — the
document keeps that history deliberately, because the wrong values were plausible and
will be rediscovered otherwise.
