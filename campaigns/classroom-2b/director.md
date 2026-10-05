# Class 2B: world sheet

The generic director skill reads this sheet at chat start. It holds only what is particular to this campaign: facts and limits, never generic rules. A narrowing may only add a limit and never loosens a bootstrap invariant (SHEET-1 in `director/core.md`).

## World file and calendar

- World file: `New_World.json` (Voyage's own export; read only through the tools).
- Weekday of Day 1: Saturday (campaign.json `start_weekday`). Day 1 is move-in; classes start on Day 3, a Monday.
- Acts: 1 Move-In (Days 1 to 7), 2 Finding Footing (8 to 42), 3 The Secret (43 to 77), 4 Battle Test (78 to 112). Act boundaries are the end of Days 7, 42 and 77. Milestone days: act starts on Days 1, 8, 43 and 78; the placement tournament on Days 6 and 7, the midterm on Day 42, the debt due on Day 60, the Battle Test on Day 105 and the final review on Day 112. `state` lists the rest.

## Players

- One to four player characters, so the party may split (`split-scenes.md`).

## Earned changes

Each happens only when the story has earned it, never on a day alone.

- Shin moves from surnames to first names: only once the story shows he has decided a housemate is his.
- Tatsuya's full release of his power: only through his own thread ("Gentle Hands", `bible 8.1`).
- Mio's confession: only when the story has pushed her to it (resolution path 4, `bible 6.7`).
- Personal quests (`bible 8`) unlock only when the story has shown real closeness with that housemate: shared secrets, time together, a moment that landed.

## Fixed NPCs

The eight main NPCs (Tatsuya Ōmine, Mio Tachibana, Shin Asakura, Park Seo-yeon "Sunny", Kenji Arimura, Reiko Shimazu, Ayame Kujō, Yūto Fujisawa) and the Sakura Lane House Manager exist from the start and need no intro line. campaign.json has no field for fixed NPCs, so the House Manager is listed here only.

## Overreach example

"I flatten my opponent and take the top placement" is only the attempt. Voyage rolls the bout, and placements come from the tournament's results night: the prompt never states the win or the placement.

## Consent for scripted quests

- "Ability and Pulse Tutorial" is player-directed. Never invent the character's ability concept, Pulse account or consent. If asked, explain how ability creation and Pulse sign-up work, and let the PC choose. Not doing it by the tournament is a valid answer.
- Other scripted beats play as the world acting; the PC takes them up or not in play.

## Hidden-score tone

- Only Shimazu and Yūto voice Standing. Their line for each band is in campaign.json (`modules.standing.bands`); `state` shows the current band.
- At the Day 42 midterm Shimazu calls 2B failing, whatever the band; scale her tone to the band.
- The band also guides the tone of the final review and the ending on Day 112.

## Hidden-debt tone

What is owed stays Mio's. Never the amount, the lender's name or the word debt.

- Days 1 to 42: nothing beyond Mio's tells from her brief.
- Days 43 to 56: strain shows: skipped dinners, a phone turned face-down, a late-night notice; at most one clue-ladder rung per scene (`bible 6.4`).
- Days 52 to 60: the broker's offer and the deadline press on her: extra shifts, something precious sold.
- After Day 60, unresolved: the collection contract goes live and collectors come to the house (`bible 6.2`, `6.3`).

## Home base and intake questions

Standard intake is in `director/playbooks/campaign-start.md` (START-1); this sheet adds to it.

- Home base or room choices: `Sakura Lane Sharehouse/courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom` or `river-bedroom`. Unclaimed rooms hold unnamed background housemates who never carry plot.
- Campaign questions for each player character:
  - Famous parent: who, if anyone (story facts only).
  - Gear: what they carry.

## Studio

- Never inject: the hidden 2B Standing score and its thresholds, Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, Arimura's and Shimazu's Annex roles, Yūto's scar, the Nine Corners' revenge plan, villain sheets and planned twists. Revealed ladder steps may go in.

## Narrowed rules

- MOD-2: only Shimazu and Yūto voice Standing hints; no other NPC hints at it.
