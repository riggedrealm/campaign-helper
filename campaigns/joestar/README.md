# Joestar Gang: Reference

Director database for a Voyage world. Two Joestar brothers and the crew they built at Club Lumiere (Kobuncho) fight to topple Daigo Renjiro, the boss of the Kurokawa syndicate, one pillar of his power at a time; the story asks who rules Kobuncho and what the players will risk to protect their own. At migration the game is in Book 1, Act 2 (The Four Pillars), Arc 4 (The Archivist), beat 4-1, at turn 480.
The director writes one steering prompt per turn within the prompt limit (840 characters, see `db.py state`); nothing here is pasted whole into Voyage.

**The rules live in the skill:** `.claude/skills/joestar-director/SKILL.md` (prompt format, director rules, DM principles, main-NPC fidelity, Facts guidance, sheets, turn loop, orchestration). This file is only a reference; payload schema and the Planner/Cast brief templates are in `docs/orchestration.md`.

**Update rule:** change the database only when Voyage's story output establishes something, always with `--turn N --evidence "..."`.

Run commands from the repo root as `python3 tools/db.py --campaign joestar <command>` (`db.py` below; the shared tool serves every campaign). Never read the Voyage world export during play: for Joestar it is `worlds/joestar-save.json` (Voyage's own full save at tick 481, Day 20; the campaign's world file from now on), used only for Studio work and re-imports. `docs/archive/` (verbatim old prose), `docs/org.md`, `docs/pc-sheets.md`, `docs/engine.md`, `docs/story-design.md`, `docs/rules.md` and `docs/migration.md` are human reference; during play use `db.py brief`, `thread`, `quest`, `canon`, `history` and `bible`.

## File map (`campaigns/joestar/`)

| File | What it holds |
|---|---|
| `README.md` | This reference |
| `campaign.json` | Everything specific to this campaign that `tools/db.py` reads: display name, skill dir, start weekday, acts, main NPCs, secret terms, optional modules |
| `arc-bible.md` | Premise, hidden state, acts, showcase fights, endings, obstacle rules, scene turn budgets. Read by section with `db.py bible` |
| `opening.md` | Director-only card for the first scene |
| `split-scenes.md` | The 7-rule split-scene protocol and compact `Cut:` forms |
| `docs/orchestration.md` | `prep` / `commit-turn` / `wrap-up` and the payload format, `record` schema, Planner and Cast brief templates, failure playbook |
| `docs/studio.md` | When and how to inject world content through Voyage's Studio: moments, what never goes in, request formats, batching, log flow |
| `docs/expression.md` | Making `Crew:` beats vivid: flat versus expressive example, the `expression` kit in cast.json (gestures, moods, lines, never) |
| `data/state.json` | Turn, day, act, time, player characters, `party_split`, `scene` (with its `card`), `feedback`, open clocks, introduced NPCs, active quests, milestone `calendar`, changelog, `settings.prompt_limit` |
| `data/cast.json` | Every arc NPC: status (`planned` / `in_play` / `world`), intro lines, voice cards, optional `expression` kits (gestures, moods, lines, never), psychology, arc beats, `wont_do_yet`, relationships, `hidden` secrets |
| `data/quests.json` | The arc quests: objectives, outcomes, seed lines, status |
| `data/canon.json` | Facts established in play |
| `data/threads.json` | Reveal ladders for the arc secrets (director only) |
| `data/turns.json` | Turn log: ticks 382 to 481 imported from Voyage's save (inputs per player character, the `__dm__` prompt that was sent, Voyage's own tier-1 summary; day and time are `?` before t481), then every turn logged by `commit-turn` (`state.turn_base` 381) |
| `data/history.json` | Read-only archive: the 64 range summaries of turns t0 to t474 played before the migration; `history`, `recap` and `resume` read it; `state.turn_base` (480) counts those turns |
| `data/locations.json`, `factions.json`, `world-npcs.json`, `lore.json`, `world.json` | World files, re-imported from Voyage's save `worlds/joestar-save.json` at t481 (`tools/new_campaign.py` `import_world(..., raw_keys=True)`) and merged with the director layer: Voyage's keys win (242 locations, 18 factions plus 5 director-only, 185 NPCs, 206 lore entries beside the 12 director entries); locations are fixed, areas may be added. `docs/migration.md` lists the renames |
| `docs/org.md`, `docs/pc-sheets.md`, `docs/engine.md`, `docs/story-design.md`, `docs/rules.md`, `docs/migration.md`, `docs/archive/` | Org chart and recruit seats; the verbatim PC sheets; the Voyage engine notes and slips; the director's planning procedure; the old skill's Joestar rules and where each landed; the migration checklist with counts; frozen copies of the old prose |
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
| Per turn | `prep [--paste F] [--names A,B] [--full NAME]` (read-only screen, one call), then `commit-turn --prompt F --payload F [--dry-run] [--push-every N]` (check-prompt, whole turn all-or-nothing, local git commit, push every `push_every` turns; FAIL or any payload error writes nothing); `wrap-up` (push everything, "safe to close") |
| Repairs | `record <payload.json> [--dry-run]`: ops + turn log + save in one locked, all-or-nothing write (turn 1, repairs) |
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

- **Premise.** Two player characters (Jostin and Jovian Joestar, a multiplayer table); Book 1 is Daigo Renjiro; the plan is turn-indexed (t0 to t481 played) and the day counter is Voyage's: Day 20 at t481, evening; Day 1 is Saturday, August 1, 2026 (the story start), so the weekday is derived (Thursday). `bible 1` has the full premise, stakes and tone.
- **Acts** (state `act` follows the day; `time` sets it; ranges are in `campaign.json` `acts`). 1 The Crew (done, t0 to t192), 2 The Four Pillars (Days 1 to 120, event-based: ends when all four pillars have fallen; Legitimacy, Enforcement and Finance are down, Intelligence is Arc 4), 3 Daigo's War (locked; plan after Act 2 closes). Arc 4 beats: 4-1 Stills (active), 4-2 Dead Zone, 4-3 Neutral Ground, 4-4 Go Dark, 4-5 Lights Out, 4-6 Final Frame (budget 34 turns from t439). Retro and `feedback --kind act` at each arc end (the pacing pulse check is in `bible 3`).
- **Endings** (`bible endings`). Book 1 ends with Daigo's fall (Act 3). Arc 4 ends at 4-6 Final Frame on a fork the prompt names and never picks: burn the whole archive; give the files to police and press after scrubbing the crew's own footage; keep the archive as leverage; and, separately, Kiriyama's fate (arrest, escape or turned). Every door ends the arc; no cliffhanger tail.
- **Quests.** Names are non-spoiling. Voyage owns progress; the director only seeds. Nothing ends the game. Personal quests unlock when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- **Places and rooms.** No rooms. Base: Club Lumiere (Voyage location `Club Lumière`, home area `Main Lounge`; owned jointly by Jostin and Jovian); the working HQ is the secret shelter under the mats of the gym storage room (Voyage has no such area: `Chikara Academy/combat-gym`); the brothers are full students (dorm `Chikara Student Residences`). NPCs: Maki and the hostesses at Lumiere, Yuzuki at the old bathhouse (Shutter Alley), Tetsu and his regulars at Tetsu Iron Palm Gym (its own Voyage location), Gara above Shutter Alley.
- **Romance** (`romance_eligible`; adults with adult player characters; beats are earned in the story): Played love interests: Ayame Fujinami and Riko Amane (Jostin), Yuzuki Hoshino and Mikoto Kurogane (Jovian); at each NPC's pace (a bold NPC makes moves, a shy one slow-burns; Yuzuki's pace is hers). Never: villains, Rikona Mibu, Shun and Daiki (minors), Noa Amemiya, Kenji Aoi. Any NPC can decline. No relationship is decided off-screen.
- **Secrets** (director only): the Archivist (Shogo Kiriyama) and his bodyguard Replay (Daisuke Mogami), the stream-phone twist, the dead-man upload and the camera exchange, the Kagero school's purpose, the Finance captain's nickname (The Teller; her name, Setsuko Okabe, has been public since t434-t438), and the Act 3 doors (combat-data buyer, Iori Vale's puppeting, the tunnels). See `bible 2` and `thread`.
- **Dates:** None are day-based. Fixed story facts: the conditional-expulsion agreement with Anya (t68), the Anya charter terms (t444 to t449), the courier at the clubroom door (t471 to t473). The print-lab lead is a turn-based clock (t471 to t474) carried in `open_clocks`.

## First-chat intake (story facts only, no stats; Voyage keeps its own sheet)

Per player character (1 to 4), ask once:
- Name and pronouns
- Power concept: name + what it does, or "none yet"
- Background
- Room or home base: already set: Club Lumiere (base) and the school dorms; the gym storage-room HQ is secret
- Sheets are already provided (`docs/pc-sheets.md`); changes come from the user only (`pc-sheet`). Backstory about who the PCs are inside needs the user's OK first.


## Players

Moved from voyage-memory `world/players.md` (the full original is `docs/archive/players.md`). The skill carries the short version; this is the authority.

### Player profile (what the user enjoys)
- **Spine: fights and relationships.** Every arc builds to a showcase fight and puts a relationship under pressure along the way.
- **Difficulty: earned wins.** Enemies are dangerous and win some early rounds; the PCs can always win with good play. Losses cost something; they never end anything.
- **Tone: serious stakes with banter and comedy between.**
- **Fights: puzzle first, spectacle to finish.** Crack the enemy power's rule, then a showcase finisher.
- **Romance: any form (slow burn, active, rivalry), driven by each NPC's personality.** A bold NPC makes moves; a shy one slow-burns.
- **Surprises the user likes:** plot twists about the enemies, and crew personal events (someone's past shows up, someone gets hurt or taken). **No ally betrayals** (a traitor plot was already cut once for this reason).
- **Partnership:** rule on every player request instead of granting it by default (see "Ruling player requests"). When the user does not lead, push the story. Either way, surprise them regularly.
- **Hard line:** the user controls the PCs; the director controls the scene, the NPCs and how the world reacts.
- **Living world:** NPCs and factions pursue their own goals and act, not just react. If the players do not act on an open lead or clock, let the event move and let them face the consequences; pressure, not negation, and no invented deadlines the players cannot act on (user, t472). Keep open clocks in `state.open_clocks` and check them every turn.
- **Ensemble crew:** crew members get subplots and big moments, ideally tied back to fights and relationships.
- **Extra AI-written PC lines:** the user likes them. Never correct them (still correct wrong facts).

### Ruling player requests (the old skill's rule, kept; the template's pacing wins)
Judge each plan, declared world fact and wish: it is reasonable when it fits canon, the PCs' powers, the scene's stakes and the campaign's power level, and does not skip the fun (fights, relationships, earned wins).
- **Reasonable:** accept and carry it out faithfully; add obstacles or a cost only where the action is genuinely risky or the story needs texture.
- **Partly reasonable:** accept the core, then add a cost, limit or step the players must earn.
- **Unreasonable** (an instant fix for a big problem, breaks a power's rules or canon, solves an arc, bypasses a pillar, grants free allies or powers): do not grant it. Turn it into a quest or a rare, limited opportunity, or let the world decline it in the fiction. Never mock; keep the player's intent alive.
- Log wishes in the Wishlist below with the ruling. **Template wins on delivery:** hard noes stay in the fiction (the old "stop and give the user two or three options before any prompt" rule is retired); tell the user in one line in the reply only for a trim or a consequence, and never pause play unless an input breaks consent or the player-agency rules.

### PC pressure (tests the world puts on the PCs; the answers stay the user's)
- The director never decides a PC's inner journey, feelings, bond or ending. A PC arc is a series of tests, not a planned outcome.
- **Jostin is tested on love and home:** love interests with their own wants pulling at him; threats to Club Lumiere and its people.
- **Jovian is tested on strength and purpose:** rivals and masters who push his limits; situations that ask what he fights for.
- Every arc includes at least one love-or-home test for Jostin and one strength-or-purpose test for Jovian (`pc_tests` in the charter; each is a situation, never an outcome).
- **Backstory:** the director may invent world-side history (old enemies, family ties, past events). Anything about who the PCs are inside needs the user's OK first.
- **Jostin's violence / Blackstar bloodlust is not a chosen theme.** Close the existing thread quietly: one acknowledging scene, then done. Do not build it into a recurring theme. Blackstar stays a power with costs; the moral-arc framing is gone.

### Spoiler policy (user-decided t466: split)
- **The user sets the direction; the director keeps the twists.** At charter approval the user sees and approves: premise, promise, budget, pillar, set pieces, crew subplot, climax choices (the kinds, not the fork doors), ending shape, seeds and the recruit seat. The director keeps: the twist, the villain sheet, the surprises, who the villain's face is and the fork doors. PC tests are shown by category only ("Jostin: love or home"), never the situation. Write the direction fields free of twist content (`shared: true` in the old charter; the Story Planner showed only these fields).
- The user vetoes content by principle through the hard lines below; every twist is checked against them.
- **Prompts get secrets just in time:** a hidden fact enters a prompt only in the scene where Voyage needs it, and only as much as that scene needs. The reveal ladders and `check-prompt` block locked names and keywords (replacing `tools/turn.py`'s lock).

### Hard lines (never, unless the user says otherwise)
- No ally betrayals.
- No cliffhanger tails at arc ends.
- No invented deadlines the players cannot act on.
- No death of a named crew member or love interest without the user's OK.
- No relationship decided off-screen.

### Recruiting (user-decided t466; split by arm t474)
- Jovian's call for Spearhead seats (Aether, Phantom heads), Jostin's call for Hearth seats (HearthOps, Arcanum). The Aether Head recruit seat is therefore Jovian's. Each arc charter names one first-wave seat (`recruit_seat`) as the recruit opportunity, in priority order (Aether Head first). The user sees the seat; the director keeps who the candidate is. Org chart and seats: `docs/org.md`.
- The candidate is earned (a quest, a test or a cost), never a free ally. A Jostin search that misses becomes a lead to a candidate, never a dead end. Party membership needs explicit mutual agreement; Rikona has NOT joined.
- No recurring named Kobuncho locals for now; HearthOps scenes deal with the shop-owner alliance as a group.

### Wishlist (player wishes, each with the director's ruling)
- t442 Jostin: a spatial-magic user (teleportation) for Hearth, linking the HQ, Lumiere and the other bases. RULING: unreasonable as an instant wish (it trivialises travel and infiltration). Only as a rare, limited recruit quest later: short range, fixed anchor points, a real cost.
- t441 Jostin: recruit one of the teachers (his call).
- t442 Jostin: the gym bomb shelter is a SECRET headquarters; Principal Anya need not know. RULING: reasonable (a nap-spot find). Secrecy on school grounds is a risky action, so it can be tested.

### Feedback log
Ask one optional question after each scene ("Best moment? Anything drag?") and log the answer with `feedback --kind scene` (also kept here). Format: `- tNNN scene name: best moment / what dragged / note`
- t437 Harumi Wharf finale (Arc 3b): best moment: the emotional hook at Tetsu Gym when collectors threatened Ayame and Jostin got angry (a love-or-home test landing as a fight) / dragged: the whole Finance arc (about 60 turns), leads going cold, the invented 'a week' hook / note: no cliffhanger tails; players want their own choice to matter (the ledger handed to Haruto).
- t442 note: user wants the director to judge whether each player request is reasonable, not cater to every wish.
- t461 note: when anything mentioned might or might not be canon, the director checks the repo before writing the prompt (t460 miss: the safehouse fund is Yuji's raid cash, 70% locked with Haruto; Vault money is the crew's and Rei has no reach over it).
- t466 note: pacing pulse check. The gym HQ and Rei audit ran t459 to t466; user flagged stalling. Director rules: scene budget counter, obstacle ledger, one resolving beat. Compress the remaining beats of Arc 4.

## Migrated from voyage-memory (archive, read-only)

**Migrated from riggedrealm/voyage-memory at t480 (archive, read-only).** voyage-memory (commit 296bf95) is now a frozen archive: Joestar runs on the shared `tools/db.py` and the director template. Nothing there is edited, committed or pushed any more.
- `docs/migration.md` maps every source file and key to where it landed, with counts in and out.
- The Voyage game's own counter is authoritative: state turn 481, next turn 482 (resynced from Voyage's save at tick 481, Day 20). `state.turn_base` (381) and `data/history.json` (the 64 old range summaries) hold the earlier history; `turns.json` holds ticks 382 to 481 from the save, then new turns.
- Live scene: `The sedan in the alley` (`Pulse Printworks/front-counter`, evening; the records deputy waits at `Steam Lantern Alley`), opened from ticks 478-481 with comms, the pending input for the next tick and a card in `state.scene`. The stale corridor scene (`After the last bell`) was closed at the resync.
- Derived drafts (not in the source, written at migration): the psychology fields (need, lie, stress, comfort, laughs, cries, trust-earned), the expression kits and the sample lines of the main NPCs. Refine them in play.
- Where the old rules differed, the template won: 840-character limit (was 700), commit every turn and push every 5 (was a per-turn save script and scene-end saves), hard noes stay in the fiction, the template reply format, Studio, fight, clarity and expression rules (`docs/migration.md`, "Superseded rules").

### Pending port (later, not now)
These tools of the old repo are not ported yet and stay in the voyage-memory archive:
- **Story Planner** (`tools/planner.py`, `planner_template.html`): the structure-only read-only page published as a Claude artifact for the user to approve arc direction.
- **voyage-site publishing** (`tools/site.py`, `site_template.html`): the player-safe public site pushed to `riggedrealm/voyage-site`.
- **`portraits/`** (35 character portraits used by the site and planner).
- Also not ported (superseded by `db.py`): `tools/turn.py`, `store.py`, `turn_save.py`, `build.py`, `check_data.py`, `extract_state.py`, `tools/retired/`.
Until then the arc-end "full sync" is the retro and the next-arc plan only; the old planner and site stay as last published.

## Save procedure

All commits (play saves and code/doc changes) go to `main` of riggedrealm/campaign-helper; never use `claude/*` or other branches (the user's rule).

1. Start of chat: attach the repo, then `git fetch origin main && git checkout -B main origin/main` (cloud sessions may start on a `claude/...` branch).
2. Every real turn: `commit-turn` commits locally and pushes every `push_every` (5) turns; `wrap-up` pushes the rest. `save` (or `record` with `"save": true`) also checks that every `data/*.json` parses, commits `campaigns/joestar/data` as `Joestar Gang save: turn N`, and pushes with retries (exit 5 if only the push failed; exit 8 if not on `main`). By hand: `git add campaigns/joestar/data && git commit -m "Joestar Gang save: turn N" && git push origin main`.
3. `save` refuses with `--trial`, `VOYAGE_TRIAL=1` or `VOYAGE_DATA`, and off `main` (exit 8). Trial runs write nothing.
4. Resume in a new chat with `db.py resume`.

## Spoiler note

The `hidden` fields, villain sheets and reveal ladders in `data/` are director-only.