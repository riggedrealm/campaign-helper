# Luxcellia: The Fifth Hero's Party: world sheet

The generic director skill reads this sheet at chat start. It holds only what is particular to this campaign: facts and limits, never generic rules. A narrowing may only add a limit and never loosens a bootstrap invariant (SHEET-1 in `director/core.md`).

## World file and calendar

- World file: `worlds/luxcellia.json` (Voyage's own export; read only through the tools).
- Weekday of Day 1: Monday (campaign.json `start_weekday`).
- Acts: 1 Severance (Days 1 to 14), 2 Bonds (15 to 45), 3 The Vanished (46 to 75), 4 Vindication (76 to 100). Act boundaries are the end of Days 14, 45 and 75. Milestone days: act starts on Days 1, 15, 46 and 76; the throne and the finale on Day 97.

## Players and mode

- Single player: one PC, so there is never a split party.
- Game mode Party and Bonds, with these rules:
  - Campfire rule: every rest holds a party moment.
  - NPC chemistry: companions react to and play off each other, not only to the PC.
  - Bond firsts: a bond's first meal, first shared job and the like are scenes in their own right.
  - Companion table time: every companion's thread gets table time; `spotlight` (companions) shows who is behind.
- No hidden score: the Standing and debt modules are off, so there is no hidden-score tone to write.

## Earned changes

Each happens only when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed), never on a day alone.

- Yumi's curse cracking (milestone Day 31).
- Ren's secret shared (milestone: Ren's song, Day 27).
- Toma's anonymous top-ups coming out (milestone Day 34).
- Daigo's debt paid (milestone Day 53).

## Fixed NPCs

The nine main NPCs (Yumi Aokiba, Ren Tsukishiro, Toma Kirisawa, Mizuho Kaimaku, Suzuha Sumeragi, Court Mage Serika Amamiya, Rin Amasaka, Daigo Hoshimura, Yui Nakahara) and Queen Celestine exist from the start and need no intro line. campaign.json has no field for fixed NPCs, so they are listed here only.

## Overreach example

"Recruit Yui" is only the attempt. Voyage rolls it, and Yui answers on her own terms after the roll: the prompt never states her yes.

## Consent for scripted quests

Scripted beats need the player's consent before they play: the PC takes one up in play, and the director never forces it.

## Home base and intake questions

Standard intake is in `director/playbooks/campaign-start.md` (START-1); this sheet adds to it.

- Home base or room choices: none. The PC starts at `Aureliath/royal-palace` and lodges at a Guild Quarter or Market District inn (Voyage names it; `add-area` once shown).
- Campaign questions for each player character:
  - Origin and hook: where they came from (one line) and which opening hook fits: Combat Class, Magic Affinity, Profession, Blessing or Cheat Skill, Rebirth or Race (story facts only, no stats).

## Studio

- Act starts are Days 1, 15, 46 and 76. Act-start bundles:
  - Act 1 (Day 1, or before Day 2): the Mizuho edit and Kazuki Ōhara.
  - Act 3 (after the Wharf raid shows the Almonry): Archbishop Isamu Tokiwa and a faction touch for the Almonry.
  - Any act: a fourth-seat NPC when the PC's bond calls for one.
- Mizuho edit: in the world file Mizuho Kaimaku works at Portmaris. Before her Day 4 beat, file `studio-request --edit` saying she is the head receptionist at the Adventurer's Guild branch in the Aureliath Guild Quarter, working the main counter. Until it is applied, an unnamed registrar speaks for her in a letter.
- Never inject: the board's operator and the Almonry before the story shows them, the Lattice and the glass cradles, Serika's null reading and sealed precedents, Rin's copied logs, Yui's fifth anchor, Daigo's buried reading, Toma's anonymous top-ups, Suzuha's engineered engagement, Ren's Earth origin, Yumi's curse, Mizuho's twenty-year case, villain sheets and planned twists. Revealed ladder steps may go in.

## Narrowed rules

- FMT-4, FMT-5: the chain quests are Voyage's. Never seed them, never record `quest-start` for them and never track them; this narrows the seeding the generic rules allow.
- CUT-3: a skip the player asks for still holds a rest's party moment (the campfire rule).
- CUT-1 (user-set 2026-10-05): a next step the player states counts as the input's reach. "A quick stop for potions, then the manor" lands at the potion stall. Cut to the first stated step and stop only at a choice the PC must make there (what to buy, what to say). Never hold a stated plan back a turn.
- REPLY-1 (user-set 2026-10-05): the reply is the prompt only, in a blockquote. No character count, no ruling line, no notes; add a line only when a tool failed or the user must decide.
