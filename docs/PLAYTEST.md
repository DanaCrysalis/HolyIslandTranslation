# Playtest log

Findings from playing the English build end to end. Bugs here are open unless marked
otherwise; anything resolved moves into `FINDINGS.md` and comes out of this file.

---

## OPEN — `MAP035.DAT` hard-locks under DOSBox

**Symptom.** The dialogue line "Back to Hamanu, fast." triggers the transition. The game
loads an empty mountain path — correct tiles, no persons present at all — and stops
responding to input.

**Key fact.** **PCem runs the same tree correctly.** The map loads with its characters
and play continues. So this is emulator-dependent, which makes a pure data corruption
unlikely and points at something the engine does at map-load time that DOSBox services
differently.

### Triage, in order

**1. Separate regression from emulation.** Run the same warp on a *pristine Chinese*
tree under the identical DOSBox config. The cheat console makes this one step:

```
F1  ->  JUMP MAP035
```

(`JUMP <mapname>` is handled before the code table, appends `.DAT`, and loads from
`.\MAP\` — see `FINDINGS.md` §8.) If pristine locks too, the translation is not
implicated and the rest of this section is the whole investigation. If pristine is fine,
skip to step 3.

**2. If it locks pristine too: suspect the CD-audio poll.** The engine does not let
MSCDEX loop for it — it issues an `int 2Fh` play for a frame range, **polls for
"playback finished", and re-issues** (`FINDINGS.md` §8). A poll that never returns is
exactly a frozen map with nothing else running, and MSCDEX emulation is precisely where
DOSBox and PCem diverge. Read the 20-byte field at **offset 0x28 of `MAP035.DAT`** and
compare its CD-DA track tag against what is actually mounted:

```
python3 -c "d=open('MAP035.DAT','rb').read(); print(d[0x28:0x3C])"
```

Then bisect the environment:

- unmount the CD image entirely and retry — if it plays, it is the audio path;
- `imgmount` the image as **ISO** rather than **CUE** and retry;
- try a different DOSBox core / `cycles` setting, since a spin-poll is timing-sensitive.

**3. If pristine is fine: suspect a translated asset-filename record.** Roughly 13% of
`.msg` records hold an asset filename (`MStg85.ANM`, `Map034.DAT`, `Ship.FTC`) rather
than dialogue, and translating one breaks a cutscene. *A map with no persons on it is
exactly what a cutscene that failed to load its actors looks like.* Grep the master CSV
for rows whose Chinese source was a bare filename and confirm they were passed through
unchanged:

```
grep -Ei '\.(anm|dat|ftc|grp|vct|xmi)' translated_updated.csv
```

**4. Check the map's own header while you are in there.** Fields at 0x00 (tile sheet),
0x14 (SFX) and 0x50 (linked sub-map) are 20-byte null-padded names. A name that runs
past its field — the failure mode `mapnames.py` guards against at 0x3C — would corrupt
the field after it. Confirm the 0x3C banner string in `MAP035.DAT` terminates before
0x4F.

### What would settle it

A DOSBox debugger break on the map-load path, or simply DOSBox's own log with
`cpu core=normal` and MSCDEX logging on. Failing that, the pristine A/B in step 1 is
enough to decide whether this ships as a known-issue note ("use PCem") or as a bug to
fix.

---

## OPEN — no ending or credits

A complete playthrough reached no ending sequence and no credits. This was previously
filed as "never located in the files"; it is now also "never reached in play", which
widens the possibilities:

1. the finale dialogue exists in the `.msg` tree but the playthrough missed its trigger;
2. it is delivered outside the dialogue engine (`demo01`–`demo07.dat`, a sibling
   `end.dat`/`end.msg`, or a baked "The End" card in a `.grp`/`.vct`);
3. the release genuinely does not have one.

First check is cheap and decides between (1) and the rest:

```
grep -E '六手甲乙佛|真命天子|摩羅王' translated_updated.csv
```

If the finale lines are present and translated, the content exists and the question is
the trigger. If they are absent, dump `demo01`–`demo07.dat` and look for an `end.*`
sibling — neither has ever been touched.

---

## RESOLVED — main-quest item names diverged between dialogue and inventory

14 items affected. Canonical set decided in `ITEM_NAMES.md`; not yet applied to either
side. Two source-glyph questions still gate it (蓮花岩木 vs 若木, 子鐲 vs 子燭).

---

## RESOLVED — choice rows absent in shops and the slave auction

Caused by the old `msgtool2` zero-padding all 236 bytes of the text field, erasing the
option table at +200. Fixed at source: import now writes and pads only bytes 0–199 and
asserts the table region is unchanged afterwards. `optfix.py restore --pristine` repairs
an already-damaged tree. Verified: 84 records carry a table, 174 slots, 0 left in
Chinese.
