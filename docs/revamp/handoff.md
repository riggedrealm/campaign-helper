# Handoff: Voyage director skill revamp (for the Opus orchestrator)

Written 2026-10-04 at the end of a planning and grill session with the user. You are the main orchestrator for this revamp. Read this file fully, then follow "Start here". Every decision below is user-approved unless it is marked as yours to make.

## 1. What you are doing and why

The user plays AI-narrated RPG campaigns in **Voyage**. Claude is the hidden **story director**: each turn it writes one steering prompt (840 characters at most; labels `Cut / Tone / Crew / Facts / World`) that goes into Voyage. Voyage narrates and owns every game mechanic. The director owns story, memory, pacing and secrets.

Today each campaign has its own director skill, generated from a template. You are replacing the three skills with **one generic director skill** that works for any campaign, and adding the functions a top-tier director needs.

**Scope: the generic skill and its tooling.** Campaign-specific rollout (Joestar's live Arc 4, backfills, when each campaign switches) is out of scope until the user raises it. Do not change campaign story data, except where a schema change needs a neutral migration.

Why the current design has to go (all verified in the repo at commit `13340a7`):

- **Inverted precedence.** `SKILL.md` describes a paste-and-`prep` loop. `docs/fast-turn.md` and `docs/player-agency.md` then "win over" it and contradict it: `prep` every turn vs none on routine turns; push every 5 turns vs every turn; cut at scene budget vs honour the input and cut only on an idle input; offer a skip at lulls vs a `World:` nudge and never a skip; Cast subagents vs no subagents.
- **No headroom.** Skills are capped at 15,000 bytes by tests; Class 2B's is at 14,999. The text is telegraphic because every new rule squeezes an old one.
- **Version drift.** The uploaded Class 2B skill is `2026-10-04.2`, the repo is `.3`. Every rule change needs a re-upload.
- **Everything loads every turn**: fights, retcon, Studio, arc planning, split party and Planner briefs, though most turns need none.
- **Repetition.** The turn loop is written in four places (skill, `orchestration.md`, root `handoff.md`, `fast-turn.md`). Canon traps are in the skill and in `campaign.json`. The generic docs are copied byte-for-byte into each campaign.

## 2. Start here

1. Repo `riggedrealm/campaign-helper`, branch **`main` only**: `git fetch origin main && git checkout -B main origin/main`. You need push access.
2. Commit this file as `docs/revamp/handoff.md` so it survives the chat.
3. Read, in this order: `.claude/skills/class2b-director/SKILL.md`; `campaigns/classroom-2b/docs/fast-turn.md` and `player-agency.md`; `orchestration.md`; `arc-planning.md`; `studio.md`; `split-scenes.md`; `README.md` (root and campaign); `tools/skilltpl.py`; `tools/sync_skill.py`. Skim `tools/db.py` by command (`-h`), not top to bottom (it is 260 KB).
4. Produce the two inventories (section 7, phase 1) and stop for the user's review. Build nothing before that review.

## 3. The user's standing rules

- **Implementation goes to Sonnet subagents** (`model: "sonnet"`) with a full brief. You plan, review every diff and verify. Planner-type drafting goes to `model: "opus"`.
- **Commit and push to `main` only.** No other branches, no PRs unless asked.
- **The director never takes over Voyage's mechanics.** Rulings decide story consequences only.
- **Never dictate what a player character does.** No menus of actions. Only the player moves their character. Goals come only from play: never ask the player what they want.
- **Trial run means write nothing**: lookups and `--dry-run` only; rehearse on a copy with `VOYAGE_DATA=/path`.
- **Never read or edit world files**: `New_World.json` and everything under `worlds/`. Tools read them; chats do not.
- **Do not ask questions you can answer yourself.** When you do ask, give a recommendation.
- Use they/them unless stated. Change campaign data only through `db.py`.

## 4. The target design

### 4.1 Three layers

1. **Bootstrap skill `voyage-director`** (uploaded once, about 3 KB, always in context):
   - repo attach steps, and "no repo, no directing: stop and say so";
   - the hard invariants in full: Voyage owns mechanics; player agency; secrets are director-only; data changes only when Voyage's output establishes something;
   - the five-question agency pre-check (from `player-agency.md`);
   - the main menu and campaign selection;
   - a version line that `resume` compares with the repo.
2. **`director/core.md`** (read at chat start, about 6 KB, plain sentences, in priority order): the one turn loop; prompt format; reply format; the state ownership table (what Voyage owns, what the director owns, what is inferred); the trigger table that names which playbook to open and when.
3. **Playbooks in `director/playbooks/`**, opened only on a trigger: fights, split party, Studio and story-fix, retcon, leaving the arc and pivot, arc planning, sync, browser adapter, failures.

Also: `director/agents/` holds one brief template per subagent role. `campaigns/NAME/director.md` is a short world sheet; canon traps, main NPCs and act days are printed by `resume` from `campaign.json`, not hand-kept in rule text.

**One home per rule.** No file may say it "wins over" another. The template's generic blocks, the per-campaign copies of generic docs and `sync_skill.py` are removed once the new layout is live.

### 4.2 Campaign selection

- Chosen every chat, never assumed. Order: the user names it; in browser mode, the Voyage tab title matched to a new `voyage_title` field in `campaign.json`; cast names in pasted text as a hint; otherwise the menu asks.
- "Last played" comes from the git log of save commits and only orders the menu.
- The choice is stored in a git-ignored session file that `db.py` reads as its default (shell variables do not persist between calls). Today `db.py` takes `--campaign` or `VOYAGE_CAMPAIGN` and errors when several campaigns exist; keep that hard error when there is no session choice.
- Every `db.py` output starts with the campaign name. Turn continuity (`state.turn + 1`) is the hard guard against a wrong-campaign write. Cast names overlap across campaigns, so a name match is a WARN only, and only when a name is unknown to this campaign and known to another.
- "send" as the first message skips the menu when the campaign is unambiguous.

### 4.3 Orchestrator model

The skill is a main menu. **The turn stays in the main chat** (read, rule, draft, check, submit, bookkeeping): a subagent has no memory of the scene, costs seconds on the user's "send" clock and breaks voice continuity. Subagents do everything off the clock.

| Menu item | Who does it |
|---|---|
| Play a turn (paste or browser) | Main chat |
| Resume digest and recap | Subagent, returns a short brief |
| Plan an act or arc | Opus subagent drafts; main chat reviews with the user |
| Pressure card for a showcase scene | Opus subagent |
| Pivot mini-charter | Opus subagent, in the background |
| Studio batches, cast and world work | Sonnet subagent |
| Sync from the save file | Subagent; main chat confirms the patch |
| Director review, canon audit, act retro | Subagent, read-only |
| Tool, test and doc changes | Sonnet subagent; main chat reviews the diff |
| New campaign scaffold | Sonnet subagent |
| Wrap-up and repairs | Main chat |

Subagent rules: each gets a brief from `director/agents/`, not the skill, and the brief says it is not directing. Read-only, except one named writer at a time. Compact results, never file dumps. Every user-facing output (recap, pivot line, sync report, menu) passes the same hidden-term scan the planner page uses.

### 4.4 The turn loop: one loop, two adapters

- **Paste is the baseline.** The user pastes the last exchange; they submit the prompt; their next paste is the proof it landed.
- **Browser is an optional adapter** for reading the output and submitting. "send" from the user = approval. Keep the stale-read stop ("Waiting..." or unfinished output: stop and tell the user). Confirm a submit by re-reading page text. No panel reads, no repeated screenshots.
- **Two tool calls per turn**: the lean brief, then `commit-turn`. This replaces the user's earlier "no `prep` on routine turns" rule; they approved the change.
- Escalate to the full process (full brief, bible lookups, canon check) on the triggers `fast-turn.md` lists today: new NPC or place, scene at budget, a fight, a milestone or ladder reveal, romance or consent edge cases, power claims, Studio fixes, broken canon.

### 4.5 State: inferred during play, synced at session end

The director cannot see Voyage's panels. It infers from Voyage's output and the player inputs.

- Records made from play carry an `inferred` flag and the quote they came from. Inferred covers position, time, presence, quest start or apparent end, stated conditions, fight status.
- Never guessed: stats, resources, relationship numbers, quest progress counts.
- Prompts stay conditional only for fight status plus at most one open question; other inferred items are simply not asserted.
- An **open questions** list holds unclear things that matter. The turn brief shows it.
- **`sync`**: at session end the user exports Voyage's state file. A subagent diffs it against the database and returns a mismatch report and a proposed patch. Dry-run by default; applied on main-chat confirmation. Three classes:
  1. Voyage-owned state (position, time, quest status, party): proposed from the save.
  2. Anything that conflicts with a canon fact or canon trap: reported as "Voyage drift", not applied; it becomes a Studio-fix candidate or a new trap.
  3. Director layer (cast bibles, ladders, traps, promises, arc plans): untouched.
- Voyage's tick numbering wins. Ticks played without the director are imported from the save; director turns that were undone are marked, not deleted.
- Storage: commit a small extracted digest; keep the raw export out of git with its checksum recorded.
- Mismatches are logged by type so `resume` shows where inference keeps failing. `wrap-up` asks for the export before "safe to close"; the user may skip it, and inferred records then stay inferred.

### 4.6 New functions

1. **Lean turn brief** (about 10 lines, every turn): scene and budget, rotating gesture picks for present NPCs, what is due, matching canon traps, relevant open promises, open questions, and a three-line rules footer.
2. **Promises**: a view over `fact` with new `kind` (promise, condition, debt, plant) and `status` (open, paid) fields. One store. Do not name it "ledger" (that is the hidden-score module).
3. **Day turnover**: on a day change, one command lists what the world does: clocks, threads going cold, front moves due, parked-arc clocks, off-screen NPC agendas.
4. **Variety tracker**: tag each scene once at `scene-start` (fight, talk, explore, mystery, downtime); warn on three of a kind in a row; compare the mix with session zero at retros. Fold the existing boredom flags into it.
5. **Director review**: a fresh read-only subagent audits the last N turns against the agency rules and reports the director's own slips. Run at scene end or wrap-up. Its findings feed `resume`'s repeat slips.
6. **Agency checks in `check-prompt`**: WARN only, never FAIL. Real tests for "new place or rule not in the database" and "`Tone:` fix older than 3 turns"; rough warnings for stated player-character condition or outcome and for a `Cut:` that skips when the input shows no travel. "NPC moved a goalpost" cannot be tested mechanically; the director review covers it. Add a lines-and-veils term check from session zero.
7. **Pivot** (section 4.7).

Not to be built: any profile that infers what the player wants. `pc-thread` records what the character did, never why.

### 4.7 Pivot: arc planning on the fly

The user's requirement: **live first, and the director must already have a plan ready.**

- **Off-ramps.** At each arc approval and midpoint, the Planner writes two or three hidden five-line sketches (promise as a question, one front, a face, a first move), one per thread the character has already pursued on screen. They are prepared, never seeded into a prompt. The tool hides them on routine turns and surfaces one only when a pivot fires.
- **Detect.** At once on an input that plainly commits to a new party or goal; otherwise after three turns on a new thread with no arc contact. The existing eight-turn drift rule and its "Re-aim?" line stay as the user-facing rule (`DRIFT_TURNS = 8`).
- **Bridge.** The main chat writes an inline card for the next scene from the existing "leaving the arc" rules, so play never waits.
- **Draft.** An Opus subagent writes a mini-charter in the background from the matching off-ramp, or from scratch: one front with two or three moves, a face, three clues, a 10 to 15 turn budget. Built only from what the character did; tied into existing ladders where it can be.
- **Adopt.** After main-chat review it goes live as `provisional`. Limits: no twist; no ladder step revealed early; at most one new NPC (the face); new areas only inside existing locations; must pass the lines-and-veils check; stays off the public planner page until approved.
- **Park.** The old arc becomes `parked`. Day turnover keeps moving its clocks and fronts. It may return as a rival or a better offer. One active arc at a time still holds.
- **Tell the user** at the next break, one line: approve, re-aim, or go back. At a multi-player table the host alone approves.
- **Multi-player.** Threads are tracked per character. If one leaves and another stays, that is a split party and the arc stays active. A pivot needs no character in arc contact.
- `db.py` today has `ARC_STATUSES = draft, approved, active, closed, set_aside`, and `arc-start` needs `approved`. Add `provisional` and `parked` with their own validation.

**Arc functions are optional per campaign.** They switch on when a campaign has a session zero and a charter. The skill must work from turn 1 for a campaign with neither.

## 5. What must not be lost

Every rule in today's generic blocks, `fast-turn.md` and `player-agency.md` must land in exactly one new home or be retired with a reason. Where they conflict, `fast-turn.md` and `player-agency.md` win, except the two changes the user approved: the 10-line brief replaces "no `prep` on routine turns", and paste is the baseline.

Keep working as they are: `commit-turn` all-or-nothing writes, snapshots, locks, `undo-turn`, `recover`, `wrap-up`, reveal ladders and their gates, the hidden-term checks, Studio batching, the planner page and its spoiler refusal, optional modules (standing, debt).

## 6. Risks the grill found

- **Rule decay**: with a small bootstrap, rules read once at chat start can fall out of context. The defences are the always-loaded bootstrap, the per-turn footer, the mechanical warnings and the director review. Do not shrink the bootstrap below what those invariants need.
- **Off-ramps tilting the director** toward the plan that is ready. The tool hides them; the director review checks `World:` lines for steering.
- **Secrets leaking through subagent output.** Scan everything user-facing.
- **Sync overwriting canon on purpose-set traps.** Never auto-apply.
- **Tests bound to the old layout**: `tests/test_templates.py` (`SKILL_LIMIT = 15000`, sync asserts), `tests/test_joestar.py` and `tests/test_expression.py` (assert the size cap and the string `Generic rules: 2026-10-04.2`), plus `resume`'s version warning, `new_campaign.py` and `campaign.json` `skill_dir`. Change tests in the same commits as the code.

## 7. Order of work

**Phase 1: inventories (you write these; user reviews before any build).**
- `docs/revamp/rule-inventory.md`: every rule, its source, its one new home, each conflict and how it is resolved. Give each rule an id.
- `docs/revamp/function-inventory.md`: every `db.py` command marked keep, merge, retire or new, with a one-line reason. `quest-obj` and `quest-end` are already legacy.

**Phase 2: rules text.** `director/core.md`, playbooks, agent briefs, the bootstrap `SKILL.md`. You draft the bootstrap and `core.md` yourself; playbooks may go to Sonnet from the inventory. Write plain full sentences; the byte pressure is gone.

**Phase 3: functions**, each as its own Sonnet brief with tests, additive so the three old skills keep working: session file and campaign selection; `menu`; lean brief; inferred flags and open questions; promises; day turnover; variety tracker; `check-prompt` warnings; arc statuses and pivot; `sync` and the digest; hidden-term scan for user-facing output.

**Phase 4: tests.** All existing tests pass or are deliberately replaced. Add a test that every rule id appears in exactly one file and that no doc contains "wins over". Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests`.

**Phase 5: trial.** Rehearse turns on data copies (trial mode, nothing written), in paste mode and browser mode, including a pivot and a sync.

**Phase 6: switch over.** Tag `pre-redesign`. The user uploads the one skill alongside the old three. Retiring the old skills, removing the template and `sync_skill.py`, and each campaign's switch are the user's call, campaign by campaign.

Stop for the user after phase 1, after the phase 2 bootstrap and `core.md` drafts, and before phase 6.

## 8. What done means

- One uploaded skill directs any campaign in the repo; adding a campaign needs no skill change.
- Always-loaded text under 10 KB (bootstrap plus `core.md`), against about 23.5 KB today.
- At most two tool calls per routine turn, plus the submit in browser mode.
- Each rule lives in one file, proven by the test.
- Over 10 real turns: director slips per turn no higher than before, and no stated player-character outcomes.
- A sync against a real export produces a report the user finds mostly signal.

## 9. Reporting

After each phase, tell the user in a few lines: what was committed (hashes), test count, anything you decided on their behalf and why, and what you need from them. Record decisions you make in `docs/revamp/decisions.md` with the reason, so the next chat can pick up from the repo alone.
