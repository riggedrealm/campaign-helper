"""The pivot: provisional and parked arcs, off-ramps, arc-pivot, arc-adopt, arc-unpark, and the planner page rules for them.
Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA); the real data dir is never written. No test asserts on the
first line of an output: every db.py output may gain a campaign-name header line, so each one searches the whole output."""
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
SAYS = "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\nCrew: Mio Tachibana counts coins twice, shoulders tight.\nWorld: The House Manager posts the chore rota."

CHARTER = {  # arc A1, the arc the PC leaves
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

PIVOT_PROMISE = "Can the net menders be repaid before the tide turns?"
PIVOT = {  # a mini-charter that respects PIV-5: no twist, one new NPC, one front with 2 moves, 3 clues, 12 turns
    "budget_turns": 12,
    "shared": {
        "title": "The Menders' Debt", "tone": "Salt air and unpaid favors", "promise": PIVOT_PROMISE,
        "premise": "The net menders ask Aiko to carry a message to the quay.", "pressure": "The tide table runs out in a week.",
        "set_pieces": ["a dockside haggle"], "pc_tests": {"Aiko Tanaka": "exploration"}, "climax_kind": "a standoff at the tide line",
        "ending_shape": "Open", "stakes": "personal", "wins_on_offer": ["the net menders as allies"], "backstory_hooks": ["the repair shop"]},
    "hidden": {
        "fronts": [{"name": "The Tide Broker", "goal": "Buy the menders' hut", "moves": ["A low offer", "A forged notice"]}],
        "antagonist": {"name": "Haru Ebisu", "face": "a tide broker", "first_contact": "an offer at the hut"},
        "clues": ["a salt-stained ledger", "a ferryman's rumor", "a missing tide table"],
        "new_npcs": ["Haru Ebisu, a tide broker"], "notes": "ties into no ladder"}}

OFFRAMPS = [
    {"thread": "went to the net menders instead of the guild clerk", "promise": PIVOT_PROMISE, "front": "a broker who wants the menders' hut",
     "face": "Haru Ebisu, a tide broker", "first_move": "A net mender hands over a tide table at dusk"},
    {"thread": "kept returning to the rota drawer", "promise": "Who has been moving the chore rota?", "front": "the house manager's quiet audit",
     "face": "Teruko Kuroda, the rota keeper", "first_move": "The rota drawer is found emptied at breakfast"},
    {"thread": "haggled with the ferry family over the fare", "promise": "What does the ferry family owe the quay?", "front": "the ferry guild's fee",
     "face": "Old Noriko of the ferry", "first_move": "The ferry fare doubles overnight on the board"}]


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, cwd=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": "classroom-2b", "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=cwd or self.tmp)

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

    def write_json(self, name, obj):
        return self.write(name, json.dumps(obj))

    def turn(self, n, flag=False):
        self.ok("turn", n, "--inputs", "Aiko chats with the housemates in the kitchen", "--summary", f"Turn {n}.",
                "--prompt", "Cut: Continue at the kitchen.\nWorld: Quiet.", *(["--arc-contact"] if flag else []))

    def advance(self, to):
        for n in range(self.load("state")["turn"] + 1, to + 1):
            self.turn(n)

    def op(self, name, *args, turn, ev="the story showed it"):
        return self.run(name, *args, "--turn", turn, "--evidence", ev)

    def arcs(self):
        return self.load("arcs")["arcs"]

    def arc(self, ident):
        return next(a for a in self.arcs() if a["id"] == ident)

    def live(self):
        return [a["id"] for a in self.arcs() if a["status"] in ("active", "provisional")]

    def draft(self, charter, mutate=None):
        c = copy.deepcopy(charter)
        if mutate:
            mutate(c)
        self.ok("arc-plan", "--file", self.write_json("draft.json", c))

    def offramps(self, ident="A1", sketches=None):
        self.ok("arc-offramps", ident, "--file", self.write_json("offramps.json", OFFRAMPS if sketches is None else sketches))


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)  # start without the optional file (the live campaign has one)
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test",
              "--background", "Grew up above a repair shop", "--power", "Mend")
    assert r.returncode == 0, r.stderr
    return e


@pytest.fixture
def pv(env):
    """Arc functions on (session zero with a line and a veil), arc A1 active since turn 2, the game at turn 2."""
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore")
    env.advance(2)
    env.draft(CHARTER)
    env.ok("arc-approve", "A1", "--lines-checked")
    assert env.op("arc-start", "A1", turn=2).returncode == 0
    return env


def pivoted(pv, at=6):
    """A1 left behind for the pivot arc A2, adopted at turn `at`: A1 parked, A2 provisional."""
    pv.advance(at)
    pv.draft(PIVOT)
    assert pv.op("arc-adopt", "A2", turn=at, ev="the PC went to the net menders").returncode == 0
    return pv


def prep_lines(env):
    out = env.ok("prep")
    return out[out.index("LIVE CHECKLIST"):]


def fired(out):
    """arc-pivot's output reports a detected pivot (a line that starts 'pivot detected'), wherever in the output that line is."""
    return any(ln.startswith("pivot detected") for ln in out.splitlines())


# ---- statuses and their validation (verify_data) ---------------------------------------------------------------------
def test_new_statuses_are_valid_and_old_files_stay_valid(pv):
    assert pv.run("wrap-up").returncode == 0  # an old-style file (no new status, no off-ramps) verifies
    a = pv.load("arcs")
    a["arcs"].append({"id": "A9", "status": "provisional", "start_turn": 2, "adopted_turn": 2, "hidden": {}, "shared": {}})
    a["arcs"][0]["status"] = "parked"
    a["arcs"][0]["parked_turn"] = 2
    pv.save_json("arcs", a)
    assert pv.run("wrap-up").returncode == 0  # parked + provisional: valid, one live arc
    a["arcs"][1]["hidden"] = {"offramps": OFFRAMPS}
    pv.save_json("arcs", a)
    assert pv.run("wrap-up").returncode == 0  # a valid off-ramps field is accepted


def test_status_validation_rules(pv):
    a = pv.load("arcs")
    good = copy.deepcopy(a)
    # a provisional arc needs start_turn and adopted_turn
    a["arcs"].append({"id": "A2", "status": "provisional", "hidden": {}, "shared": {}})
    a["arcs"][0]["status"] = "parked"
    a["arcs"][0]["parked_turn"] = 2
    pv.save_json("arcs", a)
    r = pv.run("wrap-up")
    assert r.returncode == 1 and "provisional arc A2 needs an integer start_turn" in r.stderr and "needs an integer adopted_turn" in r.stderr
    # a parked arc needs parked_turn
    b = copy.deepcopy(good)
    b["arcs"][0]["status"] = "parked"
    pv.save_json("arcs", b)
    assert "parked arc A1 needs an integer parked_turn" in pv.run("wrap-up").stderr
    # one live arc at a time: active + provisional is two
    c = copy.deepcopy(good)
    c["arcs"].append({"id": "A2", "status": "provisional", "start_turn": 2, "adopted_turn": 2, "hidden": {}, "shared": {}})
    pv.save_json("arcs", c)
    assert "more than one live (active or provisional) arc (A1, A2)" in pv.run("wrap-up").stderr
    # two provisional arcs are two live arcs; two parked arcs are fine
    c["arcs"][0].update(status="provisional", start_turn=1, adopted_turn=1)
    pv.save_json("arcs", c)
    assert "more than one live" in pv.run("wrap-up").stderr
    d = copy.deepcopy(good)
    d["arcs"][0].update(status="parked", parked_turn=2)
    d["arcs"].append({"id": "A2", "status": "parked", "parked_turn": 2, "hidden": {}, "shared": {}})
    pv.save_json("arcs", d)
    assert pv.run("wrap-up").returncode == 0
    # a malformed off-ramps field
    e = copy.deepcopy(good)
    e["arcs"][0]["hidden"]["offramps"] = [{"thread": "x", "promise": "", "front": "f", "face": "g", "extra": "h"}]
    pv.save_json("arcs", e)
    err = pv.run("wrap-up").stderr
    assert "arc A1 hidden.offramps" in err and "lacks first_move" in err and "unknown key(s) extra" in err and "promise must be a non-empty string" in err


# ---- off-ramps ---------------------------------------------------------------------------------------------------------
def test_offramps_are_stored_replaced_validated_and_planned_with_defaults(pv):
    pv.advance(4)
    pv.offramps()
    assert pv.arc("A1")["hidden"]["offramps"] == OFFRAMPS
    log = pv.load("state")["changelog"][-1]
    assert log["cmd"] == "arc-offramps" and log["turn"] == 4 and log["evidence"] == "planning session with the user"  # planning defaults
    assert "3 off-ramp sketch(es) stored" in log["summary"] and "Haru" not in log["summary"]  # the log never holds their text
    pv.ok("arc-offramps", "A1", "--file", pv.write_json("two.json", OFFRAMPS[:2]), "--turn", 3, "--evidence", "midpoint review")
    assert pv.arc("A1")["hidden"]["offramps"] == OFFRAMPS[:2]  # replaced, not merged
    assert "replacing 3" in pv.load("state")["changelog"][-1]["summary"] and pv.load("state")["changelog"][-1]["evidence"] == "midpoint review"
    messy = [{**OFFRAMPS[0], "thread": "  padded thread  "}]
    pv.offramps(sketches=messy)
    assert pv.arc("A1")["hidden"]["offramps"][0]["thread"] == "padded thread"
    pv.offramps(sketches=[])
    assert pv.arc("A1")["hidden"]["offramps"] == []  # an empty list clears
    # the whole replacement is refused for any bad shape, all problems at once, and nothing is written
    pv.offramps()
    before = (pv.data / "arcs.json").read_bytes()
    bad_ones = [
        ({"thread": "x"}, "must be a list"),
        (["a string"], "sketch 1 must be an object"),
        ([{k: v for k, v in OFFRAMPS[0].items() if k != "face"}], "sketch 1 lacks face"),
        ([{**OFFRAMPS[0], "mood": "x"}], "unknown key(s) mood"),
        ([{**OFFRAMPS[0], "front": "  "}], "front must be a non-empty string"),
        ([{**OFFRAMPS[0], "promise": 7}], "promise must be a non-empty string"),
        ([OFFRAMPS[0], {**OFFRAMPS[1], "face": ""}], "sketch 2: face must be a non-empty string"),
    ]
    for payload, needle in bad_ones:
        r = pv.run("arc-offramps", "A1", "--file", pv.write_json("bad.json", payload))
        assert r.returncode == 2 and needle in r.stderr, (needle, r.stderr)
    two = pv.run("arc-offramps", "A1", "--file", pv.write_json("bad.json", [{"thread": "t"}, {"promise": "p"}]))
    assert two.returncode == 2 and "sketch 1 lacks promise" in two.stderr and "sketch 2 lacks thread" in two.stderr
    assert pv.run("arc-offramps", "A1", "--file", pv.tmp / "nope.json").returncode == 1
    assert pv.run("arc-offramps", "A7", "--file", pv.write_json("o.json", OFFRAMPS)).returncode == 2  # no such arc
    assert (pv.data / "arcs.json").read_bytes() == before
    # arc-plan accepts and checks hidden.offramps too
    pv.ok("arc-plan", "--id", "A1", "--file", pv.write_json("u.json", {"hidden": {"offramps": OFFRAMPS[:1]}}))
    assert pv.arc("A1")["hidden"]["offramps"] == OFFRAMPS[:1]
    assert pv.run("arc-plan", "--id", "A1", "--file", pv.write_json("u.json", {"hidden": {"offramps": [{"thread": "t"}]}})).returncode == 2
    # a finished arc takes no off-ramps
    assert pv.op("arc-close", "A1", "--best", "x", turn=4).returncode == 0
    assert pv.run("arc-offramps", "A1", "--file", pv.write_json("o.json", OFFRAMPS)).returncode == 4


def test_offramps_are_never_printed_unless_asked(pv):
    pv.offramps()
    texts = [v for sk in OFFRAMPS for v in sk.values()]
    for args in (("arc",), ("arc", "A1"), ("arc", "--list"), ("arc", "A1", "--shared"), ("plan-brief",), ("resume",), ("prep",), ("state",)):
        out = pv.ok(*args)
        assert not [t for t in texts if t in out], args
    asked = pv.ok("arc", "A1", "--offramps")
    assert "off-ramps (director only" in asked and all(t in asked for t in texts)
    assert pv.run("arc", "A1", "--shared", "--offramps").returncode == 2  # --shared never shows hidden fields
    pv.offramps(sketches=[])
    assert "off-ramps (director only; never in a prompt, never to the user): none stored" in pv.ok("arc", "A1", "--offramps")
    # a planning command only: not a payload op
    r = pv.run("record", pv.write_json("p.json", {"turn": 3, "ops": [{"op": "arc-offramps", "args": {"id": "A1"}, "evidence": "x"}],
                                                  "turn_log": {"inputs": "i", "summary": "s", "prompt": "p"}}), "--dry-run")
    assert r.returncode == 2 and "unknown op 'arc-offramps'" in r.stderr


# ---- arc-pivot -------------------------------------------------------------------------------------------------------------
def test_arc_pivot_by_thread_prints_the_best_matching_offramp(pv):
    pv.offramps()
    out = pv.ok("arc-pivot", "--thread", "Aiko throws in with the net menders")
    assert "arc functions: on" in out and fired(out) and "Aiko throws in with the net menders" in out
    assert "off-ramp 1 of 3" in out and "A net mender hands over a tide table at dusk" in out and "Haru Ebisu, a tide broker" in out
    assert "rota drawer" not in out and "ferry" not in out  # only the matching sketch
    out = pv.ok("arc-pivot", "--thread", "Aiko will haggle with the ferry family")
    assert "off-ramp 3 of 3" in out and "Old Noriko of the ferry" in out and "net mender" not in out.split("off-ramp 3 of 3")[1]
    out = pv.ok("arc-pivot", "--thread", "Aiko takes up the zebra trade")  # nothing matches: draft from scratch, no off-ramp shown
    assert "no stored off-ramp matches this thread" in out and "3 stored" in out
    assert not [v for sk in OFFRAMPS for v in sk.values() if v in out]
    pv.offramps(sketches=[])
    assert "no stored off-ramp matches this thread" in pv.ok("arc-pivot", "--thread", "Aiko joins the net menders")
    assert pv.run("arc-pivot", "--thread", "  ").returncode == 2
    before = (pv.data / "arcs.json").read_bytes()
    pv.ok("arc-pivot", "--thread", "x y z")
    assert (pv.data / "arcs.json").read_bytes() == before  # read-only


def test_arc_pivot_is_silent_when_no_pivot_fires(pv):
    pv.offramps()
    texts = [v for sk in OFFRAMPS for v in sk.values()]
    pv.advance(8)  # turns 3 to 8, none with arc contact, but no pc-thread note yet
    out = pv.ok("arc-pivot")
    assert "arc functions: on" in out and "no pivot detected" in out and "no pc-thread note in or just before turns 6 to 8" in out
    assert not fired(out) and not [t for t in texts if t in out]
    # a note that is too old does not count: the window is turns 6 to 8, so only a note from turn 5 on does
    pv.op("pc-thread", "went to the net menders instead of the guild clerk", turn=3)
    assert not fired(pv.ok("arc-pivot"))
    pv.op("pc-thread", "keeps asking the net menders about the tide table", turn=5)
    assert fired(pv.ok("arc-pivot"))
    # arc contact in the window: flagged turn, a clue found, the antagonist met
    pv.turn(9, flag=True)
    out = pv.ok("arc-pivot")
    assert "no pivot detected (arc contact at turn 9" in out and not fired(out) and not [t for t in texts if t in out]
    pv.advance(12)  # window 10 to 12; the note from turn 5 is long past
    assert not fired(pv.ok("arc-pivot"))
    pv.op("pc-thread", "keeps asking the net menders about the tide table", turn=11)
    assert fired(pv.ok("arc-pivot")) and "off-ramp 1 of 3" in pv.ok("arc-pivot")
    assert pv.op("arc-clue", "A1", 1, turn=12).returncode == 0
    out = pv.ok("arc-pivot")  # a found clue is contact
    assert "no pivot detected (arc contact at turn 12" in out and not fired(out) and not [t for t in texts if t in out]
    # a front move is the world's, not the PC's contact
    pv.advance(15)
    pv.op("pc-thread", "keeps asking the net menders about the tide table", turn=14)
    assert pv.op("arc-move", "A1", "Lender", 1, turn=15).returncode == 0
    assert fired(pv.ok("arc-pivot"))


def test_arc_pivot_needs_a_live_arc_logged_turns_and_arc_functions(env):
    out = env.ok("arc-pivot")  # no arcs file at all
    assert "arc functions: off" in out and "no pivot detected" in out and not fired(out)
    out = env.ok("arc-pivot", "--thread", "Aiko joins the net menders")  # even a plain commitment: nothing to leave
    assert "no pivot detected (arc functions are off" in out and not fired(out)
    env.ok("session-zero", "--tone", "warm")
    env.advance(2)
    env.draft(CHARTER)  # a session zero and a charter: arc functions on, but no live arc
    out = env.ok("arc-pivot", "--thread", "Aiko joins the net menders")
    assert "arc functions: on" in out and "no pivot detected (no live arc to leave)" in out
    env.ok("arc-approve", "A1", "--force")
    env.op("arc-start", "A1", turn=2)
    assert "no pivot detected (fewer than 3 turns logged)" in env.ok("arc-pivot")
    env.advance(4)  # window 2 to 4 starts at the arc's own start turn: the arc has not been left yet
    env.op("pc-thread", "went to the net menders", turn=3)
    assert "not all after the arc started (turn 2)" in env.ok("arc-pivot")


# ---- arc-adopt ---------------------------------------------------------------------------------------------------------
def test_adopt_makes_the_draft_provisional_and_parks_the_live_arc(pv):
    pivoted(pv, at=6)
    a1, a2 = pv.arc("A1"), pv.arc("A2")
    assert a2["status"] == "provisional" and a2["start_turn"] == 6 and a2["adopted_turn"] == 6
    assert a1["status"] == "parked" and a1["parked_turn"] == 6 and a1["parked_for"] == "A2" and a1["start_turn"] == 2
    assert pv.live() == ["A2"]
    log = pv.load("state")["changelog"][-1]
    assert log["cmd"] == "arc-adopt" and log["turn"] == 6 and log["evidence"] == "the PC went to the net menders"
    assert "arc A1 parked" in log["summary"]
    assert pv.run("wrap-up").returncode == 0
    # reads show both
    lst = pv.ok("arc", "--list")
    assert "A1 [parked]" in lst and "parked since turn 6" in lst and "A2 [provisional]" in lst
    assert "[provisional]" in pv.ok("arc") and "pivot arc: off the planner page until approved" in pv.ok("arc")  # the live arc is the default
    assert "[parked]" in pv.ok("arc", "A1") and "parked turn 6 (taken over by A2)" in pv.ok("arc", "A1")
    res = pv.ok("resume")
    assert 'arc A2 "The Menders\' Debt" provisional t0/12 (0%)' in res and 'parked arc A1 "Who Holds the Keys"' in res
    pf = pv.run("preflight").stdout
    assert "arc A2 is provisional, a pivot arc" in pf and "arc A1 is parked since turn 6" in pf
    # only a draft is adopted; adopting needs the turn and the evidence
    assert pv.op("arc-adopt", "A2", turn=6).returncode == 4
    assert pv.run("arc-adopt", "A2").returncode == 2


def test_the_turn_ops_accept_a_provisional_arc_and_refuse_a_parked_one(pv):
    pivoted(pv, at=6)
    pv.advance(8)
    assert pv.op("arc-move", "A2", "Tide", 1, turn=7).returncode == 0
    assert pv.arc("A2")["hidden"]["fronts"][0]["moves"][0]["done_turn"] == 7
    assert pv.op("arc-clue", "A2", 2, turn=7).returncode == 0 and pv.arc("A2")["hidden"]["clues"][1]["found_turn"] == 7
    assert pv.op("arc-contact", "A2", turn=8).returncode == 0 and pv.arc("A2")["hidden"]["antagonist"]["contact_turn"] == 8
    assert pv.op("arc-reveal", "A2", turn=8).returncode == 0 and pv.arc("A2")["hidden"]["twist"]["revealed_turn"] == 8
    assert pv.op("arc-review", "A2", "--kind", "scene", "--notes", "going well", turn=8).returncode == 0
    assert pv.arc("A2")["reviews"] == [{"turn": 8, "kind": "scene", "notes": "going well"}]
    assert pv.op("arc-deviation", "A2", "the broker came early", turn=8).returncode == 0
    for name, args in (("arc-move", ("Lender", 1)), ("arc-clue", (1,)), ("arc-contact", ()), ("arc-reveal", ()), ("arc-review", ("--kind", "scene", "--notes", "x"))):
        r = pv.op(name, "A1", *args, turn=8)  # A1 is parked: not live
        assert r.returncode == 4 and "A1 is parked" in r.stderr, (name, r.stderr)
    assert pv.op("arc-start", "A1", turn=8).returncode == 4  # a parked arc comes back with arc-unpark, not arc-start


def test_prep_arc_lines_treat_a_provisional_arc_as_live(pv):
    pivoted(pv, at=6)
    out = prep_lines(pv)
    assert 'arc A2 "Can the net menders be repaid before the tide turns?" t0/12 (0%) provisional (pivot arc: approve, re-aim or go back)' in out
    assert 'arc A1 "The Menders' not in out and 'arc A1 "Who Holds the Keys" parked since turn 6' in out
    assert "no arc live" not in out and "arc-start" not in out
    pv.advance(12)  # 6 of 12 used: 50%
    assert "antagonist not on screen yet: contact due by the midpoint" in prep_lines(pv)
    pv.advance(14)  # 8 of 12 used: past 60%, and 8 turns with no arc contact
    out = prep_lines(pv)
    assert "midpoint review due (arc-review --kind midpoint)" in out and "arc drifting (8 turns without contact)" in out
    assert "clues found 0 of 3" in out
    pv.advance(18)
    assert "arc at budget: no new pressure; climax hooks where the PC is" in prep_lines(pv)
    pv.advance(22)  # 16 of 12 used: past 130%
    assert "arc at 130%: ask the user once: extend or wrap up" in prep_lines(pv)
    assert pv.op("arc-review", "A2", "--kind", "midpoint", "--notes", "on course", turn=22).returncode == 0
    assert "midpoint review due" not in prep_lines(pv)


# ---- the PIV-5 limits --------------------------------------------------------------------------------------------------
def _break(*muts):
    def go(c):
        for m in muts:
            m(c)
    return go


LIMITS = [
    (lambda c: c["hidden"].update(twist={"text": "A broker is lying", "keywords": ["ember ledger"]}), "a pivot arc has no twist"),
    (lambda c: c["hidden"].update(twist={"text": "", "ladder": "Mio's secret"}), "a pivot arc has no twist"),
    (lambda c: c["hidden"].update(twist={"text": "", "keywords": ["ember ledger"]}), "a pivot arc has no twist"),
    (lambda c: c["hidden"].update(new_npcs=["Haru Ebisu", "Kenji Sato"]), "hidden.new_npcs has 2: at most one new NPC, the face"),
    (lambda c: c["hidden"]["fronts"].append({"name": "Second", "goal": "g", "moves": ["a", "b"]}), "hidden.fronts has 2: a pivot arc has exactly one front"),
    (lambda c: c["hidden"].update(fronts=[]), "hidden.fronts has 0: a pivot arc has exactly one front"),
    (lambda c: c["hidden"]["fronts"][0].update(moves=["only one"]), 'front "The Tide Broker" needs 2 or 3 moves with text (has 1)'),
    (lambda c: c["hidden"]["fronts"][0].update(moves=["a", "b", "c", "d"]), "needs 2 or 3 moves with text (has 4)"),
    (lambda c: c["hidden"].update(clues=["one", "two"]), "hidden.clues needs at least 3 (has 2)"),
    (lambda c: c.update(budget_turns=9), "budget_turns is 9: a pivot arc takes 10 to 15 turns"),
    (lambda c: c.update(budget_turns=16), "budget_turns is 16: a pivot arc takes 10 to 15 turns"),
    (lambda c: c.pop("budget_turns"), "budget_turns is 30: a pivot arc takes 10 to 15 turns"),  # arc-plan's default budget
    (lambda c: c["shared"].update(premise="The menders say a child may come to harm if the kids walk the quay."),
     'session zero line "no harm to kids" matches shared.premise'),
    (lambda c: c["shared"].update(seeds=["a net with gore on it"]), 'session zero veil "gore" matches shared.seeds[1]'),
    (lambda c: c["hidden"].update(notes="keep the gore off the page"), 'session zero veil "gore" matches hidden.notes'),
    (lambda c: c["hidden"]["clues"].append("kids put at harm by the broker"), 'session zero line "no harm to kids" matches hidden.clues[4]'),
]


@pytest.mark.parametrize("mutate,needle", LIMITS)
def test_adopt_refuses_each_pivot_limit(pv, mutate, needle):
    pv.advance(6)
    pv.draft(PIVOT, mutate)
    before = (pv.data / "arcs.json").read_bytes()
    r = pv.op("arc-adopt", "A2", turn=6)
    assert r.returncode == 4 and needle in r.stderr, r.stderr
    assert (pv.data / "arcs.json").read_bytes() == before  # nothing changed: A1 still live, A2 still a draft
    assert pv.live() == ["A1"] and pv.arc("A2")["status"] == "draft"
    f = pv.run("arc-adopt", "A2", "--turn", 6, "--evidence", "the user said go", "--force")  # --force adopts and records why
    assert f.returncode == 0 and "--force overrides" in f.stdout
    assert pv.arc("A2")["status"] == "provisional" and any(needle in x for x in pv.arc("A2")["adopted_forced"])
    assert pv.arc("A1")["status"] == "parked" and pv.live() == ["A2"]
    assert "(FORCED)" in pv.load("state")["changelog"][-1]["summary"] and "adopted with --force" in pv.ok("arc", "A2")


def test_adopt_lists_every_problem_at_once(pv):
    pv.advance(6)
    pv.draft(PIVOT, _break(
        lambda c: c["hidden"].update(twist={"text": "A secret", "keywords": ["ember ledger"]}, new_npcs=["a", "b"], clues=["one"]),
        lambda c: c["hidden"]["fronts"].append({"name": "Second", "goal": "g", "moves": ["a", "b"]}),
        lambda c: c.update(budget_turns=40),
        lambda c: c["shared"].update(premise="Kids come to harm."), lambda c: c["hidden"].update(notes="gore")))
    r = pv.op("arc-adopt", "A2", turn=6)
    assert r.returncode == 4 and r.stderr.count("\n  - ") == 7  # twist, new NPCs, fronts, clues, budget, a line and a veil: all at once
    for needle in ("no twist", "at most one new NPC", "exactly one front", "needs at least 3", "budget_turns is 40", 'line "no harm to kids"', 'veil "gore"'):
        assert needle in r.stderr
    assert pv.live() == ["A1"]


def test_adopt_needs_a_draft_and_a_live_arc_to_park(pv):
    pv.advance(6)
    pv.draft(PIVOT)
    assert pv.op("arc-adopt", "A1", turn=6).returncode == 4  # A1 is active, not a draft
    assert pv.op("arc-adopt", "A7", turn=6).returncode == 2
    assert pv.op("arc-adopt", "A2", turn=9).returncode == 1  # ahead of the log
    assert pv.op("arc-close", "A1", "--best", "x", turn=6).returncode == 0  # no live arc left to leave
    r = pv.op("arc-adopt", "A2", turn=6)
    assert r.returncode == 4 and "no live arc to park" in r.stderr and pv.arc("A2")["status"] == "draft"
    assert pv.op("arc-adopt", "A2", "--force", turn=6).returncode == 0  # forced: provisional, nothing to park
    assert pv.arc("A2")["status"] == "provisional" and pv.live() == ["A2"]


def test_re_aim_replaces_the_pivot_arc_and_the_old_arc_stays_parked(pv):
    pivoted(pv, at=6)
    pv.advance(8)
    pv.draft(PIVOT, lambda c: c["shared"].update(title="The Ferry Fare"))
    assert pv.op("arc-adopt", "A3", turn=8, ev="the user re-aimed it").returncode == 0
    assert pv.arc("A3")["status"] == "provisional" and pv.arc("A1")["status"] == "parked"
    a2 = pv.arc("A2")
    assert a2["status"] == "set_aside" and a2["closed_turn"] == 8 and a2["retro"]["turns_used"] == 2
    assert a2["retro"]["notes"] == "re-aimed: replaced by A3"
    assert pv.live() == ["A3"] and "arc A2 set aside" in pv.load("state")["changelog"][-1]["summary"]
    assert pv.run("wrap-up").returncode == 0


# ---- approving, closing ------------------------------------------------------------------------------------------------
def test_approving_a_provisional_arc_makes_it_active_with_no_arc_start(pv):
    pivoted(pv, at=6)
    r = pv.run("arc-approve", "A2")  # session zero holds lines and veils: the statement is still needed
    assert r.returncode == 4 and "--lines-checked" in r.stderr and "[ ] line (never happens): no harm to kids" in r.stdout
    assert pv.arc("A2")["status"] == "provisional"
    ok = pv.run("arc-approve", "A2", "--lines-checked", "--turn", 7)
    assert ok.returncode == 0, ok.stderr
    a2 = pv.arc("A2")
    assert a2["status"] == "active" and a2["approved_turn"] == 7 and a2["start_turn"] == 6  # budget still counts from adoption
    assert "now active; no arc-start needed" in pv.load("state")["changelog"][-1]["summary"]
    assert pv.live() == ["A2"] and pv.arc("A1")["status"] == "parked"
    assert "already active" in pv.op("arc-start", "A2", turn=7).stdout
    assert "already active" in pv.run("arc-approve", "A2", "--lines-checked").stdout
    assert "A2 [active]" in pv.ok("arc", "--list")
    # the other checks still apply to a provisional arc: it lists every problem at once, and --force overrides
    pv.advance(8)
    pv.draft(PIVOT, lambda c: c["shared"].update(title="Third", promise=""))
    assert pv.op("arc-adopt", "A3", turn=8, ev="e").returncode == 0  # the active A2 is parked in its turn; A1 stays parked
    assert pv.arc("A2")["status"] == "parked" and pv.arc("A1")["status"] == "parked" and pv.live() == ["A3"]
    pv.ok("arc-plan", "--id", "A3", "--file", pv.write_json("u.json", {"shared": {"stakes": "huge", "pc_tests": {}}}))
    r = pv.run("arc-approve", "A3", "--lines-checked")
    assert r.returncode == 4 and "shared.promise is empty" in r.stderr and "shared.stakes must be personal or wide" in r.stderr
    assert "twist" not in r.stderr and pv.arc("A3")["status"] == "provisional"  # no twist is expected of a pivot arc
    assert pv.run("arc-approve", "A3", "--lines-checked", "--force").returncode == 0 and pv.arc("A3")["status"] == "active"
    assert pv.arc("A3")["approved_forced"]


def test_a_provisional_arc_that_gained_a_twist_is_checked_like_any(pv):
    pivoted(pv, at=6)
    pv.ok("arc-plan", "--id", "A2", "--file", pv.write_json("u.json", {"hidden": {"twist": {"text": "A secret", "keywords": []}}}))
    r = pv.run("arc-approve", "A2", "--lines-checked")
    assert r.returncode == 4 and "hidden.twist needs a ladder" in r.stderr


def test_a_parked_arc_is_not_approved_or_started_and_may_be_closed(pv):
    pivoted(pv, at=6)
    r = pv.run("arc-approve", "A1", "--lines-checked")
    assert r.returncode == 4 and "A1 is parked" in r.stderr and "arc-unpark" in r.stderr
    # closing: a parked arc stopped when it was parked
    pv.advance(9)
    assert pv.op("arc-close", "A1", "--status", "set_aside", turn=7).returncode == 1  # a retro needs something to say
    assert pv.op("arc-close", "A1", "--notes", "the user dropped the guild plot", turn=9).returncode == 4  # closed needs active
    r = pv.op("arc-close", "A1", "--status", "set_aside", "--notes", "the user dropped the guild plot", turn=9)
    assert r.returncode == 0, r.stderr
    a1 = pv.arc("A1")
    assert a1["status"] == "set_aside" and a1["closed_turn"] == 9
    assert a1["retro"]["turns_used"] == 4 and a1["retro"]["budget"] == 10 and a1["retro"]["notes"] == "the user dropped the guild plot"
    assert pv.live() == ["A2"]  # the pivot arc carries on
    # a provisional arc closes as set_aside too, never as closed
    assert pv.op("arc-close", "A2", "--best", "x", turn=9).returncode == 4
    assert pv.op("arc-close", "A2", "--status", "set_aside", "--best", "x", turn=9).returncode == 0
    assert pv.arc("A2")["status"] == "set_aside" and pv.arc("A2")["retro"]["turns_used"] == 3 and pv.live() == []


def test_one_arc_starts_at_a_time_provisional_included(pv):
    pivoted(pv, at=6)
    pv.draft(CHARTER, lambda c: c["shared"].update(title="Next", set_pieces=["a chase"]))
    pv.ok("arc-approve", "A3", "--lines-checked")
    r = pv.op("arc-start", "A3", turn=6)
    assert r.returncode == 4 and "A2 is still provisional" in r.stderr
    assert pv.op("arc-start", "A2", turn=6).returncode == 4  # a provisional arc is live already: arc-approve it
    assert pv.live() == ["A2"]


# ---- going back: arc-unpark --------------------------------------------------------------------------------------------
def test_unpark_is_one_write_that_revives_the_parked_arc_and_closes_the_pivot_arc(pv):
    pivoted(pv, at=6)
    pv.advance(10)
    pv.op("arc-clue", "A2", 1, turn=9)
    log_before, arcs_before = len(pv.load("state")["changelog"]), (pv.data / "arcs.json").read_bytes()
    r = pv.op("arc-unpark", "A1", "--notes", "Aiko helped the net menders and came back", turn=10, ev="the PC returned to the guild clerk")
    assert r.returncode == 0, r.stderr
    log = pv.load("state")["changelog"]
    assert len(log) == log_before + 1 and log[-1]["cmd"] == "arc-unpark"  # one write, one log entry: no separate close and start
    assert log[-1]["evidence"] == "the PC returned to the guild clerk" and log[-1]["turn"] == 10
    a1, a2 = pv.arc("A1"), pv.arc("A2")
    assert a1["status"] == "active" and a1["unparked_turn"] == 10
    assert a2["status"] == "set_aside" and a2["closed_turn"] == 10
    assert a2["retro"]["notes"] == "Aiko helped the net menders and came back" and a2["retro"]["turns_used"] == 4 and a2["retro"]["clues_found"] == 1
    assert pv.live() == ["A1"]  # never two live; the arcs file changed once
    assert (pv.data / "arcs.json").read_bytes() != arcs_before
    assert pv.run("wrap-up").returncode == 0
    assert "A1 [active]" in pv.ok("arc", "--list") and "A2 [set_aside]" in pv.ok("arc", "--list")
    assert 'parked arc' not in pv.ok("resume")
    # the pause is not spent from A1's budget (4 turns before it was parked, 4 parked), and drift counts from its return
    assert a1["paused_turns"] == 4 and a1["start_turn"] == 6
    assert "t4/10 (40%)" in prep_lines(pv)  # turn 10 less the 4 turns it was parked: not "t8/10"
    pv.op("pc-thread", "kept asking the net menders", turn=9)  # the quiet turns of the pivot arc do not make A1 pivot again at once
    out = pv.ok("arc-pivot")
    assert "no pivot detected (the last 3 turns are not all after the arc returned (turn 10))" in out and not fired(out)
    pv.advance(17)  # 7 turns since the return, none with contact: not drifting yet (the pivot arc's quiet turns do not count)
    assert "arc drifting" not in prep_lines(pv)
    pv.advance(18)
    assert "arc drifting" in prep_lines(pv)


def test_unpark_refusals(pv):
    pivoted(pv, at=6)
    before = (pv.data / "arcs.json").read_bytes()
    assert pv.op("arc-unpark", "A2", "--notes", "x", turn=6).returncode == 4  # not parked
    assert pv.op("arc-unpark", "A1", "--notes", "  ", turn=6).returncode == 1  # the notes are the retro
    assert pv.run("arc-unpark", "A1", "--turn", 6, "--evidence", "e").returncode == 2  # --notes is required
    assert pv.run("arc-unpark", "A1", "--notes", "x", "--turn", 6).returncode == 2  # so is the evidence
    assert pv.op("arc-unpark", "A7", "--notes", "x", turn=6).returncode == 2
    assert (pv.data / "arcs.json").read_bytes() == before
    # once the pivot arc is approved (active), going back is a different decision: the active arc is not closed silently
    pv.ok("arc-approve", "A2", "--lines-checked")
    r = pv.op("arc-unpark", "A1", "--notes", "x", turn=6)
    assert r.returncode == 4 and "A2 is active, not a provisional pivot arc" in r.stderr
    assert pv.live() == ["A2"] and pv.arc("A1")["status"] == "parked"
    # with no live arc at all the parked one simply comes back
    assert pv.op("arc-close", "A2", "--best", "done", turn=6).returncode == 0
    ok = pv.op("arc-unpark", "A1", "--notes", "back to the guild", turn=7)
    assert ok.returncode == 0 and "no provisional arc was live" in pv.load("state")["changelog"][-1]["summary"]
    assert pv.live() == ["A1"]


def test_two_arcs_are_never_live_at_once(pv):
    pivoted(pv, at=6)
    assert pv.live() == ["A2"]
    pv.draft(PIVOT, lambda c: c["shared"].update(title="Re-aimed"))
    assert pv.op("arc-adopt", "A3", turn=6).returncode == 0 and pv.live() == ["A3"]
    assert pv.op("arc-unpark", "A1", "--notes", "back", turn=7).returncode == 0 and pv.live() == ["A1"]
    pv.draft(PIVOT, lambda c: c["shared"].update(title="Again"))
    assert pv.op("arc-adopt", "A4", turn=7).returncode == 0 and pv.live() == ["A4"]
    # a hand-edited file with two live arcs is caught on every write and by wrap-up
    a = pv.load("arcs")
    a["arcs"][0]["status"] = "active"
    pv.save_json("arcs", a)
    assert pv.live() == ["A1", "A4"]
    assert "more than one live (active or provisional) arc (A1, A4)" in pv.run("wrap-up").stderr


# ---- payload ops: commit-turn and record -------------------------------------------------------------------------------
def test_adopt_and_unpark_are_payload_ops_with_evidence(pv):
    pv.advance(5)
    pv.draft(PIVOT)
    prompt = pv.write("prompt.txt", SAYS)
    ev = "Aiko followed the net menders to the quay"
    adopt = {"turn": 6, "ops": [{"op": "arc-adopt", "args": {"id": "A2"}, "evidence": ev}], "turn_log": {"inputs": "i", "summary": "s"}}
    r = pv.run("commit-turn", "--prompt", prompt, "--payload", pv.write_json("p1.json", adopt))
    assert r.returncode == 0, r.stdout + r.stderr
    assert pv.arc("A2")["status"] == "provisional" and pv.arc("A2")["start_turn"] == 6 and pv.arc("A1")["status"] == "parked"
    assert [e["evidence"] for e in pv.load("state")["changelog"] if e["cmd"] == "arc-adopt"] == [ev]
    unpark = {"turn": 7, "ops": [{"op": "arc-unpark", "args": {"id": "A1", "notes": "Aiko went back to the clerk"}, "evidence": "she walked back"}],
              "turn_log": {"inputs": "i", "summary": "s", "arc_contact": True}}
    r = pv.run("commit-turn", "--prompt", prompt, "--payload", pv.write_json("p2.json", unpark))
    assert r.returncode == 0, r.stdout + r.stderr
    assert pv.arc("A1")["status"] == "active" and pv.arc("A2")["status"] == "set_aside" and pv.live() == ["A1"]
    assert pv.arc("A2")["retro"]["notes"] == "Aiko went back to the clerk"
    # the whole payload is refused, and nothing written, when an op lacks its evidence or breaks a limit
    pv.draft(PIVOT, lambda c: c["hidden"].update(clues=["one"]))
    before = (pv.data / "arcs.json").read_bytes()
    bad = {"turn": 8, "ops": [{"op": "arc-adopt", "args": {"id": "A3"}, "evidence": ev}], "turn_log": {"inputs": "i", "summary": "s"}}
    r = pv.run("commit-turn", "--prompt", prompt, "--payload", pv.write_json("p3.json", bad))
    assert r.returncode != 0 and "hidden.clues needs at least 3" in r.stdout and (pv.data / "arcs.json").read_bytes() == before
    bad["ops"][0] = {"op": "arc-adopt", "args": {"id": "A3", "force": False}}
    r = pv.run("commit-turn", "--prompt", prompt, "--payload", pv.write_json("p3.json", bad))
    assert r.returncode != 0 and "evidence" in r.stdout and (pv.data / "arcs.json").read_bytes() == before
    forced = dict(bad, ops=[{"op": "arc-adopt", "args": {"id": "A3", "force": True}, "evidence": ev}])
    assert pv.run("record", pv.write_json("p4.json", dict(forced, turn_log={"inputs": "i", "summary": "s", "prompt": "p"})), "--dry-run").returncode == 0


# ---- the planner page --------------------------------------------------------------------------------------------------
def page(env, name="page.html"):
    r = env.run("planner-page", "--out", env.tmp / name)
    return r, env.tmp / name


def test_page_hides_a_provisional_arc_and_shows_a_parked_one(pv):
    pivoted(pv, at=6)
    r, f = page(pv)
    assert r.returncode == 0, r.stderr
    html = f.read_text(encoding="utf-8")
    assert "The Menders" not in html and PIVOT_PROMISE not in html and "Provisional" not in html and "Haru" not in html  # not until approved
    assert "Who Holds the Keys" in html and "Parked" in html and "Paused for now" in html and "In play" not in html
    assert "st-parked" in html
    assert pv.run("preflight").stdout.count("planner page renders spoiler-safe") == 1
    # once approved it is the current arc, and the parked one stays shown as parked
    pv.ok("arc-approve", "A2", "--lines-checked")
    r, f = page(pv, "page2.html")
    html = f.read_text(encoding="utf-8")
    assert r.returncode == 0 and "The Menders&#x27; Debt" in html and PIVOT_PROMISE in html and "In play" in html and "Parked" in html
    assert "Haru" not in html and "salt-stained ledger" not in html  # hidden fields stay hidden


def test_page_never_shows_offramps_and_refuses_their_text(pv):
    pv.offramps()
    r, f = page(pv)
    assert r.returncode == 0, r.stderr
    html = f.read_text(encoding="utf-8")
    for sk in OFFRAMPS:
        for v in sk.values():
            assert v.replace("'", "&#x27;") not in html and v not in html
    assert "Haru Ebisu" not in html and "off-ramp" not in html.lower()
    # the text of an off-ramp in a shared field is a hidden term: the page is refused (exit 4) and nothing is written
    leak = "The net mender hands over a tide table at dusk, and A net mender hands over a tide table at dusk."
    for field, value in (("premise", leak), ("pressure", "Watch: Old Noriko of the ferry waits."), ("subplot", "Who has been moving the chore rota?"),
                         ("tone", "a broker who wants the menders' hut")):
        pv.ok("arc-plan", "--id", "A1", "--file", pv.write_json("u.json", {"shared": {field: value}}))
        out = pv.tmp / "leak.html"
        r = pv.run("planner-page", "--out", out)
        assert r.returncode == 4 and "off-ramp" in r.stderr and not out.exists(), (field, r.stderr)
        pv.ok("arc-plan", "--id", "A1", "--file", pv.write_json("u.json", {"shared": {field: CHARTER["shared"][field]}}))
    assert pv.run("planner-page", "--out", pv.tmp / "ok.html").returncode == 0
    # preflight renders the same page: its FAIL line names the leak
    pv.ok("arc-plan", "--id", "A1", "--file", pv.write_json("u.json", {"shared": {"premise": "A net mender hands over a tide table at dusk."}}))
    assert "planner page would leak a hidden term" in pv.run("preflight").stdout


def test_an_adopted_arc_may_echo_the_offramp_it_grew_from_but_no_other_arc_may(pv):
    pv.offramps()  # sketch 1's promise is the pivot arc's promise
    pivoted(pv, at=6)
    pv.ok("arc-approve", "A2", "--lines-checked")
    r, f = page(pv)
    assert r.returncode == 0, r.stderr  # A2's promise equals an off-ramp promise stored on A1: the pivot arc was approved
    assert PIVOT_PROMISE in f.read_text(encoding="utf-8")
    pv.draft(PIVOT, lambda c: c["shared"].update(title="Not a pivot arc"))  # a plain draft with the same text is a leak
    out = pv.tmp / "leak.html"
    r = pv.run("planner-page", "--out", out)
    assert r.returncode == 4 and "off-ramp promise" in r.stderr and not out.exists()


def test_index_shows_a_parked_arc_and_never_a_provisional_one(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools"))
    import build_site
    root = tmp_path / "root"
    data = root / "campaigns" / "demo" / "data"
    data.mkdir(parents=True)
    (root / "campaigns" / "demo" / "campaign.json").write_text(json.dumps({"display": "Demo"}), encoding="utf-8")
    (data / "state.json").write_text(json.dumps({"turn": 9, "day": 3}), encoding="utf-8")
    monkeypatch.setattr(build_site, "ROOT", root)
    rows = [{"id": "A1", "status": "parked", "shared": {"title": "Old Plan"}}, {"id": "A2", "status": "provisional", "shared": {"title": "Pivot Plan"}}]
    (data / "arcs.json").write_text(json.dumps({"arcs": rows}), encoding="utf-8")
    s = build_site.summary("demo", "Old Plan Pivot Plan")
    assert s["arc_title"] == "Old Plan" and s["arc_status"] == "Parked"
    rows[0]["status"] = "active"
    (data / "arcs.json").write_text(json.dumps({"arcs": rows}), encoding="utf-8")
    assert build_site.summary("demo", "Old Plan Pivot Plan")["arc_status"] == "In play"
    rows[0]["status"] = "closed"
    (data / "arcs.json").write_text(json.dumps({"arcs": rows}), encoding="utf-8")
    assert build_site.summary("demo", "Old Plan Pivot Plan")["arc_title"] is None  # only a provisional arc is left: nothing to show
