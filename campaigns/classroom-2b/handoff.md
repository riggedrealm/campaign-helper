# Handoff: Class 2B Act 1 arc charters (for a Sonnet implementer)

Written 2026-10-04 by the director (Opus) after a planning and grill-me session with the user. Implement everything under "Your tasks", verify, then commit and push to `main`. Do not plan, re-word or "improve" the charters: they are the user-reviewed plan. If something blocks you, stop and report instead of working around it.

## Ground rules
- Repo `riggedrealm/campaign-helper`, branch **`main` only** (`git fetch origin main && git checkout -B main origin/main` first). No other branches, no PRs.
- Run everything from the repo root. `db.py` below means `python3 tools/db.py --campaign classroom-2b`.
- Change campaign data **only through `db.py`** commands, never by editing JSON in `campaigns/classroom-2b/data/` by hand.
- Never read `New_World.json`. Never edit `.claude/skills/*/SKILL.md` (no skill change is needed for this work).
- Tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests`. If pytest is not installable, run the changed test file's functions some other way and say so in your report.
- Rehearse writes on a copy first when unsure: `VOYAGE_DATA=/some/copy python3 tools/db.py --campaign classroom-2b ...`.

## Where things stand (turn 0, nothing played)
- Session zero is recorded: warm and wry; combat 3, social 3, mystery 2, exploration 1; brisk pacing; bittersweet ending hope; **4 players**; no extra lines or veils.
- Act 1 pitch "Move-In Week" is **approved**. Its hidden part carries the agreed plan as `checklist` (12 lines) and three deferred `act-deviation` ops as `pending_ops`.
- `db.py preflight` exists (commit `8775556`): read-only readiness check, exit 4 on any FAIL. It currently reports 1 FAIL (no PC sheets; 4 expected) and WARNs (no arc charter, 3 deferred ops).
- **No PC sheets yet.** The user asked for the arcs to be planned now and refined once the sheets arrive. Both charters below therefore carry `PENDING ...` placeholders and a `hidden.refine` list.

## The problem you are fixing
I rehearsed both charters on a data copy: `arc-approve` **approves them as they are**. It accepts the `PENDING PC SHEETS` placeholder as a backstory hook, and with no PCs recorded the per-PC `pc_tests` check passes vacuously. A charter must not be approvable until its placeholders are refined. Also, with two arcs approved, `preflight` reports only the newest one (A2), when the arc that matters next is A1.

## Your tasks

### 1. `arc-approve` refuses unrefined charters (`tools/db.py`, `arc_approval_problems`)
Add these problems to the list the function returns (so `--force` still overrides and is recorded, as with every other rule):
- `hidden.refine` is a non-empty list: `hidden.refine has N open item(s): <items joined by "; ">`.
- Any shared string, or any string inside a shared list, contains the marker `PENDING` (case-sensitive): `shared.<field> still holds a PENDING placeholder`. One problem per field.
- `session_zero.players` is set and fewer PCs are recorded in `state.player_characters`: `only N of M PC sheets recorded: pc_tests cannot be checked yet (pc-add)`.
Also add `refine` (list of strings) to the shape checks in `charter_shape_errors` (`hidden.refine must be a list of strings`).

### 2. `preflight` reports every arc of the act (`tools/db.py`, `preflight_items`)
Replace the single arc line with one line per arc of the current act (arcs whose `act` is the current act or missing), in id order:
- `active`: `OK   arc A1 is active (turn X of budget Y)` (use the existing progress helper if one fits).
- `approved`: `OK   arc A2 is approved (starts when the previous arc closes)` for any approved arc after the first open one; the first open approved arc reads `OK   arc A1 is approved: next to start (arc-start when its first pressure shows)`.
- `draft`: `WARN arc A1 is a draft` plus, when `hidden.refine` is non-empty, `: refine first: <items joined by "; ">`.
- No arc at all: keep today's WARN.
Keep every other preflight check as it is.

### 3. Tests (`tests/test_arcs.py`)
- `arc-approve` refuses a charter whose `hidden.refine` is non-empty, and one whose shared field holds `PENDING`; each refusal is exit 4 and names the problem; `--force` approves and records `approved_forced`.
- With `session-zero --players 2` and one PC, `arc-approve` refuses with the "only 1 of 2 PC sheets" problem.
- `act-plan`/`arc-plan` refuse `hidden.refine` that is not a list of strings (exit 2).
- `preflight` with two drafts (one with refine items) prints a WARN line per draft with the refine items; after approving both (use `--force` in the test), it prints the "next to start" line for A1 and the "starts when the previous arc closes" line for A2.
- All existing tests still pass. Note: the `env` fixture already removes the live `arcs.json` from its copy.

### 4. Docs
- `campaigns/classroom-2b/docs/arc-planning.md` and `templates/voyage-director/campaign/docs/arc-planning.md` (same edit in both): in section 4 "Hidden fields", add `refine` (list of what must change before approval, typically once PC sheets arrive; `arc-approve` refuses while it has items). In section 3 step 8, add one sentence: an arc may be drafted before the PC sheets exist, with `PENDING` placeholders and `hidden.refine`; it is approved only after refining. In section 10, mention that preflight lists each arc of the act with its refine items.
- `campaigns/classroom-2b/README.md`: extend the `preflight` bullet with "lists each arc of the act, and a draft's refine items".

### 5. Record the two charters as drafts (after tasks 1 to 4 pass)
Save the two JSON blocks below verbatim to files outside the repo (or a scratch dir) and run:
```
db.py arc-plan --file A1.json --evidence "planning session with the user (arcs drafted before PC sheets)"
db.py arc-plan --file A2.json --evidence "planning session with the user (arcs drafted before PC sheets)"
```
They must come out as **A1** and **A2**, status `draft`. **Do not approve them**, and do not run `arc-start`.

### 6. Verify, then save and push
- `db.py arc A1`, `db.py arc A2`: both drafts, fields as below.
- `db.py arc-approve A1` must now exit 4 listing the refine items, the PENDING backstory hook and "only 0 of 4 PC sheets". It writes nothing. (Session zero has no lines or veils, so `--lines-checked` is not needed.)
- `db.py preflight`: WARN lines for both drafts with their refine items; the PC-sheet FAIL is still there (expected; it clears when the user sends the sheets).
- `db.py planner-page --out /tmp/preview.html` succeeds (spoiler-safe); drafts do not appear on the public page.
- Commit code, tests and docs with a clear message, then `db.py save` (commits and pushes the data). End with `git status -sb` showing `main...origin/main` and nothing uncommitted.
- Report back: commit hashes, test result, and the `preflight` output.

## Charter A1: "Rice, Rotas and Strangers" (Days 1 to 5, budget 30)
```json
{"act": 1, "budget_turns": 30, "blind": false,
 "shared": {
  "title": "Rice, Rotas and Strangers",
  "tone": "warm and wry: banter over the stove, small frictions, something quietly off upstairs",
  "promise": "Will four strangers make Sakura Lane feel like theirs before Monday starts sorting them?",
  "premise": "Move-in weekend at Sakura Lane Sharehouse. The House Manager's rules are done, Tatsuya is up with rice, Shin is watching the door, Mio is only a whirr behind the loft door, and Sunny is a week late and on her way. Classes start Monday; the placement tournament is announced midweek.",
  "pressure": "The house finds its rhythm on its own clock: the Pulse chore rota and dinner list go live, the welcome dinner happens with whoever comes, and orientation on Monday reminds 2B that the school expects it to fail.",
  "set_pieces": ["a welcome dinner that can go either way", "a house-rules standoff over quiet hours", "a first power test in the training bays"],
  "pc_tests": {},
  "subplot": "Sunny's late arrival strains the room count, the quiet hours and everyone's patience with her ring light.",
  "climax_kind": "the tournament briefing that turns housemates into rivals for placement",
  "ending_shape": "warm but unsettled: the house has a rhythm, and the first hairline crack is visible",
  "stakes": "personal",
  "seeds": ["paperclips rearranged on the sign-in sheet", "a Pulse ping: the chore rota and dinner list are live", "Tatsuya's tea tray, one cup rattling"],
  "wins_on_offer": ["Tatsuya as someone who trusts you near him", "Shin starting to call the house 'ours'", "the rooftop chill deck as the house's place", "Yūto as an upper-year contact at the vending-machine nook"],
  "echoes": [],
  "backstory_hooks": ["PENDING PC SHEETS: one hook per PC from their sheet (famous parent, background or gear)"],
  "deviations": []},
 "hidden": {
  "twist": {"text": "Mio's skipped meals and all-night work hide money trouble (ladder step 1 only; nothing about who she owes).", "ladder": "Mio's secret", "keywords": []},
  "fronts": [
   {"name": "The House Finds Its Rhythm", "goal": "settle into routines with or without the PCs",
    "moves": [{"text": "The House Manager posts the Pulse chore rota and dinner list (Day 1)."},
              {"text": "The welcome dinner happens Day 1 evening with whoever comes; Tatsuya saves plates for anyone missing."},
              {"text": "A house group chat forms and in-jokes start (Day 2 to 3); absent PCs are tagged, not waited for."},
              {"text": "A quiet-hours clash (Sunny's ring light, Mio's night whirr) gets settled by someone (Day 4 to 5)."}]},
   {"name": "Shimazu's Doubt", "goal": "show 2B the arrangement is a gamble the school expects to lose",
    "moves": [{"text": "Orientation warning at Chikara Academy main-hall (Day 3): a verdict on a line."},
              {"text": "A Pulse notice spreads the rumor that 2B won't last a month."},
              {"text": "Tournament briefing (Day 4 to 5): placement carries weight; every team fights all three bouts."}]},
   {"name": "Mio's Leak", "goal": "keep her trouble hidden while her power leaks",
    "moves": [{"text": "Loft light on all night, a whirr down the hall; she misses the welcome dinner."},
              {"text": "Paperclips and a coin drift out from under her door; she plucks them back and flees."},
              {"text": "Her phone buzzes from an unknown number at a shared moment; she silences it: 'It's nothing, really.'"}]}],
  "antagonist": {"name": "Reiko Shimazu", "face": "Vice Principal Reiko Shimazu: formal, conditional, distrusts the arrangement, not the students", "first_contact": "Day 3 orientation at Chikara Academy/main-hall: the warning, delivered to the whole class."},
  "clues": [{"text": "Mio pays her share of the dinner fund in counted small change, twice."},
            {"text": "Mio says she already ate whenever food appears, and Tatsuya's face says she didn't."},
            {"text": "A Pulse listing under Mio's handle sells a precision tool she clearly still uses."},
            {"text": "Mio silences calls from an unknown number and goes still each time."}],
  "surprises": ["Paperclips rearranged into WELCOME on the sign-in sheet", "Sunny's ring light flickers the whole lane's lights", "Arimura leaves orientation mid-sentence and returns with snacks, saying nothing"],
  "climax_options": ["The briefing lands with the house together and joking about it", "The briefing lands with the house scattered, each hearing it alone", "Someone volunteers the house as one team and the others have to answer"],
  "pc_test_situations": {},
  "cast": ["Tatsuya Ōmine", "Shin Asakura", "Mio Tachibana", "Park Seo-yeon", "Reiko Shimazu", "Kenji Arimura", "Yūto Fujisawa", "Sakura Lane House Manager"],
  "new_npcs": [],
  "refine": ["backstory_hooks: replace the PENDING line with one hook per PC sheet", "pc_tests: one category per PC (lean social or exploration; at most one combat)", "pc_test_situations: one situation per PC in the house or at orientation"],
  "notes": "Act 1 checklist applies (preflight). Step-1 tells only: Mio (twist), Sunny (deflects the video), Shin (bolts when staff 'check in'), Shimazu's look at Yūto Day 4. Nothing for Arimura or Ayame. World-clock beats: Mio comes down when a PC is near the kitchen; Sunny's taxi the first turn after noon. Tutorial nudge once Day 4 to 5. Arc starts (arc-start) when the rota/dinner pressure first shows in Voyage's output (likely turn 2)."}}
```

## Charter A2: "Three Bouts and a Board" (Days 6 to 7 plus results night, budget 30)
```json
{"act": 1, "budget_turns": 30, "blind": false,
 "shared": {
  "title": "Three Bouts and a Board",
  "tone": "loud, bright and nervous: arena noise, puzzle fights, a gallery that remembers everything",
  "promise": "When the arena puts each of them into a class, what will the house still hold together?",
  "premise": "Days 6 to 7 at Chikara Battle Arena. Every first-year team fights three bouts that decide its specialization. The four newcomers fight as one team; the housemates fight on their own teams, and the gallery is full of 1A.",
  "pressure": "The placement board fills in after every bout, 1A watches from the gallery, and the results on Day 7 will send each housemate to a different class.",
  "set_pieces": ["a rule-puzzle team bout", "a crowded-gallery confrontation", "a results-night reckoning at the house"],
  "pc_tests": {},
  "subplot": "Tatsuya's own bout: the strongest first-year in the building refuses to let his power go.",
  "climax_kind": "the Final bout, then the results read aloud",
  "ending_shape": "bittersweet, one crack: placed together, split from the housemates, one sting that does not become a wound",
  "stakes": "personal",
  "seeds": ["brackets posted at the arena entrance: three bouts for every team", "an opposing captain bowing to Tatsuya in the training bays", "Pulse clips of the house's bouts going around 1A"],
  "wins_on_offer": ["a personal mark for each PC: an instructor's eye, an elective invite or a staff contact", "the crowd's memory of how the team fought", "1A's grudging notice", "the medical station staff as allies"],
  "echoes": ["PENDING PLAY: fill from Move-In (Rice, Rotas and Strangers) once it closes"],
  "backstory_hooks": ["PENDING PC SHEETS: one hook per PC, ideally a famous parent watching or not watching from the gallery"],
  "deviations": []},
 "hidden": {
  "twist": {"text": "Sunny's brightness in the gallery is a performance: she deflects any mention of the video and there is more to it than the public version (ladder step 1 only).", "ladder": "Sunny's scandal video", "keywords": []},
  "fronts": [
   {"name": "The Placement Board", "goal": "sort every first-year by Day 7 evening",
    "moves": [{"text": "Day 6 morning: brackets posted; every team fights Round 1, Round 2 and the Final."},
              {"text": "After Round 2: provisional marks go up in the officials-booth window."},
              {"text": "Day 7 evening: results read aloud; the housemates go to Strike, Support, Investigation and Media."}]},
   {"name": "1A in the Gallery", "goal": "keep 2B in its place",
    "moves": [{"text": "1A takes the best rows; Ayame watches without cheering."},
              {"text": "Pulse clips of 2B's bouts circulate with mocking captions."},
              {"text": "Results night: Ayame calls Media 'a consolation prize' within a PC's earshot; Sunny looks at that PC before answering."}]},
   {"name": "Tatsuya's Restraint", "goal": "never hurt anyone, even if it costs the bout",
    "moves": [{"text": "He wraps his hands in the training bays and won't spar at full strength."},
              {"text": "In his own bout he blocks a teammate's hit and refuses to release it; his team loses (heard or seen between bouts)."},
              {"text": "He skips the post-results dinner unless someone goes after him."}]}],
  "antagonist": {"name": "Daichi Sumeragi", "face": "captain of the Final's opposing team (rebound clap); courteous, relentless, studies the 2B team's bouts", "first_contact": "Day 6 morning in Chikara Battle Arena/training-bays: he bows to Tatsuya, then turns and studies the PCs."},
  "clues": [{"text": "Sunny sits as far from the 1A rows as the gallery allows."},
            {"text": "A 1A student whispers about 'that clip' when Sunny passes; her smile gets bigger, not smaller."},
            {"text": "Sunny's phone lights up with a resurfaced comment thread and she flips it face down."},
            {"text": "Asked about her old class, Sunny answers with a joke and a nickname, never a fact."}],
  "surprises": ["An opposing team's captain bows to Tatsuya", "The medical team asks Yūto to cover the station"],
  "climax_options": ["The Final ends early on a cracked rule, and results night carries the weight", "The Final goes the distance and the crowd remembers it", "The Final is lost well, and the marks still honour how they fought"],
  "pc_test_situations": {},
  "cast": ["Tatsuya Ōmine", "Shin Asakura", "Mio Tachibana", "Park Seo-yeon", "Ayame Kujō", "Yūto Fujisawa", "Kenji Arimura", "Reiko Shimazu"],
  "new_npcs": [{"name": "Daichi Sumeragi", "intro_line": "Daichi Sumeragi, a broad first-year captain who bows a little too formally."}],
  "refine": ["backstory_hooks: replace the PENDING line with one hook per PC sheet", "pc_tests: one category per PC (lean combat; one mystery for cracking rules)", "pc_test_situations: one bout moment per PC", "echoes: fill from what the PCs did in Move-In once it closes"],
  "notes": "Opponent rules, tells, weaknesses and finishers per bible 4.1: give them to Voyage as plain facts at each bout opening; never state outcomes. Bout budgets taper (R1 <=4, R2 <=6, Final <=8) with one housemate beat between bouts. The crack fallback (Day 7 morning check) is in the act checklist. Personal marks come from Voyage's bout output, delivered by existing staff (Arimura, an officials-booth proctor, Yūto). Ayame's jab is about Media, never the scandal: Ayame's ladder stays hidden. Arc starts on Day 6 morning."}}
```

## Later, not part of your tasks: refining once the PC sheets arrive (the director does this)
1. `pc-add` / `pc-sheet` for each of the 4 PCs from the user's intake (story facts only).
2. A1: replace the `PENDING` backstory hook with one hook per PC sheet; set `pc_tests` (one category per PC, leaning social or exploration, at most one combat) and `pc_test_situations`; empty `hidden.refine`; `arc-plan --id A1 --file ...`; `arc-approve A1`.
3. A2 stays a draft until A1 closes: its `echoes` come from what the PCs did in A1. Then the same refine steps, leaning combat with one mystery test for cracking rules.
4. The three deferred act deviations go into the turn 1 `record` payload (Voyage's story start), as `preflight` prints them.
