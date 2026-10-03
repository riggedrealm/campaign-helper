# Orchestration: payloads, briefs, failures

Read only when needed. The rules live in `.claude/skills/class2b-director/SKILL.md` (section "Orchestration (hybrid)"). Run commands from the repo root; `db.py` is `python3 tools/db.py --campaign classroom-2b` (the old `campaigns/classroom-2b/tools/db.py` path is a stub for the same thing).

The main chat does the judgment work. Recording is deterministic: one `db.py record payload.json` run in the background, not a subagent. A Planner (Opus) prepares showcase scenes; Cast subagents (Sonnet) are optional.

## 1. The record payload

`record` applies a whole turn under the write lock, all or nothing. It calls the same functions as the single commands, so every validator applies (places, names, ladder gates, quest states).

```json
{"turn": 3,
 "ops": [{"op": "...", "args": {"...": "..."}, "evidence": "..."}],
 "turn_log": {"inputs": "...", "summary": "...", "prompt": "...", "slips": "...", "notes": "..."},
 "save": true}
```

- `turn` must equal `state.turn + 1`. A retry of an applied turn is refused, so it cannot double-apply.
- Each op has `op` (name), `args` (the command's arguments by name; a list is allowed for `text`), and `evidence` (a quote or paraphrase from the story output). The turn is the payload's `turn` (an op may override it with `"turn"`). The scene follow-ups (`scene-obstacle`, `scene-surprise`, `scene-end`) may omit `evidence`.
- `turn_log` is applied last. `inputs`, `summary` (two lines max) and `prompt` are required (`"none"` for turn 1). `prompt` and other text values accept `@file`. The prompt must fit the prompt limit (`db.py state`).
- `slips` entries are tagged `fact|invention|teleport|outcome|dropped`, format `category: text`, separated by `;` (e.g. `"teleport: Griffin in garden; dropped: Mio's line"`); `resume` shows the top repeat categories.
- `save: true` runs `save` after verification. On a `VOYAGE_DATA` (alias `CLASS2B_DATA`) copy the save step is skipped.

| Op | Args |
|---|---|
| `add-npc` | `name`, optional `alias gender age power visual personality location area type faction` |
| `npc-seen` | `name` |
| `npc-note` | `name`, `text` |
| `agenda` | `name`, `want` and/or `next` |
| `fact` | `subject`, `text` |
| `pc-add` | `name`, `player`, `room`, optional `location area activity pronouns power background notes` |
| `pc-sheet` | `name`, at least one of `pronouns power background notes` (from the user only) |
| `pos` | `pc`, `location`, `area`, optional `activity placement` |
| `time` | any of `day block clock allow_backward` |
| `quest-start` | `name` |
| `quest-obj` | legacy, not used in play (Voyage owns quest progress) |
| `quest-end` | legacy, not used in play |
| `ledger` | `delta` (`"+3"`), `reason` |
| `clock-add` / `clock-done` | `name`, `due_day`, `note` / `name` |
| `thread-reveal` | `name`, `step`, optional `gate_met force` |
| `add-area` | `location`, `area_id`, `desc`, optional `paths` |
| `scene-start` | `name`, `budget`, optional `location area card` (text or `@file`) |
| `scene-obstacle` / `scene-surprise` / `scene-end` | `text` / (`force`) / none |
| `feedback` | `kind` (`scene` or `act`), `best` and/or `drag`, optional `notes scene`; no `evidence` needed. Put it before `scene-end` so the scene name is stored |
| `studio-request` / `studio-done` | `kind target text_file [why allow]` (turn from the payload) / `id [batch location area_id desc paths fact]`; see `docs/studio.md` |

### What `record` does

1. Validates the whole payload against current data (a simulated run, nothing written) and fails on the first bad op.
2. Takes `data/.lock`, snapshots the mutable files to `data/.snapshots/before-turn-N` (last 5 kept).
3. Applies the ops in order, then the turn log, then verifies every JSON file parses and `state.turn == N`.
4. On any error restores the snapshot and exits non-zero naming the failing op.
5. Runs `save` if asked. A push failure keeps the local commit and the applied data and exits 5.

`record payload.json --dry-run` stops after step 1 and prints the plan. Exit codes: 0 ok, 1 or 2 or 3 bad payload or op, 4 refused (wrong turn, trial run), 5 saved locally but push failed, 6 lock busy, 7 stale lock.

### Worked example: a turn

Griffin follows Tatsuya into the kitchen, dinner is announced, a new housemate appears, a quest starts, and a scene opens with a Planner card. State was at turn 1.

```json
{"turn": 2,
 "ops": [
  {"op": "pos",
   "args": {"pc": "Griffin", "location": "Sakura Lane Sharehouse", "area": "shared-kitchen", "activity": "helping Tatsuya with dinner"},
   "evidence": "Griffin follows Tatsuya into the kitchen"},
  {"op": "fact",
   "args": {"subject": "dinner", "text": "Move-in dinner is at 18:00 in the shared kitchen."},
   "evidence": "Tatsuya: 'dinner's at six'"},
  {"op": "add-npc",
   "args": {"name": "Haruna Ito", "gender": "female", "age": 16, "location": "Sakura Lane Sharehouse", "area": "shared-lounge", "personality": "shy, tidy"},
   "evidence": "Voyage introduces a shy housemate arranging cushions"},
  {"op": "quest-start",
   "args": {"name": "Move-In Weekend"},
   "evidence": "Tatsuya hands Griffin the chore rota"},
  {"op": "scene-start",
   "args": {"name": "Move-In Dinner", "budget": 6, "card": "@/tmp/scratch/card.txt"},
   "evidence": "dinner prep begins"}
 ],
 "turn_log": {
  "inputs": "Griffin: i help Tatsuya in the kitchen",
  "summary": "Tatsuya set up dinner; Haruna Ito appeared in the lounge; the chore rota was handed out.",
  "prompt": "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, evening. Tone: warm, busy.\nCrew: Tatsuya counts bowls, hands Griffin the chore rota, chatting too fast to hide nerves. Haruna Ito arranges cushions in the lounge, shy.\nWorld: Mio's rig hums behind the loft door; the rice cooker jams.",
  "slips": "",
  "notes": "card stored"},
 "save": true}
```

Output on success is about ten lines: one line per op, the turn line, a verification line and the save lines.

## 2. Planner brief template

Spawn with `Agent`, `model: "opus"`, read-only. Fill the braces. Launch it in the background two turns before the previous scene's budget ends, so the card is ready when needed. Review the card before use (see the failure and review notes below), then `scene-start ... --card @card.txt`.

```text
You are the Planner for the Class 2B campaign (repo root: {repo}). Prepare ONE scene card for the director.

Scene: {name} at {location}/{area}. Why now: {act turn | showcase fight | milestone | twist reveal | thread outgrew a side quest}. Turn budget: {N}.
Recent player feedback (what landed, what dragged; include the last act retro): {paste the last scene and act feedback entries from `resume`/`state`}. Use it: more of what landed, less of what dragged.

Read first (lookups only, run from the repo root as python3 tools/db.py --campaign classroom-2b <cmd>):
- bible {section}   (and bible 13, bible 14 for obstacles and budgets)
- state (its `feedback` list) or `resume` for the last feedback entries
- brief <name> for each NPC in the scene: {NPC list}
- thread "<name>" for each ladder involved: {threads}
- canon <topic>, state, loc "{location}" {area}

Hard rules:
- Read-only. Run lookup commands only. No record, turn, save or any update command, no file edits, no git, no commits.
- Existing locations and areas only. Never invent a place; use loc to check.
- Reveal at most ONE reveal-ladder step, and only the next hidden step the ladder shows as revealable now. Nothing past a gated milestone.
- No player-character outcomes and no combat outcomes: Voyage rolls combat. State NPC actions and enemy rules only.
- Main NPCs follow their brief: voice, psychology, current act beat, "won't do yet". Hidden facts stay out of dialogue unless that ladder step is the one you reveal.
- No invented canon that contradicts canon or state. New minor NPCs are allowed at most one, with an intro line of 90 characters or fewer.

Output: one card of about 600 words or fewer, with these headings only:
1. Opening shot (2 sentences)
2. World moves (exactly three, each something an NPC or the world does on its own agenda)
3. Surprise (exactly one)
4. Key NPC lines (one or two short lines per NPC who speaks, drawn from their bible voice)
5. The decision the scene ends on (what the players choose between, without scripting their choice)
6. Obstacle list (ordinary obstacles, at most one used per beat, in order)
7. Ladder step it may reveal (one step: thread name and step number, or "none")
Return only the card.
```

Director review before use: check the ladder step with `thread "<name>"` (act and gate), every place with `loc`, each fact against `canon`, and that no line states a player outcome. Edit or discard; the Planner never writes.

## 3. Cast brief template (optional, default off)

For set pieces with four or more main NPCs speaking, or when the user says "full cast". One Sonnet subagent per NPC, in parallel, `model: "sonnet"`, read-only.

```text
You write one line for {NPC} in the Class 2B campaign (repo root: {repo}).
Run: python3 tools/db.py --campaign classroom-2b brief "{NPC}"   (lookups only; no updates, no files, no git).
Situation: {the beat in two sentences, who is present, what just happened}. The line is for a Voyage steering prompt.
Write what {NPC} wants or does right now, in their own voice, driven by their want, fear and current act beat. Respect "won't do yet". Never state a player-character outcome. Keep hidden facts out unless the brief marks the step revealed.
Return exactly one line, 150 characters or fewer, in this form:
Crew: {short name} <what they do or say>
```

The main chat merges the lines, trims to the prompt limit, runs `check-prompt`, and writes the final `Crew:` line.

## 4. Failure playbook

| Symptom | Do |
|---|---|
| Record exit 3, 2, 1 | Bad payload or op; the message names it and nothing was applied. Fix the payload and rerun. |
| Record exit 4, "payload turn is X but the next turn is Y" | The turn was already recorded, or the payload number is wrong. Check `db.py resume`; do not rerun an applied turn. |
| Exit 6, "another write is in progress" | A writer is running. Wait for its completion notice; do not start another write. If it looks hung (over 10 minutes), kill that pid and run `db.py recover`. |
| Exit 7, or `resume`/`state` prints "stale write lock" | A writer crashed. Run `db.py recover`: if a crashed `record` left the data half-applied it restores the pre-turn snapshot, otherwise it only clears the lock. Then rerun the payload. |
| Exit 5, "saved locally, push failed" | The data is applied and committed locally. Do not rerun the payload. Run `db.py save` when the network is back (it retries and rebases). |
| A turn was recorded wrongly | `db.py undo-turn N` restores the snapshot taken before turn N (last 5 turns) and rewinds `state.turn`. Fix the payload, record again, then `db.py save` to commit the rewind. |
| Planner card breaks a rule | Do not use it. Rewrite the weak parts yourself or reuse an earlier card; nothing was written by the Planner. |
| Trial run | Never launch `record`; `record payload.json --dry-run` is allowed and writes nothing. |

Snapshots (`data/.snapshots/`) and the lock file (`data/.lock`) are git-ignored scratch files; never commit them.
