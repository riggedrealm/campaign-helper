# Fights: story only

Open this playbook when a fight is about to start or has started.

A fight is a scene like any other: open it with `scene-start` tagged `fight`, and budget it as the pacing playbook says. Voyage owns every mechanic of the fight (see the bootstrap, INV-1); this playbook covers only what you write around it.

## Who goes where

Put the villain's personality, want and dialogue in `Crew:`. Put the battlefield in `World:`. <!-- FGT-1 -->

## Opening the fight

At the fight's opening, give Voyage the villain sheet's rule and weakness as plain facts in `Facts:`. Read them from the villain sheet in the arc bible (`db.py bible` lists the sections) and write them the way `core.md`, Prompt format, writes `Facts:` (FACTS-1). Only the rule and the weakness go in; the rest of the sheet stays hidden (see the bootstrap, SEC-1). Campfire mode has no `Facts:` line: the threat's tier and rules are in the round packet (`campfire.md`). <!-- FGT-2 -->

## Conditionals

Voyage runs every exchange and holds the combat state, which you cannot see. Write fight prompts as conditionals on that state. For example: "If any rats are alive, they shy from light. If none are left, the fight is over." <!-- FGT-3 -->

## What a fight prompt never says

Never state who is alive, dead or winning, who hits, or whether the rule cracks. Never add enemies, waves, reinforcements or reversals in `World:` or `Facts:`. Describe only the setting and the enemy's standing rules. <!-- FGT-4 -->

A short illustration of a round, not a template:

```text
Facts: The Warden's armour hums and cannot cross a line of salt. Its left hinge is old and slow.
Crew: The Warden, stern and unhurried, speaks in short orders: "Stand aside."
World: A cracked bell tolls overhead and the floor is slick with lamp oil. If any guards are still standing, they keep to the doors.
```

## The fight status line

When the paste carries a `fight status:` line, use it as the state of the fight and do not infer the state from the narration. <!-- FGT-5 -->

## Ending the fight

If the user says the enemy is dead or the fight is over, or pastes a combat-panel line that shows it, close the fight at once: the prompt says so and moves to the aftermath. Otherwise the fight ends when Voyage's output shows it decided. Never pad a fight to reach its budget. <!-- FGT-6 -->

When the fight is over, close its scene with `scene-end`.

## Keeping a fight moving

Change `Crew:` and `World:` every round. Escalate, or pay off a tell or a set piece, and stay inside the limits above: new behaviour and new setting detail, never new enemies. Never reuse last round's gesture; the turn brief's rotated picks (CREW-1) help. <!-- FGT-7 -->
