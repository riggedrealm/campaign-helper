# Studio: when and how to inject world content

Read only when a Studio moment comes up. Voyage's Studio injects world content (NPCs, quests, factions, areas, story starts) from a natural-language request. It costs tokens, cannot export the world, and each request holds about 2000 characters in total, not per field (`studio_limit` in `campaign.json`; longer text is split into batches). So it is occasional, bundled, and applied by the user at a natural break. The director still handles everything else with prompts and the database. ``db.py` is `python3 tools/db.py --campaign luxcellia`.

## When to inject
- **An NPC becomes key**: they recur, the players invest in them, or the Planner ties them to an arc thread.
- **A player thread outgrows one scene** into a side quest, or an arc quest is due.
- **A thin faction** the players stick with.
- **New areas** the story established inside an existing location.
- **Act start**: one bundle with the act's planned NPCs and quests.
- **Story fix (latest turn only)**: see below. Immediate, never bundled or deferred.

Luxcellia: act starts are Days 1, 15, 46 and 76. Bundles: Act 1 (Day 1 or before Day 2): the Mizuho edit and Kazuki Ōhara; Act 3 (after the Wharf raid reveals the Almonry): Archbishop Isamu Tokiwa and a faction touch for the Almonry; any act: a fourth-seat NPC when the player's bond calls for one. Planned NPCs and quests are in `data/cast.json` and `data/quests.json` (status `planned`); Studio-injected ones are flagged `in_studio`.

**Mizuho edit (needed)**: in the world file Mizuho Kaimaku works at Portmaris/Adventurer's Guild Hall. Before her Day 4 beat send `studio-request --edit`: "Update Mizuho Kaimaku: she is the head receptionist at the Adventurer's Guild branch in the Aureliath Guild Quarter, working the main counter." Until it is applied, an unnamed registrar speaks for her in a letter.

Not a reason: a one-off extra, a name used once, anything a prompt line and `add-npc` already covers.

## Story fix (kind `story-fix`)
Studio can edit only the latest turn, so a fix is immediate. At turn-loop review, if Voyage's latest output has a load-bearing slip (a main NPC's identity, a player action decided for them, a secret blurted, a death, a wrong place or time that would carry forward), the reply gives a `story-fix` for that turn FIRST, and the next prompt assumes the fixed version. Write plain world truths of what should have happened (same guidance as `Facts:`: never "correction", never "not X"); never hidden secrets; within the limit, usually one batch. Small slips stay prompt and `Facts:` fixes. Slips found in older turns cannot be Studio-edited: fix them in the fiction (the skill's Retcon section). The `record` payload for that turn summarises the corrected story. `studio-done` logs the fix and, with `--fact KEY`, records each line as canon.

## Edits (flag `--edit`)
Studio can edit entities already in the world (NPCs, quests, factions). For something already there, send an edit with only the changed fields ("Update <name>: ...") instead of re-injecting the whole entity: it is cheaper. Use `db.py studio-request --edit`; batches start "Update <name>:".
- An NPC's situation, role, location or relationships change after a milestone.
- A revealed ladder step changes how an NPC is portrayed (e.g. after a confession).
- A faction's stance toward the players shifts.
- A quest's giver or premise changes in the story.

Never quest progress (Voyage owns it) and never hidden steps. Edits bundle like other requests. `studio-done` on an edit only logs it (an NPC already in the world keeps its `in_studio` flag). `db.py` warns if an edit names an unknown entity, or if a non-edit request names one that exists.

## What never goes in
Hidden ladder steps and secrets: the board's operator and the Almonry before the story shows them, the Lattice and the glass cradles, Serika's null reading and sealed precedents, Rin's copied logs, Yui's fifth anchor, Daigo's buried reading, Toma's anonymous top-ups, Suzuha's engineered engagement, Ren's Earth origin, Yumi's curse, Mizuho's twenty-year case, villain sheets, planned twists. Revealed ladder steps may go in. `studio-request` runs the same hidden-term check as `check-prompt`: strong hits are refused (`--allow` only for public terms), soft hits warn.

## Request formats
Plain natural-language field lines, one per line, modelled on the world data shapes. Give only what the story established; skip fields you would have to invent.

**NPC** (`world-npcs`: name, type, faction, location, basicInfo, visualDescription, personality):
```
Name: ...
Role: (type, e.g. shopkeeper, rival, teacher)
Faction: ... (or none)
Found: (location and area)
About: two or three sentences: what they do, how they treat the players, what they want.
Look: one sentence.
Personality: three or four words.
Voice: tic or catchphrase, how they speak.
```

**Quest** (`quests`: name, giver, location, objectives, success, fail):
```
Name: ...
Giver: ... Found at: (location and area)
Goal: one or two sentences.
Steps: 3 to 5 short steps, in order.
Success: ... Failure: ... (consequences in the fiction, no numbers)
```

**Faction** (`factions`: name, basicInfo, factionType):
```
Name: ...
Type: (major, minor, local)
About: what they do, who leads, how the public sees them, what they want from the players.
```

**Area**: name, the location it belongs to, one or two sentences of look and use, which areas it connects to. **Story start** and **other**: free text, same rules.

## Batching
`studio-request` splits the text itself: blank-line (entity) boundaries first, then lines, then sentences, never mid-word; each batch starts "Batch i/n — <target>: " and fits the limit with that prefix. Several entities share a batch when they fit, so bundle related requests in one file. Over the limit: let it split; do not trim facts to fit.

## Timing
The user applies batches at a natural break (scene end, time skip, act boundary), never mid-scene unless they want to. Bundle to save tokens (never a story-fix): collect pending requests and flag them in one reply line ("Studio: ..."). `resume` shows "Studio: N pending".

## The log flow
1. Draft the text to a file; `db.py studio-request --kind npc|quest|faction|area|story-start|story-fix|other --target NAME --text-file F [--edit] [--why "..."] --turn N` (also a `record` op).
2. `db.py studio` lists what is pending; `db.py studio-show ID [--batch N]` prints batches ready to paste, with character counts.
3. The user pastes the batches into Studio and confirms.
4. `db.py studio-done ID [--batch N] --turn N`. When every batch is applied: `npc` becomes a cast entry flagged `in_studio` (made in play if new; no `intro_line` needed), `quest` becomes active and `in_studio`, `area` runs `add-area` when given `--location` (`--area-id`, `--desc`, `--paths`), `story-fix` is logged, and with `--fact KEY` each line is recorded as a canon fact (`canon` still works as an old alias).
