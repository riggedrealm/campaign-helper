# Luxcellia: The Fifth Hero's Party: Reference

Director database for a Voyage world. The Fifth Hero's Party: the kingdom of Crownveil summoned four heroes and got five; the player is the discarded fifth, and a private posting board is recruiting people exactly like them. The arc is what they build instead of a revenge: a party, and an answer to the throne.
The director writes one steering prompt per turn within the prompt limit (840 characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/luxcellia-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 tools/db.py --campaign luxcellia <command>` (`db.py` below; the shared tool serves every campaign). Never read the Voyage world export during play. `arc-bible.md` section 2 (Hidden state) is the human spoiler map; during play use `db.py brief`, `db.py thread` and `db.py npc`.

## File map (`campaigns/luxcellia/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `campaign.json` | Everything specific to this campaign that `tools/db.py` reads: display name, skill dir, start weekday, acts, main NPCs, secret terms, optional modules |
| `arc-bible.md` | Premise, hidden state, acts, showcase fights, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the first scene |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `record` payload schema and example, Planner and Cast brief templates, failure playbook |
| `docs/studio.md` | When and how to inject world content through Voyage's Studio: moments, what never goes in, request formats, batching, log flow |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), `feedback`, open clocks, introduced NPCs, active quests, milestone `calendar`, changelog, `settings.prompt_limit` |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The arc quests: objectives, outcomes, seed lines, status |
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
| State updates | `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done` |
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

## Arc reference

Moved here from the skill; the skill holds the rules.

- **Premise.** One player character (single-player playtest); about 100 days; the story start "Summoned and Discarded" at `Aureliath/royal-palace`. Day 1 is a Monday. The game mode is Party and Bonds: party chemistry, bond firsts, the campfire rule, companion threads; no hidden score.
- **Acts** (state `act` follows the day; `time` sets it; ranges are in `campaign.json` `acts`). 1 Severance Days 1 to 14, 2 Bonds 15 to 45, 3 The Vanished 46 to 75, 4 Vindication 76 to 100. Act boundaries (end of Days 14, 45, 75) get a retro logged with `feedback --kind act`. Milestones: first Guild contract Days 2 to 3, Yumi Day 3, Mizuho Day 4 (needs the Studio edit), Ren Day 5, first shared job Day 7, first meal Day 9, rift break Day 20, Serika's team Day 22, Ren's song Day 27, Yumi's curse Day 31, Toma's explanation Day 34, Kazuki vanishes Days 38 to 40, Mizuho's spar Day 48, Daigo's debt Day 53, Wharf raid Day 60, Suzuha asks Day 78, the Almonry Day 90, the throne Day 97; `state` lists the rest.
- **Endings.** Four, decided by choices and who stands beside the player at the throne (Day 97): The Fifth Hero's Party, A Name Alone, The Quiet Refusal, The Cradle Remains (`bible endings`).
- **Quests.** Names are non-spoiling. Voyage owns progress; the director only seeds. Nothing ends the game. Personal quests unlock when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- **Places and rooms.** No rooms. The player starts at `Aureliath/royal-palace` and lodges in the Guild Quarter or the Market District (Voyage names the inn; `add-area` once shown). Heroes (Rin, Toma, Yui, Daigo), Suzuha, Serika and Queen Celestine live at the palace. Yumi's cart is in the Market District; Ren is in the Noble Quarter; Mizuho is Portmaris in the world file and needs the Studio edit to work in the Aureliath Guild Quarter (see `docs/studio.md`).
- **Romance** (`romance_eligible`; adults with adult player characters; beats are earned in the story): Yumi, Ren, Toma, Mizuho, Suzuha, Serika, Rin, Daigo, Yui, per the world roster; adult player characters only; Suzuha's and the heroes' ages are not in the world file, so read the story. Never the villain (the Almoner, the Masked Attendant), Kazuki, Queen Celestine. Any NPC can decline; nothing is pushed.
- **Secrets** (director only): the board's operator and what the recalibrated are (the Almoner's Lattice), Serika's null reading and two sealed precedents, Rin's copied logs, Yui's chiseled fifth anchor, Daigo's buried reading, Toma's anonymous bounty top-ups, Suzuha's engineered engagement, Ren's Earth origin, Yumi's curse, Mizuho's twenty-year case.
- **Dates:** Companion arrival is the story's: Toma and the heroes live at the palace from Day 1; Mizuho arrives Day 4 (after the Studio edit); Suzuha's market hour is Day 17; Kazuki is in the queue Day 2.

## First-chat intake (story facts only, no stats; Voyage keeps its own sheet)

Per player character (one in this playtest), ask once:
- Name and pronouns
- Power concept: name + what it does, or "none yet"
- Background
- Home base: none yet; they lodge at a Guild Quarter or Market District inn (Voyage names it)
- Origin and hook: where they came from (one line) and which opening hook fits: Combat Class, Magic Affinity, Profession, Blessing or Cheat Skill, Rebirth or Race (story facts only, no stats)

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. After every real turn: `record` with `"save": true` (or `db.py save`). It checks that every `data/*.json` parses, commits `campaigns/luxcellia/data` as `Luxcellia: The Fifth Hero's Party save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/luxcellia/data && git commit -m "Luxcellia: The Fifth Hero's Party save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `VOYAGE_TRIAL=1` or `VOYAGE_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields, villain sheets and reveal ladders in `data/` are director-only.