# Phase 2 writing conventions

Every file written in phase 2 follows these. The rule content comes from `rule-inventory.md`; this file only says how to write it down. Decisions D12 to D14 are recorded in `decisions.md`.

## Files and who writes them

| File | Holds (inventory section 4) |
|---|---|
| `.claude/skills/voyage-director/SKILL.md` | BOOT rows |
| `director/core.md` | CORE rows, including the trigger table |
| `director/playbooks/pacing.md` | PB-pacing |
| `director/playbooks/fights.md` | PB-fights |
| `director/playbooks/split-party.md` | PB-split |
| `director/playbooks/studio.md` | PB-studio |
| `director/playbooks/retcon.md` | PB-retcon |
| `director/playbooks/reveals.md` | PB-reveals |
| `director/playbooks/pivot.md` | PB-pivot |
| `director/playbooks/arc-planning.md` | PB-arcs |
| `director/playbooks/sync.md` | PB-sync |
| `director/playbooks/browser.md` | PB-browser |
| `director/playbooks/failures.md` | PB-failures |
| `director/playbooks/campaign-start.md` | PB-start |
| `director/playbooks/hidden-score.md` | PB-modules |
| `director/reference.md` | REF |
| `director/agents/common.md` and one file per role: `charter.md`, `card.md`, `pivot.md`, `world.md`, `sync.md`, `review.md`, `resume.md`, `dev.md`, `scaffold.md` | AGT rows (AGT-1 in `common.md`) |

## Rule ids (D12)

- Each rule carries its inventory id in an HTML comment at the end of the paragraph, list item or table row that states it: `<!-- FMT-4 -->`, or several at once: `<!-- CUT-2, CUT-3 -->`.
- Every id assigned to a file appears in exactly one marker in that file, and in no other file's markers. The phase 4 test counts only ids inside `<!-- ... -->` markers.
- A cross reference to a rule elsewhere is plain text, never a marker: "see the Studio playbook (STU-9)" or "as in `core.md`, Prompt format". Prefer naming the file and section; add the id when it helps a subagent find it.
- Retired ids (X-*) and campaign ids (WR-*) appear in no marker.

## Voice and content

- Plain, full sentences in the imperative, speaking to the director ("Write ...", "Never ..."). No telegraphic fragments. Short sections with headings.
- The inventory's "Rule" column is a paraphrase. Go back to the cited source for the full meaning, then write it once, clearly. Keep every condition and limit the source has; do not add new rules.
- One home per rule. Do not restate a rule owned by another file; point to it. A playbook may apply a rule to its own case without restating it.
- Never write "wins over", "takes precedence over" or any other precedence statement between files.
- Generic only: no campaign names, cast names or places from a real campaign. Examples use neutral placeholders (PCs Ren and Sam, NPCs Yumi and Kenji, places like `Home Base/shared-kitchen`).
- Describe the target design. Commands are the ones in `function-inventory.md` (existing ones plus the new `use`, `menu`, `turn-brief`, `question`, `question-close`, `promises`, `fact-status`, `day-turnover`, `review-add`, `arc-offramps`, `arc-pivot`, `arc-adopt`, `arc-unpark`, `sync`, `scan`, and the new flags it lists). Do not invent other commands or flags. Write `db.py` for `python3 tools/db.py`, run from the repo root; the campaign comes from the session choice (`use`).
- Never read `New_World.json`, anything under `worlds/`, or any raw Voyage export.

## The turn order (user decision, D13)

A routine turn is: (1) `db.py turn-brief --paste paste.txt`; (2) write the prompt file and run `db.py check-prompt` on it in the same call; (3) send the prompt; (4) write the payload and run `db.py commit-turn`, which records and pushes. Recording and the push always come after the prompt is out, in the downtime while the player reads Voyage's output.

- Paste mode: "send" means giving the user the prompt message with the `SendUserMessage` tool (the prompt in a blockquote with its character count, plus at most the one extra line). After `commit-turn`, the closing reply never repeats the prompt; it carries only what is new: a failure, a push warning, or Studio batches.
- Browser mode: "send" means submitting in Voyage (the browser playbook).

## Studio batches and story fixes (D14)

- An ordinary Studio request is logged by `commit-turn` (a `studio-request` op), after the prompt is out. Its ready-to-paste batches go in the closing reply, below everything else. The user applies them at a natural break.
- A story fix must reach Voyage before the next prompt does. On a story-fix turn (an escalation turn, not routine), write the fix and run `db.py studio-request --kind story-fix` before sending (and leave that op out of the payload), so the fix batch can go first, above the prompt, in the prompt message. In browser mode, do not submit until the user says the fix is applied.
