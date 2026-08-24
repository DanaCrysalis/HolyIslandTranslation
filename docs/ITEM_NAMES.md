# Item names — resolved

Both glyph questions are settled from the pristine item table, which still holds
the Big5 names:

- **蓮花若木**, not 岩木. `Lotus Ruo-Tree` stands — 若木 is the mythical sun-tree.
- **子燭**, not 子鐲. It is a candle. `Child Candle` stands. (鐲 does appear in
  the table, at item 297 溫熱手鐲 `Warm Bracelet` — a different object, which is
  probably where the confusion came from.)

## The Black Book was in the table all along

Item **251** `黑皮書` shipped as `Black Leather Book`. 皮 marks the binding, and
dialogue calls it "the black book" throughout, so canonical is **`Black Book`**.

## 泊天神蛹 and 泊天神俑 are TWO ITEMS, not a typo

`FINDINGS.md` said the 蛹 spelling was a source typo for 俑. It is not — both
exist as separate entries:

| Item | Big5 | Was | Now |
|---|---|---|---|
| 288 | 泊天神**蛹** (pupa) | Sky Pupa | **Heavenbound Pupa** |
| 310 | 泊天神**俑** (tomb figure) | Sky Figurine | **Heavenbound Effigy** |

**This needs a playtest check.** `game78.msg` rec 5 — the reward for the
big-eyed-corpse trade — has 泊天神蛹 as its source but its English read
"Heaven-Anchored Effigy", i.e. the *other* item's name. Meanwhile the Buddha's
relic demand (`game8:8`, `game127:2`, `game128:8`) asks for 泊天神俑. So the
source itself conflates them.

The names above keep them related but distinguishable, which is the safe choice
either way. If a playthrough shows the player receives one and the Buddha wants
the other, that is an original-game bug worth documenting — the playtester did
complete the game, so the engine's actual check evidently tolerates it.

## Applied to the exe

| Item | Was | Now | Bytes |
|---|---|---|---|
| 251 | Black Leather Book | Black Book | 10 |
| 253 | Mottled Tablet | Resplendent Slips | 17 |
| 255 | Soul Drum | Soul Echo Drum | 14 |
| 258 | Lotus Wood | Lotus Ruo-Tree | 14 |
| 261 | Unseen Chart | Unseen Admonition | 17 |
| 278 | Sky Jade | Heavenly Jade | 13 |
| 282 | Storm Drum | Cloud-Thunder Drum | 18 |
| 288 | Sky Pupa | Heavenbound Pupa | 16 |
| 306 | Small Candle | Child Candle | 12 |
| 310 | Sky Figurine | Heavenbound Effigy | 18 |

Already canonical and untouched: 260 Soul Rescue Charm, 262 Life Stone,
273 Shovel, 275 Bedroom Key, 279 True Silk, 287 Tricolor Cauldron,
311 Big-Eyed Corpse.

## Applied to dialogue — 22 rows

Every change shortens or preserves length; none approaches the 199-byte cap.

```
Unseen Admonition Scroll     -> Unseen Admonition      5 rows
spirit-saving talisman       -> Soul Rescue Charm      4 rows
Heaven-Anchored Effigy       -> Heavenbound Effigy     3 rows (+1 -> Pupa)
black book                   -> Black Book             4 rows
real silk                    -> True Silk              3 rows
Black-White-Crimson Cauldron -> Tricolor Cauldron      1 row
Resplendent Bamboo Slips     -> Resplendent Slips      1 row
life stone                   -> Life Stone             1 row
```

`heavenly jade` was already correct in the one row that carries it.

## The acrostic survives

`game8:12` — *"Take the first word of each: True, Life, Heaven, Child."*

`game8:11` now reads: *"Holy Island? You mentioned True Silk, a Life Stone,
Heavenly Jade, the Child Candle?"* The four first words line up. The shipped
inventory names `Sky Jade` and `Small Candle` broke it, and the old dialogue's
lowercase `real silk` broke it too.

## Verification

- All 17 canonical names fit the 19-byte field; longest is 18.
- `itemfit.py --against` reports **17 canonical, 0 to change, 0 not found**.
- Rebuilding from pristine via `strings_worksheet.csv` reproduces the patched
  exe with **0 differing bytes in the item table** (19 elsewhere: the banner
  byte, which `patch_banner.py` writes, plus unreachable linker padding).
- No residual old item name anywhere in the dialogue CSV.
