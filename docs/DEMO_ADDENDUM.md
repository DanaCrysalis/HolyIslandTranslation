# demo files — resolved, closed

Append to `docs/DEMO.md`. Supersedes its open questions.

## The demo maps are development leftovers, not shipped content

Confirmed by playtest via the cheat console (`F1` → `JUMP DEMO01` … `DEMO07`,
which is the only way to reach them):

- **demo01** — unfinished terrain. No collision anywhere; only the start point
  renders correctly.
- **demo02–06** — mostly isolated battles.
- **demo07** — a boss fight, and **it displays English**, so it draws its script
  from an ordinary `game##.msg` that the main pipeline already translated.

## They are unreachable in normal play

- The title menu has exactly four entries: NEW GAME, LOAD GAME, SETTINGS, EXIT.
- The cheat table has no demo command (RAISE UP, FULL UP, YOKI KEYS, GET MONEY,
  RESET GAME, SHOW MEMORY, LIFE AGAIN, SAVE DEBUG, REGETOBJ, KILL ON/OFF,
  HID/SHOW MONSTER, SHOW EVEN, SHOW MAP, STRONG, JUMP, GET OBJECT).
- `game.exe` references **only** `Demo02.GRP`, hardcoded with no `%d` template,
  sitting beside `Logo.ANM` and `Title01.FTC` — i.e. a title-sequence backdrop.
  It never names `demo.msg`, `demo01.dat`, or any other demo file.
- The string `是否離開DEMO程式？` ("leave the DEMO **program**") points at a
  separate playable-demo release rather than an attract mode inside retail.
  demo04 and demo07 borrowing `MAP025.GRP` and `MAP037A.GRP` fits a demo built
  from production maps.

## Status: done, no further work

`demo.msg` is translated and shipped in the patch. It is correct, byte-verified,
and harmless whether or not the engine ever renders it. The line-wrapping
question in `DEMO.md` is moot — the file appears unreachable, so it was never
worth a reflow pass.

**Do not run `msgtool2.py` on `demo.msg`.** That still holds: different geometry
(10-byte header, 233-byte field, 3 option slots of 11 bytes), and msgtool2 will
corrupt it. Use `demotool.py`.

The genuinely valuable output from these files was the **flag-2 GRP format**,
solved from the four demo `.grp` samples and recorded in `DEMO.md`:
`size == 7 + 768 + (count + 256) * w * h`, palette 8-bit RGB.
