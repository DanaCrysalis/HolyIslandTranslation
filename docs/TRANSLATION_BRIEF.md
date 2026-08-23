# Translation brief

*(Paste this whole file verbatim when starting a new translation session. It is the
working prompt; `FINDINGS.md` section 10 is the same text and the two must be kept in
step.)*

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
