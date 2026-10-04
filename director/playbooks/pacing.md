# Pacing: scenes, acts and days

Open this playbook when a new beat starts with no scene open, a scene reaches its budget or meets its goal, the in-game day changes, or an act ends.

## Opening a scene

When a new beat starts and no scene is open, add a `scene-start` op to that turn's payload. Give it a name, a turn budget from the table below, the place (location and area; it defaults to the first player character's place), a variety tag in `kind` (see Variety), and an optional pressure card. <!-- SCN-1 -->

## Default budgets

A budget counts director turns from the scene's first prompt. Use these unless the campaign's arc bible sets its own:

| Scene type | Budget |
|---|---|
| Fights | 4 to 8 turns |
| Big emotional scenes (confessions, splits, verdicts, results) | 3 to 6 turns |
| Investigation | 1 to 2 turns |
| Travel and waiting | 0 (cut) |
| Arrival, admin, move-in or errand scenes | 2 turns at most |

A campaign's arc bible may set per-act budgets for its named beats; `db.py bible budgets` prints the campaign's table. Treat every budget as a ceiling, not a target. <!-- SCN-2 -->

When and how to cut at budget, or when the scene's goal is met, is in `core.md`, Prompt format (CUT-4, CUT-5).

## Closing a scene

Close a scene with a `scene-end` op in the payload of the turn it ends. <!-- SCN-3 -->

At scene end the director review in `core.md`, Bookkeeping (REVIEW-1), may be due.

## Obstacles and surprises

Use at most one ordinary obstacle per beat, and record it with `scene-obstacle`. Keep obstacles ordinary: a queue, a delay, a closed door. Drama comes from people. <!-- SCN-4 -->

Use one surprise per scene, and record it with `scene-surprise`. Make it small most of the time (a note, a delay, a visitor, a malfunction, a stray memory) and save the larger ones for act turns. <!-- SCN-5 -->

## Scene feedback

Do not ask the user for scene feedback. If the user raises it themselves, record it with a `feedback` op of kind `scene` (`feedback --kind scene` on the command line), placed before the `scene-end` op so the scene's name is stored. <!-- SCN-6 -->

## Variety

Give every scene one variety tag when you open it, in the `kind` argument of `scene-start`: `fight`, `talk`, `explore`, `mystery` or `downtime`. When three scenes of one kind run in a row, `turn-brief` shows it on its `Variety:` line ("three talk scenes in a row"), and `scene-start` without `kind` leaves the scene untagged. Two variety or boredom flags (shorter player inputs, repeated skips, a drag note in the latest feedback) call for a one-line check with the user, which is the one extra line `core.md`, Reply, allows, and for more variety in the next pressure card. At retros, compare the mix of tags with the play-style pillars in session zero, using the mapping below; `db.py plan-brief` prints the mix. <!-- SCN-7 -->

| Variety tag | Session zero pillar |
|---|---|
| `fight` | combat |
| `talk` | social |
| `explore` | exploration |
| `mystery` | mystery |
| `downtime` | none; report it on its own |

## Act end

When an act ends, write a short retro yourself: what landed, which threads went cold, and, if the campaign has a hidden-score module, the score's band (see the hidden-score playbook). A read-only subagent may draft it first with `director/agents/review.md` (act retro mode); you still write the final retro. Log it with a `feedback` op of kind `act` (`feedback --kind act` on the command line) using `best`, `drag` and `notes`. The retro feeds the next act pitch. Acts exist whether or not arc functions are on, so write the retro either way. Do not ask the user for it: the retro question belongs to the planning session (see the arc-planning playbook, ARC-6). <!-- SCN-8 -->

## Days

Neglected threads go cold after about 7 in-game days: the world moves each one a step. Nothing the players earned is lost. <!-- WLD-2 -->

When the day changes, run `db.py day-turnover`. The `time` command prints "Day changed (Day N -> Day M): run `db.py day-turnover`" when the day goes up (so does a `time` op in a payload), and `--day N` names the day to check (the default is the current day). The command is read-only. It lists only what applies on the new day: open clocks due on or before it, milestones on it, threads going cold (7 or more days without story contact), the next move of every front of the live arc and of each parked arc, and main NPCs with an agenda who have been off screen for 3 or more days, each with the agenda's next move. Anything with no day on record is counted, not guessed, and the output never shows ladder steps or hidden scores. Play what it lists through `World:` lines over the next turns; each prompt still carries one world move. <!-- WLD-3 -->

## Where related rules live

- `core.md`, Prompt format: how `Cut:` behaves at budget (CUT-4), when a goal is met (CUT-5), and skips (CUT-2 and CUT-3).
- `core.md`, Chat and orchestration: run `preflight` at each act start (CHAT-4).
- The arc-planning playbook: the planning offer at an act end (ARC-5) and pressure cards (ARC-14).
- The fights playbook: a fight ends when it is decided, never padded to its budget (FGT-6).
