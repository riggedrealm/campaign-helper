# Split Scenes

Player characters may go to different places. Voyage must track them. The director adopts this protocol in full, and writes it into the `Cut:` line in a compact form (below) so the prompt fits 700 characters.

## The 7-rule protocol

1. **Positions header.** Every turn while the party is split starts with a compact block listing each player character's location, area and current activity, e.g. `📍 Aiko: Sakura Lane Sharehouse / shared-kitchen, cooking · Ren: Chikara Academy / classroom-5a, Support lecture`.
2. **Scene labels.** Each scene opens with its own label, e.g. `— Sakura Lane Sharehouse, shared-kitchen (Aiko) —`, and covers only that location's characters.
3. **Only what was acted.** Only scenes with a player action this turn advance. Other scenes hold still and are not re-narrated.
4. **No teleporting.** A player character never moves, appears or acts in a scene unless their own player says so.
5. **One place per NPC.** An NPC is in one scene at a time and knows only what happened there. Information crosses only by phone, message or travel.
6. **One shared clock.** All scenes share time. Note when someone is waiting.
7. **Regrouping.** When player characters reunite, say so once and drop the header.

Use exact world names in headers and `Cut:` lines (the examples below do): `Sakura Lane Sharehouse`, `Chikara Academy`, and the real area keys.

## Director checklist for a split turn

- Do the players want to split? Never split them yourself.
- Which scenes have a player input this turn? Only those advance (rule 3).
- Each NPC in the `Crew:` line appears in one scene only (rule 5).
- The `World:` line gives each advancing scene its own world move, labeled A or B.
- State who is waiting and since when (rule 6).
- Do not state a player character's destination or arrival. Travel happens only when the player says it (rule 4).

## Fitting a split into 700 characters

The budget is a hard 700 characters, labels included. Cost-saving moves:

- Open `Cut:` with the word `SPLIT`. Voyage reads it as the signal to run the protocol (header first, labels, hold the unacted scene).
- Name scenes **A** and **B** (and **C**) with first names of player characters in parentheses.
- One `Crew:` clause per scene, prefixed `A:` or `B:`. Skip NPCs that are not needed.
- One world move per advancing scene, prefixed `A:` or `B:`. Hold scenes get no world move.
- Drop `Tone:` unless it differs between scenes.
- Use `Facts:` only for a rule-5 or rule-4 reminder.
- If a counter treats the emoji as two characters, leave a 10-character margin.

### Compact `Cut:` forms

| Case | Form |
|---|---|
| Both scenes advance | `Cut: SPLIT, <day/time>, one clock. Open with 📍 header; label each scene. A: <Location/area> (<PC>). B: <Location/area> (<PC>). Both advance.` |
| One scene advances | `Cut: SPLIT, <day/time>. Only B advances: <Location/area> (<PC>). A holds, not re-narrated: <PC> <activity> at <Location/area>, waiting since <time>.` |
| Regroup | `Cut: REGROUP, <day/time>, <Location/area>. Say once that <PCs> have reunited; drop the header.` |
| Travel (the player has said it) | `Cut: SPLIT, <day/time>. <PC> travels from <Location/area> to <Location/area> as the player chose; arrives at <time>.` |

## Worked examples

### Example 1: both scenes advance (449 characters)

```text
Cut: SPLIT, Day 12 evening, one clock. Open with 📍 header; label each scene. A: Sakura Lane Sharehouse/shared-kitchen (Aiko). B: Chikara Academy/classroom-5a (Ren). Both advance.
Tone: warm vs tense.
Crew: A: Tatsuya cooks, apologizes for the clatter: "Sorry, sorry, almost done." B: Mio hunches over a jammed rig: "It's nothing, really."
World: A: the loft hum overhead swells, then cuts. B: Arimura on the intercom, dry: lab closes in ten minutes.
```

Counted by script (Python `len` on the exact text, trailing newline removed): **449 characters** (limit 700).

### Example 2: one scene advances, one holds (379 characters)

```text
Cut: SPLIT, Day 20, noon. Only B advances: Hero Field Complex/mobility-track (Ren). A holds, not re-narrated: Aiko waits on Sakura Lane Sharehouse/rooftop-chill-deck for Sunny's call, waiting since 11:30.
Crew: Shin times Ren's run: "Faster. Corners cost you."
Facts: Shin knows nothing about A.
World: the instructor's whistle blows; the track's middle platform slides one step.
```

Counted the same way: **379 characters** (limit 700).

Why they work:

- Example 1: rule 1 and 2 are cued by the first line; each NPC is in one place (rule 5: Tatsuya in the kitchen, Mio in the lab); each scene has its own world move.
- Example 2: rule 3 and 6 are named in the `Cut:`; Aiko's scene is not narrated; Shin is told he knows nothing of scene A (rule 5).

## Regroup note

When the player characters meet (a player says so), use the Regroup form once. Voyage says the group has reunited and drops the header. The next turn's `Cut:` reverts to "Continue at <Location/area>".
