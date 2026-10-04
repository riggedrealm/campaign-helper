# Campaign Helper

Director tooling for Voyage campaigns. The director steers the story; the Voyage engine runs all game mechanics.

## Layout
- `tools/db.py`: the one shared database tool, for every campaign (`--campaign NAME` or `VOYAGE_CAMPAIGN`; with a single campaign it is the default).
- `campaigns/NAME/`: one campaign (`campaign.json`, `README.md`, `arc-bible.md`, `data/*.json`). `campaigns/classroom-2b/tools/db.py` is a stub that keeps the old command path working.
- `.claude/skills/NAME-director/SKILL.md`: the director skill for a campaign.
- Campaigns: `classroom-2b`, `luxcellia`, and `joestar` (the Joestar Gang, migrated mid-play from `riggedrealm/voyage-memory` at turn 480 and resynced from Voyage's own save at tick 481, Day 20; world file `worlds/joestar-save.json`; see `campaigns/joestar/docs/migration.md`).
- `templates/voyage-director/`: the copy-and-fill template (generic rules plus fill blocks).
- `tools/new_campaign.py`, `tools/sync_skill.py`: scaffold and sync.

## Start a new world
1. Export or locate the Voyage world JSON, then run:
   `python3 tools/new_campaign.py NAME --display "Display Name" --world path/to/world.json [--module standing] [--module debt] [--setting "..."]`
   It creates `campaigns/NAME/` and `.claude/skills/NAME-director/SKILL.md`, imports locations, lore, factions and world NPCs, and prints the fill blocks left. The hidden-score modules are off by default (`--standing` is an alias for `--module standing`). It refuses if NAME exists.
2. In a chat, fill every `<!-- fill: ... -->` block (SKILL.md, `README.md`, `arc-bible.md`, `opening.md`), then `campaign.json`, `data/cast.json`, `quests.json`, `threads.json`. Keep SKILL.md at 15,000 bytes or less.
3. Zip `.claude/skills/NAME-director` and upload it as the skill.
4. Play with `python3 tools/db.py --campaign NAME resume`, `state`, `check-prompt`, `record`.

## Campaigns migrated mid-play
A campaign that was played elsewhere first keeps its earlier turns as a read-only archive: `data/history.json` (a list of `{label, summary, turn_from, turn_to, ...}` range summaries) and `state.turn_base` (the number of turns before `turns.json` starts, so `len(turns.json) + turn_base == state.turn`). `history` searches the archive, `recap` fills from it and `resume` shows its tail while no turn is logged. A scene may also carry `comms`, `elsewhere`, `pending_inputs` and `pending_prompt_notes` (printed by `state`/`resume`; the two pending lists are cleared when the next turn is logged). Tests: `tests/test_archive.py`, `tests/test_joestar.py`.

## Update the generic rules
The template's generic blocks (`<!-- generic:start ID -->` ... `<!-- generic:end -->`) are shared. After the template changes:
`python3 tools/sync_skill.py NAME` (replaces the generic blocks, keeps your fill content and `Skill version:`), or `--check` (exit 1 if out of date). `db.py resume` prints `Generic rules: X (template Y)` and warns when behind. Bump `Skill version:` and re-upload the zip.

## Tests
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests`

Env: `VOYAGE_DATA` (copy of a data dir), `VOYAGE_TRIAL=1` (trial run); `CLASS2B_DATA` and `CLASS2B_TRIAL` still work.
