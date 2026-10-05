# Joestar Gang: world sheet

The generic director skill reads this sheet at chat start. It holds only what is particular to this campaign: facts and limits, never generic rules. A narrowing may only add a limit and never loosens a bootstrap invariant (SHEET-1 in `director/core.md`).

## World file and calendar

- World file: `worlds/joestar-save.json`, Voyage's own save. Only tools read it (`db.py sync PATH`; `sync.md`); a chat never does.
- Weekday of Day 1: Saturday, August 1, 2026 (campaign.json `start_weekday`).
- Acts: 1 The Crew (done), 2 The Four Pillars (Days 1 to 120), 3 Daigo's War (Days 121 to 240, locked). The ranges are placeholders: Act 2 ends when the last pillar falls. Milestone days: none; milestones are events.

## Players and mode

- Two PCs, played by the user: the brothers Jostin Joestar (Hearth, the home) and Jovian Joestar (Spearhead, the field). The party can split.
- The table loves fights and relationships: each arc builds to a showcase fight and tests a relationship. Wins are earned; losses cost but end nothing.
- Tests, never outcomes: Jostin is tested on love and home, Jovian on strength and purpose, each as a situation (`bible 7`).
- Voyage defaults to school slice-of-life: state the crime register in `Tone:` when a scene is dark.
- No hidden score: the Standing and debt modules are off.

## Earned changes

Each happens only when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed), never on a day alone.

- Rei Ichinose joins as the neutral liaison (Anya's condition for the charter).
- Rikona Mibu says yes to joining: the offer is Jovian's, the answer hers.
- Ayame Fujinami gets the date Jostin owes her.
- Reiko Amagawa has her private talk with Jostin.

## Fixed NPCs

Every name in campaign.json `main_npcs` exists from the start and needs no intro line. Shogo Kiriyama (the Archivist) and Daisuke Mogami (Replay) are Arc 4's villains: they stay hidden behind their ladders until revealed.

## Overreach example

"Recruit Rei" is only the attempt. Voyage rolls it, and Rei answers on her own terms: the prompt never states her yes.

## Consent for scripted quests

The personal threads (Reiko's talk, Ayame's date, Jovian and Yuzuki, Rikona joining, Jostin's cafe plan) play only when the players ask or a PC takes one up.

## Home base and intake questions

Standard intake is in `director/playbooks/campaign-start.md` (START-1); this sheet adds to it.

- Home base or room choices: none. Base: `Club Lumière/Main Lounge`, the brothers' own ("Safehouse" means it). The secret working HQ is the shelter under the gym storage-room mats (`Chikara Academy/combat-gym`). The brothers live in `Chikara Student Residences`.
- Campaign questions for each player character: none; both sheets are on file.

## Studio

- Exact keys: Club Lumière, Tetsu Iron Palm Gym and Ward Licensing Services are locations; the Academy gym wing is the area `combat-gym`.
- Never inject: the Archivist and Replay before their ladder steps, the stream-phone twist, the dead-man upload, the camera exchange, the Kagero school's purpose, the nickname The Teller (Setsuko Okabe's name is public), the Act 3 doors (the combat-data buyer, Iori Vale's puppeting, the tunnels), villain sheets and planned twists.

## Narrowed rules

The first five are the user's hard lines, held unless the user says otherwise; at the first planning session, record them with `db.py session-zero --lines`.

- ARC-8, SCN-5: no ally betrayals. No twist, surprise or front makes a crew member or ally a traitor.
- ARC-8, CHK-2: no cliffhanger tails at arc ends. Every climax option ends the arc; its last prompt lands the aftermath.
- WLD-1, ARC-13: no invented deadlines. A clock or front sets one only when the players can see it and still act in time.
- ARC-8, SCN-5: no death of a named crew member or love interest without the user's OK. No card, surprise or front aims at one.
- NPC-7, CUT-3: no relationship decided off-screen, by a skip, a summary or a Studio edit.
- NPC-7: romance only with the played love interests, at each one's pace: Ayame Fujinami and Riko Amane (Jostin), Yuzuki Hoshino and Mikoto Kurogane (Jovian). Never villains, Rikona Mibu, Shun, Daiki, Noa Amemiya or Kenji Aoi.
- ARC-10: the user also approves the arc's pillar and recruit seat and sees PC tests by category only. You keep the twist, villain sheets, the villain's face, the fork doors and the seat's candidate.
- ARC-22: every charter's `pc_tests` gives Jostin love or home and Jovian strength or purpose.
- ARC-8, recruiting: Spearhead seats (Aether, Phantom heads) are Jovian's call, Hearth seats (HearthOps, Arcanum) Jostin's (`docs/org.md`). Each charter names one `recruit_seat`, Aether Head first. The candidate is earned, never a free ally; a missed search becomes a lead.
- FMT-2: no recurring named Kobuncho locals for now; HearthOps scenes treat the shop-owner alliance as a group.
- AGY-4, START-1: anything about who a PC is inside needs the user's OK first.
