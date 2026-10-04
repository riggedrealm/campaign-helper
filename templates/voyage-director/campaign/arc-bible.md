# {{DISPLAY}}: Arc Bible

Director-only. Everything here is final design. Prompts carry only the sliver a scene needs. Read it by section with `db.py bible` (`bible 3`, `bible act2`, `bible budgets`); never whole.

Machine-readable copies of the cast (including the villain sheets below), quests and reveal ladders live in `data/` and are queried with `db.py`; this file keeps the narrative design. If the two ever disagree, the design here wins and `data/` should be corrected before play.

The arc planner (`docs/arc-planning.md`) writes act pitches and arc charters against these acts. Charters may deviate from them; each deviation is logged and shown on the Arc Planner page. The acts stay the default spine.

Section titles `Time skips`, `Obstacle and surprise rules` and `Scene turn budgets` are looked up by the skill (`bible time skips`, `bible surprise rules`, `bible budgets`): keep those words in the headings. Act headings keep the form `Act N: Name (Days a to b)` so `bible actN` works.

## 1. Premise and stakes

<!-- fill: the premise in 1 to 3 paragraphs: where the player characters are, what the situation is, what ends the arc -->

Stakes the players can feel:

<!-- fill: three bullets, each something a player can lose or protect: a place, a reputation, a person -->

### Scope and players

- Built for 1 to 4 player characters. Assume nothing about their powers or backgrounds.
- <!-- fill: length of the arc in days or weeks; weekday of Day 1 (also set `start_weekday` in campaign.json) and the weekday of the key days -->
- <!-- fill: where player characters live or start, which rooms or areas they may claim, what unclaimed ones hold -->

### Tone

<!-- fill: scene mix (for example action / daily life / drama shares), how fights feel (puzzle first, spectacle to finish), what losses cost. Keep: enemies are dangerous but player characters can always win with good play; losses have story consequences but never end anything; the director never states player-character or combat outcomes -->

### Venue substitutes (no invented places)

<!-- fill: a table "Need | Stand-in" mapping scenes the story needs to real locations and areas in `data/locations.json` (check each with `db.py loc`); delete this section if every place exists -->

## 2. Hidden state

<!-- fill: one bullet per secret: who holds it, what is true, what it will cost when it comes out. Each secret becomes a reveal ladder in `data/threads.json` -->
<!-- module:standing:start -->
- **Standing** (optional module): start value, kept in `data/ledger.json`, never shown as a meter. Endings by threshold: <!-- fill: thresholds and ending names -->
<!-- module:standing:end -->
- **Relationship values** are Voyage's. The director does not track numbers. A personal quest unlocks when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).

## 3. Pacing at a glance

| Act | Days | Showcase fight | Relationship under pressure |
|---|---|---|---|
| 1 <!-- fill: name --> | 1 to 30 | <!-- fill: fight and day --> | <!-- fill: pair or group --> |
| 2 <!-- fill: name --> | 31 to 60 | <!-- fill --> | <!-- fill --> |
| 3 <!-- fill: name --> | 61 to 90 | <!-- fill --> | <!-- fill --> |

Keep the act day ranges in step with `acts` in `campaign.json` (`db.py time` moves the act with the day).

## 4. Act 1: <!-- fill: name --> (Days 1 to 30)

**Purpose**: <!-- fill: what this act is for and how it ends -->

**Quests**: <!-- fill: quest names seeded in this act, one new seed per turn -->

**Beats** (one per turn; a beat can take several turns if the players linger; each beat has a turn budget, see Scene turn budgets):

1. **Day 1.** *Budget: 2 turns.* <!-- fill: the arrival or admin scene; see opening.md. Arrival, admin, move-in and errand scenes budget 2 turns at most -->
2. <!-- fill: next beats with day, budget, who is present, one world move -->

### Showcase fight: <!-- fill: name and day -->

- **Venue**: <!-- fill: location/area keys from `db.py loc` -->
- **Format**: <!-- fill: who fights whom and how many player characters -->
- **Opponents**: each built from a rule: a power with a visible tell and an exploitable limit.

Villain sheet (copy for each named villain; the same fields live in `data/cast.json` under `villain_sheet`):

#### Villain sheet: <!-- fill: name "codename" (role) -->

| Field | Detail |
|---|---|
| Role | <!-- fill --> |
| Power rule | <!-- fill: the rule in one or two sentences; a hard limit (reach, count, line of sight) --> |
| Tell | <!-- fill: what shows a beat before it fires --> |
| Weakness | <!-- fill: how the rule cracks --> |
| Finisher setup | <!-- fill: the battlefield feature that lets the players finish it with spectacle --> |
| Behavior | <!-- fill: opens with, taunts, flees when --> |
| If it goes badly | <!-- fill: a story consequence, never the end of anything --> |

**Feeding the puzzle within the prompt limit** ({{PROMPT_LIMIT}}, see `db.py state`): put the rule on a `Facts:` line, show the tell in a `World:` beat, leave the weakness to be discovered. Do not state results; Voyage rolls combat.

### Act 1 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| <!-- fill: ordinary obstacle --> | <!-- fill: small surprise: a note, a delay, a visitor, a malfunction --> |

## 5. Act 2: <!-- fill: name --> (Days 31 to 60)

**Purpose**: <!-- fill -->

**Beats**: <!-- fill: numbered beats as in Act 1 -->

### Showcase fight: <!-- fill: name and day -->

<!-- fill: setup, why now, fight shape, then a villain sheet table as above -->

### Act 2 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| <!-- fill --> | <!-- fill --> |

## 6. Act 3: <!-- fill: name --> (Days 61 to 90)

**Purpose**: <!-- fill: the climax act -->

**Beats**: <!-- fill -->

### Showcase fight: <!-- fill: the finale fight -->

<!-- fill: setup, fight shape, villain sheet(s) -->

### Final review and endings

<!-- fill: when and where the arc resolves, then one entry per ending with how it is decided (by choices, never by the director's mood) and what the closing scene shows. Add or remove acts above as the arc needs: renumber the headings and update `acts` in campaign.json -->

### After any ending: sandbox

The game continues as a sandbox. <!-- fill: what stays open after each ending -->

### Act 3 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| <!-- fill --> | <!-- fill --> |

## 7. Personal quests

<!-- fill: one entry per main NPC with a personal quest: name, goal, the closeness that unlocks it -->

## 8. Time skips

Between milestones, offer an optional "skip to next week" montage with player choices about training, jobs and relationships. **Never force a skip.**

- Offer it in a prompt via an NPC or a phone notice ("Plan your week").
- The player chooses (training, job, study, home time, rest, relationships). The director sets the next-prompt `Cut:` to the first morning of the next week, using the player's chosen focus.
- Do not skip past a scheduled milestone (tournament, exercise, review, deadline).
- A skip never decides a player-character outcome; it summarizes only what the players chose.

## 9. Split scenes

Allowed. Protocol in `split-scenes.md`.
<!-- module:standing:start -->

## 10. Standing: how it moves and what Voyage may hear

Full rubric in `data/ledger.json` (`rubric`). Voyage only sees Standing through NPC hints (the `hint_bands`), never a meter. <!-- fill: which NPCs voice the hints and what changes the score -->
<!-- module:standing:end -->

## 11. Obstacle and surprise rules

- One surprise per scene; small most of the time (a note, a delay, a visitor, a malfunction, a stray memory).
- Larger surprises are saved for act turns.
- Every scene needs a world move, because NPCs are passive.
- Keep obstacles ordinary. Drama comes from people.

## 12. Scene turn budgets

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

<!-- fill: per-act budgets for the named beats, if they differ from the table -->

## 13. Story menu (optional)

Ideas the arc planner (`docs/arc-planning.md`) may draw from when it drafts a charter. Menu items, not plans: the planner picks, varies and combines them, and the user approves only shared fields.

<!-- fill: antagonists, set-piece ideas (kinds, not scheduled events) and front seeds (a force, its goal, how it escalates) the planner may draw from; delete this section if the acts are enough -->
