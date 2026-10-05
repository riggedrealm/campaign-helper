# Sessions: director, planner and all-in-one

Open this playbook at chat start when you choose the session's role, when the brief shows a planner line, and when you launch or apply planner work.

## The two roles

Play runs as two sessions. The director session runs the turn loop only (read, rule, draft, check, send, `commit-turn`) and is the only writer of turn data. The planner session runs on Opus and does everything off the clock: arc and act plans, pivot drafts, pressure cards, off-ramps, midpoint and drift checks, and planning talks with the user. It also launches the one-off subagents (see "Who launches what"). All-in-one, one session doing both jobs, is the fallback, and it must work fully. <!-- SES-1 -->

## Choosing the role

At chat start the menu asks which role this session plays. Run `db.py use NAME --role ROLE`, with ROLE `director`, `planner` or `all-in-one`; `use --role ROLE` alone changes it. When the first message is "send", run `use NAME --role auto` and play on: it stores `director` when planner output is waiting and `all-in-one` otherwise, so there is no extra round trip. Each role reads only its own playbooks:

- Director: the playbooks its triggers open in `core.md`, except `arc-planning.md` outside "In play"; and this file.
- Planner: `arc-planning.md`, `pivot.md`, `reveals.md`, `studio.md`, `pacing.md` (act end and budgets), this file, and the agent briefs it launches. Never `browser.md`, and it never plays a turn.
- All-in-one: both lists. <!-- SES-5 -->

## The repo is the channel

Each session has its own clone. The director pushes every turn. The planner pulls, reads the new turn log and saves its output as files under `campaigns/NAME/planner/`, named by kind: `card-`, `pivot-`, `offramps-`, `arc-`, `review-`, `audit-`, `retro-`, `recap-`, `studio-`, and `note-` for anything else, then a short slug (`card-wharf.md`). It commits and pushes them with `planner-save -m TEXT`. After the prompt is out, `commit-turn` fetches, and the next brief shows one line when a file is waiting: `planner: card ready (card-wharf.md). Apply at a break, then db.py planner-done FILE`. With nothing waiting there is no line. A failed fetch only warns; play on. Play never waits for a message or its answer. <!-- SES-2 -->

Nudge the planner with one line at a scene end, a day change, an input that commits the PC to a new goal, and session end. Send it as a one-line message through whatever channel the user uses between the sessions. A missed nudge costs nothing: the planner can poll the turn log. <!-- SES-3 -->

## Writes do not overlap

The director session is the only writer of campaign data, arc plans included. The planner writes only its own folder. In the planner role every command that writes campaign data refuses with exit 4 and points to `planner-save`; lookups, `check-prompt`, `scan` and the `--dry-run` forms still work.

Apply planner files in the director session at a break, never on the clock. `planner` lists the waiting files and `planner --show FILE` prints one. Review it as its brief's "Afterwards" says, then apply it with the existing commands: `arc-plan --file`, `arc-offramps --file`, `scene-start --card`, `arc-adopt`, `review-add`, `studio-request`. Then run `planner-done FILE` (with `--note TEXT` for a file you discarded). A later edit of the file shows it as waiting again. A review finding or a sync patch is likewise a proposal the director applies. Sync itself stays in the director session in both layouts, at session end: the export is attached there, and the dry run writes the digest that `sync --apply` checks. <!-- SES-4 -->

## All-in-one

With one session, launch the planner's jobs as subagents at a break: a scene end, session end, or right after a `commit-turn` when a playbook times a launch (a showcase card two turns ahead, ARC-14; a pivot draft, PIV-4). Never launch one on the clock. Off-ramps stored on the arc keep a plan ready when no planner session runs. You need no planner files: file each result with the command its brief names. <!-- SES-6 -->

## Who launches what

| Brief | Two sessions | All-in-one |
|---|---|---|
| charter, pivot, card, world, resume recap, review (all modes), dev, scaffold | the planner session launches it; the output becomes a planner file | the director, at a break, never on the clock |
| sync | the director session, at session end | the same |

## Spoilers

Hidden plan material is worked on in the planner session, which the user need not open during play. Everything user-facing still passes `db.py scan`, in either session. <!-- SES-7 -->

## Model and effort

A session cannot change its own model or effort, so this is a recommendation the user sets at session start; the skill never switches it. Routine turns: Opus at medium effort. Escalated turns: Opus at high effort. They are TRIG-1 to TRIG-9 in `core.md` (a new NPC or place, a scene at budget, a fight or its opening, a milestone or ladder reveal, a consent or romance edge case, a power claim, a story fix, broken canon) and a pivot's first turn. Never low effort: the agency pre-check is the model's job. Sonnet at medium effort is acceptable for a long quiet stretch (downtime, errands); switch back for any escalated turn. The planner session runs Opus. <!-- SES-8 -->

## Timing

Speed is measured. `check-prompt` notes when it first ran for the coming turn, and `turn-brief --full` marks the turn escalated. `commit-turn` writes the turn's timing; pass `--received TIME` when you know when the input arrived. `resume` prints one `Speed (last 20):` line with the medians, routine and escalated apart, and the session role (`Session role: ROLE`). <!-- SES-9 -->
