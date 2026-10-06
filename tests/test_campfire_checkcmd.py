"""G5, the commands: `check` (the code checks of the check stage on a draft, the checker's answers, the three-rewrite loop and its log),
`check-brief` (the checker's whole brief) and `hard-noes` (the table's list, in campaign.json)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campfire_pc import Pc  # noqa: E402

SCENE = ("Aiko vaults the counter and goes for the grey coat's wrist.\n\n"
         '@Mio Tachibana (not looking up)\n"We\'re closed."\n\n'
         "Mio slips into the back room, keys jangling.\n\n"
         "Ren checks the shelves while Yuna watches the door.\n\n"
         "The man in the grey coat does not move. What will they do?")
OPS = [{"op": "item", "player": "p_7k2m", "action": "add", "name": "keys", "qty": 1, "evidence": "keys jangling"}]
MAP = {"inputs": [{"player": "p_7k2m", "paragraphs": [1]}, {"player": "p_3hx9", "paragraphs": [4]}, {"player": "p_9qw4", "paragraphs": [4]}]}
CLEAN_ANSWERS = {"answers": [{"q": q, "answer": "yes" if q == 7 else "no", "quote": ""} for q in range(1, 8)]}


def reacted(p):
    p["scene"]["zones"] = ["the counter", "the door", "the back room"]
    for m, z in zip(p["party"], ("the counter", "the door", "the door")):
        m["zone"] = z
    p["scene"]["npcs"][0]["zone"] = "the counter"
    p["reactions"] = [{"npc": "Mio Tachibana", "kind": "move", "to": "the back room", "line": "We're closed.",
                       "applied": {"zone": {"from": "the counter", "to": "the back room"}}}]


@pytest.fixture
def pc(tmp_path):
    return Pc(tmp_path)


def check(pc, scene=SCENE, ops=OPS, *extra, mutate=reacted, mapping=MAP, rnd="1"):
    a = ["check", "--scene", pc.write("scene.md", scene), "--packet", pc.packet(mutate), "--round", rnd]
    if ops is not None:
        a += ["--ops", pc.write("ops.json", ops)]
    if mapping is not None:
        a += ["--map", pc.write("map.json", mapping)]
    return pc.db(*a, *extra)


def codes(r):
    import re
    return re.findall(r"(?:FLAG|WARN) \[(\w+)\]", r.stdout)


def test_a_clean_draft_passes_and_writes_only_its_log(pc):
    before = pc.hashes()
    r = check(pc)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no flags" in r.stdout and "the checker has not run" in r.stdout
    assert pc.hashes() == before
    log = json.loads((pc.cdir / "campfire" / "check-1.json").read_text(encoding="utf-8"))
    assert log["attempts"][0]["flags"] == [] and log["attempts"][0]["checker"] == "not run"


def test_the_checker_answers_join_the_flags(pc, tmp_path):
    ok = check(pc, SCENE, OPS, "--answers", pc.write("a.json", CLEAN_ANSWERS))
    assert ok.returncode == 0 and "the checker has not run" not in ok.stdout
    bad = json.loads(json.dumps(CLEAN_ANSWERS))
    bad["answers"][0] = {"q": 1, "answer": "yes", "quote": "Ren checks the shelves"}
    r = check(pc, SCENE, OPS, "--answers", pc.write("b.json", bad), "--reset")
    assert r.returncode == 1 and "[player_voice]" in r.stdout and '| "Ren checks the shelves"' in r.stdout


def test_hard_noes_flag_narration_and_warn_in_dialogue(pc):
    assert pc.db("hard-noes", "--add", "grey coat's wrist", "--add", "Sunny").returncode == 0
    r = check(pc)
    assert r.returncode == 1 and codes(r) == ["hard_no"]
    dialogue = SCENE.replace("goes for the grey coat's wrist", 'says "the grey coat\'s wrist"')
    r2 = check(pc, dialogue, OPS, "--reset")
    assert r2.returncode == 0 and codes(r2) == ["hard_no_dialogue"]


def test_hard_noes_command(pc):
    assert "none" in pc.db("hard-noes").stdout
    assert "now 2" in pc.db("hard-noes", "--add", "one two", "--add", "three").stdout
    assert pc.db("hard-noes", "--add", "ONE  two").returncode == 0                     # the same phrase: not added twice
    assert json.loads((pc.cdir / "campaign.json").read_text(encoding="utf-8"))["hard_noes"] == ["one two", "three"]
    assert "now 1" in pc.db("hard-noes", "--remove", "One Two").stdout
    r = pc.db("hard-noes", "--add", "x" * 61)
    assert r.returncode == 2 and "limit is 60" in r.stdout + r.stderr
    assert "Hard noes: 1 phrase(s)" in pc.db("resume").stdout


def test_a_hidden_term_is_exit_4(pc):
    r = check(pc, SCENE + "\n\nA zebrafish tank bubbles.")
    assert r.returncode == 4 and "[hidden_word]" in r.stdout and "do not post" in r.stdout


@pytest.mark.parametrize("edit,code", [
    (lambda s: s.replace("Mio slips into the back room", "Mio waits by the door"), "wrong_zone"),
    (lambda s: s.replace('"We\'re closed."', '"We are closed."'), "reaction_line_missing"),
    (lambda s: s.replace("keys jangling", "coins jangling"), "evidence_not_in_scene"),
    (lambda s: s + "\n\nTatsuya Ōmine glances in.", "cast_not_present"),
    (lambda s: s.replace("@Mio Tachibana (not looking up)", "@Nobody Atall (not looking up)"), "speaker_unknown"),
    (lambda s: s + "\n\nThey hurry into the Moonlit Annex.", "unknown_place"),
])
def test_each_state_check_flags_its_failure(pc, edit, code):
    r = check(pc, edit(SCENE))
    assert r.returncode == 1 and code in codes(r), r.stdout


def test_the_input_map_is_checked(pc):
    assert "input_unmapped" in codes(check(pc, mapping={"inputs": [MAP["inputs"][0]]}))
    assert "map_bad_paragraph" in codes(check(pc, mapping={"inputs": [{"player": "p_7k2m", "paragraphs": [99]}] + MAP["inputs"][1:]}, rnd="2"))
    assert codes(check(pc, mapping=None, rnd="3")) == []                               # no --map: the map is not checked


def test_a_pc_block_that_is_not_a_quote_is_a_flag(pc):
    r = check(pc, SCENE + '\n\n@Aiko Tanaka\n"I give up."')
    assert r.returncode == 1 and "pc_block" in codes(r)


def test_the_loop_stops_after_three_rewrites(pc):
    bad = SCENE.replace("keys jangling", "coins jangling")
    log = pc.cdir / "campfire" / "check-1.json"
    for n in (1, 2, 3):
        r = check(pc, bad)
        assert r.returncode == 1 and f"rewrite {n - 1} of 3" in r.stdout
    last = check(pc, bad)                                                              # the third rewrite, still flagged
    assert last.returncode == 9 and "STOP" in last.stdout and "Show the GM the draft and these flags" in last.stdout
    again = check(pc, SCENE)                                                           # even a clean draft: the GM decides first
    assert again.returncode == 9 and "wait for the GM" in again.stdout
    assert len(json.loads(log.read_text(encoding="utf-8"))["attempts"]) == 4
    fresh = check(pc, SCENE, OPS, "--reset")
    assert fresh.returncode == 0 and len(json.loads(log.read_text(encoding="utf-8"))["attempts"]) == 1


def test_a_clean_rewrite_inside_the_limit_passes(pc):
    assert check(pc, SCENE.replace("keys jangling", "coins jangling")).returncode == 1
    assert check(pc).returncode == 0


def test_check_needs_a_round_or_a_log(pc):
    p = pc.packet(lambda p: p["room"].pop("round"))
    r = pc.db("check", "--scene", pc.write("s.md", SCENE), "--packet", p)
    assert r.returncode == 2 and "--round N is required" in r.stdout + r.stderr


def test_check_brief_carries_nothing_beyond_the_draft_the_packet_and_the_hard_noes(pc):
    pc.db("hard-noes", "--add", "blood bath")
    pc.db("npc-intent", "Mio Tachibana", "--turn", "1", "--evidence", "t", "--want", "SECRET-WANT-XYZ", "--fear", "SECRET-FEAR-XYZ")
    cast = pc.load("cast")
    cast["Mio Tachibana"]["hidden"] = "SECRET-HIDDEN-XYZ"
    pc.save("cast", cast)
    out = pc.db("check-brief", "--scene", pc.write("scene.md", SCENE), "--packet", pc.packet(reacted)).stdout
    assert "- blood bath" in out and "Mio slips into the back room" in out and '"code": "K7Q2MX"' in out
    for secret in ("SECRET-WANT-XYZ", "SECRET-FEAR-XYZ", "SECRET-HIDDEN-XYZ", "Zebrafish"):
        assert secret.lower() not in out.lower()
    assert out.count("QUESTIONS") == 1 and "never rewrite" in out
