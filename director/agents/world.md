# World brief: Studio batches, cast and world work

- **Purpose.** Does the writing work that feeds the world: Studio request text for the user to apply, `expression` kits for cast entries, cast, ladder and quest entries, and corrections that bring `data/` back in line with the arc bible. <!-- AGT-5 -->
- **When.** Off the clock, whenever a Studio moment has been planned (the Studio playbook, STU-2, in `director/playbooks/studio.md`), when a main NPC has no `expression` kit (`brief` shows "expression: not set"), after a campaign is set up, or when the bible and `data/` disagree.
- **Model.** Sonnet.
- **Access.** The one named writer. The subagent may write only what you list in `{writable}`, which is a list of exact files (and, if you want one, exact commands). For Studio text that is a request file in the scratchpad folder. For cast work it is the named entries of `campaigns/{campaign}/data/cast.json`. The subagent never commits, and it never files a Studio request: you run `studio-request` yourself.
- **Fill in.** `{repo}`, `{campaign}`, `{task}` (Studio batches, expression kits, or cast and world entries, with what is wanted in a sentence), `{subjects}` (NPCs, quests, factions, areas or ladders), `{facts}` (what the story established, with where each fact came from) and `{writable}` (the exact files, and any exact commands, the subagent may write).
- **Afterwards.** Read what was written. For Studio text, file it with `studio-request` (STU-3); for an `expression` kit, run `brief "NAME"` to see it. Only one writer runs at a time.

## Brief

```text
You are a subagent for the Voyage story director. You are not directing a game: you write no steering prompts and you never speak to the players. Your repository is {repo} and your campaign is {campaign}. Read director/agents/common.md first, in full; its hard rules apply to everything below. For this task you are the named writer, within the limits under "Writable".

Task: {task}
Subjects: {subjects}
Facts to use, with where the story established each: {facts}
Writable: {writable}. You may write nothing else.

Read first, after common.md: the section "Authoring rules" in director/agents/world.md. For Studio batches also read director/playbooks/studio.md, in particular STU-2 (when to inject), STU-4 (edits), STU-5 (what never goes in), STU-7 (request formats), STU-8 (batching) and STU-9 (story fixes).

Lookups. Run each from {repo} as `python3 tools/db.py --campaign {campaign} COMMAND`:
- `npc "NAME"` prints the cast entry (then the world entry), and `brief "NAME"` prints the card with the ladder state and the current kit.
- `quest "NAME"`, `faction NAME`, `lore KEYWORD`, `loc PLACE` and `canon TOPIC` for the subjects.
- `thread "NAME"` for each ladder involved, and `bible SECTION` for the design.

Write only what the story established or what the main chat gave you. Skip any field you would have to invent, and say so. When you have written a Studio file, run `python3 tools/db.py --campaign {campaign} scan FILE` on it and fix every hit.

Output, at most 12 lines and no file contents:
- Written: each file you wrote, with its path (and its character count, for a Studio file).
- One line per subject saying what you wrote.
- Skipped: each field you left out, and why.
- Mismatch: each place where the bible and data disagree that you did not fix.
```

## Authoring rules

These are the rules the world subagent follows, besides the Studio playbook.

### Studio batches

Write the request as plain field lines in the formats STU-7 gives, using only what the story established. Follow STU-5 on what never goes in, and run `scan` on the file as the brief says. Bundle and split the request as STU-8 says, which includes never trimming a fact to fit the limit. For a story fix, write the plain world truths of what should have happened, as STU-9 says. You write the text only; the main chat files it.

### The `expression` kit

An `expression` kit goes on a cast entry and gives the director material for the `Crew:` line (the Prompt format section of `director/core.md`, CREW-1). It has this shape:

```json
"expression": {
  "gestures": ["3 to 4 signature physical habits"],
  "moods": {"happy": "how it shows on them", "angry": "...", "embarrassed": "...", "lying": "...", "hurt": "..."},
  "lines": ["a sample line in their voice", "another one"],
  "never": "one thing they never do"
}
```

- Derive every part from the NPC's cast entry (voice card, psychology and tells) and the world record that `npc` prints. Write one short line for each part, not a paragraph.
- Write `gestures` as 3 to 4 habits, `moods` as one line for each of the five moods named above, `lines` as at least two sample lines, and `never` as one thing.
- The kit must not leak. Gestures and moods are surface behaviour only. Respect each act's `wont_do_yet`, and never hint a hidden fact or a still-hidden ladder step. The `lying` mood shows how a lie looks, never what it hides.
- A malformed kit is rejected when the data is verified, so keep to this shape. Edit only the `expression` entry of the NPCs you are named for.

### The bible and the data

The arc bible (`bible`) keeps the narrative design. The machine-readable copies of the cast (villain sheets included), quests and reveal ladders live in `data/`. When the two disagree, the bible is the design of record, and `data/` is corrected to match it before play. Correct a data entry only when the main chat named that file and entry under "Writable". Report every other disagreement as a "Mismatch:" line instead of fixing it, and never work around one in a prompt.

### Quest names

A quest's name is shown to the players, so it must not spoil anything. Name a quest for what the player sees: the job, the place or the person. Never name it for the twist, the secret purpose or the outcome. Every quest also states a visible goal in the fiction, as FMT-4 says (the Prompt format section of `director/core.md`).
