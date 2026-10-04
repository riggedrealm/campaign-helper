# Function inventory (phase 1, for review)

Written 2026-10-04 from the repo at `0a91403`. Every `db.py` command (70 today) and every script, marked **keep**, **merge**, **retire** or **new**, with a one-line reason. Rule ids refer to `docs/revamp/rule-inventory.md`.

Phase 3 work is additive: the three old skills must keep working until each campaign switches, so nothing below is removed before phase 6 unless it says so. "At switch" means at phase 6, the user's call.

Two changes apply to every command, so they are not repeated in each row:
- **Campaign name first.** Every output starts with the campaign's display name (SEL rules, HO §4.2).
- **Campaign choice.** The default campaign becomes: `--campaign`, else `VOYAGE_CAMPAIGN`, else the session file written by `use`, else the only campaign, else today's hard error.

## 1. Existing commands

### Lookups (read-only)

| Command | Decision | Reason or change |
|---|---|---|
| `loc` | keep | Place checks behind FMT-7 and SPL-10. |
| `npc` | keep | NPC lookups for real gaps (CHAT-2). |
| `quest` | keep | Quest lookups; shows `seed_line` and surface goal (FMT-4). |
| `faction` | keep | Thin-party lookups (LEAVE-4). |
| `lore` | keep | Same. |
| `state` | keep | Adds the open questions count and the arc-functions on/off line. |
| `resume` | keep, change | Reads the version from the one bootstrap skill (VER-1) instead of each campaign's SKILL.md; the `Generic rules` line and the two "Fast turn protocol ... wins over" and "Player agency rules ... win over" lines go at switch. Prints canon traps, main NPCs and act days from `campaign.json`, open questions, sync mismatch counts by type (SYNC-7), repeat slips including director-review findings (REVIEW-1), and whether a hidden-score module is on (TRIG-17). |
| `bible` | keep | Section-only reading of the arc bible (CHAT-2). |
| `spotlight` | keep | Feeds the brief's "spotlight due" line (CHK-2). |
| `canon` | keep | Canon checks on escalation (LOOP-6). |
| `recap` | keep | Used by the resume subagent (AGT-8); its output passes the scan (ORCH-5). |
| `history` | keep, change | Adds `--last N` to print the last N turns in full (inputs, prompt, summary, slips) for the director review (AGT-7); today it only searches words. |
| `brief` | keep | The full character card on TRIG-1. (The new lean turn brief needs a different name; see `turn-brief`.) |
| `thread` | keep | Ladder lookups (REV-1). |

### Updates from play

| Command | Decision | Reason or change |
|---|---|---|
| `add-npc` | keep | An NPC appearing is established by the output, not inferred. |
| `npc-seen` | keep | Same. |
| `npc-note` | keep | Same. |
| `agenda` | keep | Day turnover lists off-screen agendas from it (WLD-3). |
| `quest-start` | keep, change | Gains the `inferred` flag and quote (STATE-2: quest start is inferred). |
| `quest-obj` | retire | Already legacy; Voyage owns objectives and progress counts are never guessed (STATE-3). Remove at switch with its tests. |
| `quest-end` | merge | Today it takes `completed\|failed` and sets the status. New mode: `quest-end NAME --inferred --evidence "..."` records an `apparent_end` note with the quote and leaves the status alone; `sync` confirms it from Voyage's own status (STATE-2, K25). The old mode retires with `quest-obj` at switch. |
| `ledger` | keep | Hidden-score module (MOD-1). |
| `fact` | keep, change | Gains `--kind promise\|condition\|debt\|plant`, `--status open\|paid`, and the `inferred` flag for stated conditions. Promises are a view over facts, one store (HO §4.6.2). |
| `pc-add` | keep | PC sheets from the user (START-1). |
| `pc-sheet` | keep | Same. |
| `pos` | keep, change | Gains the `inferred` flag and quote (STATE-2). `--placement` stays. |
| `time` | keep, change | Gains the `inferred` flag; on a day change prints "Day changed: run `day-turnover`" (WLD-3). |
| `clock-add` | keep | Clocks feed day turnover. |
| `clock-done` | keep | Same. |
| `turn` | keep, demote | The low-level turn logger. `record` and `commit-turn` use the same code, and the tests use `turn` as a fixture helper. Documented only in REF as a repair tool. |
| `thread-reveal` | keep | Gates and pull-forward (REV-1, REV-3). |
| `add-area` | keep | New areas inside existing locations (FMT-7). |
| `scene-start` | keep, change | Gains `--kind fight\|talk\|explore\|mystery\|downtime` for the variety tracker (SCN-7). Optional, so old payloads still validate. Its `--budget` help cites "arc-bible.md section 14", which is right only for Class 2B: point it at `bible budgets`. |
| `scene-card` | keep | Reads the open scene's pressure card. |
| `scene-obstacle` | keep | SCN-4. |
| `scene-surprise` | keep | SCN-5. |
| `scene-end` | keep | SCN-3. |
| `feedback` | keep, change | Fix the help text that says to ask at scene end (K20, SCN-6). |
| `pc-thread` | keep, change | Gains `--pc NAME`: threads are tracked per character (WLD-4, PIV-8, SPL-13). |

### Studio

| Command | Decision | Reason or change |
|---|---|---|
| `studio-request` | keep | STU-3; its hidden-term check stays (STU-5). |
| `studio` | keep | Pending list (STU-10). |
| `studio-show` | keep | Re-reading batches. |
| `studio-done` | keep | Applying and `--fact` canon (STU-9). |

### The turn, saving and safety

| Command | Decision | Reason or change |
|---|---|---|
| `prep` | merge | Its 60-line screen becomes `turn-brief --full` (the escalation view, LOOP-6). `prep` stays as is for the old skills; at switch it becomes an alias. Its `--full NAME` option is not carried over: the full character card is `brief NAME`. |
| `check-prompt` | keep, change | Adds WARN-only agency checks (HO §4.6.6): a place or rule not in the database (FMT-7); a corrective `Tone:` line older than 3 turns (TONE-1); a stated PC condition or outcome (AGY-2, extends today's outcome warning); a `Cut:` that skips when the input shows no travel, waiting or leaving (CUT-2, needs the inputs: `--paste` or `--inputs`); session zero's lines-and-veils terms. Never a new FAIL. |
| `commit-turn` | keep, change | `push_every` default becomes 1 (SAVE-1, Q2), and Joestar's `campaign.json` override of 5 goes (K31); `--push-every` and `--retries` stay. Accepts the new ops (fact kinds, inferred flags, open questions, scene kind). Adds the cross-campaign name WARN: a name unknown to this campaign and known to another (HO §4.2). The turn-continuity guard (`state.turn + 1`) stays the hard guard. |
| `record` | keep | Turn 1 and repairs (START-3, FAIL-9). |
| `save` | keep | Repairs (FAIL-5, FAIL-9). |
| `wrap-up` | keep, change | Asks for the Voyage export before "safe to close", shows whether a sync was done, and reminds to run the director review (SAVE-2, REVIEW-1). Skipping the export is allowed. |
| `undo-turn` | keep | FAIL-7. |
| `recover` | keep | FAIL-3, FAIL-4. |

### Arc planning

| Command | Decision | Reason or change |
|---|---|---|
| `session-zero` | keep | Its lines and veils also feed `check-prompt` and the pivot check (PIV-5). |
| `act-plan` | keep | ARC-3. |
| `act-approve` | keep | ARC-3. |
| `act-deviation` | keep | ARC-19. |
| `act-close` | keep | SCN-8, ARC-3. |
| `arc-plan` | keep, change | Accepts `hidden.offramps` (PIV-1) and a `provisional` draft from the pivot flow. |
| `arc-approve` | keep, change | Also approves a `provisional` arc (PIV-5, PIV-7). |
| `arc` | keep, change | Shows `parked` and `provisional` arcs; never prints off-ramps unless asked with a director-only flag. |
| `plan-brief` | keep, change | Adds the variety mix against session zero's pillars (SCN-7), threads per PC, and the inputs the Planner needs for off-ramps. |
| `preflight` | keep, change | Arc checks only when arc functions are on (CHAT-4, K14); the generic-rules WARN is replaced by the bootstrap version check. |
| `planner-page` | keep, change | Keeps `provisional` arcs and all off-ramps off the page until approved (PIV-5); shows a parked arc as parked. |
| `arc-start` | keep | ARC-12. A provisional arc is made live by `arc-adopt`, not `arc-start`. |
| `arc-move` | keep, change | ARC-13. Accepts a `provisional` arc as well as `active` (today `open_arc(..., "active")`); day turnover also lists due moves for parked arcs. |
| `arc-clue` | keep, change | ARC-15. Accepts `provisional` as well as `active`. |
| `arc-contact` | keep, change | ARC-15. Accepts `provisional` as well as `active`. |
| `arc-reveal` | keep, change | ARC-23. Accepts `provisional` as well as `active` (a provisional arc has no twist, PIV-5, so this is for safety). |
| `arc-review` | keep, change | ARC-16. Accepts `provisional` as well as `active`. |
| `arc-deviation` | keep | ARC-19. |
| `arc-close` | keep, change | May close a `parked` or `provisional` arc (`set_aside`, PIV-9). |

## 2. New commands

| Command | What it does | Rules |
|---|---|---|
| `use NAME` / `use` / `use --clear` | Writes, shows or clears the git-ignored session file that holds this chat's campaign choice. | SEL-1 |
| `menu` | Works without a campaign. Lists campaigns ordered by their last save commit (git log; ordering only), the current session choice and the menu items. Output passes the scan. | MENU-1, ORCH-1 |
| `turn-brief [--paste F] [--names A,B] [--full]` | The lean brief, about 10 lines: scene and budget; rotated gesture picks for present NPCs; what is due; matching canon traps; relevant open promises; open questions; variety and arc one-liners (drift, 130%, pivot); a three-line rules footer. `--full` prints today's `prep` screen. | LOOP-2, HO §4.6.1 |
| `question TEXT` / `question-close ID` | The open questions list (also payload ops). Shown by `turn-brief`, `state` and `resume`. | STATE-4 |
| `promises [--all] [--kind K]` / `fact-status ID open\|paid` | The promises view over facts, and marking one paid. | LOG-3, NPC-4 |
| `day-turnover [--day N]` | Read-only: what the world does on a day change (clocks due, threads going cold after about 7 days, front moves due, parked-arc clocks, off-screen agendas). | WLD-2, WLD-3, PIV-6 |
| `review-add --turn N --slips "cat: text"` | Records director-review findings on that turn's log with `source: review`, so `resume` counts them. The review subagent itself stays read-only; the main chat runs this. | REVIEW-1, AGT-7 |
| `arc-offramps ID --file F` | Stores the Planner's hidden off-ramp sketches on an arc. | PIV-1 |
| `arc-pivot [--thread TEXT]` | Read-only. Prints a matching off-ramp only when a pivot is detected (PIV-2: a plain commitment, or three turns on a new `pc-thread` with no arc contact); otherwise prints nothing about off-ramps. | PIV-1, PIV-2 |
| `arc-adopt ID` | Makes a pivot draft `provisional` after checking the PIV-5 limits, and parks the active arc. | PIV-5, PIV-6 |
| `arc-unpark ID` | "Go back": a parked arc becomes active again and the provisional one is parked. | PIV-9 |
| `sync EXPORT [--apply]` | Dry-run by default: reads Voyage's export, writes a small digest with the export's checksum, prints the mismatch report in three classes and the proposed patch. `--apply` applies class 1 only. Logs mismatch counts by type. | SYNC-1 to SYNC-8 |
| `scan FILE\|-` | The planner page's hidden-term scan for any user-facing text (recap, pivot line, sync report, menu). Exit 4 on a hit. | ORCH-5, SEC-1 |

No new command for the variety tracker: it is `scene-start --kind`, a warning in `turn-brief`, and the mix in `plan-brief`. The existing boredom flags fold into it.

## 3. Scripts and files

| Item | Decision | Reason |
|---|---|---|
| `tools/db.py` | keep | The one tool. |
| `tools/new_campaign.py` | keep, change | Stops generating a SKILL.md; writes `director.md`, and `campaign.json` with `voyage_title`. Adding a campaign needs no skill change (HO §8). |
| `tools/sync_skill.py` | retire at switch | Only syncs generic blocks between skills; there is one skill now (X-13). |
| `tools/skilltpl.py` | retire at switch | Its block-sync code goes with `sync_skill.py`; the placeholder `render()` moves into `new_campaign.py`. |
| `tools/planner_page.py` | keep | Its scan becomes the shared scan behind `db.py scan`. |
| `tools/build_site.py` | keep | Pages build; follows `planner-page`'s rules for provisional and parked arcs. |
| `campaigns/classroom-2b/tools/db.py` (stub) | keep until Class 2B switches | Keeps the old command path for the old skill. |
| `templates/voyage-director/SKILL.md` and the template's generic docs | retire at switch | Replaced by `director/` (X-13, X-15). The template's campaign data skeletons stay for `new_campaign.py`. |
| `.claude/skills/{class2b,joestar,luxcellia}-director/` | retire per campaign at switch | Replaced by `.claude/skills/voyage-director/`. |
| `.github/workflows/pages.yml` | keep | The Pages build and its spoiler refusal (ARC-21). |
| `site.json` | keep | `pages_base` for planner links. |
| `pytest.ini` | keep | Test config. |
| Per-campaign generic doc copies | retire per campaign at switch | X-15. |
| Root `handoff.md` | archive at switch | X-14. |
| `state-new.txt` (repo root) | deleted | A raw Voyage export; removed in `cc4650e` on the user's word (SYNC-6). Still in git history. |

## 4. Internals and data changes

All are neutral migrations: new fields are optional and absent means today's behaviour.

- `ARC_STATUSES` gains `provisional` and `parked`, each with its own validation; one live arc at a time (active or provisional). `DRIFT_TURNS = 8` stays; a new `PIVOT_TURNS = 3`.
- `push_every()` defaults to 1 (Q2).
- `skill_version()` reads `.claude/skills/voyage-director/SKILL.md`; `generic_rules_line()` and `TEMPLATE_SKILL` go at switch.
- `boredom_flags()` folds into the variety check.
- A `provisional` arc counts as live wherever `active` does today: the turn ops above, and the drift, budget and midpoint lines in `prep` and `turn-brief`.
- Doc pointers in tool output move to `director/` at switch: `docs/arc-planning.md` (four strings, including `resume`'s "Arc planner: no plan yet"), `split-scenes.md` (two), `docs/expression.md` (one), `docs/orchestration.md` (two).
- `campaign.json`: new `voyage_title`; `skill_dir` becomes unused at switch.
- Canon facts: optional `kind`, `status`, `inferred`, `quote`.
- State: `open_questions`; a sync log (digests and mismatch counts by type); `scene.kind`; inferred markers on positions and time.
- `arcs.json`: `hidden.offramps`; park and adopt turns.
- Turn logs: slips may carry `source: review`; turns undone in Voyage are marked by `sync`, not deleted.
- `.gitignore`: the session file and the raw export location.

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

0. Green baseline: Joestar tests check the resync against a pinned snapshot (or as lower bounds) instead of the live data, which moves every turn played; the Class 2B skill version pin follows the skill.
1. Session file, `use`, campaign-name headers, cross-campaign name WARN, `menu`.
2. `turn-brief` (lean and `--full`).
3. Inferred flags, open questions (`question`, `question-close`, payload ops).
4. Promises (`fact` kinds and status, `promises`, `fact-status`).
5. Day turnover.
6. Variety tracker (`scene-start --kind`, warnings, `plan-brief` mix).
7. `check-prompt` agency warnings and the lines-and-veils check.
8. Arc statuses and pivot (`provisional`, `parked`, off-ramps, `arc-pivot`, `arc-adopt`, `arc-unpark`, planner page rules).
9. `sync` and the digest.
10. `scan` for user-facing output.
11. `resume`, `preflight`, `wrap-up`, `history --last`, `review-add`, `push_every` default, `feedback` help text.
