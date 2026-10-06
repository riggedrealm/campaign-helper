"""commit-turn --scene (Campfire mode): the hidden-words check on the scene and the stakes lines, the scene / rulings / Campfire ops
recorded with the turn, and the "skipped in Campfire mode" notes. Runs on a tmp repo root (VOYAGE_ROOT) holding a copy of classroom-2b."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL = REPO / "campaigns" / "classroom-2b"
SCENE = "Mio Tachibana counts coins twice at the kitchen table. Tatsuya Ōmine pins the chore rota to the fridge and says nothing."
RULINGS = {"rulings": [{"input": "Aiko checks the rota", "stakes": "A glance costs a minute; the rota stays put."}], "threat_moves": []}
OPS = [{"op": "note", "evidence": "the scene as posted"}]
NEXT_LINE = 'Next: on the GM\'s next "send" or "draft", run prep --packet on the new round packet (director/playbooks/campfire.md).'


def plain_env(**extra):
    e = {k: v for k, v in os.environ.items()
         if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_ROOT")}
    e.update({"PYTHONDONTWRITEBYTECODE": "1", **extra})
    return e


def make_root(tmp_path, room):
    """A tmp repo root with campaign `demo`, a copy of classroom-2b whose campaign.json names the room code (None: no field)."""
    root = tmp_path / "root"
    cdir = root / "campaigns" / "demo"
    shutil.copytree(REAL / "data", cdir / "data", ignore=shutil.ignore_patterns(".lock", ".snap*", ".turn-clock*"))
    for f in ("arc-bible.md", "README.md", "director.md"):
        shutil.copy(REAL / f, cdir / f)
    cfg = json.loads((REAL / "campaign.json").read_text(encoding="utf-8"))
    cfg["name"] = "demo"
    cfg["skill_dir"] = ".claude/skills/demo-director"
    if room is not None:
        cfg["campfire_room"] = room
    (cdir / "campaign.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    sdir = root / ".claude" / "skills" / "demo-director"
    sdir.mkdir(parents=True)
    shutil.copy(REPO / ".claude" / "skills" / "class2b-director" / "SKILL.md", sdir / "SKILL.md")
    return root, cdir


def run(root, *args, tool=DB):
    return subprocess.run([sys.executable, str(tool), *map(str, args)], capture_output=True, text=True,
                          env=plain_env(VOYAGE_ROOT=str(root)), cwd=root)


class Cf:
    def __init__(self, tmp_path, room="K7Q2MX"):
        self.tmp = tmp_path
        self.root, self.cdir = make_root(tmp_path, room)
        self.data = self.cdir / "data"
        th = self.load("threads")
        k = next(iter(th))
        th[k]["steps"][0].update({"keywords": ["Zebrafish"], "status": "hidden"})  # a strong secret term
        self.save("threads", th)
        r = self.db("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
        assert r.returncode == 0, r.stderr

    def db(self, *args):
        return run(self.root, "--campaign", "demo", *args)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text if isinstance(text, str) else json.dumps(text), encoding="utf-8")
        return f

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}

    def commit(self, scene=SCENE, rulings=RULINGS, ops=OPS, payload=None, *args):
        t = self.load("state")["turn"] + 1
        payload = {"turn": t, "ops": [], "turn_log": {"inputs": "Aiko checks the rota", "summary": f"summary {t}"}, **(payload or {})}
        return self.db("commit-turn", "--scene", self.write("scene.md", scene), "--rulings", self.write("rulings.json", rulings),
                       "--ops", self.write("ops.json", ops), "--payload", self.write("payload.json", payload), *args)


@pytest.fixture
def cf(tmp_path):
    return Cf(tmp_path)


def test_a_good_campfire_commit_records_the_turn(cf):
    r = cf.commit()
    print(r.stdout)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "hidden-words check:\n  ok: scene and 1 stakes line(s) carry no hidden term" in r.stdout
    assert f"scene {len(SCENE)} chars, 1 ruling(s), 1 Campfire op(s)" in r.stdout and "prompt " not in r.stdout
    assert "NEXT BRIEF" not in r.stdout and r.stdout.strip().splitlines()[-1] == NEXT_LINE
    assert cf.load("state")["turn"] == 1
    t = cf.load("turns")[-1]
    assert t["scene"] == SCENE and t["rulings"] == RULINGS and t["campfire_ops"] == OPS
    assert t["prompt"] == "none (Campfire mode: the posted scene is the record)"
    assert t["inputs"] == "Aiko checks the rota" and "timing" in t


def test_a_strong_term_in_the_scene_fails_and_writes_nothing(cf):
    before = cf.hashes()
    r = cf.commit(scene=SCENE + " A zebrafish drifts past the window.")
    print(r.stdout)
    assert r.returncode == 1
    assert 'FAIL: hidden term "zebrafish"' in r.stdout and "in scene" in r.stdout
    assert "commit-turn: FAIL in the scene or a stakes line; nothing written. The scene may already be posted: tell the GM. " \
           "--allow TERM only for a term that is public." in r.stdout
    assert cf.hashes() == before


def test_a_strong_term_in_a_stakes_line_names_it(cf):
    before = cf.hashes()
    rul = {"rulings": [{"stakes": "fine"}, {"stakes": "The Zebrafish is at risk."}]}
    r = cf.commit(rulings=rul)
    assert r.returncode == 1 and "rulings[1].stakes" in r.stdout and "rulings[0]" not in r.stdout
    assert cf.hashes() == before


def test_allow_lets_a_public_term_through(cf):
    r = cf.commit(SCENE + " A zebrafish drifts past the window.", RULINGS, OPS, None, "--allow", "Zebrafish, other")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout and cf.load("state")["turn"] == 1


def test_a_campaign_hidden_word_fails_like_scan(cf):
    before = cf.hashes()
    r = cf.commit(scene=SCENE + " Nobody mentions the ledger.")
    assert r.returncode == 1 and 'FAIL: hidden term "ledger" (campaign hidden word) in scene' in r.stdout, r.stdout
    assert cf.hashes() == before
    r = cf.commit(SCENE + " Nobody mentions the ledger.", RULINGS, OPS, None, "--allow", "Ledger")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cf.load("state")["turn"] == 1


def test_a_soft_secret_term_only_warns(cf):
    th = cf.load("threads")
    k = next(iter(th))
    th[k]["steps"][1].update({"keywords": ["Quokka"], "status": "hidden"})
    cf.save("threads", th)
    cfg_path = cf.cdir / "campaign.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("secrets", {})["soft_terms"] = ["quokka"]
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    r = cf.commit(scene=SCENE + " A quokka sticker is on the fridge.")
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'WARN: "quokka" is also a term in' in r.stdout and "FAIL" not in r.stdout and "  ok:" not in r.stdout
    assert cf.load("state")["turn"] == 1


def test_scene_without_a_room_code_is_refused(tmp_path):
    cf = Cf(tmp_path, room=None)
    before = cf.hashes()
    r = cf.commit()
    assert r.returncode == 4
    assert "commit-turn --scene refused: campaign.json names no Campfire room code (campfire_room), so Campfire mode is off. " \
           "Nothing was written." in r.stdout + r.stderr
    assert cf.hashes() == before


def test_prompt_and_scene_together_exit_2(cf):
    before = cf.hashes()
    r = cf.db("commit-turn", "--prompt", cf.write("p.txt", "x"), "--scene", cf.write("s.md", SCENE), "--rulings", cf.write("r.json", RULINGS),
              "--ops", cf.write("o.json", OPS), "--payload", cf.write("pl.json", {}))
    assert r.returncode == 2 and cf.hashes() == before
    r = cf.db("commit-turn", "--payload", cf.write("pl.json", {}))  # neither
    assert r.returncode == 2


def test_scene_needs_rulings_and_ops_and_prompt_refuses_them(cf):
    r = cf.db("commit-turn", "--scene", cf.write("s.md", SCENE), "--ops", cf.write("o.json", OPS), "--payload", cf.write("pl.json", {}))
    assert r.returncode == 2 and "--rulings" in r.stdout + r.stderr
    r = cf.db("commit-turn", "--scene", cf.write("s.md", SCENE), "--rulings", cf.write("r.json", RULINGS), "--payload", cf.write("pl.json", {}))
    assert r.returncode == 2 and "--ops" in r.stdout + r.stderr
    r = cf.db("commit-turn", "--prompt", cf.write("p.txt", "x"), "--rulings", cf.write("r.json", RULINGS), "--payload", cf.write("pl.json", {}))
    assert r.returncode == 2


@pytest.mark.parametrize("scene,rulings,ops,needle", [
    ("   \n", RULINGS, OPS, "scene file is empty"),
    (SCENE, "{not json", OPS, "rulings file is not valid JSON"),
    (SCENE, ["a"], OPS, '"rulings" list'),
    (SCENE, {"rulings": ["x"]}, OPS, "rulings[0] must be an object"),
    (SCENE, {"rulings": [{"stakes": 5}]}, OPS, "rulings[0].stakes must be a string"),
    (SCENE, {"rulings": [], "threat_moves": "no"}, OPS, "threat_moves"),
    (SCENE, RULINGS, "[oops", "ops file is not valid JSON"),
    (SCENE, RULINGS, {"op": "x"}, "ops file must be a JSON list"),
    (SCENE, RULINGS, [{"evidence": "e"}], "ops[0] must be an object with a string 'op'"),
])
def test_malformed_campfire_files_exit_2_and_write_nothing(cf, scene, rulings, ops, needle):
    before = cf.hashes()
    r = cf.commit(scene, rulings, ops)
    assert r.returncode == 2 and needle in r.stdout, r.stdout + r.stderr
    assert cf.hashes() == before


def test_a_missing_file_exits_2(cf):
    r = cf.db("commit-turn", "--scene", str(cf.tmp / "nope.md"), "--rulings", cf.write("r.json", RULINGS), "--ops", cf.write("o.json", OPS),
              "--payload", cf.write("pl.json", {}))
    assert r.returncode == 2 and "cannot read the scene file" in r.stdout


def test_dry_run_writes_nothing(cf):
    before = cf.hashes()
    r = cf.commit(SCENE, RULINGS, OPS, None, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "dry run OK" in r.stdout and f"scene {len(SCENE)} chars, 1 ruling(s), 1 Campfire op(s)" in r.stdout and "nothing written." in r.stdout
    assert cf.hashes() == before


def test_present_comes_from_the_npc_names_in_the_scene(cf):
    assert cf.db("scene-start", "Kitchen", "--budget", "4", "--turn", "1", "--evidence", "x").returncode == 0
    r = cf.commit()
    assert r.returncode == 0, r.stdout + r.stderr
    st = cf.load("state")
    assert st["scene"]["present"] == ["Mio Tachibana", "Tatsuya Ōmine"] and "Aiko Tanaka" not in st["scene"]["present"]
    assert not st.get("expression")  # no rotation in Campfire mode
    assert "present: Mio Tachibana, Tatsuya Ōmine" in r.stdout and "rotation" not in r.stdout


def test_payload_present_wins_over_the_scene_text(cf):
    cf.db("scene-start", "Kitchen", "--budget", "4", "--turn", "1", "--evidence", "x")
    r = cf.commit(payload={"present": ["Kenji Arimura"]})
    assert r.returncode == 0, r.stdout + r.stderr
    assert cf.load("state")["scene"]["present"] == ["Kenji Arimura"]


def test_a_hand_written_turn_log_scene_is_refused(cf):
    before = cf.hashes()
    for key in ("scene", "rulings", "campfire_ops", "scene_text"):
        r = cf.commit(payload={"turn_log": {"inputs": "i", "summary": "s", key: "x"}})
        assert r.returncode == 2 and f"turn_log: unknown key '{key}'" in r.stdout, (key, r.stdout)
    assert cf.hashes() == before
    p = cf.write("rec.json", {"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "none", "scene": "x"}})
    assert cf.db("record", p).returncode == 2


def test_notes_only_with_a_room_code(tmp_path):
    on, off = Cf(tmp_path / "a"), Cf(tmp_path / "b", room=None)
    f = on.write("prompt.txt", "Cut: Continue.\nWorld: A bell rings.")
    r = on.db("check-prompt", f)
    assert r.stdout.split("\n", 1)[1].startswith("NOTE: Campfire mode (campaign.json campfire_room): check-prompt and the prompt limit are skipped; "
                               "commit-turn --scene runs the hidden-words check on the scene and the stakes lines (director/playbooks/campfire.md).\n")
    assert "Length:" in r.stdout
    assert "NOTE: Campfire" not in off.db("check-prompt", off.write("prompt.txt", "Cut: Continue.\nWorld: A bell rings.")).stdout
    note = "NOTE: Campfire mode: the steering brief is skipped; run prep --packet on the round packet (director/playbooks/campfire.md)."
    for extra in ([], ["--full"]):
        assert on.db("turn-brief", *extra).stdout.split("\n", 1)[1].startswith(note + "\n")
        assert "NOTE: Campfire" not in off.db("turn-brief", *extra).stdout
    assert "(skipped in Campfire mode)" in on.db("state").stdout and "(skipped in Campfire mode)" not in off.db("state").stdout
    assert "(skipped in Campfire mode)" in on.db("prep").stdout and "(skipped in Campfire mode)" not in off.db("prep").stdout
