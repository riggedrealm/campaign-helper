"""db.py support for campaigns migrated mid-play: state.turn_base, the read-only data/history.json archive, and scene extras.
Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA)."""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_db import Env, REAL_DATA  # noqa: E402

ARCHIVE = [
    {"id": "turn-001", "label": "t0-16", "kind": "summary", "turn_from": 0, "turn_to": 16, "summary": "The brothers register and fight Renji Kuroba."},
    {"id": "turn-002", "label": "t17-48 Lumiere", "kind": "summary", "turn_from": 17, "turn_to": 48, "summary": "Dinner at the club; the crew decides to use it as a base."},
    {"id": "turn-003", "label": "t49-64 Gara", "kind": "turn", "turn_from": 49, "turn_to": 64, "summary": "Gara asks for a name and offers routes."},
]


@pytest.fixture
def mig(tmp_path):
    """classroom-2b data migrated mid-play: no logged turns, turn_base = the old turn count, an archive."""
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data)
    env = Env(data, tmp_path)
    st = env.load("state")
    assert st["turn"] == 0 and env.load("turns") == []
    n = 50  # a campaign that was played for 50 turns elsewhere
    st["turn"] = st["turn_base"] = n
    st["scene"] = None
    env.save_json("state", st)
    env.save_json("turns", [])
    env.save_json("history", ARCHIVE)
    env.n = n
    return env


def test_resume_shows_archive_when_no_turns_are_logged(mig):
    r = mig.run("resume")
    assert r.returncode == 0, r.stderr
    assert f"Turn {mig.n} |" in r.stdout
    assert f"none logged since the migration (turn_base {mig.n}); archive has 3 range summaries" in r.stdout
    assert "[archive t49-64 Gara]" in r.stdout and "[archive t17-48 Lumiere]" in r.stdout and "[archive t0-16]" not in r.stdout


def test_recap_fills_from_the_archive_and_stays_quiet_without_one(mig):
    r = mig.run("recap", "--turns", "2")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l.startswith("- ") and not l.startswith("- Canon")]
    assert len(lines) == 2 and "t17-48 Lumiere" in lines[0] and "t49-64 Gara" in lines[1]
    (mig.data / "history.json").unlink()
    assert "nothing yet" in mig.run("recap").stdout


def test_recap_withholds_archive_lines_with_hidden_terms(mig):
    arch = ARCHIVE + [{"id": "turn-004", "label": "t65", "kind": "turn", "turn_from": 65, "turn_to": 65, "summary": "Hidden Zebrafish found."}]
    mig.save_json("history", arch)
    # hidden words come from campaign.json: use a ladder keyword instead (threads.json of the copy)
    th = mig.load("threads")
    k = next(iter(th))
    th[k]["steps"][0].update({"keywords": ["Zebrafish"], "status": "hidden"})
    mig.save_json("threads", th)
    out = mig.run("recap", "--turns", "1").stdout
    assert "summary withheld" in out and "Zebrafish" not in out


def test_history_searches_logged_turns_then_archive(mig):
    r = mig.run("history", "Gara")
    assert r.returncode == 0 and "[archive] t49-64 Gara: " in r.stdout and "offers routes" in r.stdout
    assert "[archive] t0-16" in mig.run("history", "brothers", "renji").stdout
    assert "no match" in mig.run("history", "zzzz").stdout
    # logged turns come first
    assert mig.run("turn", mig.n + 1, "--inputs", "i", "--summary", "Gara shrugs.", "--prompt", "Cut: x\nWorld: y").returncode == 0
    out = mig.run("history", "Gara").stdout.splitlines()
    assert out[0].startswith(f"T{mig.n + 1} ") and any(l.startswith("[archive]") for l in out)


def test_turn_base_keeps_verification_and_undo_working(mig):
    prompt = mig.tmp / "p.txt"
    prompt.write_text("Cut: Continue at the kitchen.\nWorld: The kettle whistles.", encoding="utf-8")
    pl = mig.tmp / "pl.json"
    pl.write_text(json.dumps({"ops": [], "turn_log": {"inputs": "i", "summary": "s"}}), encoding="utf-8")
    r = mig.run("commit-turn", "--prompt", prompt, "--payload", pl)
    assert r.returncode == 0, r.stdout + r.stderr
    assert mig.load("state")["turn"] == mig.n + 1 and len(mig.load("turns")) == 1
    r = mig.run("undo-turn", mig.n + 1)
    assert r.returncode == 0 and mig.load("state")["turn"] == mig.n and mig.load("turns") == []
    # a wrong turn_base is caught by verification and nothing is applied
    st = mig.load("state")
    st["turn_base"] = mig.n - 1
    mig.save_json("state", st)
    before = {p.name: p.read_bytes() for p in mig.data.glob("*.json")}
    r = mig.run("commit-turn", "--prompt", prompt, "--payload", pl)
    assert r.returncode != 0 and "verification failed" in (r.stdout + r.stderr)
    assert {p.name: p.read_bytes() for p in mig.data.glob("*.json")} == before


def test_without_turn_base_the_old_check_stands(mig):
    st = mig.load("state")
    st.pop("turn_base")
    mig.save_json("state", st)
    prompt = mig.tmp / "p.txt"
    prompt.write_text("Cut: Continue at the kitchen.\nWorld: The kettle whistles.", encoding="utf-8")
    pl = mig.tmp / "pl.json"
    pl.write_text(json.dumps({"ops": [], "turn_log": {"inputs": "i", "summary": "s"}}), encoding="utf-8")
    r = mig.run("commit-turn", "--prompt", prompt, "--payload", pl)
    assert r.returncode != 0 and "turns.json has" in (r.stdout + r.stderr)


def test_scene_extras_are_shown_and_pending_items_cleared_by_the_next_turn(mig):
    st = mig.load("state")
    st["scene"] = {"name": "After the bell", "location": "Sakura Lane Sharehouse", "area": "shared-kitchen", "budget": 3, "turns_used": 0,
                   "obstacles_used": [], "surprise_used": False, "started_turn": mig.n,
                   "comms": ["Nobu"], "elsewhere": {"Gym": ["Tetsu"]}, "pending_inputs": ["Jostin: waits"],
                   "pending_prompt_notes": ["Prompt sent: Cut: x"]}
    mig.save_json("state", st)
    out = mig.run("state").stdout
    assert "on comms: Nobu" in out and "elsewhere: Gym: Tetsu" in out
    assert "pending inputs (carried over): Jostin: waits" in out and "pending prompt notes (carried over): Prompt sent: Cut: x" in out
    assert mig.run("turn", mig.n + 1, "--inputs", "i", "--summary", "s", "--prompt", "Cut: x\nWorld: y").returncode == 0
    sc = mig.load("state")["scene"]
    assert "pending_inputs" not in sc and "pending_prompt_notes" not in sc and sc["comms"] == ["Nobu"] and sc["turns_used"] == 1
    assert "pending inputs" not in mig.run("state").stdout
