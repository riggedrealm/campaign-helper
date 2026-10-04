# Story design procedure (director's bible), Joestar

Moved from voyage-memory `world/story-design.md` (verbatim original: `docs/archive/story-design.md`). It is the planning authority for charters, beat cards, prep and pacing. **Where this file differs from the director template (`.claude/skills/joestar-director/SKILL.md`), the template wins:** prompt limit 840 (not 700); `commit-turn` commits every turn and pushes every 5; the template's scene-over-budget rule (cut to the next beat on a quiet input; the old "flag fights, emotional scenes, romance and banter once instead of cutting" is retired); hard noes stay in the fiction; Studio and fight rules from the template. References to `data/arcs.json`, `data/npcs.json`, `tools/store.py`, `tools/planner.py`, `tools/check_data.py` and `tools/site.py` now mean: the arc design is `arc-bible.md` (plus `cast.json`, `threads.json`, `quests.json`), updates go through `db.py`, and the planner and site are pending port (README).

Goal: make the campaign play like it is run by a great human DM. Voyage's AI DM narrates moment to moment; Claude is the director behind it. Every plan, scene and prompt is judged by one question: **will the players enjoy this turn, and does it end on a decision they care about?**
This file is the planning authority. `arc-bible.md` holds the plans; the README `Players` section holds what the players enjoy; `docs/engine.md` holds what the engine can and cannot do; the skill `joestar-director` holds the per-turn loop.

## Why this exists (audit, t438)
- Arcs ran far too long: Enforcement about 55 game turns, Hostess File about 80 (with downtime), Follow the Money about 60. Players complained about pacing.
- Obstacles outnumbered wins. Leads went cold repeatedly (lost phone, tagged van, decoy folders), so effort felt wasted.
- Endings were treated as trailers. Each finale was bolted to the next hook, so arcs never landed.
- 21 threads were open at once; most had no payoff beat.
- Villains stayed off-screen until the last scene, so the final fight had no history.
- Prompts packed 2 to 3 steps into an engine that plays one beat, so scenes dragged and the extra steps were cut anyway.

## 1. Story compass
- **Book 1 is Daigo.** Daigo Renjiro is the final boss of Book 1: a tyrant to topple, with no sympathetic reveal. Twists come from his captains, their methods and their hidden schemes.
- **Two engines.** Plot asks "who rules Kobuncho?" (territory, captains, the syndicate's pillars). Emotion asks "what will you risk to protect your own?" (every arc threatens someone the PCs care about).
- **Books 2 and 3 may follow.** Every Book 1 thread resolves by Daigo's fall; a few doors stay open for later, seeded lightly, never as cliffhangers.
- **Kobuncho's ordinary people are background color.** The story stays on the crew and the syndicate.

## 2. Vocabulary
- **Turn**: one engine beat, one prompt.
- **Scene**: a run of turns in one place and situation.
- **Beat card**: a scene-sized goal in `data/arcs.json`, about 4 to 7 game turns.
- **Arc**: one promise, 24 to 36 game turns.
- **Fork**: a choice with different consequences. Not a skill check.

## 3. The Arc Charter (written before the arc starts, approved by the user)
Stored in `data/arcs.json` on the arc object. Required fields:
1. **promise**: one sentence the players can state ("Break Finance").
2. **budget_turns** and **start_turn**: the pacing budget (24 to 36).
3. **villain_face**: what the captain wants, how they pressure the crew, and the scene where they first meet the PCs (by the midpoint, never first at the finale).
4. **villain_sheet** (captain, and lieutenants): the power as a puzzle: `rule`, `tell`, `weakness`, `finisher_setup` (what the crew's cracked rule sets up).
5. **set_pieces**: three distinct set-piece types, different from the previous arc (fight, chase, infiltration, social duel, heist, build-and-defend, mystery).
6. **twist** and **surprises**: the big twist near the midpoint (it changes the goal, not just delays it, and it is about the enemy), plus planned crew personal events (someone's past shows up, someone gets hurt or taken). Never an ally betrayal.
7. **pc_tests**: at least one Jostin love-or-home test and one Jovian strength-or-purpose test. Each is a situation, never an outcome.
8. **crew_subplot**: at least one, ideally tied back to a fight or a relationship.
9. **climax_fork**: at least three doors (obvious, clever, wildcard). Every door ends the arc.
10. **spotlight_plan**: each PC gets two signature moments tied to their powers; each key crew member gets one scene.
11. **choices / echoes**: the earlier player choices this arc calls back to.
12. **ending**: payoff, cost, breather. No cliffhanger.
13. **seeds**: at most one planted name or object for later.
14. **recruit_seat**: one first-wave seat from the org chart (`canon.json` org) offered as this arc's recruit opportunity, in priority order. The candidate is Claude's secret and must be earned.
15. **shared**: true once the user has approved the direction fields. Write premise, set_pieces, crew_subplot, choices (the choice only), ending, seeds and recruit_seat free of twist content: the Story Planner shows them to the user. Arcs chartered before t466 stay unshared.

The approval summary (user-decided t466, split): the user sees and approves premise, promise, budget, pillar, set pieces, crew subplot, climax choices (the kinds of choice, not the fork doors), ending shape, seeds and the recruit seat; PC tests by category only. The twist, surprises, villain face and sheet, and fork doors stay with Claude. Check the twist and surprises against the hard lines in `world/players.md`.

## 4. Beat cards
Each beat in `arcs.json` carries: `kind` (hook, investigate, action, social, twist, prep, climax, aftermath), `goal`, `win` (what the players visibly gain), `fork` (the choice inside the beat), `fail_forward` (what happens if they fail: the story advances with a cost), `turns` (budget).

## 5. Playbook (scene types)
- **Fights: puzzle, then spectacle.** Beat 1 shows the enemy power causing a problem; the next beats let the PCs probe and crack its rule; finish with a showcase move. Enemies telegraph big attacks so wins feel earned, and win some early rounds. Bosses and lieutenants are puzzles; regular thugs are spectacle fodder (all-puzzle gets tiring).
- **Relationship scenes:** the NPC wants something and makes a move that fits their personality (bold NPCs make moves, shy ones slow-burn). Leave something unresolved to carry forward.
- **Investigation and planning:** one beat at most. A lead points to a place the PCs can go now, never a result "by morning".
- **Banter and downtime:** let it breathe while the players keep going; a world move or two keeps it alive; advance time only when the players are done.
- **Finales:** payoff, cost, breather, close. Close an arc over about three turns with a real choice each turn.
- **Scene length by type (in turns):** fights 4 to 8; big emotional scenes 3 to 6; banter as long as the players keep going; investigation and planning 1 to 2; travel and waiting 0 (cut).
- **Surprises: one per scene, scaled.** Most scenes get a small one (an NPC reveals something, a crew member's past surfaces, an enemy changes tactics); key beats get the big ones (plot twists about the villains).
- **Openings:** start in motion.

## 6. Prep
- **Rolling prep:** an arc outline, plus the next scene in detail. Detailed whole-arc prep breaks when players deviate.
- **Scene card:** opening shot, world move(s), surprise, key NPC lines, the decision it ends on, the cut out.
- **Villain sheet** (bosses and lieutenants): the power as a puzzle: rule, tell, weakness, what sets up the finisher.
- **NPC agendas** (crew, love interests, villains) in `data/npcs.json`: current want and next move, so they act without waiting. Update them at scene end.

## 7. Pacing rules
1. **One beat per prompt.** The engine plays one beat per turn. Pace comes from hard cuts (explicit relocation or time skip on the `Cut:` line) and from cutting dead time, not from packing steps.
2. **A win every beat.** Every beat ends with a visible win or a reversal. Never end a beat on a flat obstacle.
3. **No two investigation beats in a row**, and information is loot, not a gate. Clues come from doing something fun (a fight, a con, a chase).
4. **Dead ends hand over a better lead now.** A closed lead gives a new concrete lead in the same scene. Never two cold leads in a row.
5. **Pressure, not negation.** A complication adds a cost, a clock or a choice. It never deletes an asset the players earned (a lost phone is negation; a rival bidding for the phone is pressure). Fail forward: failure advances the story with a cost.
6. **Budget governor.** At 60% of the budget run a midpoint review. At 100% the arc must be in its finale. If over budget, cut non-essential beats and jump to the next one; do not extend.
   **Scene over budget (user-decided t466; the template's rule now applies):** over budget or goal met, a quiet input gets a `Cut:` to the next beat and `scene-end`; inputs that start something new keep normal pacing. (Old text: fights, emotional scenes, romance and banter were only flagged once; retired. If the user says stay, a longer budget is set with a new scene.)
7. **Stall clock.** If players idle for two prompts, the world moves (an NPC acts, a lead arrives). Never repeat the same obstacle.
8. **One clock at a time**, real and actionable. No invented deadlines the players cannot act on.
9. **Pulse check.** When the user mentions pace or fun, note it in the arc `retro`, then compress the remaining beats.

## 8. Player agency
- Every beat contains one fork whose result is felt later. Log it in the arc `choices` list with its echo.
- Each new beat opens with at least one echo of a past choice (a name, a consequence, a face). The world remembers.
- Rule on every player request: reasonable plans and declared facts are carried out faithfully (obstacles on risky actions); partly reasonable ones get a cost or limit; unreasonable ones (instant fixes, canon or power breaks, free allies or powers) become quests, limited opportunities or an in-fiction no. Never replace a reasonable plan. Wishes are logged on the Wishlist in `world/players.md` with a ruling.
- NPC outcomes are cheap and decided in the prompt (NPCs roll nothing). Spend risk only on PC actions that are really uncertain.

## 9. Spotlight and variety
- Keep a spotlight table per arc. Check it at the midpoint: any PC or key crew member with no moment gets one in the next two beats.
- Match fun to powers: use Eagle Vision, Shadow Step, Aftershock, Blackstar (a power with costs), the Soul Forms and each crew skill on purpose, not by accident.
- Vary set pieces across arcs.

## 10. Endings and hooks
1. **Climax**: the players choose among doors; the prompt names the fork and never the pick.
2. **Aftermath**: payoff (what changed), cost (what it cost them) and a breather (1 to 3 turns of crew moments). Then close the arc.
3. **Hooks are earned**, never default. A hook is allowed only if it grows from something the players did, is a concrete person, place or object they can act on, and carries no made-up deadline. Otherwise end the arc cleanly.
4. **The next arc begins with an inciting event in its own first scene**, after the breather, not as the previous arc's last line.
5. **Act transitions**: the consequence of an arc (the pressure curve) shows in the world; it is not a threat to be tacked on.

## 11. Threads diet
- Max 8 open player-visible threads, and every thread names an arc and a payoff beat (or is tagged background).
- At each arc end close, merge or park everything without a payoff. `check_data.py` warns above 10.

## 12. The Director's check (silent, before every prompt)
1. Does it end on a decision the players care about?
2. What win, reveal or laugh do they get this turn?
3. Is there a world move?
4. Whose spotlight or PC test is it, and who has gone without?
5. Is a surprise due this scene?
If two answers are weak, rewrite the beat before writing the prompt.

## 13. Procedure
1. **Retro** the finished arc (turns vs budget, best moment, complaints) in `arcs.json` `retro`; read the feedback log in `world/players.md`.
2. **Charter** the next arc (section 3); show the user the structure-only summary. Wait for approval.
3. **Store** the beats as cards, hidden facts with unlock beats (names stay locked until their beat), the villain sheet and surprises.
4. **Rolling prep:** write the next scene card; update NPC agendas.
5. **Run** turns with the Director's check. Prompts stay conditional so they survive deviation.
6. **Midpoint review** at 60% of the budget.
7. **Climax and aftermath** per section 10.
8. **Save:** light save at every scene end; full sync at arc end (see `CLAUDE.md`).
