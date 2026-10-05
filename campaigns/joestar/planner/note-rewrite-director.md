# Rewrite companion (director only)

On 2026-10-05, at t482, the user chose "keep the played story as canon, rewrite from here". The continuity calls in `note-story-so-far.md` count as accepted, and the user may flip any of them later. That file is the director's reference summary of the played story, not a plan.

The user said not to plan with a storyboard: plan with pressures and questions (charters, act pitch). The Act 3 pitch draft is `note-act3-pitch.json`; apply it with `act-plan 3 --file` only after Act 2 closes and the user approves the shared fields. This file holds what applies at a break and what stays hidden.

## Status of earlier planner files

- **`note-arc4-tight-finish.md` and the cards for 4-3, 4-5 and 4-6 stay valid.** Apply the tight-finish note before t483 as planned; the user already approved it.
- **Act 3 sketch and the forward storyboard:** dropped (deleted). The Act 3 pitch draft replaces them.

## Continuity fixes to apply (accepted calls)

Apply these at a break, each with evidence "User accepted storyboard calls, planner session 2026-10-05".

1. **Calendar resync.** The story calendar puts t482 at Monday, October 19, 2026 = Day 80, evening.
   - Run `db.py time` with day 80 and keep the time block.
   - Check `start_weekday` (Saturday): Day 80 must print Monday.
   - Act 2's range is 1 to 120, so Day 80 stays in Act 2.
   - Review any open clock with a day due: the deputy clock moves to Day 80.
   - Rei's "Friday" deadline becomes Day 84 (Fri Oct 23).
2. **Con proof (t426 to t430).** Add `fact` (kind `decision`): "The loan-office folders were a decoy; Rin's photos of Noa's file and the courier schedule are safe in Nobu's system; the Saionji cover is burned." Bible 5.1's "proof lost" becomes "decoy; cover burned".
3. **Okabe's line at t438** ("another archive, a week") is a bluff and goes nowhere. Add a `fact` so no prompt revives it.
4. **Doorstep fight (t414 to t418):** all three collectors lived, one critical. This is already canon; add the "two bodies" lines to the slips record if they aren't logged.
5. **Hostess roster:** Chiho, Tomoe and Kaede are club staff. Kaede's debt is a HearthOps job: plant it as a `fact` (kind `plant`).
6. **Gara's owed name:** fold it into the deputy's name. When the Archivist's name surfaces at Ep 23, Gara's job counts as paid. Record a `fact` (kind `promise`) and mark it paid at the reveal.
7. **Smugglers with glowing crates (t382):** cut; log them as an `invention` slip.
8. **Jostin's hidden blade:** resolved, since he drew one at t471. Drop the "confiscated" thread.
9. **Spotlight debt:** Reiko and Mikoto have been off screen since t396. Ep 26 (Go Dark) gives both a piece. Pass this to the 4-4 inline card.

## New campaign rule (user, 2026-10-05)

The brothers are never split in a fight or any action scene where combat is tracked: the engine handles one scene well, not two. A non-combat split is allowed, but rarely.

- Add it to `campaigns/joestar/director.md` under "Narrowed rules", as a TRIG-10 narrowing.
- Fix bible 5.3's format line and the Arc 4 spotlight plan ("Jostin's Shadow Step to the archive room").
- The 4-5 card is already fixed.

## User feedback: crowded prompts (t483 trial, 2026-10-05)

"Too many active NPCs, too packed." The rule for every card from now on: at most three active NPCs per prompt, meaning the focus NPC plus one or two crew voices, each with one clause; everyone else reacts in character.

- The 4-2 close card and the 4-3, 4-5 and 4-6 cards now name who is active per turn.
- Proposed generic fix: add an "Active this turn (at most 3)" line to `director/agents/card.md`'s output and to CREW-1's guidance. The planner can make it as a doc change on the user's OK.

## Forward plan, hidden layer

**Act 2 finale:** the existing Arc 4 beats and cards (`note-arc4-tight-finish.md`, then the 4-3, 4-5 and 4-6 cards).

**Act 3:** the forces, doors and spotlight debts are in `note-act3-pitch.json`, under `hidden.notes`. Each arc's charter picks from them, built from what the players did in the arc before. Nothing is pre-scheduled.

**Session zero** gets set at the Act 3 planning session (arc functions switch on). Defaults to confirm:

- pillars: combat 3, social 3, exploration 1, mystery 2;
- tight arcs of 25 to 30 turns;
- ending hope: triumph, with "with a cost" in the act pitch;
- players: 2;
- lines: no ally betrayals; NPC-7 as narrowed.

Ask the user for veils.

**User answers (2026-10-05, planner session):**

- **Act 3 pitch:** shared fields approved as drafted, with the main question ("Who rules Kobuncho when the king comes down to fight for it?"); the alternative was declined. After Act 2 closes, run `act-plan 3 --file note-act3-pitch.json`, then `act-approve 3`.
- **Act 3 theme** changed by the user to "Daigo stops hiding and comes for your people himself" (already in `note-act3-pitch.json`).
- **Act 3, Arc 1 "Open Season"** (`arc-act3-a1-open-season.json`): shared fields **approved by the user** (2026-10-05) after three revisions:
  - plain wording;
  - Kurokawa versus Joestar only;
  - brothers never split in combat.

  After Act 2 closes and the act pitch is filed and approved, file it with `arc-plan --file arc-act3-a1-open-season.json`. First collapse `hidden.refine` (the Arc 4 fork branches) to the played pick, then run `arc-approve A1 --lines-checked`. Check whether the Arc 4 Aether Head seat filled before the recruit search starts.
- **Lines and veils:** none to add. Session zero keeps the campaign's existing rules as its lines (no ally betrayals; NPC-7 as narrowed), with `--veils ""`.
- **Session zero still pending:** the other defaults above (pillars, pacing, ending hope) were not objected to. Confirm them in one line at the Act 3 planning session.
