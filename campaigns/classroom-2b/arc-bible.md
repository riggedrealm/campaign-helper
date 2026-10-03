# Class 2B: Arc Bible

Director-only. Everything here is final design. Prompts carry only the sliver a scene needs.

Machine-readable copies of the cast (including the villain sheets below), quests and Standing rubric live in `data/` and are queried with `tools/db.py`; this file keeps the narrative design. If the two ever disagree, the design here wins and `data/` should be corrected before play.

## 1. Premise and stakes

2B is Chikara Academy's off-campus misfit experiment: eight first-year students living together at Sakura Lane Sharehouse. Each was placed there for a reason (late transfer, unstable power, a record, a scandal). An end-of-semester review by Vice Principal Reiko Shimazu decides whether 2B is **renewed** or **dissolved**. Dissolved means students are scattered to other homerooms and the sharehouse lease ends. It is not expulsion.

Stakes the players can feel:

- A home: the house, the people in it, the lease.
- A reputation: Chikara Academy's 1A looks down on 2B; Shimazu believes 2B is a liability.
- A teammate: Mio's secret can cost her her place, and the house must decide how far to go for her.

Shimazu is by the book, not a villain. She believes experiments hurt students because one already did (the Annex Cohort, Yūto's).

### Scope and players

- Built for 1 to 4 player characters. Assume nothing about their powers or backgrounds.
- One semester, about 16 weeks. **Day 1 is a Saturday** (move-in); Day 3 is Monday (classes start). Weekday of Day N: N mod 7 = 1 Sat, 2 Sun, 3 Mon, 4 Tue, 5 Wed, 6 Thu, 0 Fri. Fridays are Days 7, 14, ..., 112. Week W covers Days 7W-6 to 7W.
- Placement: the placement tournament assigns specializations (Rescue, Support, Strike, Investigation, Media, Agency Operations). 2B is the homeroom and residence cohort.
- Player characters choose from `Sakura Lane Sharehouse/courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom` and `river-bedroom`. Unclaimed rooms hold background 2B housemates (unnamed, no plot).

### Tone

Scene mix in four shares: hero action 2 (about half), school and house life 1 (about a quarter), drama 1 (about a quarter). Act milestones stay as planned; the mix steers world moves, open beats and time-skip targets, leaning toward whichever share has fallen behind. Every act has a showcase fight and puts one relationship under pressure.

- Fights are **puzzle first** (crack the enemy power's rule), **spectacle to finish**.
- **Earned wins.** Enemies are dangerous, but player characters can always win with good play. Losses cost something (Standing, a person, a place) but never end anything.
- The director never states player-character or combat outcomes; Voyage rolls combat.

### Venue substitutes (no invented places)

The world has no named 2B homeroom, Support lab, or tournament arena, so the closest existing places stand in. All are real locations and areas in `data/locations.json` (look them up with `python3 tools/db.py loc`):

| Need | Stand-in |
|---|---|
| 2B homeroom (lent space) | `Chikara Academy/classroom-4d` |
| Support lab | `Chikara Academy/classroom-5a` (lab benches) |
| Investigation class | `Chikara Academy/classroom-3c` |
| Strike class | `Chikara Battle Arena/training-bays` |
| Rescue class | `Hero Field Complex/rescue-village` |
| Media class | `Pulse Media Tower/studio-floor` |
| Agency Operations class | `Hero Agency Row/public-relations-office` |
| Placement tournament | `Chikara Battle Arena` (`main-floor`, `training-bays`, `medical-station`, `officials-booth`, `spectator-gallery`) |
| Reviews, announcements, Shimazu | `Chikara Academy/main-hall` |
| Entrance-exam gym wall | `Chikara Battle Arena/training-bays` |
| Part-time job listings | `WorkLink Exchange/job-board` |
| Jobs and clubs | `Gearshift Support Shop`, `Campus Corner Mart`, `Rescue Volunteer Desk`, `Crepe Expectations`, `Midnight Diner`, `Common Ground/club-hall`, `Clubhouse Row/club-plaza` |
| Mio's parts | `Support Street/prototype-studio`, `Gearshift Support Shop/inventory-room` |
| Nightshade meeting | `Nightshade Exchange Relay/contract-room` |
| Police report | `Koban Corner/front-desk` |
| Ultra Force contact | `Ultra Force Headquarters/reception` |

## 2. Hidden state

- **2B Standing**: start 40, kept in `data/ledger.json` (`python3 tools/db.py state`), never shown as a meter. Endings: 70+ Renewed, 40 to 69 Probation, under 40 Dissolved.
- **Mio's secret**: ¥450,000 borrowed through Nightshade Exchange (the existing criminal contract market) for a black-market control rig (a stabilizer bracelet). At the entrance exam her nerves broke and her parts scattered; the rig held her steady, so the result showed her real power (Exploded View), faked steady. With interest, ¥720,000 by Day 60.
- **Arimura**: assigned to 2B because Shimazu expects it to fail. He was also a guest instructor at the Annex Cohort exercise and left early that day.
- **Ayame**: her Edge Current caused the accident behind Sunny's scandal video; Sunny took the blame on camera. The clip was cut and leaked by a jealous 1A classmate, still in 1A.
- **Shin**: the Nine Corners' call-back is a trap: they want revenge over Daiki.
- **Yūto and Shimazu**: both carry the Annex Cohort, dissolved three years ago. Shimazu's barrier rule that day, "no projectile crosses", let a falling beam through; Yūto took the wound into himself; she signed the dissolution.
- The full cast bible is `docs/cast-bible.md` and the visual sheet is `docs/cast-visuals.md` (human reference only; during play use `db.py brief`); the eight main NPCs are in `New_World.json` and `data/cast.json` (status `world`).
- **Relationship values** are Voyage's. The director reads them from story output. A personal quest unlocks at 50 or more with that housemate.

## 3. Pacing at a glance

| Act | Days | Weeks | Showcase fight | Relationship under pressure |
|---|---|---|---|---|
| 1 Move-In | 1 to 7 | 1 | Placement tournament, Days 6 to 7 | The house splits by class |
| 2 Finding Footing | 8 to 42 | 2 to 6 | Joint field exercise breach, Day 34 | Sunny and Ayame |
| 3 The Secret | 43 to 77 | 7 to 11 | Collectors hit the house, about Day 63 | Mio and the house |
| 4 Battle Test | 78 to 112 | 12 to 16 | Battle Test, Day 105 | The house and Shimazu |

## 4. Act 1: Move-In (Days 1 to 7)

**Purpose**: Make the house a home before it is threatened. End the week with the house split by class.

**Quests**: "Move-In Weekend" (main) and "Ability and Pulse Tutorial" (side, giver: House Manager), both seeded in the Day 1 move-in scene. The tutorial is player-directed (the director never invents the character's ability concept, account or consent) and **must be done before the placement tournament on Days 6 to 7**, because characters start with no abilities. Reward: 1,000 experience.

**Beats** (one per turn; a beat can take several turns if the players linger; each beat has a turn budget, see section 14):

1. **Day 1, Dawn.** *Budget: 3 turns (turns 2 to 4).* Voyage's story start opens at `Sakura Lane Sharehouse/building-entrance` (see `opening.md`). The House Manager explains the rules and shows the bedroom. Tatsuya and Shin are around. The Manager mentions that the house Wi-Fi, chore rota and dinner list run on Pulse and that Tatsuya can help: the Ability and Pulse Tutorial seed. Small surprise: paperclips rearranged on the sign-in sheet.
2. **Day 1, late morning.** *Budget: 2 to 3 turns.* Skip here from the move-in scene. Mio is first seen coming down for food (she was heard, not seen, in the loft). Sunny arrives by taxi in the afternoon; the skip to the evening covers it unless the player is out front (then 1 to 2 turns).
3. **Day 1, evening.** *Budget: 3 to 4 turns.* Welcome dinner in `shared-lounge` / `shared-kitchen`. First chance for a house cohesion moment (+3).
4. **Day 2.** *Budget: 1 to 2 turns, then offer the time skip.* A free day: jobs, rest, the neighborhood, the Pulse app (a natural place for the Ability and Pulse Tutorial). Optional "skip" montage offer (section 10).
5. **Day 3, Monday.** *Budget: 2 to 3 turns.* Orientation at `Chikara Academy`. Arimura is checked out. Shimazu gives the class a warning (verdict on a line). The walk to school is cut.
6. **Day 4 to 5.** *Budget: 1 to 2 turns per scene (Yūto, class day), 2 to 3 for the tournament briefing.* First class days. Yūto first appears (`Chikara Academy/vending-machine-nook`). Tournament briefing: team bouts, stakes (placement). If the Ability and Pulse Tutorial is still open, the Manager or Tatsuya reminds the player once; it is due before Day 6.
7. **Day 6 to 7: showcase fight** (see below). *Budget: 4 to 8 turns per bout (Round 1, Round 2, Final).* Warm-ups and the trip to the arena are cut.
8. **Day 7 evening.** *Budget: 3 to 6 turns.* Placement results. The house splits: Tatsuya in Strike, Mio in Support, Shin in Investigation, Sunny in Media; the player characters share one specialization. First friction.

### Showcase fight: the placement tournament (Days 6 to 7)

- **Venue**: `Chikara Battle Arena`. Warm-ups in `training-bays`, bouts on `main-floor`, scoring in `officials-booth`, crowd in `spectator-gallery`, patching in `medical-station`.
- **Format**: team bouts. The player characters fight as one team; up to four players. Fill a team out with housemates the players invite (they stay fixed in their own specializations) or background 2B classmates.
- **Bouts**: Round 1 (Day 6 morning), Round 2 (Day 6 afternoon), Final (Day 7). Opponents are generic teams, each built from a rule: a power with a visible tell and an exploitable limit.

Generic opponent template (rule / tell / weakness / finisher setup):

| Bout | Opponent power rule | Tell | Weakness | Finisher setup |
|---|---|---|---|---|
| Round 1 | Heat haze: distorts distance within a shimmering ring | The air wobbles over a chalk-white line | Ring collapses if the caster is jostled | Break the caster's stance; one clean hit |
| Round 2 | Magnet-skin: sticks to metal boundary rails | A faint ticking when they step | Needs contact with metal | Pull them off the rails; leave them with nothing to grab |
| Final | Rebound clap: repeats any sound as a sonic burst a beat later | Lips move a half-beat before the burst | Needs a distinct clap to start | Drown the clap in noise; the burst hits their own team |

**Standing from the tournament**: +0 to +10 total. A guide: Round 1 win +2, Round 2 win +3, Final +3 (win or a strong loss), conduct +2 (helping a fallen opponent, fair play). Losses are 0, not negative.

**Placement rule**: Player characters are placed **as a group** into one shared specialization, chosen by how the team performed:

| What the team did | Specialization |
|---|---|
| Protected or carried teammates, rescued a fallen opponent | Rescue |
| Enabled others, buffed or repaired mid-bout | Support |
| Won with force, finished fast | Strike |
| Cracked the enemy's rule early | Investigation |
| Played to the crowd, controlled the narrative | Media |
| Ran strategy, gave orders, coordinated | Agency Operations |

A mixed performance leans to whichever dominated the Final. The NPC housemates are fixed in Strike (Tatsuya), Support (Mio), Investigation (Shin) and Media (Sunny), so they split off by class whichever specialization the team receives.

**If the fight goes badly**: the team is placed in the nearest-fit specialization at lower marks (Standing +0, no bonus). Nothing ends.

**Friction candidates** (use one at a time):

- Sunny overhears Ayame in the gallery call Media "a consolation prize".
- Mio bolts from the arena before scores are read.
- Tatsuya's bout cracks a wall panel; he leaves the post-tournament dinner.
- Shin vanishes after a staff member calls him "the record kid".

### Act 1 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Chores and quiet hours collide with new arrivals | Paperclips rearrange into "WELCOME" on the sign-in sheet |
| Sunny's late arrival strains the room count | Sunny's luggage includes a ring light that flickers the whole lane's lights |
| Arimura never answers questions | Arimura leaves the room mid-sentence and returns with snacks, saying nothing |
| Shimazu's warning leaves the class tense | A Pulse notice posts a rumor that 2B "won't last a month" |
| Tournament nerves; unknown teammates | An opposing team's captain bows to Tatsuya |
| Time pressure: the finale is also the last day of the week | The tournament medical team asks Yūto to cover the station |
| Mio's absence at dinner | Her loft light is on all night, and a small whirr carries down the hall |
| Different class schedules split the house | A hallway whiteboard reorganizes itself into a rota (Mio) |

## 5. Act 2: Finding Footing (Days 8 to 42)

**Purpose**: Build routines, give the house a pulse, and test the first outside pressure. Ends with the midterm verdict.

**Beats**:

1. **Specialization classes** begin (Day 10, Monday of week 2). Specializations meet at the stand-ins above. Show the house splitting its days and coming back at night.
2. **House routines**: chores rota, cooking nights, quiet hours, `rooftop-chill-deck` late talks, `laundry-room` runs, Pulse app group chat.
3. **Jobs and clubs**: part-time jobs through `WorkLink Exchange/job-board` (legal shifts, pay, schedules). Clubs at `Common Ground/club-hall` or `Clubhouse Row/club-plaza`. Pay matters later (Nightshade Path 1).
4. **Day 10 (Monday).** Ayame's first jab: 1A looks down on 2B. Venue: `Chikara Academy/student-courtyard`.
5. **Weeks 3 to 4.** Personal quests may unlock at relationship 50 or more. Arimura gives one useful, grudging line.
6. **Day 34 (Thursday): showcase fight.** Joint 1A/2B field exercise at `Hero Field Complex/rescue-village`. Members of the powered dropout gang (the Hollow Dogs) from the `Academy District Abandoned Training Facility` attack the exercise.
7. **Day 35 to 41.** Fallout: injuries, a statement to staff, Pulse coverage, Sunny and Ayame forced into the same room.
8. **Day 42 (Friday).** Midterm progress review in `Chikara Academy/main-hall`: **Shimazu tells 2B it is failing**, whatever Standing is. Her tone follows the Standing hint bands in `data/ledger.json` (`hint_bands`); the verdict stays.

### Showcase fight: the dropout gang attack (Day 34)

**Setup**: A joint rescue drill. Each pair mixes 1A and 2B students, with civilian-actor volunteers in the mock village. The Hollow Dogs hit the exercise to steal the complex's rescue gear cache and humiliate the academy that closed their proving ground. They are dangerous, not murderous: they want gear, a scene, and a name.

**Why now**: The academy has scheduled the abandoned facility for demolition. The gang wants it known they still exist.

**Fight shape**: Puzzle first (crack Mooring's threads), spectacle to finish. Pressure: 1A and 2B must work together; Sunny and Ayame end up in the same pair or the same corner.

#### Villain sheet: Jun Kurose "Mooring" (gang leader)

| Field | Detail |
|---|---|
| Role | Hollow Dogs leader, 20, dropout |
| Power rule | **Anchor Threads.** He fires glowing orange cords from his wrists. A cord hooks the first solid thing it touches and holds that point fixed to him: the target can move around the anchor but cannot go farther than the cord's length (about 10 meters), and he can reel in slack. He can hold at most four cords at once. |
| Tell | The cord glows faint orange a beat before it fires, and his wrist twitches like casting a line. Anchors show as a bright ring where they hit. |
| Weakness | Cords cannot cross: two that touch fray and snap. A taut cord snaps if a moving mass crosses it fast. He needs line of sight to his anchors, and cutting sight drops them. |
| Finisher setup | The village's overhead crane and steel beams. Lure him into pinning two fast targets on crossing paths; the snapped cords whip back to him and tangle his own arms. A swing of the crane beam or a shockwave finishes it. |
| Behavior | Opens by pinning the strongest-looking target, taunts the weak ones, flees only if four cords are cut. |
| If it goes badly | The gang escapes with the rescue gear cache; one civilian actor and a 1A student are injured (not worse); Pulse runs a story on "2B's failure". Standing: −5 for a disciplinary incident only if the players defied an instruction to evacuate. |

The three Hollow Dogs are generic and quick to read: one with a cracked helmet (charges in a straight line), one with a bat (reinforced strikes), one with a toothpick (sparks off metal). Each has a plainly visible limit (the charger cannot turn, the bat-wielder tires, sparks fade on wet ground).

**Feeding the puzzle within the prompt limit (840, see `db.py state`)**: Put the rule on a `Facts:` line ("Mooring's cords glow orange before firing; crossing cords snap"), show the tell in a `World:` beat, leave the weakness to be discovered. Do not state results; Voyage rolls combat.

**Standing**: Public rescues and good conduct +3 to +5. Gang beaten with civilians protected: +5. A disciplinary incident (defying orders) −5.

**Aftermath beat**: Shimazu visits the field (her Bastion barriers hold the village's edge); she notes 2B and 1A cooperating, or not, and says nothing yet.

### Act 2 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Class schedules mean the house rarely meets | A group chat chime goes off in every pocket in the classroom |
| Money: rent, food, parts | A job listing wants "someone with a steady hand", which suits Mio |
| 1A's jabs in public | Ayame offers a polite, cutting compliment to Tatsuya, and walks off |
| Arimura's absence at a key moment | He is spotted on the roof doing a very long, very silent run |
| Tatsuya's leakage damages the house | The shared-lounge table develops a hairline crack he hides under a book |
| Mio avoids Shin's handshakes | A coin rolls out from under her door, and she snatches it back |
| Skipping classes tempts a PC | A neighbor invites the player to a festival the same afternoon |
| Gang attack panic | A civilian actor in the village is actually a kid from the lane |

## 6. Act 3: The Secret (Days 43 to 77)

**Purpose**: Mio's debt collides with the house. The act tests the house's loyalty and ends with Arimura's turn.

### Mio's hidden truth

Before Chikara Academy's entrance exam, Mio borrowed **¥450,000** through **Nightshade Exchange** to buy a black-market control rig, a stabilizer bracelet. Her nerves broke at the exam and her parts scattered; the rig held her steady, so the test showed her real Exploded View, faked steady. She cheated to get a steadiness she did not have. With Nightshade's interest, it is **¥720,000 due Day 60**. The rig is hidden under the loose floorboard in `loft-bedroom`. She has paid interest through the Nightshade app out of part-time money and gear sales; she is out of options.

### Collection in two stages

1. **Job offer.** Broker **Sōichi Tamaru** messages Mio (and, if she pulls the house in, the players): clear the debt by stealing a prototype, the **Lantern Coil**, from the Support lab (`Chikara Academy/classroom-5a`). Quest: "The Lab Job".
2. **Collection contract.** If the offer is refused or stalls past Day 60, a collection contract goes live and freelance collectors hit `Sakura Lane Sharehouse`. That is the Act 3 **showcase fight / mid-semester incident**.

### Beats (suggested days)

| Days | Beat |
|---|---|
| 43 to 49 | Aftermath of the midterm. Mio is strained: skipped dinners, a phone she turns face-down, a late-night payment notice. |
| 50 to 56 | Clue ladder (below). The job offer arrives around Day 52. |
| 57 to 60 | Decision window. The deadline is Day 60. |
| 61 to 63 | If unresolved, the contract goes live (Day 61). Collectors hit Day 63 evening (a Friday) or within two days. |
| 64 to 70 | Fallout. The house splits over whether to cover for Mio. Arimura's turning point. |
| 71 to 77 | Resolution. Shimazu opens an inquiry if the fraud or the fight is known. |

### Clue ladder (fair play; use one rung per scene)

1. Mio turns her phone face-down; a notification buzzes through the table.
2. An envelope slipped under the loft door: Shin rewinds it and watches hurried, gloved handling in the last few minutes, without seeing the contents.
3. Mio asks for extra shifts, then sells something precious.
4. A loose board in the loft; metal clinks under it.
5. A broker's clean voice on a call through the Nightshade app.

### Showcase fight: Nightshade collection

The collection happens somewhere in every path. If the collectors do not reach the house, the same villain sheet is used at the transaction point instead (see the path table).

#### Villain sheet: Hayami Gen "Tally" (Nightshade collector lead)

| Field | Detail |
|---|---|
| Role | Freelance Nightshade collection lead, 29, with two junior collectors (net launcher, folding baton) |
| Power rule | **Tally Mark.** His ringed hand leaves a glowing gold tick on whatever he touches. Each tick adds heavy weight; four ticks pin a person to the ground. Ticks last one minute, and only the ring can place them. Touch only. |
| Tell | He spins the brass stamp ring on his thumb before stamping; ticks show as gold lines on clothing. He always stamps the biggest threat first. |
| Weakness | Range: he must touch. If the ring leaves his hand (knocked off, pulled off), all marks vanish. He never stamps the same target twice in a row. |
| Finisher setup | Marks go on objects as well as people: a heavily ticked coin or throwable thing becomes a tiny anvil. Redirect the weight onto him (a thrown tick-laden object, or knocking the ring loose just as he marks the floor). Mio's Railpin can launch a ticked metal object if she is present, but the plan works without her. |
| Behavior | Polite, patient, relentless; talks debt as arithmetic. Backs off if a civilian is clearly in danger and he is told Ultra Force has been called; not a killer. |
| Junior collectors | Net launcher (entangles; weak to cutters, a hard pull breaks the net's release), baton (close-range strikes; tires fast, flinches at bright light). |
| If it goes badly | Tally's crew leaves with the loft's rig and a day's warning; a housemate is hurt (not worse); Standing −5 if it was an off-books fight. The debt stays. |

**Standing**: Fight off the collectors: −5 (off-books fight), +3 to +5 if civilians are protected (Manager, lane neighbors). No double-counting of unrelated gains.

**Setting**: `house-courtyard`, `shared-lounge`, `shared-kitchen`, `rooftop-chill-deck`, `building-entrance`. Civilians: the House Manager (unless it is her Wednesday afternoon off), neighbors drawn by the noise.

### Arimura's fixed turning point

When the collectors hit the house, Arimura shows up and takes responsibility in front of Shimazu. From then on he actively coaches.

- **Trigger**: the moment collectors attack `Sakura Lane Sharehouse`.
- **Staging**: Arimura arrives during or just after the fight, fast (Slipstream). Shimazu arrives within minutes with campus security after the lane's alarm. She asks who is responsible. Arimura says, "I am. They were put in my class and I treated it like exile. The house is mine." He admits, with her present, that she assigned him expecting 2B to fail. She does not deny it.
- **Fallback**: if no collectors reach the house (Paths 1 or 2), stage the same scene when a house-level incident first puts 2B in front of Shimazu: the transaction fight spilling onto a street, a hearing after a theft inquiry, or a Nightshade warning smashing the house on Day 70 at the latest. Arimura speaks the same words.
- **After**: He coaches. Training days with Slipstream drills on `Hero Field Complex/mobility-track`, sarcasm intact.

### Five resolution paths and Standing

| # | Path | Standing | What happens |
|---|---|---|---|
| 1 | **Pay it off by pooling job money** | Neutral; the fraud stays hidden | Needs ¥720,000 by Day 60, or a partial payment for a five-day grace. Handoff at `Nightshade Exchange Relay/contract-room` is tense: Tally demands a late fee and the confrontation (fight) moves to the `exit-alley`. |
| 2 | **Do the job** | −25 if discovered; it might never be discovered | Steal the Lantern Coil from the Support lab. Handoff at `Riverside Green/riverside-bridge`: Tally double-crosses and tries to keep both the Coil and the "collection fee". Fight uses the Tally sheet. |
| 3 | **Fight off the collectors** | −5 off-books; +3 to +5 if civilians are protected | The fight at the house. Defeating Tally closes the contract only until the next collector; the debt still stands. |
| 4 | **Come clean (Mio confesses)** | −10 now; +15 at the final review for integrity | Mio confesses (to Arimura, Shimazu, or the house). Shimazu starts to respect 2B. The retest is triggered. |
| 5 | **Bring in Ultra Force or the police** | Neutral to positive (0 to +3 for civic conduct) | Report to `Ultra Force Headquarters/reception` or `Koban Corner/front-desk`. The debt's origin is recorded only as an "unspecified loan" unless Mio confesses. Nightshade becomes hostile to the house. |

Paths combine. Confession (4) can sit on top of any of the others; 3 and 5 are responses to the hit; 1 and 2 happen before it.

**Discovery clock for Path 2**: three hidden ticks after the theft. Each tick that finds a clue (lab inventory check, camera footage, a staff member's check of what Shin rewound, a Pulse post) moves toward discovery. If three ticks pass with no clue, it may never come out; keep it as a sandbox hook. When discovered, Standing −25 at once.

**Nightshade hostile (Path 5)**: scouts watch the lane; a warning painted on the entrance; a leak to Shimazu at the director's choice (optional trigger for the retest).

### The retest

If the fraud comes out (confession, theft discovery, or a leak), Mio must pass a supervised **retest** before the Battle Test, using only her real power and her own legitimate gear. The retest checks her *control* without the rig: can she hold Exploded View steady on her own?

- **When**: within seven days of the fraud coming out, no later than Day 98. Default: Day 84 if the fraud comes out in Act 3.
- **Where**: `Chikara Academy/classroom-5a` (the Support lab), with Shimazu and Arimura supervising.
- **Test**: build a working rescue tool from standard stock parts and use it, with Exploded View only (no rig), to free a mock casualty from a jammed pressure door, holding her parts steady under watch.
- **Passing**: keeps her; Standing +10. **Failing**: removes her (transfer); this feeds the Probation ending.
- **Fair play**: pass if Mio had two or more meaningful prep beats (study sessions, the "Built, Not Born" quest, legitimate control gear); fail only if prep was absent and the in-scene puzzle goes unsolved. The director states Mio's result as an NPC outcome; players supply support.
- **Quest tie**: "Built, Not Born" gives her a legitimate control gauntlet that makes the pass natural.

### The house may split

Whether to cover for Mio divides the house along character lines:

- Tatsuya wants to tell the truth but will not betray a friend.
- Shin covers; he knows what it is to be judged by a record, and loyalty to the house comes first.
- Sunny knows what exposure costs and what lies cost; torn.

Put this under pressure in a house scene (`shared-lounge`) after the fight.

### Act 3 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Mio's secrecy | Her phone rings in a quiet lecture; she throws it into her bag |
| Money and time | A job posts a one-day pay rate that is just enough |
| Moral pressure: steal, tell, or fight | A lab technician mentions the Coil's case alarm is "usually off" |
| Mixed loyalty | Shin offers a locked door and no questions |
| Shimazu's inquiry | Yūto mentions Shimazu asked the clinic for a list of recent night injuries among students |
| Collectors' timing | Tally holds the door for the House Manager, politely |
| Fallout | Sunny's followers bump overnight; she deletes the post |
| The split | Tatsuya cracks the lounge table when he shouts, and apologizes |

## 7. Act 4: Battle Test (Days 78 to 112)

**Purpose**: Everything pays off in one shared arena and one verdict. Close the quests, then the review.

**Beats**:

| Days | Beat |
|---|---|
| 78 to 80 | Pairs announced at `Chikara Academy/main-hall` (Day 80, Monday). |
| 80 to 98 | Training arc. Arimura coaches (Slipstream drills, rescue basics). Retest if triggered (default Day 84). Personal quest finales. |
| 99 to 104 | Site walk at `Hero Field Complex`. Nerves. Last house dinner before the test. |
| 105 (Friday) | **Battle Test.** |
| 106 to 110 | Scores post. Quiet beats: apologies, decisions. |
| 112 (Friday) | **Final review** in `Chikara Academy/main-hall`. Ending. |

### Pairs

- Player characters pair with each other, and their pairs **share one sector**.
- NPC pairs are Tatsuya + Mio and Shin + Sunny.
- With 1 or 3 player characters, the odd player character pairs with Sunny, and Shin gets a fill-in partner from another class (Natsuki Sone).
- Ayame is paired with her 1A partner Takumi Hoshino.
- If Mio has been removed (failed retest), Tatsuya pairs with a fill-in; if any housemate has left, use a fill-in. Do not leave a player character without a partner.

### Showcase fight: the Battle Test

**Venue**: `Hero Field Complex`. A staged disaster, a simulated collapsing transit station built in `rescue-village`, with the `observation-tower` as judging post. `field-complex` for staging and briefings. `mobility-track` for the approach course.

**Scenario**:

- Civilian actors in the station need evacuation.
- "Villain" proctors are out to stop evacuation.
- A mid-test **second collapse** twist: about halfway through, a section of the concourse ceiling drops, cuts routes, and shoves pairs into each other's sectors. Staged, but real hazards; Shimazu's barrier staff hold the actors' zones.
- It is a **shared arena**: several pairs are on the field at once, including Ayame and her partner. **Helping other pairs (including 1A) can score better than winning.**
- Sectors (director assigns): Concourse, Platform, Stairwell, Tunnel. The player pairs share one sector; the others hold their own. The second collapse breaks the borders.

**Scoring** (hidden): civilians evacuated, proctor threats neutralized, teamwork, rescues, and help given to other pairs. Helping 1A is a high-value action. The overall Standing gain is **+5 to +25**:

| Result | Standing |
|---|---|
| Completed the evacuation alone, no help to others | +5 to +10 |
| Strong teamwork or a proctor cracked | +10 to +15 |
| Rescue of someone in another sector | +15 to +20 |
| Helping 1A (including Ayame) at real cost, plus civilians out and the second collapse handled | +20 to +25 |

**Ayame's beat**: her pride is tested when the second collapse pins her and Takumi. Whether she accepts help sets the tone of her ending and the "Off-Camera" resolution.

**If the test goes badly**: Standing +0 to +5; the proctors "win"; the players do not lose their places. Nothing ends.

#### Proctor threats

##### Rokuro Daimon "Faultline"

| Field | Detail |
|---|---|
| Role | Veteran proctor; main physical threat; stationed in or near the player sector |
| Power rule | **Seismic Seam.** A heavy stomp opens a crack along existing seams in the floor (tile joints, rail lines), sending a line of breaks outward. Cracks run in straight lines from his stomp. |
| Tell | He plants his foot and dust jumps along a line a beat before the crack. |
| Weakness | He cannot crack through solid, welded or filled joints (steel rails, a poured edge). He cannot stomp while airborne or off solid ground. |
| Finisher setup | The platform edge and the rail trench. Lure his line into the sealed trench so the platform section behind him drops, and he slides into the foam-lined pit. The second collapse offers a bonus: his cracks trigger another section if misdirected. |

##### Haruka Sōma "Static"

| Field | Detail |
|---|---|
| Role | Proctor; locks routes; operates near the control room and shutters |
| Power rule | **Static Lock.** She charges powered devices (turnstiles, shutters, door panels) and locks them in place; locked devices do not open for anyone but her. Her charge works only on powered devices. |
| Tell | The ceiling lights flicker in a short pattern before a device locks, and her hair rises. |
| Weakness | Locks have a manual crank override. A grounded path discharges the lock. She can maintain only three locks at once. |
| Finisher setup | Redirect a lock onto her: re-power a shutter beside her, then let it drop and pin the cloak. Mio, if present, can lift a panel's lock apart in an exploded view. |

##### Ibuki Narita "Mirror Crowd"

| Field | Detail |
|---|---|
| Role | Proctor; mimics civilians; roams across sectors |
| Power rule | **Mirror Crowd.** Makes light-formed copies of civilians; copies move and cry out like the real ones but cannot carry weight. |
| Tell | Copies cast no shadow and are silent underfoot; real actors have footsteps. |
| Weakness | The copies are soundless; a loud noise or touch dissolves one. He can sustain only five at once. |
| Finisher setup | Make the copies stand in a line against a bright light so the shadowless ones stand out; grab the real civilian; the hidden proctor, exposed, is the target. |

Proctors know which sector contains whom: put at least one in the player sector and have the others roam. Their rules must be demonstrated before the lethal use. A proctor wins only the points it denies; no one is permanently hurt.

### Final review and endings

Held on Day 112, `Chikara Academy/main-hall`. Shimazu reads the verdict with Arimura present.

| Standing | Ending |
|---|---|
| 70+ | **Renewed.** The review passes and the lease is renewed. Shimazu personally signs the renewal and may respect them. |
| 40 to 69 | **Probation.** 2B survives with conditions Shimazu sets; one housemate leaves or transfers (possibly Mio, depending on choices). |
| Under 40 | **Dissolved.** 2B is scattered; Shimazu offers the strongest students places in other classes; a move-out epilogue and a final house scene show the bonds lasting. |

Apply the final +15 for a confession before reading the threshold. Name the ending in the scene with Shimazu's voice; never read the number out.

**Renewed**: Shimazu signs in front of the house. Beat: she says "I was wrong to expect failure" or something in her voice. Arimura and Shimazu share a moment.

**Probation**: conditions set by Shimazu (examples: monthly reviews with Arimura, no unsupervised power use off campus, one housemate transferring). The departing housemate is chosen by choices, not by the director's mood: Mio if the fraud came out and the retest failed; otherwise the housemate whose arc points elsewhere.

**Dissolved**: Shimazu offers places to the strongest. Players choose. Then the move-out epilogue at `Sakura Lane Sharehouse/building-entrance` and a final house scene (`shared-lounge` or `rooftop-chill-deck`) showing the bonds lasting.

### After any ending: sandbox

The game continues as a sandbox.

- **Renewed or Probation**: stay at Sakura Lane. New semester threads: Nightshade fallout, Shin's old gang, Sunny's media career, Tatsuya's control, Mio's control gear, Ayame's friendship.
- **Dissolved**: move-out epilogue; then each player character picks new housing. Existing options: `Chikara Student Residences`, `Willowbank Residences`, `Mizuno Heights`, `Lantern House Apartments`, `Harborview Terrace`. The House Manager helps with the move.

### Act 4 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Training fatigue; pair friction | Arimura demonstrates a move and winces at his knee |
| Retest tension | Mio's tools rattle on the bench before she touches them |
| A partner is unavailable | A fill-in introduces herself with a note and two pens |
| Ayame's pride | Ayame leaves a folded note in a 2B locker: "Do not die." |
| Second collapse | A civilian actor is really Mirror Crowd |
| Ending logistics | The House Manager's notebook lists everyone's tea |
| Shimazu's mask | She straightens the 2B placard in the hall before leaving |
| Time pressure | The test siren sounds two minutes early |

## 8. Personal quests

Each unlocks for the player character who reaches **relationship 50 or more** with that housemate. Other player characters may join if present or invited. Full triggers, objectives and seed lines are in `data/quests.json` (`python3 tools/db.py quest <name>`).

### "Gentle Hands" (Tatsuya): find a safe way to fully release his power

- **Stages**: (1) Ask why he apologizes; he admits the wall. (2) Test controlled releases on `Hero Field Complex/field-complex`. (3) Design a "bleed-off": plates or a sink (Mio can help), and Arimura or Yūto as spotter. (4) The last release at the gym wall he broke: `Chikara Battle Arena/training-bays`.
- **End**: the wall holds, or he brings it down deliberately and rebuilds it. Either way he walks out unafraid.
- **Reward**: a reliable big move for the Battle Test; Standing +3 (a house cohesion moment).

### "Built, Not Born" (Mio): build legitimate control gear of her own

- **Stages**: (1) See her sketches in `loft-bedroom`; learn she builds to prove something. (2) Source parts at `Support Street/prototype-studio` and `Gearshift Support Shop/inventory-room`. (3) Build and bench test. (4) Field test at `Hero Field Complex/mobility-track`.
- **Ties into the retest**: the control gauntlet makes the pass natural. **Works even if the secret never comes out.**
- **Reward**: her own control gauntlet, nothing black-market; a smoother Battle Test; Standing +3 (cohesion) if shared.

### "Old Corners" (Shin): his old gang wants him for one job

- **Stages**: (1) A message arrives; Shin goes quiet. (2) Meet at `Kurokawa District/backstreet-crossroads`. The Nine Corners want a lookout for one night; it is a trap, the gang's revenge over Daiki (director-only, reveal ladder step 4). (3) Does he trust anyone at the academy? He can ask a player, Yūto, or go alone. (4) The job: refuse, foil it, or redirect it.
- **End**: the old boss lets him go, or he walks away with the house behind him. A clean record.
- **Reward**: Shin's trust; a Standing hint line from him.

### "Off-Camera" (Sunny): the truth behind her scandal video, and settling things with Ayame

- **Stages**: (1) Sunny deflects any mention of the video. (2) Find the unedited footage (a media archive at `Pulse Media Tower/press-room`, or a recording at `Power Practice Studio/practice-floor`). (3) The truth: she took Ayame's blame (and, later, that a jealous 1A classmate cut and leaked the clip). (4) The conversation with Ayame, in private (`Chikara Academy/north-rooftop-overlook`) or at the Battle Test.
- **End**: Sunny chooses what to do (expose, forgive, or let it go) and Ayame chooses whether to own it.
- **Reward**: a lasting bond; Standing +3 to +5 for good conduct if handled well.

## 9. Standing: how it moves (summary)

Full rubric in `data/ledger.json` (`rubric`). Voyage only sees Standing through NPC hints (Shimazu's warnings, Yūto's remarks), never a meter.

## 10. Time skips

Between milestones, offer an optional "skip to next week" montage with player choices about training, jobs and relationships. **Never force a skip.**

- Offer it in a prompt via an NPC or the Pulse app ("Plan your week").
- The player chooses (training, job, study, house time, rest, relationships). The director sets the next-prompt `Cut:` to the first morning of the next week, using the player's chosen focus.
- A "good week" (+2 Standing) needs attendance and no incident; it is not automatic.
- Do not skip past a scheduled milestone (tournament, exercise, review, deadline).
- A skip never decides a player-character outcome; it summarizes only what the players chose.

## 11. Split scenes

Allowed. Protocol in `split-scenes.md`.

## 12. Hints for Standing (what Voyage may hear)

Shimazu's warnings and Yūto's remarks only (see `hint_bands` in `data/ledger.json` for the bands). At the midterm, Shimazu says 2B is failing no matter the number.

## 13. Obstacle and surprise rules

- One surprise per scene; small most of the time (a note, a delay, a visitor, a malfunction, a stray memory).
- Larger surprises are saved for act turns (the broker's offer, the second collapse).
- Every scene needs a world move, because NPCs are passive.
- Keep obstacles ordinary. Drama comes from people.

## 14. Scene turn budgets

Every scene gets a turn budget, so the arc keeps moving and the player's attention goes where the story is. Based on the Joestar playbook.

**Budgets** (director turns, counted from the first prompt of the scene):

| Scene type | Budget |
|---|---|
| Fights | 4 to 8 turns |
| Big emotional scenes (confessions, splits, verdicts, placement results) | 3 to 6 turns |
| Investigation | 1 to 2 turns |
| Travel and waiting | 0 (cut) |
| Arrival or admin scenes | 2 to 3 turns |

- **Over budget: cut to the next beat.** When a scene runs past its budget, the next prompt's `Cut:` moves to the next beat. Do not wait for a perfect ending; the players can bring a loose thread along.
- **Time skips: offer one at natural lulls.** At the end of a scene, a meal or a night, offer a single skip (one NPC line or a Pulse notice: "skip to ..."). Never force one, never skip past a scheduled milestone, and a skip never decides a player-character outcome (section 10).
- A fight is over when its finisher lands; do not pad it to reach the budget. Budgets are ceilings, not targets.

Act 1 budgets (also noted on each beat in section 4): move-in 3 turns; Mio's first appearance 2 to 3; welcome dinner 3 to 4; Day 2 free day 1 to 2 then a skip; orientation 2 to 3; each Day 4 to 5 scene 1 to 2 (tournament briefing 2 to 3); each tournament bout 4 to 8; placement results and the split 3 to 6. Travel between all of them is 0.
