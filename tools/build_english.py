#!/usr/bin/env python3
"""Build a fully English Holy Island tree from a pristine Chinese copy.

Runs every translation tool in dependency order against a *fresh copy* of the
game, so the tools that demand a pristine game.exe always see one. Nothing here
touches your original -- everything happens under --out.

    python3 build_english.py --game PRISTINE_DIR --data DATA_DIR --out BUILD_DIR

Order matters. See docs/FINDINGS.md section 9:

  1. translate_all.py   VERIFIES original bytes; refuses an already-patched exe
  2. exestrings.py      idempotent; dialog labels, combat log, cheat feedback
  3. patch_banner.py    VERIFIES; one-byte imul 12 -> 16 in the banner routine

There is NO patch_menu.py. A byte diff of the pristine and shipped executables
shows exactly ONE code change in the whole image -- the banner imul at
0x28FB1. The title menu is aligned by leading spaces inside its strings
("  EXIT", "  AUDIO"), which travel in the string table like any other text.
  4. make_pstat_en.py   MUST overwrite PStat.GRP -- the only name the exe loads
  6. apply_names.py     keyed by Big5, so the map###b.dat variants that
                        share a name are covered; then delete its .bak files
  7. msgtool2.py import writes bytes 0..199 only; option tables survive

DATA_DIR holds the translator-side inputs that are NOT part of the game:
    map_names.csv         English area names keyed by Big5, for apply_names.py
    strings_worksheet.csv game.exe UI / item / spell tables, for translate_all.py
    pstat_en.bin          status-panel pixel overlay, for make_pstat_en.py
    translated_final.csv  build artifact from the textflow/markerfix pipeline
    option_labels.csv      English choice labels (only needed on a fresh build)
(translate_all.py and make_pstat_en.py carry their own data.)
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT_CAP = 199  # bytes 0..199 of the .MSG text field; +200 is the option table


def run(*cmd, optional=False):
    print("  $", " ".join(str(c) for c in cmd))
    try:
        subprocess.run([str(c) for c in cmd], check=True)
    except FileNotFoundError:
        if optional:
            print("    (skipped: tool not present)")
            return
        raise


def find(d: Path, name: str) -> Path:
    """DOS names are case-insensitive; match regardless of case on disk."""
    for p in d.iterdir():
        if p.name.lower() == name.lower():
            return p
    raise FileNotFoundError(f"{name} not found in {d}")


def need(tools: Path, name: str) -> Path:
    p = tools / name
    if not p.exists():
        sys.exit(f"missing tool: {p}\n"
                 f"See tools/README.md -- the reverse-engineering tools live in "
                 f"your working tree and must be dropped in here.")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, type=Path, help="pristine game dir")
    ap.add_argument("--data", required=True, type=Path, help="translation data dir")
    ap.add_argument("--out", required=True, type=Path, help="build output dir")
    ap.add_argument("--tools", type=Path, default=Path(__file__).parent,
                    help="dir holding the .py tools")
    ap.add_argument("--fresh-labels", action="store_true",
                    help="also write English option labels (needed on a build "
                         "from pristine, since that restores the Chinese ones)")
    a = ap.parse_args()
    T = a.tools

    if a.out.exists():
        shutil.rmtree(a.out)
    print(f"[1/7] copy pristine tree -> {a.out}")
    shutil.copytree(a.game, a.out)

    exe = find(a.out, "game.exe")
    mapdir = find(a.out, "map")

    print("[2/7] game.exe string tables  (translate_all.py -- needs pristine bytes)")
    run(sys.executable, need(T, "translate_all.py"), exe, "-o", exe,
        "--csv", a.data / "strings_worksheet.csv")

    print("[3/7] engine dialogs, combat log, cheat feedback  (exestrings.py)")
    run(sys.executable, need(T, "exestrings.py"), "apply", exe, "-o", exe)

    print("[4/7] banner width  imul 12 -> 16  (patch_banner.py)")
    run(sys.executable, need(T, "patch_banner.py"), exe, "-o", exe)

    print("[5/7] status panel -> PStat.GRP  (the only name the exe loads)")
    run(sys.executable, need(T, "make_pstat_en.py"), a.out,
        "--delta", a.data / "pstat_en.bin")

    print("[6/7] map area names  (apply_names.py)")
    run(sys.executable, need(T, "apply_names.py"), mapdir,
        "--csv", a.data / "map_names.csv")
    for bak in mapdir.rglob("*.bak"):  # keep .bak out of the diff
        bak.unlink()

    print("[7/7] dialogue  (msgtool2.py import)")
    run(sys.executable, need(T, "msgtool2.py"), "import", mapdir,
        a.data / "translated_final.csv", "--max-bytes", str(PROMPT_CAP))
    if a.fresh_labels:
        print("      option labels  (optfix.py labels)")
        run(sys.executable, need(T, "optfix.py"), "labels", mapdir,
            a.data / "option_labels.csv", "--apply")

    print("\nverifying...")
    verify = T / "verify_tree.py"
    if verify.exists():
        run(sys.executable, verify, a.out)

    print(f"\nDone. English tree in {a.out}")


if __name__ == "__main__":
    main()
