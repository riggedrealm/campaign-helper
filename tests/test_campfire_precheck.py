"""`precheck --scene F --packet F [--rulings F] [--ops F]`: the read-only pre-check of a Campfire post (playbook step 6). The
hidden-words check on the scene and the stakes lines, as strict as commit-turn's, and the speaker-block warnings: a block naming
nobody in the room (not a character, a scene NPC or a threat on the table, nor added by the post's ops), a player character's block
that is not a quote from their input, a bare `@` line, a long delivery note. Runs on a tmp repo root (VOYAGE_ROOT) holding a copy of
classroom-2b whose campaign.json names the fixture packet's room."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL = REPO / "campaigns" / "classroom-2b"
PACKET = REPO / "tests" / "fixtures" / "campfire-round.json"

NPC_BLOCK = '@Mio Tachibana (not looking up)\n"We\'re closed."'
THREAT_BLOCK = '@the man in the grey coat (from the shelf)\n"Nobody moves."'
PC_BLOCK = '@Aiko Tanaka\n"I vault the counter and go for the grey coat\'s wrist."'  # the fixture input, word for word
CLEAN = "Mio counts the till a third time.\n\n" + NPC_BLOCK + "\n\n" + PC_BLOCK + "\n\n" + THREAT_BLOCK + "\n\nThe door sticks."
RULINGS = {"rulings": [{"stakes": "Disarm him, or he gets a shot off."}, {"stakes": "fine"}], "threat_moves": []}
OPS = [{"op": "scene", "npcs": [{"name": "Tatsuya Ōmine", "attitude": "neutral"}], "evidence": "Tatsuya steps in."},
       {"op": "threat-add", "id": "dog", "name": "the shop dog", "tier": "trivial", "rules": "Barks.", "evidence": "A dog barks."}]
NOBODY = "names nobody in the room (not a character, a scene NPC or a threat on the table)"


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

    def precheck(self, scene=CLEAN, rulings=RULINGS, ops=OPS, mutate=None, *args, env=None):
        a = ["precheck", "--scene", self.write("scene.md", scene), "--packet", self.packet(mutate)]
        if rulings is not None:
            a += ["--rulings", self.write("rulings.json", rulings)]
        if ops is not None:
            a += ["--ops", self.write("ops.json", ops)]
        return self.db(*a, *args, env=env)


@pytest.fixture
def pc(tmp_path):
    return Pc(tmp_path)


def warns(r):
    return [ln for ln in r.stdout.splitlines() if ln.startswith("WARN: ")]


# ---- a clean post -----------------------------------------------------------------
def test_a_clean_post_passes_with_no_warning(pc):
    before = pc.hashes()
    r = pc.precheck()
    print(r.stdout)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pre-check: round 4 of room K7Q2MX, scene " in r.stdout and "2 ruling(s), 2 op(s)" in r.stdout
    assert "hidden-words check:\n  ok: scene and 2 stakes line(s) carry no hidden term" in r.stdout
    assert 'speaker blocks: "@Mio Tachibana", "@Aiko Tanaka", "@the man in the grey coat"' in r.stdout
    assert not warns(r) and r.stdout.rstrip().endswith("pre-check: ok; the five questions are yours to answer before gm post.")
    assert pc.hashes() == before  # read-only


def test_rulings_and_ops_are_optional(pc):
    r = pc.precheck(rulings=None, ops=None)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ruling(s)" not in r.stdout and "op(s)" not in r.stdout
    assert "  ok: scene and 0 stakes line(s) carry no hidden term (no --rulings: stakes not checked)" in r.stdout


def test_a_scene_without_speaker_blocks_says_none(pc):
    r = pc.precheck(scene="Mio counts the till. Nobody speaks.")
    assert r.returncode == 0 and "speaker blocks: none" in r.stdout and not warns(r)


# ---- the speaker name must be someone in the room ---------------------------------
def test_an_unknown_speaker_warns_with_the_paragraph(pc):
    r = pc.precheck(scene=CLEAN + '\n\n@Nobody Known\n"Hm."')
    assert r.returncode == 0, r.stdout + r.stderr
    w = warns(r)
    assert len(w) == 1 and w[0].startswith('WARN: speaker block "@Nobody Known" (paragraph 6) ' + NOBODY)
    assert "add them with a scene op in this post, or use the name the room lists" in w[0]
    assert "pre-check: ok with 1 warning(s)" in r.stdout


@pytest.mark.parametrize("written,listed", [
    ("mio tachibana", "Mio Tachibana"),        # case
    ("Mio Tachibana.", "Mio Tachibana"),       # punctuation
    ("Mr Hasegawa", "Mr. Hasegawa"),           # a dropped full stop
    ("Hasegawa", "Mr. Hasegawa"),              # part of one listed name
    ("grey coat", "the man in the grey coat"),  # part of a threat's name
])
def test_a_near_miss_names_the_listed_name(pc, written, listed):
    r = pc.precheck(scene=f'@{written}\n"Hm."')
    w = warns(r)
    assert len(w) == 1 and NOBODY in w[0] and f'the room lists "{listed}": the name must match exactly' in w[0], r.stdout


def test_a_database_npc_not_in_the_scene_says_add_a_scene_op(pc):
    r = pc.precheck(scene='@Kenji Arimura\n"Evening."', ops=[])
    w = warns(r)
    assert len(w) == 1 and NOBODY in w[0]
    assert '"Kenji Arimura" is in the database but not in the scene: add them with a scene op (name and attitude) in this post' in w[0]


def test_an_alias_of_a_database_npc_is_resolved_for_the_hint(pc):
    r = pc.precheck(scene='@Sunny\n"Evening."', ops=[])  # Sunny is Park Seo-yeon's alias, and the scene does not list them
    w = warns(r)
    assert len(w) == 1 and '"Park Seo-yeon" is in the database but not in the scene' in w[0]


def test_the_posts_own_ops_add_npcs_and_threats(pc):
    scene = CLEAN + '\n\n@Tatsuya Ōmine\n"Evening."\n\n@the shop dog\n"Woof."'
    assert not warns(pc.precheck(scene=scene))  # OPS adds both
    w = warns(pc.precheck(scene=scene, ops=[]))
    assert len(w) == 2 and "@Tatsuya Ōmine" in w[0] and "@the shop dog" in w[1]


def test_a_retired_threat_is_not_on_the_table(pc):
    def retire(p):
        p["threats"][0]["status"] = "retired"
    w = warns(pc.precheck(scene=THREAT_BLOCK, mutate=retire))
    assert len(w) == 1 and '"@the man in the grey coat"' in w[0] and NOBODY in w[0]
    w = warns(pc.precheck(scene=THREAT_BLOCK, mutate=lambda p: p["threats"][0].update(status="full")))
    assert not w


def test_a_result_packet_works_too(pc):
    def resolved(p):  # the result packet: the same fields, inputs resolved, a moves list
        p["room"]["phase"] = "writing"
        for x in p["inputs"]:
            x.update(ruling={"kind": "automatic"}, roll=None, effect={}, words=f"{x['name']}: automatic.")
        p["moves"] = []
    r = pc.precheck(mutate=resolved)
    assert r.returncode == 0 and not warns(r), r.stdout + r.stderr


# ---- a player character's block must be their own words ---------------------------
def test_a_pc_block_that_is_not_a_quote_warns(pc):
    r = pc.precheck(scene='@Ren Okabe\n"Keep the door, Sunny."')
    w = warns(r)
    assert len(w) == 1 and w[0].startswith('WARN: speaker block "@Ren Okabe" (paragraph 1) is a player character\'s block, and this line is '
                                           "not a quote from their input: Keep the door, Sunny.. Set only their own words, word for word")
    assert "report what they did in narration" in w[0]


def test_a_pc_quote_matches_across_quote_marks_and_case(pc):
    scene = '@Ren Okabe\n“I ask Sunny to keep the door while I look at the shelves.”'  # curly quotes, the input word for word
    assert not warns(pc.precheck(scene=scene))
    scene = '@Ren Okabe\n"i ask sunny to keep the door"'  # a part of the input is still their words
    assert not warns(pc.precheck(scene=scene))


def test_a_pc_who_wrote_no_input_gets_no_block(pc):
    w = warns(pc.precheck(scene=PC_BLOCK, mutate=lambda p: p["inputs"].pop(0)))
    assert len(w) == 1 and "Aiko Tanaka wrote no input this round: never give a player character words their player did not write" in w[0]


def test_every_line_of_a_pc_block_is_checked(pc):
    scene = '@Aiko Tanaka\n"I vault the counter"\n"and I was never here."'
    w = warns(pc.precheck(scene=scene))
    assert len(w) == 1 and "and I was never here." in w[0]


# ---- the block grammar ------------------------------------------------------------
def test_a_bare_at_line_warns_that_it_renders_as_text(pc):
    w = warns(pc.precheck(scene="@Mio Tachibana\n\nShe says nothing."))
    assert len(w) == 1 and w[0] == ('WARN: speaker block "@Mio Tachibana" (paragraph 1) has no line after it: the client renders it as '
                                   "ordinary text; put the spoken line on the next line")


def test_an_escaped_at_and_an_email_are_not_blocks(pc):
    scene = '\\@Nobody Known\n"Not a block."\n\nMail to nobody@example.com arrives.\n\n  @Mio Tachibana\n"Indented still counts."'
    r = pc.precheck(scene=scene)
    assert 'speaker blocks: "@Mio Tachibana"' in r.stdout and not warns(r)


def test_a_long_delivery_note_warns(pc):
    note = "a" * 61
    w = warns(pc.precheck(scene=f'@Mio Tachibana ({note})\n"Out."'))
    assert len(w) == 1 and w[0] == f'WARN: speaker block "@Mio Tachibana" (paragraph 1): the delivery note is 61 characters; keep it under 60'
    assert not warns(pc.precheck(scene=f'@Mio Tachibana ({"a" * 60})\n"Out."'))


def test_windows_line_endings_and_blank_lines_with_spaces_split_paragraphs(pc):
    scene = 'Mio looks up.\r\n  \r\n@Mio Tachibana\r\n"Closed."\r\n\r\n@Nobody Known\r\n"Hm."'
    w = warns(pc.precheck(scene=scene))
    assert len(w) == 1 and '"@Nobody Known" (paragraph 3)' in w[0]


# ---- the hidden-words check -------------------------------------------------------
def test_a_hidden_term_in_the_scene_fails_with_exit_4(pc):
    r = pc.precheck(scene=CLEAN + " A zebrafish drifts past the window.")
    assert r.returncode == 4, r.stdout + r.stderr
    assert 'FAIL: hidden term "zebrafish"' in r.stdout and "in scene" in r.stdout
    assert "pre-check: FAIL, a hidden term is in the scene or a stakes line; do not post." in r.stdout
    assert "speaker blocks:" in r.stdout  # the speaker check still runs, so one run shows everything


def test_a_hidden_term_in_a_stakes_line_names_the_ruling(pc):
    r = pc.precheck(rulings={"rulings": [{"stakes": "fine"}, {"stakes": "The Zebrafish is at risk."}]})
    assert r.returncode == 4 and "rulings[1].stakes" in r.stdout and "rulings[0]" not in r.stdout


def test_a_campaign_hidden_word_fails_and_allow_passes(pc):
    r = pc.precheck(scene=CLEAN + " Nobody mentions the ledger.")
    assert r.returncode == 4 and 'FAIL: hidden term "ledger" (campaign hidden word) in scene' in r.stdout
    r = pc.precheck(CLEAN + " Nobody mentions the ledger.", RULINGS, OPS, None, "--allow", "Ledger")
    assert r.returncode == 0 and "FAIL" not in r.stdout, r.stdout + r.stderr


def test_precheck_agrees_with_scan_and_commit_turn_on_a_soft_term(pc):
    th = pc.load("threads")
    th[next(iter(th))]["steps"][1].update({"keywords": ["Quokka"], "status": "hidden"})
    pc.save("threads", th)
    cfg_path = pc.cdir / "campaign.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("secrets", {})["soft_terms"] = ["quokka"]
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    r = pc.precheck(scene=CLEAN + " A quokka sticker is on the fridge.")
    assert r.returncode == 0 and 'WARN: "quokka" is also a term in' in r.stdout and "FAIL" not in r.stdout and "  ok:" not in r.stdout


# ---- files, the room and the environment ------------------------------------------
@pytest.mark.parametrize("scene,rulings,ops,needle", [
    ("   \n", RULINGS, OPS, "scene file is empty"),
    ("x" * 12001, RULINGS, OPS, "the limit is 12000"),
    (CLEAN, "{not json", OPS, "rulings file is not valid JSON"),
    (CLEAN, {"rulings": [{"stakes": 5}]}, OPS, "rulings[0].stakes must be a string"),
    (CLEAN, RULINGS, {"op": "x"}, "ops file must be a JSON list"),
    (CLEAN, RULINGS, [{"evidence": "e"}], "ops[0] must be an object with a string 'op'"),
])
def test_malformed_files_exit_2(pc, scene, rulings, ops, needle):
    r = pc.precheck(scene, rulings, ops)
    assert r.returncode == 2 and "pre-check: 1 problem(s) in the Campfire files" in r.stdout and needle in r.stdout, r.stdout + r.stderr


def test_a_missing_or_malformed_packet_exits_2(pc):
    r = pc.db("precheck", "--scene", pc.write("s.md", CLEAN), "--packet", pc.tmp / "nope.json")
    assert r.returncode == 2 and "no such packet file" in r.stdout + r.stderr
    r = pc.db("precheck", "--scene", pc.write("s.md", CLEAN), "--packet", pc.write("bad.json", "[]"))
    assert r.returncode == 2 and "expected a JSON object" in r.stdout + r.stderr
    r = pc.db("precheck", "--packet", pc.packet())  # --scene is required
    assert r.returncode == 2


def test_the_room_warnings_match_prep(tmp_path):
    off = Pc(tmp_path / "a", room=None)
    r = off.precheck()
    assert r.returncode == 0 and "WARN: campaign.json names no Campfire room code (campfire_room): Campfire mode is off for this campaign" in r.stdout
    other = Pc(tmp_path / "b", room="ABCDEF")
    r = other.precheck()
    assert r.returncode == 0 and "WARN: packet room K7Q2MX is not this campaign's room ABCDEF" in r.stdout
    assert "Packet: round" not in r.stdout  # prep's packet line is prep's


def test_precheck_works_in_a_trial_run_and_writes_nothing(pc):
    before = pc.hashes()
    r = pc.precheck(scene=CLEAN + '\n\n@Nobody Known\n"Hm."', env={"VOYAGE_TRIAL": "1"})
    assert r.returncode == 0 and len(warns(r)) == 1, r.stdout + r.stderr
    assert pc.hashes() == before


def test_commit_turn_still_needs_rulings_and_ops(pc):
    r = pc.db("commit-turn", "--scene", pc.write("s.md", CLEAN), "--payload", pc.write("pl.json", {}))
    assert r.returncode == 2 and "--rulings" in r.stdout + r.stderr


def test_the_playbook_and_the_readme_name_the_command(pc):
    pb = (REPO / "director" / "playbooks" / "campfire.md").read_text(encoding="utf-8")
    assert "python3 tools/db.py precheck --scene campaigns/NAME/campfire/scene-N.md --packet campaigns/NAME/campfire/result-N.json" in pb
    assert "db.py precheck" in (REPO / "README.md").read_text(encoding="utf-8")


def test_a_number_the_packet_contradicts_is_a_precheck_warning_and_the_playbook_examples_still_pass(pc):
    """The number check runs in precheck as a warning (the state check flags it); the playbook's own examples, its rulings file, its ops
    file and its speaker-block example, pass precheck on the fixture packet with no number warning."""
    r = pc.precheck(CLEAN + "\n\nAiko, down to forty health, steadies herself.")
    assert r.returncode == 0 and any("says forty health, but the packet has" in w for w in warns(r)), r.stdout
    pb = (REPO / "director" / "playbooks" / "campfire.md").read_text(encoding="utf-8")
    rulings_ex, ops_ex = [json.loads(b) for b in re.findall(r"## Worked example: [^\n]*\n(?:[^`]|`(?!``))*?```json\n(.*?)\n```", pb, re.S)]
    speaker_ex = re.search(r"```\n(@Station Master Oda[^\n]*\n[^\n]*)\n```", pb).group(1)
    for scene, rulings, ops in [(CLEAN, rulings_ex, OPS), (CLEAN, RULINGS, ops_ex), (CLEAN + "\n\n" + speaker_ex, RULINGS, OPS)]:
        r = pc.precheck(scene, rulings, ops)
        assert r.returncode == 0 and not any("packet has" in w for w in warns(r)), r.stdout
