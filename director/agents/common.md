# Subagent briefs: common rules

Every subagent the main chat launches gets a brief built from one file in this folder. The brief is the fenced text in that role's file. It is short on purpose: it names the task, the inputs, the lookups and the output, and it points at the rules by id and file instead of copying them. This file holds what every brief shares, and every brief tells its subagent to read it first.

## For the main chat

To launch a subagent, open the role's file, read its header, fill in the braces in the fenced brief and pass that text as the subagent's prompt. Set the model the header recommends. Never hand a subagent the bootstrap skill as its brief: a subagent is not directing, and the brief says so.

| File | Launch it for |
|---|---|
| `charter.md` | A draft arc charter for a planning session |
| `card.md` | A pressure card for a showcase fight, a twist reveal or a finale |
| `pivot.md` | Off-ramp sketches, or a pivot mini-charter |
| `world.md` | Studio batches, cast and world work |
| `sync.md` | The dry-run sync report against Voyage's export |
| `review.md` | The director review of the last N turns |
| `resume.md` | The resume digest and the recap |
| `dev.md` | A tool, test or doc change |
| `scaffold.md` | A new campaign |

Every brief uses the same two placeholders:

- `{repo}` is the absolute path of the repository root, where `tools/db.py` lives. The subagent runs every command from there.
- `{campaign}` is the campaign's folder name, the value that `--campaign` takes. In `scaffold.md` it is the name of the campaign being created.

Only four briefs may write: `world.md`, `dev.md` and `scaffold.md` for the files you name, and `sync.md` only for the digest and checksum that its `db.py sync` dry run writes by itself. Fill in the placeholder that lists the exact files (and any exact commands) the writer may use. Have one writer running at a time. Every other brief is read-only.

When a result comes back, review it before you use it. Any text the user might see goes through `db.py scan` first. If a result breaks a hard rule below, do not use it: rewrite the weak parts yourself or reuse an earlier one.

## Hard rules for every brief

These rules apply to every subagent, whatever its role. A brief does not repeat them; it tells the subagent to read this file, and the rules hold from that point. <!-- AGT-1 -->

1. You are not directing a game. You write no steering prompts, you never speak to the players and you decide nothing a player character does. The main chat reviews your result before anything is used.
2. You are read-only unless your brief names you as the writer. Read-only means lookups only: run read commands as `python3 tools/db.py --campaign {campaign} COMMAND` from the repo root, and read the repo files your brief names. Never run an update command, never create or edit a file and never use git or make a commit. A brief that names you as the writer says exactly what you may write, and you touch nothing else. No brief lets you apply a sync, commit or push.
3. Never open `New_World.json`, anything under `worlds/` or a raw Voyage export. The tools read them; you do not (WF-1 in the bootstrap skill applies to you as it does to the main chat).
4. Use existing locations and areas only. Never invent a place; check each one with `loc`.
5. Reveal at most one reveal-ladder step, and only the next hidden step that `thread "NAME"` shows as revealable now. Nothing past a gated milestone.
6. Write no player-character outcomes and no combat outcomes, because Voyage rolls combat. State what NPCs do and what the enemy's standing rules are, never who hits, who wins, or what a player character feels, says or chooses.
7. Main NPCs follow their brief (`brief "NAME"`): voice, psychology, current act beat and "won't do yet". Keep hidden facts out of their dialogue unless that ladder step is the one you reveal.
8. Invent no canon that contradicts canon or state; check with `canon TOPIC` and `state`. You may add a new minor NPC, with an intro line of 90 characters or fewer.
9. Keep your output compact. Return exactly what your brief asks for, within its size limit. Never paste file contents or whole lookup outputs.

## Hidden material and the scan

Every text you return that the user might see will go through `db.py scan` before the user sees it, and a text with a hit is rejected. So it must contain no hidden material: no hidden fields, no unrevealed ladder steps, no hidden scores or debt, no off-ramps, no `pc_threads` and no secret behind a ladder. You may read these in lookups and use them to limit your own work, but never copy, quote or hint at them in a reply meant for the user. Each brief says which parts of its reply are for the director only. When you are unsure whether a term is hidden, leave it out.

## Returning your result

Return the output your brief asks for, in its order, with nothing before it and nothing after it. Do not mention these rules or your brief. If a lookup fails or a fact you need is missing, say so in one line that starts with "Open:", carry on with what you have, and never fill the gap with invention.
