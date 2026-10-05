# Campaign Helper

Director tooling for Voyage campaigns. The director steers the story; the Voyage engine runs all game mechanics.

## Layout
- `tools/db.py`: the one shared database tool, for every campaign (`--campaign NAME` or `VOYAGE_CAMPAIGN`; with a single campaign it is the default).
- `campaigns/NAME/`: one campaign (`campaign.json`, `README.md`, `arc-bible.md`, `data/*.json`). `campaigns/classroom-2b/tools/db.py` is a stub that keeps the old command path working.
- `.claude/skills/NAME-director/SKILL.md`: the director skill for a campaign.
- Campaigns: `classroom-2b`, `luxcellia`, and `joestar` (the Joestar Gang, migrated mid-play from `riggedrealm/voyage-memory` at turn 480 and resynced from Voyage's own save at tick 481, Day 20; world file `worlds/joestar-save.json`; see `campaigns/joestar/docs/migration.md`).
- `templates/voyage-director/`: the copy-and-fill template (generic rules plus fill blocks).
- `tools/new_campaign.py`, `tools/sync_skill.py`: scaffold and sync. `tools/build_site.py`: the GitHub Pages site (see Arc Planner pages).

## Start a new world
1. Export or locate the Voyage world JSON, then run:
   `python3 tools/new_campaign.py NAME --display "Display Name" --world path/to/world.json [--module standing] [--module debt] [--setting "..."]`
   It creates `campaigns/NAME/` and `.claude/skills/NAME-director/SKILL.md`, imports locations, lore, factions and world NPCs, and prints the fill blocks left. The hidden-score modules are off by default (`--standing` is an alias for `--module standing`). It refuses if NAME exists.
2. In a chat, fill every `<!-- fill: ... -->` block (SKILL.md, `README.md`, `arc-bible.md`, `opening.md`), then `campaign.json`, `data/cast.json`, `quests.json`, `threads.json`. Keep SKILL.md at 15,200 bytes or less.
3. Zip `.claude/skills/NAME-director` and upload it as the skill.
4. Play with `python3 tools/db.py --campaign NAME resume`, `state`, `check-prompt`, `record`.

## Campaigns migrated mid-play
A campaign that was played elsewhere first keeps its earlier turns as a read-only archive: `data/history.json` (a list of `{label, summary, turn_from, turn_to, ...}` range summaries) and `state.turn_base` (the number of turns before `turns.json` starts, so `len(turns.json) + turn_base == state.turn`). `history` searches the archive, `recap` fills from it and `resume` shows its tail while no turn is logged. A scene may also carry `comms`, `elsewhere`, `pending_inputs` and `pending_prompt_notes` (printed by `state`/`resume`; the two pending lists are cleared when the next turn is logged). Tests: `tests/test_archive.py`, `tests/test_joestar.py`.

## Campfire mode
A campaign whose `campaign.json` names a Campfire room code (`"campfire_room": "K7Q2MX"`, six characters) is played in Campfire: its server rolls the dice and holds the sheets, and the director rules each input and writes the scene. A turn starts only when the GM types "send" or "draft"; the director then follows `director/playbooks/campfire.md`. campaign-helper's side: `db.py prep --packet FILE` reads the round packet `gm pull` wrote, and `db.py commit-turn --scene FILE --rulings FILE --ops FILE --payload FILE` records the posted scene with the rulings, the Campfire ops and the turn log, after a hidden-words check on the scene and the stakes lines. The GM token is never stored here (it stays in the Campfire CLI's own room store), and nothing hidden (ladders, arcs, Standing, debt) is ever posted. The per-turn packet files under `campaigns/NAME/campfire/` are not committed. Tests: `tests/test_campfire_*.py`.

## Update the generic rules
The template's generic blocks (`<!-- generic:start ID -->` ... `<!-- generic:end -->`) are shared. After the template changes:
`python3 tools/sync_skill.py NAME` (replaces the generic blocks, keeps your fill content and `Skill version:`), or `--check` (exit 1 if out of date). `db.py resume` prints `Generic rules: X (template Y)` and warns when behind. Bump `Skill version:` and re-upload the zip.

## Arc Planner pages
Each campaign has a read-only Arc Planner page on GitHub Pages: `https://riggedrealm.github.io/campaign-helper/<campaign>/` (for example `.../joestar/`), with an index at the site root. `db.py resume` prints the link as `Planner page: URL`. The base URL is `pages_base` in `site.json`; `arcs.json` `page_url` overrides it for one campaign.

- **Public.** Anyone with the link can read it. It shows direction fields and session zero (tone, play styles, lines and veils), never hidden fields. Every page is scanned for hidden terms before it is built.
- **Rebuilds** on every push to `main` that touches `campaigns/`, `tools/`, `templates/` or the workflow (`.github/workflows/pages.yml`), and by hand from the Actions tab (Run workflow). `commit-turn` pushes every few turns and `wrap-up` pushes the rest.
- **Spoiler refusal.** If any page would leak a hidden term, the build fails, nothing deploys and the last good site stays live. Fix the shared field and push again.
- **Local build:** `python3 tools/build_site.py --out _site` (default `_site/`, not committed). It writes nothing if any campaign fails. One campaign only: `python3 tools/db.py --campaign NAME planner-page --out FILE`.
- **One-time setup (by hand):** in the GitHub repo, Settings > Pages > Build and deployment > Source: **GitHub Actions**. Then push to `main` or run the workflow once.

## Tests
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests`

Env: `VOYAGE_DATA` (copy of a data dir), `VOYAGE_TRIAL=1` (trial run); `CLASS2B_DATA` and `CLASS2B_TRIAL` still work.
