# Browser mode: reading Voyage and submitting

Open this playbook when the session is in browser mode: the browser tools read Voyage's output and submit the prompt, instead of the user pasting and submitting.

Browser mode is an optional adapter. It changes only how Voyage's output is read and how the prompt is sent; the order of a turn is LOOP-2 in `core.md` (The turn). Matching the Voyage tab's title to the campaign is campaign selection (SEL-1 in the bootstrap skill) and is already done by the time you use this playbook.

"The browser tools" means whichever set the session offers: Claude in Chrome or the desktop app's built-in browser. The steps are the same in both; only the tool names differ.

## The user's word

"send" from the user is the approval to read, draft and submit. It stays a manual trigger: no polling and no auto-run. <!-- BRW-1 -->

## Load the tools

Load the browser tools in one tool search, naming every tool you will need in that one query: the tab-context tool, `find`, `form_input`, `computer`, `browser_batch` and `javascript_tool`. If the tab group shows only a blank tab, ask the user for the Voyage link, or to add the tab. <!-- BRW-2 -->

## The browser turn

On "send", run the turn in this order. `core.md` (The turn, LOOP-2) owns the order; these are its steps in browser mode.

1. Read Voyage's output with the script below.
2. Save what you read to `paste.txt`: Voyage's latest output followed by the pending input. Write the slices, joined in order, with the file tool.
3. Rule and draft from the brief already in context, which the last `commit-turn` printed (or `resume`, on a chat's first turn). Run no lookup first unless an escalation trigger or a pivot's first turn calls for it (LOOP-6 in `core.md`).
4. In one call, write the prompt file and run `db.py check-prompt` on it with `--paste paste.txt` (or `--inputs "..."`, the players' inputs as text), so the `Cut:` skip warning can see the input; without inputs that warning is skipped, and `commit-turn` repeats the check with the payload's `inputs`. In the same message, find the text box and the Submit button.
5. Submit, and confirm the submit by re-reading the page text.
6. Write the payload and run `db.py commit-turn`. It records, pushes, fetches planner output and prints the next turn's brief, which you keep for the next "send".
7. Reply as described under "The closing reply".

If the reading script fails because the page has fewer than two `Turn N` labels (for example at the very first turn), stop and ask the user to paste the exchange instead.

## Read Voyage's output

Read the page with one `browser_batch` of `javascript_tool` calls. The first call finds the pending block and stores it on the page:

```
const t=document.body.innerText; const m=[...t.matchAll(/\nTurn (\d+)/g)]; const tail=t.slice(m[m.length-2].index); const s=tail.indexOf('\n\n', tail.indexOf('World:')); window.__o=tail.slice(s); window.__o.slice(0,800)
```

Then, in the same batch, read the stored text in slices: `window.__o.slice(800,1600)`, `window.__o.slice(1600,2400)`, and so on. Tool output truncates near 1000 characters, so keep each slice to 800. Return no header string: one once got a chunk blocked. <!-- BRW-3 -->

The block after the last `Turn N` label is the pending player input. If it reads "Waiting..." or Voyage's output looks unfinished, stop and tell the user. Never draft from stale data. <!-- BRW-4 -->

The script expects the prompts on the page to end with the label `World:`. If the page's last prompt label is a different one, change the marker in the script to the last label your prompts end with. <!-- BRW-5 -->

## Submit

Submit in one `browser_batch`: `form_input` on the "What will happen next?" text box with the exact prompt text, a `computer` `left_click` on the Submit ref, `wait` 2, and a page-script call that returns the end of the page text (under 800 characters). Confirm the submit from that text: your prompt, or its opening words, now appears on the page. Never confirm with a screenshot. If the text did not register, retry the submit once, then stop and report to the user. <!-- BRW-6 -->

Once the submit is confirmed, go on to `commit-turn`. On a story-fix turn the submit waits until the user says the fix is applied (the Studio playbook, STU-6).

## The closing reply

After `commit-turn`, the closing reply shows the prompt you submitted in a blockquote with its character count, with at most the one extra line (`core.md`, Reply), and below them any Studio batches.

## What not to do

Do not read Voyage's panels, and do not take repeated screenshots. Never click regenerate, undo or delete, whatever the page offers; if a repair seems to need one, raise it with the user as the retcon playbook says (RET-5). <!-- BRW-7 -->
