# Cast: Class 2B

The cast cards (visual line, intro line, personality, voice card, want, fear, agenda, relationships, hidden facts, romance flag, villain sheets and status) now live in **`data/cast.json`**. World NPCs from the world file are in `data/world-npcs.json`.

Look an NPC up with:

```
python3 tools/db.py npc "Mio"        # cast.json first, then world-npcs.json
```

Update them only from Voyage's story output (`npc-seen`, `npc-note`, `agenda`, `add-npc`; each needs `--turn N --evidence "..."`). See `README.md`.

What stays here is the director guidance that does not fit a data field.

## Using a card in a prompt

- **Intro line**: paste it into the `Crew:` line the first time an NPC appears (150 characters or fewer). Voyage creates the NPC from it. After that, use the name only. `check-prompt` warns when a planned NPC shows up without it.
- **Voice card**: key NPCs get one `Crew:` line in their voice.
- **Hidden**: director-only fields. Put one in a prompt only in the scene that needs it.

## Rooms

NPC housemates take `Sakura Lane Sharehouse/maple-bedroom` (Tatsuya), `loft-bedroom` (Mio), `street-bedroom` (Shin) and `sunrise-bedroom` (Sunny). Player characters choose from `courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom` and `river-bedroom`. With fewer than four player characters, the unclaimed rooms hold background 2B housemates: unnamed until a scene needs one, never carrying plot, and scattered with everyone else if 2B is dissolved.

## Romance and consent notes

- Romance is optional, never scripted, and never pushed by the director. Voyage follows the player's lead.
- Eligible (`romance_eligible: true` in `data/cast.json`): Tatsuya, Mio, Shin, Sunny, Ayame, Yūto (all adults, with adult player characters). Not eligible: Arimura, Shimazu, the House Manager, and every villain or fight NPC.
- Everything is consent-based. Any NPC can decline, and a decline ends it. A romantic beat still has to be earned by the relationship value.
