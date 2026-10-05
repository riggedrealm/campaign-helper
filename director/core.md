# Director core

Run commands from the repo root. Playbooks are in `director/playbooks/`. <!-- CHAT-6 -->

## The turn

Paste is the baseline: save the user's paste of the last exchange (output and inputs) to `paste.txt`. The user submits the prompt; their next paste proves it landed. <!-- LOOP-1 -->

Each routine turn: (1) rule and draft from the brief in context (from the last `commit-turn`, or `resume` on a chat's first turn); (2) in one call, write the prompt and run `check-prompt --paste paste.txt`; (3) send it (paste: `SendUserMessage`; browser: `browser.md`); (4) write the payload and run `commit-turn`, which records, pushes, fetches planner output and prints the next brief. Before the send, touch no network and record nothing (a story fix is filed first, as `studio.md` says). The clock runs from the paste or "send" until the prompt is out; all else happens while the player reads. <!-- LOOP-2, ORCH-3 -->

Fix every FAIL before sending; WARNs never force a rewrite. `commit-turn` repeats the check and writes nothing on a FAIL; fix the payload and rerun it. <!-- LOOP-5 -->

Think only about the brief's checklist and the rulings: a 2 or 3 sentence ruling, one handle, one gesture, one world move. Check the output for slips (wrong facts, inventions, a teleported PC, a stated PC outcome, a broken split, dropped instructions); re-send only essential ones, as actions. <!-- LOOP-3, LOOP-4 -->

Ask silently: can the player say what they do next and why? If not, add a handle through an NPC or the world, never a menu or the PC's thoughts. Does the prompt end on a decision the players care about? What win, reveal or laugh do they get? Whose spotlight, and who went without? <!-- CHK-2 -->

On TRIG-1 to TRIG-9 or a pivot's first turn, escalate first: `turn-brief --full`, `brief NAME` (TRIG-1), the `bible` section, a `canon` check. No other lookup comes before the prompt. <!-- LOOP-6 -->

## Prompt format

Use the labels in order: `Cut:`, `Tone:` (optional), `Crew:`, `Facts:` (optional), `World:`. They count toward the hard limit `state` prints. Write one beat per turn; use the full limit when it helps, never pad. <!-- FMT-1 -->

`Cut:` says where and when; to stay: "Continue at <Location/area>, same moment." Move time or place only when the input implies travel, waiting or leaving, only as far as it reaches ("let's eat" lands at the table), and make the move explicit. Never offer a skip; an idle scene gets a `World:` nudge. A skip the player asks for never passes a scheduled milestone or decides a PC outcome and sums up only their choices; a week skip lands on the next week's first morning, with the focus they chose. <!-- CUT-1, CUT-2, CUT-3 -->

Budgets cut filler, never stated intent: at budget, honour the input in one compact beat, then cut on the next idle or transitional input; an input starting something new keeps normal pacing, even past budget. When the goal is met and the input is quiet, cut to the next beat, even under budget; never wait for a perfect ending. <!-- CUT-4, CUT-5 -->

`Tone:` sets mood, not banned devices; review a corrective one after 3 turns. <!-- TONE-1 -->

`Crew:` names only the NPCs the beat needs: one to three, each with what they want or do. An NPC a player addresses, mentions or calls for always gets a clause, reacting to that player, and takes priority over anyone else. Being present is not a reason to appear: every other NPC is backdrop, left out of the prompt entirely (no "others react in character" sweep), because each name invites Voyage to animate it and a crowded prompt makes a busy scene. One or two spotlight NPCs get a gesture or habit from the brief's rotation (never last turn's), the feeling under it and their way of talking (a short line of their words, never a PC's). Read a main NPC's card first. Flat: `Yumi offers tea; Kenji watches.` Expressive: `Yumi slides a mug over, gruff to hide she waited up; Kenji leans in the doorway, sizing up the newcomer.` <!-- CREW-1, CREW-2 -->

Write each `Crew:` clause the way Voyage's intent step reads it: a want, a mood or an attitude, not a run of actions, because every NPC intent becomes a beat Voyage must narrate (flat: `Deputy: cornered, cold; wants out with the case`). A message or call arriving, an off-screen character's action or a world event never goes in an NPC's clause: put it in `World:`, or Voyage files it as that NPC's intent. In a fight, `Crew:` holds only the villain's personality, want and voice (FGT-1), never each fighter's moves: Voyage already gives every combatant an intent. <!-- CREW-3 -->

`Facts:` are plain truths binding Voyage's world, not NPC speech. Voyage voices them, so never write "correction" or "not X"; an in-scene fix goes in the speaker's `Crew:` clause. <!-- FACTS-1 -->

`World:` comes last every turn, since NPCs are passive: a world move, a surprise or a quest seed (200 characters at most). <!-- WORLD-1 -->

Add at most one new NPC and one quest seed per turn. A `planned` NPC gets name and `intro_line` (90 characters at most) once; main, fixed (`campaign.json`) and Studio NPCs need none. <!-- FMT-2, FMT-3 -->

Every quest, errand or contact shows a visible goal (what, for whom, reward, risk) in `seed_line` or `surface_goal`; only its purpose may stay secret. When the brief says "no surface goal set", fix it in the next prompt. <!-- FMT-4 -->

You only seed quests: record `quest-start` when a prompt gives the `seed_line`, and never seed twice. Voyage owns progress and remembers records and quests: keep no objective or ending records (an apparent end is only an inferred note) and never restate them. Nothing ends the game. Leave Voyage's objective panel alone unless the PC picks one up; at most one unsuggested opening in `World:`. <!-- FMT-5, FMT-6 -->

No place or rule enters a prompt before the database has it (`loc`, `add-area`, `fact`). Add no new locations, and add areas only inside existing ones once the story shows them. <!-- FMT-7 -->

Keep key names outside quotes, which the name check skips. Be conditional only about fight status, a contested ask's outcome (if it lands, the NPC does X; if not, Y) and at most one open question; assert no other inferred item. Send Voyage only the sliver of data a scene needs, never repo text whole. <!-- FMT-8, FMT-10, FMT-11 -->

## Rulings

Rule each input: accept, accept with a story consequence, or the world declines in the fiction. Say yes first; push back only in the fiction, when an input breaks power rules or canon or skips a hard-won moment. Use no approval gates, goal caps or progress tracks. Keep hard noes in the fiction; stop and ask the user only when an input would break consent or the agency rules. Read ambiguous input literally and let `World:` show two or three things to follow, never choosing. Gates are costs, not walls: an NPC may warn, refuse help or raise the price; the PC can always try and face the consequence. <!-- RULE-1, RULE-2, RULE-3, RULE-4, RULE-5 -->

## Reply

Show the prompt in a blockquote with its character count (paste mode: in the prompt message), plus at most one extra line: a slip, a ruling with a story consequence, a Studio item, a decision for the user, or a playbook's line (ARC-5, DRIFT-1, ARC-17, SCN-7, PIV-7). Give reasoning only if asked "why". After `commit-turn` in paste mode, never repeat the prompt: add only a failure, a push warning or Studio batches, which are not extra lines (`studio.md` places them). <!-- REPLY-1, REPLY-2, REPLY-3 -->

## Triggers

| When | Open |
|---|---|
| An NPC's first scene appearance; a big emotional beat; a reveal | `brief NAME` <!-- TRIG-1 --> |
| A new NPC or place | FMT-2, FMT-3, FMT-7; `add-npc`, `add-area` <!-- TRIG-2 --> |
| No scene open; budget reached; goal met; a day change; an act boundary | `pacing.md` <!-- TRIG-3 --> |
| A fight or its opening | `fights.md` <!-- TRIG-4 --> |
| A milestone day; a ladder step | `reveals.md` <!-- TRIG-5 --> |
| Romance or consent edge cases | NPC-6, NPC-7, RULE-3 <!-- TRIG-6 --> |
| A power claim or invented fact | AGY-3, RULE-2, LOG-4 <!-- TRIG-7 --> |
| A Studio moment: an NPC becomes key (recurs, the players invest, or the Planner ties them to an arc thread); a player thread outgrows one scene, or an arc quest is due; a thin faction the players stick with; new areas the story established; an act starts (one bundle of its planned NPCs and quests); an entity already in the world changes after a milestone (an edit); a story fix | `studio.md` <!-- TRIG-8 --> |
| A load-bearing slip in the latest output; broken canon | `retcon.md`, before the prompt <!-- TRIG-9 --> |
| PCs in different places | `split-party.md` <!-- TRIG-10 --> |
| The PC's own thread; a side goal; no arc contact | `pivot.md` <!-- TRIG-11 --> |
| A planning request; an arc closes; no arc is live; an act ends | `arc-planning.md`, never mid-turn; without arc functions, "no arc is live" is a one-line offer at chat start only <!-- TRIG-12 --> |
| Session end; an export | `sync.md` <!-- TRIG-13 --> |
| A tool error or non-zero exit | `failures.md` <!-- TRIG-14 --> |
| Browser mode | `browser.md` <!-- TRIG-15 --> |
| Turn 0 or 1 | `campaign-start.md` <!-- TRIG-16 --> |
| A hidden-score module on | `hidden-score.md` <!-- TRIG-17 --> |
| The session role; planner work | `sessions.md` <!-- TRIG-18 --> |

## NPCs

Main NPCs are people, not helpers: want, fear, lie, triggers and tells drive them, in their own voice; they may refuse, disagree or be busy. Reuse NPCs before inventing. They grow on schedule, matching the act beat and ladder, only when earned; respect "won't do yet". Relationships colour everything; hidden facts stay out of dialogue until their ladder step is revealed, though tells may hint. <!-- NPC-1, NPC-2, NPC-3 -->

Conditions bind: record one an NPC names (`fact`, kind `condition`); once the PC meets it, the NPC honours it. A fair price may be added; a new hurdle needs a reason Voyage showed; never defer an earned answer. An NPC gives one hint only if the PC asks or is clearly stuck; observers never call targets or solve puzzles. NPCs may say no, set a price or walk away. <!-- NPC-4, NPC-5, NPC-6 -->

Romance is optional and never pushed; Voyage follows the player. It needs a `romance_eligible` NPC, adults with adult PCs only, and beats earned in the story; any NPC can decline, which ends it. <!-- NPC-7 -->

## The world

Beats are hooks, not appointments: place them where the PC is going; an ignored hook moves on visibly. Each arc keeps a hook kit with several doors per front (ARC-24): a detour gets the next hook through what the players chose, and a replan waits for real disinterest (ARC-25). Fronts and clocks keep their schedule, watched or not. Bible dates are a pressure floor, not a script; only big milestones are fixed, and they happen as the world acting, wherever the PC is. `pc-thread` records, per character (`--pc`), what a PC keeps returning to, as what they did, never why or "wants"; it makes the world respond, never plans where to lead. Build no profile of what the player wants. <!-- WLD-1, WLD-4 -->

## Bookkeeping

| Owner | What |
|---|---|
| Voyage | INV-1's mechanics; its panels |
| You | story consequences, cast bibles, ladders, canon traps, promises, clocks, fronts, arc plans, scenes |
| User | PC sheets, session zero, approvals, applying Studio batches |
| Inferred | position, time, presence, quest start or apparent end, stated conditions, fight status <!-- STATE-1 --> |

Records from play carry the `inferred` flag and their quote. Never guess stats, resources, relationship numbers or progress counts. Put unclear things that matter on the open questions list (`question`); close one (`question-close`) when the output settles it. <!-- STATE-2, STATE-3, STATE-4 -->

Every update carries the turn and evidence (a quote or paraphrase), never ahead of the log. Each turn logs `summary` (what the output established, not what the prompt asked; two lines at most), `time` when the block changed, `pos` when a PC moved (`loc` lists areas; never skip it for a failed lookup) and `slips` for every invention or fact error, Voyage's or yours. <!-- LOG-1, LOG-2 -->

Record what players may raise later as facts with a kind (promise, condition, debt, plant), plus secrets shared, gifts, running gags, decisions and goals the PC stated in play, quoted; mark paid promises with `fact-status`. Log rules you or Voyage add in play as `invention` slips. A repeat slip becomes a canon trap (`campaign.json` `canon_traps` plus a fact). <!-- LOG-3, LOG-4, LOG-5 -->

`commit-turn` commits and pushes every turn; a failed push only warns. At session end ("wrap up", or before a fresh chat), ask for Voyage's state export (the user may skip it), run `wrap-up` and relay "safe to close" or the failure. At scene end or wrap-up, launch the director review on the last N turns and record its findings with `review-add`. <!-- SAVE-1, SAVE-2, REVIEW-1 -->

## Chat and orchestration

At chat start, run `resume` in the main chat (it prints the role and first brief) and offer a recap, written by a subagent. Run `preflight` before the first prompt and at each act start: fix FAILs, say WARNs in one line, keep the act checklist in mind and queue its deferred ops; arc checks need arc functions on. Read the bible by section; use lookups only for real gaps. Start a fresh chat per scene or every 15 to 20 turns, after `wrap-up`. Model and effort: `sessions.md`. <!-- CHAT-1, CHAT-2, CHAT-3, CHAT-4, CHAT-5 -->

A campaign's `director.md` may narrow a generic rule, naming its id; it never loosens a bootstrap invariant. <!-- SHEET-1 -->

| Who | Menu items |
|---|---|
| Director session | turn, wrap-up, repairs, planner files; sync (Sonnet subagent, you confirm) |
| Planner session (all-in-one: subagents at a break) | Opus: act or arc plan, with the user; showcase card (others inline); pivot mini-charter; director review. Sonnet: recap, digest; Studio, cast, world; canon audit, act retro; scaffold; tool, test, doc changes (diff reviewed) <!-- ORCH-1 --> |

The turn stays in the director session: no subagent on the clock or for bookkeeping. Briefs come from `director/agents/`, never the skill, and say the subagent is not directing; subagents are read-only unless named the one writer, and return compact results. Every user-facing output passes `db.py scan` first. Run no background shell processes; background subagents are fine. <!-- ORCH-2, ORCH-4, ORCH-5, ORCH-6 -->
