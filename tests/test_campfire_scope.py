"""Campfire mode is a change to voyage-director only: nothing of it may be in the per-campaign skills or the generic rules they bundle,
and the pipeline playbook stays gated and names only commands that exist."""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIPE = REPO / "director" / "playbooks" / "campfire-pipeline.md"


def test_per_campaign_skills_and_the_template_carry_no_campfire_text():
    files = list((REPO / ".claude" / "skills").glob("*-director/SKILL.md")) + [REPO / "templates" / "voyage-director" / "SKILL.md"]
    for f in files:
        if f.parent.name == "voyage-director" and f.parent.parent.name == "skills":
            continue                                                  # the one skill Campfire mode is approved for
        t = f.read_text(encoding="utf-8")
        assert not re.search(r"campfire_room|campfire mode|campfire\.md|room code", t, re.I), f   # Luxcellia's own "campfire rule" is a story rule
        assert len(t.encode("utf-8")) <= 15000, f
        assert "Generic rules: 2026-10-05.3" in t, f


def test_the_pipeline_playbook_is_gated_and_names_real_commands():
    t = PIPE.read_text(encoding="utf-8")
    assert t.splitlines()[2].startswith("> **Not yet in force.**")
    helptext = subprocess.run([sys.executable, str(REPO / "tools" / "db.py"), "-h"], capture_output=True, text=True).stdout
    for cmd in set(re.findall(r"db\.py ([a-z][a-z-]+)", t)):
        assert cmd in helptext, cmd
    for cmd in ("check", "check-brief", "react-check", "hard-noes", "campfire-undo", "commit-turn"):
        assert f"db.py {cmd}" in t, cmd
    assert not re.search(r"\b(opus|sonnet|haiku|claude)\b", t, re.I)


def test_campfire_md_points_at_the_pipeline_behind_its_own_gate():
    t = (REPO / "director" / "playbooks" / "campfire.md").read_text(encoding="utf-8")
    assert "campfire-pipeline.md" in t and "Not yet in force.** `campfire-pipeline.md`" in t
