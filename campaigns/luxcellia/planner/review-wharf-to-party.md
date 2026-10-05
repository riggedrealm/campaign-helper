# Director review: turns 47 to 63 (wharf scene and party agreement)

Mode A, run on Opus from the planner session, 2026-10-05. Read-only. Spot-checked by the planner against the turn log: turns 57, 61 and 63 confirmed.

## Findings

turn 47: other: TONE-1 corrective Tone 'No similes, no narrating feelings' has run unreviewed since turn 34 or earlier and bans devices, kept at 48 and 49
turn 48: invention: Cut 'a modest eatery near the guild' puts the scene in a new venue that no area or fact in the database holds
turn 49: teleport: input was talk at the table, but Cut 'Skip to the street outside the eatery as the dusk bell rings' ends the meal and walks both to the wharf
turn 50: invention: Facts 'within about three metres of the pier edge' and 'A net winch with a counterweight', plus World 'the third pier', had no fact in the database
turn 51: other: NPC-5 observer Yumi calls targets for him: 'the bright patch moved' (51), 'which one is closest to him' (53), 'where the next strike will come' (54), 55, 56
turn 53: other: TONE-1 Yumi-voice fix set at 50, 'one flat body report at most' from 52, passes 3 turns here and runs unreviewed through 58
turn 57: outcome: 'She notices he favours his left leg and says so' states the PC's condition against his input (relaxed posture, injuries not hindering), repeated at 58
turn 57: other: NPC-4 Yumi's test was met at 56, yet 'She gives no yes, no no, no price tonight' defers the earned answer behind a new cart-in-daylight step, kept at 58, 59
turn 57: invention: World 'along the lamplit river road' invents a route (the wharf links only to outer-districts), reused at 59 'along the river road toward the market'
turn 61: outcome: 'Agree to all three and the answer is yes' settles a recruit ask without a roll, and 62 states it, 'so the answer is yes, said plainly'
turn 62: other: WLD-1 asked for a job lead, Yumi offers Ren's show and World porters on 'the famous bard' repeat it, one dated beat pushed twice with no other thread
turn 63: fact: Mizuho's 'Two names this time. Good.' contradicts f083 (Yumi gave the book a mark, no name) and assumes a pair entry the input never asked for
reviewed turns 47 to 63: 12 findings

## Applying it (director session, at a break)

Slip-tagged findings go in with `review-add`, one call per turn, joining same-turn findings with `;`:

```
python3 tools/db.py review-add --turn 48 --slips "invention: Cut 'a modest eatery near the guild' puts the scene in a new venue that no area or fact in the database holds"
python3 tools/db.py review-add --turn 49 --slips "teleport: input was talk at the table, but Cut 'Skip to the street outside the eatery as the dusk bell rings' ends the meal and walks both to the wharf"
python3 tools/db.py review-add --turn 50 --slips "invention: Facts 'within about three metres of the pier edge' and 'A net winch with a counterweight', plus World 'the third pier', had no fact in the database"
python3 tools/db.py review-add --turn 57 --slips "outcome: 'She notices he favours his left leg and says so' states the PC's condition against his input (relaxed posture, injuries not hindering), repeated at 58; invention: World 'along the lamplit river road' invents a route (the wharf links only to outer-districts), reused at 59 'along the river road toward the market'"
python3 tools/db.py review-add --turn 61 --slips "outcome: 'Agree to all three and the answer is yes' settles a recruit ask without a roll, and 62 states it, 'so the answer is yes, said plainly'"
python3 tools/db.py review-add --turn 63 --slips "fact: Mizuho's 'Two names this time. Good.' contradicts f083 (Yumi gave the book a mark, no name) and assumes a pair entry the input never asked for"
```

The five "other" findings are the director's own call (no `review-add`): two stale corrective `Tone:` lines (turns 47 and 53), the observer calling targets during the eel fight (NPC-5), the deferred earned answer at turn 57 (NPC-4), and Ren's show pushed twice at turn 62 (WLD-1).

## Planner notes

- Turn 63 is a judgement call: "Two names" may refer to the pair line (f080) rather than the ledger mark (f083). Record it or drop it.
- Two findings already shaped canon: the turn 61 yes is now recorded as accepted (f090, f092), so no repair is needed beyond the slip. The left-leg line at 57 and 58 and the turn 61 yes are two outcome slips in one stretch. Consider a canon trap if the pattern repeats (LOG-5).
- The NPC-5 pattern (an observer calling targets) ran five turns in one fight. Worth a line in `director.md` if fights with Yumi as observer recur.
