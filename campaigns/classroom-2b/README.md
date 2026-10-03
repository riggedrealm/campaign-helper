# Class 2B: Reference

Director database for a Voyage arc at Chikara Academy and Sakura Lane Sharehouse: eight first-years in an off-campus misfit experiment; an end-of-semester review decides renewed or dissolved.
The director writes one steering prompt per turn within the prompt limit (840 characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/class2b-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 campaigns/classroom-2b/tools/db.py <command>`. Never read `New_World.json` during play. `cast-bible.md` and `cast-visuals.md` (in `docs/`) are human reference only; during play use `db.py brief` and `db.py npc`.

## File map (`campaigns/classroom-2b/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `arc-bible.md` | Premise, hidden state, four acts, showcase fights, Nightshade paths, retest, personal quests, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the Day 1 move-in |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `record` payload schema and example, Planner and Cast brief templates, failure playbook |
| `docs/cast-bible.md`, `docs/cast-visuals.md` | Main-cast bible (all secrets) and visual sheet. Human reference only |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), open clocks, introduced NPCs, active quests, milestone calendar, debt, changelog, `settings.prompt_limit` (840) |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The 12 arc quests: objectives, outcomes, Standing effect, seed lines, status |
| `data/ledger.json` | Hidden 2B Standing: current value, thresholds, rubric, hint bands, entries |
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the six arc secrets (director only) |
| `data/turns.json` | Turn log: day, time, inputs, summary, prompt, slips, notes |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | World files copied from `New_World.json` once; locations are fixed, areas may be added |
| `data/.snapshots/`, `data/.lock` | Last 5 pre-turn snapshots and the write lock (git-ignored) |
| `tools/db.py` | The database tool (Python 3 standard library only) |

## `db.py` commands

Run `db.py <command> -h` for options. Names match fuzzily. `CLASS2B_DATA=/path/to/copy` runs against a copy of `data/`.

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `brief <name>`, `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `canon <search>`, `history <words> [--limit N]`, `thread [name]`, `state`, `resume`, `bible [section]` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start`, `quest-obj <name> <obj_id> <status>`, `quest-end <name> completed\|failed` |
| State updates | `ledger`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Scenes | `scene-start <name> --budget N [--card @file]` (needs `--turn`/`--evidence`; `--location`/`--area` default to the first player character), `scene-card`, `scene-obstacle <text>`, `scene-surprise`, `scene-end` |
| Log, check, save | `turn N+1 --inputs --summary --prompt --slips --notes` (`--summary` required, two lines), `check-prompt <file or ->` (prompt limit, names, split header), `save` |
| Whole turn | `record <payload.json> [--dry-run]`: ops + turn log + save in one locked, all-or-nothing write |
| Safety | `undo-turn N` (restore the snapshot taken before turn N), `recover` (clear a stale lock; restore if a crashed record left the data half-applied) |

- `resume`: start-of-chat summary (state header, scene with a 400-character card excerpt, last 3 turns, clocks, milestones, quests, NPC beats, ladder steps). `state` prints the prompt limit; both warn about a stale lock.
- Every write command takes an exclusive lock on `data/.lock`; a second writer fails at once (exit 6). Reads never lock. `record` refuses unless `turn == state.turn + 1` and under `CLASS2B_TRIAL=1` (except `--dry-run`); any error restores the snapshot. Exit codes: 4 refused, 5 saved locally but push failed, 6 lock busy, 7 stale lock.
- `bible`: no argument lists headings; `bible 6`, `bible act3` or `bible retest` prints one section.
- `turn` adds 1 to the open scene's `turns_used`; `state` and `resume` show `scene X: used/budget turns, obstacles, surprise` and warn when over budget.

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. After every real turn: `record` with `"save": true` (or `db.py save`). It checks that every `data/*.json` parses, commits `campaigns/classroom-2b/data` as `Class 2B save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/classroom-2b/data && git commit -m "Class 2B save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `CLASS2B_TRIAL=1` or `CLASS2B_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields, villain sheets, ledger, debt and reveal ladders in `data/` are director-only; the 2B Standing number is never shown as a meter.
