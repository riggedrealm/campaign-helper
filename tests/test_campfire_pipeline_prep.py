"""G2 and G7: prep --packet in the pipeline: the hard noes matched against the inputs in code, the director layer, memory retrieved by the
packet's names and places (facts, turn records), precedent from the ruling log, and the repetition tracker. Read-only, secret, local."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_campfire_memory import Cm, RECORD, SCENE, log_for  # noqa: E402


@pytest.fixture
def cm(tmp_path):
    return Cm(tmp_path)


def prep(cm, mutate=None):
    r = cm.db("prep", "--packet", cm.packet(mutate))
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_prep_is_read_only(cm):
    before = cm.hashes()
    prep(cm)
    assert cm.hashes() == before


def test_hard_noes_none_set_clean_and_hit(cm):
    assert "Hard noes: none set" in prep(cm)
    cm.db("hard-noes", "--add", "wrist", "--add", "never said")
    out = prep(cm)
    assert "Hard noes: 2 phrase(s); 1 HIT" in out and "HIT: Aiko Tanaka's input contains \"wrist\"" in out
    clean = prep(cm, lambda p: p["inputs"][0].update(text="I vault the counter."))
    assert "no input touches one" in clean and "HIT" not in clean


def test_the_director_layer(cm):
    out = prep(cm, lambda p: p["scene"]["npcs"].append({"name": "Mio Tachibana", "attitude": "wary"}))
    assert "DIRECTOR LAYER (secret; never posted)" in out and "arc: none live" in out
    assert "scene budget: no scene open" in out
    assert "ladder Mio's secret: next hidden step 1" in out and "keep it out of the scene" in out
    assert "She is hiding money trouble." not in out and "debt to a criminal lender" not in out        # a hidden step's text is never printed


def test_memory_by_names_and_places_and_recent_turns(cm):
    assert "MEMORY" not in prep(cm)
    assert cm.commit().returncode == 0
    out = prep(cm, lambda p: p["scene"]["npcs"].append({"name": "Mio Tachibana", "attitude": "wary"}))
    assert "F1 (t1): Mio counts the till twice when she is afraid." in out
    assert "RECENT TURNS" in out and "T1: summary 1" in out
    unrelated = prep(cm, lambda p: (p["scene"]["npcs"].clear(), p["scene"].update(location="Elsewhere"), p["threats"].clear(),
                                    p["party"][0].update(name="Zed"), p["inputs"].clear()))
    assert "F1" not in unrelated and "T1: summary 1" in unrelated                                      # the latest turns always show


def test_older_turns_show_only_when_they_mention_the_names(cm):
    for i in range(5):
        s = f"Mio Tachibana nods {i}." if i == 0 else f"A quiet beat number {i}."
        assert cm.commit(s, log=log_for(s), record={"reactions": []}).returncode == 0
    t = cm.load("turns")
    t[0]["summary"] = "Mio Tachibana owes the landlord."
    cm.save("turns", t)
    out = prep(cm)
    assert "T1: Mio Tachibana owes the landlord." in out and "T5: summary 5" in out
    other = prep(cm, lambda p: (p["scene"]["npcs"].clear(), p["threats"].clear()))
    assert "T1:" not in other.split("RECENT TURNS")[1].split("LIVE CHECKLIST")[0]


def test_precedent_is_the_last_ruling_on_each_skill_in_play(cm):
    assert "Precedent" not in prep(cm)
    cm.commit()
    s2 = SCENE + "\n\nA second beat."
    rul2 = {"rulings": [{"player": "p_7k2m", "kind": "roll", "skill": "Close Quarters Combat", "difficulty": "easy",
                         "target": {"kind": "npc", "name": "Mio"}, "stakes": "Second time."}]}
    assert cm.commit(s2, rul2, log=log_for(s2), record={"reactions": []}).returncode == 0
    out = prep(cm)
    lines = [ln for ln in out.splitlines() if ln.startswith("Precedent")]
    assert any("Close Quarters Combat, turn 2): roll, easy, target npc: Mio | Second time." in ln for ln in lines)
    assert not any("turn 1): roll, hard" in ln for ln in lines)                                        # only the last ruling per skill
    assert not any("Observation" in ln for ln in lines)                                                # not a skill in play this round
    assert "Observation" in prep(cm, lambda p: p["inputs"][0]["declared"].update(skill="Observation"))


def test_the_tracker_shows_what_to_avoid(cm):
    assert "AVOID" not in prep(cm)
    phrase = "the lights flicker twice and everyone freezes."
    for i, n in enumerate(("one", "two", "three")):
        s = f"Scene {n} begins. Then {phrase}"
        assert cm.commit(s, log=log_for(s), record={"reactions": []}).returncode == 0
    out = prep(cm)
    assert "AVOID (stock phrases of the last scenes):" in out and "Last openings:" in out


def test_last_gestures_reach_the_compact_brief(cm):
    cm.commit()
    out = prep(cm, lambda p: p["scene"]["npcs"].append({"name": "Mio Tachibana", "attitude": "wary"}))
    assert "last gesture: counts the till twice" in out
