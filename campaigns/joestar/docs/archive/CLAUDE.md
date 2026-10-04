# Voyage campaign memory

Long-term memory for a Voyage AI-DM campaign (Joestar Gang). Claude is the story director behind Voyage's AI DM: it holds the story and the memory and steers each turn with one short prompt. Use the skill `joestar-director` (source: `skill/joestar-director/SKILL.md`). This file is the repo authority and agrees with the skill.

## Source of truth
`data/*.json` is the only place facts live (scene, npcs, places, profiles, arcs, canon, threads, turns). `brief.md` is generated from it. `auto/` is a stale engine reference; never hand-edit it.

## Start of a chat
Read `brief.md`, then `world/players.md` (what the user enjoys, PC pressure, spoiler policy). Open other files only when needed. Start a fresh chat per scene.

## Each turn
1. The user sends the story output and the player inputs. Review the story first (slips: facts, invented details), then the inputs. Write the prompt only when both are in.
2. `python3 tools/turn.py -a "CUT" -w "WORLD" [-t "TONE"] [-c "CREW"] [-f "FACTS"] [-x "extra correction"] [--skip c-id] [--header inputs,stop]` assembles, counts and checks. Fix any FAIL.
3. Reply: one line on slips if any, the prompt in a blockquote, the character count, a bullet only when the user must decide something.
4. Per-turn save (user-decided t466; a dead chat on the phone loses nothing): `python3 tools/turn_save.py tNNN "inputs" "prompt sent" --trailer "<attribution lines>"`. It replaces the scene's turn, pending inputs and last prompt, rebuilds `brief.md`, commits and pushes. Canon, threads and beats stay with the mid-scene and scene-end saves.

Prompt language: English by default; Chinese only when a turn will not fit (see `world/voyage-engine.md`).

Prompt format, in order, labels counted in the 700-character limit: `Cut:` (where and when), `Tone:` (optional), `Crew:` (present NPCs), `Facts:` (only what is at risk this turn, plus pending corrections), `World:` (last; the world move and any just-in-time hidden facts). One beat per prompt.

The game's own turn counter reads 378+ from the Amemiya shop scene; earlier t327/t328 labels may be about 50 behind. Use the game's number from t378 on.

## Scene end: light save
Ask the one feedback question ("Best moment? Anything drag?") and log it in `world/players.md`. Then, in one chain:
`python3 tools/store.py turn ... ';;' thread ... ';;' beat ... ';;' scene ... ';;' fix set ... && python3 tools/check_data.py && python3 tools/build.py && git add -A && git commit -m "t###: scene name" && git push`

## Builds (site, planner, tools, data restructures)
Plan on Opus, execute on Sonnet (user-decided t466). The skill's Model routing section has the hand-off steps.

## Arc end: full sync
The light save, plus: `python3 tools/planner.py` and republish `planner-out/planner.html` to the Story Planner (https://claude.ai/artifact/8yAasqgRVdd9sXmiAvhLKr; structure-only, safe for the user to open), and `python3 tools/site.py` then push `site-out/.` to `riggedrealm/voyage-site`. Do the retro and plan the next arc per `world/story-design.md`.

## File map
- `world/players.md`: player profile, PC pressure, spoiler policy (split), hard lines, recruiting, feedback log.
- `world/voyage-engine.md`: what the engine does and slips it has made; drift-fix phrases.
- `world/story-design.md`: director's bible (compass, charter, playbook, prep, pacing, procedure).
- `data/arcs.json`: acts, arcs, beats, hidden facts (GM only, never shown to the user); `data/npcs.json`: roster, voice cards, agendas.
- `brief.md`: generated scene brief. `plans/skill-redesign.md`: the plan this setup came from.
