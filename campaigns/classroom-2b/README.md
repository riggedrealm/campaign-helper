# Class 2B: Director Arc Bible

Director-side notes and database for a Voyage arc set at Chikara Academy and Sakura Lane Sharehouse. A human director reads these files and writes one short steering prompt per turn. Nothing here is meant to be pasted whole into Voyage.

## Purpose

Class 2B is Chikara Academy's off-campus misfit experiment: eight first-years living together at Sakura Lane Sharehouse, with an end-of-semester review deciding whether the class is renewed or dissolved. The arc runs one semester (about 16 weeks), is built for 1 to 4 player characters, and assumes nothing about their powers or backgrounds. Day 1 is a Saturday (move-in); classes start Day 3 (Monday).

The arc is an even mix of school and house life, drama, and hero action. Every act has a showcase fight and puts one relationship under pressure.

## The database is the source of truth

All facts the director needs live in `data/` (JSON) and are read and written only through `tools/db.py`.

- **Never read `New_World.json` during play.** It was copied into `data/` once (locations, factions, world NPCs, lore, story start, time and money rules, resources, relationship stages, NPC types, narrator style) and is never edited by this folder.
- **Locations are fixed.** Only locations and areas that exist in `data/locations.json` may be used. `db.py pos` refuses anything else, and `check-prompt` flags unknown names.
- **Arc NPCs and quests are `planned` until they appear in Voyage's story output, then `in_play` (NPCs) or `active` (quests).**

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
3. `Crew:` what each present NPC wants or does. Key NPCs get one line matching their voice card (`db.py npc <name>`).
4. `Facts:` optional. Facts at risk this turn.
5. `World:` always last. The world move, a surprise, and only the hidden facts this scene needs.

Rules of the format:

- **One beat per turn.**
- Voyage reads prompts literally. Never state player-character outcomes or combat outcomes; Voyage rolls combat itself. NPC actions and enemy rules may be stated.
- NPCs are passive, so every prompt needs a world move.
- Voyage keeps its own memory of records and quests. The director does not restate them.
- **New NPCs** are introduced by name plus their `intro_line` (150 characters or fewer) the first time they appear in a prompt. Voyage then creates them.
- **Quests** are generated when a prompt tells Voyage to start one. Use the `seed_line` (200 characters or fewer) inside the `World:` line.
- The world file already has one NPC used here: **Sakura Lane House Manager** (at Sakura Lane Sharehouse, building-entrance). She needs no intro line.
- **Turn 1 is not written by the director.** Voyage's existing "01 - Classroom 2B" story start produces the opening narration. The director steps in from turn 2.

Split scenes (player characters in different places) follow the protocol in `split-scenes.md`, including a compact `Cut:` form that fits the 700-character budget.

## Per-turn workflow with `db.py`

Run everything from `campaigns/classroom-2b`. Turn numbers are Voyage turns: turn 1 is the story start (no director prompt); the prompt you write after reading turn N's output is logged as turn N+1.

1. **Review the story output.** The user sends the story output for turn N and the player inputs. Read them against `python3 tools/db.py state`.
2. **Record what the output established**, each with `--turn N --evidence "..."`:
   - New or newly seen people: `add-npc` (Voyage generated someone not in the cast), `npc-seen` (a planned or world NPC appeared), `npc-note` (a new fact about an NPC), `agenda` (rewrite want and next move).
   - Quests: `quest-start`, `quest-obj`, `quest-end`.
   - Facts about places or anything else not covered above: `fact "<subject>" "<text>"`. Track the open flags the same way with subjects such as `flag: mio_confessed` (see the ledger notes in `data/ledger.json`).
   - Where everyone is: `pc-add` (once per player character), `pos <pc> <location> <area> --activity "..."` (refuses unknown places and sets `party_split` automatically), `pos ... --placement Strike` after the tournament.
   - Time: `time --day D --block <block> --clock HH:MM` (weekday is recomputed; Day 1 is Saturday). Deadlines and waiting: `clock-add` / `clock-done`.
   - Standing: `ledger +N|-N "reason"`.
3. **Draft the next prompt** (one beat, with a world move) into a file, using `db.py npc`, `quest`, `loc` and `lore` for lookups.
4. **Check it:** `python3 tools/db.py check-prompt prompt.txt`
   - fails if it is over 700 characters (prints the count; keep a 10-character margin if a counter treats the emoji in a position header as two);
   - flags any capitalized name or phrase that is not a known location, area, NPC, faction, quest or player character (exit code 2);
   - warns if the party is split and the prompt has no 📍 header;
   - warns if a `planned` NPC or quest appears without its `intro_line` or `seed_line`.
5. **Log the turn** once the prompt is final:
   `python3 tools/db.py turn N+1 --inputs "<story output summary and player inputs>" --prompt @prompt.txt --slips "<Voyage slips to correct>" --notes "<beat, world move, surprise, hidden facts used>"`
   Log turn 1 first, with `--prompt none`, when the story start arrives. Turns must be logged in order.

`slips` means mistakes Voyage made in the output you just reviewed (a teleported player character, a stated player outcome, a broken split protocol, an invented place) that the new prompt corrects.

## `db.py` commands

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `state`, `canon <search>` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start`, `quest-obj <name> <obj_id> <status>`, `quest-end <name> completed\|failed` |
| State updates | `ledger`, `fact`, `pc-add`, `pos`, `time`, `clock-add`, `clock-done`, `turn` |
| Check | `check-prompt <file or ->` |

Run `python3 tools/db.py <command> -h` for options. Fuzzy matching handles accents and partial names (`npc omine`, `loc "Sakura Lane"`). Set `CLASS2B_DATA=/path/to/copy` to try commands against a copy of `data/` without touching the real files.

## File map

| File | What it holds |
|---|---|
| `README.md` | This file: purpose, rules, per-turn workflow, file map, spoiler note |
| `data/state.json` | Turn, day, weekday, time block and clock, player characters and positions, `party_split`, open clocks, introduced NPCs, active quests, milestone calendar, hidden debt, changelog |
| `data/cast.json` | Every arc NPC: main cast, villains and their rule sheets, supporting and partners (status `planned` / `in_play` / `world`), intro lines, voice cards, agendas, relationships, canon notes |
| `data/quests.json` | All 11 arc quests with objectives, outcomes, Standing effect, seed line, status and log |
| `data/ledger.json` | Hidden 2B Standing: start, current, thresholds, rubric, hint bands, dated entries |
| `data/canon.json` | Facts established in play that are not in any other file |
| `data/turns.json` | Turn log: day, time, inputs, prompt, slips, notes |
| `data/locations.json` | All 238 world locations with their areas and paths (the fixed map) |
| `data/factions.json` | All 13 factions |
| `data/world-npcs.json` | The 30 existing world NPCs (status `world`) |
| `data/lore.json` | All world lore entries, `{key: text}` |
| `data/world.json` | The Classroom 2B story start, time blocks, train hours and currency, resource settings, relationship stages, NPC types, narrator style |
| `tools/db.py` | The database tool (Python 3 standard library only) |
| `arc-bible.md` | Narrative design: premise, stakes, tone, four acts with beats, showcase fights, Nightshade paths, retest, personal quests, endings, time skips, obstacle and surprise lists |
| `opening.md` | Director-only scene card for the Day 1 move-in |
| `split-scenes.md` | The 7-rule split-scene protocol and 700-character header forms with counted examples |
| `cast.md` | Pointer to `data/cast.json` plus the card-use, room and romance/consent guidance |
| `quests.md` | Pointer to `data/quests.json` plus the rules for quests in prompts |
| `ledger.md` | Pointer to `data/ledger.json` plus the hidden-Standing rule |

## Place names

Every location and area named in these files and in `data/` is an existing key in `data/locations.json`. Places are written as `Location/area`. No place is invented; where the arc needs a venue the world lacks (a 2B homeroom, a Support lab), the closest existing area stands in and `arc-bible.md` says so.

## Spoiler note

The user designed this arc and knows the twist. Hidden facts still enter a prompt only in the scene that needs them: Mio's debt and fraud, Arimura's real assignment, Shimazu's reasons, Ayame's part in the scandal video, Yūto's history, and the 2B Standing number never appear in a prompt outside the scene that needs them. Standing is never shown as a meter; Voyage only sees it through NPC hints (Shimazu's warnings, Yūto's remarks). Quest titles and seed lines are written so they do not spoil. The `hidden` fields, `villain_sheet`s, ledger and debt in `data/` are director-only.
