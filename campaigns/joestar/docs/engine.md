# Working with the Voyage engine (Joestar)

Moved from voyage-memory `world/voyage-engine.md`; the verbatim original is `docs/archive/voyage-engine.md`. **Changes at migration (template wins):** the prompt limit is **840** characters (it was 700; `db.py state` prints it; `check-prompt` fails above it); prompts are checked by `check-prompt`, not `tools/turn.py`; drift fixes are written by hand (the `--header` flag is gone); the standing facts are in `data/canon.json` and `campaign.json` `canon_traps`. Evidence: `docs/archive/notes-npcs-and-ai-rules.md` (the engine's own instructions), the `slip:` entries in `data/history.json` (t327 to t416) and the corrections in `data/canon.json` (subjects `correction (...)`, with slip counts).

Evidence: `world/notes/npcs-and-ai-rules.md` sections A to C (the engine's own instructions), the `slip` entries in `data/turns.json` (t327 to t416) and the corrections in `data/canon.json`. The skill `joestar-director` carries the short version; this file has the detail.

## What the engine does, and what it means for a prompt
| Engine behavior | What the prompt does about it |
|---|---|
| **One beat per turn.** It resolves the player inputs and the immediate reactions, then stops. A multi-step prompt is cut to one beat. The old "2 to 3 steps per prompt" rule fought this and caused dragging. | One beat per prompt, and make it count. Pace comes from cutting dead time, not from cramming steps. |
| **No relocation or time skip unless told.** | Make hard cuts explicit on the `Cut:` line ("Cut to the wharf fence, after midnight."). Time of day is allowed (user decision, t395). Use "Continue at ..." when staying. |
| **NPCs are passive by design:** 0 to 2 out-of-combat intents, and only when a PC engages them and there is urgency. | Every prompt carries a world move: someone acts on their own agenda (crew doing their task, a villain making a play, a love interest making a move). Even a small one. Agendas live in `data/npcs.json` (`agenda`). |
| **It adds no new pressure** in calm scenes or after wins ("no stakes inflation in mundane beats"). | Place surprises and twists on purpose. If the scene is calm, the world move is what keeps it alive. |
| **Default tone is school slice-of-life** (warm cel-shaded anime). The campaign is Kobuncho crime. | State the register when a scene is dark ("Tone: tense, crime drama") or it softens. |
| **It reads prompts literally.** A mentioned possibility tends to happen. A prompt once "pre-failed" Nobu's loop and the DM played the failure. | Never state outcomes; describe what NPCs attempt and want. Mention failure only when you want it on the table. |
| **It rolls combat itself.** The AI only renders Combat Results and must not decide hits, injuries or deaths. | Prompts say what is attempted, never the result. Do not decide hits, injuries or deaths. |
| **It keeps its own memory:** NPC records, relationship scores, hidden info, quests, its own arcs and event templates. | Do not repeat what it already tracks. Give goals and one signature line; send only what it lacks. |
| **Knowledge firewall:** NPCs know only what they observed; reputation and ties are tracked separately; party membership needs explicit mutual agreement; abilities unlock only when tested in play. | Establish witnesses and channels. Treat declared power unlocks as risky attempts. Never assume someone has joined. |
| **Player agency is absolute:** it narrates only what is in the payload. | Prompts do not script PCs. Extra PC lines it writes anyway are accepted (the user likes them). |
| **Strengths:** fight rendering, short punchy NPC dialogue, respecting power costs. | Give NPCs goals plus one signature line from the voice card; let it voice the rest. Use power weaknesses as failure stakes. |
| **Voyage's hard limit was 700 characters per prompt (user confirmed); the template raised it to 840** (`state.settings.prompt_limit`). Headerless prompts from t381 stay. | Labels count toward the limit. `check-prompt` fails above 840 and warns within 10 characters. |

## Prompt language (user-decided t466)
English by default. Chinese only when a turn will not fit in the prompt limit (now 840) in English; with the larger limit this should be rare. In a Chinese prompt, names, labels (`Cut:`, `Crew:` ...) and quoted signature lines stay in English, and the prompt includes "Narrate in English". `check-prompt` counts characters, so a Chinese character counts as one.

## Slip history (t327 to t416)
11 entries in `data/turns.json` carry `"slip": true`. By type, most common first:

1. **Facts and canon (7 entries, about 9 incidents).** Power credited to the wrong person (Eagle Vision to Jovian, t327 Kagero); wrong gear (a camera rig for Kaito Arashima, whose gear is a cable-bow, t378); wrong presence (Kaito on the second floor; Yuzuki saying nobody saw Noa taken; Rikona voting at the Lumiere table when she is not crew and was not there); wrong state (the beaten man walking away when he was left cold on the pavement; Sayaka saying "two bodies" when all three lived); wrong label (Jostin "enrolled-adjacent"; Kurokawa called a district).
2. **Invented details (2 entries, 3 incidents; both entries also carry a fact slip above).** The plate tied to Daigo's finance network (t328); naming the unnamed men (Matsumoto, Kazuya Oka) and inventing a cut-off slam (t412 to t414).
3. **Writing PC lines and actions (4 entries, t327; `c-pc-lines` counts 6).** The user likes these. Policy: never correct them; still correct wrong facts.

No logged cases of skipping inputs or running past the stop. So the rule is: **guard only the facts at risk this turn** (`Facts:` line); do not carry standing rules for problems that are not happening.

Corrections by status are in `data/canon.json` (subject `correction (<status>, <n> slips)`; the same traps run in the LIVE CHECKLIST from `campaign.json` `canon_traps`). Put a trap on the `Facts:` line only when it is at risk this turn.

## Drift-fix phrases
Used only when drift is observed, and only the failing piece, a few words. They were split from the old standard header (retired from `canon.json`: "Play out each player's input first; follow any roll strictly, and let failure change or block the advance. Then advance as below, stop, and end on a moment players can react to. Scene facts are hidden; show only what the crew would notice."). Stored in `data/canon.json` as facts with subject `drift fix: ...`; write the phrase into the prompt by hand (the old `turn.py --header` flag is retired).
- `inputs`: "Play out each input first."
- `rolls`: "Follow rolls strictly; let failure change the advance."
- `stop`: "Stop at a moment players can react to."
- `notice`: "Show only what the crew would notice."
- t466 speaker labels: after the first Chinese-language prompt, Rei's lines were labelled SOMEONE. Cause unknown (Voyage's own helper blamed its narrator metadata). Drift fix if it recurs: `Label Rei's lines REI ICHINOSE.`; if it persists, go back to English. Chinese prompts (633 characters) were otherwise accepted and the narration stayed in English when the prompt said so; the engine used an English sample line verbatim.


## Engine rules and old prompt rules (canon.json `engine_rules`, `prompt_rules`)
Engine rules (also facts `engine rule 1..7` in `data/canon.json`):
1. The engine simulates combat and rolls; the AI only renders results.
2. One beat per turn; only the PC actions in the payload.
3. NPCs know only what they saw; fame and reputation are tracked separately.
4. Party membership needs explicit mutual agreement.
5. Abilities unlock only when tested in play.
6. Default tone is school slice-of-life; state the darker crime tone.
7. Known slips: garbles Shun as 'Saturday', places the party in 'Shutter Alley', says the crew squats at Lumiere.

Old prompt rules (voyage-memory `canon.json` `prompt_rules`) and their landing:
1. Under 700 characters including labels, counted by tools/turn.py.
2. Lines in order: Cut:, Tone: (optional), Crew:, Facts: (optional), World: last.
3. One beat per prompt; every player input is answered.
4. Cut: state where and when explicitly when moving; 'Continue at ...' when not. Time of day is allowed.
5. Every prompt has a world move in World: someone acting on their own agenda.
6. Never script PCs or state PC or combat outcomes; NPC non-combat outcomes may be decided.
7. Branches only for genuinely risky PC actions, with failure stakes from the power's weakness.
8. Enemy facts conditional and position-free; hidden facts only as far as this scene needs.
9. Facts: only the facts at risk this turn, plus pending corrections.
10. Write the prompt only after BOTH the story output and the new player inputs are in (user, t327).

Disposition: rule 1 is superseded (840, template); rules 2 to 9 are the template's prompt format, turn loop and fight rules (same content; the old 'branches only for risky PC actions, with failure stakes from the power's weakness' lives on in `docs/rules.md`); rule 10 (write the prompt only after both the story output and the new inputs are in) is the template's turn loop (the paste carries both).

## Slips by campaign phase (standing guidance)
Guard only the facts at risk this turn (`Facts:`); do not carry standing rules for problems that are not happening. Name traps are in `campaign.json` `canon_traps`: Kaito Arashima vs Kaito Serizawa, Kurokawa is a syndicate, Keito Takeda excluded, Shun garbled as 'Saturday', "Safehouse" means Club Lumiere (the gym storage-room shelter is the working HQ), Multiple Daigos/Renjis.
