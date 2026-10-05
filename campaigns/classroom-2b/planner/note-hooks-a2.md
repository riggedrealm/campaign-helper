# Hook kit for A2 "Three Bouts and a Board" (director only)

New generic rules (2026-10-05, user: "plan like a great D&D DM; this applies to all campaigns"): every front keeps a hook kit (ARC-8, ARC-24), and a replan waits for real disinterest (ARC-25). See director/playbooks/arc-planning.md and pivot.md.

**Apply at a break.**

1. Merge the list below into A2's `hidden.hooks`, then run `db.py arc-plan --id A2 --file F.json`. Start F.json from the current A2 (`arc A2`); A2 is still a draft.
2. **Checked by the planner:**
   - front names match A2;
   - Arimura, Yūto, Sunny, Shin, Mio and Tatsuya are in the cast;
   - Sakura Lane building-entrance and shared-lounge, and the arena's spectator-gallery, training-bays and officials-booth, are existing areas.

**Open items before approval:**

- **Bonds:** the person hooks assume Move-In builds the PCs' bonds with the housemates, Arimura (from Day 3) and Yūto (from Day 4). Check them against the real bonds when Move-In closes.
- **Ayame's jab:** Move 3 of the 1A front has Ayame make a jab to a PC on Day 7. Her brief's "won't do yet" says she won't speak to 2B beyond a polite cut until Day 10. The kit has her only watching; settle the front move before approval.
- **Arena hooks:** they are place hooks only while the PCs keep returning to the arena on Days 6 and 7. If the PCs leave, use the house or world hooks.

```json
[
  {"front": "The Placement Board", "door": "person", "text": "Arimura finds the team wherever it is between bouts, counts heads out loud, reads off the time and opponent of their next bout, says \"Aim higher,\" and leaves."},
  {"front": "The Placement Board", "door": "person", "text": "Yūto turns up wherever the PCs are between bouts, presses cold vending-machine cans into their hands and asks how the last bout actually went before the board updates."},
  {"front": "The Placement Board", "door": "place", "text": "When the PCs come home on Day 6 night, the noticeboard at the Sakura Lane building-entrance holds a printout of the brackets with each housemate's bouts circled in a different pen."},
  {"front": "The Placement Board", "door": "world", "text": "Wherever the PCs are after Round 2, every first-year's phone buzzes with a Pulse alert that provisional marks are up in the officials-booth window, and the people around them start checking."},
  {"front": "1A in the Gallery", "door": "person", "text": "Sunny drops down beside the PCs wherever they are, reads a 1A student's caption on a Pulse clip of their bout aloud in her camera voice, and asks them for a better comeback."},
  {"front": "1A in the Gallery", "door": "person", "text": "Shin, leaning in the nearest doorway, tells the PCs flatly that 1A took the best rows and has phones out for every 2B bout, and that he is watching them back."},
  {"front": "1A in the Gallery", "door": "place", "text": "Whenever the PCs are at Chikara Battle Arena, 1A holds the best rows of the spectator-gallery, with Ayame sitting straight-backed among them and not cheering."},
  {"front": "1A in the Gallery", "door": "place", "text": "At Sakura Lane, the shared-lounge television's Pulse feed shows a 1A student's clip of a 2B bout under a mocking caption, already shared a few hundred times."},
  {"front": "1A in the Gallery", "door": "world", "text": "Wherever the PCs are, Pulse clips of their bouts go around with mocking 1A captions, and strangers nearby glance up from their phones at them."},
  {"front": "Tatsuya's Restraint", "door": "person", "text": "Tatsuya finds the PCs wherever they are with wrapped rice balls for the team, his own hands taped up, and apologizes that he will not spar with anyone at full strength."},
  {"front": "Tatsuya's Restraint", "door": "person", "text": "Mio sends the PCs a long run-on text asking them to get a small damper she built into Tatsuya's hands before his bout, because she cannot find him herself."},
  {"front": "Tatsuya's Restraint", "door": "place", "text": "On results night at Sakura Lane, the dinner Tatsuya cooked sits covered on the shared-lounge table and his seat stays empty."},
  {"front": "Tatsuya's Restraint", "door": "place", "text": "Whenever the PCs pass the arena's training-bays, Tatsuya is in one alone, wrapping his hands and drilling at half strength."},
  {"front": "Tatsuya's Restraint", "door": "world", "text": "Between bouts, wherever the PCs are, talk and Pulse posts spread that Tatsuya blocked a teammate's hit in his own bout and would not let the force go."}
]
```
