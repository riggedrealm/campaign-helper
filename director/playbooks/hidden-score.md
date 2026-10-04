# Hidden scores: Standing and debt

Open this playbook when `resume` says the campaign has a hidden-score module on (Standing, or debt).

A hidden-score module keeps a number the players never see. For Standing it lives in `data/ledger.json`: the current value, the thresholds, the rubric, the hint bands and the entries. The `ledger` command and the Standing lines in `state` and `resume` exist only while the module is enabled.

## Moving the score

Standing changes only through `db.py ledger +N|-N "reason"`, and only for events the story has established, as the rubric in `data/ledger.json` says. Like every update it carries the turn and the evidence (LOG-1, `core.md`, Bookkeeping). The op is in `director/reference.md`. <!-- MOD-1 -->

## What Voyage may hear

Standing is never a meter and is never named in a prompt. Voyage hears it only through NPC hints by band: `state` shows the current band, and the arc bible's Standing section (`db.py bible` lists the headings) says which NPCs voice the hints and what moves the score. <!-- MOD-2 -->

## What it never does

Standing guides story pressure. It never limits what a player may attempt. <!-- MOD-3 -->

## Debt

The debt module, in a campaign that has one, is hidden the same way as Standing: it is never a meter and never named in a prompt. <!-- MOD-4 -->
