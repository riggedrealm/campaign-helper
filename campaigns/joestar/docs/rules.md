# The old joestar-director skill: every rule and where it landed

Source: voyage-memory `skill/joestar-director/SKILL.md` (14,187 bytes; verbatim copy `archive/old-joestar-director-SKILL.md`). The new skill is the director template plus a small fill block (15,000-byte ceiling), so campaign rules live here, in the README `Players` section, in `arc-bible.md`, in `data/canon.json` and in `campaign.json` `canon_traps` (which `prep` prints in its LIVE CHECKLIST). **Where an old rule differed from the template, the template won.**

## Kept Joestar-specific rules (read when a case comes up)
- **Check before denying or asserting canon.** Before assembling a prompt, check the repo for anything mentioned that might or might not be canon (funds, names, places, past events, rules): `canon <topic>`, `npc`, `history <words>`, `thread`, `loc`, `lore`. Never assume or deny it from memory; search the whole database (not one or two files) before saying something is not on file (user note t461).
- **Branches only for genuinely risky PC actions,** with failure stakes taken from the power's weakness (Peach strain, Soul Burn, Blackstar spill); safe actions get no branch. NPC non-combat outcomes may be decided in the prompt (NPCs roll nothing); spend risk only on PC actions that are really uncertain.
- **Answer every player input** (the NPC who answers, the obstacle) after ruling whether each request is reasonable (README "Ruling player requests").
- **Enemy facts are conditional and position-free** (template Fights rule covers the conditionals).
- **Drift fix:** when drift is observed, restore only the failing piece in a few words (`canon` facts `drift fix: inputs|rolls|stop|notice`, `docs/engine.md`).
- **PC tests, never PC outcomes:** Jostin on love and home, Jovian on strength and purpose; backstory about who the PCs are inside needs the user's OK; Jostin's Blackstar violence closes after one acknowledging scene.
- **Obstacle ledger:** list the complications already used in this scene before adding one; never repeat one; a hiding or sneaking scene gets one test, then the resolution (the template's `scene-obstacle` ledger).
- **Prep:** rolling prep (an arc outline plus the next scene in detail); a scene card (opening shot, world moves, surprise, key NPC lines, the decision it ends on, the cut out); villain sheets for bosses and lieutenants; keep each NPC's `agenda` current (`agenda` command). Charter procedure: `story-design.md`.
- **Living world / clocks:** keep open clocks in `state.open_clocks`; if the players do not act on a lead or clock, advance it in the `World:` line (pressure, not negation; no invented deadlines).
- **Planner model routing** (planning on Opus, builds planned on Opus and executed on Sonnet with "do not commit"): the template's Orchestration section; the effort nudge (suggest high effort at a twist reveal, a boss-cracking fight turn or a finale turn) is the template's "Effort medium; high only for twist reveals, showcase finishers, finales".

## Section by section
| Old skill section | Landing |
|---|---|
| Purpose | README "Premise"; `arc-bible.md` section 1 |
| Start of a chat (attach voyage-memory; read CLAUDE.md, brief.md, players.md) | Superseded: template "Start of a chat" (`resume`, `recap`, `bible` by section); `brief.md` is replaced by `resume`/`prep` |
| Model routing (Sonnet 5.5 default, Opus planner, builds, effort nudges) | Template Orchestration; this file |
| Players and PCs (profile, earned wins, tone, romance, surprises) | README `Players`; skill fill block (short); `arc-bible.md` Tone |
| Rule on every player request (reasonable / partly / unreasonable, wishlist) | README "Ruling player requests" and Wishlist; template DM principles. **Retired:** "a hard no comes first with 2 or 3 options and no prompt until the user answers" (template: hard noes stay in the fiction) |
| Living world | README `Players` ("Living world"); `state.open_clocks`; this file |
| PC tests | README "PC pressure"; `arc-bible.md` section 7 |
| Story compass | `arc-bible.md` sections 1 and 2 |
| Working with Voyage (one beat, cuts, passive NPCs, no pressure in calm scenes, tone, literal reading, rolls combat, own memory, slips, 700 limit, language) | `docs/engine.md` (limit now 840; language rule kept as a rare fallback); canon facts `engine rule 1..7` |
| Turn loop (story first, then inputs; repo check; list dropped parts; voice cards; `turn.py`; per-turn save) | Template turn loop (`prep`, `commit-turn`, `dropped` slips); `turn.py` and `turn_save.py` are retired; commit every turn, push every 5 |
| Prompt format (Cut, Tone, Crew, Facts, World; rules) | Template prompt format (same labels and order; 840 limit) |
| Director's check (7 questions) | Template turn loop steps 4 to 5 (silent checks); obstacle ledger and budgets in `prep` |
| Playbook (fights, relationships, investigation, banter, finales, lengths, surprises) | `arc-bible.md` sections 8, 11, 12; `docs/story-design.md` section 5 |
| Prep and arcs (charter, villain sheets, agendas, recruit seats, `shared`) | `docs/story-design.md`; `docs/org.md`; README Recruiting |
| Spoilers (split) | README "Spoiler policy"; skill fill block |
| Scene end and arc end (light save, full sync, planner, site) | Template (scene end ask, `feedback`, `commit-turn`); planner and site are **pending port** (README) |
| Canon traps | `campaign.json` `canon_traps` (13), skill fill block (short), canon facts `correction ...` |

## Canon traps (old skill) and their landing
- Kaito Arashima vs Kaito Serizawa: always full names -> `canon_traps`, cast `use_full_name`, `NameIndex` ambiguity WARN.
- Kurokawa is the syndicate, not a district; "Safehouse" means Club Lumiere until one exists -> `canon_traps`, canon facts `base`, `kurokawa`.
- Recruiting is split by arm (Jovian: Spearhead; Jostin: Hearth); Reiko keeps discipline, roster and training -> README, `docs/org.md`, `canon_traps` (Reiko).
- Keito Takeda excluded; Shun garbled as "Saturday"; Nobu's real tech skill -> `canon_traps`, canon facts.
- Player-declared power unlocks are risky attempts, not facts; party membership needs explicit mutual agreement; NPCs know only what they observed; the game's turn counter is authoritative from t378 -> `canon_traps` (always-on) and canon `engine rule` facts.
- Do not develop Daigo directly in Act 2 -> `canon_traps` (Daigo), cast Daigo `wont_do_yet`, canon `exclusion: daigo`.
