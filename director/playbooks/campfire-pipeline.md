# Campfire pipeline: react, write and check

> **Not yet in force.** This applies once Campfire's engine and server ship the react stage and `gm react` (GDD v2, the engine's E2 to E4 and the CLI's E6). Until the director lifts this line, `campfire.md` is the whole procedure and nothing here is yours to do. The commands named below already exist in campaign-helper and run read-only or on files, so they are safe to try.

`campfire.md` is the procedure for a turn. This file is the part that GDD v2 adds between the dice and the post: the characters react after the dice, the scene is written only from results, and a check reads the draft before it posts. Your pillars do not change. **Code decides outcomes; you interpret, react and narrate.** Nothing secret ever goes in a line the players will read.

## The turn, in order

1. **Pull** and **prep** (`campfire.md`, steps 1 and 2). Prep also prints the director layer, the hard noes matched against the inputs, the memory that matches the round's names and places, precedent for each skill in play, and what to avoid repeating. Read all of it.
2. **Rule** (`campfire.md`, step 3). Write the rulings only. Threat moves are no longer part of this file: they come after the dice.
3. **Resolve** (`campfire.md`, step 4). The result packet holds every roll and every effect.
4. **React**, below. Check the file, then `gm react`.
5. **Write**, below. The scene, the ops and the input-to-paragraph map.
6. **Check**, below. Code first, then the checker. At most three rewrites.
7. **Post** (`campfire.md`, step 7), then **commit**, below.
8. **Report** to the GM in one line, plus any flag you overruled, any rewrite the check forced, and any hard-no hit prep raised.

In "draft" you stop twice: after the rulings (before the dice) and after the checked scene with the reactions beside it (before the post). "go" continues.

## React

From the result packet and each present NPC's brief, decide what every active threat does and what every NPC in the scene does about it. Write one file, `campaigns/NAME/campfire/react-N.json`:

```json
{
  "threat_moves": [
    { "threat": "gunman", "kind": "press", "target": "p_3x9q" }
  ],
  "reactions": [
    { "npc": "Kenji", "kind": "move", "to": "the back room", "line": "Not my fight." },
    { "npc": "Okabe", "kind": "attitude", "word": "wary" }
  ]
}
```

- **Threat moves.** Exactly one for each threat that is active or full. `press` takes a `target` (a player id; not Out), `press all`, `hold` and `flee` take none, and any move may carry `to`, a zone next to the threat's own. A threat whose clock is full may only hold or flee. The engine rolls the target's Defense and decides the harm; you never write it.
- **Reactions.** At most one for each NPC in the scene, and none is fine: an NPC with no reaction stays where it is. The kinds are `stay`, `move` (with `to`), `leave`, `attitude` (with `word`, one step from the current attitude: friendly, neutral, wary, hostile), `give` (with `player`, `item`, `qty` 1 to 3), `refuse` (with `player`) and `turn` (the NPC becomes a threat: `id`, `tier`, `reach`, `rules`; once a scene). No reaction carries a number except a give's `qty`.
- **Decide as the person.** Read the brief's want, fear, trigger now and refusal, and the voice lines. A reaction is what that NPC does about what just happened, not what the plot needs. The brief is secret: only the reaction goes to the server.
- **Never act on a player character.** A reaction cannot move, speak for, or decide for one. An NPC may refuse or give; what the player does about it is the player's.
- **A `line`** is the NPC's own words, up to 200 characters, and it will be quoted in the scene exactly. Keep any hidden fact out of it: it reaches every player.
- **Vary.** The brief's last gesture is what the scene used last time; do not repeat it.

Run `python3 tools/db.py react-check --reactions campaigns/NAME/campfire/react-N.json --packet campaigns/NAME/campfire/result-N.json` (exit 0 ok, 1 problems, 4 a hidden term). Then:

```sh
gm react --room CODE --reactions campaigns/NAME/campfire/react-N.json --round N --json campaigns/NAME/campfire/reacted-N.json
```

The reacted packet is the result packet plus every move's Defense rolls and every reaction's applied change. If the command refuses, fix the file from the error list and send it again; after three refusals stop and show the GM the errors.

## Write

Write the scene from the reacted packet and your memory, and nothing else as a source of outcomes. `campfire.md` step 5 holds the scene rules; these are added:

- Every input's outcome is in the scene at its tier. A Failure is a failure; a Basic Success has its cost; no input is left out.
- Every approved reaction's `line` appears in the scene word for word. NPCs act as their reactions say and threats as their moves say.
- Everyone is where the reacted packet puts them. A character named in a sentence with a zone is in that zone after the round.
- No number in the prose beyond the words the packet gives.
- Do not turn a failure into a success, and do not soften what the engine decided.
- The scene ends on something the players can act on.

Alongside the scene and the ops, write the **input-to-paragraph map**, `campaigns/NAME/campfire/map-N.json`, so the check can see that every input was answered:

```json
{ "inputs": [ { "player": "p_7k2m", "paragraphs": [1, 2] }, { "player": "p_3x9q", "paragraphs": [4] } ] }
```

Paragraphs are numbered from 1, counting each blank-line-separated paragraph (a speaker block is one). Map each input to the paragraph or paragraphs that show its outcome; the paragraph must name the character.

## Check

```sh
python3 tools/db.py check --scene campaigns/NAME/campfire/scene-N.md --packet campaigns/NAME/campfire/reacted-N.json --ops campaigns/NAME/campfire/ops-N.json --map campaigns/NAME/campfire/map-N.json --round N
```

It runs the code checks and appends the run to `campfire/check-N.json`: the hidden-words check, the campaign's hard noes (a hard no in narration is a flag; inside quoted dialogue it is a warning), each speaker block naming someone in the room, cast names that are neither present nor arriving, places the scene or the database does not know, anyone named in a sentence with the wrong zone, every op's evidence found in the scene, every approved reaction line unchanged, and the map. A **flag** goes back to you to fix; a **warning** is yours to judge. Exit 0 passed, 1 flags, 4 a hidden term (do not post), 9 STOP.

Then the checker. Print its whole brief and give exactly that to a subagent on the faster tier: `python3 tools/db.py check-brief --scene ... --packet ...`. It holds the draft, the reacted packet and the hard noes and the fixed questions, and nothing else: do not add your briefs, your memory or your reasons, and do not tell it what you intended. It never rewrites; it answers yes or no to each question with a quote. Save its JSON reply to `campfire/answers-N.json` and run `check` again with `--answers`. A yes on questions 1 to 6, or a no on question 7, is a flag.

**The loop.** Fix the flags and run `check` again, up to three times (four checks in all). If the third rewrite is still flagged, `check` stops with exit 9: show the GM the draft and the flags and wait. When the GM says what to do, run `check --reset` on the draft they approve. A flag you judge wrong is not dropped silently: you may overrule it, but only with a reason that goes in the commit record and in your report line.

## Commit

After the post, record the turn:

```sh
python3 tools/db.py commit-turn --scene ... --rulings ... --ops ... --payload ... --record campaigns/NAME/campfire/record-N.json --check campaigns/NAME/campfire/check-N.json
```

`record-N.json` holds what only you know. Every key is optional:

```json
{
  "threat_moves": [], "reactions": [],
  "facts": [ { "text": "Kenji keeps the spare key in the biscuit tin.", "evidence": "the biscuit tin rattled", "names": ["Kenji"], "places": ["the back room"] } ],
  "gestures": { "Kenji": "turns the tin over in his hands" },
  "results": [ { "player": "p_7k2m", "tier": "Success" } ],
  "overruled": [ { "code": "unknown_place", "reason": "The GM named the annex in the table notes." } ]
}
```

- **Facts.** Record what the posted scene established that later scenes must stay consistent with: a name, a promise, a wound, where an object is, what someone saw. One plain sentence each, with a quote from the scene as evidence (commit-turn refuses a fact the scene does not hold). A fact is local to this machine; prep brings it back when its names or places come up.
- **Gestures.** Each NPC who reacted gets a last gesture so the next scene avoids repeating it. Give it in your own words; if you leave it out, commit-turn derives one from the reaction's kind.
- **Overruled.** Every flag still raised on the final draft must be overruled here with a reason, or commit-turn refuses. The check log must end on the scene you are committing.

commit-turn records the reactions, every flag and rewrite, the facts, the ruling log (prep shows the last ruling on each skill as precedent), last gestures and the repetition tracker, and runs the hidden-words check once more on what was posted. There is no summary, batch or replay stage.

## Hard noes and consent

The table's hard noes are phrases agreed with the players and kept in `campaign.json` on this machine: `python3 tools/db.py hard-noes` lists them, `--add PHRASE` and `--remove PHRASE` change them. They never reach the server. Prep flags an input that contains one; rule it as the table agreed and do not play it out on the page. The check matches the draft in code, and the checker reads for them in any wording.

## Undo

If the GM undoes a round on the server (`gm undo`), undo campaign-helper's side in the same breath: `python3 tools/db.py campfire-undo --turn N --reason "..."`. It restores the data from before that turn and writes a reversing record that keeps the undone turn and the reason. Only the latest turn can be undone this way.

## What stays secret

The briefs, the director layer, the hard noes, the facts, the check log, rejected drafts and their flags, and the tracker are never posted and never put in a line, a stakes line, an op's evidence or a reason. The scene, the ops (their evidence), every reaction `line`, the rulings' stakes and `reason`, and a turn reaction's `rules` all reach the players.
