# Studio: injecting world content and fixing the story

Open this playbook when `core.md` calls a Studio moment (Triggers, TRIG-8): a request to plan, batches to hand over, or a story fix.

Studio is Voyage's tool for adding world content (NPCs, quests, factions, areas, story starts) from a written request. You plan, write and log the requests; the user applies every batch in Voyage.

## Use it sparingly

Studio costs tokens, cannot export the world, and one request holds about 2000 characters in total, not per field (`studio_limit` in `campaign.json`; longer text is split into batches). So it is occasional: bundle requests, and let the user apply them at a natural break. Everything else is handled with prompt lines and the database. <!-- STU-1 -->

## When to inject

The moments that call for a Studio request are listed in `core.md`, Triggers (TRIG-8). A one-off extra, a name used once and anything a prompt line and `add-npc` already cover are not reasons for one. <!-- STU-2 -->

## Plan and log a request

Write the request text to a file, then plan it as a `studio-request` op in the turn's payload; `commit-turn` stores it and splits it into batches. (A story fix is the exception: it is filed before the prompt goes out, see "Where the batches go".) Outside a payload the same thing is:

`db.py studio-request --kind npc|quest|faction|area|story-start|story-fix|other --target NAME --text-file F [--edit] [--why "..."] --turn N`

`db.py studio` lists what is pending, and `db.py studio-show ID [--batch N]` prints the batches ready to paste, with their character counts. When the user says they have applied a batch, run `db.py studio-done ID [--batch N] --turn N`. When every batch of a request is applied:

- an `npc` becomes a cast entry flagged `in_studio` (made in play if it is new; it needs no `intro_line`);
- a `quest` becomes active and flagged `in_studio`;
- an `area` runs `add-area` when `studio-done` is given `--location` (with `--area-id`, `--desc` and `--paths`);
- a `story-fix` is logged (and may record canon, see "Writing a story fix"). <!-- STU-3 -->

## Edits

For an NPC, quest or faction that is already in the world, send an edit with only the changed fields ("Update <name>: ...") instead of the whole entity again. It is cheaper. Use `--edit` (or `edit` in the op's args); the batches start "Update <name>:". Edit when:

- an NPC's situation, role, location or relationships change after a milestone;
- a revealed ladder step changes how an NPC is portrayed, for example after a confession;
- a faction's stance toward the players shifts;
- a quest's giver or premise changes in the story.

Never send quest progress, because Voyage owns it, and never a hidden step. Edits bundle like other requests. `studio-done` on an edit only logs it; an NPC already in the world keeps its `in_studio` flag. `db.py` warns when an edit names an unknown entity, and when a request that is not an edit names one that exists. <!-- STU-4 -->

## What never goes in

Nothing that SEC-1 (the bootstrap skill) keeps hidden may go into a request; a ladder step that has been revealed in play may. `studio-request` runs the same hidden-term check as `check-prompt`: it refuses strong hits (pass `--allow` only for public terms) and warns on soft ones. The check covers only the campaign's hidden words, secrets and ladders, so read any never-inject list in the campaign's `director.md` before writing. <!-- STU-5 -->

## Where the batches go

An ordinary request is logged by `commit-turn`, after the prompt is out. `commit-turn` prints each new request's batches in full (the same text as `studio-show`) at the end of its output, so the closing reply carries them with no extra call: put them below everything else, each batch in its own code block with its character count. Never answer a new request with only a bare "Studio: ..." line. At a natural break, one line may remind the user what is still pending.

A story fix must reach Voyage before the next prompt does, so it cannot wait for `commit-turn`. On a story-fix turn, write the fix to a file and run `db.py studio-request --kind story-fix --target "Turn N" --text-file F --turn N` before the prompt is sent, where N is the turn you are about to record, then `db.py studio-show ID` for the batches. Leave that request out of the payload; it is already logged. Put the fix batch first, above the prompt, in the prompt message (`core.md`, Reply; the turn order is in The turn, LOOP-2). In browser mode, send that message to the user with `SendUserMessage` as well, and hold the submit until the user says the fix is applied. <!-- STU-6 -->

## Request formats

A request is plain natural-language field lines, one per line, modelled on the world data shapes. Give only what the story established, and skip a field you would have to invent. Use one of these templates per entity. <!-- STU-7 -->

**NPC** (name, role, faction, where found, about, look, personality, voice):

```
Name: ...
Role: (type, e.g. shopkeeper, rival, teacher)
Faction: ... (or none)
Found: (location and area)
About: two or three sentences: what they do, how they treat the players, what they want.
Look: one sentence.
Personality: three or four words.
Voice: tic or catchphrase, how they speak.
```

**Quest** (name, giver and where, goal, steps, success and failure):

```
Name: ...
Giver: ... Found at: (location and area)
Goal: one or two sentences.
Steps: 3 to 5 short steps, in order.
Success: ... Failure: ... (consequences in the fiction, no numbers)
```

**Faction** (name, type, about):

```
Name: ...
Type: (major, minor, local)
About: what they do, who leads, how the public sees them, what they want from the players.
```

**Area**: its name, the location it belongs to, one or two sentences of look and use, and which areas it connects to. **Story start** and **other**: free text, under the same rules.

## Batching

`studio-request` splits the text itself: first at blank lines (entity boundaries), then at lines, then at sentences, never mid-word. Each batch starts "Batch i/n — <target>: " and fits the limit with that prefix. Several entities share a batch when they fit, so put related requests in one file. When the text is over the limit, let it split; never trim facts to fit. <!-- STU-8 -->

## Writing a story fix

A story fix covers Voyage's latest turn only, so it is immediate. Whether a slip calls for one is decided in the retcon playbook (RET-1 to RET-3); this section is how to write it. Write plain world truths of what should have happened, worded as FACTS-1 words a `Facts:` line (`core.md`, Prompt format). Put nothing hidden in it (SEC-1). Within the limit it is usually one batch. For example, when Voyage placed at the east gate a courier who had already left town:

```
The courier left town last night. Yumi keeps the stall at the east gate and has not seen the courier since.
```

The next prompt assumes the fixed version, and the turn's payload summarises the corrected story. When the user confirms the fix is applied, `db.py studio-done ID --turn N --fact KEY` records each line as a canon fact. <!-- STU-9 -->

## Timing

The user applies batches at a natural break, such as a scene end, a time skip or an act boundary, never mid-scene unless they want to. Collect ordinary requests and bundle them to save tokens. A story fix is never bundled and never deferred; STU-6 says how it is filed and sent. `resume` shows "Studio: N pending". <!-- STU-10 -->
