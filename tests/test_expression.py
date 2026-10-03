"""Expression kits (cast `expression`), the `brief` SHOW block, verify_data and the check-prompt flat-Crew WARN."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_db import Env, REAL_DATA, env, DB  # noqa: E402,F401
import test_db  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MOODS = {"happy", "angry", "embarrassed", "lying", "hurt"}
KITS = {"classroom-2b": 8, "luxcellia": 9}


def cast_of(camp):
    return json.loads((REPO / "campaigns" / camp / "data" / "cast.json").read_text(encoding="utf-8"))


def main_npcs(camp):
    return json.loads((REPO / "campaigns" / camp / "campaign.json").read_text(encoding="utf-8"))["main_npcs"]


@pytest.mark.parametrize("camp", sorted(KITS))
def test_main_npc_kits_complete_and_shaped(camp):
    cast, mains = cast_of(camp), main_npcs(camp)
    assert len(mains) == KITS[camp]
    for n in mains:
        x = cast[n]["expression"]
        assert set(x) == {"gestures", "moods", "lines", "never"}, n
        assert 3 <= len(x["gestures"]) <= 4 and len(x["lines"]) >= 2, n
        assert set(x["moods"]) == MOODS, n
        assert all(isinstance(v, str) and v.strip() for v in x["moods"].values()), n
        assert isinstance(x["never"], str) and x["never"].strip(), n


def test_kits_do_not_leak_hidden_terms():
    bad = ("annex", "scar", "nightshade", "debt", "floorboard", "rig", "daiki", "nine corners", "ōta", "ota ", "broadcast",
           "curse", "reborn", "earth", "bounty", "chisel", "ledger", "null", "second dagger", "logs", "van")
    for camp in KITS:
        for n in main_npcs(camp):
            blob = " ".join(json.dumps(cast_of(camp)[n]["expression"], ensure_ascii=False).lower().split())
            blob = re.sub(r"[^a-zōū ]", " ", blob)
            for w in bad:
                assert not re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", blob), (camp, n, w)


def test_brief_prints_show_block_and_not_set(env):
    r = env.run("brief", "Shin Asakura")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "SHOW (pick one, vary):" in out and "gestures:" in out and "moods:" in out and "lines:" in out and "never:" in out
    assert out.index("sample:") < out.index("SHOW (pick one, vary):") < out.index("want:")
    r = env.run("brief", "Sakura Lane House Manager")
    assert "expression: not set" in r.stdout and "SHOW" not in r.stdout


def test_brief_not_set_after_removing_kit(env):
    c = env.load("cast")
    del c["Shin Asakura"]["expression"]
    env.save_json("cast", c)
    assert "expression: not set" in env.run("brief", "Shin Asakura").stdout


def record_ok(env):
    return env.run("record", env.payload(1))


def test_verify_accepts_good_kit_and_rejects_bad(env):
    assert record_ok(env).returncode == 0
    for bad in ({"gestures": ["only one"]}, {"moods": {"sulking": "x"}}, {"lines": ["one"]}, {"never": ""},
                {"gestures": "a,b,c"}, {"extra": 1}):
        c = env.load("cast")
        c["Shin Asakura"]["expression"] = bad
        env.save_json("cast", c)
        r = env.run("record", env.payload(2))
        assert r.returncode != 0 and "expression" in (r.stdout + r.stderr), bad
    c = env.load("cast")
    c["Shin Asakura"]["expression"] = ["not", "an", "object"]
    env.save_json("cast", c)
    assert env.run("record", env.payload(2)).returncode != 0


def test_verify_accepts_partial_kit(env):
    c = env.load("cast")
    c["Shin Asakura"]["expression"] = {"gestures": ["a", "b", "c"], "never": "x"}
    env.save_json("cast", c)
    assert record_ok(env).returncode == 0


CUT = "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\n"


@pytest.mark.parametrize("crew", [
    "Tatsuya Ōmine offers tea; Shin watches.",
    "Shin Asakura watches; Mio nods; others react in character.",
    "Tatsuya smiles.",
    "Mio listens and agrees.",
])
def test_check_prompt_warns_on_flat_crew(env, crew):
    r = env.prompt(CUT + "Crew: " + crew + "\nWorld: The House Manager posts the chore rota.")
    assert "flat verbs" in r.stdout and "WARN" in r.stdout
    assert "FAIL" not in r.stdout and r.returncode == 0


def test_check_prompt_expressive_crew_is_clean(env):
    crew = ("Tatsuya slides a mug over without looking up, gruff to hide that he waited up (\"it was extra\"); "
            "Shin leans in the doorway, arms crossed, rating the newcomer like a lock he hasn't picked; others react in character.")
    r = env.prompt(CUT + "Crew: " + crew + "\nWorld: The House Manager posts the chore rota.")
    assert "flat verbs" not in r.stdout and r.returncode == 0, r.stdout


def test_check_prompt_others_clause_and_quotes_exempt(env):
    r = env.prompt(CUT + "Crew: Shin says \"Sure.\"; Mio looks away, jaw tight; others react in character.\nWorld: A pot lid rattles.")
    assert "flat verbs" not in r.stdout
    r = env.prompt(CUT + "Crew: Everyone else reacts in character.\nWorld: A pot lid rattles.")
    assert "flat verbs" not in r.stdout


def test_check_prompt_flat_warn_only_flags_the_flat_names(env):
    r = env.prompt(CUT + "Crew: Tatsuya hums over the stove, apron strings trailing; Shin watches.\nWorld: A pot lid rattles.")
    assert "Shin Asakura" in r.stdout and "Tatsuya" not in "".join(l for l in r.stdout.splitlines() if "flat verbs" in l)


def test_skill_rule_and_template_docs_present():
    tpl = (REPO / "templates" / "voyage-director" / "SKILL.md").read_text(encoding="utf-8")
    assert "Generic rules: 2026-10-03.5" in tpl
    assert "Spotlight NPCs (1 to 2 per turn)" in tpl and "never repeat last turn's gesture" in tpl and "docs/expression.md" in tpl
    for p in (REPO / "templates" / "voyage-director" / "campaign" / "docs" / "expression.md",
              REPO / "campaigns" / "classroom-2b" / "docs" / "expression.md",
              REPO / "campaigns" / "luxcellia" / "docs" / "expression.md"):
        t = p.read_text(encoding="utf-8")
        assert "Tatsuya slides a mug" in t and "`expression`" in t and "gestures" in t and "never" in t
    for sk in ("class2b-director", "luxcellia-director"):
        t = (REPO / ".claude" / "skills" / sk / "SKILL.md").read_text(encoding="utf-8")
        assert len(t.encode("utf-8")) <= 14000 and "Generic rules: 2026-10-03.5" in t and "Spotlight NPCs" in t


def test_scaffold_has_expression_doc_and_guidance(tmp_path):
    from test_templates import scaffold, skill_path
    root, r = scaffold(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    doc = root / "campaigns" / "harbor-nights" / "docs" / "expression.md"
    assert doc.is_file() and "{{" not in doc.read_text(encoding="utf-8")
    assert "`expression` kit" in r.stdout and "gestures, moods, lines, never" in r.stdout
    assert "Spotlight NPCs" in skill_path(root).read_text(encoding="utf-8")
