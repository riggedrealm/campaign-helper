Superseded by plans/skill-redesign.md (Oct 2026).

# Redesign checklist: one store, everything reads from it

Decision (user): repo JSON store is the source of truth. The tracker and GM prompts read off it. Biggest pain: prompt workflow.

## 0. Rhythm (user-decided)
- [x] Per turn: prompt only, no commit
- [x] Extract from JSON/`auto/` once, when planning a new arc or quest
- [x] Write and commit at scene end, arc/quest end, before compaction, or on request
- [x] Build scripts fit this: `scene.json`/`npcs.json` updates happen at checkpoints, not per turn

## 1. Data model (`data/`)
- [x] `scene.json`: location, time, present NPCs, downtime flag, current beat, pending player questions
- [x] `npcs.json` (people incl. PCs; places and factions in `places.json`): status, voice card (notice/want), signature + two moves, what they know
- [x] `arcs.json`: beats; hidden facts tagged with the beat they unlock at
- [x] `canon.json`: facts, corrections (with slip counts), exclusions with reasons
- [x] `threads.json`: player-visible open threads (after t300 only)
- [x] `turns.json` (plus `history.json` for the tracker's old log): one line per turn
- [x] Schema (`data/schema/schema.json`) plus `tools/check_data.py` (PCs never scripted, refs resolve, hidden facts have an unlock beat)

## 2. Migration (nothing lost)
- [x] Convert `campaign-state.md` into the JSON files
- [x] `world/road-to-daigo.md` beats and hidden facts are in `arcs.json` (plan stays prose); `world/canon.md` stays prose reference, key facts are in `canon.json`
- [x] Convert tracker entities, threads and log (completeness checked: every entity, thread and log row is in the store)
- [x] Keep `auto/` as read-only lore reference
- [ ] Generate `campaign-state.md` from the store and diff it against today's; fix gaps (not built yet)

## 3. Build script (`tools/build.py`)
- [x] Generates `brief.md` (scene, present NPCs, active threads, corrections, exclusions)
- [ ] Generates `campaign-state.md`
- [ ] Generates the tracker feed
- [ ] Assembles the fixed prompt parts: header, one `Crew:` line per present NPC, `Correction:` lines, exclusion reasons
- [ ] I only write `Advance to:` and `World:`

## 4. Check script (`tools/check.py`), run before every prompt
- [x] Under 700 characters (counted)
- [x] Jostin/Jovian named in `Advance to:`/`World:`/`Crew:` (warning only; naming is fine, scripting is not)
- [x] Only NPCs in `scene.json` speak (warning for named NPCs not present, on comms or at the club)
- [x] No hidden fact whose unlock beat isn't reached (keyword match)
- [ ] Every player input has an answering NPC or obstacle
- [ ] Risky actions have both branches; safe ones don't
- [x] No timestamps
- [ ] Enemy facts conditional and position-free

## 5. Tracker sync
- [ ] One batch write from `data/` to the tracker DB
- [ ] Tracker pages read only what the sync writes
- [ ] Remove any data the tracker holds that the store doesn't

## 6. Workflow and docs
- [ ] Update `CLAUDE.md`, `README.md` and the `voyage-gm-prompts` skill (via `propose_skills`) to the new per-turn flow
- [ ] Per turn: update `scene.json`/`npcs.json`/`threads.json` + `turns.json` → build → draft `Advance to:`/`World:` → check → commit and push
- [ ] Dry run on the current scene (t327) before switching over


## Status (t327, switched over)
Done: store with schema and validation; migration of campaign-state, road-to-daigo beats and the tracker (entities, threads, log); `turn.py` (assemble + check, replaces check_prompt.py); `store.py` (checkpoint edits); `build.py` (brief.md); `sync.py` (changed docs only, version-pinned, manifest committed); first sync pushed (36 docs); dry run on t327 (697-character prompt matched); `campaign-state.md` retired; CLAUDE.md and README rewritten.
Decided (user): fresh chat per scene; story and inputs may come in one message; short replies; Sonnet for turns, Opus for planning; no local-only state (pending corrections live in canon.json until a checkpoint marks them delivered).
Left: manual prompt checks (both branches for risky actions, enemy facts conditional, every input answered) stay with the writer; skill update proposed via the review card.
