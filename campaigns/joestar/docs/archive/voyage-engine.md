# Working with the Voyage engine

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
| **Voyage's hard limit is 700 characters per prompt** (user confirmed). Headerless prompts from t381 stay. | Labels count. `tools/turn.py` fails at 700 or more. |

## Prompt language (user-decided t466)
English by default. Chinese only when a turn will not fit in 700 characters in English. In a Chinese prompt, names, labels (`Cut:`, `Crew:` ...) and quoted signature lines stay in English, and the prompt includes "Narrate in English". `turn.py` counts characters, so a Chinese character counts as one.

## Slip history (t327 to t416)
11 entries in `data/turns.json` carry `"slip": true`. By type, most common first:

1. **Facts and canon (7 entries, about 9 incidents).** Power credited to the wrong person (Eagle Vision to Jovian, t327 Kagero); wrong gear (a camera rig for Kaito Arashima, whose gear is a cable-bow, t378); wrong presence (Kaito on the second floor; Yuzuki saying nobody saw Noa taken; Rikona voting at the Lumiere table when she is not crew and was not there); wrong state (the beaten man walking away when he was left cold on the pavement; Sayaka saying "two bodies" when all three lived); wrong label (Jostin "enrolled-adjacent"; Kurokawa called a district).
2. **Invented details (2 entries, 3 incidents; both entries also carry a fact slip above).** The plate tied to Daigo's finance network (t328); naming the unnamed men (Matsumoto, Kazuya Oka) and inventing a cut-off slam (t412 to t414).
3. **Writing PC lines and actions (4 entries, t327; `c-pc-lines` counts 6).** The user likes these. Policy: never correct them; still correct wrong facts.

No logged cases of skipping inputs or running past the stop. So the rule is: **guard only the facts at risk this turn** (`Facts:` line); do not carry standing rules for problems that are not happening.

Corrections by status are in `data/canon.json` (`corrections`); pending ones are added to the `Facts:` line by `tools/turn.py`.

## Drift-fix phrases
Used only when drift is observed, and only the failing piece, a few words. They were split from the old standard header (retired from `canon.json`: "Play out each player's input first; follow any roll strictly, and let failure change or block the advance. Then advance as below, stop, and end on a moment players can react to. Scene facts are hidden; show only what the crew would notice."). Stored in `canon.json` as `drift_fixes`; `tools/turn.py --header inputs,stop` prepends them.
- `inputs`: "Play out each input first."
- `rolls`: "Follow rolls strictly; let failure change the advance."
- `stop`: "Stop at a moment players can react to."
- `notice`: "Show only what the crew would notice."
- t466 speaker labels: after the first Chinese-language prompt, Rei's lines were labelled SOMEONE. Cause unknown (Voyage's own helper blamed its narrator metadata). Drift fix if it recurs: `Label Rei's lines REI ICHINOSE.`; if it persists, go back to English. Chinese prompts (633 characters) were otherwise accepted and the narration stayed in English when the prompt said so; the engine used an English sample line verbatim.
