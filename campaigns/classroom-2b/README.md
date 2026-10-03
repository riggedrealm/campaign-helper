# Class 2B: Director Arc Bible

Director-side notes and database for a Voyage arc set at Chikara Academy and Sakura Lane Sharehouse. A human director reads these files and writes one short steering prompt per turn. Nothing here is meant to be pasted whole into Voyage.

## Purpose

Class 2B is Chikara Academy's off-campus misfit experiment: eight first-years living together at Sakura Lane Sharehouse, with an end-of-semester review deciding whether the class is renewed or dissolved. The arc runs one semester (about 16 weeks), is built for 1 to 4 player characters, and assumes nothing about their powers or backgrounds. Day 1 is a Saturday (move-in); classes start Day 3 (Monday).

The arc is an even mix of school and house life, drama, and hero action. Every act has a showcase fight and puts one relationship under pressure.

## The database is the source of truth

All facts the director needs live in `data/` (JSON) and are read and written only through `tools/db.py`.

- **Never read `New_World.json` during play.** It was copied into `data/` once (locations, factions, world NPCs, lore, story start, time and money rules, resources, relationship stages, NPC types, narrator style) and is not edited from this folder. The one exception: the eight main Class 2B NPCs (Tatsuya, Mio, Shin, Sunny, Arimura, Shimazu, Ayame, Yūto) were added to `New_World.json` (`npcs` and `worldVoices`) and mirrored into `data/world-npcs.json` and `data/cast.json`.
- **Locations are fixed; areas may be added.** Only locations and areas that exist in `data/locations.json` may be used. `db.py pos` refuses anything else, and `check-prompt` flags unknown names. New locations are never added. A new area inside an existing location is allowed once it appears in story output, and is recorded with `add-area` (see "DM principles: player-driven play").
- **Arc NPCs and quests are `planned` until they appear in Voyage's story output, then `in_play` (NPCs) or `active` (quests).** The eight main NPCs are the exception: they exist in `New_World.json`, so their status in `data/cast.json` starts at `world` (`npc-seen` still moves them to `in_play`). The other arc NPCs (villains, proctors, fill-ins) are not in the world file and stay `planned`.

### The update rule

World and arc data change **only when Voyage's story output establishes something**: an NPC Voyage generated, an NPC or quest that appeared, a quest started or finished, a new fact about a person or place, a move, a time change, a Standing change. Never from plans or guesses.

Every update command requires:

```
--turn N --evidence "short quote or paraphrase from the story output"
```

`--turn` is the turn whose output justified the change, and it cannot be ahead of the log. Each update is also appended to `changelog` in `data/state.json`, so every change can be traced to a turn and a quote. If the story output only hints at something, do not record it yet.

## How the prompt workflow works

Voyage's AI narrates the game. Each turn the director pastes **one steering prompt, at most 700 characters** (hard limit, labels included). Lines, in order:

1. `Cut:` where and when the beat happens. Use explicit relocation or a time skip if moving; otherwise "Continue at ...".
2. `Tone:` optional.
3. `Crew:` what each present NPC wants or does. Key NPCs get one line matching their voice card (`db.py brief <name>` for the main eight, `db.py npc <name>` for the rest).
4. `Facts:` optional. Facts at risk this turn, written as plain world truths (see "Writing `Facts:` lines" below).
5. `World:` always last. The world move, a surprise, and only the hidden facts this scene needs.

Rules of the format:

- **One beat per turn.**
- Voyage reads prompts literally. Never state player-character outcomes or combat outcomes; Voyage rolls combat itself. NPC actions and enemy rules may be stated.
- NPCs are passive, so every prompt needs a world move.
- Voyage keeps its own memory of records and quests. The director does not restate them.
- **New NPCs** that are not in the world file (villains, proctors, fill-ins; status `planned`) are introduced by name plus their `intro_line` (90 characters or fewer: name, age and the most visual details) the first time they appear in a prompt. Voyage then creates them. **Introduce at most one new NPC per turn.** If two housemates are due, the second waits for the next turn.
- **Quests** are generated when a prompt tells Voyage to start one. Use the `seed_line` (200 characters or fewer) inside the `World:` line.
- **World NPCs need no intro line.** The **Sakura Lane House Manager** (at Sakura Lane Sharehouse, building-entrance) and the eight main NPCs are already in `New_World.json`, so Voyage knows their look and voice; `check-prompt` never demands an intro line for an NPC with status `world`. The main NPCs' `intro_line` stays in `data/cast.json` as an optional anchor for a first appearance, and the one-new-NPC-per-turn pacing still applies.
- **The twists stay director-side.** `New_World.json` carries only what is public (look, public power rule, routine, public goal) and Act-1-safe behavior tells. Every secret (Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, Arimura's and Shimazu's Annex roles, Yūto's scar) lives only in `data/cast.json` (`hidden`), `data/threads.json`, `cast-bible.md` and `arc-bible.md`.
- **Turn 1 is not written by the director.** Voyage's existing "01 - Classroom 2B" story start produces the opening narration. The director steps in from turn 2.

### Writing `Facts:` lines

Voyage turns `Facts:` lines into dialogue ("one correction: ..."). So write each fact as a plain world truth, never as a "correction" or a "not X". If an in-scene fix is needed (someone has the wrong idea), put it in the speaking NPC's `Crew:` line instead, as something that NPC says or does.

- Bad: `Facts: Correction: Griffin's room is not the garden-bedroom. 2B is not a second-year class.`
- Good: `Facts: Griffin's room: river-bedroom. 2B is a first-year class.`
- In-scene fix, in the speaker's line: `Crew: Tatsuya gently points Griffin to the river-bedroom ("that one's yours").`

### Player character sheets

Each player character's sheet (`pronouns`, `power`, `background`, `notes`) **comes from the user**. The director never derives or fills it in from story output, and never invents a power or background. Ask the user, then record it with `pc-add` (`--pronouns --power --background --notes`) or later with `pc-sheet <name> --power "..."`. `pc-sheet <name>` with no options shows the full sheet; `state` prints it compactly under each player character. Use `--evidence "sheet provided by the user"`.

Split scenes (player characters in different places) follow the protocol in `split-scenes.md`, including a compact `Cut:` form that fits the 700-character budget.

## Director rules (from trial runs)

Lessons from trial runs. They apply to every prompt and every read of the story output.

1. **Player actions are the player's.** Narrate each player character's action exactly as the player gave it. The director decides only the results and consequences. Never offer the player a menu of actions to choose from, and never script what the character does, says, thinks or feels.
   - Example: the input is "i use kamehameha" on a barrier power. Narrate the attempt as stated; the result is that no beam comes out and a barrier flares, with a small Power Strain cost.
2. **Only the player moves their character.** NPCs may suggest going somewhere ("the courtyard has more room"), but the scene relocates a player character only when the player's input says so.
   - Example: Tatsuya says the courtyard has more room. The player character stays where they are until the player writes that they go.
3. **Over budget, cut on a quiet input.** When a scene has used its turn budget, the next quiet or downtime input (resting, drinking tea, settling in) gets a time skip to the next planned beat. Inputs that start something new keep normal pacing.
   - Example: the scene is over budget and the player writes "i sip my tea" → `Cut:` skips to the next planned beat. If the player writes "i follow Ayame out", pacing stays normal.
4. **Voyage's room numbers are door labels.** Voyage may call bedrooms by number (e.g. "room four", from a player's inventory key). Don't fight it. Record the mapping as a canon fact from story output and use the named area in prompts.
   - Example: the key reads "room four" and the story puts the player in the river bedroom. Record `fact "room 4" "Room 4 = river-bedroom"` with `--turn N --evidence "..."`, and write `river-bedroom` in later prompts.
5. **Main NPCs are real characters.** The eight main NPCs (Tatsuya, Mio, Shin, Sunny, Arimura, Shimazu, Ayame, Yūto) are people, not prompt furniture. Before writing any `Crew:` line for one of them, run `python3 tools/db.py brief <name>` and write the reaction from it.
   - **Psychology drives the reaction.** Use their want, need, fear, the lie they believe, and their stress, comfort and anger triggers. Their tells show when a trigger is hit.
   - **Their own voice.** Use the voice card: speech pattern, tics, catchphrase, how they swear or don't, and how they sound when sincere.
   - **They are people, not helpers.** They may refuse, disagree, be busy, have a bad day, or pursue their own want in the scene. They don't exist to serve the player characters.
   - **Growth on schedule.** Behavior matches their current act beat and the reveal ladder. Earned changes (Shin using first names, Tatsuya releasing his power, Mio confessing) happen only when the story has earned them; the brief's "won't do yet" line lists what is still off the table.
   - **Relationships color everything.** How they treat each player character and each other follows their bonds and history, plus any canon notes from play.
   - Hidden facts stay out of their dialogue unless the ladder step is revealed. Tells may hint.
   - Example: Shin at act 1 calls a housemate by surname, not first name, however well the scene goes.

## DM principles: player-driven play

The players steer; the arc is the weather. These principles sit on top of the director rules above.

- **Yes first.** Players may pursue anything: ventures (a bakery, a band, a channel), detours, personal goals. The director makes the world respond believably and pushes back only, as an in-fiction result, when something breaks power rules or canon or skips a hard-won moment. No approval gates and no caps on how many goals a player character can pursue.
- **Plan when they commit.** No cost tables, progress tracks or venture mechanics in advance. When a player commits, prep just enough for the next scene: who's involved, what's in the way, what's interesting.
- **The arc is pressure, not a script.** Arc clocks keep running (Nightshade deadline, midterm, Battle Test, Ayame's rivalry). If players are elsewhere, the arc finds them where they are. Beats may move, reshape or relocate; only the big milestones are fixed, as the world acting.
- **Weave, don't wall off.** Tie player projects into the cast (housemates helping, Sunny promoting on Pulse, Mio building gear). Never use an arc threat to punish a player project.
- **Let it grow.** If a player-driven thread becomes what the table loves, the director proposes to the user that it get its own arc, with a short direction sketch for approval.
- **What stays protected:** established canon, power rules, consent, the player-agency rules, and existing locations. **New areas inside existing locations are allowed** (e.g. a bakery corner in Nakano Residential Arcade), recorded once they appear in story output with `db.py add-area` (below).

Rules of thumb, not limits:

- Size side goals as errand, thread or storyline, for pacing only.
- A one-beat goal is just an action. A goal becomes a side quest when it needs more than one scene; its objectives are world-side steps toward the player's own stated goal, and its giver is the most involved NPC or the player character.
- Rule each player goal reasonable / partly / unreasonable, with costs or pushback shown in the fiction plus a one-line note to the user, never pausing play.
- Neglected threads go cold after about 7 in-game days and the world moves them on a step. Nothing earned is deleted.
- Player side quests may advance an arc thread by at most one step on its reveal ladder (see below), never past a milestone.
- Standing changes only through the existing rubric.
- Reuse existing NPCs first; new NPCs get intro lines and are recorded when they appear.
- Rewards are left to Voyage.

Side quests and ventures are recorded in the database only once they appear in story output. Add no new quest fields until a real case needs them.

### Reveal ladders (`data/threads.json`)

Each arc secret is a thread with an ordered list of steps: `{step, reveal, earliest_act, milestone_gate, status}`. A step is `hidden` until story output establishes it, then `revealed`. The ladder says what may become known and when; it is not a schedule. Threads: Mio's secret, Sunny's scandal video, Shin's old gang, Shimazu and the Annex Cohort, Arimura's broadcast failure, Ayame's guilt.

- `python3 tools/db.py thread` lists every ladder; `thread "<name>"` (fuzzy, e.g. `thread Mio`) shows the steps and the next revealable step for the current act and day.
- `python3 tools/db.py thread-reveal "<name>" <step> --turn N --evidence "..."` marks a step revealed. It **refuses** a step whose `earliest_act` is later than the current act, a step with earlier steps still hidden, and a step whose `milestone_gate` has not been confirmed (add `--gate-met` once the gate milestone has happened). `--force` overrides all of these and records the step as forced.
- **Current act.** `data/state.json` has an `act` field (1 to 4), derived from `day`: Act 1 is Days 1 to 7, Act 2 Days 8 to 42, Act 3 Days 43 to 77, Act 4 Day 78 onward. `db.py time` updates `act` whenever it sets the day, so never edit it by hand. `state` prints it next to the day, and `thread` uses it.

### Adding areas to existing locations

`python3 tools/db.py add-area "<location>" <area-id> --desc "..." --turn N --evidence "..." [--paths a,b]` adds an area to a location that already exists in `data/locations.json`; it refuses unknown locations and areas that already exist. The area is stored under that location with `added_turn` and `evidence` (and optional `paths` to existing areas), and the change is logged in the `state.json` changelog. `pos`, `loc` and `check-prompt` accept the area afterwards. Example: `add-area "Nakano Residential Arcade" bakery-corner --desc "A small bakery corner between the grocery row and family dining." --turn 12 --evidence "..."`.

## Per-turn workflow with `db.py`

Run everything from `campaigns/classroom-2b`. Turn numbers are Voyage turns: turn 1 is the story start (no director prompt); the prompt you write after reading turn N's output is logged as turn N+1.

1. **Review the story output.** The user sends the story output for turn N and the player inputs. Read them against `python3 tools/db.py state`.
2. **Record what the output established**, each with `--turn N --evidence "..."`:
   - New or newly seen people: `add-npc` (Voyage generated someone not in the cast), `npc-seen` (a planned or world NPC appeared), `npc-note` (a new fact about an NPC), `agenda` (rewrite want and next move).
   - Quests: `quest-start`, `quest-obj`, `quest-end`.
   - Facts about places or anything else not covered above: `fact "<subject>" "<text>"`. Track the open flags the same way with subjects such as `flag: mio_confessed` (see the ledger notes in `data/ledger.json`).
   - Where everyone is: `pc-add` (once per player character; the sheet fields come from the user, see above), `pos <pc> <location> <area> --activity "..."` (refuses unknown places and sets `party_split` automatically), `pos ... --placement Strike` after the tournament.
   - Time: `time --day D --block <block> --clock HH:MM` (weekday is recomputed; Day 1 is Saturday). Deadlines and waiting: `clock-add` / `clock-done`.
   - Standing: `ledger +N|-N "reason"`.
3. **Brief the cast.** For each main NPC present in the scene, run `python3 tools/db.py brief <name>` before drafting the prompt (see "Main NPCs are real characters").
4. **Draft the next prompt** (one beat, with a world move) into a file, using `db.py npc`, `quest`, `loc` and `lore` for lookups.
5. **Check it:** `python3 tools/db.py check-prompt prompt.txt`
   - fails if it is over 700 characters (prints the count; keep a 10-character margin if a counter treats the emoji in a position header as two);
   - flags any capitalized name or phrase that is not a known location, area, NPC, faction, quest or player character (exit code 2); text inside quotation marks (`"..."`, `“...”`, `'...'` used as quotes, `‘...’`) is spoken or quoted words and is skipped for this check, so put names that matter outside the quotes;
   - warns if the party is split and the prompt has no 📍 header;
   - warns if a `planned` NPC or quest appears without its `intro_line` or `seed_line` (NPCs with status `world`, including the eight main NPCs, are never asked for one).
6. **Log the turn** once the prompt is final:
   `python3 tools/db.py turn N+1 --inputs "<story output summary and player inputs>" --prompt @prompt.txt --slips "<Voyage slips to correct>" --notes "<beat, world move, surprise, hidden facts used>"`
   Log turn 1 first, with `--prompt none`, when the story start arrives. Turns must be logged in order.

`slips` means mistakes Voyage made in the output you just reviewed (a teleported player character, a stated player outcome, a broken split protocol, an invented place) that the new prompt corrects.

## `db.py` commands

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `brief <name>` (read-only character card for writing a turn), `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `state`, `canon <search>`, `thread [name]` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start`, `quest-obj <name> <obj_id> <status>`, `quest-end <name> completed\|failed` |
| State updates | `ledger`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done`, `turn` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Check | `check-prompt <file or ->` |

Run `python3 tools/db.py <command> -h` for options. Fuzzy matching handles accents and partial names (`npc omine`, `loc "Sakura Lane"`). Set `CLASS2B_DATA=/path/to/copy` to try commands against a copy of `data/` without touching the real files.

## File map

| File | What it holds |
|---|---|
| `README.md` | This file: purpose, rules, per-turn workflow, file map, spoiler note |
| `data/state.json` | Turn, day, act (follows the day), weekday, time block and clock, player characters (user-provided sheets and positions), `party_split`, open clocks, introduced NPCs, active quests, milestone calendar, hidden debt, changelog |
| `data/cast.json` | Every arc NPC: main cast, villains and their rule sheets, supporting and partners (status `planned` / `in_play` / `world`; the eight main NPCs start as `world`), intro lines, voice cards, want / need / fear, the bible fields for the eight main NPCs (`lie`, `stress`, `comfort`, `anger`, `laughs`, `cries`, `newcomer_stance`, `trust_earned_by`, and `wont_do_yet` per act), agendas, relationships, hidden secrets, portrait prompts, palettes, signature moves, arc beats, endings, quotes, canon notes |
| `data/quests.json` | All 12 arc quests with objectives (status `pending`, `active`, `hidden`, `done`, `failed` or `skipped`), outcomes, Standing effect, reward, seed line, status and log |
| `data/ledger.json` | Hidden 2B Standing: start, current, thresholds, rubric, hint bands, dated entries |
| `data/canon.json` | Facts established in play that are not in any other file |
| `data/threads.json` | Reveal ladders for the six arc secrets: the NPCs each is tied to (`npcs`), steps with `reveal`, `earliest_act`, `milestone_gate`, `status` (director only) |
| `data/turns.json` | Turn log: day, time, inputs, prompt, slips, notes |
| `data/locations.json` | All 238 world locations with their areas and paths (locations are fixed; areas added from story output carry `added_turn` and `evidence`) |
| `data/factions.json` | All 13 factions |
| `data/world-npcs.json` | The 38 world NPCs (status `world`): the 30 original ones plus the eight main Class 2B NPCs added to the world file |
| `data/lore.json` | All world lore entries, `{key: text}` |
| `data/world.json` | The Classroom 2B story start, time blocks, train hours and currency, resource settings, relationship stages, NPC types, narrator style |
| `tools/db.py` | The database tool (Python 3 standard library only) |
| `arc-bible.md` | Narrative design: premise, stakes, tone, four acts with beats, showcase fights, Nightshade paths, retest, personal quests, endings, time skips, obstacle and surprise lists, scene turn budgets |
| `opening.md` | Director-only scene card for the Day 1 move-in |
| `split-scenes.md` | The 7-rule split-scene protocol and 700-character header forms with counted examples |
| `cast-bible.md` | The approved main-cast character bible (identity, origin, power, psychology, voice, daily life, combat, bonds, arc, secret ladders, endings, quotes). Director-only: it holds every secret |
| `cast-visuals.md` | The approved visual identity sheet (silhouette, palette, hair and eyes, accessories, looks, power effects, portrait prompts, 90-character intro lines) |
| `cast.md` | Pointer to `data/cast.json` plus the card-use, room and romance/consent guidance |
| `quests.md` | Pointer to `data/quests.json` plus the rules for quests in prompts |
| `ledger.md` | Pointer to `data/ledger.json` plus the hidden-Standing rule |

## Place names

Every location and area named in these files and in `data/` is an existing key in `data/locations.json`. Places are written as `Location/area`. No location is invented, and an area exists only if it was in the world file or was added with `add-area` from story output; where the arc needs a venue the world lacks (a 2B homeroom, a Support lab), the closest existing area stands in and `arc-bible.md` says so.

## Spoiler note

The user designed this arc and knows the twist. Hidden facts still enter a prompt only in the scene that needs them: Mio's debt, rig and fraud, Arimura's real assignment and the Annex exercise he left early, Shimazu's barrier wording and reasons, Ayame's part in the scandal video and who leaked it, Yūto's history and scar, the Nine Corners' revenge plan over Daiki, and the 2B Standing number never appear in a prompt outside the scene that needs them. Standing is never shown as a meter; Voyage only sees it through NPC hints (Shimazu's warnings, Yūto's remarks). Quest titles and seed lines are written so they do not spoil. The `hidden` fields, `villain_sheet`s, ledger, debt and reveal ladders (`threads.json`) in `data/` are director-only.
