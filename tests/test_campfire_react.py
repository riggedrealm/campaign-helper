"""G3: `react-check`, the read-only check of a react file (threat moves and NPC reactions) against the result packet, before `gm react`."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campfire_pc import Pc  # noqa: E402

GOOD = {"threat_moves": [{"threat": "grey-coat", "kind": "press", "target": "p_7k2m"}],
        "reactions": [{"npc": "Mio Tachibana", "kind": "attitude", "word": "neutral", "line": "Not my fight."},
                      {"npc": "Mr. Hasegawa", "kind": "give", "player": "p_3hx9", "item": "a torch", "qty": 1}]}


def zones(p):
    p["scene"]["zones"] = ["the counter", "the back room"]


@pytest.fixture
def pc(tmp_path):
    return Pc(tmp_path)


def rc(pc, obj, mutate=zones, *extra):
    return pc.db("react-check", "--reactions", pc.write("react.json", obj), "--packet", pc.packet(mutate), *extra)


def test_a_good_react_file_passes_and_writes_nothing(pc):
    before = pc.hashes()
    r = rc(pc, GOOD)
    assert r.returncode == 0 and "react-check: ok" in r.stdout and "1 threat move(s), 2 reaction(s)" in r.stdout
    assert pc.hashes() == before


def edit(**kw):
    o = copy.deepcopy(GOOD)
    for k, f in kw.items():
        f(o)
    return o


@pytest.mark.parametrize("obj,msg", [
    (edit(threat_moves=lambda o: o["threat_moves"].clear()), 'threat "grey-coat" is active and needs exactly one move'),
    (edit(threat_moves=lambda o: o["threat_moves"].append({"threat": "grey-coat", "kind": "hold"})), "has two moves"),
    (edit(threat_moves=lambda o: o["threat_moves"][0].update(kind="charge")), "kind must be one of press, press all, hold, flee"),
    (edit(threat_moves=lambda o: o["threat_moves"][0].pop("target")), "press needs a target"),
    (edit(threat_moves=lambda o: o["threat_moves"][0].update(target="nobody")), "press needs a target"),
    (edit(threat_moves=lambda o: o["threat_moves"].__setitem__(0, {"threat": "grey-coat", "kind": "hold", "target": "p_7k2m"})), "only press takes a target"),
    (edit(threat_moves=lambda o: o["threat_moves"].append({"threat": "ghost", "kind": "hold"})), 'no threat "ghost"'),
    (edit(reactions=lambda o: o["reactions"].append({"npc": "Mio Tachibana", "kind": "stay"})), "has two reactions"),
    (edit(reactions=lambda o: o["reactions"].append({"npc": "Sunny", "kind": "stay"})), "is not an NPC in the scene"),
    (edit(reactions=lambda o: o["reactions"][0].update(word="friendly")), "is not one step from wary"),
    (edit(reactions=lambda o: o["reactions"][0].update(kind="relationship")), "not in the first playtest"),
    (edit(reactions=lambda o: o["reactions"][1].update(qty=4)), "qty must be a whole number from 1 to 3"),
    (edit(reactions=lambda o: o["reactions"][1].update(player="p_nope")), "is not in the party"),
    (edit(reactions=lambda o: o["reactions"][0].update(line="x" * 201)), "line must be 1 to 200 characters"),
    (edit(reactions=lambda o: o["reactions"][0].update(harm=3)), "harm is not a field of a attitude reaction"),
    (edit(reactions=lambda o: o["reactions"].__setitem__(1, {"npc": "Mr. Hasegawa", "kind": "move"})), "a move reaction needs to"),
    (edit(reactions=lambda o: o["reactions"].__setitem__(1, {"npc": "Mr. Hasegawa", "kind": "move", "to": "the roof"})), "is not one of the scene's zones"),
    ({"threat_moves": [], "reactions": [], "extra": 1}, 'unknown key "extra"'),
])
def test_each_rule_of_the_menu(pc, obj, msg):
    r = rc(pc, obj)
    assert r.returncode == 1 and msg in r.stdout, r.stdout


def test_a_threat_that_is_full_may_only_hold_or_flee(pc):
    full = lambda p: (zones(p), p["threats"][0].update(status="full"))  # noqa: E731
    assert "may only hold or flee" in rc(pc, GOOD, full).stdout
    ok = edit(threat_moves=lambda o: o["threat_moves"][0].update(kind="flee", target=None))
    del ok["threat_moves"][0]["target"]
    assert rc(pc, ok, full).returncode == 0


def test_a_retired_threat_gets_no_move(pc):
    r = rc(pc, GOOD, lambda p: (zones(p), p["threats"][0].update(status="retired")))
    assert r.returncode == 1 and "is retired and gets no move" in r.stdout


def test_a_pressed_character_who_is_out_is_refused(pc):
    def out(p):
        zones(p)
        p["party"][0]["conditions"] = [{"name": "Out", "turns": None}]
    assert "cannot be pressed" in rc(pc, GOOD, out).stdout


def test_a_hidden_term_in_a_line_is_exit_4(pc):
    obj = edit(reactions=lambda o: o["reactions"][0].update(line="The zebrafish know."))
    r = rc(pc, obj)
    assert r.returncode == 4 and 'hidden term "zebrafish"' in r.stdout and "reactions[0].line" in r.stdout
    assert rc(pc, obj, zones, "--allow", "Zebrafish").returncode == 0


def test_a_missing_or_malformed_file_is_exit_2(pc):
    assert pc.db("react-check", "--reactions", str(pc.tmp / "none.json"), "--packet", pc.packet()).returncode == 2
    assert pc.db("react-check", "--reactions", pc.write("bad.json", "{"), "--packet", pc.packet()).returncode == 2
