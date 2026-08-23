# Holy Island — project notes

Single reference for the fan translation of 聖光島 (*Holy Island*, also listed as
聖光島：摩羅王朝戰記), a 1997 DOS RPG by 世紀縱橫, published through Soft-World.

Supersedes and absorbs the previous `FINDINGS.md`, `MAP_NAMES.md` and
`00_INSTRUCTIONS.txt`.

Engine string in the exe: `RPG Game System ver7.00 (c)Copyright 1997/09/02 by YOKI`
(at file 0x89B81). `game.exe` is a plain uncompressed LE / DOS4GW binary — Watcom,
32-bit flat model, 622,929 bytes — so all data is patchable in place.

---

# 1. Status at a glance

**Confirmed rendering in DOSBox:**

- Dialogue box renders ASCII correctly (NPC conversations verified in play).
- Map-name banner renders ASCII and **centres** the string rather than drawing at
  a fixed X.
- Engine confirm dialogs render ASCII, centre correctly, and their button frames
  track label width.
- Choice/option rows and shop prompts render ASCII.

**Confirmed by full playtest (2026-08):** shops, inns and the slave auction present
their choice rows correctly; the dialogue tree is playable start to finish; map banners
render English at the patched 16 px/byte width.

**Still unverified in game:** title-menu alignment; `Retype` as the right sense on
the name-entry cancel button; the 13-byte option-row width (measured off a
screenshot, not disassembled).

**Open bug:** `MAP035.DAT` ("Back to Hamanu, fast.") loads an empty mountain path with
no persons present and hard-locks — **under DOSBox only; PCem runs the same tree
correctly.** See `PLAYTEST.md`.

**Never located:** the ending / credits sequence. Confirmed absent in a full playthrough
— the game does not present an ending or credits, which upgrades this from "not found in
the files" to "not reached in play".

**Never touched:** `demo.msg`, `demo01`–`demo07.dat`, `demo.ini`, `gameobj.dat`.

---

# 2. What lives where

| Screen | Source | How to translate |
|---|---|---|
| Title menu, options menu | strings in `game.exe` | patch bytes |
| Fight menu, element names | strings in `game.exe` | patch bytes |
| Item names (316) | table in `game.exe` | patch bytes |
| Spells / status / monsters (57) | table in `game.exe` | patch bytes |
| Engine confirm dialogs, cheat feedback, combat log | strings in `game.exe` | patch bytes |
| Intro crawl | strings in `game.exe` | patch bytes |
| Character status panel | baked artwork in `pstat.grp` | repaint pixels |
| Map area-name banners | field at 0x3C of each `map###.dat` | patch bytes |
| Party default names | `game.ini` / `demo.ini` (party tables, not INIs) | patch bytes |
| All dialogue | `game*.msg` (95 files) + `demo.msg` | tool pipeline |
| Fight window art | no text at all | nothing to do |

`pstat2.grp` is the same status panel **already in English** — Name / HitPoint /
MagicPoint / Strength / Attack / Defense / Agility / Dexterity / Karma. The exe never
loads it (it only ever references `PStat.GRP`), so it is a leftover from an abandoned
English build. It has 9 stat rows where the shipping Chinese panel has 13, and rows
sit ~3px lower, so it is not a drop-in replacement — but it is a useful reference for
house style.

**The 0x5C trap.** Big5 trail bytes include 0x5C (`\`) and 0x7C (`|`). Any tool that
treats this data as text, or shell-escapes it, will silently corrupt the dump. Work in
`bytes`, never `str`, until the very last step.

---

# 3. File formats

## game.pal
768 bytes, 256 × (R,G,B), **full 8-bit range** — do not shift left by 2 as you would
for a 6-bit VGA palette. The palette contains duplicate RGB entries, so index → RGB →
index is not reversible; unedited pixels must keep their original index and only
genuinely changed pixels get re-matched.

## .GRP — uncompressed cel sheet
```
u16 width | u16 height | u16 cel_count | u8 pad
cel_count * (width*height) bytes of palette indices
```
Verified: `menu.grp` = 16×16 × 9 → 7 + 9*256 = 2311 = exact file size.

## .VCT — same header, then sparse runs
```
u16 width | u16 height | u16 cel_count | u8 pad
cel_count * { u32 file_offset ; u32 byte_length }
each cel: u16 run_count, then run_count * { u16 x ; u16 y ; u16 len ; len bytes }
```
Uncovered pixels are transparent. Verified on `fmenu.vct`: all 8 cels consume their
declared length to the byte.

PNG round-trip is byte-identical on all 21 assets tested.

## FONT.GRP
- Latin: **8 × 15**, 15 bytes per glyph, base 0, ASCII order.
  It is *not* 8×16. Assuming 16 makes the first few CP437 glyphs look right and then
  silently returns the wrong letter for everything from about `A` upward.
- Big5: 16 × 16, 32 bytes per glyph, base `0x1004`, index 0 = Big5 `0xA140`.
  (Note the 4-byte gap at 0x1000.)

## FONT24.GRP
- Latin: **16 × 24**, 48 bytes per glyph, base 0, ASCII order.
- Big5: 24 × 24, 72 bytes per glyph, base `0x3000`, index 0 = Big5 `0xA440`.
  Subtract 471 from the standard index — the symbol block is omitted.
  13502 glyphs = 86 × 157, covering `A440`–`F9FE` exactly.

Shared index formula:
```
index = (hi - 0xA1) * 157 + (lo - 0x40 if lo < 0x7F else lo - 0x62)
```

**The two fonts do not share a layout.** This caused real rework; do not assume.

## map###.dat header
A run of five 20-byte, null-padded fields. Example, `map001.dat`:

| Offset | Size | Contents | What it is |
|---|---|---|---|
| 0x00 | 20 | `MAP001.GRP` | tile sheet for this map |
| 0x14 | 20 | `MSTG03` | sound / SFX reference |
| 0x28 | 20 | `CD2` + `01.XMI` | music: CD-DA track tag + XMI fallback |
| **0x3C** | **20** | area name, Big5 | **the banner string** |
| 0x50 | 20 | `MAP005B.DAT` | linked sub-map |

The exe reaches this as a `0x6A`-byte current-map record at data offset `0x10BC8`,
indexed by the map number in `[0x3260]` — five 20-byte fields plus 6 trailing bytes,
which independently confirms the layout above.

## game.ini / demo.ini
Despite the names, these are the **initial party table**: four person records on the
`0x9E` (158-byte) stride with a 20-byte name field at offset 0. 4 × 0x9E = 0x278, and
0x278 is where names stop and other data begins, so four is the whole party. The exe
opens `game.ini` directly (string at 0x89A48, overlapping into `PosGame.INI` in the
pool). `demo.ini` holds the attract-mode party.

## .SAV
Save files carry their own copy of party names, so name changes need a **new game** to
test. Name field is 20 bytes at offset 0 of a 158-byte person record, so a save editor
reaches it directly.

---

# 4. Patching game.exe

## The basic rule, and the correction to it

Strings are null-terminated in a pool and referenced by address, so a replacement can
never be longer than **its field**. Shorter is fine — pad with zeros. Write the *full*
field zero-filled rather than string+NUL, so linker alignment junk gets cleaned up too.

The original note said "never longer than the original", which understates the room.
Watcom aligns these to 4 bytes and leaves the gaps filled with garbage (`ot `, `h m`,
`\nNo` — junk, not strings; nothing points at them). The real field is the distance to
the next *referenced* offset.

**How to derive fields correctly.** Scanning the code segment for `push imm32` /
`mov r32, imm32` operands landing in the data segment produces false positives. The
authoritative source is the **LE relocation table**: obj2 is based at VA 0x80000 and
the immediates hold object-relative placeholders; each has a fixup record carrying the
real target, and **the loader overwrites the instruction operand at load time**. Patch
the imm32 and the game ignores you. The set of fixup targets in object 2 is the
complete, exact list of string starts — **1465 of them**.

**Relocating a string** (to escape a squeezed field) means patching the fixup record's
target field, not the call site. Findable: the main-menu cancel is page 26, source
offset 0x1C6, target 2804; the combat-log string is page 13, source offset 0xB27,
target 1960.

**Free space for relocation:** object 1 has **1645 zero bytes of page padding at file
0x89393–0x899FF** (virtsize 0x62993, 99 pages rounds to 0x63000). obj2's file image is
packed solid — no hole 24 bytes or larger. Worth one test string to confirm the loader
maps the padding rather than truncating at virtsize.

## The spacing trick

The title labels have an ASCII space between every Chinese character
(`AD AB 20 B7 73 20 ...`), which is why a naive search for the 8-byte sequence finds
nothing. Several other UI strings hide the same way — search spaced variants before
concluding a string is absent.

## Metrics for centring at 24px

A 4-glyph Chinese label with spaces is `4*24 + 3*16 = 144 px`. Latin is 16px wide
there, so 9 ASCII characters fill the same width exactly.

## String tables

| Group | Location | Count | Budget |
|---|---|---|---|
| UI / menus / prompts / intro crawl | scattered, 0x89000–0x8B300 | 52 | varies, 2–44 bytes |
| Spells, status, monsters | 0x93768, stride 0x40 | 57 | 20 chars |
| Item names | 0x8CD68, stride 0x54 | 316 | 19 chars |

Item records are 84 bytes with the name in a fixed **20-byte** field at offset 0.

`translate_all.py` patches all 425 in one pass. It verifies the original Big5 bytes at
every offset before writing and refuses to run if anything mismatches, so it must be
run against a **pristine** `game.exe`, not an already-patched one.

Important implementation detail: replacements are written into the *full* available
field, zero-padded to its exact length. Assigning a slice of a different length to a
Python `bytearray` inserts or deletes bytes and shifts the entire file — which
silently corrupts everything downstream.

## Engine confirm dialogs

Six call sites all reach the **same routine at file 0x28754**, args pushed
right-to-left as `(prompt, ok_label, cancel_label)`:

| Call site | prompt | ok | cancel |
|---|---|---|---|
| 0x3FBD4 | Open the main menu? (0x8A504) | 啟動 0x8A4FC | 取消 0x8A4F4 |
| 0x4097F | Quit the game? (0x8A524) | `Exit` 0x8A51C | 取消 0x8A4F4 |
| 0x29BB1 | Quit the demo? | 否 0x89CCC | 是 0x89CD0 |
| 0x2A6A6 | Use the default name? | 確定 0x89EFC | `More` 0x89EF4 |
| 0x2A6DE | Use this new name? | 確定 0x89EFC | `More` 0x89EF4 |

取消 is **one shared string** — one patch fixes both boxes. These are engine dialogs,
not script: right-click and Escape are not dialogue nodes, so `optfix.py` will never
touch them, and `translate_all.py` never warned about them because a string absent
from the worksheet is a string it does not know exists.

**Patched state** (via `exestrings.py`, which derives every field from the fixup table
and is idempotent):

| | was | now |
|---|---|---|
| main menu | 啟動 / 取消 | Open / Cancel |
| quit game | Exit / 取消 | Exit / Cancel |
| quit demo | 是 / 否 | Yes / No |
| name entry | 確定 / More | OK / Retype |
| combat log | `%s對%s使用%s` | `%s -> %s: %s` |
| item use / spell learned / level up | 使用%s, 學會%s, %s升級 | Use %s, Got %s, %s up! |
| cheats | 得金錢10000, 開啟 | Got 10000 gold, ON |

`▼` at ds+0x60C is the more-text arrow glyph and is deliberately untouched.

**Linker-merge hazard.** 0x8A1A8 is `%s對%s使用%s` and 0x8A1AC is `%s使用%s` — the
short one is a byte-suffix of the long one, merged by the linker. The long one turned
out to have no fixup pointing at it (a dead tail), so 0x7A8 is a single live string
with a **16-byte** field; but a naive independent patch of the two produces the hybrid
`%s對%s uses %s`. The 16-byte write at 0x8A1A8 covers the whole field and cleans it.

**Verification of the patched exe (static):** size identical; MZ stub, LE header,
object table, fixup page table, fixup record table and all of object 1 byte-for-byte
unchanged; same 1465 relocation targets; 0 new field overruns; 0 changed `%s` counts
(a format string with more specifiers than arguments reads garbage off the stack, so
this was the real crash risk); all 13 slots NUL-terminated inside their own fields.
84 bytes changed across 19 regions.

## The banner width patch

The banner routine at **VA 0x12558 / file 0x28F58** measures the string with `strlen`
and allots **12 px per byte**:

```
call    strlen
add     esp, 4
imul    eax, eax, 12          <-- file 0x28FAF
mov     ebx, 640
sub     ebx, eax
shr     ebx, 1                ; text x = (640 - 12n)/2 = 320 - 6n
add     eax, ebx
lea     esi, [ebx - 36]       ; frame left
lea     edi, [eax + 36]       ; frame right
...
push 0x67 ; push ebx ; push [0x10BC0] ; call draw_string   ; y = 103
```

12 px/byte is correct for Big5 (2 bytes → one 24 px FONT24 glyph) but wrong for the
16×24 Latin block, which advances 16 px per byte. Measured from screenshots
(640×480, n = string length in bytes): frame = 12n + 52, text origin = 320 − 6n,
overhang = 4n − 26. The frame is quantised as `roundup(12n+72,16) − 28`.

**The patch:** file offset `0x28FAF`, `6B C0 0C` (`imul eax,eax,12`) → `6B C0 10`
(`imul eax,eax,16`). One byte actually changes; length identical, nothing shifts.
Frame becomes 16n + 52, origin 320 − 8n, 36 px of frame either side, no clipping at
the 19-byte ceiling (frame runs x=132..508 on a 640 px screen).

**Is the multiply shared?** Effectively no. 0x12558 has five callers: `0x2CB83`,
`0x31BAA`, `0x31C49`, `0x62D19` — all `("%s", map_header+0x3C)`, the banner — plus
`0x2BE59`, the `使用%s` "Use *item*" popup, which becomes ASCII too once that string
and the item table are patched. No measure loop needed, no padding fallback.

**Does the frame tile or stretch?** It tiles. The frame blitter at VA `0x48A48` does
`(x2-x1+15)>>4` and `(y2-y1+15)>>4` — a 16×16 cel grid. The inner box at VA `0x50070`
is a per-pixel palette remap over a plain rectangle. Both scale to any width.

There is a byte-identical twin of this routine at VA `0x12632` (imul at file
`0x290A5`). No `call rel32` reaches it and its address appears nowhere in the file as
a dword — dead code from an earlier revision. Left alone.

`patch_banner.py` verifies the engine version string, the full 24-byte instruction
window, and re-reads the output; it no-ops if already patched and takes `--revert`.

---

# 5. The status panel

Labels are baked artwork; the characters appear nowhere in the exe. Text is a dark
core (palette index **237**) with a light bevel (**241**) one pixel below each stroke,
on parchment background 242.

Fixed geometry that must not be disturbed, because the runtime blits values at fixed
coordinates:

| Row | y (label top) | Chinese | English | Space available |
|---|---|---|---|---|
| 1 | 37 | 姓　名 | Name | x21–71, colon at 72–73 → 6 chars |
| 2 | 55 | 生命值 | HP | same |
| 3 | 73 | 法　力 | MP | same |
| 4 | 91 | 經驗值 | Exp | same |
| 5 | 111 | 技　巧 | Skill | same |
| 6 | 127 | 負載值 | Load | same |
| 7 | 145 | 攻擊力 | Attack | same |
| 8 | 163 | 防禦力 | Defend | same |
| 9 | 181 | 反應力 | **Reflex** | same |
| 10 | 199 | 敏捷度 | **Speed** | same |
| 11 | 222 | 法術抗拒力 | Resistance | x21–105, no colon → 10 chars |
| 12 | 240 | 水 / 火 | Wtr / Fir | colons fixed at x40–41 and x104–105 → 3 chars each |
| 13 | 258 | 風 / 地 | Wnd / Ert | same |

`make_pstat_en.py` erases each label by copying clean parchment from 86px to the
right — that region is where the game draws the values at runtime, so it is guaranteed
empty and it preserves the paper texture instead of leaving a flat rectangle.

**Known defect:** the erase window is about 3px too short at the bottom, so stray
bevel pixels from the original Chinese survive at y=52 (x26–27, 34–35) and y=70
(x21–23). The y=196 and y=214 instances were cleaned by hand during the Reflex/Speed
re-cut; rows 1 and 2 still have theirs.

## What those two stats actually do

Traced through the combat code, which is why the labels are Reflex and Speed rather
than a literal React/Agile.

**反應力 (record offset 0x55) is the to-hit / evade roll.** `0x5A37C` is
`get_effective_stats(actor, *atk, *def, *react)`, called twice at the top of the melee
resolver at `0x5186C` — once for attacker, once for defender. Then:

```
if (att_react > def_react) {
    d = att_react - def_react;
    r = rand() & (d < 40 ? 0x27 : d);
} else {
    r = rand() & 9;
}
if (r < 3) return MISS;              // 0x519B8
damage = att_attack - def_defense;   // 0x519C4
```

A straight opposed check. Losing it drops you to `rand()&9`, which yields {0,1,8,9}
and therefore misses half the time; winning gives `rand()&0x27`, roughly 19% miss. The
roll is symmetric, so the same number is accuracy on offence and evasion on defence —
which is why "Aim" would have hidden half the meaning. The ranged/monster variant at
`0x51B80` uses the same contest.

Supporting detail worth knowing: a defender with a disabling status has react forced
to **0** (`0x518F7`), which is why status effects feel like guaranteed hits rather
than good odds. A stunned attacker has attack *and* react halved (`0x518C8`). The
consumable at `0xD226` doubles attacker react for a fixed number of swings and
decrements per use — a charge-based accuracy item, not a timed one, distinct from the
`+0x59/+0x5D` buff pair in the record itself.

**敏捷度 (record offset 0x61) is the ATB fill rate.** Two routines, and 0x61 appears
nowhere else in combat:

- `0x28CC4` — scans the party for the highest *base* 敏捷度 and stores `max * 10` at
  `0xD21C` as the action threshold; also sums equipment agility into `0x115D0[i]`.
- `0x28D68` — each tick, every living combatant does `gauge[+0x96] += 敏捷度 +
  equip_bonus`. A second loop applies the same to monsters.
- `0x5412D` — `if (gauge >= [0xD21C] && hp > 0) { gauge = 0; take_turn(); }`

So the fastest party member acts once every 10 ticks and everyone else scales down
proportionally. The threshold uses base agility only while the gauge uses base +
equipment, so agility gear genuinely pushes you above the baseline.

---

# 6. Map area names

The banner that appears on entering a new area (`孟郡城北` on entering map 2) is a
**string in the map's `.dat` header**, not artwork. The signboard frame is drawn by the
engine; `map002.grp` and `map002b.grp` contain no text at all.

## Where it lives

Offset **0x3C**, 20 bytes, null-padded, **Big5** (consistent with `game.exe` and the
fonts — searching as GBK finds nothing). A regex sweep for double-byte Big5 runs over
the whole of `map002.dat` returns **exactly one hit**, at 0x3C. Area names are the only
Chinese text in the map files, so a search-and-replace cannot catch anything else.
Dialogue lives in `.MSG`, not here.

`map002b.dat` carries the same name at the same offset, which is why the outdoor map
and its interior variant announce themselves identically. Both files need patching or
the banner reverts on re-entry. The tooling therefore keys on the **original Big5
string** and patches every `.dat` carrying it.

## Budget

19 bytes plus a terminator. Fields are on a clean 20-byte stride and the runtime reads
them as a fixed struct, so **do not** let a name run past 0x4F into the linked-map
field. Writes are length-checked and zero-padded to the full 20 bytes — the same rule
as `translate_all.py`, and for the same reason.

Two names sit at exactly 19 bytes, filling the field: **Shiban Harbor North** and
**Blazingstone Temple**. Four more sit at 18: Mengjun City North, Mengjun City South,
Hidden Path Forest, Ravaged Stonelands.

## Rendering — resolved

Both open questions from the old `MAP_NAMES.md` are now closed. The banner routine
**does** render the FONT24 Latin block, and the engine **centres** rather than drawing
at a fixed X. The width bug that came with that is fixed by `patch_banner.py`
(section 4). No fullwidth-Latin fallback and no leading-edge padding are needed.

## The name table

Keyed by original Big5. Note that these are deliberately compressed against the
19-byte budget and so diverge from the prose glossary in section 10 (no leading "the",
`Blazingstone` as one word, `Shattered Crypt` for the Shattered Gloom Crypt). That is
intentional; do not "fix" one to match the other without re-checking the budget.

**Mengjun City and the opening area**
```
主角的家     Hero's House          孟郡城北   Mengjun City North
孟郡城西     Mengjun City West     孟郡城東   Mengjun City East
孟郡城南     Mengjun City South    孟郡城郊外 Mengjun Outskirts
孟郡森林     Mengjun Forest        孟郡王城   Mengjun Palace
莉莉的家     Lily's House          老婆婆的家 Old Woman's House
```
**Tajira and the northern woods**
```
泰吉拉       Tajira                泰吉拉北   Tajira North
泰吉拉南     Tajira South          泰吉拉郊外 Tajira Outskirts
西籬溫泉     Xili Hot Spring       西籬楓林   Xili Maple Woods
風之林       Wind Forest           芳心湖北   Lonely Lake North
幽徑森林     Hidden Path Forest    石碑幽徑   Stele Path
神之洞穴     Cave of the God
```
**Vale of Grief / Ravaged Stonelands**
```
殘慟谷       Vale of Grief         殘餘洞     Remnant Cave
殘缺森林     Broken Forest         聖壇       Holy Altar
耗劫石地     Ravaged Stonelands
```
**Hamanu**
```
哈曼奴       Hamanu                哈曼奴近郊 Hamanu Outskirts
哈曼大旅社   Haman Grand Inn       旅社地下室 Inn Basement
黑煞森林     Black Curse Forest    黑煞沼澤   Black Curse Marsh
```
**Jialu City**
```
嘉露城       Jialu City            嘉露城近郊 Jialu Outskirts
嘉露森林     Jialu Forest          嘉露劇院   Jialu Opera House
```
**Dejia Old Town and the crypt**
```
疾靈森林     Wraith Forest         德佳古     Dejia Old Town
德佳古東     Dejia East            針織橋     Needlework Bridge
碎冥墓穴     Shattered Crypt
```
**Mount Dread**
```
怖懼山洞口   Dread Cavern Mouth    怖懼山洞   Dread Cavern
邪惡祭壇     Evil Altar            石像廟     Statue Temple
蝙蝠洞       Bat Cavern            小木屋     Log Cabin
```
**Jielisha and Shiban Harbor**
```
捷里沙       Jielisha              捷里沙近郊 Jielisha Outskirts
石斑港       Shiban Harbor         石斑港北   Shiban Harbor North
石斑港西     Shiban Harbor West
```
**Ruins**
```
廢墟郊外     Ruins Outskirts       巫士廢墟   Sorcerers' Ruins
遺跡郊外     Benlong Outskirts     奔龍遺跡   Benlong Ruins
```
**Sugeli**
```
蘇格禮       Sugeli                蘇格禮郊外 Sugeli Outskirts
```
**Xuan'en City and the frozen north**
```
宣恩城       Xuan'en City          宣恩城郊外 Xuan'en Outskirts
冰寒森林     Frozen Forest         冰寒大廳   Frozen Hall
```
**Endgame**
```
炎灼石廟     Blazingstone Temple   烈風地窖   Windrift Vault
聖光島       Holy Island           聖光島入口 Holy Island Entry
聖光島大廳   Holy Island Hall      聖光島二樓 Holy Island 2F
聖光島三樓   Holy Island 3F        聖光島四樓 Holy Island 4F
聖光島頂樓   Holy Island Top
```

Note the source spelling drift against the dialogue glossary: 耗劫石地 (maps) vs
浩劫石地 (script), 烈風地窖 vs 裂風地窖, 奔龍遺跡 vs 奔龍遺蹟. All are the same
places.

## Procedure

```
python3 mapnames.py dump  <mapdir> > names.csv
# fill in the `translation` column
python3 mapnames.py apply <mapdir> names.csv
```

`dump` walks every `.dat` and emits filename, raw hex, decoded original and an empty
translation column. `apply` skips blank rows, so the file can be worked through in
passes, and drops a `.bak` beside each file on first touch, **once only**, so
re-running never overwrites a pristine backup with a patched one. `--revert` restores
from `.bak`.

---

# 7. .MSG dialogue

```
[32-byte file header][ record ][ record ] ...
record = 253 bytes = [17-byte header][236-byte text field]
```

95 of 95 `game*.msg` files fit `32 + k*253` exactly. Files run `game1`–`game144` with
gaps. Roughly 1,281 translated lines across ~1,466 records.

The 32-byte file header was found by re-framing an earlier wrong model: offsets 0–31
read `00:133` with exactly one outlier each, and that outlier was always record 0.
Under the corrected model those 32 bytes are the file header, and for records 1+ the
same span is the *previous record's text padding*, hence all zeros. A stray `A6 B3`
(有) at what looked like header bytes 8–9 was stale text left behind when the engine
wrote a shorter string over a longer one.

Record header fields identified so far:

| Byte | Meaning |
|---|---|
| 1 | speaker / portrait ID |
| 15 | dialogue node pointer — this is a tree, not a flat list |
| 4, 6, 8–11, 13 | condition flags / branch triggers |

There is no length field. Roughly 13% of records hold an asset filename
(`MStg85.ANM`, `Map034.DAT`, `Ship.FTC`) rather than dialogue; translating one breaks
a cutscene.

## demo.msg — the outlier

`demo.msg` is the sole file on different geometry. Probed and solved:
`5135 == 32 + 21*243`.

| | `game*.msg` | `demo.msg` |
|---|---|---|
| file header | 32 | **32** |
| record size | 253 | 243 |
| record header | 17 | 10 |
| text field | 236 | 233 |
| records | varies | 21 |

The 32-byte file header is identical and record-header byte 1 is the same speaker-ID
slot (`0x07` here). Same engine, slightly different record dimensions — probably a
script-compiler version difference.

*(This corrects the earlier note that `demo.msg` had a 75-byte header. It does not.)*

Its 21 records are **real playable content**, not throwaway attract text — a child
asking to be let go home, a half-blind old woman asking for help. Worth translating.
`msgtool2` takes `--rec 243 --hdr 10`, but with `--rec`/`--hdr` it falls back to
treating the whole field as prompt, which is safe but not correct if `demo.msg` has
option tables of its own at the shifted offset.

## Rendering geometry

The renderer advances **8 px per byte** and wraps on a fixed **30-byte** line, so a
line is 30 ASCII characters or 15 Chinese, with **no word-boundary logic whatsoever** —
the font test split `breakfas` / `t!` mid-word. Break lines yourself by padding each
one out to the 30-byte boundary.

Two consequences worth knowing before touching the text:

- **Padding costs budget.** Up to 29 bytes a line, ~14 on a typical record, charged
  against the same 199. Text that fits unpadded may not fit padded; the fallback is to
  write it flat and accept a mid-word break.
- **Concatenated lines look like typos.** Where a line ends on a word with no padding
  left over, the next line's first word butts against it in storage:
  `...are black the` + `world over...` reads as `theworld` but draws as two words on
  two lines. Any merged-word check must ignore seams that fall exactly on a 30-byte
  boundary, or it will "fix" them and shift every subsequent break in the record.

**Historical hazard.** An early line-breaking pass padded correctly but ate the space
*after* the first word of each new line, producing `thisdynasty`, `theworld`, `thinka`
and `Ｅsells` in the shipped `.msg` files while the source CSV stayed clean. Symptom:
merged words whose seam is *not* on a 30-byte boundary. `textflow.py check`
distinguishes the two cases.

## The option table — last 36 bytes of every text field

The text field is **not** 236 bytes of text. Its tail is a fixed table that choice
prompts use — shops, inns, yes/no questions, the slave auction:

```
text field +0   ..+199   prompt, NUL-terminated
text field +200 ..+211   option slot 0
text field +212 ..+223   option slot 1
text field +224 ..+235   option slot 2

slot = [10-byte label, Big5, NUL-padded][u16 value, little-endian]
```

`value` is the branch target: a dialogue node number for ordinary choices, or `999` for
the "open shop transaction" action, paired with `0` to exit. It must be carried through
untouched. This is why `離開` and `不要` both work as a bail-out, and why the buy and
sell records look identical apart from one glyph.

Across the shipping script, **84 records carry a table**: 76 with two options, 7 with
three (`game122:0`, `game2:10`, `game28:4`, `game31:58`, `game33:5`, `game75:7`,
`game96:3`) and one with a single forced acknowledgement (`game9:34`). Only **80
distinct labels** fill all 174 slots — 23 of them are `離開` — so they are worth
translating once by label, not per record.

Some labels carry ASCII or fullwidth spaces for centring (`買 了`, `我　沒　有`); match
on the label with spacing stripped.

**Consequence: the prompt has 199 usable bytes, not 236.** Anything longer runs into
slot 0.

**A tool that treats the field as 236 bytes of text and zero-pads on write will
silently erase every option table in the game.** The prompt still renders; the options
simply never appear. This is exactly what happened — it presented as "shops and the
slave auction don't show their choices" — and `optfix.py` exists to repair it.

## The 199-byte ceiling

**Confirmed, not inferred.** A filler record of exactly 199 bytes was written into
`game1.msg:0` and renders correctly in DOSBox, closing the 196–199 band that the
original 195/200 crash bracket left untested. Records at the ceiling ship fine:
`game91:3` is 199 bytes; `game127:2`, `game28:0` and `game9:7` are 198.

This retires three earlier wrong numbers. The 236-byte storage field, the 210-byte
"7 lines × 30" arithmetic, and the empirical 194 (the highest the original script ever
used across 1,466 records) were all approximations of the same struct boundary. The
"8 rendered lines crashes" result was the same overrun measured a different way.

## Where the option row is drawn

Options are **not** blitted at a fixed position. They flow inline in the same 30-byte
stream as the prompt, starting roughly 2 bytes after the prompt's last character, with
about 2 more between labels — call it **13 bytes** for a two-option row. Measured off a
shop screenshot at 16 px per character, so treat it as ±1.

Which line the options land on is therefore decided entirely by where the prompt ends,
and for shop lines that is only known at runtime because `Ｅ` expands to the item name.
A prompt ending at 51 bytes puts the options on line 2; one ending in 60–77 puts them
on line 3. Forcing consistency means padding after `Ｆ` by a fixed N, which is only
possible if

```
(longest item - shortest item) + (price digit spread) <= 17
```

`itemfit.py` reads the item table and computes N, or reports that the spread is too
wide.

## Runtime substitution markers

The fullwidth block at Big5 `0xA2CF`–`0xA2D4` is **control data** inside `.MSG` text,
not text:

| Marker | Big5 | Meaning |
|---|---|---|
| Ａ Ｂ Ｃ Ｄ | A2CF–A2D2 | party member 0–3; opens the name-entry box |
| Ｅ | A2D3 | item name |
| Ｆ | A2D4 | price |

Converting any of them to ASCII while translating breaks name entry or leaves a shop
line with a blank where the item should be. They substitute with **no surrounding
whitespace** — the Chinese source ran `Ｅ只賣Ｆ` with no space needed — so English lines
must supply their own, or you get `Healing Lemonsells for only 10`. `markerfix.py`
finds every marker sitting against a letter or digit; punctuation (`Ａ's`, `(Ｆ)`,
`Ｅ.`) correctly needs no space.

### Drawn width

A marker is 2 stored bytes and draws as whatever it substitutes, so everything after it
on the same line shifts right by an unknown amount at runtime. This is why hand-placed
line breaks go wrong around them.

`Ａ`–`Ｄ` are predictable in the common case, since the defaults live in `game.ini`:

| Marker | Slot | Offset | Big5 | Pinyin | Default | Drawn |
|---|---|---|---|---|---|---|
| Ａ | 0 | 0x0000 | 凡提 | Fántí | Vanti | 5 |
| Ｂ | 1 | 0x009E | 寒依 | Hányī | Hani | 4 |
| Ｃ | 2 | 0x013C | 法諾 | Fǎnuò | Fano | 4 |
| Ｄ | 3 | 0x01DA | 藍奇 | Lánqí | Lanqi | 5 |

Three of the four use characters the glossary already treats as transliteration
syllables (諾 = the standard *no* as in 諾亞/Noah, 藍 = *lan/ran*, 凡 = *Va* as fixed by
凡妮拉/Vanilla), so they belong in the Kanon/Rosa/Sius bucket rather than the Cao
Xiao'an bucket. 寒依 is the one that could plausibly be read as meaning-bearing ("cold"
+ "rely") but reads as a sound. Slot 1 is very likely the ID 09 female companion.

Only Vanti is confirmed on screen; the other three renderings were proposed and may
not have been patched into `game.ini`. `demo.ini` needs the same treatment or the title
demo shows Chinese names. Existing `.SAV` files carry their own copy, so testing needs
a new game.

Lay name-marker lines out against the **drawn** width (`textflow.py --names`) and they
break cleanly for any player who keeps the defaults, degrading to stray double spaces
for one who renames. `Ｅ`/`Ｆ` have no such fallback — an item name can be 19
characters — so nothing after the first `Ｅ`/`Ｆ` on a line should be padded at all.
The practical shop pattern is a fixed first line padded to the boundary and a tail of
at most about 6 bytes:

```
A fine eye, sir. The price:      <- padded to 30
Ｅ - Ｆ                           <- 19 + 3 + 5 = 27 worst case, still one line
```

---

# 8. Hidden systems

## Cheat / debug console — press F1

The keyboard handler reads the last BIOS scancode from a global and compares it against
a short chain; `cmp bx, 0x3B00` (F1) branches to the prompt that draws
"請輸入作弊代碼" (enter cheat code).

Input is passed through `strupr` before `strcmp`, so codes are **case-insensitive**,
but the spaces are part of the string and do matter. The 16 codes live in a pointer
table at file 0x281AC / VA 0x117AC, and a match dispatches through a jump table:

```
RAISE UP      FULL UP       YOKI KEYS     GET MONEY
RESET GAME    SHOW MEMORY   LIFE AGAIN    SAVE DEBUG
REGETOBJ      KILL ON       KILL OFF      HID MONSTER
SHOW MONSTER  SHOW EVEN     SHOW MAP      STRONG
```

`HID MONSTER` / `SHOW MONSTER` are the monster toggle. `KILL ON` / `KILL OFF` are the
one-hit-kill toggle.

Two commands are handled *before* the table lookup and take an argument: the code
compares the first four characters against `JUMP`, then treats the rest of the input as
a map name, appends `.DAT` and loads it — so `JUMP <mapname>` is a warp (maps live in
`.\MAP\` as `Map001.DAT` etc). There is a matching `GET OBJECT` string nearby.

## Monsters are placed, not spawned

**This engine has no random encounters.** Monsters are placed map objects — "persons"
with a type byte ≥ 0x0E at record offset 0x27, loaded from the map data. Forty-two
separate code sites branch on that check. Wandering around will not spawn anything; a
map either has monsters placed on it or it does not.

`SHOW MONSTER` does not mean what it looks like:

```
mov byte [0x3224], 0          ; clear the "monsters hidden" flag
loop over persons on CURRENT map:
    if person[+0x27] >= 0x0E and person[+0x95] == 0x0A:
        person[+0x95] = 0     ; un-hide
```

It only un-hides monsters *already loaded on the map you are standing on*. If the map
has none placed, the loop does nothing and the confirmation message prints anyway. The
flag is read in exactly one place, the map-load path, so it does persist across maps.

## Why New Game never asks for a name

Name entry is **script-driven, not part of the new-game flow**. The routine at
VA 0x13BA0 walks a dialogue string looking for a Big5 character with high byte 0xA2 and
low byte 0xCF–0xD2 — the fullwidth letters Ａ Ｂ Ｃ Ｄ mapping to party members 0–3.

When the message engine hits one it opens the input box. A bitmask global records who
has already been named, so each marker only fires once. Leaving the box empty asks "use
the default name?"; typing something asks "use this new name?". The result is copied
into the 20-byte field at offset 0 of the person record.

So the prompt appears at a specific story beat whose message text contains the marker —
not at New Game. The default name comes from `game.ini`, not `game.exe`. To force a
prompt, drop a fullwidth Ａ into any `.MSG` line.

The name-entry screen has an 英數 (alphanumeric) / 注音 (Zhuyin) toggle; 英數 has been
patched, so Latin input works.

## Saving

Right-click opens the main menu; save lives inside it. (The engine's own confirm dialog
for this is the 0x3FBD4 call site in section 4.)

## Music

The per-area track is selected by the 20-byte field at **0x28** of the map header. It
holds two null-terminated strings — e.g. `CD2\0` and `01.XMI\0`. `CD2` is the CD-DA
(Redbook) track tag and `01.XMI` the MIDI fallback: confirmed because the `cd/` folder
holds `02.ogg` etc. (track 1 being the data track), and there are no other `.XMI` files
in the tree — `music/test.wav` and `music/test.xmi` are placeholder stubs.

**Looping is not a map-data problem.** DOS CD audio does not loop itself: the game
tells MSCDEX (via `int 2Fh`) to play a frame range, polls for "playback finished", and
re-issues the play command. Every in-game seam is that poll-and-restart cycle, and it
is inherently gappy. A perfectly seamless OGG can still hard-cut in game.

Two practical notes from the audio work: the `.cue` mislabels every track as `MP3` when
they are OGG — the correct token is `OGG`, and a wrong type can affect how some builds
compute track length at the loop boundary. And **VLC is not a valid way to test a
loop**: its repeat-one tears down and re-initialises the decoder at EOF, producing a
stutter-and-reseek on a perfectly looping file. Audition a self-concatenated copy
played straight through instead.

`02.ogg` was re-cut to a sample-accurate 40.0 s loop (seam correlation 0.85, waveform
step 0.0001), outro discarded. The remaining 37 tracks have not been processed and each
will have its own designed loop length; a few may be through-composed with no internal
loop at all.

---

# 9. Tools and build order

```
python3 holytool.py    export    <file.grp|vct> [outdir]
python3 holytool.py    import    <file.png> <original> <out>
python3 holytool.py    exportall <gamedir> <outdir>
python3 big5scan.py    <dir|file> [-o report.txt] [-m 4] [--csv strings.csv]
python3 probe.py       <file|dir> [--glob '*.msg']
python3 translate_all.py <game.exe> [-o out.exe] [-n]
python3 exestrings.py  report|apply <game.exe> [-o out.exe]
python3 patch_banner.py <game.exe> [-o out.exe] [-n] [--revert]
python3 patch_menu.py  <game.exe> [-o out.exe]
python3 make_pstat_en.py <gamedir> <out.grp>
python3 findnames.py   scan|dump|patch <dir|file> [offset name]
python3 mapnames.py    dump|apply <mapdir> [names.csv]
python3 msgtool2.py    verify|analyse|export|import <mapdir> ...
python3 optfix.py      scan|restore|export|import|labels <mapdir> ...
python3 textflow.py    check|unmerge|reflow <csv> [--col C] [--names ...]
python3 markerfix.py   report|fix <csv>
python3 itemfit.py     <game.exe|names.csv>
python3 build_english.py --game <pristine> --data <transdata> --out <build>
python3 mkpatch.py     build|apply ...
```

**Which tools verify, and which do not.** `translate_all.py` and `patch_banner.py`
check original bytes and refuse to run on an already-patched file — they need a
pristine `game.exe`. `exestrings.py` and `msgtool2.py import` do *not* verify prior
contents and are idempotent, so they can be re-run over a patched tree freely. This
distinction decides build order.

`msgtool2.py import` writes and pads **only bytes 0–199** of the text field and asserts
the option table is unchanged afterwards.

`optfix.py` repairs `.msg` option tables the old `msgtool2` overwrote.
`restore --pristine <dir>` copies the tables back from a clean tree without disturbing
translated prompts; `labels <dir> option_labels.csv` writes one English label into every
slot that uses it.

`textflow.py` handles line breaking. `reflow` discards existing padding and re-wraps at
30 bytes, marker-aware; `check` reports merged words, ignoring reflow seams; `unmerge`
repairs them using `wordsegment` plus a real-frequency guard (`wordfreq`) so closed
compounds like `cannot` and glossary names like `Mengjun` survive.

## Dialogue build order

```
translated_updated.csv          <- the master. Edit here. Natural sentences.
  textflow.py unmerge           <- only needed on text recovered from disk
  markerfix.py fix              <- spaces around Ａ-Ｆ
  textflow.py reflow            <- line breaks and padding
translated_final.csv            <- build artifact. Do not hand-edit.
  msgtool2.py import --max-bytes 199
```

`translated_final.csv` stores each record as its lines concatenated, so it is not
readable prose and editing a byte in it shifts every later break in that record. Option
labels are untouched by import, so `optfix.py labels` does not need re-running unless
the tree is rebuilt from pristine.

## Full-tree build order

Running these in the wrong order silently corrupts things:

1. **`game.exe` strings first, on a fresh copy** — `translate_all.py` refuses to run on
   an already-patched exe, so it must see pristine bytes. Build into a throwaway copy
   so this is guaranteed every time.
2. **`exestrings.py`** for the dialog labels, combat log and cheat feedback that were
   never in `strings_worksheet.csv`. (Better: add those rows to the worksheet and let
   step 1 do it, so the build has one provenance.)
3. **`patch_banner.py`** — code segment, far from any string field, so order does not
   strictly matter, but keep it after the stricter verifier.
4. **`patch_menu.py`** — title-menu alignment on top of the translated strings. Check
   whether it also demands pristine bytes; if so, reconcile with step 1.
5. **Status panel → `PStat.GRP`, not a new name.** The exe only ever loads
   `PStat.GRP`, so the build must overwrite the shipping Chinese panel or the English
   art never shows.
6. **Map names**, then delete the `.bak` files `mapnames.py` leaves behind so they do
   not enter the diff.
7. **Dialogue** via the pipeline above.

## Distribution

Do not distribute a translated game — that ships the copyrighted original. Distribute a
**diff** applied to the user's own pristine copy. No stock patch format does validated
whole-directory patching in one artifact (`xdelta3`, `bps`, `bsdiff` are all
one-source-to-one-target), so the shape is: `build_english.py` reproduces the English
tree from pristine, then `mkpatch.py` bundles a per-file `xdelta3` diff plus a SHA-256
of each expected source into one `.hip`. Only diffs and genuinely translator-authored
files travel; untouched game files never do. A mismatched dump, wrong region or
already-patched folder fails before a single byte is written.

---

# 10. Translation brief

*(This section is the working prompt for translating script chunks. Paste it verbatim
when starting a new translation session.)*

I am fan-translating 聖光島 (Holy Island), a 1997 Taiwanese DOS role-playing game, from
Traditional Chinese into English. I will paste the script in numbered chunks. Please
translate each chunk and return it in exactly the format described below.

## TONE
- The story is serious and often bleak: poverty, tyranny, grief, abuse. Translate
  plainly and with feeling. Do not sanitise it.
- Do not use mock-archaic fantasy diction (no "thee", "thou", "'tis").
- 1997 Taiwanese RPG dialogue is direct and exclamatory, but Chinese uses ！ far more
  than English uses "!". Convert most of them to full stops and keep exclamation marks
  only where there is real force.
- Write natural modern English. Avoid translationese.
- Chengyu and folk proverbs are common. Render them as plain English sayings with the
  same force; only translate the image literally when the speaker is playing with it
  (for example when the following line answers it).
- Some scenes are crude, sexual or deliberately vulgar (the brothel in game72, the
  feuding artists in game98/99). Keep the crudeness; do not clean it up or make it coy.

## HARD RULES
- ASCII only. No curly quotes, em dashes, ellipsis characters, or accented letters.
  Use `'` and `"` and `...` and `-`.
- EXCEPTION: the full-width letters Ａ Ｂ Ｃ Ｄ Ｅ Ｆ are runtime placeholders. Copy them
  through EXACTLY as they appear. Never translate, romanise, or delete them.
- The character ‧ is used as an ellipsis. Render it as `...` (never stacked).
- Each translation must be at most 210 characters. Shorter is better. Lines marked
  (TIGHT) are close to the limit — be concise there.
- Use the glossary below for every proper noun, without exception.
- **Item names must match the inventory exactly.** Dialogue tells the player what to
  look for in the menu; a divergence is a soft-lock in practice. The glossary's item
  renderings are already cut to the 19-byte item-table field, so use them as written
  even where a longer phrase would read better.
- Translate only. No commentary, no notes, no merging or splitting of lines.
- Placeholder or junk strings that are already ASCII (for example a run of `x`
  characters, or a run of ？ marks) are copied through unchanged.
- Some records are one half of a sentence that continues in the next record. Translate
  each record as its own line and let the sentence run across the break; do not merge
  them or add a false full stop.

## OUTPUT FORMAT
One line per input line, in the same order, exactly like this:

```
[game1.msg:0] Wake up! Come and eat breakfast.
[game1.msg:1] We have been eating food like this for so long.
```

Keep the `[file:record]` tag byte-for-byte identical to the input. No blank lines
between entries, and do not wrap the output in a code block.

## SPEAKERS
Each line is tagged with a speaker ID. The same ID is the same character throughout, so
keep voice and gender consistent for each. ID 01 is the player character, 65 is his
mother, 00 is generic NPCs and narration. ID 09 is a female companion who travels with
the party.

Note: IDs 65, 66, 67 and similar are reused for different local characters from map to
map (65 is the mother early on, but Kanon, Lian, Ed, Ali and others later). Take the
speaker from context within each file, and keep it consistent inside that file.

Note: several late files (game66, game68) are duplicates of an earlier file with every
speaker flattened to 00. Translate them identically to the original wherever the
Chinese matches.

## GARBLED TEXT
Some records contain corrupted byte runs that do not decode to real Chinese (for
example game103.msg:10, game2.msg:16, game60.msg:12). Render these as `%$#@*&` rather
than attempting a translation.

---

## GLOSSARY (use these renderings exactly)

### PLACES
```
聖光島 = Holy Island   [Official English title. Literally 'Isle of Holy Light' -- use the official form.]
泰吉拉 = Tajira   [Northern village; destroyed mid-game. Emotionally important -- the hero's childhood memories.]
孟郡城 = Mengjun City   [Capital of the Moro Dynasty. Paired with Tajira on a signpost: 'North - Tajira, South - Mengjun City'.]
德佳古鎮 / 德佳古村 = Dejia Old Town   [Where the mother goes looking for work in the opening scene. Source varies between 鎮 and 村; use Dejia Old Town for both, and 'Dejia' where the source shortens it.]
嘉露城 = Jialu City   [Entertainment city, famous for its opera house.]
宣恩城 = Xuan'en City   [City where children have been going missing.]
哈曼奴 = Hamanu   [Ivory-trading region. Note: a PLACE, not a person -- 'after my husband went to Hamanu'.]
蘇格禮 = Sugeli   [Town of painters and wood carvers; where the carver Ali works.]
捷里沙 = Jielisha   [Shipbuilding town; home of the shipwright Das.]
石斑港 = Shiban Harbor   [Where the ship is moored.]
殘慟谷 = the Vale of Grief   [Literally 'valley of lingering sorrow'. Suffers a landslide from over-logging.]
怖懼山 = Mount Dread   [Also 怖懼山洞 = Dread Cavern. The fortune teller's altar is inside it.]
西籬溫泉 = the Xili Hot Spring   [West of the hero's village. The female companion's house is north of it.]
舞韻歌劇院 = the Rhapsody Opera House   [Literally 'dance-rhythm opera house'. Tickets 5000; under-18s barred.]
巫士廢墟 = the Sorcerers' Ruins   [Where the Sacred Sutra was taken.]
炎灼石廟 = the Blazing Stone Temple
石碑幽徑 = the Stele Path
寂寞芳心湖 = Lonely Hearts Lake   [Named for a rich girl who starved gazing at her reflection.]
浩劫石地 = the Ravaged Stonelands   [Site of an unnatural tremor; a lead early in the party's search.]
黑煞沼澤 = the Black Curse Marsh   [Elephant habitat near Hamanu; where gusha grass is said to grow.]
心意旅店 = the Goodwill Inn   [Kanon's inn in Hamanu. Literally 'inn of one's own intention' -- guests pay what they wish. Guests vanish there.]
碎冥墓穴 = the Shattered Gloom Crypt   [Nobles' graveyard outside Dejia. Entered with the staff of rites; the Envoy of Pestilence lairs there.]
針織橋 = the Needlework Bridge   [Outside Dejia; head north from it to the crypt entrance.]
裂風地窖 = the Windrift Vault   [Where the Six-Armed Buddha of Jiayi waits. Entered via the Stele of the Fallen Dynasty.]
奔龍遺蹟 = the Benlong Ruins   [Surface site above the Benlong caverns; Prince Sius blasted the mountain here.]
冰寒大廳 = the Frozen Hall   [Requires a warming bracelet to survive.]
西城食堂 = the west city canteen   [Where Miss Lily lost her vanity case. Not a proper noun.]
```

### PEOPLE
```
摩羅王朝 = the Moro Dynasty   [The ruling regime the plot aims to overthrow.]
摩羅王 = King Moro   [Tyrant who purged the kingdom's magicians by poisoning them at a banquet. Revealed to be the hero's father.]
帕伐摩羅 = Pafa Moro   [The dynasty's founder, who seized power by plot and issued the Great Charter of Rank and Order.]
修斯王子 / 休斯王子 = Prince Sius   [Villainous prince; destroyed the Benlong by blasting their mountain. Both spellings appear; use Sius for each.]
洛莎 = Rosa   [The hero's mother, named by the king. Dies of the plague in Dejia.]
卡農 = Kanon   [Major landowner in Hamanu, and the ivory buyer. Spoken of warmly by villagers, but revealed to be a blood-drinker who preyed on outsiders at his inn, and later killed. 卡農一世 = Kanon the First, on a gravestone in the crypt.]
梅亞 = Meia   [The Hamanu mayor's daughter. Disabled, mourns the slaughtered elephants, suspects Kanon. May hang herself.]
曼德拉 = Mandela   [Former scholar, now mad; lives on the east side of the city.]
傷心女神 = the Goddess of Sorrow   [Subject of a statue and its inscribed poem.]
阿蓮 = Lian   [Woman in an abusive marriage; her husband sold their daughter to a brothel. Her husband is a fortune teller with the power to petrify, drawn from a shrine (祭堂).]
艾德 = Ed   [Village chief of Dejia Old Town, died in the plague. His ghost wants the spirit-saving talisman; his safe key is inside his own corpse. Address him as 'Chief Ed' where 村長 is attached.]
達斯 = Das   [Shipwright of Jielisha, taken by a fox spirit. His father begs the party to find him; his return earns the party a ship.]
小梅 = Xiaomei   [Girl who drowned herself; her poor sweetheart writes her a lament and follows her.]
珠珠 = Zhuzhu   [Name called out by a customer in the brothel.]
莉莉小姐 = Miss Lily   [化粧師莉莉 = Lily the makeup artist; she loses her vanity case.]
阿里 = Ali   [Carver in Sugeli who makes the withering clarinet and sells warming bracelets.]
曹小安 = Cao Xiao'an   [Self-styled master of realism in Sugeli; feuds with Zhuang Xiaojun across the street.]
莊小俊 = Zhuang Xiaojun   [Self-styled leader of abstraction in Sugeli; the other half of the same feud. The two files are mirror images -- keep the parallel wording.]
阿舉師 = Master Aju   /  阿起師 = Master Aqi   [Throwaway names in the artists' brush-offs; keep them distinct.]
柯特 = Kurt   [Rock musician cameo.]
癟三雄 = Xiong the Bum   [Fallen gang boss in Jialu City. 癟三 = a bum/lowlife.]
極惡大鼎 / 林大鼎 = Dading the Vicious / Lin Dading   [Boss of the Black Turtle Gang, Jialu City. Use the full 'Lin Dading' only where the source gives 林大鼎.]
黑龜幫 = the Black Turtle Gang   [Dading the Vicious's gang in Jialu City.]
凡妮拉 = Vanilla   [Name in a lovestruck NPC's line.]
六手甲乙佛 = the Six-Armed Buddha of Jiayi   [Guide of Holy Island. Receives the six relics. 六手 = six-handed/armed.]
痛苦使者 = the Envoy of Pain   [Elder sworn brother of the Envoy of Pestilence; avenges him.]
瘟疫使者 = the Envoy of Pestilence   [Spread the plague that killed Dejia Old Town, to harvest slaves and a private army. Keep distinct from the Envoy of Pain.]
五骨大將 = the Five Bone Generals   [The Envoy of Pestilence's minions.]
奔龍族 = the Benlong   [Subterranean race, the world's first inhabitants; wiped out by Prince Sius. 'the Benlong people' where a noun is needed.]
狐狸精 = fox spirit   [The creature holding Das. Also an insult for a seductress -- keep the pun where the source plays on it.]
終極歷程的不朽先知 = the undying prophet out of the final journey   [How the figure at the stele names himself.]
高潮雙姝 = the Twin Sisters of Ecstasy
裸體姐妹花 = the naked sisters
青春小鳥 = the bird of youth
村長 = village chief
鎮長 = mayor   [Head of a town rather than a village -- keep distinct from 村長.]
客倌 = sir / madam   [Innkeeper's form of address to a customer. Not a name.]
```

### PARTY DEFAULT NAMES
```
凡提 = Vanti   [Ａ, party slot 0. The player character; renameable.]
寒依 = Hani    [Ｂ, party slot 1. Very likely the ID 09 female companion.]
法諾 = Fano    [Ｃ, party slot 2.]
藍奇 = Lanqi   [Ｄ, party slot 3.]
```

### THE SIX RELICS
Canonical names — **identical in dialogue and in the item table.** All fit the 19-byte
item-name field. See `ITEM_NAMES.md` for the reconciliation and the bytes.
```
蓮花若木 / 蓮花岩木 = the Lotus Ruo-Tree   [Relic 1 of 6. 若木 is the mythical sun-tree of Chinese myth. Source drifts to 岩木; same object.]
雲雷風鼓 = the Cloud-Thunder Drum   [Relic 2 of 6.]
斑瀾文簡 = the Resplendent Slips   [Relic 3 of 6. 文簡 = inscribed bamboo writing strips. 'Resplendent Bamboo Slips' is 24 bytes and does not fit the item field.]
玄白赤鼎 = the Tricolor Cauldron   [Relic 4 of 6. 鼎 is a ritual tripod cauldron; 玄白赤 = black/white/crimson. Literal rendering is 25 bytes.]
泊天神俑 / 泊天神蛹 = the Heavenbound Effigy   [Relic 5 of 6. 神俑 = divine tomb figure. The 蛹 spelling is a typo in the source -- same object.]
未見箴圖 = the Unseen Admonition   [Relic 6 of 6. Held by the spirit in the painting at the Rhapsody Opera House. Dropping 'Scroll' buys the fit.]
```

**Relic-adjacent items** (quest keys, not relics themselves):
```
魂應鼓 = the Soul Echo Drum   [Wakes the painting at the Rhapsody Opera House so it will speak. Keep distinct from the Cloud-Thunder Drum.]
大眼童屍 = the Big-Eyed Corpse   [Traded for the Heavenbound Effigy.]
鏟子 = shovel   [Digs up the bedroom key.]
黑皮書 = the Black Book   [Opens the Cave of the God.]
```

### THE FOUR HOLY ITEMS
These four spell out 真命天子 'the true-fated son of heaven' from their first
characters. The acrostic is load-bearing — `game8:12` reads *"Take the first word of
each: True, Life, Heaven, Child."* — so the **first word of each English name is fixed**
and the shipped inventory renderings `Sky Jade` and `Small Candle` are wrong.
```
真絹 = True Silk
命石 = Life Stone
天玉 = Heavenly Jade
子燭 / 子鐲 = the Child Candle   [Source drifts to 子鐲 (bracelet). Verify against the item table before committing the noun; the acrostic holds either way.]
```

### OTHER ITEMS
```
釋聖經 = the Sacred Sutra   [Stolen by sorcerers. 釋 marks it as Buddhist scripture.]
克勞蒂香水 = Claudie perfume
絢麗面具 = the Dazzling Mask
烈燄服 = the Blazing Flame Robe
牛馬角 = the Ox-Horse Horn
潘尼羅亞茶 = Panneroia tea
約書亞樹枝 = a Joshua tree branch
枯萎豎笛 = the withering clarinet
火種 = fire-starter
野餐盒 = picnic box
獵魂釘 = soul-hunting nail   [Driven into a victim; pulling it out summons the Envoy of Pain.]
枯骨法器 = withered-bone talisman   [Carried by the pale ascetic monk; the sign his brother searches for.]
粧箱 / 化粧箱 = vanity case   [Dressing/cosmetics box.]
水仙花 = narcissus   [NOT a proper noun -- an ordinary flower. Also 枯萎水仙花 = withered narcissus.]
陰影銅環 = the Shadow Bronze Ring   [Cursed ring; slipping it onto a sleeper's wrist kills him. Wanted by both Jialu City gang bosses.]
菇沙草 = gusha grass   [Legendary plant of the Black Curse Marsh; offered to the dead so they may be reborn human. Lowercase, not a proper noun.]
拯救亡靈符 = the Soul Rescue Charm   [Frees a bound spirit; several ghosts beg for one, and the painting trades it for the Unseen Admonition. Was 'the spirit-saving talisman' in dialogue -- 24 bytes, does not fit the item field. Keep distinct from 枯骨法器, the withered-bone talisman.]
祭文之杖 = the staff of rites   [Found in the village chief's house; set into the stone base to open the Shattered Gloom Crypt.]
解脫橄欖 = the olive of release   [Lets a man cursed to neither live nor die finally die.]
銀匕首 = silver dagger   [In the crypt; cures the plague by cutting the poison out.]
鎮壓符 = the sealing charm   [Pinned to the Stele of the Fallen Dynasty. Tearing it off releases the dark power.]
亡朝碑 = the Stele of the Fallen Dynasty   [The great boulder; also the key to the Windrift Vault.]
沁冰刻刀 = the Chillfrost Carving Knife   [Legendary blade sought by the armless carver.]
九天乾坤 = the Nine Heavens Cosmos   [His reward for it; useful in the Benlong Ruins. A guess -- the item's function is never described.]
溫熱手鐲 = warming bracelet   [Ten thousand gold each; prevents frostbite in the Frozen Hall.]
左花扇 / 右花扇 = the left flower fan / the right flower fan   [A pair, found separately.]
變形藥水 = transformation potion
哭牆 = the wall of tears   [Built by the Envoy of Pestilence out of tears taken from the dying.]
水晶球 = crystal ball   [The Benlong shaman's; shows what has happened.]
單旋律聖歌 = Monody   [Title of the chant on the scroll in the dead tree.]
紫衣 = purple robe
朱冠 = red crest
祭堂 = shrine   [The source of the fortune teller's petrifying power; Lian asks the party to destroy it.]
KEYS: 鐵鑰匙 = iron key, 金銀鑰匙 = gold and silver key, 古銅鑰匙 = old bronze key,
      臥房鑰匙 = bedroom key (dug up with the shovel; opens the room holding the
      Resplendent Slips), 保險箱鑰匙 = safe key.
```

### REAL-WORLD CAMEOS
Sugeli's music quiz name-checks 1990s bands. Use the real English names, not romanised
Chinese.
```
超脫合唱團 = Nirvana
小紅莓 = The Cranberries
麥克傑克森 = Michael Jackson
製作小組 = the development team   [Fourth-wall joke in Mandela's dialogue.]
```

### MISCELLANEOUS
```
階級秩序大憲章 / 階級制序大憲章 = the Great Charter of Rank and Order   [Both spellings appear; use this rendering for each.]
神 = god   [Lowercase in the cult's dialogue.]
使徒 = apostle
圓 = gold   [Opera tickets are 五千圓 = 5000 gold. 兩萬圓 = twenty thousand gold. 一萬五千圓 = fifteen thousand gold.]
石化 = petrification / turn to stone
黑暗力量 = the dark power   [Released when the hero tears the sealing charm off the stele. Lowercase 'dark power', with 'the'.]
是否要休息？ = Rest here?   [Recurring menu prompt. Keep it short; 是否要... prompts are all UI questions, not dialogue.]
```

---

# 11. Still open

## Gates on a public release
- **`demo.msg` has never been touched.** Its 21 records are real content. Its option
  tables, if any, sit at a different offset because of the 243-byte stride, and
  `msgtool2` falls back to treating the whole field as prompt when `--rec`/`--hdr` are
  used — safe, but not correct.
- **The ending / credits has never been located, and a full playthrough reached no
  ending or credits at all.** That is now a gameplay observation, not just a file-search
  failure. The narrative finale is almost certainly already in the 95-file `.msg` export
  (grep the script CSV for 六手甲乙佛, 真命天子, 摩羅王 to confirm). What is *not*
  covered is anything delivered outside the dialogue engine: a closing crawl through the
  demo/attract subsystem (`demo01`–`demo07.dat`, or a sibling `end.dat`/`end.msg`), or a
  baked credits / "The End" card in a `.grp`/`.vct` needing pixel repainting. No
  "ending" file was ever named in any file listing, which is itself a clue. A third
  possibility is now live: the release may simply not have one, or the final node may be
  gated behind a flag the playthrough never set.
- **`MAP035.DAT` hard-locks under DOSBox.** Empty mountain path, no persons, no input.
  PCem runs the identical tree correctly, so this is emulation-dependent and not a
  translation regression on its face — but it has not been reproduced against a pristine
  Chinese tree, which is the first thing to do. See `PLAYTEST.md`.
- **`game.ini` / `demo.ini` party names.** Whether Hani / Fano / Lanqi were ever
  actually patched in is unconfirmed; `textflow.py --names` assumes them. `demo.ini`
  needs the same treatment or the title demo shows Chinese names.

## Only sampled, never swept
- **Map names beyond maps 2 and 2b.** The "do not run past 0x4F" budget is assumed, not
  proven. Dump every `.dat` and confirm no shipping name overruns before committing to
  the field size; if any does, the fields are longer than they look and the budget can
  be revised upward.
- **Baked text in map tilesheets across the full set.** Only `map002.grp` /
  `map002b.grp` were confirmed text-free. Others may have signposts or shop signs
  painted into the tile art — for instance the "North – Tajira, South – Mengjun City"
  signpost, *if* that is artwork rather than a `.msg` line.
- **`gameobj.dat`** was flagged early as a possible home for names, then superseded when
  items and monsters turned up in the exe, but never actually dumped and cleared. One
  `big5scan` run rules it out.

## Cosmetic / quality
- Title-menu alignment is still unverified in DOSBox and is the most likely thing to
  need a nudge. Now that the engine is confirmed to *centre* rather than draw at fixed
  X, `patch_menu.py`'s leading-space workaround may be unnecessary — or actively wrong.
- `Retype` on the name-entry cancel is a guess at what the original `More` meant.
- The combat log is terse (`%s -> %s: %s`) because 15 characters will not hold anything
  better with args arriving actor, target, item. Relocating the string into object 1's
  padding would fix this.
- Six records are too long to pad and are written flat, so the engine may break a word
  mid-line in them. Trimming a few bytes each would fix it.
- The 13-byte option-row width is measured off a screenshot, not disassembled.
- Nine records carry `Ａ`–`Ｄ`. Four could put the marker last (`game1:14`, `game116:7`,
  `game58:14`; `game31:22` already does), which would make them exact for any
  player-chosen name rather than only the defaults.
- Several labels are squeezed by tiny fields: 快/中/慢 (fast/medium/slow) get 1–2 chars,
  技 gets 2, and the four element names get 3. Real words there need the strings
  relocated into object 1's 1645 bytes of page padding and their fixup records
  repointed.
- `make_pstat_en.py`'s erase window is ~3px short at the bottom; stray bevel pixels
  survive on rows 1 and 2.
- Item names were translated fairly literally. Weapon and armour lines are formulaic
  (材質 + 類型), so they read stiff; `strings_worksheet.csv` is the place to punch them
  up. 裸女一/二 are rendered as Succubus I/II rather than literally.
- **Main-quest item names diverge between dialogue and inventory** for 14 items. The
  canonical set is decided (`ITEM_NAMES.md` / `data/item_names.csv`) but not yet applied
  to either side. Two source-glyph questions gate it: 蓮花**岩**木 vs 若木, and
  子**鐲** (bracelet) vs 子燭 (candle) — if the item table really says 鐲, the object is
  a bracelet and "Small Candle" is the shipped mistranslation rather than the reverse.
- 37 of 38 CD audio tracks still have their un-looped outros.

## Decisions to make rather than problems to solve
- **The `voice/` folder.** The game is partly voice-acted in Chinese. The audio cannot
  be translated, so on-screen English will now diverge from the spoken lines. Worth a
  conscious decision rather than a surprise.
- Confirm an English player is not dropped into 注音 by default on the name-entry
  screen.
- Check the gold/money HUD counter is not drawing a baked 圓 glyph, and that combat
  result strings (miss / critical / gained N exp) are all inside the 57-entry table.
