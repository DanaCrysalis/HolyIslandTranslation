#!/usr/bin/env python3
"""Bundle a whole Holy Island translation into ONE patch file, and apply it.

The patch (.hip) is a zip holding:
    manifest.json         per-file source SHA-256 + how to reconstruct it
    delta/<path>.xdelta   binary diff for each changed file
    whole/<path>          full bytes for files that are NEW in the English tree
                          (translator-authored, so no copyrighted original is
                          embedded)

Only diffs and translator-authored files ever travel -- never the untouched
game. The end user applies the .hip to their own pristine copy, and the source
SHA-256s make a wrong version (or an already-patched dir) fail loudly instead
of producing garbage.

Requires the `xdelta3` binary on PATH  (apt install xdelta3 / brew install xdelta).

    python3 mkpatch.py build PRISTINE_DIR ENGLISH_DIR holyisland-en.hip
    python3 mkpatch.py apply PRISTINE_DIR holyisland-en.hip OUT_DIR
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel_map(root: Path):
    """lowercased-relative-path -> real Path, for case-insensitive matching."""
    return {p.relative_to(root).as_posix().lower(): p
            for p in root.rglob("*") if p.is_file()}


def xdelta(args):
    try:
        subprocess.run(["xdelta3", *map(str, args)], check=True)
    except FileNotFoundError:
        sys.exit("xdelta3 not found on PATH.  "
                 "apt install xdelta3  /  brew install xdelta")


def build(pristine: Path, english: Path, out: Path):
    src, dst = rel_map(pristine), rel_map(english)
    manifest = {"format": 1, "files": []}
    with tempfile.TemporaryDirectory() as td, \
            zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        tmp = Path(td) / "d.xdelta"
        for key, npath in sorted(dst.items()):
            rel = npath.relative_to(english).as_posix()   # original casing
            if key in src:
                opath = src[key]
                if sha(opath) == sha(npath):
                    continue                              # unchanged: ship nothing
                xdelta(["-e", "-9", "-f", "-s", opath, npath, tmp])
                z.write(tmp, f"delta/{rel}.xdelta")
                manifest["files"].append({
                    "path": rel, "mode": "delta",
                    "src_sha256": sha(opath), "dst_sha256": sha(npath)})
            else:
                z.write(npath, f"whole/{rel}")            # new, translator-authored
                manifest["files"].append({
                    "path": rel, "mode": "whole", "dst_sha256": sha(npath)})
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
    print(f"wrote {out} covering {len(manifest['files'])} changed file(s)")


def apply(pristine: Path, hip: str, outdir: Path):
    src = rel_map(pristine)
    if outdir.exists():
        shutil.rmtree(outdir)
    shutil.copytree(pristine, outdir)          # full playable tree, then overlay
    with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(hip) as z:
        tmp = Path(td) / "d.xdelta"
        manifest = json.loads(z.read("manifest.json"))

        bad = [e["path"] for e in manifest["files"] if e["mode"] == "delta"
               and (e["path"].lower() not in src
                    or sha(src[e["path"].lower()]) != e["src_sha256"])]
        if bad:
            sys.exit("Source mismatch (wrong version, or already patched):\n  "
                     + "\n  ".join(bad))

        for e in manifest["files"]:
            target = outdir / e["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if e["mode"] == "whole":
                target.write_bytes(z.read(f"whole/{e['path']}"))
            else:
                tmp.write_bytes(z.read(f"delta/{e['path']}.xdelta"))
                xdelta(["-d", "-f", "-s", src[e["path"].lower()], tmp, target])
            if sha(target) != e["dst_sha256"]:
                sys.exit(f"Post-apply checksum failed: {e['path']}")
    print(f"patched tree written to {outdir}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("pristine", type=Path)
    b.add_argument("english", type=Path)
    b.add_argument("out", type=Path)
    p = sub.add_parser("apply")
    p.add_argument("pristine", type=Path)
    p.add_argument("hip")
    p.add_argument("outdir", type=Path)
    a = ap.parse_args()
    build(a.pristine, a.english, a.out) if a.cmd == "build" \
        else apply(a.pristine, a.hip, a.outdir)


if __name__ == "__main__":
    main()
