"""Campaign choice (SEL-1, SEL-2, MENU-1, HO 4.2): the session file written by `use`, the precedence of the ways to choose a campaign,
the campaign line that starts every campaign command's output, and `menu`. Every test runs on a tmp tree (VOYAGE_ROOT) of small
scaffolded campaigns and its own session file (DB_SESSION_FILE); the real campaigns and the repo's session file are never touched,
except for read-only lookups on classroom-2b."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
DB = TOOLS / "db.py"
NAMES = ("alpha", "beta", "gamma")
DISPLAY = {"alpha": "Alpha Tale", "beta": "Beta Tale", "gamma": "Gamma Tale"}
LINE = {n: f"== {d} ({n}) ==" for n, d in DISPLAY.items()}


def run(*args, root=None, session=None, env=None, stdin=None, path=None):
    """db.py in a child process: VOYAGE_ and CLASS2B_ variables dropped, the session file given (None: the suite's own from conftest.py,
    False: none, so the default place), VOYAGE_ROOT set when a tmp tree is used."""
    e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    if session is False:  # no override at all: db.py uses .voyage-session.json in its repo root
        e.pop("DB_SESSION_FILE", None)
    elif session is not None:
        e["DB_SESSION_FILE"] = str(session)
    if root is not None:
        e["VOYAGE_ROOT"] = str(root)
    if path is not None:
        e["PATH"] = str(path)
    e.update(env or {})
    return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, input=stdin,
                          cwd=root or REPO)


def first_line(r):
    return r.stdout.splitlines()[0] if r.stdout.splitlines() else ""


def campaign_json(root, name):
    return root / "campaigns" / name / "campaign.json"


def set_title(root, name, title):
    p = campaign_json(root, name)
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if title is None:
        cfg.pop("voyage_title", None)
    else:
        cfg["voyage_title"] = title
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


@pytest.fixture(scope="module")
def template_root(tmp_path_factory):
    """Three small scaffolded campaigns (no world import): alpha and beta have a voyage_title, gamma has none."""
    root = tmp_path_factory.mktemp("session-template") / "root"
    root.mkdir()
    for n in NAMES:
        r = subprocess.run([sys.executable, str(TOOLS / "new_campaign.py"), n, "--display", DISPLAY[n], "--root", str(root)],
                           capture_output=True, text=True, cwd=root,
                           env={**{k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))},
                                "VOYAGE_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"})
        assert r.returncode == 0, r.stdout + r.stderr
    set_title(root, "alpha", "Alpha Tale")
    set_title(root, "beta", "Beta Tale")
    return root


@pytest.fixture
def root(template_root, tmp_path):
    dst = tmp_path / "root"
    shutil.copytree(template_root, dst)
    return dst


@pytest.fixture
def sess(tmp_path):
    return tmp_path / "state" / "session.json"  # the parent folder does not exist yet: `use` must create it


def read_sess(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---- the session file: use NAME, use, use --clear ------------------------------------------------------------
def test_use_writes_the_session_file_and_shows_it(root, sess):
    r = run("use", "beta", root=root, session=sess)
    assert r.returncode == 0, r.stderr
    assert first_line(r) == LINE["beta"] and "beta" in r.stdout
    d = read_sess(sess)
    assert d["campaign"] == "beta" and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", d["set_at"])
    r = run("use", root=root, session=sess)
    assert r.returncode == 0 and first_line(r) == LINE["beta"] and "session campaign: beta" in r.stdout and d["set_at"] in r.stdout
    assert list(sess.parent.iterdir()) == [sess]  # no temp file is left behind


def test_use_replaces_an_earlier_choice(root, sess):
    assert run("use", "alpha", root=root, session=sess).returncode == 0
    assert run("use", "gamma", root=root, session=sess).returncode == 0
    assert read_sess(sess)["campaign"] == "gamma"


def test_use_rejects_an_unknown_campaign_and_keeps_the_old_choice(root, sess):
    assert run("use", "alpha", root=root, session=sess).returncode == 0
    r = run("use", "nope", root=root, session=sess)
    assert r.returncode == 2 and "not found" in r.stderr and "alpha, beta, gamma" in r.stderr and r.stdout == ""
    assert read_sess(sess)["campaign"] == "alpha"
    assert run("use", "nope", root=root, session=sess.with_name("other.json")).returncode != 0
    assert not sess.with_name("other.json").exists()


def test_use_without_a_choice_says_so(root, sess):
    r = run("use", root=root, session=sess)
    assert r.returncode == 0 and "no session campaign set" in r.stdout and not sess.exists()


def test_use_clear_removes_the_file(root, sess):
    assert run("use", "beta", root=root, session=sess).returncode == 0
    r = run("use", "--clear", root=root, session=sess)
    assert r.returncode == 0 and "cleared" in r.stdout and "beta" in r.stdout and not sess.exists()
    r = run("use", "--clear", root=root, session=sess)  # nothing to clear is not an error
    assert r.returncode == 0 and "no session campaign was set" in r.stdout
    assert "no session campaign set" in run("use", root=root, session=sess).stdout


def test_use_takes_one_of_name_title_clear(root, sess):
    for args in (["beta", "--clear"], ["beta", "--title", "Beta Tale"], ["--title", "Beta Tale", "--clear"]):
        r = run("use", *args, root=root, session=sess)
        assert r.returncode == 2 and "only one" in r.stderr and not sess.exists(), args


def test_session_file_lives_in_the_repo_root_by_default_and_is_git_ignored(root):
    r = run("use", "beta", root=root, session=False)  # the suite's override is dropped: the default place, the tree's root
    assert r.returncode == 0, r.stderr
    f = root / ".voyage-session.json"
    assert f.is_file() and read_sess(f)["campaign"] == "beta"
    assert first_line(run("state", root=root, session=False)) == LINE["beta"]
    assert not Path(os.environ["DB_SESSION_FILE"]).exists()  # and the suite's own file was not used
    assert any(ln.strip() == ".voyage-session.json*" for ln in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines())
    if shutil.which("git"):
        c = subprocess.run(["git", "check-ignore", "-q", ".voyage-session.json"], cwd=REPO)
        assert c.returncode == 0  # git says the session file is ignored


# ---- precedence: --campaign, VOYAGE_CAMPAIGN, the session file, the only campaign ------------------------------
def test_session_file_is_the_default_campaign(root, sess):
    assert run("use", "beta", root=root, session=sess).returncode == 0
    r = run("state", root=root, session=sess)
    assert r.returncode == 0, r.stderr
    assert first_line(r) == LINE["beta"]


def test_precedence_flag_then_env_then_session(root, sess):
    assert run("use", "beta", root=root, session=sess).returncode == 0
    assert first_line(run("state", root=root, session=sess)) == LINE["beta"]
    assert first_line(run("state", root=root, session=sess, env={"VOYAGE_CAMPAIGN": "gamma"})) == LINE["gamma"]
    assert first_line(run("--campaign", "alpha", "state", root=root, session=sess)) == LINE["alpha"]
    assert first_line(run("state", "--campaign", "alpha", root=root, session=sess, env={"VOYAGE_CAMPAIGN": "gamma"})) == LINE["alpha"]
    assert read_sess(sess)["campaign"] == "beta"  # none of these changed the choice


def test_use_notes_an_env_choice_that_takes_precedence(root, sess):
    r = run("use", "beta", root=root, session=sess, env={"VOYAGE_CAMPAIGN": "gamma"})
    assert r.returncode == 0 and "VOYAGE_CAMPAIGN=gamma" in r.stdout and "precedence" in r.stdout
    assert "VOYAGE_CAMPAIGN" not in run("use", root=root, session=sess).stdout


def test_a_stale_session_file_is_not_replaced_by_the_only_campaign(root, sess):
    for n in ("beta", "gamma"):
        shutil.rmtree(root / "campaigns" / n)
    r = run("state", root=root, session=sess)  # one campaign, no session file: it is the default
    assert r.returncode == 0 and first_line(r) == LINE["alpha"]
    sess.parent.mkdir(parents=True)
    sess.write_text(json.dumps({"campaign": "beta", "set_at": "2026-10-01T00:00:00Z"}), encoding="utf-8")
    r = run("state", root=root, session=sess)  # the session file names a campaign that is gone: an error, not the only campaign
    assert r.returncode == 2 and "no longer exists" in r.stderr and "'beta'" in r.stderr and r.stdout == ""


def test_several_campaigns_and_no_choice_stay_a_hard_error_with_a_hint(root, sess):
    r = run("state", root=root, session=sess)
    assert r.returncode == 2 and r.stdout == ""
    assert "several campaigns exist (alpha, beta, gamma)" in r.stderr and "db.py use NAME" in r.stderr
    assert "--campaign NAME" in r.stderr and "VOYAGE_CAMPAIGN" in r.stderr


def test_stale_session_file_is_an_error_that_says_so(root, sess):
    sess.parent.mkdir(parents=True)
    sess.write_text(json.dumps({"campaign": "gone", "set_at": "2026-10-01T00:00:00Z"}), encoding="utf-8")
    r = run("state", root=root, session=sess)
    assert r.returncode == 2 and r.stdout == ""
    assert "session file" in r.stderr and "'gone'" in r.stderr and "no longer exists" in r.stderr and "use --clear" in r.stderr
    assert run("use", root=root, session=sess).returncode == 2  # showing the choice reports it too
    assert first_line(run("--campaign", "alpha", "state", root=root, session=sess)) == LINE["alpha"]  # an explicit choice still works
    assert first_line(run("state", root=root, session=sess, env={"VOYAGE_CAMPAIGN": "beta"})) == LINE["beta"]
    r = run("menu", root=root, session=sess)  # the menu works and names the problem
    assert r.returncode == 0 and "'gone' no longer exists" in r.stdout
    assert run("use", "beta", root=root, session=sess).returncode == 0  # and `use NAME` repairs it
    assert first_line(run("state", root=root, session=sess)) == LINE["beta"]


@pytest.mark.parametrize("content", ["not json", "[]", '{"campaign": 7}', '{"campaign": ""}', "{}"])
def test_unusable_session_file_is_an_error(root, sess, content):
    sess.parent.mkdir(parents=True)
    sess.write_text(content, encoding="utf-8")
    r = run("state", root=root, session=sess)
    assert r.returncode == 2 and "not valid" in r.stderr and "use --clear" in r.stderr
    assert run("menu", root=root, session=sess).returncode == 0
    assert run("use", "--clear", root=root, session=sess).returncode == 0 and not sess.exists()


# ---- use --title: the Voyage tab title against campaign.json voyage_title ----------------------------------------
@pytest.mark.parametrize("tab", ["Beta Tale", "beta tale", "  BETA   TALE ", "Beta Tale | Voyage", "voyage - beta tale - Chrome"])
def test_use_title_picks_the_campaign_case_insensitively(root, sess, tab):
    r = run("use", "--title", tab, root=root, session=sess)
    assert r.returncode == 0, r.stderr
    assert first_line(r) == LINE["beta"] and read_sess(sess)["campaign"] == "beta"


def test_use_title_prefers_the_exact_and_the_longer_title(root, sess):
    set_title(root, "gamma", "Alpha Tale Retest")
    assert run("use", "--title", "Alpha Tale", root=root, session=sess).returncode == 0
    assert read_sess(sess)["campaign"] == "alpha"  # exact
    assert run("use", "--title", "alpha tale RETEST - Voyage", root=root, session=sess).returncode == 0
    assert read_sess(sess)["campaign"] == "gamma"  # both titles are inside the tab text: the one that is not part of the other


def test_use_title_ambiguous_lists_the_candidates_and_writes_nothing(root, sess):
    set_title(root, "gamma", "beta tale")  # the same title as beta, other case
    assert run("use", "alpha", root=root, session=sess).returncode == 0
    r = run("use", "--title", "Beta Tale", root=root, session=sess)
    assert r.returncode != 0 and "several campaigns match" in r.stderr and "beta" in r.stderr and "gamma" in r.stderr
    assert read_sess(sess)["campaign"] == "alpha"


def test_use_title_without_a_match_lists_the_candidates_and_writes_nothing(root, sess):
    r = run("use", "--title", "Some Other Page", root=root, session=sess)
    assert r.returncode != 0 and "no campaign has a voyage_title matching" in r.stderr
    assert "alpha = 'Alpha Tale'" in r.stderr and "beta = 'Beta Tale'" in r.stderr and "gamma =" not in r.stderr
    assert not sess.exists()


def test_use_title_when_no_campaign_has_a_voyage_title(root, sess):
    for n in NAMES:
        set_title(root, n, None)
    r = run("use", "--title", "Beta Tale", root=root, session=sess)
    assert r.returncode != 0 and "no campaign sets voyage_title" in r.stderr and not sess.exists()


@pytest.mark.parametrize("bad", ["", "   ", "'"])
def test_use_title_needs_text(root, sess, bad):
    set_title(root, "gamma", "'")  # a title with no letters in it never matches
    r = run("use", "--title", bad, root=root, session=sess)
    assert r.returncode != 0 and not sess.exists()


def test_voyage_title_must_be_a_string_to_count(root, sess):
    p = campaign_json(root, "beta")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["voyage_title"] = 5
    p.write_text(json.dumps(cfg), encoding="utf-8")
    r = run("use", "--title", "Beta Tale", root=root, session=sess)
    assert r.returncode != 0 and "beta =" not in r.stderr and not sess.exists()


# ---- the campaign line starts every campaign command's output ------------------------------------------------
READ_CMDS = [["state"], ["resume"], ["recap"], ["prep"], ["bible"], ["canon", "x"], ["plan-brief"], ["arc", "--list"],
             ["session-zero"], ["spotlight"], ["history", "x"], ["promises"], ["loc", "nowhere"], ["npc", "nobody"]]


@pytest.mark.parametrize("cmd", READ_CMDS, ids=lambda c: c[0])
def test_every_campaign_command_starts_with_the_campaign_line(root, sess, cmd):
    r = run("--campaign", "beta", *cmd, root=root, session=sess)  # whatever the exit code, the line comes first on stdout
    assert first_line(r) == LINE["beta"], (r.stdout, r.stderr)
    assert LINE["beta"] not in r.stderr and r.stdout.count(LINE["beta"]) == 1


def test_write_and_check_commands_start_with_the_campaign_line(root, sess, tmp_path):
    prompt = tmp_path / "p.txt"
    prompt.write_text("Cut: Continue at the dock.\nWorld: The gulls wheel overhead.", encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"turn": 1, "ops": [], "turn_log": {"inputs": "i", "summary": "s", "prompt": "Cut: a\nWorld: b"}}), encoding="utf-8")
    for cmd in (["check-prompt", prompt], ["record", payload, "--dry-run"], ["turn", "1", "--inputs", "i", "--summary", "s", "--prompt", "Cut: a\nWorld: b"],
                ["check-prompt", "-"]):
        r = run("--campaign", "gamma", *cmd, root=root, session=sess, stdin="Cut: x\nWorld: y")
        assert first_line(r) == LINE["gamma"], (cmd, r.stdout, r.stderr)
    r = run("--campaign", "gamma", "state", root=root, session=sess)
    assert r.returncode == 0 and r.stdout.splitlines()[1].startswith("Turn 1 |")  # the write command did write: the line is no mere echo


def test_campaign_line_follows_the_chosen_campaign_and_names_the_display_name(root, sess):
    for n in NAMES:
        assert first_line(run("--campaign", n, "state", root=root, session=sess)) == f"== {DISPLAY[n]} ({n}) =="
    p = campaign_json(root, "alpha")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg.pop("display")
    p.write_text(json.dumps(cfg), encoding="utf-8")
    assert first_line(run("--campaign", "alpha", "state", root=root, session=sess)) == "== alpha =="  # no display name: the folder name


def test_real_campaign_line():
    r = run("--campaign", "classroom-2b", "state")
    assert r.returncode == 0 and first_line(r) == "== Class 2B (classroom-2b) =="


def test_help_works_with_several_campaigns_and_no_choice(root, sess):
    for args in (["-h"], ["use", "-h"], ["state", "-h"]):
        r = run(*args, root=root, session=sess)
        assert r.returncode == 0 and first_line(r).startswith("usage:"), (args, r.stderr)  # help is no campaign output: no campaign line
    assert " use " in run("-h", root=root, session=sess).stdout and " menu " in run("-h", root=root, session=sess).stdout


def test_menu_needs_no_campaign_so_it_starts_with_its_title(root, sess):
    r = run("menu", root=root, session=sess)
    assert r.returncode == 0 and first_line(r) == "Voyage director: main menu" and "== " not in r.stdout


# ---- menu ----------------------------------------------------------------------------------------------------
def menu_campaigns(out):
    """Folder names of the campaign list, in the order printed."""
    lines = out.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("Campaigns"))
    stop = next(i for i, ln in enumerate(lines) if ln.startswith("Session choice"))
    return [re.search(r"\((\S+)\)", ln).group(1) for ln in lines[start + 1:stop]]


def test_menu_works_with_several_campaigns_and_no_choice(root, sess):
    r = run("menu", root=root, session=sess)
    assert r.returncode == 0, r.stderr
    assert sorted(menu_campaigns(r.stdout)) == list(NAMES)
    assert all(f"{DISPLAY[n]} ({n})" in r.stdout for n in NAMES)
    assert "Session choice: none" in r.stdout and "db.py use NAME" in r.stdout and "<- session choice" not in r.stdout
    assert run("use", root=root, session=sess).returncode == 0  # and so does `use`


def test_menu_marks_the_session_choice(root, sess):
    assert run("use", "gamma", root=root, session=sess).returncode == 0
    r = run("menu", root=root, session=sess)
    marked = [ln for ln in r.stdout.splitlines() if "<- session choice" in ln]
    assert len(marked) == 1 and "(gamma)" in marked[0]
    assert "Session choice: gamma, set " in r.stdout


def menu_items(out):
    """(item, who) for each numbered line of the menu part."""
    rows = []
    for ln in out.split("Menu (who does it):\n", 1)[1].splitlines():
        m = re.match(r"^\s*(\d+)\.\s+(.*?)\s{2,}(.*\S)\s*$", ln)
        assert m, ln
        rows.append((int(m.group(1)), m.group(2), m.group(3)))
    assert [n for n, _, _ in rows] == list(range(1, len(rows) + 1))
    return [(item, who) for _, item, who in rows]


def orch1_rows():
    """The ORCH-1 table of director/core.md: role -> its menu-items cell, lower case."""
    text = (REPO / "director" / "core.md").read_text(encoding="utf-8")
    rows = {}
    for ln in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$", ln)
        if m and m.group(1) not in ("Who", "---"):
            rows[m.group(1).lower()] = re.sub(r"<!--.*?-->", "", m.group(2)).strip().lower()
    return rows


# (item as the menu prints it, the role that does it, the role's row in the ORCH-1 table, the words that row holds for the item)
MENU_EXPECT = [
    ("Play a turn (paste or browser)", "main chat", "main chat", "turn"),
    ("Resume digest and recap", "subagent", "subagent", "resume digest, recap"),
    ("Plan an act or arc", "opus subagent", "opus", "act or arc plan"),
    ("Pressure card for a showcase scene", "opus subagent", "opus", "pressure card"),
    ("Pivot mini-charter", "opus subagent", "opus", "pivot mini-charter"),
    ("Studio, cast and world work", "sonnet subagent", "sonnet", "studio, cast and world work"),
    ("Sync from the save file", "subagent", "subagent", "sync"),
    ("Director review, canon audit, act retro", "read-only subagent", "read-only subagent", "director review, canon audit, act retro"),
    ("Tool, test and doc changes", "sonnet subagent", "sonnet", "tool, test and doc changes"),
    ("New campaign", "sonnet subagent", "sonnet", "new campaign scaffold"),
    ("Wrap-up and repairs", "main chat", "main chat", "wrap-up"),
]


def test_menu_lists_the_main_menu_items_with_who_does_each(root, sess):
    items = menu_items(run("menu", root=root, session=sess).stdout)
    assert [item for item, _ in items] == [e[0] for e in MENU_EXPECT]
    for (item, who), (_, role, _, _) in zip(items, MENU_EXPECT):
        assert who.lower().startswith(role), (item, who)


def test_menu_items_follow_the_orch1_table_in_core_md(root, sess):
    rows = orch1_rows()
    assert {"main chat", "subagent", "opus", "sonnet", "read-only subagent"} <= set(rows)  # the table is still where we read it
    for item, role, row, words in MENU_EXPECT:
        assert words in rows[row], (item, row, rows[row])  # core.md lists the item under that role
    shown = run("menu", root=root, session=sess).stdout.lower()
    for row in ("main chat", "subagent", "opus", "sonnet", "read-only subagent"):
        for part in re.split(r"[;,]", re.sub(r"\(.*?\)", "", rows[row])):
            assert part.strip().split(" ")[0] in shown, (row, part)  # and no item of the table is missing from the menu


# ---- menu order: the newest git commit touching campaigns/NAME/data (ordering only), with fallbacks ----------
def git(cwd, *args, when=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    if when is not None:
        e.update(GIT_AUTHOR_DATE=f"{when} +0000", GIT_COMMITTER_DATE=f"{when} +0000")
    r = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *map(str, args)], cwd=cwd,
                       capture_output=True, text=True, env=e)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def commit_file(root, rel, text, when, msg):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg, when=when)


@pytest.fixture
def repo(root):
    if not shutil.which("git"):
        pytest.skip("git is not installed")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "all campaigns", when=1_700_000_000)
    commit_file(root, "campaigns/beta/data/marker.txt", "b", 1_700_000_100, "Beta save: turn 3")
    commit_file(root, "campaigns/gamma/data/marker.txt", "g", 1_700_000_200, "Gamma save: turn 9")
    commit_file(root, "campaigns/alpha/notes.txt", "n", 1_700_000_500, "docs only, not a save")  # outside data/: no effect on the order
    return root


def test_menu_orders_by_the_last_commit_touching_the_campaign_data(repo, sess):
    r = run("menu", root=repo, session=sess)
    assert r.returncode == 0, r.stderr
    assert menu_campaigns(r.stdout) == ["gamma", "beta", "alpha"]  # alphabetical order would be the reverse
    commit_file(repo, "campaigns/alpha/data/marker.txt", "a", 1_700_000_900, "Alpha save: turn 1")
    assert menu_campaigns(run("menu", root=repo, session=sess).stdout) == ["alpha", "gamma", "beta"]
    assert "1_700" not in r.stdout and "17000" not in r.stdout  # ordering only: no time is printed


def test_menu_falls_back_to_name_order_when_git_cannot_say(root, sess, tmp_path):
    r = run("menu", root=root, session=sess)  # not a git repository (or no history for these paths)
    assert r.returncode == 0 and menu_campaigns(r.stdout) == list(NAMES)
    empty = tmp_path / "nogit"
    empty.mkdir()
    r = run("menu", root=root, session=sess, path=empty)  # no git program on PATH
    assert r.returncode == 0 and menu_campaigns(r.stdout) == list(NAMES)


def test_menu_puts_a_campaign_with_no_save_commit_last(repo, sess):
    shutil.copytree(repo / "campaigns" / "gamma", repo / "campaigns" / "delta")  # never committed: no save time
    r = run("menu", root=repo, session=sess)
    assert r.returncode == 0 and menu_campaigns(r.stdout) == ["gamma", "beta", "alpha", "delta"]


def test_menu_in_a_repository_without_commits(root, sess):
    if not shutil.which("git"):
        pytest.skip("git is not installed")
    git(root, "init", "-q")
    r = run("menu", root=root, session=sess)
    assert r.returncode == 0 and menu_campaigns(r.stdout) == list(NAMES)


def test_menu_in_a_shallow_clone(repo, sess, tmp_path):
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", "--depth", "1", f"file://{repo}", clone)
    r = run("menu", root=clone, session=sess)
    assert r.returncode == 0, r.stderr
    assert menu_campaigns(r.stdout) == list(NAMES)  # one commit holds every campaign: same time, so the name order


# ---- hermetic: the suite's own session file, never the repo's ------------------------------------------------
def test_the_suite_points_db_at_its_own_session_file():
    p = Path(os.environ["DB_SESSION_FILE"])
    assert REPO not in p.parents and p.name == "session.json"
    repo_file = REPO / ".voyage-session.json"
    existed = repo_file.exists()
    try:
        r = subprocess.run([sys.executable, str(DB), "use", "classroom-2b"], capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, cwd=REPO)  # the environment as a helper would pass it on
        assert r.returncode == 0, r.stderr
        assert p.is_file() and json.loads(p.read_text(encoding="utf-8"))["campaign"] == "classroom-2b"
        assert repo_file.exists() == existed  # the repo root was not touched
    finally:
        if not existed and repo_file.exists():
            repo_file.unlink()


def test_the_environment_variable_survives_the_helpers_filters():
    e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    assert e["DB_SESSION_FILE"] == os.environ["DB_SESSION_FILE"]
