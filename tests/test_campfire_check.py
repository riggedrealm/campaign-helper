"""G5, the pure half: tools/campfire_check.py. The phrase check (code matches phrases, narration flags, dialogue warns), each state
check with a passing and a failing scene, the checker's brief (nothing beyond the draft, the packet and the hard noes) and its answers."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import campfire_check as CK  # noqa: E402


# ---- the phrase match -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,hit", [
    ("He said Blood Bath twice.", True),                       # case ignored
    ("a blood​ bath", True),                              # zero-width space cleaned (a space remains between the words)
    ("blood​bath", False),                                # the words are glued once the invisible character goes
    ("bl​ood bath", True),                                # a zero-width space inside a word is removed
    ("bloodbath", False),                                      # whole words only
    ("the blood, the bath", False),                            # contiguous
    ("bath blood", False),                                     # in order
    ("a Ｂlood bath", True),                               # NFKC: a full-width B
    ("blood-bath", True),                                      # punctuation between words is not a word
])
def test_phrase_match(text, hit):
    assert bool(CK.phrase_spans(text, "blood bath")) is hit


def test_apostrophe_stays_inside_a_word():
    assert CK.phrase_spans("She didn’t go", "didn't go") and not CK.phrase_spans("She didn go", "didn't go")


def test_phrase_flags_narration_flags_and_dialogue_warns():
    scene = 'The room stank of old tea.\n\nOda says, "Nobody touches the blood bath."\n\nThen the blood bath began.'
    fl = CK.phrase_flags(scene, ["blood bath"])
    assert [(f["code"], f["severity"], f["para"]) for f in fl] == [("hard_no_dialogue", "warn", 2), ("hard_no", "flag", 3)]
    assert CK.phrase_flags(scene, []) == []


def test_hard_noe_problems():
    assert CK.hard_noe_problems(["a", "b c"]) == []
    assert CK.hard_noe_problems("x") and CK.hard_noe_problems([1]) and CK.hard_noe_problems(["!!"])
    assert CK.hard_noe_problems(["x" * 61]) and CK.hard_noe_problems(["a b", "A  B"]) and CK.hard_noe_problems([f"w{i}" for i in range(31)])
    assert CK.hard_noe_problems([f"w{i}" for i in range(30)]) == []


# ---- the state checks, each with a passing and a failing scene -------------------------------------------------------
def test_evidence_in_scene_up_to_whitespace_and_case():
    scene = "Mio  counts the till.\n\nThe door sticks."
    ops = [{"op": "item", "evidence": "mio counts\nthe TILL."}]
    assert CK.evidence_flags(scene, ops) == []
    bad = CK.evidence_flags(scene, ops + [{"op": "coin", "evidence": "Mio counts the shelf."}, {"op": "rest"}])
    assert [f["code"] for f in bad] == ["evidence_not_in_scene", "evidence_missing"]


def test_reaction_lines_must_appear_unchanged():
    scene = 'Kenji backs off. "Not my fight," he says.'
    assert CK.reaction_line_flags(scene, [{"npc": "Kenji", "kind": "stay", "line": "Not my fight"}, {"npc": "X", "kind": "stay"}]) == []
    fl = CK.reaction_line_flags(scene, [{"npc": "Kenji", "kind": "stay", "line": "Not my war"}])
    assert [f["code"] for f in fl] == ["reaction_line_missing"]


def test_zone_check():
    pos = {"Kenji": "the back room", "Mira": "the door"}
    zones = ["the door", "the back room"]
    assert CK.zone_flags("Kenji slips into the back room.", pos, zones) == []
    assert CK.zone_flags("Kenji waits at the door.", pos, zones)[0]["code"] == "wrong_zone"
    assert CK.zone_flags("Kenji crosses from the door to the back room.", pos, zones) == []   # a move across two named zones
    assert CK.zone_flags("Kenji whistles.", pos, zones) == []                                  # no zone in the sentence
    assert CK.zone_flags("Kenji waits at the door.", {}, zones) == [] and CK.zone_flags("Kenji waits at the door.", pos, []) == []


def test_place_check():
    known = ["Page Turner Books", "the back room", "Sakura Lane"]
    assert CK.place_flags("They walk to the Sakura Lane pharmacy? No: in the Sakura Lane.", known) == []
    fl = CK.place_flags("Mio hurries into the Moonlit Annex.", known)
    assert [f["code"] for f in fl] == ["unknown_place"] and "Moonlit Annex" in fl[0]["text"]
    assert CK.place_flags("She goes to the door, then to the shop.", known) == []   # lower case is not a named place


def test_input_map():
    scene = "Aiko vaults the counter.\n\nRen asks Sunny to keep the door.\n\nThe room waits."
    inputs = [{"player": "p1", "name": "Aiko Tanaka"}, {"player": "p2", "name": "Ren Okabe"}]
    names = lambda x: [x["name"]] + x["name"].split()[:1]  # noqa: E731
    ok = {"inputs": [{"player": "p1", "paragraphs": [1]}, {"player": "p2", "paragraphs": [2]}]}
    assert CK.map_flags(scene, inputs, ok, names) == []
    codes = lambda m: [f["code"] for f in CK.map_flags(scene, inputs, m, names)]  # noqa: E731
    assert codes({"inputs": [{"player": "p1", "paragraphs": [1]}]}) == ["input_unmapped"]
    assert codes({"inputs": [{"player": "p1", "paragraphs": [1]}, {"player": "p2", "paragraphs": [9]}]}) == ["map_bad_paragraph"]
    assert codes({"inputs": [{"player": "p1", "paragraphs": [1]}, {"player": "p2", "paragraphs": [3]}]}) == ["input_outcome_missing"]
    assert codes({"inputs": [{"player": "p1", "paragraphs": []}, {"player": "p2", "paragraphs": [2]}]}) == ["input_unmapped"]


# ---- the checker's brief and answers ---------------------------------------------------------------------------------
def test_checker_brief_holds_the_questions_the_noes_the_packet_and_the_draft():
    packet = {"room": {"code": "K7Q2MX"}, "party": [{"name": "Mira"}]}
    b = CK.checker_brief("The draft text.\n", packet, ["blood bath"])
    for _c, q, _bad in CK.QUESTIONS:
        assert q in b
    assert "- blood bath" in b and '"code": "K7Q2MX"' in b and b.rstrip().endswith("The draft text.")
    assert "(none)" in CK.checker_brief("d", packet, [])
    assert len(CK.QUESTIONS) == 7 and CK.QUESTIONS[-1][2] == "no"


def answers():
    base = {i: ("yes" if i == 7 else "no") for i in range(1, 8)}  # the clean pattern: no on 1 to 6, yes on 7
    return {"answers": [{"q": q, "answer": a, "quote": "x"} for q, a in base.items()]}


def test_clean_answers_raise_no_flag():
    assert CK.answer_flags(answers(), "x") == []


def test_a_yes_on_1_to_6_and_a_no_on_7_are_flags_with_the_quote_checked():
    obj = answers()
    obj["answers"][0] = {"q": 1, "answer": "yes", "quote": "Mira sighs"}
    obj["answers"][6] = {"q": 7, "answer": "no", "quote": ""}
    fl = CK.answer_flags(obj, "Mira sighs and leaves.")
    assert [f["code"] for f in fl] == ["player_voice", "no_decision"] and "not in the draft" not in fl[0]["text"]
    obj["answers"][0]["quote"] = "invented"
    assert "the quote is not in the draft" in CK.answer_flags(obj, "Mira sighs.")[0]["text"]


@pytest.mark.parametrize("bad", [None, [], {"answers": "no"}, {"answers": [{"q": 1, "answer": "maybe"}]}, {"answers": [{"q": 1, "answer": "no"}]}])
def test_a_malformed_reply_is_a_flag(bad):
    assert [f["code"] for f in CK.answer_flags(bad, "x")] == ["checker_bad_reply"]


def test_the_module_is_pure():
    src = Path(CK.__file__).read_text(encoding="utf-8")
    assert not any(w in src for w in ("import os", "import subprocess", "import socket", "urllib", "open(", "Path("))
