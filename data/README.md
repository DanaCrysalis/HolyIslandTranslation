# data/

Translator-side inputs. None of this is game data — it is the translation itself plus
the tables the tools need to place it.

## Tracked

**`item_names.csv`** — the canonical name for each main-quest item, keyed by Big5, with
the old dialogue-side and inventory-side strings so a sweep can find them. Every
`canonical` value is ASCII and fits the 19-byte item-name field. Reasoning is in
`docs/ITEM_NAMES.md`.

## Untracked (`.gitignore`d, with a `.example` showing the schema)

These hold the full script. Decide deliberately whether to track them; do not let them
arrive by accident.

**`translated_updated.csv`** — **the master.** Edit here. Natural sentences, no padding,
no manual line breaks. Everything else in the dialogue pipeline is derived.

**`translated_final.csv`** — build artifact from `textflow.py reflow`. Each record is its
lines concatenated, so it is not readable prose, and editing a byte shifts every later
break in that record. Do not hand-edit.

**`strings_worksheet.csv`** — the `game.exe` string tables: 52 UI strings, 57 spells /
status / monsters (stride 0x40, 20 chars), 316 item names (stride 0x54, 19 chars).
`max_bytes` is the real field, derived from the LE fixup table, not from the original
string's length. `translate_all.py` reads this.

**`names.csv`** — map area names, from `mapnames.py dump`. 19 bytes plus a terminator;
anything longer runs into the linked-map field at 0x50.

**`option_labels.csv`** — one English label per distinct choice label. 80 distinct labels
fill all 174 slots across 84 records, so they are translated once by label rather than
per record. **10 bytes each**, and the `u16` branch value that follows must never be
touched. Match on the label with ASCII and fullwidth spaces stripped.

## Byte budgets, in one place

| Field | Budget | Overrun does what |
|---|---|---|
| `.MSG` prompt | 199 bytes | runs into option slot 0; choices vanish |
| `.MSG` option label | 10 bytes | overwrites the branch value; choice goes nowhere |
| Map area name | 19 bytes | runs into the linked-map filename at 0x50 |
| Item name | 19 bytes | overruns the 20-byte field in an 84-byte record |
| Spell / status / monster | 20 bytes | overruns the 0x40 stride |
| UI strings | 2–44 bytes, varies | overwrites the next referenced string |

The `.MSG` prompt budget is **confirmed**, not inferred: a filler record of exactly 199
bytes renders correctly in DOSBox. The earlier figures 194, 210 and 236 were all
approximations of the same struct boundary.
