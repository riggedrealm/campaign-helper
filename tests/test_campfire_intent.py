"""G1: the NPC brief's intent fields (want, fear, trigger, refusal, voice lines, last gesture) in cast.json: validated, set by
`npc-intent`, shown in the brief and in prep's compact brief."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campfire_pc import Pc  # noqa: E402

VOICE = ["Not my fight.", "Shop's closed.", "Ask someone else."]


@pytest.fixture
def pc(tmp_path):
    return Pc(tmp_path)


def cast_key(pc):
    return "Mio Tachibana"


def set_intent(pc, *extra, key=None):
    return pc.db("npc-intent", key or cast_key(pc), "--turn", "1", "--evidence", "test", *extra)


def test_set_and_show(pc):
    key = cast_key(pc)
    r = set_intent(pc, "--want", "Keep the shop open", "--fear", "The grey coat", "--trigger", "Anyone touches the till",
                   "--refusal", "Name the customer", "--gesture", "counts the till", *sum((["--voice", v] for v in VOICE), []), key=key)
    assert r.returncode == 0, r.stdout + r.stderr
    it = pc.load("cast")[key]["intent"]
    assert it["want"] == "Keep the shop open" and it["voice_lines"] == VOICE and it["last_gesture"] == "counts the till"
    b = pc.db("brief", key).stdout
    assert "INTENT (Campfire; secret):" in b and "wants: Keep the shop open" in b and "last gesture: counts the till" in b


def test_only_the_fields_given_change(pc):
    key = cast_key(pc)
    assert set_intent(pc, "--want", "a", key=key).returncode == 0
    assert set_intent(pc, "--fear", "b", key=key).returncode == 0
    assert pc.load("cast")[key]["intent"] == {"want": "a", "fear": "b"}


@pytest.mark.parametrize("args,msg", [
    (["--voice", "one", "--voice", "two"], "voice_lines must be 3 to 5"),
    (sum((["--voice", f"l{i}"] for i in range(6)), []), "voice_lines must be 3 to 5"),
    (["--want", "x" * 241], "intent.want must be a non-empty string of at most 240"),
    ([], "give at least one of"),
])
def test_bad_intent_is_refused_and_nothing_written(pc, args, msg):
    before = pc.hashes()
    r = set_intent(pc, *args)
    assert r.returncode != 0 and msg in r.stdout + r.stderr
    assert pc.hashes() == before


def test_world_npc_is_refused(pc):
    w = pc.load("world-npcs")
    name = next((k for k in w if k not in pc.load("cast")), None)
    if name is None:
        pytest.skip("no world-only NPC in the fixture data")
    r = set_intent(pc, "--want", "x", key=name)
    assert r.returncode != 0 and "world NPC" in r.stdout + r.stderr


def test_verify_data_rejects_a_hand_written_bad_intent():
    import importlib.util
    spec = importlib.util.spec_from_file_location("dbmod", Path(__file__).resolve().parent.parent / "tools" / "db.py")
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    bad = db.intent_problems({"want": "ok", "colour": "red", "voice_lines": ["only one"]})
    assert any("intent.colour is not a known field" in m for m in bad) and any("voice_lines must be 3 to 5" in m for m in bad)
    assert db.intent_problems({"want": "a", "voice_lines": ["a", "b", "c"], "last_gesture": "g"}) == []
    assert db.intent_problems("no") == ["intent must be an object"]


def test_prep_compact_brief_shows_the_intent(pc):
    key = cast_key(pc)
    set_intent(pc, "--want", "Keep the shop open", "--gesture", "counts the till", key=key)
    pk = pc.packet(lambda p: p["scene"]["npcs"].append({"name": key, "attitude": "wary"}))
    out = pc.db("prep", "--packet", pk).stdout
    assert "wants: Keep the shop open" in out and "last gesture: counts the till" in out
