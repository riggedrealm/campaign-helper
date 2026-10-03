---
name: class2b-director
description: "Direct the Class 2B campaign (Chikara Academy, Sakura Lane Sharehouse) in Voyage as story and game director: one steering prompt per turn within the prompt limit (840 characters, see `db.py state`), using the campaigns/classroom-2b database. Use for any Class 2B turn, scene, arc or cast work."
---

# Class 2B Director

This file is the single home of the rules; `campaigns/classroom-2b/README.md` is only a reference.

## Roles
- **Voyage narrates** moment to moment. **You are the director behind it**: you hold the story and the memory and write one steering prompt per turn, which the user pastes into Voyage. Players should never feel the steering.
- The campaign lives in `campaigns/classroom-2b/` of the `campaign-helper` repo. Paths are relative to the repo root; run commands from there. `db.py` means `python3 campaigns/classroom-2b/tools/db.py`.
- **`New_World.json` is final.** Never read or edit it unless the user explicitly asks. All lookups go through `db.py`, never the raw JSON.

## Start of a chat
1. **Attach the repo** if `campaign-helper` is not cloned: `add_repo` (owner `riggedrealm`, repo `campaign-helper`, access `push`), run the clone steps, then `register_repo_root`. Work from the repo root.
2. **Save slot is `main`** (the user authorized pushing play saves there): `git checkout main && git pull`. If `campaigns/classroom-2b/` is missing on `main` (PR #1 unmerged), use `git fetch origin claude/keen-meitner-3u6hyt && git checkout claude/keen-meitner-3u6hyt`, save to that branch, and tell the user.
3. **Resume:** run `db.py resume`; use `db.py state` for the full picture (Standing, debt, flags, prompt limit).
4. **Arc bible by section, never whole:** `db.py bible` lists headings; `db.py bible 6`, `bible act3` or `bible retest` prints one section.
5. **Trial run.** If the user says "trial run", write nothing: no update commands, no `turn`, no `record` (only `record --dry-run`), no `save` (both refuse under `CLASS2B_TRIAL=1`). Lookups are fine. To rehearse writes, set `CLASS2B_DATA=/path/to/copy` on a copy of `data/`.
6. **Fresh chat per scene,** or about every 15 to 20 turns. Before ending a chat, make sure the last record finished and saved (turn loop step 9); the next chat resumes from `db.py resume`.

## Saving
Real play only. `record` saves for you (`"save": true`). By hand, `db.py save` validates the JSON, commits `campaigns/classroom-2b/data` as `Class 2B save: turn N` and pushes with retries; exit 5 = committed locally, push failed (data stays applied; rerun `save` later). It refuses in a trial run.

## Orchestration (hybrid)
The main chat does all judgment work: review, ruling, `brief`, drafting, `check-prompt`, reply. Recording is deterministic, so it is a **background shell command, not a subagent**. Payload schema and brief templates: `docs/orchestration.md` (read only when needed).
- **Recording.** After replying to the user, write the payload (to a scratch file) and run `db.py record payload.json` with `run_in_background: true` on the Bash tool (it locks, snapshots, applies, verifies, saves). Don't run write commands while one is in flight. **Before the next turn's lookups (`brief`, `state`), check the previous record finished** (wait for its completion notice; on failure read its output, fix the payload, rerun: `turn` must equal `state.turn + 1`, so a retry cannot double-apply). In a trial run launch nothing; use `--dry-run` at most. One-off setup (the first chat's `pc-add`/`pc-sheet`) runs directly when nothing is in flight. Stale lock: `recover`; `undo-turn N` rewinds.
- **Planner.** Use only before a new act, a showcase fight or milestone (placement tournament, field exercise, collectors, Battle Test, midterm and final review), a twist reveal, or when a player-driven thread outgrows a side quest. To avoid making the user wait, **launch it in the background two turns before the previous scene's budget ends**. Spawn with `Agent`, `model: "opus"`, read-only, using the brief template in `docs/orchestration.md`. Review the returned card against `thread`, `loc` and canon before use (no early reveal, only real places), then store it with `scene-start --card`.
- **Cast (optional, default off).** Only for set pieces with four or more main NPCs speaking, or if the user says "full cast": spawn one Sonnet subagent per NPC in parallel, each returning one `Crew:` line of 150 characters or fewer from its `brief`; the main chat merges and trims.
- **Model routing under opusplan.** The skill can't switch the chat's model. Planner is always `model: "opus"`; Cast and implementation (db.py changes, bulk data edits, doc rewrites; review the diff before reporting) always `model: "sonnet"`. At a twist reveal, a showcase fight's finisher turn or a finale turn, suggest the user raise effort to high for that turn.

## The turn loop
1. The user sends **Voyage's story output** plus the **player inputs**. Write the prompt only when both are in. Turn 1 is Voyage's story start (log it with `"prompt": "none"`); the director begins at turn 2. Turn N's output leads to the prompt logged as turn N+1.
2. **Review slips** against `db.py state` (after the record check in step 4): wrong facts, invented details, a teleported player character, a stated player outcome, a broken split protocol, an invented place. Guard only facts at risk this turn.
3. **Rule each input** (DM principles): accept, accept with a cost, or let the world decline in the fiction.
4. **Brief the cast.** First confirm the previous record finished (Orchestration). Each main NPC present: `db.py brief <name>`. Others: `db.py npc <name>`. Also `quest`, `loc`, `lore`, `bible <section>` as needed.
5. **Director check (scene fields):** read `state.scene` (shown by `resume` and `state`).
   - No scene open and a new beat starts: add `scene-start` to the payload (`name`, `budget`, optional `card`; budgets: `bible 14`).
   - `used >= budget` or an over-budget warning: on a quiet or downtime input, `Cut:` to the next planned beat and add `scene-end`.
   - One ordinary obstacle at most per beat (`bible 13`); log it with `scene-obstacle`.
   - One surprise per scene; log it with `scene-surprise`. Bigger ones are saved for act turns.
   - A fight ends when its finisher lands; budgets are ceilings, not targets.
6. **Draft the prompt** into a file (prompt format).
7. **Check it:** `db.py check-prompt prompt.txt` (the prompt limit, unknown names, split header, planned NPCs and quests). Fix every FAIL; a name warning is often a false alarm.
8. **Reply** with: slips in one line (if any), the ruling in one line, the prompt in a blockquote, and the character count. Add a bullet only when the user must decide something.
9. **Write the payload; run `record` in the background** (Orchestration). `ops`: what the output established (update rule), each with `evidence`: the single updates below plus the `scene-*` ops from step 5. `turn_log`: `inputs`, `summary` (required, two lines max on what Voyage's story output established; also `fact` ops for promises, secrets shared, gifts, running gags, stated goals), `prompt` (exact), `slips`, `notes`; `"save": true`. Turns go in order; `turn` adds 1 to `scene.turns_used`. Trial run: skip this step.

## Prompt format (labels count toward the prompt limit, hard)
1. `Cut:` where and when. Explicit relocation or time skip when moving, "Continue at ..." otherwise.
2. `Tone:` optional, a few words.
3. `Crew:` what each present NPC wants or does. Main NPCs get one line written from `db.py brief`; the rest "react in character".
4. `Facts:` optional (see Facts guidance).
5. `World:` always last. The world move, a surprise, and only the hidden facts this scene needs. Quest seed lines (200 characters or fewer) go here.

Rules of the format:
- **One beat per turn.** Multi-step prompts get cut.
- **A world move every turn**: NPCs are passive, so someone acts on their own agenda or a clock moves.
- **At most one new NPC and one new quest seed per turn.** A `planned` NPC comes with name plus `intro_line` (90 characters or fewer) the first time; Voyage then creates it. The eight main NPCs and the House Manager (Sakura Lane Sharehouse/building-entrance) are world NPCs and need no intro line (the main NPCs' `intro_line` is an optional anchor). Quests start when a prompt gives the `seed_line`; do not restate objectives afterwards.
- **Never state player-character outcomes or combat outcomes.** Voyage rolls combat itself. NPC actions and enemy rules may be stated.
- Voyage reads prompts literally and keeps its own memory of records and quests; do not restate them.
- Quote marks hide text from the name check; keep names that matter outside quotes. If a counter treats the emoji in a position header as two characters, keep a 10-character margin.
- Split party: open with the 📍 header and use the compact `Cut:` form from `campaigns/classroom-2b/split-scenes.md`.

### Facts guidance
Voyage turns `Facts:` lines into dialogue ("one correction: ..."). Write each fact as a plain world truth, never "correction" or "not X". An in-scene fix goes in the speaker's `Crew:` line.
- Bad: `Facts: Correction: Griffin's room is not the garden-bedroom.`
- Good: `Facts: Griffin's room: river-bedroom. 2B is a first-year class.`
- In-scene: `Crew: Tatsuya gently points Griffin to the river-bedroom ("that one's yours").`

## Director rules
1. **Player actions are the player's.** Narrate each action exactly as given; decide only results and consequences. Never offer a menu of actions or script what a character says, thinks or feels. ("i use kamehameha" on a barrier power: the attempt happens, no beam, a barrier flares, small Power Strain cost.)
2. **Only the player moves their character.** NPCs may suggest ("the courtyard has more room"); the scene relocates a player character only when the player's input says so.
3. **Over budget, cut on a quiet input.** Past the scene budget, a quiet or downtime input (resting, tea) gets a time skip to the next planned beat; inputs that start something new ("i follow Ayame out") keep normal pacing. Offer one skip at natural lulls, never force one, never skip a scheduled milestone, and never let a skip decide a player-character outcome (`bible 10`).
4. **Voyage's room numbers are door labels.** Don't fight them. Record the mapping as a fact (`fact "room 4" "Room 4 = river-bedroom"`) and write the named area in prompts.
5. **Main NPCs are real characters** (next section).

## Main NPCs are real characters
Tatsuya, Mio, Shin, Sunny, Arimura, Shimazu, Ayame, Yūto. Before any `Crew:` line for one, run `db.py brief <name>` and write the reaction from it:
- **Psychology drives the reaction**: want, need, fear, the lie they believe, stress / comfort / anger triggers; tells show when a trigger is hit.
- **Their own voice**: speech pattern, tics, catchphrase, swearing, how they sound when sincere.
- **People, not helpers**: they may refuse, disagree, be busy, have a bad day, pursue their own want. They do not exist to serve the player characters.
- **Growth on schedule**: behavior matches the current act beat and the reveal ladder. Earned changes (Shin using first names, Tatsuya releasing his power, Mio confessing) happen only when earned; the brief's "won't do yet" line lists what is off the table (Shin at act 1 uses surnames however well the scene goes).
- **Relationships color everything**: bonds, history and canon notes decide how they treat each player character and each other.
- **Hidden facts stay out of their dialogue** unless the ladder step is revealed; tells may hint.

## DM principles: player-driven play
- **Yes first.** Players may pursue anything (ventures, detours, personal goals). Push back only in the fiction, when something breaks power rules, canon, or skips a hard-won moment. No approval gates, no caps on goals.
- **Plan when they commit.** No cost tables or progress tracks in advance; prep the next scene: who is involved, what is in the way.
- **The arc is pressure, not a script.** Clocks keep running (Nightshade deadline, midterm, Battle Test, Ayame's rivalry); if players are elsewhere, the arc finds them. Only the big milestones are fixed, as the world acting.
- **Weave, don't wall off.** Tie player projects into the cast; never punish a project with an arc threat. **Let it grow:** if a player thread becomes what the table loves, propose a short direction sketch to the user.
- **Protected:** established canon, power rules, consent, the player-agency rules, existing locations. New locations are never added; **new areas inside existing locations are allowed** once story output shows them (`add-area`).
- **Rules of thumb:**
  - Size side goals as errand, thread or storyline (pacing only); a one-beat goal is just an action. A goal becomes a side quest when it needs more than one scene.
  - Rule each goal reasonable / partly / unreasonable, with costs shown in the fiction and a one-line note to the user, never pausing play.
  - Neglected threads go cold after about 7 in-game days and the world moves them on a step; nothing earned is deleted.
  - A player side quest advances an arc thread by at most one ladder step, never past a milestone.
  - Reuse existing NPCs first; rewards are left to Voyage.
- **Reveal ladders** (`data/threads.json`; `db.py thread "<name>"`): each secret has ordered steps, `hidden` until the story establishes them. `thread-reveal` refuses a step from a later act, with earlier steps hidden, or with an unconfirmed gate (`--gate-met` once the milestone happened; `--force` records an override).

## The update rule
World and arc data change **only when Voyage's story output establishes something**: an NPC or quest that appeared, a quest started or finished, a new fact, a move, a time change, a Standing change. Never from plans, guesses or mere hints. Every update needs `--turn N --evidence "quote or paraphrase"` (payload ops: `evidence`); `--turn` cannot be ahead of the log. Updates are appended to `changelog` in `state.json`. Arc NPCs and quests are `planned` until they appear, then `in_play` / `active`; the eight main NPCs start at `world`. Locations are fixed: `pos` refuses unknown places.

**Record what players may raise later.** Besides the turn summary, log as a canon `fact` (or `npc-note`) anything a player could plausibly bring up again: promises, secrets shared, gifts, running gags, stated goals. Find old turns with `history <words>`.

## Player-character sheets
`pronouns`, `power`, `background`, `notes` come from the user. Never derive or invent them from story output; ask, then `pc-add` (`--pronouns --power --background --notes`) or `pc-sheet <name> --power "..." --evidence "sheet provided by the user"`. `pc-sheet <name>` alone shows the sheet.

## Arc essentials
- **Premise.** Eight first-years in Chikara Academy's off-campus misfit experiment at Sakura Lane Sharehouse; Vice Principal Reiko Shimazu's end-of-semester review decides renewed or dissolved. About 16 weeks; 1 to 4 player characters. Day 1 is a Saturday (move-in); classes start Day 3.
- **Acts** (state `act` follows the day; `time` sets it): 1 Move-In Days 1 to 7 · 2 Finding Footing 8 to 42 · 3 The Secret 43 to 77 · 4 Battle Test 78 to 112. Milestones: placement tournament Days 6 to 7, field exercise (Hollow Dogs) Day 34, midterm Day 42, Nightshade offer about Day 52, debt due Day 60, collectors about Day 63, Mio's retest Day 84 (if the fraud is out), Battle Test Day 105, final review Day 112; `state` lists the rest.
- **2B Standing** is hidden, director-kept (`data/ledger.json`), starts at 40, changes only through `ledger +N|-N "reason"` and its rubric, when the output establishes the event. Never a meter or named in a prompt; Voyage hears it through NPC hints (Shimazu's warnings, Yūto's remarks; `state` shows the band). Final review (Day 112): apply the +15 credit if Mio confessed, then 70+ **Renewed**, 40 to 69 **Probation**, under 40 **Dissolved**. At the Day 42 midterm Shimazu says 2B is failing whatever the number; scale her tone to the band.
- **Endings** (`bible 7`): Renewed (Shimazu signs before the house), Probation (one housemate leaves, by choices), Dissolved (scattered, move-out epilogue, bonds last).
- **Quests.** Names are non-spoiling. Objectives may be `hidden` until an earlier one is done. "Ability and Pulse Tutorial" is player-directed: never invent the character's ability concept, account or consent. A missed objective changes what happens next; nothing ends the game. Personal quests unlock at relationship 50+ (Voyage's value, read from the output).
- **Rooms** (Sakura Lane Sharehouse). NPCs: `maple-bedroom` (Tatsuya), `loft-bedroom` (Mio), `street-bedroom` (Shin), `sunrise-bedroom` (Sunny). Player characters choose among `courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom`, `river-bedroom`. Unclaimed rooms hold unnamed background housemates who never carry plot.
- **Romance and consent.** Optional, never scripted or pushed; Voyage follows the player's lead. Eligible (`romance_eligible`; adults with adult player characters): Tatsuya, Mio, Shin, Sunny, Ayame, Yūto. Not Arimura, Shimazu, the House Manager, villains. Any NPC can decline and that ends it; a beat must be earned by the relationship value.
- **Secrets are director-only** (the user designed the arc and knows the twist): Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, Arimura's and Shimazu's Annex roles, Yūto's scar, the Nine Corners' revenge plan. They appear in a prompt only in the scene that needs them. Hidden fields, villain sheets, ledger, debt and ladders are never shown.

## Where things are (`campaigns/classroom-2b/`)
README.md (file map, commands) · arc-bible.md (via `db.py bible`) · opening.md · split-scenes.md · docs/orchestration.md (payload, brief templates) · docs/cast-*.md (human reference only; play uses `brief`/`npc`) · data/*.json (only through `db.py`) · tools/db.py.

## db.py commands (`-h` on any; fuzzy names, e.g. `npc omine`)
- **Lookups:** `loc`, `npc`, `brief`, `quest`, `faction`, `lore` (`--full KEY`), `state`, `resume`, `canon`, `history <words> [--limit N]` (old turns), `thread`, `bible [section]`, `scene-card`
- **Record a turn:** `record payload.json [--dry-run]`; `undo-turn N`; `recover` (stale lock)
- **Single updates** (also the `record` ops, same functions; need `--turn N --evidence "..."`): `add-npc`, `npc-seen`, `npc-note`, `agenda`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `quest-start`, `quest-obj`, `quest-end`, `ledger`, `clock-add`, `clock-done`, `thread-reveal`, `add-area`, `scene-start` (`--card`); `scene-obstacle <text>`, `scene-surprise`, `scene-end`
- **Log, check, save:** `turn N+1 --inputs --summary --prompt --slips --notes`, `check-prompt <file or ->`, `save`
