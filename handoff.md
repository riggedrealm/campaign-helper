# Handoff: Voyage director (Class 2B + Luxcellia), for a new chat

Written 2026-10-03 at the end of a Claude Code session. Read this first, then follow "Start here".

## What this is
The user plays AI-DM campaigns in **Voyage** (Latitude's AI RPG). Claude is the **director** behind Voyage: each turn it writes **one steering prompt** (≤ 840 characters, `Cut / Tone / Crew / Facts / World`) that the user pastes into Voyage. **Voyage narrates and runs every game mechanic** (rolls, success, damage, stats, relationship values, quest progress). The director steers story, characters, memory, pacing and secrets only.

Everything lives in the repo **`riggedrealm/campaign-helper`**, branch **`main` only** (head `7a4d202`). Never use other branches.

## Start here
1. Use the uploaded skill for the campaign being played: **`luxcellia-director`** (v2026-10-03.3) or **`class2b-director`** (v2026-10-03.8). The user uploaded both from the latest zips.
2. Get the repo (attach `riggedrealm/campaign-helper` with push access, or clone it), on `main`.
3. Run `python3 tools/db.py --campaign <name> resume`. It prints "Skill version (repo)". If that differs from the loaded skill's version line, tell the user to re-upload the zip.
4. Follow the skill. Read the arc bible only by section: `db.py --campaign <name> bible <section>`.

## The user's standing rules
- **Implementation goes to Sonnet subagents** (`model: "sonnet"`) with a full brief. The main chat plans, reviews the diff and verifies. Planner work goes to `model: "opus"`.
- **Commit and push to `main` only.** No PRs unless asked.
- **The director never takes over Voyage's mechanics.** Rulings decide story consequences only.
- **Never dictate what a player character does.** Never offer menus. Only the player moves their character.
- **Main NPCs are real characters.** Run `brief <name>` before writing their `Crew:` line.
- **Yes first.** The arc is pressure, not a script. When players leave the arc, their choice wins (skill section "When players leave the arc").
- **Trial run means write nothing:** lookups and `--dry-run` only.
- **Don't ask questions you can answer yourself.** Give a recommendation whenever you ask.
- **Pronouns:** use they/them unless stated.
- **World JSON files are never edited.** The world changes only through user-approved **Studio** requests.

## Tools (run from the repo root)
- **`python3 tools/db.py --campaign <name> <cmd>`:** the one shared tool. The old path `python3 campaigns/classroom-2b/tools/db.py` still works for Class 2B.
  - Lookups: `resume state brief npc loc quest lore canon thread bible history spotlight recap`.
  - Turns: `check-prompt <file>`; per turn `prep --paste paste.txt`, then `commit-turn --prompt prompt.txt --payload payload.json` (locks, records, commits locally, pushes every 5 turns); `wrap-up` at session end; `record` for repairs. Also `undo-turn N` and `recover`.
  - Other writes: `feedback`, `studio-request` / `studio` / `studio-show` / `studio-done`, `pc-add`.
- **`check-prompt`:**
  - FAILs on: over the limit, labels missing or out of order, strong secret terms.
  - WARNs on: unknown names, "correction"/"not X" in Facts, stated player outcomes, flat `Crew:` verbs.
- **Template system:**
  - `templates/voyage-director/` is the template.
  - `tools/new_campaign.py NAME --display ... --world w.json --story-start ...` creates a new world.
  - `tools/sync_skill.py NAME [--check]` pulls template rule updates into a campaign's skill. Generic rules are at 2026-10-03.6.
  - Each campaign's settings are in `campaigns/<name>/campaign.json`.
  - The Standing and debt modules are optional.
- **Tests:** `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests` (123 pass). Skill size ceiling is 14,000 bytes.
- **Docs per campaign:** `README.md`, `arc-bible.md`, `opening.md`, and in `docs/`: `orchestration.md`, `studio.md`, `expression.md`.

## Studio (occasional, never every turn)
- **What it is:** Voyage's Studio injects or edits world content from a natural-language request. It costs tokens and has a **2,000-character limit per request**. **It cannot export**, so `studio-done` keeps the database in sync. It can **edit existing entities** (use `studio-request --edit`).
- **When to use it:**
  - an NPC becomes key;
  - a player thread needs 2+ scenes;
  - a thin faction the players stick with;
  - new areas the story has shown;
  - an act-start batch;
  - an edit after a milestone.
- **When to apply it:** the user applies it at a natural break, in auto-split batches.
- **Story fixes:** Studio can edit **only the latest turn**. A load-bearing slip in Voyage's latest output gets a `story-fix` **immediately, before the next prompt**. Slips in older turns get fixed in the fiction instead.
- **Never send:** hidden secrets or ladder steps that haven't been revealed.

## NPC expression (just added; under test)
- **Spotlight rule:** 1 or 2 spotlight NPCs per turn get a specific gesture, the feeling under it, and their voice. Pick from their `brief` "SHOW" kit (gestures, moods, lines, never-does) and vary it each turn. Everyone else "reacts in character".
- **If narration is still flat after a few turns:** fix 3 is a one-time Studio edit to the narrator style and the key NPCs' records. Not done yet; the user decides.

## Campaign 1: Luxcellia, "The Fifth Hero's Party" (`luxcellia`): next to play
- **Setup:**
  - World `worlds/luxcellia.json`, an isekai fantasy world (sha256 starts `a0392c58a0305b46`).
  - Story start **🗡️ Summoned and Discarded**, game mode **🫂 Party and Bonds**.
  - **Single player, one character.** No hidden-score module.
- **The user did not edit the opening;** it plays as authored. Turn 1 is Voyage's start (log prompt "none"), and the director begins at turn 2 (see `opening.md`).
- **Voyage's own quest chain** (Voyage owns progress):
  1. Severance and a Side Door
  2. The Power They Couldn't Measure (its text assumes a dimensional-boundary power; the player's sheet decides, treat loosely)
  3. The Misfire's Vindication
- **Arc:**
  - Acts: Severance (Days 1–14), Bonds (15–45), The Vanished (46–75), Vindication (76–100).
  - Party candidates: Yumi Aokiba (her emotion-reading fails on the player), Ren Tsukishiro (his charm fails on them) and Toma Kirisawa. The fourth seat is open. Joining always needs mutual agreement.
  - Through-line: Mizuho Kaimaku's private-board disappearances.
- **Villain (director secret):** Archbishop Isamu Tokiwa, "the Almoner", Church of the First Light Almonry. Act 4 fight around Day 90; a Wharf scout fight around Day 60.
- **Cast and secrets:** 9 main NPCs with expression kits, and 10 reveal ladders.
- **Open before turn 1:**
  1. **The user's character sheet** (they will give it). Run `pc-add`. Never invent sheet details.
  2. **The user's OK or veto on the Almoner** as the board's operator. Not yet confirmed.
  3. **The Mizuho Studio edit** (text in `docs/studio.md`). It moves her from Portmaris to the Aureliath Guild and is needed before her Day 4 beat. Until then an unnamed registrar stands in.

## Campaign 2: Class 2B (`classroom-2b`): built, not yet played
- **Setup:**
  - Superhero Tokyo, world `New_World.json` (sha256 starts `85d275c9c5968a32`).
  - Story start "01 - Classroom 2B" at Sakura Lane Sharehouse, one semester, hidden 2B Standing (start 40).
- **The database is clean:** turn 0, no player characters.
- **Open:** the user's character sheets. From the trial runs, Griffin's sheet had these questions:
  - "Unpowered" trait vs his barrier power;
  - room 4 means river-bedroom;
  - which weapon "Ranged Weapons" means;
  - the famous parent.

## Planned, not built
- **Browser mode (next time):** the director reads Voyage's output and types the prompt through Claude in Chrome, so the user never copy-pastes. It needs the Claude desktop app with the extension. Plan:
  - The user tells the director their move in chat. The director reads the latest output from the user's Voyage tab and types the prompt. The user presses send by default.
  - A page map is saved in `docs/browser.md`. Output fingerprints prevent double processing.
  - Never click regenerate, undo or delete. Fall back to paste after 2–3 failures.
  - Open questions: does the prompt go in the same box players type in (assumed yes)? Send policy? Desktop app availability?
- **Until then:** the user pastes the last exchange (their input plus Voyage's output) as one block, and the director splits it.

## Context-saving habits
- Start a fresh chat per scene, or every 15–20 turns, after the last `record` has saved.
- Never read whole bibles or world files; use `bible <section>` and the lookups.

## Fast turn loop (2 tool calls per turn)
1. The user pastes the last exchange (their input plus Voyage's output) as one block. Save it to `paste.txt`.
2. **Call 1:** `db.py --campaign <name> prep --paste paste.txt` prints the state, the NPCs present with compact briefs and rotating expression picks, the scene, clocks, pending Studio requests, the character budget, and a **LIVE CHECKLIST**. Reason only about the checklist items plus the rulings. Use `--names` to add NPCs and `--full NAME` for a full brief (first appearance in a scene, a big emotional beat, a reveal).
3. **Call 2:** in the same call, write `prompt.txt` and `payload.json`, then run `commit-turn --prompt prompt.txt --payload payload.json`. It checks the prompt and writes nothing on a FAIL. It lists all payload errors at once and normalises time words such as "Dusk". It records, commits locally, and pushes every 5 turns. Rerun only on a FAIL; name warnings don't force a rewrite.
4. **Reply format:**
   - Give the prompt in a blockquote with its character count.
   - Add one line only for a slip, a ruling with a story consequence, or a decision for the user.
   - **When there is a Studio plan, put the full ready-to-paste batches in the same reply.** A story fix goes above the prompt; anything else goes below it. `commit-turn` prints the batches.
   - Give full reasoning only when asked "why".
5. When the user says **"wrap up"**, or before a fresh chat, run `wrap-up` (pushes everything and lists anything pending).
6. Effort: medium on normal turns; high only for twist reveals, showcase finishers and finales.
