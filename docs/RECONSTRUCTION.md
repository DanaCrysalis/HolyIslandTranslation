# Reconstruction findings

Everything below came from byte-diffing the pristine and shipped files. These are
observations, not inferences, except where marked.

---

## 1. `MAP035.DAT` hard lock — header settled, cause identified, mechanism inferred

This section was wrong twice before it was right. Both wrong versions are recorded here
because both were plausible and will otherwise be rediscovered.

### The header

| Offset | Width | Field |
|---|---|---|
| 0x00 | 20 | tile sheet |
| 0x14 | 20 | SFX |
| 0x28 | 20 | audio set |
| 0x3C | 20 | area name |
| 0x50 | 20 | **linked map** |
| 0x64 | — | 15-byte record entries begin |

**What settles it:** scanning all 159 files, the byte at 0x50 is `0x4D` (`M`) in exactly
three — map006, map031, map032. That is only possible if 0x50 is the first character of
the name.

*Wrong reading #1* took 0x50 as a fifth name field and called the NUL corruption in all
14 files that showed it — which was right about the offset but wrong about the
significance, and would have written `M` into files where it does nothing.
*Wrong reading #2* over-corrected: a 1-byte flag at 0x50 and a 19-byte name at 0x51.
That reading lands the record table at 0x64 too, which is why it looked convincing. It is
a coincidence.

### The damage

15 files have that first byte zeroed, so the engine reads an empty filename. Whether it
matters depends entirely on whether the intended target exists:

| | files | effect of restoring `M` |
|---|---|---|
| target absent | 11 (`MAP005B`, `MAP002B`, `MAP003B`) | **none** — empty name and missing file fail identically |
| target present | **map035, map035a, map036** | creates a real link where there is now none |

That second row is the entire crash cluster, and nothing else in 159 files shares the
property. As a correlation from static data this is about as tight as it gets.

### Two theories killed along the way

- **Link cycles are not fatal.** map031 and map032 name each other, both intact, both
  targets present — an intact mutual link that works. This was the previous prime suspect.
- **A dangling link is not fatal.** Eleven maps point at files that are not on disk and
  all eleven work.

### Confidence, stated honestly

That the damage is real and that the map035 cluster is the only place it can matter:
**high**, and directly evidenced.

*Why* an absent link hangs, when eleven other maps survive having no usable link:
**inferred, not established.** The likely explanation is that the transition is only
reachable in the map035 cluster — "Back to Hamanu, fast." triggers it, and the equivalent
edge in map001 is never crossed — but that has not been demonstrated. It is also possible
the header is fine and the real fault is in the 15-byte record table at 0x64, which is
where "no characters present" would point.

**Fix and test:** `maplinks.py --fix --apply` restores the byte on those three files only,
drops a `.bak`, and refuses the 11 no-ops unless given `--all`. Then warp to map035 in
DOSBox. If it loads, done. If it still hangs, the header is exonerated and the record
table is next — which needs a working map's `.dat` alongside map035's to compare.

## 2. There is no `patch_menu.py`, and there never was

A full byte diff of the two executables shows **exactly one code change in the entire
image**: `0x28FB1`, the immediate of the banner `imul`, `0x0C` → `0x10`. Everything else
lies in the data object.

The title menu is aligned by **leading spaces inside its strings** — `'  EXIT'`,
`'  AUDIO'` — which travel in the string table like any other text.

This has a sharp practical edge: **never `.strip()` the english column.** A spreadsheet
that helpfully trims whitespace silently destroys the menu alignment. The reconstructed
`translate_all.py` had this exact bug during development and it cost two rounds of
diffing to notice, which is why the docstring says so twice.

The missing-tool count drops from four to zero.

---

## 3. `strings_worksheet.csv` — reconstructed, 436 rows

| Kind | Count | Base | Stride | Field |
|---|---|---|---|---|
| `ui` | 63 | — | — | distance to the next LE fixup target |
| `item` | 316 | `0x08CD68` | `0x54` | 20 bytes (19 usable) |
| `spell` | 57 | `0x093768` | `0x40` | 20 bytes (19 usable) |

Both strides were confirmed empirically rather than assumed: stride `0x54` decodes 316/316
item slots as ASCII in the shipped exe, and no other candidate is close (`0x50` gives
58/316). Spell stride `0x40` gives 57/60.

**Coverage is total.** Every differing byte between the two executables is accounted for
by these 436 rows plus the single banner byte. Nothing is unexplained.

The `ui` field sizes come from the LE relocation fixup table, so they are true field
boundaries: the set of obj2 fixup targets is the complete set of string starts, and
anything between one target and the next is linker padding nothing can reach.

---

## 4. `translate_all.py` — reconstructed and round-trip verified

Applying the worksheet to the pristine exe reproduces the shipped build to within **19
bytes**, every one of which sits past a NUL terminator and before the next fixup target —
provably unreachable linker alignment. The only other difference is the banner byte, which
is `patch_banner.py`'s job.

The original patcher was inconsistent about how far it padded. The reconstruction zeroes
the full field by default, which is cleaner and matches what `exestrings.py` documents;
`--preserve-tail` gets closer to the shipped bytes if you want a low-noise diff against
the existing BUILD. Neither is detectable by the game.

It verifies every row's Chinese source against what is on disk, so it refuses an
already-patched exe — confirmed, it rejects all 436 rows when re-run on the output.

---

## 5. `make_pstat_en.py` — reconstructed, byte-identical output

`PStat.GRP` is 196×314, one cel, flag 0, `7 + 196*314 = 61551` bytes exactly.

The English lettering is stored as a pixel delta in `data/pstat_en.bin`: zlib over
`[u32 offset][u16 length][length bytes]`, 516 runs, 4453 changed pixels, confined to rows
38–272. Applying it to the pristine panel reproduces the shipped panel **byte for byte**.
SHA-256 of both source and result is checked, so a double application or a wrong source
file fails loudly.

Only translator-drawn pixels are in the delta — the untouched original art is not in it.

---

## 6. The GRP header's seventh byte is a format flag, not padding

This is what made these files look inconsistent.

| Flag | Layout |
|---|---|
| 0 | raw: `7 + count*w*h` bytes of 8-bit palette indices |
| 2 | 768-byte palette at +7, then a body **not yet decoded** |

`map035.grp` is 16×16, count 317, flag 2, 147463 bytes — and `7 + 317*16*16 = 81159`, so
`count` is not a plain cel count in this variant. `147463 - 7 = 147456`, which is exactly
`576 * 256`, hinting at 576 tiles somewhere, but that does not reconcile with 317 and I am
not going to guess. **Unsolved and reported as such.**

It does not block anything: the translation repaints only `PStat.GRP`, which is flag 0.

---

## 7. `.VCT` — solved

```
[u16 width][u16 height][u16 count][u8 flag]        7-byte header
count * [u32 offset][u32 size]                     cel directory
per cel:  [u16 run_count]
          run_count * [u16 x][u16 y][u16 len][len bytes]
```

Each run is a horizontal span of palette indices at (x, y); anything not covered is
transparent. Verified on `menu01.vct`: 16×16, 8 cels, directory offsets chain from `0x47`
to the 795-byte file end with no slack, and cel 0's declared 55-byte size matches its 5
runs exactly (`2 + 5*6 + 23 = 55`).

`holytool.py` exports both `.vct` and flag-0 `.grp`. **Import is deliberately not
implemented** — writing back a format that is only partly understood is a good way to
corrupt art silently, and nothing in the translation needs it.

---

## 8. The ending exists: `animate/holyend.ftc`

From the file listing:

```
animate/holyend.ftc      the ending
animate/holylose.ftc     the losing ending
animate/over.ftc         game over
animate/stage00..05.ftc  chapter transitions
animate/title01,02.ftc   title sequence
game/map/ship.ftc        the asset cue seen in .msg records
```

`.FTC` is the cutscene container, which the `.msg` asset cues already pointed at
(`Ship.FTC`). Thirteen of them. So the finale is not missing from the files — the
playthrough did not reach it, or it plays without text.

This closes the "never located" half of the open item and reframes the other half: the
question is now the trigger, or whether `holyend.ftc` carries text at all.

Also in the listing, and previously unknown:

- **`make/big5.img` + `make/big5.tab`** — the Big5 font, and `make/ascii.emg`. This is
  where the 16×24 Latin block lives, and it is why the banner patch was a width change
  rather than a font change.
- **`cd/02.ogg`–`39.ogg`** — 38 CD audio tracks, already as OGG.
- **`game/voice/`** — a voice directory, never examined.
- `phonetic.tab`, `title.lig`, `role1.anv`, `ice.piv`, `sun00.mov` — unexamined formats.

---

## 9. What is still open

- Does restoring the clobbered byte on map035/035a/036 clear the DOSBox lock? Untested,
  and it is the single most valuable thing to try next.
- Why does an absent link hang map035 when 11 other maps survive the same damage?
- What is in the 15-byte record table at 0x64, and does map035's differ from a working
  map's? "No characters present" points here if the header fix does not help.
- One file reports 0xF0 at 0x50 and gameobj.dat is not a map -- both are unexplained and
  neither is on the critical path.
- The flag-2 GRP body layout.
- `demo.msg` (21 records, 243-byte stride) and `demo01`–`demo07.dat`, deferred by
  agreement.
- Whether `holyend.ftc` contains translatable text.
