"""campaign.json `campfire_room` (the Campfire mode signal): every tool that reads campaign.json tolerates the field, and `resume`
names the room. Runs on a tmp repo root (VOYAGE_ROOT) holding a copy of classroom-2b."""
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


def test_every_campaign_json_reader_tolerates_the_room_code(tmp_path):
    """Each reader behaves exactly as without the field: same exit code, same output (bar resume's one Campfire line and the skipped-in-Campfire-mode notes)."""
    with_room, _ = make_root(tmp_path / "a", "K7Q2MX")
    without, _ = make_root(tmp_path / "b", None)
    cmds = [(DB, "--campaign", "demo", c) for c in ("resume", "state", "prep", "turn-brief", "preflight", "menu", "bible", "spotlight")]
    cmds += [(REPO / "tools" / "sync_skill.py", "demo", "--check")]
    for tool, *args in cmds:
        a, b = run(with_room, *args, tool=tool), run(without, *args, tool=tool)
        assert "Traceback" not in a.stderr, (args, a.stderr)
        assert a.returncode == b.returncode, (args, a.returncode, b.returncode, a.stdout[-400:])
        drop = lambda out: [ln for ln in out.replace(str(with_room), "").replace(str(without), "").replace(" (skipped in Campfire mode)", "").splitlines()
                            if "Campfire room" not in ln and not ln.startswith("NOTE: Campfire mode")]
        assert drop(a.stdout) == drop(b.stdout), args
    r = run(with_room, "--campaign", "demo", "planner-page", "--out", tmp_path / "page.html")
    assert r.returncode == 0 and "Traceback" not in r.stderr, r.stderr
    a = run(with_room, "--out", tmp_path / "_site_a", tool=REPO / "tools" / "build_site.py")
    b = run(without, "--out", tmp_path / "_site_b", tool=REPO / "tools" / "build_site.py")
    assert "Traceback" not in a.stderr and a.returncode == b.returncode, a.stderr


def test_resume_names_the_room_code(tmp_path):
    root, _cdir = make_root(tmp_path, "K7Q2MX")
    out = run(root, "--campaign", "demo", "resume").stdout
    assert "Campfire room: K7Q2MX" in out and "playbooks/campfire.md" in out


def test_resume_without_the_field_is_unchanged(tmp_path):
    root, _cdir = make_root(tmp_path, None)
    out = run(root, "--campaign", "demo", "resume").stdout
    assert "Campfire" not in out


@pytest.mark.parametrize("bad", ["K7Q2M", "K7Q2MXX", "k7q2mx", "K7Q2M0", "K7Q2MI", 123456])
def test_a_malformed_room_code_warns_and_leaves_campfire_mode_off(tmp_path, bad):
    root, _cdir = make_root(tmp_path, bad)
    r = run(root, "--campaign", "demo", "resume")
    assert r.returncode == 0, r.stderr
    assert "is not a Campfire room code" in r.stdout and "Campfire mode is off" in r.stdout


def test_room_code_helper():
    sys.path.insert(0, str(REPO / "tools"))
    try:
        import db  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    assert db.campfire_room({"campfire_room": "K7Q2MX"}) == "K7Q2MX"
    assert db.campfire_room({}) is None
    assert db.campfire_room({"campfire_room": "K7Q2M1"}) is None  # 1 is not in the alphabet
    assert db.campfire_room_problem("23456Z") is None
