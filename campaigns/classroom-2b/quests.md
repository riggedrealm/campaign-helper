# Quests

Every arc quest, with the trigger to introduce it, giver and location, objectives in order, outcomes, Standing effect, and a ready **seed line** for the `World:` line of a prompt. Voyage generates the quest when a prompt tells it to start one; it then keeps its own record, so do not restate objectives after the first prompt.

Rules for quests in prompts:

- A seed line goes in `World:` and costs about 100 to 200 characters. Count it with the rest of the prompt (700 maximum).
- Quest names are what the players see. They are written not to spoil.
- Introduce one quest per turn at most.
- Quests do not "fail" and end the game. A missed objective changes what happens next and what Standing does; nothing ends.
- Standing is never named in a prompt.

All givers and locations below are existing NPCs, new NPCs introduced in `cast.md`, and existing places.

| # | Quest | Kind | Trigger | Start seed length |
|---|---|---|---|---|
| 1 | Move-In Weekend | Act 1 | Turn 2 (Day 1) | 110 chars |
| 2 | Midterm Marks | Act 2 | First specialization class, Day 10 | 158 chars |
| 3 | Cracks in the House | Act 3 | After the midterm, Day 43 | 151 chars |
| 4 | Final Review | Act 4 | Day 78 | 154 chars |
| 5 | Gentle Hands | Personal (Tatsuya) | Relationship 50 or more | 140 chars |
| 6 | Built, Not Born | Personal (Mio) | Relationship 50 or more | 117 chars |
| 7 | Old Corners | Personal (Shin) | Relationship 50 or more | 112 chars |
| 8 | Off-Camera | Personal (Sunny) | Relationship 50 or more | 130 chars |
| 9 | The Lab Job | Nightshade job offer | Around Day 52 | 156 chars |
| 10 | Retest | Mio's retest | The fraud comes out | 157 chars |
| 11 | Battle Test | Act 4 showcase | Pairs announced, Day 80 | 157 chars |

---

## 1. "Move-In Weekend" (Act 1 main quest)

- **Trigger**: the first director prompt (turn 2), as soon as the story start has played out. Update on Day 4 when the tournament is announced.
- **Giver / location**: Sakura Lane House Manager at `Sakura Lane Sharehouse/building-entrance`.
- **Objectives**:
  1. Settle in: unpack, choose how to spend the weekend.
  2. Meet the housemates (Tatsuya, Mio, Shin, Sunny).
  3. Prep for Monday: orientation at `Chikara Academy`, Day 3.
  4. Enter the placement tournament as a team at `Chikara Battle Arena`, Days 6 to 7.
  5. Receive a placement.
- **Success**: the team is placed. Standing +0 to +10 from the tournament, +3 for a house cohesion moment (welcome dinner).
- **Missed / fail**: a skipped class −2; a tournament loss costs marks, not a place.
- **Seed (start)**: `Start quest "Move-In Weekend" (giver: Sakura Lane House Manager): settle in, meet housemates, prep for Monday.`
- **Seed (update, Day 4)**: `Update quest "Move-In Weekend": placement tournament Days 6-7 at Chikara Battle Arena; enter as a team.`

## 2. "Midterm Marks" (Act 2 main quest)

- **Trigger**: the first specialization class, Day 10 (Monday of week 2).
- **Giver / location**: Kenji Arimura at `Chikara Academy/classroom-4d`.
- **Objectives**:
  1. Attend specialization classes.
  2. Take a part-time job (`WorkLink Exchange/job-board`) or join a club.
  3. Take part in the joint 1A/2B field exercise, Day 34, `Hero Field Complex/rescue-village`.
  4. Attend the midterm progress review, Day 42, `Chikara Academy/main-hall`.
- **Success**: classes attended, house routines kept; +2 per good week, +3 to +5 for public rescues or good conduct in the field exercise.
- **Missed / fail**: skipped classes −2 each; a disciplinary incident −5; a public scandal −5. Shimazu still tells 2B it is failing at the review.
- **Seed**: `Start quest "Midterm Marks" (giver: Kenji Arimura): attend specialization classes, find a job or club, join the Day 34 field exercise, face the Day 42 review.`

## 3. "Cracks in the House" (Act 3 main quest)

- **Trigger**: after the midterm (Day 43), when the house is quiet and strained.
- **Giver / location**: Sakura Lane House Manager in `Sakura Lane Sharehouse/shared-lounge`: "Something is wearing on this house."
- **Objectives**:
  1. Find out what is wrong with the house, starting with who is carrying a weight.
  2. Decide how to handle it: help, confront, hide, or report.
  3. Protect the house if trouble comes to the door.
  4. Face Shimazu's inquiry.
- **Success**: the house survives the crisis intact, whichever path is chosen. Standing per path (see `arc-bible.md`).
- **Missed / fail**: a path left unresolved lets the collection contract go live on Day 61; the next fight happens on worse terms. Theft discovered −25. An off-books fight −5.
- **Seed**: `Start quest "Cracks in the House" (giver: Sakura Lane House Manager): something is wearing on the house; find out what, and decide what to do about it.`

## 4. "Final Review" (Act 4 main quest)

- **Trigger**: Day 78, as Act 4 opens.
- **Giver / location**: Kenji Arimura at `Chikara Academy/main-hall`.
- **Objectives**:
  1. Learn the Battle Test pairs (Day 80).
  2. Train with Arimura through weeks 12 to 14.
  3. Take the Battle Test (separate quest).
  4. Attend the final review, Day 112, `Chikara Academy/main-hall`.
- **Success**: the review is held; the ending is set by Standing (70+ Renewed, 40 to 69 Probation, under 40 Dissolved). The +15 integrity credit applies for a confession.
- **Missed / fail**: no failure; the ending changes. Dissolved still gives a move-out epilogue.
- **Seed**: `Start quest "Final Review" (giver: Kenji Arimura): the semester ends in the Battle Test and a Day 112 review by Vice Principal Shimazu; train and prepare.`

## 5. "Gentle Hands" (Tatsuya's personal quest)

- **Trigger**: a player character reaches relationship 50 or more with Tatsuya. Other player characters may join if present or invited.
- **Giver / location**: Tatsuya Ōmine, `Sakura Lane Sharehouse/maple-bedroom` or `shared-kitchen`.
- **Objectives**:
  1. Learn why he apologizes, and what happened at the gym wall.
  2. Test small, controlled releases at `Hero Field Complex/field-complex`.
  3. Build a safe "bleed-off" (plates or a shock sink; Mio can help; a spotter such as Yūto or Arimura).
  4. Make the full release at the gym wall he broke, `Chikara Battle Arena/training-bays`.
- **Success**: the full release is controlled and the wall holds (or comes down deliberately). A reliable big move for the Battle Test; Standing +3 (house cohesion).
- **Missed / fail**: it stays open. Tatsuya keeps leaking; furniture cracks.
- **Seed**: `Start quest "Gentle Hands" (giver: Tatsuya Ōmine): find a safe way for Tatsuya to fully release his power; it ends at the gym wall he broke.`

## 6. "Built, Not Born" (Mio's personal quest)

- **Trigger**: a player character reaches relationship 50 or more with Mio. Works whether or not the secret comes out.
- **Giver / location**: Mio Tachibana, `Sakura Lane Sharehouse/loft-bedroom`.
- **Objectives**:
  1. See her sketches and hear what she wants to build.
  2. Source parts at `Support Street/prototype-studio` and `Gearshift Support Shop/inventory-room`.
  3. Build and bench-test the rig.
  4. Field-test it at `Hero Field Complex/mobility-track`.
- **Success**: a legitimate rig of her own; ties into the retest (makes a pass natural); Standing +3 (cohesion) if it is shared with the house.
- **Missed / fail**: it stays open. If the fraud comes out, her retest is harder.
- **Seed**: `Start quest "Built, Not Born" (giver: Mio Tachibana): help Mio build a gear rig of her own, from parts to field test.`

## 7. "Old Corners" (Shin's personal quest)

- **Trigger**: a player character reaches relationship 50 or more with Shin.
- **Giver / location**: Shin Asakura, `Sakura Lane Sharehouse/rooftop-chill-deck` or the entrance step.
- **Objectives**:
  1. Learn why Shin has gone quiet (a message from the old gang).
  2. Go with him to `Kurokawa District/backstreet-crossroads`, where the Nine Corners want him for one job.
  3. Decide whom Shin trusts: a player, Yūto, Arimura, or no one.
  4. Resolve the job: refuse, foil it, or redirect it.
- **Success**: the old boss releases him, or Shin walks away with the house behind him; a clean break. Standing +3 for good conduct if the job is stopped without scandal.
- **Missed / fail**: it stays open; the gang tries again. A public scandal −5.
- **Seed**: `Start quest "Old Corners" (giver: Shin Asakura): Shin's old gang wants him for one job; decide who he can trust.`

## 8. "Off-Camera" (Sunny's personal quest)

- **Trigger**: a player character reaches relationship 50 or more with Sunny.
- **Giver / location**: Park Seo-yeon "Sunny", `Sakura Lane Sharehouse/rooftop-chill-deck` or `sunrise-bedroom`.
- **Objectives**:
  1. Learn what the scandal video really was, and why she deflects.
  2. Find the unedited footage (`Pulse Media Tower/press-room` or `Power Practice Studio/practice-floor`).
  3. Learn what the footage shows: she took the blame for Ayame.
  4. Settle things with Ayame, privately (`Chikara Academy/north-rooftop-overlook`) or at the Battle Test.
- **Success**: Sunny chooses (expose, forgive, or let it go) and Ayame chooses whether to own it. Standing +3 to +5 for good conduct if handled well.
- **Missed / fail**: it stays open; the clip resurfaces. A public scandal −5.
- **Seed**: `Start quest "Off-Camera" (giver: Park Seo-yeon "Sunny"): find the truth behind Sunny's scandal video and settle things with Ayame.`

## 9. "The Lab Job" (Nightshade job offer)

- **Trigger**: around Day 52, when Mio's broker message reaches the players (Mio brings it to them, or a player sees it).
- **Giver / location**: Sōichi Tamaru, through the Nightshade app; in person at `Nightshade Exchange Relay/contract-room` if the players go.
- **Objectives**:
  1. Learn what the job is: steal the Lantern Coil from the Support lab, `Chikara Academy/classroom-5a`, to clear Mio's debt.
  2. Decide: accept, refuse, or stall (deadline Day 60).
  3. If accepted: scout the lab, get in, take the Coil, hand it off at `Riverside Green/riverside-bridge`.
- **Outcomes**:
  - **Accept and succeed**: debt cleared. Standing −25 if the theft is discovered (it might never be).
  - **Refuse or stall**: the collection contract goes live on Day 61; collectors hit the house (see "Cracks in the House").
- **Seed**: `Start quest "The Lab Job" (giver: Sōichi Tamaru): a broker offers to clear a debt in exchange for taking a prototype from the Support lab; answer by Day 60.`

## 10. "Retest" (Mio's retest)

- **Trigger**: the fraud comes out: a confession, a theft discovery, or a Nightshade leak. Within seven days; no later than Day 98. Default Day 84.
- **Giver / location**: Reiko Shimazu at `Chikara Academy/classroom-5a`, with Arimura supervising.
- **Objectives**:
  1. Prepare: help Mio study, build, practice (at least two meaningful prep beats).
  2. Sit the supervised retest: Mio builds a working tool from standard stock and uses only Minor Magnetism to free a mock casualty from a jammed door.
- **Success**: Mio stays at Chikara Academy and in 2B. Standing +10.
- **Fail**: Mio is removed (transferred out); this feeds the Probation ending. Fail only if prep was absent and the in-scene puzzle goes unsolved.
- **Seed**: `Start quest "Retest" (giver: Reiko Shimazu): Mio must pass a supervised retest with her real power and her own gear before the Battle Test; help her prepare.`

## 11. "Battle Test" (Act 4 showcase)

- **Trigger**: Day 80, pairs announced.
- **Giver / location**: Reiko Shimazu at `Chikara Academy/main-hall`; test held at `Hero Field Complex` (`rescue-village`, judged from the `observation-tower`).
- **Objectives**:
  1. Learn your pair (players pair with each other; odd player with Sunny).
  2. Train with Arimura (`Hero Field Complex/mobility-track`).
  3. Walk the site (`Hero Field Complex/field-complex`).
  4. On Day 105: evacuate civilians from the simulated collapsing transit station, handle the proctor threats, and respond to the second collapse. Help other pairs, including 1A.
- **Success**: Standing +5 to +25 (scoring, teamwork, rescues, helping 1A).
- **Fail**: Standing +0 to +5; nothing ends.
- **Seed**: `Start quest "Battle Test" (giver: Reiko Shimazu): paired training for the Day 105 Battle Test at Hero Field Complex; evacuate civilians and help other pairs.`
