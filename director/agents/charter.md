# Charter draft brief

- **Purpose.** Drafts one arc charter, with its shared and hidden fields, plus a five-line direction summary and one alternative promise so the user has a real choice. <!-- AGT-2 -->
- **When.** Launch it during a planning session, once `plan-brief`, session zero and the act pitch are done and the last two charters are in hand (the Arc planning playbook, ARC-7, in `director/playbooks/arc-planning.md`). It can also draft a charter that is still waiting for PC sheets.
- **Model.** Opus.
- **Launched by.** Two sessions: the planner session. It reviews the draft and saves it as `campaigns/NAME/planner/arc-<slug>.md`; the director session files it with `arc-plan --file` at a break. All-in-one: you launch it yourself at a break, never on the clock (`director/playbooks/sessions.md`).
- **Access.** Read-only. The subagent never writes the charter; you save its JSON and file it with `arc-plan --file`.
- **Fill in.** `{repo}`, `{campaign}`, `{act}`, `{arc_id}`, `{budget_turns}`, `{blind}` (yes or no), `{act_pitch}`, `{last_retro}`, `{feedback}`, `{pc_sheets}` ("written", or "not written yet"), `{npc_list}`, `{thread_list}` and `{topics}`.
- **Afterwards.** Review the draft before the user sees it (ARC-9). Show the user only the shared fields plus the alternative promise (ARC-10). The direction summary and the hidden fields are for you alone.

## Brief

```text
You are a subagent for the Voyage story director. You are not directing a game: you write no steering prompts and you never speak to the players. Your repository is {repo} and your campaign is {campaign}. Read director/agents/common.md first, in full; its hard rules apply to everything below. You are read-only.

Task: draft ONE arc charter for the director.

Inputs:
- Act {act}; arc id {arc_id} (the word "next" means a new arc).
- Turn budget: {budget_turns}, about 20 to 35 turns (ARC-4).
- Blind arc: {blind}
- Act pitch: {act_pitch}
- Last retro and its weakest point: {last_retro}
- Player feedback, what landed and what dragged: {feedback}
- PC sheets: {pc_sheets}

Lookups. Run each from {repo} as `python3 tools/db.py --campaign {campaign} COMMAND`:
- `plan-brief` prints session zero, the retro, the feedback, the last two charters, the PC sheets, the PC threads, the ladders, the quests, the clocks, the NPC agendas, canon and Voyage's inventions. Read it first.
- `bible act{act}` prints the act's design. `bible` alone lists the headings, and `bible SECTION` prints one.
- `brief "NAME"` for each NPC the arc may use: {npc_list}
- `thread "NAME"` for each ladder the arc touches: {thread_list}
- `canon TOPIC` and `loc PLACE` for anything else you rely on: {topics}
- `arc {arc_id}` shows the existing draft, only when {arc_id} names an arc that exists.

Rules. Read the charter rules (ARC-8) and the field reference (ARC-22) in director/playbooks/arc-planning.md before you draft, and follow ARC-8 point by point. Also follow ARC-4 in the same file: build the charter from what the PC actually did (the PC threads, canon and the feedback), as pressure and never as a script, and never from what you suppose the PC wants. If the PC sheets are not written yet, put PENDING in the shared fields that need a sheet and list what to refine in hidden.refine (ARC-11). Keep every hidden fact in the hidden fields: the shared fields are shown to the user and appear on a public page.

Output, in this order, and nothing else:
1. One JSON object in the charter file shape of ARC-22 (act, budget_turns, blind, shared, hidden), in a single code block. Keep each value to a sentence or two.
2. A direction summary of exactly 5 lines, in plain words, for the director.
3. ONE alternative promise, written as a question, with one line on how it would change the arc.
Keep the whole reply under 1,200 words. Return only the reply.
```
