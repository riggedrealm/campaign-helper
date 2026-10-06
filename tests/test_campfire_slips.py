"""A1 of the GDD v2 test plan: the slip corpus in check/fixtures/slips (one reacted packet, a clean control and seven slips). The code half is
run for real: the control passes every code check, the zone, NPC-line and number slips are flagged by their state check alone, and the others
pass the code checks (the checker's to catch). The checker half is the brief it gets; the gate runs the checker over the corpus."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import campfire_check as CK  # noqa: E402
from campfire_pc import Pc  # noqa: E402

DIR = Path(__file__).resolve().parent.parent / "check" / "fixtures" / "slips"
MANIFEST = json.loads((DIR / "manifest.json").read_text(encoding="utf-8"))["drafts"]
IDS = [d["id"] for d in MANIFEST]
CODES = [c for c, _q, _bad in CK.QUESTIONS]


def draft(d):
    return (DIR / "drafts" / f"{d['id']}.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pc(tmp_path_factory):
    return Pc(tmp_path_factory.mktemp("slips"))


def run_check(pc, d):
    a = ["check", "--scene", pc.write("s.md", draft(d)), "--packet", str(DIR / "packet.json"), "--ops", str(DIR / "ops.json"),
         "--map", str(DIR / "map.json"), "--round", "4", "--reset"]
    return pc.db(*a)


def test_the_corpus_is_one_control_and_seven_slips():
    assert len(MANIFEST) == 8 and len(set(IDS)) == 8
    assert [d["id"] for d in MANIFEST if d["slip"] is None] == ["00-control"]
    assert all(d["slip"]["question"] in CODES for d in MANIFEST if d["slip"])
    assert {d["slip"]["question"] for d in MANIFEST if d["slip"]} == {"player_voice", "tier_mismatch", "number_mismatch", "npc_off_reaction", "wrong_place"}


@pytest.mark.parametrize("d", MANIFEST, ids=IDS)
def test_the_quote_of_a_slip_is_in_its_draft(d):
    if d["slip"]:
        assert CK.squash(d["slip"]["quote"]) in CK.squash(draft(d))


@pytest.mark.parametrize("d", MANIFEST, ids=IDS)
def test_code_flags_the_zone_npc_line_and_number_slips_and_passes_the_rest(pc, d):
    r = run_check(pc, d)
    got = re.findall(r"FLAG \[(\w+)\]", r.stdout)
    if d["code_catches"]:
        assert r.returncode == 1 and got == [d["code_catches"]], r.stdout
    else:
        assert r.returncode == 0 and got == [], r.stdout


def test_code_flags_the_number_slip_by_itself_and_no_other_draft(pc):
    n = next(d for d in MANIFEST if d["id"] == "07-number")
    r = run_check(pc, n)
    assert r.returncode == 1 and re.findall(r"FLAG \[(\w+)\]", r.stdout) == ["number_mismatch"], r.stdout
    assert "down to forty health" in r.stdout
    for d in MANIFEST:
        if d is not n:
            assert "number_mismatch" not in run_check(pc, d).stdout, d["id"]


@pytest.mark.parametrize("d", MANIFEST, ids=IDS)
def test_the_right_answer_raises_exactly_the_slip_and_the_control_raises_nothing(d):
    out = []
    for i, (code, _q, bad) in enumerate(CK.QUESTIONS, 1):
        hit = d["slip"] is not None and d["slip"]["question"] == code
        out.append({"q": i, "answer": bad if hit else ("no" if bad == "yes" else "yes"), "quote": d["slip"]["quote"] if hit else ""})
    fl = CK.answer_flags({"answers": out}, draft(d))
    assert [f["code"] for f in fl] == ([d["slip"]["question"]] if d["slip"] else [])


@pytest.mark.parametrize("d", MANIFEST, ids=IDS)
def test_the_checker_brief_holds_the_draft_and_no_label_of_the_corpus(pc, d):
    out = pc.db("check-brief", "--scene", pc.write("s.md", draft(d)), "--packet", str(DIR / "packet.json")).stdout
    assert draft(d).rstrip("\n") in out and out.count("DRAFT") == 1
    assert d["id"] not in out and d["note"] not in out
