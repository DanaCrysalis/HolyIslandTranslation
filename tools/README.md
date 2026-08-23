# Tools

Everything the build needs is here except four scripts that were never in
`AdjustScripts/` — see **Still missing** below.

```
tools/
  build_english.py   orchestrator: pristine tree -> English tree
  mkpatch.py         build/apply the single-file .hip distributable
  verify_tree.py     structural check on a built tree

  translate_all.py   MISSING -- exe string tables
  patch_menu.py      MISSING -- title-menu alignment
  make_pstat_en.py   MISSING -- status panel art
  holytool.py        MISSING -- .grp/.vct sprite export/import

  exestrings.py      engine dialogs, combat log, cheat feedback
  patch_banner.py    banner width, imul 12 -> 16 at 0x28FAF
  apply_names.py     write English map area names
  mapnames.py        dump/inspect map area names
  msgtool2.py        .msg export / import
  optfix.py          .msg option table repair and label translation
  textflow.py        line breaking, merged-word repair
  markerfix.py       spacing around the Ａ-Ｆ runtime markers
  itemfit.py         item-name byte budgets and canonical reconciliation
  big5scan2.py       locate Big5 prose in unknown binaries
  probe.py           derive record geometry from string positions
  findnames.py       locate and patch the default party names

  workflow/          translation-side, not part of the build
  attic/             superseded. Read for history, do not run.
```

## Which tools verify originals, and which do not

This is what decides build order.

| Tool | Verifies? | Consequence |
|---|---|---|
| `translate_all.py` | **yes** | refuses an already-patched exe; must run first, on pristine bytes |
| `patch_banner.py` | **yes** | checks for `6B C0 0C`; `--revert` puts it back |
| `exestrings.py` | no | idempotent, re-runnable over a patched tree |
| `msgtool2.py import` | no | idempotent; writes text into fixed offsets |
| `optfix.py` | no | idempotent |
| `apply_names.py` | partial | skips fields that are already plain ASCII |

## Still missing

Four scripts are referenced by the docs and by `build_english.py` but are not in
`AdjustScripts/`. The orchestrator exits with a clear message naming any one it can't
find, so the build fails cleanly rather than half-completing.

| Tool | What it does | Why it can't be reconstructed |
|---|---|---|
| `translate_all.py` | Writes the `game.exe` UI, spell and item string tables | Carries its own offset/verification data |
| `patch_menu.py` | Title-menu alignment | Carries the menu offsets |
| `make_pstat_en.py` | Renders the English status panel into `PStat.GRP` | Carries the pixel art |
| `holytool.py` | `.grp` / `.vct` sprite sheet export and import | Format handling for the art container |

`itemfit.py` and `markerfix.py` were also missing and **have been written fresh** — they
are new code, not recovered, so read them before trusting them on a live tree.

## Changes made to the scripts as they came out of AdjustScripts

None of them had hardcoded paths, and all compiled clean, so the adjustments were about
correctness and safety rather than portability.

**`apply_names.py`** — the 71-entry English name table was an embedded `NAMES` dict.
Moved to `data/map_names.csv` (`--csv` overrides), so game-derived data lives in `data/`
per `CONTRIBUTING.md`. Added `--help`, which previously fell through and silently
"patched 0 files" while treating `--help` as a directory name. Behaviour is otherwise
identical, including the `.bak`-once rule and the already-ASCII skip.

This is now the tool the build calls, not `mapnames.py apply`, because it keys on the
**original Big5 string** rather than the filename — which means the `map###b.dat`
night/interior variants that share a name are patched from the same row automatically.
`mapnames.py` stays for `dump`.

**`textflow.py`** — `wordsegment` and `wordfreq` were imported at module scope, so
`reflow` (which needs neither) died on an unrelated `ImportError` and even `--help`
failed. Imports are now lazy: `check` and `unmerge` load the word list and print an
install hint if it's absent; `reflow` runs without them.

**`exestrings.py`** — `-o` was parsed as `sys.argv[sys.argv.index("-o") + 1]`, which
raises `IndexError` if `-o` is the last argument. Now checked.

**`build_english.py`** — step 7 switched from `mapnames.py apply names.csv` to
`apply_names.py --csv map_names.csv`, for the keyed-by-Big5 reason above.

**`verify_tree.py`** — the stray-`.bak` warning named only `mapnames.py`;
`msgtool2 --backup` drops them too.

## attic/

Superseded, kept so old output can be understood. Each carries a banner saying why.

**`msgtool.py` is actively dangerous** — it assumes a 49-byte header and a 204-byte text
field. The real layout is a 32-byte file header then 253-byte records of
`[17-byte record header][236-byte text field]`, proven by `game31.msg` solving exactly as
`32 + 134*253`. Importing with it writes text over record headers.

**`wrap.py`** defaulted `--capacity` to 236, the whole text field including the option
table — running it would erase the choice rows in every shop and the slave auction. The
default is corrected to 199 in the copy here, but `textflow.py reflow` is the tool to
use. `wrap.py` was also the pass that ate spaces after moved words (`theworld`,
`thinka`), which `textflow.py unmerge` then had to repair.

**`big5scan.py`** demanded that decoded runs be mostly CJK ideographs — but the Big5
standard plane *is* mostly CJK ideographs, so random VGA data passed at ~100%.
`big5scan2.py` discriminates on character frequency instead.

**`audit.py`** and **`bytetest.py`** are one-off diagnostics: rendered size per record,
and the CSV generator used to find the 199-byte prompt cap empirically.

## workflow/

Translation-side, not part of the build. `chatprep.py` splits the script into
paste-sized chunks with the glossary and merges the replies back;
`translate_batch.py` does the same through the Anthropic API and needs a key;
`prep.py` classifies rows as command / dialogue / placeholder / mixed, which is what
keeps asset cues like `MStg85.ANM` from being translated.

## Dependencies

`textflow.py check` and `unmerge` need `wordsegment` and `wordfreq`;
`workflow/translate_batch.py` needs `anthropic`. Everything else is standard library.
`mkpatch.py` needs the `xdelta3` binary on PATH.

```
pip install -r ../requirements.txt
apt install xdelta3     # or: brew install xdelta
```
