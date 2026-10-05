# Campfire mode playbook

This is your operating manual for running a Campfire room from Claude Code. You are the director and the narrator in one. campaign-helper is your memory. The Campfire server and its rules engine hold every number. The `gm` command line is your only way to reach the server.

Read this file in full when Campfire mode starts. Then follow it exactly.

## When this applies

Campfire mode is on when both of these are true:

1. The campaign file names a room code (six characters from the alphabet `23456789ABCDEFGHJKMNPQRSTUVWXYZ`).
2. The GM has typed "send" or "draft".

Nothing else starts a turn. If the campaign file names a room code and the GM has typed neither word, do not touch the room. You may answer questions and read files. You do not run `gm pull`, `gm resolve`, `gm post` or `gm scene`. You may run `gm status` when the GM asks about the room.

The commands below assume one room for the campaign. If the campaign has several rooms, add `--room CODE` to every `gm` command. The examples use `--room CODE` anyway so they stay exact.

## The pillars that bind you

| Pillar | What it means for you |
| --- | --- |
| Judgement to Claude | You decide what an input is, which skill it tests, how hard it is, what is at risk, and what each threat does this round. You write every NPC line, every consequence and the scene. |
| Numbers to the engine | You never add, subtract, remember or invent a value. Rolls, health, Guard, Combat Energy, Power Strain, coin, XP, levels, skill levels and clocks are the engine's. Every decision you make is a word from a closed list, and the engine turns the word into a number. |
| Choices to players | Players own their characters. You never move, speak, think or decide for a player character. A ruling decides how the world tests an input, never what was attempted. |
| One voice | You write the scene yourself from the engine's results and your own memory. There is no narrator to steer. |
| Secrets never reach the server | Arcs, reveal ladders, hidden NPC facts, Standing, debt and plans stay in campaign-helper on the GM's machine. Rulings, stakes, scene text, ops and asides are all visible to players. Write nothing in them that a player should not know yet. |
| Human-triggered only | Every turn starts because the GM typed "send" or "draft". You run one turn per word. When the turn ends, you stop. |

## "send", step by step

A "send" is one turn of the room: pull, rule, resolve, write, post, record. Do the steps in order. Do not skip one.

Pick the round number N from the pull. Run every command from the repo root. The turn files sit in the campaign directory: `campaigns/NAME/campfire/round-N.json`, `campaigns/NAME/campfire/rulings-N.json`, `campaigns/NAME/campfire/result-N.json`, `campaigns/NAME/campfire/scene-N.md` and `campaigns/NAME/campfire/ops-N.json`. The CLI creates the `campaigns/NAME/campfire/` directory when it writes a packet.

### Step 1. Pull the round packet

```sh
gm pull --room CODE --json campaigns/NAME/campfire/round-N.json
```

This locks the round and writes the round packet to the file. No dice are thrown. The command prints a summary and the path.

If it exits non-zero, go to "Refusals and exit codes". Do not continue until the pull has succeeded.

### Step 2. Run campaign-helper prep on the file

Run campaign-helper's prep step on the file: `python3 tools/db.py prep --packet campaigns/NAME/campfire/round-N.json`. It matches the names in the inputs against the cast, prints the briefs for the NPCs present, the scene's budget and the arc pressure, and flags anything the inputs reach for that the database does not know. Read all of it. Do not read the inputs from a paste or from memory of an earlier packet.

### Step 3. Write the rulings and threat moves

Write `campaigns/NAME/campfire/rulings-N.json` from the inputs and the briefs. The format is:

```json
{ "rulings": [ ... ], "threat_moves": [ ... ] }
```

Write one ruling per input and one move per active threat. Every field is a word from its closed list. The engine refuses the whole set if any entry is wrong, and it rolls nothing.

**Choosing the kind.**

| Case | Ruling |
| --- | --- |
| The input is an uncontested action that simply happens (walking, speaking, looking at what is plainly there) | `"kind": "automatic"`. No die, no effect. It happens as written. |
| The input tests something, contests something, or can fail in a way that matters | `"kind": "roll"` |
| The character is Downed | `"kind": "automatic"`. A Downed character may submit only text, and the engine refuses anything else. |
| The input targets a threat (declared or by your own ruling) | `"kind": "roll"`. A threat-targeted input is never automatic. Threats always roll. |

**Rules for a roll ruling.**

- **skill.** Use the skill the player declared. If you rule a different skill, set `reason` to a short explanation of at most 80 characters. The reveal shows it to the players. Rule only a skill the character holds. The party line lists every skill the character holds.
- **difficulty.** One of `trivial`, `easy`, `routine`, `hard`, `very hard`, `heroic`. Required unless the target is a threat. It is authoritative: the engine uses your word, whatever the table's attitude column suggests. The attitude of an NPC in the scene is the default to start from.

  | Word | Default for an NPC attitude |
  | --- | --- |
  | trivial | none |
  | easy | friendly |
  | routine | neutral |
  | hard | wary |
  | very hard | hostile |
  | heroic | none |

  Precedent matters more than the table. campaign-helper records every ruling. Rule similar actions with similar words.
- **target.** `null` for none, `{ "kind": "threat", "id": "<threat id>" }` for a threat, or `{ "kind": "npc", "name": "<name>" }` for an NPC. It defaults to the player's declaration. The NPC need not be in the scene yet. The post's scene op adds them.
- **Threat target.** When the target is a threat, leave `difficulty` out. The threat's tier sets the difficulty and the harm. A `risk` word on a threat-targeted input is ignored, so leave it out.
- **risk.** What a bad roll costs when there is no threat target. Either `"none"` or a lowercase threat tier: `trivial`, `minor`, `standard`, `elite`, `boss`, `mythic`. A bad roll applies that tier's harm: half on Mixed Results, full on Failure, clean on Critical Failure. `"none"` means the roll can only fail, never wound. This is the only way harm enters the game outside a threat. Choose the tier the fiction implies. Do not use a risk to punish.
- **ability.** An ability id the character holds, or `null`. It defaults to the player's declaration. It must belong to the ruled skill's school. The engine refuses an ability the character cannot pay for in Combat Energy or that is on cooldown. The party line names each ability and the Combat Energy shown there is what the character has.
- **stakes.** Up to 140 characters: what success and failure mean in the fiction. The reveal shows it beside the tier. Check every stakes line against the campaign's hidden words with campaign-helper's hidden-words check before you write it into the file. A stakes line is player-facing text.

**Overreach.** An input that reaches beyond the character's power is never refused. Rule it a roll at `heroic` difficulty with the risk the fiction implies, and let the world answer within the power. The player's attempt stands as written.

**Threat moves.** Every active threat gets exactly one move. List them in the order you want them resolved.

| Move | JSON | What the engine does |
| --- | --- | --- |
| press | `{ "threat": "gunman", "kind": "press", "target": "<player id>" }` | The target rolls Defense against the threat's difficulty. |
| press all | `{ "threat": "gunman", "kind": "press-all" }` | Every active, present, not Downed character rolls Defense. |
| hold | `{ "threat": "gunman", "kind": "hold" }` | Nothing. For a threat that is waiting, talking or wounded. |
| flee | `{ "threat": "gunman", "kind": "flee" }` | The threat is retired. |

A press must target a character whose status is active (not away or dead) and who is not Out. A threat whose status is `full` (its clock is filled) may be given `hold` or `flee` only; if you omit its move, it holds. A retired threat gets no move. Choose each move as the threat would, from what you know of it and of the scene.

The engine, not you, decides what a press costs. You decide only who it presses and why. A hold or flee that the fiction supports is as valid as a press.

### Step 4. Resolve

```sh
gm resolve --room CODE --rulings campaigns/NAME/campfire/rulings-N.json --round N --json campaigns/NAME/campfire/result-N.json
```

On success the engine has rolled every die, applied every effect and written the result packet to the file. The command prints a summary: one words line per input, one per threat move with its Defense rolls, the party and the threats.

On refusal the command prints every error, exits 1, and nothing was rolled. Go to "Refusals and exit codes".

In "draft", you stop before this step. See below.

### Step 5. Write the scene and the ops

Write the scene to `campaigns/NAME/campfire/scene-N.md` and the ops to `campaigns/NAME/campfire/ops-N.json`, from the result packet and your memory.

**The scene.**

- State every outcome exactly as its tier says. A Critical Failure is a Critical Failure. A Basic Success is a success with a cost or a shortfall, not a flawless win. Mixed Results is neither a clean success nor a clean failure. Do not soften a tier, do not harden one, and do not reverse one.
- Report every effect as the packet shows it, in the fiction: the hit that landed, the Guard that broke, the threat whose clock filled. Do not name the number. Use the words.
- Write every NPC line yourself. NPCs are people with wants, and they may refuse.
- Write every threat move as the engine resolved it, in the order the packet gives. A press that cost its target nothing is a press that was turned aside.
- An automatic input happens as written. Show it happening.
- A character who is Downed or Out is written as the packet describes them. Nobody dies. Death is a story event the GM records with the fix command in v0.2.
- Never script a player character's words, thoughts or choices beyond what their own input wrote. Their input is what they attempted; you report how the world answered.
- Do not put a hidden fact in the scene before the story reaches it.
- Introduce no rule, gate or place that is not in campaign-helper's database. If you need one, add it to the database first.
- End the scene on a decision the players care about. Do not choose it for them and do not offer a menu.
- The scene text is at most 12,000 characters. Plain paragraphs. `**bold**` and `*italic*` are the only formatting.

**The ops.** List only the story changes the scene established. Each op carries an `evidence` field: a short quote or paraphrase from the scene text, up to 200 characters. The quote must be findable in the scene you wrote. Players are referenced by id.

No op carries a number, except a quest `id` (a string), an item `qty` and a condition's `turns`. There is no op for health, Guard, Combat Energy, Power Strain, XP, level, skill level, a clock, a roll, a tier, an attribute or an ability. The engine refuses any op or field that names one. Never type an XP, coin or harm value.

| Op | Fields | Rule |
| --- | --- | --- |
| `condition` | `player`, `action` (`add` or `remove`), `name`, optional `turns` | Use for a story condition the scene established. Engine-owned names are refused: Downed, Out, Hurt, Guard-broken, Strained. `turns` is a duration in the character's own turns. Omit it for a condition that stays until removed. |
| `item` | `player`, `action` (`add` or `remove`), `name`, `qty` | An inventory holds up to 10 entries. Adding an existing name raises its quantity. Removing an item the character does not hold is refused. |
| `coin` | `player` (an id or `"all"`), `action` (`gain` or `spend`), `size` | Size is `small`, `medium` or `large`. Use only for a payment or a purchase the scene established. `"all"` means every active character. A spend that would take coin below zero is refused. |
| `quest-start` | `id`, `title`, `goal`, `giver`, `reward_text`, `size`, `risk` | Every field is required. State what, for whom, the reward and the risk. `size` is `errand`, `thread` or `storyline`, the same words campaign-helper uses for quest sizing. The size sets the XP and coin paid at completion. |
| `quest-complete` | `id` | Pays the size's XP and coin to every active character. Never in the post that starts the quest: start it, then complete it in a later post. |
| `quest-fail` | `id` | Pays nothing. Also refused in the post that starts the quest. |
| `threat-add` | `id`, `name`, `tier`, `rules` | Once per scene: the scene's one surprise. `tier` is a lowercase threat tier. `rules` is up to 280 characters of standing rules text. A fifth live threat is refused. |
| `threat-retire` | `id` | A threat that fled, surrendered or was resolved. Use it when the scene shows the fight is over. |
| `stabilize` | `player`, `by` | Lifts a Downed ally to a tenth of their health. Allowed only if `by` had an input this round with no threat target that reached Basic Success or better. |
| `rest` | none | A night, a safe house, a hospital: rest the story earned. Restores everyone as the engine defines it. |
| `scene` | optional `location`, `day`, `time`, `mood`, `npcs`, `npcs_leave` | Small changes the story establishes: a move, a new NPC, a changed attitude. `npcs` is a list of `{ "name", "attitude" }` upserted by name. `npcs_leave` is a list of names. `day` and `time` are free text. |

Every op needs evidence. An op whose evidence is missing is refused. An op the scene did not establish does not belong in the file. If the scene changed nothing, write `[]`.

### Step 6. Run the five-question pre-check

Before you post, read the scene and the ops against these five questions. Fix the file and ask again until every answer is no, no, no, no, yes:

1. Does any line script a player character's words, thoughts or choices?
2. Does any line contradict a tier or a number in the packet?
3. Does any stakes line or scene line carry a hidden word?
4. Is any rule, gate or place new and not in the database?
5. Does the scene end on a decision the players care about?

Questions 1 to 4 are failures when the answer is yes. Question 5 is a failure when the answer is no. In "send", the pre-check is your own and you post straight after it. Run campaign-helper's hidden-words check on the stakes lines and on the scene text as part of question 3: `python3 tools/db.py scan campaigns/NAME/campfire/scene-N.md` and `python3 tools/db.py scan campaigns/NAME/campfire/rulings-N.json` (exit 0 is clean).

### Step 7. Post

```sh
gm post --room CODE --scene campaigns/NAME/campfire/scene-N.md --ops campaigns/NAME/campfire/ops-N.json --round N
```

The engine validates the whole post and applies it or applies nothing. On success it applies the ops, ticks each acting character's turn counts, awards XP, resolves level-ups, reveals the inputs, advances the round and broadcasts the scene. The command prints `Posted round N. Round M is collecting.` and a line for each level-up.

On refusal the command prints every error, exits 1, and nothing was applied. Go to "Refusals and exit codes".

### Step 8. Commit the turn in campaign-helper

Run campaign-helper's commit-turn with the posted scene as the record of the turn, the rulings file, the ops file and the turn log: `python3 tools/db.py commit-turn --scene campaigns/NAME/campfire/scene-N.md --rulings campaigns/NAME/campfire/rulings-N.json --ops campaigns/NAME/campfire/ops-N.json --payload campaigns/NAME/campfire/payload-N.json`, where the payload holds the turn log and campaign-helper's own ops (`director/reference.md`). The turn log is your own account of what happened and what it changes in the story: who did what, how each tier landed, who the threats pressed, which NPC attitudes moved, what the players now know and what stays hidden. commit-turn runs the hidden-words check on the scene and the stakes. Record changes to NPCs, arcs and hidden ledgers here, in campaign-helper, and nowhere on the server.

### Step 9. Reply to the GM in one line

One line, in words, and nothing else. Name the round, the headline of the turn and the state the table is in. Do not list numbers. Example:

> Round 7 posted: Mira's disarm landed on the gunman, Jun leaned on Sergeant Okabe, Kaito's climb went wrong; round 8 is collecting.

If something needs the GM's attention, such as a level-up queue or a refusal you could not resolve, add it as a second clause in the same line. Do not start another turn.

## "draft"

"draft" runs the same steps as "send" and stops twice. It is the GM's review.

1. **After the rulings, before any die is thrown.** Do steps 1 to 3. Then show the GM the rulings in words: for each input, the character, the kind, the skill (and the override reason, if any), the difficulty word, the target, the risk, the ability and the stakes; and for each threat, its move. Do not run `gm resolve`. Wait for the GM to type "go". If the GM asks for a change, change the file and show it again. Resolve only after "go".
2. **After the scene, before the post.** After "go", do steps 4 and 5 and the pre-check of step 6. Then show the GM the scene text and the ops. Do not run `gm post`. Wait for the GM to type "go". If the GM asks for a change, change the scene or the ops, run the pre-check again and show them again. Post only after "go".

"go" continues from either stop. It is the GM's word, typed in the conversation. Nothing else counts as "go". After the post, do steps 8 and 9 as for "send".

## Refusals and exit codes

A refused ruling set or post is fixed from the printed error list and resent. Every error prints as `  <path>: <code>: <message>`. The path points into the file, for example `rulings[2].skill`. Fix every error in the list, not only the first, then resend the same command.

**After three refusals on the same step, stop.** Show the GM every error from the refusals, in full, and wait. Do not try a fourth time. Do not work around the error. Do not change the ruling so that it passes without regard to the fiction.

| Exit | Meaning | What you do |
| --- | --- | --- |
| 0 | ok | Continue to the next step. |
| 1 | refused, or a local problem such as a bad file or a round mismatch (nothing was sent) | Read the printed errors. Fix the file. Resend. This counts toward the three-refusal limit. Exception: a refusal with the code `wrong_round` is not fixable by editing. See below. |
| 2 | auth | Stop. Tell the GM the token is missing or wrong. Do not try other rooms or tokens, and do not print or ask for the token. |
| 3 | network | Stop. Tell the GM the network failed and which command it was. Do not run the command again on your own. The GM decides. |
| 4 | wrong phase | Run `gm status`. Do the step the phase calls for. The table below says which. |

**Exit 4 and the phases.**

| Room phase | Step it calls for |
| --- | --- |
| collecting | Nothing is locked. Start from `gm pull` if the GM asked for a turn, otherwise report the state. |
| ruling | The round is locked. Use the packet already pulled, or pull again: a pull in the ruling phase returns the same packet. Then rule and resolve. |
| writing | The round is resolved. A resolve in the writing phase returns the same result packet. Write the scene and the ops, then post. |

Pull and resolve are idempotent in the phase they produced. Repeating them is safe. Post is not: it ends the round.

**`wrong_round`.** A post refused with `wrong_round` means the post already landed or the round moved. Run `gm status`. Compare its round to yours. Do not post again. Tell the GM what the status shows. If the status shows a later round in collecting, the post landed and the turn only needs steps 8 and 9.

A post resent for the round that just landed (after a network drop, say) gets the stored answer of the first post: it prints the same `Posted round N` line, exits 0 and applies nothing again. Any other post that arrives when the room is already collecting is refused with a wrong-phase error and exits 4. Treat it the same way: check `gm status`, never post twice.

## Scene changes, asides and the v0.2 commands

**Scene changes.** When the story moves to a new place or a new time, write a `SceneRequest` file and run:

```sh
gm scene --room CODE --file campaigns/NAME/campfire/scene-change.json
```

A scene change restores Guard and Combat Energy, lowers Power Strain, and brings Downed and Out characters back. So it is refused while any threat is active. A scene change is never an escape from a fight. Retire the threats first, in the open: rule `flee` for the threat in the round's moves, or retire it with a `threat-retire` op in a post whose scene shows it ending. A threat that is `full` needs no retiring: the scene command retires every full threat itself and logs a line for each, so leave `threats_retire` empty. Only then run `gm scene`. The command works only when the room is collecting, so run it after a post, never between resolve and post. Run it only in a turn the GM started, and only when the posted story moved. The format:

```json
{
  "name": "The back stairs",
  "location": "Sakura Lane Sharehouse, rear stairwell",
  "day": "Day 3, Monday",
  "time": "Late evening",
  "mood": "Tense and quiet",
  "npcs": [ { "name": "Sergeant Okabe", "attitude": "wary" } ],
  "threats_add": [],
  "threats_retire": []
}
```

`threats_add` entries take `id`, `name`, `tier` and `rules` (no evidence). They count against the cap of four live threats and do not use the scene's one surprise.

**Asides.** `gm aside "text"` posts a narrator line to the log and the players at any time, in any phase. It changes no state. Use it only inside a turn the GM started, for a short out-of-scene note such as a ruling the table should see. It is player-facing, so the secrets rule applies to it as to a scene.

**v0.2 commands.** `gm edit`, `gm fix`, `gm undo` and `gm rekey` are v0.2. The server answers 501 `not_implemented` and the command exits 1. Do not repeat the command, and do not try to get the same effect another way. If a fix is needed (a wrong ruling already resolved, a character edit, a death), tell the GM it waits for v0.2 and suggest how to carry it in the next scene's fiction.

## Which director rules survive

These stand unchanged in Campfire mode. They are about players and secrets.

- Only the player moves, speaks, thinks or decides for their character.
- An overreaching input is attempted, and the world answers within the power.
- No menus.
- NPCs are people with wants, and they may refuse.
- Secrets are director-only, and enter a scene only when the story reaches them.
- Data changes only when the posted scene establishes something, with evidence.

## Retired in Campfire mode

These existed because Voyage rolled. They do not apply.

- The rules that existed because Voyage rolled. Voyage's narrator did not know the outcome, so you steered it. Now the engine decided it.
- Claude now states every outcome, because the engine decided it and you are reporting it.
- Fight scenes are no longer conditional. The packet carries the exact fight state.
- No Facts line.
- No slip category for a narrator. There is no separate narrator.
- No prompt budget.
- No steering brief, no check-prompt, no prompt limit.
- The hidden-words check runs on the stakes lines and the scene text, not on a prompt.

**A GM who also holds a seat.** The GM who plays a character through the web page sees the other inputs through the packet before the scene. That is accepted: a friend group plays on trust. Do not treat that GM differently in rulings.

## The two packets and how to read their words

Both packets are JSON files. The `gm` command prints a summary of each. Read the words first. The numbers sit beside the words for the GM and for tests. You never need one to rule or to write, you never compute with one, and you never carry one forward from a turn to the next. Read words and write words.

### The round packet (pull)

The round packet is what the engine hands you before the dice.

| Field | What it holds |
| --- | --- |
| `room` | Code, title, campaign, room difficulty, round, phase |
| `scene` | Name, location, day, time, mood, the NPCs present with attitudes, and whether this scene's one surprise is used |
| `last_scene` | The text of the last posted scene, or null before the first |
| `party` | One party line per character (below) |
| `threats` | Every threat that is not retired, one threat line each (below) |
| `quests` | The quests, each with its size and status |
| `inputs` | The raw inputs: player id, name, text, declarations, whether it is early, and the attitude of a declared NPC target when the scene lists them |
| `missing` | Who has not submitted |

An input marked `early` was sent while you were writing the previous round. It is the player's words as they wrote them, before they saw the scene. The player was asked to confirm or revise it. Take what the text says. If the scene since then makes the text strange, rule it as written and let the world answer.

### The result packet (resolve)

The result packet is the round packet after the dice. It has the same fields, except that each input is a resolved input and there is a new `moves` list.

| Field | What it adds |
| --- | --- |
| `inputs[].ruling` | Your ruling, as accepted |
| `inputs[].roll` | The die, the skill level, the bonuses, the difficulty, the score and the tier. Null for an automatic ruling |
| `inputs[].effect` | Everything the roll changed, with from and to values. Empty for an automatic ruling |
| `inputs[].words` | The input words line |
| `moves[]` | Each threat's move, the Defense rolls it caused, any change to the threat's status, and the move's words |
| `party` and `threats` | Updated to the state after the dice |

Skill XP is computed at resolve and applied at post. Levels and level-ups happen at post. Do not narrate them. The players' sheets and the reveal show them, and `gm post` prints each level-up.

### Descriptor words

Health, Guard and Power Strain are words. Combat Energy is the number, 0 to 5.

| Meter | Words | Thresholds |
| --- | --- | --- |
| Health | full, scratched, hurt, bloodied, critical, Downed, Out | scratched below full, hurt below three quarters, bloodied below two fifths, critical below a sixth. Downed and Out come from the conditions. |
| Guard | intact, chipped, broken | intact at its maximum, chipped below it, broken at 0 |
| Combat Energy | the number, 0 to 5 | |
| Power Strain | fresh, warm, high, strained, locked out | The words change at 25, 50, 75 and 100 |

At "strained" the engine adds the Strained condition. At "locked out" the power is shut until a scene or a rest brings it down. Both are words for you to narrate.

### The party line

A party line reads:

`Mira, level 3 Initiate, hurt, Guard broken, Combat Energy 2, Power Strain high, Hurt for 2 turns, abilities Steady Strike II and Iron Wind (created).`

Read it left to right:

- **Mira, level 3 Initiate.** The name, the level and the title. The title is all you need of progression.
- **hurt.** The health word.
- **Guard broken.** The Guard word. A broken Guard means the next hit goes to health.
- **Combat Energy 2.** The number. An ability costs 0 to 3, so a character on 2 cannot pay for a cost-3 ability.
- **Power Strain high.** The strain word. Strained or locked out limits power use.
- **Hurt for 2 turns.** A condition and how long it lasts, counted in that character's turns. Hurt has no numeric effect. It is a word for you.
- **abilities Steady Strike II and Iron Wind (created).** The abilities the character holds. A roman numeral is the rank. "(created)" marks a technique the player wrote. Read its description (each ability in the packet's `party[].abilities` carries it) before the player uses it, since the description is the whole of what it permits.

### The input words line

After resolve, each input has a words line:

`Mira, Close Quarters Combat vs the gunman (standard): Success. Clock 3/5.`

It reads: the character, the skill used, the target with its attitude or tier in parentheses, the tier reached, and any clock change. Before the dice, the CLI prints the raw input in this form: `<name>: "<text>"` followed, when the player declared anything, by `[declared: skill ..., ability ..., target ...]` and `(early)` if it was early.

### The threat line and the move line

A threat line reads:

`the gunman (standard), clock 1/5`

It gives the threat's name, its tier, and its clock as turns landed against its size. A full clock means the threat is beaten or resolved. It stays in play until you retire it or let it flee.

A move line is the move's words, followed by one line for each Defense roll it caused, for example the target's name, Defense, the tier reached and the resulting hit or the lack of one. A press that landed on a Downed character is a near-death save, not a Defense roll. Narrate it as the character being too hurt to defend.

## Worked example: a rulings file

This is a complete `rulings-N.json` for a round with three inputs and one active threat. The party is Mira (`p_7k2m`), Jun (`p_3x9q`) and Kaito (`p_8w4d`). The scene lists the gunman as a threat (`gunman`, standard) and the room has no Sergeant Okabe yet.

```json
{
  "rulings": [
    {
      "player": "p_7k2m",
      "kind": "roll",
      "skill": "Close Quarters Combat",
      "target": { "kind": "threat", "id": "gunman" },
      "ability": null,
      "stakes": "Disarm him, or he gets a shot off at the counter."
    },
    {
      "player": "p_3x9q",
      "kind": "roll",
      "skill": "Intimidation",
      "reason": "Leaning on the sergeant is a threat, not banter.",
      "difficulty": "hard",
      "target": { "kind": "npc", "name": "Sergeant Okabe" },
      "ability": null,
      "stakes": "He lets Jun through, or he writes Jun's name down."
    },
    {
      "player": "p_8w4d",
      "kind": "roll",
      "skill": "Athletics",
      "difficulty": "hard",
      "target": null,
      "risk": "minor",
      "ability": null,
      "stakes": "He reaches the fire escape, or the rusted rail gives way."
    }
  ],
  "threat_moves": [
    { "threat": "gunman", "kind": "press", "target": "p_3x9q" }
  ]
}
```

What the file shows:

- Mira's ruling targets a threat, so it has no `difficulty` and no `risk`. The threat's tier sets the difficulty.
- Jun declared Banter against an NPC the scene does not list yet. The ruling overrides the skill to Intimidation, so `reason` is required and is under 80 characters. The difficulty `hard` matches a wary NPC. The post's scene op will add Sergeant Okabe.
- Kaito's input has no target. The ruling adds a risk, `minor`, so a bad roll can hurt. `risk` is a lowercase tier word. A risk of `"none"` would mean he can only fail.
- The gunman presses Jun because Jun insulted him in the scene. The engine decides what that costs.
- Every stakes line is under 140 characters and was checked against the hidden words.

## Worked example: an ops file

This is a complete `ops-N.json` for the same round. It assumes a scene that introduced Sergeant Okabe, had Jun shaken by the gunman's shot, had Kaito pick up a key on the fire escape, and had a courier hand Mira a job.

```json
[
  {
    "op": "scene",
    "npcs": [ { "name": "Sergeant Okabe", "attitude": "wary" } ],
    "evidence": "Sergeant Okabe stepped out of the doorway, hand on his belt."
  },
  {
    "op": "condition",
    "player": "p_3x9q",
    "action": "add",
    "name": "Shaken",
    "turns": 3,
    "evidence": "Jun's hands would not stop shaking after the shot."
  },
  {
    "op": "item",
    "player": "p_8w4d",
    "action": "add",
    "name": "Brass stairwell key",
    "qty": 1,
    "evidence": "Kaito pocketed the brass key from the landing."
  },
  {
    "op": "quest-start",
    "id": "courier-job",
    "title": "The courier's package",
    "goal": "Carry the sealed package to the pharmacy on Sakura Lane.",
    "giver": "The courier",
    "reward_text": "Ten thousand yen on delivery.",
    "size": "errand",
    "risk": "Someone else wants the package.",
    "evidence": "\"Take this to the pharmacy,\" the courier said. \"Ten thousand, and don't open it.\""
  }
]
```

Every op has `evidence`. The evidence strings are quotes or paraphrases from the scene. The only numbers are `turns` on a story condition and `qty` on the item. The quest `id` is a string. The `quest-start` size is `errand`, the same word as campaign-helper's quest sizing, and the engine pays the XP and coin for that size when the quest completes. There is no op for the gunman's shot or for Kaito's climb, because the engine already applied them.
