# Opening: Day 1 Move-In (scene card)

Director-only. **There is no director prompt for turn 1.** Voyage's existing "01 - Classroom 2B" story start produces the opening narration. The director steps in from turn 2, after the user sends the story output and the player inputs. This card is what to know before writing that first prompt.

## What the story start already establishes

From the world's "01 - Classroom 2B" story start, stored in `data/world.json` (do not repeat it in a prompt):

- **Day 1, Dawn**, `Sakura Lane Sharehouse/building-entrance`. State once, then treat as established time state.
- The **Sakura Lane House Manager** is the opening speaker. She explains the ordinary house rules (privacy, chores, safety, communication, quiet hours) and shows the player to an assigned private bedroom (`courtyard-bedroom`, `garden-bedroom`, `lilac-bedroom` or `river-bedroom`).
- Nobody is required to become a friend, join a party, share personal information, or stay in a conversation. Residents give space when asked and never enter locked private rooms.
- The player has the rest of **Saturday and all of Sunday** to settle in, work, rest, socialize, explore, or keep to themselves. Classes start **Monday, Day 3**.
- Player-character dialogue comes only from the player. The director never writes it.

So turn 1 ends with the Manager done with the rules and the player at or near their bedroom door. Turn 2 (the director's first prompt) continues from there.

## Who is home on move-in morning

Keep the opening to **one or two** housemates in the scene; the rest arrive later in the day.

| Who | Where / when | What they are doing |
|---|---|---|
| **Tatsuya Ōmine** | Present at the start. `shared-kitchen`, then the `resident-hallway` and `building-entrance`. | Up since five. Making tea and rice balls for the newcomers; tries to carry the tray quietly and fails (the cups rattle); apologizes. |
| **Shin Asakura** | Present at the start. On the front step or just inside `building-entrance`. | Eating a convenience-store breakfast, watching who arrives. Says little; leaves if the Manager's rules turn into a lecture. |
| **Mio Tachibana** | Home all along in `loft-bedroom`; not in the scene. | Door shut, light under it. Only sounds reach the hall: a faint whirr, a tapped screw. First seen late morning when she comes down for food once the house is quiet. |
| **Park Seo-yeon "Sunny"** | Arrives mid-afternoon at the front door by taxi. | Late transfer (arrives a week later than scheduled), too much luggage, a phone that never stops buzzing. Performs "fine". |
| **Arimura** | Day 3, orientation. | Absent until then. |
| **Shimazu** | Day 3, orientation. | Absent until then. |
| **Yūto** | Day 4, `Chikara Academy/vending-machine-nook`. | Absent until then. |
| **Ayame** | Day 6 at the tournament, at a distance; first jab Day 10. | Absent until then. |

The House Manager is at the entrance in the mornings; off duty Wednesday afternoons.

## First world moves and the small surprise

Every prompt needs a world move because NPCs are passive. Candidates for the first prompts, in order of use (one beat per turn):

1. **Turn 2 world move**: Tatsuya arrives with the tea tray and startles when he sees the newcomer; a cup rattles off the tray and lands in his hand (his power leaking). Shin watches from the step.
2. **Turn 2 or 3 small surprise (one per scene)**: the paperclips on the Manager's sign-in sheet rearrange to spell WELCOME when the player writes their name. Nobody admits it; the loft above hums once. (This is Mio, and the first Mio clue.)
3. **Turn 3 world move**: the Manager mentions a resident who is arriving late today ("a transfer, due last week"); the evening welcome dinner is suggested for the `shared-lounge`.
4. **Turn 4 world move**: mid-afternoon, a taxi stops at the lane and Sunny arrives.
5. **Turn 5**: evening and the welcome dinner. Optional house cohesion beat (+3 Standing).

Do not fire more than one surprise in a scene. Keep Mio unseen until late morning at the earliest.

## The decision the scene builds toward

**Do you take the offer of the house's first shared meal tonight, or spend the weekend your own way?**

The Manager (and Tatsuya) invite the player to the welcome dinner in the `shared-lounge` / `shared-kitchen` this evening. It is an offer, never an order. Whatever the player chooses, the weekend stays open: the neighborhood, a job through `WorkLink Exchange/job-board`, a nap, Mio's door, Shin's step. The scene ends with the invitation; the player decides what to do with the day.

## Intro lines for first-appearance prompts

Paste into the `Crew:` line the first time each NPC appears. Each is 150 characters or fewer. The source of truth is the `intro_line` field in `data/cast.json` (`python3 tools/db.py npc <name>`); this table is a copy for reading.

| NPC | Intro line | Length |
|---|---|---|
| Tatsuya Ōmine | `Tatsuya Ōmine, 19: huge, soft-eyed, hoodie sleeves too short, carrying a tea tray as if it might break.` | 103 |
| Shin Asakura | `Shin Asakura, 19: lean, scar through one eyebrow, bleached fringe, hands in jacket pockets, watching the door.` | 110 |
| Mio Tachibana | `Mio Tachibana, 18: small, goggles in messy hair, oil-stained sleeves, pockets clinking with screws and bolts.` | 109 |
| Park Seo-yeon "Sunny" | `Park Seo-yeon "Sunny", 19, Korean: glossy waves, oversized sunglasses indoors, designer luggage, phone always buzzing.` | 118 |

The House Manager needs no intro line; use her name.

## Turn 2 ingredients (not a prompt)

When the user sends the story output and inputs, build the first prompt from these. This is not a ready-to-paste prompt; the director writes it fresh from what the player actually did.

- **Cut**: "Continue at `Sakura Lane Sharehouse/building-entrance`" (or the bedroom, if the story start ended there).
- **Tone**: light, domestic.
- **Crew**: Tatsuya (one line in his voice; intro line the first time); Shin (intro line; says very little); House Manager (one warm line).
- **Facts**: none needed on turn 2. Hidden facts (Mio's debt, the Annex Cohort, Ayame's guilt) stay out.
- **World**: one world move (Tatsuya's tray), the paperclip surprise as the small surprise, and the quest seed `Start quest "Move-In Weekend" (giver: Sakura Lane House Manager): settle in, meet housemates, prep for Monday.` if the budget allows.

Check the length of the written prompt before it goes out (700 characters, labels included).

## Cautions

- Do not state what the player says or does. React to the story output.
- Do not push a conversation or a party on the player; offer.
- Do not let a housemate enter a locked room.
- Do not name Standing or any hidden fact.
- Do not move the player; the story start has already set the room.
