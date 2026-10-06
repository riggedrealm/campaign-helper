# Night Line: Reference

Director database for a Campfire test campaign (no Voyage world file). A starter campaign for testing Campfire mode: commuters and strangers are stuck at Meridian Central Station in Kestrel Bay when the last Line 9 train is held, and a courier needs a locked case carried to Harrow Street Depot. At stake is one frightened teenager and a night that ends well, gently or badly depending on the table's choices.
The director writes one steering prompt per turn within the prompt limit (840 characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/campfire-test-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 tools/db.py --campaign campfire-test <command>` (`db.py` below; the shared tool serves every campaign). This campaign has no Voyage world export (world file: none). There are no human-only reference docs in this campaign. `campfire-start.json` (campaign root) is the GM's optional first `gm scene` request for the room: scene "The held train" at Platform 4 with Mara Venn, Tobias Achterberg and Officer Priya Sandoval; it holds no hidden word.

## File map (`campaigns/campfire-test/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `campaign.json` | Everything specific to this campaign that `tools/db.py` reads: display name, skill dir, start weekday, acts, main NPCs, secret terms, optional modules |
| `arc-bible.md` | Premise, hidden state, acts, showcase fights, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the first scene |
| `campfire-start.json` | The GM's optional first `gm scene` request (a SceneRequest for "The held train"); no hidden word. It sits at the campaign root because `campaigns/*/campfire/` is git-ignored |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `prep` / `commit-turn` / `wrap-up` and the payload format, `record` schema, Planner (charter and pressure card) and Cast brief templates, failure playbook |
| `docs/arc-planning.md` | The arc planner: session zero, act pitches, arc charters (shared and hidden fields), planning sessions, fronts and pressure cards in play, drift, budget, retro, the Arc Planner page |
| `docs/studio.md` | When and how to inject world content through Voyage's Studio: moments, what never goes in, request formats, batching, log flow |
| `docs/expression.md` | Making `Crew:` beats vivid: flat versus expressive example, the `expression` kit in cast.json (gestures, moods, lines, never) |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), `feedback`, open clocks, introduced NPCs, active quests, milestone `calendar`, changelog, `settings.prompt_limit` |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, optional `expression` kits (gestures, moods, lines, never), psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The arc quests: objectives, outcomes, seed lines, status |
| `data/arcs.json` | Optional. The arc plan: session zero, act pitches, arc charters (shared and `hidden` fields), `pc_threads`, retros, the planner page link. A missing file reads as empty |
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the arc secrets (director only) |
| `data/turns.json` | Turn log: day, time, inputs, summary, prompt, slips, notes |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | Written by hand for this campaign (no Voyage world import); locations are fixed, areas may be added |
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
| Arc planning | `plan-brief`, `session-zero`, `act-plan`, `act-approve`, `act-close`, `arc-plan`, `arc-approve`, `arc [ID] [--list] [--shared]`, `planner-page --out FILE` / `--set-url URL`; in play (also `record` ops) `arc-start`, `arc-move`, `arc-clue`, `arc-contact`, `arc-reveal`, `arc-review`, `arc-deviation`, `act-deviation`, `arc-close`, `pc-thread`; see `docs/arc-planning.md` |
| Ladders and map | `thread-reveal <name> <step>` (`--gate-met`, `--force`), `add-area <location> <area-id> --desc` (`--paths`) |
| Scenes | `scene-start <name> --budget N [--card @file]` (needs `--turn`/`--evidence`; `--location`/`--area` default to the first player character), `scene-card`, `scene-obstacle <text>`, `scene-surprise`, `scene-end` |
| Log, check, save | `turn N+1 --inputs --summary --prompt --slips --notes` (`--summary` required, two lines), `check-prompt <file or ->` (prompt limit, names, split header), `save` |
| Per turn | `prep [--paste F] [--names A,B] [--full NAME]` (read-only screen, one call), then `commit-turn --prompt F --payload F [--dry-run] [--push-every N]` (check-prompt, whole turn all-or-nothing, local git commit, push every `push_every` turns; FAIL or any payload error writes nothing); `wrap-up` (push everything, "safe to close") |
| Repairs | `record <payload.json> [--dry-run]`: ops + turn log + save in one locked, all-or-nothing write (turn 1, repairs) |
| Safety | `undo-turn N` (restore the snapshot taken before turn N), `recover` (clear a stale lock; restore if a crashed record left the data half-applied) |

- `recap [--turns N]`: a 3 to 5 line "previously on" for the table at a fresh chat; read-only, never pasted into Voyage.
- Slips: `turn_log` `slips` entries are tagged `fact|invention|teleport|outcome|dropped` (format "category: text"); `resume` shows the top repeat categories. `check-prompt` also FAILs on missing or out-of-order labels (Cut first, World last) and on words from hidden ladder steps, and WARNs on "correction"/"not X" in Facts and on stated player outcomes.
- `spotlight`: read-only; counts mentions (inputs, summary, prompt) of each player character and main NPC over the last N logged turns (default 10), least featured first, 0 flagged.
- `feedback`: appended to `state.feedback`, so it is snapshotted and rewound by `undo-turn`. `resume` shows the last 3 entries.
- `resume`: start-of-chat summary ("Skill version (repo)" and "Generic rules: X (template Y)" read from SKILL.md, state header, scene with a 400-character card excerpt, last 3 turns, clocks, milestones, quests, NPC beats, ladder steps). `state` prints the prompt limit; both warn about a stale lock.
- Every write command takes an exclusive lock on `data/.lock`; a second writer fails at once (exit 6). Reads never lock. `record` refuses unless `turn == state.turn + 1` and under `VOYAGE_TRIAL=1` (except `--dry-run`); any error restores the snapshot. Exit codes: 4 refused, 5 saved locally but push failed, 6 lock busy, 7 stale lock.
- `plan-brief`: read-only planning brief (session zero, current act, last retro, feedback, PC sheets, ladders, quests, clocks, canon, `invention` slips). `prep` and `resume` print the arc lines (active arc, budget, midpoint, antagonist contact, drift, boredom flags) and the planner page link.
- `bible`: no argument lists headings; `bible 6`, `bible act3`, `bible budgets` prints one section.
- `turn` adds 1 to the open scene's `turns_used`; `state` and `resume` show `scene X: used/budget turns, obstacles, surprise` and warn when over budget.

## Arc reference

Moved here from the skill; the skill holds the rules.

- **Premise.** Commuters and strangers on Platform 4 of Meridian Central Station, Kestrel Bay, a present-day coastal city where about one person in fifty has a power (registered with the Registry Office; unregistered use is a fine, not a crime). One act, two days. Player characters come from the Campfire room's party lines, not from this repo. Day 1 is a Friday; the day rolls over at 05:00.
- **Acts** (state `act` follows the day; `time` sets it; ranges are in `campaign.json` `acts`). 1 The Last Train, Days 1 to 2. Milestones: Day 1 23:40 the held train; late Day 1 the static in the tunnel; end of Day 2 the finale at Harrow Street Depot. No act retro (single act).
- **Endings** (`bible endings`). (a) Wren is calmed and goes home on the train, and Sandoval files nothing. (b) Sandoval takes Wren in for registration, gently. (c) Wren flees into the tunnels and the thread stays open. Endings are decided by choices, never by the director's mood.
- **Quests.** Names are non-spoiling. Voyage owns progress; the director only seeds. Nothing ends the game. Personal quests unlock when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- **Places and rooms.** No home base and no rooms. Players start at `Meridian Central Station/platform-4`. NPCs: Mara Venn works the station (`platform-4` and the office), Tobias Achterberg waits on `platform-4`, Officer Priya Sandoval works the platform and `signal-box`, June Halloway plays in `concourse`. Other places: `maintenance-tunnel`, `line-9-night-train` (`rear-carriage`, `drivers-cab`) and Harrow Street Depot (`loading-bay`, `night-office`).
- **Romance** (`romance_eligible`; adults with adult player characters; beats are earned in the story): none. Nobody is `romance_eligible` in this test campaign.
- **Secrets** (director only): the case holds a prescribed dampener cuff for Tib's younger brother, who is the static in the tunnel (reveal ladder `What Tib is carrying`, four steps).
- **Dates:** Day 1 (Friday) 23:31 the signal box shorted; 23:45 the Line 9 last train is held; the day rolls over at 05:00; the finale is the end of Day 2.

## First-chat intake (story facts only, no stats; Voyage keeps its own sheet)

Per player character (1 to 4), ask once:
- Name and pronouns
- Power concept: name + what it does, or "none yet"
- Background
- Room or home base: none (Campfire players build their own characters; no rooms).
- none (intake is not run in Campfire).

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. Every real turn: `commit-turn` commits locally and pushes every `push_every` (5) turns; `wrap-up` pushes the rest. `save` (or `record` with `"save": true`) also checks that every `data/*.json` parses, commits `campaigns/campfire-test/data` as `Night Line save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/campfire-test/data && git commit -m "Night Line save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `VOYAGE_TRIAL=1` or `VOYAGE_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields (including the hidden fields of every arc in `data/arcs.json`), `pc_threads`, villain sheets and reveal ladders in `data/` are director-only. The user sees only the shared fields, through the Arc Planner page.