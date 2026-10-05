"""Session roles, planner output and the turn clock (handoff 2; SES-1 to SES-9, docs/revamp/handoff-2-design.md).

Every test runs in a tmp git repository (VOYAGE_ROOT) that holds a copy of the classroom-2b campaign, with a bare repository as its
origin and its own session file (DB_SESSION_FILE). The real data, the real session file and the real remote are never touched.
Covers: the role stored in the session file (use, auto, menu, resume), the planner's write gate, `planner`, `planner-done` and
`planner-save`, the planner line in the brief, the commit-turn tail (fetch, NEXT BRIEF), the timing figures, and that nothing on the
clock touches the network."""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
CAMPAIGN = "classroom-2b"
REAL_CAMPAIGN = REPO / "campaigns" / CAMPAIGN
PLANNER = f"campaigns/{CAMPAIGN}/planner"
SAYS = "Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\nCrew: {crew}\nWorld: The House Manager posts the chore rota."
CREW_MIO = "Mio Tachibana counts coins twice, shoulders tight, mouth flat: \"I'm fine, really.\""
GATE = ("this session is the planner; only the director session writes campaign data. "
        f"Put the output under campaigns/{CAMPAIGN}/planner/ and run `db.py planner-save`.")
NOT_CHOSEN = "Session role: not chosen (director, planner or all-in-one: db.py use --role ROLE)"
CARD, PIVOT = "card-wharf.md", "pivot-yumi.md"
LINE_BOTH = f"planner: card ready ({CARD}); pivot draft ready ({PIVOT}). Apply at a break, then db.py planner-done FILE"


def planner_lines(out):
    """The brief's planner lines ("Arc planner: ..." in resume is another line)."""
    return [ln for ln in out.splitlines() if ln.startswith("planner: ")]


def git(cwd, *a, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    assert not check or r.returncode == 0, r.stderr
    return r.stdout.strip()


class Proj:
    """A tmp repository with one campaign, a bare origin, a session file and a way to run db.py in it."""

    def __init__(self, tmp):
        self.tmp = tmp
        self.remote, self.work, self.sess = tmp / "remote.git", tmp / "work", tmp / "session.json"
        self.data = self.work / "campaigns" / CAMPAIGN / "data"

    def env(self, extra=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
        e.update({"VOYAGE_ROOT": str(self.work), "DB_SESSION_FILE": str(self.sess), "PYTHONDONTWRITEBYTECODE": "1"})
        e.update(extra or {})
        return e

    def run(self, *args, env=None, stdin=None):
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=self.env(env), cwd=self.work,
                              input=stdin)

    def ok(self, *args, env=None):
        r = self.run(*args, env=env)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}

    def file(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def commit(self, crew=CREW_MIO, payload=None, *args, env=None):
        t = self.load("state")["turn"] + 1
        pl = {"turn": t, "ops": [], "turn_log": {"inputs": "i", "summary": f"summary {t}"}, **(payload or {})}
        return self.run("commit-turn", "--prompt", self.file("prompt.txt", SAYS.format(crew=crew)), "--payload",
                        self.file("payload.json", json.dumps(pl)), *args, env=env)

    def role(self, role):
        self.ok("use", CAMPAIGN, "--role", role)

    def session(self):
        return json.loads(self.sess.read_text(encoding="utf-8"))

    # the planner's files, written the way the planner session would: in the work tree, or from a second clone of the origin
    def planner_write(self, files):
        for name, text in files.items():
            f = self.work / PLANNER / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")

    def planner_push_from_clone(self, files, msg="planner output"):
        other = self.tmp / "planner-clone"
        if not other.exists():
            git(self.tmp, "clone", "-q", str(self.remote), str(other))
            git(other, "config", "user.email", "p@example.com")
            git(other, "config", "user.name", "P")
        git(other, "pull", "-q", "origin", "main")
        for name, text in files.items():
            f = other / PLANNER / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", msg)
        git(other, "push", "-q", "origin", "main")

    def planner_publish(self, files, role="all-in-one"):
        """Planner files in this clone, saved and pushed with `planner-save`."""
        self.role(role)
        self.planner_write(files)
        self.ok("planner-save", "-m", "planner files")


@pytest.fixture
def proj(tmp_path):
    p = Proj(tmp_path)
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(p.remote))
    p.work.mkdir()
    git(p.work, "init", "-q", "-b", "main")
    git(p.work, "config", "user.email", "t@example.com")
    git(p.work, "config", "user.name", "T")
    shutil.copytree(REAL_CAMPAIGN, p.work / "campaigns" / CAMPAIGN, ignore=shutil.ignore_patterns(".lock", ".snapshots", "snapshots*", ".turn-clock*"))
    (p.work / ".gitignore").write_text(".voyage-session.json*\ncampaigns/*/data/.turn-clock*\n", encoding="utf-8")
    git(p.work, "add", "-A")
    git(p.work, "commit", "-q", "-m", "init")
    git(p.work, "remote", "add", "origin", str(p.remote))
    git(p.work, "push", "-q", "-u", "origin", "main")
    p.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    git(p.work, "commit", "-q", "-am", "pc")
    git(p.work, "push", "-q")
    return p


# ---- the role in the session file (SES-5) ---------------------------------------------------------------------------
def test_use_name_with_a_role_stores_it_and_use_shows_it(proj):
    out = proj.ok("use", CAMPAIGN, "--role", "planner")
    assert "Session role: planner" in out and proj.session()["role"] == "planner" and proj.session()["campaign"] == CAMPAIGN
    shown = proj.ok("use")
    assert "session campaign: classroom-2b" in shown and "Session role: planner" in shown


def test_use_role_alone_changes_the_role_of_the_current_choice_and_keeps_the_campaign_time(proj):
    proj.role("planner")
    before = proj.session()
    out = proj.ok("use", "--role", "director")
    after = proj.session()
    assert "Session role: director" in out and after["role"] == "director"
    assert after["campaign"] == before["campaign"] and after["set_at"] == before["set_at"]


def test_use_role_alone_without_a_choice_is_an_error_and_writes_nothing(proj):
    r = proj.run("use", "--role", "director")
    assert r.returncode == 2 and "no session campaign set" in r.stderr and not proj.sess.exists()


def test_use_rejects_an_unknown_role_and_clear_with_role(proj):
    r = proj.run("use", CAMPAIGN, "--role", "boss")
    assert r.returncode == 2 and "boss" in r.stderr and not proj.sess.exists()
    proj.role("planner")
    r = proj.run("use", "--clear", "--role", "director")
    assert r.returncode == 2 and proj.session()["role"] == "planner"


def test_use_name_without_a_role_keeps_the_role_of_this_chat(proj):
    proj.role("planner")
    out = proj.ok("use", CAMPAIGN)
    assert proj.session()["role"] == "planner" and "Session role: planner" in out
    proj.ok("use", "--clear")
    proj.ok("use", CAMPAIGN)
    assert "role" not in proj.session()
    assert NOT_CHOSEN in proj.ok("use")


def test_role_auto_is_director_when_planner_output_waits_else_all_in_one(proj):
    out = proj.ok("use", CAMPAIGN, "--role", "auto")
    assert proj.session()["role"] == "all-in-one" and "Session role: all-in-one (auto: no planner output is waiting)" in out
    proj.planner_publish({CARD: "# Wharf card\nbody\n"})
    out = proj.ok("use", "--role", "auto")
    assert proj.session()["role"] == "director" and "Session role: director (auto: planner output is waiting)" in out
    proj.ok("planner-done", CARD)
    proj.ok("use", "--role", "auto")
    assert proj.session()["role"] == "all-in-one"  # applied: nothing waits any more
    assert "auto" not in proj.sess.read_text(encoding="utf-8")  # the resolved value is what is stored


def test_an_invalid_role_makes_the_session_file_unusable_with_a_clear_message(proj):
    proj.sess.write_text(json.dumps({"campaign": CAMPAIGN, "set_at": "2026-10-05T10:00:00Z", "role": "boss"}), encoding="utf-8")
    for cmd in (["state"], ["use"]):
        r = proj.run(*cmd)
        assert r.returncode == 2, (cmd, r.stdout, r.stderr)
        assert "'boss'" in r.stderr and "director, planner, all-in-one" in r.stderr and "use NAME" in r.stderr
    out = proj.ok("menu")
    assert "Session choice: unusable" in out and "boss" in out and "Session role:" not in out
    assert proj.run("--campaign", CAMPAIGN, "state").returncode == 0  # an explicit campaign still works: the role gate cannot read the file
    proj.ok("use", CAMPAIGN, "--role", "director")  # `use NAME` replaces the bad file
    assert proj.session()["role"] == "director"


def test_menu_and_resume_print_the_role_line(proj):
    assert NOT_CHOSEN in proj.ok("menu") and NOT_CHOSEN in proj.ok("resume")
    proj.role("director")
    for cmd in ("menu", "resume"):
        out = proj.ok(cmd)
        assert "Session role: director" in out.splitlines() and "not chosen" not in out
    proj.role("planner")
    assert "Session role: planner" in proj.ok("resume").splitlines()


def test_the_role_comes_only_from_the_session_file(proj):
    proj.role("planner")
    r = proj.run("--campaign", CAMPAIGN, "fact", "Ren", "owes a favor", "--turn", "1", "--evidence", "x")
    assert r.returncode == 4 and GATE in r.stderr
    r = proj.run("clock-add", "Rent", "--due-day", "3", "--turn", "1", "--evidence", "x", env={"VOYAGE_CAMPAIGN": CAMPAIGN})
    assert r.returncode == 4 and GATE in r.stderr


# ---- the planner's write gate (SES-4) -----------------------------------------------------------------------------
def gated_commands(proj):
    payload = proj.file("rec.json", json.dumps({"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}))
    prompt = proj.file("pr.txt", SAYS.format(crew=CREW_MIO))
    return [["clock-add", "Rent", "--due-day", "3", "--turn", "1", "--evidence", "x"], ["record", payload],
            ["commit-turn", "--prompt", prompt, "--payload", payload], ["save"], ["planner-done", CARD], ["undo-turn", "1"], ["recover"],
            ["wrap-up"], ["turn", "1", "--inputs", "i", "--summary", "s", "--prompt", "Cut: a\nWorld: b"], ["session-zero", "--tone", "x"],
            ["studio-done", "S1", "--turn", "1"]]


def test_the_planner_role_refuses_every_writing_command_with_exit_4_and_changes_nothing(proj):
    proj.role("planner")
    before, head = proj.hashes(), git(proj.work, "rev-parse", "HEAD")
    for cmd in gated_commands(proj):
        r = proj.run(*cmd)
        assert r.returncode == 4 and GATE in r.stderr and f"{cmd[0]} refused" in r.stderr, (cmd[0], r.returncode, r.stdout, r.stderr)
    assert proj.hashes() == before and git(proj.work, "rev-parse", "HEAD") == head and not ((proj.data / ".lock").exists() and (proj.data / ".lock").read_text())


def test_the_planner_role_still_allows_lookups_checks_dry_runs_and_planner_save(proj):
    proj.role("planner")
    prompt = proj.file("pr.txt", SAYS.format(crew=CREW_MIO))
    payload = proj.file("rec.json", json.dumps({"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}))
    allowed = [["npc", "Mio"], ["loc", "shared-kitchen"], ["canon", "rota"], ["state"], ["resume"], ["turn-brief"], ["turn-brief", "--full"],
               ["prep"], ["check-prompt", prompt], ["scan", prompt], ["planner"], ["planner", "--all"], ["record", payload, "--dry-run"],
               ["commit-turn", "--prompt", prompt, "--payload", payload, "--dry-run"], ["save", "--dry-run"],
               ["menu"], ["use"]]
    before = proj.hashes()
    for cmd in allowed:
        r = proj.run(*cmd)
        assert r.returncode == 0, (cmd, r.returncode, r.stdout, r.stderr)
    assert proj.hashes() == before
    proj.planner_write({CARD: "# card\n"})
    assert proj.run("planner-save", "--dry-run").returncode == 0
    assert "committed:" in proj.ok("planner-save", "-m", "a card") and f"{PLANNER}/{CARD}" in git(proj.work, "show", "--name-only", "--format=", "HEAD")


def test_other_roles_write_normally(proj):
    for role in ("director", "all-in-one"):
        proj.role(role)
        proj.ok("clock-add", f"Rent {role}", "--due-day", "3", "--turn", "1", "--evidence", "x")
    assert proj.commit().returncode == 0


# ---- planner output: planner, planner-done, the brief line ----------------------------------------------------------
def test_no_planner_folder_means_no_brief_line_and_a_quiet_planner_command(proj):
    assert not planner_lines(proj.ok("turn-brief")) and not planner_lines(proj.ok("resume")) and not planner_lines(proj.ok("turn-brief", "--full"))
    out = proj.ok("planner")
    assert "nothing waiting" in out and "planner-save" in out


def test_readme_and_other_non_planner_files_are_ignored_or_notes(proj):
    proj.planner_publish({"README.md": "# What this folder is\n"})
    assert not planner_lines(proj.ok("turn-brief")) and "nothing waiting" in proj.ok("planner")
    proj.planner_publish({"scratch.txt": "loose thoughts\n", "note-a.md": "# Note\n"})
    assert "planner: note (note-a.md, scratch.txt). Apply at a break, then db.py planner-done FILE" in proj.ok("turn-brief")


def test_the_brief_line_appears_for_new_files_and_names_each_kind(proj):
    proj.planner_publish({CARD: "# Wharf card\n", PIVOT: "# Pivot for Yumi\n"})
    for cmd in (["turn-brief"], ["turn-brief", "--full"]):
        out = proj.ok(*cmd)
        assert LINE_BOTH in out.splitlines(), (cmd, out)
    assert f"NEXT BRIEF (turn 1):" in proj.ok("resume") and LINE_BOTH in proj.ok("resume").splitlines()
    proj.planner_publish({"offramps-a.md": "x\n", "arc-b.md": "x\n", "review-c.md": "x\n", "audit-d.md": "x\n", "retro-e.md": "x\n",
                          "recap-f.md": "x\n", "studio-g.md": "x\n"})
    line = next(ln for ln in proj.ok("turn-brief").splitlines() if ln.startswith("planner:"))
    for want in (f"card ready ({CARD})", f"pivot draft ready ({PIVOT})", "off-ramps ready (offramps-a.md)", "arc plan ready (arc-b.md)",
                 "review ready (review-c.md)", "audit ready (audit-d.md)", "retro draft ready (retro-e.md)", "recap ready (recap-f.md)",
                 "Studio draft ready (studio-g.md)"):
        assert want in line, (want, line)


def test_the_brief_line_goes_after_planner_done_and_returns_when_the_file_changes(proj):
    proj.planner_publish({CARD: "# Wharf card\nv1\n", PIVOT: "# Pivot\n"})
    out = proj.ok("planner-done", CARD, "--note", "scene card stored")
    assert "planner output applied: card-wharf.md" in out
    line = next(ln for ln in proj.ok("turn-brief").splitlines() if ln.startswith("planner:"))
    assert CARD not in line and f"pivot draft ready ({PIVOT})" in line
    rec = proj.load("state")["planner_applied"]
    blob = git(proj.work, "rev-parse", f"origin/main:{PLANNER}/{CARD}")
    assert len(rec) == 1 and rec[0]["file"] == CARD and rec[0]["blob"] == blob and rec[0]["note"] == "scene card stored"
    assert rec[0]["turn"] == proj.load("state")["turn"] and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", rec[0]["at"])
    assert "already applied" in proj.ok("planner-done", CARD) and len(proj.load("state")["planner_applied"]) == 1
    proj.ok("planner-done", PIVOT)
    assert not planner_lines(proj.ok("turn-brief")) and "nothing waiting" in proj.ok("planner")
    # the planner edits the card: a new blob, so it waits again
    proj.planner_write({CARD: "# Wharf card\nv2\n"})
    proj.ok("planner-save")
    assert f"planner: card ready ({CARD}). Apply at a break, then db.py planner-done FILE" in proj.ok("turn-brief").splitlines()
    proj.ok("planner-done", f"{PLANNER}/{CARD}")  # the path as git prints it works too
    assert not planner_lines(proj.ok("turn-brief")) and len(proj.load("state")["planner_applied"]) == 3


def test_planner_lists_waiting_files_with_their_first_line_and_shows_one(proj):
    proj.planner_publish({CARD: "# Wharf card\nthe body\n", PIVOT: "\n\n## Pivot for Yumi\n"})
    proj.ok("planner-done", PIVOT)
    out = proj.ok("planner")
    assert "1 waiting" in out and f"card ready: {CARD}: Wharf card" in out and PIVOT not in out
    allout = proj.ok("planner", "--all")
    assert f"applied (turn 0): {PIVOT}: Pivot for Yumi" in allout and CARD in allout
    assert proj.ok("planner", "--show", CARD).endswith("# Wharf card\nthe body\n")
    r = proj.run("planner", "--show", "nope.md")
    assert r.returncode == 2 and CARD in r.stderr
    r = proj.run("planner-done", "nope.md")
    assert r.returncode == 2 and "nope.md" in r.stderr and len(proj.load("state")["planner_applied"]) == 1


def test_planner_output_is_read_from_origin_main_else_head(proj):
    proj.planner_publish({CARD: "# Wharf card\n"})
    proj.planner_write({PIVOT: "# local only\n"})  # in the work tree, not committed: never seen
    git(proj.work, "add", "-A")
    git(proj.work, "commit", "-q", "-m", "local pivot")  # committed, not pushed: origin/main does not have it
    assert "pivot draft ready" not in proj.ok("turn-brief")
    git(proj.work, "update-ref", "-d", "refs/remotes/origin/main")  # no origin/main ref: HEAD is the view
    assert LINE_BOTH in proj.ok("turn-brief").splitlines()


def test_a_planner_output_without_git_is_silent(proj, tmp_path):
    bare = tmp_path / "nogit"
    shutil.copytree(proj.work / "campaigns", bare / "campaigns")  # a tree with no repository around it
    e = proj.env({"VOYAGE_ROOT": str(bare)})
    r = subprocess.run([sys.executable, str(DB), "--campaign", CAMPAIGN, "turn-brief"], capture_output=True, text=True, env=e, cwd=bare)
    assert r.returncode == 0 and not planner_lines(r.stdout)
    r = subprocess.run([sys.executable, str(DB), "--campaign", CAMPAIGN, "planner"], capture_output=True, text=True, env=e, cwd=bare)
    assert r.returncode == 0 and "not available" in r.stdout


def test_the_state_accepts_planner_applied_and_older_state_without_it(proj):
    proj.planner_publish({CARD: "# c\n"})
    assert "planner_applied" not in proj.load("state") and "dry run" in proj.ok("save", "--dry-run")  # an older state file is fine
    proj.ok("planner-done", CARD)
    assert "dry run" in proj.ok("save", "--dry-run")
    st = proj.load("state")
    st["planner_applied"] = [{"file": "x.md", "blob": "", "turn": "one", "at": 5}]
    proj.save_json("state", st)
    r = proj.run("save", "--dry-run")
    assert r.returncode != 0 and "planner_applied #1" in r.stderr
    st["planner_applied"] = "x"
    proj.save_json("state", st)
    assert "planner_applied must be a list" in proj.run("save", "--dry-run").stderr


# ---- planner-save ------------------------------------------------------------------------------------------------
def test_planner_save_commits_only_the_planner_folder_and_pushes(proj):
    proj.role("planner")
    proj.planner_write({CARD: "# card\n", "sub/ignored.md": "x\n"})
    (proj.work / "campaigns" / CAMPAIGN / "README.md").write_text("stray edit\n", encoding="utf-8")
    out = proj.ok("planner-save", "-m", "Wharf card")
    assert "committed: Wharf card" in out and "pushed main" in out
    assert sorted(git(proj.work, "show", "--name-only", "--format=", "HEAD").split()) == [f"{PLANNER}/{CARD}", f"{PLANNER}/sub/ignored.md"]
    assert git(proj.work, "log", "-1", "--format=%s") == "Wharf card" and git(proj.remote, "log", "-1", "--format=%s", "main") == "Wharf card"
    assert "README.md" in git(proj.work, "status", "--porcelain")  # the stray edit was left alone
    assert "nothing new to commit" in proj.ok("planner-save")  # a second run has nothing to add
    assert git(proj.work, "log", "-1", "--format=%s") == "Wharf card"


def test_planner_save_default_message_and_dry_run(proj):
    proj.role("all-in-one")
    proj.planner_write({CARD: "# card\n"})
    assert "dry run: would commit" in proj.ok("planner-save", "--dry-run") and "?? " + PLANNER in git(proj.work, "status", "--porcelain")
    proj.ok("planner-save")
    assert git(proj.work, "log", "-1", "--format=%s") == "Class 2B planner output"


def test_planner_save_is_refused_for_the_director_a_trial_run_a_data_copy_and_off_main(proj):
    proj.planner_write({CARD: "# card\n"})
    proj.role("director")
    r = proj.run("planner-save")
    assert r.returncode == 4 and "this session is the director" in r.stderr and len(r.stderr.strip().splitlines()) == 1
    proj.role("planner")
    r = proj.run("planner-save", env={"VOYAGE_TRIAL": "1"})
    assert r.returncode == 4 and "trial run" in r.stderr
    copy = proj.tmp / "copy"
    shutil.copytree(proj.data, copy)
    r = proj.run("planner-save", env={"VOYAGE_DATA": str(copy)})
    assert r.returncode == 4 and "points at a copy" in r.stderr
    git(proj.work, "checkout", "-q", "-b", "side")
    assert proj.run("planner-save").returncode == 8
    assert PLANNER not in git(proj.remote, "ls-tree", "-r", "--name-only", "main")


def test_planner_save_without_a_planner_folder_says_so(proj):
    proj.role("planner")
    r = proj.run("planner-save")
    assert r.returncode == 2 and "does not exist yet" in r.stderr


def test_planner_save_rebases_when_the_push_is_rejected(proj):
    proj.planner_push_from_clone({"note-other.md": "# from the other clone\n"})
    proj.role("planner")
    proj.planner_write({CARD: "# card\n"})
    out = proj.ok("planner-save", "--retries", "3")
    assert "pushed main" in out
    tree = git(proj.remote, "ls-tree", "-r", "--name-only", "main")
    assert f"{PLANNER}/{CARD}" in tree and f"{PLANNER}/note-other.md" in tree


# ---- the commit-turn tail (SES-2, LOOP-2) ----------------------------------------------------------------------------
def test_commit_turn_ends_with_the_next_brief_after_push_and_studio(proj):
    f = proj.file("fix.txt", "Fix text.")
    r = proj.commit(payload={"ops": [{"op": "studio-request", "args": {"kind": "story-fix", "target": "T1", "text_file": str(f)}, "evidence": "x"}]})
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "NEXT BRIEF (turn 2):" in out and "pushed main" in out and "STUDIO request" in out
    assert out.index("pushed main") < out.index("STUDIO request") < out.index("NEXT BRIEF (turn 2):")
    tail = out.split("NEXT BRIEF (turn 2):\n", 1)[1]
    assert tail.splitlines()[0].startswith("Turn 1 (next 2)") and "Rules: Voyage owns every mechanic" in tail and "WARN" not in tail
    assert "planner fetch" not in out  # the push worked, so no fetch (and no warning)


def test_commit_turn_fetches_and_the_next_brief_carries_the_planner_line(proj):
    proj.role("director")
    proj.planner_push_from_clone({CARD: "# Wharf card\n", PIVOT: "# Pivot\n"})
    assert not planner_lines(proj.ok("turn-brief"))  # not fetched yet: this clone has not seen it
    r = proj.commit(CREW_MIO, None, "--push-every", 5)  # no push this turn: the fetch brings the planner's push in
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARN" not in r.stdout and "unpushed 1/5" in r.stdout
    tail = r.stdout.split("NEXT BRIEF (turn 2):\n", 1)[1]
    assert LINE_BOTH in tail.splitlines()
    assert LINE_BOTH in proj.ok("turn-brief").splitlines()
    assert git(proj.work, "rev-parse", "origin/main") == git(proj.remote, "rev-parse", "main")


def test_commit_turn_dry_run_prints_none_of_the_tail(proj):
    proj.planner_push_from_clone({CARD: "# c\n"})
    r = proj.commit(CREW_MIO, None, "--dry-run")
    assert r.returncode == 0 and "dry run OK" in r.stdout and "NEXT BRIEF" not in r.stdout and "planner" not in r.stdout
    assert git(proj.work, "rev-parse", "origin/main") != git(proj.remote, "rev-parse", "main")  # nothing was fetched
    assert proj.load("state")["turn"] == 0


def test_a_failed_fetch_only_warns_once_and_commit_turn_succeeds(proj):
    git(proj.work, "remote", "set-url", "origin", str(proj.tmp / "no-such-remote.git"))
    r = proj.commit(CREW_MIO, None, "--push-every", 5)
    assert r.returncode == 0, r.stdout + r.stderr
    warns = [ln for ln in r.stdout.splitlines() if "WARN" in ln]
    assert len(warns) == 1 and warns[0].startswith("WARN planner fetch failed (") and warns[0].endswith("); play on, the next turn retries")
    assert "NEXT BRIEF (turn 2):" in r.stdout and proj.load("state")["turn"] == 1
    assert r.stdout.rstrip().splitlines()[-1].startswith("       `Cut:`")  # the brief is still the last thing printed
    r = proj.commit(CREW_MIO, None, "--push-every", 5)  # and it retries the next turn
    assert r.returncode == 0 and r.stdout.count("WARN planner fetch failed") == 1 and proj.load("state")["turn"] == 2


def test_a_failed_push_and_a_failed_fetch_each_warn_but_the_turn_is_kept(proj):
    git(proj.work, "remote", "set-url", "origin", str(proj.tmp / "no-such-remote.git"))
    r = proj.commit(CREW_MIO, None, "--retries", 1)
    assert r.returncode == 0 and "WARN push failed" in r.stdout and "WARN planner fetch failed" in r.stdout and "NEXT BRIEF (turn 2):" in r.stdout
    assert git(proj.work, "log", "-1", "--format=%s") == "Class 2B save: turn 1"


def test_no_fetch_and_no_warning_on_a_data_copy_or_outside_git(proj, tmp_path):
    for where in (tmp_path / "copy-out-of-git", proj.work / "datacopy"):  # outside any repository, and a VOYAGE_DATA copy inside the checkout
        shutil.copytree(proj.data, where, ignore=shutil.ignore_patterns(".lock"))
        git(proj.work, "remote", "set-url", "origin", str(proj.tmp / "no-such-remote.git"))  # a fetch here would fail loudly
        r = proj.commit(CREW_MIO, None, env={"VOYAGE_DATA": str(where), "VOYAGE_CAMPAIGN": CAMPAIGN})
        assert r.returncode == 0, r.stdout + r.stderr
        assert "planner fetch" not in r.stdout and "git: skipped" in r.stdout and "NEXT BRIEF (turn 2):" in r.stdout


# ---- timing (SES-9) --------------------------------------------------------------------------------------------------
def clock(proj):
    p = proj.data / ".turn-clock"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def test_check_prompt_records_its_first_run_for_the_coming_turn(proj):
    prompt = proj.file("pr.txt", SAYS.format(crew=CREW_MIO))
    assert clock(proj) is None
    assert proj.run("check-prompt", prompt).returncode == 0
    first = clock(proj)
    assert list(first) == ["1"] and set(first["1"]) == {"checked"} and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", first["1"]["checked"])
    first["1"]["checked"] = "2026-01-01T00:00:00+00:00"  # prove a later run keeps the first time
    (proj.data / ".turn-clock").write_text(json.dumps(first), encoding="utf-8")
    assert proj.run("check-prompt", prompt).returncode == 0
    assert clock(proj)["1"]["checked"] == "2026-01-01T00:00:00+00:00"
    assert ".turn-clock" not in [p.name for p in proj.data.glob("*.json")] and not list(proj.data.glob("*.json.tmp"))
    assert "dry run" in proj.ok("save", "--dry-run") and ".turn-clock" not in git(proj.work, "status", "--porcelain", "--untracked-files=all")


def test_turn_brief_full_adds_full_at_and_plain_turn_brief_writes_nothing(proj):
    proj.ok("turn-brief")
    assert clock(proj) is None
    proj.ok("turn-brief", "--full")
    first = clock(proj)["1"]
    assert list(first) == ["full_at"]
    assert proj.run("check-prompt", proj.file("pr.txt", SAYS.format(crew=CREW_MIO))).returncode == 0
    both = clock(proj)["1"]
    assert set(both) == {"checked", "full_at"} and both["full_at"] == first["full_at"]


def test_a_trial_run_writes_no_clock(proj):
    e = {"VOYAGE_TRIAL": "1"}
    assert proj.run("check-prompt", proj.file("pr.txt", SAYS.format(crew=CREW_MIO)), env=e).returncode == 0
    assert proj.run("turn-brief", "--full", env=e).returncode == 0
    assert clock(proj) is None


def test_commit_turn_records_the_timing_and_clears_the_clock(proj):
    assert proj.run("check-prompt", proj.file("pr.txt", SAYS.format(crew=CREW_MIO))).returncode == 0
    checked = clock(proj)["1"]["checked"]
    r = proj.commit(CREW_MIO, None, "--received", "08:30")
    assert r.returncode == 0, r.stdout + r.stderr
    tm = proj.load("turns")[-1]["timing"]
    assert set(tm) == {"received", "checked", "committed", "escalated"} and tm["checked"] == checked and tm["escalated"] is False
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT08:30:00[+-]\d\d:\d\d", tm["received"]) and re.fullmatch(r"\d{4}-\d\d-\d\dT.*", tm["committed"])
    assert clock(proj) is None  # the entry is cleared after the commit


def test_commit_turn_without_a_check_or_a_received_time_stores_nulls(proj):
    assert proj.commit().returncode == 0
    tm = proj.load("turns")[-1]["timing"]
    assert tm["received"] is None and tm["checked"] is None and tm["escalated"] is False and tm["committed"]


@pytest.mark.parametrize("given,seconds", [("2026-10-05T14:03:00+09:00", None), ("2026-10-05T14:03:00", None), ("9:05:07", "09:05:07"), ("23:59", "23:59:00")])
def test_received_accepts_iso_and_clock_times(proj, given, seconds):
    assert proj.commit(CREW_MIO, None, "--received", given).returncode == 0
    got = proj.load("turns")[-1]["timing"]["received"]
    assert got and (seconds is None or f"T{seconds}" in got) and (seconds is not None or got.startswith("2026-10-0"))


def test_a_bad_received_time_is_refused_before_anything_is_written(proj):
    before = proj.hashes()
    r = proj.commit(CREW_MIO, None, "--received", "lunchtime")
    assert r.returncode == 2 and "--received" in r.stderr and proj.hashes() == before


def test_escalated_comes_from_the_payload_or_from_turn_brief_full(proj):
    assert proj.commit(CREW_MIO, {"turn_log": {"inputs": "i", "summary": "s", "escalated": True}}).returncode == 0
    assert proj.load("turns")[-1]["timing"]["escalated"] is True
    proj.ok("turn-brief", "--full")
    assert proj.commit().returncode == 0
    assert proj.load("turns")[-1]["timing"]["escalated"] is True and clock(proj) is None
    assert proj.commit().returncode == 0
    assert proj.load("turns")[-1]["timing"]["escalated"] is False  # the next turn starts clean
    r = proj.commit(CREW_MIO, {"turn_log": {"inputs": "i", "summary": "s", "escalated": "yes"}})
    assert r.returncode != 0 and "escalated must be true or false" in r.stdout


def test_a_payload_cannot_carry_its_own_timing(proj):
    r = proj.commit(CREW_MIO, {"turn_log": {"inputs": "i", "summary": "s", "timing": {"committed": "x"}}})
    assert r.returncode != 0 and "unknown key 'timing'" in r.stdout


def test_dry_run_leaves_the_clock_alone(proj):
    assert proj.run("check-prompt", proj.file("pr.txt", SAYS.format(crew=CREW_MIO))).returncode == 0
    before = clock(proj)
    assert proj.commit(CREW_MIO, None, "--dry-run", "--received", "08:30").returncode == 0
    assert clock(proj) == before


def test_the_turn_log_with_timing_passes_the_data_check(proj):
    assert proj.commit(CREW_MIO, None, "--received", "08:30").returncode == 0
    assert "dry run" in proj.ok("save", "--dry-run")
    turns = proj.load("turns")
    turns[-1]["timing"]["escalated"] = "maybe"
    proj.save_json("turns", turns)
    r = proj.run("save", "--dry-run")
    assert r.returncode != 0 and "timing: escalated must be true or false" in r.stderr


def test_resume_shows_the_speed_of_the_last_turns_routine_and_escalated_apart(proj):
    assert "Speed (last 20)" not in proj.ok("resume")  # no turn has timing yet
    for _ in range(5):
        assert proj.commit().returncode == 0
    turns = proj.load("turns")
    # (received to checked, checked to committed) in seconds; None: not known
    spec = [(30, 60, False), (50, 100, False), (70, 140, False), (None, 20, False), (None, 300, True)]
    base = "2026-10-05T10:00:00+00:00"
    t0 = dt.datetime.fromisoformat(base)
    for t, (rc, cc, esc) in zip(turns, spec):
        checked = t0 + dt.timedelta(seconds=rc or 0)
        t["timing"] = {"received": t0.isoformat() if rc else None, "checked": checked.isoformat(),
                       "committed": (checked + dt.timedelta(seconds=cc)).isoformat(), "escalated": esc}
    proj.save_json("turns", turns)
    out = proj.ok("resume")
    assert ("Speed (last 20): routine 4 turns, input to check median 50s (3 with --received), check to commit median 80s; "
            "escalated 1 turn, check to commit median 5m00s") in out.splitlines()
    for t in turns:  # only the turns that have timing count, and a group with no data is left out
        t["timing"]["escalated"] = False
    proj.save_json("turns", turns)
    assert next(ln for ln in proj.ok("resume").splitlines() if ln.startswith("Speed")).startswith("Speed (last 20): routine 5 turns,")
    assert "escalated" not in next(ln for ln in proj.ok("resume").splitlines() if ln.startswith("Speed"))


def test_resume_counts_only_the_last_20_turns_that_have_timing(proj):
    assert proj.commit().returncode == 0
    turns = proj.load("turns")
    entry = turns[0]
    base = "2026-10-05T10:00:00+00:00"
    turns = []
    for n in range(1, 26):
        turns.append({**entry, "turn": n, "timing": {"received": None, "checked": base, "committed": "2026-10-05T10:01:00+00:00" if n > 5 else "2026-10-05T11:00:00+00:00",
                                                     "escalated": False}})
    proj.save_json("turns", turns)
    line = next(ln for ln in proj.ok("resume").splitlines() if ln.startswith("Speed"))
    assert line == "Speed (last 20): routine 20 turns, check to commit median 60s"  # the 5 slow early turns fall outside the window


# ---- nothing on the clock touches the network (SES-2, LOOP-2) ------------------------------------------------------
GUARD = textwrap.dedent('''
    import os, runpy, socket, subprocess, sys
    LOG = os.environ["NET_LOG"]
    BAD = {"fetch", "push", "pull", "ls-remote", "clone"}

    class NetworkCall(BaseException):
        pass

    def note(what):
        with open(LOG, "a") as f:
            f.write(what + "\\n")

    def check(args):
        a = [str(x) for x in (args if isinstance(args, (list, tuple)) else str(args).split())]
        if a and os.path.basename(a[0]) == "git" and BAD & set(a[1:]):
            note("git " + " ".join(a[1:]))
            raise NetworkCall(" ".join(a))

    real_run, RealPopen = subprocess.run, subprocess.Popen

    def run(args, *k, **kw):
        check(args)
        return real_run(args, *k, **kw)

    class Popen(RealPopen):
        def __init__(self, args, *k, **kw):
            check(args)
            super().__init__(args, *k, **kw)

    def connect(self, *a, **k):
        note("socket connect")
        raise NetworkCall("socket connect")

    subprocess.run, subprocess.Popen = run, Popen
    socket.socket.connect = connect
    socket.socket.connect_ex = connect
    if sys.argv[1:2] == ["--selftest"]:
        try:
            subprocess.run(["git", "fetch", "origin", "main"])
        except NetworkCall:
            sys.exit(42)
        sys.exit(1)
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    runpy.run_path(os.environ["DB_PY"], run_name="__main__")
''')


def guarded(proj, *args):
    guard = proj.tmp / "guard.py"
    guard.write_text(GUARD, encoding="utf-8")
    log = proj.tmp / "net.log"
    e = proj.env({"NET_LOG": str(log), "DB_PY": str(DB)})
    r = subprocess.run([sys.executable, str(guard), *map(str, args)], capture_output=True, text=True, env=e, cwd=proj.work)
    return r, (log.read_text(encoding="utf-8") if log.exists() else "")


def test_the_network_guard_itself_catches_a_fetch(proj):
    r, log = guarded(proj, "--selftest")
    assert r.returncode == 42 and "git fetch origin main" in log


def test_nothing_on_the_clock_touches_the_network(proj):
    proj.planner_publish({CARD: "# c\n"})
    prompt = proj.file("pr.txt", SAYS.format(crew=CREW_MIO))
    paste = proj.file("paste.txt", "Mio Tachibana counts the chore coins at the shared kitchen table.")
    for cmd in (["check-prompt", prompt, "--paste", paste], ["turn-brief", "--paste", paste], ["turn-brief"], ["turn-brief", "--full", "--paste", paste],
                ["npc", "Mio"], ["loc", "shared-kitchen"], ["canon", "rota"], ["planner"], ["resume"]):
        r, log = guarded(proj, *cmd)
        assert r.returncode == 0 and log == "", (cmd, r.returncode, r.stdout, r.stderr, log)
        assert "NetworkCall" not in r.stderr
    assert LINE_BOTH.replace(f"; pivot draft ready ({PIVOT})", "") in guarded(proj, "turn-brief")[0].stdout
