#!/usr/bin/env python3
"""
apply_names.py - write English area names into every map###.dat.

The area name is a 20-byte null-padded Big5 field at offset 0x3C.
Budget is 19 bytes plus a terminator.

Usage:
    python apply_names.py <mapdir>          patch
    python apply_names.py <mapdir> --dry    report only, write nothing
    python apply_names.py <mapdir> --revert restore from .bak

Every file gets a .bak on first touch, once only, so re-running never
overwrites a pristine backup with a patched one.
"""

import sys, os, glob, shutil

NAME_OFF = 0x3C
NAME_LEN = 20

# Keyed by the original Big5 string. Every .dat carrying that name is patched.
NAMES = {
    # --- Mengjun City and the opening area ---
    "主角的家":   "Hero's House",
    "孟郡城北":   "Mengjun City North",
    "孟郡城西":   "Mengjun City West",
    "孟郡城東":   "Mengjun City East",
    "孟郡城南":   "Mengjun City South",
    "孟郡城郊外": "Mengjun Outskirts",
    "孟郡森林":   "Mengjun Forest",
    "孟郡王城":   "Mengjun Palace",
    "莉莉的家":   "Lily's House",
    "老婆婆的家": "Old Woman's House",

    # --- Tajira and the northern woods ---
    "泰吉拉":     "Tajira",
    "泰吉拉北":   "Tajira North",
    "泰吉拉南":   "Tajira South",
    "泰吉拉郊外": "Tajira Outskirts",
    "西籬溫泉":   "Xili Hot Spring",
    "西籬楓林":   "Xili Maple Woods",
    "風之林":     "Wind Forest",
    "芳心湖北":   "Lonely Lake North",
    "幽徑森林":   "Hidden Path Forest",
    "石碑幽徑":   "Stele Path",
    "神之洞穴":   "Cave of the God",

    # --- Vale of Grief / Ravaged Stonelands ---
    "殘慟谷":     "Vale of Grief",
    "殘餘洞":     "Remnant Cave",
    "殘缺森林":   "Broken Forest",
    "聖壇":       "Holy Altar",
    "耗劫石地":   "Ravaged Stonelands",

    # --- Hamanu ---
    "哈曼奴":     "Hamanu",
    "哈曼奴近郊": "Hamanu Outskirts",
    "哈曼大旅社": "Haman Grand Inn",
    "旅社地下室": "Inn Basement",
    "黑煞森林":   "Black Curse Forest",
    "黑煞沼澤":   "Black Curse Marsh",

    # --- Jialu City ---
    "嘉露城":     "Jialu City",
    "嘉露城近郊": "Jialu Outskirts",
    "嘉露森林":   "Jialu Forest",
    "嘉露劇院":   "Jialu Opera House",

    # --- Dejia Old Town and the crypt ---
    "疾靈森林":   "Wraith Forest",
    "德佳古":     "Dejia Old Town",
    "德佳古東":   "Dejia East",
    "針織橋":     "Needlework Bridge",
    "碎冥墓穴":   "Shattered Crypt",

    # --- Mount Dread ---
    "怖懼山洞口": "Dread Cavern Mouth",
    "怖懼山洞":   "Dread Cavern",
    "邪惡祭壇":   "Evil Altar",
    "石像廟":     "Statue Temple",
    "蝙蝠洞":     "Bat Cavern",
    "小木屋":     "Log Cabin",

    # --- Jielisha and Shiban Harbor ---
    "捷里沙":     "Jielisha",
    "捷里沙近郊": "Jielisha Outskirts",
    "石斑港":     "Shiban Harbor",
    "石斑港北":   "Shiban Harbor North",
    "石斑港西":   "Shiban Harbor West",

    # --- Ruins ---
    "廢墟郊外":   "Ruins Outskirts",
    "巫士廢墟":   "Sorcerers' Ruins",
    "遺跡郊外":   "Benlong Outskirts",
    "奔龍遺跡":   "Benlong Ruins",

    # --- Sugeli ---
    "蘇格禮":     "Sugeli",
    "蘇格禮郊外": "Sugeli Outskirts",

    # --- Xuan'en City and the frozen north ---
    "宣恩城":     "Xuan'en City",
    "宣恩城郊外": "Xuan'en Outskirts",
    "冰寒森林":   "Frozen Forest",
    "冰寒大廳":   "Frozen Hall",

    # --- Endgame ---
    "炎灼石廟":   "Blazingstone Temple",
    "烈風地窖":   "Windrift Vault",
    "聖光島":     "Holy Island",
    "聖光島入口": "Holy Island Entry",
    "聖光島大廳": "Holy Island Hall",
    "聖光島二樓": "Holy Island 2F",
    "聖光島三樓": "Holy Island 3F",
    "聖光島四樓": "Holy Island 4F",
    "聖光島頂樓": "Holy Island Top",
}


def find_dats(directory):
    """Every .dat in the directory, case-insensitive, no duplicates."""
    seen = {}
    for p in glob.glob(os.path.join(directory, "*")):
        if p.lower().endswith(".dat"):
            seen.setdefault(os.path.basename(p).lower(), p)
    return [seen[k] for k in sorted(seen)]


def revert(directory):
    n = 0
    for p in find_dats(directory):
        if os.path.exists(p + ".bak"):
            shutil.copy2(p + ".bak", p)
            n += 1
    print(f"restored {n} files from .bak")


def main(directory, dry=False):
    # Table sanity check before touching anything on disk.
    bad = [(k, v) for k, v in NAMES.items() if len(v.encode("ascii")) > NAME_LEN - 1]
    if bad:
        for k, v in bad:
            print(f"  !! over budget ({len(v)}B): {v}")
        return 1

    patched = untranslated = 0
    missing = set()

    for path in find_dats(directory):
        name = os.path.basename(path)
        with open(path, "rb") as f:
            f.seek(NAME_OFF)
            field = f.read(NAME_LEN)

        raw = field.split(b"\x00")[0]
        if not raw:
            continue

        # Already patched on a previous run: field is plain ASCII.
        if all(0x20 <= b < 0x7F for b in raw):
            continue

        try:
            original = raw.decode("big5")
        except UnicodeDecodeError:
            print(f"  !! {name}: field is not valid Big5, skipped")
            continue

        english = NAMES.get(original)
        if english is None:
            missing.add(original)
            untranslated += 1
            continue

        enc = english.encode("ascii").ljust(NAME_LEN, b"\x00")

        print(f"  {name:16s} -> {english}")
        if not dry:
            if not os.path.exists(path + ".bak"):
                shutil.copy2(path, path + ".bak")
            with open(path, "r+b") as f:
                f.seek(NAME_OFF)
                f.write(enc)
        patched += 1

    verb = "would patch" if dry else "patched"
    print(f"\n{verb} {patched} files")
    if missing:
        # Printed as hex so a cp1252 console cannot choke on it.
        print(f"{untranslated} files had names not in the table:")
        for m in sorted(missing):
            print("  " + m.encode("big5").hex())
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = sys.argv[1]
    flags = [a.lower() for a in sys.argv[2:]]
    if "--revert" in flags:
        revert(d)
    else:
        sys.exit(main(d, dry="--dry" in flags))
