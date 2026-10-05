"""Guards for the director's rule files (phase 4 of the revamp).

The rules live in the bootstrap skill, director/core.md, director/playbooks/*.md, director/reference.md and director/agents/*.md. Each
rule id sits in an HTML comment marker (D12). These tests check the id map, the banned precedence wording, the `db.py` commands the
files name, the size of the always-loaded layer, that the generic files carry no campaign names, and the bootstrap/brief headers."""
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO / ".claude" / "skills" / "voyage-director" / "SKILL.md"
CORE = REPO / "director" / "core.md"
INVENTORY = REPO / "docs" / "revamp" / "rule-inventory.md"
DIRECTOR_FILES = sorted((REPO / "director").rglob("*.md"))
RULE_FILES = [BOOTSTRAP] + DIRECTOR_FILES
GENERIC_FILES = RULE_FILES
CAMPAIGN_DIRECTORS = sorted((REPO / "campaigns").glob("*/director.md"))
ALWAYS_LOADED_LIMIT = 17_500

MARKER = re.compile(r"<!--(.*?)-->", re.S)
ID = re.compile(r"[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+")


def rel(path):
    return str(Path(path).relative_to(REPO))


def read(path):
    return Path(path).read_text(encoding="utf-8")


def inventory_section(number):
    """The text of one numbered '## N. ...' section of the rule inventory."""
    text = read(INVENTORY)
    m = re.search(r"^## %d\. .*?(?=^## \d+\. |\Z)" % number, text, re.S | re.M)
    assert m, "section %d not found in %s" % (number, rel(INVENTORY))
    return m.group(0)


def table_ids(section_text):
    """Ids in the first cell of every table row of a section (the header row is skipped)."""
    ids = []
    for line in section_text.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if ID.fullmatch(cell):
            ids.append(cell)
    return ids


def marker_ids(text):
    found = []
    for m in MARKER.finditer(text):
        for token in re.split(r"[,\s]+", m.group(1).strip()):
            if token:
                found.append(token)
    return found


def ids_by_file():
    """id -> sorted list of files whose markers hold it (a file repeating an id lists twice)."""
    where = {}
    for f in RULE_FILES:
        for i in marker_ids(read(f)):
            where.setdefault(i, []).append(rel(f))
    return where


def test_the_rule_files_exist():
    assert BOOTSTRAP.is_file(), "bootstrap missing: " + rel(BOOTSTRAP)
    assert CORE.is_file()
    assert len(DIRECTOR_FILES) >= 20, "director/**/*.md looks incomplete: %d files" % len(DIRECTOR_FILES)


def test_every_rule_id_has_exactly_one_home():
    inventory = table_ids(inventory_section(4))
    assert len(inventory) > 100, "inventory section 4 parsed to only %d ids" % len(inventory)
    dupes = sorted({i for i in inventory if inventory.count(i) > 1})
    assert not dupes, "rule-inventory section 4 lists these ids twice: " + ", ".join(dupes)
    where = ids_by_file()
    problems = []
    for i in inventory:
        files = where.get(i, [])
        if not files:
            problems.append("%s: in no marker (expected exactly one)" % i)
        elif len(files) > 1:
            problems.append("%s: in %d markers: %s" % (i, len(files), ", ".join(files)))
    for i in sorted(where):
        if i not in inventory:
            problems.append("%s: marker id not in inventory section 4 (%s)" % (i, ", ".join(where[i])))
    retired = set(table_ids(inventory_section(6)))
    for i in sorted(where):
        if i in retired or i.startswith("X-") or i.startswith("WR-"):
            problems.append("%s: retired or campaign id inside a marker (%s)" % (i, ", ".join(where[i])))
    assert not problems, "rule id problems:\n" + "\n".join(sorted(set(problems)))


def test_no_precedence_wording():
    files = RULE_FILES + [REPO / "templates" / "voyage-director" / "campaign" / "director.md"] + CAMPAIGN_DIRECTORS
    hits = []
    for f in files:
        if not f.is_file():
            continue
        for n, line in enumerate(read(f).splitlines(), 1):
            if re.search(r"wins over", line, re.I):
                hits.append("%s:%d: %s" % (rel(f), n, line.strip()[:120]))
    assert not hits, 'precedence wording "wins over" found:\n' + "\n".join(hits)


def real_subcommands():
    out = subprocess.run([sys.executable, "tools/db.py", "-h"], cwd=REPO, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    names = set()
    in_list = False
    for line in out.stdout.splitlines():
        if line.startswith("positional arguments:"):
            in_list = True
            continue
        if in_list:
            if line and not line.startswith(" "):
                break
            m = re.match(r"^    ([a-z][a-z0-9-]*)(?:\s|$)", line)
            if m:
                names.add(m.group(1))
    assert len(names) > 20, "could not read the subcommands from `db.py -h`"
    return names


def test_named_db_commands_exist():
    real = real_subcommands()
    pattern = re.compile(r"`(?:python3 tools/)?db\.py(?:\s+--campaign\s+\S+)?\s+([a-z][a-z0-9-]*)")
    bad = []
    for f in RULE_FILES:
        for n, line in enumerate(read(f).splitlines(), 1):
            for m in pattern.finditer(line):
                if m.group(1) not in real:
                    bad.append("%s:%d: `db.py %s` is not a db.py subcommand" % (rel(f), n, m.group(1)))
    assert not bad, "\n".join(bad)


def test_always_loaded_layer_size():
    size = BOOTSTRAP.stat().st_size + CORE.stat().st_size
    assert size <= ALWAYS_LOADED_LIMIT, (
        "The always-loaded layer (bootstrap %s + director/core.md) is %d bytes, over the %d-byte limit. These two files load in "
        "every chat, so every byte costs on every turn: move text into a playbook or reference.md." % (rel(BOOTSTRAP), size, ALWAYS_LOADED_LIMIT))


def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def campaign_names():
    names = {}
    for cj in sorted((REPO / "campaigns").glob("*/campaign.json")):
        data = json.loads(read(cj))
        for name in [data.get("display", "")] + list(data.get("main_npcs", [])):
            name = (name or "").strip()
            if len(re.sub(r"[^A-Za-z]", "", fold(name))) >= 4:
                names.setdefault(name, cj.parent.name)
    return names


def test_generic_files_carry_no_campaign_names():
    names = campaign_names()
    assert names, "no campaign names found"
    hits = []
    for f in GENERIC_FILES:
        text = fold(read(f))
        for name, campaign in names.items():
            if re.search(r"(?<![a-z0-9])" + re.escape(fold(name)) + r"(?![a-z0-9])", text):
                hits.append("%s names %r (campaign %s)" % (rel(f), name, campaign))
    assert not hits, "campaign names in generic files:\n" + "\n".join(hits)


def test_bootstrap_header_and_version_line():
    text = read(BOOTSTRAP)
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "bootstrap has no frontmatter"
    assert re.search(r"^name:\s*voyage-director\s*$", m.group(1), re.M), "frontmatter lacks `name: voyage-director`"
    assert re.search(r"^Skill version: \d{4}-\d{2}-\d{2}\.\d+\s*$", text, re.M), "no `Skill version: YYYY-MM-DD.n` line"


def test_agent_briefs_name_a_model():
    briefs = [f for f in sorted((REPO / "director" / "agents").glob("*.md")) if f.name != "common.md"]
    assert len(briefs) >= 9, "expected the nine role briefs, found %d" % len(briefs)
    bad = []
    for f in briefs:
        text = read(f)
        # the header is everything before the first fenced block (the brief itself)
        header = text.split("```", 1)[0]
        if not re.search(r"\b(Opus|Sonnet)\b", header):
            bad.append(rel(f))
    assert not bad, "no model (Opus or Sonnet) named in the header of: " + ", ".join(bad)
