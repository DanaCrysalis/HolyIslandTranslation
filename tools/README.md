# Tools

Three tools are in this repository. The other thirteen were written across the
reverse-engineering work and live in the working tree; **drop them into this directory**
before running `build_english.py`, which looks for them here by name and exits with a
clear message if one is missing.

They are not committed yet because they have never been reviewed as a set — several
carry hardcoded absolute paths from their original sessions, and a couple were edited
in place mid-session rather than versioned. Committing them unchanged would put paths
like `D:\Games\Emulators\DOS\Games\Holy Island` into a public repository.

## In this repository

| Tool | Purpose |
|---|---|
| `build_english.py` | Orchestrator. Copies pristine, runs every step in dependency order. |
| `mkpatch.py` | `build`/`apply` the single-file `.hip` distributable, with per-file source SHA-256 validation. |
| `verify_tree.py` | Structural check on a built tree: exe length and banner patch, GRP header consistency, map name field bounds, `.MSG` geometry and option-table integrity. |

## To be dropped in

| Tool | Signature | Verifies originals? |
|---|---|---|
| `holytool.py` | `export <file.grp\|vct> [outdir]` / `import <file.png> <original> <out>` / `exportall <gamedir> <outdir>` | n/a |
| `big5scan.py` | `<dir\|file> [-o report.txt] [-m 4] [--csv strings.csv]` | read-only |
| `probe.py` | `<file\|dir> [--glob '*.msg']` | read-only |
| `translate_all.py` | `<game.exe> [-o out.exe] [-n]` | **yes — needs a pristine exe** |
| `exestrings.py` | `report\|apply <game.exe> [-o out.exe]` | no; idempotent |
| `patch_banner.py` | `<game.exe> [-o out.exe] [-n] [--revert]` | **yes** |
| `patch_menu.py` | `<game.exe> [-o out.exe]` | unknown — see below |
| `make_pstat_en.py` | `<gamedir> <out.grp>` | n/a |
| `findnames.py` | `scan\|dump\|patch <dir\|file> [offset name]` | n/a |
| `mapnames.py` | `dump\|apply <mapdir> [names.csv]` | writes one `.bak`, once |
| `msgtool2.py` | `verify\|analyse\|export\|import <mapdir> ...` | no; idempotent |
| `optfix.py` | `scan\|restore\|export\|import\|labels <mapdir> ...` | no; idempotent |
| `textflow.py` | `check\|unmerge\|reflow <csv> [--col C] [--names ...]` | n/a |
| `markerfix.py` | `report\|fix <csv>` | n/a |
| `itemfit.py` | `<game.exe\|names.csv>` | read-only |

**Which verify and which do not decides build order.** `translate_all.py` and
`patch_banner.py` check original bytes and refuse an already-patched file, so they must
see pristine input — which is why the build always works on a throwaway copy.
`exestrings.py` and `msgtool2.py import` do not verify and are idempotent, so they can be
re-run over a patched tree freely.

**`patch_menu.py` is the unreconciled one.** It has never been confirmed whether it also
demands pristine bytes. If it does, it collides with `translate_all.py` running first and
one of the two has to change. Check this before the first clean build.

## Before committing any of them

1. Strip absolute paths; take directories as arguments.
2. Confirm `--help` works and the CLI matches the table above.
3. `python3 -m py_compile` clean.
4. No game data embedded — extracted tables belong in `data/`, not in source.

## Dependencies

`textflow.py unmerge` needs `wordsegment` and `wordfreq`; everything else is standard
library. `mkpatch.py` needs the `xdelta3` binary on PATH.

```
pip install -r ../requirements.txt
apt install xdelta3     # or: brew install xdelta
```
