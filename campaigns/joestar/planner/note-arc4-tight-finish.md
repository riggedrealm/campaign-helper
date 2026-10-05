# Arc 4 tight finish, then Act 3 (director only)

Planner session, 2026-10-05, at turn 482. The user chose two things:

- **Path to Act 3: tight finish.** The rest of Arc 4 runs short (about 17 turns, t483 to about t500), then Act 2 closes and Act 3 is planned.
- **Current scene: one-turn close.** The players' next input resolves the back-lane chase in one compact beat, then a hard cut.

Arc 4 is at 44 turns of 34 (129%). This is the user's "wrap up" answer to ARC-17, so don't ask again. Act 2 ends when Intelligence falls (bible 3).

## Beat budgets (were / now)

| Beat | Was | Now | Notes |
|---|---|---|---|
| 4-2 Dead Zone | 6 | 1 | t483: the close (card below); `scene-start` and `scene-end` both go in t483's payload |
| Regroup and invitation | 0 | 1 | t484: the players' input after the chase (deputy fork, Reiko if they ask); `World:` brings the invitation |
| 4-3 Neutral Ground | 5 | 3 | Opus card, `card-4-3-neutral-ground.md`; the twist lands even if the talk breaks |
| 4-4 Go Dark | 4 | 3 | one spotlight-montage turn (Hana's room, Mikoto's drills, Rin's rent find, Ayame's decoy), then the decoy and plan |
| 4-5 Lights Out | 8 | 5 | 1 infiltration turn, then the showcase fight, which ends when it's decided (FGT-6) |
| 4-6 Final Frame | 5 | 3 | corner, the fork (prompt names the fork, never the pick), aftermath |
| Breather | 2-3 | 1-2 | morning after at Lumiere; no cliffhanger, no "a week later" hook |

Personal threads don't count against these budgets: Ayame's owed date, Jovian and Yuzuki, Reiko's talk. They play only when the players ask, per the consent rule, and get their own turns.

Launch the Opus showcase card for 4-5 when 4-4's second turn is out (ARC-14), and the finale card for 4-6 when 4-5's fight starts.

## Plan changes (log them)

1. **Replay debuts at 4-3, not as a 4-2 intercept.** A one-turn chase can't hold a fight, so the round-one loss is gone. He first stands at Kiriyama's shoulder at 4-3 and shows his tell only. The 4-5 showcase is unchanged, because his rule still rests on footage.
   - Change the gate of `Replay's tape` step 1 from "Beat 4-2 Dead Zone: he intercepts the crew" to "Beat 4-3 Neutral Ground: he stands at Kiriyama's shoulder".
2. **Budgets** as in the table: update bible 5.2 (beat headers), bible 12 (named beats) and bible 3's pulse check.
3. **Deviation op** for t483's payload:
   `act-deviation 2 "Arc 4 tight finish (user, planner session t482): 4-2 closes in one turn; budgets 4-3 3, 4-4 3, 4-5 5, 4-6 3; Replay debuts at 4-3 instead of a 4-2 intercept." ` with evidence "User chose 'Tight finish' and 'One-turn close' in the planner session".

## 4-2 close: pressure card for t483 (inline)

Place: `Steam Lantern Alley/noodle-corner`, the back lane behind the closed noodle counter. Before the prompt, `pos` both PCs there; the state still has them at Pulse Printworks. Tag: `fight` (a contested chase), budget 1.

**NPC wants now**
- **Records deputy:** wants out with the locked case before a lens gets his face.
- **Scooter rider** (unnamed pickup, no new NPC): wants no trouble.
- **Sedan driver:** wants to be forgotten.
- **Kaito Arashima** (on a roof): wants the angle; calls lines, dry.
- **Nobu:** can kill the lane's one camera on a word.
- **Haruto:** curt; wants this done fast and quiet.

**If the PCs engage**
- **Deputy:** runs for the scooter. If cornered, he bargains with the case. A contested ask either way, so Voyage rolls it, and the prompt carries a conditional, never his yes.
- **Rider:** leaves the moment it turns loud, with or without him.
- **Sedan driver:** bolts at the first slack.

**If they don't engage**
- The deputy reaches the scooter and is gone.

**World, either way (bible 5.2 fail forward):**
- If the crew holds the deputy, his phone lights up in a PC's hand. If he slips, he drops it on the stairs. On screen, the contact he reports to shows the name Shogo Kiriyama, 'The Archivist'.
- That is `The Archivist's name` step 1, so follow `reveals.md` (TRIG-5). Run `thread-reveal` with `--gate-met` only after Voyage's output shows the name.
- No power details in the prompt: Still Frame stays for 4-3.

**Close**
- `scene-end` in t483's payload.
- `clock-done` for "Deputy at the Steam Lantern Alley storeroom (t479)" once the output resolves the deputy.
- Next `Cut:` only as far as the players' input reaches.

**Fork (players only):** if they hold him, police or turn him is their call at t484. Reiko questions him only if a PC brings her in.

## t484: regroup and invitation

- `World:` (200 characters at most): the deputy's phone, or the case, gets a courteous message from the same contact. It invites the crew to talk in public: a named place from the 4-3 card and a time (tomorrow, Day 21 Friday, evening).
- No threat: a trade offer, leverage as manners.
- `Cut:` to the meeting only when the players' input accepts or travels there (CUT-2).
- **Studio:** if the deputy stays in play (held or turned), file the recurring-NPC Studio request for him. If he slipped, skip it.

## After the breather: closing Act 2 (director session, at a break)

1. **Act retro (SCN-8).** The planner launches `review.md` in act-retro mode. The director writes the retro and logs it: `feedback --kind act --best --drag --notes --turn N`.
2. **Close Act 2.** Run `act-close 2 --retro @file`. Set Act 3's `from_day` to the current day in `campaign.json` `acts` (bible 3), and unlock bible 6.
3. **Plan Act 3 in a planner session with the user, never mid-turn:**
   - the ARC-6 retro question ("Best moment? Anything drag?");
   - session zero, the first time (this switches arc functions on);
   - the Act 3 pitch (`act-plan 3`);
   - the first Act 3 charter (`charter.md`, Opus), whose recruit seat follows ARC-8 as narrowed in `director.md`.
4. **Run `preflight` at the act start.**

Until then, the open personal threads stay available as breather scenes (bible 5.5).
