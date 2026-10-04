# Split party: protocol and compact forms

Open this playbook when the player characters (PCs) are in different places.

Voyage tracks a split party, and you ask it to by writing the protocol into `Cut:` in compact form. `db.py pos` sets `party_split` automatically when PCs stand in different locations.

## The seven-rule protocol

Adopt the protocol in full, and write it into `Cut:` in the compact forms below so the prompt fits the prompt limit (`db.py state` prints it; the default is 840). <!-- SPL-1 -->

1. **Positions header.** Every turn while the party is split starts with a compact block listing each PC's location, area and current activity, for example `📍 Ren: Home Base / shared-kitchen, cooking · Sam: City Academy / classroom-5a, chemistry class`. <!-- SPL-2 -->
2. **Scene labels.** Each scene opens with its own label, for example `— Home Base, shared-kitchen (Ren) —`, and covers only the characters at that location. <!-- SPL-3 -->
3. **Only what was acted.** Only scenes with a player action this turn advance. The other scenes hold still and are not re-narrated. <!-- SPL-4 -->
4. **No teleporting.** A PC never moves, appears or acts in a scene unless their own player says so. Never state a PC's destination or arrival unless the player did. <!-- SPL-5 -->
5. **One place per NPC.** An NPC is in one scene at a time and knows only what happened there. Information crosses only by phone, message or travel. <!-- SPL-6 -->
6. **One shared clock.** All scenes share time. Note who is waiting and since when. <!-- SPL-7 -->
7. **Regrouping.** When the PCs reunite (a player says so), say so once with the Regroup form below and drop the header. The next turn's `Cut:` returns to the stay form, `Continue at <Location/area>, same moment.` (`core.md`, Prompt format, CUT-1). <!-- SPL-8 -->

Use exact world names in headers and `Cut:` lines: the real location names and area keys from `db.py loc`. The examples below use placeholder names. <!-- SPL-10 -->

## Director checklist for a split turn

- Do the players want to split? Never split the party yourself. <!-- SPL-9 -->
- Which scenes have a player input this turn? Only those advance (rule 3).
- Does each NPC in the `Crew:` line appear in one scene only (rule 5)?
- Does `World:` give each advancing scene its own world move, labelled A or B?
- Does the prompt say who is waiting and since when (rule 6)?
- Does the prompt avoid stating a PC's destination or arrival? Travel happens only when the player says it (rule 4).

## Fitting a split into the prompt limit

The budget is the prompt limit, a hard cap with labels included (`db.py state` prints it; the default is 840). Spend it like this:

- Open `Cut:` with the word `SPLIT`. Voyage reads it as the signal to run the protocol: header first, scene labels, and the scene without an action held still.
- Name the scenes A and B (and C), and put the first names of the PCs in parentheses.
- Write one `Crew:` clause per scene, prefixed `A:` or `B:`, and skip NPCs you do not need.
- Give each advancing scene one world move in `World:`, prefixed `A:` or `B:`. A scene that holds gets no world move.
- Drop `Tone:` unless the mood differs between scenes.
- Use `Facts:` only for a reminder of rule 4 or rule 5. <!-- SPL-11 -->

A character counter may treat the 📍 emoji as two characters, so leave a margin of 10 characters under the limit. <!-- SPL-12 -->

### Compact `Cut:` forms

| Case | Form |
|---|---|
| Both scenes advance | `Cut: SPLIT, <day/time>, one clock. Open with 📍 header; label each scene. A: <Location/area> (<PC>). B: <Location/area> (<PC>). Both advance.` |
| One scene advances | `Cut: SPLIT, <day/time>. Only B advances: <Location/area> (<PC>). A holds, not re-narrated: <PC> <activity> at <Location/area>, waiting since <time>.` |
| Regroup | `Cut: REGROUP, <day/time>, <Location/area>. Say once that <PCs> have reunited; drop the header.` |
| Travel (the player has said it) | `Cut: SPLIT, <day/time>. <PC> travels from <Location/area> to <Location/area> as the player chose; arrives at <time>.` |

## Worked examples

Both examples use placeholder PCs, NPCs and places. Each count below comes from a script (Python `len` on the exact text in the block, trailing newline removed). The default limit is 840.

### Example 1: both scenes advance (444 characters)

```text
Cut: SPLIT, Day 12 evening, one clock. Open with 📍 header; label each scene. A: Home Base/shared-kitchen (Ren). B: City Academy/classroom-5a (Sam). Both advance.
Tone: warm vs tense.
Crew: A: Yumi stirs a pot and apologizes for the clatter: "Sorry, almost done." B: Kenji fights a jammed projector and waves it off: "It's nothing, really."
World: A: the kettle whistles, then cuts off. B: an intercom voice, dry: the room closes in ten minutes.
```

### Example 2: one scene advances, one holds (351 characters)

```text
Cut: SPLIT, Day 20, noon. Only B advances: City Academy/classroom-5a (Sam). A holds, not re-narrated: Ren waits on Home Base/rooftop for Kenji's call, waiting since 11:30.
Crew: Yumi times Sam's quiz: "Faster. Careless errors cost you."
Facts: Yumi knows nothing about A.
World: the hallway bell rings; a late student slips in and takes the last seat.
```

Why they work:

- Example 1: the first line cues rules 1 and 2 (the header and the labels). Each NPC is in one place (rule 5: Yumi in the kitchen, Kenji in the classroom). Each scene has its own world move.
- Example 2: the `Cut:` names rules 3 and 6 (only B advances; A holds, with a waiting-since time). Scene A is not narrated. Yumi is told she knows nothing of scene A (rule 5).

## Multi-player tables

At a table with several players, threads are tracked per character (`pc-thread`, naming the character in its text). If one PC leaves the arc and another stays, that is a split party and the arc stays active. A pivot needs no PC in arc contact (see the pivot playbook, PIV-8). <!-- SPL-13 -->
