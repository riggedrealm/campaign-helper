# Rewrite companion (director only)

On 2026-10-05, at t482, the user chose "keep the played story as canon, rewrite from here". The storyboard's continuity calls (`note-storyboard-rewrite.md`) count as accepted, and the user may flip any of them later.

The forward plan for the user is `note-storyboard-forward.md`, a draft awaiting approval. This file holds what applies at a break and what stays hidden.

## Status of earlier planner files

- **`note-arc4-tight-finish.md` and the cards for 4-3, 4-5 and 4-6 stay valid.** The forward storyboard's Eps 23 to 29 are the same tight finish.
  - Apply the tight-finish note before t483 as planned.
  - The forward storyboard's approval isn't needed for Arc 4, which the user already approved.
- **Act 3 sketch:** dropped (deleted).

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

## Forward plan, hidden layer

**Act 2 finale, Eps 23 to 29:** the existing Arc 4 beats with the existing cards.

| Ep | Beat | Card |
|---|---|---|
| 23 | 4-2 close | `note-arc4-tight-finish.md` |
| 24 | Invitation | `note-arc4-tight-finish.md` |
| 25 | 4-3 | `card-4-3-neutral-ground.md` |
| 26 | 4-4 | inline card |
| 27 | 4-5 | `card-4-5-lights-out.md` (provisional) |
| 28 | 4-6 | `card-4-6-final-frame.md` (provisional) |

**Act 3, the doors per arc.** Pick at charter time; at most one or two per arc.

- **Arc 5, Siege of the Home:**
  - Daigo's people hit the home ground.
  - Candidate door: the tunnels (Gara's tip) as the siege's approach. The bathhouse service tunnels already link Lumière and Yuzuki's bathhouse (t111), which makes the home's own tunnels the vulnerability.
  - Showcase: one of Daigo's own; design the villain sheet in the charter.
- **Arc 6, Strike Back:**
  - Candidate doors: the ten-win strike team, and a bigger Kurokawa power broker (name truncated, "Masat..."; a Book 2 door, seed lightly).
  - The combat-data buyer, seeded in Arc 4, stays a Book 2 door: mention it once at most.
- **Arc 7, The King in the Street:**
  - The personal core: Daigo puppeted Iori Vale into Jostin's strike (t182). The payoff for Jostin's control of Blackstar lands here.
  - Daigo's villain sheet (Iron Palm Strike, Territorial Command, Unshakable Stance): rule, tell, weakness, finisher. No sympathetic reveal.

**Recruit seats.** ARC-8 is narrowed: check whether Arc 4's Aether Head seat filled. Then Arc 5 takes a Hearth seat (HearthOps or Arcanum; Jostin's call) and Arc 6 a Spearhead seat.

**Session zero** gets set at the Act 3 planning session (arc functions switch on). Defaults to confirm:

- pillars: combat 3, social 3, exploration 1, mystery 2;
- tight arcs of 25 to 30 turns;
- ending hope: triumph, with "with a cost" in the act pitch;
- players: 2;
- lines: no ally betrayals; NPC-7 as narrowed.

Ask the user for veils.
