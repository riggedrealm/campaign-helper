# 2B Standing Ledger

**Hidden. Director only. Never shown as a meter and never named in a prompt.** Voyage sees Standing only through NPC hints (Shimazu's warnings, Yūto's remarks).

The rubric, thresholds, hint bands, current value and dated entries now live in **`data/ledger.json`**.

```
python3 tools/db.py state                                    # current Standing and its hint band
python3 tools/db.py ledger +3 "welcome dinner landed" --turn 5 --evidence "..."
```

A change is recorded only when Voyage's story output establishes the event that moves Standing (a tournament result, a good week, a discovered theft). Never for plans or guesses. At the final review (Day 112) apply the +15 come-clean credit first (if Mio confessed), then read the ending: 70 or more Renewed, 40 to 69 Probation, under 40 Dissolved. At the midterm (Day 42) Shimazu tells 2B it is failing whatever the number: scale her tone to the hint band, not her verdict.
