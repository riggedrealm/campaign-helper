"""Shared harness for the Campfire pipeline tests (GDD v2, G1 to G7): a tmp repo root (VOYAGE_ROOT) holding a copy of classroom-2b
whose campaign.json names the fixture packet's room, with one player character."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL = REPO / "campaigns" / "classroom-2b"
PACKET = REPO / "tests" / "fixtures" / "campfire-round.json"


def plain_env(**extra):
    e = {k: v for k, v in os.environ.items()
         if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_ROOT")}
    e.update({"PYTHONDONTWRITEBYTECODE": "1", **extra})
    return e


class Pc:
    def __init__(self, tmp_path, room="K7Q2MX"):
        self.tmp = tmp_path
        self.root = tmp_path / "root"
        self.cdir = self.root / "campaigns" / "demo"
        self.data = self.cdir / "data"
        shutil.copytree(REAL / "data", self.data, ignore=shutil.ignore_patterns(".lock", ".snap*", ".turn-clock*"))
        for f in ("arc-bible.md", "README.md", "director.md"):
            shutil.copy(REAL / f, self.cdir / f)
        cfg = json.loads((REAL / "campaign.json").read_text(encoding="utf-8"))
        cfg["name"] = "demo"
        cfg["skill_dir"] = ".claude/skills/demo-director"
        if room is not None:
            cfg["campfire_room"] = room
        (self.cdir / "campaign.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        sdir = self.root / ".claude" / "skills" / "demo-director"
        sdir.mkdir(parents=True)
        shutil.copy(REPO / ".claude" / "skills" / "class2b-director" / "SKILL.md", sdir / "SKILL.md")
        th = self.load("threads")
        th[next(iter(th))]["steps"][0].update({"keywords": ["Zebrafish"], "status": "hidden"})  # a strong secret term
        self.save("threads", th)
        r = self.db("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
        assert r.returncode == 0, r.stderr

    def db(self, *args, env=None):
        return subprocess.run([sys.executable, str(DB), "--campaign", "demo", *map(str, args)], capture_output=True, text=True,
                              env=plain_env(VOYAGE_ROOT=str(self.root), **(env or {})), cwd=self.root)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text if isinstance(text, str) else json.dumps(text, ensure_ascii=False), encoding="utf-8")
        return f

    def packet(self, mutate=None):
        p = json.loads(PACKET.read_text(encoding="utf-8"))
        if mutate:
            mutate(p)
        return self.write("packet.json", p)

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}
