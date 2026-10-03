"""Tests for the director template, tools/new_campaign.py and tools/sync_skill.py (everything runs in a tmp root)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
FIXTURE = REPO / "tests" / "fixtures" / "mini_world.json"
SKILL_LIMIT = 13000
sys.path.insert(0, str(TOOLS))
import skilltpl  # noqa: E402


def clean_env(**extra):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    e.update(extra)
    return e


def run(script, *args, root=None, cwd=None):
    env = clean_env(**({"VOYAGE_ROOT": str(root)} if root else {}))
    return subprocess.run([sys.executable, str(TOOLS / script), *map(str, args)], capture_output=True, text=True,
                          env=env, cwd=cwd or root or REPO)


def db(root, name, *args):
    return run("db.py", "--campaign", name, *args, root=root)


def scaffold(tmp_path, *flags, name="harbor-nights", world=True):
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    args = [name, "--display", "Harbor Nights", "--root", root, *flags]
    if world:
        args += ["--world", FIXTURE]
    r = run("new_campaign.py", *args, root=root)
    return root, r


def skill_path(root, name="harbor-nights"):
    return root / ".claude" / "skills" / f"{name}-director" / "SKILL.md"


# ---- Class 2B is built from the template -----------------------------------------------------
def test_class2b_skill_in_sync_with_template():
    r = run("sync_skill.py", "classroom-2b", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "up to date" in r.stdout


def test_class2b_skill_size_version_and_generic_blocks():
    p = REPO / ".claude" / "skills" / "class2b-director" / "SKILL.md"
    text = p.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= SKILL_LIMIT
    assert re.search(r"^Skill version: 2026-10-03\.4$", text, re.M)
    cfg = json.loads((REPO / "campaigns" / "classroom-2b" / "campaign.json").read_text(encoding="utf-8"))
    tpl = skilltpl.render((REPO / "templates" / "voyage-director" / "SKILL.md").read_text(encoding="utf-8"),
                          skilltpl.context(cfg), skilltpl.enabled_modules(cfg))
    mine, theirs = skilltpl.blocks(text), skilltpl.blocks(tpl)
    assert mine == theirs and len(mine) >= 2  # byte-identical generic blocks
    assert skilltpl.fills_left(text) == []  # every fill block of the Class 2B skill is filled
    assert skilltpl.rules_version(text) == skilltpl.rules_version(tpl)


def test_template_structure():
    t = (REPO / "templates" / "voyage-director" / "SKILL.md").read_text(encoding="utf-8")
    ids = re.findall(r"<!-- generic:start ([\w-]+) -->", t)
    assert len(ids) == len(set(ids)) >= 2 and t.count("<!-- generic:end -->") == len(ids)
    assert re.search(r"^Generic rules: \d{4}-\d{2}-\d{2}\.\d+$", t, re.M)
    for ph in ("{{NAME}}", "{{SLUG}}", "{{DISPLAY}}", "{{PROMPT_LIMIT}}"):
        assert ph in t, ph
    assert t.count("<!-- module:standing:start -->") == t.count("<!-- module:standing:end -->") > 0
    assert "<!-- fill:" in t


def test_resume_reports_generic_rules_for_class2b():
    r = db(REPO, "classroom-2b", "resume")
    assert r.returncode == 0
    m = re.search(r"^Generic rules: (\S+) \(template (\S+)\)$", r.stdout, re.M)
    assert m and m.group(1) == m.group(2) and "WARNING" not in r.stdout


# ---- scaffolding ---------------------------------------------------------------------------------
def test_scaffold_default_has_standing_off(tmp_path):
    root, r = scaffold(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    cdir = root / "campaigns" / "harbor-nights"
    cfg = json.loads((cdir / "campaign.json").read_text(encoding="utf-8"))
    assert cfg["name"] == "harbor-nights" and cfg["display"] == "Harbor Nights"
    assert cfg["modules"]["standing"]["enabled"] is False and cfg["modules"]["debt"]["enabled"] is False
    assert not (cdir / "data" / "ledger.json").exists()
    skill = skill_path(root).read_text(encoding="utf-8")
    assert len(skill.encode("utf-8")) <= SKILL_LIMIT
    assert "Standing" not in skill and "ledger" not in skill and "{{" not in skill
    assert re.search(r"^name: harbor-nights-director$", skill, re.M)
    assert "campaigns/harbor-nights" in skill and "python3 tools/db.py --campaign harbor-nights" in skill
    for f in ("README.md", "arc-bible.md", "split-scenes.md", "docs/orchestration.md", "opening.md"):
        text = (cdir / f).read_text(encoding="utf-8")
        assert "{{" not in text and "module:" not in text, f
        assert "ledger" not in text.replace("hidden ladder", ""), f
    assert "fill block(s) left" in r.stdout and "SKILL.md" in r.stdout and "story starts: 2" in r.stdout


def test_scaffold_with_standing(tmp_path):
    root, r = scaffold(tmp_path, "--standing")
    assert r.returncode == 0, r.stderr + r.stdout
    cdir = root / "campaigns" / "harbor-nights"
    assert json.loads((cdir / "campaign.json").read_text(encoding="utf-8"))["modules"]["standing"]["enabled"] is True
    led = json.loads((cdir / "data" / "ledger.json").read_text(encoding="utf-8"))
    assert led["current"] == led["start"] and led["hint_bands"] and led["entries"] == []
    skill = skill_path(root).read_text(encoding="utf-8")
    assert len(skill.encode("utf-8")) <= SKILL_LIMIT
    assert "Standing" in skill and "ledger" in skill and "module:" not in skill
    assert db(root, "harbor-nights", "ledger", "+2", "first dinner", "--turn", 1, "--evidence", "e").returncode == 0
    assert "Standing (director only): 42" in db(root, "harbor-nights", "resume").stdout


def test_scaffold_module_flags(tmp_path):
    root, r = scaffold(tmp_path, "--module", "standing", "--module", "debt")
    assert r.returncode == 0, r.stderr
    cfg = json.loads((root / "campaigns" / "harbor-nights" / "campaign.json").read_text(encoding="utf-8"))["modules"]
    assert cfg["standing"]["enabled"] and cfg["debt"]["enabled"]
    st = json.loads((root / "campaigns" / "harbor-nights" / "data" / "state.json").read_text(encoding="utf-8"))
    assert st["debt"] == {"principal": 0, "due": 0, "due_day": 0}
    out = db(root, "harbor-nights", "state").stdout
    assert "Standing (director only)" in out and "Debt (hidden)" in out
    assert len(skill_path(root).read_bytes()) <= SKILL_LIMIT


def test_scaffold_refuses_existing_name(tmp_path):
    root, r = scaffold(tmp_path)
    assert r.returncode == 0
    before = skill_path(root).read_bytes()
    root, r = scaffold(tmp_path)
    assert r.returncode == 1 and "already exists" in r.stderr
    assert skill_path(root).read_bytes() == before
    r = run("new_campaign.py", "Bad Name", "--display", "x", "--root", root, root=root)
    assert r.returncode == 1 and "NAME must" in r.stderr


def test_scaffold_without_world_gives_empty_data(tmp_path):
    root, r = scaffold(tmp_path, world=False)
    assert r.returncode == 0, r.stderr
    d = root / "campaigns" / "harbor-nights" / "data"
    assert json.loads((d / "locations.json").read_text()) == {} and json.loads((d / "turns.json").read_text()) == []
    assert db(root, "harbor-nights", "resume").returncode == 0


def test_world_import_shapes_match_classroom_2b(tmp_path):
    root, r = scaffold(tmp_path)
    assert r.returncode == 0, r.stderr
    d = root / "campaigns" / "harbor-nights" / "data"
    real = REPO / "campaigns" / "classroom-2b" / "data"
    load = lambda base, n: json.loads((base / f"{n}.json").read_text(encoding="utf-8"))
    loc, rloc = load(d, "locations"), load(real, "locations")
    assert set(loc) == {"Lantern Quay", "Salt Row"}
    sample, rsample = loc["Lantern Quay"], next(iter(rloc.values()))
    assert set(sample) == set(rsample)
    assert set(sample["areas"]["ferry-landing"]) == set(next(iter(rsample["areas"].values()))) - {"added_turn", "evidence"}
    assert sample["areas"]["ferry-landing"]["paths"] == ["market-hall"]
    assert "café-corner" in sample["areas"] and sample["areas"]["market-hall"]["paths"] == ["ferry-landing", "café-corner"]
    fac, rfac = load(d, "factions"), load(real, "factions")
    assert set(fac["Dock Guild"]) == set(next(iter(rfac.values())))
    npc, rnpc = load(d, "world-npcs"), load(real, "world-npcs")
    assert set(npc["Harbor Master"]) == set(next(iter(rnpc.values())))
    assert npc["Harbor Master"]["status"] == "world" and npc["Net Mender"]["faction"] is None
    lore = load(d, "lore")
    assert set(lore) == {"ferry-bell", "dock-guild-fees"} and all(isinstance(v, str) for v in lore.values())
    world = load(d, "world")
    assert world["story_start"]["name"] == "01 - Harbor Nights" and len(world["time"]["blocks"]) == 7  # time stays the skeleton
    assert world["resource_settings"] == [{"name": "health", "usage": "Tracks physical health."}]
    assert world["npc_types"] == ["Official", "Craftsperson"] and world["narrator_style"].startswith("Salt-air")
    assert world["relationship_stages"][0]["name"] == "Stranger"
    assert set(load(d, "state")) == set(load(real, "state")) - {"debt", "feedback"}
    assert (d / "world.json").exists() and set(p.name for p in d.glob("*.json")) == \
        set(p.name for p in real.glob("*.json")) - {"ledger.json"}


def test_world_import_alternative_layout(tmp_path):
    """Areas as a separate top-level list, lore and factions as dicts, a wrapper key: still imported."""
    w = {"world": {
        "locations": {"Old Mill": {"basicInfo": "A mill.", "region": "North"}},
        "locationAreas": [{"location": "Old Mill", "id": "Wheel Room", "description": "Big wheel.", "paths": ["Loft"]},
                          {"location": "Old Mill", "name": "Loft", "description": "Hay."}],
        "factions": {"Millers": {"basicInfo": "Grind grain."}},
        "lore": {"mill-lore": "The wheel never stops."},
        "worldNPCs": {"Old Miller": {"currentLocation": "Old Mill", "currentArea": "wheel-room", "personality": "stern"}},
    }}
    f = tmp_path / "alt.json"
    f.write_text(json.dumps(w), encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    r = run("new_campaign.py", "alt", "--display", "Alt", "--world", f, "--root", root, root=root)
    assert r.returncode == 0, r.stderr
    d = root / "campaigns" / "alt" / "data"
    loc = json.loads((d / "locations.json").read_text())
    assert set(loc["Old Mill"]["areas"]) == {"wheel-room", "loft"} and loc["Old Mill"]["areas"]["wheel-room"]["paths"] == ["loft"]
    assert json.loads((d / "lore.json").read_text()) == {"mill-lore": "The wheel never stops."}
    assert json.loads((d / "world-npcs.json").read_text())["Old Miller"]["personality"] == ["stern"]
    assert json.loads((d / "factions.json").read_text())["Millers"]["name"] == "Millers"


def test_scaffolded_campaign_runs_resume_check_prompt_and_record(tmp_path):
    root, r = scaffold(tmp_path)
    assert r.returncode == 0, r.stderr
    res = db(root, "harbor-nights", "resume")
    assert res.returncode == 0, res.stderr
    assert res.stdout.startswith("Turn 0 | Day 1 Monday (Act 1)") and "Standing" not in res.stdout
    assert re.search(r"^Generic rules: (\S+) \(template \1\)$", res.stdout, re.M)
    assert db(root, "harbor-nights", "bible", "budgets").stdout.startswith("## ")
    prompt = tmp_path / "p.txt"
    prompt.write_text("Cut: Continue at Lantern Quay/ferry-landing, Day 1 evening.\nCrew: Harbor Master logs the arrival.\n"
                      "World: the ferry bell rings twice.", encoding="utf-8")
    chk = db(root, "harbor-nights", "check-prompt", prompt)
    assert chk.returncode == 0 and "OK:" in chk.stdout, chk.stdout
    pc = db(root, "harbor-nights", "pc-add", "Ren", "--player", "Sam", "--location", "Lantern Quay", "--area", "ferry-landing",
            "--turn", 1, "--evidence", "player sheet")
    assert pc.returncode == 0, pc.stderr
    payload = {"turn": 1, "ops": [{"op": "fact", "args": {"subject": "bell", "text": "The ferry bell rings twice for a stranger."},
                                   "evidence": "the bell rang twice"}],
               "turn_log": {"inputs": "Ren: i step off the ferry", "summary": "Ren arrived at Lantern Quay.", "prompt": "none"}}
    pf = tmp_path / "payload.json"
    pf.write_text(json.dumps(payload), encoding="utf-8")
    rec = db(root, "harbor-nights", "record", pf)
    assert rec.returncode == 0, rec.stderr + rec.stdout
    state = json.loads((root / "campaigns" / "harbor-nights" / "data" / "state.json").read_text())
    assert state["turn"] == 1
    assert db(root, "harbor-nights", "ledger", "+1", "x", "--turn", 1, "--evidence", "e").returncode == 4  # module off


def test_single_campaign_is_the_default_and_several_need_a_name(tmp_path):
    root, r = scaffold(tmp_path)
    env = clean_env(VOYAGE_ROOT=str(root))
    one = subprocess.run([sys.executable, str(TOOLS / "db.py"), "state"], capture_output=True, text=True, env=env, cwd=root)
    assert one.returncode == 0 and one.stdout.startswith("Turn 0")
    r = run("new_campaign.py", "second", "--display", "Second", "--root", root, root=root)
    assert r.returncode == 0
    two = subprocess.run([sys.executable, str(TOOLS / "db.py"), "state"], capture_output=True, text=True, env=env, cwd=root)
    assert two.returncode == 2 and "--campaign" in two.stderr
    env["VOYAGE_CAMPAIGN"] = "second"
    three = subprocess.run([sys.executable, str(TOOLS / "db.py"), "state"], capture_output=True, text=True, env=env, cwd=root)
    assert three.returncode == 0


# ---- sync ------------------------------------------------------------------------------------------
def test_sync_check_and_repair_keep_fill_content(tmp_path):
    root, r = scaffold(tmp_path, "--standing")
    p = skill_path(root)
    assert run("sync_skill.py", "harbor-nights", "--check", root=root).returncode == 0
    text = p.read_text(encoding="utf-8")
    # hand-fill one block and damage one generic rule, as an old copy would
    filled = text.replace(re.search(r"<!-- fill: Canon traps.*?-->", text, re.S).group(0), "- The quay bell rings twice for strangers.")
    damaged = filled.replace("**Voyage narrates; you direct behind it**", "**Voyage narrates**").replace(
        "Generic rules: 2026-10-03.2", "Generic rules: 2026-09-01.1")
    assert damaged != filled
    p.write_text(damaged, encoding="utf-8")
    chk = run("sync_skill.py", "harbor-nights", "--check", root=root)
    assert chk.returncode == 1 and "OUT OF DATE" in chk.stdout and "block 'core' updated" in chk.stdout
    assert p.read_text(encoding="utf-8") == damaged  # --check writes nothing
    res = db(root, "harbor-nights", "resume").stdout
    assert "Generic rules: 2026-09-01.1 (template 2026-10-03.2)" in res and "WARNING generic rules are behind" in res
    fix = run("sync_skill.py", "harbor-nights", root=root)
    assert fix.returncode == 0 and "synced" in fix.stdout
    assert p.read_text(encoding="utf-8") == filled
    assert run("sync_skill.py", "harbor-nights", "--check", root=root).returncode == 0
    assert "WARNING" not in db(root, "harbor-nights", "resume").stdout


def test_sync_follows_module_state(tmp_path):
    root, r = scaffold(tmp_path)  # standing off: the module text must not come back
    p = skill_path(root)
    assert "ledger" not in p.read_text(encoding="utf-8")
    p.write_text(p.read_text(encoding="utf-8").replace("Bullet only if the user must decide.", "Bullet always."), encoding="utf-8")
    assert run("sync_skill.py", "harbor-nights", root=root).returncode == 0
    text = p.read_text(encoding="utf-8")
    assert "Bullet only if the user must decide." in text and "Standing" not in text


def test_sync_unknown_campaign(tmp_path):
    r = run("sync_skill.py", "nope", "--check", root=tmp_path)
    assert r.returncode == 2


def test_leave_the_arc_rule_in_template_and_class2b():
    for p in (REPO / "templates" / "voyage-director" / "SKILL.md", REPO / ".claude" / "skills" / "class2b-director" / "SKILL.md"):
        t = p.read_text(encoding="utf-8")
        assert "## When players leave the arc" in t and "If the new party is thin" in t and "`add-npc`, `agenda`, `fact`" in t
        assert "4 = trial run" in t and "split header" in t and "multi-step prompts get cut" in t
