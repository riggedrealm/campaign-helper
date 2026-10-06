"""`prep --packet FILE`: the Campfire round packet as prep's input. Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA);
the room-code warnings run on a tmp repo root (VOYAGE_ROOT)."""
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
REAL_DATA = REAL / "data"
PACKET = REPO / "tests" / "fixtures" / "campfire-round.json"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": "classroom-2b", "PYTHONDONTWRITEBYTECODE": "1"})
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def packet(self, mutate=None):
        """The fixture packet (optionally changed by `mutate(dict)`) written to a tmp file; returns its path."""
        p = json.loads(PACKET.read_text(encoding="utf-8"))
        if mutate:
            mutate(p)
        f = self.tmp / "packet.json"
        f.write_text(json.dumps(p), encoding="utf-8")
        return f

    def prep(self, *args, mutate=None):
        r = self.run("prep", "--packet", self.packet(mutate), *args)
        assert r.returncode == 0, r.stderr + r.stdout
        return r.stdout


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr
    return e


def line(out, prefix):
    return next(l for l in out.splitlines() if l.startswith(prefix))


def unknown_block(out):
    """The lines under `Not in the database:`."""
    ls = out.splitlines()
    i = ls.index("Not in the database:")
    block = []
    for l in ls[i + 1:]:
        if not l.startswith("  - "):
            break
        block.append(l)
    return block


# ---- names from the packet's data ---------------------------------------------
def test_briefs_for_scene_npc_and_declared_alias(env):
    out = env.prep()
    present = line(out, "PRESENT:")
    assert "Mio Tachibana (scene)" in present and "Park Seo-yeon (declared)" in present  # "Sunny" is an alias
    assert "voice:" in out and "won't yet:" in out and "beat A" in out
    assert out.count("  voice:") == 2


def test_prose_mention_is_not_scanned(env):
    out = env.prep()
    assert "Tatsuya" in PACKET.read_text(encoding="utf-8")
    assert "Tatsuya" not in line(out, "PRESENT:") and "Tatsuya Ōmine [" not in out
    assert "Aiko Tanaka (" not in line(out, "PRESENT:")  # a PC is not an NPC


def test_names_flag_adds_to_the_packet_names(env):
    present = line(env.prep("--names", "Tatsuya"), "PRESENT:")
    assert "Tatsuya Ōmine (--names)" in present and "Mio Tachibana (scene)" in present


def test_ambiguous_name_warns(env):
    cast = env.load("cast")
    cast["Mio Hayashi"] = dict(cast["Mio Tachibana"])  # a second Mio: the short name is now ambiguous
    env.save_json("cast", cast)
    out = env.prep(mutate=lambda p: p["scene"]["npcs"].append({"name": "Mio", "attitude": "calm"}))
    assert any(l.startswith("WARN: AMBIGUOUS name Mio:") for l in out.splitlines())
    assert not any("NPC Mio " in l for l in unknown_block(out))


def test_main_npcs_beyond_four_are_one_liners(env):
    names = ["Mio Tachibana", "Tatsuya Ōmine", "Shin Asakura", "Park Seo-yeon", "Kenji Arimura", "Reiko Shimazu"]
    out = env.prep(mutate=lambda p: p["scene"].update(npcs=[{"name": n, "attitude": "calm"} for n in names]))
    assert out.count("  voice:") == 4 and "more main NPCs shown as one-liners" in out


# ---- what the database does not know ------------------------------------------
def test_unknown_things_are_flagged(env):
    out = env.prep()
    assert "Not in the database:" in out
    block = "\n".join(unknown_block(out))
    assert "NPC Mr. Hasegawa (scene NPC)" in block
    assert "NPC Detective Sato (declared target of Yuna)" in block
    assert "quest The Stolen Receipts" in block
    assert "party member Ren Okabe" in block and "party member Yuna" in block
    assert "Page Turner Books" not in block and "Mio Tachibana" not in block and "Sunny" not in block and "Aiko" not in block


def test_unknown_location_is_flagged_and_area_forms_pass(env):
    out = env.prep(mutate=lambda p: p["scene"].update(location="Nowhere Annex"))
    assert any("location Nowhere Annex" in l for l in unknown_block(out))
    for form in ("Page Turner Books/back-room", "Page Turner Books, back room", "page turner books"):
        out = env.prep(mutate=lambda p, f=form: p["scene"].update(location=f))
        assert "Not in the database:" not in out or not any("location" in l for l in unknown_block(out))


def test_nothing_unknown_omits_the_heading(env):
    def clean(p):
        p["scene"]["npcs"] = [{"name": "Mio Tachibana", "attitude": "wary"}]
        p["inputs"] = [x for x in p["inputs"] if x["name"] == "Aiko Tanaka"]
        p["party"] = p["party"][:1]
        p["quests"] = []
    assert "Not in the database" not in env.prep(mutate=clean)


def test_a_packet_quest_matching_an_active_quest_gets_the_goal_line(env):
    key = next(iter(env.load("quests")))
    st = env.load("state")
    st["active_quests"] = [key]
    env.save_json("state", st)
    out = env.prep(mutate=lambda p: p.update(quests=[{"id": "x", "title": key.upper(), "status": "active"}]))
    assert f"Quest mentioned: {key}" in out
    assert "surface goal" in out or "no surface goal set" in out
    assert "Not in the database" not in out or "quest" not in "\n".join(unknown_block(out))


# ---- party, inputs, fight -------------------------------------------------------
def test_party_input_and_fight_lines(env):
    out = env.prep()
    assert "PC Aiko Tanaka, level 3 Initiate" in out and "(not in the database: pc-add)" in line(out, "PC Ren Okabe")
    assert 'Aiko Tanaka: "I vault the counter and go for the grey coat\'s wrist." [declared: skill Close Quarters Combat, target threat grey-coat]' in out
    assert line(out, "Ren Okabe:").endswith("[declared: skill persuasion, target Sunny] (target attitude: wary)")
    assert line(out, "Yuna:").endswith("[declared: target Detective Sato] (early)")
    assert "Fight: the man in the grey coat (standard), clock 1/5 [active]" in out
    assert "Missing:" not in out


def test_missing_and_no_threat(env):
    def m(p):
        p["missing"] = [{"player": "p_x", "name": "Hana"}, {"player": "p_y", "name": "Kei"}]
        p["threats"] = []
    out = env.prep(mutate=m)
    assert "Missing: Hana, Kei" in out and "Fight: no live threat" in out


def test_ability_declaration(env):
    def m(p):
        p["inputs"][0]["declared"] = {"ability": "Iron Wind"}
    assert line(env.prep(mutate=m), "Aiko Tanaka:").endswith('[declared: ability Iron Wind]')


def test_party_first_name_matches_the_character(env):
    out = env.prep(mutate=lambda p: p["party"][1].update(name="Aiko"))
    assert "party member Aiko" not in out


def test_header_and_no_prompt_budget_or_fight_unknown(env):
    out = env.prep()
    assert "Prompt budget" not in out and "fight status unknown" not in out
    assert line(out, "Packet:") == ('Packet: round 4, phase ruling, room K7Q2MX | scene "Closing Time" @ Page Turner Books, Tuesday, evening, '
                                    'mood uneasy, surprise used: no | NPCs: Mio Tachibana (wary), Mr. Hasegawa (friendly)')
    assert line(out, "PREP ").startswith("PREP Class 2B | turn 0") and "LIVE CHECKLIST" in out and "PCs: " in out


def test_fight_unknown_line_never_appears_with_a_fighting_scene(env):
    env.run("scene-start", "Brawl", "--location", "Sakura Lane Sharehouse", "--area", "shared-kitchen", "--kind", "fight")
    out = env.prep()
    assert "fight status unknown" not in out and "Fight: the man in the grey coat" in out


def test_full_works_in_packet_mode(env):
    out = env.prep("--full", "Mio")
    assert "Mio Tachibana" in out.split("LIVE CHECKLIST", 1)[1]
    r = env.run("prep", "--packet", env.packet(), "--full", "Nobody Atall")
    assert r.returncode == 2


def test_is_read_only(env):
    before = {p.name: p.read_bytes() for p in env.data.glob("*.json")}
    env.prep()
    assert before == {p.name: p.read_bytes() for p in env.data.glob("*.json")}


# ---- refusals -------------------------------------------------------------------
def test_paste_with_packet_exits_2(env):
    paste = env.tmp / "paste.txt"
    paste.write_text("hello", encoding="utf-8")
    r = env.run("prep", "--paste", paste, "--packet", env.packet())
    assert r.returncode == 2 and "--packet" in (r.stderr + r.stdout) and "--paste" in (r.stderr + r.stdout)


@pytest.mark.parametrize("bad, word", [
    (lambda p: [1, 2], "object"),
    (lambda p: {**p, "room": "x"}, "room"),
    (lambda p: {**p, "scene": []}, "scene"),
    (lambda p: {**p, "party": {}}, "party"),
    (lambda p: {**p, "threats": None}, "threats"),
    (lambda p: {**p, "inputs": "x"}, "inputs"),
    (lambda p: {**p, "inputs": [{"name": "A"}]}, "inputs[0]"),
    (lambda p: {**p, "inputs": [{"name": 3, "text": "x"}]}, "inputs[0]"),
    (lambda p: {k: v for k, v in p.items() if k != "scene"}, "scene"),
])
def test_wrong_shapes_exit_2(env, bad, word):
    f = env.tmp / "bad.json"
    f.write_text(json.dumps(bad(json.loads(PACKET.read_text(encoding="utf-8")))), encoding="utf-8")
    r = env.run("prep", "--packet", f)
    assert r.returncode == 2 and word in (r.stderr + r.stdout)


def test_missing_file_and_invalid_json_exit_2(env):
    r = env.run("prep", "--packet", env.tmp / "nope.json")
    assert r.returncode == 2 and "no such packet file" in (r.stderr + r.stdout)
    f = env.tmp / "junk.json"
    f.write_text("{not json", encoding="utf-8")
    r = env.run("prep", "--packet", f)
    assert r.returncode == 2 and "not valid JSON" in (r.stderr + r.stdout)


# ---- the room check ---------------------------------------------------------------
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
    return root


def run_root(root, *args):
    e = {k: v for k, v in os.environ.items()
         if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_ROOT")}
    e.update({"PYTHONDONTWRITEBYTECODE": "1", "VOYAGE_ROOT": str(root)})
    return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=root)


def test_no_room_in_campaign_json_warns_mode_off(env):
    out = env.prep()
    assert "WARN: campaign.json names no Campfire room code (campfire_room): Campfire mode is off for this campaign" in out


@pytest.mark.parametrize("room, warn", [
    ("K7Q2MX", None),
    ("ABCDEF", "WARN: packet room K7Q2MX is not this campaign's room ABCDEF"),
    (None, "Campfire mode is off for this campaign"),
    ("bad", "Campfire mode is off for this campaign"),
])
def test_room_code_warnings(tmp_path, room, warn):
    root = make_root(tmp_path, room)
    r = run_root(root, "prep", "--packet", PACKET)
    assert r.returncode == 0, r.stderr + r.stdout
    out = r.stdout
    assert "Packet: round 4" in out  # prep still prints
    if warn:
        assert warn in out
    else:
        assert "WARN: packet room" not in out and "Campfire mode is off" not in out


# ---- paste mode and the seam --------------------------------------------------------
def test_paste_mode_is_unchanged(env):
    paste = env.tmp / "paste.txt"
    paste.write_text("Sunny flopped on the sofa. Mio sighed.", encoding="utf-8")
    r = env.run("prep", "--paste", paste)
    assert r.returncode == 0, r.stderr
    assert "Prompt budget: limit 840" in r.stdout and "Packet:" not in r.stdout and "Not in the database" not in r.stdout
    assert "PRESENT: " in r.stdout and "Park Seo-yeon (paste)" in r.stdout
