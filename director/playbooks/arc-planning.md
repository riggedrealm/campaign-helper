# Arc planning

Open this playbook when a planning trigger fires (the user asks to plan, an arc closes, an act ends, or no arc is live), and again whenever an arc is live and you need its bookkeeping rules.

Arc functions are optional per campaign. They are on when the campaign has a session zero and a charter (the Pivot playbook, PIV-10), and `preflight` and `arc-pivot` say whether they are on. A campaign with neither plays on open threads from turn 1, and nothing under "In play" below applies to it. Planning the first session zero and the first charter is what switches the functions on.

## The three records

The plan has three records, all in `data/arcs.json`. The file is optional: a missing file reads as empty, and the first write creates it. <!-- ARC-1 -->

- **Session zero** is the style of the game. It is about the game, never about the player character's goals. It holds the tone; the lines (what never happens); the veils (what happens offscreen only); how much of each play style the table wants (combat, social, exploration and mystery, each from 0 to 3); the pacing the table likes; the ending the table hopes for (triumph, bittersweet or open); and the player count. The first time, ask the user. In later sessions, print it, confirm it in a line or two, and change only what the user changes. <!-- ARC-2 -->
- **An act pitch** is a short pitch written at each act start, before the arc, against the existing act. Read the act's design first with `db.py bible act<N>`. Acts and their day boundaries stay exactly as `campaign.json` and the bible have them. A pitch may depart from the act's design, and each departure is logged with a reason (see "Departures from the plan"). The final act's pitch builds toward the ending the table hoped for in session zero. <!-- ARC-3 -->
- **An arc charter** covers one arc at a time, about 20 to 35 turns, built from what the player character actually did and serving the act pitch. The plan is pressure, never a script, and the player character can walk away from all of it. The user steers only in chat and sees the planner page's shared fields; the hidden fields stay with you. <!-- ARC-4 -->

## When a planning session happens

Planning sessions are user-requested: the user steers the world's direction there. One happens when the user says "plan the arc" or "plan the act", when an arc closes, when an act ends, or when no arc is live and arc functions are on. Without arc functions, the offer to plan is only the single line at chat start that `core.md`, Triggers, describes (TRIG-12).

Never start a planning session mid-turn. Add one line under the prompt instead, for example "Arc closed. Plan the next one now or later?", which is the planning line that `core.md`, Reply, allows (REPLY-2). The user may defer. If they do, play continues on the open threads and no new arc pressure starts until they plan. <!-- ARC-5 -->

## Running a planning session

Work through these steps in order. <!-- ARC-7 -->

1. **Pull the brief.** Run `db.py plan-brief`. It is the read-only planning view, and the charter subagent gets its inputs from it too.
2. **Ask the retro question if an arc just closed.** Ask "Best moment? Anything drag?" at the start of this session and nowhere else, then record the answer with `db.py feedback --kind act --best "..." --drag "..." --turn N` so the next brief shows it. <!-- ARC-6 -->
3. **Session zero.** Ask the first time and confirm later, as described under "The three records". The first time, record it with `db.py session-zero --tone ... --lines "a;b" --veils "a;b" --pillars combat=3,social=2,exploration=1,mystery=2 --pacing ... --ending-hope ... --players N` (or `--file F.json`). `--players` is how many player characters sit at the table, and `preflight` counts the PC sheets against it. In later sessions, `db.py session-zero` with no options prints it.
4. **Act pitch.** At an act start, write the act pitch first (see "Act pitches"), then the arc.
5. **Launch the charter draft.** Start the Opus subagent with the brief in `director/agents/charter.md`, and give it the last two charters so the set pieces vary.
6. **Review the draft before the user sees it.** Check it against the charter rules below. Also check that the places, the NPCs and the canon it uses exist (`loc`, `npc`, `canon`), and that the twist links to a reveal ladder (`thread "<name>"`) or has keywords of its own. Edit the draft or discard it; the Planner never writes. <!-- ARC-9 -->
7. **Show the user the shared fields only,** plus one alternative promise. For a blind arc (`"blind": true`), show only the promise and the tone and ask for approval of those two. Never show hidden fields, even to explain a choice. <!-- ARC-10 -->
8. **Revise with the user until they approve,** then write the file and run `db.py arc-plan --file F.json` for a new draft (it takes the next id), or `db.py arc-plan --file F.json --id A2` to update one. Approve it as described under "Approval" below.
9. **Push the approved plan** so the planner page rebuilds, and give the user the link `resume` prints (see "The planner page"). When the plan is approved, the arc's off-ramps are prepared as the Pivot playbook describes (PIV-1).
10. **Put what the user agreed into the act pitch,** so it survives the chat: `hidden.checklist` (one line per agreed rule) and `hidden.pending_ops` (turn ops that cannot run before turn 1, such as `act-deviation`). Then run `db.py preflight` (`core.md`, Chat and orchestration, CHAT-4; `db.py preflight -h` lists its checks, and the arc checks run only when arc functions are on).

### Approval

Approve a charter with `db.py arc-approve A2 --lines-checked`. The `--lines-checked` flag is your statement that the charter respects session zero; without it the command prints the lines and veils as a checklist. Use `--force` only when the user has said to skip a check, because it is recorded. An arc may be drafted before the PC sheets exist: use `PENDING` placeholders and list the open work in `hidden.refine`. `arc-approve` refuses while `refine` has items, while a shared field still says `PENDING`, and while fewer PC sheets exist than `session_zero.players`. It lists every problem at once and exits 4. <!-- ARC-11 -->

## Charter rules

Every charter, whether you write it or the Planner drafts it, follows these rules:

- The promise is a question, never an outcome.
- The pressure is forces, not secrets.
- The set pieces are kinds, never events, and they differ from the last two charters' set pieces.
- The wins on offer are allies, information, places or reputation, never numbers (Voyage owns rewards).
- At least one backstory hook comes from a PC sheet or an established relationship.
- Every front has a goal and 2 to 4 escalating moves.
- The antagonist's face reaches the PC on screen by the midpoint.
- There are at least 3 clues, none tied to a scene, and no conclusion rests on one clue.
- There are at most 3 new NPCs.
- No line from session zero is crossed, and no veil shows on screen.
- No field names a PC outcome or a combat outcome.
- The draft answers the weakest point of the last retro.

<!-- ARC-8 -->

## Field reference

A charter is a JSON file for `arc-plan`, and an act pitch is a JSON file for `act-plan`. Each has shared fields, which the user sees and the planner page shows, and hidden fields, which only you see. The charter rules above (ARC-8) govern what a field may hold and are not repeated in the tables; the examples show them applied, each with a good and a bad one. Extra keys inside `shared` and `hidden` are kept. <!-- ARC-22 -->

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

An act pitch is `{"shared": {...}, "hidden": {...}}` with the fields listed below.

### Shared fields of a charter

| Field | Holds | Good | Bad |
|---|---|---|---|
| `title` | A short name | "Salt and Debt" | "Arc 2" |
| `tone` | The feel of the arc | "tense, wry, a market under pressure" | "good" |
| `promise` | The arc's question | "Can the quay market stay open once the fees double?" | "The market is saved." |
| `premise` | The opening situation, in a few lines | "A shipment is late and the guild wants its fees." | "Ren fights the guild master." |
| `pressure` | Forces in motion | "The guild raises fees every week the shipment is late." | "The guild master is secretly skimming the fees." |
| `set_pieces` | Kinds of set piece | "a chase", "a market standoff" | "Kenji's crew ambushes Ren at the docks on Day 12" |
| `pc_tests` | One category per PC: combat, social, exploration or mystery | `{"Ren": "social"}` | `{"Ren": "Ren must lie to the guild master"}` |
| `subplot` | A smaller thread alongside | "A rival stall copies the PC's habits." | "Ren falls for the rival." |
| `climax_kind` | The kind of finale | "a public confrontation" | "Ren wins the vote." |
| `ending_shape` | How the arc is meant to land | "bittersweet" | "Everyone is happy." |
| `stakes` | `personal` or `wide` | `wide` | "high" |
| `seeds` | Hooks the first scenes can show | "a bailiff pins a notice to the posting board" | "Ren finds the notice and follows the bailiff." |
| `wins_on_offer` | What the PC can gain | "the net menders as allies; a map of the lower docks" | "+200 coins", "level up" |
| `echoes` | Past player choices this arc calls back to (the page titles them "Your choices that shaped this arc") | "You paid the ferry fee for the stranger." | "The PC is brave." |
| `backstory_hooks` | Hooks from PC sheets or relationships | "Ren's sheet names a debt to a boat family." | "Ren secretly wants revenge." (a PC goal nobody stated) |
| `deviations` | Where the charter departs from the act's design, each with a reason | "Turn 120: the guild arc moves up; the PC asked about it first." | a departure with no reason |

### Hidden fields of a charter

| Field | Holds | Good | Bad |
|---|---|---|---|
| `twist` | `text`, and either `ladder` (a key in `data/threads.json`) or `keywords` (the words kept out of prompts until the reveal); `arc-reveal` sets `revealed_turn` | `{"text": "The clerk has been forging the fee notices", "ladder": "harbour-ledger"}` | `{"text": "Someone is behind it"}`, with no ladder and no keywords to guard |
| `fronts` | Forces, each with a `goal` and escalating `moves` | Front "Dock Guild", goal "take the quay"; moves: raises fees, closes the market hall, sends bailiffs to the PC's rooms | Front "The guild", goal "be bad", one move: "gets stronger" |
| `antagonist` | `name`, `face` (who the PC meets) and `first_contact` (how and where the face reaches the PC on screen) | face "the clerk who serves the PC's stall"; first contact "the clerk posts the new fee at the PC's stall in the first market scenes" | first contact "the face turns up late in the arc" |
| `clues` | Facts that point at the twist or the antagonist; place them wherever the PC goes | "The late shipment's seal matches the guild's own stamp." | "On Day 12 in the market hall, Yumi tells Ren the seal is forged." (tied to a scene, and it hands over the conclusion) |
| `refine` | Strings: what must change before approval, typically once the PC sheets arrive | "Replace PENDING in `pc_tests` once Sam's sheet is in." | "tidy up later" |
| `surprises` | Small turns the world can spring | "A tide table goes missing from the net menders' hut." | "Ren discovers the traitor." |
| `climax_options` | Ways the finale can go | "the ledger goes public at the spring tide"; "the net menders close the quay" | "Ren defeats the guild master in a duel." |
| `pc_test_situations` | Per PC, a situation that fits the `pc_tests` category | `{"Ren": "a clerk offers a bribe in front of the market crowd"}` | `{"Ren": "Ren refuses the bribe"}` |
| `cast` | Named NPCs the arc uses, all in the database | `["Yumi", "Kenji"]` | an NPC in neither the database nor `new_npcs` |
| `new_npcs` | New minor NPCs | one clerk with a name and a one-line role | five new faces |
| `notes` | Anything else for you | "Keep the ferry debt off screen until the midpoint." | a PC outcome |

An arc also keeps a hidden `offramps` list, which the Pivot playbook owns (PIV-1).

### Fields of an act pitch

| Field | Holds | Good | Bad |
|---|---|---|---|
| `title` (shared) | A short name | "The Quay Season" | "Act 2" |
| `theme` (shared) | What the act is about | "who gets to belong when money tightens" | "good versus evil" |
| `question` (shared) | The act's big question | "Will the quay still belong to the people who work it?" | "The quay is saved." |
| `builds_to` (shared) | What the act leads toward | "a public reckoning at the spring tide" | "Ren wins." |
| `stakes_scale` (shared) | How large the stakes run | "the harbour district" | "very big" |
| `ending_shape` (shared) | How the act is meant to land | "bittersweet" | "Everyone is happy." |
| `turning_point` (hidden) | The act's hinge, as a force | "the guild's ledger surfaces" | "Ren betrays the net menders." |
| `notes` (hidden) | Anything else for you | "Hold the ferry family back until the midpoint." | a PC outcome |
| `checklist` (hidden, optional) | Strings: the plan agreed with the user; `preflight` prints each one for you to confirm | "No cliffhanger tails at scene ends, as the user asked." | "do well" |
| `pending_ops` (hidden, optional) | Payload ops deferred until a turn exists; `preflight` lists each until it is in the data | `{"op": "act-deviation", "args": {"n": 1, "text": "..."}, "evidence": "..."}` | an op with no evidence |

## Act pitches

Write the pitch at each act start, before the arc. Create or replace the draft with `db.py act-plan N --file F.json`; this refuses a closed act, and editing an approved pitch keeps it approved and logs the change. Approve it with `db.py act-approve N`, which needs all six shared fields. Close the act with `db.py act-close N --retro "text|@file"`. The act retro written at the act boundary (the Pacing playbook, SCN-8) feeds the next pitch.

## In play

These rules apply while an arc is live. A live arc is an active one, or a provisional one after a pivot (the Pivot playbook).

**Start.** Run `db.py arc-start A2 --turn N --evidence "..."` when the arc's first pressure shows in Voyage's output. Only one arc is live at a time. <!-- ARC-12 -->

**Fronts.** When a front's move happens visibly in the story, record it with `db.py arc-move A2 "Dock Guild" 1`. Fronts move on their own schedule, whether or not the PC is watching (`core.md`, The world, WLD-1). <!-- ARC-13 -->

**Pressure cards, not scene cards.** For each scene tied to the arc, write a short card inline: what each relevant NPC wants now, what they do if the PC engages, and what they do if not, and which one to three of them are active per prompt (the rest are backdrop, CREW-1). Write no scripted opening shot and no "decision the scene ends on". The Opus Planner writes a card only for a showcase fight, a twist reveal or a finale, using the brief in `director/agents/card.md`. Launch it in the background two turns before the previous scene's budget ends. Before the card goes in with `scene-start --card`, check it with `thread`, `loc` and `canon`, and check that no line states a PC outcome. <!-- ARC-14 -->

A pressure card, bad: "Opens on the market at noon. Ren must choose between the guild and the net menders."

A pressure card, good: "Guild clerk: wants the late shipment logged today; if Ren engages, offers a fee waiver for a favor; if not, posts the new fee at dusk. Net mender: wants the clerk watched; if Ren engages, shares a tide table; if not, leaves for the lower docks."

**Ops each turn.** Record these as they happen, each with `evidence`, as payload ops or as commands. <!-- ARC-15 -->

- `arc-clue ID N`: clue N was found.
- `arc-contact ID`: the antagonist reached the PC on screen.
- `arc-reveal ID`: the twist is out.
- `arc-review ID --kind midpoint|drift|scene --notes TEXT`: a review happened.
- `arc-deviation ID "text"`: a departure from the act's design.

In the turn log, set `"arc_contact": true` on any turn where the PC engaged the arc's pressure.

**The twist's keywords.** Keep them out of prompts until you have recorded `arc-reveal`; `check-prompt` blocks them until then. <!-- ARC-23 -->

**Midpoint review.** At 60% of the budget, run a review. Stay silent with the user unless something is off: drift, the antagonist not yet on screen, or twist timing that no longer fits. Record it with `arc-review ID --kind midpoint --notes ...`. This is also when the Planner writes the arc's off-ramps (the Pivot playbook, PIV-1). <!-- ARC-16 -->

**Budget.** At 100% of the budget, start no new pressure and let the climax hooks find the PC wherever they are. At 130%, tell the user once, in one line: extend or wrap up. To extend, raise `budget_turns` with `db.py arc-plan --id A2 --file F.json`. <!-- ARC-17 -->

**Voyage's harmless inventions.** Fold slips tagged `invention` into the fronts at the midpoint or at a scene end ("yes, and"). `plan-brief` lists the candidates. <!-- ARC-18 -->

**Departures from the plan.** Log every departure from the act's design with a reason: `act-deviation N "text"` for the act and `arc-deviation ID "text"` for the arc. The planner page shows them. <!-- ARC-19 -->

Drift, when the PC stays away from the arc, belongs to the Pivot playbook (DRIFT-1). Boredom and variety flags belong to the Pacing playbook (SCN-7).

## Closing an arc

Write the retro yourself from the turn log. A read-only subagent may draft it first, using `director/agents/review.md` in its act retro mode; the retro you record is still your own. Then run:

`db.py arc-close A2 --turn N --evidence "..." [--status closed|set_aside] --best "..." --drag "..." --wins "..." --spotlight "..." --threads-closed "..." --weakest "..." --notes "..."`

You need at least one of `--best`, `--drag`, `--notes` and `--weakest`. The command adds the turns used against the budget and the clues found against the clues placed. The retro names the weakest point, and the next charter must answer it. Ask the user nothing mid-play: the one question waits for the next planning session (step 2 of "Running a planning session"). An arc the user drops for good closes as `set_aside` with a short retro on what pulled the PC away (the Pivot playbook, PIV-9). <!-- ARC-20 -->

## The planner page

The planner page shows only shared fields, session zero, progress and player-visible state. It never shows hidden fields, `pc_threads`, any hidden score or hidden ladder steps, and a blind arc shows only its title, promise, tone and progress. Provisional arcs and off-ramps stay off the page until the arc is approved, and a parked arc shows as parked (the Pivot playbook, PIV-5). The page is public: anyone with the link can read it. A spoiler refusal fails the build and leaves the last good site live; fix the field that leaked and push again. After an approval, push with `wrap-up` or `save` and give the user the link that `resume` prints. <!-- ARC-21 -->
