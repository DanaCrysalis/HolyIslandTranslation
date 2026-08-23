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
  4. patch_menu.py      title-menu alignment on top of the translated strings
  5. make_pstat_en.py   MUST overwrite PStat.GRP -- the only name the exe loads
  6. mapnames.py        then delete the .bak files it drops
  7. msgtool2.py import writes bytes 0..199 only; option tables survive

DATA_DIR holds the translator-side inputs that are NOT part of the game:
    names.csv             filled-in map area names, for `mapnames.py apply`
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
    print(f"[1/8] copy pristine tree -> {a.out}")
    shutil.copytree(a.game, a.out)

    exe = find(a.out, "game.exe")
    mapdir = find(a.out, "map")

    print("[2/8] game.exe string tables  (translate_all.py -- needs pristine bytes)")
    run(sys.executable, need(T, "translate_all.py"), exe, "-o", exe)

    print("[3/8] engine dialogs, combat log, cheat feedback  (exestrings.py)")
    run(sys.executable, need(T, "exestrings.py"), "apply", exe, "-o", exe)

    print("[4/8] banner width  imul 12 -> 16  (patch_banner.py)")
    run(sys.executable, need(T, "patch_banner.py"), exe, "-o", exe)

    print("[5/8] title-menu alignment  (patch_menu.py)")
    # If patch_menu also insists on pristine bytes it collides with step 2;
    # reconcile before shipping. See FINDINGS section 9, step 4.
    run(sys.executable, need(T, "patch_menu.py"), exe, "-o", exe)

    print("[6/8] status panel -> PStat.GRP  (the only name the exe loads)")
    pstat = find(a.out, "pstat.grp")
    run(sys.executable, need(T, "make_pstat_en.py"), a.out, pstat)

    print("[7/8] map area names  (mapnames.py apply)")
    run(sys.executable, need(T, "mapnames.py"), "apply", mapdir, a.data / "names.csv")
    for bak in mapdir.rglob("*.bak"):  # keep .bak out of the diff
        bak.unlink()

    print("[8/8] dialogue  (msgtool2.py import)")
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
