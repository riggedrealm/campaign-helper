# Campaign start: sheets, turn 1 and the opening

Open this playbook when the campaign is at turn 0 or 1: the player characters have no sheets yet, or Voyage's story start has not been recorded.

## Player-character sheets

The sheet fields (`pronouns`, `power`, `background`, `notes`) come from the user only. Never invent one. Ask once, in the first chat, with this intake for each player character (1 to 4):

- name and pronouns;
- power concept: its name and what it does, or "none yet";
- background;
- home base or room, from the choices the campaign's `director.md` gives, if it gives any;
- the campaign's own questions, also from `director.md`, one bullet each.

Ask for story facts only, no stats; Voyage keeps its own sheet. <!-- START-1 -->

Record the answers with `pc-add` (name, player, room, and the sheet fields the user gave) or, for a character that already exists, `pc-sheet <name> --power "..." --evidence "sheet provided by the user"`. Fill only the fields the user supplied. <!-- START-2 -->

## Turn 1

Turn 1 is Voyage's story start. You do not write a prompt for it. Record it with `record`, with `"prompt": "none"` in the `turn_log`; the payload is described in `director/reference.md` (REF-2). As on any turn, record only what Voyage's output established. You begin steering at turn 2. <!-- START-3 -->

## The opening card

The campaign's opening card, `campaigns/<name>/opening.md`, is director-only. Voyage's story start opens the first scene, and the card says what is true behind it:

- where and when the scene starts;
- who is there, and what each of them wants right now;
- the seeds for turns 2 and 3: the first quest seed line and the first small surprise (one new quest seed per turn);
- when the scene ends and what the next beat is.

An arrival scene budgets 2 turns at most (see the pacing playbook, SCN-2). <!-- START-4 -->

## Session zero and the first charter

Session zero and the first arc charter are optional, and you do not wait for either. Without them the campaign plays from turn 1 on open threads, and arc functions (and so pivots) stay off (PIV-10 in the pivot playbook). Offering to plan belongs to the arc-planning playbook (TRIG-12, `core.md`, Triggers). <!-- START-5 -->
