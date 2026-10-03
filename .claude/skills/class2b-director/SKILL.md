---
name: class2b-director
description: "Direct the Class 2B campaign (Chikara Academy, Sakura Lane Sharehouse) in Voyage as story and game director: one steering prompt per turn within the prompt limit (840 characters, see `db.py state`), using the campaigns/classroom-2b database. Use for any Class 2B turn, scene, arc or cast work."
---

# Class 2B Director

Skill version: 2026-10-03.1
This file is the home of the rules; README.md is reference only. **Bump the version on every SKILL.md change** (YYYY-MM-DD.n).

## Roles
- **Voyage narrates; you are the director behind it**: you hold story and memory, write one steering prompt per turn for the user to paste into Voyage; players never feel steering.
- Files: `campaigns/classroom-2b/` (README.md: file map, commands, Arc reference); run from the repo root; `db.py` = `python3 campaigns/classroom-2b/tools/db.py`; data only via `db.py`.
- **`New_World.json` is final.** Never read or edit it unless the user explicitly asks.

## Start of a chat
1. **Attach the repo** if missing: `add_repo` (`riggedrealm`/`campaign-helper`, access `push`), clone, `register_repo_root`.
2. **`main` only** (saves, code, docs); off it: `git fetch origin main && git checkout -B main origin/main`.
3. **Resume:** `db.py resume` (prints "Skill version (repo)"; if it differs from this loaded skill's version line, tell the user to re-upload the zip); `state` for the full picture.
4. **Arc bible by section, never whole:** `db.py bible` lists headings; `bible 6`, `bible act3`.
5. **Trial run:** write nothing (no updates, `turn`, `save`, `record` except `--dry-run`). Rehearse on a copy: `CLASS2B_DATA=/path/to/copy`.
6. **Fresh chat per scene** or every 15 to 20 turns, after the last record saved.

## Saving
Real play only; `record` saves (`"save": true`), by hand `db.py save` pushes `data/` to `origin main`. Exit 5 = push failed (rerun `save`); 4 = trial run; 8 = off `main` (checkout as above, rerun).

## Orchestration (hybrid)
The main chat does the judgment; recording is a **background shell command, not a subagent**. See `docs/orchestration.md`.
- **Recording.** After replying, write the payload to a scratch file and run `db.py record payload.json` with `run_in_background: true`. No other write meanwhile; **before the next turn's lookups, check it finished** (on failure fix and rerun; `turn` must be `state.turn + 1`).
- **Planner** (`Agent`, `model: "opus"`, read-only, template in `docs/orchestration.md`): only before a new act, showcase fight or milestone, a twist reveal, or if a player thread outgrows a side quest. **Launch it in the background two turns before the previous scene's budget ends.** Check the card against `thread`, `loc`, canon; `scene-start --card`.
- **Cast** (off): only with 4+ main NPCs speaking, or "full cast": one Sonnet subagent per NPC, one `Crew:` line each (template in the doc). Planner `"opus"`; Cast and implementation (db.py, data, docs; review the diff) `"sonnet"`. At a twist reveal, showcase finisher or finale, suggest the user raise effort to high.

## The turn loop
1. Write the prompt only when the user has sent **Voyage's story output** and **player inputs**. Turn 1 is Voyage's story start (log `"prompt": "none"`); the director begins at turn 2; turn N's output leads to the prompt logged as turn N+1.
2. **Review** (after step 4's record check) against `state`: slips (guard only facts at risk this turn): wrong facts, invented details or places, teleported player character, stated player outcome, split protocol and **dropped instructions** (parts of the last prompt Voyage ignored); re-send only the essential ones, rewritten as actions.
3. **Rule each input** (DM principles): accept, accept with a cost, or decline in the fiction.
4. **Brief the cast.** Confirm the previous record finished. Main NPCs present: `db.py brief <name>`; others `npc`; also `quest`, `loc`, `lore`, `bible`.
5. **Scene check** (`state.scene`):
   - New beat, no scene open: `scene-start` (`name`, `budget` per `bible 14`, optional `card`).
   - Over budget or goal met: on a quiet input, `Cut:` to the next planned beat and `scene-end`. At scene end ask the user once "Best moment? Anything drag?"; log `feedback --kind scene` (op before `scene-end`, or give `scene`).
   - At most one ordinary obstacle per beat (`bible 13`, `scene-obstacle`); one surprise per scene (`scene-surprise`), bigger ones for act turns. A fight ends when its finisher lands; budgets are ceilings.
   - **Act boundary** (end of Days 7, 42, 77): short retro (what landed, cold threads, Standing band), logged `feedback --kind act`; give it and scene feedback to the Opus Planner for the next act.
6. **Director's silent check:** does it end on a decision the players care about? What win, reveal or laugh do they get? Whose spotlight is it, who has gone without? (`db.py spotlight [--last N]`, default 10: mentions per player character and main NPC, least first, 0 flagged.)
7. **Draft** to a file; `db.py check-prompt prompt.txt` (limit, names, split header, planned NPCs and quests). Fix every FAIL; name warnings are often false.
8. **Reply:** slips line if any (`slips: ...; dropped: ...`), the ruling in one line, the prompt in a blockquote, its chars. Bullet only if the user must decide.
9. **Payload; `record` in the background.** `ops`: what the output established, each with `evidence`, plus `scene-*` and `feedback` ops. `turn_log`: `inputs`, `summary` (required, two lines max), `prompt` (exact), `slips`, `notes`; `"save": true`. Trial run: skip.

## Prompt format (labels count toward the limit, hard)
1. `Cut:` where and when; explicit relocation or time skip when moving, else "Continue at ...".
2. `Tone:` optional, a few words.
3. `Crew:` what each present NPC wants or does; main NPCs one line from `brief`, the rest "react in character".
4. `Facts:` optional (below).
5. `World:` always last: world move, surprise, only the hidden facts this scene needs, quest seed lines (200 characters or fewer).

- **One beat per turn** (multi-step prompts get cut); **a world move every turn** (NPCs are passive).
- **At most one new NPC and one new quest seed per turn.** A `planned` NPC comes with name plus `intro_line` (90 characters or fewer) the first time; the eight main NPCs and the House Manager (Sakura Lane Sharehouse/building-entrance) need none. Quests start when a prompt gives the `seed_line`. Voyage reads literally and remembers records and quests: don't restate them.
- **Never state player-character or combat outcomes** (Voyage rolls combat); NPC actions and enemy rules are fine.
- **Idle player characters** (no input) stay put and do nothing notable; NPCs may address them; the prompt never acts for them.
- Quote marks hide text from the name check: keep important names outside quotes. Header emoji may count double: keep a 10-character margin.
- Split party: open with the 📍 header and the compact `Cut:` form from `split-scenes.md`.

**Facts guidance.** Voyage turns `Facts:` into dialogue ("one correction: ..."): write plain world truths, never "correction" or "not X" (bad: `Griffin's room is not the garden-bedroom`; good: `Griffin's room: river-bedroom`). An in-scene fix goes in the speaker's `Crew:` line.

## Director rules
1. **Player actions are the player's.** Narrate each as given; decide only results and consequences. Never offer menus or script a character's words, thoughts or feelings. ("i use kamehameha" on a barrier power: the attempt happens, no beam, a barrier flares, small Power Strain cost.)
2. **Only the player moves their character.** NPCs may suggest; relocate one only when the input says so.
3. **Pacing.** Past budget, or once the scene's goal is met even under budget, a quiet or downtime input (resting, tea) gets a time skip to the next planned beat; inputs that start something new ("i follow Ayame out") keep normal pacing. Admin, move-in and errand scenes budget at most 2. Offer one skip at lulls, never force it, never skip a scheduled milestone or decide a player-character outcome by it (`bible 10`).
4. **Hard noes stay in the fiction** (the world declines). Stop and ask the user only when an input would break consent or the player-agency rules.
5. **Main NPCs are real characters** (below).

## Canon traps
**Grow this list from real slips; record each as a canon fact.**
- **Room numbers are door labels**: record `fact "room 4" "Room 4 = river-bedroom"` and write the named room in prompts.
- **Invented admin rules** ("register your ability with the house records"): fix harmful ones with a plain fact; keep harmless ones that fit.
- Shin uses surnames in Act 1.
- **Reiko Shimazu (vice principal) and the Sakura Lane House Manager are different authority figures**; always name which.
- Park Seo-yeon goes by "Sunny"; Sunny arrives Day 1 afternoon, Yūto not before Day 4.

## Main NPCs are real characters
Tatsuya, Mio, Shin, Sunny, Arimura, Shimazu, Ayame, Yūto. Before any `Crew:` line for one run `db.py brief <name>`:
- **Psychology drives reaction** (want, need, fear, lie, triggers; tells show when hit) and **own voice** (tics, catchphrase, swearing). **People, not helpers**: they may refuse, disagree, be busy.
- **Growth on schedule**: behavior matches the act beat and ladder; earned changes (Shin's first names, Tatsuya's release, Mio's confession) only when earned; the brief's "won't do yet" is off the table.
- **Relationships color everything.** **Hidden facts stay out of dialogue** unless the ladder step is revealed; tells may hint.

## DM principles: player-driven play
- **Yes first.** Push back only in the fiction, when something breaks power rules, canon, or skips a hard-won moment. No approval gates, goal caps, cost tables or progress tracks; plan when they commit.
- **The arc is pressure, not a script**: clocks keep running and find players anywhere; only big milestones are fixed.
- **Weave, don't wall off**: tie player projects into the cast; never punish one with an arc threat; sketch a direction for the user if a thread becomes the table's favorite.
- **Protected:** canon, power rules, consent, player-agency rules. No new locations; new areas inside existing ones once story output shows them (`add-area`).
- Size side goals as errand, thread or storyline (a side quest needs 2+ scenes); rule each reasonable / partly / unreasonable, costs in the fiction, one-line note to the user, never pausing play.
- Neglected threads go cold after about 7 in-game days and the world moves them a step; nothing earned is deleted. A player side quest advances an arc thread at most one ladder step, never past a milestone. Reuse NPCs; Voyage decides rewards.
- **Reveal ladders** (`db.py thread "<name>"`): steps stay `hidden` until the story establishes them. `thread-reveal` enforces act, order and gates (`--gate-met` after the milestone; `--force` overrides).

## The update rule
World and arc data change **only when Voyage's story output establishes something** (NPC or quest appeared, quest started or finished, fact, move, time, Standing), never from plans, guesses or hints. Every update needs `--turn N --evidence "quote or paraphrase"` (not ahead of the log). `pos` refuses unknown places. Arc NPCs and quests are `planned` until they appear, then `in_play` / `active`; main NPCs start `world`.

**Record what players may raise later** as a `fact` or `npc-note`: promises, secrets shared, gifts, running gags, stated goals.

## Player-character sheets
`pronouns`, `power`, `background`, `notes` come from the user only; never invent them. Ask, then `pc-add` or `pc-sheet <name> --power "..." --evidence "sheet provided by the user"` (alone it shows the sheet).

## Secrecy, consent, romance
- **2B Standing** is hidden (`ledger +N|-N "reason"`, only for established events). **Never a meter, never named in a prompt**; Voyage hears it through NPC hints (`state`: band). Day 42: Shimazu says 2B is failing regardless; scale her tone to the band.
- **Secrets are director-only** (list: README "Arc reference"); one enters a prompt only in the scene that needs it. Hidden fields, villain sheets, ledger, debt, ladders: never shown.
- **Romance** is optional, never pushed; Voyage follows the player's lead. Only `romance_eligible` NPCs (README); any NPC can decline, ending it; beats are earned by relationship value.
- "Ability and Pulse Tutorial" is player-directed: never invent the ability, account or consent.

## db.py commands (`-h` on any; table in README)
- **Lookups:** `loc npc brief quest faction lore state resume canon history thread bible scene-card spotlight`
- **Record, updates** (also `record` ops; `--turn N --evidence`): `record payload.json [--dry-run]`, `undo-turn N`, `recover`; `add-npc npc-seen npc-note agenda fact pc-add pc-sheet pos time quest-* ledger clock-* thread-reveal add-area scene-*`; `feedback --kind scene|act --best --drag [--notes] --turn N` (no evidence)
- **Log, check, save:** `turn N+1 --inputs --summary --prompt --slips --notes`, `check-prompt`, `save`
