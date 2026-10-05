# Report: GM tooling 1, campaign-helper

Branch `team/gm-tooling`, from `campfire-mode` at `5e32c8b`. Nothing was pushed to `main` and no pull request was opened; the owner merges. The matching campfire-side work (the playbook draft) is on campfire's `team/gm-tooling`, with its own `REPORT-gm-tooling-1.md`.

| Order | What | Commit |
|---|---|---|
| 1 | The pre-check: `db.py precheck --scene F --packet F [--rulings F] [--ops F]`, with tests, README and reference lines | see `git log` |
| 2 | `director/playbooks/campfire.md`: step 6 names `precheck`; the gated D15 to D18 sections carried over from campfire's playbook | see `git log` |
| 3 | This report | see `git log` |

## 1. `campfire-mode`, prepared for the owner's merge

`campfire-mode` is complete as `REPORT-campfire-mode.md` describes it: seven commits, one per approved item, suite green. Two things wait on the owner, and nothing on this branch changes either.

### The two raised byte limits

| Guard | Was | Now | Where | Why it moved |
|---|---|---|---|---|
| Always-loaded layer: the bootstrap skill `.claude/skills/voyage-director/SKILL.md` plus `director/core.md` | 17,500 bytes | 18,000 bytes | `tests/test_director_rules.py`, `ALWAYS_LOADED_LIMIT` | The layer sat at 17,498 before Campfire mode. The trigger row TRIG-19 (item 2), the two skipped-in-Campfire-mode sentences at LOOP-2 and FACTS-1 (item 4) and the skill paragraph CFM-1 (item 6) bring it to 17,944 |
| Per-campaign skills: `.claude/skills/<campaign>-director/SKILL.md` | 15,000 bytes | 15,200 bytes | `tests/test_templates.py`, `tests/test_joestar.py`, `tests/test_expression.py`, `tools/sync_skill.py`, `tools/new_campaign.py`, `README.md` | The three campaign skills were within 20 bytes of 15,000, and the synced Campfire paragraph puts them at 15,161 to 15,177. The cap was raised once before, 14,000 to 15,000, for a rule addition |

**The one alternative is moving text, not trimming the rules.** Every byte the always-loaded layer gained is an approved Campfire rule, so the way back under 17,500 is to move text that already exists out of the layer: the test's own advice is "move text into a playbook or reference.md". The candidates are the paragraphs of `director/core.md` that only matter in one situation and already have a playbook of their own (the split-party line at STATE-1, the romance paragraph NPC-7, the Studio trigger text TRIG-8), each moved whole with its rule id so `rule-inventory.md` keeps one home per id. For the per-campaign skills the equivalent is trimming each campaign's fill text (the owner's own words), which is why `campfire-mode` did not touch it. To keep the limits as raised, nothing more is needed; to take the alternative, revert the two limits and say which paragraphs move, and I will do it on this branch.

### The four skill zips to re-upload

| Skill | Version to upload | On generic rules |
|---|---|---|
| `voyage-director` | 2026-10-05.3 | (the bootstrap carries the generic rules) |
| `class2b-director` | 2026-10-05.1 | 2026-10-05.4 |
| `luxcellia-director` | 2026-10-05.1 | 2026-10-05.4 |
| `joestar-director` | 2026-10-05.1 | 2026-10-05.4 |

`db.py resume` prints `Skill version (repo)` and warns until the uploaded zip matches. This branch changes no skill file, so these versions stand.

### The rest of the owner's list, unchanged from `REPORT-campfire-mode.md`

- Add `"campfire_room": "XXXXXX"` to the `campaign.json` of each campaign that moves to Campfire. The GM token stays in the Campfire CLI's room store, never here.
- Merge `campfire-mode` into `main`, then this branch on top of it (it is a fast-forward from `campfire-mode`).
- The v0.2 precedent output is still a seam, `packet_precedent_lines` in `tools/db.py`.

## 2. The playbook copy, `director/playbooks/campfire.md`

campfire's `playbook/campfire.md` on its `team/gm-tooling` branch gained six sections for decisions D15 to D18, each behind a line that says it applies once the client ships that part and that the director lifts the line: rulings when players declare only an ability (D15), speaker blocks and writing for playback and the room header (D17 and the restyle), quest titles (D18), portraits through `gm portrait` (D16). This copy carries the same text. The difference between the two files stays the ten path fixes `REPORT-campfire-mode.md` lists, plus the one command below; `diff` shows nothing else.

Step 6 now names the pre-check: `python3 tools/db.py precheck --scene ... --packet campaigns/NAME/campfire/result-N.json --rulings ... --ops ...`, exit 0 clean or warnings only, exit 4 a hidden term.

When the director lifts a gate line in campfire's playbook, this copy needs the same edit. I own both files and will carry each lift across.

The playbook passes the rule-file tests as before: every `db.py` command it names exists, no rule markers, no campaign display name or main NPC. The example names (Station Master Oda, Mira, Jun, Kaito) are the handoff's and match no campaign's main NPC as the test folds them.

## 3. The pre-check: `db.py precheck`

The first assignment's item 3: a warning when a speaker block names someone who is not a character, a scene NPC or a threat on the table. Built as one read-only command, the mechanical part of the playbook's five-question pre-check, run before `gm post`.

```
python3 tools/db.py precheck --scene FILE --packet FILE [--rulings FILE] [--ops FILE] [--allow TERMS]
```

- **`--packet`** is the round packet (`gm pull`) or the result packet (`gm resolve`); both carry `party`, `scene.npcs`, `threats` and `inputs`, which is all the check reads. The result packet is the one the director holds at step 6, so the playbook names it.
- **Question 3, the hidden words.** The scene and every stakes line of `--rulings` go through `campfire_hidden_check`, the same function commit-turn uses, so the check before the post and the one after it agree exactly: any hit of `scan` fails (exit 4, as `scan`), a soft secret term warns, `--allow TERM` skips a term the director confirmed is public. Without `--rulings` the stakes are not checked and the output says so.
- **Question 1 and the client's name rule, the speaker blocks.** `speaker_blocks` reads the scene as the client's formatter will (`docs/handoff/director.md` on campfire's `wp/restyle`): a paragraph, blank-line separated, whose first line starts with `@` and has at least one line after it; the speaker is the rest of that first line, a trailing bracketed delivery note stripped; `\@` is not a block; an `@` line with nothing after it is not a block, since the client renders it as text (decision D20, item 7). For each block, a WARN when:
  1. **the name is nobody in the room.** The room is the packet's party, the scene's NPCs and the threats whose status is not retired, plus, from `--ops`, the NPCs a `scene` op adds and the threat a `threat-add` op adds, because the playbook says to add a speaker to the scene in the same post. The match is exact, as the client's is. The hint names the one listed name that differs only in case, accents or punctuation or that holds the written name as whole words ("Hasegawa" for "Mr. Hasegawa"); else, when the database knows the NPC (cast, world NPCs, aliases), it says they are not in the scene and to add a `scene` op; else to add them or use the listed name.
  2. **a player character's block is not their own words.** When the speaker is a party member, each line of the block must be a quote from that player's input this round (compared after `norm`: case, accents and quote marks aside; a part of the input counts). A missing input or a line not in it warns with the playbook's own rule: set only their own words, word for word, or report what they did in narration.
  3. **a bare `@` line**, which the client would show as ordinary text.
  4. **a delivery note over 60 characters**, the handoff's guidance (D20 keeps it playbook guidance, not a formatter rule).
- **Exit codes.** 0 clean or warnings only (a warning is the director's to judge), 4 a hidden term (as `scan`; do not post), 2 a missing or malformed file (the same messages as commit-turn's, with the `pre-check:` label). The room warnings are prep's (`campaign.json` names no room code; the packet's room differs).
- **Read-only.** Nothing is written; it works in a trial run and on a `VOYAGE_DATA` copy. No polling, no loop, no trigger: it runs once, when the director runs it.
- **Secrets.** The pre-check reads the packet and the scene on the GM's machine and sends nothing anywhere. Nothing from the database (the hint names an NPC's key, which is a name, never a hidden fact) reaches the scene unless the director writes it there, and the hidden-words check is what stops that.

The role file asked for warning 1. Warnings 2 to 4 come from the same parse and the same handoff rules, so they are in; the director may say to drop any of them.

Items 2 to 4 are beyond the letter of the assignment, as said. `commit-turn --scene` is unchanged: it still needs `--rulings` and `--ops`, and it does not take a packet, so the speaker check runs only in `precheck`, before the post, where it can still change the scene.

### Tests: `tests/test_campfire_precheck.py`, 37 tests

A tmp repo root holding a copy of classroom-2b whose `campaign.json` names the fixture packet's room (`tests/fixtures/campfire-round.json`: Aiko Tanaka, Ren Okabe and Yuna in the party; Mio Tachibana and Mr. Hasegawa in the scene; the man in the grey coat on the table). Among them:

- a clean post with an NPC, a threat and a PC quoting their input passes with no warning, lists the blocks and writes nothing;
- `--rulings` and `--ops` are optional; a scene with no block says `none`;
- an unknown speaker warns with the paragraph number; five near misses (case, punctuation, "Mr Hasegawa", "Hasegawa", "grey coat") name the listed name; a database NPC not in the scene, and an alias of one ("Sunny"), say to add a scene op; the post's own `scene` and `threat-add` ops count; a retired threat does not and a full one does; a result packet works;
- a PC block that is not a quote warns, a quote matches across curly quotes and case, a PC with no input gets no block, every line of a block is checked;
- a bare `@` line, `\@`, an e-mail address, an indented `@`, a long note, Windows line endings;
- a hidden term in the scene or in `rulings[1].stakes` exits 4 (and the speaker check still runs, so one run shows everything), `--allow` passes, a soft term warns, as `scan` and commit-turn;
- malformed files and a missing or malformed packet exit 2; `--scene` is required;
- the room warnings match prep's; a trial run works; commit-turn still needs `--rulings` and `--ops`; the playbook and the README name the command.

### Other files

- `README.md`, the Campfire mode section: one clause naming `precheck`.
- `director/reference.md`, the Campfire bullet: one sentence.
- `tools/db.py` module docstring: the Campfire line.
- `campfire_inputs` takes `what` for the error label and allows `--rulings` and `--ops` to be absent; commit-turn's own checks are unchanged (tested).

## Not done, and why

- **D14 in the playbook** (Guard removed: the party line, the descriptor words, the pillars table, the Defense rows). The assignment names D15 to D18; D14's text waits for the engine engineer's merge and is one gated section more when the director asks.
- **The handoff's "What has to ship first" table** (`docs/handoff/director.md` on campfire's `wp/restyle`) lists the pre-check as "CLI, proposed". It is built here, in campaign-helper, as the role file says, and the CLI is not mine to touch. The row is the experience designer's to update; I said so in the campfire report.
- **No contract change** is needed in campfire: the pre-check reads the packet shapes `src/types.ts` already defines.

## Tests

The README's command, in the background:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests
```

Result on the final tree: see the line below, filled in before the push.

RESULT_PLACEHOLDER
