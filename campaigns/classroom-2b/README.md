# Class 2B: Reference

Director database for a Voyage arc at Chikara Academy and Sakura Lane Sharehouse: eight first-years in an off-campus misfit experiment; an end-of-semester review decides renewed or dissolved.
The director writes one steering prompt per turn within the prompt limit (840 characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/class2b-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 tools/db.py --campaign classroom-2b <command>` (`db.py` below; the shared tool serves every campaign, and the old `python3 campaigns/classroom-2b/tools/db.py <command>` path still works as a stub that defaults to this campaign). Never read `New_World.json` during play. `cast-bible.md` and `cast-visuals.md` (in `docs/`) are human reference only; during play use `db.py brief` and `db.py npc`.

## File map (`campaigns/classroom-2b/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `arc-bible.md` | Premise, hidden state, four acts, showcase fights, Nightshade paths, retest, personal quests, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the Day 1 move-in |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `prep` / `commit-turn` / `wrap-up` and the payload format, `record` schema, Planner (charter and pressure card) and Cast brief templates, failure playbook |
| `docs/arc-planning.md` | The arc planner: session zero, act pitches, arc charters (shared and hidden fields), planning sessions, fronts and pressure cards in play, drift, budget, retro, the Arc Planner page |
| `docs/studio.md` | When and how to inject world content through Voyage's Studio: moments, what never goes in, request formats, batching, log flow |
| `docs/expression.md` | Making `Crew:` beats vivid: flat versus expressive example, the `expression` kit in cast.json (gestures, moods, lines, never) |
| `docs/cast-bible.md`, `docs/cast-visuals.md` | Main-cast bible (all secrets) and visual sheet. Human reference only |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), `feedback` (list, created on first use), open clocks, introduced NPCs, active quests, milestone calendar, debt, changelog, `settings.prompt_limit` (840) |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, optional `expression` kits (gestures, moods, lines, never), psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The 12 arc quests: objectives, outcomes, Standing effect, seed lines, status |
| `data/ledger.json` | Hidden 2B Standing: current value, thresholds, rubric, hint bands, entries |
| `data/arcs.json` | Optional. The arc plan: session zero, act pitches, arc charters (shared and `hidden` fields), `pc_threads`, retros, the planner page link. A missing file reads as empty |
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the six arc secrets (director only) |
| `data/turns.json` | Turn log: day, time, inputs, summary, prompt, slips, notes |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | World files copied from `New_World.json` once; locations are fixed, areas may be added |
| `data/.snapshots/`, `data/.lock` | Last 5 pre-turn snapshots and the write lock (git-ignored) |
| `campaign.json` | Everything specific to Class 2B that the shared tool reads: display name, skill dir, start weekday (Day 1 = Saturday), acts, main NPCs, secret terms, optional modules (`standing` and `debt` are on here) |
| `tools/db.py` | Stub: runs the shared `tools/db.py` (repo root, Python 3 standard library only) with `--campaign classroom-2b` |

## `db.py` commands

Run `db.py <command> -h` for options. Names match fuzzily. `VOYAGE_DATA=/path/to/copy` runs against a copy of `data/`; `VOYAGE_TRIAL=1` marks a trial run (`CLASS2B_DATA` and `CLASS2B_TRIAL` still work as aliases).

| Kind | Commands |
|---|---|
| Lookups | `loc <name> [area]`, `npc <name>`, `brief <name>`, `quest <name>`, `faction <name>`, `lore <terms>` (`--full KEY`), `canon <search>`, `history <words> [--limit N]`, `thread [name]`, `state`, `resume`, `bible [section]`, `spotlight [--last N]`, `recap [--turns N]` |
| NPC updates | `add-npc`, `npc-seen`, `npc-note`, `agenda` |
| Quest updates | `quest-start` (only one used in play: marks a quest seeded so it is never seeded twice; Voyage owns quest progress), `quest-obj <name> <obj_id> <status>` and `quest-end <name> completed\|failed` (legacy, not used in play) |
| State updates | `ledger`, `fact`, `pc-add`, `pc-sheet`, `pos`, `time`, `clock-add`, `clock-done` |
| Feedback | `feedback --kind scene\|act --best "..." --drag "..." [--notes] [--scene NAME] --turn N` (no evidence; stored in `state.feedback`; also a `record` op) |
| Studio | `studio-request --kind npc\|quest\|faction\|area\|story-start\|story-fix\|other --target NAME --text-file F [--why] --turn N` (auto-batched to `studio_limit`, hidden-term check, `--allow`), `studio [--all]`, `studio-show ID [--batch N]`, `studio-done ID [--batch N] --turn N` (`--location --area-id --desc --paths` for areas, `--fact KEY` for story-fix (immediate, latest turn only)); both writes are also `record` ops; stored in `state.studio`; see `docs/studio.md` |
| Arc planning | `plan-brief`, `session-zero`, `act-plan`, `act-approve`, `act-close`, `arc-plan`, `arc-approve`, `arc [ID] [--list] [--shared]`, `planner-page --out FILE` / `--set-url URL`; in play (also `record` ops) `arc-start`, `arc-move`, `arc-clue`, `arc-contact`, `arc-reveal`, `arc-review`, `arc-deviation`, `act-deviation`, `arc-close`, `pc-thread`; see `docs/arc-planning.md` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Scenes | `scene-start <name> --budget N [--card @file]` (needs `--turn`/`--evidence`; `--location`/`--area` default to the first player character), `scene-card`, `scene-obstacle <text>`, `scene-surprise`, `scene-end` |
| Log, check, save | `turn N+1 --inputs --summary --prompt --slips --notes` (`--summary` required, two lines), `check-prompt <file or ->` (prompt limit, names, split header), `save` |
| Per turn | `prep [--paste F] [--names A,B] [--full NAME]` (read-only screen, one call), then `commit-turn --prompt F --payload F [--dry-run] [--push-every N]` (check-prompt, whole turn all-or-nothing, local git commit, push every `push_every` turns; FAIL or any payload error writes nothing); `wrap-up` (push everything, "safe to close") |
| Repairs | `record <payload.json> [--dry-run]`: ops + turn log + save in one locked, all-or-nothing write (turn 1, repairs) |
| Safety | `undo-turn N` (restore the snapshot taken before turn N), `recover` (clear a stale lock; restore if a crashed record left the data half-applied) |

- `recap [--turns N]`: a 3 to 5 line "previously on" for the table at a fresh chat; read-only, never pasted into Voyage.
- Slips: `turn_log` `slips` entries are tagged `fact|invention|teleport|outcome|dropped` (format "category: text"); `resume` shows the top repeat categories. `check-prompt` also FAILs on missing or out-of-order labels (Cut first, World last) and on words from hidden ladder steps, and WARNs on "correction"/"not X" in Facts and on stated player outcomes.
- `spotlight`: read-only; counts mentions (inputs, summary, prompt) of each player character and main NPC over the last N logged turns (default 10; first name, surname, alias such as Sunny), least featured first, 0 flagged.
- `feedback`: appended to `state.feedback` (turn, day, kind, scene, best, drag, notes), so it is snapshotted and rewound by `undo-turn`; no new file. `resume` shows the last 3 entries.
- `resume`: start-of-chat summary ("Skill version (repo)" and "Generic rules: X (template Y)" read from SKILL.md, state header, scene with a 400-character card excerpt, last 3 turns, clocks, milestones, quests, NPC beats, ladder steps). `state` prints the prompt limit; both warn about a stale lock.
- Every write command takes an exclusive lock on `data/.lock`; a second writer fails at once (exit 6). Reads never lock. `record` refuses unless `turn == state.turn + 1` and under `VOYAGE_TRIAL=1` (except `--dry-run`); any error restores the snapshot. Exit codes: 4 refused, 5 saved locally but push failed, 6 lock busy, 7 stale lock.
- `plan-brief`: read-only planning brief (session zero, current act, last retro, feedback, PC sheets, ladders, quests, clocks, canon, `invention` slips). `prep` and `resume` print the arc lines (active arc, budget, midpoint, antagonist contact, drift, boredom flags) and the planner page link.
- `bible`: no argument lists headings; `bible 6`, `bible act3` or `bible retest` prints one section.
- `turn` adds 1 to the open scene's `turns_used`; `state` and `resume` show `scene X: used/budget turns, obstacles, surprise` and warn when over budget.

## Arc reference

Moved here from the skill; the skill holds the rules.

- **Premise.** Eight first-years in Chikara Academy's off-campus misfit experiment at Sakura Lane Sharehouse; Vice Principal Reiko Shimazu's end-of-semester review decides renewed or dissolved. About 16 weeks; 1 to 4 player characters. Day 1 is a Saturday (move-in); classes start Day 3.
- **Acts** (state `act` follows the day; `time` sets it): 1 Move-In Days 1 to 7, 2 Finding Footing 8 to 42, 3 The Secret 43 to 77, 4 Battle Test 78 to 112. Act boundaries (end of Days 7, 42, 77) get a retro logged with `feedback --kind act`. Milestones: placement tournament Days 6 to 7, field exercise (Hollow Dogs) Day 34, midterm Day 42, Nightshade offer about Day 52, debt due Day 60, collectors about Day 63, Mio's retest Day 84 (if the fraud is out), Battle Test Day 105, final review Day 112; `state` lists the rest.
- **2B Standing** is hidden, kept in `data/ledger.json`, starts at 40, changes only through `ledger +N|-N "reason"` and its rubric. Final review (Day 112): apply the +15 credit if Mio confessed, then 70+ Renewed, 40 to 69 Probation, under 40 Dissolved.
- **Endings** (`bible 7`): Renewed (Shimazu signs before the house), Probation (one housemate leaves, by choices), Dissolved (scattered, move-out epilogue, bonds last).
- **Quests.** Names are non-spoiling. Voyage owns progress; the director only seeds. Nothing ends the game. Personal quests unlock when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- **Rooms** (Sakura Lane Sharehouse). NPCs: `maple-bedroom` (Tatsuya), `loft-bedroom` (Mio), `street-bedroom` (Shin), `sunrise-bedroom` (Sunny). Player characters choose among `courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom`, `river-bedroom`. Unclaimed rooms hold unnamed background housemates who never carry plot.
- **Romance** (`romance_eligible`; adults with adult player characters; beats are earned in the story): Tatsuya, Mio, Shin, Sunny, Ayame, Yūto. Not Arimura, Shimazu, the House Manager, villains.
- **Secrets** (director only): Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, Arimura's and Shimazu's Annex roles, Yūto's scar, the Nine Corners' revenge plan.
- **Dates:** Sunny arrives Day 1 afternoon, Yūto not before Day 4.

## First-chat intake (story facts only, no stats; Voyage keeps its own sheet)

Per player character (1 to 4), ask once:
- Name and pronouns
- Power concept: name + what it does, or "none yet"
- Background
- Room: courtyard / garden / lilac / river
- Famous parent
- Gear

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. Every real turn: `commit-turn` commits locally and pushes every `push_every` (5) turns; `wrap-up` pushes the rest. `save` (or `record` with `"save": true`) also checks that every `data/*.json` parses, commits `campaigns/classroom-2b/data` as `Class 2B save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/classroom-2b/data && git commit -m "Class 2B save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `VOYAGE_TRIAL=1` or `VOYAGE_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields (including the hidden fields of every arc in `data/arcs.json`), `pc_threads`, villain sheets, ledger, debt and reveal ladders in `data/` are director-only; the 2B Standing number is never shown as a meter. The user sees only the shared fields, through the Arc Planner page.
