# Holy Island — English translation

A fan translation of **聖光島** (*Holy Island*, also listed as 聖光島：摩羅王朝戰記), a
1997 Taiwanese DOS RPG by 世紀縱橫, published through Soft-World.

This repository holds the **research, tooling and translation data**. It does not and
will not contain any part of the game. The distributable is a validated diff applied to
your own pristine copy.

---

## What is here

```
docs/
  FINDINGS.md           the single reference: formats, offsets, patches, glossary
  ITEM_NAMES.md         canonical item names and why each was cut to fit
  PLAYTEST.md           open bugs from playing the build end to end
  TRANSLATION_BRIEF.md  the working prompt, pasteable verbatim
data/
  item_names.csv        canonical item names, keyed by Big5
  map_names.csv         English area names, keyed by Big5
  *.example             schemas for the working CSVs (real ones are untracked)
tools/
  build_english.py      orchestrator: pristine tree -> English tree
  mkpatch.py            bundle/apply the .hip distributable
  verify_tree.py        structural check on a built tree
  *.py                  the reverse-engineering tools
  workflow/             translation-side, not part of the build
  attic/                superseded. Read for history, do not run.
  README.md             what each tool does and which verify originals
```

`docs/FINDINGS.md` is the authoritative document. Everything else is either derived
from it or a working file it describes.

---

## State of the translation

Playable start to finish in English. Dialogue, item and spell tables, engine dialogs,
map banners, the status panel and the choice rows in shops and the slave auction are all
done and verified in play.

**Open before a public release:**

| | |
|---|---|
| `MAP035.DAT` hard-locks under DOSBox | PCem runs the same tree correctly. Not yet A/B'd against pristine. `docs/PLAYTEST.md` |
| No ending or credits reached | Never located in the files, and never reached in a full playthrough |
| Item names diverge dialogue vs inventory | Canonical set decided, not yet applied. `docs/ITEM_NAMES.md` |
| `demo.msg` untranslated | 21 records of real content on a different 243-byte stride |
| Title-menu alignment unverified | Most likely thing still needing a nudge |

---

## Building

You need a pristine Chinese copy of the game, Python 3.9+, and `xdelta3` on PATH for the
packaging step.

```bash
python3 tools/build_english.py \
    --game  /path/to/PRISTINE \
    --data  ./data \
    --out   ./BUILD

python3 tools/verify_tree.py ./BUILD
python3 tools/mkpatch.py build /path/to/PRISTINE ./BUILD holyisland-en.hip
```

Build order is not negotiable — several tools verify original bytes and refuse to run on
an already-patched file, and one silently corrupts the tree if run late. The orchestrator
encodes the order; `docs/FINDINGS.md` §9 explains it.

Four tools are still missing — `translate_all.py`, `patch_menu.py`, `make_pstat_en.py`
and `holytool.py`. The orchestrator names any it cannot find and stops, so the build
fails cleanly rather than half-completing. See `tools/README.md`.

## Applying (end users)

```bash
python3 mkpatch.py apply /path/to/your-pristine-copy holyisland-en.hip ./HolyIsland-EN
```

Every file the patch touches carries a SHA-256 of the source it expects, so a wrong
dump, a wrong region, or an already-patched folder fails before a single byte is written.

---

## Two traps worth knowing before you touch anything

**The 0x5C trap.** Big5 trail bytes include `0x5C` (`\`) and `0x7C` (`|`). Any tool that
treats this data as text, or shell-escapes it, silently corrupts the dump. Work in
`bytes`, never `str`, until the very last step.

**The `.MSG` text field is not 236 bytes of text.** Its last 36 bytes are a fixed option
table used by every choice prompt in the game. A writer that pads the full field erases
all 84 of them; the prompt still renders and the options simply never appear. Prompts
have **199** usable bytes.

---

## Legal

The tools and documentation here are MIT-licensed (see `LICENSE`). The game is not ours
and is not distributed here in any form — no game files, no extracted assets, no script
in its original language beyond the short quotations needed to document formats and
glossary decisions. The patch carries only binary diffs and translator-authored text,
and is useless without a copy of the original.
