# Night Line: Arc Bible

Director-only. Everything here is final design. Prompts carry only the sliver a scene needs. Read it by section with `db.py bible` (`bible 3`, `bible act2`, `bible budgets`); never whole.

Machine-readable copies of the cast (including the villain sheets below), quests and reveal ladders live in `data/` and are queried with `db.py`; this file keeps the narrative design. If the two ever disagree, the design here wins and `data/` should be corrected before play.

The arc planner (`docs/arc-planning.md`) writes act pitches and arc charters against these acts. Charters may deviate from them; each deviation is logged and shown on the Arc Planner page. The acts stay the default spine.

Section titles `Time skips`, `Obstacle and surprise rules` and `Scene turn budgets` are looked up by the skill (`bible time skips`, `bible surprise rules`, `bible budgets`): keep those words in the headings. Act headings keep the form `Act N: Name (Days a to b)` so `bible actN` works.

## 1. Premise and stakes

Kestrel Bay is a present-day coastal city where roughly one person in fifty has a power. Powers are registered with the city's Registry Office; unregistered use is a fine, not a crime. The tone is grounded, warm and a little noir, with low lethality: nobody dies in this test campaign.

It is 23:40 on a Friday at Meridian Central Station. The 23:45 last train on Line 9 is held because the signal box shorted at 23:31. The player characters are commuters and strangers stuck on Platform 4. The arc ends at the end of Day 2, when the night's cause has been dealt with in one of three ways (see Final review and endings).

Stakes the players can feel:

- A frightened sixteen-year-old in the maintenance tunnel, who can be calmed, taken in or lost.
- Tib's trust and his brother's safety, which the party can protect or spend.
- The last train and the favours the night earns: Sandoval's debt, Mara's tolerance and Tib's payment.

### Scope and players

- Built for 1 to 4 player characters. Assume nothing about their powers or backgrounds. In Campfire the players build their own characters; they arrive in the round packet's party lines.
- Two days: Day 1 is Friday night from 23:40 (the day rolls over at 05:00, so the whole night is Day 1) and Day 2 is Saturday. Day 1 is a Friday (`start_weekday`).
- Everyone starts on `Meridian Central Station/platform-4`. There are no rooms and no home base.

### Tone

Scene mix: about half talk and investigation (rulings against NPCs of different attitudes), a third tension in the tunnel, the rest a quiet run to the depot. The static is a puzzle first, never a spectacle. Keep: the threat is dangerous but player characters can always win with good play; losses have story consequences but never end anything; nobody dies; the director never states player-character or combat outcomes.

## 2. Hidden state

- **The static is Wren Achterberg, 16, Tib's younger brother.** He is an unregistered power user whose power shorts electronics when he panics; he shorted the signal box at 23:31. The locked case holds his prescribed dampener cuff, which Tib collected from the Lumen Clinic tonight; Tib is smuggling both the cuff and his brother home on the last train. June Halloway has talked to the boy through the service door grille and knows only that he is scared. If it comes out wrongly, Wren is registered against his will, Tib is fined and the family splits. Reveal ladder `What Tib is carrying`:
  1. June mentions "the boy in the tunnel".
  2. A dropped clinic receipt, or Tib flinches at the tunnel noise.
  3. Tib admits the truth.
  4. The cuff goes on and the lights come back.
  Steps reveal only when play earns them.
- **Relationship values** are Voyage's. The director does not track numbers. A personal quest unlocks when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).

## 3. Pacing at a glance

| Act | Days | Showcase encounter | Relationship under pressure |
|---|---|---|---|
| 1 The Last Train | 1 to 2 | The static in the tunnel (late Day 1) | Tib and Officer Sandoval |

Keep the act day ranges in step with `acts` in `campaign.json` (`db.py time` moves the act with the day).

## 4. Act 1: The Last Train (Days 1 to 2)

**Purpose**: a short, complete night that exercises every Campfire step. It ends at the end of Day 2 with one of the three endings.

**Quests**: `Get Tib's case to Harrow Street` (errand, giver Tobias Achterberg) in round 2 or 3, then `What shorted the signal box?` (thread, giver Officer Priya Sandoval) one turn later.

**Beats** (one per turn; a beat can take several turns if the players linger; each beat has a turn budget, see Scene turn budgets):

1. **Day 1, 23:40.** *Budget: 2 turns.* The held train on Platform 4 (see opening.md). Mara announces an indefinite hold; Tib looks for someone to hold his case while Sandoval passes. First small surprise in round 2: the platform lights die in a ripple from the tunnel end and every phone fills with static.
2. **Day 1, about 23:55.** *Budget: 2 turns.* Concourse and Platform 4: June's music and "the boy in the tunnel"; Tib offers the errand to someone trustworthy; Sandoval asks for help with the signal box. World move: Mara quietly checks the service door.
3. **Day 1, about 00:15.** *Budget: 3 to 5 turns.* The Maintenance Tunnel: the static. Add threat `static` (tier minor) with one `threat-add` op when someone goes toward the tunnel or the static is cornered. World move: the party's phones and torches die as they approach.
4. **Day 1, about 01:00.** *Budget: 2 turns.* The Rear Carriage of the Line 9 Night Train: the cuff, the ride to the end of the line, Tib's choice. A scene change is allowed only after the threat is retired.
5. **Day 2, morning.** *Budget: 2 turns.* Harrow Street Depot (Loading Bay, then Night Office): the errand completes, Sandoval's decision, the favour and the payment. The finale is the end of Day 2.

### Showcase encounter: The static in the tunnel (late Day 1)

- **Venue**: `Meridian Central Station/maintenance-tunnel`, with `Meridian Central Station/platform-4` behind it.
- **Format**: one minor threat against 1 to 4 player characters. It can be talked down (hold), can flee, or can press.
- **Opponents**: built from a rule: a power with a visible tell and an exploitable limit.

Villain sheet (the same fields live in `data/cast.json` under `villain_sheet` for Wren Achterberg):

#### Villain sheet: the static in the tunnel "Static" (the scene's one surprise)

| Field | Detail |
|---|---|
| Role | The scene's one surprise: a minor threat, id `static`. A frightened teenager, not a villain. |
| Power rule | Lights die and phones scramble within a carriage-length of it. It lashes out when cornered or shouted at. Hard limit: a carriage-length. |
| Tell | The platform lights ripple out from the tunnel end; every phone screen fills with static; a low hum rises. |
| Weakness | Calm voices and light it cannot kill (a flame, a glow stick, a wind-up lantern). The cuff in Tib's case ends it. |
| Finisher setup | The tunnel's handrail and dark: Tib kneels in the dark and opens the case; the cuff snaps on and the lights come back in a ripple toward the platform. |
| Behavior | Holds while approached calmly; presses when cornered or shouted at; flees into the tunnels when crowded or when an officer shouts. |
| If it goes badly | A dead torch, a scorched phone, a bruise and a missed slot; Sandoval has to write something down. Nobody dies. |

**Feeding the puzzle in Campfire**: put the rule in the `threat-add` rules text (at most 280 characters, player-facing): "Lights die and phones scramble within a carriage-length of it. It lashes out when cornered or shouted at; it backs off from calm voices and from light it cannot kill." Show the tell in the scene, leave the weakness to be discovered. Do not state results; the engine rolls.

### Act 1 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| A locked signal box, a closed kiosk, a stuck departure board, Sandoval's questions | The platform lights die in a ripple from the tunnel end and every phone fills with static (round 2); later the static itself, as the scene's one surprise |

## 5. Final review and endings

The arc resolves at the end of Day 2 at Harrow Street Depot (`night-office`). Endings are decided by the party's choices, never by the director's mood.

- **(a) Wren is calmed and goes home on the train.** The cuff goes on in the tunnel or carriage, Tib takes his brother home and Sandoval files nothing. Closing scene: the night office, a kettle, Tib laughing for the first time.
- **(b) Sandoval takes Wren in for registration, gently.** The party or Sandoval chooses the Registry Office path; she keeps it kind. Closing scene: Sandoval at the depot gate, holding a door open.
- **(c) Wren flees into the tunnels.** The cuff never reaches him; the thread stays open. Closing scene: June's theremin falling silent, a dark tunnel and Tib's empty hands.

### After any ending: sandbox

The game continues as a sandbox. After (a), Tib owes a favour and the Achterberg family is a new contact; after (b), Sandoval owes the party one and the Registry Office thread is open; after (c), the tunnels and the thread stay open and Tib asks for help again.

## 6. Personal quests

- **Tobias Achterberg**: `Get Tib's case to Harrow Street` (errand). Unlocks when a player has shown they can be trusted with the case.
- **Officer Priya Sandoval**: `What shorted the signal box?` (thread). Unlocks when the party has shown it is willing to look in the tunnel.

## 7. Time skips

Between milestones, offer an optional "skip to next week" montage with player choices about training, jobs and relationships. **Never force a skip.**

- Offer it in a prompt via an NPC or a phone notice ("Plan your week").
- The player chooses (training, job, study, home time, rest, relationships). The director sets the next-prompt `Cut:` to the first morning of the next week, using the player's chosen focus.
- Do not skip past a scheduled milestone (tournament, exercise, review, deadline).
- A skip never decides a player-character outcome; it summarizes only what the players chose.

## 8. Split scenes

Allowed. Protocol in `split-scenes.md`.

## 9. Obstacle and surprise rules

- One surprise per scene; small most of the time (a note, a delay, a visitor, a malfunction, a stray memory).
- Larger surprises are saved for act turns.
- Every scene needs a world move, because NPCs are passive.
- Keep obstacles ordinary. Drama comes from people.

## 10. Scene turn budgets

Every scene gets a turn budget, so the arc keeps moving and the player's attention goes where the story is.

**Budgets** (director turns, counted from the first prompt of the scene):

| Scene type | Budget |
|---|---|
| Fights | 4 to 8 turns |
| Big emotional scenes (confessions, splits, verdicts, results) | 3 to 6 turns |
| Investigation | 1 to 2 turns |
| Travel and waiting | 0 (cut) |
| Arrival, admin, move-in or errand scenes | 2 turns at most |

- **Over budget, or goal met: cut to the next beat.** When a scene runs past its budget, or its goal is met even under budget and the input is quiet, the next prompt's `Cut:` moves to the next beat. Do not wait for a perfect ending; the players can bring a loose thread along.
- **Time skips: offer one at natural lulls.** At the end of a scene, a meal or a night, offer a single skip. Never force one, never skip past a scheduled milestone, and a skip never decides a player-character outcome (see Time skips).
- A fight is over when its finisher lands; do not pad it to reach the budget. Budgets are ceilings, not targets.

This is a one-act test campaign: the table above applies as written. The arrival scene ("The held train") is 2 rounds; the tunnel scene is 3 to 5 rounds; the Harrow Street scene is 2 rounds.
