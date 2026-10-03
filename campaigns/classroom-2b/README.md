# Class 2B: Reference

Director database for a Voyage arc at Chikara Academy and Sakura Lane Sharehouse: eight first-years in an off-campus misfit experiment, with an end-of-semester review deciding renewed or dissolved.
The director writes one steering prompt (700 characters or fewer) per turn; nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/class2b-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop). This file is only a reference.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 campaigns/classroom-2b/tools/db.py <command>`. Never read `New_World.json` during play. `cast-bible.md` and `cast-visuals.md` (in `docs/`) are human reference only; during play use `db.py brief` and `db.py npc`.

## File map (`campaigns/classroom-2b/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `arc-bible.md` | Premise, hidden state, four acts, showcase fights, Nightshade paths, retest, personal quests, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the Day 1 move-in |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/cast-bible.md`, `docs/cast-visuals.md` | Main-cast bible (all secrets) and visual sheet. Human reference only |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene`, open clocks, introduced NPCs, active quests, milestone calendar, debt, changelog |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The 12 arc quests: objectives, outcomes, Standing effect, seed lines, status |
| `data/ledger.json` | Hidden 2B Standing: current value, thresholds, rubric, hint bands, entries |
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the six arc secrets (director only) |
| `data/turns.json` | Turn log: day, time, inputs, summary, prompt, slips, notes |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | World files copied from `New_World.json` once; locations are fixed, areas may be added |
| `tools/db.py` | The database tool (Python 3 standard library only) |

## `db.py` commands

Run `db.py <command> -h` for options. Fuzzy matching handles accents and partial names. `CLASS2B_DATA=/path/to/copy` runs against a copy of `data/`.

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `brief <name>`, `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `canon <search>`, `thread [name]`, `state`, `resume`, `bible [section]` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start`, `quest-obj <name> <obj_id> <status>`, `quest-end <name> completed\|failed` |
| State updates | `ledger`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Scenes | `scene-start <name> --budget N` (needs `--turn`/`--evidence`; `--location`/`--area` default to the first player character), `scene-obstacle <text>`, `scene-surprise`, `scene-end` |
| Log, check, save | `turn N+1 --inputs --summary --prompt --slips --notes` (`--summary` required, two lines), `check-prompt <file or ->`, `save` |

- `resume`: start-of-chat summary (state header, scene, last 3 turns, clocks, next milestones, quests, main NPC beats, revealed ladder steps).
- `bible`: no argument lists headings with numbers; `bible 6`, `bible act3` or `bible retest` prints only that section.
- `turn` adds 1 to the open scene's `turns_used`; `state` and `resume` show `scene X: used/budget turns, obstacles, surprise` and warn when over budget.

## Save procedure

All real-play saves go to `main` of riggedrealm/campaign-helper (the save slot); the user has authorized pushing them there.

1. Start of chat: attach the repo, `git checkout main && git pull`. If `campaigns/classroom-2b/` is missing on `main` (PR #1 not merged), use branch `claude/keen-meitner-3u6hyt` instead and tell the user.
2. After every real turn: `db.py save`. It checks that every `data/*.json` parses, commits `campaigns/classroom-2b/data` as `Class 2B save: turn N`, and pushes with retries. By hand: `git add campaigns/classroom-2b/data && git commit -m "Class 2B save: turn N" && git push origin main`.
3. `save` refuses with `--trial` or `CLASS2B_TRIAL=1` (and when `CLASS2B_DATA` is set). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The user designed this arc and knows the twist. The `hidden` fields, villain sheets, ledger, debt and reveal ladders in `data/` are director-only; the 2B Standing number is never shown as a meter.
