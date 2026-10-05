# Hook kit for Act 1 "Severance" (director only)

New generic rules (2026-10-05, user: "plan like a great D&D DM; this applies to all campaigns"): every front keeps a hook kit (ARC-8, ARC-24), and a replan waits for real disinterest (ARC-25). See director/playbooks/arc-planning.md and pivot.md.

Luxcellia has no arc record yet: Act 1 lives in the arc bible (`bible act1`, section 4). The bible names no fronts, so the planner named three pressures from the act's purpose, beats and the 4.2 obstacles table.

**Use:**

- When the PCs go somewhere unplanned, deliver the hook whose door is where they already are, inside what they chose. At most one hook per scene.
- Replan only on the interest test: three hooks declined through at least two doors, or the user says so. Record each declined hook as a `fact` until an arc record exists.
- When an Act 1 charter is filed, copy this list into its `hidden.hooks`.

**Checked by the planner:**

- Kazuki Ōhara, Mizuho Kaimaku, Toma Kirisawa and Yumi Aokiba are in play.
- `Aureliath/guild-quarter` exists.
- The courier's look matches canon f026 (grey, brass lantern).
- No hidden ladder step is used. Ren Tsukishiro is not used, since Alistair hasn't met him on screen.

```json
[
  {"front": "The private board", "door": "person", "text": "Kazuki Ōhara catches up with them wherever their errand has them to say a soft-voiced man in grey offered him tea in the Guild queue and asked whether anyone expects him home, and he asks whether he should tell Mizuho."},
  {"front": "The private board", "door": "person", "text": "A Guild runner finds them mid-errand with a note in Mizuho Kaimaku's hand: a posting she never stamped turned up on her counter after they left, and she asks whether either of them saw who put it there."},
  {"front": "The private board", "door": "place", "text": "On the Guild hall posting wall in the Guild Quarter, a fresh grey-wax slip hangs among the stamped rows, offering work for one person alone at a pay above anything stamped, with no sender named."},
  {"front": "The private board", "door": "world", "text": "Wherever they stop, a figure in grey stands at the crowd's edge with a small brass lantern whose flame does not move in the breeze, and is gone before anyone reaches the spot."},
  {"front": "The private board", "door": "world", "text": "Somewhere along their errand a grey-wax slip turns up in Alistair's path, offering solo work at a pay above anything stamped and naming no sender."},
  {"front": "The Crown's eye", "door": "person", "text": "Toma Kirisawa turns up in a plain cloak wherever their errand takes them, claiming it is for ingredients, carrying one portion more than is needed, and he keeps his back to the street while a palace guard patrol passes."},
  {"front": "The Crown's eye", "door": "place", "text": "At the plain Guild Quarter inn, the innkeeper says someone in junior Court Mage robes asked which room the fifth one keeps, was told the house answers no questions, and left without a name."},
  {"front": "The Crown's eye", "door": "world", "text": "A palace page in Crown livery brings a note under the princess's seal to wherever Alistair is, asking in two clipped lines what the Guild's collateral has been doing with his days."},
  {"front": "The Crown's eye", "door": "world", "text": "Wherever they stop, a junior in Court Mage robes stands across the street writing on a slate, and walks off when anyone looks back."},
  {"front": "The misfire's name", "door": "person", "text": "Yumi Aokiba reports flatly that two of her morning customers asked whether her new partner is the fifth one who read nothing, and that she charged both of them extra for asking."},
  {"front": "The misfire's name", "door": "person", "text": "Kazuki Ōhara mentions, with a laugh that runs too long, that the queue has started calling Alistair the palace zero and that he told one of them to stop, adding that it's fine."},
  {"front": "The misfire's name", "door": "place", "text": "In the Guild hall queue, a clerk reads Alistair's rank column aloud wrong, the word zero carries, and the room goes quiet."},
  {"front": "The misfire's name", "door": "world", "text": "Wherever they stop to trade, a merchant recognizes Alistair as the stranger who came out of the palace side door and says the price a second time, slower."}
]
```
