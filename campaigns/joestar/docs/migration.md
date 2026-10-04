# Migration checklist: riggedrealm/voyage-memory (t480) to campaigns/joestar

Done at turn 480 (next 481); resynced from Voyage's own save at tick 481 (section below). voyage-memory (commit 296bf95) is now a frozen archive: nothing there was modified, committed or pushed. Decisions (user): **full move** (Joestar runs on the shared `tools/db.py` and the director template), and **where the old rules differ from the template, the template wins**.

## Resync from Voyage's own save (tick 481, Day 20), 2026-10-04
The user supplied Voyage's full save of this game (`engineState.ticks` 481, story start "07 - Multiplayer Mayhem"). It is stored unchanged as **`worlds/joestar-save.json`** and is the campaign's world file from now on (`campaign.json` `world_file`; README, `docs/studio.md`). Voyage's save is the source of truth for the current state; the old repo data is the director layer. Nothing in `/home/user/voyage-memory`, `New_World.json`, `worlds/luxcellia.json`, `campaigns/classroom-2b/` or `campaigns/luxcellia/` was touched.

### What changed
| Area | Before (t480 migration) | Now (t481 resync) |
|---|---|---|
| World import | rebuilt from old place profiles (11 locations, 136 areas, 13 factions, 15 world NPCs, 12 lore) | `tools/new_campaign.py` `import_world(world, story_start, raw_keys=True)` (new `raw_keys` option: Voyage's own area keys and paths verbatim; NPC dict keys, with the in-story label and `properName` as aliases, and `gender`): **242 locations (1067 areas), 18 factions, 185 NPCs, 206 lore entries**, merged with the director layer |
| Locations | slugified area keys; Club Lumiere, Tetsu Gym and the annex were AREAS of Kobuncho | Voyage's keys: **Club Lumière, Tetsu Iron Palm Gym and Ward Licensing Services are LOCATIONS** (areas keep Voyage's case, e.g. `Main Lounge`); director text kept where Voyage's is empty; old sub-areas Voyage lacks live in `director_areas` (never used for positions) |
| Factions | 13 | 18 from Voyage plus 5 director-only (`director_only`: Speedwagon Foundation, Seiran Tech, Tetsu Iron Palm Gym, Shop-owner alliance, Primes); the old org-chart text is kept as `directorInfo` where it differs |
| World NPCs | 15 | 153: the 15 director entries plus 138 Voyage NPCs (many are crowd placeholders such as `guard 1`); each Voyage-known NPC carries `voyage` (key, type, last place, last seen tick: no stats, hp or relationship numbers); NPCs Voyage places in a location outside its map (`Wilderness`, `Spaceship Crash Site`, ...) keep the string in `voyage_where` |
| Lore | 12 | 218: the 12 director entries (the location tracker rewritten for Voyage's keys) plus Voyage's 206 |
| World file | none; `story_start` placeholder | `story_start` "07 - Multiplayer Mayhem" and `narrator_style` from the save (the director's register note kept as `director_narrator_note`); `resource_settings` and `relationship_stages` stay empty (Voyage's mechanics) |
| State | turn 480, Day 1 Monday 16:00 (placeholders), corridor scene | **turn 481 (next 482), Day 20 Thursday, Evening 17:00 (block start), act 2**; PCs at `Pulse Printworks/front-counter`; scene `The sedan in the alley`; clock "Deputy at the Steam Lantern Alley storeroom (t479)"; stale pending prompt notes cleared, the next tick's pending input (Jostin's Plan B) stored |
| Calendar | `start_weekday` Monday, "Day 1 = migration day" | `start_weekday` Saturday: the save's story start is "Day 1: Saturday, August 1, 2026", so Day 20 is Thursday, August 20 (derived, and consistent with Anya's Friday reports: Day 21 is the next). The clock stays the block start (Voyage keeps only a block) |
| Turn history | `turns.json` empty, `turn_base` 480 | **`turns.json` = ticks 382 to 481 (100 turns)**: inputs per PC, the `__dm__` prompt that was sent, and Voyage's own tier-1 summary for that tick (cut at a sentence boundary under 400 characters); day and time are `?` before t481 (the save keeps none per turn; `history`/`recap`/`resume` print `tNNN`); `turn_base` 381; the 64 old range summaries stay in `history.json` for earlier turns (their last labels, t467 to t474, overlap the real turns) |
| Canon | 72 facts | 159: 79 facts from Voyage's `journalEvents` (83 events; the 2 `adventure-start` and 2 duplicates of existing facts or of each other were skipped; subject `journal tN (type)`) plus 8 resync facts (f152 to f159) |
| db.py | | `when(t)`: turns without a day print as `tNNN` |
| Skill | version 2026-10-04.1 | 2026-10-04.2 (the World rules line named the migration day and "no world file") |

### Renames and remaps (every reference moved to a real key)
- Locations/areas: `Kobuncho/club-lumiere` (and `club-lumiere-*`) to `Club Lumière/Main Lounge`, `Back Office`, `Kitchen`, `Stage Alcove`, `Storage Closet`; `Kobuncho/tetsu-iron-palm-gym*` to `Tetsu Iron Palm Gym/Main Training Floor`, `Front Entrance & Reception`, `Tea Corner & Office`, `Private Storage Room`, `Back Alley Exit`; `Kobuncho/annex-*` to `Ward Licensing Services/ground-floor`, `Front Office`, `Back Hall`, `Paper Vault`, `Captain's Seat`, `Service Ramp`, `Roof Access`; `Kobuncho/club-kagero` to `Kobuncho/Club Kagerō`; `Chikara Academy/gym-corridor` and `gym-storage-room` (no Voyage areas) to `combat-gym`; `principal-anyas-office` to `Principal Anya's office`. Every other old slug maps to Voyage's key by slug (`neon-lantern-street` to `Neon Lantern Street`, `shutter-alley` to `Shutter Alley`, `the-house` to `The House`, ...). Voyage has two keys that differ only by case in Club Lumière (`back office` and `Back Office`), kept as is.
- Remapped references: `campaign.json` `home` (`Club Lumière`/`Main Lounge`), all 27 quests (`location`, `area`, `places`; the print-lab quest moved to `Pulse Printworks/front-counter` plus `Steam Lantern Alley/noodle-corner`), the 15 director world NPCs' positions, both PCs, the scene, and the location-hierarchy lore entry. Cast entries carry no place; canon facts only name places in prose.
- Faction `Joestar Crew` to Voyage's `Joestar Gang` (old text kept as `directorInfo`).
- NPCs: no cast key was renamed (the director keys stay, with the Voyage key and in-story labels added as aliases): Anya = `Principal Anya`, Hana/Nobu/Mikoto/Reiko/Banda = the full cast names, `Yamamoto` (label Tetsu) = `Tetsu`, `Sena Fujimori` (label Sena Amagawa) = `Sena Amagawa`, `Legitimacy captain` = `Councilor Ohmori`, `Kazuki` (label Man in dark suit) = `The records deputy` (inferred from the label), `Sasaki` (label suited handler) = `Suited handler`, `Satoshi Tsuge` = `Tsuge`, `Natsumi` = `Natsumi Arai`. Kept apart on purpose (name traps), and the only Voyage NPC keys renamed (the Voyage key stays in `voyage.key`) so a bare name still resolves to the director's NPC: `Renji` to `Renji (dorm student)`, `Daigo` to `Daigo (student)`, `Hoshino` to `Hoshino (registrar)`, `Ryota` to `Ryota Minazuki` (its properName), `Handler` to `Handler (teacher)`; `Daigo Kurosawa` (properName Ginta Kurosawa) is a separate world NPC with a note, so a bare "Daigo" now warns AMBIGUOUS. The sedan driver is Voyage's `Ryota Kobayashi` (label SEDAN DRIVER), the van's driver `Yuji Hara` (label Driver); neither name has appeared in the story, so prompts keep the labels.

### Flags from t480: resolved or still open
| Flag | Status | Evidence |
|---|---|---|
| 1 Stale scene header | **Resolved**: the corridor scene is closed; the live scene is the alley outside Pulse Printworks (Voyage's place: `Pulse Printworks/front-counter`; the lead is at `Steam Lantern Alley`). The old "t480 pending prompt" was the prompt of tick 481: it is logged as turn 481 and its outcome is in the t481 story | ticks 478 to 481 stories and `partyState` |
| 2 Day counter and weekday | **Resolved**: Day 20, Thursday, evening. Weekday derived from the story start (Saturday, August 1, 2026 = Day 1); the clock is only the block start | `partyState.day` 20, `timeOfDay` evening; `storyStarts['07 - Multiplayer Mayhem']` |
| 3a Okabe locked | **Resolved, revealed** (`thread-reveal "Okabe, the Teller" 1`, turn 438): the players know Setsuko Okabe: she spoke in play, offered to void the Amemiya debt and Noa's contract, took Jostin's three slaps; the master ledger of every Kobuncho debt was read aloud (t437) and burned (t438); Haruto at t439: "Okabe's week is void". Her name left the hidden-word lists (`campaign.json`); the nickname "The Teller" never appeared and stays hidden | story t434 to t439, journal t437/t438, memory bank |
| 3b Kagero school's purpose | **Still hidden** (no ladder reveal). The players know Club Kagerō was the main house where debt-bound people like Noa Amemiya were held, with a "manager of records" who runs debts for anonymous clients (t361 to t371) and that the crew destroyed it (t370). Nothing in the story, journal or memory bank shows the school's purpose | stories t361 to t376, journal, memory bank searched |
| 4 Turn labels | **Resolved for t382 to t481** (Voyage's own ticks); labels before t378 in the 64 old summaries may still be about 50 behind | `turnData` ticks 382 to 481 |
| 5 Rikona and the minors | unchanged (teenagers, not romance eligible). **New open item**: Voyage lists Rikona Mibu in `partyMembers`, but there is no ask or yes in the journal or in the t382 to t481 summaries; canon says she is not in the crew: fact f157 | `partyState.partyMembers` |
| 6 Kaito Arashima | **Resolved**: full crew member (joined as ranged support at t115, vouched for by Josuke Higashikata; in the Voyage party). The "still deciding" line is now only a character note | journal t115, `partyMembers` |
| 7 Name traps | kept; Voyage's own separate `Renji`, `Daigo`, `Daigo Kurosawa` records added as world NPCs with notes | `npcs` |
| 8 Iori Vale | **Resolved: dead.** Jostin killed her by accident when Daigo Renjiro puppeted her into his strike (t182); she died in his arms; the crew carried her body to Club Lumière (t185). Canon f041 and the PC notes updated, fact f152 | journal t182 `companionDeath`, t185 |
| 9 Derived drafts | unchanged | |
| 10 No world export | **Resolved**: `worlds/joestar-save.json` | |
| 11 Arc 4 over budget | **Still true, updated**: 43 turns of 34 at t481. Beat 4-1 Stills' win was met at t479; the live scene hands to 4-2 Dead Zone at t482 | story t479 to t481 |
| 12 Generic strictness | unchanged | |

### Voyage-side status (not mirrored: Voyage owns it)
Voyage's party at t481: Jostin, Jovian, Kaito Arashima, Ayame, Reiko, Mikoto, Hana, Haruto, Nobu, Rikona Mibu, Yuzuki, Rin (all are `in_play` cast; Rikona see above). Voyage's active quest is the generated "Prove the Club's Utility" (Anya's first project for the Joestar Community Outreach Club, charter t449, club announced t471). Stats, resources, relationship numbers, quest progress, inventory and portraits were not imported. `partyState.sceneNPCs` lists Yuji Hara, lookout 2, Ryota Kobayashi and the party members as scene NPCs (the story shows only Haruto, Nobu and Kaito on comms). Voyage's quest list (112) is generated content, not mirrored in `quests.json`.

### Remaining open items
1. Hana, Ayame, Yuzuki, Rin: place unconfirmed in the alley scene (Voyage puts them at the Printworks counter; no lines t478 to t481).
2. Rikona's Voyage party membership vs the canon trap (she is not in the crew).
3. The Kagero school ladder step (hidden; reveal only with story evidence).
4. `The records deputy` = Voyage `Kazuki` and `Kazuya Oda` = the grey-cap courier are label inferences.
5. Imported turns t382 to t480 have no day or time; feedback log entries still say "D1" (placeholder days from the old counter).
6. Act day ranges in `campaign.json` (Act 2 days 1 to 120, Act 3 121 to 240) are planning placeholders; the real boundaries are event-based.
7. 138 Voyage NPCs are imported as world NPCs; crowd placeholders (`guard 1`, `loader 2`, ...) add little: prune in a later pass if they clutter `prep`.

## World check (step 1)
`New_World.json` was inspected with Python (keys and string counts only; never edited). It is the Chikara Tokyo world used by Class 2B: it contains Chikara Academy (359 hits), Sakura Lane, Student Clinic, Riverside Food Market, Second Signal, Steam Lantern Alley, Glassline, Deadbeats Club and Kurokawa locations, but **no Kobuncho, no Club Lumiere (only 'Maison Lumière', a French bistro), no Daigo, no Joestar, no Tetsu gym, no Neon Lantern Street, no Harumi**. So the Joestar setting is NOT in it: the campaign was scaffolded **without** `--world`
(`python3 tools/new_campaign.py joestar --display "Joestar Gang" --setting "Kobuncho, Tokyo"`) and the world files were rebuilt from `places.json`, `profiles.json`, `world/canon.md` and the world bible in `world/notes/lore-and-places.md`. Skill dir: `.claude/skills/joestar-director/` (frontmatter name `joestar-director`, version 2026-10-04.1), so the user's upload replaces the old skill.

## Source to landing, with counts
| Source (voyage-memory) | In | Landed in | Out |
|---|---|---|---|
| `data/npcs.json` | 48 (2 PCs, 10 crew, 36 others) | PCs -> `state.player_characters` (2) and `docs/pc-sheets.md`; mains -> `cast.json` (20 main: the 10 crew, Rei, Anya, Riko, Aurelia, Maki, Tetsu, Gara, Daigo from the enemy list, and Kiriyama and Mogami from `arcs.json` villain data); minor people with a profile -> `cast.json` (20 minor, kind `npc`); the rest -> `world-npcs.json` (15); `others` -> world-npcs (Sonobe, Old Man Koga, Dr. Kiyose), faction `Shop-owner alliance`, canon exclusion (Keito Takeda) | cast 40 + world-npcs 15 + 2 PCs |
| `data/npcs.json` fields: `voice`, `agenda`, `knows`, `note`, `summary`, `division`, `tracker_id`, `public`/`public_summary`, `group`, `scripted`, `student` | all | `voice_card.style` and `notice`, `agenda`, `knows`, `hook`/`canon_status`/notes, org chart (`docs/org.md`), canon fact `students`; `tracker_id`, `scripted`, `public` were store/site plumbing (dropped; `public_summary` kept on the records deputy) | - |
| `data/places.json` | 17 (13 places, 4 factions) | `locations.json` (11 locations, 136 areas; Club Lumiere, Club Kagero, Tetsu Gym and the annex are AREAS of Kobuncho per canon) and `factions.json` (13: the 4 source factions plus 9 from the world bible) | 11 + 13 |
| `data/profiles.json` | 67 | NPC texts -> condensed fields in `cast.json`/`world-npcs.json`; the 2 PC texts -> `state` sheets and `docs/pc-sheets.md`; place texts -> `locations.json`; faction texts -> `factions.json`; the 3 `rule-*` labels -> `docs/engine.md`; **all 67 verbatim in `docs/archive/profiles.md`**; engine ranks/HP and portrait blob ids dropped (Voyage's own) | 67 verbatim |
| `data/arcs.json` `acts` / `arcs` / beats / `hidden` / `pressure_curve` / `open_decisions` | 3 acts, 5 arcs, 27 beats, 6 hidden, 3 curve lines, 6 open decisions | `campaign.json` `acts` (3; day-based, see below) and `arc-bible.md` (all arcs, beats with goal/win/fork/fail-forward, the 4-1 scene card, villain sheets, pc_tests, crew subplots, spotlight plan, choices/echoes, ending, seeds, surprises, revisions, retro, open decisions, pressure curve); the 6 hidden facts -> 6 ladders in `threads.json` (+2 from `hidden_lore`) | 8 ladders, 10 steps |
| `data/canon.json` `facts` | 33 | `canon.json` facts `f001...` (subject = old id, evidence = old id and source) | 33 |
| `canon.json` `corrections` (with slip counts) | 13 | canon facts `correction (<status>, <n> slips): ...` (slip counts and statuses in the subject) + `campaign.json` `canon_traps` | 13 + traps |
| `canon.json` `exclusions` | 3 | canon facts `exclusion: ...` + traps (Keito Takeda, Daigo); the no-leakage rule is the ladders | 3 |
| `canon.json` `engine_rules` / `drift_fixes` | 7 / 4 | canon facts `engine rule n` / `drift fix: ...` and `docs/engine.md` | 7 / 4 |
| `canon.json` `prompt_rules` | 10 | `docs/engine.md` (disposition per rule); superseded by the template | 10 listed |
| `canon.json` `hidden_lore` | 2 | ladders "The combat-data buyer" and "World secrets (Act 3 doors)" | 2 |
| `canon.json` `org` | 2 branches, ranks, rules, plan | `docs/org.md` (every seat, wave, covered-by, recruit rules) + canon facts `divisions`, `org-balance` | full |
| `data/threads.json` | 27 (11 open, 6 parked, 10 done; 1 GM-only) | `quests.json` 27 quests: 11 `active` (with `surface_goal`) + `state.active_quests`; 6 parked -> `planned`; 10 done -> `completed` with `ended_turn` | 27 (11 active) |
| `data/turns.json` | 64 range summaries (11 flagged `slip`) | `history.json` (64, labels verbatim, `turn_from`/`turn_to` parsed, `slip` kept); `state.turn_base` 480; `turns.json` empty | 64 |
| `data/scene.json` | 1 scene at t480 | `state.scene` (present, `comms`, `elsewhere`, `pending_inputs`, `pending_prompt_notes`, card), `state.open_clocks` (print lab lead), `state.turn` 480 | 1 |
| `world/players.md` | 8 sections | README `Players` (profile, ruling requests, PC pressure, spoiler split, hard lines, recruiting, wishlist, feedback log) + `state.feedback` (4 entries) + skill fill block | all |
| `world/story-design.md` | 13 sections | `docs/story-design.md` (adapted) + `arc-bible.md` (compass, vocabulary used in sections 1 and 5) | all |
| `world/voyage-engine.md` | engine table, language, slips, drift fixes | `docs/engine.md` (limit 840) | all |
| `world/canon.md` | setting, base, PCs, org, crew, enemies, relationships, debts, traps, roster corrections, crew powers, location hierarchy | `lore.json` (`joestar-setting-and-base`, `location-hierarchy-tracker`), cast entries (crew powers), canon facts, `docs/org.md`; verbatim `docs/archive/canon.md` | all |
| `world/road-to-daigo.md` | acts, 4 pillars, arcs 3a/3b/4, Act 2 finale, Act 3 | `arc-bible.md` sections 3 to 6; verbatim `docs/archive/road-to-daigo.md` | all |
| `world/notes/*.md` (6) | 160 KB | `lore.json` (world bible split into 10 + 2 entries) and verbatim `docs/archive/notes-*.md` | all |
| `CLAUDE.md`, `README.md`, `REDESIGN.md`, `brief.md`, `plans/skill-redesign.md`, `skill/joestar-director/SKILL.md` | 6 | verbatim `docs/archive/`; superseded workflow (see below); rules in `docs/rules.md` | all |
| `auto/` (stale engine snapshot, 10 files) | 10 | **not copied** (stale; regenerated by `extract_state.py`); stays in the archive | 0 |
| `portraits/` (35 jpg), `tools/` (planner, site, store, turn, build, check_data, extract_state, sync) , `data/schema/` | - | **not ported**: Story Planner, voyage-site publishing and portraits are pending port (README); the rest is superseded by `db.py` | 0 |

## State at migration
- `state.turn` 480 (next 481; the game's own counter is authoritative), `turn_base` 480, `turns.json` empty, `history.json` 64.
- PCs: Jostin Joestar and Jovian Joestar (sheets from the engine profiles; pronouns he/him from the profile text; both players `user`).
- Scene `After the last bell` at `Chikara Academy/gym-corridor` with present Rei Ichinose, comms Nobu/Haruto/Kaito Arashima, pending inputs and the t480 prompt note; open clock `Print lab lead (t471)`; 11 active quests.
- Day 1 = migration day, weekday Monday and clock Afternoon 16:00 are placeholders (the old store never tracked a day counter). Acts in `campaign.json`: 1 The Crew (done, from_day 0), 2 The Four Pillars (Days 1 to 120), 3 Daigo's War (121 to 240); the real boundaries are event-based (Act 2 ends when all four pillars fall): set Act 3's `from_day` when it is planned.

## Superseded rules (template wins)
| Old rule | New |
|---|---|
| 700-character prompt limit | 840 (`campaign.json` `prompt_limit_default`, `state.settings.prompt_limit`) |
| Per-turn save by `turn_save.py` (replace scene turn, rebuild brief, commit and push); scene-end `store.py` chain; push each save | `commit-turn` commits `data/` every turn and pushes every 5 (`push_every` 5); `wrap-up` at the end |
| `tools/turn.py` assembles and checks the prompt; `--header` drift fixes | `check-prompt` / `commit-turn`; drift fixes written by hand |
| Hard no: ruling plus 2 or 3 options and no prompt until the user answers | Hard noes stay in the fiction; stop only for consent or player-agency breaks |
| Scene over budget: flag fights, emotional scenes, romance and banter once instead of cutting | Over budget on a quiet input: `Cut:` to the next beat and `scene-end` (template) |
| Reply: one line on slips, the prompt in a blockquote, the character count, a bullet when the user must decide | Template reply format (prompt in a blockquote with its char count; one extra line only for a slip, a ruling with a story consequence, a Studio item or a decision; Studio batches below the prompt, `story-fix` above) |
| `brief.md` generated from data | `resume`, `prep`, `brief NAME` |
| Chinese-language prompts when 700 will not fit | Kept as a rare fallback only (`docs/engine.md`) |
| Planner on every arc, Story Planner artifact, public site | Template Planner (Opus subagent, before an act or showcase fight); Story Planner and site pending port |
| "No timestamps in prompts" check | Timestamps are allowed (user, t395); no check |
| Standing and debt modules | not used (off) |

## Could not map cleanly (flagged at t480; status after the t481 resync in the section above)
1. **Stale scene header.** `scene.json` located the scene in the school corridor with Rei, but its `pending_prompt_notes` and `pending_inputs` (t480) describe an alley with a sedan driver and a lookout, and the `summary` says "resolve in t467, close by t468". The user asked for the corridor scene to be carried over, so it was; the card and `opening.md` say to ask the user which scene is live. Scene counters (budget 2, used 3, started t466) are placeholders reproducing "over budget".
2. **Day counter and weekday.** Never tracked in the old store (the engine's day counter conflicted: Day 2 vs Day 8/9). Day 1 restarts at the migration; the 3 acts are placeholders in days.
3. **Okabe stays locked.** The old repo still listed Okabe and The Teller (3b-5) and the Kagero school's purpose (3a-5) as locked after those beats had passed; both remain hidden ladder steps for parity (`thread-reveal` them when the story shows the players learned them).
4. **Turn labels.** The old turn log labels before t378 may be about 50 behind the game's counter; `history.json` keeps labels verbatim. `turns.json` ended at t474; t475 to t480 exist only as the scene's pending notes.
5. **Rikona and the minors.** Rikona, Shun, Daiki are teenagers by profile: `romance_eligible` false. Ages for some adults are not in the source (`age` null).
6. **Kaito Arashima's commitment.** The profile says full crew member (user, t387), `world/canon.md` says still deciding: both kept (role vs hidden/agenda).
7. **Kaito Arashima vs Kaito Serizawa, Daigo vs Daigo Kurosawa vs the student Daigo, Renjiro vs Renji, Tetsu vs engine 'Yamamoto'.** Name traps are in `canon_traps`; `NameIndex` warns AMBIGUOUS on a bare "Kaito".
8. **Iori Vale.** Sources disagree (freed from the Puppeteer t181, killed t182, 'coma' vs death record): kept as written in canon and the PC notes ("treat as dead").
9. **Derived drafts.** The psychology fields (need, lie, stress, comfort, laughs, cries, newcomer stance, trust-earned), the expression kits and the sample lines were written at migration from the profiles and voice cards (no secret leaks; kits checked against the hidden terms by `tests/test_joestar.py`); source facts stay in role, power, personality, hook, notes, hidden, agenda and relationships.
10. **No Voyage world export.** `locations.json` and `factions.json` are rebuilt, not exported: Studio edits need a world file from the user. The world file's `story_start` is a placeholder.
11. **Arc 4 is over budget** (41 of 34 turns at t480, still in beat 4-1): compress (arc-bible section 3).
12. **Generic `check-prompt` strictness.** "Replay", "Rerun" and "Still Frame" are strong hidden terms (parity with the old locked-name list); "Echo", "Hush", "Oblivion" are soft (ordinary words).

## db.py changes made for this migration (tests in `tests/test_archive.py`)
- `state.turn_base` (default 0): `verify_data` and `recover` expect `len(turns.json) + turn_base == state.turn`.
- Optional read-only `data/history.json`: `history` searches it after the logged turns; `recap` fills from it; `resume` shows its tail when no turns are logged.
- Optional scene extras (`comms`, `elsewhere`, `pending_inputs`, `pending_prompt_notes`) are printed by `scene_lines`; the two pending lists are cleared when the next turn is logged.

## Counts (checked by `tests/test_joestar.py`)
```json
{
 "in": {
  "npcs": 48,
  "places": 17,
  "profiles": 67,
  "arcs.acts": 3,
  "arcs.arcs": 5,
  "arcs.beats": 27,
  "arcs.hidden": 6,
  "arcs.pressure_curve": 3,
  "arcs.open_decisions": 6,
  "canon.facts": 33,
  "canon.corrections": 13,
  "canon.exclusions": 3,
  "canon.prompt_rules": 10,
  "canon.engine_rules": 7,
  "canon.hidden_lore": 2,
  "canon.drift_fixes": 4,
  "canon.org.branches": 2,
  "threads": 27,
  "threads.open": 11,
  "turns": 64
 },
 "out": {
  "cast.main": 20,
  "cast.total": 40,
  "world-npcs": 153,
  "locations": 242,
  "locations.areas": 1067,
  "factions": 23,
  "lore": 218,
  "quests": 27,
  "quests.active": 11,
  "threads(ladders)": 8,
  "threads.steps": 10,
  "canon.facts": 159,
  "canon_traps": 13,
  "history": 64,
  "state.turn": 481,
  "state.turn_base": 381,
  "turns.json": 100,
  "state.player_characters": 2,
  "state.feedback": 4,
  "state.open_clocks": 1
 },
 "canon_by_origin": {
  "arcs/players-derived": 12,
  "corrections": 13,
  "exclusions": 3,
  "engine_rules": 7,
  "drift_fixes": 4,
  "facts": 33,
  "voyage journal": 79,
  "resync": 8
 },
 "resync": {
  "save": {
   "locations": 242,
   "areas": 1067,
   "factions": 18,
   "npcs": 185,
   "lore": 206,
   "turnData": 100,
   "journalEvents": 83,
   "partyMembers": 12
  },
  "matched_to_existing_npcs": 47,
  "new_world_npcs": 138
 }
}
```
