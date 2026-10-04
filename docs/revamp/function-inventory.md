# Function inventory (phase 1, for review)

Written 2026-10-04 from the repo at `0a91403`; the Built column and sections 2 to 6 were updated after phase 3 against the tool as built (`db.py` now has 85 commands). Every `db.py` command and every script is marked **keep**, **merge**, **retire** or **new**, with a one-line reason, and each row says what was built. Rule ids refer to `docs/revamp/rule-inventory.md`.

Phase 3 work is additive: the three old skills must keep working until each campaign switches, so nothing below is removed before phase 6 unless it says so. "At switch" means at phase 6, the user's call.

Two changes apply to every command, so they are not repeated in each row:
- **Campaign name first.** Every output starts with the campaign's display name (SEL rules, HO §4.2).
- **Campaign choice.** The default campaign becomes: `--campaign`, else `VOYAGE_CAMPAIGN`, else the session file written by `use`, else the only campaign, else today's hard error. Built. The session file is `.voyage-session.json` in the repo root (git-ignored); the environment variable `DB_SESSION_FILE` names another file, which is how the tests point it at a temp path (the name avoids the `VOYAGE_` and `CLASS2B_` prefixes that test helpers strip).
- **Campaign header.** Built: every output starts with `== Display name (campaign) ==`.

## 1. Existing commands

### Lookups (read-only)

| Command | Decision | Reason or change | Built |
|---|---|---|---|
| `loc` | keep | Place checks behind FMT-7 and SPL-10. | unchanged |
| `npc` | keep | NPC lookups for real gaps (CHAT-2). | unchanged |
| `quest` | keep | Quest lookups; shows `seed_line` and surface goal (FMT-4). | unchanged |
| `faction` | keep | Thin-party lookups (LEAVE-4). | unchanged |
| `lore` | keep | Same. | unchanged |
| `state` | keep | Adds the open questions count and the arc-functions on/off line. | built in part: the open questions count is on; the arc-functions on/off line is not (`preflight` and `arc-pivot` print it) |
| `resume` | keep, change | Reads the version from the one bootstrap skill (VER-1) instead of each campaign's SKILL.md; the `Generic rules` line and the two "Fast turn protocol ... wins over" and "Player agency rules ... win over" lines go at switch. Prints canon traps, main NPCs and act days from `campaign.json`, open questions, sync mismatch counts by type (SYNC-7), repeat slips including director-review findings (REVIEW-1), and whether a hidden-score module is on (TRIG-17). | built: prints `Director skill version (repo)` from the bootstrap skill beside the old `Skill version` and `Generic rules` lines (they go at switch), canon traps, main NPCs, act days, open questions, the `Last sync:` line, repeat slips with review findings, the hidden-score line |
| `bible` | keep | Section-only reading of the arc bible (CHAT-2). | unchanged |
| `spotlight` | keep | Feeds the brief's "spotlight due" line (CHK-2). | unchanged |
| `canon` | keep | Canon checks on escalation (LOOP-6). | unchanged |
| `recap` | keep | Used by the resume subagent (AGT-8); its output passes the scan (ORCH-5). | unchanged |
| `history` | keep, change | Adds `--last N` to print the last N turns in full (inputs, prompt, summary, slips) for the director review (AGT-7); today it only searches words. | built: `--last N` (turn, day and time, inputs, prompt, summary, slips, review slips, notes, oldest first) |
| `brief` | keep | The full character card on TRIG-1. (The new lean turn brief needs a different name; see `turn-brief`.) | unchanged |
| `thread` | keep | Ladder lookups (REV-1). | unchanged |

### Updates from play

| Command | Decision | Reason or change | Built |
|---|---|---|---|
| `add-npc` | keep | An NPC appearing is established by the output, not inferred. | unchanged |
| `npc-seen` | keep | Same. | unchanged |
| `npc-note` | keep | Same. | unchanged |
| `agenda` | keep | Day turnover lists off-screen agendas from it (WLD-3). | unchanged |
| `quest-start` | keep, change | Gains the `inferred` flag and quote (STATE-2: quest start is inferred). | built: `--inferred` |
| `quest-obj` | retire | Already legacy; Voyage owns objectives and progress counts are never guessed (STATE-3). Remove at switch with its tests. | still present and still a payload op (it retires at switch) |
| `quest-end` | merge | Today it takes `completed\|failed` and sets the status. New mode: `quest-end NAME --inferred --evidence "..."` records an `apparent_end` note with the quote and leaves the status alone; `sync` confirms it from Voyage's own status (STATE-2, K25). The old mode retires with `quest-obj` at switch. | built: `--inferred` note form; the legacy `completed\|failed` form is still accepted |
| `ledger` | keep | Hidden-score module (MOD-1). | unchanged |
| `fact` | keep, change | Gains `--kind promise\|condition\|debt\|plant`, `--status open\|paid`, and the `inferred` flag for stated conditions. Promises are a view over facts, one store (HO §4.6.2). | built: `--kind`, `--status`, `--inferred` |
| `pc-add` | keep | PC sheets from the user (START-1). | unchanged |
| `pc-sheet` | keep | Same. | unchanged |
| `pos` | keep, change | Gains the `inferred` flag and quote (STATE-2). `--placement` stays. | built: `--inferred` |
| `time` | keep, change | Gains the `inferred` flag; on a day change prints "Day changed: run `day-turnover`" (WLD-3). | built: `--inferred`; on a day change prints `Day changed (Day N -> Day M): run `db.py day-turnover`` |
| `clock-add` | keep | Clocks feed day turnover. | unchanged |
| `clock-done` | keep | Same. | unchanged |
| `turn` | keep, demote | The low-level turn logger. `record` and `commit-turn` use the same code, and the tests use `turn` as a fixture helper. Documented only in REF as a repair tool. | unchanged; documented in `reference.md` as the repair logger |
| `thread-reveal` | keep | Gates and pull-forward (REV-1, REV-3). | unchanged |
| `add-area` | keep | New areas inside existing locations (FMT-7). | unchanged |
| `scene-start` | keep, change | Gains `--kind fight\|talk\|explore\|mystery\|downtime` for the variety tracker (SCN-7). Optional, so old payloads still validate. Its `--budget` help cites "arc-bible.md section 14", which is right only for Class 2B: point it at `bible budgets`. | built: `--kind fight\|talk\|explore\|mystery\|downtime`; `--budget` help points at `bible budgets` |
| `scene-card` | keep | Reads the open scene's pressure card. | unchanged |
| `scene-obstacle` | keep | SCN-4. | unchanged |
| `scene-surprise` | keep | SCN-5. | unchanged |
| `scene-end` | keep | SCN-3. | unchanged |
| `feedback` | keep, change | Fix the help text that says to ask at scene end (K20, SCN-6). | built: the help text no longer says to ask at scene end |
| `pc-thread` | keep, change | Gains `--pc NAME`: threads are tracked per character (WLD-4, PIV-8, SPL-13). | not built: no `--pc` flag; the character is named in the text |

### Studio

| Command | Decision | Reason or change | Built |
|---|---|---|---|
| `studio-request` | keep | STU-3; its hidden-term check stays (STU-5). | unchanged (its kinds include `canon`) |
| `studio` | keep | Pending list (STU-10). | unchanged |
| `studio-show` | keep | Re-reading batches. | unchanged |
| `studio-done` | keep | Applying and `--fact` canon (STU-9). | unchanged |

### The turn, saving and safety

| Command | Decision | Reason or change | Built |
|---|---|---|---|
| `prep` | merge | Its 60-line screen becomes `turn-brief --full` (the escalation view, LOOP-6). `prep` stays as is for the old skills; at switch it becomes an alias. Its `--full NAME` option is not carried over: the full character card is `brief NAME`. | unchanged; `turn-brief --full` prints the same screen (the alias comes at switch) |
| `check-prompt` | keep, change | Adds WARN-only agency checks (HO §4.6.6): a place or rule not in the database (FMT-7); a corrective `Tone:` line older than 3 turns (TONE-1); a stated PC condition or outcome (AGY-2, extends today's outcome warning); a `Cut:` that skips when the input shows no travel, waiting or leaving (CUT-2, needs the inputs: `--paste` or `--inputs`); session zero's lines-and-veils terms. Never a new FAIL. | built: WARN-only checks (place or rule not in the database, repeated `Tone:`, PC condition or outcome, `Cut:` skip without travel, session zero lines and veils, a name known only to another campaign); `--paste FILE` and `--inputs TEXT` give the skip check the inputs; exit 1 on a FAIL, 2 on unknown names only |
| `commit-turn` | keep, change | `push_every` default becomes 1 (SAVE-1, Q2), and Joestar's `campaign.json` override of 5 goes (K31); `--push-every` and `--retries` stay. Accepts the new ops (fact kinds, inferred flags, open questions, scene kind). Adds the cross-campaign name WARN: a name unknown to this campaign and known to another (HO §4.2). The turn-continuity guard (`state.turn + 1`) stays the hard guard. | built: pushes every turn by default; the new ops; prompt check with the payload's `inputs`; cross-campaign name WARN; no campaign overrides `push_every` any more |
| `record` | keep | Turn 1 and repairs (START-3, FAIL-9). | unchanged |
| `save` | keep | Repairs (FAIL-5, FAIL-9). | unchanged |
| `wrap-up` | keep, change | Asks for the Voyage export before "safe to close", shows whether a sync was done, and reminds to run the director review (SAVE-2, REVIEW-1). Skipping the export is allowed. | built: reminds about the export (`Reminder: no sync for turn N`) and the director review; neither blocks "safe to close" |
| `undo-turn` | keep | FAIL-7. | unchanged; also rewinds a `sync --apply` and keeps `review_slips` of turns that stay |
| `recover` | keep | FAIL-3, FAIL-4. | unchanged |

### Arc planning

| Command | Decision | Reason or change | Built |
|---|---|---|---|
| `session-zero` | keep | Its lines and veils also feed `check-prompt` and the pivot check (PIV-5). | unchanged |
| `act-plan` | keep | ARC-3. | unchanged |
| `act-approve` | keep | ARC-3. | unchanged |
| `act-deviation` | keep | ARC-19. | unchanged |
| `act-close` | keep | SCN-8, ARC-3. | unchanged |
| `arc-plan` | keep, change | Accepts `hidden.offramps` (PIV-1) and a `provisional` draft from the pivot flow. | built: validates `hidden.offramps`; a pivot draft is an ordinary draft until `arc-adopt` |
| `arc-approve` | keep, change | Also approves a `provisional` arc, which makes it active with no `arc-start` (PIV-9, D16). | built: approves a `provisional` arc (becomes `active`, no `arc-start`) |
| `arc` | keep, change | Shows `parked` and `provisional` arcs; never prints off-ramps unless asked with a director-only flag. | built: shows parked and provisional arcs; `--offramps` (director only; refused with `--shared`) prints the off-ramps |
| `plan-brief` | keep, change | Adds the variety mix against session zero's pillars (SCN-7), threads per PC, and the inputs the Planner needs for off-ramps. | built in part: the scene mix against the pillars (`SCENE MIX`); the last 10 PC threads, not per PC |
| `preflight` | keep, change | Arc checks only when arc functions are on (CHAT-4, K14); the generic-rules WARN is replaced by the bootstrap version check. | built: arc checks only when arc functions are on; checks the bootstrap skill version |
| `planner-page` | keep, change | Keeps `provisional` arcs and all off-ramps off the page until approved (PIV-5); shows a parked arc as parked. | built: parked arc shown as parked; provisional arcs and off-ramps kept off |
| `arc-start` | keep | ARC-12. A provisional arc is made live by `arc-adopt`, not `arc-start`. | unchanged |
| `arc-move` | keep, change | ARC-13. Accepts a `provisional` arc as well as `active` (today `open_arc(..., "active")`); day turnover also lists due moves for parked arcs. | built: accepts `provisional` as well as `active` |
| `arc-clue` | keep, change | ARC-15. Accepts `provisional` as well as `active`. | built: accepts `provisional` |
| `arc-contact` | keep, change | ARC-15. Accepts `provisional` as well as `active`. | built: accepts `provisional` |
| `arc-reveal` | keep, change | ARC-23. Accepts `provisional` as well as `active` (a provisional arc has no twist, PIV-5, so this is for safety). | built: accepts `provisional` |
| `arc-review` | keep, change | ARC-16. Accepts `provisional` as well as `active`. | built: accepts `provisional` |
| `arc-deviation` | keep | ARC-19. | unchanged |
| `arc-close` | keep, change | May close a `parked` or `provisional` arc (`set_aside`, PIV-9). | built: `--status closed\|set_aside`; `set_aside` also for a draft, approved, provisional or parked arc |

## 2. New commands

All of them are built. The Built column says how the tool differs from the plan, if it does.

| Command | What it does | Rules | Built |
|---|---|---|---|
| `use NAME` / `use --title TEXT` / `use` / `use --clear` | Writes, shows or clears the git-ignored session file (`.voyage-session.json`; env `DB_SESSION_FILE` names another, for tests) that holds this chat's campaign choice. `--title` picks the campaign whose `campaign.json` `voyage_title` matches a Voyage tab title, case-insensitively. | SEL-1 | Built; `--title` was added beyond the plan. |
| `menu` | Works without a campaign. Lists campaigns ordered by their last save commit (git log; ordering only), the current session choice and the menu items. Output passes the scan. | MENU-1, ORCH-1 | Built; `tests/test_session.py` checks the menu against the ORCH-1 table in `director/core.md`. |
| `turn-brief [--paste F] [--names A,B] [--full]` | The lean brief, about 10 lines: scene and budget; rotated gesture picks for present NPCs; what is due; matching canon traps (always-on traps only in `--full`); relevant open promises; open questions; a `Variety:` line and arc one-liners (drift, 130%, a pivot line); `Studio:` cues; a three-line rules footer. `--full` prints today's `prep` screen. | LOOP-2, HO §4.6.1 | Built. |
| `question TEXT` / `question-close ID` | The open questions list (also payload ops; ids look like `q1`). Shown by `turn-brief`, `state` and `resume`. | STATE-4 | Built. |
| `promises [--all] [--kind K]` / `fact-status ID open\|paid [--inferred]` | The promises view over facts, and marking one paid (also a payload op). | LOG-3, NPC-4 | Built; `fact-status` also takes `--inferred`. |
| `day-turnover [--day N]` | Read-only: what the world does on a day change (clocks due, milestones, threads going cold after 7 days, the next move of every front of the live and each parked arc, off-screen agendas of main NPCs after 3 days). Days not on record are counted, not guessed. | WLD-2, WLD-3, PIV-6 | Built. |
| `review-add --turn N --slips "cat: text"` | Records director-review findings on that turn's log as `review_slips` with `source: review`, so `resume` counts them. The review subagent itself stays read-only; the main chat runs this. Any tag outside the five is refused. | REVIEW-1, AGT-7 | Built. |
| `arc-offramps ID --file F` | Stores the Planner's hidden off-ramp sketches on an arc (a JSON list; each sketch has non-empty `thread`, `promise`, `front`, `face`, `first_move`). Replaces the earlier list. | PIV-1 | Built. |
| `arc ID --offramps` | Reads an arc's off-ramps (director only; refused with `--shared`). | PIV-1 | Built beyond the plan. |
| `arc-pivot [--thread TEXT]` | Read-only. Prints a matching off-ramp only when a pivot is detected (PIV-2: `--thread`, or three logged turns with no arc contact and a `pc-thread` note in or just before them); otherwise says no pivot is detected and shows no off-ramp. | PIV-1, PIV-2 | Built. |
| `arc-adopt ID --turn N --evidence TEXT [--force]` | Makes a pivot draft `provisional` after checking the PIV-5 limits the tool can check (no twist, at most one new NPC, one front with 2 or 3 moves, 3 clues, budget 10 to 15, no session-zero line or veil match), and parks the live arc; a re-aim sets the earlier provisional arc aside. Lists every problem and exits 4 unless `--force`. | PIV-5, PIV-6 | Built; also a payload op. |
| `arc-unpark OLD_ID --notes TEXT --turn N --evidence TEXT` | "Go back", in one write: the parked arc becomes active again and the provisional one closes as `set_aside` with the note as its short retro, so two arcs are never live at once. | PIV-9, D20 | Built; also a payload op. |
| `sync EXPORT [--apply]` | Dry-run by default: reads Voyage's export, writes a digest to `data/sync.json` (with the export's SHA-256) and one `state.sync_log` entry, prints the mismatch report in three classes and the proposed patch. `--apply` applies class 1 only, with the tick import and the undone marks, under the lock with a snapshot (`undo-turn` rewinds it); refused in a trial run. | SYNC-1 to SYNC-8 | Built. |
| `scan FILE\|-` | The planner page's hidden-term scan for any user-facing text. Exit 0 and one line when clean, exit 4 and a line per hit, exit 1 for a missing file. Soft secret terms are not scanned. | ORCH-5, SEC-1 | Built. |

No new command for the variety tracker: it is `scene-start --kind`, a warning in `turn-brief`, and the mix in `plan-brief`. The existing boredom flags fold into it.

## 3. Scripts and files

| Item | Decision | Reason | Built |
|---|---|---|---|
| `tools/db.py` | keep | The one tool. | Built: phase 3 is in. |
| `tools/new_campaign.py` | keep, change | Stops generating a SKILL.md; writes `director.md`, and `campaign.json` with `voyage_title`. Adding a campaign needs no skill change (HO §8). | Not built: it still writes `.claude/skills/NAME-director` from the template, writes no `director.md` and no `voyage_title`. |
| `tools/sync_skill.py` | retire at switch | Only syncs generic blocks between skills; there is one skill now (X-13). | Present; goes at switch. |
| `tools/skilltpl.py` | retire at switch | Its block-sync code goes with `sync_skill.py`; the placeholder `render()` moves into `new_campaign.py`. | Present; goes at switch. |
| `tools/planner_page.py` | keep | Its scan becomes the shared scan behind `db.py scan`. | Built: `db.py scan` uses its hidden-term code. |
| `tools/build_site.py` | keep | Pages build; follows `planner-page`'s rules for provisional and parked arcs. | Present (the page rules are in `planner_page.py`). |
| `campaigns/classroom-2b/tools/db.py` (stub) | keep until Class 2B switches | Keeps the old command path for the old skill. | Present. |
| `templates/voyage-director/SKILL.md` and the template's generic docs | retire at switch | Replaced by `director/` (X-13, X-15). The template's campaign data skeletons stay for `new_campaign.py`. | Present; goes at switch. |
| `.claude/skills/{class2b,joestar,luxcellia}-director/` | retire per campaign at switch | Replaced by `.claude/skills/voyage-director/`. | Present; go per campaign at switch. |
| `.github/workflows/pages.yml` | keep | The Pages build and its spoiler refusal (ARC-21). | Unchanged. |
| `site.json` | keep | `pages_base` for planner links. | Unchanged. |
| `pytest.ini` | keep | Test config. | Unchanged. |
| Per-campaign generic doc copies | retire per campaign at switch | X-15. | Present; go per campaign at switch. |
| Root `handoff.md` | archive at switch | X-14. | Present; archived at switch. |
| `state-new.txt` (repo root) | deleted | A raw Voyage export; removed in `cc4650e` on the user's word (SYNC-6). Still in git history. | Done. |

## 4. Internals and data changes

All are neutral migrations: new fields are optional and absent means today's behaviour.

- Built: `ARC_STATUSES` gains `provisional` and `parked`, each with its own validation; one live arc at a time (`ARC_LIVE`: active or provisional). `DRIFT_TURNS = 8` stays; new `PIVOT_TURNS = 3` and `PIVOT_BUDGET = (10, 15)`.
- Built: `push_every()` defaults to 1 (Q2); no campaign overrides it.
- Built beside the old code: `director_skill_version()` reads `.claude/skills/voyage-director/SKILL.md` (`BOOTSTRAP_SKILL`); `skill_version()`, `generic_rules_line()` and `TEMPLATE_SKILL` still serve the old skills and go at switch.
- Built: `boredom_flags()` folds into `variety_flags()`, which adds "three <kind> scenes in a row".
- Built: a `provisional` arc counts as live wherever `active` does today: the turn ops above, and the drift, budget and midpoint lines in `prep` and `turn-brief`.
- Not yet (at switch): doc pointers in tool output move to `director/`: `docs/arc-planning.md` (four strings, including `resume`'s "Arc planner: no plan yet"), `split-scenes.md` (two), `docs/expression.md` (one), `docs/orchestration.md` (two).
- `campaign.json`: `voyage_title` is read by `use --title`, but no campaign sets it yet and `new_campaign.py` does not write it; `skill_dir` becomes unused at switch.
- Built: canon facts take optional `kind`, `status`, `inferred`; the quote is the fact's `evidence`.
- Built: state holds `open_questions`, `sync_log` (turn, time, tick, mismatch counts by type, applied) and `scene.kind`, with inferred markers on positions and time; the digests are in `data/sync.json`, a list with one digest per export.
- Built: `arcs.json` holds `hidden.offramps` and the park, adopt and unpark turns (`parked_turn`, `adopted_turn`, `unparked_turn`).
- Built: director-review findings are a separate `review_slips` list on the turn, each with `source: review` (the turn's own `slips` are untouched); turns undone in Voyage are marked `undone: true` by `sync --apply`, not deleted.
- Built: `.gitignore` holds `.voyage-session.json*` and `campaigns/*/exports/`.

## 5. Tests bound to the old layout (changed in the same commits as the code)

- `tests/test_templates.py`: `SKILL_LIMIT = 15000`, `sync_skill.py` runs, `Generic rules:` asserts, template SKILL.md asserts.
- `tests/test_joestar.py`: the size cap, `sync_skill.py --check`, `skill_dir`, the `Generic rules: X (template X)` line in `resume`.
- `tests/test_expression.py`: `Generic rules: 2026-10-04.2` and the size cap in every skill.
- `tests/test_arcs.py`: asserts `resume`'s "(docs/arc-planning.md)" pointer string.
- New in phase 4: every rule id appears in exactly one file; no file under `director/`, the bootstrap skill or a campaign `director.md` contains "wins over"; one test per new command.

Baseline at `cc4650e` (pytest installed from GitHub sources, see `decisions.md`): 221 tests, 211 pass, 1 skipped, 9 fail. All 9 failures predate the revamp and are stale pins, not broken code:
- eight in `tests/test_joestar.py` pin the tick 481 resync (turn 481, 159 facts, ticks 382 to 481), but Joestar has since been played to turn 482;
- `tests/test_templates.py::test_class2b_skill_size_version_and_generic_blocks` pins Class 2B's skill at `2026-10-04.2`; the repo is at `.3`.

Phase 3 starts by making the baseline green (brief 0 below).

## 6. Phase 3 briefs (one Sonnet brief each, in this order)

0. Green baseline: Joestar tests check the resync against a pinned snapshot (or as lower bounds) instead of the live data, which moves every turn played; the Class 2B skill version pin follows the skill. Built.
1. Session file, `use`, campaign-name headers, cross-campaign name WARN, `menu`. Built.
2. `turn-brief` (lean and `--full`). Built.
3. Inferred flags, open questions (`question`, `question-close`, payload ops). Built.
4. Promises (`fact` kinds and status, `promises`, `fact-status`). Built.
5. Day turnover. Built.
6. Variety tracker (`scene-start --kind`, warnings, `plan-brief` mix). Built.
7. `check-prompt` agency warnings and the lines-and-veils check. Built.
8. Arc statuses and pivot (`provisional`, `parked`, off-ramps, `arc-pivot`, `arc-adopt`, `arc-unpark`, planner page rules). Built, except `pc-thread --pc` (no flag; see section 1).
9. `sync` and the digest. Built.
10. `scan` for user-facing output. Built.
11. `resume`, `preflight`, `wrap-up`, `history --last`, `review-add`, `push_every` default, `feedback` help text. Built, except the arc-functions line of `state`.
