# Revamp decisions

Calls made on the user's behalf during the director revamp, with the reason, so a new chat can pick up from the repo alone. User decisions live in `handoff.md`; open questions are listed in the latest phase report and at the end of `rule-inventory.md`.

## Phase 1 (2026-10-04)

- **D1. Extra playbooks.** Beyond the handoff's list: `pacing.md` (scenes, budgets, acts, day turnover), `reveals.md`, `campaign-start.md`, `hidden-score.md`, plus `director/reference.md` for the payload schema. Reason: each has a clean trigger, and keeping them out of `core.md` is what keeps the always-loaded text near the 10 KB target.
- **D2. Stay form of `Cut:`.** "Continue at <Location/area>, same moment." Reason: merges the skill's form (naming the place guards against teleports) with player-agency's "Stay, same moment." (guards against skips).
- **D3. Parked versus set aside.** After a pivot the old arc is `parked`; "go back" revives it; `set_aside` stays for an arc dropped for good. Reason: the handoff keeps the drift rule's "Re-aim?" and adds parking; both need a status.
- **D4. Briefs reference rules, never copy them.** Subagent briefs point at rule ids in the playbooks. Reason: one home per rule.
- **D5. Campaign rules move at each switch.** Canon traps, main NPCs and world-sheet text move to `campaign.json` and `director.md` when each campaign switches, not before. Reason: campaign rollout is out of scope until the user raises it.
- **D6. Lean brief name.** The new per-turn brief is `turn-brief`; `prep` stays unchanged for the old skills and becomes an alias of `turn-brief --full` at switch. Reason: `brief` is taken (the character card), and changing `prep` in place would break the old skills, which must keep working through phase 3.
- **D7. `quest-end` repurposed.** It becomes the inferred "apparently ended" record that `sync` confirms; `quest-obj` retires. Reason: the handoff makes a quest's apparent end an inferred item, and Voyage owns progress.
- **D8. Review findings are written by the main chat.** The director-review subagent stays read-only; the main chat records its findings with `review-add`. Reason: the one-writer rule for subagents.
- **D9. Planning offer without arc functions.** "No arc is live" is a one-line offer at chat start, never a per-turn trigger. Reason: arc functions are optional, and a campaign without them would otherwise be nagged every turn.
- **D10. Variety tags map to pillars.** fight to combat, talk to social, explore to exploration, mystery to mystery; downtime is reported on its own. Reason: retros compare the scene mix with session zero, which uses the pillar names.
- **D11. Campaign sheets narrow, never loosen.** A campaign's `director.md` may add a limit to a generic rule and names the rule id it narrows; it never loosens a bootstrap invariant. Reason: one home per rule while keeping real campaign differences (Luxcellia's chain quests, Joestar's hard lines).
- **Phase 1 audit.** A fresh read-only subagent checked both inventories against every source. Its findings (missing rules, two-home overlaps, eight unlisted conflicts, tool strings pointing at retiring docs) were applied before commit.

## User answers after phase 1 (2026-10-04)

These are the user's decisions, recorded here so the next chat has them. Details in `rule-inventory.md` section 8.

- **Turn order, both modes:** lean brief, `check-prompt`, send the prompt, then `commit-turn`. Recording and the push must happen after the prompt is out, in the downtime while the player reads Voyage's output. This replaces the handoff's "two tool calls" target with three (LOOP-2).
- **Push every turn:** the tool default becomes 1; Joestar's `push_every: 5` override goes (phase 3).
- **Skips:** never offered, weekly montage included.
- **`state-new.txt`:** deleted in `cc4650e` (still in git history; no force push done).
- **Voyage-voiced PC lines:** the repair line is removed for now, the same for every campaign (X-16). The live skills and their docs stay unchanged until each campaign switches.
- **pytest:** install it. PyPI is blocked from the cloud sandbox, so it was installed from the official GitHub sources: shallow clones of `pytest-dev/pytest` tag `8.3.3`, `pytest-dev/pluggy` tag `1.5.0` and `pytest-dev/iniconfig` tag `v2.0.0` into `/home/claude/.pydeps`, a hand-written `_version.py` in `_pytest/` and `pluggy/` (they are normally generated at build time), and a `.pth` file in `/usr/local/lib/python3.13/dist-packages` listing the three `src` folders. A new session must redo this.
- **Phase 2 waits for the user's go-ahead.**

Test baseline at `cc4650e`: 221 tests, 211 pass, 1 skipped, 9 fail. The 9 failures are stale pins (eight Joestar tests pin the tick 481 resync, but Joestar has been played to turn 482; one test pins Class 2B's skill at `2026-10-04.2`, the repo is at `.3`). Fixing them is phase 3 brief 0.
