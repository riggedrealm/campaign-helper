"""day-turnover (WLD-2, WLD-3, PIV-6): the read-only list of what the world does on a new in-game day, and the `time` hint that points to it.
Every test runs on a tmp copy of a real campaign's data (VOYAGE_DATA); the real data dir is never written. No test asserts on the first line
of an output: every db.py output may gain a campaign-name header line, so each one searches the whole output or one section of it."""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL_DATA = REPO / "campaigns" / "classroom-2b" / "data"
HEADS = ("Clocks due", "Milestones on", "Threads going cold", "Front moves due", "Off-screen agendas")
SAYS = ("Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\nCrew: Tatsuya Ōmine offers tea; others react in character.\n"
        "World: The House Manager posts the chore rota.")

CHARTER = {  # arc A1, the arc the PC leaves: fronts The Lender (3 moves) and The Agent (2 moves), and hidden material that must never print
    "budget_turns": 10,
    "shared": {
        "title": "Who Holds the Keys", "tone": "Wry and warm", "promise": "Can you earn the house's trust before it must choose?",
        "premise": "A quiet squeeze on the house.", "pressure": "An inspection nobody can move.",
        "set_pieces": ["a tense house meeting", "a favor traded under time pressure"], "pc_tests": {"Aiko Tanaka": "social"},
        "subplot": "A favor owed outside the house.", "climax_kind": "A public inspection", "ending_shape": "Bittersweet",
        "stakes": "personal", "seeds": ["a scratched-out name"], "wins_on_offer": ["a staff ally"], "echoes": ["you covered a chore"],
        "backstory_hooks": ["the repair shop"], "deviations": []},
    "hidden": {
        "twist": {"text": "A housemate took the money.", "ladder": "Mio's secret", "keywords": ["glass lantern"]},
        "fronts": [{"name": "The Lender", "goal": "Get paid", "moves": ["A polite offer", "A second visit", "A written deadline"]},
                   {"name": "The Agent", "goal": "End the lease", "moves": ["A walkthrough", "A formal notice"]}],
        "antagonist": {"name": "Sōichi Tamaru", "face": "a polite broker", "first_contact": "an offer at the gate"},
        "clues": ["a thick envelope", "a neighbor's story", "a cash payment", "a card in a coat"],
        "surprises": ["the inspector knows Arimura"], "climax_options": ["a house vote"], "pc_test_situations": {"Aiko Tanaka": "two opposite promises"},
        "cast": ["Mio Tachibana"], "new_npcs": [], "notes": "keep it offscreen"}}

PIVOT = {  # the pivot arc A2 (PIV-5: no twist, one new NPC, one front with 2 moves, 3 clues, 12 turns)
    "budget_turns": 12,
    "shared": {
        "title": "The Menders' Debt", "tone": "Salt air and unpaid favors", "promise": "Can the net menders be repaid before the tide turns?",
        "premise": "The net menders ask Aiko to carry a message to the quay.", "pressure": "The tide table runs out in a week.",
        "set_pieces": ["a dockside haggle"], "pc_tests": {"Aiko Tanaka": "exploration"}, "climax_kind": "a standoff at the tide line",
        "ending_shape": "Open", "stakes": "personal", "wins_on_offer": ["the net menders as allies"], "backstory_hooks": ["the repair shop"]},
    "hidden": {
        "fronts": [{"name": "The Tide Broker", "goal": "Buy the menders' hut", "moves": ["A low offer", "A forged notice"]}],
        "antagonist": {"name": "Haru Ebisu", "face": "a tide broker", "first_contact": "an offer at the hut"},
        "clues": ["a salt-stained ledger", "a ferryman's rumor", "a missing tide table"],
        "new_npcs": ["Haru Ebisu, a tide broker"], "notes": "ties into no ladder"}}

OFFRAMPS = [
    {"thread": "went to the net menders instead of the guild clerk", "promise": "Can the net menders be repaid before the tide turns?",
     "front": "a broker who wants the menders' hut", "face": "Haru Ebisu, a tide broker", "first_move": "A net mender hands over a tide table at dusk"},
    {"thread": "kept returning to the rota drawer", "promise": "Who has been moving the chore rota?", "front": "the house manager's quiet audit",
     "face": "Teruko Kuroda, the rota keeper", "first_move": "The rota drawer is found emptied at breakfast"},
    {"thread": "haggled with the ferry family over the fare", "promise": "What does the ferry family owe the quay?", "front": "the ferry guild's fee",
     "face": "Old Noriko of the ferry", "first_move": "The ferry fare doubles overnight on the board"}]


class Env:
    def __init__(self, data, tmp, campaign="classroom-2b", root=None):
        self.data, self.tmp, self.campaign, self.root = data, tmp, campaign, root

    def run(self, *args):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": self.campaign, "PYTHONDONTWRITEBYTECODE": "1"})
        if self.root:
            e["VOYAGE_ROOT"] = str(self.root)
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def play(self, n, day, inputs="Aiko hangs about the kitchen"):
        """Log turn n on in-game day `day` (moving the clock to that day first when it is later than the current one)."""
        if day > self.load("state")["day"]:
            self.ok("time", "--day", day, "--turn", n, "--evidence", "days pass")
        self.ok("turn", n, "--inputs", inputs, "--summary", f"Turn {n}.", "--prompt", "Cut: Continue at the kitchen.\nWorld: Quiet.")

    def advance(self, to):
        for n in range(self.load("state")["turn"] + 1, to + 1):
            self.play(n, self.load("state")["day"])

    def op(self, name, *args, turn, ev="the story showed it"):
        return self.run(name, *args, "--turn", turn, "--evidence", ev)

    def draft(self, charter):
        self.ok("arc-plan", "--file", self.write("draft.json", json.dumps(charter)))

    def arc(self, ident):
        return next(a for a in self.load("arcs")["arcs"] if a["id"] == ident)

    def files(self):
        """Every entry of the data dir with its bytes and mtime: any write, new file or lock shows."""
        return {p.name: (p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns) for p in sorted(self.data.iterdir())}


def section(out, head):
    """The stripped lines under the heading that starts with `head`, up to the next line that starts at column 0."""
    lines, grab = [], False
    for ln in out.splitlines():
        if ln and not ln.startswith(" "):
            grab = ln.startswith(head)
        elif grab and ln.strip():
            lines.append(ln.strip())
    return lines


def heads(out):
    return [h for h in HEADS if any(ln.startswith(h) for ln in out.splitlines())]


def no_leak(env, out):
    """Nothing hidden shows: not a ladder step (revealed or not), not a thread summary, not the debt, not the hidden-score lines."""
    for t in env.load("threads").values():
        for text in [s["reveal"] for s in t["steps"]] + [t["summary"]]:
            assert text not in out, text
    debt = env.load("state")["debt"]
    for n in (debt["principal"], debt["due"]):
        assert str(n) not in out and f"{n:,}" not in out
    assert "Standing (" not in out and "Debt (hidden)" not in out


def copy_data(tmp_path, campaign="classroom-2b"):
    data = tmp_path / "data"
    shutil.copytree(REPO / "campaigns" / campaign / "data", data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    return data


@pytest.fixture
def env(tmp_path):
    return Env(copy_data(tmp_path), tmp_path)


@pytest.fixture
def pv(env):
    """Arc functions on, arc A1 active since turn 2 and the game at turn 2 (the live campaign's own draft arcs are set aside first)."""
    (env.data / "arcs.json").unlink(missing_ok=True)
    env.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test",
           "--background", "Grew up above a repair shop", "--power", "Mend")
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore")
    env.advance(2)
    env.draft(CHARTER)
    env.ok("arc-approve", "A1", "--lines-checked")
    assert env.op("arc-start", "A1", turn=2).returncode == 0
    return env


# ---- nothing to list --------------------------------------------------------------------------------------------------
def test_nothing_due_says_so_in_one_line(env):
    out = env.ok("day-turnover")
    assert [ln for ln in out.splitlines() if "nothing is due" in ln and "Day 1" in ln] and heads(out) == []
    assert sum("Day turnover" in ln for ln in out.splitlines()) == 1  # the one line


def test_day_option_defaults_to_the_current_day_and_rejects_less_than_one(env):
    env.play(1, 5)
    assert env.ok("day-turnover") == env.ok("day-turnover", "--day", 5)
    assert "Day 5 (" in env.ok("day-turnover") and "Day 9 (" in env.ok("day-turnover", "--day", 9)
    r = env.run("day-turnover", "--day", 0)
    assert r.returncode == 1 and "--day must be 1 or more" in r.stderr


# ---- clocks -----------------------------------------------------------------------------------------------------------
def test_clocks_due_on_or_before_the_day_and_still_open(env):
    for name, due in (("Rent notice", 4), ("Bake sale", 6), ("Inspection", 9)):
        env.ok("clock-add", name, "--due-day", due, "--note", f"{name} is the note", "--turn", 1, "--evidence", "said so")
    lines = section(env.ok("day-turnover", "--day", 6), "Clocks due")
    assert len(lines) == 2  # the clock due on Day 9 is not yet due
    assert lines[0].startswith("- Rent notice: due Day 4 (2 days overdue)") and "Rent notice is the note" in lines[0]  # most overdue first
    assert lines[1].startswith("- Bake sale: due Day 6 (today)")
    env.ok("clock-done", "Rent notice", "--turn", 1, "--evidence", "paid")
    lines = section(env.ok("day-turnover", "--day", 6), "Clocks due")
    assert len(lines) == 1 and "Bake sale" in lines[0]  # a closed clock is not open any more
    assert "Clocks due" not in env.ok("day-turnover", "--day", 3)
    assert "Inspection" in " ".join(section(env.ok("day-turnover", "--day", 10), "Clocks due"))


# ---- milestones -------------------------------------------------------------------------------------------------------
def test_milestones_on_the_day_names_and_places_only(env):
    lines = section(env.ok("day-turnover", "--day", 3), "Milestones on Day 3")
    assert lines == ["- Day 3: Orientation; classes start (Monday) (Chikara Academy)"]
    for day in (6, 7):  # a range holds each of its days
        assert section(env.ok("day-turnover", "--day", str(day)), f"Milestones on Day {day}") == [
            "- Day 6-7: Placement tournament (Chikara Battle Arena)"]
    assert "Milestones on" not in env.ok("day-turnover", "--day", 5)
    out = env.ok("day-turnover", "--day", 60)  # its calendar note holds the hidden debt: never printed
    assert section(out, "Milestones on Day 60") == ["- Day 60: Nightshade deadline (debt due)"]
    no_leak(env, out)
    assert "Debt stands" not in out


def test_a_campaign_without_milestone_data_has_no_milestone_section(env):
    st = env.load("state")
    st["calendar"] = []
    env.save_json("state", st)
    assert "Milestones on" not in env.ok("day-turnover", "--day", 3)
    del st["calendar"]
    env.save_json("state", st)
    assert "Milestones on" not in env.ok("day-turnover", "--day", 3)


# ---- threads going cold -----------------------------------------------------------------------------------------------
def test_active_quests_go_cold_after_seven_days_dated_by_log_and_by_turns_that_name_them(env):
    env.play(1, 1)
    env.ok("quest-start", "Move-In Weekend", "--turn", 1, "--evidence", "the House Manager hands over keys")  # log turn 1: Day 1
    env.ok("quest-start", "Ability and Pulse Tutorial", "--turn", 1, "--evidence", "Pulse sign-up is mentioned")
    env.play(2, 5, "Aiko keeps going on the Move-In Weekend chores")  # names the first quest on Day 5
    assert "Threads going cold" not in env.ok("day-turnover", "--day", 7)  # 6 days: not yet
    lines = section(env.ok("day-turnover", "--day", 8), "Threads going cold")
    assert lines == ['- quest "Ability and Pulse Tutorial": last story contact Day 1 (7 days ago)']  # Move-In Weekend was named on Day 5
    lines = section(env.ok("day-turnover", "--day", 12), "Threads going cold")
    assert lines == ['- quest "Ability and Pulse Tutorial": last story contact Day 1 (11 days ago)',
                     '- quest "Move-In Weekend": last story contact Day 5 (7 days ago)']  # the coldest first
    assert "Threads going cold" not in env.ok("day-turnover", "--day", 1)  # a contact after the day checked is ignored: nothing is cold
    env.ok("quest-end", "Move-In Weekend", "completed", "--turn", 2, "--evidence", "done")
    assert "Move-In Weekend" not in env.ok("day-turnover", "--day", 12)  # no longer active


def test_a_quest_log_entry_counts_as_contact(env):
    env.play(1, 1)
    env.ok("quest-start", "Move-In Weekend", "--turn", 1, "--evidence", "keys")
    env.play(2, 4)
    env.ok("quest-end", "Move-In Weekend", "--inferred", "--turn", 2, "--evidence", "the weekend seems over")  # an apparent end: log turn 2, Day 4
    assert section(env.ok("day-turnover", "--day", 11), "Threads going cold") == [
        '- quest "Move-In Weekend": last story contact Day 4 (7 days ago)']


def test_a_ladder_goes_cold_by_its_latest_revealed_step_and_prints_no_step(env):
    env.play(1, 1)
    env.ok("thread-reveal", "Mio's secret", 1, "--turn", 1, "--evidence", "Mio hides a money worry")
    assert "Threads going cold" not in env.ok("day-turnover", "--day", 7)
    out = env.ok("day-turnover", "--day", 8)
    lines = section(out, "Threads going cold")
    assert len(lines) == 1 and lines[0].startswith('- ladder "Mio\'s secret": last step revealed Day 1 (7 days ago)')
    assert "ladder \"Sunny" not in out  # a ladder with no revealed step has no contact to date
    no_leak(env, out)  # no step text, not even the revealed one, and no thread summary
    th = env.load("threads")
    for step in th["Mio's secret"]["steps"]:
        step["status"], step["revealed_day"] = "revealed", 1
    env.save_json("threads", th)
    assert "ladder \"Mio" not in env.ok("day-turnover", "--day", 30)  # a finished ladder has nothing left to move


def test_contacts_without_a_day_are_counted_not_guessed(env):
    env.play(1, 1)
    env.ok("quest-start", "Move-In Weekend", "--turn", 1, "--evidence", "keys")
    assert section(env.ok("day-turnover", "--day", 9), "Threads going cold")  # dated: cold
    turns = env.load("turns")
    turns[0]["day"] = "?"  # a turn imported without a day
    env.save_json("turns", turns)
    out = env.ok("day-turnover", "--day", 9)
    assert "Threads going cold" not in out  # not called cold on a guess
    note = [ln for ln in out.splitlines() if "Not checked, no turn day on record" in ln]
    assert len(note) == 1 and "1 active quest(s)" in note[0] and "main NPC(s) with an agenda" in note[0]
    assert "not on screen yet" not in out  # nor are the main NPCs called off screen on a guess


# ---- front moves of the live and the parked arcs ----------------------------------------------------------------------
def test_front_moves_due_for_the_live_arc_and_every_parked_arc_and_nothing_hidden(pv):
    pv.ok("arc-offramps", "A1", "--file", pv.write("offramps.json", json.dumps(OFFRAMPS)))
    assert pv.op("arc-move", "A1", "Lender", 1, turn=3).returncode == 0  # move 1 of The Lender is done
    out = pv.ok("day-turnover", "--day", 2)
    assert section(out, "Front moves due") == [
        'A1 [active] "Who Holds the Keys":', "- The Lender, move 2 of 3: A second visit", "- The Agent, move 1 of 2: A walkthrough"]
    pv.advance(6)
    pv.draft(PIVOT)
    assert pv.op("arc-adopt", "A2", turn=6, ev="the PC went to the net menders").returncode == 0
    assert [a["status"] for a in pv.load("arcs")["arcs"]] == ["parked", "provisional"]
    out = pv.ok("day-turnover")
    lines = section(out, "Front moves due")
    assert lines == ['A2 [provisional] "The Menders\' Debt":', "- The Tide Broker, move 1 of 2: A low offer",
                     'A1 [parked] "Who Holds the Keys":', "- The Lender, move 2 of 3: A second visit", "- The Agent, move 1 of 2: A walkthrough"]
    assert "A polite offer" not in out  # done before the arc was parked
    # nothing hidden leaks: not the twist, the antagonist, the clues, the off-ramps, a ladder step or a score
    for secret in ("A housemate took the money", "glass lantern", "Sōichi Tamaru", "a polite broker", "a thick envelope", "a cash payment",
                   "Haru Ebisu", "a salt-stained ledger", "went to the net menders instead of the guild clerk", "Teruko Kuroda",
                   "keep it offscreen", "ties into no ladder"):
        assert secret not in out, secret
    no_leak(pv, out)


def test_a_front_with_every_move_done_and_a_closed_or_draft_arc_are_not_listed(pv):
    for n in (1, 2, 3):
        assert pv.op("arc-move", "A1", "Lender", n, turn=3).returncode == 0
    lines = section(pv.ok("day-turnover"), "Front moves due")
    assert lines == ['A1 [active] "Who Holds the Keys":', "- The Agent, move 1 of 2: A walkthrough"]
    other = copy.deepcopy(CHARTER)
    other["hidden"]["fronts"] = [{"name": "The Ghost Front", "goal": "Haunt", "moves": ["A cold draft"]}]
    other["shared"]["title"] = "A Draft Not Yet Approved"
    pv.draft(other)
    assert pv.arc("A2")["status"] == "draft"
    out = pv.ok("day-turnover")
    assert "Ghost" not in out and "A cold draft" not in out  # a draft arc does not move
    assert pv.op("arc-close", "A1", "--status", "set_aside", "--notes", "left it", turn=2).returncode == 0
    assert "Front moves due" not in pv.ok("day-turnover")  # a closed arc does not move


def test_a_parked_arc_that_comes_back_moves_as_the_live_arc_again(pv):
    pv.advance(6)
    pv.draft(PIVOT)
    assert pv.op("arc-adopt", "A2", turn=6, ev="the PC went to the net menders").returncode == 0
    r = pv.run("arc-unpark", "A1", "--notes", "back to the guild", "--turn", "6", "--evidence", "the PC went back")
    assert r.returncode == 0, r.stderr + r.stdout
    lines = section(pv.ok("day-turnover"), "Front moves due")
    assert lines[0] == 'A1 [active] "Who Holds the Keys":' and not any("A2" in ln or "Tide Broker" in ln for ln in lines)  # A2 closed as set_aside


# ---- off-screen agendas -----------------------------------------------------------------------------------------------
def test_off_screen_main_npcs_with_an_agenda_step(env):
    cast = env.load("cast")
    cast["Yūto Fujisawa"]["status"] = "planned"  # not in the story yet: not listed
    cast["Shin Asakura"]["agenda"] = {"want": "Watch the step.", "next_move": ""}  # no next move: nothing to list
    cast["Reiko Shimazu"]["first_seen_turn"] = 1  # on screen when first seen: Day 1, even though no turn text names her
    env.save_json("cast", cast)
    env.play(1, 1, "Tatsuya makes tea and Mio Tachibana hides upstairs")
    env.play(2, 5, "Mio helps with the dishes")
    out = env.ok("day-turnover", "--day", 8)
    lines = section(out, "Off-screen agendas")
    by = {ln.split(" (")[0].lstrip("- "): ln for ln in lines}
    assert "last on screen Day 5, 3 days ago): Come down for food only when the house is quiet." in by["Mio Tachibana"]  # the window is 3 days
    assert "last on screen Day 1, 7 days ago)" in by["Tatsuya Ōmine"] and "last on screen Day 1, 7 days ago)" in by["Reiko Shimazu"]
    assert "not on screen yet): Appears at a distance" in by["Ayame Kujō"] and "not on screen yet" in by["Kenji Arimura"]
    assert "Yūto Fujisawa" not in by and "Shin Asakura" not in by
    assert [ln.split(" (")[0].lstrip("- ") for ln in lines] == [  # the longest off screen first, then by name; Mio, off for 3 days, last
        "Ayame Kujō", "Kenji Arimura", "Park Seo-yeon", "Reiko Shimazu", "Tatsuya Ōmine", "Mio Tachibana"]
    day7 = " ".join(section(env.ok("day-turnover", "--day", 7), "Off-screen agendas"))
    assert "Mio Tachibana" not in day7  # off for 2 days only: inside the window
    assert "Tatsuya Ōmine (last on screen Day 1, 6 days ago)" in day7
    # the agenda's next move only: not the want, not the NPC's hidden fields
    for text in ("payment notice", "Nightshade", "stabilizer", "Daiki", "Nine Corners", "Annex Cohort", "scar"):
        assert text not in out, text
    no_leak(env, out)


def test_off_screen_agendas_are_capped_and_the_rest_counted(tmp_path):
    root = tmp_path / "root"
    cdir = root / "campaigns" / "demo"
    shutil.copytree(REAL_DATA, cdir / "data", ignore=shutil.ignore_patterns(".lock", ".snap*"))
    cfg = json.loads((REAL_DATA.parent / "campaign.json").read_text(encoding="utf-8"))
    cast = json.loads((cdir / "data" / "cast.json").read_text(encoding="utf-8"))
    cfg["name"] = "demo"
    for i in range(4):
        name = f"Zed Extra{i}"
        cast[name] = {"name": name, "gender": "f", "status": "world", "kind": "main", "agenda": {"want": "w", "next_move": f"Does errand {i}."}}
        cfg["main_npcs"].append(name)
    (cdir / "campaign.json").write_text(json.dumps(cfg), encoding="utf-8")
    (cdir / "data" / "cast.json").write_text(json.dumps(cast, ensure_ascii=False), encoding="utf-8")
    e = Env(cdir / "data", tmp_path, campaign="demo", root=root)
    lines = section(e.ok("day-turnover", "--day", 10), "Off-screen agendas")
    assert len(lines) == 9 and lines[-1] == "- (+4 more main NPCs off screen)"
    assert not any("Zed Extra" in ln for ln in lines[:8])  # sorted by name: the four extras come last, so they are the ones cut


# ---- it writes nothing ------------------------------------------------------------------------------------------------
def test_day_turnover_writes_nothing(pv):
    pv.ok("quest-start", "Move-In Weekend", "--turn", 2, "--evidence", "keys")
    pv.ok("clock-add", "Rent notice", "--due-day", 3, "--turn", 2, "--evidence", "said so")
    pv.ok("thread-reveal", "Mio's secret", 1, "--turn", 2, "--evidence", "money worry")
    pv.advance(4)
    pv.ok("time", "--day", 20, "--turn", 5, "--evidence", "weeks pass")
    before = pv.files()
    for args in ((), ("--day", 1), ("--day", 9), ("--day", 20), ("--day", 60), ("--day", 500), ("--day", 0), ("--help",)):
        pv.run("day-turnover", *args)
    out = pv.ok("day-turnover")
    assert heads(pv.ok("day-turnover", "--day", 34)) == list(HEADS)  # Day 34 has a milestone: this one exercises every section
    assert pv.files() == before  # every file byte for byte and mtime for mtime, and no new file (no lock, no snapshot, no tmp)


@pytest.mark.parametrize("campaign", ["classroom-2b", "joestar", "luxcellia"])
def test_runs_on_every_real_campaign_and_writes_nothing(tmp_path, campaign):
    e = Env(copy_data(tmp_path, campaign), tmp_path, campaign=campaign)
    before = e.files()
    day = e.load("state")["day"]
    for args in ((), ("--day", day + 9), ("--day", 1)):
        out = e.ok("day-turnover", *args)
        assert "Day turnover, Day " in out
    assert e.files() == before


# ---- the time hint ----------------------------------------------------------------------------------------------------
def test_time_hints_day_turnover_only_when_the_day_changes(env):
    out = env.ok("time", "--day", 3, "--turn", 1, "--evidence", "Monday comes")
    hint = [ln for ln in out.splitlines() if "day-turnover" in ln]
    assert len(hint) == 1 and "Day 1 -> Day 3" in hint[0] and "db.py day-turnover" in hint[0]
    for args in (("--block", "Evening"), ("--clock", "21:30"), ("--day", 3, "--block", "Late Night"), ("--day", 3)):  # same day
        assert "day-turnover" not in env.ok("time", *args, "--turn", 1, "--evidence", "later that day"), args
    assert "day-turnover" not in env.ok("time", "--day", 2, "--allow-backward", "--turn", 1, "--evidence", "fix a slip")  # backward: no
    out = env.ok("time", "--day", 3, "--turn", 1, "--evidence", "Monday again")  # forward again, from the corrected Day 2
    assert "Day 2 -> Day 3" in out and "day-turnover" in out


def test_the_hint_shows_when_a_payload_changes_the_day(env):
    def payload(turn, day=None):
        ops = [{"op": "time", "args": {"day": day}, "evidence": "the next day"}] if day else []
        return env.write(f"p{turn}.json", json.dumps({"turn": turn, "ops": ops, "turn_log": {"inputs": "i", "summary": f"s{turn}", "prompt": "Cut: a\nWorld: b"}}))
    out = env.ok("record", payload(1, 2))
    assert [ln for ln in out.splitlines() if "day-turnover" in ln]
    assert not [ln for ln in env.ok("record", payload(2)).splitlines() if "day-turnover" in ln]  # no time op: no hint
    out = env.ok("record", payload(3, 3), "--dry-run")
    assert "day-turnover" not in out  # a dry run only lists the plan
    r = env.run("commit-turn", "--prompt", env.write("prompt.txt", SAYS), "--payload", payload(3, 4))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [ln for ln in r.stdout.splitlines() if "Day changed" in ln and "day-turnover" in ln]
    r = env.run("commit-turn", "--prompt", env.write("prompt.txt", SAYS), "--payload", payload(4))
    assert r.returncode == 0 and "day-turnover" not in r.stdout
