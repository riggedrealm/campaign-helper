# Pressure card: 4-3 Neutral Ground (twist reveal, budget 3)

This card is director-only. The Opus card was checked by the planner, which made these edits:

- **Time:** set by the t484 invitation (Day 21 Friday evening), not straight on from 4-2.
- **The trade:** the crew's footage for Haruto's police file. There are no "Kagero files": the archive was buried and nothing was taken (bible 5.2; f006, f063).
- **Archivist step 2:** reveals here on meeting him.

Open with `scene-start "Neutral Ground" --kind talk --budget 3 --card @this-file`.

Checks run: `loc "Central Tokyo" media-plaza` exists, as do business-avenue, arcade-quarter and rooftop-gardens. `canon "police file"` gives f006 and f063. `thread` gives The Archivist's name step 2 (gate 4-3) and The Lumiere clip step 1 (gate 4-3). No line states a PC outcome.

## 1. Where the PC is heading

- **Jostin:** hands-on. He used a knife and chains on the sedan, kept Eagle Vision on the driver, asked "who do you work for", took the phone and called Plan B.
- **Jovian:** runs the comms (Kaito on point, Haruto and Nobu on recon). He drove Road Hog through the van, then leaned back and let Jostin lead. At t482 he collared the driver to use as a guide.
- No PC threads are recorded yet. Both arrive only if their input accepts the t484 invitation (CUT-2).

## 2. NPC wants now

Place: `Central Tokyo/media-plaza`: screens, studios, café terraces. An incident here is citywide news within minutes. The meeting is at the time the invitation named.

- **Kiriyama:** wants to keep working. He trades copies of the crew's footage (the Tetsu Gym doorstep, the wharf) for Haruto's police file (the ledger-page photos).
- **Bodyguard** (Mogami, never named on screen): wants to do the job; he is bored.
- **Haruto:** wants a clean number; knows his police file cuts both ways.
- **Reiko:** wants every hand in view and Sena out of any frame.
- **Ayame:** wants to own the angle and keep her followers out of it.
- **Nobu:** counts the lenses; Dead Air here would black out a live broadcast.
- **Records deputy:** wants not to be handed back. He is in the scene only if the crew holds him.

## 3. If the PC engages

**Turn 1**
- Kiriyama has a corner café table and coffee ordered for everyone; his own cup stays untouched. "I only keep what you have shown me."
- The bodyguard stands at his shoulder, weight even. When a PC shifts weight or anyone tenses, he murmurs a source ("The wharf, left hook.") and nothing more.
- Nobu: "Every screen here is a lens."

**Turn 2**
- Kiriyama shows a tablet with the doorstep and the wharf. "Shall we trade?"
- Haruto asks whether the price buys originals or copies.
- Kiriyama goes still mid-sentence, eyes unfocused (his tell). Then he plays a clip filmed at table height inside Lumiere's back office.
- Nobu: "Phone lens. Not CCTV." Ayame puts her phone down and stays silent.

**Turn 3**
- Whatever the crew answers, Kiriyama nods as if granting a favor, pays and leaves first; the bodyguard leaves last. Reiko steps into the bodyguard's line.
- If a PC starts a fight: Kiriyama backs off and never fights, and the bodyguard counters the first move he recognizes. Broadcast cameras swing round. Voyage rolls the fight; the prompt is conditional on combat state.

## 4. If not

- **If the talk stalls or breaks:** Kiriyama still plays the clip, leaves the tablet running and walks away. The twist lands either way.
- **If the crew never comes:** the clip's first frame lands on both brothers' phones from an unknown number, with "Shall we trade?" and the plaza.

## 5. One surprise

Small: as a courtesy, Kiriyama mentions that one of Ayame's followers tagged her dorm window last week. It is never a threat.

## 6. Obstacles

Use at most one per turn, in this order:

- **Turn 1:** an event crew sets up a live segment, and a camera boom sweeps the terrace.
- **Turn 2:** the waiter arrives with the order in the middle of the trade.
- **Turn 3:** an event crowd clogs the way to business-avenue; arcade-quarter and rooftop-gardens stay open.

## 7. Clue placements available

None; Arc 4 has no clue list.

Optional seed: an invoice to the outside combat-data buyer, glimpsed once at the tablet's edge (bible 5.2 seed). Never name the buyer and never follow it up.

## 8. Ladder steps it may reveal

- **The Archivist's name, step 2** (gate 4-3), when he is met in person. Step 1 must already be recorded at t483.
- **The Lumiere clip, step 1** (gate: the clip is played). Record it with `thread-reveal --gate-met` once Voyage's output shows the clip.
- **Not here:**
  - Replay's tape step 1: show the tell only; his name and power stay off screen until the gate edit in `note-arc4-tight-finish.md` is applied and he is revealed.
  - The dead-man upload: where the archive lives waits for Rin's rent find at 4-4.

## After the scene

Go to 4-4 Go Dark: the goal becomes "go dark first", and Hana's lens-free room pays off the safehouse thread.
