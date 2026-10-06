# Reference: payloads, ops, statuses and names

Read this when you write a payload by hand, look up an op's arguments, or repair a turn.

The names in the examples are placeholders: player characters Ren and Sam, the NPCs Yumi and Kenji, and the place `Home Base`. Use the ones from your campaign.

## The `commit-turn` payload

`db.py commit-turn --prompt prompt.txt --payload payload.json` takes one JSON object with these keys:

- `ops`: a list of `{"op": "...", "args": {...}, "evidence": "..."}`. Every op needs `evidence`, a quote or paraphrase from Voyage's output, except the scene follow-ups (`scene-obstacle`, `scene-surprise`, `scene-end`), `feedback` and `studio-request`, which take none, and `pc-sheet` and `studio-done`, where it is optional.
- `turn_log`: `inputs` and `summary` are required (the summary is two lines at most); `slips`, `notes` and `arc_contact` are optional, and any other key is refused. Set `arc_contact` to true or false: whether the PC engaged the active arc's pressure this turn.
- `present` (optional): the names of the NPCs who stay in the scene. Without it, the NPCs named in the prompt's `Crew:` line are stored. Backdrop NPCs left out of `Crew:` need no entry: Voyage keeps its own scene list.

The prompt comes from the file, so leave `prompt` and `save` out of the payload (both are ignored). `--dry-run` checks everything and writes nothing. After recording, `commit-turn` pushes, fetches planner output (a failed fetch only warns) and ends with `NEXT BRIEF (turn N+1):` and the next turn's brief; `--dry-run` runs none of that tail. `--received TIME` (ISO 8601, or `HH:MM`) records when the input arrived (the Sessions playbook, Timing).

Normalisation is forgiving, and each change it makes is printed as `~ ...`: a missing `turn` becomes `state.turn + 1`; op names such as `studio_request` become `studio-request`; a `save` key is dropped with a note; arguments written beside `op` move into `args`; and `time` accepts words (see "Time words"). <!-- REF-1 -->

```json
{"ops": [
  {"op": "time", "args": {"block": "Dusk", "inferred": true},
   "evidence": "the lanterns come on along the street"},
  {"op": "fact", "args": {"subject": "cart", "text": "Yumi parks her cart beside the posting board."},
   "evidence": "Yumi leaned over her cart"},
  {"op": "fact",
   "args": {"subject": "Yumi's offer", "text": "Yumi will show Ren the stall's knots once Ren returns the lost ledger.",
            "kind": "condition", "inferred": true},
   "evidence": "Yumi: 'bring me the ledger and I'll show you the knots'"},
  {"op": "scene-obstacle", "args": {"text": "guild queue"}},
  {"op": "studio-request", "args": {"kind": "npc", "target": "Yumi", "text_file": "yumi.txt"},
   "evidence": "Yumi has become a regular at the posting board"}],
 "turn_log": {"inputs": "Ren: asks Yumi about the courier",
              "summary": "Yumi sells Ren a charm and mentions the courier.",
              "slips": "outcome: Ren is said to succeed", "notes": ""},
 "present": ["Yumi"]}
```

A story fix is not part of this payload: it is filed before the prompt goes out (the Studio playbook).

## The `record` payload

`db.py record payload.json [--dry-run]` applies a whole turn under the write lock, all or nothing. It calls the same functions as the single commands, so every validator applies (places, names, ladder gates, quest states). Use it for turn 1 and for repairs (the failures playbook).

```json
{"turn": 3,
 "ops": [{"op": "...", "args": {"...": "..."}, "evidence": "..."}],
 "turn_log": {"inputs": "...", "summary": "...", "prompt": "...", "slips": "...", "notes": "..."},
 "save": true}
```

- `turn` must equal `state.turn + 1`. A retry of a turn that was applied is refused, so a turn cannot be applied twice.
- Each op has `op` (its name), `args` (the command's arguments by name; a list is allowed for `text`) and `evidence`. An op belongs to the payload's `turn`; it may override that with its own `turn`.
- `turn_log` is applied last. `inputs`, `summary` (two lines at most) and `prompt` are required; the prompt is `"none"` for turn 1. `slips`, `notes` and `arc_contact` are optional. The prompt must fit the prompt limit (`db.py state` prints it). `prompt` and other text values accept `@file`.
- `save: true` runs `save` after verification. On a `VOYAGE_DATA` copy the save step is skipped.
- `--dry-run` validates the whole payload against the current data, prints the plan and writes nothing.
- Campfire mode (`campfire.md`): `commit-turn --scene FILE --rulings FILE --ops FILE --payload FILE` takes the posted scene as the record of the turn, with the rulings, the Campfire ops and the turn log. check-prompt and the prompt limit are skipped: `turn_log.prompt` is not needed (commit-turn stores `none`), and the hidden-words check runs on the scene and the stakes lines instead (a FAIL writes nothing; `--allow TERM` only for a term that is public). Before the post, `precheck --scene FILE --packet FILE [--rulings FILE] [--ops FILE]` runs the same check read-only and warns about the scene's speaker blocks. The pipeline commands (`campfire-pipeline.md`, gated): `npc-intent` sets an NPC's want, fear, trigger, refusal, voice lines and last gesture; `hard-noes` lists, adds and removes the table's hard noes; `react-check --reactions FILE --packet FILE` checks a react file; `check --scene FILE --packet FILE [--ops FILE] [--map FILE] [--answers FILE] --round N` runs the code checks and the three-rewrite loop (exit 9 = show the GM); `check-brief --scene FILE --packet FILE` prints the checker's whole brief; `commit-turn ... --record FILE --check FILE` records the facts, the ruling log, last gestures, the repetition tracker and the check's flags and rewrites in `data/campfire.json` and the turn entry; `campfire-undo --turn N --reason TEXT` undoes the latest Campfire turn with a reversing record.

`db.py turn N+1 --inputs ... --summary ... --prompt ... --slips ... --notes ... [--arc-contact]` is the low-level logger that `record` and `commit-turn` both use (`--inputs`, `--summary` and `--prompt` are required, the summary two lines at most). Use it only as a repair tool. <!-- REF-2 -->

A worked example: Ren and Sam help Yumi with dinner, Kenji appears, a quest starts, and a scene opens with a pressure card. State was at turn 1.

```json
{"turn": 2,
 "ops": [
  {"op": "pos",
   "args": {"pc": "Ren", "location": "Home Base", "area": "shared-kitchen", "activity": "helping Yumi with dinner", "inferred": true},
   "evidence": "Ren follows Yumi into the kitchen"},
  {"op": "pos",
   "args": {"pc": "Sam", "location": "Home Base", "area": "shared-kitchen", "inferred": true},
   "evidence": "Sam leans on the counter and asks about the menu"},
  {"op": "fact",
   "args": {"subject": "dinner", "text": "Move-in dinner is at 18:00 in the shared kitchen."},
   "evidence": "Yumi: 'dinner's at six'"},
  {"op": "fact",
   "args": {"subject": "seats", "text": "Yumi will save Ren and Sam two seats at the dinner table.", "kind": "promise", "status": "open"},
   "evidence": "Yumi: 'I'll save you both a seat'"},
  {"op": "add-npc",
   "args": {"name": "Kenji", "gender": "male", "age": 16, "location": "Home Base", "area": "shared-lounge", "personality": "shy, tidy"},
   "evidence": "Voyage introduces a shy housemate arranging cushions"},
  {"op": "quest-start", "args": {"name": "Settling In", "inferred": true},
   "evidence": "Yumi hands Ren the chore rota"},
  {"op": "scene-start",
   "args": {"name": "Dinner Prep", "budget": 2, "kind": "talk", "card": "@card.txt"},
   "evidence": "dinner prep begins"},
  {"op": "question", "args": {"text": "Is Kenji a housemate or a visitor?"},
   "evidence": "Kenji arranges cushions but nobody calls him a housemate"}
 ],
 "turn_log": {
  "inputs": "Ren: I help Yumi with dinner. Sam: I ask what is on the menu.",
  "summary": "Yumi set out dinner and handed Ren the chore rota; Kenji appeared in the lounge.",
  "prompt": "Cut: Continue at Home Base/shared-kitchen, same moment.\nTone: warm, busy.\nCrew: Yumi counts bowls and talks too fast to hide nerves. Kenji arranges cushions in the lounge, shy.\nWorld: a pot lid rattles; the rice cooker jams.",
  "slips": "",
  "notes": "card stored"},
 "save": true}
```

## The ops

Each op is a command run from the payload, with the command's arguments given by name. Optional arguments are marked "optional". Write a text value as `@file` to read it from a file. <!-- REF-3 -->

| Op | Args |
|---|---|
| `add-npc` | `name`, optional `alias gender age power visual personality location area type faction` |
| `npc-seen` | `name` |
| `npc-note` | `name`, `text` |
| `agenda` | `name`, `want` and/or `next` |
| `fact` | `subject`, `text`, optional `kind` (`promise`, `condition`, `debt` or `plant`), `status` (`open` or `paid`; needs a `kind`), `inferred` |
| `fact-status` | `id` (the fact's id, such as `f012`), `status` (`open` or `paid`), optional `inferred`; only for a fact that has a `kind` |
| `pc-add` | `name`, `player`, optional `room location area activity pronouns power background notes` |
| `pc-sheet` | `name`, at least one of `pronouns power background notes` (from the user only) |
| `pos` | `pc`, `location`, `area`, optional `activity placement inferred` |
| `time` | any of `day block clock allow_backward inferred` |
| `quest-start` | `name`, optional `inferred` |
| `quest-end` | `name`, `inferred` set to true: it records an apparent end as a note with the evidence as its quote and leaves the quest's status alone; `sync` confirms it from Voyage's own status. Use only this form. (The tool still accepts the legacy `name` plus `completed` or `failed`, which sets the status, and `quest-obj` with `name`, `obj_id`, `status`; Voyage owns objectives, so do not use them.) |
| `ledger` | `delta` (`"+3"`), `reason`; exists only while the Standing module is on |
| `clock-add` / `clock-done` | `name`, `due_day`, `note` / `name` |
| `thread-reveal` | `name`, `step`, optional `gate_met force player_driven` |
| `add-area` | `location`, `area_id`, `desc`, optional `paths` |
| `scene-start` | `name`, `budget`, optional `location area card kind` (`kind` is `fight`, `talk`, `explore`, `mystery` or `downtime`) |
| `scene-obstacle` / `scene-surprise` / `scene-end` | `text` / optional `force` / none |
| `feedback` | `kind` (`scene` or `act`), `best` and/or `drag`, optional `notes scene`; needs no `evidence`. Put it before `scene-end` so the scene name is stored |
| `arc-start` / `arc-contact` / `arc-reveal` | `id` |
| `arc-adopt` | `id`, optional `force`; a pivot draft becomes `provisional` and the live arc is parked (the Pivot playbook) |
| `arc-unpark` | `id` (the parked arc), `notes`; the parked arc is active again and the provisional arc closes as `set_aside` with the notes as its retro |
| `arc-move` | `id`, `front`, `n` |
| `arc-clue` | `id`, `n` |
| `arc-review` | `id`, `kind` (`midpoint`, `drift` or `scene`), `notes` |
| `arc-deviation` / `act-deviation` | `id` / `n`, `text` |
| `arc-close` | `id`, optional `status` (`closed` or `set_aside`) `best drag wins spotlight threads_closed weakest notes` (at least one of `best drag notes weakest`) |
| `pc-thread` | `text`, `pc` (the character; optional with one PC, required with two or more) |
| `question` | `text` |
| `question-close` | `id` (the question's id, such as `q1`, as the brief, `state` and `resume` list it) |
| `studio-request` / `studio-done` | `kind` (`npc`, `quest`, `faction`, `area`, `story-start`, `story-fix`, `canon` or `other`), `target`, `text_file`, optional `why allow edit` (the turn comes from the payload) / `id`, optional `batch location area_id desc paths fact`; see the Studio playbook |

`inferred` is a flag in `args`; the quote it came from goes in the op's `evidence`. Which items are inferred, and which are never guessed, is set out in `core.md` (Bookkeeping, STATE-1 to STATE-3). To mark an existing promise paid, use the `fact-status` op, or run `db.py fact-status ID paid --turn N --evidence "..."`; `db.py promises [--all] [--kind K]` lists the open ones (all with `--all`). Any command not in the table (`arc-plan`, `arc-approve`, `arc-offramps`, `act-plan`, `act-approve`, `act-close`, `session-zero`, `review-add` and the lookups) is not an op: run it as a command.

## Slip tags

Each entry in `turn_log` `slips` is tagged `fact`, `invention`, `teleport`, `outcome` or `dropped`, written `category: text`, and separated by `;` (or one per line). An untagged entry, or one with another tag, is counted as `other` with a warning. For example: `"teleport: Ren in garden; dropped: Sam's line"`. A `fact` slip is a wrong fact, an `invention` is an invented detail, place or rule, a `teleport` is a PC moved without their player, an `outcome` is a stated PC outcome, and `dropped` is an input or instruction left out, by Voyage or by the director. A slip is Voyage's or your own (LOG-2, `core.md`, Bookkeeping). `resume` shows the top repeat categories.

Record director-review findings with `db.py review-add --turn N --slips "category: text; category: text"` (the text, `@file` or `-`), and only under these five tags: the tool refuses any other tag, so a finding that fits none of them is left for the main chat to decide and is not recorded. The turn must already be in the log. The findings are stored apart from the turn's own `slips`, as `review_slips` with `source: review`; no payload key writes them, and `resume`'s repeat-slip count includes them. <!-- REF-4 -->

## Statuses

- An arc NPC or quest is `planned` until it appears in Voyage's output. Then an NPC is `in_play` and a quest is `active`. Main NPCs start as `world`.
- A fact that has a `kind` (a promise, condition, debt or plant) is `open` until it is `paid`.
- An open question is `open` until `question-close` makes it `closed`.
- An arc is `draft`, `approved`, `active`, `provisional`, `parked`, `closed` or `set_aside`. Only one arc is live at a time: an `active` one, or the `provisional` pivot arc. After a pivot the new live arc is `provisional` and the old one is `parked` (the pivot playbook); `arc-unpark` sets the provisional one aside.
- `pos` refuses a place that is not in the database.

Quest records and positions follow `core.md` (Prompt format, FMT-5; Bookkeeping, LOG-2 and STATE-1). <!-- REF-5 -->

## Time words

In a `time` op, `block` accepts words and maps them to the campaign's time blocks, with a clock inside the block: dawn, morning, late morning, noon, afternoon, dusk, sunset, evening, night, late night, midnight, small hours and similar. `day` accepts `"Day 5"` and reads it as 5. A clock such as `"6:30 pm"` becomes `18:30`; `clock` is HH:MM, 24-hour. A word given as `time_block`, `time` or `when` is read as `block`. When a `time` op moves the day forward it prints `Day changed (Day N -> Day M): run `db.py day-turnover``, and `record` and `commit-turn` repeat that line at the end of their output (the Pacing playbook, WLD-3). <!-- REF-6 -->

## Names

Cast and world NPC entries may carry `aliases` (a list). The first name, the surname and the title-less form are derived automatically (titles are `name_skip_tokens` in `campaign.json`), unless two people share them: then the check prints `WARN: AMBIGUOUS name X: A | B`, and an explicit alias or the full name settles it. `"use_full_name": true` on an entry (a canon trap) makes a short form warn `use full name` instead of passing silently. `canon_traps` in `campaign.json` is a list such as `[{"match": ["Yumi"], "text": "Yumi keeps the stall at the east gate."}]`, where an empty `match` means always. The turn brief shows the traps whose `match` words occur; `resume` and `turn-brief --full` also show the always-on ones. <!-- REF-7 -->
