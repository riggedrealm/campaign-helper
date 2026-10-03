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

Keep the opening to **one or two** housemates in the scene; the rest arrive later in the day. Introduce **at most one new NPC per turn**.

| Who | Where / when | What they are doing |
|---|---|---|
| **Tatsuya Ōmine** | Present at the start (new NPC on turn 2). `shared-kitchen`, then the `resident-hallway` and `building-entrance`. | Up since five. Making tea and rice balls for the newcomers; tries to carry the tray quietly and fails (the cups rattle); apologizes. |
| **Shin Asakura** | On the front step or just inside `building-entrance` from turn 3 (one new NPC per turn, so Tatsuya comes first). | Eating a convenience-store breakfast, watching who arrives. Says little; leaves if the Manager's rules turn into a lecture. |
| **Mio Tachibana** | Home all along in `loft-bedroom`; not in the scene. | Door shut, light under it. Only sounds reach the hall: a faint whirr, a tapped screw. First seen late morning when she comes down for food once the house is quiet. |
| **Park Seo-yeon "Sunny"** | Arrives mid-afternoon at the front door by taxi. | Late transfer (arrives a week later than scheduled), too much luggage, a phone that never stops buzzing. Performs "fine". |
| **Arimura** | Day 3, orientation. | Absent until then. |
| **Shimazu** | Day 3, orientation. | Absent until then. |
| **Yūto** | Day 4, `Chikara Academy/vending-machine-nook`. | Absent until then. |
| **Ayame** | Day 6 at the tournament, at a distance; first jab Day 10. | Absent until then. |

The House Manager is at the entrance in the mornings; off duty Wednesday afternoons.

## Scene budget, first world moves and the small surprise

**Move-in scene budget: 3 turns (turns 2 to 4).** The scene is arrival and admin, so it stays short; when it is over, cut to the next beat rather than letting it drift. Then **skip to late morning** for Mio's first appearance (budget 2 to 3 turns), and **skip to the evening** for the welcome dinner (budget 3 to 4 turns). Offer each skip at the natural lull (never force one: if the players are mid-conversation or want to explore, follow them; see `arc-bible.md`, section 14). Waiting, walking round the lane and the dead hours between are cut, not played.

Every prompt needs a world move because NPCs are passive. The move-in scene, in order of use (one beat and at most one new NPC per turn):

1. **Turn 2**: Tatsuya arrives with the tea tray and startles when he sees the newcomer; a cup rattles off the tray and lands in his hand (his power leaking). The House Manager mentions that the house Wi-Fi, chore rota and dinner list run on Pulse, and that Tatsuya can help: the **Ability and Pulse Tutorial** seed.
2. **Turn 3 (small surprise, one per scene)**: the paperclips on the Manager's sign-in sheet rearrange to spell WELCOME when the player writes their name. Nobody admits it; the loft above hums once. (This is Mio, and the first Mio clue.) Shin is on the step, watching. The **Move-In Weekend** seed goes here (one quest per turn).
3. **Turn 4**: the Manager mentions a resident who is arriving late today ("a transfer, due last week") and suggests the evening welcome dinner in the `shared-lounge`. Offer the skip to late morning.
4. **Late morning (turns 5 to 7, 2 to 3 turns)**: Mio comes down for food once the house is quiet. Offer the skip to the evening.
5. **Evening (3 to 4 turns)**: the welcome dinner. Sunny arrived by taxi in the afternoon (the skip covers it; if the player is out front, play it as one short arrival turn). She is introduced with her intro line on her first turn on screen. Optional house cohesion beat (+3 Standing).

Do not fire more than one surprise in a scene. Keep Mio unseen until late morning at the earliest.

## The decision the scene builds toward

**Do you take the offer of the house's first shared meal tonight, or spend the weekend your own way?**

The Manager (and Tatsuya) invite the player to the welcome dinner in the `shared-lounge` / `shared-kitchen` this evening. It is an offer, never an order. Whatever the player chooses, the weekend stays open: the neighborhood, a job through `WorkLink Exchange/job-board`, a nap, Mio's door, Shin's step. The scene ends with the invitation; the player decides what to do with the day.

## Intro lines for first-appearance prompts

Paste into the `Crew:` line the first time each NPC appears (optional for these four, see below). Each is 90 characters or fewer (name, age, the most visual details). The source of truth is the `intro_line` field in `data/cast.json` (`python3 tools/db.py npc <name>`); this table is a copy for reading.

| NPC | Intro line | Length |
|---|---|---|
| Tatsuya Ōmine | `Tatsuya Ōmine, 19: huge, cat-ear beanie, shy amber eyes, a hoodie two sizes too small.` | 86 |
| Shin Asakura | `Shin Asakura, 19: white fringe over one eye, scarred brow, bomber jacket, hands hidden.` | 87 |
| Mio Tachibana | `Mio Tachibana, 18: tiny, violet-tipped bob, cracked goggles, screws orbiting her.` | 81 |
| Park Seo-yeon "Sunny" | `Park Seo-yeon "Sunny", 19, Korean: rose-gold waves, heart sunglasses, phone raised.` | 83 |

All four housemates are also in `New_World.json` (status `world` in `data/cast.json`), so Voyage already knows them and `check-prompt` does not demand the intro line; it is still the safest way to anchor the look on a first appearance, and it keeps the one-new-NPC-per-turn pacing.

The House Manager needs no intro line; use her name.

## Turn 2 ingredients (not a prompt)

When the user sends the story output and inputs, build the first prompt from these. This is not a ready-to-paste prompt; the director writes it fresh from what the player actually did.

- **Cut**: "Continue at `Sakura Lane Sharehouse/building-entrance`" (or the bedroom, if the story start ended there). Move-in scene budget: 3 turns (turns 2 to 4).
- **Tone**: light, domestic.
- **Crew**: Tatsuya (one line in his voice; his intro line, the only new NPC this turn); House Manager (one warm line: the house Wi-Fi, chore rota and dinner list run on Pulse, and Tatsuya can help). Shin waits for turn 3.
- **Facts**: none needed on turn 2. Hidden facts (Mio's debt, the Annex Cohort, Ayame's guilt) stay out. Write any fact as a plain world truth (Facts guidance in `.claude/skills/class2b-director/SKILL.md`).
- **World**: one world move (Tatsuya's tray) and the quest seed `Start quest "Ability and Pulse Tutorial" (giver: House Manager): create your first Ability, then sign up for Pulse; the house Wi-Fi and lists run on it.` The Move-In Weekend seed `Start quest "Move-In Weekend" (giver: Sakura Lane House Manager): settle in, meet housemates, prep for Monday.` and the paperclip surprise follow on turn 3 (one quest and one new NPC per turn).
- **Reminder (director-side, not for the prompt)**: the Ability and Pulse Tutorial is **due before the placement tournament on Days 6 to 7**. Characters start with no abilities. It is player-directed: never invent the character's ability concept, account or consent; explain how ability creation and Pulse sign-up work if asked. If it is still open on Day 4 to 5, have the Manager or Tatsuya offer help again, once.

Check the length of the written prompt before it goes out (the prompt limit, 840, see `db.py state`; labels included).

## Cautions

- Do not state what the player says or does. React to the story output.
- Do not push a conversation or a party on the player; offer.
- Do not let a housemate enter a locked room.
- Do not name Standing or any hidden fact.
- Do not move the player; the story start has already set the room.
- Do not invent the player character's ability, Pulse account or consent to sign up. The player decides all three.
