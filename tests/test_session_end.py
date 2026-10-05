"""Session start and end: resume, preflight, wrap-up, history --last, review-add, push every turn, help texts (SAVE-1, SAVE-2, REVIEW-1,
LOG-5, CHAT-1, CHAT-4, D8, K14, K20). Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA).
No test asserts on the first line of an output: every campaign command starts with the campaign line."""
import fcntl
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
REAL_DATA = REPO / "campaigns" / "classroom-2b" / "data"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, campaign="classroom-2b"):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": campaign, "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def record(self, n, slips="", inputs=None, prompt=None):
        tl = {"inputs": inputs or f"input of turn {n}", "summary": f"summary {n}", "prompt": prompt or f"Cut: Continue at the kitchen, turn {n}.\nWorld: Quiet.",
              "notes": f"note {n}"}
        if slips:
            tl["slips"] = slips
        f = self.tmp / f"rec{n}.json"
        f.write_text(json.dumps({"turn": n, "ops": [], "turn_log": tl}), encoding="utf-8")
        return self.ok("record", f)

    def review(self, turn, slips):
        return self.run("review-add", "--turn", turn, "--slips", slips)


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)
    e = Env(data, tmp_path)
    e.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    return e


def bootstrap_version():
    return re.search(r"^Skill version:\s*(\S+)", (REPO / ".claude/skills/voyage-director/SKILL.md").read_text(encoding="utf-8"), re.M).group(1)


# ---- push every turn (SAVE-1) -------------------------------------------------------
def test_push_every_defaults_to_one_and_joestar_no_longer_overrides_it():
    for name in ("classroom-2b", "joestar", "luxcellia"):
        assert "push_every" not in json.loads((REPO / "campaigns" / name / "campaign.json").read_text(encoding="utf-8")), name
        code = "import sys; sys.path.insert(0, 'tools'); import db; print(db.push_every())"
        e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
        e.update({"VOYAGE_CAMPAIGN": name, "PYTHONDONTWRITEBYTECODE": "1"})
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=REPO)
        assert r.stdout.strip() == "1", (name, r.stdout, r.stderr)


def test_commit_turn_help_names_the_new_default(env):
    out = env.ok("commit-turn", "-h")
    assert "else 1" in out and "default: campaign.json push_every, 5" not in out


# ---- help texts (K20) ------------------------------------------------------------
def test_feedback_help_no_longer_asks_at_scene_end(env):
    out = " ".join(env.ok("feedback", "-h").split())
    assert "Best moment" not in out and "Anything drag" not in out
    assert "only when the player raises it" in out


def test_scene_start_budget_help_points_at_bible_budgets(env):
    out = " ".join(env.ok("scene-start", "-h").split())
    assert "section 14" not in out and "arc-bible.md" not in out and "bible budgets" in out
    r = env.run("scene-start", "x", "--budget", "0", "--turn", "1", "--evidence", "t")
    assert r.returncode != 0 and "bible budgets" in r.stderr and "section 14" not in r.stderr


# ---- resume (CHAT-1, SYNC-7, REVIEW-1) ----------------------------------------------
def test_resume_with_a_director_md_prints_only_the_generic_version_and_no_old_skill_pointers(env):
    assert (REPO / "campaigns/classroom-2b/director.md").is_file()  # the campaign runs under the generic skill
    out = env.ok("resume")
    assert f"Director skill version (repo): {bootstrap_version()}" in out
    assert "Skill version (repo)" not in out.replace("Director skill version (repo)", "")
    assert re.search(r"^Generic rules: \S+ \(template \S+\)$", out, re.M)  # still printed: its tests (test_templates, test_joestar) rely on it
    assert "fast-turn.md" not in out and "player-agency.md" not in out and "wins over" not in out and "win over" not in out


def test_resume_prints_canon_traps_main_npcs_and_act_days(env):
    cfg = json.loads((REPO / "campaigns/classroom-2b/campaign.json").read_text(encoding="utf-8"))
    out = env.ok("resume")
    assert f"Canon traps ({len(cfg['canon_traps'])}" in out and cfg["canon_traps"][0]["text"][:40] in out
    assert "Main NPCs: " in out and cfg["main_npcs"][0] in " ".join(out.split())
    assert re.search(r"Acts: 1 Move-In d1-7; 2 Finding Footing d8-42", " ".join(out.split()))


def test_resume_shows_open_questions_and_not_closed_ones(env):
    assert "Open questions: none" in env.ok("resume")
    env.ok("question", "Who owns the blue umbrella?", "--turn", "1", "--evidence", "seen in the hall")
    env.ok("question", "Where did Mio go at night?", "--turn", "1", "--evidence", "door heard")
    out = env.ok("resume")
    assert "Open questions (2):" in out and "q1 (turn 1): Who owns the blue umbrella?" in out and "q2 (turn 1): Where did Mio go" in out
    env.ok("question-close", "q1", "--turn", "1", "--evidence", "it was Aiko's")
    out = env.ok("resume")
    assert "Open questions (1):" in out and "blue umbrella" not in out and "q2 (turn 1)" in out


def test_resume_says_never_synced_without_a_sync_log(env):
    assert "sync_log" not in env.load("state")
    out = env.ok("resume")
    assert "Last sync: never" in out


def test_resume_shows_the_latest_sync_entry(env):
    env.record(1)
    env.record(2)
    st = env.load("state")
    st["sync_log"] = [
        {"turn": 1, "at": "2026-10-04T10:00:00Z", "tick": 5, "mismatches": {"position": 0, "time": 0, "quest": 0, "party": 0, "drift": 0}, "applied": False},
        {"turn": 2, "at": "2026-10-05T09:30:00Z", "tick": 9, "mismatches": {"position": 2, "time": 1, "quest": 0, "party": 3, "drift": 4}, "applied": True}]
    env.save_json("state", st)
    out = env.ok("resume")
    line = next(ln for ln in out.splitlines() if ln.startswith("Last sync:"))
    assert "turn 2" in line and "2026-10-05T09:30:00Z" in line and "tick 9" in line
    assert "position 2, time 1, quest 0, party 3, drift 4" in line and "applied" in line and "0 turn(s) ago" in line


def test_resume_survives_a_malformed_sync_log(env):
    for bad in ("nonsense", [], ["x", 3], [{"turn": "?", "mismatches": "none"}]):
        st = env.load("state")
        st["sync_log"] = bad
        env.save_json("state", st)
        assert "Last sync:" in env.ok("resume")


def test_resume_counts_review_findings_in_the_repeat_slips(env):
    env.record(1, slips="outcome: the prompt said Aiko was nervous")
    env.record(2)
    env.record(3)
    out = env.ok("resume")
    assert "Repeat slips: outcome x1" in out and "from director reviews" not in out
    env.ok("review-add", "--turn", 2, "--slips", "outcome: 'Aiko smiled' states a feeling; invention: a rooftop door nobody listed")
    env.ok("review-add", "--turn", 3, "--slips", "outcome: Cut: skipped the walk")
    out = env.ok("resume")
    assert "Repeat slips: outcome x3, invention x1 (3 of 4 from director reviews)" in out
    assert "latest outcome: T3: Cut: skipped the walk" in out


# ---- review-add (REVIEW-1, D8, LOG-5) -------------------------------------------------
def test_review_add_appends_apart_from_the_turns_own_slips(env):
    env.record(1, slips="fact: wrong room")
    r = env.ok("review-add", "--turn", 1, "--slips", "outcome: 'she felt proud' is a feeling; DROPPED: ignored the promise to Mio")
    assert "2 review finding(s)" in r
    t = env.load("turns")[0]
    assert t["slips"] == "fact: wrong room"  # the turn's own slips are untouched
    assert t["review_slips"] == [{"category": "outcome", "text": "'she felt proud' is a feeling", "source": "review"},
                                 {"category": "dropped", "text": "ignored the promise to Mio", "source": "review"}]
    env.ok("review-add", "--turn", 1, "--slips", "teleport: Cut: moved Aiko to the shop")  # a second review appends
    assert [x["category"] for x in env.load("turns")[0]["review_slips"]] == ["outcome", "dropped", "teleport"]
    assert "outcome: 'she felt proud'" in env.ok("history", "--last", 1)
    out = env.ok("review-add", "--turn", 1, "--slips", "teleport: Cut: moved Aiko to the shop")  # the same finding twice is not doubled
    assert "nothing written" in out and len(env.load("turns")[0]["review_slips"]) == 3


@pytest.mark.parametrize("slips", ["other: NPC-4 broken", "tone: too loud", "no tag at all", "fact:", "fact: fine; steering: bad", "  ;  "])
def test_review_add_refuses_a_bad_tag_and_writes_nothing(env, slips):
    env.record(1)
    before = (env.data / "turns.json").read_bytes(), (env.data / "state.json").read_bytes()
    r = env.review(1, slips)
    assert r.returncode == 2 and "error:" in r.stderr
    assert ((env.data / "turns.json").read_bytes(), (env.data / "state.json").read_bytes()) == before


def test_review_add_refuses_a_turn_that_is_not_logged(env):
    env.record(1)
    r = env.review(7, "fact: x")
    assert r.returncode == 2 and "turn 7 is not in the turn log" in r.stderr and "review_slips" not in env.load("turns")[0]


def test_review_add_writes_under_the_lock(env):
    env.record(1)
    before = (env.data / "turns.json").read_bytes()
    fd = os.open(env.data / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # another writer holds the lock
        r = env.review(1, "fact: x")
        assert r.returncode == 6 and "another write is in progress" in r.stderr
        assert (env.data / "turns.json").read_bytes() == before
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert env.review(1, "fact: x").returncode == 0  # free again
    assert not (env.data / ".lock").read_text().strip()  # and released cleanly


def test_review_add_leaves_the_data_valid_for_wrap_up(env):
    env.record(1)
    env.ok("review-add", "--turn", 1, "--slips", "invention: a new rule")
    assert "safe to close" in env.ok("wrap-up")


def test_undo_turn_rewinds_review_findings_of_the_undone_turn_and_keeps_the_others(env):
    for n in (1, 2, 3):
        env.record(n)
    env.ok("review-add", "--turn", 2, "--slips", "fact: on turn 2")
    env.ok("review-add", "--turn", 3, "--slips", "outcome: on turn 3")
    out = env.ok("undo-turn", 3)
    turns = env.load("turns")
    assert [t["turn"] for t in turns] == [1, 2] and env.load("state")["turn"] == 2
    assert "review_slips" not in turns[0] and turns[1]["review_slips"][0]["text"] == "on turn 2"  # the older review survives the rewind
    assert "kept the director-review findings on turn(s) 2" in out
    resume = env.ok("resume")
    assert "Repeat slips: fact x1 (1 of 1 from director reviews)" in resume and "outcome" not in resume.split("Repeat slips:")[1].splitlines()[0]
    env.ok("undo-turn", 2)
    assert [t["turn"] for t in env.load("turns")] == [1] and "Repeat slips" not in env.ok("resume")


# ---- history --last (AGT-7) -----------------------------------------------------------
def test_history_last_prints_the_last_turns_in_full_oldest_first(env):
    env.record(1, slips="fact: slip one")
    env.record(2, inputs="Aiko opens the kitchen window and calls out to Mio.")
    env.record(3, slips="invention: a rooftop door", prompt="Cut: Continue at the kitchen.\nCrew: Mio Tachibana stirs the pot.\nWorld: Rain starts.")
    env.ok("review-add", "--turn", 3, "--slips", "outcome: 'Aiko felt sure'")
    out = env.ok("history", "--last", 2)
    assert "Turn 1 |" not in out and out.index("Turn 2 |") < out.index("Turn 3 |")
    assert "Last 2 logged turn(s), oldest first (turn 2 to 3):" in out
    t2, t3 = out.split("Turn 3 |")[0], out.split("Turn 3 |")[1]
    assert "Day 1 " in out and "inputs: Aiko opens the kitchen window and calls out to Mio." in t2
    assert "summary: summary 2" in t2 and "slips: -" in t2 and "notes: note 2" in t2
    assert "prompt: Cut: Continue at the kitchen. / Crew: Mio Tachibana stirs the pot. / World: Rain starts." in t3  # in full, lines joined
    assert "slips: invention: a rooftop door" in t3 and "review slips: outcome: 'Aiko felt sure'" in t3 and "notes: note 3" in t3
    assert "(turn 1 to 3)" in env.ok("history", "--last", 9)


def test_history_last_does_not_clip_a_long_prompt(env):
    long_prompt = "Cut: Continue at the kitchen.\nCrew: " + "Mio Tachibana stirs the pot slowly. " * 20 + "\nWorld: End marker."
    env.record(1, prompt=long_prompt[:800])
    out = env.ok("history", "--last", 1)
    assert "..." not in out and re.sub(r"\s*\n\s*", " / ", long_prompt[:800]) in out


def test_history_search_is_unchanged_and_last_excludes_words(env):
    env.record(1, inputs="Aiko bakes a lemon cake")
    env.record(2, inputs="Mio sulks")
    out = env.ok("history", "lemon")
    assert "T1 (" in out and "matched in: inputs" in out and "Turn 1 |" not in out
    assert env.run("history").returncode != 0  # neither words nor --last
    assert env.run("history", "lemon", "--last", 1).returncode == 2
    assert env.run("history", "--last", 0).returncode == 1


def test_history_last_with_no_turns(env):
    assert "no turns logged yet" in env.ok("history", "--last", 3)


# ---- preflight (CHAT-4, K14) ----------------------------------------------------------
def test_preflight_without_arc_functions_does_not_fail_for_them(env):
    r = env.run("preflight")
    assert r.returncode == 0, r.stdout
    flat = " ".join(r.stdout.split())
    assert "arc functions are off" in flat
    for gone in ("session zero not recorded", "no pitch", "pitch is draft", "no arc charter", "deferred op", "PLAN"):
        assert gone not in flat, gone
    assert "RESULT: 0 FAIL" in flat and "ready to play" in flat
    assert f"OK director skill version (repo) {bootstrap_version()}" in flat
    assert "OK skill version (repo)" in flat  # the per-campaign line stays
    assert "PC Aiko Tanaka: sheet lacks" in flat  # the other checks stay


def test_preflight_still_checks_the_pcs_and_git_without_arc_functions(env):
    st = env.load("state")
    st["player_characters"] = []
    env.save_json("state", st)
    r = env.run("preflight")
    assert r.returncode == 4 and "FAIL no PC sheets yet" in r.stdout and "arc functions are off" in r.stdout


def test_preflight_with_arc_functions_on_keeps_the_arc_checks(env):
    from test_arcs import CHARTER  # a full, valid charter
    env.ok("session-zero", "--tone", "warm")
    f = env.tmp / "c.json"
    f.write_text(json.dumps(CHARTER), encoding="utf-8")
    env.ok("arc-plan", "--file", f)
    r = env.run("preflight")
    assert r.returncode == 4 and "arc functions are off" not in r.stdout
    flat = " ".join(r.stdout.split())
    assert "OK session zero recorded" in flat and "FAIL act 1: no pitch" in flat and "arc A1 is a draft" in flat


# ---- wrap-up (SAVE-2, REVIEW-1) -------------------------------------------------------
def test_wrap_up_reminds_about_the_export_and_the_review_without_blocking(env):
    env.record(1)
    r = env.run("wrap-up")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = r.stdout.splitlines()
    sync = next(i for i, ln in enumerate(lines) if "no sync for turn 1" in ln)
    review = next(i for i, ln in enumerate(lines) if "director review" in ln and "review-add" in ln)
    closing = next(i for i, ln in enumerate(lines) if ln.startswith("safe to close:"))
    assert "Voyage's state export" in lines[sync] and "may skip" in lines[sync]
    assert sync < closing and review < closing  # both come before "safe to close"
    assert lines[closing] == "safe to close: yes (nothing in git to push)."


def test_wrap_up_skips_the_export_reminder_when_this_turn_was_synced(env):
    env.record(1)
    st = env.load("state")
    st["sync_log"] = [{"turn": 1, "at": "2026-10-05T09:00:00Z", "tick": 3,
                       "mismatches": {"position": 0, "time": 0, "quest": 0, "party": 0, "drift": 0}, "applied": False}]
    env.save_json("state", st)
    out = env.ok("wrap-up")
    assert "no sync for turn" not in out and "director review" in out and "safe to close" in out
    st["sync_log"][0]["turn"] = 0  # an older sync does not count for the current turn
    env.save_json("state", st)
    assert "no sync for turn 1" in env.ok("wrap-up")


def test_wrap_up_reminders_never_block_with_a_malformed_sync_log(env):
    st = env.load("state")
    st["sync_log"] = "junk"
    env.save_json("state", st)
    r = env.run("wrap-up")
    assert r.returncode == 0 and "no sync for turn" in r.stdout and "safe to close" in r.stdout
