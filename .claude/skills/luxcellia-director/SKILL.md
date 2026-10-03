---
name: luxcellia-director
description: "Direct the Luxcellia: The Fifth Hero's Party campaign (Aureliath, Crownveil Sovereignty) in Voyage: one steering prompt per turn within the prompt limit (840 characters, see `db.py state`). Use for any Luxcellia: The Fifth Hero's Party turn, scene, arc or cast work."
---

# Luxcellia: The Fifth Hero's Party Director

Skill version: 2026-10-03.1
Generic rules: 2026-10-03.4
**Bump the version on every change.**

<!-- generic:start core -->
## Roles
- **Voyage narrates; you direct behind it**: you hold story and memory and write one steering prompt per turn for the user to paste into Voyage; players never feel it.
- Files: `campaigns/luxcellia/` (README.md: file map, command table, Arc reference); run from the repo root; `db.py` = `python3 tools/db.py --campaign luxcellia` (`-h` on any command); data only via it.
- **The Voyage world export JSON is final**: never read it unless asked; it changes only via user-approved Studio requests (`docs/studio.md`).

## Start of a chat
1. Repo: attach if missing (`add_repo` `riggedrealm`/`campaign-helper`, `push`; clone, `register_repo_root`). `main` only; off it: `git fetch origin main && git checkout -B main origin/main`.
2. Resume: `db.py resume` (if "Skill version (repo)" differs from this version line, tell the user to re-upload the zip); `state` for detail; offer `recap [--turns N]`.
3. Arc bible by section, never whole: `db.py bible` lists headings.
4. Trial run: write nothing (no updates, `turn`, `save`, `record` except `--dry-run`). Rehearse on a copy (`VOYAGE_DATA=/path`).
5. Fresh chat per scene or every 15 to 20 turns, after saving.

## Saving
Real play only; `record` saves (`"save": true`), by hand `db.py save`. Exit 5 = push failed (rerun `save`); 4 = trial run; 8 = off `main` (checkout, rerun).

## Orchestration (hybrid)
Main chat judges; recording is a **background shell command, not a subagent** (`docs/orchestration.md`).
- Recording. After replying, write the payload to a scratch file; run `db.py record payload.json` with `run_in_background: true`. No other write meanwhile; before the next turn's lookups, check it finished (on failure fix, rerun; `turn` = `state.turn + 1`).
- Planner (`Agent`, `"opus"`, read-only): only before a new act, showcase fight, milestone or twist reveal, or when a player thread outgrows a side quest. Launch it in the background two turns before the scene budget ends. Check the card (`thread`, `loc`, canon); then `scene-start --card`.
- Cast (off): only with 4+ main NPCs speaking or "full cast": one Sonnet subagent per NPC, one `Crew:` line each (doc templates). Implementation work `"sonnet"`, diff reviewed. Suggest higher effort at a twist reveal, showcase finisher or finale.

## The turn loop
1. Write the prompt only once the user has sent **Voyage's story output** and player inputs. Turn 1 is Voyage's story start (`"prompt": "none"`); you begin at turn 2.
2. Review (once the last record has finished) against `state`; guard only facts at risk this turn. Slips: wrong facts, invented details or places, teleported player character, stated player outcome, split protocol, dropped instructions (ignored parts of the last prompt); re-send only essential ones, as actions. Load-bearing slip in the latest output: Studio `story-fix` now, before the prompt.
3. Rule each input: accept, accept with a story consequence, or the world declines in the fiction. **Voyage decides success, failure, strain, damage and every number; you decide only story consequences** (who reacts, what the world does, where the scene turns).
4. Brief the cast. Main NPCs present: `db.py brief <name>`; others `npc`; also `quest`, `loc`, `lore`, `bible`.
5. Scene check (`state.scene`):
   - New beat, no scene open: `scene-start` (`name`, `budget` per `bible budgets`, optional `card`).
   - Over budget or goal met: on a quiet input, `Cut:` to the next beat and `scene-end`. At scene end ask once "Best moment? Anything drag?"; log `feedback --kind scene` (op before `scene-end`, or give `scene`).
   - One ordinary obstacle per beat at most (`bible surprise rules`, `scene-obstacle`); one surprise per scene (`scene-surprise`), bigger for act turns.
   - Act boundary (end of each act): short retro (what landed, cold threads), `feedback --kind act`; give it and scene feedback to the Opus Planner.
6. Director's silent check: does it end on a decision the players care about? What win, reveal or laugh do they get? Whose spotlight, who has gone without? (`db.py spotlight`).
7. Draft to a file; `db.py check-prompt prompt.txt` (FAILs: limit, labels, hidden ladder-step words; WARNs: names, split header, "correction"/"not X" in Facts, stated outcomes). Fix every FAIL; name warnings are often false.
8. Reply: slips line if any (`slips: ...`), the ruling in one line, the prompt in a blockquote, its char count. Bullet only if the user must decide.
9. Payload; `record` in the background. `ops`: what the output established, each with `evidence`, plus `scene-*`, `feedback`. `turn_log`: `inputs`, `summary` (two lines max), `prompt` (exact), `slips` ("category: text"; `fact|invention|teleport|outcome|dropped`), `notes`; `"save": true`.

## Prompt format (labels count toward the limit, hard)
1. `Cut:` where and when; explicit relocation or skip when moving, else "Continue at ...".
2. `Tone:` optional.
3. `Crew:` what each present NPC wants or does; main NPCs one line from `brief`, others "react in character".
4. `Facts:` optional (below).
5. `World:` always last: world move, surprise, hidden facts only as this scene needs, quest seed lines (200 characters or fewer).

- One beat per turn (multi-step prompts get cut); a world move every turn (NPCs are passive).
- At most one new NPC and one new quest seed per turn. A `planned` NPC comes with name plus `intro_line` (90 characters or fewer) once; main NPCs and the fixed NPCs named in World rules need none. Quests start when a prompt gives the `seed_line`; then `quest-start` (never seeded twice). Voyage owns quest progress: no objective or ending records. Voyage remembers records and quests: don't restate them.
- **Never state player-character or combat outcomes** (Voyage rolls combat); NPC actions and enemy rules are fine.
- Idle player characters stay put, do nothing notable; NPCs may address them; the prompt never acts for them.
- Quotes hide text from the name check: keep key names outside. Header emoji may count double: keep a 10-char margin.
- Split party: 📍 header and compact `Cut:` form from `split-scenes.md`.

Voyage turns `Facts:` into dialogue ("one correction: ..."): plain truths, never "correction" or "not X". An in-scene fix goes in the speaker's `Crew:` line.
<!-- generic:end -->

<!-- generic:start play-rules -->
## Director rules
1. Player actions are the player's. Narrate each as given; decide only story consequences. No menus; never script a character's words, thoughts or feelings. Overreaching input: the attempt happens, the world answers within the power.
2. Only the player moves their character. NPCs may suggest; relocate only when the input says so.
3. Pacing. Past budget or goal met, a quiet input gets a time skip to the next planned beat; inputs starting something new keep normal pacing. Admin, move-in and errand scenes budget at most 2. Offer one skip at lulls, never force it, never skip a milestone or decide a player outcome by it (`bible time skips`).
4. Hard noes stay in the fiction. Stop and ask the user only when an input would break consent or the player-agency rules.
5. Main NPCs are real characters.

## Main NPCs are real characters
Run `db.py brief <name>` before any `Crew:` line for one (list: World rules):
- Psychology drives reaction (want, fear, lie, triggers, tells) and own voice (tics, catchphrase). People, not helpers: they may refuse, disagree, be busy.
- Growth on schedule: behavior matches the act beat and ladder; earned changes only when earned; "won't do yet" is off the table.
- Relationships color everything. Hidden facts stay out of dialogue until the ladder step is revealed; tells may hint.

## DM principles: player-driven play
- Yes first. Push back only in the fiction, when something breaks power rules, canon, or skips a hard-won moment. No approval gates, goal caps or progress tracks.
- The arc is pressure, not a script: clocks find players anywhere; only big milestones are fixed.
- Weave, don't wall off: tie player projects into the cast; never punish one with an arc threat; if a thread becomes the table's favorite, sketch a direction for the user (the Opus Planner re-plans).
- Protected: canon, power rules, consent, player-agency rules. No new locations; new areas inside existing ones once the story shows them (`add-area`).
- Size side goals as errand, thread or storyline (a side quest needs 2+ scenes); rule each reasonable / partly / unreasonable, consequences in the fiction, a one-line user note, never pausing play.
- Neglected threads go cold after about 7 in-game days and the world moves them a step; nothing earned is deleted. A side quest advances an arc thread at most one step, never past a milestone. Reuse NPCs; Voyage decides rewards.
- Reveal ladders (`thread "<name>"`): steps stay `hidden` until the story establishes them; `thread-reveal` enforces act, order, gates (`--gate-met` after the milestone; `--force`).

## Fights (story only)
Villain personality, want, dialogue: `Crew:`; battlefield and its changes: `World:`. At the fight's opening give Voyage the villain sheet's rule and weakness (`bible`) as plain facts. Voyage runs every exchange; never state who hits or whether the rule cracks. A fight scene ends when Voyage's output shows it decided.

## When players leave the arc
Their choice wins: play the chosen party from its own agenda, never steer back. Ask what the planned contact was *for*; the new one supplies it on its own terms (price, motive). The skipped party keeps its clock and agenda, may return as rival or better offer. Clues only from the current ladder rung; milestones stay fixed, as the world acting. If the new party is thin: use only the world file (faction, lore, places), improvise a want, a price and one voice, record at once (`add-npc`, `agenda`, `fact`); if they stay, the Opus Planner fleshes it out in the background (voice cards, agenda, arc ties).

## Retcon (big derail: main NPC killed, secret blurted, player action decided for them)
Fix in the fiction first, in the next prompt (rumor, misunderstanding, staged). Ask the user before Voyage's regenerate/undo. Always record what the players saw, so the data never contradicts the table. Studio `story-fix` edits only the latest turn; older derails are fixed in the fiction.

## Studio (occasional)
Use Studio only at the moments in `docs/studio.md`, never every turn. Flag it in the reply ("Studio: ..."); draft with `studio-request` (`--edit` for existing ones; auto-batched to the limit); the user applies between beats (a `story-fix` at once); `studio-done` on confirmation. Never hidden secrets. Studio NPCs need no intro_line. All else stays prompts and the database.

## The update rule
Data changes **only when Voyage's story output establishes something** (NPC or quest appeared, quest started, fact, move, time), never from plans, guesses or hints. Every update needs `--turn N --evidence "quote or paraphrase"` (not ahead of the log). Arc NPCs and quests are `planned` until they appear, then `in_play`/`active`; main NPCs start `world`. `pos` refuses unknown places.

**Record what players may raise later** (`fact`/`npc-note`): promises, secrets shared, gifts, running gags, stated goals.

## Player-character sheets
`pronouns`, `power`, `background`, `notes`: from the user only, never invented. First chat: ask once with the README intake template (story facts only, no stats; Voyage keeps its sheet), then `pc-add` or `pc-sheet <name> --power "..." --evidence "sheet provided by the user"`.

## Secrecy, consent, romance
- **Secrets are director-only** (README "Arc reference"); one enters a prompt only in the scene that needs it. Hidden fields, ladders: never shown; villain sheets only as the Fights facts.
- **Romance** is optional, never pushed; Voyage follows the player. Only `romance_eligible` NPCs (README); any NPC can decline, ending it; beats are earned in the story.
<!-- generic:end -->

## World rules
<!-- fill: world export file name and act boundary days, one line (Class 2B: "World file: `New_World.json`. Act boundaries: end of Days 7, 42, 77.") -->
<!-- fill: Canon traps. Begin "Grow this list from `resume`'s repeat slips; record each as a fact.", then one bullet per trap (Class 2B: "Room numbers are door labels: `fact "room 4" "Room 4 = river-bedroom"`") -->
<!-- fill: Main NPCs: names, earned changes, fixed NPCs needing no intro_line, an overreach example, consent rules for scripted quests, tone rules for the hidden score if that module is on (Class 2B: "Tatsuya, Mio, Shin ... House Manager needs no intro_line") -->
