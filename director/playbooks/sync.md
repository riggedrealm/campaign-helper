# Sync: checking the database against Voyage's own state

Open this playbook at session end, or whenever the user supplies an export of Voyage's state.

You cannot see Voyage's panels. Between turns you infer position, time, presence, quest starts and stated conditions from Voyage's output, and those records carry the `inferred` flag (`core.md`, Bookkeeping). A sync compares them with the state file Voyage exports. This playbook is the main chat's side of it: when to ask, how to run it, how to read the report, and how to apply it.

## When to ask for the export

At session end, when the user says "wrap up" or before a fresh chat, ask for the export before `wrap-up` (`core.md`, Bookkeeping, SAVE-2). The user may skip it; see "When the user skips". If the user supplies an export at any other time, run the sync then.

Ask the user to export Voyage's state file and to give you its path. Never open the export yourself, and never ask a subagent to read it: only the tool reads it (WF-1 in the bootstrap skill).

## Run the dry run through the subagent

Launch a subagent with the brief in `director/agents/sync.md`. It runs `db.py sync EXPORT` and returns a compact report. Without `--apply` the command is a dry run: it reads the export, compares it with the database, and prints the mismatches in three classes together with a proposed patch. The dry run changes none of the campaign's records. The only thing it writes is the digest and checksum described under "Storage", and for that the sync subagent is the one named writer, limited to those two files. It never runs `--apply`. The patch is applied only after the user agrees, by the main chat, as described under "Confirm and apply". Never apply a sync automatically, even when the report is clean and even when there is only one item. <!-- SYNC-1 -->

In a trial run (`VOYAGE_DATA` or `VOYAGE_TRIAL=1`, see the bootstrap skill, TRIAL-1), run `sync` only against a `VOYAGE_DATA` copy, because the dry run writes a digest. Never run it, or `--apply`, against the real campaign data in a trial run.

The report is user-facing, so run it through `db.py scan -` before the user sees it (`core.md`, Chat and orchestration, ORCH-5).

## Read the three classes

**Class 1: Voyage-owned state.** This is position, time, quest status and party, taken from the save. The proposed patch contains class 1 only. A quest you recorded as apparently ended (an inferred `quest-end`) is confirmed or contradicted here by Voyage's own status. <!-- SYNC-2 -->

**Class 2: Voyage drift.** This is anything in the save that conflicts with a canon fact or a canon trap. It is reported and never applied. Treat each item as a candidate for a Studio fix (`director/playbooks/studio.md`: STU-6 says how a story fix is filed and when it is sent, and STU-9 how it is written; the Retcon playbook, RET-2 and RET-3, says when a fix applies) or, when the same error keeps coming back, for a new canon trap (`core.md`, Bookkeeping, LOG-5). <!-- SYNC-3 -->

**Class 3: the director layer.** This is the cast bibles, the ladders, the canon traps, the promises and the arc plans. A sync never touches it and never proposes a patch for it. Any change there follows the ordinary rules: records change only when Voyage's output establishes something (DATA-1 in the bootstrap skill). <!-- SYNC-4 -->

## Confirm and apply

1. Read the class 1 patch against what you know from play. If an item looks wrong, do not apply it; say so to the user in the summary.
2. Show the user a short summary of the class 1 patch: how many items in each class, the class 1 changes as one line each, and each class 2 item with a line on what you propose. For example: "Sync report: 2 position updates (Ren to Home Base/shared-kitchen, Sam to Home Base/shared-lounge), 1 time update (Day 6, Evening), 1 quest marked complete. One drift item: Voyage has Kenji arriving by the east gate, but the canon fact says the north gate. Nothing in the director layer changed. Apply the class 1 changes?"
3. Only after the user says yes, run `db.py sync EXPORT --apply` yourself in the main chat. It applies class 1 only, never class 2 or class 3. The subagent never applies. If the user says no or does not answer, apply nothing.
4. Continue with `wrap-up` if the session is ending. `wrap-up` shows whether a sync was done.

## Voyage's tick numbering

Voyage numbers its turns as ticks, and the database follows Voyage's numbering. Ticks that were played without the director are imported from the save. Director turns that Voyage undid are marked, not deleted. The report names the ticks and turns involved. Read that part with care, because the next turn number follows Voyage's numbering; check `state` before the next prompt. <!-- SYNC-5 -->

## Storage

The command writes a small digest extracted from the export and records the export's checksum. Commit the digest, using `save` or `wrap-up` as for any campaign data. Keep the raw export out of git: it stays in a git-ignored location, and you never add it to a commit. <!-- SYNC-6 -->

## The mismatch log

The tool logs mismatch counts by type each time it runs, and `resume` prints them at the start of the next chat, so you can see where inference keeps failing. <!-- SYNC-7 -->

## When the user skips

The user may skip the export. When they do, change nothing: records made from play stay `inferred`, with the quotes they came from, and nothing is confirmed. Carry on with `wrap-up`. <!-- SYNC-8 -->

## Commands

Plain reference.

| Command | Use |
|---|---|
| `sync EXPORT` | Dry run: write the digest, print the three-class report and the proposed patch |
| `sync EXPORT --apply` | Apply class 1 only |
| `scan FILE\|-` | Hidden-term scan of the report before the user sees it |
| `wrap-up` | Session end; shows whether a sync was done |
| `resume` | Prints the mismatch counts by type |
