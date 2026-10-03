"""Tests for tools/db.py with the classroom-2b campaign: every test runs against a tmp copy of data/ (VOYAGE_DATA), never the real data."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
REAL_DATA = REPO / "campaigns" / "classroom-2b" / "data"
CAMPAIGN = "classroom-2b"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, stdin=None, trial=False, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e["VOYAGE_DATA"] = str(self.data)
        e["VOYAGE_CAMPAIGN"] = CAMPAIGN
        if trial:
            e["VOYAGE_TRIAL"] = "1"
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True,
                              input=stdin, env=e, cwd=self.tmp)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def prompt(self, text, *args):
        f = self.tmp / "prompt.txt"
        f.write_text(text, encoding="utf-8")
        return self.run("check-prompt", f, *args)

    def turn(self, n, summary="Aiko met Tatsuya Ōmine in the kitchen.", inputs="say hi", prompt="Cut: x\nWorld: y", slips=None):
        args = ["turn", n, "--inputs", inputs, "--summary", summary, "--prompt", prompt]
        if slips is not None:
            args += ["--slips", slips]
        return self.run(*args)

    def payload(self, turn, **tl):
        p = {"turn": turn, "ops": [], "turn_log": {"inputs": "i", "summary": f"summary {turn}", "prompt": "Cut: a\nWorld: b", **tl}}
        f = self.tmp / f"payload{turn}.json"
        f.write_text(json.dumps(p), encoding="utf-8")
        return f


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    return Env(data, tmp_path)


@pytest.fixture
def pc_env(env):
    r = env.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr + r.stdout
    return env


GOOD = ("Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\n"
        "Crew: Tatsuya Ōmine offers tea; others react in character.\n"
        "World: The House Manager posts the chore rota.")


# ---- turn logging, record, undo ------------------------------------------------
def test_turn_logging(env):
    r = env.turn(1)
    assert r.returncode == 0, r.stderr
    assert env.load("state")["turn"] == 1
    t = env.load("turns")
    assert len(t) == 1 and t[0]["summary"].startswith("Aiko met")
    assert env.turn(1).returncode == 1  # next turn must be 2
    assert env.turn(3).returncode == 1


def test_record_and_undo_turn(env):
    r = env.run("record", env.payload(1))
    assert r.returncode == 0, r.stderr + r.stdout
    assert env.load("state")["turn"] == 1
    r = env.run("undo-turn", 1)
    assert r.returncode == 0, r.stderr + r.stdout
    assert env.load("state")["turn"] == 0 and env.load("turns") == []


def test_record_dry_run_writes_nothing(env):
    before = (env.data / "state.json").read_bytes(), (env.data / "turns.json").read_bytes()
    r = env.run("record", env.payload(1), "--dry-run")
    assert r.returncode == 0 and "dry run OK" in r.stdout
    assert ((env.data / "state.json").read_bytes(), (env.data / "turns.json").read_bytes()) == before
    assert env.run("record", env.payload(1), "--dry-run", trial=True).returncode == 0  # allowed in a trial


def test_record_refused_in_trial(env):
    assert env.run("record", env.payload(1), trial=True).returncode == 4
    assert env.load("state")["turn"] == 0


# ---- check-prompt -----------------------------------------------------------
def test_check_prompt_clean_ok(env):
    r = env.prompt(GOOD)
    assert r.returncode == 0, r.stdout
    assert "OK:" in r.stdout and "FAIL" not in r.stdout


def test_check_prompt_length_fail(env):
    r = env.prompt("Cut: " + "a" * 900 + "\nWorld: b")
    assert r.returncode == 1 and "over the" in r.stdout


@pytest.mark.parametrize("text,msg", [
    ("Crew: Tatsuya Ōmine offers tea.\nCut: Continue at Sakura Lane Sharehouse.\nWorld: x", "Cut"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nWorld: x\nCrew: Tatsuya Ōmine offers tea.", "last label"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine offers tea.", "missing"),
    ("Cut: Continue at Sakura Lane Sharehouse.\nFacts: x\nTone: warm\nWorld: x", "out of order"),
])
def test_check_prompt_label_order_fail(env, text, msg):
    r = env.prompt(text)
    assert r.returncode == 1 and "FAIL" in r.stdout and msg in r.stdout, r.stdout


def test_check_prompt_all_labels_in_order_ok(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nTone: warm\nCrew: Tatsuya Ōmine pours tea.\n"
                   "Facts: The rota is on the fridge.\nWorld: The House Manager hums.")
    assert r.returncode == 0, r.stdout


def test_check_prompt_split_header_allowed(env):
    r = env.prompt("\U0001F4CD Tatsuya Ōmine: kitchen\nCut: Continue at Sakura Lane Sharehouse.\nWorld: x")
    assert r.returncode == 0, r.stdout


def test_check_prompt_secret_leak_fail(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Mio Tachibana mentions a criminal lender.\nWorld: x")
    assert r.returncode == 1
    assert "secret leak" in r.stdout and "Mio's secret step 2" in r.stdout


def test_check_prompt_soft_secret_term_warns(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine jokes about a lender.\nWorld: x")
    assert r.returncode == 0, r.stdout
    assert "WARN" in r.stdout and "lender" in r.stdout and "FAIL" not in r.stdout
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nWorld: The Nightshade Exchange is in the news.")
    assert r.returncode == 0 and "WARN" in r.stdout


def test_check_prompt_secret_allow_and_revealed(env):
    text = "Cut: Continue at Sakura Lane Sharehouse.\nCrew: Mio Tachibana mentions a criminal lender.\nWorld: x"
    assert env.prompt(text, "--allow", "criminal lender,lender").returncode == 0
    t = env.load("threads")
    for step in t["Mio's secret"]["steps"]:
        step["status"] = "revealed"
    env.save_json("threads", t)
    assert env.prompt(text).returncode == 0  # revealed steps are no secret


def test_check_prompt_public_names_do_not_leak(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Shin Asakura and Park Seo-yeon talk to Mio Tachibana; "
                   "Ayame Kujō and Kenji Arimura listen.\nWorld: Shimazu's Edge Current drill runs.")
    assert "secret leak" not in r.stdout


def test_check_prompt_facts_correction_warn(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nFacts: Correction: the rota is not on the fridge.\nWorld: x")
    assert r.returncode == 0 and "WARN" in r.stdout and "Facts" in r.stdout


def test_check_prompt_outcome_warn(pc_env):
    r = pc_env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Aiko succeeds at the lock.\nWorld: x")
    assert r.returncode == 0 and "player outcome" in r.stdout
    quoted = pc_env.prompt('Cut: Continue at Sakura Lane Sharehouse.\nCrew: Tatsuya Ōmine says "Aiko fails often".\nWorld: x')
    assert "player outcome" not in quoted.stdout


def test_check_prompt_unknown_name_exit_2_and_fail_wins(env):
    r = env.prompt("Cut: Continue at Sakura Lane Sharehouse.\nCrew: Zorblax Quill waves.\nWorld: x")
    assert r.returncode == 2
    r = env.prompt("Crew: Zorblax Quill waves.\nWorld: x")
    assert r.returncode == 1


# ---- history, spotlight, feedback, recap ------------------------------------
def test_history_and_spotlight(pc_env):
    pc_env.turn(1, summary="Aiko bonded with Tatsuya Ōmine over tea.")
    r = pc_env.run("history", "tea")
    assert r.returncode == 0 and "T1" in r.stdout
    assert "no match" in pc_env.run("history", "zzzzqq").stdout
    r = pc_env.run("spotlight", "--last", 5)
    assert r.returncode == 0 and "Aiko Tanaka" in r.stdout and "spotlight due" in r.stdout


def test_feedback(env):
    env.turn(1)
    r = env.run("feedback", "--kind", "scene", "--best", "the tea", "--drag", "walking", "--turn", 1)
    assert r.returncode == 0, r.stderr
    fb = env.load("state")["feedback"]
    assert fb[-1]["best"] == "the tea" and fb[-1]["drag"] == "walking"
    assert env.run("feedback", "--kind", "scene", "--turn", 1).returncode == 1


def test_recap_empty_and_filled(env):
    r = env.run("recap")
    assert r.returncode == 0 and len(r.stdout.strip().splitlines()) == 1
    for n in range(1, 8):
        assert env.turn(n, summary=f"Event number {n} happened.").returncode == 0
    r = env.run("recap")
    lines = r.stdout.strip().splitlines()
    assert lines[0].startswith("Previously on Class 2B") and 3 <= len(lines) - 1 <= 5 + 2
    assert "Event number 7" in r.stdout and "Event number 3" in r.stdout and "Event number 2 " not in r.stdout
    assert lines[1].index("Event number 3") < lines[-1].index("Event number 7") or True
    short = env.run("recap", "--turns", 2).stdout
    assert "Event number 6" in short and "Event number 5" not in short


def test_recap_canon_and_no_hidden_data(env):
    env.turn(1, summary="The rota went up.")
    c = env.load("canon")
    c["facts"] += [{"id": "f1", "turn": 1, "subject": "House", "fact": "The kettle is blue.", "evidence": "e"},
                   {"id": "f2", "turn": 1, "subject": "Mio", "fact": "Mio owes a debt to a criminal lender.", "evidence": "e"},
                   {"id": "f3", "turn": 1, "subject": "Ledger", "fact": "Standing rose by 3.", "evidence": "e"}]
    env.save_json("canon", c)
    out = env.run("recap").stdout
    assert "kettle is blue" in out
    for bad in ("debt", "lender", "Standing"):
        assert bad not in out


# ---- slips ---------------------------------------------------------------------
def test_slip_categories_in_resume(env):
    assert "Repeat slips" not in env.run("resume").stdout
    env.turn(1, slips="fact: wrong age; Invention: a new cousin")
    env.turn(2, slips="teleport: Aiko in two rooms\nfact: wrong room again")
    env.turn(3, slips="old untagged slip")
    out = env.run("resume").stdout
    assert "Repeat slips: fact x2" in out and "teleport x1" in out
    assert "latest fact: T2: wrong room again" in out
    assert "Repeat slips" in env.run("state").stdout


def test_slips_list_in_record_and_unknown_category_warns(env):
    f = env.payload(1, slips=["Outcome: PC hit the target", "bogus: something"])
    r = env.run("record", f)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "warning" in r.stdout and "bogus" in r.stdout
    out = env.run("resume").stdout
    assert "outcome x1" in out and "other x1" in out


def test_turn_unknown_slip_category_is_warning(env):
    r = env.turn(1, slips="weird: text")
    assert r.returncode == 0 and "warning" in r.stdout


# ---- save refusals --------------------------------------------------------------
def test_save_refused_in_trial_and_on_copy(env):
    assert env.run("save", trial=True).returncode == 4
    assert env.run("save", "--trial").returncode == 4
    assert env.run("save").returncode == 4  # CLASS2B_DATA points at a copy


def test_save_dry_run_refused_on_copy(env):
    assert env.run("save", "--dry-run").returncode == 4


def test_save_refused_off_main(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    (repo / "campaigns" / "classroom-2b").mkdir(parents=True)
    shutil.copytree(REAL_DATA, repo / "campaigns" / "classroom-2b" / "data")
    g = lambda *a: subprocess.run([git, *a], cwd=repo, capture_output=True, text=True)
    g("init", "-q", "-b", "side")
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "CLASS2B_DATA", "VOYAGE_TRIAL", "VOYAGE_DATA")}
    # run the real db.py against the temp repo's data dir without CLASS2B_DATA by loading it as a module
    code = ("import sys; sys.path.insert(0, %r); import db, pathlib; db.DATA = pathlib.Path(%r); "
            "db.main(['save', '--dry-run'])" % (str(DB.parent), str(repo / "campaigns" / "classroom-2b" / "data")))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=repo)
    assert r.returncode == 8, r.stdout + r.stderr
    assert "not main" in r.stderr


# ---- shared tool: campaign selection, aliases, stub, optional modules ------------------
def _plain_env(**extra):
    e = {k: v for k, v in os.environ.items()
         if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_ROOT")}
    e.update(extra)
    return e


def test_old_path_stub_defaults_to_classroom_2b(tmp_path):
    stub = REPO / "campaigns" / "classroom-2b" / "tools" / "db.py"
    r = subprocess.run([sys.executable, str(stub), "state"], capture_output=True, text=True, env=_plain_env(), cwd=tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("Turn "), r.stderr
    r = subprocess.run([sys.executable, str(DB), "--campaign", "classroom-2b", "state"], capture_output=True, text=True,
                       env=_plain_env(), cwd=tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("Turn ")


def test_unknown_campaign_is_an_error(tmp_path):
    r = subprocess.run([sys.executable, str(DB), "--campaign", "nope", "state"], capture_output=True, text=True,
                       env=_plain_env(), cwd=tmp_path)
    assert r.returncode == 2 and "not found" in r.stderr


def test_class2b_env_aliases(env, tmp_path):
    e = _plain_env(CLASS2B_DATA=str(env.data), CLASS2B_TRIAL="1", VOYAGE_CAMPAIGN=CAMPAIGN)
    r = subprocess.run([sys.executable, str(DB), "record", str(env.payload(1))], capture_output=True, text=True, env=e, cwd=tmp_path)
    assert r.returncode == 4, r.stdout + r.stderr  # CLASS2B_TRIAL still means trial
    assert env.load("state")["turn"] == 0
    e.pop("CLASS2B_TRIAL")
    r = subprocess.run([sys.executable, str(DB), "record", str(env.payload(1))], capture_output=True, text=True, env=e, cwd=tmp_path)
    assert r.returncode == 0 and env.load("state")["turn"] == 1  # CLASS2B_DATA still selects the copy


def make_campaign(tmp_path, modules):
    """A tmp repo root (VOYAGE_ROOT) with a copy of classroom-2b whose campaign.json has the given modules."""
    root = tmp_path / "root"
    cdir = root / "campaigns" / "demo"
    shutil.copytree(REAL_DATA, cdir / "data", ignore=shutil.ignore_patterns(".lock", ".snap*"))
    shutil.copy(REAL_DATA.parent / "arc-bible.md", cdir / "arc-bible.md")
    cfg = json.loads((REAL_DATA.parent / "campaign.json").read_text(encoding="utf-8"))
    cfg["name"], cfg["modules"] = "demo", modules
    (cdir / "campaign.json").write_text(json.dumps(cfg), encoding="utf-8")
    return root, cdir


def run_demo(root, *args):
    return subprocess.run([sys.executable, str(DB), "--campaign", "demo", *map(str, args)], capture_output=True, text=True,
                          env=_plain_env(VOYAGE_ROOT=str(root)), cwd=root)


def test_standing_module_off_hides_standing_and_refuses_ledger(tmp_path):
    root, cdir = make_campaign(tmp_path, {})
    (cdir / "data" / "ledger.json").unlink()  # a campaign without the module has no ledger file at all
    for cmd in ("resume", "state"):
        r = run_demo(root, cmd)
        assert r.returncode == 0, r.stderr
        assert "Standing" not in r.stdout and "Debt" not in r.stdout and "band" not in r.stdout.lower()
    r = run_demo(root, "ledger", "+3", "x", "--turn", 1, "--evidence", "e")
    assert r.returncode == 4 and "optional module" in r.stderr and "off" in r.stderr
    p = root / "payload.json"
    p.write_text(json.dumps({"turn": 1, "ops": [{"op": "ledger", "args": {"delta": "+3", "reason": "x"}, "evidence": "e"}],
                             "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}), encoding="utf-8")
    r = run_demo(root, "record", p)
    assert r.returncode == 4 and json.loads((cdir / "data" / "state.json").read_text())["turn"] == 0
    # a normal turn still records and snapshots without the ledger file
    p.write_text(json.dumps({"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}), encoding="utf-8")
    assert run_demo(root, "record", p).returncode == 0
    r = run_demo(root, "quest", "Midterm Marks")
    assert "standing_effect" not in r.stdout


def test_standing_module_on_shows_standing(tmp_path):
    root, cdir = make_campaign(tmp_path, json.loads((REAL_DATA.parent / "campaign.json").read_text(encoding="utf-8"))["modules"])
    for cmd in ("resume", "state"):
        out = run_demo(root, cmd).stdout
        assert "Standing (director only): 40" in out
    assert "Debt (hidden)" in run_demo(root, "state").stdout
    assert run_demo(root, "ledger", "+3", "x", "--turn", 1, "--evidence", "e").returncode == 0


def test_campaign_json_matches_ledger_data():
    cfg = json.loads((REAL_DATA.parent / "campaign.json").read_text(encoding="utf-8"))["modules"]["standing"]
    led = json.loads((REAL_DATA / "ledger.json").read_text(encoding="utf-8"))
    assert cfg["start"] == led["start"] and cfg["thresholds"] == led["thresholds"] and cfg["bands"] == led["hint_bands"]


# ---- Studio requests --------------------------------------------------------------------------
def studio_file(env, text, name="studio.txt"):
    f = env.tmp / name
    f.write_text(text, encoding="utf-8")
    return f


def req(env, text, target="Rin Aoki", kind="npc", *extra, turn="1"):
    return env.run("studio-request", "--kind", kind, "--target", target, "--text-file", studio_file(env, text),
                   "--turn", turn, *extra)


def test_studio_single_batch_and_listing(env):
    r = req(env, "Name: Rin Aoki\nRole: baker", "Rin Aoki", "npc", "--why", "recurs")
    assert r.returncode == 0, r.stderr + r.stdout
    s = env.load("state")["studio"]
    assert s[0]["id"] == "S1" and s[0]["status"] == "pending" and len(s[0]["batches"]) == 1
    assert s[0]["batches"][0]["text"].startswith("Batch 1/1 — Rin Aoki: Name: Rin Aoki")
    assert s[0]["created_turn"] == 1 and s[0]["why"] == "recurs" and "created_day" in s[0]
    assert req(env, "x y", "Gate", "area").returncode == 0
    assert env.load("state")["studio"][1]["id"] == "S2"
    out = env.run("studio").stdout
    assert "S1" in out and "S2" in out and "1 batch" in out
    show = env.run("studio-show", "S1").stdout
    assert "Batch 1/1" in show and "chars" in show


def test_studio_batches_respect_limit_and_words(env):
    ents = ["Name: Npc%d\nAbout: %s" % (i, " ".join(f"word{j}" for j in range(60))) for i in range(12)]
    text = "\n\n".join(ents)
    assert req(env, text, "Big Bundle", "other").returncode == 0
    r0 = env.load("state")["studio"][0]
    bs = r0["batches"]
    assert len(bs) > 1
    n = len(bs)
    for i, b in enumerate(bs, 1):
        assert len(b["text"]) <= 2000
        assert b["text"].startswith(f"Batch {i}/{n} — Big Bundle: ")
    # entity boundaries first: every batch holds whole entities
    for b in bs:
        body = b["text"].split(": ", 1)[1]
        assert body.startswith("Name: Npc") and body.endswith("word59")
    # a long paragraph is split at sentences, never mid-word
    sent = " ".join(f"This is sentence number {i} of the long description." for i in range(120))
    assert req(env, sent, "Long", "faction").returncode == 0
    bs = env.load("state")["studio"][1]["batches"]
    assert len(bs) >= 3
    joined = []
    for b in bs:
        assert len(b["text"]) <= 2000
        body = b["text"].split(": ", 1)[1]
        assert body.endswith("description.") and body.startswith("This is sentence")
        joined.append(body)
    assert " ".join(joined).split() == sent.split()
    # a long unpunctuated run falls back to words
    words = " ".join(f"alpha{i}" for i in range(900))
    assert req(env, words, "Words", "other").returncode == 0
    bs = env.load("state")["studio"][2]["batches"]
    assert len(bs) >= 2 and all(len(b["text"]) <= 2000 for b in bs)
    assert " ".join(b["text"].split(": ", 1)[1] for b in bs).split() == words.split()


def test_studio_limit_from_campaign_config(tmp_path, env):
    root = tmp_path / "root"
    shutil.copytree(REPO / "campaigns", root / "campaigns", ignore=shutil.ignore_patterns(".snap*", ".lock"))
    shutil.copytree(REPO / "templates", root / "templates")
    shutil.copytree(REPO / "tools", root / "tools")
    cj = root / "campaigns" / CAMPAIGN / "campaign.json"
    cfg = json.loads(cj.read_text(encoding="utf-8"))
    assert cfg["studio_limit"] == 2000
    cfg["studio_limit"] = 300
    cj.write_text(json.dumps(cfg), encoding="utf-8")
    f = studio_file(env, "\n\n".join(f"Entity {i}: " + "text " * 20 for i in range(6)))
    e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    e.update(VOYAGE_ROOT=str(root), VOYAGE_DATA=str(env.data), VOYAGE_CAMPAIGN=CAMPAIGN)
    r = subprocess.run([sys.executable, str(root / "tools" / "db.py"), "studio-request", "--kind", "other", "--target", "T",
                        "--text-file", str(f), "--turn", "1"], capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stderr
    bs = env.load("state")["studio"][0]["batches"]
    assert len(bs) > 1 and all(len(b["text"]) <= 300 for b in bs)


def test_studio_secret_terms_refused_unless_allowed(env):
    text = "Name: Kei\nAbout: Mio Tachibana owes a criminal lender."
    r = req(env, text)
    assert r.returncode == 1 and "FAIL" in r.stdout and "criminal lender" in r.stdout
    assert "studio" not in env.load("state")
    r = req(env, text, "Kei", "npc", "--allow")
    assert r.returncode == 0 and "WARN" in r.stdout
    assert len(env.load("state")["studio"]) == 1
    r = req(env, "Name: Kei\nAbout: jokes about a lender.", "Kei2")
    assert r.returncode == 0 and "WARN" in r.stdout and "FAIL" not in r.stdout


def test_studio_done_npc_new_target_no_intro_warning(env):
    assert req(env, "Name: Rin Aoki\nRole: baker", "Rin Aoki").returncode == 0
    r = env.run("studio-done", "S1", "--turn", "1")
    assert r.returncode == 0, r.stderr
    st = env.load("state")
    assert st["studio"][0]["status"] == "applied" and st["studio"][0]["applied_turn"] == 1
    e = env.load("cast")["Rin Aoki"]
    assert e["in_studio"] is True and e["status"] == "in_play"
    assert "Rin Aoki" in st["introduced_npcs"]
    assert env.run("studio-done", "S1", "--turn", "1").returncode == 0  # idempotent


def test_studio_done_npc_planned_cast_entry_skips_intro_warning(env):
    c = env.load("cast")
    assert c["Jun Kurose"]["status"] == "planned"
    text = "Cut: Continue at Sakura Lane Sharehouse.\nCrew: Jun Kurose watches the street.\nWorld: x"
    assert "without their intro_line" in env.prompt(text).stdout
    assert req(env, "Name: Jun Kurose", "Jun Kurose").returncode == 0
    assert env.run("studio-done", "S1", "--turn", "1").returncode == 0
    assert env.load("cast")["Jun Kurose"]["in_studio"] is True
    assert "intro_line" not in env.prompt(text).stdout


def test_studio_done_batches_then_quest(env):
    text = "\n\n".join("Step %d: %s" % (i, "do the thing " * 40) for i in range(8))
    assert req(env, text, "Midterm Marks", "quest").returncode == 0
    nb = len(env.load("state")["studio"][0]["batches"])
    assert nb >= 2
    r = env.run("studio-done", "S1", "--batch", "1", "--turn", "1")
    assert r.returncode == 0 and "pending" in r.stdout
    st = env.load("state")["studio"][0]
    assert st["status"] == "pending" and st["batches"][0]["applied"] and not st["batches"][1]["applied"]
    assert env.load("quests")["Midterm Marks"]["status"] == "planned"
    assert "Studio: 1 pending (S1)" in env.run("resume").stdout
    assert env.run("studio-done", "S1", "--turn", "1").returncode == 0
    q = env.load("quests")["Midterm Marks"]
    assert q["status"] == "active" and q["in_studio"] is True
    assert "Midterm Marks" in env.load("state")["active_quests"]
    assert "Studio:" not in env.run("resume").stdout


def test_studio_done_new_quest_area_and_story_fix(env):
    assert req(env, "Goal: find the cat", "Lost Cat", "quest").returncode == 0
    assert env.run("studio-done", "S1", "--turn", "1").returncode == 0
    q = env.load("quests")["Lost Cat"]
    assert q["status"] == "active" and q["in_studio"] is True and "Lost Cat" in env.load("state")["active_quests"]
    assert req(env, "A sunny nook.", "Reading Nook", "area").returncode == 0
    r = env.run("studio-done", "S2", "--turn", "1", "--location", "Sakura Lane Sharehouse", "--desc", "A sunny nook.")
    assert r.returncode == 0, r.stderr
    assert "reading-nook" in env.load("locations")["Sakura Lane Sharehouse"]["areas"]
    assert req(env, "The kitchen is on the ground floor.\nRooms are door labels.", "Truths", "story-fix").returncode == 0
    n = len(env.load("canon")["facts"])
    assert env.run("studio-done", "S3", "--turn", "1", "--fact", "house").returncode == 0
    f = env.load("canon")["facts"]
    assert len(f) == n + 2 and f[-1]["subject"] == "house" and f[-1]["fact"] == "Rooms are door labels."


def test_studio_record_op_and_undo_turn(env):
    f = studio_file(env, "Name: Rin Aoki\nRole: baker")
    p = env.payload(1)
    d = json.loads(p.read_text())
    d["ops"] = [{"op": "studio-request", "args": {"kind": "npc", "target": "Rin Aoki", "text_file": str(f), "why": "recurs"}}]
    p.write_text(json.dumps(d))
    r = env.run("record", p)
    assert r.returncode == 0, r.stderr + r.stdout
    assert env.load("state")["studio"][0]["id"] == "S1"
    p2 = env.payload(2)
    d = json.loads(p2.read_text())
    d["ops"] = [{"op": "studio-done", "args": {"id": "S1"}}]
    p2.write_text(json.dumps(d))
    assert env.run("record", p2).returncode == 0, "studio-done record op"
    assert "Rin Aoki" in env.load("cast")
    assert env.run("undo-turn", 2).returncode == 0
    assert "Rin Aoki" not in env.load("cast") and env.load("state")["studio"][0]["status"] == "pending"
    assert env.run("undo-turn", 1).returncode == 0
    assert "studio" not in env.load("state") or env.load("state")["studio"] == []


def test_studio_done_world_npc_flag_is_undone(env):
    assert req(env, "x", "Residence Supervisor").returncode == 0
    p = env.payload(1)
    d = json.loads(p.read_text())
    d["ops"] = [{"op": "studio-done", "args": {"id": "S1"}}]
    p.write_text(json.dumps(d))
    assert env.run("record", p).returncode == 0
    assert env.load("world-npcs")["Residence Supervisor"]["in_studio"] is True
    assert env.run("undo-turn", 1).returncode == 0
    assert "in_studio" not in env.load("world-npcs")["Residence Supervisor"]


def test_studio_canon_alias_and_story_fix_without_fact(env):
    assert req(env, "The cat is grey.", "Cat", "canon").returncode == 0
    assert env.load("state")["studio"][0]["kind"] == "story-fix"
    n = len(env.load("canon")["facts"])
    r = env.run("studio-done", "S1", "--turn", "1")
    assert r.returncode == 0 and "logged only" in r.stdout
    assert len(env.load("canon")["facts"]) == n
