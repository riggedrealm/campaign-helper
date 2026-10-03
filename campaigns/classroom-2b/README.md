# Class 2B: Director Arc Bible

Director-side notes for a Voyage arc set at Chikara Academy and Sakura Lane Sharehouse. A human director reads these files and writes one short steering prompt per turn. Nothing here is meant to be pasted whole into Voyage, and `New_World.json` is never edited by this folder.

## Purpose

Class 2B is Chikara Academy's off-campus misfit experiment: eight first-years living together at Sakura Lane Sharehouse, with an end-of-semester review deciding whether the class is renewed or dissolved. The arc runs one semester (about 16 weeks), is built for 1 to 4 player characters, and assumes nothing about their powers or backgrounds. Day 1 is a Saturday (move-in); classes start Day 3 (Monday).

The arc is an even mix of school and house life, drama, and hero action. Every act has a showcase fight and puts one relationship under pressure.

## How the director workflow works

Voyage's AI narrates the game. Each turn the user pastes **one steering prompt, at most 700 characters** (hard limit, labels included). Lines, in order:

1. `Cut:` where and when the beat happens. Use explicit relocation or a time skip if moving; otherwise "Continue at ...".
2. `Tone:` optional.
3. `Crew:` what each present NPC wants or does. Key NPCs get one line matching their voice card (see `cast.md`).
4. `Facts:` optional. Facts at risk this turn.
5. `World:` always last. The world move, a surprise, and only the hidden facts this scene needs.

Rules of the format:

- **One beat per turn.**
- Voyage reads prompts literally. Never state player-character outcomes or combat outcomes; Voyage rolls combat itself. NPC actions and enemy rules may be stated.
- NPCs are passive, so every prompt needs a world move.
- Voyage keeps its own memory of records and quests. The director does not restate them.
- **New NPCs** are introduced by name plus a short visual line the first time they appear in a prompt (use the intro lines in `cast.md`, each 150 characters or fewer). Voyage then creates them.
- **Quests** are generated when a prompt tells Voyage to start one. Use the seed lines in `quests.md` inside the `World:` line.
- The world file already has one NPC used here: **Sakura Lane House Manager** (at Sakura Lane Sharehouse, building-entrance). She needs no intro line.
- **Turn 1 is not written by the director.** Voyage's existing "01 - Classroom 2B" story start produces the opening narration. The director steps in from turn 2.

Per-turn loop:

1. The user sends the story output and the player inputs.
2. The director reviews them, updates `ledger.md` (Standing) and `turn-log.md`, and updates agendas in `cast.md`.
3. The director writes the next prompt (one beat, with a world move) and checks its length:
   `python3 -c "print(len(open('prompt.txt').read().rstrip('\n')))"`
   If a counter treats the emoji in a position header as two characters, keep a 10-character margin.

Split scenes (player characters in different places) follow the protocol in `split-scenes.md`, including a compact `Cut:` form that fits the 700-character budget.

## File map

| File | What it holds |
|---|---|
| `README.md` | This file: purpose, workflow, file map, spoiler note |
| `arc-bible.md` | Premise, stakes, tone, four acts with beats, showcase fights with villain sheets, Nightshade paths, retest, personal quests, endings, time skips, obstacle and surprise lists |
| `cast.md` | Cast cards: visual line, personality, voice card, want, fear, agenda, relationships, intro line; plus supporting and fight NPCs |
| `quests.md` | Every arc quest with trigger, giver, location, objectives, outcomes, Standing effect, and a ready seed line for `World:` |
| `ledger.md` | Hidden 2B Standing rubric, current value, dated entry table, hint bands |
| `split-scenes.md` | The 7-rule split-scene protocol and 700-character header forms with counted examples |
| `turn-log.md` | Empty per-turn template |
| `opening.md` | Director-only scene card for the Day 1 move-in |

## Place names

Every location and area named in these files is an existing key in `New_World.json` (`locations`, and each location's `areas`). Places are written in backticks as `Location/area`. No place is invented; where the arc needs a venue the world lacks (a 2B homeroom, a Support lab), the closest existing area stands in and `arc-bible.md` says so.

## Spoiler note

The user designed this arc and knows the twist. Hidden facts still enter a prompt only in the scene that needs them: Mio's debt and fraud, Arimura's real assignment, Shimazu's reasons, Ayame's part in the scandal video, Yūto's history, and the 2B Standing number never appear in a prompt outside the scene that needs them. Standing is never shown as a meter; Voyage only sees it through NPC hints (Shimazu's warnings, Yūto's remarks). Quest titles and seed lines are written so they do not spoil.
