# Revamp decisions

Calls made on the user's behalf during the director revamp, with the reason, so a new chat can pick up from the repo alone. User decisions live in `handoff.md`; open questions are listed in the latest phase report and at the end of `rule-inventory.md`.

## Phase 1 (2026-10-04)

- **D1. Extra playbooks.** Beyond the handoff's list: `pacing.md` (scenes, budgets, acts, day turnover), `reveals.md`, `campaign-start.md`, `hidden-score.md`, plus `director/reference.md` for the payload schema. Reason: each has a clean trigger, and keeping them out of `core.md` is what keeps the always-loaded text near the 10 KB target.
- **D2. Stay form of `Cut:`.** "Continue at <Location/area>, same moment." Reason: merges the skill's form (naming the place guards against teleports) with player-agency's "Stay, same moment." (guards against skips).
- **D3. Parked versus set aside.** After a pivot the old arc is `parked`; "go back" revives it; `set_aside` stays for an arc dropped for good. Reason: the handoff keeps the drift rule's "Re-aim?" and adds parking; both need a status.
- **D4. Briefs reference rules, never copy them.** Subagent briefs point at rule ids in the playbooks. Reason: one home per rule.
- **D5. Campaign rules move at each switch.** Canon traps, main NPCs and world-sheet text move to `campaign.json` and `director.md` when each campaign switches, not before. Reason: campaign rollout is out of scope until the user raises it.
- **D6. Lean brief name.** The new per-turn brief is `turn-brief`; `prep` stays unchanged for the old skills and becomes an alias of `turn-brief --full` at switch. Reason: `brief` is taken (the character card), and changing `prep` in place would break the old skills, which must keep working through phase 3.
- **D7. `quest-end` repurposed.** It becomes the inferred "apparently ended" record that `sync` confirms; `quest-obj` retires. Reason: the handoff makes a quest's apparent end an inferred item, and Voyage owns progress.
- **D8. Review findings are written by the main chat.** The director-review subagent stays read-only; the main chat records its findings with `review-add`. Reason: the one-writer rule for subagents.
- **D9. Planning offer without arc functions.** "No arc is live" is a one-line offer at chat start, never a per-turn trigger. Reason: arc functions are optional, and a campaign without them would otherwise be nagged every turn.
- **D10. Variety tags map to pillars.** fight to combat, talk to social, explore to exploration, mystery to mystery; downtime is reported on its own. Reason: retros compare the scene mix with session zero, which uses the pillar names.
- **D11. Campaign sheets narrow, never loosen.** A campaign's `director.md` may add a limit to a generic rule and names the rule id it narrows; it never loosens a bootstrap invariant. Reason: one home per rule while keeping real campaign differences (Luxcellia's chain quests, Joestar's hard lines).
- **Phase 1 audit.** A fresh read-only subagent checked both inventories against every source. Its findings (missing rules, two-home overlaps, eight unlisted conflicts, tool strings pointing at retiring docs) were applied before commit.

## User answers after phase 1 (2026-10-04)

These are the user's decisions, recorded here so the next chat has them. Details in `rule-inventory.md` section 8.

- **Turn order, both modes:** lean brief, `check-prompt`, send the prompt, then `commit-turn`. Recording and the push must happen after the prompt is out, in the downtime while the player reads Voyage's output. This replaces the handoff's "two tool calls" target with three (LOOP-2).
- **Push every turn:** the tool default becomes 1; Joestar's `push_every: 5` override goes (phase 3).
- **Skips:** never offered, weekly montage included.
- **`state-new.txt`:** deleted in `cc4650e` (still in git history; no force push done).
- **Voyage-voiced PC lines:** the repair line is removed for now, the same for every campaign (X-16). The live skills and their docs stay unchanged until each campaign switches.
- **pytest:** install it. PyPI is blocked from the cloud sandbox, so it was installed from the official GitHub sources: shallow clones of `pytest-dev/pytest` tag `8.3.3`, `pytest-dev/pluggy` tag `1.5.0` and `pytest-dev/iniconfig` tag `v2.0.0` into `/home/claude/.pydeps`, a hand-written `_version.py` in `_pytest/` and `pluggy/` (they are normally generated at build time), and a `.pth` file in `/usr/local/lib/python3.13/dist-packages` listing the three `src` folders. A new session must redo this.
- **Phase 2 waits for the user's go-ahead.**

Test baseline at `cc4650e`: 221 tests, 211 pass, 1 skipped, 9 fail. The 9 failures are stale pins (eight Joestar tests pin the tick 481 resync, but Joestar has been played to turn 482; one test pins Class 2B's skill at `2026-10-04.2`, the repo is at `.3`). Fixing them is phase 3 brief 0.

## Phase 2 (2026-10-04)

- **Orchestration.** The user asked that all drafting go to subagents, with the main chat orchestrating and reviewing. This replaces the handoff's "you draft the bootstrap and core.md yourself". The bootstrap and `core.md` go to one Opus writer (always-loaded, judgment-heavy, a shared 10 KB budget); the playbooks, reference and agent briefs go to Sonnet writers in parallel, on disjoint files.
- **D12. Rule id markers.** Ids sit in HTML comments (`<!-- FMT-4 -->`) at the end of the text that states the rule; the phase 4 test counts only ids inside markers, so plain-text cross references are allowed. Reason: one-home checking without forbidding cross references.
- **D13. The prompt message in paste mode.** Paste mode sends the prompt with the `SendUserMessage` tool, then runs `commit-turn`; the closing reply never repeats the prompt. Reason: the user's turn order puts recording and the push after the prompt is out.
- **D14. Studio batches under the new order.** Ordinary Studio batches go in the closing reply after `commit-turn`; a story fix is filed with `studio-request` before the prompt is sent (and left out of the payload) so it can go above the prompt, and in browser mode the submit waits until the user says the fix is applied. Reason: a story fix must reach Voyage before the next prompt; everything else can wait for a natural break.

Writing conventions for all phase 2 files: `phase2-conventions.md`.
- **D3 revised (phase 2 review).** "Re-aim" now means redrafting the new (provisional) arc's direction with the user while the old arc stays parked. Approve makes the provisional arc active; go back unparks the old arc and closes the provisional one. Reason: as first written, "re-aim" and "approve" did the same thing, and the drift line's "Re-aim?" (start the pivot flow) read differently from the three-way line.
- **D15. The sync subagent writes the digest.** It is the one named writer, limited to the digest and checksum its `db.py sync EXPORT` dry run writes; it never runs `--apply`. Reason: the dry run writes a digest, which a read-only subagent may not do.
- **D16. Approving a provisional arc makes it active.** It is already live, so no `arc-start` follows; `arc-approve` keeps its `--lines-checked` statement. Reason: the pivot flow and the planning flow must not both start the same arc.
- **D17. Canon audit and act retro briefs.** Both are extra modes of `director/agents/review.md` (read-only). The act retro subagent drafts; the main chat writes and records the retro. Reason: ORCH-1 lists them as subagent jobs, and no brief existed.
- **D18. Size of the always-loaded layer.** The bootstrap and `core.md` drafts total 16.6 KB against the handoff's 10 KB target; the inventory's own paraphrases of those rows already total about 16 KB. Left for the user to decide at the phase 2 stop.
- **D19. Sync confirmation and trial runs.** The main chat shows the user a short summary of the class 1 patch and runs `sync --apply` only after the user says yes. In a trial run, `sync` runs only against a `VOYAGE_DATA` copy, because its dry run writes a digest. Reason: the patch changes data from an outside source, and a trial run writes nothing to the real campaign.
- **D20. Going back is one command.** `arc-unpark OLD_ID --notes TEXT` revives the parked arc and closes the provisional one as `set_aside` (the note is its short retro) in the same write. Reason: one live arc at a time must hold even between two commands.
- **D18 resolved.** The user accepted about 16.5 KB for the bootstrap and `core.md` together (option A: everything left is used every turn).
- **D21. Studio moments live in the trigger table.** The list of moments that call for a Studio request moves from `studio.md` (STU-2) into `core.md`'s trigger row (TRIG-8), and `turn-brief` prints mechanical Studio cues (pending requests, an act-start bundle due, a recurring NPC or a started quest not yet in Studio, new areas). Reason: the director must know a Studio moment without first opening the Studio playbook (a check the user asked for).

## Phase 3 (2026-10-05)

How it ran: twelve implementation briefs plus two follow-ups, each a Sonnet subagent, in four waves. Parallel implementers worked in isolated git worktrees and left their changes uncommitted; the main chat reviewed each diff, applied it to `main`, ran the full suite, committed each brief separately and removed the worktrees and their local branches. Nothing was committed to any other branch.

Choices the implementers made that the main chat accepted:
- **Inferred records.** `inferred: true` plus `quote` on the record changed (the PC entry, the quest, the fact; `time_inferred` and `time_quote` on state). A plain update clears them; `quest-start` on an inferred active quest confirms it.
- **Open questions** live in `state.open_questions` (closed ones stay, ids are not reused). **Promises** are facts with `kind` and `status`; `fact-status` changes the status.
- **Pivot detection.** `arc-pivot` fires on `--thread`, or when the last 3 turns lack arc contact (an `arc_contact` flag, a clue found, the face met, the twist out) and a `pc-thread` note was added in or just before them. Off-ramps are matched by word overlap and shown only then. `arc-unpark` shifts the arc's start by the paused turns. Adopting a new draft while a provisional arc is live sets the old provisional arc aside (re-aim).
- **Session file.** `.voyage-session.json` in the repo root (git-ignored); tests use `DB_SESSION_FILE` via `tests/conftest.py`. Every campaign command prints `== Display (name) ==` first.
- **Day turnover** dates a quest's last contact from its log and from turns naming it; anything without a recorded day is counted, never guessed. Off-screen agendas use a 3-day window, at most 8 listed.
- **Variety.** Finished scenes are kept in `state.scene_log`; the boredom flags and the three-of-a-kind check print as one "variety flags (N)" line; `plan-brief` shows the scene mix since the act began.
- **check-prompt** warnings are rough by design and never FAIL. On real prompts the stale-Tone warning fires often (Luxcellia kept one Tone for 10 turns), which is the point of TONE-1.
- **scan** exits 0 clean, 4 on a hit, 1 on a missing file; soft secret terms are not scanned (they only warn in check-prompt).
- **Sync.** The digest lives in `data/sync.json`; raw exports belong in a git-ignored `campaigns/NAME/exports/`. Quest matching between the save and the database is by name and the save's quest field names are inferred from code, not from reading a save: on the real Joestar save no quest matched, so this must be checked in the phase 5 trial with a real export.
- **pc-thread** takes `--pc` (required with two or more PCs). Arc contact is still a per-turn flag, not per PC.
- **new_campaign.py** now also writes `campaigns/NAME/director.md` from a template and a `voyage_title`; it still generates the old per-campaign skill until the user retires it.
- **Not built, accepted:** `state` prints no arc-functions line (preflight and arc-pivot do); `arc-adopt` leaves the "no early ladder step" and "new areas" limits to the director; `turn-brief` omits always-on canon traps, which `resume` prints at chat start.

## Phase 5 trial (2026-10-05, Luxcellia)

The user played four rehearsal turns (58 to 61) in the real game with prompts drafted under the new rules and recorded on a data copy; a sync dry run and apply ran on their real export against the copy. Real campaign data was not written; it stops at turn 57 until a real sync.

- **D22. Contested social asks are rolled.** On turn 61 the director's prompt scripted Yumi's conditional yes to "will you join my party?"; Voyage rolled the recruitment and Alistair failed his charisma check, but the scripted yes went through. Rule change, approved by the user: social contested actions (recruiting, persuading, bargaining, intimidating) are attempts Voyage rolls (AGY-3); a prompt about one is written as a conditional on the roll (FMT-10); the first pre-check question also asks about an NPC's answer to a contested ask (CHK-1); `check-prompt` warns when the input makes a contested ask and the prompt states an NPC's yes. The user chose to keep the scene as played (no story fix). At Luxcellia's switch, its overreach note ("she answers on her terms") becomes "she answers on her terms, after Voyage's roll".
- **Trial fixes** (sync names unmatched quests and shows compared values; the Studio cue skips what Voyage already has; negated "No skip" is not a skip; "as <PC> chose" is not a stated outcome) were built after the trial. An earlier attempt was interrupted; its patches were kept in the session scratchpad and reused.
- **Not rehearsed:** browser mode and a pivot (the user ended the trial).

## Phase 6 (2026-10-05)

- **Restore point.** `pre-redesign` is commit `ff3b65d` (all three old skills working, the new layout added beside them). The tag exists in this session's clone only: pushing it was refused by the session's git policy (HTTP 403), so the hash here is the record. The state before the revamp began is `13340a7`. To restore the old setup, check out `ff3b65d`'s files (the old skills never changed during the revamp).
- **Upload.** The user uploads `voyage-director` (version 2026-10-05.1) alongside the three old skills; each campaign switches on the user's word.

## Handoff 2 (2026-10-05): sessions, speed, models

`docs/revamp/handoff-2.md` adds four user-approved items; where it differs from the first handoff it wins. New rules SES-1 to SES-9 (`director/playbooks/sessions.md`) and TRIG-18; changed: LOOP-2, LOOP-6, ORCH-3, CHAT-1, CHAT-5, MENU-1, the director review's model.
- **Speed rule (HO2 §0) replaces D13's order.** A routine turn is one tool call before the prompt (write the prompt and run `check-prompt`), then the send, then `commit-turn`, which records, pushes, fetches and prints the next turn's brief. The first turn of a chat takes its brief from `resume`. Nothing on the clock touches the network.
- **D23. The planner writes only its own folder.** The handoff says the planner "writes arc plans". `arcs.json` holds both plans and turn-time arc progress the director records every turn; two sessions pushing changes to one JSON file risk git conflicts in the middle of play. So the planner commits its output as files under `campaigns/NAME/planner/` and the director session applies them at a break with the existing commands (SES-4). One writer of campaign data, as with sync (D15) and reviews (D8).
- **D24. The director review runs on Opus;** canon audit and act retro stay on Sonnet (HO2 §2).
- **D25. Model and effort are a recommendation** the user sets at session start (SES-8); a session cannot change its own effort. The Opus-versus-Sonnet trial comparison (HO2 §3) has not run: the user ended the phase 5 trial before handoff 2 arrived.
- **D26. Sync stays in the director session**, in both layouts, at session end. The export is attached in the director's chat, the dry run writes the digest that `sync --apply` checks, and both are campaign-data writes (SES-4). The planner launches the other one-off jobs (recaps, audits, reviews, Studio drafts) and commits their results as planner files.
- The build follows `docs/revamp/handoff-2-design.md` (session role in the session file, planner folder and commands, `commit-turn` tail, timing).
