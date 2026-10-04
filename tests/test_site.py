"""The GitHub Pages site (tools/build_site.py): full documents, an index, and no deploy when a page would leak.
Every test works on a tmp copy of campaigns/, tools/, templates/ and .claude/ (VOYAGE_ROOT points at it); the real data is never written."""
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CAMPAIGNS = sorted(p.name for p in (REPO / "campaigns").iterdir() if (p / "campaign.json").is_file())
IGNORE = shutil.ignore_patterns(".lock", "snapshots*", ".snap*", "__pycache__", "*.pyc")

CHARTER = {
    "budget_turns": 10,
    "shared": {
        "title": "Who Holds the Keys", "tone": "Wry and warm", "promise": "Can you earn the house's trust before it must choose?",
        "premise": "A quiet squeeze on the house.", "pressure": "An inspection nobody can move.",
        "set_pieces": ["a tense house meeting", "a favor traded under time pressure"], "subplot": "A favor owed outside the house.",
        "climax_kind": "A public inspection", "ending_shape": "Bittersweet", "stakes": "personal", "seeds": ["a scratched-out name"],
        "wins_on_offer": ["a staff ally"], "echoes": ["you covered a chore"], "backstory_hooks": ["the repair shop"], "deviations": []},
    "hidden": {
        "twist": {"text": "A housemate took the money.", "ladder": "Mio's secret", "keywords": ["glass lantern"]},
        "fronts": [{"name": "The Lender", "goal": "Get paid", "moves": ["A polite offer", "A second visit", "A written deadline"]},
                   {"name": "The Agent", "goal": "End the lease", "moves": ["A walkthrough", "A formal notice"]}],
        "antagonist": {"name": "Sōichi Tamaru", "face": "a polite broker", "first_contact": "an offer at the gate"},
        "clues": ["a thick envelope", "a neighbor's story", "a cash payment", "a card in a coat"],
        "surprises": ["the inspector knows Arimura"], "climax_options": ["a house vote"], "pc_test_situations": {},
        "cast": ["Mio Tachibana"], "new_npcs": [], "notes": "keep it offscreen"}}


def make_tree(dest, clean_arcs=False):
    """A scratch repo root with the parts the build reads. clean_arcs drops every arcs.json so the copy starts with no plans."""
    for part in ("campaigns", "tools", "templates", ".claude"):
        shutil.copytree(REPO / part, dest / part, ignore=IGNORE)
    shutil.copy(REPO / "site.json", dest / "site.json")
    if clean_arcs:
        for f in (dest / "campaigns").glob("*/data/arcs.json"):
            f.unlink()
    return dest


def tree_hash(path):
    h = hashlib.sha256()
    for f in sorted(p for p in Path(path).rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def env_for(root):
    e = {k: v for k, v in os.environ.items() if k not in ("VOYAGE_DATA", "CLASS2B_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_TRIAL", "CLASS2B_TRIAL")}
    e.update({"VOYAGE_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"})
    return e


def run(root, script, *args):
    return subprocess.run([sys.executable, str(root / "tools" / script), *map(str, args)], capture_output=True, text=True, env=env_for(root))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = make_tree(tmp_path_factory.mktemp("tree"), clean_arcs=True)
    out = tmp_path_factory.mktemp("out") / "_site"
    before = tree_hash(REPO / "campaigns")
    r = run(root, "build_site.py", "--out", out)
    assert r.returncode == 0, r.stderr + r.stdout
    assert tree_hash(REPO / "campaigns") == before  # the real data is untouched
    return root, out


def test_there_are_campaigns():
    assert {"classroom-2b", "luxcellia", "joestar"} <= set(CAMPAIGNS)


@pytest.mark.parametrize("name", CAMPAIGNS)
def test_campaign_page_is_a_full_document(built, name):
    page = (built[1] / name / "index.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>\n<html lang=\"en\">")
    head, body = page.split("</head>", 1)
    assert head.count("<title>") == 1 and "<title>" not in body and "</title>" not in body
    assert re.search(r"<title>[^<]+Arc Planner</title>", head)
    assert '<meta charset="utf-8">' in head and '<meta name="robots" content="noindex">' in head
    assert 'content="width=device-width, initial-scale=1, viewport-fit=cover"' in head
    assert "[hidden]{display:none!important}" in head and "color-scheme:light" in head
    assert page.count("<!doctype") == 1 and page.count("<body>") == 1 and page.rstrip().endswith("</html>")
    assert '<div class="wrap">' in body and "prefers-color-scheme:dark" in head


def test_index_lists_every_campaign(built):
    out = built[1]
    page = (out / "index.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and '<meta name="robots" content="noindex">' in page and "<title>Arc Planner</title>" in page
    assert (out / ".nojekyll").is_file()
    for name in CAMPAIGNS:
        cfg = json.loads((REPO / "campaigns" / name / "campaign.json").read_text(encoding="utf-8"))
        assert f'href="{name}/"' in page
        assert f"<h2>{html.escape(cfg.get('display') or name)}</h2>" in page
    assert page.count("No arc planned yet") == len(CAMPAIGNS)  # the build tree has no arcs.json
    st = json.loads((REPO / "campaigns" / "joestar" / "data" / "state.json").read_text(encoding="utf-8"))
    assert f"Turn {st['turn']}" in page and f"Day {st['day']}" in page


def test_index_shows_the_arc_title(tmp_path):
    root = make_tree(tmp_path / "tree", clean_arcs=True)
    charter = tmp_path / "c.json"
    charter.write_text(json.dumps(CHARTER), encoding="utf-8")
    e = env_for(root) | {"VOYAGE_CAMPAIGN": "classroom-2b"}
    for cmd in (["arc-plan", "--file", charter], ["arc-approve", "A1", "--lines-checked"]):
        r = subprocess.run([sys.executable, str(root / "tools" / "db.py"), *map(str, cmd)], capture_output=True, text=True, env=e)
        assert r.returncode == 0, r.stderr + r.stdout
    out = tmp_path / "_site"
    r = run(root, "build_site.py", "--out", out)
    assert r.returncode == 0, r.stderr
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Who Holds the Keys" in index and index.count("No arc planned yet") == len(CAMPAIGNS) - 1
    assert "glass lantern" not in index and "Tamaru" not in index


def test_a_leak_fails_the_build_and_writes_no_site(tmp_path):
    root = make_tree(tmp_path / "tree", clean_arcs=True)
    charter = json.loads(json.dumps(CHARTER))
    charter["shared"]["premise"] = "Watch for the glass lantern in the hall."  # a hidden twist keyword in a shared field
    f = tmp_path / "leaky.json"
    f.write_text(json.dumps(charter), encoding="utf-8")
    e = env_for(root) | {"VOYAGE_CAMPAIGN": "classroom-2b"}
    r = subprocess.run([sys.executable, str(root / "tools" / "db.py"), "arc-plan", "--file", str(f)], capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stderr + r.stdout
    out = tmp_path / "_site"
    r = run(root, "build_site.py", "--out", out)
    assert r.returncode != 0
    assert "classroom-2b" in r.stderr and "glass lantern" in r.stderr and "no site written" in r.stderr
    assert not out.exists() or not list(out.rglob("index.html"))  # nothing a deploy could pick up
    # an earlier good build in the same directory stays as it was
    arcs = root / "campaigns" / "classroom-2b" / "data" / "arcs.json"
    arcs.unlink()
    assert run(root, "build_site.py", "--out", out).returncode == 0
    good = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert (out / "index.html").is_file() and (out / "classroom-2b" / "index.html").is_file()
    r = subprocess.run([sys.executable, str(root / "tools" / "db.py"), "arc-plan", "--file", str(f)], capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stderr
    assert run(root, "build_site.py", "--out", out).returncode != 0
    assert {p: p.read_bytes() for p in out.rglob("*") if p.is_file()} == good


def test_resume_prints_the_pages_link(tmp_path):
    root = make_tree(tmp_path / "tree")
    site = json.loads((REPO / "site.json").read_text(encoding="utf-8"))
    assert site["pages_base"].startswith("https://riggedrealm.github.io/campaign-helper")
    e = env_for(root) | {"VOYAGE_CAMPAIGN": "luxcellia"}

    def resume():
        r = subprocess.run([sys.executable, str(root / "tools" / "db.py"), "resume"], capture_output=True, text=True, env=e)
        assert r.returncode == 0, r.stderr
        return r.stdout

    assert "Planner page: https://riggedrealm.github.io/campaign-helper/luxcellia/\n" in resume()
    (root / "site.json").write_text(json.dumps({"pages_base": "https://example.test/x"}), encoding="utf-8")
    assert "Planner page: https://example.test/x/luxcellia/\n" in resume()
    (root / "site.json").unlink()
    assert "Planner page" not in resume()
    arcs = root / "campaigns" / "luxcellia" / "data" / "arcs.json"
    arcs.write_text(json.dumps({"version": 1, "page_url": "https://claude.ai/artifact/abc", "session_zero": {}, "pc_threads": [], "acts": [], "arcs": []}),
                    encoding="utf-8")
    assert "Planner page: https://claude.ai/artifact/abc\n" in resume()
