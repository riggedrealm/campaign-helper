"""G6: commit-turn's Campfire memory: the turn record (reactions, the check's flags and rewrites, overruled flags), the fact store, the
ruling log, last gestures, the repetition tracker, and the reversing record of `campfire-undo`. All of it lives in data/ on the GM's
machine (campfire.json, turns.json, cast.json) and none of it is posted."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campfire_pc import Pc  # noqa: E402

SCENE = "Mio Tachibana counts the till twice at the counter.\n\nThe man in the grey coat watches the door and says nothing."
RULINGS = {"rulings": [{"player": "p_7k2m", "kind": "roll", "skill": "Close Quarters Combat", "difficulty": "hard",
                        "target": {"kind": "threat", "id": "grey-coat"}, "stakes": "Disarm him, or he gets a shot off."},
                       {"player": "p_3hx9", "kind": "automatic", "skill": "Observation", "target": None, "stakes": "Nothing hangs on it."}],
           "threat_moves": []}
OPS = [{"op": "note", "evidence": "counts the till twice"}]
REACTIONS = [{"npc": "Mio Tachibana", "kind": "stay", "line": "We're closed."}]
RECORD = {"reactions": REACTIONS, "threat_moves": [{"threat": "grey-coat", "kind": "hold"}],
          "facts": [{"text": "Mio counts the till twice when she is afraid.", "evidence": "counts the till twice", "names": ["Mio Tachibana"],
                     "places": ["the counter"]}],
          "gestures": {"Mio Tachibana": "counts the till twice"}, "results": [{"player": "p_7k2m", "tier": "Success"}]}


def sha(scene):
    return hashlib.sha256(scene.encode("utf-8")).hexdigest()[:12]


def log_for(scene=SCENE, flags=(), attempts=1):
    return {"round": 1, "attempts": [{"attempt": i + 1, "scene_sha": sha(scene if i == attempts - 1 else scene + str(i)), "checker": "answered",
                                      "flags": list(flags) if i == attempts - 1 else [{"code": "x", "severity": "flag", "text": "earlier"}],
                                      "scene": scene if i == attempts - 1 else scene + str(i)} for i in range(attempts)]}


class Cm(Pc):
    def commit(self, scene=SCENE, rulings=RULINGS, ops=OPS, record=RECORD, log="default", *extra):
        t = self.load("state")["turn"] + 1
        payload = {"turn": t, "ops": [], "turn_log": {"inputs": "Aiko checks the rota", "summary": f"summary {t}"}}
        a = ["commit-turn", "--scene", self.write("scene.md", scene), "--rulings", self.write("rulings.json", rulings),
             "--ops", self.write("ops.json", ops), "--payload", self.write("payload.json", payload)]
        if record is not None:
            a += ["--record", self.write("record.json", record)]
        log = log_for(scene) if log == "default" else log
        if log is not None:
            a += ["--check", self.write("check.json", log)]
        return self.db(*a, *extra)

    def store(self):
        return self.load("campfire")


@pytest.fixture
def cm(tmp_path):
    return Cm(tmp_path)


def test_a_commit_records_the_memory(cm):
    r = cm.commit()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 fact(s), 1 gesture(s), check: 0 rewrite(s)" in r.stdout
    c = cm.store()
    assert c["facts"] == [{"id": "F1", "turn": 1, "text": "Mio counts the till twice when she is afraid.", "names": ["Mio Tachibana"],
                           "places": ["the counter"], "evidence": "counts the till twice"}]
    assert [(x["skill"], x["difficulty"], x["target"], x["tier"]) for x in c["rulings"]] == [
        ("Close Quarters Combat", "hard", "threat: grey-coat", "Success"), ("Observation", None, None, None)]
    assert cm.load("cast")["Mio Tachibana"]["intent"]["last_gesture"] == "counts the till twice"
    t = cm.load("turns")[-1]["campfire"]
    assert t["reactions"] == REACTIONS and t["facts"] == ["F1"] and t["rulings_logged"] == 2
    assert t["gestures"]["Mio Tachibana"] == {"was": None, "now": "counts the till twice"}
    assert t["check"]["rewrites"] == 0 and t["check"]["attempts"][0]["scene"] == SCENE
    assert c["repetition"]["turn"] == 1 and c["repetition"]["openings"][0]["text"] == "mio tachibana counts the till twice"


def test_fact_ids_continue_and_the_gesture_it_replaces_is_kept(cm):
    cm.commit()
    scene2 = SCENE + "\n\nShe folds a note into her sleeve."
    rec2 = {**RECORD, "gestures": {}, "facts": [{"text": "Mio hides a note.", "evidence": "folds a note into her sleeve"}]}
    r = cm.commit(scene2, record=rec2, log=log_for(scene2))
    assert r.returncode == 0, r.stdout
    assert [f["id"] for f in cm.store()["facts"]] == ["F1", "F2"]
    g = cm.load("turns")[-1]["campfire"]["gestures"]["Mio Tachibana"]
    assert g == {"was": "counts the till twice", "now": "stayed where they were"}        # no text given: derived from the reaction's kind


def test_the_rewrites_and_every_flag_are_recorded(cm):
    log = log_for(SCENE, attempts=3)
    r = cm.commit(log=log)
    assert r.returncode == 0 and "check: 2 rewrite(s)" in r.stdout
    att = cm.load("turns")[-1]["campfire"]["check"]["attempts"]
    assert len(att) == 3 and att[0]["flags"][0]["text"] == "earlier" and att[0]["scene"].endswith("0")


@pytest.mark.parametrize("mutate,msg", [
    (lambda r: r["facts"][0].update(evidence="a sentence the scene does not hold"), "evidence is not in the posted scene"),
    (lambda r: r["facts"][0].pop("evidence"), "needs evidence"),
    (lambda r: r["facts"][0].update(text="x" * 241), "at most 240"),
    (lambda r: r.update(colour="red"), 'unknown key "colour"'),
    (lambda r: r.update(gestures={"Mio Tachibana": ""}), "record.gestures must be"),
    (lambda r: r.update(overruled=[{"code": "x"}]), "needs a flag code and a reason"),
])
def test_a_bad_record_writes_nothing(cm, mutate, msg):
    rec = json.loads(json.dumps(RECORD))
    mutate(rec)
    before = cm.hashes()
    r = cm.commit(record=rec)
    assert r.returncode == 2 and msg in r.stdout, r.stdout
    assert cm.hashes() == before


def test_the_check_log_must_end_on_the_committed_scene(cm):
    before = cm.hashes()
    r = cm.commit(log=log_for(SCENE + " Changed."))
    assert r.returncode == 2 and "not the draft the check log ended on" in r.stdout
    assert cm.hashes() == before


def test_an_open_flag_needs_an_overruled_reason(cm):
    flag = {"code": "unknown_place", "severity": "flag", "text": "paragraph 1 names a place"}
    before = cm.hashes()
    r = cm.commit(log=log_for(SCENE, [flag]))
    assert r.returncode == 2 and "still raised [unknown_place]" in r.stdout and cm.hashes() == before
    ok = cm.commit(log=log_for(SCENE, [flag, {"code": "repeated_phrase", "severity": "warn", "text": "w"}]),
                   record={**RECORD, "overruled": [{"code": "unknown_place", "reason": "The GM told me the annex exists."}]})
    assert ok.returncode == 0, ok.stdout
    assert cm.load("turns")[-1]["campfire"]["overruled"][0]["reason"].startswith("The GM told me")


def test_without_a_check_log_the_commit_warns_and_records_none(cm):
    r = cm.commit(log=None)
    assert r.returncode == 0 and "WARN no --check log" in r.stdout
    assert cm.load("turns")[-1]["campfire"]["check"] is None


def test_without_a_record_the_rulings_are_still_logged(cm):
    r = cm.commit(record=None, log=None)
    assert r.returncode == 0 and cm.store()["facts"] == [] and len(cm.store()["rulings"]) == 2


def test_a_reacting_npc_outside_the_cast_gets_a_note_and_no_gesture(cm):
    rec = {**RECORD, "reactions": [{"npc": "Nobody At All", "kind": "leave"}], "gestures": {}}
    r = cm.commit(record=rec)
    assert r.returncode == 0 and '"Nobody At All" is not a cast NPC' in r.stdout


def test_dry_run_writes_nothing(cm):
    before = cm.hashes()
    r = cm.commit(SCENE, RULINGS, OPS, RECORD, "default", "--dry-run")
    assert r.returncode == 0 and "dry run OK" in r.stdout and cm.hashes() == before and not (cm.data / "campfire.json").exists()


def test_the_tracker_names_stock_phrases_and_check_warns(cm):
    phrase = "the lights flicker twice and everyone freezes."
    for i in range(3):
        s = f"Scene number {['one', 'two', 'three'][i]} begins. Then {phrase}"
        assert cm.commit(s, log=log_for(s), record={"reactions": []}).returncode == 0
    stock = [x["phrase"] for x in cm.store()["repetition"]["stock"]]
    assert "the lights flicker twice" in stock or "lights flicker twice and" in stock
    draft = "Dawn comes slowly. Later, the lights flicker twice and everyone freezes."
    out = cm.db("check", "--scene", cm.write("d.md", draft), "--packet", cm.packet(), "--round", "9").stdout
    assert "WARN [repeated_phrase]" in out


def test_campfire_undo_restores_and_writes_the_reversing_record(cm):
    cm.commit()
    assert cm.load("cast")["Mio Tachibana"]["intent"]["last_gesture"]
    r = cm.db("campfire-undo", "--turn", "1", "--reason", "The GM undid the post on the server.")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cm.load("state")["turn"] == 0 and "intent" not in cm.load("cast")["Mio Tachibana"]
    c = cm.store()
    assert c["facts"] == [] and c["rulings"] == [] and len(c["reversals"]) == 1
    rv = c["reversals"][0]
    assert rv["turn"] == 1 and rv["reason"].startswith("The GM undid") and rv["record"]["scene"] == SCENE
    assert rv["reversed"]["facts"] == ["F1"] and rv["reversed"]["gestures"]["Mio Tachibana"]["now"] == "counts the till twice"
    assert cm.commit().returncode == 0 and [f["id"] for f in cm.store()["facts"]] == ["F1"]       # the turn can be committed again


def test_campfire_undo_only_takes_the_latest_campfire_turn(cm):
    cm.commit()
    cm.commit(SCENE + "\n\nMore.", log=log_for(SCENE + "\n\nMore."))
    r = cm.db("campfire-undo", "--turn", "1", "--reason", "x")
    assert r.returncode != 0 and "only the latest turn" in r.stdout + r.stderr
    assert cm.db("campfire-undo", "--turn", "2", "--reason", " ").returncode == 2


def test_the_store_shape_is_verified():
    import importlib.util
    spec = importlib.util.spec_from_file_location("dbmod2", Path(__file__).resolve().parent.parent / "tools" / "db.py")
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    assert db.campfire_store_problems(db.campfire_skeleton()) == []
    sk = db.campfire_skeleton()
    sk["facts"] = [{"id": "F1", "text": "a", "turn": 1}, {"id": "F1", "text": "b", "turn": 1}]
    assert any("appears twice" in m for m in db.campfire_store_problems(sk))
    assert db.campfire_store_problems([]) == ["campfire.json must be an object"]
