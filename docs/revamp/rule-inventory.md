# Rule inventory (phase 1, for review)

Written 2026-10-04 from the repo at `0a91403`. Every rule in today's director layer, the one file it moves to, and how each conflict is resolved. Nothing is built yet: this is the map that phase 2 writes from. Items marked **decision** are calls I made on the user's behalf; section 8 records the user's answers to the phase 1 questions.

## 1. How to read this

Each rule has an id. In phase 2 the id goes into the new file next to the rule (for example `<!-- FMT-4 -->`), and a test checks that each id appears in exactly one file. Retired rules keep their id in section 6 with the reason.

The text in the "Rule" column is a short paraphrase for review, not the final wording. Ids are never renumbered; a removed row leaves a gap.

Two kinds of row are deliberate pointers, not second homes: the trigger table (TRIG-*) and the five pre-check questions (CHK-1), which ask whether rules owned elsewhere were broken. In phase 2 each pointer names the ids it points at. A playbook row may also apply an invariant to its own case (how Studio's hidden-term check works, which fields the planner page shows) without restating the invariant itself.

### New homes

| Code | File | Loaded |
|---|---|---|
| BOOT | `.claude/skills/voyage-director/SKILL.md` (the one uploaded skill) | always |
| CORE | `director/core.md` | read at chat start |
| PB-pacing | `director/playbooks/pacing.md`: scenes, budgets, obstacles, surprises, variety, act end, day turnover | scene start or end, scene at budget, day change, act end |
| PB-fights | `director/playbooks/fights.md` | a fight opens |
| PB-split | `director/playbooks/split-party.md` | PCs in different places |
| PB-studio | `director/playbooks/studio.md`: Studio requests and story fixes | a Studio moment |
| PB-retcon | `director/playbooks/retcon.md`: load-bearing slips and repairs | Voyage broke canon or agency |
| PB-reveals | `director/playbooks/reveals.md`: reveal ladders, milestones, personal quests | a milestone day or a ladder step |
| PB-pivot | `director/playbooks/pivot.md`: side goals, leaving the arc, drift, pivot | the PC follows a thread of their own |
| PB-arcs | `director/playbooks/arc-planning.md` | a planning trigger; arc functions on |
| PB-sync | `director/playbooks/sync.md` | session end, or the user supplies an export |
| PB-browser | `director/playbooks/browser.md` | browser mode |
| PB-campfire | `director/playbooks/campfire.md`: Campfire mode, copied from Campfire's `playbook/campfire.md` (2026-10-05) | the campaign names a Campfire room code and the GM types "send" or "draft" |
| PB-failures | `director/playbooks/failures.md` | a tool error or exit code |
| PB-start | `director/playbooks/campaign-start.md`: PC sheets, turn 1, opening | the campaign is at turn 0 or 1 |
| PB-modules | `director/playbooks/hidden-score.md`: Standing and debt | the campaign has a hidden-score module on |
| PB-sessions | `director/playbooks/sessions.md`: the two-session layout, the all-in-one fallback, models and effort (handoff 2) | chat start (choosing a role), and when launching or applying planner work |
| REF | `director/reference.md`: payload schema, op table, statuses, slip tags | when writing a payload by hand or repairing |
| AG-x | `director/agents/x.md`: one brief per subagent role, plus `common.md` | when that subagent is launched |
| CAMP | `campaigns/NAME/campaign.json` (printed by `resume` and the brief) | via tools |
| SHEET | `campaigns/NAME/director.md` (short world sheet) | read at chat start |
| TOOL | enforced by `db.py`; described in its `-h` text only | never read as rules |

PB-pacing, PB-reveals, PB-start, PB-modules and REF are additions to the handoff's playbook list (**decision D1**, section 7).

### Sources

| Code | Source (all at `0a91403`) |
|---|---|
| SK-core, SK-play | The two generic blocks of the skills (`templates/voyage-director/SKILL.md`; identical in the three campaign skills apart from module text) |
| FT | `docs/fast-turn.md` (identical in all campaigns and the template) |
| PA | `docs/player-agency.md` (identical everywhere) |
| ORC | `docs/orchestration.md` (template copy; campaign copies differ only in names) |
| ARC | `docs/arc-planning.md` (template copy; Class 2B matches it; Joestar's and Luxcellia's copies are an older version without preflight, `refine` and `--players`) |
| STU | `docs/studio.md` (template copy) |
| SPL | `split-scenes.md` (template copy) |
| EXP | `docs/expression.md` (template copy) |
| BIB | Generic sections of the template `arc-bible.md`: 8 Time skips, 11 Obstacle and surprise rules, 12 Scene turn budgets |
| RDM | Generic lines of the template campaign `README.md` (Arc reference, intake, save procedure, spoiler note) |
| ROOT | Root `README.md` and root `handoff.md` (2026-10-03) |
| HO | `docs/revamp/handoff.md`: new rules the user approved |
| WR-x | A campaign skill's `World rules` section (section 9) |

## 2. Size check for the always-loaded layer

The handoff's target is under 10 KB for BOOT plus CORE. Section 4 puts 21 rules in BOOT and 86 in CORE (the 17 trigger rows are short pointers). At plain-sentence length that estimates to about 3.5 KB and 6.5 KB. Phase 2 measures the real drafts; if CORE runs over, the first moves out are the NPC depth rules (NPC-1 to NPC-3, into a `director/playbooks/npcs.md` opened when a main NPC is present), not the agency rules.

## 3. Conflicts and how they are resolved

| Id | Conflict | Resolution |
|---|---|---|
| K1 | `prep` every turn (SK-core turn loop 1, ORC §0) vs no `prep` on routine turns (FT) | User-approved change: the lean brief every turn (LOOP-2). Both earlier forms retire (X-3). |
| K2 | Push every 5 turns (SK-core Saving, ORC §0, RDM) vs `--push-every 1` every turn (FT step 7) | FT wins: push every turn (SAVE-1). The tool default changes to 1 in phase 3 so no flag is needed, and Joestar's override goes (K31). |
| K3 | At budget, cut on a quiet input (SK-core turn loop 4, BIB 12) vs honour the input in one compact beat, then cut on the next idle or transitional input (PA) | PA wins (CUT-4). The two agree in spirit; PA adds the compact beat and the "never stated intent" rule. |
| K4 | Offer one skip at lulls; weekly montage offered via an NPC (SK-play rule 3, BIB 8 and 12) vs skips follow the input; an idle scene gets a `World:` nudge, never a skip (PA) | PA wins: the director never offers a skip (CUT-2). The limits on a skip the player asked for stay (CUT-3). Offering retires (X-5), the weekly montage included (user decision, Q3). |
| K5 | Cast subagents for 4+ speaking main NPCs (SK-core Orchestration, ORC §3) vs no subagents in the turn (FT, HO §4.3) | Retired (X-4). The main chat writes every `Crew:` line. |
| K6 | Paste loop (SK-core) vs Chrome loop (FT) | User-approved change: paste is the baseline (LOOP-1); the browser is an optional adapter (PB-browser). |
| K7 | Confirm a submit with a screenshot at scale 0.4 (FT step 6) vs re-read the page text, no repeated screenshots (HO §4.4) | HO wins (BRW-6). |
| K8 | Stay form of `Cut:` "Continue at ..." (SK-core format, SPL regroup) vs "Stay, same moment." (PA) | Merged: "Continue at <Location/area>, same moment." Naming the place guards against teleports; "same moment" guards against skips (CUT-1, **decision D2**). |
| K9 | World export: "never read it unless asked" (SK-core Roles) vs never read world files; tools read them (HO §3) | HO wins (WF-1). |
| K10 | "No background jobs" (SK-core, ORC §0) vs pressure cards launched in the background (ORC §2) and the pivot mini-charter drafted in the background (HO §4.7) | Both hold: no background shell processes; background subagents are fine (ORCH-6). |
| K11 | Never a bare "Studio: ..." line (SK-core reply, STU "In the reply") vs "flag them in one reply line" (STU Timing) | Batches always go in the reply that creates the request; at a natural break a one-line reminder of what is still pending is allowed (STU-6). |
| K12 | Drift "Re-aim?" yes closes the arc as `set_aside` (ARC §5) vs a pivot parks the old arc (HO §4.7) | After a pivot the old arc is `parked`. "Approve" makes the new arc active; "re-aim" redrafts the new arc with the user; "go back" makes the parked arc live again; `set_aside` stays for an arc the user drops for good (PIV-9, **decision D3**, revised in phase 2). |
| K13 | A favourite thread: "sketch a direction for the user (the Planner re-plans)" (SK-play Weave) vs the pivot flow (HO §4.7) | Replaced by the pivot flow (X-9). |
| K14 | `preflight` FAILs with no session zero or no act pitch (ARC §10) vs arc functions are optional per campaign (HO §4.7) | Arc checks run only when arc functions are on (CHAT-4). Tool change in phase 3. |
| K15 | Joestar `engine.md`: Voyage's extra PC lines "are accepted (the user likes them)"; never correct them vs PA: if Voyage voiced the PC, the next prompt ends with a repair line | User decision (2026-10-04): the repair line is removed for now, the same for every campaign (X-16). A player action Voyage decided that matters is still load-bearing (RET-1). |
| K16 | A fight "is over when its finisher lands" (BIB 12) vs it ends "when Voyage's output shows it decided" (SK-play Fights) | Same rule; the SK wording keeps the decision with Voyage (FGT-6). |
| K17 | Record the PC's "stated goals" (SK-play update rule) vs never write "the PC wants" (PA) | Not a real conflict: record what the PC said or did in play, with the quote (LOG-3, WLD-4). |
| K18 | Precedence statements: SK-core "they win over this file", FT "wins over", PA "win over", ARC header "player-agency still wins" | Retired (X-1). One home per rule makes them unnecessary; a test bans "wins over". |
| K19 | FT checks the prompt before the submit and runs `commit-turn` after it (bookkeeping off the clock) vs HO: two calls, lean brief then `commit-turn` | User decision (2026-10-04): FT's order, in both modes. The prompt is checked, then sent; recording and the push run after it, while the player reads Voyage's output (LOOP-2). A turn is three tool calls plus the browser batches. |
| K20 | `feedback -h` says "scene end: ask 'Best moment? Anything drag?'" vs SK-core "scene feedback only if the user raises it" and FT "no scene-feedback requests" | SK and FT win (SCN-6). The help text is fixed in phase 3. |
| K21 | SK-core says think only about prep's "LIVE CHECKLIST" | Becomes the lean brief's checklist lines (LOOP-3). |
| K22 | ARC §2 trigger list and SK-core "Arc planning" trigger list are duplicates | One home: the trigger table (TRIG-12); the procedure in PB-arcs. |
| K23 | Surface goal rule in SK-core prompt format and ORC §0b.1; silent check in SK-core loop 5 and ORC §0b.2; pull-forward in SK-play and ORC §0b.3; changed premise in SK-core loop 2, ORC §0b.4 and STU | Duplicates, each given one home (FMT-4, CHK-2, REV-3, RET-2). |
| K24 | Retcon: "fix in the fiction first" for a main NPC killed, a secret blurted or an action decided for the player (SK-play Retcon) vs the same cases are load-bearing and get an immediate Studio `story-fix` (SK-core loop 2, ORC §0b.4, STU "Story fix") | The newer, more specific rule wins for the latest turn: `story-fix` now (RET-2). STU already says older turns cannot be Studio-edited, so those are fixed in the fiction (RET-3). |
| K25 | "Voyage owns quest progress (no objective or ending records)" (SK-core format, ORC op table "legacy") vs a quest's apparent end is an inferred item (HO §4.5) | No progress or status records. An apparent end is an inferred note with its quote; `sync` reads Voyage's own status (FMT-5, STATE-2, decision D7). |
| K26 | Never ask the player what they want (HO §3) vs session zero asks for pacing, play styles and the hoped-for ending, and the retro question asks what landed (ARC §3) | Both hold: the ban covers the character's goals, feelings and choices; session zero and the retro ask about the game (AGY-5, ARC-2). |
| K27 | Planning trigger "no arc is live" (SK-core, ARC §2) vs arc functions are optional (HO §4.7) | Without arc functions the planning offer is one line at chat start (from `resume`), never a per-turn trigger (TRIG-12, **decision D9**). |
| K28 | "Act on prep's arc lines (midpoint, ...) with one line to the user" (SK-core "Arc planning") vs midpoint: stay silent unless something is off (ARC §5); FT's one-line list omits the midpoint | ARC wins (ARC-16). |
| K29 | Variety tags (fight, talk, explore, mystery, downtime; HO §4.6.4) vs session zero's pillars (combat, social, exploration, mystery) | Mapped for comparison: fight to combat, talk to social, explore to exploration, mystery to mystery; downtime is reported on its own (SCN-7, **decision D10**). |
| K30 | Campaign rules that narrow generic ones: Luxcellia's chain quests are Voyage's (never seed or track) against FMT-4 and FMT-5; Luxcellia's campfire rule against CUT-2; Joestar's "no invented deadlines" and "no cliffhanger tails" against clocks and CHK-2 | A campaign's `director.md` may narrow a generic rule (add a limit) and names the id it narrows; it never loosens a BOOT invariant (SHEET-1, **decision D11**). Each case is settled at that campaign's switch. |
| K31 | `campaigns/joestar/campaign.json` sets `"push_every": 5`, which overrides the tool default, while FT (the same file in Joestar) says push every turn | User decision (Q2): the default becomes 1 and the override goes, in phase 3. |

## 4. The inventory

### BOOT: the bootstrap skill (always loaded)

| Id | Rule | Source |
|---|---|---|
| REPO-1 | Attach `riggedrealm/campaign-helper` with push access, clone it, register it; work on `main` only (`git fetch origin main && git checkout -B main origin/main`). | SK-core Start 1; RDM Save 1; HO §2 |
| REPO-2 | No repo, no directing: if the repo cannot be attached or cloned, stop and say so. Never direct from memory. | HO §4.1 (new) |
| REPO-3 | Commit and push to `main` only. No other branches; no PRs unless asked. | RDM Save; HO §3 |
| VER-1 | The skill carries a version line. `resume` compares it with the repo's copy; on a mismatch, tell the user to re-upload the skill. | SK-core Start 2; HO §4.1 |
| ROLE-1 | Voyage narrates; the director steers from behind with one prompt per turn and is never felt by the players. | SK-core Roles |
| INV-1 | Voyage owns every mechanic: success, failure, strain, damage, every number, combat state, quest progress and rewards. The director decides only story consequences: who reacts and what the world does. | SK-core loop 3; SK-play DM ("Voyage decides rewards"); HO §3 |
| AGY-1 | Only the player moves their character. NPCs may suggest; relocate only when the input says so. | SK-play rule 2; PA |
| AGY-2 | Never state the PC's condition, feelings, thoughts, words, choices or results. NPCs may watch closely; Voyage's roll decides what they notice. | PA "The player character"; SK-core format; SK-play rule 1 |
| AGY-3 | Uncontested actions in the input happen as written. Fights and contested actions, social ones included (recruiting, persuading, bargaining, intimidating), are attempts Voyage rolls. Never confirm a scripted kill or win, or an NPC's yes to a contested ask (phase 5 trial, D22). An overreaching input: the attempt happens and the world answers within the power. | PA; SK-play rule 1 |
| AGY-4 | No menus of actions. Never script a PC's words, thoughts or feelings. | SK-play rule 1; HO §3 |
| AGY-5 | Goals come only from play. Never ask the player what their character wants, feels or will do, in play or in a planning session; session zero and the retro ask about the game, not the character (ARC-2, ARC-6). | PA "The player's story", "Planning sessions"; HO §3 (K26) |
| AGY-6 | Idle PCs stay put and do nothing notable. NPCs may address them; the prompt never acts for them. | SK-core format |
| AGY-7 | Companions stay where the PC left them. The director never removes, sends away or moves one the player did not dismiss. A two-person beat is asked for in the fiction by an NPC, and the PC decides. | PA "Companions and time" |
| SEC-1 | Two tiers. Never shown to the user or Voyage: hidden fields, unrevealed ladder steps, hidden scores and debt, off-ramps, `pc_threads`; villain sheets reach Voyage only as the fight facts (FGT-2). An arc secret (a campaign secret behind a ladder or twist) enters a prompt only in the scene that needs it. Nothing of the first tier reaches Studio, the planner page or any user-facing output. | SK-play Secrecy; RDM Spoiler note; STU "What never goes in"; ARC §8; HO §4.7 |
| DATA-1 | Campaign data changes only when Voyage's output establishes something, never from plans, guesses or hints, and only through `db.py`. | SK-play update rule; RDM; HO §3 |
| WF-1 | Never read or edit world files (`New_World.json`, anything under `worlds/`, raw Voyage exports). Tools read them; chats do not. The world changes only through user-approved Studio requests. | SK-core Roles; HO §3 (K9) |
| TRIAL-1 | A trial run writes nothing: lookups and `--dry-run` only; rehearse on a copy with `VOYAGE_DATA=/path`; `VOYAGE_TRIAL=1` makes the tool refuse writes (exit 4). | SK-core Start 3; RDM Save 3; ORC §1; HO §3 |
| CHK-1 | The five-question pre-check on every draft: (1) does a line state a PC's condition, feeling, words or a contested result, or an NPC's answer to a contested ask; (2) did `Cut:` move time, place or a companion further than the input reached; (3) does an NPC hand over an unasked answer or move a met goalpost; (4) is any rule, gate or place new and not in the database; (5) is the `Tone:` line a fix older than 3 turns. | PA "Pre-check"; FT step 3 |
| SEL-1 | The campaign is chosen every chat, never assumed. Order: the user names it; in browser mode the tab title matched to `voyage_title`; cast names in pasted text as a hint; otherwise the menu asks. | HO §4.2 (new) |
| SEL-2 | "send" as the first message skips the menu only when the campaign is unambiguous. | HO §4.2 (new) |
| MENU-1 | The skill is a main menu: `db.py menu` prints it. Chat start: choose the campaign and the session role (`use NAME --role ROLE`: director, planner or all-in-one; `--role auto` after a first "send"), then read `director/core.md` and the campaign's `director.md` (CORE takes it from there). | HO §4.1, §4.3 (new); HO2 §1 (role) |
| CFM-1 | When the campaign file names a Campfire room code (`campfire_room`) and the GM types "send" or "draft", follow `campfire.md` and not the Voyage steering flow. | CFP item 6 |

### CORE: `director/core.md`

**Chat start and session**

| Id | Rule | Source |
|---|---|---|
| CHAT-1 | At chat start: `resume` in the main chat (state, version check, preflight summary, canon traps and main NPCs from `campaign.json`); offer the recap, which a subagent writes. `resume` also prints the session role and the first turn's brief. | SK-core Start 2; HO §4.2, §4.3; HO2 §0, §1 |
| CHAT-2 | Read the arc bible by section only (`bible` lists headings). Use lookups (`npc`, `quest`, `loc`, `lore`, `bible`) only for real gaps. | SK-core Start 2, loop 1; ROOT handoff |
| CHAT-3 | Start a fresh chat per scene or every 15 to 20 turns, after `wrap-up`. | SK-core Start 4; ROOT handoff |
| CHAT-4 | Run `preflight` before the first prompt of a chat and at each act start. Fix FAILs; say WARNs in one line; keep the act plan's checklist in mind and queue its deferred ops. Arc checks apply only when arc functions are on. | ARC §10; WR-C2B "Preflight" (K14) |
| CHAT-5 | Model and effort: a pointer to SES-8 in `sessions.md` (handoff 2 replaced the effort sentence). | SK-core Orchestration; HO2 §3 |
| CHAT-6 | Run every command from the repo root. | SK-core Roles; RDM; ORC header |
| SHEET-1 | A campaign's `director.md` may narrow a generic rule (add a limit) and names the id it narrows; it never loosens a BOOT invariant. | K30 (new) |

**Orchestrator**

| Id | Rule | Source |
|---|---|---|
| ORCH-1 | Who does what: the menu table (turn: main chat; resume digest and recap: subagent; act or arc plan: Opus subagent, reviewed with the user; pressure card for a showcase fight, twist reveal or finale: Opus (all others inline, ARC-14); pivot mini-charter: Opus, in the background; Studio, cast and world work: Sonnet; sync: subagent, main chat confirms; director review, canon audit, act retro: read-only subagent; tool, test and doc changes: Sonnet, main chat reviews the diff; new campaign scaffold: Sonnet; wrap-up and repairs: main chat). Handoff 2: the director session keeps the turn, wrap-up, repairs, applying planner files and sync; the Opus and Sonnet jobs run in the planner session or, all-in-one, as subagents at a break; the director review is Opus (D24). | HO §4.3; HO §3; SK-core Orchestration; HO2 §1, §2 |
| ORCH-2 | The turn stays in the main chat: read, rule, draft, check, submit, bookkeeping. No subagent on the clock or for bookkeeping. Handoff 2: "main chat" becomes the director session; the model line moves to SES-8. | HO §4.3; FT Standing choices; HO2 §1, §3 |
| ORCH-3 | The clock runs from the user's paste (or "send") to the prompt reaching them (paste mode: shown in the chat; browser mode: submitted). Recording and the push come after, in the downtime while the player reads Voyage's output. Everything else is off the clock too. Handoff 2: nothing on the clock touches the network. | FT intro; user decision 2026-10-04; HO2 §0 |
| ORCH-4 | A subagent gets its brief from `director/agents/`, never the skill, and the brief says it is not directing. Read-only, except one named writer at a time. Results are compact, never file dumps. | HO §4.3 |
| ORCH-5 | Every user-facing output (recap, pivot line, sync report, menu) passes the hidden-term scan before the user sees it. | HO §4.3, §6 |
| ORCH-6 | No background shell processes (a process can die when its call ends; the container can reset). Background subagents are fine. | SK-core; ORC §0 (K10) |

**The turn loop**

| Id | Rule | Source |
|---|---|---|
| LOOP-1 | Paste is the baseline: the user pastes the last exchange (Voyage's output and the inputs); save it to `paste.txt`. The user submits the prompt; their next paste proves it landed. | SK-core turn loop; HO §4.4 (K6) |
| LOOP-2 | A routine turn is one tool call before the prompt and one after it: rule and draft from the brief already in context (printed by the last `commit-turn`, or by `resume` for a chat's first turn); one call writes the prompt and runs `check-prompt`; send it (shown to the user in paste mode, submitted in browser mode); then `commit-turn` with the payload, which records, pushes, fetches planner output and prints the next brief. Nothing before the send touches the network; never record or push before the prompt is out. Handoff 2 replaced D13's brief-first order. | HO §4.4; SK-core loop 1 and 6; FT steps 4 to 7; user decision 2026-10-04 (K1, K19); HO2 §0 |
| LOOP-3 | Routine turn: the ruling in 2 or 3 sentences, one handle, one gesture, one world move. Think only about the brief's checklist and the rulings. | FT step 2; SK-core loop 2 (K21) |
| LOOP-4 | Read Voyage's latest output for slips: wrong facts, invented details or places, a teleported PC, a stated PC outcome, a broken split protocol, dropped instructions. Re-send only the essential ones, as actions. | SK-core loop 2 |
| LOOP-5 | Fix every FAIL from `check-prompt` before the prompt goes out; WARNs never force a rewrite. `commit-turn` repeats the check and writes nothing on a FAIL; a payload error found after the prompt is out is fixed and rerun off the clock. | SK-core loop 6; FT step 4; ORC §0 |
| LOOP-6 | Escalation: on TRIG-1 to TRIG-9 or a pivot's first turn, run the full process before drafting: `turn-brief --full`, the full character card where TRIG-1 applies, the relevant `bible` section and a `canon` check. Only these justify a lookup before the prompt; off the clock, lookups only for real gaps (CHAT-2). | FT step 2; SK-core loop 1; HO §4.4; HO2 §0 |
| CHK-2 | Silent check before drafting: can the player say what they do next and why? If not, give a handle through an NPC or the world (never a menu, never the PC's thoughts). Does the prompt end on a decision the players care about? What win, reveal or laugh do they get? Whose spotlight, and who went without? | SK-core loop 5; ORC §0b.2 |

**Rulings**

| Id | Rule | Source |
|---|---|---|
| RULE-1 | Rule each input: accept; accept with a story consequence; or the world declines in the fiction. | SK-core loop 3 |
| RULE-2 | Yes first. Push back only in the fiction, and only when something breaks power rules or canon, or skips a hard-won moment (consent is RULE-3). No approval gates, goal caps or progress tracks. | SK-play DM principles |
| RULE-3 | Hard noes stay in the fiction. Stop and ask the user only when an input would break consent or the agency rules. | SK-play rule 4 |
| RULE-4 | Ambiguous input: take the most literal reading; let `World:` show two or three things the PC could follow; never decide which one matters. | PA |
| RULE-5 | Gates are costs, not walls: an NPC may warn, refuse help or raise the price; the PC can always attempt it and face the consequence. | PA "NPCs" |

**Prompt format**

| Id | Rule | Source |
|---|---|---|
| FMT-1 | Labels in order: `Cut:`, `Tone:` (optional), `Crew:`, `Facts:` (optional), `World:` last. Labels count toward the hard limit (`state` prints it). One beat per turn. Use the full limit when it helps; never pad. | SK-core format; FT step 3 |
| CUT-1 | `Cut:` says where and when. Staying: "Continue at <Location/area>, same moment." | SK-core format; PA; SPL regroup (K8) |
| CUT-2 | Skips follow the input: move time or place only when the input implies travel, waiting or leaving, and only as far as it reaches ("let's eat" lands at the table, not after the meal). Make the relocation explicit. An idle scene gets a `World:` nudge. The director never offers a skip. | PA; SK-core format (K4) |
| CUT-3 | A skip the player asked for never passes a scheduled milestone, never decides a PC outcome and sums up only what the player chose. A week skip lands on the first morning of the next week, using the focus the player chose (training, job, study, home time, rest, relationships). | BIB 8, 12; SK-play rule 3 |
| CUT-4 | Scene budgets cut filler, never stated intent. At budget, honour the input in one compact beat, then cut on the next idle or transitional input. An input that starts something new keeps normal pacing, even past budget. | PA; SK-play rule 3; SK-core loop 4; BIB 12 (K3) |
| CUT-5 | Goal met, even under budget, and the input is quiet: cut to the next beat. Do not wait for a perfect ending; the players can bring a loose thread along. | SK-core loop 4; BIB 12 |
| TONE-1 | `Tone:` is optional and describes mood, not banned devices. A `Tone:` line written to correct something lasts 3 turns, then gets reviewed. | SK-core format; PA "Director habits" |
| CREW-1 | `Crew:` names only the one to three NPCs the beat needs; an NPC a player addresses, mentions or calls for comes first; every other present NPC is backdrop and stays out of the prompt (no "others react in character" sweep). One or two spotlight NPCs get a gesture or habit, the feeling under it and their way of talking (a short line of their own words, never a PC's), from the brief's rotated picks, never last turn's. One flat-versus-expressive example. | SK-core format; EXP; user 2026-10-05 |
| CREW-2 | Use the brief's card for a main NPC before writing their `Crew:` line. | SK-play "Main NPCs"; ROOT handoff |
| CREW-3 | Each `Crew:` clause is a want, mood or attitude, not a run of actions (every NPC intent is a beat Voyage must narrate); an arriving message, an off-screen action or a world event goes in `World:`; in fights `Crew:` holds only the villain's personality, want and voice (FGT-1). | user 2026-10-05 (world-creator NPC-intent review) |
| FACTS-1 | `Facts:` are plain truths; Voyage turns them into dialogue, so never write "correction" or "not X". An in-scene fix goes in the speaker's `Crew:` clause. `Facts:` binds Voyage's world, not what NPCs say. | SK-core format; PA "Discovery" |
| WORLD-1 | `World:` comes last every turn: a world move (NPCs are passive), a surprise or a quest seed line (200 characters at most). | SK-core format; BIB 11 |
| FMT-2 | At most one new NPC and one new quest seed per turn. | SK-core format |
| FMT-3 | A `planned` NPC gets name plus `intro_line` (90 characters at most) once. Main NPCs, fixed NPCs (`campaign.json`) and Studio NPCs need none. | SK-core format; SK-play Studio |
| FMT-4 | Every quest, errand or contact states a visible goal in the fiction: what, for whom, reward, risk. Only its purpose may stay secret. It lives in `seed_line` or `surface_goal`; when the brief says "no surface goal set", fix it in the next prompt. | SK-core format; ORC §0b.1 (K23) |
| FMT-5 | The director only seeds quests; Voyage owns their progress, so there are no objective or ending records (an apparent end is an inferred note, STATE-2). A quest starts when a prompt gives its `seed_line`; record `quest-start`; never seed it twice. Voyage remembers records and quests: never restate them. Nothing ends the game. | SK-core format; RDM Quests; ORC op table (K25) |
| FMT-6 | No push toward Voyage's objective panel: leave its objectives alone unless the PC picks one up; at most one opening in `World:` that nobody suggests. | PA |
| FMT-7 | No invented places or rules in a prompt unless they are in the database first (`loc`, `add-area`, `fact`). No new locations; new areas only inside existing ones once the story shows them. | PA "Director habits"; SK-play DM "Protected" |
| FMT-8 | Quoted text is hidden from the name check: keep key names outside quotes. | SK-core format |
| FMT-10 | Prompts are conditional only about fight status, the outcome of a contested ask (if it lands, the NPC does X; if not, Y), and at most one open question. Other inferred items are simply not asserted. | HO §4.5; phase 5 trial, D22 |
| FMT-11 | A prompt carries only the sliver of the database a scene needs; nothing from the repo is pasted whole into Voyage. | RDM intro; template `arc-bible.md` intro |

**NPCs**

| Id | Rule | Source |
|---|---|---|
| NPC-1 | Main NPCs are people, not helpers: psychology drives the reaction (want, fear, lie, triggers, tells) and they speak in their own voice. They may refuse, disagree or be busy. Reuse NPCs before inventing new ones. | SK-play "Main NPCs"; SK-play DM |
| NPC-2 | Growth runs on schedule: behaviour matches the act beat and the ladder and changes only when earned; "won't do yet" is off the table. | SK-play "Main NPCs" |
| NPC-3 | Relationships colour everything. Hidden facts stay out of dialogue until their ladder step is revealed; tells may hint. | SK-play "Main NPCs" |
| NPC-4 | Conditions bind: when an NPC names a condition, record it (a fact of kind `condition`). Once the PC meets it, the NPC honours it. A fair price may be added; a new hurdle needs a reason Voyage already showed. No deferring an earned answer. | PA "NPCs"; HO §4.6.2 |
| NPC-5 | Discovery belongs to the PC: an NPC gives one hint only if the PC asks or is clearly stuck; observers do not call targets or solve puzzles. | PA "NPCs" |
| NPC-6 | NPCs keep their own consent and agency: they can say no, set a price or walk away. | PA "NPCs" |
| NPC-7 | Romance is optional and never pushed; Voyage follows the player. Only `romance_eligible` NPCs, and only adults with adult PCs. Any NPC can decline, which ends it. Beats are earned in the story. | SK-play Romance; RDM Romance |

**The world between turns**

| Id | Rule | Source |
|---|---|---|
| WLD-1 | Beats are hooks, not appointments: place arc beats where the PC is going. An ignored hook moves on visibly without them. Fronts and clocks act on their own schedule whether or not the PC is watching. Bible dates are a pressure floor, not a script; only big milestones are fixed, and they happen as the world acting, even when the PC is elsewhere. | PA "The player's story"; SK-play DM "The arc is pressure"; SK-play "Leaving the arc" |
| WLD-4 | `pc-thread` records what the PC keeps returning to, as what they did ("went back to the cart three times"), never why and never "wants". It is kept per character. It makes the world respond; it never plans where to lead them. No profile of what the player wants is ever built. | PA; ARC §5; HO §4.6, §4.7 |

(WLD-2 and WLD-3 are in PB-pacing.)

**State and bookkeeping**

| Id | Rule | Source |
|---|---|---|
| STATE-1 | The ownership table. Voyage: everything in INV-1, plus its own panels. The director owns: story consequences, cast bibles, ladders, canon traps, promises, clocks, fronts, arc plans, scenes. The user owns: PC sheets, session zero, approvals, applying Studio batches. Inferred by the director: position, time, presence, quest start or apparent end, stated conditions, fight status. | HO §4.5; SK-play "Player-character sheets"; ORC; migration.md "not mirrored" |
| STATE-2 | A record made from play carries the `inferred` flag and the quote it came from. | HO §4.5 (new) |
| STATE-3 | Never guessed: stats, resources, relationship numbers, quest progress counts. | HO §4.5 |
| STATE-4 | Unclear things that matter go on the open questions list; the brief shows it; close an item when Voyage's output settles it. | HO §4.5 (new) |
| LOG-1 | Every update carries the turn and evidence (a quote or paraphrase of the output), never ahead of the log. | SK-play update rule; RDM |
| LOG-2 | Every turn logs: `summary` = what the output established, not what the prompt asked (two lines at most); `time` when the block changed; `pos` when a PC moved (`loc <city>` lists areas; never skip it because a lookup failed); `slips` for every invention or fact error, Voyage's or the director's. | FT step 7; SK-core loop 6 |
| LOG-3 | Record what players may raise later as facts with a kind: promise, condition, debt, plant; also secrets shared, gifts, running gags, decisions, and goals the PC stated in play (as said, with the quote). Mark a promise `paid` when it is paid. | SK-play update rule; FT step 7; HO §4.6.2 (K17) |
| LOG-4 | Any new rule the director or Voyage adds in play is logged as an `invention` slip. | PA "Gates are costs" |
| LOG-5 | Repeat slips become canon traps: add the trap to `campaign.json` `canon_traps` and record a fact. | Template World rules fill; WR-C2B header |
| SAVE-1 | `commit-turn` commits and pushes every turn; a push failure only warns (the data is saved and committed). | SK-core Saving; FT step 7 (K2) |
| SAVE-2 | Session end ("wrap up", or before a fresh chat): ask for Voyage's state export (PB-sync; the user may skip), then `wrap-up`, and relay "safe to close" or the failure. | SK-core Saving; HO §4.5 |
| REVIEW-1 | At scene end or wrap-up, launch the director review (a read-only subagent) on the last N turns; its findings feed `resume`'s repeat slips. | HO §4.6.5 (new) |

**Reply**

| Id | Rule | Source |
|---|---|---|
| REPLY-1 | The prompt goes in a blockquote with its character count. | SK-core loop 7; FT step 8 |
| REPLY-2 | The one extra line: at most one, and only for a slip, a ruling with a story consequence, a Studio item, a decision for the user, or one of the user lines the playbooks own (planning ARC-5, drift DRIFT-1, budget ARC-17, variety SCN-7, pivot PIV-7). Reasoning only if asked "why". | SK-core loop 7; FT step 8 |
| REPLY-3 | Studio batches are not extra lines; PB-studio says where they go. | SK-core loop 7; STU |

**Trigger table** (each row names when to open which playbook)

| Id | Trigger | Opens |
|---|---|---|
| TRIG-1 | A first appearance of an NPC in a scene, a big emotional beat or a reveal | the full brief for that NPC (`brief NAME`) |
| TRIG-2 | A new NPC or place in the output or the plan | FMT-2, FMT-3, FMT-7, and `add-npc` / `add-area` in the payload |
| TRIG-3 | A new beat with no scene open; a scene at budget; the scene's goal met; a day change; an act boundary | PB-pacing |
| TRIG-4 | A fight, or a fight opening | PB-fights |
| TRIG-5 | A milestone day or a ladder step in play | PB-reveals |
| TRIG-6 | Romance or consent edge cases | NPC-6, NPC-7, RULE-3 (ask the user if needed) |
| TRIG-7 | A player power claim or invented fact | AGY-3, RULE-2, LOG-4 |
| TRIG-8 | A Studio moment: an NPC becomes key (recurs, the players invest, or the Planner ties them to an arc thread); a player thread outgrows one scene, or an arc quest is due; a thin faction the players stick with; new areas the story established; an act starts (bundle the act's planned NPCs and quests); an entity already in the world changes after a milestone (an edit); a story fix | PB-studio |
| TRIG-9 | A load-bearing slip in the latest output, or broken canon | PB-retcon, before the prompt |
| TRIG-10 | PCs in different places | PB-split |
| TRIG-11 | The PC follows a thread of their own; a side goal; no arc contact | PB-pivot |
| TRIG-12 | Planning: the user asks, an arc closes, no arc is live, an act ends. Without arc functions, "no arc is live" is only a one-line offer at chat start (K27) | PB-arcs (never mid-turn) |
| TRIG-13 | Session end, or the user supplies an export | PB-sync |
| TRIG-14 | A tool error or non-zero exit | PB-failures |
| TRIG-15 | Browser mode | PB-browser |
| TRIG-19 | The campaign file names a Campfire room code (`campfire_room`) and the GM types "send" or "draft" | PB-campfire (row next to Browser mode in `core.md`'s trigger table) |
| TRIG-16 | The campaign is at turn 0 or 1 | PB-start |
| TRIG-17 | The campaign has a hidden-score module on (`resume` says so) | PB-modules |
| TRIG-18 | Choosing the session's role at chat start; launching or applying planner work | PB-sessions (row in `core.md`'s trigger table) |

### PB-pacing: scenes, acts and days

| Id | Rule | Source |
|---|---|---|
| SCN-1 | A new beat with no scene open: `scene-start` (name, budget from the table, place, optional card, variety tag). | SK-core loop 4; HO §4.6.4 |
| SCN-2 | Default budgets (director turns from the scene's first prompt): fights 4 to 8; big emotional scenes 3 to 6; investigation 1 to 2; travel and waiting 0; arrival, admin, move-in or errand scenes 2 at most. A campaign's bible may set per-act budgets. Budgets are ceilings, not targets. | BIB 12; SK-play rule 3 |
| SCN-3 | Close a scene with `scene-end` on the turn it ends. | FT step 7; SK-core loop 4 |
| SCN-4 | At most one ordinary obstacle per beat (`scene-obstacle`). Keep obstacles ordinary; drama comes from people. | SK-core loop 4; BIB 11 |
| SCN-5 | One surprise per scene (`scene-surprise`), small most of the time; bigger ones are saved for act turns. | SK-core loop 4; BIB 11 |
| SCN-6 | Scene feedback only if the user raises it (`feedback --kind scene`, before `scene-end`). | SK-core loop 4; FT step 8 (K20) |
| SCN-7 | Variety: each scene gets one tag at `scene-start` (fight, talk, explore, mystery, downtime). Three of a kind in a row warns; two variety or boredom flags (shorter inputs, repeated skips, a "drag" note) mean a one-line check with the user and more variety in the next pressure card. At retros the mix is compared with session zero's pillars (fight to combat, talk to social, explore to exploration, mystery to mystery; downtime on its own). | ARC §5 boredom flags; HO §4.6.4 (K29) |
| SCN-8 | Act end: write a short retro (what landed, cold threads, the hidden-score band if that module is on) and log it with `feedback --kind act`; it feeds the next act pitch. Acts exist without arc functions. | SK-core loop 4; ARC §7 |
| WLD-2 | Neglected threads go cold after about 7 in-game days: the world moves them a step. Nothing earned is lost. | SK-play DM |
| WLD-3 | On a day change, run `day-turnover` and play what it lists (clocks, threads going cold, front moves, parked-arc clocks, off-screen agendas) through `World:` lines over the next turns. | HO §4.6.3 (new) |

### PB-fights

| Id | Rule | Source |
|---|---|---|
| FGT-1 | The villain's personality, want and dialogue go in `Crew:`; the battlefield goes in `World:`. | SK-play Fights |
| FGT-2 | At the fight's opening, give Voyage the villain sheet's rule and weakness (`bible`) as plain facts. | SK-play Fights |
| FGT-3 | Voyage runs every exchange and holds the combat state the director cannot see. Fight prompts are conditionals on it ("If any rats are alive, they shy from light. If none are left, the fight is over."). | SK-play Fights; ORC §0 Fights |
| FGT-4 | Never state who is alive, dead or winning, who hits or whether the rule cracks. Never add enemies, waves, reinforcements or reversals in `World:` or `Facts:`; describe only the setting and the enemy's standing rules. | SK-play Fights |
| FGT-5 | A `fight status:` line in the paste wins over inference. | SK-play Fights |
| FGT-6 | If the user says the enemy is dead or the fight is over (or pastes a combat-panel line), close it at once: the prompt says so and moves to the aftermath. Otherwise the fight ends when Voyage's output shows it decided. Never pad a fight to reach its budget. | SK-play Fights; BIB 12 (K16) |
| FGT-7 | Fights move: change `Crew:` and `World:` every round; escalate, or pay off a tell or a set piece. Never reuse last round's gesture. | PA "Director habits" |

### PB-split

| Id | Rule | Source |
|---|---|---|
| SPL-1 | Adopt the seven-rule protocol in full and write it into `Cut:` in compact form. | SPL intro |
| SPL-2 | Positions header: every split turn opens with a 📍 block of each PC's location, area and activity. | SPL rule 1 |
| SPL-3 | Each scene opens with its own label and covers only that location's characters. | SPL rule 2 |
| SPL-4 | Only scenes with a player action this turn advance; the others hold still and are not re-narrated. | SPL rule 3 |
| SPL-5 | No teleporting: a PC never moves, appears or acts in a scene unless their own player says so. Never state a PC's destination or arrival unless the player did. | SPL rule 4; SPL checklist |
| SPL-6 | One place per NPC: an NPC is in one scene at a time and knows only what happened there; information crosses only by phone, message or travel. | SPL rule 5 |
| SPL-7 | One shared clock: all scenes share time; note who is waiting and since when. | SPL rule 6; SPL checklist |
| SPL-8 | Regrouping: when PCs reunite (a player says so), say so once and drop the header; the next `Cut:` returns to the stay form. | SPL rule 7; SPL regroup note |
| SPL-9 | Never split the party yourself. | SPL checklist |
| SPL-10 | Use exact world names in headers and `Cut:` lines. | SPL |
| SPL-11 | Fitting it in: open `Cut:` with `SPLIT`; name scenes A, B, C with PC first names; one `Crew:` clause and one world move per advancing scene, prefixed `A:` or `B:`; hold scenes get no world move; drop `Tone:` unless it differs; `Facts:` only for a rule 4 or 5 reminder; the four compact `Cut:` forms and two worked examples. | SPL "Fitting"; SPL forms |
| SPL-12 | The 📍 emoji may count as two characters: keep a 10-character margin. | SK-core format; SPL |
| SPL-13 | At a multi-player table threads are tracked per character; if one PC leaves the arc and another stays, it is a split party and the arc stays active. | HO §4.7 (new) |

### PB-studio

| Id | Rule | Source |
|---|---|---|
| STU-1 | Studio is occasional: it costs tokens, cannot export, and one request holds about 2000 characters in total (`studio_limit`). Bundle requests; the user applies them at a natural break. | STU intro; SK-play Studio |
| STU-2 | Not a reason for Studio: a one-off extra, a name used once, or anything a prompt line and `add-npc` already cover. (The moments that are reasons are the trigger, TRIG-8.) | STU "When to inject" |
| STU-3 | Plan it as a `studio-request` op (auto-batched); confirm with `studio-done` when the user has applied it. | SK-play Studio; STU log flow |
| STU-4 | Edits (`--edit`): send only the changed fields ("Update <name>: ...") for an entity already in the world: a role or place change after a milestone, a revealed ladder step, a faction's shift, a quest's changed giver or premise. Never quest progress. | STU "Edits" |
| STU-5 | Applying SEC-1 to Studio: revealed ladder steps may go in; `studio-request` runs the hidden-term check, which refuses strong hits (`--allow` only for public terms) and warns on soft ones. | STU "What never goes in"; SK-play Studio |
| STU-6 | In the reply: a new request's batches go right below the prompt, each in a code block with its character count; a story fix goes above the prompt. Never a bare "Studio: ..." for a new request. At a natural break, one line may remind what is still pending. | STU "In the reply", "Timing"; SK-core loop 7 (K11) |
| STU-7 | Request text: plain field lines modelled on the world data shapes, one template each for NPC (name, role, faction, where found, about, look, personality, voice), quest (name, giver and where, goal, 3 to 5 steps, success and failure as consequences in the fiction with no numbers), faction (name, type, about), area, and story start or other. Only what the story established; skip fields you would have to invent. | STU "Request formats" |
| STU-8 | Bundle related requests in one file; over the limit, let it split; never trim facts to fit. | STU "Batching" |
| STU-9 | Writing a story fix: plain world truths of what should have happened, written as FACTS-1 says, with nothing hidden (SEC-1), usually one batch. The next prompt assumes the fixed version and the turn's payload summarises the corrected story. `studio-done --fact KEY` records each line as canon. | STU "Story fix" |
| STU-10 | Timing: never mid-scene unless the user wants it; a story fix is never bundled or deferred. `resume` shows what is pending. | STU "Timing" |

### PB-retcon

| Id | Rule | Source |
|---|---|---|
| RET-1 | A load-bearing slip is: a main NPC killed or misidentified, a player action decided for them, a secret blurted, a death, a wrong place or time that would carry forward, a changed job premise or terms, a quest's giver or goal changed, or what an NPC asked for changed. | STU "Story fix"; SK-core loop 2; ORC §0b.4; SK-play Retcon |
| RET-2 | In Voyage's latest turn: a Studio `story-fix` now, before the next prompt (PB-studio STU-9). Never let a changed premise pass as harmless. | SK-core loop 2; ORC §0b.4; STU (K23, K24) |
| RET-3 | In an older turn (Studio can edit only the latest): fix it in the fiction in the next prompt (a rumour, a misunderstanding, something staged). | SK-play Retcon; STU |
| RET-4 | Small slips stay prompt and `Facts:` fixes. | STU "Story fix" |
| RET-5 | Ask the user out of game only when the next prompt cannot repair it, and always before Voyage's regenerate or undo. | SK-play Retcon; PA |
| RET-6 | Record what the players saw. | SK-play Retcon |

### PB-reveals

| Id | Rule | Source |
|---|---|---|
| REV-1 | Ladder steps stay hidden until the story establishes them; `thread-reveal` enforces act, order and gates (`--gate-met` after the milestone; `--force` only on the user's word). | SK-play DM "Reveal ladders" |
| REV-3 | Player-driven pull-forward: when the PC reaches a thread early, its next step may move up exactly one act if the scene needs it, with no unmet gate and every earlier step revealed (`--player-driven`). Two acts early, gated or skipped steps still need `--force`. | ORC §0b.3; SK-play DM (K23) |
| REV-4 | A side quest advances an arc thread at most one step, never past a milestone. | SK-play DM |
| REV-5 | Personal quests unlock only when the story has shown real closeness with that NPC (shared secrets, time together, a moment that landed). | RDM Quests |
| REV-6 | After a revealed step changes how an NPC is portrayed, plan a Studio edit (PB-studio STU-4). | STU "Edits" |

### PB-pivot: side goals, leaving the arc, pivot

| Id | Rule | Source |
|---|---|---|
| SIDE-1 | Size a side goal as an errand, a thread or a storyline (a side quest needs 2+ scenes). Rule it reasonable, partly or unreasonable; consequences come in the fiction; one line to the user; never pause play. | SK-play DM |
| SIDE-2 | Weave, don't wall off: tie player projects into the cast; never punish one with an arc threat. | SK-play DM |
| LEAVE-1 | When players leave the arc, their choice wins: play the chosen party from its own agenda; never steer back. | SK-play "Leaving the arc"; ROOT handoff |
| LEAVE-2 | Ask what the planned contact was for; the new party supplies it on its own terms (price, motive). | SK-play "Leaving the arc" |
| LEAVE-3 | Clues come only from the current ladder rung. | SK-play "Leaving the arc" |
| LEAVE-5 | The party the players passed over keeps its clock and agenda and may return as a rival or a better offer, with or without arc functions. | SK-play "Leaving the arc" |
| LEAVE-4 | A thin new party: build it from the world data through lookups (`faction`, `lore`, `loc`), improvise a want, a price and one voice, and record them at once (`add-npc`, `agenda`, `fact`). If they stay, the Planner fleshes them out. | SK-play "Leaving the arc" (WF-1 makes "use only the world file" mean "through the tools") |
| DRIFT-1 | Drift: 8 turns in a row since the arc started with no arc contact: the world moves the front on, and one line asks the user "Re-aim?" (`DRIFT_TURNS = 8`). | ARC §5; HO §4.7 |
| PIV-1 | Off-ramps: at each arc approval and midpoint the Planner writes two or three hidden five-line sketches (promise as a question, one front, a face, a first move), one per thread the PC already pursued on screen. They are never seeded into a prompt; the tool hides them on routine turns. | HO §4.7 (new) |
| PIV-2 | Detect a pivot at once on an input that plainly commits to a new party or goal; otherwise after three turns on a new thread with no arc contact. | HO §4.7 (new) |
| PIV-3 | Bridge: the main chat writes an inline pressure card for the next scene from LEAVE-1 to LEAVE-4, so play never waits. | HO §4.7 (new) |
| PIV-4 | Draft: an Opus subagent writes a mini-charter in the background from the matching off-ramp or from scratch: one front with two or three moves, a face, three clues, a 10 to 15 turn budget; built only from what the PC did; tied into existing ladders where it can be. | HO §4.7 (new) |
| PIV-5 | Adopt after main-chat review as `provisional`. Limits: no twist; no ladder step revealed early; at most one new NPC (the face); new areas only inside existing locations; passes the lines-and-veils check; off the public planner page until approved. | HO §4.7 (new) |
| PIV-6 | Park the old arc (`parked`): day turnover keeps moving its clocks and fronts, and it may come back as LEAVE-5 says. | HO §4.7 |
| PIV-7 | Tell the user at the next break, one line: approve, re-aim or go back. At a multi-player table the host alone approves. | HO §4.7 (new) |
| PIV-8 | A pivot needs no PC in arc contact (one PC leaving while another stays is SPL-13). | HO §4.7 (new) |
| PIV-9 | The user's three answers: "approve" makes the provisional arc active; "re-aim" means redrafting the new arc's direction with the user while the old arc stays parked; "go back" makes the parked arc live again and closes the provisional one. An arc the user drops for good closes as `set_aside` with a short retro on what pulled the PC away. | ARC §5, §6; HO §4.7 (K12; D3 as revised) |
| PIV-10 | Arc functions (and so pivots) switch on only when the campaign has a session zero and a charter; everything else works from turn 1 without them. | HO §4.7 (new) |

### PB-arcs: arc planning

| Id | Rule | Source |
|---|---|---|
| ARC-1 | The plan has three records in `arcs.json` (optional file): session zero, act pitches, arc charters. | ARC §1 |
| ARC-2 | Session zero is about the game, never the PC's goals: tone; lines (never happens); veils (happens offscreen only); how much of each play style the table wants (combat, social, exploration, mystery, each 0 to 3); pacing; the hoped-for ending (triumph, bittersweet, open); player count. First time: ask the user; later: print it and confirm in a line or two; change only what the user changes. | ARC §1, §3 step 3 |
| ARC-3 | An act pitch is written at each act start, before the arc, against the existing act (read `bible act<N>` first). Acts and their days stay as `campaign.json` and the bible have them; a pitch may depart, each departure logged with a reason. The final act's pitch builds toward the ending hoped for in session zero. | ARC §1, §7 |
| ARC-4 | A charter: about 20 to 35 turns, built from what the PC actually did, serving the act pitch. The plan is pressure, never a script; the PC can walk away from all of it. | ARC §1 |
| ARC-5 | Planning sessions are user-requested; the user steers the world's direction there. Never start one mid-turn: one line under the prompt; the user may defer, and then no new arc pressure starts until they plan. | PA "Planning sessions"; ARC §2; SK-core "Arc planning" |
| ARC-6 | The retro question ("Best moment? Anything drag?") is asked only at the start of the planning session after an arc closed; record it with `feedback --kind act`. | ARC §3 step 2 |
| ARC-7 | The session steps: `plan-brief`; retro question; session zero; act pitch at an act start; launch the Opus charter brief with the last two charters; review; show the user; revise; write and approve; push so the page rebuilds and give the link; put agreed rules into the pitch's `checklist` and deferred ops into `pending_ops`, then `preflight`. | ARC §3 |
| ARC-8 | Charter rules: the promise is a question, never an outcome; pressure is forces, not secrets; set pieces are kinds, never events, and differ from the last two charters'; wins on offer are allies, information, places or reputation, never numbers; at least one backstory hook from a PC sheet or an established relationship; fronts have a goal and 2 to 4 escalating moves; the antagonist's face reaches the PC on screen by the midpoint; at least 3 clues, none tied to a scene, and no conclusion rests on one clue; at most 3 new NPCs; no line crossed, no veil on screen; no field names a PC or combat outcome; the draft answers the last retro's weakest point. | ARC §3 step 6, §4; ORC §2a |
| ARC-9 | Review a draft before the user sees it against ARC-8, plus places, NPCs and canon existing (`loc`, `npc`, `canon`) and the twist linked to a ladder or its own keywords. Edit or discard; the Planner never writes. | ARC §3 step 6; ORC §2 review |
| ARC-10 | Show the user only the shared fields plus one alternative promise; for a blind arc only the promise and tone. Never show hidden fields, even to explain a choice. | ARC §3 step 7; SK-core "Arc planning" |
| ARC-11 | Approve with `arc-approve --lines-checked` (your statement that the charter respects session zero); `--force` only when the user said to skip a check. A charter drafted before the PC sheets uses `PENDING` placeholders and `hidden.refine`; `arc-approve` refuses while `refine` has items, a shared field still says `PENDING`, or fewer PC sheets exist than `session_zero.players`. | ARC §3 step 8, §4 |
| ARC-12 | `arc-start` when the arc's first pressure shows in Voyage's output. One live arc at a time (active, or provisional after a pivot). | ARC §5; HO §4.7 |
| ARC-13 | Record `arc-move` when a front's move happens visibly in the story (fronts move on their own, WLD-1). | ARC §5 |
| ARC-14 | Pressure cards, not scene cards: for each arc scene, what each relevant NPC wants now, what they do if the PC engages and if not. No scripted opening shot; no "decision the scene ends on". The director writes them inline; the Opus Planner writes them only for showcase fights, twist reveals and finales, launched in the background two turns before the previous scene's budget ends, and checked (`thread`, `loc`, `canon`, no PC outcome) before `scene-start --card`. | ARC §5; SK-core Orchestration; ORC §2 |
| ARC-15 | In play, record `arc-clue`, `arc-contact`, `arc-reveal`, `arc-review`, `arc-deviation` as they happen, and set `arc_contact` in the turn log when the PC engaged the arc's pressure. | ARC §5 |
| ARC-16 | Midpoint review at 60% of budget: stay silent with the user unless something is off (drift, the antagonist not yet on screen, twist timing); record it. The Planner writes the off-ramps then (PIV-1). | ARC §5; HO §4.7 |
| ARC-17 | At 100% of budget: no new pressure; climax hooks wherever the PC is. At 130%: one line to the user, once: extend or wrap up. | ARC §5 |
| ARC-18 | Voyage's harmless inventions (`invention` slips) are folded into fronts at the midpoint or a scene end ("yes, and"). | ARC §5 |
| ARC-19 | Departures from the act plan are logged (`act-deviation`, `arc-deviation`) with a reason; the page shows them. | ARC §5, §7 |
| ARC-20 | Closing: write the retro yourself from the turn log (`arc-close`, at least one of best, drag, notes, weakest); it names the weakest point and the next charter answers it. Ask the user nothing mid-play. | ARC §6 |
| ARC-21 | The planner page shows only shared fields, session zero, progress and player-visible state. It is public; a spoiler refusal fails the build and leaves the last good site live: fix the leaking field and push again. After an approval, push (`wrap-up` or `save`) and give the user the link `resume` prints. | ARC §8; ROOT README |
| ARC-22 | Field reference: the charter's shared fields (title, tone, promise, premise, pressure, set_pieces, pc_tests as one category per PC, subplot, climax_kind, ending_shape, stakes as personal or wide, seeds, wins_on_offer, echoes, backstory_hooks, deviations) and hidden fields (twist with a ladder key or its own keywords, fronts, antagonist with face and first contact, clues, refine, surprises, climax_options, pc_test_situations, cast, new_npcs, notes), each with its good and bad example; the act pitch's shared fields (title, theme, question, builds_to, stakes_scale, ending_shape) and hidden ones (turning_point, notes, checklist, pending_ops). Extra keys are kept. | ARC §4, §7 |
| ARC-23 | A twist's keywords stay out of prompts until `arc-reveal` (`check-prompt` blocks them). | ARC §4, §5 |
| ARC-24 | Hooks follow the players: each front keeps a hook kit (three or more ways in through person, place and world doors); a detour gets the next hook through a door where the players already are, inside what they chose, at most one per scene, never cancelling their choice. | user 2026-10-05 ("plan like a great D&D DM") |
| ARC-25 | Replan only on disinterest: three hooks declined through at least two doors, or the user says so; each declined hook is recorded with `arc-review --kind drift`. A detour is not disinterest. | user 2026-10-05 |

### PB-sync (all new, HO §4.5)

| Id | Rule |
|---|---|
| SYNC-1 | At session end the user exports Voyage's state file; a subagent diffs it against the database and returns a mismatch report and a proposed patch. Dry-run by default; applied only on main-chat confirmation. Never auto-applied. |
| SYNC-2 | Class 1, Voyage-owned state (position, time, quest status, party): proposed from the save. |
| SYNC-3 | Class 2, anything that conflicts with a canon fact or canon trap: reported as "Voyage drift", never applied; it becomes a Studio-fix candidate or a new trap. |
| SYNC-4 | Class 3, the director layer (cast bibles, ladders, traps, promises, arc plans): untouched. |
| SYNC-5 | Voyage's tick numbering wins. Ticks played without the director are imported from the save; director turns that were undone are marked, not deleted. |
| SYNC-6 | Commit a small extracted digest; keep the raw export out of git and record its checksum. |
| SYNC-7 | Log mismatches by type so `resume` shows where inference keeps failing. |
| SYNC-8 | If the user skips the export, inferred records stay inferred. |

### PB-browser

| Id | Rule | Source |
|---|---|---|
| BRW-1 | "send" from the user is the approval to read, draft and submit. It stays a manual trigger: no polling, no auto-run. | FT; HO §4.4 |
| BRW-2 | Load the browser tools in one tool search; if the tab group shows only a blank tab, ask for the Voyage link or the tab. | FT Standing choices |
| BRW-3 | Read with one batch of page-script calls (the turn-marker snippet, then 800-character slices in the same batch; output truncates near 1000 characters; return no header string). | FT loop 1 |
| BRW-4 | The block after the last `Turn N` label is the pending input. "Waiting..." or unfinished output: stop and tell the user; never draft from stale data. | FT loop 1; HO §4.4 |
| BRW-5 | If the page's last prompt label is not `World:`, adjust the marker to the label the prompts end with. | FT loop 1 |
| BRW-6 | Submit in one batch (find the "What will happen next?" box and Submit, fill the exact prompt text, click). Confirm by re-reading the page text; no screenshots. If the text did not register, retry once, then stop and report. | FT loop 5, 6; HO §4.4 (K7) |
| BRW-7 | No panel reads, no repeated screenshots. Never click regenerate, undo or delete. | HO §4.4; ROOT handoff |

### PB-failures

| Id | Rule | Source |
|---|---|---|
| FAIL-1 | Exit 1, 2 or 3 from `record` or `commit-turn`: a bad payload or prompt; nothing was applied. Fix and rerun. | ORC §4 |
| FAIL-2 | Exit 4, "payload turn is X but the next turn is Y": the turn was recorded or the number is wrong; check `resume`; never rerun an applied turn. | ORC §4 |
| FAIL-3 | Exit 6, lock busy: wait; if it looks hung over 10 minutes, kill that process and run `recover`. | ORC §4 |
| FAIL-4 | Exit 7 or "stale write lock": `recover`, then rerun. | ORC §4 |
| FAIL-5 | Exit 5, saved locally but push failed: do not rerun; `save` (or the next `commit-turn` or `wrap-up`) retries. `wrap-up` exit 5 means "not safe to close": rerun later. | ORC §4; SK-core Saving |
| FAIL-6 | Exit 8: not on `main`; check out `main` and rerun. | SK-core Saving |
| FAIL-7 | A turn recorded wrongly: `undo-turn N` (last 5 kept), fix, record again, then `save`. | ORC §4 |
| FAIL-8 | A Planner card or charter breaks a rule: do not use it; rewrite the weak parts or reuse an earlier one. | ORC §4 |
| FAIL-9 | Repairs use `record` (all-or-nothing, turn 1 and fixes) and `save`; by hand: commit `campaigns/NAME/data` as "<Display> save: turn N" and push to `main`. | SK-core Saving; RDM Save 2 |
| FAIL-10 | Snapshots and the lock file are git-ignored scratch files; never commit them. | ORC §4 |

### PB-start: campaign start

| Id | Rule | Source |
|---|---|---|
| START-1 | PC sheet fields (pronouns, power, background, notes) come from the user only, never invented. Ask once in the first chat with the intake template (name and pronouns, power concept or "none yet", background, home base, plus the campaign's own questions from `director.md`): story facts only, no stats; Voyage keeps its own sheet. | SK-play "Player-character sheets"; RDM intake |
| START-2 | Record them with `pc-add` or `pc-sheet ... --evidence "sheet provided by the user"`. | SK-play sheets |
| START-3 | Turn 1 is Voyage's story start: `record` it with prompt "none"; the director begins at turn 2. | SK-core turn loop |
| START-4 | The campaign's opening card (`opening.md`) says what is true behind the story start; arrival scenes budget 2 turns at most. | Template `opening.md` |
| START-5 | Session zero and the first charter are optional; without them play runs on open threads and arc functions stay off (PIV-10). | HO §4.7 |

### PB-modules: hidden scores

| Id | Rule | Source |
|---|---|---|
| MOD-1 | The hidden score (Standing) changes only through `ledger +N\|-N "reason"` for established events, per its rubric. | SK-play Secrecy; RDM Arc reference |
| MOD-2 | Never a meter and never named in a prompt; Voyage hears it only through NPC hints by band (`state` shows the band). | SK-play Secrecy; BIB 10 |
| MOD-3 | It guides story pressure, never limits what a player may attempt. | SK-play Secrecy |
| MOD-4 | The debt module is hidden the same way. | RDM Spoiler note |

### REF: `director/reference.md` (tool-backed reference, read on demand)

| Id | Entry | Source |
|---|---|---|
| REF-1 | The `commit-turn` payload: `ops` (each with `evidence`; scene follow-ups and `feedback` need none), `turn_log` (`inputs`, `summary` two lines, `slips`, `notes`, `arc_contact`), optional `present`; forgiving normalisation; the prompt comes from the file. | SK-core loop 6; ORC §0 |
| REF-2 | The `record` payload (`turn` must be `state.turn + 1`; all or nothing; `save: true`) and the worked example. | ORC §1 |
| REF-3 | The op table with arguments. | ORC §1 |
| REF-4 | Slip tags: `fact`, `invention`, `teleport`, `outcome`, `dropped`, as "category: text" separated by `;`. | SK-core loop 6; ORC §1 |
| REF-5 | Statuses: arc NPCs and quests are `planned` until they appear, then `in_play` or `active`; main NPCs start `world`; `pos` refuses unknown places. | SK-play update rule |
| REF-6 | Time words map to the campaign's time blocks. | ORC §0 |
| REF-7 | Names: `aliases`, derived short forms, `name_skip_tokens`, `use_full_name`, and `canon_traps` `match` lists. | ORC §0 Names |

### AG: subagent briefs (`director/agents/`)

| Id | Rule | Home | Source |
|---|---|---|---|
| AGT-1 | Hard rules for every brief: read-only (lookups only; no updates, files, git or commits) unless named the writer; you are not directing; existing locations and areas only; at most one ladder step and only the next revealable one; no PC or combat outcomes; main NPCs follow their brief; no canon that contradicts canon or state; new minor NPCs allowed with an intro line of 90 characters or fewer; compact output. | AG-common | ORC §2 hard rules; HO §4.3 |
| AGT-2 | Charter draft brief: inputs, lookups to run, output (charter JSON, a 5-line direction summary, one alternative promise). Rules by reference to ARC-8 and ARC-22. | AG-charter | ORC §2a |
| AGT-3 | Pressure card brief: inputs, lookups, the 8 headings, about 500 words at most, more of what landed and less of what dragged. Rules by reference to ARC-14. | AG-card | ORC §2b |
| AGT-4 | Off-ramp and pivot mini-charter brief (PIV-1, PIV-4, PIV-5). | AG-pivot | HO §4.7 (new) |
| AGT-5 | Studio, cast and world work brief, including the `expression` kit: derived from the cast entry, one short line each, surface behaviour only, never leaking a hidden fact, a still-hidden ladder step or past `wont_do_yet`; the bible-versus-data rule (the design in the bible wins; data is corrected before play); quest names are non-spoiling. | AG-world | EXP kit; template `arc-bible.md` intro; RDM Quests |
| AGT-6 | Sync brief (SYNC-1 to SYNC-8; the save's structure comes from `tools/new_campaign.py` `import_world` and `campaigns/joestar/docs/migration.md`, never from reading the export in chat). | AG-sync | HO §4.5 (new) |
| AGT-7 | Director review brief: audit the last N turns against BOOT agency rules, CHK-1 and the NPC rules; report the director's own slips; check `World:` lines for steering toward a ready plan (off-ramp tilt) and NPCs moving goalposts. The director review runs on Opus; canon audit and act retro stay on Sonnet (D24). | AG-review | HO §4.6.5, §6 (new); HO2 §2 |
| AGT-8 | Resume digest and recap brief: 3 to 5 lines, never hidden data, passes the scan, for the table only (never pasted into Voyage). | AG-resume | `recap -h`; RDM; HO §4.3 |
| AGT-9 | Implementer brief: Sonnet; `main` only; tests change in the same commit as the code; run the suite; never read world files. | AG-dev | HO §3, §6 |
| AGT-10 | Scaffold brief: `new_campaign.py`; `campaign.json` (with `voyage_title`, canon traps, main and fixed NPCs, acts); `director.md` slots (world file, calendar, earned changes, an overreach example, consent rules for scripted quests, hidden-score tone if a module is on, intake questions, any narrowed rules per SHEET-1); bible headings keep the words `Time skips`, `Obstacle and surprise rules`, `Scene turn budgets` and `Act N: Name (Days a to b)` so lookups work. | AG-scaffold | Template `arc-bible.md` intro; ROOT README |

### PB-sessions: `director/playbooks/sessions.md`, sessions, models and effort (handoff 2, all new)

| Id | Rule | Source |
|---|---|---|
| SES-1 | Play runs as two sessions: a director session (the turn loop only; the only writer of turn data) and an Opus planner session (everything off the clock: arc work, pivot drafts, pressure cards, off-ramps, midpoint and drift checks, planning talks with the user, and launching the sync, Studio, recap, audit and review subagents). All-in-one, one session doing both, is the fallback and must work fully. | HO2 §1 |
| SES-2 | The repo is the channel; messages are only nudges. Each session has its own clone. The director pushes every turn; the planner pulls, reads the turn log and commits its output as files in `campaigns/NAME/planner/`. After the prompt is out, `commit-turn` fetches, and the next brief shows one line when new planner output is waiting. Play never waits for a message or its answer. | HO2 §1 |
| SES-3 | Nudges from director to planner, one line each: scene end, day change, an input that commits to a new goal, session end. A missed nudge costs nothing; the planner can poll the turn log. | HO2 §1 |
| SES-4 | Writes do not overlap. The director session is the only writer of campaign data, arc plans included; the planner writes only its own files under `campaigns/NAME/planner/`, and the director applies them at a break with the existing commands (`arc-plan --file`, `arc-offramps --file`, `scene-start --card`, `arc-adopt`). A sync patch or review finding is likewise a proposal the director applies (D8, D15). | HO2 §1; D23 |
| SES-5 | At chat start the menu asks the session's role (director, planner or all-in-one) and stores it with the campaign choice; each role reads only its own playbooks. "send" as the first message means director, or all-in-one when no planner output has been touched this session; no extra round trip. | HO2 §1 |
| SES-6 | All-in-one: the director launches the planner's jobs as subagents at breaks (scene end, session end), never on the clock; off-ramps stored in the data keep a plan ready when no planner session runs. | HO2 §1 |
| SES-7 | Hidden plan material is worked on in the planner session, which the user need not open during play; everything user-facing still passes `db.py scan`. | HO2 §1 |
| SES-8 | Model and effort, a recommendation the user sets at session start (a session cannot change its own model or effort): routine turns Opus at medium effort; escalated turns Opus at high; never low effort; Sonnet at medium is an acceptable fallback for a long quiet stretch, switching back for any escalated turn. The planner session runs Opus. | HO2 §3 |
| SES-9 | Speed is measured: each turn log records when its `check-prompt` first ran and when `commit-turn` ran (and `--received`, when the input arrived, if known); `resume` shows the median of the last 20 turns, routine and escalated apart. | HO2 §0 |

## 5. Source coverage (every source line maps to an id above or in section 6)

| Source | Ids |
|---|---|
| SK-core Roles | ROLE-1, REPO-1 (files and commands), CHAT-6, DATA-1, WF-1 |
| SK-core Start of a chat | REPO-1, VER-1, CHAT-1, CHAT-2, TRIAL-1, CHAT-3, BRW-1, X-1 |
| SK-core Saving | SAVE-1, SAVE-2, FAIL-5, FAIL-6, FAIL-9 |
| SK-core Orchestration | LOOP-2, ORCH-6, CHAT-5, ARC-14, X-4, ORCH-1 |
| SK-core Arc planning | TRIG-12, ARC-5, ARC-10, REPLY-2, ARC-16, ARC-17, DRIFT-1, SCN-7, ARC-19 |
| SK-core Turn loop | LOOP-1, START-3, LOOP-2, TRIG-1, LOOP-6, CHAT-2, CUT-5, LOOP-3, LOOP-4, RET-1, RET-2, RULE-1, INV-1, SCN-1, CUT-4, SCN-6, SCN-4, SCN-5, SCN-8, CHK-2, LOOP-5, REF-1, REF-4, REPLY-1, REPLY-2, REPLY-3, STU-6 |
| SK-core Prompt format | FMT-1, CUT-1, CUT-2, TONE-1, CREW-1, FACTS-1, WORLD-1, FMT-2, FMT-3, FMT-4, FMT-5, AGY-2, AGY-6, FMT-8, SPL-12, TRIG-10 |
| SK-play Director rules | AGY-2, AGY-3, AGY-4, AGY-1, CUT-4, SCN-2, X-5, RULE-3 |
| SK-play Main NPCs | CREW-2, NPC-1, NPC-2, NPC-3 |
| SK-play DM principles | RULE-2, WLD-1, SIDE-2, X-9, FMT-7, SIDE-1, WLD-2, REV-4, NPC-1, INV-1, REV-1, REV-3 |
| SK-play Fights | FGT-1 to FGT-6 |
| SK-play When players leave the arc | LEAVE-1 to LEAVE-5, WLD-1 |
| SK-play Retcon | RET-1, RET-3, RET-5, RET-6, STU-9 |
| SK-play Studio | STU-1, STU-3, STU-5, FMT-3 |
| SK-play The update rule | DATA-1, LOG-1, REF-5, LOG-3 |
| SK-play Player-character sheets | START-1, START-2, STATE-1 |
| SK-play Secrecy, consent, romance | MOD-1 to MOD-3, SEC-1, NPC-7 |
| FT | X-1 (precedence), ORCH-3, BRW-1, ORCH-2, X-3, CHK-1, BRW-2, BRW-3, BRW-4, BRW-5, LOOP-3, LOOP-6, TRIG-1 to TRIG-9, FMT-1, LOOP-5, BRW-6, X-7, LOG-2, SCN-3, LOG-3, SAVE-1, X-8, REPLY-1, REPLY-2, SCN-6 |
| PA | X-1, AGY-5, WLD-4, WLD-1, ARC-5, FMT-6, RULE-4, AGY-2, AGY-3, X-16, RET-5, AGY-7, CUT-2, CUT-4, NPC-4, NPC-5, FACTS-1, RULE-5, LOG-4, NPC-6, TONE-1, FGT-7, FMT-7, CHK-1 |
| ORC | X-10 (pointer), ORCH-1, ORCH-6, LOOP-2, X-11 (prep description), FGT-3, LOOP-5, REF-1, REF-6, REF-7, FMT-4, CHK-2, REV-3, RET-2, REF-2, REF-3, REF-4, AGT-1, AGT-2, AGT-3, ARC-8, ARC-9, ARC-14, X-4, FAIL-1 to FAIL-10 |
| ARC | ARC-1 to ARC-23, TRIG-12, DRIFT-1, SCN-7, WLD-4, PIV-9, CHAT-4, X-1 |
| STU | STU-1 to STU-10, RET-1, RET-3, RET-4, REV-6, SEC-1 |
| SPL | SPL-1 to SPL-12, CUT-1 |
| EXP | CREW-1, AGT-5, X-12 (tool behaviour) |
| BIB | CUT-2, CUT-3, CUT-4, CUT-5, SCN-2, SCN-4, SCN-5, WORLD-1, FGT-6, MOD-2, X-5 |
| RDM | DATA-1, LOG-1, WF-1, CHAT-6, FMT-5, FMT-11, AGT-5, AGT-8, REV-5, NPC-7, START-1, REPO-1, REPO-3, SAVE-1, FAIL-9, TRIAL-1, SEC-1, MOD-4 |
| ROOT | CHAT-2, CHAT-3, CREW-2, LEAVE-1, RET-5, BRW-7, ARC-21, AGT-10, X-13, X-14 |
| Template fills and `opening.md` | LOG-5, START-4 |
| Retirement-only lines | X-2 (SK-core, FT, PA), X-6 (SK-core, ORC, RDM), X-15 (campaign copies) |
| HO2 (handoff 2) | SES-1 to SES-9; changes to LOOP-2, LOOP-6, ORCH-3, CHAT-1, CHAT-5, MENU-1, TRIG-18 |
| HO (new rules, no earlier source) | REPO-2, SEL-1, SEL-2, MENU-1, SHEET-1 (from K30), ORCH-4, ORCH-5, FMT-10, STATE-2, STATE-3, STATE-4, REVIEW-1, TRIG-11 to TRIG-17 (pointers for the new and existing playbooks), WLD-3, SPL-13, PIV-1 to PIV-10, SYNC-1 to SYNC-8, START-5, AGT-4, AGT-6 to AGT-9 |
| CFP (Campfire's campaign-helper proposal, items 1 to 8, approved 2026-10-05) | CFM-1, TRIG-19; notes on LOOP-2 and FACTS-1 (skipped in Campfire mode) |

## 6. Retired rules

| Id | Rule | Source | Reason |
|---|---|---|---|
| X-1 | Precedence statements ("they win over this file", "wins over", "still wins") | SK-core Start 5; FT; PA; ARC header | One home per rule; banned by a test (K18). |
| X-2 | "Read `fast-turn.md` and `player-agency.md` now" | SK-core Start 5; FT; PA | Their rules now live in BOOT and CORE, which load at chat start. |
| X-3 | `prep` with a 60-line screen every turn; and "no `prep` or paste file on routine turns" | SK-core loop 1; FT | Replaced by the lean brief every turn (K1, user-approved). |
| X-4 | Cast subagents (one Sonnet subagent per NPC for 4+ speaking main NPCs or "full cast") and the Cast brief | SK-core Orchestration; ORC §3 | The turn stays in the main chat (K5, HO §4.3). |
| X-5 | Offer one skip at lulls; offer a weekly montage via an NPC or phone notice | SK-play rule 3; BIB 8, 12 | Skips follow the input and the director never offers one (K4); confirmed by the user (Q3). |
| X-6 | Push every 5 turns (`push_every` 5) | SK-core Saving; ORC; RDM | Push every turn (K2). |
| X-7 | Confirm the submit with a screenshot | FT step 6 | Re-read the page text (K7). |
| X-8 | "The Stop hook flags unpushed commits" | FT step 7 | Not a director rule (environment behaviour); `resume` and the brief show "unpushed: N". |
| X-9 | "If a thread becomes the table's favourite, sketch a direction for the user (the Planner re-plans)" | SK-play DM | Replaced by the pivot flow (K13). |
| X-10 | "Read only when needed; the rules live in SKILL.md" pointers at the top of each doc | ORC, ARC, STU, EXP | The trigger table replaces the pointers. |
| X-11 | Descriptions of what `prep`, `commit-turn`, `record` and `wrap-up` print | ORC §0, §1 | Tool behaviour, kept in `db.py -h` (TOOL), not rule text. |
| X-12 | "`check-prompt` WARNs on flat verbs", "`brief` shows 'expression: not set'" | EXP | Tool behaviour (TOOL). |
| X-13 | The generic-rules sync flow: `Generic rules:` line, `sync_skill.py`, bump and re-upload per campaign, the 15,000-byte cap | ROOT README; SK header; tests | One uploaded skill with a version line (VER-1); removed at switch-over. |
| X-14 | Root `handoff.md` (2026-10-03) as a rule source | ROOT | Historical; superseded by `docs/revamp/handoff.md`. Archive at switch-over (user's call). |
| X-15 | Copies of the generic docs in each campaign (`docs/orchestration.md`, `arc-planning.md`, `studio.md`, `expression.md`, `fast-turn.md`, `player-agency.md`, `split-scenes.md`) | campaigns/*/ | One home per rule; removed per campaign at its switch. Joestar's and Luxcellia's `arc-planning.md` are already an older version. |
| X-16 | If Voyage voiced the PC, end the next prompt with "<PC> says and does nothing beyond the player's input." (was FMT-9) | PA "The player character" | Removed for now by the user (2026-10-04), the same for every campaign; Voyage's extra PC lines are left as they are. The live skills keep their current docs until each switch. |

## 7. Decisions I made (also recorded in `docs/revamp/decisions.md`)

- **D1.** Four playbooks and one reference file beyond the handoff's list: PB-pacing (scenes, budgets, acts, day turnover), PB-reveals, PB-start, PB-modules, and `director/reference.md`. Each has a clean trigger, and keeping them out of CORE is what lets CORE stay near 6 KB.
- **D2.** The stay form of `Cut:` is "Continue at <Location/area>, same moment." (K8).
- **D3.** After a pivot the old arc is `parked`; "approve" makes the new arc active, "re-aim" redrafts it with the user, "go back" revives the parked one; `set_aside` stays for an arc dropped for good (K12; revised in phase 2).
- **D4.** Subagent briefs reference playbook rules by id instead of copying them, so a rule never has two homes (for example, the charter brief points at ARC-8).
- **D5.** Campaign-specific rules (section 9) move to `campaign.json` or `director.md` at each campaign's switch, not before.
- D6 to D8 concern commands; see `decisions.md` and `function-inventory.md`.
- **D9.** Without arc functions, "no arc is live" is a one-line planning offer at chat start, never a per-turn trigger (K27).
- **D10.** Variety tags map to session zero's pillars for retros: fight to combat, talk to social, explore to exploration, mystery to mystery; downtime is reported on its own (K29).
- **D11.** A campaign's `director.md` may narrow a generic rule and must name the id it narrows; it never loosens a BOOT invariant (SHEET-1, K30).

## 8. The user's answers (2026-10-04)

- **Q1. Turn order.** Option A, in both modes: brief, `check-prompt`, send the prompt, then `commit-turn`. Recording and the push happen after the prompt is out, while the player reads Voyage's output (LOOP-2, ORCH-3, K19).
- **Q2. Push every turn.** Yes: the tool default becomes 1 and Joestar's `"push_every": 5` goes (SAVE-1, K31). Tool and config change in phase 3.
- **Q3. Skips.** The director never offers a skip, weekly montage included (CUT-2, X-5).
- **Q4. `state-new.txt`.** Deleted from the repo in `cc4650e`. It is still in git history; removing it from history would need a force push, which has not been done.
- **Q5. Voyage-voiced PC lines.** The repair line is removed for now, the same for every campaign (X-16, K15). The current skills and their docs stay as they are until each campaign switches.
- **Q6. Tests.** pytest is installed in the sandbox from its GitHub sources (see `decisions.md`).

## 9. Campaign-specific rules (moved at each campaign's switch)

| Id | Rule | From | To |
|---|---|---|---|
| WR-C2B-1 | World file and act boundaries (Days 7, 42, 77) | WR Class 2B | CAMP `acts` (already there) |
| WR-C2B-2 | Canon traps: room numbers are door labels; Shin uses surnames in Act 1; Shimazu and the House Manager are different; "Sunny" and the arrival days | WR Class 2B | CAMP `canon_traps` (already there; duplicate removed from the skill) |
| WR-C2B-3 | Invented admin rules: fix harmful ones with a plain fact; keep harmless ones | WR Class 2B | CAMP `canon_traps` (missing there today) |
| WR-C2B-4 | Main NPCs; earned changes (Shin's first names, Tatsuya's release, Mio's confession); the House Manager needs no intro line | WR Class 2B | CAMP `main_npcs`, fixed NPCs; SHEET earned changes |
| WR-C2B-5 | Standing: Day 42 Shimazu calls 2B failing regardless, tone scaled to the band; the tutorial quest is player-directed (never invent the ability, account or consent) | WR Class 2B | SHEET |
| WR-C2B-6 | Studio: act starts are Days 1, 8, 43 and 78 (act-start bundles); the campaign's never-inject list (the Standing score and thresholds, Mio's debt and rig, Sunny's and Ayame's video, Shin's gang, the Annex roles, Yūto's scar, the Nine Corners' plan) | Class 2B `docs/studio.md` | CAMP `acts`; the never-inject list in SHEET (the tool's check covers only what `hidden_words`, `secrets` and the ladders hold) |
| WR-JOE-1 | World file, calendar, players and hard lines in README, engine notes | WR Joestar | SHEET |
| WR-JOE-2 | Canon traps (five bullets) | WR Joestar | CAMP `canon_traps` |
| WR-JOE-3 | Main NPCs (the crew, Rei, Anya, Riko, Aurelia, Maki, Tetsu, Gara, Daigo); Arc 4's villains stay hidden (ladders); earned changes (Rei joins, Rikona's yes, Ayame's date, Reiko's talk); two PCs; romance at the NPC's pace; no ally betrayals; the spoiler split (the user approves premise, set pieces, ending shape, recruit seat and tests by category; the director keeps twists, sheets, fork doors); "they love fights and relationships: earned wins"; tests, never outcomes (Jostin love and home, Jovian strength and purpose); overreach example ("recruit Rei" is only the attempt) | WR Joestar | CAMP `main_npcs`; SHEET |
| WR-JOE-4 | Hard lines (no ally betrayals, no cliffhanger tails, no invented deadlines, no named deaths without OK, no off-screen relationships): removed by the user on 2026-10-05 | WR Joestar | none (retired) |
| WR-JOE-5 | Studio and world file: `worlds/joestar-save.json` is Voyage's own save; Studio work and imports use it; never edited by hand; a newer save replaces it and is re-merged with Voyage's keys winning; Studio requests use Voyage's exact keys (Club Lumière, Tetsu Iron Palm Gym and Ward Licensing Services are locations; the gym wing is the area `combat-gym`) | Joestar `docs/studio.md` | SHEET; the save handling becomes PB-sync's job |
| WR-LUX-1 | World file; single player; Party and Bonds rules (campfire rule, NPC chemistry, bond firsts, companion table time); act days; no hidden score | WR Luxcellia | SHEET; CAMP `acts` |
| WR-LUX-2 | Canon traps (four bullets) | WR Luxcellia | CAMP `canon_traps` |
| WR-LUX-3 | Main NPCs, earned changes, fixed NPCs, overreach example; chain quests are Voyage's (never seed or track; a narrowing under SHEET-1); scripted beats need consent | WR Luxcellia | CAMP; SHEET |
| WR-LUX-4 | Studio: act starts Days 1, 15, 46, 76 and the act bundles (Act 1: the Mizuho edit and Kazuki Ōhara; Act 3: Archbishop Isamu Tokiwa and an Almonry faction touch; any act: a fourth-seat NPC when the bond calls for one); the Mizuho edit is needed before her Day 4 beat (until then an unnamed registrar speaks for her in a letter); the campaign's never-inject list | Luxcellia `docs/studio.md` | SHEET |

Joestar's own docs (`engine.md`, `rules.md`, `story-design.md`, `org.md`, `pc-sheets.md`) are campaign-layer and out of scope. One part is generic and worth lifting later: the table in `engine.md` that explains why the core rules exist (one beat per turn, passive NPCs, literal reading). It could become a short "Why" note in `director/` if you want it.
