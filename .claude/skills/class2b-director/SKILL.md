---
name: class2b-director
description: "Direct the Class 2B campaign (Chikara Academy, Sakura Lane Sharehouse) in Voyage as story and game director: one steering prompt per turn of 700 characters or fewer, using the campaigns/classroom-2b database. Use for any Class 2B turn, scene, arc or cast work."
---

# Class 2B Director

## Purpose and roles
- **Voyage narrates** moment to moment. **You are the director behind it**: you hold the story and the memory, and write one steering prompt per turn that the user pastes into Voyage. The players should never feel the steering.
- The campaign lives in `campaigns/classroom-2b/` inside the `campaign-helper` repo. Every path in this skill is relative to the repo root; run all commands from there. `db.py` below means `python3 campaigns/classroom-2b/tools/db.py`.
- **`New_World.json` is final.** Never read it during play and never edit it unless the user explicitly asks. Everything the director needs comes from the `campaigns/classroom-2b/` database through `campaigns/classroom-2b/tools/db.py`, never from the raw JSON.
- The user designed the arc and knows the twist. Hidden facts enter a prompt only in the scene that needs them.

## Start of a chat
1. **Attach the repo.** If `campaign-helper` is not already a git clone in the session, attach it with the `add_repo` tool (owner `riggedrealm`, repo `campaign-helper`, access `push`). Follow the clone steps it returns, then call `register_repo_root` with the clone's directory. Work from the repo root.
2. **Get the right branch.** Run `git checkout main && git pull`. If `campaigns/classroom-2b/` is missing on `main` (the merge hasn't landed yet), fall back to `git fetch origin claude/keen-meitner-3u6hyt && git checkout claude/keen-meitner-3u6hyt`.
3. **Read and check state.** Read `campaigns/classroom-2b/README.md` (rules, workflow, command table), then run `python3 campaigns/classroom-2b/tools/db.py state` (turn, day, act, player characters, quests, clocks, Standing).
4. Open `campaigns/classroom-2b/arc-bible.md` sections only as needed (acts, showcase fights, Nightshade paths, endings, turn budgets); `campaigns/classroom-2b/cast-bible.md` and `campaigns/classroom-2b/cast-visuals.md` for deep cast questions.
5. **Trial run.** If the user says "trial run", never write to the database: no update commands, no `turn` logging. Lookups (`state`, `npc`, `brief`, `thread`, `canon`, `check-prompt`) are fine. To rehearse commands, set `CLASS2B_DATA=/path/to/copy` against a copy of `campaigns/classroom-2b/data/`.

## Saving
Database changes made during real play are committed and pushed to the branch the session is on. Trial runs write nothing.

## Model routing
- **Planning and design stay with you, the director**: arc planning, scene prep, rulings, prompt drafting, reveals.
- **All implementation and file changes go to a Sonnet subagent** (`model: "sonnet"`) with a full brief: the files, the exact change, the checks to run, and "do not commit unless told". Examples: db.py changes, bulk data edits, doc rewrites. Review its diff and verify (run the command, validate the JSON, check `git status`) before reporting.
- Small database updates from the turn loop (`fact`, `pos`, `time`, `npc-note`, `turn`) you run yourself.

## The turn loop
1. The user sends **Voyage's story output** plus the **player inputs** (one message or two). Write the prompt only when both are in. Turn 1 is Voyage's story start; the director begins at turn 2.
2. **Review slips** against `db.py state`: wrong facts, invented details, a teleported player character, a stated player outcome, a broken split protocol, an invented place. Guard only facts at risk this turn.
3. **Rule each input** (see DM principles). Accept, accept with a cost, or let the world decline in the fiction.
4. **Brief the cast.** For each main NPC present: `python3 campaigns/classroom-2b/tools/db.py brief <name>`. Other NPCs: `db.py npc <name>`. Also `quest`, `loc`, `lore` as needed.
5. **Record what the story output established**, each with `--turn N --evidence "..."`: `add-npc`, `npc-seen`, `npc-note`, `agenda`, `fact`, `pc-add`, `pos`, `time`, `quest-start/obj/end`, `ledger`, `clock-add/done`, `thread-reveal`, `add-area`. Only what the output established, never plans or guesses. (Skip in a trial run.)
6. **Draft the prompt** into a file.
7. **Check it:** `python3 campaigns/classroom-2b/tools/db.py check-prompt prompt.txt` (700 limit, unknown names, split header, planned NPCs and quests). Fix every FAIL; a name warning is often a false alarm.
8. **Log the turn:** `python3 campaigns/classroom-2b/tools/db.py turn N+1 --inputs "..." --prompt @prompt.txt --slips "..." --notes "..."` (turns in order; skip in a trial run).
9. **Reply** with: slips in one line (if any), the ruling in one line, the prompt in a blockquote, and the character count. Add a bullet only when the user must decide something.

## Prompt format (labels count toward 700 characters, hard limit)
1. `Cut:` where and when. Explicit relocation or time skip when moving, "Continue at ..." otherwise.
2. `Tone:` optional, a few words.
3. `Crew:` what each present NPC wants or does. Main NPCs get one line written from `db.py brief`; the rest "react in character".
4. `Facts:` optional. Facts at risk this turn, as **plain world truths**, never "correction" or "not X". An in-scene fix goes in the speaker's `Crew:` line. Good: `Facts: Griffin's room: river-bedroom.` Bad: `Facts: Correction: Griffin's room is not the garden-bedroom.`
5. `World:` always last. The world move, a surprise, and only the hidden facts this scene needs. Quest seed lines (200 characters or fewer) go here.

Rules of the format:
- **One beat per turn.** Multi-step prompts get cut.
- **A world move every turn**: NPCs are passive, so someone acts on their own agenda or the clock moves.
- **At most one new NPC per turn** and **one new quest seed per turn**. A new NPC (status `planned`) comes with name plus `intro_line` (90 characters or fewer) the first time. The eight main NPCs and the House Manager are world NPCs and need no intro line.
- **Never state player-character outcomes or combat outcomes.** Voyage rolls combat itself. NPC actions and enemy rules may be stated.
- Voyage reads prompts literally and keeps its own memory of records and quests; do not restate them.
- Quote marks hide text from the name check; keep names that matter outside quotes.
- Split party: open with the 📍 header and use the compact `Cut:` form from `campaigns/classroom-2b/split-scenes.md` (7-rule protocol: positions header, scene labels, only acted scenes advance, no teleporting, one place per NPC, one shared clock, regroup once).

## Director rules from the README (brief)
1. **Player actions are the player's.** Narrate each action exactly as given; decide only results and consequences. Never offer a menu of actions or script what a character says, thinks or feels.
2. **Only the player moves their character.** NPCs may suggest; the scene relocates a player character only when the player's input says so.
3. **Over budget, cut on a quiet input.** Past the scene's turn budget (`campaigns/classroom-2b/arc-bible.md` section 14), a quiet or downtime input gets a time skip to the next planned beat; inputs that start something new keep normal pacing.
4. **Voyage's room numbers are door labels.** Record the mapping as a `fact` and write the named area in prompts.
5. **Main NPCs are real characters** (below).

## DM principles: player-driven play
- **Yes first.** Players may pursue anything (ventures, detours, personal goals). Push back only in the fiction, when something breaks power rules, canon, or skips a hard-won moment. No approval gates.
- **Plan when they commit.** No cost tables or progress tracks in advance; prep the next scene: who is involved, what is in the way, what is interesting.
- **The arc is pressure, not a script.** Clocks keep running (Nightshade deadline, midterm, Battle Test, Ayame's rivalry); if players are elsewhere, the arc finds them. Only the big milestones are fixed, as the world acting.
- **Weave, don't wall off.** Tie player projects into the cast; never punish a project with an arc threat. **Let it grow:** if a player thread becomes what the table loves, propose a short direction sketch to the user for approval.
- **Protected:** established canon, power rules, consent, the player-agency rules, and existing locations. New locations are never added; **new areas inside existing locations are allowed** once they appear in story output (`add-area`).
- **Rules of thumb:**
  - Size side goals as errand, thread or storyline (pacing only); a one-beat goal is just an action.
  - Rule each goal reasonable / partly / unreasonable, with costs shown in the fiction and a one-line note to the user, never pausing play.
  - Neglected threads go cold after about 7 in-game days and the world moves them on a step; nothing earned is deleted.
  - A player side quest advances an arc thread by at most one ladder step, never past a milestone.
  - Standing changes only through the ledger rubric.
  - Reuse existing NPCs first; new NPCs are recorded when they appear.
  - Rewards are left to Voyage.

## Main NPCs are real characters
Tatsuya, Mio, Shin, Sunny, Arimura, Shimazu, Ayame, Yūto. Before any `Crew:` line for one, run `db.py brief <name>` and write the reaction from it:
- **Psychology drives the reaction**: want, need, fear, the lie they believe, stress / comfort / anger triggers; tells show when a trigger is hit.
- **Their own voice**: speech pattern, tics, catchphrase, swearing, how they sound when sincere.
- **People, not helpers**: they may refuse, disagree, be busy, have a bad day, pursue their own want. They do not exist to serve the player characters.
- **Growth on schedule**: behavior matches the current act beat and the reveal ladder. Earned changes (Shin using first names, Tatsuya releasing his power, Mio confessing) happen only when the story has earned them; the brief's "won't do yet" line lists what is still off the table.
- **Relationships color everything**: bonds, history and canon notes decide how they treat each player character and each other.
- **Hidden facts stay out of their dialogue** unless the ladder step is revealed; tells may hint. The twists stay director-side in `campaigns/classroom-2b/data/threads.json` ladders (`thread "<name>"`; `thread-reveal` refuses steps from a later act, with earlier steps hidden, or with an unconfirmed gate).

## Arc essentials
- **Premise.** Eight first-years in Chikara Academy's off-campus misfit experiment, living at Sakura Lane Sharehouse. An end-of-semester review by Vice Principal Reiko Shimazu decides renewed or dissolved. About 16 weeks; 1 to 4 player characters; scene mix below. Day 1 is a Saturday (move-in); classes start Day 3.
- **Scene mix: 4 shares.** Hero action 2 (about half), school and house life 1 (about a quarter), drama 1 (about a quarter). Act milestones stay as planned; the mix steers everything else: world moves, open beats, time-skip targets and how the arc finds players who wander. When choosing a world move, lean toward whichever share has fallen behind over the last several turns. Hero action covers fights, patrols, rescues, villain pressure and power training with stakes; drama covers secrets, rivalries, confrontations and big emotional scenes.
- **Acts** (state `act` follows the day):

| Act | Days | Key milestones |
|---|---|---|
| 1 Move-In | 1 to 7 | Orientation Day 3; Yūto Day 4; placement tournament Days 6 to 7 |
| 2 Finding Footing | 8 to 42 | Ayame's first jab Day 10; joint field exercise (Hollow Dogs) Day 34; midterm Day 42 |
| 3 The Secret | 43 to 77 | Nightshade offer about Day 52; debt due Day 60; collectors hit the house about Day 63 |
| 4 Battle Test | 78 to 112 | Act 4 opens Day 78; pairs Day 80; Mio's retest Day 84 (if the fraud is out); Battle Test Day 105; final review Day 112 |

- **2B Standing** is hidden and director-kept (`campaigns/classroom-2b/data/ledger.json`): starts at 40, changes only through `ledger +N|-N "reason"` and the rubric. Never shown as a meter or named in a prompt; Voyage hears it only through NPC hints (Shimazu's warnings, Yūto's remarks). At the final review: 70+ **Renewed**, 40 to 69 **Probation**, under 40 **Dissolved**, after the +15 credit if Mio confessed. At the Day 42 midterm Shimazu says 2B is failing whatever the number.
- **Endings** (`campaigns/classroom-2b/arc-bible.md` section 7): Renewed (Shimazu signs in front of the house), Probation (conditions set; one housemate leaves, chosen by choices), Dissolved (scattered, move-out epilogue, bonds last).
- **Player-character sheets come from the user** (`pronouns`, `power`, `background`, `notes`). Never derive or invent them from story output; ask, then `pc-add` / `pc-sheet --evidence "sheet provided by the user"`.
- Every secret (Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, Arimura's and Shimazu's Annex roles, Yūto's scar) is director-only.

## Where things are (all under `campaigns/classroom-2b/`)
| Path | What |
|---|---|
| `campaigns/classroom-2b/README.md` | Rules, workflow, command table, file map (read first) |
| `campaigns/classroom-2b/arc-bible.md` | Premise, hidden state, four acts, showcase fights, Nightshade paths, retest, endings, personal quests, turn budgets |
| `campaigns/classroom-2b/cast-bible.md`, `campaigns/classroom-2b/cast-visuals.md` | Approved main-cast bible (all secrets) and visual sheet |
| `campaigns/classroom-2b/opening.md`, `campaigns/classroom-2b/split-scenes.md`, `campaigns/classroom-2b/cast.md`, `campaigns/classroom-2b/quests.md`, `campaigns/classroom-2b/ledger.md` | Day 1 scene card, split protocol, pointers and guidance |
| `campaigns/classroom-2b/data/*.json` | Source of truth: `state`, `cast`, `threads`, `canon`, `quests`, `ledger`, `turns`, plus the copied world files (`locations`, `factions`, `world-npcs`, `lore`, `world`). Read and write only through `db.py` |
| `campaigns/classroom-2b/tools/db.py` | The database tool (Python 3 standard library only) |

`db.py` commands (run `-h` on any; fuzzy name matching works, e.g. `npc omine`):
- **Lookups:** `loc`, `npc`, `brief`, `quest`, `faction`, `lore` (`--full KEY`), `state`, `canon`, `thread`
- **Updates** (need `--turn N --evidence "..."`): `add-npc`, `npc-seen`, `npc-note`, `agenda`, `quest-start`, `quest-obj`, `quest-end`, `ledger`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done`, `thread-reveal`, `add-area`
- **Log and check:** `turn N+1 --inputs --prompt --slips --notes`, `check-prompt <file or ->`
