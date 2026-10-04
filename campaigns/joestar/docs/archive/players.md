# Players and PCs (what the user enjoys; how the PCs are tested)

Authority for the skill `joestar-director`. Summarised in the skill; this is the full text. Update the profile only when a pattern shows up in the feedback log.

## Player profile
- **Spine: fights and relationships.** Every arc builds to a showcase fight and puts a relationship under pressure along the way.
- **Difficulty: earned wins.** Enemies are dangerous and win some early rounds; the PCs can always win with good play. Losses cost something; they never end anything.
- **Tone: serious stakes with banter and comedy between.**
- **Fights: puzzle first, spectacle to finish.** Crack the enemy power's rule, then a showcase finisher.
- **Romance: any form (slow burn, active, rivalry), driven by each NPC's personality.** A bold NPC makes moves; a shy one slow-burns.
- **Surprises the user likes:** plot twists about the enemies, and crew personal events (someone's past shows up, someone gets hurt or taken). **No ally betrayals** (a traitor plot was already cut once for this reason).
- **Partnership:** Claude rules on every player request instead of granting it by default. Reasonable plans and facts (they fit canon, powers, stakes and power level) are carried out faithfully with obstacles where risky; partly reasonable ones are accepted with a cost or limit; unreasonable ones (instant fixes, canon or power breaks, free allies or powers) become quests, limited opportunities or an in-fiction no, never mocked. When the user does not lead, Claude pushes the story. Either way, surprise them regularly.
- **Hard line:** the user controls the PCs; Claude controls the scene, the NPCs and how the world reacts.
- **Living world:** NPCs and factions pursue their own goals and act, not just react. (User t472: if the players do not act on an open lead or clock, let the event move and let them face the consequences; pressure, not negation.)
- **Ensemble crew:** crew members get subplots and big moments, ideally tied back to fights and relationships.
- **Extra AI-written PC lines:** the user likes them. Never correct them (still correct wrong facts).

## PC pressure (tests the world puts on the PCs; the answers stay the user's)
- Claude never decides a PC's inner journey, feelings, bond or ending. A PC arc is a series of tests, not a planned outcome.
- **Jostin is tested on love and home:** love interests with their own wants pulling at him; threats to Club Lumiere and its people.
- **Jovian is tested on strength and purpose:** rivals and masters who push his limits; situations that ask what he fights for.
- Every arc includes at least one love-or-home test for Jostin and one strength-or-purpose test for Jovian (`pc_tests` in the charter; each is a situation, never an outcome).
- **Backstory:** Claude may invent world-side history (old enemies, family ties, past events). Anything about who the PCs are inside needs the user's OK first.
- **Jostin's violence / Blackstar bloodlust is not a chosen theme.** Close the existing thread quietly: one acknowledging scene, then done. Do not build it into a recurring theme. Blackstar stays a power with costs; the moral-arc framing is gone.

## Spoiler policy (user-decided t466: split)
- **The user sets the direction; Claude keeps the twists.** At charter approval the user sees and approves: premise, promise, budget, pillar, set pieces, crew subplot, climax choices, ending shape, seeds and the recruit seat. Claude keeps: the twist, the villain sheet, the surprises and who the villain's face is. PC tests are shown by category only ("Jostin: love or home"), never the situation.
- The user vetoes content by principle through the hard lines below; every twist is checked against them.
- **Prompts get secrets just in time:** a hidden fact enters a prompt only in the scene where Voyage needs it, and only as much as that scene needs. `tools/turn.py` blocks locked names and keywords.
- **The Story Planner shows the approved direction fields** and nothing from Claude's list. Twists and hidden-fact text live in GM-only data (`data/arcs.json` hidden entries, charter fields `twist`, `villain_face`, `villain_sheet`, `surprises`, `climax_fork`).

## Hard lines (never, unless the user says otherwise)
- No ally betrayals.
- No cliffhanger tails at arc ends.
- No invented deadlines the players cannot act on.
- No death of a named crew member or love interest without the user's OK.
- No relationship decided off-screen.

## Recruiting (user-decided t466)
- Recruiting is split by arm (user, t474; was Jostin's alone): Jovian's call for Spearhead seats (Aether, Phantom heads), Jostin's call for Hearth seats (HearthOps, Arcanum). The Aether Head recruit seat is therefore Jovian's. Each arc charter names one first-wave seat (`recruit_seat`) as the recruit opportunity, in priority order (Aether Head first). The user sees the seat; Claude keeps who the candidate is.
- The candidate is earned (a quest, a test or a cost), never a free ally. A Jostin search that misses becomes a lead to a candidate, never a dead end.
- No recurring named Kobuncho locals for now; HearthOps scenes deal with the shop-owner alliance as a group.

## Wishlist (player wishes, each with the director's ruling)
- t442 Jostin: a spatial-magic user (teleportation) for Hearth, linking the HQ, Lumiere and the other bases. RULING: unreasonable as an instant wish (it trivialises travel and infiltration). Only as a rare, limited recruit quest later: short range, fixed anchor points, a real cost.
- t441 Jostin: recruit one of the teachers (his call; recruiting is Jostin's).
- t442 Jostin: the gym bomb shelter is a SECRET headquarters; Principal Anya need not know. RULING: reasonable (a nap-spot find). Secrecy on school grounds is a risky action, so it can be tested.

## Feedback log
Ask one optional question after each scene ("Best moment? Anything drag?"). Log the answer here.
Format: `- tNNN scene name: best moment / what dragged / note`
- t437 Harumi Wharf finale (Arc 3b): best moment: the emotional hook at Tetsu Gym when collectors threatened Ayame and Jostin got angry (a love-or-home test landing as a fight) / dragged: the whole Finance arc (about 60 turns), leads going cold, the invented 'a week' hook / note: no cliffhanger tails; players want their own choice to matter (the ledger handed to Haruto).
- t442 note: user wants the director to judge whether each player request is reasonable, not cater to every wish.
- t461 note: when anything mentioned might or might not be canon, the director checks the repo before writing the prompt (t460 miss: the safehouse fund is Yuji's raid cash, 70% locked with Haruto; Vault money is the crew's and Rei has no reach over it).
- t466 note: pacing pulse check. The gym HQ and Rei audit ran t459 to t466; user flagged stalling. Director rules: scene budget counter, obstacle ledger, one resolving beat. Compress the remaining beats of Arc 4 (story-design section 7, rule 9).
