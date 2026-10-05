# Handoff 2: session layout, models and effort (addendum for the revamp orchestrator)

Written 2026-10-05 from the planning chat. It adds four user-approved items to `docs/revamp/handoff.md`. Checked against `main` at `497944b`: the session layout, the review model and the effort rule are not in the repo yet; the speed rule (section 0) is partly there as D13. Commit this file as `docs/revamp/handoff-2.md`, record each item in `docs/revamp/decisions.md`, and fold the work into the phase you are in. Where this file and the first handoff differ, this file wins.

Constraint to respect: the always-loaded layer is already at about 16.5 KB (D18, accepted by the user). Put the new rules in a playbook and the agent briefs. `core.md` and the bootstrap should gain no more than a menu line and a trigger row.

## 0. The speed rule: the prompt comes first, and fast

The user's rule, stated 2026-10-05: **turning the player input and Voyage's output into a prompt must be as quick as possible, unless the story requires more.** Anything that can run in another session or after the prompt is out must do so. This rule governs the other sections of this file and the turn loop in `core.md`.

**On the clock** (from the paste or "send" until the prompt is out) a routine turn does only this:

1. Read the input and output (already in the chat in paste mode; one page read in browser mode).
2. Rule and draft from what is already in context: the brief printed after the previous turn, and the always-loaded rules.
3. One tool call: write the prompt file and run `check-prompt`. Fix a FAIL and rerun; WARNs never force a rewrite.
4. Send the prompt (`SendUserMessage` in paste mode per D13; the submit in browser mode).

**Off the clock**, after the prompt is out: `commit-turn`, the push, the planner-output fetch, nudges to the planner, Studio batches (D14, except a story fix), and the brief for the next turn.

What this changes:

- **The brief is prepared ahead.** `commit-turn` ends by printing the `turn-brief` for the next turn, so the director already holds it when the next input arrives. No brief call on the clock. A routine turn therefore costs one tool call before the prompt and one after it. The first turn of a chat gets its brief from `resume`.
- **The pre-printed brief can be stale by one output.** It is built from the scene as recorded, before Voyage's newest output. That is acceptable on a routine turn. A new name, a new place, a day change or a fight opening in the newest output is exactly what triggers the slow path.
- **Nothing on the clock touches the network**: no fetch, no push, no subagent, no message that waits for a reply. The planner-output check moves into `commit-turn`'s tail, and its one-line result appears in the next brief.
- **The slow path is the exception and is named.** The story requires more only on the escalation triggers the turn loop already lists (new NPC or place, scene at budget, fight or fight opening, milestone or ladder reveal, consent or romance edge case, power claim, story fix, broken canon, a pivot's first turn). Then the director may run `turn-brief --full`, lookups and bible sections before drafting. Nothing else justifies a lookup before the prompt.
- **Foreseeable heavy turns are prepared in advance.** Showcase cards, pivot drafts and off-ramps are written by the planner before they are needed (two turns before a scene budget ends, at arc approval and midpoint), so even a big turn is mostly drafting from a ready card.
- **Deliberation stays short on routine turns**: the ruling in two or three sentences, one handle, one gesture, one world move, as `fast-turn.md` already said. The reply is the prompt and at most one extra line.
- **Measure it.** `commit-turn` records two timestamps per turn in the turn log: when the turn's `check-prompt` first ran and when `commit-turn` ran. Add an optional `--received` time for when the input arrived, if the client can supply it. `resume` shows the median for the last 20 turns, split into routine and escalated turns. Without a number, "fast" cannot be checked.

Add to the phase 4 tests: `commit-turn` prints the next brief; no command in the routine on-the-clock path performs a network call. Add to "what done means": a routine turn needs one tool call before the prompt is out.

## 1. Play runs as two sessions, with an all-in-one fallback

The user asked whether play should use several sessions that message each other. Decision after review: **two sessions**.

| Session | Model | Job |
|---|---|---|
| **Director** | the user's play model (section 3) | The turn loop only: read, rule, draft, check, submit, bookkeep. The only writer of turn data (`commit-turn`). |
| **Planner** | Opus | Everything off the clock. Holds the arc (charter, fronts, off-ramps, hidden fields); drafts pivot mini-charters and pressure cards; runs midpoint and drift checks; holds planning conversations with the user; launches the Sonnet subagents for sync, Studio batches, recaps and canon audits, and the director review. |

Why two, not one: a planner subagent launched from the director session can hold up the turn, and planning conversations fill the director's context. Why not three: sync, Studio batches, recaps and audits are one-off jobs with nothing to remember, so a standing third session adds a clone and coordination for no gain; the director review must be a fresh agent each time to stay independent. The planner session is already off the clock, so it launches those as subagents.

Rules:

- **The repo is the channel; messaging is only a nudge.** Each session has its own clone. The director pushes every turn. The planner pulls, reads the new turn log, and commits its output as files (cards, mini-charters, off-ramps, sync reports) under one known path. After the prompt is out, `commit-turn` fetches, and the next brief prints one line when new planner output is waiting ("planner: card ready", "planner: pivot draft ready"). Play must never depend on a message arriving or being answered: a cloud session may receive messages without being able to reply.
- **Nudges from director to planner**: scene end, day change, a committing input, session end. One line each. A missed nudge costs nothing, because the planner can also poll the turn log.
- **Writes do not overlap.** The director writes turn data. The planner writes arc plans and its own output files. Anything that changes turn data (a sync patch, a review finding) is a proposal that the director session applies. This keeps D8 and D15 intact: the sync subagent still writes only its digest, and the director's main chat still records review findings.
- **Session role.** At chat start the menu asks which role this session plays: director, planner, or all-in-one. Each role reads only its own playbooks. "send" as the first message means director (or all-in-one when no planner output path has been touched this session); do not add a round trip.
- **All-in-one is the fallback and must work fully.** With one session, the director launches the planner jobs as subagents at breaks (scene end, session end), as `core.md` ORCH-1 already describes. Off-ramps stored in the data are what keep a plan ready when no planner session is running.
- **Spoilers.** Hidden plan material is worked on in the planner session, which the user need not open during play. Everything user-facing still passes `db.py scan`.

Work this needs:

1. A new playbook, `director/playbooks/sessions.md`: the roles, what each reads and writes, the nudges, the planner output path and file names, the all-in-one fallback. Give its rules ids like the others.
2. `commit-turn` tail: the fetch and the one-line "planner output waiting" check, run after the prompt is out (section 0) and shown in the next brief. It must stay silent when there is no planner session, and a failed fetch only warns (offline play).
3. `menu`: the role choice, stored in the session file next to the campaign.
4. Agent briefs: say which session launches each one in the two-session layout (planner) and in all-in-one (director, at a break).
5. Tests: the brief line appears only when a new planner file exists; a failed fetch only warns; the role is stored and read back.
6. Trial (phase 5): rehearse one pivot and one showcase card in the two-session layout on data copies, and the same in all-in-one.

## 2. The director review runs on Opus at scene end

`director/agents/review.md` says Sonnet in all three modes. Change the **director review** mode to **Opus**. Canon audit and act retro stay on Sonnet.

Reason: the review is the main safety net for the agency rules. The `check-prompt` agency checks only warn, and one rule ("an NPC handed over an answer or moved a goalpost the player had met") cannot be tested by a tool at all. That is a judgement about story, and it is the model's judgement that catches it. It runs once per scene, off the clock, so the cost is small.

## 3. Model and effort for playing a turn

`core.md` says the turn stays "on the current model", and the new text has no effort rule (the old skills had "Effort medium; high only for twist reveals, showcase finishers, finales", which appears to have been dropped). Add a short recommendation; the user still chooses the model per session, and the skill never switches it.

Recommended, to be stated as a recommendation and not enforced:

- **Routine turns: Opus at medium effort.**
- **Escalated turns: Opus at high effort.** Use the escalation triggers the turn loop already has: a fight or fight opening, a twist or ladder reveal, a milestone, a finale, a consent or romance edge case, a power claim, a pivot's first turn, broken canon.
- **Never low effort.** The agency pre-check is done by the model; low effort is where a stated player outcome or an over-long `Cut:` slips through.
- **Sonnet at medium effort is an acceptable fallback** for a long quiet stretch (downtime, errands) when speed or usage matters more. Switch back for any escalated turn.

Speed (section 0) is now a criterion alongside quality. The skill cannot change the model per turn, so the per-turn lever is how much the director looks up and deliberates, which section 0 fixes; the session model is the user's one choice per sitting. In the two-session layout the heavy story thinking is done ahead by the Opus planner, which is what would let the director session run a faster model.

Reason for the default: a turn is small in volume but dense in judgement. It rules player inputs under the agency rules, keeps each NPC's voice and growth, and packs it into 840 characters; a weak prompt becomes story that cannot be taken back. One prompt per human turn makes the cost per turn low, so the stronger model is worth it. Medium effort keeps the wait after "send" short; the lean brief and `check-prompt` carry the mechanical checks, so extra thinking adds little on a routine turn.

This is the planning chat's opinion, not a measurement. In the phase 5 trial, play the same rehearsal turns on Opus medium and Sonnet medium and compare three things: seconds from input to prompt (section 0's timestamps), slips per turn, and the director-review findings. If Sonnet is clearly faster with no more slips, make Sonnet at medium the default for the director session in the two-session layout and keep Opus for all-in-one; record the result in `decisions.md` and adjust the recommendation if Sonnet holds up.

Where it goes: one row in the `core.md` orchestration table or a line in `sessions.md`. If effort cannot be set from inside a session in the user's client, say so and give the recommendation as a setting for the user to choose at session start.

## 4. Stops

No new stop for the user. Report these three items in your next phase report: what was committed, and the trial comparison in section 3 once phase 5 has run.
