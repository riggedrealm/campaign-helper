# Reveals: ladders, milestones and personal quests

Open this playbook when a milestone day arrives or a reveal-ladder step is about to be played or recorded.

## Ladder steps

A reveal ladder holds an arc secret as a list of steps (`db.py thread "<name>"` shows a ladder). Its steps stay hidden until the story establishes them. `thread-reveal` enforces the act, the order and the gates of each step: after the milestone that a gate waits for has happened, record it with `--gate-met`, and use `--force` only on the user's word. <!-- REV-1 -->

What stays out of prompts and dialogue until a step is revealed is set by the bootstrap (SEC-1) and `core.md`, NPCs (NPC-3). The brief to read on a reveal is in `core.md`, Triggers (TRIG-1).

## Pulling a step forward

When the PC reaches a thread early, its next step may move up exactly one act if the scene needs it to make sense. Record it with `thread-reveal NAME STEP --player-driven --evidence "..."`, or with `"player_driven": true` on the op in a payload. The step is allowed only when it has no unmet gate and every earlier step is revealed. The command stores the flag and the evidence. A step two or more acts early, a gated step and a step that skips earlier steps still need `--force`. Milestones stay fixed. <!-- REV-3 -->

## Side quests

A side quest advances an arc thread by at most one step, and never past a milestone. <!-- REV-4 -->

## Personal quests

A personal quest unlocks only when the story has shown real closeness with that NPC: shared secrets, time together, a moment that landed. The arc bible's Personal quests section (`db.py bible`) names each quest and the closeness that unlocks it. When one unlocks, seed it like any other quest (`core.md`, Prompt format). <!-- REV-5 -->

## After a reveal

After a revealed step changes how an NPC is portrayed, plan a Studio edit with only the changed fields (see the Studio playbook, STU-4; a revealed step may go into Studio, STU-5). It is bundled and applied at a natural break like any other Studio request. <!-- REV-6 -->

## Where related rules live

- `core.md`, The world: beats as hooks and fixed milestones (WLD-1).
- The arc-planning playbook: a twist reveal gets a pressure card from the Opus planner (ARC-14), and `arc-reveal` records the twist (ARC-23).
