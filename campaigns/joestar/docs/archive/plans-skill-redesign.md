# Skill redesign: implementation plan (Oct 2026)

Author: Opus (orchestrator), from a planning session with the user on 2026-10-02.
Implementer: a Sonnet agent. Reviewer: Opus. Do not push; Opus reviews and pushes.

## 0. Why this exists
The skill `joestar-campaign-gm` grew into a rulebook of format checks, bookkeeping and "don'ts". It lost sight of its purpose and fights the Voyage engine instead of working with it. The user re-planned it from first principles. Every decision below was made by the user (or accepted from Opus's recommendation) and is final unless marked open.

**Purpose (one line, put it at the top of the skill):** make the Voyage campaign play like it is run by a great human DM. Voyage's AI DM narrates moment to moment; Claude is the director behind it (holds the story, holds the memory, steers each turn with one short prompt). The players should never feel the steering, only a coherent, reactive, exciting story.

## 1. Decisions (with reasons; use the reasons to judge edge cases)

### 1.1 Player profile (what the user enjoys)
- **Spine: fights and relationships.** Every arc builds to a showcase fight and puts a relationship under pressure along the way.
- **Difficulty: earned wins.** Enemies are dangerous and win some early rounds; PCs can always win with good play. Losses cost something; they never end anything.
- **Tone: serious stakes with banter and comedy between.**
- **Fights: puzzle first, spectacle to finish.** Crack the enemy power's rule, then a showcase finisher.
- **Romance: any form (slow burn, active, rivalry), driven by each NPC's personality.** A bold NPC makes moves; a shy one slow-burns.
- **Surprises the user likes: plot twists about the enemies, and crew personal events** (someone's past shows up, someone gets hurt or taken). **No ally betrayals** (a traitor plot was already cut once for this reason).
- **Partnership:** when the user's inputs make a plan, carry it out faithfully and make it interesting with obstacles; never replace it. When the user does not lead, Claude pushes the story. Either way, surprise them regularly.
- **Hard line:** the user controls the PCs; Claude controls the scene, the NPCs and how the world reacts.
- **Living world:** NPCs and factions pursue their own goals and act, not just react.
- **Ensemble crew:** crew members get subplots and big moments, ideally tied back to fights and relationships.

### 1.2 PC pressure (tests the world puts on the PCs; the answers stay the user's)
- Claude never decides a PC's inner journey, feelings, bond or ending. A PC arc is a series of tests, not a planned outcome.
- **Jostin is tested on love and home:** love interests with their own wants pulling at him; threats to Club Lumiere and its people.
- **Jovian is tested on strength and purpose:** rivals and masters who push his limits; situations that ask what he fights for.
- Every arc includes at least one love-or-home test for Jostin and one strength-or-purpose test for Jovian.
- **Backstory:** Claude may invent world-side history (old enemies, family ties, past events). Anything about who the PCs are inside needs the user's OK first.
- **Jostin's violence / Blackstar bloodlust is NOT a chosen theme.** Close the existing thread quietly: one acknowledging scene, then done. Do not build it into a recurring theme. (Blackstar as a power with costs stays; the moral-arc framing goes.)

### 1.3 Story compass
- **Book 1 = Daigo.** Daigo Renjiro is the final boss of Book 1, a tyrant to topple (no sympathetic reveal). Twists come from his captains, their methods and hidden schemes.
- **Two engines:** plot asks "who rules Kobuncho?" (territory, captains, the syndicate's pillars). Emotion asks "what will you risk to protect your own?" (every arc threatens someone the PCs care about).
- **Books 2 and 3 may follow.** Every Book 1 thread resolves by Daigo's fall; a few doors stay open for later, seeded lightly, never as cliffhangers.
- **Kobuncho's ordinary people are background color.** The story stays on the crew and the syndicate.

### 1.4 Working with the Voyage engine (evidence: `world/notes/npcs-and-ai-rules.md` sections A to C, and the `slip` entries in `data/turns.json`)
Findings Opus derived from the data:
- **One beat per turn.** The engine resolves the player inputs, immediate reactions, then stops. Multi-step prompts get cut to one beat. The old rule "a prompt covers 2 to 3 steps" fights this and caused dragging. **New rule: one beat per prompt, and make it count.** Pace comes from cutting dead time, not from cramming.
- **No relocation or time skip unless told.** Hard cuts must be explicit ("Cut to the wharf fence, after midnight."). Time of day is allowed in prompts (user decision t395; remove the stale "No timestamps" exclusion).
- **NPCs are passive by design** (0 to 2 out-of-combat intents, only when a PC engages them). **New rule: every prompt carries a world move**: someone acting on their own agenda (crew doing their task, a villain making a play, a love interest making a move). Even a small one.
- **It adds no new pressure** in calm scenes or after wins. Surprises and twists must be placed by Claude on purpose.
- **Default tone is school slice-of-life.** State the register when the scene is dark ("tense, crime drama") or it softens.
- **It reads prompts literally.** A possibility mentioned tends to happen (a prompt once "pre-failed" Nobu's action and the DM played it). Never state outcomes; describe what NPCs attempt and want. Mention failure only when you want it on the table.
- **The engine rolls combat itself.** The AI only renders results. Prompts never decide hits, injuries or deaths.
- **It keeps its own memory** (NPC records, relationship scores, hidden info, quests, its own arcs and event templates). Do not repeat what it already tracks.
- **Its strengths:** fight rendering, short punchy NPC dialogue, respecting power costs. Give NPCs goals plus one signature line; let it voice the rest.
- **Its actual slips (t327 to t416):** (1) facts and canon, most common: power credited to the wrong person (Eagle Vision to Jovian), wrong gear (camera rig for Kaito Arashima's cable-bow), wrong presence (Rikona voting at a table she wasn't at), Kurokawa called a district; (2) invented details: naming unnamed men, inventing a slam, tying a plate to Daigo's network; (3) writing PC lines, which the user LIKES (policy: never correct it). No logged cases of skipping inputs or running past the stop. **New rule: guard only the facts at risk this turn; drop rules for problems that aren't happening.**
- **700 characters is Voyage's hard limit** (user confirmed). Headerless prompts (from t381) stay.

### 1.5 Prompt format (new)
Lines, in this order, labels included in the 700 count:
1. `Cut:` where and when this beat happens. An explicit relocation or time skip when moving; "Continue at ..." when not.
2. `Tone:` optional; a few words, used when the scene is dark or shifts register.
3. `Crew:` what each present crew NPC wants or is doing; key NPCs get one line matching their voice card; the rest "react in character". Only present NPCs speak.
4. `Facts:` optional; only the facts at risk this turn (who has which power or gear, who is present or absent, name traps), plus any pending corrections.
5. `World:` LAST. The world move, the surprise when one is due, and only the hidden facts Voyage needs for this scene. Last so the user can paste without reading it.
Rules: one beat; every player input is answered (the NPC who answers, the obstacle); branches ("If it works... if it fails...") only for genuinely risky PC actions, failure stakes from the power's stated weakness; never script PCs; never state PC or combat outcomes; NPC non-combat outcomes may be decided; enemy facts conditional and position-free; drift fix = restore only the failing piece in a few words, only when drift is observed.

### 1.6 Director's playbook (scene types)
- **Fights:** puzzle, then spectacle. Beat 1 shows the enemy power causing a problem; next beats let the PCs probe and crack its rule; finish with a showcase move. Enemies telegraph big attacks so wins feel earned. Bosses and lieutenants are puzzles; regular thugs are spectacle fodder (all-puzzle gets tiring).
- **Relationship scenes:** the NPC wants something and makes a move that fits their personality; leave something unresolved to carry forward.
- **Investigation and planning:** one beat at most; a lead points to a place the PCs can go now, never a result "by morning".
- **Banter and downtime:** let it breathe while the players keep going; a world move or two keeps it alive; advance time only when players are done.
- **Finales:** payoff, cost, breather, close. Close an arc over about three turns with a real choice each turn.
- **Scene length by type:** fights about 4 to 8 turns; big emotional scenes about 3 to 6; banter as long as the players keep going; investigation and planning 1 to 2; travel and waiting 0 (cut).
- **Surprises: one per scene, scaled.** Most scenes get a small one (an NPC reveals something, a crew member's past surfaces, an enemy changes tactics); key beats get the big ones (plot twists about the villains).
- **Openings:** start in motion.

### 1.7 Prep
- **Rolling prep:** an arc outline, plus the next scene in detail. (Detailed whole-arc prep breaks when players deviate.)
- **Scene card:** opening shot, world move(s), surprise, key NPC lines, the decision it ends on, the cut out.
- **Villain sheet** (bosses and lieutenants): power as a puzzle: its rule, its tell, its weakness, what sets up the finisher.
- **NPC agendas** for crew, love interests and villains: current want and next move, so they act without waiting.

### 1.8 Spoilers
- The user is both partner and player. **Anything shown to the user outside prompts is structure-only** (arc names, length, scene types, whose tests come up). Twists and villain secrets stay with Claude.
- **Prompts get secrets just in time:** a hidden fact enters a prompt only in the scene where Voyage needs it, and only as much as that scene needs. Voyage needs the truth to play NPCs right, so secrets are not hidden from prompts; they are only delayed.
- **The Story Planner becomes structure-only.** Twists and hidden-fact text live in GM-only files the user does not open (`data/arcs.json` hidden entries).

### 1.9 Process
- **Feedback:** after each scene, one optional question ("Best moment? Anything drag?"). Log answers; update the player profile when a pattern emerges.
- **Saving:** a light save at every scene end (turn log, scene, threads, brief, commit and push). Full sync (Story Planner and public site) only at arc end.
- **Outputs kept:** Story Planner (structure-only) and the public player site. **The tracker artifact retires** (no more `sync.py` in the workflow).

### 1.10 What gets cut
The 2-to-3-steps rule; the tracker sync; rules for problems that aren't happening (skipped inputs, running past the stop, as standing rules); the long checklists (fold into a short director's check); the old violence-arc framing.

## 2. Deliverables

### 2.1 `skill/joestar-director/SKILL.md` (new; the skill source lives in the repo now)
The installed skill is plugin-backed and cannot be edited from a session. The new skill will be saved under a new name, **`joestar-director`**, through a skill proposal card that Opus shows the user after review. Write the full SKILL.md with frontmatter:
```
---
name: joestar-director
description: Direct the Joestar Gang campaign in Voyage as its story and game director: one steering prompt per turn, scene prep, arc planning and light saves to the memory repo. Use for any turn, scene or arc work.
---
```
Keep it lean (aim under 9,000 characters): it is loaded every chat. Sections, in order:
1. **Purpose** (1.0 above, 3 to 4 lines).
2. **Start of a chat:** attach and clone `riggedrealm/voyage-memory` if missing (same steps as the old skill: `add_repo` owner `riggedrealm`, repo `voyage-memory`, access `push`; clone; `git pull`); read `CLAUDE.md`, then `brief.md`, then `world/players.md`. Open other files only when needed. Fresh chat per scene.
3. **Players and PCs:** a 5 to 7 line digest of 1.1 and 1.2; full text in `world/players.md`.
4. **Story compass:** 3 to 4 lines from 1.3.
5. **Working with Voyage:** the engine facts from 1.4 as short bullets; full detail in `world/voyage-engine.md`.
6. **Turn loop:** the user sends story output and player inputs (one message or two). Review the story first (slips: facts, invented details; never correct extra PC lines), then the inputs. Write the prompt only when both are in. Read voice cards in `data/npcs.json` for NPCs who will speak. Assemble with `tools/turn.py` (new flags, see 2.6). Reply: one line on slips if any, the prompt in a blockquote, the character count, a bullet only when the user must decide something. No file writes per turn.
7. **Prompt format:** 1.5 in full.
8. **Director's check** (silent, every prompt, 5 questions): Does it end on a decision the players care about? What win, reveal or laugh do they get? Is there a world move? Whose spotlight or PC test is it, and who has gone without? Is a surprise due this scene?
9. **Playbook:** compact form of 1.6; full text in `world/story-design.md`.
10. **Prep and arcs:** 1.7 in brief; arc planning procedure lives in `world/story-design.md`; approvals shown to the user are structure-only.
11. **Spoilers:** 1.8 in brief.
12. **Scene end:** ask the feedback question; light save (2.7). **Arc end:** retro, full sync.
13. **Canon traps** (keep from the old skill): Kaito Arashima is the archer (cable-bow), Kaito Serizawa is the gym regular, always full names; Kurokawa is the syndicate; "safehouse" means Club Lumiere until one exists; recruiting is owned by Jostin, Reiko keeps discipline, roster and training; Keito Takeda is excluded ("Keito is absent today" if needed); name Shun (engine garbles him as "Saturday"); Nobu has real tech and comms skill; player-declared power unlocks are risky attempts, not facts; party membership needs explicit mutual agreement; NPCs know only what they observed; game turn counter is authoritative from t378; do not develop Daigo directly in Act 2 (he acts through captains, orders and consequences).
Do not copy the old skill's checklists verbatim; this is a rewrite around the purpose.

### 2.2 `world/players.md` (new)
Full text of 1.1 (player profile), 1.2 (PC pressure, backstory rule), 1.8 (spoiler policy), plus an empty `## Feedback log` section with the format `- tNNN scene name: best moment / what dragged / note`.

### 2.3 `world/voyage-engine.md` (new)
Full text of 1.4: each engine behavior with what it means for prompts, the slip history summary with counts and examples (from `data/turns.json` slip entries and `data/canon.json` corrections), and the drift-fix phrases (from `canon.json` `prompt_header`, split into reusable pieces: "Play out each input first." / "Follow rolls strictly; let failure change the advance." / "Stop at a moment players can react to." / "Show only what the crew would notice.").

### 2.4 `world/story-design.md` (rewrite the director's bible)
Keep what still holds from the current file (the audit, arc charter idea, threads diet, endings and hooks, player agency, fail forward, pressure not negation, one clock at a time). Change:
- **Vocabulary:** Turn = one engine beat (one prompt). Scene = a run of turns in one place and situation. Beat card = a scene-sized goal. Arc = one promise, 24 to 36 turns. Remove "Step" and the 2-to-3-steps rule.
- Add **Story compass** (1.3) as the first section after the audit.
- **Arc charter:** add `pc_tests` (at least one Jostin love-or-home test and one Jovian strength-or-purpose test, each a situation, never an outcome), `crew_subplot` (at least one), `villain_sheet` (rule, tell, weakness, finisher setup for the captain), `surprises` (the big twist plus planned crew personal events). Keep promise, budget, villain face by midpoint, three set pieces, twist, three-door climax fork, spotlight plan, choices/echoes, ending (payoff, cost, breather), seeds. Approval summary shown to the user is structure-only.
- Add **Playbook** (1.6) and **Prep** (1.7) sections.
- **Pacing rules:** keep a win every beat, dead ends hand over a better lead now, no two investigation beats in a row, budget governor at 60% and 100%, stall clock (if players idle two prompts the world moves). Replace "a prompt covers 2 to 3 steps" with one beat per prompt plus hard cuts.
- **Director's check:** same 5 questions as the skill.
- **Procedure:** retro, charter (structure-only approval), store beats and hidden facts, rolling prep (next scene card), run, midpoint review, climax and aftermath, save.

### 2.5 `CLAUDE.md` (rewrite, short)
It is the repo authority and must agree with the skill. Point to the skill `joestar-director`, list start-of-chat reads (`brief.md`, `world/players.md`), the turn loop in 3 lines, the new prompt format in 1 line, scene-end light save and arc-end full sync commands, and the file map (`world/players.md`, `world/voyage-engine.md`, `world/story-design.md`). Remove all tracker references. Keep the turn-counter note. Update `README.md` tables the same way (tracker row and `sync.py` row marked retired; planner described as structure-only; new files listed).

### 2.6 `tools/turn.py` (new format)
- Flags: `--cut/-a` (required; keep `-a` as alias so muscle memory works), `--tone/-t`, `--crew/-c` (default "Only NPCs present speak."), `--facts/-f`, `--world/-w` (required: the world move lives here), `-x/--fix` (extra correction; appended to the Facts line), `--skip`, `--header` (opt-in: prepend one or more drift-fix pieces by key, e.g. `--header inputs,stop`; keys map to the pieces in 2.3; store them in `canon.json` as `drift_fixes` object). Remove `--no-header` (headerless is the default); accept and ignore it with a note so old calls don't break.
- Order: Cut, Tone, Crew, Facts, World. Pending corrections from `canon.json` go into the Facts line.
- Count the whole prompt; FAIL at 700 or more.
- Keep: hidden-fact leak check, excluded-name check, PC-named warning, not-present NPC warning. Update checks for the new labels (required: `Cut:` and `World:`; `World:` must be the last line).
- Update the docstring.

### 2.7 Saving (scene end and arc end)
- **Scene end (light):** `tools/store.py` for turn lines, scene, threads, beats, corrections delivered; then `tools/check_data.py`, `tools/build.py`; commit and push. Document this as one chained command in `CLAUDE.md`.
- **Arc end (full):** the light save, plus `tools/planner.py` and republish `planner-out/planner.html` to the Story Planner artifact (https://claude.ai/artifact/8yAasqgRVdd9sXmiAvhLKr), plus `tools/site.py` and push `site-out/.` to `riggedrealm/voyage-site`.
- Retire the tracker: move `tools/sync.py` and `data/sync-manifest.json` to `tools/retired/` (keep for history); remove every workflow mention. Make sure no other tool imports them.

### 2.8 `tools/planner.py` and `tools/planner_template.html` (structure-only)
- Remove hidden-fact text, arc `revisions` text, `captain` names not yet revealed, beat summaries of beats not yet done, and open-decision text that names secrets. Keep: acts, arcs (title, pillar, status, promise, budget vs turns used), beats (name, kind, status, turn budget; done-beat summaries are fine since they happened), pacing (midpoint and budget flags), counts of hidden facts per arc (number only), spotlight and PC-test coverage (who has had a moment, without content), current scene pointer.
- Rule of thumb: if a field could reveal something the players have not seen in play, drop it. Run the same spoiler scan `site.py` uses against the planner output and FAIL the build on a hit (reuse `lib.leaks` or the site scan).
- Update the template so it renders the reduced data without errors.
- Update the docstring: "structure-only; safe for the user to open."

### 2.9 Data changes
- `data/npcs.json`: add an optional `agenda` field `{ "want": "...", "next_move": "..." }` (one sentence each) and fill it for: crew (Haruto Saionji, Nobu Takamine, Hana Kisaragi, Mikoto, Kaito Arashima, Reiko, Yuzuki Hoshino, Ayame Fujinami), love interests (Riko Amane, plus Ayame and Yuzuki already listed), and currently active villains or captains that already have records. Ground every agenda in existing records (`npcs.json`, `profiles.json`, `world/notes/npcs-and-ai-rules.md`, open threads). Do not invent new secrets or plot. A villain agenda must not contain hidden-fact names or keywords (the leak check must pass). Mark each with `"agenda_status": "draft"` for Opus review. Update `data/schema/schema.json`.
- `data/arcs.json`: add the new charter fields (`pc_tests`, `crew_subplot`, `villain_sheet`, `surprises`) to the schema as optional. For `arc-3b` (active) and `arc-4` (planned), leave content empty (`[]` or `{}`); Opus fills them. Do not change arc statuses or beats.
- `tools/check_data.py` / `lib.story_lint`: WARN (not fail) when an active or planned arc lacks `pc_tests` or `villain_sheet`; keep existing lints.
- `data/canon.json`: remove the exclusion "No timestamps in prompts" (stale; time of day is allowed). Add `drift_fixes` (2.6). Replace `prompt_rules` with the rules from 1.5 (short strings). Keep `prompt_header` for history or remove it if nothing reads it after 2.6 (check `site.py`, `build.py`, `lib.py`).
- `data/threads.json`: "Jostin's violence" thread: set priority low and change its text to say it closes after one acknowledging scene (per 1.2). Do not delete it.
- `tools/build.py` (`brief.md`): drop "No timestamps" naturally via canon; add a short "Agendas" section listing present NPCs' `next_move`; keep the rest.

### 2.10 Leave alone
- `auto/` (stale engine reference), `world/notes/`, `world/canon.md`, `world/road-to-daigo.md`, `data/profiles.json`, `portraits/`.
- Story content in `arcs.json` beats and hidden facts.
- The missing turns t417 to about t440 are NOT in scope (the user must supply the story text).
- `REDESIGN.md`: add one line at the top: "Superseded by plans/skill-redesign.md (Oct 2026)."

## 3. Verification (must all pass before reporting done)
1. `python3 tools/check_data.py` runs clean (warnings allowed only for the new optional charter fields and the existing thread count).
2. `python3 tools/build.py` succeeds; `brief.md` has no "No timestamps" line and shows an Agendas section.
3. `python3 tools/turn.py -a "Cut test" -c "Haruto checks the exits." -w "Nobu's drone pings a second car."` prints the prompt in order Cut, Crew, Facts (if pending corrections), World, with a count, exit 0. A 700+ prompt exits 1. A prompt naming a still-locked hidden name exits 1. Use an Arc 4 name such as "Kiriyama" (unlocks at 4-2), since 3b-5 is active and Okabe may already count as unlocked (check `lib.reached`).
4. `python3 tools/planner.py` succeeds; grep the output for every hidden-fact name and keyword from `arcs.json` that is not yet unlocked: zero hits.
5. `python3 tools/site.py` still succeeds.
6. `grep -rn "sync.py\|tracker" CLAUDE.md README.md skill/ world/story-design.md` returns nothing except the retired note in README.
7. `skill/joestar-director/SKILL.md` is under 9,000 characters (`wc -c`), has valid frontmatter, and mentions none of: "2 to 3 steps", "tracker", "No timestamps".
8. Commit locally on `main` with message `Skill redesign: joestar-director, engine-aware prompts, structure-only planner` (include the session's Co-Authored-By trailer lines if provided). **Do not push.**

## 4. Report back
List every file changed or added, the verification results (pass/fail per item), anything you could not do and why, and any judgement calls you made that the plan did not cover.
