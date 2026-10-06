# Fast turn protocol (Voyage via Claude in Chrome)

User-set 2026-10-04. It applies to every turn of this campaign in every chat and wins over "The turn loop" and "Orchestration" in SKILL.md where they conflict. The clock is "send" to submitted in Voyage.

## Standing choices
- **"send" from the user = approval**: read, draft, submit. It stays a manual trigger: no polling, no auto-run.
- Stay on the current model. No subagent for bookkeeping. No `prep` or paste file on routine turns.
- **Player agency rules** (`docs/player-agency.md`) apply to every turn; read them with this file at chat start. Its pre-check runs on every draft.
- Drive Voyage through Claude in Chrome. Load the tools in one ToolSearch: `tabs_context_mcp`, `find`, `form_input`, `computer`, `browser_batch`, `javascript_tool`. If the tab group shows only a blank tab, ask the user for the Voyage link or to add the tab.

## The loop (steps 1 to 6 are the clock; 7 and 8 come after the submit)
1. **Read**: one `browser_batch` of `javascript_tool` calls.
   - First call: `const t=document.body.innerText; const m=[...t.matchAll(/\nTurn (\d+)/g)]; const tail=t.slice(m[m.length-2].index); const s=tail.indexOf('\n\n', tail.indexOf('World:')); window.__o=tail.slice(s); window.__o.slice(0,800)`
   - Then `window.__o.slice(800,1600)`, `slice(1600,2400)`, and so on, in the same batch. Tool output truncates near 1000 characters. Return no header string: one once got a chunk blocked.
   - The block after the last `Turn N` label is the pending player input. If it reads "Waiting..." or the output looks unfinished, stop and tell the user. Never draft from stale data.
   - If the page's last prompt label is not `World:`, adjust the marker to the last label your prompts end with.
2. **Triage.** Routine turn: the ruling in 2 to 3 sentences, one handle, one gesture, one world move. Escalate to the full process (`prep`, bible lookups, canon check) for: a new NPC or place; a scene hitting its budget (the cut turn); any fight or fight opening; a milestone day or ladder reveal; romance or consent edge cases; player power claims or invented facts; Studio fixes; Voyage output that broke canon.
3. **Draft.** Prompts may use the full limit when it helps; never pad. Run the player-agency pre-check (5 questions) in your head before writing the file.
4. **Pre-check.** `Write` prompt.txt to the session scratchpad, then `db.py check-prompt FILE` (no writes). Fix any FAIL before anything goes out.
5. **Find.** In the same message as the pre-check, `find` the "What will happen next?" textbox and its Submit button.
6. **Submit.** One `browser_batch`: `form_input` (the exact prompt text), `computer` `left_click` the Submit ref, `wait` 2, `screenshot` at scale 0.4. If the text did not register, retry once, then stop and report.
7. **Bookkeeping, off the clock.**
   - Lean does not mean skipping. Every turn logs: `summary` = what Voyage's output established (not what the prompt asked); `time` when the block changed; `pos` when the PC moved (areas: `loc <city>` lists them; never skip because a lookup by area name failed); `scene-start` with a budget on a scene's first turn and `scene-end` when it closes; a `fact` for promises, secrets, gifts, decisions and NPC conditions; `slips` for every invention or fact error, Voyage's or the director's.
   - Then `commit-turn --prompt FILE --payload FILE --push-every 1`. The Stop hook flags unpushed commits.
8. **Reply.** The prompt in a blockquote with its character count. One extra line only for a ruling, slip, Studio item or decision that needs the user. The same slot takes the one-line planning trigger ("Arc closed. Plan the next one now or later?") and the one-line arc checks from `prep`: drift ("Re-aim?"), 130% of budget (extend or wrap up) and two boredom flags. Never more than one extra line of any kind. No scene-feedback requests unless the user raises it.
