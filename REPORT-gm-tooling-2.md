# Report: GM tooling 2, campaign-helper (GDD v2, G1 to G7)

Branch `team/gm-tooling`, on top of the commits of `REPORT-gm-tooling-1.md`. Nothing was pushed to `main` and no pull request was opened; the owner merges. Source: `docs/design/gdd-v2-migration.md` and `GDD.md` on campfire's `team/systems` (the migration plan is not on campfire's `main`); the section "GM tooling engineer". Only voyage-director's own material changed: `tools/`, `director/`, `tests/`, `docs/`, `README.md`. The per-campaign skills, the template and the generic rules are untouched (`tests/test_campfire_scope.py` keeps it so), and `voyage-director/SKILL.md` did not change in this round.

| Step | What | Commit |
|---|---|---|
| G1 | NPC briefs carry intent: `npc-intent`, validation, brief and prep | `G1: NPC briefs carry intent fields` |
| G5 | The check module, `check`, `check-brief`, `hard-noes` | `G5: the check module, check and check-brief` |
| G6 | commit-turn records the memory; `campfire-undo` | `G6: commit-turn records the Campfire memory` |
| G2, G7 | prep: memory retrieval, director layer, hard noes, precedent, tracker | `G2, G7: prep retrieves memory and shows the director layer` |
| G3 | `react-check` | `G3: react-check for the react file` |
| G3, G4 | The pipeline playbook, gated | `G3, G4: the pipeline playbook, gated` |

## What each step does

**G1, the brief's intent.** A cast entry may hold `intent`: `want`, `fear`, `trigger` (the one active now), `refusal`, `voice_lines` (3 to 5) and `last_gesture`, each at most 240 characters. `db.py npc-intent NAME --turn N --evidence E [--want ..] [--fear ..] [--trigger ..] [--refusal ..] [--gesture ..] [--voice L]...` sets only the fields given (cast NPCs only). `verify_data` checks the shape; `brief` prints an `INTENT (Campfire; secret)` block; prep's compact brief shows the fields.

**G2, prep.** `prep --packet` now prints, after the packet block: the **hard noes** (the table's phrases from `campaign.json` `hard_noes`, matched against every input in code: a hit names the player and the phrase); the **director layer** (live arc and its next front moves, scene budget, the reveal ladders of NPCs present as "next hidden step N, keep it out" without the step's text, the Standing band when that module is on); **memory** (facts and turn records retrieved by the packet's names and places; the latest three turns always); **precedent** (the last ruling on each skill in play, from the ruling log; `packet_precedent_lines` is no longer a seam, and the test that pinned it empty was replaced by `tests/test_campfire_pipeline_prep.py`); and **what to avoid repeating** (the tracker). No world tick: it is v2.1.

**Hard noes.** `db.py hard-noes [--add P] [--remove P]` edits `campaign.json` `hard_noes`; `resume` shows the count. The match is the GDD's consent-phrase rule: invisible and zero-width characters removed, Unicode NFKC, then the phrase's words appear contiguously, in order, as whole words, case ignored; an apostrophe stays inside a word. Code matches phrases only: a paraphrase is for the director and the checker.

**G3, react.** The react file is `{"threat_moves": [...], "reactions": [...]}` (the GDD names the two lists and the body `round, threat_moves, reactions`; the playbook gives the example). `db.py react-check --reactions F --packet F` checks it against the result packet before `gm react`: one move for each active or full threat, a full threat holds or flees, a press targets a character who is not Out, at most one reaction per NPC present, the closed kinds and their fields, an attitude one step from the current one, give `qty` 1 to 3, line 200 characters, no numbers, and the hidden-words check on every line and rules text. The server stays the authority; adjacency and the lock are the server's.

**G4, write.** The playbook rules for writing from the reacted packet; the **input-to-paragraph map** `{"inputs": [{"player": ID, "paragraphs": [N...]}]}` (paragraphs counted from 1); `check --map` requires every input to have an entry, every paragraph to exist, and a mapped paragraph to name the character.

**G5, the check.** `tools/campfire_check.py` is pure (no file, database or network; a test enforces it). `db.py check --scene F --packet F [--ops F] [--reactions F] [--map F] [--answers F] --round N`:
- code checks: hidden words; the hard noes (a flag in narration, a warning inside quoted dialogue); the seven state checks of the GDD (speaker blocks name someone in the room; cast NPCs named but neither present nor arriving; places; a character named in a sentence with a zone is in that zone after the round's moves; no hidden word or hard no; every op's evidence in the scene up to whitespace and case; every approved reaction line unchanged); the map; and warnings for a stock phrase, opening or closing the tracker has seen.
- `check-brief` prints the checker subagent's whole brief: the draft, the reacted packet, the hard noes, seven fixed questions and the answer format, nothing else (a test plants an intent, a hidden fact and a hidden word in the database and finds none in the brief). The playbook says to run it on the faster tier; no model is named in any repo file.
- The loop: every run is appended to `campfire/check-N.json`. A run with flags is a rewrite request; after the third rewrite (the fourth check) still flagged, it exits 9 STOP and prints the draft's flags for the GM; further runs refuse until `--reset`. Exit codes: 0 passed, 1 flags, 4 a hidden term, 9 STOP.

**G6, commit-turn.** `commit-turn --scene ... --record FILE --check FILE`. The turn entry gains `campfire`: reactions, threat moves, every check attempt with its flags, checker status and draft text (so each rewrite is kept), the rewrite count, overruled flags with reasons, fact ids, gestures with the one each replaced, the ruling-log count. commit-turn refuses (exit 2, nothing written) when a fact's evidence is not in the posted scene, when the check log did not end on the scene being committed, or when a flag still raised on the final draft is not overruled with a reason. Without `--check` it commits and warns. New optional data file `data/campfire.json` (snapshotted with the turn, so a failed commit restores it): `facts` (`F1`, `F2`... with turn, text, names, places, evidence), `rulings` (the ruling log, newest 300), `repetition` (stock phrases that recur in at least three of the last six scenes, and each scene's opening and closing words), `reversals`. Each reacting cast NPC's `intent.last_gesture` is set from the record's `gestures`, or derived from the reaction's kind. `campfire-undo --turn N --reason R` restores the snapshot taken before the turn and writes a reversing record holding the undone turn entry and what it had added; only the latest turn, and `gm undo` on the server stays a separate step.

**G7.** Prep reads the turn records and the fact store directly (see G2).

**The retry limit.** It is defined once, `WRITE_RETRIES = 3` in `tools/campfire_check.py`, with a comment naming Campfire's `LIMITS.write_retries`; campaign-helper never imports Campfire code, and a test pins the value to 3 and that `db.py` reads it from there. The QA plan's A1 slips corpus is not built here (the director withdrew it); the checker's brief and its answers are tested in `test_campfire_check.py` and `test_campfire_checkcmd.py`.

## Decisions where the GDD is silent

These are mine; the director or owner may change any of them.

1. **Brief storage.** `intent` is a sub-object of the cast entry (not new top-level fields), so existing cast checks and `brief` code keep working.
2. **Hard-noes list.** One list, `campaign.json` `hard_noes`. The GDD says "hard noes" in some places and "ban list" in others; I treated them as one list. Limits are the v2.1 consent lists' (30 phrases, 60 characters each); the GDD gives none for the playtest.
3. **Checker answers.** JSON `{"answers": [{"q": N, "answer": "yes"|"no", "quote": "..."}]}`, seven questions numbered 1 to 7. The GDD's question 7 (veils and romance) is v2.1, so its question 8 (the scene ends on something the players can act on) is my 7, and a "no" there is the flag.
4. **The map, the fact store, the ruling log, the tracker, the turn record, the reversing record.** All shapes above are mine. A fact is a plain sentence the posted scene established, with a quote from the scene as evidence.
5. **Zones in the packet.** The zone checks read `scene.zones`, a `zone` on party, scene NPCs and threats, each reaction's `applied.zone.to` and the post's `move` ops. If the result packet carries none of that, the zone checks skip. campfire's contract should confirm those field names.
6. **The threat-move key.** The playbook example uses `threat` (as `campfire.md` already does); the GDD stores the move as `{kind, target?, to?, rolls}`.
7. **Places.** The place check reads capitalised phrases after "in the", "at the", "to the" and similar. It is deliberately narrow; the checker covers the rest.

## For the director or owner

- `docs/design/gdd-v2-migration.md` lists a world-tick test (0, 1 and 31 days); the GDD makes the tick v2.1, so none was built.
- The GDD still mentions a "call log" at two places and drops it at two others (D28); none was built.
- The gate in `campfire-pipeline.md` ("not yet in force") needs lifting by the director when `gm react` ships. `campfire.md` points to it behind its own gate. The campfire playbook rewrite is not done here.
- Zip: unchanged. `voyage-director` 2026-10-05.3 is the one zip to re-upload (as `REPORT-gm-tooling-1.md` says); nothing in this round touches a skill file.

## Tests

New tests in seven files (`test_campfire_intent`, `_check`, `_checkcmd`, `_memory`, `_pipeline_prep`, `_react` and `_scope`), one removed (the empty-seam test for precedent). The README's command, in the background:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests
```

Result on the final tree (the full suite, run once, in the background, after the last code change; only this report changed after it): **994 passed, 20 skipped in 1010.84s.** The 20 skips are the same ones as in `REPORT-gm-tooling-1.md` (887 passed, 20 skipped); nothing was skipped or disabled.
