"""Arc planner: data/arcs.json, planning commands, turn ops, prep/resume lines, check-prompt, snapshots and the planner page.
Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA); the real data dir is never written."""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL_DATA = REPO / "campaigns" / "classroom-2b" / "data"
SAYS = "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\nCrew: Mio Tachibana counts coins twice, shoulders tight.\nWorld: The House Manager posts the chore rota."

CHARTER = {
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

    def charter(self, mutate=None):
        c = copy.deepcopy(CHARTER)
        if mutate:
            mutate(c)
        return self.write("charter.json", json.dumps(c))

    def turn(self, n, inputs="Aiko chats with the housemates in the kitchen", cut="Continue at the kitchen.", flag=False):
        a = ["turn", n, "--inputs", inputs, "--summary", f"Turn {n}.", "--prompt", f"Cut: {cut}\nWorld: Quiet."]
        self.ok(*a, *(["--arc-contact"] if flag else []))

    def advance(self, to):
        for n in range(self.load("state")["turn"] + 1, to + 1):
            self.turn(n)

    def op(self, name, *args, turn, ev="the story showed it"):
        return self.run(name, *args, "--turn", turn, "--evidence", ev)

    def planned(self, mutate=None, approve=True):
        """Draft (and approve) arc A1 on the scratch data."""
        self.ok("arc-plan", "--file", self.charter(mutate))
        if approve:
            self.ok("arc-approve", "A1", "--lines-checked")

    def active(self, start=2, **kw):
        self.advance(start)
        self.planned(**kw)
        assert self.op("arc-start", "A1", turn=start).returncode == 0


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)  # start without the optional file (the live campaign has one): it is exercised
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test",
              "--background", "Grew up above a repair shop", "--power", "Mend")
    assert r.returncode == 0, r.stderr
    return e


# ---- the optional file ---------------------------------------------------------
def test_everything_reads_without_arcs_json(env):
    out = env.ok("resume")
    assert "Arc planner: no plan yet: offer a planning session (docs/arc-planning.md)" in out
    assert "no arc live: one line under the prompt offers a planning session" in env.ok("prep")
    assert "no arc yet" in env.ok("arc") and "no arcs yet" in env.ok("arc", "--list")
    assert "Session zero: not recorded" in env.ok("plan-brief")
    assert "not recorded" in env.ok("session-zero")
    assert env.run("check-prompt", env.write("p.txt", SAYS)).returncode in (0, 2)
    assert not (env.data / "arcs.json").exists()  # reads never create it
    env.ok("session-zero", "--tone", "warm")  # the first write does
    assert env.load("arcs")["session_zero"]["tone"] == "warm" and env.load("arcs")["version"] == 1


def test_template_ships_the_skeleton():
    t = json.loads((REPO / "templates" / "voyage-director" / "campaign" / "data" / "arcs.json").read_text(encoding="utf-8"))
    assert t == {"version": 1, "page_url": None, "session_zero": {"tone": "", "lines": [], "veils": [], "pillars": {}, "pacing": "",
                                                                   "ending_hope": "", "notes": "", "updated_turn": None},
                 "pc_threads": [], "acts": [], "arcs": []}


# ---- session zero --------------------------------------------------------------
def test_session_zero_merges(env):
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids;no betrayal by allies", "--veils", "gore",
           "--pillars", "combat=1,social=3", "--pacing", "steady", "--ending-hope", "bittersweet")
    env.ok("session-zero", "--pillars", "combat=2,mystery=3", "--lines", "no harm to kids", "--turn", "1")
    sz = env.load("arcs")["session_zero"]
    assert sz["pillars"] == {"combat": 2, "social": 3, "mystery": 3}  # merged per style
    assert sz["lines"] == ["no harm to kids"] and sz["veils"] == ["gore"] and sz["tone"] == "warm"  # lists replaced, the rest kept
    assert sz["updated_turn"] == 1
    f = env.write("sz.json", json.dumps({"notes": "likes puzzles", "pillars": {"exploration": 2}}))
    env.ok("session-zero", "--file", f)
    sz = env.load("arcs")["session_zero"]
    assert sz["notes"] == "likes puzzles" and sz["pillars"]["exploration"] == 2 and sz["pillars"]["social"] == 3
    shown = env.ok("session-zero")
    assert "lines (never happens): no harm to kids" in shown and "combat 2" in shown
    assert env.run("session-zero", "--pillars", "combat=9").returncode == 2
    assert env.run("session-zero", "--file", env.write("bad.json", '{"mood": "x"}')).returncode == 2


# ---- act pitches -----------------------------------------------------------------
ACT = {"shared": {"title": "Move-In", "theme": "Strangers become a house", "question": "Who do you become?", "builds_to": "The first meeting",
                  "stakes_scale": "A room and a rota", "ending_shape": "Warm and unsettled"}, "hidden": {"turning_point": "Day 6", "notes": "n"}}


def test_act_plan_approve_close(env):
    f = env.write("act.json", json.dumps(ACT))
    env.ok("act-plan", 1, "--file", f)
    assert env.load("arcs")["acts"][0]["status"] == "draft"
    thin = copy.deepcopy(ACT)
    thin["shared"].update({"theme": "", "builds_to": " "})
    env.ok("act-plan", 1, "--file", env.write("thin.json", json.dumps(thin)))
    r = env.run("act-approve", 1)
    assert r.returncode == 4 and "shared.theme is empty" in r.stderr and "shared.builds_to is empty" in r.stderr  # all at once
    assert env.run("act-approve", 1, "--force").returncode == 0 and env.load("arcs")["acts"][0]["approved_forced"]
    env.ok("act-plan", 1, "--file", f)  # editing an approved pitch keeps it approved
    assert env.load("arcs")["acts"][0]["status"] == "approved" and "stays approved" in env.load("state")["changelog"][-1]["summary"]
    assert env.run("act-deviation", 1, "Day 6 moves to Day 5", "--turn", 1, "--evidence", "player moved").returncode == 0
    assert env.load("arcs")["acts"][0]["deviations"] == [{"turn": 1, "text": "Day 6 moves to Day 5"}]
    assert env.run("act-deviation", 3, "x", "--turn", 1, "--evidence", "e").returncode == 2  # no pitch for act 3
    env.ok("act-close", 1, "--retro", "Warm start, one slow errand")
    a = env.load("arcs")["acts"][0]
    assert a["status"] == "closed" and a["retro"].startswith("Warm") and a["closed_turn"] is not None
    assert env.run("act-plan", 1, "--file", f).returncode == 4  # closed: refused
    assert env.run("act-plan", 9, "--file", f).returncode == 2  # not an act of this campaign
    assert env.run("act-plan", 2, "--file", env.write("x.json", '{"pitch": {}}')).returncode == 2


# ---- arc charters ----------------------------------------------------------------
def test_arc_plan_new_and_update_keep_progress(env):
    env.ok("arc-plan", "--file", env.charter())
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(title="Second")))
    arcs = env.load("arcs")["arcs"]
    assert [a["id"] for a in arcs] == ["A1", "A2"] and arcs[0]["status"] == "draft" and arcs[0]["act"] == 1 and arcs[0]["budget_turns"] == 10
    d = env.load("arcs")["arcs"][0]
    assert d["hidden"]["clues"][0] == {"text": "a thick envelope", "found_turn": None}
    assert d["hidden"]["fronts"][0]["moves"][0] == {"text": "A polite offer", "done_turn": None}
    default = env.write("d.json", json.dumps({"shared": CHARTER["shared"], "hidden": CHARTER["hidden"]}))
    env.ok("arc-plan", "--file", default)
    assert env.load("arcs")["arcs"][2]["budget_turns"] == 30  # default budget
    # update: given keys merge; an active arc keeps its progress and its status
    env.advance(2)
    env.ok("arc-approve", "A1", "--lines-checked")
    env.op("arc-start", "A1", turn=2)
    env.advance(4)
    env.op("arc-move", "A1", "Lender", 1, turn=3)
    env.op("arc-clue", "A1", 2, turn=4)
    upd = env.write("u.json", json.dumps({"budget_turns": 12, "shared": {"tone": "Wry and quiet"}, "hidden": {"clues": ["a thick envelope", "a neighbor's story", "a cash payment", "a new clue"],
                                                                                                           "fronts": CHARTER["hidden"]["fronts"]}}))
    env.ok("arc-plan", "--file", upd, "--id", "A1")
    a = env.load("arcs")["arcs"][0]
    assert a["status"] == "active" and a["budget_turns"] == 12 and a["shared"]["tone"] == "Wry and quiet" and a["shared"]["title"] == "Who Holds the Keys"
    assert a["hidden"]["clues"][1]["found_turn"] == 4 and a["hidden"]["fronts"][0]["moves"][0]["done_turn"] == 3
    assert a["hidden"]["twist"]["text"] and "stays active" in env.load("state")["changelog"][-1]["summary"]
    env.op("arc-close", "A1", "--best", "x", turn=5)
    assert env.run("arc-plan", "--file", upd, "--id", "A1").returncode == 4  # closed arcs cannot be edited
    assert env.run("arc-plan", "--file", upd, "--id", "A7").returncode == 2
    assert env.run("arc-plan", "--file", env.write("w.json", '{"shared": {"set_pieces": "oops"}}')).returncode == 2


@pytest.mark.parametrize("mutate,needle", [
    (lambda c: c["shared"].update(promise=""), "shared.promise is empty"),
    (lambda c: c["shared"].update(stakes="huge"), "shared.stakes must be personal or wide"),
    (lambda c: c["shared"].update(set_pieces=[]), "shared.set_pieces needs at least one"),
    (lambda c: c["shared"].update(wins_on_offer=[]), "shared.wins_on_offer needs at least one"),
    (lambda c: c["shared"].update(backstory_hooks=[]), "shared.backstory_hooks needs at least one"),
    (lambda c: c["shared"].update(pc_tests={}), 'no test for player character "Aiko Tanaka"'),
    (lambda c: c["hidden"]["twist"].update(text=""), "hidden.twist.text is empty"),
    (lambda c: c["hidden"]["twist"].update(ladder="Nobody's secret"), "is not a key of threads.json"),
    (lambda c: c["hidden"]["twist"].update(ladder=None, keywords=[]), "needs a ladder"),
    (lambda c: c["hidden"].update(fronts=[]), "hidden.fronts needs at least one front"),
    (lambda c: c["hidden"]["fronts"][0].update(goal=""), "has no goal"),
    (lambda c: c["hidden"]["fronts"][0].update(moves=["only one"]), "needs 2 to 4 escalating moves"),
    (lambda c: c["hidden"]["fronts"][0].update(moves=list("abcde")), "needs 2 to 4 escalating moves"),
    (lambda c: c["hidden"]["antagonist"].update(first_contact=""), "antagonist.first_contact is empty"),
    (lambda c: c["hidden"].update(clues=["one", "two"]), "needs at least 3"),
    (lambda c: c["hidden"].update(new_npcs=list("abcd")), "at most 3"),
])
def test_arc_approve_refuses_each_rule(env, mutate, needle):
    env.planned(mutate, approve=False)
    r = env.run("arc-approve", "A1", "--lines-checked")
    assert r.returncode == 4 and needle in r.stderr, r.stderr
    assert env.load("arcs")["arcs"][0]["status"] == "draft"
    f = env.run("arc-approve", "A1", "--lines-checked", "--force")  # --force approves and records why
    assert f.returncode == 0 and env.load("arcs")["arcs"][0]["status"] == "approved" and env.load("arcs")["arcs"][0]["approved_forced"]


def test_arc_approve_lists_every_problem_and_warns_without_act_pitch(env):
    env.planned(lambda c: (c["shared"].update(promise="", stakes=""), c["hidden"].update(clues=[])), approve=False)
    r = env.run("arc-approve", "A1")
    assert r.returncode == 4 and r.stderr.count("\n  - ") >= 3
    env.planned(approve=False)  # A2 is fine
    ok = env.run("arc-approve", "A2", "--lines-checked")
    assert ok.returncode == 0 and "act 1 has no approved pitch" in ok.stdout


def test_set_piece_repeat_and_lines_gate(env):
    env.planned()
    env.ok("session-zero", "--lines", "no harm to kids", "--veils", "gore")
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(set_pieces=[" A Tense House Meeting ", "a chase"])))
    r = env.run("arc-approve", "A2", "--lines-checked")
    assert r.returncode == 4 and "set pieces repeat arc A1" in r.stderr and "A Tense House Meeting" in r.stderr
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(set_pieces=["a chase"])), "--id", "A2")
    r = env.run("arc-approve", "A2")  # session zero holds lines and veils: the checklist is printed and --lines-checked required
    assert r.returncode == 4 and "[ ] line (never happens): no harm to kids" in r.stdout and "[ ] veil (offscreen only): gore" in r.stdout
    assert "--lines-checked" in r.stderr
    assert env.run("arc-approve", "A2", "--lines-checked").returncode == 0


def test_arc_start_one_at_a_time_and_reads(env):
    env.advance(2)
    env.planned()
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(title="Next", set_pieces=["a chase"])))
    env.ok("arc-approve", "A2", "--lines-checked")
    assert env.op("arc-start", "A1", turn=2).returncode == 0
    r = env.op("arc-start", "A2", turn=2)
    assert r.returncode == 4 and "A1 is still active" in r.stderr
    assert env.op("arc-start", "A1", turn=2).returncode == 0 and "already active" in env.op("arc-start", "A1", turn=2).stdout
    assert env.load("arcs")["arcs"][0]["start_turn"] == 2
    full, shared = env.ok("arc", "A1"), env.ok("arc", "--shared")
    assert "glass lantern" in full and "hidden (director only)" in full and "Sōichi Tamaru" in full
    assert "glass lantern" not in shared and "Sōichi Tamaru" not in shared and "Who Holds the Keys" in shared
    assert "A2 [approved]" in env.ok("arc", "--list")
    assert 'arc A1 "Who Holds the Keys" active t0/10' in env.ok("resume")
    assert "Planner page: https://riggedrealm.github.io/campaign-helper/classroom-2b/\n" in env.ok("resume")  # default from site.json
    env.ok("planner-page", "--set-url", "https://claude.ai/artifact/abc123")
    assert "Planner page: https://claude.ai/artifact/abc123\n" in env.ok("resume") and "github.io" not in env.ok("resume")  # a stored page_url wins


# ---- turn ops through commit-turn --------------------------------------------------
def test_turn_ops_through_commit_turn_payload(env):
    env.active(start=2)
    env.advance(3)
    ev = "Voyage showed it"
    payload = {"turn": 4, "ops": [
        {"op": "arc-move", "args": {"id": "A1", "front": "lender", "n": 1}, "evidence": ev},
        {"op": "arc-clue", "args": {"id": "A1", "n": 2}, "evidence": ev},
        {"op": "arc-contact", "args": {"id": "A1"}, "evidence": ev},
        {"op": "arc-review", "args": {"id": "A1", "kind": "scene", "notes": "fine"}, "evidence": ev},
        {"op": "arc-deviation", "args": {"id": "A1", "text": "the inspection moved"}, "evidence": ev},
        {"op": "pc-thread", "args": {"text": ["went back to the rota drawer", "three times"]}, "evidence": ev}],
        "turn_log": {"inputs": "i", "summary": "s", "arc_contact": True}}
    pf, prompt = env.write("payload.json", json.dumps(payload)), env.write("prompt.txt", SAYS)
    r = env.run("commit-turn", "--prompt", prompt, "--payload", pf)
    assert r.returncode == 0, r.stdout + r.stderr
    a = env.load("arcs")
    arc = a["arcs"][0]
    assert arc["hidden"]["fronts"][0]["moves"][0]["done_turn"] == 4 and arc["hidden"]["clues"][1]["found_turn"] == 4
    assert arc["hidden"]["antagonist"]["contact_turn"] == 4 and arc["reviews"] == [{"turn": 4, "kind": "scene", "notes": "fine"}]
    assert arc["shared"]["deviations"] == [{"turn": 4, "text": "the inspection moved"}]
    assert a["pc_threads"] == [{"turn": 4, "text": "went back to the rota drawer three times", "evidence": ev}]
    assert env.load("turns")[-1]["arc_contact"] is True
    assert "arc_contact" not in env.load("turns")[0]
    # a bad op or a non-boolean flag rejects the whole payload and writes nothing
    before = (env.data / "arcs.json").read_bytes()
    bad = dict(payload, turn=5, ops=[{"op": "arc-clue", "args": {"id": "A1", "n": 9}, "evidence": ev}])
    r = env.run("commit-turn", "--prompt", prompt, "--payload", env.write("b.json", json.dumps(bad)))
    assert r.returncode != 0 and "has 4 clues" in r.stdout and (env.data / "arcs.json").read_bytes() == before
    bad = dict(payload, turn=5, ops=[], turn_log={"inputs": "i", "summary": "s", "arc_contact": "yes"})
    r = env.run("commit-turn", "--prompt", prompt, "--payload", env.write("b.json", json.dumps(bad)))
    assert r.returncode != 0 and "arc_contact must be true or false" in r.stdout
    assert env.run("record", env.write("r.json", json.dumps(dict(payload, turn=5, ops=[], turn_log={"inputs": "i", "summary": "s", "x": 1}))), "--dry-run").returncode == 2


def test_ops_refuse_wrong_state_and_are_idempotent(env):
    env.advance(2)
    env.planned()
    assert env.op("arc-clue", "A1", 1, turn=2).returncode == 4  # approved, not started
    env.op("arc-start", "A1", turn=2)
    assert env.op("arc-move", "A1", "nobody", 1, turn=2).returncode == 2
    assert env.op("arc-move", "A1", "Lender", 5, turn=2).returncode == 1
    assert env.op("arc-move", "A1", "Lender", 2, turn=2).returncode == 0  # out of order: a note, not a refusal
    assert "already done" in env.op("arc-move", "A1", "Lender", 2, turn=2).stdout
    assert env.op("arc-review", "A1", "--kind", "scene", "--notes", " ", turn=2).returncode == 1
    assert env.op("arc-reveal", "A1", turn=2).returncode == 0
    assert env.op("pc-thread", "x", turn=9).returncode == 1  # turn ahead of the log


# ---- prep lines -----------------------------------------------------------------
def prep_lines(env):
    out = env.ok("prep")
    return out[out.index("LIVE CHECKLIST"):]


def test_prep_arc_lines_midpoint_antagonist_budget(env):
    env.active(start=2)
    assert "arc A1 \"Can you earn the house's trust before it must choose?\" t0/10 (0%)" in prep_lines(env)
    env.advance(6)  # 4 of 10 used
    out = prep_lines(env)
    assert "t4/10 (40%)" in out and "midpoint review due" not in out and "clues found 0 of 4" in out
    env.advance(7)  # 50%
    assert "antagonist not on screen yet: contact due by the midpoint" in prep_lines(env)
    env.op("arc-contact", "A1", turn=7)
    env.advance(8)  # 60%
    out = prep_lines(env)
    assert "midpoint review due (arc-review --kind midpoint)" in out and "antagonist not on screen" not in out
    env.op("arc-review", "A1", "--kind", "midpoint", "--notes", "on course", turn=8)
    assert "midpoint review due" not in prep_lines(env)
    env.advance(12)
    out = prep_lines(env)
    assert "arc at budget: no new pressure; climax hooks where the PC is" in out and "arc at 130%" not in out
    env.advance(15)
    assert "arc at 130%: ask the user once: extend or wrap up" in prep_lines(env)


def test_prep_arc_approved_waiting(env):
    env.advance(2)
    env.planned()
    assert "arc A1 approved, not started: arc-start when its first pressure shows in Voyage's output" in prep_lines(env)


def test_drift_window_and_boredom_flags(env):
    env.active(start=2)
    env.advance(10)
    env.op("arc-clue", "A1", 1, turn=10)  # a recorded op in the window counts as contact
    assert "drifting" not in prep_lines(env)
    env.advance(18)  # window 11-18: the clue at 10 is out
    assert "arc drifting" in prep_lines(env)
    assert "boredom" not in prep_lines(env)
    # boredom: needs 10+ turns; short inputs, skips in the Cut line, a drag note
    for n in range(19, 23):
        env.turn(n, inputs="a" * 120)
    for n in (23, 24):
        env.turn(n, inputs="ok", cut="Skip to the evening.")
    env.turn(25, inputs="ok")
    out = prep_lines(env)
    assert "boredom flags: shorter inputs, repeated skips" in out and "two boredom flags: one-line check with the user; next pressure card adds variety" in out
    env.ok("feedback", "--kind", "scene", "--drag", "the waiting", "--turn", 25)
    assert "boredom flags: shorter inputs, repeated skips, drag in the latest feedback" in prep_lines(env)


# ---- check-prompt -----------------------------------------------------------------
def test_check_prompt_blocks_twist_keywords_until_revealed(env):
    env.active(start=2)
    leak = env.write("leak.txt", "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen.\nCrew: Mio Tachibana stares at the glass lantern.\nWorld: Quiet.")
    r = env.run("check-prompt", leak)
    assert r.returncode == 1 and 'FAIL: possible secret leak "glass lantern" from arc A1 twist' in r.stdout
    assert env.op("arc-reveal", "A1", turn=2).returncode == 0
    assert env.run("check-prompt", leak).returncode in (0, 2) and "secret leak" not in env.run("check-prompt", leak).stdout
    # a closed arc's twist no longer blocks, a draft's does
    env.op("arc-close", "A1", "--best", "x", turn=2)
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(set_pieces=["a chase"])))
    assert "from arc A2 twist" in env.run("check-prompt", leak).stdout


# ---- close, retro, snapshots ----------------------------------------------------------
def test_arc_close_computes_the_retro(env):
    env.active(start=2)
    env.advance(9)
    env.op("arc-clue", "A1", 1, turn=9)
    env.op("arc-clue", "A1", 3, turn=9)
    assert env.op("arc-close", "A1", turn=9).returncode == 1  # a retro needs something to say
    assert env.op("arc-close", "A1", "--best", "the vote", "--drag", "the walk", "--wins", "an ally", "--spotlight", "Mio led",
                  "--threads-closed", "none", "--weakest", "slow middle", "--notes", "ok", turn=9).returncode == 0
    arc = env.load("arcs")["arcs"][0]
    assert arc["status"] == "closed" and arc["closed_turn"] == 9
    assert arc["retro"] == {"best": "the vote", "drag": "the walk", "wins": "an ally", "spotlight": "Mio led", "threads_closed": "none",
                            "clues_found": 2, "clues_placed": 4, "turns_used": 7, "budget": 10, "weakest": "slow middle", "notes": "ok"}
    assert env.op("arc-close", "A1", "--best", "x", turn=9).returncode == 4  # already closed
    assert "weakest: slow middle" in env.ok("plan-brief") and "A1 [closed]" in env.ok("plan-brief")
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(set_pieces=["a chase"])))
    env.ok("arc-approve", "A2", "--lines-checked")
    assert env.op("arc-close", "A2", "--status", "set_aside", "--notes", "dropped before it started", turn=9).returncode == 0
    assert env.load("arcs")["arcs"][1]["status"] == "set_aside" and env.load("arcs")["arcs"][1]["retro"]["turns_used"] == 0


def test_snapshots_cover_arcs_and_a_missing_file(env):
    env.advance(2)
    prompt = env.write("prompt.txt", SAYS)
    # a snapshot taken when arcs.json did not exist: undo-turn removes the file again
    p = {"turn": 3, "ops": [], "turn_log": {"inputs": "i", "summary": "s"}}
    env.ok("session-zero", "--tone", "x")
    (env.data / "arcs.json").unlink()
    assert env.run("commit-turn", "--prompt", prompt, "--payload", env.write("p.json", json.dumps(p))).returncode == 0
    assert not (env.data / "arcs.json").exists() and not (env.data / ".snapshots" / "before-turn-3" / "arcs.json").exists()
    env.ok("session-zero", "--tone", "after")
    assert env.run("undo-turn", 3).returncode == 0
    assert not (env.data / "arcs.json").exists() and env.load("state")["turn"] == 2
    # with a file: a turn that changes it is rewound with the rest
    env.ok("session-zero", "--tone", "before")
    p = {"turn": 3, "ops": [{"op": "pc-thread", "args": {"text": "went back to the cart"}, "evidence": "e"}], "turn_log": {"inputs": "i", "summary": "s"}}
    assert env.run("commit-turn", "--prompt", prompt, "--payload", env.write("p.json", json.dumps(p))).returncode == 0
    assert len(env.load("arcs")["pc_threads"]) == 1 and (env.data / ".snapshots" / "before-turn-3" / "arcs.json").exists()
    assert env.run("undo-turn", 3).returncode == 0 and env.load("arcs")["pc_threads"] == [] and env.load("arcs")["session_zero"]["tone"] == "before"
    # record restores arcs.json when a later op fails
    before = (env.data / "arcs.json").read_bytes()
    p["turn_log"]["prompt"] = SAYS
    r = env.run("record", env.write("r.json", json.dumps(p)), "--fail-after", 1)
    assert r.returncode == 9 and (env.data / "arcs.json").read_bytes() == before


def test_verify_data_checks_the_arcs_file(env):
    env.planned(approve=False)
    a = env.load("arcs")
    a["arcs"].append(copy.deepcopy(a["arcs"][0]))
    env.save_json("arcs", a)
    assert env.run("wrap-up").returncode == 1 and "appears twice" in env.run("wrap-up").stderr
    a["arcs"][1]["id"] = "A2"
    a["arcs"][0]["status"] = a["arcs"][1]["status"] = "active"
    env.save_json("arcs", a)
    assert "more than one active arc" in env.run("wrap-up").stderr
    a["arcs"][1]["status"] = "nonsense"
    env.save_json("arcs", a)
    assert "status must be one of" in env.run("wrap-up").stderr


# ---- the planner page ---------------------------------------------------------------
def page(env, name="page.html"):
    r = env.run("planner-page", "--out", env.tmp / name)
    return r, (env.tmp / name)


def test_planner_page_shows_shared_and_hides_everything_else(env):
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore", "--pillars", "combat=1,social=3",
           "--ending-hope", "bittersweet")
    env.ok("act-plan", 1, "--file", env.write("act.json", json.dumps(ACT)))
    env.ok("act-approve", 1)
    env.advance(3)
    env.planned()
    env.op("arc-start", "A1", turn=3)
    env.advance(5)
    env.op("arc-move", "A1", "Lender", 1, turn=5)
    env.op("pc-thread", "went back to the rota drawer three times", turn=5)
    env.op("arc-deviation", "A1", "the inspection moved into the kitchen", turn=5)
    r, f = page(env)
    assert r.returncode == 0, r.stderr
    html = f.read_text(encoding="utf-8")
    assert html.startswith("<title>Class 2B Arc Planner</title>") and "<!doctype" not in html.lower() and "<html" not in html and "<body" not in html
    assert "<script" not in html and "localStorage" not in html
    for shown in ("Who Holds the Keys", "Can you earn the house&#x27;s trust", "Wry and warm", "a tense house meeting", "Aiko Tanaka", "social",
                  "a staff ally", "you covered a chore", "the inspection moved into the kitchen", "Move-In", "Who do you become?",
                  "2 of 10 turns", "no harm to kids", "gore", "bittersweet", "Read-only", "Generated at turn 5"):
        assert shown in html, shown
    for hidden in ("glass lantern", "Sōichi", "Tamaru", "polite broker", "a thick envelope", "A polite offer", "A housemate took the money",
                   "Mio's secret", "rota drawer", "three times", "keep it offscreen", "the inspector knows", "Day 6", "ladder", "He was demoted",
                   "It is a debt", "Nightshade", "loan shark"):
        assert hidden.lower() not in html.lower(), hidden
    # contract: tokens in light and both dark blocks, body background, fonts only from Google Fonts, no other external resources
    assert html.count("--accent:#2F6F8F") == 1 and html.count("--accent:#7DB4CF") == 2
    assert '@media (prefers-color-scheme:dark){:root:not([data-theme="light"])' in html and ':root[data-theme="dark"]' in html
    assert "body{margin:0;background:var(--bg);color:var(--fg)" in html and "text-wrap:balance" in html and "padding-inline:16px" in html
    assert set(re.findall(r"https?://[^\"'\s)]+", html)) == {m for m in re.findall(r"https?://[^\"'\s)]+", html) if m.startswith("https://fonts.googleapis.com/")}
    assert "<title>" in html and html.index("<title>") == 0 and html.index("<style>") > html.index("</title>")


def test_planner_page_empty_state_and_escaping(env):
    r, f = page(env)
    assert r.returncode == 0
    html = f.read_text(encoding="utf-8")
    assert "No arc planned yet. Say &ldquo;plan the arc&rdquo; in chat." in html and "No pitch for this act yet" in html and "Not recorded yet" in html
    env.planned(lambda c: c["shared"].update(title="<script>alert(1)</script>", tone="a & b <i>"), approve=False)
    env.ok("arc-approve", "A1", "--lines-checked")
    html = page(env)[1].read_text(encoding="utf-8")
    assert "<script>alert" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html and "a &amp; b &lt;i&gt;" in html
    assert "Coming up" in html and "Approved" in html


def test_planner_page_blind_arc_shows_only_title_promise_tone(env):
    env.advance(2)
    env.ok("arc-plan", "--file", env.write("blind.json", json.dumps({**CHARTER, "blind": True})))
    env.ok("arc-approve", "A1", "--lines-checked")
    env.op("arc-start", "A1", turn=2)
    env.advance(4)
    html = page(env)[1].read_text(encoding="utf-8")
    for shown in ("Who Holds the Keys", "Can you earn the house&#x27;s trust", "Wry and warm", "2 of 10 turns", "Blind arc"):
        assert shown in html, shown
    for hidden in ("a tense house meeting", "An inspection nobody can move", "A quiet squeeze", "a staff ally", "Bittersweet", "the repair shop", "a scratched-out name"):
        assert hidden not in html, hidden
    assert "shared fields only" in env.ok("arc", "--shared") and "An inspection" not in env.ok("arc", "--shared")


def test_planner_page_refuses_when_a_hidden_term_leaks(env):
    env.planned(lambda c: c["shared"].update(premise="Watch for the glass lantern in the hall."))
    out = env.tmp / "leaky.html"
    r = env.run("planner-page", "--out", out)
    assert r.returncode == 4 and "glass lantern" in r.stderr and not out.exists()
    # the antagonist's name is hidden until it appears in shared fields, is in play or has made contact
    env.ok("arc-plan", "--id", "A1", "--file", env.charter(lambda c: c["shared"].update(premise="A man called Sōichi Tamaru will come.")))
    r = env.run("planner-page", "--out", out)
    assert r.returncode == 0 and "Tamaru" in out.read_text(encoding="utf-8")  # named in the shared fields: the user already knows
    env.ok("arc-plan", "--id", "A1", "--file", env.charter(lambda c: c["shared"].update(premise="Fine.")))
    out.unlink()
    env.advance(2)
    env.op("arc-start", "A1", turn=2)
    env.ok("arc-contact", "A1", "--turn", 2, "--evidence", "the broker stopped Aiko at the gate")  # on screen: the name is public
    env.ok("arc-plan", "--id", "A1", "--file", env.charter(lambda c: c["shared"].update(tone="Tamaru at the gate")))
    assert env.run("planner-page", "--out", out).returncode == 0
    # a still-hidden ladder term leaks too
    env.ok("arc-plan", "--id", "A1", "--file", env.charter(lambda c: c["shared"].update(tone="Wry", premise="Someone owes a loan shark money.")))
    out.unlink(missing_ok=True)
    r = env.run("planner-page", "--out", out)
    assert r.returncode == 4 and not out.exists()
    assert env.run("planner-page").returncode == 1  # nothing to do


def test_planner_page_set_url_validates_and_stores(env):
    assert env.run("planner-page", "--set-url", "not a url").returncode == 2
    env.ok("planner-page", "--set-url", "https://claude.ai/artifact/xyz")
    assert env.load("arcs")["page_url"] == "https://claude.ai/artifact/xyz"
    assert not (env.tmp / "x.html").exists()


def test_the_real_data_dir_is_never_written(env):
    real = REAL_DATA / "arcs.json"
    before = real.read_bytes() if real.exists() else None  # the live campaign may have a plan by now
    env.ok("session-zero", "--tone", "scratch only")
    env.ok("act-plan", 1, "--file", env.write("act.json", json.dumps(ACT)))
    assert (real.read_bytes() if real.exists() else None) == before


# ---- preflight -----------------------------------------------------------------
def test_preflight_fails_until_ready_and_lists_the_act_checklist(env):
    r = env.run("preflight")
    assert r.returncode == 4
    assert "FAIL session zero not recorded" in r.stdout and "FAIL act 1: no pitch" in r.stdout
    assert "Preflight: 2 FAIL" in env.ok("resume")
    env.ok("session-zero", "--tone", "warm", "--players", "2")
    assert env.load("arcs")["session_zero"]["players"] == 2 and "players (PCs at the table): 2" in env.ok("session-zero")
    assert env.run("session-zero", "--players", "0").returncode == 2
    act = copy.deepcopy(ACT)
    op = {"op": "act-deviation", "args": {"n": 1, "text": "Beats run on the clock."}, "evidence": "planning session"}
    act["hidden"].update({"checklist": ["Every team fights all three bouts."], "pending_ops": [op]})
    env.ok("act-plan", 1, "--file", env.write("act.json", json.dumps(act)))
    out = env.run("preflight").stdout
    assert "FAIL act 1: pitch is draft" in out and "FAIL 1 of 2 PC sheets recorded" in out
    assert "[ ] Every team fights all three bouts." in out and '"Beats run on the clock."' in out
    env.ok("act-approve", 1)
    env.ok("pc-add", "Ren Ito", "--player", "Kai", "--room", "river-bedroom", "--turn", "1", "--evidence", "test", "--power", "none yet")
    r = env.run("preflight")
    assert r.returncode == 0 and "RESULT: 0 FAIL" in r.stdout
    assert "PC Ren Ito: sheet lacks pronouns, background" in r.stdout and "no arc charter for this act yet" in r.stdout
    env.ok("act-deviation", 1, "Beats run on the clock.", "--turn", "1", "--evidence", "planning session")
    assert "deferred op" not in env.ok("preflight")  # done once the deviation is on the pitch
    bad = copy.deepcopy(act)
    bad["hidden"]["pending_ops"] = ["not an op"]
    assert env.run("act-plan", 1, "--file", env.write("bad.json", json.dumps(bad))).returncode == 2


# ---- unrefined charters, and one preflight line per arc ----------------------------
def test_arc_approve_refuses_open_refine_items(env):
    env.planned(lambda c: c["hidden"].update(refine=["pc_tests: one per PC", "echoes: fill from play"]), approve=False)
    r = env.run("arc-approve", "A1", "--lines-checked")
    assert r.returncode == 4 and 'hidden.refine has 2 open item(s): pc_tests: one per PC; echoes: fill from play' in r.stderr, r.stderr
    assert env.load("arcs")["arcs"][0]["status"] == "draft"  # a refusal writes nothing
    f = env.run("arc-approve", "A1", "--lines-checked", "--force")
    arc = env.load("arcs")["arcs"][0]
    assert f.returncode == 0 and arc["status"] == "approved" and any("hidden.refine has 2 open item(s)" in x for x in arc["approved_forced"])
    env.planned(lambda c: (c["hidden"].update(refine=[]), c["shared"].update(set_pieces=["a chase"])), approve=False)  # an empty refine list is ready
    assert env.run("arc-approve", "A2", "--lines-checked").returncode == 0


@pytest.mark.parametrize("mutate,field", [
    (lambda c: c["shared"].update(backstory_hooks=["PENDING PC SHEETS: one hook per PC"]), "backstory_hooks"),
    (lambda c: c["shared"].update(echoes=["fine", "PENDING PLAY: fill from the last arc"]), "echoes"),
    (lambda c: c["shared"].update(tone="PENDING tone"), "tone"),
])
def test_arc_approve_refuses_a_pending_placeholder(env, mutate, field):
    env.planned(mutate, approve=False)
    r = env.run("arc-approve", "A1", "--lines-checked")
    assert r.returncode == 4 and f"shared.{field} still holds a PENDING placeholder" in r.stderr, r.stderr
    assert r.stderr.count("PENDING placeholder") == 1  # one problem per field
    assert env.load("arcs")["arcs"][0]["status"] == "draft"
    f = env.run("arc-approve", "A1", "--lines-checked", "--force")
    assert f.returncode == 0 and env.load("arcs")["arcs"][0]["approved_forced"]


def test_arc_approve_refuses_while_pc_sheets_are_missing(env):
    env.ok("session-zero", "--tone", "warm", "--players", "2")  # the fixture records one PC
    env.planned(approve=False)
    r = env.run("arc-approve", "A1", "--lines-checked")
    assert r.returncode == 4 and "only 1 of 2 PC sheets recorded: pc_tests cannot be checked yet (pc-add)" in r.stderr, r.stderr
    env.ok("pc-add", "Ren Ito", "--player", "Kai", "--room", "river-bedroom", "--turn", "1", "--evidence", "test", "--power", "none yet")
    env.ok("arc-plan", "--file", env.write("t.json", json.dumps({"shared": {"pc_tests": {"Aiko Tanaka": "social", "Ren Ito": "combat"}},
                                                               "hidden": {"pc_test_situations": {"Aiko Tanaka": "x", "Ren Ito": "y"}}})), "--id", "A1")
    assert env.run("arc-approve", "A1", "--lines-checked").returncode == 0


@pytest.mark.parametrize("hidden", [{"refine": "backstory_hooks"}, {"refine": [1, 2]}, {"refine": {"a": "b"}}])
def test_plans_refuse_a_refine_that_is_not_a_list_of_strings(env, hidden):
    bad = env.write("bad.json", json.dumps({"hidden": hidden}))
    for cmd in (("arc-plan", "--file", bad), ("act-plan", 1, "--file", bad)):
        r = env.run(*cmd)
        assert r.returncode == 2 and "hidden.refine must be a list of strings" in r.stderr, (cmd, r.stderr)


def flat(out):
    return " ".join(out.split())


def test_preflight_lists_every_arc_of_the_act(env):
    assert "no arc charter for this act yet" in flat(env.run("preflight").stdout)
    env.ok("arc-plan", "--file", env.charter(lambda c: c["hidden"].update(refine=["backstory_hooks: one per PC", "pc_tests: one per PC"])))
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(title="Second")))
    out = flat(env.run("preflight").stdout)
    assert "WARN arc A1 is a draft: refine first: backstory_hooks: one per PC; pc_tests: one per PC" in out
    assert "WARN arc A2 is a draft" in out and "no arc charter for this act yet" not in out
    assert out.index("arc A1 is a draft") < out.index("arc A2 is a draft")  # id order
    env.ok("arc-approve", "A1", "--lines-checked", "--force")
    env.ok("arc-approve", "A2", "--lines-checked", "--force")
    out = flat(env.run("preflight").stdout)
    assert "OK arc A1 is approved: next to start (arc-start when its first pressure shows)" in out
    assert "OK arc A2 is approved (starts when the previous arc closes)" in out


def test_preflight_shows_the_active_arc_and_a_waiting_one(env):
    env.active(start=2)
    env.ok("arc-plan", "--file", env.charter(lambda c: c["shared"].update(title="Second")))
    env.ok("arc-approve", "A2", "--lines-checked", "--force")
    out = flat(env.run("preflight").stdout)
    assert re.search(r"OK arc A1 is active \(turn \d+ of budget 10\)", out), out
    assert "OK arc A2 is approved (starts when the previous arc closes)" in out
