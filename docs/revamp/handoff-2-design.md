# Handoff 2: design for the build

The interface that `tools/db.py` and the director docs both follow. Rules: SES-1 to SES-9 in `rule-inventory.md`; decisions D23 to D26 in `decisions.md`.

## Turn order (replaces D13's brief-first order)

On the clock (from the paste or "send" until the prompt is out), a routine turn is:
1. read the paste;
2. rule and draft from the brief already in context (printed at the end of the previous `commit-turn`; for the first turn of a chat, printed by `resume`);
3. one tool call: write the prompt file and run `check-prompt --paste paste.txt`;
4. send.

Off the clock: write the payload and run `commit-turn`, which records, commits, pushes, fetches, and prints the next turn's brief.

The slow path, run before drafting, is allowed only on the escalation triggers (TRIG-1 to TRIG-9) or a pivot's first turn: `turn-brief --full`, lookups, bible sections. `turn-brief --full` marks the turn as escalated for the speed figures.

On the clock nothing touches the network: `check-prompt`, `turn-brief` (plain and `--full`) and the lookups make no fetch, push, pull or ls-remote call. A local `git log` or `git ls-tree` is fine.

## Session role

- The session file (`.voyage-session.json`, or env `DB_SESSION_FILE`) holds `{"campaign", "set_at", "role"}`. `role` is one of `director`, `planner`, `all-in-one`, or absent (not chosen yet).
- `db.py use NAME --role ROLE` sets both the campaign and the role. `use --role ROLE` alone changes the role of the current choice. `use` shows both. `use --clear` removes the file.
- `--role auto`, for a first message of "send": `director` when planner output is waiting (see below), otherwise `all-in-one`. The role that results is what gets stored.
- `menu` and `resume` print `Session role: ROLE`, or `Session role: not chosen (director, planner or all-in-one: db.py use --role ROLE)`.
- Planner role, the write gate: every command that writes campaign data refuses with exit 4 (`EXIT_REFUSED`), saying "this session is the planner; only the director session writes campaign data. Put the output under campaigns/NAME/planner/ and run `db.py planner-save`." Lookups, `check-prompt`, `scan`, the `--dry-run` forms and `planner-save` still work. The planner never runs `sync` (see D26).

## Planner output

- Folder: `campaigns/NAME/planner/`. The planner session writes only here. The file name prefix gives the kind:

| Prefix | Kind | Shown as |
|---|---|---|
| `card-` | pressure card | card ready |
| `pivot-` | pivot mini-charter | pivot draft ready |
| `offramps-` | off-ramps | off-ramps ready |
| `arc-` | arc or act plan | arc plan ready |
| `review-` | director review findings | review ready |
| `audit-` | canon audit | audit ready |
| `retro-` | act retro draft | retro draft ready |
| `recap-` | recap | recap ready |
| `studio-` | Studio request draft | Studio draft ready |
| `note-` | anything else | note |

- "Waiting" means a file under that folder in the newest local view of `origin/main`, falling back to `HEAD` when there is no `origin/main` ref, whose git blob hash is not recorded in `state.planner_applied`. The check runs `git ls-tree`/`git show` locally and never touches the network. The folder's `README.md` is ignored.
- `db.py planner` (read-only) lists the waiting files: kind, path and first line. `--all` adds the applied ones. `--show FILE` prints a file from the same tree.
- `db.py planner-done FILE [FILE ...] [--note TEXT]` is the director session's writer. It appends `{file, blob, turn, at, note}` to `state.planner_applied`. A later edit of the file (a new blob) shows as waiting again. It is refused in the planner role.
- `db.py planner-save [-m TEXT]` (planner role, or all-in-one) commits only `campaigns/NAME/planner/` and pushes to `main`, rebasing on a rejected push as `push_main` already does. It is refused in a trial run and on a `VOYAGE_DATA` copy, like `save`.
- The brief line, in `turn-brief` and in the brief that `commit-turn` and `resume` print: `planner: card ready (card-wharf.md); pivot draft ready (pivot-yumi.md). Apply at a break, then db.py planner-done FILE`. With nothing waiting, or no planner folder, or no git, there is no line at all.

## commit-turn tail (after the prompt is out)

After recording and committing:
1. push, as now;
2. `git fetch origin main` with a timeout, unless the push just ran and succeeded. A failed or timed-out fetch prints one `WARN planner fetch failed (...); play on, the next turn retries` line and nothing more. Skipped (silent) when the data is not in git or is a `VOYAGE_DATA` copy;
3. Studio requests, as now;
4. last of all: `NEXT BRIEF (turn N+1):` followed by the same output `turn-brief` gives without a paste, planner line included.

`--dry-run` does none of the tail.

## Timing (SES-9)

- `check-prompt` records the time it first ran for the coming turn (state turn + 1) in `DATA/.turn-clock`. The name has no `.json` extension on purpose, so it stays out of JSON validation, and `.gitignore` keeps it out of git. Later runs for the same turn keep the first time. `turn-brief --full` adds `full_at`. Nothing is written in a trial run (`VOYAGE_TRIAL=1`).
- `commit-turn [--received TIME]` (ISO 8601, or `HH:MM`/`HH:MM:SS` meaning today in local time) writes `turn_log.timing = {"received": ISO or null, "checked": ISO or null, "committed": ISO, "escalated": bool}`. `escalated` is true when the payload's `turn_log.escalated` is true or `full_at` was recorded for this turn. It then clears the clock entry.
- The clock is keyed by the coming turn, so a run long before the real turn would give it a wrong time: `commit-turn` sets `checked` to null, and ignores `full_at` for `escalated` (unless the payload says so), when that time is more than `CLOCK_FRESH_MINUTES` (60) before the commit or after it.
- `resume` prints one line over the last 20 turns that have timing, routine and escalated apart: `Speed (last 20): routine 15 turns, input to check median 48s (9 with --received), check to commit median 95s; escalated 5 turns, ...`. A figure without data is left out; there is no line at all when no turn has timing.

## Agent launches (sessions playbook)

| Brief | Two sessions | All-in-one |
|---|---|---|
| charter, pivot, card, world, resume recap, review (all modes), dev, scaffold | planner session launches; output becomes a planner file | director at a break (scene end, session end), never on the clock |
| sync | director session, at session end (the export is attached there; `--apply` checks the digest the dry run wrote; D26) | the same |

The director review runs on Opus. Canon audit and act retro stay on Sonnet (D24).
