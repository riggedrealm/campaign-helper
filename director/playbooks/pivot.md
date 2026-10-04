# Pivot: side goals, leaving the arc, drift

Open this playbook when the player character follows a thread of their own: a side goal, a move away from the arc's planned party or place, or a stretch with no arc contact.

Side goals and leaving the arc work in every campaign from turn 1. Drift and the pivot flow need an arc to leave, so they run only when arc functions are on. Arc functions (and so pivots) switch on only when the campaign has a session zero and a charter; everything else works from turn 1 without them. <!-- PIV-10 -->

## Side goals

Size a side goal when the PC takes it up: an errand, a thread or a storyline. A side quest needs at least two scenes. Rule it reasonable, partly reasonable or unreasonable; the consequences come in the fiction. Give the user one line about the ruling, which is the ruling line that `core.md`, Reply, allows (REPLY-2), and never pause play. <!-- SIDE-1 -->

Weave side goals into the world instead of walling them off. Tie the player's projects into the cast, and never punish a project with an arc threat. A thread the PC keeps following until it carries their story is the case for the pivot flow below. <!-- SIDE-2 -->

## Leaving the arc

These rules apply when the players walk away from the party, contact or place the arc planned for them. For example, the arc planned for the PC to learn a rumor from the guild clerk, and the PC goes to the net menders instead.

- The players' choice stands. Play the chosen party from its own agenda, and never steer back toward the arc. <!-- LEAVE-1 -->
- Ask yourself what the planned contact was for. The new party supplies it on its own terms, with its own price and motive. In the example, the net menders give the rumor, and what they want for it is theirs to decide. <!-- LEAVE-2 -->
- Whatever clues the new party offers come only from the current ladder rung (`thread "<name>"` shows it). Never hand out a later step. Milestones are unaffected: they stay fixed and happen as the world acting (`core.md`, The world, WLD-1). <!-- LEAVE-3 -->
- If the new party is thin, build it through lookups (`faction`, `lore`, `loc`), never from the world files themselves. Improvise a want, a price and one voice, and record them at once (`add-npc`, `agenda`, `fact`). If the PC stays with them, the Planner fleshes them out. <!-- LEAVE-4 -->
- The party the players passed over keeps its clock and its agenda. It may return as a rival or as a better offer. This holds with or without arc functions. <!-- LEAVE-5 -->

## Drift

Drift is a stretch away from the arc. Count the turns since the arc started in which no turn log set `"arc_contact": true`. When 8 turns in a row have passed with no arc contact, the world moves the front on (record it with `arc-move`), you record `arc-review ID --kind drift --notes ...`, and you ask the user one line: "Re-aim?" The turn brief prints the drift line when the count is reached. <!-- DRIFT-1 -->

The drift line "Re-aim?" is the question the user hears. A yes starts the pivot flow below at the bridge, built from what the PC has been doing; the old arc is parked when the new arc is adopted, not closed.

## The pivot flow

A pivot turns the story toward a direction the PC has already chosen, without ever making play wait. The steps are: off-ramps (prepared ahead of time), detect, bridge, draft, adopt and park, and tell the user. The subagent brief for the off-ramps and the mini-charter is `director/agents/pivot.md`; the charter shape it fills is the one in `director/agents/charter.md` and in the Field reference of the Arc planning playbook.

### Off-ramps

At each arc approval and at each midpoint review (the Arc planning playbook, ARC-16), launch the Opus Planner with the brief in `director/agents/pivot.md`. It writes two or three hidden sketches of five lines each: the promise as a question, one front, a face and a first move, tied to the thread it grows from. Write one sketch per thread the PC has already pursued on screen; `db.py plan-brief` gives the Planner its inputs. Read what comes back, then store it with `db.py arc-offramps ID --file F.json`: a JSON list of sketches, each an object of non-empty strings with the keys `thread`, `promise`, `front`, `face` and `first_move`. A new list replaces the earlier one, and the arc must still be going. <!-- PIV-1 -->

Off-ramps are prepared, never seeded into a prompt. You do not see them on routine turns: `arc` leaves them out (`arc ID --offramps` prints them, for you only), and `arc-pivot` prints one only when a pivot is detected. They are director-only (the bootstrap skill, SEC-1).

### Detect

Detect a pivot at once when an input plainly commits the PC to a new party or goal, for example when the player says Ren will throw in with the net menders. Otherwise, detect it after three turns on a new thread with no arc contact. Run `db.py arc-pivot` (add `--thread "<the thread>"` when you are matching a plain commitment). It is read-only. It prints `arc functions: on` or `off`, then either `no pivot detected (reason)` or `pivot detected (reason)` with the live arc and the matching off-ramp, only when a pivot is detected. Without `--thread`, the three-turn count needs a `pc-thread` note in or just before the last three logged turns, so record the thread as it shows. The turn brief also shows a pivot line when the three-turn count is reached. Threads come from the `pc-thread` notes you keep (`core.md`, The world, WLD-4). <!-- PIV-2 -->

A pivot happens only when no PC is in arc contact. Threads are tracked per character (`pc-thread`, naming the character in its text). If one PC leaves the arc while another stays in it, that is a split party and the arc stays active (the Split-party playbook, SPL-13). <!-- PIV-8 -->

### Bridge

When a pivot is detected, write the card for the next scene yourself, inline, from the leaving-the-arc rules above (LEAVE-1 to LEAVE-4). Use the pressure-card shape from the Arc planning playbook (ARC-14): what each relevant NPC wants now, what they do if the PC engages, and what they do if not. Do not wait for the draft; the bridge card exists so that play never waits. <!-- PIV-3 -->

### Draft

At the same time, launch an Opus subagent in the background with the brief in `director/agents/pivot.md`. It writes a mini-charter from the matching off-ramp, or from scratch when none matches. The mini-charter has one front with two or three moves, a face, three clues and a budget of 10 to 15 turns. It is built only from what the PC did, and it is tied into existing ladders where it can be. Keep playing on bridge cards until the draft is ready. The subagent returns the charter as JSON; write it to a file and store it with `db.py arc-plan --file F.json`. <!-- PIV-4 -->

A mini-charter is still a charter, so review it yourself the way the Arc planning playbook reviews one (ARC-8 and ARC-9) before you adopt it.

### Adopt

After your review, adopt the draft with `db.py arc-adopt ID --turn N --evidence "..."`. It checks the limits below, makes the arc `provisional` and parks the active arc. It takes a `draft` only and needs a live arc to park. Of the limits, it checks the twist, the new NPC count, one front with two or three moves, three clues, a budget of 10 to 15 turns and a session zero line or veil match; it lists every problem and exits 4 unless you pass `--force`, which is recorded. The ladder and area limits are yours to hold. A provisional arc is live: record its moves, clues and contact like an active arc's (the Arc planning playbook, In play). The limits are:

- No twist.
- No ladder step revealed early.
- At most one new NPC, the face.
- New areas only inside existing locations. The main chat adds one with `add-area` only once the story shows it (`core.md`, Prompt format, FMT-7); a mini-charter that names an area does not create it.
- It passes the same lines-and-veils check as any charter, against session zero.
- It stays off the public planner page until it is approved.

<!-- PIV-5 -->

### Park

`arc-adopt` leaves the old arc `parked`. While it is parked, day turnover keeps moving its clocks and fronts (`director/playbooks/pacing.md`, WLD-3), and it may come back as a rival or a better offer, as LEAVE-5 says. The parked arc is not live, so one live arc at a time still holds. <!-- PIV-6 -->

### Tell the user

At the next natural break after adopting, give the user one line with three choices: approve, re-aim or go back. For example: "The story has turned toward the net menders and away from the guild plot. Approve the new direction, re-aim it with me, or go back to the guild?" Name only what the PC did on screen, and pass the line through `db.py scan` before the user sees it (`core.md`, Chat and orchestration, ORCH-5). This is the pivot line that `core.md`, Reply, allows (REPLY-2). At a multi-player table the host alone approves. <!-- PIV-7 -->

### What each answer does

- **Approve:** the provisional arc becomes active. Run `db.py arc-approve ID --lines-checked` (the flag is needed when session zero holds lines or veils). No `arc-start` follows, because the arc is already live. It may now appear on the planner page.
- **Re-aim:** redraft the new arc's direction with the user. Take the user's steer, have the Planner redraft the mini-charter with the brief in `director/agents/pivot.md`, review it as under "Draft", and adopt it. The provisional arc stays live until the new draft is adopted, and the old arc stays parked; `arc-adopt` then sets the earlier provisional arc aside.
- **Go back:** run `db.py arc-unpark OLD_ID --notes "..." --turn N --evidence "..."`. In one write it makes the parked arc live again and closes the provisional arc as `set_aside`, with the note as its short retro on what the PC did there, so two arcs are never live at once.
- **Drop for good:** when the user drops the old arc for good, close it as `set_aside` with a short retro on what pulled the PC away: `db.py arc-close OLD_ID --status set_aside --turn N --evidence "..." --notes "..."`.

<!-- PIV-9 -->

## Commands

Plain reference. These take the write lock, except `arc-pivot` and `scan`, which are read-only.

| Command | Use |
|---|---|
| `arc-offramps ID --file F.json` | Store the Planner's hidden off-ramp sketches on an arc |
| `arc-pivot [--thread TEXT]` | Print the matching off-ramp, only when a pivot is detected |
| `arc-plan --file F.json` | File the mini-charter as a draft |
| `arc-adopt ID --turn N --evidence TEXT [--force]` | Check the limits, make the draft `provisional`, park the active arc |
| `arc-approve ID --lines-checked` | Approve a provisional arc: it becomes active |
| `arc-unpark OLD_ID --notes TEXT --turn N --evidence TEXT` | Go back: the parked arc is live again and the provisional one closes as `set_aside`, in one write |
| `arc-close ID --status set_aside --turn N --evidence TEXT --notes TEXT` | Drop an arc for good |
| `arc ID --offramps` | Read an arc's off-ramps (director only) |
| `pc-thread "text" --turn N --evidence TEXT` | Record what a PC keeps returning to (name the character in the text) |
| `scan FILE\|-` | Hidden-term scan of the pivot line |

A `provisional` arc is live but not yet approved; a `parked` arc is paused, with its clocks and fronts still moving.
