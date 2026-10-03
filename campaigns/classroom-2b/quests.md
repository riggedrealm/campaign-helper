# Quests

All 12 arc quests (trigger, giver, location and area, objectives, outcomes, Standing effect, seed line, status and log) now live in **`data/quests.json`**.

```
python3 tools/db.py quest "Midterm Marks"
```

Update them only from Voyage's story output: `quest-start`, `quest-obj`, `quest-end` (each needs `--turn N --evidence "..."`). Quests are `planned` until Voyage starts one, then `active`, then `completed` or `failed`. See `README.md`.

## Rules for quests in prompts

- Voyage generates a quest when a prompt tells it to start one. The seed line (`seed_line` in the data, 200 characters or fewer) goes in the `World:` line and costs about 100 to 200 characters. Count it with the rest of the prompt (700 maximum). `check-prompt` warns when a planned quest is named without its seed line.
- Quest names are what the players see. They are written not to spoil.
- Introduce one quest per turn at most.
- Objectives can be `hidden` until an earlier one is done (set it to `active` with `quest-obj` when the story shows the first finished). "Ability and Pulse Tutorial" is player-directed: the director never invents the character's ability concept, account or consent.
- Quests do not "fail" and end the game. A missed objective changes what happens next and what Standing does; nothing ends.
- Standing is never named in a prompt.
- Voyage keeps its own record of a quest once started, so do not restate its objectives after the first prompt.
- Personal quests unlock when a player character reaches relationship 50 or more with that housemate (Voyage's value, read from the story output).
