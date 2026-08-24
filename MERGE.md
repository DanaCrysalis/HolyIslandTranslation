# demo.msg — merge

```
tools/demotool.py     -> tools/   (new)
tools/holytool.py     -> tools/   (REPLACES; flag-2 GRP now solved)
data/demo_script.csv  -> data/    (new)
build/demo.msg        -> your BUILD map dir, or wherever demo.msg lives
docs/DEMO.md          -> docs/    (new)
```

`build/demo.msg` is the English prologue, ready to drop in. 5135 bytes, same as
the original; option tables and record headers verified unchanged.

**Do not run msgtool2.py on demo.msg.** Different geometry — it will corrupt it.
Add demo.msg to any glob msgtool2 uses, as an exclusion.

## Test first

Play the attract sequence and check the line breaks. The demo text box may not
use the main dialogue box's 30-byte width, so `build/demo.msg` ships unwrapped.
If it looks wrong, see `docs/DEMO.md` for the reflow command.

## Then update FINDINGS.md

- demo.msg is no longer untranslated; it is the prologue, 21 records, done.
- GRP flag 2 is solved: `7 + 768 + (count + 256) * w * h`, palette is 8-bit.
