# Act 3 sketch (DRAFT, not approved)

Planner session, 2026-10-05, at turn 482, while Arc 4 is still live.

The user asked to sketch Act 3 early. They had no preference on direction, ending, play mix or pacing, so the planner picked defaults from the bible (1, 6, 7) and the feedback log. Nothing here is approved.

**Apply nothing until Act 2 closes.** Then, in the Act 3 planning session:

1. Ask the ARC-6 retro question.
2. Confirm session zero below with the user and record it.
3. Show the pitch's shared fields, then run `act-plan 3` and `act-approve 3`.
4. Draft the first charter.

## Session zero (draft; ARC-2 says ask the user, so confirm each line)

- **Tone:** serious stakes with banter and comedy between; crime and vigilante register (state it in `Tone:` when dark); fights puzzle-first, spectacle to finish; earned wins.
- **Lines:**
  - no ally betrayals (bible 1.2);
  - romance only with the played love interests, adults only, never villains or the excluded NPCs (`director.md` NPC-7);
  - the director never scripts a PC.
- **Veils:** none recorded. Ask the user.
- **Pillars:** combat=3, social=3, exploration=1, mystery=2. The table loves fights and relationships; each arc has a showcase fight and a relationship under pressure.
- **Pacing:** tight arcs of 25 to 30 turns; three-turn finales with a real choice each turn; cut what stalls; no invented time-skip hooks. This answers the Arc 3 drag (about 60 turns) and Arc 4's overrun.
- **Ending hope:** triumph, with a cost. Daigo falls; something real is paid; Book 2 doors are seeded lightly, never as cliffhangers (bible 1).
- **Players:** 2.

```
db.py session-zero --tone "serious stakes with banter; crime and vigilante register; puzzle-first fights" --lines "no ally betrayals;romance only with the played love interests, adults only, never villains" --veils "" --pillars combat=3,social=3,exploration=1,mystery=2 --pacing "tight arcs of 25 to 30 turns; three-turn finales; cut what stalls" --ending-hope triumph --players 2
```

`--ending-hope` takes triumph, bittersweet or open. Record "with a cost" in the act pitch's `ending_shape`.

## Act 3 pitch (draft for `act-plan 3 --file`)

The direction blends two of the three offered options. Its spine is Daigo's War (the bible's act title and purpose); it opens on Siege of the Home, the bible's emotional question.

### Shared fields (what the user sees)

| Field | Draft |
|---|---|
| `title` | Daigo's War |
| `theme` | What you will risk to protect your own when the enemy can no longer be outplayed, only outlasted |
| `question` | Who rules Kobuncho when the king comes down to fight for it? |
| `builds_to` | A showdown with Daigo Renjiro in the open, in front of the district |
| `stakes_scale` | Kobuncho: the whole district, and everyone the crew chose |
| `ending_shape` | Triumph with a cost |

### Hidden fields (director only)

**`turning_point`:** blind, broke and paranoid after Act 2 (bible 5 pressure curve), Daigo stops ruling through captains and moves personally, hitting what he can still see without eyes: the crew's home ground.

**`notes`:** each Act 3 door is chosen at charter time, at most one or two per arc, and never all at once:

- Daigo puppeted Iori Vale into Jostin's strike (t182): the personal core, and the payoff for Jostin's Blackstar control.
- The tunnels (Gara's tip) as a battlefield.
- The combat-data buyer: the invoice seeded in Arc 4; a Book 2 door, seed lightly.
- The ten-win strike team.
- Harumi Wharf.
- The bigger power broker ("Masat...", name truncated): a Book 2 door.

No sympathetic reveal for Daigo. The Act 3 showcase villain sheet (Iron Palm Strike, Territorial Command, Unshakable Stance: rule, tell, weakness, finisher) is built with the finale charter.

**`checklist`:**

- Arcs of 25 to 30 turns; three-turn finales with a real choice each turn.
- No ally betrayals.
- No invented time-skip hooks after finales.
- Every charter gives Jostin love or home and Jovian strength or purpose (ARC-22).
- One `recruit_seat` per charter: check whether Arc 4's Aether Head seat filled before choosing (ARC-8 narrowed).

## Arc outline (kinds only; each becomes a charter, user-approved)

| Arc | Working title | Shape | Showcase kind | Relationship under pressure |
|---|---|---|---|---|
| 5 | Siege of the Home | Daigo's people hit Lumière, Tetsu Gym and the people the crew chose; defend first, then find where the blows come from | a defence of home ground | Jostin: home (Lumière, Maki, the hostesses) |
| 6 | Strike Back | the crew takes the fight into Daigo's remaining ground; rival crews (Shirogane, Honebi, public in Kobuncho's basic info) circle the vacuum | an assault on enemy ground | Jovian: purpose (what ruling the street would make him) |
| 7 | The King in the Street | Daigo in the open; Book 1 finale | the Daigo Renjiro showcase (bible 6.1) | both brothers; love and strength tests at the fork |

About 80 turns in all.

## Stale items spotted (for the director)

- **Bible 7, Jovian's purpose test,** still says "the footage for the Kagero files". The trade is now footage for Haruto's police file (`card-4-3-neutral-ground.md`).
- **Bible 1.3** suggests Kobuncho venues for 4-3's neutral ground, but the card uses `Central Tokyo/media-plaza`. Either one exists in the database; pick one before the scene opens.
