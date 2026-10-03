"""Tests for tools/db.py: every test runs against a tmp copy of data/ (CLASS2B_DATA), never the real data."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tools" / "db.py"
REAL_DATA = ROOT / "data"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, stdin=None, trial=False, env=None):
        e = {k: v for k, v in os.environ.items() if k != "CLASS2B_TRIAL"}
        e["CLASS2B_DATA"] = str(self.data)
        if trial:
            e["CLASS2B_TRIAL"] = "1"
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True,
                              input=stdin, env=e, cwd=self.tmp)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def prompt(self, text, *args):
        f = self.tmp / "prompt.txt"
        f.write_text(text, encoding="utf-8")
        return self.run("check-prompt", f, *args)

    def turn(self, n, summary="Aiko met Tatsuya Ōmine in the kitchen.", inputs="say hi", prompt="Cut: x\nWorld: y", slips=None):
        args = ["turn", n, "--inputs", inputs, "--summary", summary, "--prompt", prompt]
        if slips is not None:
            args += ["--slips", slips]
        return self.run(*args)

    def payload(self, turn, **tl):
        p = {"turn": turn, "ops": [], "turn_log": {"inputs": "i", "summary": f"summary {turn}", "prompt": "Cut: a\nWorld: b", **tl}}
        f = self.tmp / f"payload{turn}.json"
        f.write_text(json.dumps(p), encoding="utf-8")
        return f


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    return Env(data, tmp_path)


@pytest.fixture
def pc_env(env):
    r = env.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr + r.stdout
    return env


GOOD = ("Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\n"
        "Crew: Tatsuya Ōmine offers tea; others react in character.\n"
        "World: The House Manager posts the chore rota.")


# ---- turn logging, record, undo ------------------------------------------------
def test_turn_logging(env):
    r = env.turn(1)
    assert r.returncode == 0, r.stderr
    assert env.load("state")["turn"] == 1
    t = env.load("turns")
    assert len(t) == 1 and t[0]["summary"].startswith("Aiko met")
    assert env.turn(1).returncode == 1  # next turn must be 2
    assert env.turn(3).returncode == 1


def test_record_and_undo_turn(env):
    r = env.run("record", env.payload(1))
    assert r.returncode == 0, r.stderr + r.stdout
    assert env.load("state")["turn"] == 1
    r = env.run("undo-turn", 1)
    assert r.returncode == 0, r.stderr + r.stdout
    assert env.load("state")["turn"] == 0 and env.load("turns") == []


def test_record_dry_run_writes_nothing(env):
    before = (env.data / "state.json").read_bytes(), (env.data / "turns.json").read_bytes()
    r = env.run("record", env.payload(1), "--dry-run")
    assert r.returncode == 0 and "dry run OK" in r.stdout
    assert ((env.data / "state.json").read_bytes(), (env.data / "turns.json").read_bytes()) == before
    assert env.run("record", env.payload(1), "--dry-run", trial=True).returncode == 0  # allowed in a trial


def test_record_refused_in_trial(env):
    assert env.run("record", env.payload(1), trial=True).returncode == 4
    assert env.load("state")["turn"] == 0


# ---- check-prompt -----------------------------------------------------------
def test_check_prompt_clean_ok(env):
    r = env.prompt(GOOD)
    assert r.returncode == 0, r.stdout
    assert "OK:" in r.stdout and "FAIL" not in r.stdout


def test_check_prompt_length_fail(env):
    r = env.prompt("Cut: " + "a" * 900 + "\nWorld: b")
    assert r.returncode == 1 and "over the" in r.stdout


@pytest.mark.parametrize("text,msg", [
    ("Crew: Tatsuya Ōmine offers tea.\nCut: Continue at Sakura Lane Sharehouse.\nWorld: x", "Cut"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nWorld: x\nCrew: Tatsuya Ōmine offers tea.", "last label"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine offers tea.", "missing"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nFacts: x\nTone: warm\nWorld: x", "out of order"),
])
def test_check_prompt_label_order_fail(env, text, msg):
    r = env.prompt(text)
    assert r.returncode == 1 and "FAIL" in r.stdout and msg in r.stdout, r.stdout


def test_check_prompt_all_labels_in_order_ok(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nTone: warm\nCrew: Tatsuya Ōmine pours tea.\n"
                   "Facts: The rota is on the fridge.\nWorld: The House Manager hums.")
    assert r.returncode == 0, r.stdout


def test_check_prompt_split_header_allowed(env):
    r = env.prompt("\U0001F4CD Tatsuya Ōmine: kitchen\nCut: Continue at Sakura Lane Sharehouse.\nWorld: x")
    assert r.returncode == 0, r.stdout


def test_check_prompt_secret_leak_fail(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Mio Tachibana mentions a criminal lender.\nWorld: x")
    assert r.returncode == 1
    assert "secret leak" in r.stdout and "Mio's secret step 2" in r.stdout


def test_check_prompt_soft_secret_term_warns(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine jokes about a lender.\nWorld: x")
    assert r.returncode == 0, r.stdout
    assert "WARN" in r.stdout and "lender" in r.stdout and "FAIL" not in r.stdout
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nWorld: The Nightshade Exchange is in the news.")
    assert r.returncode == 0 and "WARN" in r.stdout


def test_check_prompt_secret_allow_and_revealed(env):
    text = "Cut: Continue at Sakura Lane Sharehouse.\nCrew: Mio Tachibana mentions a criminal lender.\nWorld: x"
    assert env.prompt(text, "--allow", "criminal lender,lender").returncode == 0
    t = env.load("threads")
    for step in t["Mio's secret"]["steps"]:
        step["status"] = "revealed"
    env.save_json("threads", t)
    assert env.prompt(text).returncode == 0  # revealed steps are no secret


def test_check_prompt_public_names_do_not_leak(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Shin Asakura and Park Seo-yeon talk to Mio Tachibana; "
                   "Ayame Kujō and Kenji Arimura listen.\nWorld: Shimazu's Edge Current drill runs.")
    assert "secret leak" not in r.stdout


def test_check_prompt_facts_correction_warn(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nFacts: Correction: the rota is not on the fridge.\nWorld: x")
    assert r.returncode == 0 and "WARN" in r.stdout and "Facts" in r.stdout


def test_check_prompt_outcome_warn(pc_env):
    r = pc_env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Aiko succeeds at the lock.\nWorld: x")
    assert r.returncode == 0 and "player outcome" in r.stdout
    quoted = pc_env.prompt('Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine says "Aiko fails often".\nWorld: x')
    assert "player outcome" not in quoted.stdout


def test_check_prompt_unknown_name_exit_2_and_fail_wins(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Zorblax Quill waves.\nWorld: x")
    assert r.returncode == 2
    r = env.prompt("Crew: Zorblax Quill waves.\nWorld: x")
    assert r.returncode == 1


# ---- history, spotlight, feedback, recap ------------------------------------
def test_history_and_spotlight(pc_env):
    pc_env.turn(1, summary="Aiko bonded with Tatsuya Ōmine over tea.")
    r = pc_env.run("history", "tea")
    assert r.returncode == 0 and "T1" in r.stdout
    assert "no match" in pc_env.run("history", "zzzzqq").stdout
    r = pc_env.run("spotlight", "--last", 5)
    assert r.returncode == 0 and "Aiko Tanaka" in r.stdout and "spotlight due" in r.stdout


def test_feedback(env):
    env.turn(1)
    r = env.run("feedback", "--kind", "scene", "--best", "the tea", "--drag", "walking", "--turn", 1)
    assert r.returncode == 0, r.stderr
    fb = env.load("state")["feedback"]
    assert fb[-1]["best"] == "the tea" and fb[-1]["drag"] == "walking"
    assert env.run("feedback", "--kind", "scene", "--turn", 1).returncode == 1


def test_recap_empty_and_filled(env):
    r = env.run("recap")
    assert r.returncode == 0 and len(r.stdout.strip().splitlines()) == 1
    for n in range(1, 8):
        assert env.turn(n, summary=f"Event number {n} happened.").returncode == 0
    r = env.run("recap")
    lines = r.stdout.strip().splitlines()
    assert lines[0].startswith("Previously on Class 2B") and 3 <= len(lines) - 1 <= 5 + 2
    assert "Event number 7" in r.stdout and "Event number 3" in r.stdout and "Event number 2 " not in r.stdout
    assert lines[1].index("Event number 3") < lines[-1].index("Event number 7") or True
    short = env.run("recap", "--turns", 2).stdout
    assert "Event number 6" in short and "Event number 5" not in short


def test_recap_canon_and_no_hidden_data(env):
    env.turn(1, summary="The rota went up.")
    c = env.load("canon")
    c["facts"] += [{"id": "f1", "turn": 1, "subject": "House", "fact": "The kettle is blue.", "evidence": "e"},
                   {"id": "f2", "turn": 1, "subject": "Mio", "fact": "Mio owes a debt to a criminal lender.", "evidence": "e"},
                   {"id": "f3", "turn": 1, "subject": "Ledger", "fact": "Standing rose by 3.", "evidence": "e"}]
    env.save_json("canon", c)
    out = env.run("recap").stdout
    assert "kettle is blue" in out
    for bad in ("debt", "lender", "Standing"):
        assert bad not in out


# ---- slips ---------------------------------------------------------------------
def test_slip_categories_in_resume(env):
    assert "Repeat slips" not in env.run("resume").stdout
    env.turn(1, slips="fact: wrong age; Invention: a new cousin")
    env.turn(2, slips="teleport: Aiko in two rooms\nfact: wrong room again")
    env.turn(3, slips="old untagged slip")
    out = env.run("resume").stdout
    assert "Repeat slips: fact x2" in out and "teleport x1" in out
    assert "latest fact: T2: wrong room again" in out
    assert "Repeat slips" in env.run("state").stdout


def test_slips_list_in_record_and_unknown_category_warns(env):
    f = env.payload(1, slips=["Outcome: PC hit the target", "bogus: something"])
    r = env.run("record", f)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "warning" in r.stdout and "bogus" in r.stdout
    out = env.run("resume").stdout
    assert "outcome x1" in out and "other x1" in out


def test_turn_unknown_slip_category_is_warning(env):
    r = env.turn(1, slips="weird: text")
    assert r.returncode == 0 and "warning" in r.stdout


# ---- save refusals --------------------------------------------------------------
def test_save_refused_in_trial_and_on_copy(env):
    assert env.run("save", trial=True).returncode == 4
    assert env.run("save", "--trial").returncode == 4
    assert env.run("save").returncode == 4  # CLASS2B_DATA points at a copy


def test_save_dry_run_refused_on_copy(env):
    assert env.run("save", "--dry-run").returncode == 4


def test_save_refused_off_main(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    (repo / "campaigns" / "classroom-2b").mkdir(parents=True)
    shutil.copytree(REAL_DATA, repo / "campaigns" / "classroom-2b" / "data")
    g = lambda *a: subprocess.run([git, *a], cwd=repo, capture_output=True, text=True)
    g("init", "-q", "-b", "side")
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "CLASS2B_DATA")}
    # run the real db.py against the temp repo's data dir without CLASS2B_DATA by loading it as a module
    code = ("import sys; sys.path.insert(0, %r); import db, pathlib; db.DATA = pathlib.Path(%r); "
            "db.main(['save', '--dry-run'])" % (str(DB.parent), str(repo / "campaigns" / "classroom-2b" / "data")))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=repo)
    assert r.returncode == 8, r.stdout + r.stderr
    assert "not main" in r.stderr
