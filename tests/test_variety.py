"""The variety tracker (SCN-1, SCN-7, D10): scene-start --kind, the finished-scene history, the three-of-a-kind warning, the one
variety check in prep, plan-brief's scene mix and verify_data. Every test runs on a tmp copy of the classroom-2b data
(VOYAGE_DATA), never the real data. No test asserts on the first line of an output: a campaign-name header line may come first."""
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
GOOD = ("Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\n"
        "Crew: Tatsuya Ōmine offers tea; others react in character.\n"
        "World: The House Manager posts the chore rota.")
KINDS = "fight|talk|explore|mystery|downtime"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": "classroom-2b", "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def mutable(self):
        return {n: (self.data / f"{n}.json").read_bytes() for n in ("state", "canon", "quests", "turns", "cast")}

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}

    def turn(self, n, inputs="Aiko chats with the housemates in the kitchen", cut="Continue at the kitchen."):
        self.ok("turn", n, "--inputs", inputs, "--summary", f"Turn {n}.", "--prompt", f"Cut: {cut}\nWorld: Quiet.")

    def start(self, name, kind=None, turn=1, budget=3):
        args = ["scene-start", name, "--budget", budget, "--turn", turn, "--evidence", "test"]
        return self.ok(*args, *(["--kind", kind] if kind else []))

    def scene(self, name, kind=None, turn=1):
        """Open and close a scene; returns the scene-start output."""
        out = self.start(name, kind, turn)
        self.ok("scene-end", "--turn", turn)
        return out

    def payload(self, ops, turn):
        p = {"turn": turn, "ops": ops, "turn_log": {"inputs": "i", "summary": f"summary {turn}", "prompt": "Cut: a\nWorld: b"}}
        return self.write(f"payload{turn}.json", json.dumps(p))

    def commit(self, ops, turn, *args):
        p = {"turn": turn, "ops": ops, "turn_log": {"inputs": "i", "summary": f"summary {turn}"}}
        return self.run("commit-turn", "--prompt", self.write("prompt.txt", GOOD), "--payload",
                        self.write("cpayload.json", json.dumps(p)), *args)

    def prep_checklist(self):
        out = self.ok("prep")
        return out[out.index("LIVE CHECKLIST"):]


def start_op(name, kind=None, budget=3):
    args = {"name": name, "budget": budget}
    if kind:
        args["kind"] = kind
    return {"op": "scene-start", "args": args, "evidence": "e"}


END_OP = {"op": "scene-end", "args": {}}


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    e = Env(data, tmp_path)
    e.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test")
    return e


# ---- 1. scene-start --kind and the history of finished scenes ------------------------------------
def test_scene_start_stores_the_kind_on_the_scene_and_shows_it(env):
    env.turn(1)
    env.turn(2)
    out = env.start("Kitchen talk", "talk", turn=3)
    assert "kind talk" in out and "WARNING" not in out
    assert env.load("state")["scene"]["kind"] == "talk"
    assert "kind: talk" in env.ok("prep")
    assert "(started turn 3, kind talk)" in env.ok("resume")


@pytest.mark.parametrize("kind", ["fight", "talk", "explore", "mystery", "downtime"])
def test_scene_start_takes_every_kind(env, kind):
    env.start("A scene", kind)
    assert env.load("state")["scene"]["kind"] == kind


def test_scene_start_refuses_an_unknown_kind_and_writes_nothing(env):
    before = env.hashes()
    r = env.run("scene-start", "Brawl", "--budget", 3, "--kind", "brawl", "--turn", 1, "--evidence", "e")
    assert r.returncode == 2 and "invalid choice" in r.stderr and "brawl" in r.stderr
    assert env.hashes() == before


def test_scene_start_without_a_kind_behaves_as_before(env):
    out = env.start("Plain scene")
    assert "kind" not in out and "WARNING" not in out
    sc = env.load("state")["scene"]
    assert "kind" not in sc and sc["name"] == "Plain scene" and sc["budget"] == 3
    line = next(ln for ln in env.ok("prep").splitlines() if ln.startswith('Scene "Plain scene"'))
    assert "kind" not in line
    env.ok("scene-end", "--turn", 4)
    st = env.load("state")
    assert st["scene"] is None
    assert st["scene_log"] == [{"name": "Plain scene", "start_turn": 1, "end_turn": 4}]  # the history keeps untagged scenes too


def test_scene_end_keeps_the_kind_and_the_start_and_end_turns(env):
    env.turn(1)
    env.start("The vault", "mystery", turn=2)
    env.turn(2)
    env.turn(3)
    env.ok("scene-end", "--turn", 3)
    env.start("Courtyard bout", "fight", turn=4)
    env.turn(4)
    env.ok("scene-end", "--turn", 4)
    st = env.load("state")
    assert st["scene_log"] == [{"name": "The vault", "kind": "mystery", "start_turn": 2, "end_turn": 3},
                               {"name": "Courtyard bout", "kind": "fight", "start_turn": 4, "end_turn": 4}]


def test_old_data_without_kinds_stays_valid(env):
    st = env.load("state")
    assert "scene_log" not in st and st["scene"] is None  # the real data has no history and no kinds
    assert "safe to close" in env.ok("wrap-up")
    env.start("No tag")
    assert "safe to close" in env.ok("wrap-up")  # an open scene without a kind
    env.ok("scene-end", "--turn", 2)
    assert "safe to close" in env.ok("wrap-up")  # a history entry without a kind


# ---- 2. the three-of-a-kind warning ---------------------------------------------------------------
def test_scene_start_warns_when_the_last_three_scenes_share_a_kind(env):
    assert "WARNING" not in env.scene("One", "fight")
    assert "WARNING" not in env.scene("Two", "fight")
    out = env.start("Three", "fight")
    warn = [ln for ln in out.splitlines() if "WARNING variety" in ln]
    assert len(warn) == 1 and "three fight scenes in a row" in warn[0]
    env.ok("scene-end", "--turn", 1)
    out = env.start("Four", "talk")  # the run is broken
    assert "WARNING" not in out


def test_a_different_kind_or_an_untagged_scene_breaks_the_run(env):
    env.scene("One", "fight")
    env.scene("Two", "talk")
    assert "WARNING" not in env.start("Three", "fight")  # fight, talk, fight
    env.ok("scene-end", "--turn", 1)
    env.scene("Four", None)  # untagged never counts as a kind
    env.scene("Five", "fight")
    assert "WARNING" not in env.start("Six", "fight")  # untagged, fight, fight
    env.ok("scene-end", "--turn", 1)
    env.scene("Seven", "downtime")
    env.scene("Eight", "downtime")
    assert "three downtime scenes in a row" in env.start("Nine", "downtime")  # every kind warns, downtime too


def test_record_surfaces_the_warning_and_a_payload_op_takes_the_kind(env):
    env.ok("record", env.payload([start_op("One", "talk")], 1))
    assert env.load("state")["scene"]["kind"] == "talk"
    env.ok("record", env.payload([END_OP, start_op("Two", "talk")], 2))
    out = env.ok("record", env.payload([END_OP, start_op("Three", "talk")], 3))
    assert "three talk scenes in a row" in out
    st = env.load("state")
    assert [x["name"] for x in st["scene_log"]] == ["One", "Two"] and st["scene"]["kind"] == "talk"
    assert st["scene_log"][0] == {"name": "One", "kind": "talk", "start_turn": 1, "end_turn": 2}  # end turn is the payload's turn


def test_prep_checklist_prints_one_variety_line_for_three_of_a_kind(env):
    assert "variety flags" not in env.prep_checklist()
    env.scene("One", "mystery")
    env.scene("Two", "mystery")
    assert "variety flags" not in env.prep_checklist()
    env.start("Three", "mystery")
    chk = env.prep_checklist()
    assert chk.count("three mystery scenes in a row") == 1
    assert "variety flags (1): three mystery scenes in a row" in chk
    assert "one-line check" not in chk  # one flag alone is not the trigger
    env.ok("scene-end", "--turn", 1)
    assert "three mystery scenes in a row" in env.prep_checklist()  # still the last three, with no scene open
    env.start("Four", "explore")
    assert "variety flags" not in env.prep_checklist()


# ---- 3. one variety check: the boredom flags and the kind run -------------------------------------
def test_one_drag_flag_counts_as_one_and_adding_the_kind_run_makes_two(env):
    for n in range(1, 11):
        env.turn(n)
    assert "variety flags" not in env.prep_checklist()
    env.ok("feedback", "--kind", "scene", "--drag", "the waiting", "--turn", 10)
    chk = env.prep_checklist()
    assert "variety flags (1): drag in the latest feedback" in chk and "one-line check" not in chk
    for name in ("One", "Two", "Three"):
        env.start(name, "fight", turn=10)
        if name != "Three":
            env.ok("scene-end", "--turn", 10)
    chk = env.prep_checklist()
    assert "variety flags (2): drag in the latest feedback, three fight scenes in a row" in chk
    assert "two or more variety flags: one-line check with the user; next pressure card adds variety" in chk
    assert "boredom" not in chk


def test_every_flag_keeps_its_behaviour_inside_the_variety_check(env):
    for n in range(1, 8):
        env.turn(n, inputs="a" * 120)
    for n in (8, 9):
        env.turn(n, inputs="ok", cut="Skip to the evening.")
    assert "variety flags" not in env.prep_checklist()  # nine turns: the boredom flags need ten
    env.turn(10, inputs="ok")
    chk = env.prep_checklist()
    assert "variety flags (2): shorter inputs, repeated skips" in chk and "two or more variety flags: one-line check with the user" in chk
    env.ok("feedback", "--kind", "scene", "--drag", "the waiting", "--turn", 10)
    assert "variety flags (3): shorter inputs, repeated skips, drag in the latest feedback" in env.prep_checklist()
    for name in ("One", "Two", "Three"):
        env.start(name, "talk", turn=10)
        if name != "Three":
            env.ok("scene-end", "--turn", 10)
    assert "variety flags (4): shorter inputs, repeated skips, drag in the latest feedback, three talk scenes in a row" in env.prep_checklist()


# ---- 4. plan-brief: the mix of kinds against session zero's pillars --------------------------------
def test_plan_brief_maps_the_kinds_to_the_pillars_and_lists_downtime_and_untagged(env):
    env.turn(1)
    env.scene("A", "fight")
    env.scene("B", "talk")
    env.scene("C", "talk")
    env.scene("D", "downtime")
    env.scene("E", None)
    env.start("F", "explore")  # the open scene counts too
    out = env.ok("plan-brief")
    assert ("SCENE MIX since act 1 began (turn 1), 6 scenes: combat (fight) 1 [session zero 3], social (talk) 2 [session zero 3], "
            "exploration (explore) 1 [session zero 1], mystery (mystery) 0 [session zero 2]") in out
    assert "downtime 1 (on its own); untagged 1" in out
    lines = out.splitlines()
    zero = next(i for i, ln in enumerate(lines) if "play styles (0 to 3)" in ln)
    assert next(i for i, ln in enumerate(lines) if ln.startswith("SCENE MIX")) > zero  # printed with session zero's pillars
    assert next(i for i, ln in enumerate(lines) if ln.startswith("SCENE MIX")) - zero <= 4


def test_plan_brief_counts_only_the_scenes_started_since_the_current_act_began(env):
    env.turn(1)
    env.scene("Old one", "fight", turn=1)
    env.turn(2)
    env.scene("Old two", "fight", turn=2)
    env.ok("time", "--day", 8, "--turn", 2, "--evidence", "a week passes")  # act 2 starts on day 8
    env.turn(3)
    env.scene("New talk", "talk", turn=3)
    env.start("New mystery", "mystery", turn=4)
    out = env.ok("plan-brief")
    assert "SCENE MIX since act 2 began (turn 3), 2 scenes: combat (fight) 0 [session zero 3], social (talk) 1 [session zero 3]" in out
    assert "mystery (mystery) 1 [session zero 2]" in out


def test_plan_brief_says_so_when_no_scene_is_tagged_yet(env):
    env.turn(1)
    out = env.ok("plan-brief")
    assert "SCENE MIX since act 1 began (turn 1), 0 scenes (tag each scene: scene-start --kind " + KINDS + ")" in out


def test_plan_brief_falls_back_to_the_last_ten_scenes_when_the_act_start_is_unknown(env):
    st = env.load("state")  # no turn is logged, so the act's first turn cannot be told
    st["scene_log"] = [{"name": f"S{i}", "kind": "mystery" if i < 2 else "talk", "start_turn": i + 1, "end_turn": i + 1} for i in range(12)]
    env.save_json("state", st)
    out = env.ok("plan-brief")
    assert "SCENE MIX, the last 10 scenes at most (the act's first turn is unknown), 10 scenes" in out
    assert "social (talk) 10 [session zero 3]" in out and "mystery (mystery) 0 [session zero 2]" in out


def test_plan_brief_names_session_zero_styles_that_have_no_scene_tag(env):
    arcs = env.load("arcs")
    arcs["session_zero"]["pillars"]["romance"] = 2
    env.save_json("arcs", arcs)
    env.turn(1)
    env.scene("A", "talk")
    assert "session-zero play styles with no scene tag: romance 2" in env.ok("plan-brief")


# ---- 5. verify_data -------------------------------------------------------------------------------
def test_verify_accepts_the_new_fields_when_well_formed(env):
    env.scene("A", "fight")
    env.start("B", "downtime")
    assert "safe to close" in env.ok("wrap-up")


def test_verify_rejects_an_unknown_kind_and_malformed_history_and_lists_every_problem(env):
    env.start("Open one", "talk")
    st = env.load("state")
    st["scene"]["kind"] = "brawl"
    st["scene_log"] = [{"name": "A", "kind": "chase", "start_turn": 1, "end_turn": 2},
                       {"name": "", "kind": "fight"},
                       {"name": "C", "start_turn": "one", "end_turn": 2.5},
                       "not an object"]
    env.save_json("state", st)
    r = env.run("wrap-up")
    assert r.returncode == 1 and "not safe to close" in r.stderr
    for part in ("state.json scene: kind 'brawl' is not one of fight, talk, explore, mystery, downtime",
                 "scene_log #1: kind 'chase' is not one of fight, talk, explore, mystery, downtime",
                 "scene_log #2: name must be non-empty text", "scene_log #3: start_turn must be an integer",
                 "scene_log #3: end_turn must be an integer", "scene_log #4: must be an object"):
        assert part in r.stderr, part
    st["scene_log"] = {"A": 1}
    env.save_json("state", st)
    assert "scene_log must be a list" in env.run("wrap-up").stderr


def test_record_rolls_back_when_the_data_carries_an_unknown_kind(env):
    st = env.load("state")
    st["scene_log"] = [{"name": "A", "kind": "chase", "start_turn": 1, "end_turn": 1}]
    env.save_json("state", st)
    before = env.mutable()
    r = env.run("record", env.payload([{"op": "question", "args": {"text": "Why?"}, "evidence": "e"}], 1))
    assert r.returncode == 1 and "verification failed" in r.stderr and "Restored the pre-turn snapshot" in r.stderr
    assert env.mutable() == before


# ---- payloads: record and commit-turn ----------------------------------------------------------------
def test_record_refuses_an_unknown_kind_in_a_payload_and_writes_nothing(env):
    before = env.hashes()
    r = env.run("record", env.payload([start_op("Bad", "brawl")], 1))
    assert r.returncode != 0 and "Nothing applied" in r.stderr + r.stdout and "invalid choice" in r.stderr + r.stdout
    assert env.hashes() == before


def test_commit_turn_takes_the_kind_and_refuses_an_unknown_one(env):
    before = env.hashes()
    r = env.commit([start_op("Bad", "brawl")], 1)
    assert r.returncode == 2 and "invalid choice" in r.stdout and env.hashes() == before
    r = env.commit([start_op("Vault", "mystery")], 1)
    assert r.returncode == 0, r.stdout + r.stderr
    assert env.load("state")["scene"]["kind"] == "mystery"
    r = env.commit([END_OP], 2)
    assert r.returncode == 0, r.stdout + r.stderr
    assert env.load("state")["scene_log"] == [{"name": "Vault", "kind": "mystery", "start_turn": 1, "end_turn": 2}]


def test_a_payload_without_a_kind_still_records_the_old_scene_shape(env):
    r = env.ok("record", env.payload([start_op("Plain")], 1))
    assert "WARNING" not in r
    assert "kind" not in env.load("state")["scene"]
    env.ok("record", env.payload([END_OP], 2))
    assert env.load("state")["scene_log"] == [{"name": "Plain", "start_turn": 1, "end_turn": 2}]


def test_undo_turn_rewinds_the_kind_and_the_history(env):
    before = env.mutable()
    env.ok("record", env.payload([start_op("One", "fight")], 1))
    after_one = env.mutable()
    env.ok("record", env.payload([END_OP, start_op("Two", "talk")], 2))
    st = env.load("state")
    assert st["scene"]["kind"] == "talk" and len(st["scene_log"]) == 1
    env.ok("undo-turn", 2)
    assert env.mutable() == after_one
    st = env.load("state")
    assert st["scene"]["kind"] == "fight" and "scene_log" not in st
    env.ok("undo-turn", 1)
    assert env.mutable() == before
    st = env.load("state")
    assert st["scene"] is None and "scene_log" not in st
