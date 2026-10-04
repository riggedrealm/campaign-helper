# Arc planning

How the director plans the story's direction with the user, keeps the plan as pressure and shows the user a read-only page. Read this file before a planning session and when an arc is live. The rules in `{{SKILL_DIR}}/SKILL.md` ("Arc planning") point here; `docs/player-agency.md` still wins on anything about the player character (PC). Run commands from the repo root; `db.py` is `python3 tools/db.py --campaign {{NAME}}`.

## 1. What it is

The plan has three records, all in `data/arcs.json` (an optional file; a missing file reads as empty and the first write creates it).

- **Session zero**: the style of the game, recorded once and revisited briefly at each act pitch. Tone, lines (never happens), veils (happens offscreen only), how much of each play style the table wants (combat, social, exploration, mystery), pacing taste, and the kind of ending the player hopes for (triumph, bittersweet, open). It is about the game, never about the PC's goals.
- **Act pitch**: a short pitch written at each act start against the existing act. Acts and their day boundaries stay exactly as `campaign.json` and `arc-bible.md` have them.
- **Arc charter**: one arc at a time, about 20 to 35 turns, built from what the PC actually did and serving the act pitch.

The plan is pressure, never a script. Fronts move when nobody stops them. The PC can walk away from all of it. The user steers only in chat and sees a read-only page (section 8) with the shared fields. Hidden fields stay with the director.

## 2. When a planning session happens

- The user says "plan the arc" or "plan the act".
- An arc closes.
- No arc is live.
- An act boundary.

Never start one mid-turn. Add ONE line under the prompt, for example: "Arc closed. Plan the next one now or later?" The user may defer. Then play continues on the open threads and no new arc pressure starts until they plan.

## 3. Running a planning session

1. Pull the brief: `db.py plan-brief`. It prints session zero, the current act and its pitch status, the last retro (with its weakest point), the last 5 feedback entries, the last two charters' set pieces and stakes, PC sheets, recent `pc_threads`, reveal ladders with their next hidden step, active quests, open clocks, main NPCs in play, recent canon facts as echo candidates, and `invention` slips since the last arc started.
2. Ask the deferred retro question if an arc just closed: "Best moment? Anything drag?" This is the only place it is asked. Record the answer with `db.py feedback --kind act --best "..." --drag "..." --turn N` so the next brief shows it.
3. Session zero. First time: ask the user, then `db.py session-zero --tone ... --lines "a;b" --veils "a;b" --pillars combat=3,social=2,exploration=1,mystery=2 --pacing ... --ending-hope ... --players N` (or `--file F.json`). `--players` is how many PCs sit at the table; `preflight` counts the PC sheets against it. Later sessions: print it with `session-zero` alone, confirm it in one or two lines, change only what the user changes. Never ask what the PC wants.
4. At an act start, write the act pitch first (section 7), then the arc.
5. Launch the Opus Planner with the Charter draft brief (`docs/orchestration.md` section 2). Give it the last two charters so the set pieces vary.
6. Review the draft before the user sees it:
   - Canon, places and NPCs exist (`loc`, `npc`, `canon`).
   - The twist links to a reveal ladder (`thread "<name>"`) or has its own keywords.
   - Nothing crosses a session zero line or shows a veil on screen.
   - Three-clue rule: at least 3 clues, none tied to a scene.
   - The antagonist's first contact plan puts a face in front of the PC by the midpoint.
   - At most 3 new NPCs.
   - Set-piece kinds differ from the previous arc's.
   - The promise is a question and no field names a PC or combat outcome.
   - The draft answers the last retro's weakest point.
7. Show the user ONLY the shared fields, plus one alternative promise. For a blind arc show only the promise and the tone and ask for approval of those two. Never show hidden fields, even to explain a choice.
8. Revise with the user until they approve. Write the file, then `db.py arc-plan --file F.json` (new draft, next id) or `arc-plan --file F.json --id A2` (update). Approve with `db.py arc-approve A2 --lines-checked`. An arc may be drafted before the PC sheets exist, with `PENDING` placeholders and `hidden.refine`; it is approved only after refining.
9. Push the approved plan so the page rebuilds: run `wrap-up` or `save`, then give the user the Pages link (section 8).
10. Put what the user agreed into the act pitch so it survives the chat: `hidden.checklist` (one line per agreed rule) and `hidden.pending_ops` (turn ops that cannot run before turn 1, such as `act-deviation`). Then run `db.py preflight` (section 10).

`arc-approve` lists every problem at once and exits 4. `--force` overrides and is recorded, so use it only when the user has said to skip a check. The `--lines-checked` flag is your statement that the charter respects session zero. Without it the command prints the lines and veils as a checklist.

## 4. Field reference

Charter file for `arc-plan`:

```json
{"act": 2, "budget_turns": 30, "blind": false,
 "shared": {"title": "...", "tone": "...", "promise": "...", "premise": "...", "pressure": "...",
            "set_pieces": ["a chase"], "pc_tests": {"Ren": "social"}, "subplot": "...",
            "climax_kind": "...", "ending_shape": "...", "stakes": "personal",
            "seeds": [], "wins_on_offer": [], "echoes": [], "backstory_hooks": [], "deviations": []},
 "hidden": {"twist": {"text": "...", "ladder": "thread-key", "keywords": []},
            "fronts": [{"name": "...", "goal": "...", "moves": [{"text": "..."}]}],
            "antagonist": {"name": "...", "face": "...", "first_contact": "..."},
            "clues": [{"text": "..."}], "surprises": [], "climax_options": [],
            "pc_test_situations": {}, "cast": [], "new_npcs": [], "notes": ""}}
```

### Shared fields (the user sees these; the page shows them)

| Field | What goes in it | Good | Bad |
|---|---|---|---|
| `title` | A short name | "Salt and Debt" | "Arc 2" |
| `tone` | The feel of the arc | "tense, wry, a market under pressure" | "good" |
| `promise` | A QUESTION the arc asks. Never an outcome | "Can the quay market stay open once the fees double?" | "The market is saved." |
| `premise` | The situation at the start, in a few lines | "A shipment is late and the guild wants its fees." | "Ren fights the guild master." |
| `pressure` | Forces in motion. Forces, not secrets | "The guild raises fees every week the shipment is late." | "The guild master is secretly skimming the fees." |
| `set_pieces` | KINDS of set piece | "a chase", "a market standoff" | "Mio's gang ambushes you at the docks on Day 12" |
| `pc_tests` | One category per PC (combat, social, exploration or mystery) | `{"Ren": "social"}` | `{"Ren": "Ren must lie to the guild master"}` |
| `subplot` | A smaller thread alongside | "A rival stall copies the PC's habits." | "Ren falls for the rival." |
| `climax_kind` | The kind of finale | "a public confrontation" | "Ren wins the vote." |
| `ending_shape` | How the arc is meant to land | "bittersweet" | "Everyone is happy." |
| `stakes` | `personal` or `wide` | `wide` | "high" |
| `seeds` | Hooks the first scenes can show | "a bailiff pins a notice to the posting board" | "Ren finds the notice and follows the bailiff." |
| `wins_on_offer` | Allies, information, places, reputation. Never numbers: Voyage owns rewards | "the net menders as allies; a map of the lower docks" | "+200 coins", "level up" |
| `echoes` | Past player choices this arc calls back to (the page calls them "Your choices that shaped this arc") | "You paid the ferry fee for the stranger." | "The PC is brave." |
| `backstory_hooks` | At least 1, from PC sheets or established relationships | "Ren's sheet names a debt to a boat family." | "Ren secretly wants revenge." (a PC goal nobody stated) |
| `deviations` | Where the charter departs from the bible's act plan, each with a reason | "Turn 120: the guild arc moves up; the PC asked about it first." | none |

### Hidden fields (director only)

- `twist`: `text`, and either `ladder` (a key in `data/threads.json`) or `keywords` (the words that must stay out of prompts until the reveal). `revealed_turn` is set by `arc-reveal`.
- `fronts`: each is a force with a `goal` and 2 to 4 escalating `moves` that happen if nobody stops it. Example: front "Dock Guild", goal "take the quay"; moves: raises fees; closes the market hall; sends bailiffs to the PC's rooms.
- `antagonist`: `name`, `face` (who the PC meets) and `first_contact` (how and where the face reaches the PC on screen). The face must reach the PC by the midpoint.
- `clues`: at least 3, each a fact that points at the twist or the antagonist and is not tied to any scene. Place them wherever the PC goes. Three-clue rule: no conclusion rests on one clue.
- `refine`: a list of strings, what must change before approval (typically once the PC sheets arrive: replace `PENDING` placeholders, set `pc_tests`). `arc-approve` refuses while it has items, while a shared field still holds `PENDING`, and while fewer PC sheets are recorded than `session_zero.players`.
- `surprises`, `climax_options` (two or three ways the finale can go), `pc_test_situations` (per PC, a situation that fits the `pc_tests` category), `cast` (named NPCs the arc uses), `new_npcs` (at most 3), `notes`.

Extra keys inside `shared` and `hidden` are kept.

## 5. In play

- **Start.** `db.py arc-start A2 --turn N --evidence "..."` when the arc's first pressure shows in Voyage's output. Only one arc is active.
- **Fronts advance when unopposed.** When a move happens visibly in the story, record it: `arc-move A2 "Dock Guild" 1`. The world acts whether or not the PC is watching.
- **Pressure cards, not scene cards.** For each scene tied to the arc, write a short inline card: what each relevant NPC wants now; what they do if the PC engages; what they do if not. No scripted opening shot. No "decision the scene ends on". The Opus Planner writes cards only for showcase fights, twist reveals and finales.
- **Ops each turn** (payload `ops`, each with `evidence`): `arc-move ID FRONT N`, `arc-clue ID N` (clue N found), `arc-contact ID` (the antagonist reached the PC on screen), `arc-reveal ID` (the twist is out; its keywords stop being blocked), `arc-review ID --kind midpoint|drift|scene --notes TEXT`, `arc-deviation ID "text"`, `pc-thread "text"`. In `turn_log`, set `"arc_contact": true` on any turn where the PC engaged the arc's pressure.
- **`pc-thread`** is a private note of what the PC keeps returning to, written as what the PC did ("went back to the cart three times"), never "the PC wants". It feeds the next charter.
- **Midpoint review at 60% of budget.** `prep` says when it is due. Stay silent with the user unless something is off: drift, the antagonist not yet on screen, or twist timing that no longer fits. Record it with `arc-review ID --kind midpoint --notes ...`.
- **At 100% of budget:** no new pressure; climax hooks wherever the PC is.
- **At 130%:** ask the user once, one line: extend or wrap up. To extend, update the budget with `arc-plan --id A2 --file F.json` (`budget_turns`).
- **Drift.** 8 consecutive turns since the arc started with no arc contact: the world moves the front on, and you ask the user one line: "Re-aim?" If yes, close the arc as `set_aside` and build the next charter from what the PC is doing.
- **Boredom flags.** Shorter inputs, repeated skips, a "drag" note in the latest feedback. `prep` prints them. Two flags: one-line check with the user, and the next pressure card adds variety.
- **Voyage's harmless inventions.** Slips tagged `invention` are folded into fronts at the midpoint or at scene end ("yes, and"). `plan-brief` lists the candidates.
- **Deviations from the act plan.** `act-deviation N "text"` for the act, `arc-deviation ID "text"` for the arc. Each gets a reason. The page shows them.

Pressure card example. Bad: "Opens on the market at noon. Ren must choose between the guild and the net menders." Good: "Guild clerk: wants the late shipment logged today; if Ren engages, offers a fee waiver for a favor; if not, posts the new fee at dusk. Net mender: wants the clerk watched; if Ren engages, shares a tide table; if not, leaves for the lower docks."

## 6. Closing an arc

Write the retro yourself from the turn log, then run:

`db.py arc-close A2 --turn N --evidence "..." [--status closed|set_aside] --best "..." --drag "..." --wins "..." --spotlight "..." --threads-closed "..." --weakest "..." --notes "..."`

You need at least one of `--best`, `--drag`, `--notes`, `--weakest`. The command adds turns used against budget and clues found against clues placed. The retro names the weakest point, and the next charter must answer it. Do not ask the user anything mid-play: the one question waits for the next planning session (section 3, step 2).

`set_aside` is for an arc the PC left behind (drift, or the user chose to re-aim). Its retro is shorter: say what pulled the PC away.

## 7. Act pitches

At each act start, before the arc, write a pitch against the existing act.

- Shared: `title`, `theme`, `question` (the big question), `builds_to`, `stakes_scale`, `ending_shape`.
- Hidden: `turning_point`, `notes`, and optionally `checklist` (strings: the plan agreed with the user, printed by `preflight` for the director to confirm) and `pending_ops` (payload ops deferred until a turn exists, e.g. `{"op": "act-deviation", "args": {"n": 1, "text": "..."}, "evidence": "..."}`; `preflight` lists each until it is in the data).

File shape: `{"shared": {...}, "hidden": {...}}`. Commands: `db.py act-plan N --file F.json` (creates or replaces the draft; refuses a closed act; editing an approved act keeps it approved and logs the change), `act-approve N` (needs all six shared fields), `act-deviation N "text"`, `act-close N --retro "text|@file"`.

Read the act's design first with `db.py bible act<N>`. A pitch may depart from the bible's act plan. Log each departure with `act-deviation` and a reason. The act retro from the act boundary (SKILL.md, "The turn loop" step 4) feeds the next pitch. The final act pitch builds toward the ending the player hoped for in session zero.

## 8. The Arc Planner page

`db.py planner-page --out FILE` renders one self-contained HTML page: header, current act, current arc with a progress bar, coming up, past arcs with their retro, session zero, open threads. It shows only shared fields, session zero, progress and player-visible state. It never shows hidden fields, `pc_threads`, any hidden score or hidden ladder steps. A blind arc shows only its title, promise, tone and progress.

Before it writes, the tool scans the text for hidden words. On a hit it prints the terms and exits 4 without writing.

The page is hosted on GitHub Pages and rebuilt by the workflow on every push to main. `commit-turn` pushes every few turns and `wrap-up` pushes the rest. After the user approves a plan, run `wrap-up` or `save` so it goes up now. Then give the user the link that `resume` prints (`Planner page: URL`). The rebuild takes about a minute.

The site is public: anyone with the link can read it. It shows direction fields and session zero (tone, play styles, lines and veils) but never hidden fields.

A spoiler refusal fails the build and leaves the last good site live. Fix the shared field that leaked (or change the hidden term) and push again.

`planner-page --out FILE` stays available for a local preview. `--set-url URL` stores a different link; `resume` prints it in place of the default.

## 9. Commands

| Command | Use |
|---|---|
| `session-zero [--file F] [--tone T] [--lines "a;b"] [--veils "a;b"] [--pillars combat=3,...] [--pacing P] [--ending-hope E] [--notes N]` | Merge into session zero; with no options, print it |
| `act-plan N --file F.json` | Create or replace an act pitch draft |
| `act-approve N [--force]` | Approve a pitch |
| `act-deviation N "text"` | Log a departure from the bible's act plan |
| `act-close N --retro "text\|@file"` | Close an act |
| `arc-plan --file F.json [--id A2]` | New draft or update |
| `arc-approve ID [--force] [--lines-checked]` | Validate and approve |
| `arc [ID] [--list] [--shared]` | Read an arc; `--shared` is the user's view |
| `plan-brief` | Read-only planning brief |
| `preflight` | Readiness check before the first prompt of a chat and at each act start (read-only; exit 4 on any FAIL) |
| `planner-page --out FILE` / `--set-url URL` | Render a local preview / store a non-default link |
| `arc-start ID` | Approved to active |
| `arc-move ID FRONT N`, `arc-clue ID N`, `arc-contact ID`, `arc-reveal ID` | Record what happened on screen |
| `arc-review ID --kind midpoint\|drift\|scene --notes TEXT` | Record a review |
| `arc-deviation ID "text"` | Log a departure from the act plan |
| `arc-close ID [--status closed\|set_aside] [--best] [--drag] [--wins] [--spotlight] [--threads-closed] [--weakest] [--notes]` | Close with a retro |
| `pc-thread "text"` | Private note of what the PC keeps returning to |

The turn ops (`arc-start` to `pc-thread`, plus `act-deviation`) need `--turn` and `--evidence` and can also go in a `commit-turn` payload (`docs/orchestration.md` section 1). The planning commands take `--turn` (default: the current turn) and `--evidence` (default: "planning session with the user"). All of them take the write lock.

## 10. Preflight (before play)

Run `db.py preflight` before the first prompt of every chat and at each act start. It is read-only and exits 4 on any FAIL. `resume` prints a one-line summary while play is starting (turn 0 or 1) or once the campaign has act pitches. It lists each arc of the current act (active, approved or draft) with one line each, and a draft's `hidden.refine` items.

- **FAIL** (fix before the first prompt): off `main`, a stale write lock, no session zero, fewer PC sheets than `session_zero.players` (or none), no approved pitch for the current act, a planner page that would leak a hidden term.
- **WARN** (say it in one line, then play): unpushed commits, generic rules behind the template, a PC sheet missing pronouns, power or background, no approved arc charter (play may run on open threads), each `pending_ops` entry not yet in the data, printed as JSON ready to paste into the next `record` or `commit-turn` payload (at turn 0: the turn 1 record of Voyage's story start).
- **OK / READ**: the repo skill version (compare it with the loaded skill; if they differ, the user re-uploads the zip), the turn 0 reminder, and the docs to read now.
- **ACT N PLAN**: the act pitch's `checklist`, one `[ ]` line per agreed rule. Read every line and keep it in mind for the act; nothing is ticked in the data.
