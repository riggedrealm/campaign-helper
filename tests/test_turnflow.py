"""prep / commit-turn / wrap-up and alias matching. Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA)."""
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
SAYS = "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\nCrew: {crew}\nWorld: The House Manager posts the chore rota."
CREW_MIO = "Mio Tachibana counts coins twice, shoulders tight, mouth flat: \"I'm fine, really.\""


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, trial=False, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": "classroom-2b", "PYTHONDONTWRITEBYTECODE": "1"})
        if trial:
            e["VOYAGE_TRIAL"] = "1"
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def files(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def prep(self, paste=None, *args):
        a = ["prep", *args]
        if paste is not None:
            a += ["--paste", self.files("paste.txt", paste)]
        r = self.run(*a)
        assert r.returncode == 0, r.stderr + r.stdout
        return r.stdout

    def commit(self, prompt, payload=None, *args, **kw):
        payload = payload if payload is not None else {}
        t = self.load("state")["turn"] + 1
        payload = {"turn": t, "ops": [], "turn_log": {"inputs": "i", "summary": f"summary {t}"}, **payload}
        return self.run("commit-turn", "--prompt", self.files("prompt.txt", prompt), "--payload",
                        self.files("payload.json", json.dumps(payload)), *args, **kw)

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr
    return e


# ---- prep ---------------------------------------------------------------------
def test_prep_detects_names_aliases_and_places(env):
    out = env.prep('Sunny flopped on the sofa. "Where is Tatsuya?" Mio sighed in the Sakura Lane Sharehouse kitchen.')
    present = next(l for l in out.splitlines() if l.startswith("PRESENT:"))
    for who in ("Park Seo-yeon", "Tatsuya Ōmine", "Mio Tachibana"):  # alias, first name, first name
        assert who in present
    assert "BRIEF" not in out and "voice:" in out and "won't yet:" in out and "beat A" in out
    assert "Sakura Lane Sharehouse" in out and "LIVE CHECKLIST" in out and "unpushed:" in out
    assert len(out.splitlines()) <= 70
    assert "Prompt budget: limit 840" in out


def test_prep_names_option_and_full(env):
    out = env.prep(None, "--names", "Arimura,Shin", "--full", "Kenji")
    present = next(l for l in out.splitlines() if l.startswith("PRESENT:"))
    assert "Kenji Arimura (--names)" in present and "Shin Asakura (--names)" in present
    assert "BRIEF Kenji Arimura" in out  # --full prints the whole brief
    bad = env.run("prep", "--names", "Nobody Atall")
    assert bad.returncode == 0 and "no NPC matches" in bad.stdout


def test_prep_unknown_paste_file_fails(env):
    assert env.run("prep", "--paste", env.tmp / "nope.txt").returncode == 1


def test_scene_present_carries_over(env):
    assert env.run("scene-start", "Kitchen", "--budget", "4", "--turn", "1", "--evidence", "x").returncode == 0
    r = env.commit(SAYS.format(crew=CREW_MIO))
    assert r.returncode == 0, r.stdout + r.stderr
    assert env.load("state")["scene"]["present"] == ["Mio Tachibana"]
    out = env.prep(None)  # no paste, no names: carried over from the open scene
    assert "Mio Tachibana (scene)" in out
    out = env.prep("Tatsuya waved.")
    assert "Mio Tachibana (scene)" in out and "Tatsuya Ōmine (paste)" in out


def test_present_override_in_payload(env):
    env.run("scene-start", "Kitchen", "--budget", "4", "--turn", "1", "--evidence", "x")
    r = env.commit(SAYS.format(crew=CREW_MIO), {"present": ["Tatsuya", "Reiko Shimazu"]})
    assert r.returncode == 0, r.stdout
    assert env.load("state")["scene"]["present"] == ["Tatsuya Ōmine", "Reiko Shimazu"]


def test_expression_rotation_never_repeats_last_two_turns(env):
    seen = []
    for _ in range(4):
        out = env.prep(None, "--names", "Mio")
        shows = [l.split("show:", 1)[1].strip() if "show:" in l else l.strip() for l in out.splitlines()
                 if "show:" in l or l.startswith("        ")]
        seen.append(shows)
        kit = env.load("cast")["Mio Tachibana"]["expression"]
        # write the first pick into the Crew line, as the director would
        first = shows[0].split(": ", 1)[1].strip('"')
        r = env.commit(SAYS.format(crew=f"Mio Tachibana: {first}, shoulders tight."))
        assert r.returncode == 0, r.stdout + r.stderr
    rec = env.load("state")["expression"]["Mio Tachibana"]
    assert rec["cursor"] == 4 and len(rec["recent"]) == 2 and all(rec["recent"])  # the picks were detected as used
    for i in range(2, 4):
        prev = " ".join(seen[i - 1] + seen[i - 2])
        assert seen[i][0].split(": ", 1)[1] not in prev, (i, seen)
    assert kit  # the kit exists


def test_checklist_never_leaks_hidden_ladder_text(env):
    threads = env.load("threads")
    names = ",".join(n for t in threads.values() for n in t.get("npcs") or [])
    out = env.prep("Mio Tachibana and Tatsuya argued.", "--names", names)
    for k, t in threads.items():
        for s in t["steps"]:
            if s["status"] == "hidden":
                assert s["reveal"] not in out, (k, s["step"])
    assert "next hidden step: Mio's secret step 1" in out and "keep out" in out


def test_checklist_shows_revealed_step_only_and_slip_reminder(env):
    assert env.run("thread-reveal", "Mio's secret", 1, "--turn", "1", "--evidence", "e", "--force").returncode == 0
    for n, cat in ((1, "teleport"), (2, "teleport")):
        assert env.run("turn", n, "--inputs", "i", "--summary", "s", "--prompt", "Cut: x\nWorld: y", "--slips", f"{cat}: moved").returncode == 0
    out = env.prep(None, "--names", "Mio")
    assert "public: She is hiding money trouble." in out
    assert "next hidden step: Mio's secret step 2" in out and "It is a debt to a criminal lender" not in out
    assert "repeat slips: teleport x2" in out and "reminder: teleport slips are common" in out


# ---- aliases, ambiguity -----------------------------------------------------------------
def add_npc(env, key, **kw):
    cast = env.load("cast")
    cast[key] = {"name": key, "alias": None, "status": "in_play", "gender": "female", "kind": "housemate", **kw}
    env.save_json("cast", cast)


def test_ambiguous_short_name_warns(env):
    add_npc(env, "Hana Kuroda")
    add_npc(env, "Rika Kuroda")
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Kuroda hums by the stove.")))
    assert r.returncode == 0, r.stdout
    assert "WARN: AMBIGUOUS name Kuroda: Hana Kuroda | Rika Kuroda" in r.stdout
    out = env.prep("Kuroda smiled.")
    assert "WARN: AMBIGUOUS name Kuroda" in out
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Hana Kuroda hums by the stove.")))
    assert "AMBIGUOUS" not in r.stdout


def test_explicit_alias_beats_derived_form(env):
    add_npc(env, "Hana Kuroda", aliases=["Kuroda"])
    add_npc(env, "Rika Kuroda")
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Kuroda hums by the stove.")))
    assert "AMBIGUOUS" not in r.stdout
    assert "Hana Kuroda (paste)" in env.prep("Kuroda smiled.")


def test_default_aliases_title_less_and_first_last(env):
    add_npc(env, "Park Minho")  # "Park" is a skipped title token in this campaign
    add_npc(env, "Hana Mei Sato")
    for form, key in (("Minho", "Park Minho"), ("Hana", "Hana Mei Sato"), ("Sato", "Hana Mei Sato"), ("Hana's", "Hana Mei Sato")):
        assert f"{key} (paste)" in env.prep(f"{form} bowed."), form
    assert "Park Minho (paste)" not in env.prep("Park bowed.")  # the skipped token is not an alias


def test_use_full_name_warns_but_is_not_unknown(env):
    add_npc(env, "Court Mage Serika Amamiya", aliases=["Serika"], use_full_name=True)
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Serika sips cold tea without a word.")))
    assert r.returncode == 0 and 'WARN: use full name "Court Mage Serika Amamiya"' in r.stdout and "UNKNOWN" not in r.stdout
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Court Mage Serika Amamiya sips cold tea without a word.")))
    assert "use full name" not in r.stdout


def test_unknown_name_still_exit_2(env):
    r = env.run("check-prompt", env.files("p.txt", SAYS.format(crew="Zorblax Quenth grins.")))
    assert r.returncode == 2 and "UNKNOWN" in r.stdout


def test_shipped_cast_explicit_aliases(env):
    cast = json.loads((REPO / "campaigns" / "luxcellia" / "data" / "cast.json").read_text(encoding="utf-8"))
    assert cast["Court Mage Serika Amamiya"]["use_full_name"] is True and "Serika" in cast["Court Mage Serika Amamiya"]["aliases"]
    main = json.loads((REPO / "campaigns" / "luxcellia" / "campaign.json").read_text(encoding="utf-8"))["main_npcs"]
    assert all(cast[n].get("aliases") for n in main)
    c2 = json.loads((REPO / "campaigns" / "classroom-2b" / "data" / "cast.json").read_text(encoding="utf-8"))
    assert c2["Tatsuya Ōmine"]["aliases"] == ["Tatsuya"]


# ---- commit-turn ---------------------------------------------------------------------
def test_commit_turn_applies_like_record(env):
    p = {"ops": [{"op": "fact", "args": {"subject": "rota", "text": "Chore rota is on the fridge."}, "evidence": "posted"}]}
    r = env.commit(SAYS.format(crew=CREW_MIO), p)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "commit-turn 1: ok" in r.stdout and "git: skipped" in r.stdout
    t = env.load("turns")[0]
    assert t["prompt"] == SAYS.format(crew=CREW_MIO) and env.load("state")["turn"] == 1
    assert env.load("canon")["facts"][0]["subject"] == "rota"
    assert env.commit(SAYS.format(crew=CREW_MIO), {"turn": 1}).returncode == 4  # replay is refused
    assert not list(env.data.glob("*.tmp"))


def test_commit_turn_fail_writes_nothing(env):
    before = env.hashes()
    r = env.commit("Cut: x\n" + "a" * 900 + "\nWorld: y")
    assert r.returncode == 1 and "FAIL" in r.stdout and "nothing written" in r.stdout
    r2 = env.commit("Crew: no cut label first\nWorld: y")
    assert r2.returncode == 1
    assert env.hashes() == before and not (env.data / ".snapshots").exists()


def test_commit_turn_name_warnings_do_not_block(env):
    r = env.commit(SAYS.format(crew="Zorblax Quenth grins at Tatsuya."))  # unknown name: warning only
    assert r.returncode == 0, r.stdout
    assert env.load("state")["turn"] == 1


def test_commit_turn_collects_all_payload_errors(env):
    before = env.hashes()
    p = {"ops": [
        {"op": "pos", "args": {"pc": "Aiko", "location": "Atlantis", "area": "x"}, "evidence": "e"},
        {"op": "time", "args": {"block": "Teatime"}, "evidence": "e"},
        {"op": "fact", "args": {"subject": "only subject"}, "evidence": "e"},
        {"op": "nonsense", "args": {}},
        {"op": "fact", "args": {"subject": "ok", "text": "fine"}},  # no evidence
    ], "turn_log": {"inputs": "", "summary": "one\ntwo\nthree"}}
    r = env.commit(SAYS.format(crew=CREW_MIO), p)
    assert r.returncode == 2, r.stdout
    assert "problem(s), nothing written" in r.stdout
    n = int(r.stdout.split("commit-turn: ")[1].split(" problem")[0])
    assert n >= 6
    for frag in ("Atlantis", "Teatime", "op 3 (fact)", "unknown op 'nonsense'", "op 5 (fact)", "turn_log.inputs", "two lines max"):
        assert frag in r.stdout, frag
    assert env.hashes() == before


def test_commit_turn_normalises_time_words(env):
    t = env.load("state")["time_block"]
    p = {"ops": [{"op": "time", "args": {"block": "Dusk"}, "evidence": "lanterns on"}]}
    r = env.commit(SAYS.format(crew=CREW_MIO), p)
    assert r.returncode == 0, r.stdout
    assert 'block "Dusk" -> "Evening"' in r.stdout
    st = env.load("state")
    assert (st["time_block"], st["clock"]) == ("Evening", "18:30") and t != "Evening"


@pytest.mark.parametrize("word,block", [("dawn", "Dawn"), ("late morning", "Morning"), ("noon", "Afternoon"), ("Afternoon", "Afternoon"),
                                         ("evening", "Evening"), ("night", "Late Night"), ("late night", "Late Night"),
                                         ("midnight", "Midnight"), ("sunset", "Evening"), ("MORNING", "Morning")])
def test_time_word_mapping(env, word, block):
    p = {"ops": [{"op": "time", "args": {"day": "Day 2", "block": word}, "evidence": "e"}]}
    r = env.commit(SAYS.format(crew=CREW_MIO), p, "--dry-run")
    assert r.returncode == 0, r.stdout
    import re
    assert re.search(rf"-> Day 2 \w+ {block} ", r.stdout), r.stdout
    assert env.load("state")["turn"] == 0  # dry run


def test_commit_turn_dry_run_and_trial(env):
    before = env.hashes()
    r = env.commit(SAYS.format(crew=CREW_MIO), None, "--dry-run", trial=True)
    assert r.returncode == 0 and "dry run OK" in r.stdout and env.hashes() == before
    assert env.commit(SAYS.format(crew=CREW_MIO), trial=True).returncode == 4


def test_commit_turn_prints_studio_batches(env):
    f = env.files("fix.txt", "Mio never left the kitchen.")
    p = {"ops": [{"op": "studio-request", "args": {"kind": "story-fix", "target": "Turn 1", "text_file": str(f)}, "evidence": "slip"}]}
    r = env.commit(SAYS.format(crew=CREW_MIO), p)
    assert r.returncode == 0, r.stdout
    tail = r.stdout.split("STUDIO request S1", 1)[1]
    assert "--- Batch 1/1:" in tail and "Mio never left the kitchen." in tail
    shown = env.run("studio-show", "S1").stdout
    assert "Mio never left the kitchen." in shown
    r = env.commit(SAYS.format(crew=CREW_MIO))
    assert "STUDIO request" not in r.stdout  # only requests created this turn


def test_commit_turn_error_restores(env, monkeypatch):
    # a failing op in the real run (after validation) is covered by record's restore; here: ordinary failure leaves data intact
    before = env.hashes()
    r = env.commit(SAYS.format(crew=CREW_MIO), {"ops": [{"op": "quest-start", "args": {"name": "No Such Quest"}, "evidence": "e"}]})
    assert r.returncode == 2 and env.hashes() == before


def test_old_record_still_works(env):
    p = {"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}
    f = env.files("rec.json", json.dumps(p))
    assert env.run("record", f).returncode == 0 and env.load("state")["turn"] == 1


# ---- git: local commits, push_every batching, wrap-up -----------------------------------------
def git(cwd, *a):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def genv(tmp_path):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    work.mkdir()
    git(work, "init", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "T")
    data = work / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (work / ".gitignore").write_text("data/.snapshots/\ndata/.lock\ndata/*.json.tmp\n")
    git(work, "add", "-A")
    git(work, "commit", "-m", "init")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-u", "origin", "main")
    e = Env(data, tmp_path)
    assert e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "t").returncode == 0
    git(work, "commit", "-am", "pc")
    git(work, "push")
    e.work, e.remote = work, remote
    return e


def ahead(e):
    return int(git(e.work, "rev-list", "--count", "origin/main..HEAD"))


def test_commit_turn_commits_locally_and_pushes_in_batches(genv):
    e = genv
    for n in range(1, 4):
        r = e.commit(SAYS.format(crew=CREW_MIO), None, "--push-every", 3)
        assert r.returncode == 0, r.stdout + r.stderr
        assert f'committed "Class 2B save: turn {n}"' in r.stdout or f"save: turn {n}" in r.stdout
        if n < 3:
            assert f"unpushed {n}/3" in r.stdout and "pushed main" not in r.stdout
            assert ahead(e) == n
    assert "pushed main" in r.stdout and ahead(e) == 0
    files = git(e.work, "show", "--name-only", "--format=", "HEAD").split()
    assert files and all(f.startswith("data/") and f.endswith(".json") for f in files)
    assert git(e.remote, "log", "-1", "--format=%s", "main") == "Class 2B save: turn 3"
    assert "unpushed: 0" in e.run("resume").stdout


def test_default_push_every_is_one(genv):
    e = genv  # SAVE-1: every turn is pushed unless the campaign or --push-every says otherwise
    for n in range(1, 3):
        r = e.commit(SAYS.format(crew=CREW_MIO))
        assert r.returncode == 0 and "pushed main" in r.stdout and ahead(e) == 0, r.stdout + r.stderr
    assert "unpushed: 0" in e.prep(None)
    r = e.commit(SAYS.format(crew=CREW_MIO), None, "--push-every", 2)  # the option still overrides
    assert "unpushed 1/2" in r.stdout and "pushed main" not in r.stdout and ahead(e) == 1


def test_push_failure_keeps_going(genv):
    e = genv
    shutil.rmtree(e.remote)
    r = e.commit(SAYS.format(crew=CREW_MIO), None, "--push-every", 1, "--retries", 1)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARN push failed" in r.stdout and e.load("state")["turn"] == 1
    assert git(e.work, "log", "-1", "--format=%s") == "Class 2B save: turn 1"


def test_off_main_refused_before_writing(genv):
    e = genv
    git(e.work, "checkout", "-b", "side")
    before = e.hashes()
    r = e.commit(SAYS.format(crew=CREW_MIO))
    assert r.returncode == 8 and e.hashes() == before


def test_wrap_up_pushes_everything(genv):
    e = genv
    for _ in range(2):
        e.commit(SAYS.format(crew=CREW_MIO), None, "--push-every", 5)
    assert ahead(e) == 2
    # an uncommitted change made by plain `record` is picked up too
    p = {"turn": 3, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}
    assert e.run("record", e.files("rec.json", json.dumps(p))).returncode == 0
    r = e.run("wrap-up")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "safe to close: pushed" in r.stdout and "Studio pending: none" in r.stdout and "Open items:" in r.stdout
    assert ahead(e) == 0 and git(e.work, "status", "--porcelain", "--", "data") == ""
    assert git(e.remote, "log", "-1", "--format=%s", "main").endswith("(wrap-up)")
    again = e.run("wrap-up")
    assert "nothing to push" in again.stdout and "safe to close" in again.stdout


def test_wrap_up_reports_failure_and_pending_studio(genv):
    e = genv
    f = e.files("fix.txt", "Fix text.")
    e.commit(SAYS.format(crew=CREW_MIO), {"ops": [{"op": "studio-request", "args": {"kind": "story-fix", "target": "T1", "text_file": str(f)}, "evidence": "x"}]},
             "--push-every", 5)
    shutil.rmtree(e.remote)
    r = e.run("wrap-up", "--retries", 1)
    assert r.returncode == 5 and "NOT safe to close" in r.stdout


def test_wrap_up_without_git_is_fine(env):
    r = env.run("wrap-up")
    assert r.returncode == 0 and "safe to close" in r.stdout and "nothing to push" in r.stdout


# ---- player-driven pull-forward, surface goals ----------------------------------------------
def reveal(env, name, step, *extra):
    return env.run("thread-reveal", name, step, "--turn", "1", "--evidence", "player reached it", *extra)


def test_player_driven_allows_exactly_one_act_early(env):
    assert reveal(env, "Mio's secret", 1).returncode == 0
    assert reveal(env, "Mio's secret", 2).returncode == 4  # act 2 step in act 1, no flag: refused
    r = reveal(env, "Mio's secret", 2, "--player-driven")
    assert r.returncode == 0, r.stdout + r.stderr
    s = env.load("threads")["Mio's secret"]["steps"][1]
    assert s["status"] == "revealed" and s["player_driven"] is True and s["evidence"] == "player reached it" and "forced" not in s
    assert "PLAYER-DRIVEN" in env.run("thread", "Mio's secret").stdout


def test_player_driven_refuses_two_acts_early_gated_and_skipped_steps(env):
    assert reveal(env, "Mio's secret", 1).returncode == 0
    assert reveal(env, "Mio's secret", 3, "--player-driven").returncode == 4  # act 3 from act 1; step 2 still hidden
    assert reveal(env, "Mio's secret", 2, "--player-driven").returncode == 0
    r = reveal(env, "Mio's secret", 3, "--player-driven")  # act 3 while in act 1: two acts early
    assert r.returncode == 4 and "ONE act" in r.stderr + r.stdout
    assert env.load("threads")["Mio's secret"]["steps"][2]["status"] == "hidden"
    # a gated step one act early still needs its gate
    th = env.load("threads")
    th["Shin's old gang"]["steps"][1]["milestone_gate"] = "the rooftop talk"
    env.save_json("threads", th)
    assert reveal(env, "Shin's old gang", 1).returncode == 0
    assert reveal(env, "Shin's old gang", 2, "--player-driven").returncode == 4
    assert reveal(env, "Shin's old gang", 2, "--player-driven", "--gate-met").returncode == 0
    # --force still works and is recorded as forced
    assert reveal(env, "Mio's secret", 3, "--force").returncode == 0
    assert env.load("threads")["Mio's secret"]["steps"][2]["forced"] is True


def test_player_driven_flag_in_commit_turn_op(env):
    assert reveal(env, "Mio's secret", 1).returncode == 0
    op = {"op": "thread-reveal", "args": {"name": "Mio's secret", "step": 2, "player_driven": True}, "evidence": "player pressed Mio about the money"}
    r = env.commit(SAYS.format(crew=CREW_MIO), {"ops": [op]})
    assert r.returncode == 0, r.stdout + r.stderr
    s = env.load("threads")["Mio's secret"]["steps"][1]
    assert s["player_driven"] is True and "pressed Mio" in s["evidence"]


def test_prep_prints_surface_goal_or_flags_missing(env):
    q = env.load("quests")
    st = env.load("state")
    a, b = list(q)[:2]
    q[a].update(status="active", seed_line="", surface_goal="Carry the House Manager's parcel to the station for 500 yen; late means a scolding.")
    q[b].update(status="active", seed_line="")
    c = list(q)[2]
    q[c].update(status="active", seed_line="Start quest: the rota errand, for the House Manager, 300 yen.")
    st["active_quests"] = [a, b, c]
    env.save_json("quests", q); env.save_json("state", st)
    out = env.prep(f"They talked about {a}, {b} and {c}.")
    assert "Carry the House Manager's parcel" in out
    assert f"quest {b}: no surface goal set" in out
    assert "the rota errand, for the House Manager" in out
    assert "no surface goal set" not in next(l for l in out.splitlines() if "surface goal," in l and a in l)


def test_prep_fight_status_line(env):
    st = env.load("state")
    st["scene"] = {"name": "Cellar brawl", "location": "Sakura Lane Sharehouse", "area": "shared-kitchen", "budget": 4,
                   "turns_used": 0, "obstacles_used": [], "surprise_used": False, "started_turn": 1}
    env.save_json("state", st)
    assert "fight status unknown: write conditional prompt" in env.prep("Nothing yet.")
    out = env.prep("Aiko swings.\nfight status: 0 rats left")
    assert "fight status: 0 rats left" in out and "status unknown" not in out
    st["scene"].update(name="Chore rota", fight=False)
    env.save_json("state", st)
    assert "fight status" not in env.prep("Quiet morning.")
    st["scene"]["fight"] = True
    env.save_json("state", st)
    assert "fight status unknown" in env.prep("Quiet morning.")
