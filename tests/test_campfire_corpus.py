"""A1 of the GDD v2 test plan: a small corpus of drafts (tests/fixtures/checker-corpus.json) that is tested both ways. Every draft passes
the code checks, so what a slip needs is the checker; five are clean and five slip a player's choice or a hard no past the code. Here
the code half is run for real and the checker half is the brief it gets and the flag its answer would raise; the gate runs the same
corpus through the checker subagent."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import campfire_check as CK  # noqa: E402
from campfire_pc import Pc  # noqa: E402
from test_campfire_checkcmd import MAP, OPS, reacted  # noqa: E402

CORPUS = json.loads((Path(__file__).resolve().parent / "fixtures" / "checker-corpus.json").read_text(encoding="utf-8"))
SCENES = CORPUS["scenes"]
CODES = [c for c, _q, _bad in CK.QUESTIONS]
IDS = [s["id"] for s in SCENES]


@pytest.fixture(scope="module")
def pc(tmp_path_factory):
    p = Pc(tmp_path_factory.mktemp("corpus"))
    for ph in CORPUS["hard_noes"]:
        assert p.db("hard-noes", "--add", ph).returncode == 0
    return p


def answers_for(slip):
    out = []
    for i, (code, _q, bad) in enumerate(CK.QUESTIONS, 1):
        hit = slip is not None and slip["question"] == code
        out.append({"q": i, "answer": bad if hit else ("no" if bad == "yes" else "yes"), "quote": slip["quote"] if hit else ""})
    return {"answers": out}


def test_the_corpus_is_half_clean_and_half_slips():
    assert len(SCENES) == 10 and len(set(IDS)) == 10
    slips = [s for s in SCENES if s["slip"]]
    assert len(slips) == 5 and all(s["slip"]["question"] in ("player_voice", "hard_no_reworded") for s in slips)
    assert {s["slip"]["question"] for s in slips} == {"player_voice", "hard_no_reworded"}


@pytest.mark.parametrize("s", SCENES, ids=IDS)
def test_every_draft_passes_the_code_checks(pc, s):
    a = ["check", "--scene", pc.write("s.md", s["scene"]), "--packet", pc.packet(reacted), "--ops", pc.write("o.json", OPS),
         "--map", pc.write("m.json", MAP), "--round", str(IDS.index(s["id"]) + 1)]
    r = pc.db(*a)
    assert r.returncode == 0 and "FLAG [" not in r.stdout, r.stdout


@pytest.mark.parametrize("s", SCENES, ids=IDS)
def test_the_quote_of_a_slip_is_in_its_draft_and_a_hard_no_is_not_matched_in_code(s):
    if s["slip"]:
        assert CK.squash(s["slip"]["quote"]) in CK.squash(s["scene"])
    assert CK.phrase_flags(s["scene"], CORPUS["hard_noes"]) == []


@pytest.mark.parametrize("s", SCENES, ids=IDS)
def test_the_checker_brief_holds_the_draft_the_packet_the_noes_and_the_questions_only(pc, s):
    out = pc.db("check-brief", "--scene", pc.write("s.md", s["scene"]), "--packet", pc.packet(reacted)).stdout
    assert s["scene"] in out and all(f"- {p}" in out for p in CORPUS["hard_noes"]) and '"code": "K7Q2MX"' in out
    assert out.count("QUESTIONS") == 1 and out.count("DRAFT") == 1 and out.count("HARD NOES") == 1 and out.count("REACTED PACKET") == 1
    assert s["id"] not in out and (not s["note"] or s["note"] not in out)                              # nothing of the corpus's labels leaks in


@pytest.mark.parametrize("s", SCENES, ids=IDS)
def test_the_right_answer_raises_exactly_the_slip_and_a_clean_draft_raises_nothing(s):
    fl = CK.answer_flags(answers_for(s["slip"]), s["scene"])
    if s["slip"] is None:
        assert fl == []
    else:
        assert [f["code"] for f in fl] == [s["slip"]["question"]] and "not in the draft" not in fl[0]["text"]
