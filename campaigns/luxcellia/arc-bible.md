# Luxcellia: The Fifth Hero's Party: Arc Bible

Director-only. Everything here is final design. Prompts carry only the sliver a scene needs. Read it by section with `db.py bible` (`bible 3`, `bible act2`, `bible budgets`); never whole.

Machine-readable copies of the cast (including the villain sheets below), quests and reveal ladders live in `data/` and are queried with `db.py`; this file keeps the narrative design. If the two ever disagree, the design here wins and `data/` should be corrected before play.

The arc planner (`docs/arc-planning.md`) writes act pitches and arc charters against these acts. Charters may deviate from them; each deviation is logged and shown on the Arc Planner page. The acts stay the default spine.

Section titles `Time skips`, `Obstacle and surprise rules` and `Scene turn budgets` are looked up by the skill (`bible time skips`, `bible surprise rules`, `bible budgets`): keep those words in the headings. Act headings keep the form `Act N: Name (Days a to b)` so `bible actN` works.

## 1. Premise and stakes

The kingdom of Crownveil summoned four heroes and got five. Court Mage Serika Amamiya read the fifth as a misfire, paid them 25 gold and sent them out a side door. The player is that fifth summon: the crystal read nothing, and the power behind their ribs runs on principles Luxcellia's instruments were never built to detect. Voyage runs the world and all mechanics; the director steers story.

The arc turns a discarded stranger into the Fifth Hero's party. In Aureliath the Guild's head receptionist, Mizuho Kaimaku, has noticed that solo, talented adventurers with no family are taking jobs from a private posting board that bypasses her counter, and two have not come back. The player fits the profile exactly; the board recruits them. By choosing who to stand with (Yumi Aokiba, Ren Tsukishiro, Toma Kirisawa, and a fourth seat left open), the player turns a recruiting trap into a family. The arc ends in the throne room where they were discarded, with a party beside them and Princess Suzuha's offer on the table. Nothing ends the game; the party is the reward.

Stakes the players can feel:

- A person: Kazuki, the friendly stranger in the Guild queue who takes the board's job and does not come back; then whoever the board takes next, possibly a companion.
- A family: the party itself. Each companion carries a secret that a wrong word could break and that standing together can mend (Yumi's curse, Ren's second chance, Toma's secret top-ups).
- A name: the player's reputation. The Crown called them a misfire; becoming visible makes every faction want or fear them, and the first Reborn-classified adventurer will be known to all.

### Scope and players

- Built for **one player character** (single-player playtest). Assume nothing about their power or background; the sheet comes from the user. Chain quest 2's text assumes a dimensional-boundary power: treat that loosely; the sheet decides.
- About 100 days (14 weeks). **Day 1 is a Monday** (also `start_weekday` in campaign.json); Weekday of Day N: N mod 7 = 1 Mon, 2 Tue, 3 Wed, 4 Thu, 5 Fri, 6 Sat, 0 Sun. Mondays are Days 1, 8, 15, ...
- Start: `Aureliath/royal-palace` (the story start "Summoned and Discarded"). The player has no home: they lodge in the Guild Quarter or the Market District (Voyage names the inn; add the area with `add-area` once the story shows it). Rooms do not apply; there is no room claim. The four heroes live in the palace.
- Party seats: Yumi, Ren and Toma (a guest member who sneaks out) are the candidates; the fourth seat is deliberately open (see Party rules below). Joining needs explicit mutual agreement, always; Suzuha never joins without it.
- The player is a palace-discarded zero: public NPCs treat them as the misfire until Voyage shows the power surface.

### Tone

Premium isekai fantasy in novel form: dramatic, indulgent, sincere, trope-forward. Scene mix: party life and bonds about 40 percent (meals, campfires, banter, NPC-to-NPC chemistry), mystery and investigation 25, action 25, palace politics 10. The Party and Bonds game mode drives it: every companion has a relationship with every other, not only with the player; every extended rest includes a meaningful party moment (the campfire rule); once per arc a campfire truth.

- Fights are **puzzle first** (crack the enemy's rule), **spectacle to finish**, and they punish solo play: the party that covers for each other wins.
- **Earned wins.** Enemies are dangerous, but the player can always win with good play. Losses have story consequences (a companion asleep in glass, a lead lost) but never end anything.
- The director never states player-character or combat outcomes; Voyage rolls combat and decides every number.

### Party rules (Party and Bonds)

- **Mutual agreement.** A companion joins only when the player and the NPC both say so in the fiction. A job done together is not a recruitment. Offers can be declined; they stay friends and appear as rivals, patrons or hosts.
- **Bond firsts** (the director lets them happen, Voyage tracks them): first shared meal (Day 9); first admitted fear; first honest argument; first covered retreat (rift break, Day 20); first secret shared (Ren, Day 27); first campfire truth (Yumi, about Day 31; the signature scene, once per arc, no later than Day 88); first laugh at the same joke.
- **NPC-to-NPC chemistry matters**: Yumi sees Ren's seams; Ren plays for Toma; Toma feeds Yumi's customers; Mizuho grades Rin; Daigo shouts at Yui and Yui steers him. Every companion's thread gets table time; spotlight is the companions (`db.py spotlight`).
- **Fourth seat.** Left open on purpose. Whoever the player bonds with in play fills it: Kazuki (if rescued), Mizuho (partner, not a recruit), Rin, Daigo or Yui (a hero stepping out of the palace), or a director-created NPC injected through Studio. Never fill it for them.
- **Toma** attends as a guest: he sneaks out of the palace for outings, joins on explicit agreement, and the palace does not know until Day 34.
- **Heroes at the palace** (Rin, Daigo, Yui) appear in palace and joint-op scenes; they leave only on a joint op or a personal beat. **Suzuha** is a palace contact with a market hour; not a party member.

### Venue substitutes (no invented places)

The world has no named inn, joint-op safehouse or Almonry, so existing locations and areas stand in. Check each with `db.py loc`. Add areas with `add-area` only after the story shows them.

| Need | Stand-in |
|---|---|
| Guild registration, counter, queue | `Aureliath/guild-quarter` |
| Yumi's spell cart | `Aureliath/market-district` (and `noble-quarter` on business days) |
| Ren's galas and the palace gala | `Aureliath/noble-quarter`, `Aureliath/palace-gardens` (`Roseglass Ballroom` optional) |
| Lodging | `Aureliath/guild-quarter` or `market-district` (add an area: an inn) |
| First shared job | `Aureliath/riverside-wharf` |
| Rift break | `The Forgotten Aqueducts/junction-chamber` (a second wave at `Aureliath/outer-districts`) |
| Palace scenes (heroes, Toma's explanation, the offer) | `Aureliath/royal-palace`, `Aureliath/council-wing` |
| Hero training | `Knight's Tournament Grounds/training-yards`, `Royal Summoning Annex/training-yard` |
| Serika's lab and the circle | `Royal Summoning Annex/research-laboratory`, `summoning-chamber` |
| Yui's archive hunting | `Silver Crescent Academy/library-tower`, `Royal Summoning Annex` |
| The board's drop | `Aureliath/riverside-wharf` |
| The Almonry and Lattice | `Aureliath/temple-district` (add the area `almonry` once the story shows it; the Lattice is beneath it) |
| Campfire scenes | outdoors: `Aureliath/riverside-wharf`, `palace-gardens`; or the cart in the market |
| Throne room | `Aureliath/royal-palace` |

## 2. Hidden state

- **The board and its operator.** The private posting board is run by the Church of the First Light's Almonry in `Aureliath/temple-district`. Its operator is **Archbishop Isamu Tokiwa, "the Almoner"** (director-created; kind, devout, certain). The board recruits solo, talented, no-family adventurers (Reborn, null-reading, anomalous), because nobody asks where they went. The Almoner "recalibrates" them: binds them in glass cradles in the Lattice beneath the Almonry, alive and asleep, to hold a prophesied convergence from forming. This is the same keeping that sealed Serika's two precedents and took Mizuho's party twenty years ago. It is a centuries-old script, not the whole Church; High Priestess Shirayuki suspects, Inquisitor Genma's archive requests circle the same file, and neither appears unless the story reaches them. Why this operator: it is the only hidden-info thread that unites recruitment by profile (Reborn and null readings), the sealed recalibrations, Church possessiveness toward the Reborn and Summoned, and the Guild-bypassing board; Thorne's network is legal harassment, Souen's is political, neither recruits.
- **Mizuho**: her old party was recruited through the same board twenty years ago; a friend sealed a door so she could escape and was taken. She is rebuilding the case off the books and has begun wearing the second dagger.
- **Serika**: the crystal returned a null value with no category; she chose "misfire". Her spies exist to learn whether she is watching a third null; she knows of two Church-sealed precedents (both summonings of five; both fifth readings reported as zero by court mages later struck). She is deciding whether to certify the null reading as real. If cornered with proof, she offers a private alliance with honest strings.
- **Rin**: copied the measurement logs before the Court sealed them. Two oaths. **Yui**: a fifth anchor chiseled over, with marks older than this summoning; a ledger of Court inconsistencies. **Daigo**: his reading was the second-lowest of the four and buried; his debt is paid in person. **Toma**: anonymous Guild bounty top-ups near the player; his count of five matches Yui's anchor.
- **Suzuha**: the marriage shortlist has narrowed to two names; one house funds border provocations to make the alliance look urgent; her evidence runs through her maids.
- **Ren**: Reborn from Earth, told no one; his unperformed song is an Earth melody; the masked attendant at his galas is the board's scout. **Yumi**: her emotion-reading is her mother's curse (she feels all but her own); her mother fled the board's recruitment twenty years ago; an old glyph of hers has resurfaced in a noble scandal tied to House Souen's records.
- **The player**: the fifth summon in a summoning of five, exactly the profile of the two earlier nulls. Queen Celestine has read the file and is letting the heroes' investigation run.
- **Relationship values** are Voyage's. The director does not track numbers. A personal quest unlocks when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed).
- Reveal ladders for all of these are in `data/threads.json`; the human-readable spoiler map is this section.

## 3. Pacing at a glance

| Act | Days | Showcase fight | Relationship under pressure |
|---|---|---|---|
| 1 Severance | 1 to 14 | The first shared job at the Wharf, Day 7 | Player and the first two companions (Yumi, Ren) |
| 2 Bonds | 15 to 45 | The rift break, Day 20 | Ren's secret and Toma's secret: the party and the palace |
| 3 The Vanished | 46 to 75 | The Wharf drop raid with the hero party, Day 60 | Mizuho's case and a companion's quest (Ren, Yumi) |
| 4 Vindication | 76 to 100 | The Almoner at the Almonry, Day 90 | The whole party, and Serika's choice |

Keep the act day ranges in step with `acts` in `campaign.json` (`db.py time` moves the act with the day). Chain quests (Voyage-owned): 1 at the start, 2 at the rift break (Day 20), 3 at the throne (Day 97).

## 4. Act 1: Severance (Days 1 to 14)

**Purpose**: Turn a discarded stranger into someone with a first job, a first friend and a first meal. Introduce Yumi and Ren, make the private board's slip visible, and form the party's first two seats by mutual agreement. End with a party that has eaten together and a receptionist who has warned them about a posting that did not come through her counter.

**Quests**: Chain quest 1, "Summoned and Discarded: Severance and a Side Door" (Voyage grants it at the start; never seed it). "The Quiet Posting" (main, giver: Mizuho Kaimaku), seeded Day 4 to 5, one new seed per turn.

**Beats** (one per turn; a beat can take several turns if the player lingers; each beat has a turn budget, see Scene turn budgets):

1. **Day 1.** *Budget: 2 turns (turns 2 to 3).* The palace side door and the downhill walk to the Guild Quarter (see `opening.md`). Toma slips them a wrapped snack and a pointing finger toward the Guild; Rin looks at the floor. Arrival and admin: cut the walk.
2. **Day 1, evening.** *Budget: 1 to 2 turns.* First night: a lodging in the Guild Quarter; the tavern's posting board and queue gossip. Offer the skip to Day 2.
3. **Day 2.** *Budget: 2 turns.* Registration: the queue, the form, the rank, the unnamed registrar. Kazuki Ōhara, an F-Rank orphan, shares a meat bun and a first-contract worry (intro line once; Studio-inject him at the Act 1 bundle).
4. **Day 2 to 3.** *Budget: 2 turns.* Choosing a first contract at the counter (Voyage's quest 1 ends when the player accepts one; never choose for them). One ordinary posting is on the board; the world move is a posting that did not come through the counter.
5. **Day 3.** *Budget: 2 turns.* The Market District: Yumi's spell cart. The player is the one person she cannot read; she sells them a small charm and says it feels like walking into a quiet room. The masked attendant, a gentle courier in grey, slips the player a private posting; Yumi remarks that the courier feels like nothing. One new NPC per turn.
6. **Day 4.** *Budget: 2 turns.* Mizuho arrives in the Guild Quarter (after the Studio edit; until then an unnamed registrar speaks for her in a letter). She reads the player in one glance, files them under "watch", warns against any posting not stamped at her counter without saying why. Seed "The Quiet Posting".
7. **Day 5.** *Budget: 2 turns.* A Guild celebration: Ren performs. His charm fails on the player; his set list drifts toward their taste; a masked figure stands at the back where sightlines converge.
8. **Day 6.** *Budget: 1 to 2 turns.* Toma in the market "for ingredients", snacks for one more than present.
9. **Day 7: showcase.** *Budget: 4 to 6 turns.* The first shared job (see below). Companions join only on explicit mutual agreement; if the player goes alone it is a solo job and the companions meet them after.
10. **Day 8 to 9.** *Budget: 3 turns.* The first meal together at Yumi's cart (campfire rule). Bond first: first shared meal.
11. **Day 10 to 12.** *Budget: 3 to 4 turns.* The party question: who asks whom. Yumi asks plainly or is asked; Ren drifts in with a joke and the same question; Toma attends as a guest when he can. The fourth seat is mentioned and left empty.
12. **Day 14.** Act retro (`feedback --kind act`).

### Showcase fight: the Wharf job (Day 7)

- **Venue**: `Aureliath/riverside-wharf`.
- **Format**: the player with Yumi and/or Ren (if they have agreed) against a nest of Riftlight eels under a pier.
- **Opponents**: each built from a rule: a power with a visible tell and an exploitable limit.

| Field | Detail |
|---|---|
| Role | Riftlight eel nest (low-rank Guild job) |
| Power rule | The eels strike from the water at anything within about three metres of the pier edge; they cannot leave the water. |
| Tell | The water goes still and bright a beat before they strike. |
| Weakness | Keep to the pier's middle or use a line; fire and glyphs crack the bright patch. |
| Finisher setup | The pier's net winch: a hoisted net on a counterweight scoops the nest out. |
| Behavior | Strike the loudest first; retreat when the winch drops. |
| If it goes badly | A lost day and a soaked pier; the contract stays open, nobody dies. |

**Feeding the puzzle within the prompt limit** (840, see `db.py state`): put the rule on a `Facts:` line, show the tell in a `World:` beat, leave the weakness to be discovered. Do not state results; Voyage rolls combat.

### Act 1 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Admin and registration queues | A clerk misreads the rank column and the room goes quiet |
| Coin: 25 gold is not much | An unclaimed meat bun lands on the player's table |
| Nobody knows the player | A merchant recognizes the side door |
| Yumi cannot read the player | Her glyph on a wheel hub flickers when the player passes |
| Ren's charm fails | A string snaps mid-song for no reason |
| The private board | A posting appears on the counter that Mizuho did not stamp |

## 5. Act 2: Bonds (Days 15 to 45)

**Purpose**: Make the party matter. The power surfaces, each companion's secret meets the player, the Crown starts watching, and the midpoint takes someone the player knew. End with a party that has lost a friend and knows the board is real.

**Beats** (one per turn unless noted):

1. **Day 15 to 19.** *Budget: 2 to 3 turns, then offer a skip.* Party routine: jobs, cart, lodging. Day 17: Suzuha's market hour; she stumbles into the party at Yumi's cart and her disdain fails. A hero-sighting: Rin at dawn training, a bow to a dummy.
2. **Day 20: showcase.** *Budget: 4 to 8 turns.* The rift break (see below). Chain quest 2 begins (Voyage's); the power surfaces. Bond first: first covered retreat. If it spills to the Outer Districts and the Royal Knights see it, Rin and Toma arrive and Rin stands beside the player first.
3. **Day 22.** *Budget: 2 to 3 turns.* Serika's verification team arrives (unnamed Court observers) to confiscate a supposed artifact; there is none. Crisis for her system.
4. **Day 27.** *Budget: 3 to 6 turns.* A palace gala (Ren's invitation brings the party). Ren plays an Earth melody; Yui hums the chorus; Ren freezes. First secret shared: the song's name, in private afterward.
5. **Day 31.** *Budget: 3 to 4 turns.* Yumi's curse cracks around the player after a bad day: one unmediated feeling and her forensic narration fails. First campfire truth if the player is close to her.
6. **Day 34.** *Budget: 3 to 6 turns.* Toma's top-ups surface at the palace; he answers the Court honestly, and the party can stand beside him. The palace now knows he leaves the grounds.
7. **Day 38 to 40: midpoint.** *Budget: 3 to 6 turns.* Kazuki takes the board's job (a bigger rank, a plausible patron) and does not come back. Mizuho counts him on a list of two. Offer a skip to the Day 45 retro only after the scene lands.
8. **Day 45.** Act retro.

### Showcase fight: the rift break (Day 20)

- **Venue**: `The Forgotten Aqueducts/junction-chamber`; a second wave at `Aureliath/outer-districts`.
- **Format**: the party (the player plus whichever companions agreed) against rift-born "seam-wraiths". Voyage runs the player's power; the sheet decides it.
- **Opponents**: a rift's creatures that flicker between two points.

| Field | Detail |
|---|---|
| Role | Seam-wraiths (rift-born, flickering) |
| Power rule | Each wraith blinks between its seam and a point up to ten metres away every other beat; it can only strike right after it arrives. |
| Tell | The air folds like paper a beat before it blinks. |
| Weakness | They must return to the same seam every third blink; whoever holds the seam shut pins them. |
| Finisher setup | The junction chamber's central seam: when it is shut the wraiths dissolve into Riftlight at once. |
| Behavior | Pick off the ranged member first; retreat through the seam when it narrows. |
| If it goes badly | The seam widens; a Guild team is cut off; the cost is a rescue mission, not a death. |

### Act 2 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Party schedules (the palace, the cart, the galas) | A note arrives by sparrow in three different hands |
| Serika's observers | An observer's pen runs dry mid-notation |
| Toma sneaking out | A palace guard tails him at a distance and bows when spotted |
| Ren's secret | The gala musicians fall silent when he tunes |
| Yumi's old client | An enchanted lantern burns green in her cart |
| The board's offers | The same grey courier appears at the next stall |
| Mizuho's counter | A paper crane sits on the player's stamped contract |

## 6. Act 3: The Vanished (Days 46 to 75)

**Purpose**: Reopen the case. The party learns what happened to the vanished and who runs the board, the hero party joins, and a companion's personal quest collides with the main thread. End with the Almonry named and the party committed.

**Beats**:

1. **Day 46 to 48.** *Budget: 2 turns, then offer a skip.* Mizuho's counter after Kazuki's disappearance; the dawn spar, first light, no witnesses (quest "First Light, No Witnesses"). She tells the half-truth she can.
2. **Day 49 to 52.** *Budget: 1 to 2 turns per scene.* Investigation: Kazuki's lodging, a meat-bun stall, the grey courier's route. Yumi senses the courier's calm as the same kind of nothing as her mother's old letters.
3. **Day 53.** *Budget: 3 to 5 turns.* Daigo pays his debt in person: he finds the party at a job (an Outer Districts Riftlight spill) and fights beside them at full weight, loud and apologetic.
4. **Day 55 to 58.** *Budget: 3 to 4 turns.* Yui and Toma compare counts; Rin and Daigo have their first honest conversation about the logs and the buried number: the heroes stop being the Court's assets and start being the fifth summon's search party. A campfire at the palace gardens if the party is invited.
5. **Day 60: showcase.** *Budget: 4 to 8 turns.* The first joint op: the hero party and Mizuho raid the board's drop at the Wharf (see below).
6. **Day 62 to 66.** *Budget: 2 turns each.* Serika feels out an alliance; if cornered with proof she offers a private one with honest strings. A Studio bundle: the Almoner NPC (after the Wharf raid reveals the Almonry).
7. **Day 68.** *Budget: 3 to 6 turns.* A companion's personal quest collides with the main thread: the attendant offers Ren a private commission; or Yumi's mother's trail leads to the Almonry.
8. **Day 70 to 74.** The Almonry is named (Temple District). The party commits.
9. **Day 75.** Act retro.

### Showcase fight: the Wharf drop raid (Day 60)

- **Venue**: `Aureliath/riverside-wharf`, at night in rain.
- **Format**: the party with Rin, Yui, Toma and Daigo (a joint op) and Mizuho against the board's attendants. The hero party's joining is a story choice: they come if asked; they leave the palace without orders.
- **Opponents**: the masked attendant and a handful of grey-clad couriers (background, no powers).

#### Villain sheet: the Masked Attendant (the board's scout)

| Field | Detail |
|---|---|
| Role | The board's courier and scout; a gentle attendant of the Almonry, not a mage |
| Power rule | Ring-kit: a closed ring of chalk about three metres across that dampens abilities inside it; one ring per fight, laid with both hands and a full breath. |
| Tell | The attendant stops moving and lifts the lantern half a second before closing a ring. |
| Weakness | Any scuff of the chalk breaks the ring; cut the lantern and the ring dies. |
| Finisher setup | The Wharf's tarred pilings and the rain: chalk smears, the lantern gutters. |
| Behavior | Offers tea and a posting; if cornered lays the ring and retreats along the wharf; never kills. |
| If it goes badly | The drop moves; the party keeps only a posting and a trail. |

**Feeding the puzzle within the prompt limit** (840): rule on `Facts:`, tell in `World:`, weakness discovered; never state outcomes.

### Act 3 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| The hero party must come and go from the palace | A guard shuts a gate by one second |
| Mizuho's reluctance | She leaves a second dagger on the counter and takes it back |
| Companion friction (jealousy about who is trusted on point) | Daigo says the first honest thing he has said all week |
| The board's quiet | The courier's route is exactly the same on a different day |
| Serika's observers | A junior mage sketches the player's footprints |
| The case's old paperwork | A Guild file with half its pages cut out |

## 7. Act 4: Vindication (Days 76 to 100)

**Purpose**: The climax act. The party gets the case, faces the operator, and answers the Crown as one. End with the sleepers waking and the throne room's question answered by a party, not a lone zero.

**Beats**:

1. **Day 76 to 78.** *Budget: 2 turns.* Suzuha asks for a deniable outsider; her maids are at risk; she needs evidence taken without house allegiance. She sets her market hour.
2. **Day 79 to 86.** *Budget: 2 to 3 turns each.* Preparation: Serika decides (testimony, certification, or private alliance); Yui authenticates the Almonry's records; Mizuho names the friend who sealed the door; the party plans.
3. **Day 88: the campfire truth.** *Budget: 3 to 6 turns.* The night before; a campfire in the palace gardens or the wharf. Once per arc someone says the thing they have carried. This is the signature scene.
4. **Day 90: showcase.** *Budget: 4 to 8 turns.* The Almoner at the Almonry (see below).
5. **Day 91 to 96.** *Budget: 3 to 6 turns.* Aftermath: the sleepers wake; Kazuki; Mizuho's friend; Yumi's mother's trail; Serika's statement.
6. **Day 97.** *Budget: 3 to 6 turns.* The throne room: chain quest 3 (Voyage's). Suzuha makes the private offer; the player answers with the party beside them; Serika must accept her system is incomplete or double down.
7. **Day 98 to 100.** Epilogue (`feedback --kind act`); the sandbox opens.

### Showcase fight: the Almoner (Day 90)

- **Venue**: `Aureliath/temple-district`: the Almonry's glass-roofed reliquary hall above the Lattice.
- **Format**: the party against the Almoner and his attendants; won by covering for each other. Voyage runs everything.
- **Opponents**: Archbishop Isamu Tokiwa. He is kind to the end.

#### Villain sheet: Archbishop Isamu Tokiwa "the Almoner" (board operator)

| Field | Detail |
|---|---|
| Role | Archbishop and Almoner of the Temple District's Almonry; runs the private posting board; keeper of the Lattice |
| Power rule | **Lantern-script rings.** His staff-lantern draws a closed ring of sealing script, about six metres across; anyone inside has their abilities and will pressed down to the reference value of the Church's instruments (blank). Up to three rings at once; rings seal only what is inside. The player's power, being null, slips a ring only at a cost; it cannot protect the companions. |
| Tell | The lantern flame turns from gold to white a breath before the closing stroke; chalk dust falls from his sleeve. |
| Weakness | A ring needs one unbroken line: a foot, a blade or a thrown plate that scuffs it from outside breaks it. All rings share one lantern; break line of sight to the flame and they drop. The script holds only in lantern-light. |
| Finisher setup | The glass roof above the Lattice: break the lens so daylight floods the hall and every ring dies at once; the glass cradles hum and open. |
| Behavior | Opens with parley and an offer of rest ("a weary traveler"); seals the strongest first (the companions, then a hero); taunts with the zero; flees down the Lattice stairs if the lantern breaks. |
| If it goes badly | He seals one companion in a cradle (alive, rescuable); the sleepers stay asleep; the Almonry shuts its doors. Never a death. |

**Feeding the puzzle within the prompt limit** (840): put the rule on a `Facts:` line ("a ring of chalk and light holds whatever stands inside it; a scuffed line breaks it"), show the tell in a `World:` beat, leave the weakness and the roof to be discovered. Never state who is sealed or whether a ring cracks.

### Final review and endings

When and where: Day 97 in the throne room (`Aureliath/royal-palace`), after the Almonry's fall. No hidden score; endings follow choices and who stands beside the player.

| Ending | How it is decided (by choices, never by the director's mood) | Closing scene |
|---|---|---|
| **The Fifth Hero's Party** | The player answers Suzuha's offer with at least two companions beside them and one hero (Rin or Daigo or Yui) standing with them | The throne room, the party in a line; Serika certifies the null reading; the Crown opens the Reborn classification; a table with five plates. |
| **A Name Alone** | The player answers with no or one companion beside them | The throne room, a lone figure and a long hall; the offer is accepted with strings; a companion's cart or seat waits outside. |
| **The Quiet Refusal** | The player declines the offer | Suzuha honors it and sends a market sweet; the party leaves by the front gate, not the side door. |
| **The Cradle Remains** | The Almoner was not stopped, or a companion stayed in glass | The throne scene is delayed; a rescue arc opens; the party's hall is a vigil. |

Name the ending in the scene from a character's voice; never read it as a score.

### After any ending: sandbox

The game continues as a sandbox. Open threads by ending:
- **The Fifth Hero's Party**: the Church's wider keeping, Yumi's mother, Ren's song, Toma's discipline, the Reborn classification's first applicants, Shinji Souen's ledger.
- **A Name Alone / Quiet Refusal**: companions' threads stay open; the board's remnants; Suzuha's shortlist; the Guild's next posting.
- **The Cradle Remains**: the rescue arc.

### Act 4 obstacles and surprises

| Obstacle | Small surprise (one per scene) |
|---|---|
| Serika's hesitation | She recalibrates the nearest instrument in front of the party |
| The hero party's leave from the palace | The Queen's seal is on a pass nobody applied for |
| Mizuho's old wound | Her second dagger is already sharpened |
| The Almoner's patience | A pot of tea waits on a stone table |
| Time pressure | Tolling temple bells run an hour early |
| The throne room | The side door is left open, then closed |

## 8. Personal quests

Each unlocks for the player when the story has shown **real closeness** with that NPC (shared secrets, time together, a moment that landed). Full triggers, objectives and seed lines are in `data/quests.json` (`python3 tools/db.py --campaign luxcellia quest <name>`).

### "Door of Her Own" (Yumi): find her mother, lift the curse, get ahead of the resurfaced glyph

- **Stages**: (1) See what the curse does to her. (2) The resurfaced glyph and House Souen's records. (3) Her mother's trail (the Almonry, the board). (4) The choice: lift it or keep it.
- **Collision (Act 3)**: the board's calm couriers match her mother's old letters.
- **Reward**: the fox and her cart permanently in the party; a feeling she names herself.

### "The Unperformed Song" (Ren): finish a song written for no audience

- **Stages**: (1) Hear it half-finished. (2) Meet the person who recognized it. (3) The masked attendant's requests. (4) Play it where it can be heard.
- **Collision (Act 3)**: the attendant offers Ren a private commission (the board's recruitment).
- **Reward**: the first honest opinion; the song's last bar.

### "A Seat Saved" (Toma): stand with him when the Court asks him to explain

- **Stages**: (1) Learn what he has been doing. (2) The palace (Day 34). (3) Compare the count with Yui. (4) Make room at the table.
- **Reward**: the shield for the party's exposed side; the meal.

### "First Light, No Witnesses" (Mizuho): the spar and the case

- **Stages**: (1) Dig up the record. (2) Spar at first light. (3) Hear what the incident was. (4) Take the case together.
- **Reward**: a partner and the fiercest guardian angel in the Guild.

Other threads (Rin's two oaths, Daigo's debt, Yui's fifth anchor, Suzuha's engagement, Serika's signature) are ladders in `data/threads.json` and appear in joint scenes; they are not separate journal quests unless the player takes one up.

## 9. Time skips

Between milestones, offer an optional "skip to next week" montage with player choices about jobs, training and relationships. **Never force a skip.**

- Offer it in a prompt via an NPC (Yumi at the cart, Mizuho at the counter) or a posting ("Plan your week").
- The player chooses (a Guild job, training, the cart, the palace, rest, relationships). The director sets the next-prompt `Cut:` to the first morning of the next week, using the player's chosen focus.
- Do not skip past a scheduled milestone (the rift break, the gala, Toma's explanation, Kazuki's job, the raid, the throne room).
- A skip never decides a player-character outcome; it summarizes only what the players chose.

## 10. Split scenes

Single player, one party; no split party. A companion's scene without the player is not played: it is reported by an NPC. `split-scenes.md` stays for reference only.

## 11. Obstacle and surprise rules

- One surprise per scene; small most of the time (a note, a delay, a visitor, a malfunction, a stray memory).
- Larger surprises are saved for act turns (the rift break, the gala, Kazuki's job, the Wharf raid).
- Every scene needs a world move, because NPCs are passive.
- Keep obstacles ordinary. Drama comes from people.

## 12. Scene turn budgets

Every scene gets a turn budget, so the arc keeps moving and the player's attention goes where the story is.

**Budgets** (director turns, counted from the first prompt of the scene):

| Scene type | Budget |
|---|---|
| Fights | 4 to 8 turns |
| Big emotional scenes (confessions, campfire truths, verdicts, the palace) | 3 to 6 turns |
| Investigation | 1 to 2 turns |
| Travel and waiting | 0 (cut) |
| Arrival, admin, registration, errand scenes | 2 turns at most |

- **Over budget, or goal met: cut to the next beat.** When a scene runs past its budget, or its goal is met even under budget and the input is quiet, the next prompt's `Cut:` moves to the next beat. Do not wait for a perfect ending; the players can bring a loose thread along.
- **Time skips: offer one at natural lulls.** At the end of a scene, a meal or a night, offer a single skip. Never force one, never skip past a scheduled milestone, and a skip never decides a player-character outcome (see Time skips).
- A fight is over when its finisher lands; do not pad it to reach the budget. Budgets are ceilings, not targets.

Per-act notes (also on each beat above): Act 1: palace exit 2, first night 1 to 2, registration 2, contract 2, cart 2, Mizuho 2, celebration 2, Wharf job 4 to 6, first meal 3, party question 3 to 4. Act 2: rift break 4 to 8, observers 2 to 3, gala 3 to 6, curse 3 to 4, palace explanation 3 to 6, Kazuki's job 3 to 6. Act 3: spar 2, investigation 1 to 2 per scene, Daigo 3 to 5, the heroes compare 3 to 4, Wharf raid 4 to 8, collision 3 to 6. Act 4: Suzuha 2, preparation 2 to 3, campfire 3 to 6, Almonry 4 to 8, aftermath 3 to 6, throne 3 to 6.
