# {{DISPLAY}}: Reference

Director database for a Voyage world. <!-- fill: one or two sentences: the premise and what is at stake (Class 2B: "Eight first-years in an off-campus misfit experiment; an end-of-semester review decides renewed or dissolved.") -->
The director writes one steering prompt per turn within the prompt limit ({{PROMPT_LIMIT}} characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `{{SKILL_DIR}}/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 tools/db.py --campaign {{NAME}} <command>` (`db.py` below; the shared tool serves every campaign). Never read the Voyage world export during play. <!-- fill: human-only reference docs, if any (Class 2B: "`cast-bible.md` and `cast-visuals.md` (in `docs/`) are human reference only; during play use `db.py brief` and `db.py npc`.") -->

## File map (`campaigns/{{NAME}}/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `campaign.json` | Everything specific to this campaign that `tools/db.py` reads: display name, skill dir, start weekday, acts, main NPCs, secret terms, optional modules |
| `arc-bible.md` | Premise, hidden state, acts, showcase fights, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the first scene |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `record` payload schema and example, Planner and Cast brief templates, failure playbook |
| `docs/studio.md` | When and how to inject world content through Voyage's Studio: moments, what never goes in, request formats, batching, log flow |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), `feedback`, open clocks, introduced NPCs, active quests, milestone `calendar`, changelog, `settings.prompt_limit`<!-- module:debt:start -->, `debt`<!-- module:debt:end --> |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The arc quests: objectives, outcomes, seed lines, status |
<!-- module:standing:start -->
| `data/ledger.json` | Hidden Standing score: current value, thresholds, rubric, hint bands, entries |
<!-- module:standing:end -->
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the arc secrets (director only) |
| `data/turns.json` | Turn log: day, time, inputs, summary, prompt, slips, notes |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | World files imported from the Voyage world once (`tools/new_campaign.py --world`); locations are fixed, areas may be added |
| `data/.snapshots/`, `data/.lock` | Last 5 pre-turn snapshots and the write lock (git-ignored) |

## `db.py` commands

Run `db.py <command> -h` for options. Names match fuzzily. `VOYAGE_DATA=/path/to/copy` runs against a copy of `data/`; `VOYAGE_TRIAL=1` marks a trial run. (`CLASS2B_DATA` and `CLASS2B_TRIAL` still work as aliases.)

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `brief <name>`, `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `canon <search>`, `history <words> [--limit N]`, `thread [name]`, `state`, `resume`, `bible [section]`, `spotlight [--last N]`, `recap [--turns N]` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start` (only one used in play: marks a quest seeded so it is never seeded twice; Voyage owns quest progress), `quest-obj <name> <obj_id> <status>` and `quest-end <name> completed\|failed` (legacy, not used in play) |
| State updates | <!-- module:standing:start -->`ledger` (module `standing`), <!-- module:standing:end -->`fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done` |
| Feedback | `feedback --kind scene\|act --best "..." --drag "..." [--notes] [--scene NAME] --turn N` (no evidence; stored in `state.feedback`; also a `record` op) |
| Studio | `studio-request --kind npc\|quest\|faction\|area\|story-start\|story-fix\|other --target NAME --text-file F [--why] --turn N` (auto-batched to `studio_limit`, hidden-term check, `--allow`), `studio [--all]`, `studio-show ID [--batch N]`, `studio-done ID [--batch N] --turn N` (`--location --area-id --desc --paths` for areas, `--fact KEY` for story-fix (immediate, latest turn only)); both writes are also `record` ops; stored in `state.studio`; see `docs/studio.md` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Scenes | `scene-start <name> --budget N [--card @file]` (needs `--turn`/`--evidence`; `--location`/`--area` default to the first player character), `scene-card`, `scene-obstacle <text>`, `scene-surprise`, `scene-end` |
| Log, check, save | `turn N+1 --inputs --summary --prompt --slips --notes` (`--summary` required, two lines), `check-prompt <file or ->` (prompt limit, names, split header), `save` |
| Whole turn | `record <payload.json> [--dry-run]`: ops + turn log + save in one locked, all-or-nothing write |
| Safety | `undo-turn N` (restore the snapshot taken before turn N), `recover` (clear a stale lock; restore if a crashed record left the data half-applied) |

- `recap [--turns N]`: a 3 to 5 line "previously on" for the table at a fresh chat; read-only, never pasted into Voyage.
- Slips: `turn_log` `slips` entries are tagged `fact|invention|teleport|outcome|dropped` (format "category: text"); `resume` shows the top repeat categories. `check-prompt` also FAILs on missing or out-of-order labels (Cut first, World last) and on words from hidden ladder steps, and WARNs on "correction"/"not X" in Facts and on stated player outcomes.
- `spotlight`: read-only; counts mentions (inputs, summary, prompt) of each player character and main NPC over the last N logged turns (default 10), least featured first, 0 flagged.
- `feedback`: appended to `state.feedback`, so it is snapshotted and rewound by `undo-turn`. `resume` shows the last 3 entries.
- `resume`: start-of-chat summary ("Skill version (repo)" and "Generic rules: X (template Y)" read from SKILL.md, state header, scene with a 400-character card excerpt, last 3 turns, clocks, milestones, quests, NPC beats, ladder steps). `state` prints the prompt limit; both warn about a stale lock.
- Every write command takes an exclusive lock on `data/.lock`; a second writer fails at once (exit 6). Reads never lock. `record` refuses unless `turn == state.turn + 1` and under `VOYAGE_TRIAL=1` (except `--dry-run`); any error restores the snapshot. Exit codes: 4 refused, 5 saved locally but push failed, 6 lock busy, 7 stale lock.
- `bible`: no argument lists headings; `bible 6`, `bible act3`, `bible budgets` prints one section.
- `turn` adds 1 to the open scene's `turns_used`; `state` and `resume` show `scene X: used/budget turns, obstacles, surprise` and warn when over budget.
<!-- module:standing:start -->
- Standing is an optional module (`campaign.json` `modules.standing`): `ledger` and the Standing lines in `state`/`resume` exist only while it is enabled.
<!-- module:standing:end -->

## Arc reference

Moved here from the skill; the skill holds the rules.

- **Premise.** <!-- fill: premise, player count, calendar (Class 2B: "Eight first-years ...; about 16 weeks; 1 to 4 player characters. Day 1 is a Saturday (move-in)") -->
- **Acts** (state `act` follows the day; `time` sets it; ranges are in `campaign.json` `acts`). <!-- fill: act names with day ranges, milestones, retro days (Class 2B: "1 Move-In Days 1 to 7 ... Act boundaries get a retro logged with `feedback --kind act`") -->
<!-- module:standing:start -->
- **Standing** is hidden, kept in `data/ledger.json`, changes only through `ledger +N|-N "reason"` and its rubric. <!-- fill: start value, final-review rules and ending thresholds (Class 2B: "starts at 40 ... 70+ Renewed, 40 to 69 Probation, under 40 Dissolved") -->
<!-- module:standing:end -->
- **Endings** (`bible endings`). <!-- fill: one line per ending -->
- **Quests.** Names are non-spoiling. Voyage owns progress; the director only seeds. Nothing ends the game. Personal quests unlock when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- **Places and rooms.** <!-- fill: home base, which rooms or areas player characters may take, where NPCs live (Class 2B: "NPCs: `maple-bedroom` (Tatsuya) ... Player characters choose among `courtyard-bedroom` ...") -->
- **Romance** (`romance_eligible`; adults with adult player characters; beats are earned in the story): <!-- fill: eligible NPCs, and who is never eligible -->
- **Secrets** (director only): <!-- fill: one clause per secret -->
- **Dates:** <!-- fill: arrival days and other fixed dates NPCs must respect -->

## First-chat intake (story facts only, no stats; Voyage keeps its own sheet)

Per player character (1 to 4), ask once:
- Name and pronouns
- Power concept: name + what it does, or "none yet"
- Background
- Room or home base: <!-- fill: the choices (Class 2B: "courtyard / garden / lilac / river") -->
- <!-- fill: world-specific questions, one bullet each (Class 2B: "Famous parent", "Gear") -->

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. After every real turn: `record` with `"save": true` (or `db.py save`). It checks that every `data/*.json` parses, commits `campaigns/{{NAME}}/data` as `{{DISPLAY}} save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/{{NAME}}/data && git commit -m "{{DISPLAY}} save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `VOYAGE_TRIAL=1` or `VOYAGE_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields, villain sheets and reveal ladders in `data/` are director-only.<!-- module:standing:start --> So is the ledger; the Standing number is never shown as a meter.<!-- module:standing:end --><!-- module:debt:start --> The debt is hidden too.<!-- module:debt:end -->
