# Orchestration: payloads, briefs, failures

Read only when needed. The rules live in `.claude/skills/luxcellia-director/SKILL.md` (sections "Orchestration" and "The turn loop"). Run commands from the repo root; `db.py` is `python3 tools/db.py --campaign luxcellia`.

The main chat does the judgment work; recording is deterministic and runs inside the second call. A Planner (Opus) prepares showcase scenes; Cast subagents (Sonnet) are optional.

## 0. Normal turns: prep, commit-turn, wrap-up

Two shell calls per turn, one process each, no background jobs (in a chat each call is a round trip, a background process can die when its call ends, and the container can reset between sessions).

**Call 1: `db.py prep --paste paste.txt [--names A,B] [--full NAME]`** (read-only, about 60 lines). The user's last exchange is saved to `paste.txt`. It prints: the state line (turn, day, time, act, PC positions, "unpushed: N"), the open scene (budget used, obstacle and surprise used), due or overdue clocks and the next milestone, pending Studio requests, and the character budget left for a prompt. Present NPCs are the names found in the paste (full name, first name, surname, title-less form or an alias), the NPCs stored in `scene.present` last turn, and `--names`. Each main NPC gets a compact brief: voice, want, current act beat, won't-do-yet, and two expression picks that rotate (the last 2 turns' picks for that NPC are not repeated); other NPCs get one line. Then places named (location and area validity), active quests named, new capitalized names not in the database, and the LIVE CHECKLIST: canon facts and traps about the present names and places, the next hidden ladder step of each present NPC's thread (never its text; only an already revealed step's text is shown), repeat-slip categories and a reminder when one is common, scene budget warnings, planned NPCs needing their `intro_line`, a split-party header, spotlight due. `--full NAME` appends the full `brief`. A short name that fits two people prints `WARN: AMBIGUOUS name X: A | B`.

**Fights.** `prep` adds a LIVE CHECKLIST line when the open scene looks like a fight (name or card mentions fight, battle, combat, brawl or ambush, or a `fight` flag on the scene): "fight status unknown: write conditional prompt", or your pasted `fight status:` line echoed. The director cannot see Voyage's combat state, so fight prompts are conditionals on it (see SKILL.md, Fights).

**Call 2: write `prompt.txt` and `payload.json`, then `db.py commit-turn --prompt prompt.txt --payload payload.json`** in the same call (`--dry-run` checks only; `--push-every N` overrides `campaign.json` `push_every`, default 5).

1. Runs the `check-prompt` logic. Any FAIL (length, labels, hidden ladder-step words) is printed and the command exits 1, writing nothing. Name warnings (unknown, ambiguous, "use full name") never block.
2. Normalises and validates the whole payload, collecting every problem in one list (exit 2, nothing written; exit 4 if the turn is not `state.turn + 1`, exit 8 if off `main`).
3. Applies it exactly like `record` (lock, snapshot, verify, restore on any error), logs `turn_log.prompt` from the prompt file, stores `scene.present` (the NPCs named in the prompt's `Crew:` line, or the payload's `"present": [names]`) and the expression rotation.
4. `git commit`s `data/*.json` locally every turn; pushes (synchronously, with retries) only when `push_every` commits are unpushed. A push failure prints a warning and still exits 0: the data is saved and committed.
5. For each `studio-request` op it prints the new request's batches in full (same text as `studio-show`) so the reply can carry them.

The payload is the `record` payload (section 1) without `prompt` and `save` (both ignored), plus the optional `present`. Forgiving normalisation, each change printed as `~ ...`: a missing `turn` becomes `state.turn + 1`; op names such as `studio_request` become `studio-request`; arguments given beside `op` move into `args`; `time` accepts words (dawn, morning, late morning, noon, afternoon, dusk, sunset, evening, night, late night, midnight, small hours and similar) and maps them to the campaign's time blocks (and a clock inside the block), `"Day 5"` becomes 5, `"6:30 pm"` becomes `18:30`.

```json
{"ops": [
  {"op": "time", "args": {"block": "Dusk"}, "evidence": "the lanterns come on along the street"},
  {"op": "fact", "args": {"subject": "cart", "text": "Yumi parks her cart beside the posting board."}, "evidence": "Yumi leaned over her cart"},
  {"op": "scene-obstacle", "args": {"text": "guild queue"}},
  {"op": "studio-request", "args": {"kind": "story-fix", "target": "Turn 3", "text_file": "fix.txt"}, "evidence": "Voyage let Serika speak to the player"}],
 "turn_log": {"inputs": "Aiko: asks Yumi about the courier", "summary": "Yumi sells Aiko a charm and mentions the courier.",
              "slips": "outcome: Aiko is said to succeed", "notes": ""},
 "present": ["Yumi Aokiba"]}
```

Output: `~ op 1 (time): block "Dusk" -> "Evening" (clock 18:30)`, one line per op, `git: committed "<name> save: turn 4"; unpushed 2/5`, then the Studio batches.

**`db.py wrap-up`** (session end, or before a fresh chat): commits stray data changes, pushes every unpushed commit (synchronously, retries), prints pending Studio requests and open items, and ends with `safe to close` or the failure (exit 5: the commits are kept; rerun later). `resume` and `prep` show `unpushed: N`.

Names: cast and world NPC entries may carry `aliases` (list); first name, surname and title-less forms (titles are `name_skip_tokens` in `campaign.json`) are derived automatically unless two people share them (then WARN AMBIGUOUS; an explicit alias or the full name settles it). `"use_full_name": true` on an entry (a canon trap) makes a short form WARN `use full name` instead of passing silently. `campaign.json` `canon_traps` (`[{"match": ["Serika"], "text": "..."}]`, empty `match` = always) feed the LIVE CHECKLIST.

## 0b. Clarity rules (surface goal, handle, pull-forward, premise)
Added 2026-10-03.7 after a playtest where a private-board errand had no visible goal, Voyage changed the job's premise mid-scene and the director let it pass, and the one NPC who could explain was ladder-gated to a later act.
1. **Surface goal.** Every quest, errand or contact the director seeds or plays states a visible goal in the fiction: what the player is doing, for whom, the reward, the risk. The secret purpose may stay hidden; the surface goal may not. Put it in the quest's `seed_line` (or a `surface_goal` field) so `prep` can print it. `prep` shows the goal line in the LIVE CHECKLIST for each active quest mentioned in the paste or tied to the open scene's place, and says "no surface goal set" when neither field exists: fix it in the next prompt.
2. **Silent check question.** Before writing the prompt: "Can the player say what they're doing next and why?" If not, the next prompt gives a handle through an NPC (someone states the job, the deadline, the price) or the world (a sign, a summons, a clock). Never a menu, never the player's thoughts.
3. **Player-driven pull-forward.** When the player reaches a thread early, its next ladder step may move up ONE act if the scene needs it to make sense. `thread-reveal NAME STEP --player-driven --evidence "..."` (also `"player_driven": true` on the op in a record or commit-turn payload) allows a step whose act is exactly one later than the current act, only when it has no unmet gate and every earlier step is revealed. It records `player_driven: true` and the evidence. Two or more acts early, a gated step (no `--gate-met` yet) or skipped earlier steps are still refused and need `--force`. Milestones stay fixed.
4. **Changed premise is a load-bearing slip.** If Voyage changes a job's premise or terms, a quest's giver or goal, or what an NPC asked for, treat it as load-bearing: an immediate Studio `story-fix` for the latest turn before the next prompt (`docs/studio.md`, Story fixes). Never let it pass as harmless.

## 1. The record payload (turn 1 and repairs)

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
- `slips` entries are tagged `fact|invention|teleport|outcome|dropped`, format `category: text`, separated by `;` (e.g. `"teleport: Ren in garden; dropped: Sam's line"`); `resume` shows the top repeat categories.
- `save: true` runs `save` after verification. On a `VOYAGE_DATA` copy the save step is skipped.

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

Ren follows Sam into the kitchen, dinner is announced, a new housemate appears, a quest starts, and a scene opens with a Planner card. State was at turn 1. (Names, places and quests below are placeholders: use the ones in your campaign.)

```json
{"turn": 2,
 "ops": [
  {"op": "pos",
   "args": {"pc": "Ren", "location": "Home Base", "area": "shared-kitchen", "activity": "helping Sam with dinner"},
   "evidence": "Ren follows Sam into the kitchen"},
  {"op": "fact",
   "args": {"subject": "dinner", "text": "Move-in dinner is at 18:00 in the shared kitchen."},
   "evidence": "Sam: 'dinner's at six'"},
  {"op": "add-npc",
   "args": {"name": "Haruna Ito", "gender": "female", "age": 16, "location": "Home Base", "area": "shared-lounge", "personality": "shy, tidy"},
   "evidence": "Voyage introduces a shy housemate arranging cushions"},
  {"op": "quest-start",
   "args": {"name": "Settling In"},
   "evidence": "Sam hands Ren the chore rota"},
  {"op": "scene-start",
   "args": {"name": "Move-In Dinner", "budget": 6, "card": "@/tmp/scratch/card.txt"},
   "evidence": "dinner prep begins"}
 ],
 "turn_log": {
  "inputs": "Ren: i help Sam in the kitchen",
  "summary": "Sam set up dinner; Haruna Ito appeared in the lounge; the chore rota was handed out.",
  "prompt": "Cut: Continue at Home Base/shared-kitchen, evening. Tone: warm, busy.\nCrew: Sam counts bowls, hands Ren the chore rota, chatting too fast to hide nerves. Haruna Ito arranges cushions in the lounge, shy.\nWorld: a pot lid rattles; the rice cooker jams.",
  "slips": "",
  "notes": "card stored"},
 "save": true}
```

Output on success is about ten lines: one line per op, the turn line, a verification line and the save lines.

## 2. Planner brief template

Spawn with `Agent`, `model: "opus"`, read-only. Fill the braces. Launch it in the background two turns before the previous scene's budget ends, so the card is ready when needed. Review the card before use (see the failure and review notes below), then `scene-start ... --card @card.txt`.

```text
You are the Planner for the Luxcellia: The Fifth Hero's Party campaign (repo root: {repo}). Prepare ONE scene card for the director.

Scene: {name} at {location}/{area}. Why now: {act turn | showcase fight | milestone | twist reveal | thread outgrew a side quest}. Turn budget: {N}.
Recent player feedback (what landed, what dragged; include the last act retro): {paste the last scene and act feedback entries from `resume`/`state`}. Use it: more of what landed, less of what dragged.

Read first (lookups only, run from the repo root as python3 tools/db.py --campaign luxcellia <cmd>):
- bible {section}   (and `bible surprise rules`, `bible budgets` for obstacles and budgets)
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
You write one line for {NPC} in the Luxcellia: The Fifth Hero's Party campaign (repo root: {repo}).
Run: python3 tools/db.py --campaign luxcellia brief "{NPC}"   (lookups only; no updates, no files, no git).
Situation: {the beat in two sentences, who is present, what just happened}. The line is for a Voyage steering prompt.
Write what {NPC} wants or does right now, in their own voice, driven by their want, fear and current act beat. Respect "won't do yet". Never state a player-character outcome. Keep hidden facts out unless the brief marks the step revealed.
Return exactly one line, 150 characters or fewer, in this form:
Crew: {short name} <what they do or say>
```

The main chat merges the lines, trims to the prompt limit, runs `check-prompt`, and writes the final `Crew:` line.

## 4. Failure playbook

| Symptom | Do |
|---|---|
| Record or commit-turn exit 3, 2, 1 | Bad payload or op; the message names it and nothing was applied. Fix the payload and rerun. |
| Record exit 4, "payload turn is X but the next turn is Y" | The turn was already recorded, or the payload number is wrong. Check `db.py resume`; do not rerun an applied turn. |
| Exit 6, "another write is in progress" | A writer is running. Wait for it to finish; do not start another write. If it looks hung (over 10 minutes), kill that pid and run `db.py recover`. |
| Exit 7, or `resume`/`state` prints "stale write lock" | A writer crashed. Run `db.py recover`: if a crashed `record` left the data half-applied it restores the pre-turn snapshot, otherwise it only clears the lock. Then rerun the payload. |
| Exit 5, "saved locally, push failed" | The data is applied and committed locally. Do not rerun the payload. Run `db.py save` when the network is back (it retries and rebases). |
| A turn was recorded wrongly | `db.py undo-turn N` restores the snapshot taken before turn N (last 5 turns) and rewinds `state.turn`. Fix the payload, record again, then `db.py save` to commit the rewind. |
| Planner card breaks a rule | Do not use it. Rewrite the weak parts yourself or reuse an earlier card; nothing was written by the Planner. |
| Trial run | Never launch `record`, `commit-turn` or `wrap-up`; `--dry-run` is allowed and writes nothing. |
| `commit-turn` exit 1 | FAIL in the prompt; nothing was written. Fix the FAIL lines, rerun the same call. |
| `WARN push failed` after commit-turn | Data is saved and committed locally; the next push or `wrap-up` retries. |
| `wrap-up` exit 5 | Committed but not pushed ("NOT safe to close"); rerun `wrap-up` when the network is back. |

Snapshots (`data/.snapshots/`) and the lock file (`data/.lock`) are git-ignored scratch files; never commit them.
