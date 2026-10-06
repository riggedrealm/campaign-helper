# Night Line: world sheet

The generic director skill reads this sheet at chat start. It holds only what is particular to this campaign: facts and limits, never generic rules. A narrowing may only add a limit and never loosens a bootstrap invariant (SHEET-1 in `director/core.md`).

## World file and calendar

- World file: none. This campaign has no Voyage world file; everything lives in `data/`. It is a TEST campaign for Campfire mode (`director/playbooks/campfire.md`).
- Weekday of Day 1: Friday (campaign.json `start_weekday`). The day rolls over at 05:00 (`day_start`), so the whole night run from 23:40 to dawn is Day 1 and Day 2 is Saturday.
- Acts and milestone days: one act, 1 The Last Train (Days 1 to 2). Milestones: the act starts on Day 1 at 23:40 on Platform 4; the static in the tunnel is the scene's one surprise, late Day 1; the finale is the end of Day 2 at Harrow Street Depot.

## Earned changes

- Tib opens up only when the story earns it: the reveal ladder in `thread "What Tib is carrying"` (four steps, each earned by play, never by the clock).
- Sandoval eases only when the signal box has an honest explanation.
- The static backs down only to calm voices or light it cannot kill; it never stops because the story needs it to.

## Fixed NPCs

- Mara Venn (night station master), Tobias Achterberg (courier), Officer Priya Sandoval (transit police) and June Halloway (busker) exist from the start and need no intro line.
- No other named NPCs are invented: the Line 9 driver, passengers and Registry staff are unnamed background.

## Overreach example

A player says they rewire the signal box with their power in one move. That is the attempt only: rule it a heroic roll, and the world answers within the power (a spark, a half-fixed relay, a hum of current), never a signed-safe signal box.

## Consent for scripted quests

none

## Home base and intake questions

Standard intake is in `director/playbooks/campaign-start.md` (START-1); this sheet adds to it.

- Home base or room choices: none. Players are commuters and strangers stuck at the station; there are no rooms (`pc_rooms` is empty). The start is `Meridian Central Station/platform-4`.
- Campaign questions for each player character: none. In Campfire the players build their own characters on the Campfire server; do not run intake or invent sheets.

## Narrowed rules

none.

## Test campaign for Campfire mode

- This is a throwaway starter campaign made to test Campfire mode. It is one act with one threat, one secret, two quests and four NPCs, enough to exercise rulings against NPCs of different attitudes, a threat to press, hold or flee, a quest start and a quest complete, a scene change and the hidden-words scan.
- Player characters come from the room's party lines in each round packet. There is no `pc-add`, no sheet in `data/state.json` and no room assigned to anyone. Never invent a player character.
- There is no Campfire room code yet: the owner adds `campfire_room` to `campaign.json` when the room exists.
- `campfire-start.json` (campaign root) is the GM's optional first `gm scene` request. It holds no hidden word.
- The static (threat id `static`, tier `minor`) is director-only until it appears. Add it with one `threat-add` op when someone goes toward the tunnel or the static is cornered; it is the scene's one surprise. Rules text: "Lights die and phones scramble within a carriage-length of it. It lashes out when cornered or shouted at; it backs off from calm voices and from light it cannot kill."
- Nobody dies. A hold, a flee or a talked-down static are as valid as a press.

