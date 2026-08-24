# demo.msg and the demo maps

## demo.msg is the prologue, and it is real content

21 records, a complete scene: a boy is strung up in a tree for throwing a stone
at Prince Sius; the hero cuts him down; a guard sees it; an old woman hides the
hero and sends him out an upstairs window; the guards find the open window and
kill her for lying. The hero closes on *"What kind of dynasty is this...? I will
bring it down."*

This is not detached filler. `game7.msg` picks up moments later — the hero finds
the old woman dying, and `game4.msg` has villagers recounting the same events.
Leaving demo.msg in Chinese leaves the game's opening in Chinese.

All 21 are translated in `data/demo_script.csv` and applied in `build/demo.msg`.
Established glossary was followed: **Prince Sius** (not Xiu), **grandmother**
for 老婆婆, **Mister** for 大哥哥.

## The format — solved, and NOT the main .msg layout

`msgtool2.py` will corrupt this file. Use `demotool.py`.

```
32-byte file header
21 records of 243 bytes:
    [10-byte record header]      byte 1 is the speaker id
    [233-byte text field]
        bytes   0..199   prompt text, NUL-terminated   (199 usable)
        bytes 200..232   3 option slots of 11 bytes
```

`32 + 21*243 == 5135` exactly. Compare the main files: 253-byte records of
`[17][236]`, option table also at field offset 200 but in 12-byte slots. **Both
formats reserve the same 200-byte prompt region** — only the header and the slot
width differ.

Speaker ids: 1 hero, 2 and 3 hero narration, 7 boy, 8 guard, 9 old woman.

### The option slots hold developer placeholders

Every one of the 21 records has the identical labels `test`, `test2`, `test3` in
bytes 200..232 — one distinct block across all 21. They are leftovers. They are
also the reason a naive writer must not pad the full 233-byte field, exactly as
in the main files. `demotool.py import` writes only bytes 0..199 and then asserts
both the option tables and the record headers are byte-identical afterwards.

Verified: import of all 21 records leaves the file at 5135 bytes with every
changed byte inside a prompt region.

## Still to check in game: line wrapping

The main-file pipeline runs `textflow.py reflow` to insert breaks and pad to a
30-byte line grid, because the renderer does not word-wrap Latin text. **Whether
the demo's text box uses the same 30-byte width is unknown** — it is a cutscene
overlay, not the standard dialogue box, and the Chinese originals show no
30-byte structure to copy.

`build/demo.msg` is therefore **unwrapped**. Test it first. If lines break badly:

```
python3 tools/textflow.py reflow data/demo_script.csv -o /tmp/demo_final.csv
python3 tools/demotool.py import demo.msg /tmp/demo_final.csv --backup
```

The longest translated line is 91 bytes against a 199-byte cap, so there is ample
room for padding either way.

## demo*.dat are maps, and demo*.grp solved the flag-2 format

The seven `demo0N.dat` files use the ordinary map header. Two of them reuse
production tile sheets — `demo04` takes `MAP025.GRP`, `demo07` takes
`MAP037A.GRP` — so the attract mode replays real locations. Their area names
were already patched to English by `apply_names.py`, since it keys on the Big5
string and these carry the same names as the maps proper.

The four `demo0N.grp` files supplied the missing samples for the flag-2 layout:

```
size == 7 + 768 + (count + 256) * w * h
```

Exact on all five known samples — demo01/02/03/05.grp (count 304, 575, 382, 991)
and map035.grp (count 317). A 256-entry RGB palette sits at +7, and `count`
excludes a shared base bank of 256 cels.

**The palette is 8-bit RGB, not 6-bit VGA** — components reach 255, so do not
scale it by 255/63 the way DOS palettes usually need.

Decoded and eyeballed: coherent stone walls, dirt paths, wooden fencing and a
well. `holytool.py` now exports flag-2 sheets using the embedded palette, so no
`--pal` argument is needed:

```
python3 tools/holytool.py info   map/
python3 tools/holytool.py export map/demo01.grp out/
```

That closes the last unsolved container format. GRP flag 0, GRP flag 2 and VCT
are all decoded.
