# verify_tree.py — false positives removed

Replaces `tools/verify_tree.py`. No other file changes.

## The 5 "clobbered link" errors were wrong

That check dated from the first MAP035 theory, before testing showed restoring
the byte is a **regression** (garbled terrain, symptom unchanged, harder crash).
It should never have been ERROR severity, and following its advice would damage
a working tree.

It now reports as a note:

```
ok  map035.dat: linked map disabled (name reads NUL+'AP036.DAT'; MAP036.DAT
    exists). Intentional -- do not restore.
```

Five files have a disabled link whose target still exists: map002, map003,
map035, map035a, map036. Ten more point at targets that were deleted. All work
as shipped. Zeroing the first character is how the developers disabled a link
whose file still existed; there was no other way.

## demo.msg note refreshed

Was: `untranslated content -- see FINDINGS 11`, stale once demo.msg was
translated. Now counts English records and names the right tool:

```
ok  demo.msg: 21 records on the 243-byte stride, 21 in English
    (use demotool.py, NOT msgtool2)
```

## Expected clean output

```
0 error(s)
```

with notes for the 15 disabled links and one warning only if `.bak` files are
still lying around.
