# Joestar Gang: Arc Bible

Director-only. Everything here is final design. Prompts carry only the sliver a scene needs. Read it by section with `db.py bible` (`bible 3`, `bible act2`, `bible budgets`); never whole.

Machine-readable copies of the cast (including the villain sheets below), quests and reveal ladders live in `data/` and are queried with `db.py`; this file keeps the narrative design. If the two ever disagree, the design here wins and `data/` should be corrected before play.

The arc planner (`docs/arc-planning.md`) writes act pitches and arc charters against these acts. Charters may deviate from them; each deviation is logged and shown on the Arc Planner page. The acts stay the default spine.

Section titles `Time skips`, `Obstacle and surprise rules` and `Scene turn budgets` are looked up by the skill (`bible time skips`, `bible surprise rules`, `bible budgets`): keep those words in the headings. Act headings keep the form `Act N: Name (Days a to b)` so `bible actN` works.

**Migrated from riggedrealm/voyage-memory at t480** (`data/arcs.json`, `world/road-to-daigo.md`, `world/story-design.md`). The game is mid-play: Book 1, Act 2, Arc 4 (The Archivist), beat 4-1 Stills won at t479 and handing to 4-2 Dead Zone. **Resynced from Voyage's own save at tick 481 (Day 20, Thursday evening)**: Voyage's day counter was authoritative until t482; **at t482 the user accepted the story calendar (`planner/note-story-so-far.md`): t482 is Monday, October 19, 2026, Day 80**; the plan is turn-indexed (t0 to t481). `docs/migration.md` maps every source key to its landing place.

## 1. Premise and stakes

Two brothers of the Joestar lineage (a hereditary heart-shaped birthmark high on the upper back), **Jostin** and **Jovian**, registered at Chikara Academy (a Tokyo superhero university) and built a crew out of Club Lumiere, a half-repaired cabaret on Neon Lantern Street in Kobuncho, the nightlife district. Powers are Stands, Joestar Breathing forms, Pulse abilities and magic. Tone: Lookism-style crews and JoJo-style powers in a crime and vigilante register. The Voyage engine's default is warm school slice-of-life, so `Tone:` must say when a scene is dark.

**Book 1 is Daigo Renjiro**, the real boss of the Kurokawa syndicate: a tyrant to topple, with no sympathetic reveal; twists come from his captains, their methods and their hidden schemes. The plot asks "who rules Kobuncho?" (territory, captains, the syndicate's four pillars: Legitimacy, Enforcement, Intelligence, Finance). The emotion asks "what will you risk to protect your own?" (every arc threatens someone the players care about). Books 2 and 3 may follow: every Book 1 thread resolves by Daigo's fall; a few doors stay open for later, seeded lightly, never as cliffhangers. Kobuncho's ordinary people are background colour; no recurring named locals for now (HearthOps deals with the shop-owner alliance as a group).

Stakes the players can feel:

- **Club Lumiere and its people** (the home): Maki, Natsumi, the hostesses, the staff whose debts are unresolved. Jostin is tested here.
- **The crew's faces and Ayame's public risk**: every fight of theirs was recorded; the Kurokawa Intelligence pillar sees through lenses; Ayame's stream is the crew's public shield and its public risk.
- **The people they chose**: Reiko's sister, Noa and the Amemiya shop, Rikona's block, the gym people (Tetsu, Riko, Kaito Serizawa): each arc puts someone under pressure.

### Scope and players

- Built for **two player characters** (multiplayer table): Jostin Joestar (Hearth, the home) and Jovian Joestar (Spearhead, the field). The user controls the PCs; the director controls the scene, NPCs and the world's reaction. Never script a PC.
- **Turn counter:** the game's own counter is authoritative; at the resync it stood at t481 (next 482). Earlier labels t327/t328 in old notes may be about 50 behind. **Day 1 = Saturday, August 1, 2026** (Voyage's story start), so `start_weekday` is Saturday and Day 20 is Thursday; Voyage tracks only the time-of-day block (the clock is the block's start). The Act day ranges below are planning placeholders (Act 2 is event-based).
- Places (Voyage's keys): base Club Lumiere (location `Club Lumière`: Main Lounge, Back Office, Kitchen, Stage Alcove, Storage Closet), the Academy (`Chikara Academy`) with the gym storage-room HQ and corridor (no Voyage areas: use `combat-gym`; the old keys survive in `director_areas`), Tetsu Iron Palm Gym (its own location), Shutter Alley, the old bathhouse (Yuzuki, service tunnels), the dorms (`Chikara Student Residences`). No rooms. Voyage made Club Lumière, Tetsu Iron Palm Gym and the annex (`Ward Licensing Services`) locations of their own (the old user decision said areas of Kobuncho; Voyage's world wins). New areas inside existing locations are allowed once the story shows them (`add-area`); no new locations.
- The Voyage world for Joestar is in this repo as `worlds/joestar-save.json` (Voyage's full save at tick 481; `New_World.json` is the Class 2B world and has no Kobuncho). `data/locations.json`, `factions.json`, `world-npcs.json` and `lore.json` were re-imported from it and merged with the director layer; Studio edits and future imports use that file.

### Tone

Serious stakes with banter and comedy between. Fights are **puzzle first** (crack the enemy power's rule), **spectacle to finish**; bosses and lieutenants are puzzles, regular thugs are spectacle fodder. **Earned wins:** enemies are dangerous and win some early rounds; the PCs can always win with good play; losses cost something and never end anything. The user loves fights and relationships: every arc builds to a showcase fight and puts a relationship under pressure. Surprises the user likes: plot twists about the enemies and crew personal events (someone's past shows up, someone gets hurt or taken); **no ally betrayals**. Romance in any form, driven by each NPC's personality (a bold NPC makes moves, a shy one slow-burns). The director never states player-character or combat outcomes; Voyage rolls combat and decides every number.

### Venue substitutes (no invented places)

| Need | Stand-in |
|---|---|
| A lens-free room / the crew's true safehouse (4-4) | `Chikara Academy/combat-gym` (the gym wing; the secret shelter under the mats is the working HQ since t461-t462; Voyage has no storage-room area); the Forge safehouse spec (no site chosen yet) |
| The print lab and the sedan's alley (live scene at t481) | `Pulse Printworks/front-counter` (Voyage's own place); the deputy's storeroom is `Steam Lantern Alley/noodle-corner` |
| Neutral ground, public and full of lenses (4-3) | `Kobuncho/Neon Lantern Street` or `Kobuncho Station Front`; `add-area` for a named venue |
| The camera exchange (4-5) | Not in `data/locations.json`: `add-area` inside Kobuncho when the story shows it; never a new location |
| The crew's gym | `Tetsu Iron Palm Gym` (a Voyage location; areas: Front Entrance & Reception, Main Training Floor, Tea Corner & Office, Private Storage Room, Back Alley Exit) |
| Students' talk, Rei, Anya | `Chikara Academy/main-hall`, `Principal Anya's office`, `combat-gym` |

## 2. Hidden state

All of it is director-only; each secret is a reveal ladder in `data/threads.json` (`db.py thread`). Names and key phrases are blocked in prompts (`check-prompt`) until the ladder step is revealed with `thread-reveal`.

- **The Archivist (Intelligence captain)**: Shogo Kiriyama, 'The Archivist', the forgettable suited man; power Still Frame; the records deputy answers to him. Unlock at 4-2 (name), 4-3 (met in person). Ladder "The Archivist's name".
- **Replay (his bodyguard)**: Daisuke Mogami; power Rerun; weakness: only what was filmed. Unlock at 4-3 (moved from 4-2 at t482); weakness at 4-5. Ladder "Replay's tape".
- **The Lumiere clip (the 4-3 twist)**: Kiriyama has watched Club Lumiere through Ayame's stream phone. Ladder "The Lumiere clip".
- **The dead-man upload (4-5)**: the archive sits in a lens-free room inside a camera exchange; seizing him without a key triggers a dead-man upload. Ladder "The dead-man upload".
- **The Kagero school's purpose**: informants and honey traps to compromise officials, police and Ultra Force staff, then blackmail them (3a-5; kept locked for parity). Ladder "The Kagero school's purpose".
- **Okabe, the Teller**: the Finance captain's name stayed locked after Harumi Wharf. Ladder "Okabe, the Teller".
- **Act 3 doors**: the combat-data buyer (the circuit harvested combat data for a buyer interested in synthetic powers; the rigged Saturday championship and Harumi Wharf 'liquidation' were planned, not played); Daigo puppeted Iori Vale into Jostin's strike (t182), the personal core of Act 3; Daigo's tunnels (Gara's tip); the ten-win strike team; a bigger Kurokawa broker 'Masat...'. Ladders "The combat-data buyer" and "World secrets (Act 3 doors)" (Echo, Hush, Oblivion, Yuzuki's Stand).
- **Open decisions** (source `open_decisions`): Kiriyama's and Okabe's names and powers are proposals (override freely); Okabe's power was dropped (resolved: no power); whether Rikona joins once her block is free; the old 'Act 2 closing hook form' was replaced by 'no cliffhanger; Act 3 planned separately'; the Arc 4 charter was approved at t438 (active from t439). Rikona's mark (was her paid debt actually cleared from the ledger?) is an unused twist option, or skip.
- **Relationship values** are Voyage's. The director does not track numbers. A personal thread unlocks when the story has shown real closeness (shared secrets, time together, a moment that landed).

## 3. Pacing at a glance

Act 2 (The Four Pillars) breaks every pillar of Daigo's power. Daigo stays off-screen: he reacts only through captains, orders and consequences.

| Arc | Pillar and captain | Showcase | Relationship under pressure | Status |
|---|---|---|---|---|
| Expose the Legitimacy Captain | Legitimacy: Councilor Ohmori | the annex (captain arrested t248; Ayame filmed the forged signature) | Ayame and the crew | done |
| The House Always Wins (Tag Night), t301-t326 | Enforcement: Goki Banda | Tag Night: Round 1 Vise and Paper Cut, Round 2 Aoi, boss phase; Banda killed by Mikoto's Riot Pulse | Mikoto and Jovian; Shun and the debtor casters | done |
| Hostess Disappearance File (3a) and Follow the Money (3b), about t327-t437 | Finance: Setsuko Okabe, 'The Teller' | Club Kagero breach; Rematch Night (Jovian beats Kaito Serizawa, collectors crushed on the gym doorstep); Harumi Wharf (master ledger burned) | Jostin and Ayame/Riko; Reiko and Sena; Rikona and Noa | done |
| **The Archivist (Arc 4)**, start t439, budget 34 turns | Intelligence: Shogo Kiriyama | 4-5 Lights Out: Replay against Jovian (and Mikoto) in the dark | Jostin's date owed to Ayame (love or home); Jovian and Yuzuki; the fork's voice of caution (Haruto, Reiko) | **active: 4-1 Stills won at t479; 4-2 Dead Zone closes in one turn at t483 (tight finish)** |

**Pulse check at t481:** Arc 4 has run 43 turns (t439 to t481) of a 34-turn budget. The gym HQ and Rei audit ran t438 to t474 (user flagged stalling at t466); the print-lab lead ran t475 to t481 and its win is met: the sedan driver gave up the records deputy (a storeroom over a closed noodle counter on Steam Lantern Alley, t479). The live scene is the handoff: the deputy is warned and goes for the back stairs, so the next input opens 4-2 Dead Zone. Per the pacing rules, compress: run the chase in a few turns, then jump to 4-3 and cut non-essential beats.

**Pulse check at t482 (tight finish, user's ARC-17 answer in the planner session; don't ask again):** Arc 4 is at 44 of 34 turns. The rest runs about 17 turns (t483 to about t500), then Act 2 closes and Act 3 is planned. t483: 4-2 closes in one compact beat (card in `planner/note-arc4-tight-finish.md`), then a hard cut. t484: regroup; `World:` brings the courteous invitation to 4-3 (the next evening, Day 81 Tuesday, after the t482 calendar resync to Day 80). Budgets now: 4-2 1; regroup 1; 4-3 3; 4-4 3; 4-5 5; 4-6 3; breather 1 to 2. Personal threads don't count against them. Replay debuts at 4-3 at Kiriyama's shoulder (tell only), not as a 4-2 intercept; there is no round-one loss.

Keep the act day ranges in step with `acts` in `campaign.json` (`db.py time` moves the act with the day). Act 2 is event-based (it ends when all four pillars have fallen); when Arc 4 ends, plan Act 3 and set its `from_day` to the current day.

## 4. Act 1: The Crew (Days 0 to 0)

**Purpose**: done and archived (t0 to t192): the brothers register at Chikara Academy and fight Renji Kuroba (the gym crew steps in); train at Tetsu Gym; dinner at Club Lumiere and beating two collectors, deciding to use it as the base; recruit Nobu and Hana; the deed via Aurelia Voss and the Speedwagon Foundation (about t65-t80); the disciplinary agreement with Principal Anya (t68); Gara; Sato; Iori Vale's death (t182, puppeted into Jostin's strike); Haruto's four-pillar briefing. Full range summaries: `data/history.json` (`history`, `recap`) and `docs/archive/notes-*.md`.

## 5. Act 2: The Four Pillars (Days 1 to 120)

**Purpose**: break every pillar of Daigo's power; Daigo stays off-screen (reacts through captains, orders, consequences). Act 2 ends when all four pillars have fallen; no cliffhanger tail; Act 3 is planned separately from the pressure curve.

**Pressure curve** (Daigo, off-screen, consequences only):

- After Enforcement falls: Daigo annoyed; learns Banda skimmed; orders an audit (seeds 3b).
- After Finance falls: broke and exposed; cannot pay his people.
- After Intelligence falls: Daigo blind in Kobuncho; paranoid, trusts no one; the Act 2 finale hook.

**Pillar status at t481:** Legitimacy broken (captain arrested t248); Enforcement broken (The House fell t323, Banda dead); Finance broken (master ledger burned at Harumi Wharf t437; the Amemiya debt and Noa's indenture voided); **Intelligence is Arc 4** (untouched: hub in a bathhouse service tunnel per the engine's Kurokawa notes; the records deputy and his captain).

**Quests**: the 11 open threads in `data/quests.json` (Voyage owns progress); one new seed per turn.

### Arc history (played)

**Expose the Legitimacy Captain** (done): Captain arrested (t242-248).

**The House Always Wins (Tag Night)** (done, t301-t326): Shun and the debtor casters freed; hum broken; Banda killed by Mikoto's Riot Pulse; Haruto holds Yuji's duffel and the second ledger (t301-t326). Beats: e-1 Red Tokens; e-2 The Door; e-3 The Bunker; e-4 Round 1: Vise & Paper Cut; e-5 Back Rooms; e-6 Round 2: Aoi; e-7 Found Out / Relay; e-8 Extraction; e-9 Boss phase; e-10 The House Falls.

**The Hostess Disappearance File** (Finance; captain Setsuko Okabe, 'The Teller' (hidden until 3b); done): Hostess Noa Amemiya goes missing; the crew finds Club Kagero (shuttered front, invite-only after-hours 'school'). Compressed by play: the crew breached it, pulled Noa out, and Jostin collapsed the club with the archive. Collectors then came for Noa's contract (Marumo Financial Services); the crew refused to pay.

Premise: Hostesses are vanishing across Kobuncho. Club Kagero is Lumiere's dark mirror: glamorous floors, a VIP level, a closed upper floor where the 'school' runs.

Beats: 3a-1 Cold Numbers (Maki reports Noa missing; phone traced to Neon Lantern Street.); 3a-2 Getting In (Crew breached the shuttered satellite club, tagged and stopped the van, learned Noa was at Kagero, entered with Kaito's tethers pinning the bouncers.); 3a-3 Floor by Floor (Played compressed: records room, terms offered, Nobu's loop on the feeds, stair guards, Rikona's barrier.); 3a-4 The School (Noa found willing under contract; archive buried by Jostin's Aftershock; no files taken.); 3a-5 Who Wants Out (Noa is out but her 4.6M yen contract stands on paper; the crew chose to hunt the collectors rather than pay. Debrief at Lumiere is next.); 3a-6 Come Collecting (Collectors came: Marumo Financial Services served Noa's contract at the Amemiya shop; the sedans trace to a leasing shell family.)

Spotlight: Reiko (protecting women), Ayame (showbiz), Haruto (money cover), Yuzuki (the scared ones), Nobu (cameras), Rin (numbers), Rikona (Noa's family).

Revisions and decisions:
- Hostess canon list: Airi Kurosawa, Mirei Tachibana, Noa Amemiya, Rika Saotome, Sena Amagawa; manager Maki Hayashida. Tomoe/Chiho/Kaede are NOT hostesses.
- Missing hostess: Noa Amemiya (willing; recruited to clear her family's debt; wants out only if the debt is cleared).
- Sena (Reiko's sister): plant only; turned the offer down; not taken. Airi: lead-giver only.
- Schedule: Mon-Wed school by day, investigation by night; Thursday's Kaito Serizawa rematch is beat 3b-3.
- Rin (ex-House clerk): her lead links Noa's dead numbers to Kagero's cash couriers; spotlight Rin.
- Rikona tie-in: Noa's family shop is on Rikona's block; Rikona agreed to ONE case; her face is known to collectors.
- Safehouse payoff: no files were stolen (archive buried); Forge's safehouse spec still waits for a use.
- t327 (user-approved): the man in the dark suit is a records DEPUTY, not the captain; players are told he is the same suited watcher from the annex (Reiko). The captain above him stays unnamed until reached; Kiriyama / Still Frame belong to that captain.
- Stream/lens risk: phones filmed the collapse and crew faces; Nobu's Dead Air and feed loops are the counter.
- Airi: her 3b secret stays hidden until its beat (kept out of her public summary).
- Finance rebase (user-approved): Arc 3 (3a + 3b) is the FINANCE pillar and ends with the master ledger burning. No traitor and no hostess betrayal: the leak is cause and effect (Ayame's stream advertises the rematch). Okabe's Promissory Mark power is dropped. Intelligence (Kiriyama) moves to Arc 4.

**Follow the Money** (Finance falls at the end; captain Setsuko Okabe, 'The Teller' (hidden until reached); done): Rin's numbers and the collectors point to a loan office on Neon Lantern Street that buys debts and ships cash by boat. The crew follows the money, survives the Thursday rematch crash and burns the master ledger at Harumi Wharf. Finance falls.

Beats: 3b-1 Finance Planning (Rin traced Marumo's couriers; the crew chose to pose as a client and Yamaguchi at the leasing branch offered a trial placement.); 3b-2 The Cash Run (The courier hand-off worked and the shop was held by Reiko.); 3b-3 Rematch Night (Thursday rematch: Jovian beat Kaito Serizawa (no betrayal). Ayame's stream drew Kurokawa collectors, who were crushed on the gym doorstep by Jostin; one phone, one lead.); 3b-4 The Vault (Con at the loan office: the folders were a decoy (Rin's photos safe in Nobu's system), Saionji cover burned, dusk van tagged and followed to Harumi Wharf; ledger strongbox seen aboard the boat.); 3b-5 Harumi Wharf (Harumi Wharf: the Finance captain offered terms; the crew refused. Haruto photographed the ledger for the police, then burned it; Amemiya debt and Noa's indenture voided. Finance fell.)

Spotlight: Rin (numbers), Haruto (the con), Nobu (the trace), Hana (the vault), Reiko (the shop), Jovian (the rematch), Rikona (her block), Kaito Arashima.

Revisions and decisions:
- Ozu seed (optional): Ginji Ozu ('ask around Kobuncho') shows up counting cash for Okabe's side during 3b-2. Do not use before 3b unless the players go looking.
- No traitor: the old Airi-coerced secret is removed. Airi stays a lead-giver only.
- t416 CONSEQUENCES PLAN (GM decided): the Thursday crash went violent (three Kurokawa collectors crushed by Blackstar; one critical). Retaliation is pressure, not war: (1) the debt side answers ('the bill just grew': Noa's 4.6M contract is raised, Finance leans on the Amemiya shop); (2) Tetsu Gym gets a visit and heat (police ask about an ambulance call; Tetsu protects the crew but names the cost); (3) Ayame's stream: blurred clips circulate, a Kurokawa-side viewer learns her face; (4) Jostin pays: strained muscles, Blackstar spill, and Rikona/Riko/Haruto react to the beating. The phone trace (prepaid line, routed, tower fix by morning) points to the loan-office district on Neon Lantern Street, which feeds 3b-4 The Vault. No Finance captain or Okabe reveal before 3b-5.
- t432 FINALE PLAN (user: not too fast, not dragging): the Harumi Wharf raid is the closing scene, played over THREE turns with real player choices. Turn A: arrive, Eagle Vision scan (nine red, gold strongbox in the boat cabin), clock: a car is expected in ten minutes; stop at the fence on the entry choice. Turn B: the assault and cabin; the captain (Setsuko Okabe, elderly, no combat power, two guards) arrives and offers terms; stop on her first line. Turn C: the PCs choose (burn the ledger, or take her terms); the ledger burns, contracts void (Noa's too), Finance falls; dawn debrief and the Arc 4 hook (Archivist). Do not compress into one turn.

Retro: Played t378 to t437 (about 60 game turns; the new target is 24 to 36). Promise kept: Finance fell at Harumi Wharf, Amemiya and Noa are free. What dragged (user feedback): leads kept going cold (lost phone, tagged van, decoy folders), retaliation beats before the vault, and an invented 'a week' hook after the finale, which was cancelled. What worked: the three-turn finale with a real choice each turn; Jostin's third option (hand the ledger to Haruto) was honoured. Best moment (user): the Tetsu Gym hook when collectors threatened Ayame and Jostin got angry.

### Arc 4: The Archivist (Intelligence) (current)

**Promise** (user-approved direction): Put out Daigo's eyes in Kobuncho and decide what happens to everything they have seen.

**Premise**: Intelligence, the last pillar. The crew has been the hunter; now they learn every fight of theirs was recorded. They take down the Archivist's camera empire in six beats and choose what happens to the blackmail archive. Daigo ends the arc blind. Arc 4 starts with its own inciting event after the Harumi breather, not as a hook from 3b: stills of the crew's own violence arrive at Lumiere.

**Budget**: 34 turns from t439 (charter approved by the user at t438). **Recruit seat** (first-wave, the user sees the seat; the director keeps the candidate): Aether Head (Jovian's call).

**Direction fields the user approved** (premise, promise, budget, pillar, set pieces, crew subplot, climax choices as kinds, ending shape, seeds, recruit seat): set pieces: Chase through a camera-dead city (4-2); Social duel on neutral ground (4-3); Lights-out infiltration and showcase fight with Replay (4-5). Crew subplots: Ayame (4-4): Her stream phone was the lens; she turns it into the decoy.; Hana (4-4): Builds the lens-free room; the safehouse thread pays off.; Yuzuki (4-6): Comforts the frightened witness; her new bond with Jovian gets a quiet moment.; Mikoto (4-5): Unfilmed, she is Replay's blind spot; she wins on her own merits.. Ending: payoff: Intelligence falls; Daigo is blind in Kobuncho and trusts no one; all four pillars are down. Cost: Whatever the archive choice costs: a lost justice, a leak risk, or the crew's own dark turn. Breather: Morning-after crew scene (2 to 3 turns). No cliffhanger. Act 3 is planned separately from the pressure curve. Seeds: An invoice from Kiriyama to the outside combat-data buyer (Act 3 door; mention once, never a hook).

**Villain face** (director-only): Kiriyama is the forgettable suited observer: courteous, never loud, treats leverage as manners. He wants to keep working (blackmail files, selling the crew's 'combat data' to the outside buyer). He pressures with footage of the PCs' own violence (the doorstep beating, the wharf), not with threats. First met in person at 4-3, in a public place full of lenses.

**Twist** (director-only): At 4-3 Kiriyama plays a clip filmed inside Club Lumiere through a lens he once touched (Ayame's stream phone). The goal changes from 'find him' to 'go dark first'. That pays off the safehouse thread: the crew builds a lens-free room.

**Beats** (one per turn; a beat can take several turns if the players linger; each has a turn budget). Current: **4-1 Stills won (t479); 4-2 Dead Zone closes at t483 (tight finish, t482 pulse check)**.

**4-1 Stills** [won t479: the sedan driver gave up the deputy; handoff scene live at t481] (hook, budget 3 turns)
- Goal: Find who sent the envelope of stills (doorstep beating, wharf) to Lumiere.
- Win: The courier is caught and gives up where the records deputy is holed up tonight; the crew knows someone has been filming them.
- Fork: Lean on the courier, pay him, or flip him.
- Fail forward: The courier slips but drops the envelope's return slip: same lead, one scrap lost.
- Plan: Inciting event in the scene's first minute: stills of the crew's fights arrive at Lumiere. Tail the courier. Small surprise: the same forgettable suited man is in the background of two stills (Kiriyama's face, unnamed). If Jostin goes to Tetsu Gym, Riko's straight talk about the doorstep beating is the one acknowledging scene for Blackstar; then that thread is closed.

**4-2 Dead Zone** [live: the crew moved on the deputy at t482; closes in one turn at t483] (action, budget 1 turn; was 6)
- Goal: Reach the records deputy through a city-wide camera-dead night.
- Win: The deputy (or his phone) gives the Archivist's name.
- Fork: Hand the deputy to the police or turn him.
- Fail forward: The deputy slips but his phone gives the name and a place.
- Plan: One compact beat (tight finish): Nobu can kill the lane's one camera; the deputy runs for the scooter or bargains with the case; held or slipped, his phone shows the name. Replay does not intercept here (moved to 4-3).

**4-3 Neutral Ground** [planned] (twist, budget 3 turns; was 5)
- Goal: Meet Kiriyama in public on his terms and take his measure.
- Win: One real concession from him (where the archive lives), and the crew sees the extent of his eyes.
- Fork: Take his trade (the Kagero files for the footage) or refuse it.
- Fail forward: If the talk breaks, he still shows the Lumiere clip and the same twist lands.
- Plan: Social duel. Replay's debut: he stands at Kiriyama's shoulder and shows his tell only. Twist: a clip filmed inside Lumiere through Ayame's stream phone. Goal becomes: go dark first. Card: `planner/card-4-3-neutral-ground.md`.

**4-4 Go Dark** [planned] (prep, budget 3 turns; was 4)
- Goal: Build a lens-free safehouse and a decoy so Kiriyama cannot see the plan.
- Win: The crew gets its first true safehouse and every member contributes a piece.
- Fork: Who plays decoy and who goes in with whom.
- Fail forward: One lens survives; the crew feeds it a false plan and uses it.
- Plan: One spotlight-montage turn, then the decoy and plan. Spotlight debt: Reiko and Mikoto have been off screen since t396, so both get a piece here. Prep with a spotlight round: Hana builds the lens-free room, Ayame's stream baits, Rin finds the archive's rent, Mikoto drills the crew in moves never used on camera. Ayame's owed date may land here if the players call it (user plays it).

**4-5 Lights Out** [planned] (action, budget 5 turns; was 8)
- Goal: Infiltrate the camera exchange with every lens dead and beat Replay in the showcase fight.
- Win: Replay falls to something he never saw on film; the archive room is reached and Kiriyama is blind for the first time.
- Fork: Silent route (Shadow Step) or loud route (Soul Forms); cut or keep the building's power.
- Fail forward: An alarm trips; the fight happens in the dark, and the archive is still reachable.
- Plan: One infiltration turn, then the arc's showcase fight (ends when decided, FGT-6) in the dark: Replay against Jovian (and Mikoto). Kaito Arashima's sightlines; Jostin's Shadow Step inside the fight (the brothers stay together in combat; the archive door comes after the fight is decided).

**4-6 Final Frame** [planned] (climax, budget 3 turns: corner, fork, aftermath; was 5)
- Goal: Corner Kiriyama in the lens-free room and decide the archive's fate.
- Win: Intelligence falls; Daigo is blind.
- Fork: Burn it, give it to police and press (scrubbed), or keep it as leverage; separately decide Kiriyama's fate.
- Fail forward: A dead-man upload starts; the players must stop it, and every door still ends the arc.
- Plan: Climax with a real fork. Every door ends the arc; the prompt names the fork, never the pick.

**4-1 scene card** (opening of the arc, t439):

> OPENING (t439, after the t438 breather; explicit cut, Club Lumiere, Sunday late afternoon): Natsumi brings a padded envelope left at the service door, no name. Inside: glossy stills of the Tetsu Gym doorstep beating, the Harumi Wharf boat, crew faces. High fixed angles plus a few phone angles. IN MOTION: the courier (grey cap, scooter) is still across the street, photographing the door to confirm delivery. WORLD MOVES: Kaito Arashima spots the courier; Nobu reads the angles as CCTV, not phones; Ayame checks how far the blurred gym clips have spread; Rin prices the prints (pro lab, someone with money). SURPRISE (small): the same forgettable suited man stands in the background of two stills (gym street and wharf). Unnamed; never name him. KEY LINES: Kaito Arashima: 'Grey cap. Across the street. He's waiting to see who opens it.' Nobu: 'Fixed lens, high angle. That's CCTV.' Ayame: 'Someone got a better angle than me. Rude.' ENDS ON: the courier bolts; take him how (lean, pay, flip)? WIN: the courier gives where the records deputy is holed up tonight (live lead, no 'by morning'). CUT OUT: hard cut to that night, the dead-zone chase (4-2). OPTIONAL: if Jostin visits Tetsu Gym, Riko's straight talk about the doorstep beating is the one Blackstar acknowledging scene; then the thread closes. GUARD: no locked names; Kiriyama, Archivist, Replay stay out of prompts until 4-2.

**Spotlight**: Nobu (Dead Air), Ayame (the stream), Hana (the dark room), Rin (numbers), Haruto (the table and the fork), Reiko (the deputy), Yuzuki (aftermath), Kaito Arashima (sightlines), Jostin (Eagle Vision and Blackstar cost), Jovian (the duel and the Forms).

**Spotlight plan**: jostin: 4-2 Eagle Vision marks every live lens; 4-5 Shadow Step inside the fight, then the archive door once it is decided; 4-1 optional Riko talk closes the Blackstar thread; jovian: 4-3 persuasion duel with Kiriyama; 4-5 beats Replay with an unfilmed move; nobu: 4-2 and 4-5 Dead Air kills lenses block by block; ayame: 4-4 turns her stream into the decoy; hana: 4-4 builds the lens-free room (safehouse payoff); haruto: 4-3 at the table, 4-6 the fork's voice of caution; rin: 4-1 and 4-2 numbers behind the camera accounts; reiko: 4-2 questions the deputy and protects the witness; yuzuki: aftermath comfort and healing; kaito: 4-5 sightlines: an archer against the lenses; mikoto: 4-4 drills unfilmed moves; 4-5 the fighter Replay has no tape on

**Surprises** (director-only): At 4-3 Kiriyama plays a clip filmed inside Club Lumiere through Ayame's stream phone. Crew events: Ayame's face is known to a Kurokawa-side viewer; her dorm and followers become a worry. A frightened witness in the deputy's chain needs Yuzuki and Reiko.

**Choices and echoes** (player choices this arc calls back to): 3b-5: Jostin slapped Okabe; Jovian refused her terms; Haruto photographed the pages for the police file, then burned the ledger -> Kiriyama holds the footage of the wharf; the police file Haruto kept is leverage on both sides | 3b-3: Jostin crushed the collectors at Tetsu Gym on Blackstar -> The doorstep beating is among the stills; one optional acknowledging scene (Riko), then closed. | th-safehouse: A second, hidden safehouse was speced by Forge but never built -> 4-4 builds it as a lens-free room

**Revisions**: t438 review: added Replay (lieutenant, showcase fight; Jovian strength test; Mikoto spotlight); Kiriyama cameo in 4-1 stills; 4-1 hands a live lead to 4-2; Blackstar framed as one optional acknowledging scene; seed for the combat-data buyer. Beats total 31 of 34. t438: charter approved by the user. Ayame's owed date slotted at 4-4 (prep), the user plays it. t482 planner session: tight finish (user): 4-2 closes in one turn; budgets 4-3 3, 4-4 3, 4-5 5, 4-6 3; Replay debuts at 4-3 instead of a 4-2 intercept. `Replay's tape` step 1's stored gate still reads 4-2 (no db.py command edits gates): reveal it at 4-3 with `--gate-met`, citing this revision.

### Showcase fight: Replay against Jovian (and Mikoto), beat 4-5

- **Venue**: the camera exchange (add-area inside Kobuncho when the story shows it); all lenses dead (Nobu's Dead Air), the building's power cut or kept.
- **Format**: Jovian (with Mikoto) against Mogami, Kiriyama's guards around; Jostin in the same fight (Shadow Step inside it; the brothers are never split in combat, user 2026-10-05), the archive door after the fight is decided; Kaito Arashima's sightlines.
- **Opponents**: each built from a rule: a power with a visible tell and an exploitable limit.

#### Villain sheet: Shogo Kiriyama, 'The Archivist' (Intelligence captain)

| Field | Detail |
|---|---|
| Role | Intelligence captain, hidden until reached; first met in person at 4-3 |
| Power rule | Still Frame: he replays and walks through anything a lens recorded, and sees through any camera he has touched. |
| Tell | He goes still, eyes unfocused, mid-sentence when he walks a recording. |
| Weakness | Blind where there is no lens; Dead Air kills lenses and the lens-free room blinds him. Not a brawler; relies on guards and leverage. |
| Finisher setup | 4-5 Replay falls to an unfilmed move and the power cut leaves Kiriyama blind; 4-6 the lens-free room and a dead-man upload make the climax a race and a choice. |
| Behavior | Opens with courtesy and an offer of a trade (the footage for the Kagero files); never raises his voice; sends guards, not himself. |
| If it goes badly | A dead-man upload starts; the players must stop it; every door still ends the arc. |

#### Villain sheet: Daisuke Mogami, 'Replay' (bodyguard, hidden until 4-3)

| Field | Detail |
|---|---|
| Role | Kiriyama's bodyguard and lieutenant; the showcase fighter |
| Power rule | Rerun: he can perform and counter any move he has watched on recorded footage; Kiriyama's archive of the crew's fights is his training tape. |
| Tell | He mutters where he saw it ('Tag Night, round two', 'the wharf, left hook') a beat before a counter. |
| Weakness | Only what was filmed: a new move, an improvised combo, or a fighter he has no footage of (Mikoto) breaks his read. Dead Air does not touch him (memorized). |
| Finisher setup | Once the crew cracks the rule, an unrecorded move or tag-in sets up the finisher; Jovian's Forms used in a way never filmed. |
| Behavior | Calm, polite, bored; counters the first move he recognizes. |
| If it goes badly | He wins a round at 4-5: the crew falls back in the dark and the archive is still reachable; losses cost a lead, never the end. (The 4-2 round one was cut at t482.) |

**Feeding the puzzle within the prompt limit** (840, see `db.py state`): put the rule on a `Facts:` line, show the tell in a `World:` beat, leave the weakness to be discovered; fight prompts are conditionals on Voyage's combat state (skill, Fights). Do not state results; Voyage rolls combat.

### Final review and endings

The climax (4-6 Final Frame) is a real fork; **every door ends the arc; the prompt names the fork, never the pick**. Doors (director-only; the user approves only the *kinds* of choice):

- Burn the whole archive: clean slate and Daigo blind, but the corrupt officials walk free.
- Give the files to police and press after scrubbing the crew's own footage: justice, at the risk of a leak.
- Keep the archive as leverage: the crew becomes the eyes of Kobuncho, at the cost of its own conscience (Haruto and Reiko object).
- Wildcard: Kiriyama's own fate (arrest, escape, or turned). Players may pick this independently.

Aftermath: payoff, cost, breather (2 to 3 crew-moment turns), then close. Intelligence falls; Daigo is blind in Kobuncho and trusts no one; all four pillars are down. After the arc: the retro, then plan Act 3 (`docs/story-design.md`, procedure).

### After the arc: sandbox

If the table wants a breather the game continues as a sandbox: the open personal threads (Reiko's talk, Ayame's date, Jovian and Yuzuki, Rikona, Jostin's cafe plan) stay available as breather scenes; the next arc begins with its own inciting event, not as this arc's last line.

### Act 2 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| The courier bolts (4-1): take him by leaning on him, paying him or flipping him | The same forgettable suited man in the background of two stills (never name him) |
| The deputy slips (4-2): the phone gives the name and a place | A frightened witness in the deputy's chain needs Yuzuki and Reiko |
| The talk at neutral ground breaks (4-3): he still plays the clip | Ayame's face is known to a Kurokawa-side viewer; her dorm and followers become a worry |
| One lens survives (4-4): the crew feeds it a false plan | A move nobody ever filmed saves a round (Mikoto) |
| An alarm trips (4-5): the fight happens in the dark | The lens-free room has a second door |

## 6. Act 3: Daigo's War (Days 121 to 240) (locked)

**Purpose**: plan after Act 2 closes. Daigo finally feels the Joestar threat and moves personally: a big story arc. Known threads to build from: Daigo puppeted Iori Vale into Jostin's strike (t182), the personal core and the payoff for Jostin's Blackstar control; Daigo's tunnels (Gara's tip) as a battlefield; the combat-data buyer (synthetic power development); Harumi Wharf; the ten-win strike team; a bigger Kurokawa power broker ('Masat...', name truncated in the extract). Plan it with the charter (`docs/story-design.md`) and the user's approval; nothing here goes into a prompt.

### Showcase fight: Daigo Renjiro (Book 1 finale)

To be designed with the Act 3 charter: villain sheet (rule, tell, weakness, finisher) for Daigo's Iron Palm Strike, Territorial Command and Unshakable Stance. No sympathetic reveal.

### Act 3 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| (to be planned) | (to be planned) |

## 7. Personal quests and PC tests

PC arcs are series of tests, never planned outcomes; each arc has at least one love-or-home test for Jostin and one strength-or-purpose test for Jovian (situations, never outcomes). Jostin's Blackstar bloodlust is not a theme: one acknowledging scene (Riko's straight talk, optional at 4-1), then closed.

| PC | Test | Situation (director-only) | Beat |
|---|---|---|---|

| Jostin | home | Club Lumiere turns out to be watched through a lens; the crew's home must be made safe. | 4-4 |
| Jostin | love | The date he owes Ayame competes with the arc's pressure, and her stream phone is the lens risk. | 4-4 |
| Jovian | purpose | Kiriyama's trade (the footage for the Kagero files) asks what Jovian actually fights for. | 4-3 |
| Jovian | strength | A fighter who has studied every fight Jovian has had on camera; their first fight, in the dark, asks him to fight past his own record (the earlier round-one loss was cut at t482). | 4-5 |

Open personal threads (breather scenes when the players ask; each at the NPC's pace): Reiko's private talk with Jostin; Jostin owes Ayame a date (4-4 prep beat); Jovian and Yuzuki; Rikona joining (Jovian's offer, her yes); Jostin's cafe plan (Hearth business, possible date). Backstory about who the PCs are inside needs the user's OK first; the director may invent world-side history.


## 8. Time skips

Between milestones, offer an optional "skip to next week" montage with player choices about training, base work, errands and relationships. **Never force a skip.**

- Offer it in a prompt via an NPC or a phone notice ("Plan your week").
- The player chooses (training, job, study, home time, rest, relationships). The director sets the next-prompt `Cut:` to the first morning of the next week, using the player's chosen focus.
- Do not skip past a scheduled milestone (a fork, a deadline the players can act on, a showcase fight).
- A skip never decides a player-character outcome; it summarizes only what the players chose.

## 9. Split scenes

Allowed. Protocol in `split-scenes.md`.

## 11. Obstacle and surprise rules

- One surprise per scene; small most of the time (a note, a delay, a visitor, a malfunction, a stray memory).
- Larger surprises are saved for act turns.
- Every scene needs a world move, because NPCs are passive.
- Keep obstacles ordinary. Drama comes from people.

## 12. Scene turn budgets

Every scene gets a turn budget, so the arc keeps moving and the player's attention goes where the story is.

**Budgets** (director turns, counted from the first prompt of the scene):

| Scene type | Budget |
|---|---|
| Fights | 4 to 8 turns |
| Big emotional scenes (confessions, splits, verdicts, results) | 3 to 6 turns |
| Investigation | 1 to 2 turns |
| Travel and waiting | 0 (cut) |
| Arrival, admin, move-in or errand scenes | 2 turns at most |

- **Over budget, or goal met: cut to the next beat.** When a scene runs past its budget, or its goal is met even under budget and the input is quiet, the next prompt's `Cut:` moves to the next beat. Do not wait for a perfect ending; the players can bring a loose thread along.
- **Time skips: offer one at natural lulls.** At the end of a scene, a meal or a night, offer a single skip. Never force one, never skip past a scheduled milestone, and a skip never decides a player-character outcome (see Time skips).
- A fight is over when its finisher lands; do not pad it to reach the budget. Budgets are ceilings, not targets.

**Named beats of Arc 4** (tight finish from t482; was 31 of 34): 4-1 Stills 3 (done); 4-2 Dead Zone 1; regroup and invitation 1; 4-3 Neutral Ground 3; 4-4 Go Dark 3; 4-5 Lights Out 5; 4-6 Final Frame 3 (corner, fork, aftermath); breather 1 to 2, morning after at Lumiere, no cliffhanger. Personal threads play only when asked and don't count.

**Scene length by type** (turns, from the old playbook, same as the table): fights 4 to 8; big emotional scenes 3 to 6; investigation and planning 1 to 2; travel and waiting 0 (cut); banter as long as the players keep going (budget it, but a flagged lull may be offered a skip). Time skips: the Joestar calendar is turn-based, not day-based; offer "plan your week" montages only at natural lulls and never skip a scheduled beat.

**Arc budget governor.** At 60 percent of an arc's budget run a midpoint review; at 100 percent the arc is in its finale; over budget, cut non-essential beats and jump (pulse check rule, `docs/story-design.md`).
