"""pc-thread per player character: --pc (and `pc` in a payload op), the one-PC default, the refusals, old notes, plan-brief grouping and
arc-pivot naming the PC. Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA); the real data dir is never written.
No test asserts on the first line of an output: every db.py output may gain a campaign-name header line."""
import json
import shutil

import pytest

from test_pivot import CHARTER, REAL_DATA, Env

THREAD = "went to the net menders instead of the guild clerk"


@pytest.fixture
def one(tmp_path):
    """One PC (Aiko Tanaka), no arcs file."""
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr
    return e


@pytest.fixture
def two(one):
    """Two PCs: Aiko Tanaka and Ren Okada."""
    r = one.run("pc-add", "Ren Okada", "--player", "Kit", "--room", "river-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr
    return one


def notes(env):
    return env.load("arcs")["pc_threads"] if (env.data / "arcs.json").exists() else []


def payload(env, name, args):
    ops = [{"op": "pc-thread", "args": args, "evidence": "e"}]
    return env.write(name, json.dumps({"turn": 1, "ops": ops, "turn_log": {"inputs": "i", "summary": "s", "prompt": "none"}}))


def test_one_pc_is_the_default(one):
    assert one.op("pc-thread", THREAD, turn=1).returncode == 0
    assert notes(one) == [{"turn": 1, "text": THREAD, "evidence": "the story showed it", "pc": "Aiko Tanaka"}]


def test_pc_option_resolves_fuzzily_and_stores_the_canonical_name(two):
    assert two.op("pc-thread", THREAD, "--pc", "aiko", turn=1).returncode == 0
    assert two.op("pc-thread", "kept asking about the ferry", "--pc", "Okada", turn=1).returncode == 0
    assert [n["pc"] for n in notes(two)] == ["Aiko Tanaka", "Ren Okada"]


def test_two_pcs_need_pc_and_the_refusal_lists_them(two):
    r = two.op("pc-thread", THREAD, turn=1)
    assert r.returncode == 2
    assert "--pc" in r.stderr and "Aiko Tanaka" in r.stderr and "Ren Okada" in r.stderr
    assert notes(two) == []


def test_unknown_pc_is_refused(two):
    r = two.op("pc-thread", THREAD, "--pc", "Zebediah Quux", turn=1)
    assert r.returncode == 2 and "player character" in r.stderr
    assert notes(two) == []


def test_payload_op_takes_pc(two):
    # without pc in the payload, two PCs refuse it and nothing is written
    r = two.run("record", payload(two, "p2.json", {"text": "another thread"}))
    assert r.returncode == 2 and "--pc" in r.stderr
    assert notes(two) == []
    r = two.run("record", payload(two, "p.json", {"text": THREAD, "pc": "Ren"}))
    assert r.returncode == 0, r.stderr
    assert [(n["pc"], n["text"]) for n in notes(two)] == [("Ren Okada", THREAD)]


def test_old_notes_without_a_pc_stay_valid(two):
    two.save_json("arcs", {"version": 1, "session_zero": {}, "pc_threads": [{"turn": 1, "text": "went back to the cart", "evidence": "e"}],
                           "acts": [], "arcs": []})
    assert two.run("wrap-up").returncode == 0
    out = two.ok("plan-brief")
    assert "(no PC):" in out and "went back to the cart" in out


def test_plan_brief_groups_threads_by_pc(two):
    two.op("pc-thread", "kept asking about the ferry", "--pc", "Ren", turn=1)
    two.op("pc-thread", "went back to the cart", "--pc", "Aiko", turn=1)
    two.op("pc-thread", "counted the ferry coins again", "--pc", "Ren", turn=1)
    out = two.ok("plan-brief")
    out = out[out.index("PC THREADS"):]
    i, j = out.index("  Aiko Tanaka:"), out.index("  Ren Okada:")
    assert i < j  # the order of the state's player characters
    aiko, ren = out[i:j], out[j:]
    assert "went back to the cart" in aiko and "ferry" not in aiko
    assert "kept asking about the ferry" in ren and "counted the ferry coins again" in ren and "went back to the cart" not in ren


@pytest.fixture
def pivot(one):
    """Arc A1 active since turn 2 (planned while Aiko was the only PC), then Ren joins; turns 3 to 5 logged without arc contact."""
    two = one
    two.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore")
    two.advance(2)
    two.ok("arc-plan", "--file", two.write("c.json", json.dumps(CHARTER)))
    two.ok("arc-approve", "A1", "--lines-checked")
    assert two.op("arc-start", "A1", turn=2).returncode == 0
    r = two.run("pc-add", "Ren Okada", "--player", "Kit", "--room", "river-bedroom", "--turn", "2", "--evidence", "test")
    assert r.returncode == 0, r.stderr
    two.advance(5)
    return two


def fired(out):
    return any(ln.startswith("pivot detected") for ln in out.splitlines())


def test_arc_pivot_names_the_pc(pivot):
    assert pivot.op("pc-thread", THREAD, "--pc", "Ren", turn=4).returncode == 0
    out = pivot.ok("arc-pivot")
    assert fired(out) and THREAD in out and "pc: Ren Okada" in out


def test_arc_pivot_on_an_old_note_names_no_pc(pivot):
    a = pivot.load("arcs")
    a["pc_threads"].append({"turn": 4, "text": THREAD, "evidence": "e"})
    pivot.save_json("arcs", a)
    out = pivot.ok("arc-pivot")
    assert fired(out) and THREAD in out and "pc:" not in out


def test_arc_pivot_keeps_the_split_party_note(pivot):
    pivot.turn(6, flag=True)  # another PC is still in the arc: the last logged turn has arc contact
    out = pivot.ok("arc-pivot", "--thread", "Ren joins the net menders")
    assert "split party" in out and "PIV-8" in out
