# Main-quest item names — reconciliation

A playtest found 14 main-quest items whose **dialogue** name and **inventory** name
differ. That is a soft-lock in practice: dialogue tells the player what to hunt for in
the menu, and the menu calls it something else.

## The rule

**One canonical string per item, used in both places.** The item table in `game.exe`
(0x8CD68, stride 0x54, 20-byte name field at offset 0) allows **19 bytes plus a
terminator**, so the inventory side is the binding constraint and the dialogue side is
what moves. This is the opposite of the map-banner convention in `FINDINGS.md` §6, where
divergence from the prose glossary is deliberate — banners are decoration, item names
are navigation.

Every dialogue name below except three already exceeded 19 bytes. Names are ASCII, so
bytes == characters.

## The canonical set

| Big5 | Canonical (both sides) | Bytes | Was, in dialogue | Was, in inventory |
|---|---|---:|---|---|
| 黑皮書 | Black Book | 10 | Black Book | Black Book |
| 未見箴圖 | Unseen Admonition | 17 | Unseen Admonition Scroll | Unseen Chart |
| 魂應鼓 | Soul Echo Drum | 14 | Soul Drum | Soul Drum |
| 拯救亡靈符 | Soul Rescue Charm | 17 | spirit-saving talisman | Soul Rescue Charm |
| 蓮花若木 / 岩木 | Lotus Ruo-Tree | 14 | Lotus Ruo-Tree | Lotus Wood |
| 雲雷風鼓 | Cloud-Thunder Drum | 18 | Cloud-Thunder Drum | Storm Drum |
| 玄白赤鼎 | Tricolor Cauldron | 17 | Black-White-Crimson Cauldron | Tricolor Cauldron |
| 泊天神俑 / 神蛹 | Heavenbound Effigy | 18 | Heaven-Anchored Effigy | Sky Figurine |
| 大眼童屍 | Big-Eyed Corpse | 15 | Big-Eyed Corpse | Big-Eyed Corpse |
| 鏟子 | Shovel | 6 | Shovel | Shovel |
| 臥房鑰匙 | Bedroom Key | 11 | Bedroom Key | Bedroom Key |
| 真絹 | True Silk | 9 | real silk | True Silk |
| 命石 | Life Stone | 10 | Life Stone | Life Stone |
| 天玉 | Heavenly Jade | 13 | Heavenly Jade | Sky Jade |
| 子燭 / 子鐲 | Child Candle | 12 | Child Candle | Small Candle |

## Why these words

**The acrostic is load-bearing.** `game8:12` reads *"Take the first word of each: True,
Life, Heaven, Child."* The shipped inventory names `Sky Jade` and `Small Candle` break
it outright, and the old glossary's lowercase `real silk` broke it too. First words are
therefore fixed: **True / Life / Heaven / Child.**

**Three relics lost a word to the field, not to taste.** `Resplendent Bamboo Slips` is
24 bytes and `Black-White-Crimson Cauldron` is 28; neither fits. `Resplendent Slips` and
`Tricolor Cauldron` keep the distinguishing adjective, which is the part a player
searches on.

**`Heavenbound` over `Heaven-Anchored`** buys 18 bytes instead of 22 and reads as one
word rather than a compound.

**Two drums must stay distinguishable.** 魂應鼓 (opens the painting) and 雲雷風鼓
(relic 2) both shipped as bare "drum" names. `Soul Echo Drum` and `Cloud-Thunder Drum`
keep them apart in a menu list.

**`Soul Rescue Charm` moves the dialogue, not the inventory** — it was already the
inventory string, it fits, and `withered-bone talisman` (枯骨法器) is a different object
that needs to keep the word "talisman" to itself.

## Two unresolved source-glyph questions

Both must be checked against the actual item table before committing:

- **蓮花岩木 vs 蓮花若木.** 若木 is the mythical sun-tree; 岩木 is "rock wood" and is
  likely the typo. If the table says 岩木, `Lotus Ruo-Tree` is still right for the
  dialogue and the table entry is what gets corrected.
- **子鐲 vs 子燭.** 鐲 is a bracelet, 燭 a candle. If the item table genuinely says 鐲,
  then the object is a bracelet and `Small Candle` was the shipped mistranslation, not
  the reverse — in which case the canonical name is `Child Bracelet` (14 bytes). The
  acrostic survives either way, since only "Child" is fixed.

## Applying it

The set lives in `data/item_names.csv`, keyed by Big5, with both the inventory-side and
dialogue-side old strings so a sweep can find them.

```
# 1. inventory side -- reconcile into the exe worksheet, then rebuild from pristine
python3 big5scan.py <pristine>/game.exe --csv items.csv
#    edit strings_worksheet.csv rows to the canonical column of data/item_names.csv
python3 translate_all.py <pristine>/game.exe -o build/game.exe

# 2. dialogue side -- five strings move
#    sweep translated_updated.csv for the `dialogue_old` column, replace with `canonical`
python3 markerfix.py fix   translated_updated.csv -o step2.csv
python3 textflow.py  reflow step2.csv -o translated_final.csv
python3 msgtool2.py  import <build>/map translated_final.csv --max-bytes 199
```

Re-check byte budgets after the dialogue sweep: `Unseen Admonition` is 7 bytes shorter
than the phrase it replaces, but `Soul Rescue Charm` is 5 bytes shorter than
`spirit-saving talisman` only before padding, and `textflow reflow` re-pads to the
30-byte line boundary. Any record that was near the 199-byte ceiling should be
re-measured, not assumed.
