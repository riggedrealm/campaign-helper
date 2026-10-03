# Expression: making NPC beats vivid

Read when a `Crew:` line comes out flat. The rule lives in `.claude/skills/luxcellia-director/SKILL.md` (Prompt format, `Crew:`). The data lives in each NPC's `expression` kit in `cast.json`; `db.py brief <name>` prints it as "SHOW (pick one, vary):".

## The rule
Spotlight NPCs (1 to 2 per turn) get, in their `Crew:` clause: one specific gesture or habit, the feeling under it, and their way of talking. A short quoted line of THEIR words is a fine flavour hint; never put words in a player character's mouth. Pick from the kit and vary it turn to turn: do not repeat the last turn's gesture. Everyone else "reacts in character".

## Flat versus expressive
- Flat: `Crew: Tatsuya offers tea; Shin watches.`
- Expressive: `Crew: Tatsuya slides a mug over without looking up, gruff to hide that he waited up ("it was extra"); Shin leans in the doorway, arms crossed, rating the newcomer like a lock he hasn't picked.`

`check-prompt` WARNs when a named NPC's clause uses only flat verbs (reacts, agrees, watches, nods, listens, looks, says, smiles). It never FAILs.

## The `expression` kit (optional, per cast entry)
```json
"expression": {
  "gestures": ["3 to 4 signature physical habits"],
  "moods": {"happy": "how it shows on them", "angry": "...", "embarrassed": "...", "lying": "...", "hurt": "..."},
  "lines": ["two sample lines in their voice", "..."],
  "never": "one thing they never do"
}
```
- Derive it from the cast entry (voice card, psychology, tells) and the world record; one short line each.
- It must not leak: respect each act's `wont_do_yet` and never hint a `hidden` fact or a still-hidden ladder step. Gestures and moods are surface behaviour only.
- `brief` shows "expression: not set" when a kit is missing; `verify_data` rejects malformed kits.
