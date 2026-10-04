"""`db.py scan FILE|-`: the hidden-term scan for any text the user may see (ORCH-5, SEC-1). Exit 0 and one line when the text is clean,
exit 4 and one line per hit when it is not. Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA); a tmp VOYAGE_ROOT
holds a changed campaign.json where a test needs one. No test asserts on the first line of an output: every db.py output may gain a
campaign-name header line, so each one searches the whole output."""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
CAMPAIGN = "classroom-2b"
REAL_DATA = REPO / "campaigns" / CAMPAIGN / "data"

CLEAN = "Aiko and Tatsuya Ōmine share tea in the kitchen while the House Manager posts the chore rota."
LADDER_LEAK = "Mio Tachibana lowers her voice: the criminal lender wants the money back."  # a hidden step of "Mio's secret" (strong term)
LADDER_SOFT = "Tatsuya Ōmine jokes about a lender."  # a soft term: check-prompt only warns on it

CHARTER = {  # a draft arc: hidden twist keywords, a hidden antagonist, shared text that holds neither
    "budget_turns": 10,
    "shared": {
        "title": "Who Holds the Keys", "tone": "Wry and warm", "promise": "Can you earn the house's trust before it must choose?",
        "premise": "A quiet squeeze on the house.", "pressure": "An inspection nobody can move.",
        "set_pieces": ["a tense house meeting", "a favor traded under time pressure"], "pc_tests": {"Aiko Tanaka": "social"},
        "subplot": "A favor owed outside the house.", "climax_kind": "A public inspection", "ending_shape": "Bittersweet",
        "stakes": "personal", "seeds": ["a scratched-out name"], "wins_on_offer": ["a staff ally"], "echoes": ["you covered a chore"],
        "backstory_hooks": ["the repair shop"], "deviations": []},
    "hidden": {
        "twist": {"text": "A housemate took the money.", "ladder": "Mio's secret", "keywords": ["glass lantern"]},
        "fronts": [{"name": "The Lender", "goal": "Get paid", "moves": ["A polite offer", "A second visit", "A written deadline"]},
                   {"name": "The Agent", "goal": "End the lease", "moves": ["A walkthrough", "A formal notice"]}],
        "antagonist": {"name": "Sōichi Tamaru", "face": "a polite broker", "first_contact": "an offer at the gate"},
        "clues": ["a thick envelope", "a neighbor's story", "a cash payment", "a card in a coat"],
        "surprises": ["the inspector knows Arimura"], "climax_options": ["a house vote"], "pc_test_situations": {"Aiko Tanaka": "two opposite promises"},
        "cast": ["Mio Tachibana"], "new_npcs": [], "notes": "keep it offscreen"}}

OFFRAMPS = [{"thread": "went to the net menders instead of the guild clerk", "promise": "Can the net menders be repaid before the tide turns?",
             "front": "a broker who wants the menders' hut", "face": "Haru Ebisu, a tide broker",
             "first_move": "A net mender hands over a tide table at dusk"}]


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, stdin=None, trial=False, root=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA", "VOYAGE_ROOT")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": CAMPAIGN, "PYTHONDONTWRITEBYTECODE": "1"})
        if trial:
            e["VOYAGE_TRIAL"] = "1"
        if root:
            e["VOYAGE_ROOT"] = str(root)
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, input=stdin, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    def text(self, text, name="out.txt"):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def scan(self, text, **kw):
        return self.run("scan", self.text(text), **kw)

    def draft_arc(self, mutate=None):
        c = copy.deepcopy(CHARTER)
        if mutate:
            mutate(c)
        self.ok("arc-plan", "--file", self.text(json.dumps(c), "charter.json"))

    def offramps(self, ident="A1"):
        self.ok("arc-offramps", ident, "--file", self.text(json.dumps(OFFRAMPS), "offramps.json"))

    def with_campaign(self, change):
        """A tmp VOYAGE_ROOT whose classroom-2b campaign.json is the real one after `change(cfg)`."""
        root = self.tmp / "root"
        cdir = root / "campaigns" / CAMPAIGN
        cdir.mkdir(parents=True, exist_ok=True)
        cfg = json.loads((REPO / "campaigns" / CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))
        change(cfg)
        (cdir / "campaign.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        return root


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)  # start without arcs: a test that needs one drafts it
    return Env(data, tmp_path)


def hit(r, term, where=None):
    """The scan refused the text (exit 4) and names the term (and where it comes from) somewhere in its output."""
    assert r.returncode == 4, (r.returncode, r.stdout, r.stderr)
    assert f'HIT "{term}"' in r.stdout, r.stdout
    if where:
        assert where in r.stdout, r.stdout
    return r.stdout


# ---- clean texts -----------------------------------------------------------------------------------------------------------
def test_a_clean_text_passes_with_one_line(env):
    r = env.scan(CLEAN)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "clean" in r.stdout and "HIT" not in r.stdout
    assert len([ln for ln in r.stdout.splitlines() if "scan:" in ln]) == 1
    assert env.run("scan", env.text("")).returncode == 0  # an empty text holds nothing


def test_a_soft_secret_term_is_no_hit_but_a_strong_one_is(env):
    assert env.scan(LADDER_SOFT).returncode == 0  # check-prompt only warns on soft terms
    out = hit(env.scan(LADDER_LEAK), "criminal lender", "Mio's secret step 2")
    assert "the criminal lender wants" in out  # a short excerpt around the term


# ---- hidden ladder steps ---------------------------------------------------------------------------------------------------
def test_a_hidden_ladder_word_fails_and_a_revealed_step_passes(env):
    assert env.scan(LADDER_LEAK).returncode == 4
    assert env.scan("Mio mentions a Loan Shark.").returncode == 4  # case does not matter
    assert env.scan("Mio mentions the loan   sharks.").returncode == 4  # nor does spacing, nor a plural ending
    t = env.load("threads")
    for step in t["Mio's secret"]["steps"]:
        step["status"] = "revealed"
    env.save_json("threads", t)
    assert env.scan(LADDER_LEAK).returncode == 0  # a revealed step is no secret
    assert env.scan("Mio mentions a Loan Shark.").returncode == 0


def test_a_public_ok_term_passes_where_the_same_term_otherwise_fails(env):
    assert env.scan(LADDER_LEAK).returncode == 4
    root = env.with_campaign(lambda cfg: cfg.update(public_ok=list(cfg.get("public_ok") or []) + ["criminal lender"]))
    r = env.scan(LADDER_LEAK, root=root)
    assert r.returncode == 0, r.stdout + r.stderr
    assert env.scan("Mio mentions a loan shark.", root=root).returncode == 4  # only the listed term is public


# ---- hidden arc fields -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,term,where", [
    ("A glass lantern sits on the sill.", "glass lantern", "arc A1 twist keyword"),
    ("Everyone avoids mentioning the glass lanterns.", "glass lantern", "arc A1 twist keyword"),  # a plural ending
    ("A polite broker named Sōichi Tamaru waits at the gate.", "soichi tamaru", "arc A1 antagonist"),
    ("Soichi Tamaru waits at the gate.", "soichi tamaru", "arc A1 antagonist"),  # the accent does not matter
])
def test_a_hidden_arc_field_fails(env, text, term, where):
    assert env.scan(text).returncode == 0  # no arc yet: nothing to hide
    env.draft_arc()
    hit(env.scan(text), term, where)
    assert env.scan(CLEAN).returncode == 0
    assert env.scan("The house hears the title Who Holds the Keys and the promise of trust.").returncode == 0  # shared fields are public


def test_a_revealed_twist_and_a_public_antagonist_pass(env):
    env.draft_arc()
    assert env.scan("A glass lantern sits on the sill.").returncode == 4
    a = env.load("arcs")
    a["arcs"][0]["hidden"]["twist"]["revealed_turn"] = 3  # what arc-reveal records
    env.save_json("arcs", a)
    assert env.scan("A glass lantern sits on the sill.").returncode == 0
    assert env.scan("Sōichi Tamaru waits at the gate.").returncode == 4
    a["arcs"][0]["hidden"]["antagonist"]["contact_turn"] = 3  # the antagonist's face reached the PC on screen
    env.save_json("arcs", a)
    assert env.scan("Sōichi Tamaru waits at the gate.").returncode == 0


# ---- off-ramps -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,field", [
    ("They say she went to the net menders instead of the guild clerk.", "thread"),
    ("Can the net menders be repaid before the tide turns?", "promise"),
    ("Meet Haru Ebisu, a tide broker.", "face"),
    ("At dusk a net mender hands over a tide table at dusk. A net mender hands over a tide table at dusk.", "first_move"),
])
def test_an_offramp_term_fails(env, text, field):
    env.draft_arc()
    assert env.scan(text).returncode == 0  # nothing stored yet
    env.offramps()
    hit_out = env.scan(text)
    assert hit_out.returncode == 4 and f"off-ramp {field}" in hit_out.stdout, hit_out.stdout
    assert env.scan("The net menders mend nets by the quay.").returncode == 0  # a few of its words are not its text


def test_scan_agrees_with_the_planner_page_on_an_offramp_in_a_shared_field(env):
    env.draft_arc()
    env.offramps()
    leak = "A net mender hands over a tide table at dusk."
    env.ok("arc-plan", "--id", "A1", "--file", env.text(json.dumps({"shared": {"premise": leak}}), "u.json"))
    page = env.tmp / "page.html"
    assert env.run("planner-page", "--out", page).returncode == 4 and not page.exists()  # the page refuses the shared field...
    assert env.scan(leak).returncode == 4  # ...and the scan refuses the same text anywhere


# ---- campaign hidden words and hidden-score words --------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["The ledger is open on the desk.", "Nobody mentions the debts.", "Her Standing is the talk of the house."])
def test_a_campaign_hidden_word_fails(env, text):
    out = env.scan(text)
    assert out.returncode == 4 and "campaign hidden word" in out.stdout, out.stdout


def test_a_hidden_score_module_name_fails_even_without_a_hidden_words_list(env):
    def change(cfg):
        cfg["hidden_words"] = {"prompt": [], "recap": []}
        cfg["modules"]["standing"].update(label="Reputation")
    root = env.with_campaign(change)
    hit(env.scan("Her Reputation is falling.", root=root), "reputation", "hidden-score word")
    assert env.scan(CLEAN, root=root).returncode == 0

    def off(cfg):
        change(cfg)
        cfg["modules"]["standing"]["enabled"] = False
    assert env.scan("Her Reputation is falling.", root=env.with_campaign(off)).returncode == 0  # a module that is off hides nothing


# ---- input, output, and read-only ------------------------------------------------------------------------------------------
def test_stdin_input_works(env):
    r = env.run("scan", "-", stdin=CLEAN)
    assert r.returncode == 0 and "clean" in r.stdout
    r = env.run("scan", "-", stdin=LADDER_LEAK)
    assert r.returncode == 4 and 'HIT "criminal lender"' in r.stdout
    r = env.run("scan", "-", stdin="Mio hides a loan shark, Sōichi wrote.\n")
    assert r.returncode == 4 and 'HIT "loan shark"' in r.stdout


def test_every_hit_is_listed_once_and_a_missing_file_is_not_a_clean_scan(env):
    out = hit(env.scan("A loan shark, a criminal lender, another loan shark, and the ledger."), "loan shark")
    assert out.count('HIT "loan shark"') == 1 and 'HIT "criminal lender"' in out and 'HIT "ledger"' in out
    r = env.run("scan", env.tmp / "nope.txt")
    assert r.returncode == 1 and "no such file" in r.stderr and "clean" not in r.stdout


def test_scan_writes_nothing_and_works_in_a_trial_run(env):
    env.draft_arc()
    env.offramps()
    before = {p.name: p.read_bytes() for p in env.data.iterdir() if p.is_file()}
    assert env.scan(CLEAN, trial=True).returncode == 0
    assert env.scan(LADDER_LEAK, trial=True).returncode == 4
    assert env.run("scan", "-", stdin="the glass lantern", trial=True).returncode == 4
    assert {p.name: p.read_bytes() for p in env.data.iterdir() if p.is_file()} == before
