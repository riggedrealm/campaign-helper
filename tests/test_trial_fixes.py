"""Fixes from the Luxcellia trial run: the sync report names its unmatched quests and its compared values, turn-brief's Studio cues
leave out what the latest sync digest shows in Voyage, and a `Cut:` line only counts as a skip when it really skips (no negated
forms). Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA) with small synthetic saves and digests; no world file or
Voyage export is opened, and no test asserts on the first line of an output (a campaign line comes first)."""
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
HOME_LOC, HOME_AREA = "Sakura Lane Sharehouse", "building-entrance"
OTHER_LOC, OTHER_AREA = "Midnight Diner", "counter"
HOME = "Sakura Lane Sharehouse/shared-kitchen"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp, self.n = data, tmp, 0

    def run(self, *args):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": CAMPAIGN, "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def edit(self, name, fn):
        d = self.load(name)
        fn(d)
        (self.data / f"{name}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def turn(self, n, inputs="Aiko chats with the housemates in the kitchen", cut="Continue at the kitchen."):
        self.ok("turn", n, "--inputs", inputs, "--summary", f"Turn {n}.", "--prompt", f"Cut: {cut}\nWorld: Quiet.")

    def advance(self, to):
        for n in range(self.load("state")["turn"] + 1, to + 1):
            self.turn(n)

    def export(self, save):
        self.n += 1
        return self.write(f"export{self.n}.json", json.dumps(save))

    def sync(self, save):
        return self.ok("sync", self.export(save))

    def studio(self):
        got = [ln for ln in self.ok("turn-brief").splitlines() if ln.startswith("Studio:")]
        return got[0] if got else None

    def prep_checklist(self):
        out = self.ok("prep")
        return out[out.index("LIVE CHECKLIST"):]

    def check(self, prompt, *args):
        return self.run("check-prompt", self.write("prompt.txt", prompt), *args)


@pytest.fixture
def env(tmp_path):
    """Classroom 2B copy without its arcs file, Aiko at the sharehouse, three turns logged, Day 5 morning."""
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    (data / "arcs.json").unlink(missing_ok=True)
    e = Env(data, tmp_path)
    e.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    e.ok("pos", "Aiko Tanaka", HOME_LOC, HOME_AREA, "--turn", "1", "--evidence", "test")
    e.ok("time", "--day", 5, "--block", "Morning", "--clock", "09:00", "--turn", 1, "--evidence", "test")
    e.advance(3)
    return e


def save_of(tick=3, members=("Aiko Tanaka",), place=(OTHER_LOC, OTHER_AREA), quests=None):
    save = {"engineState": {"ticks": tick},
            "partyState": {"day": 5, "timeOfDay": "Morning", "currentLocation": place[0], "currentArea": place[1],
                           "partyMembers": [{"name": m} for m in members]},
            "turnData": []}
    if quests is not None:
        save["quests"] = {f"q{i}": {"name": n, "status": s} for i, (n, s) in enumerate(quests.items())}
    return save


# ---- 1. the sync report names what did not match ------------------------------------------------------------------------------
def line_of(out, start):
    got = [ln.strip() for ln in out.splitlines() if ln.strip().startswith(start)]
    assert got, f"no line starting {start!r} in:\n{out}"
    return got[0]


def test_sync_lists_the_quests_that_matched_nothing_on_either_side(env):
    db_names = list(env.load("quests"))
    out = env.sync(save_of(quests={db_names[0]: "active", "Voyage Own Errand": "active", "Another Chain Quest": "completed"}))
    assert "quests matched 1 of 3 in the save" in out
    assert line_of(out, "save quests with no database match") == "save quests with no database match (2): Voyage Own Errand; Another Chain Quest"
    unmatched = line_of(out, "database quests with no save match")
    assert unmatched.startswith(f"database quests with no save match ({len(db_names) - 1}): ")
    assert db_names[0] not in unmatched and db_names[1] in unmatched
    assert "Voyage Own Errand" not in unmatched


def test_sync_says_none_when_every_quest_matches(env):
    db_names = list(env.load("quests"))
    out = env.sync(save_of(quests={n: "active" for n in db_names}))
    assert line_of(out, "save quests with no database match") == "save quests with no database match (0): none"
    assert line_of(out, "database quests with no save match") == "database quests with no save match (0): none"


def test_sync_matches_a_quest_by_its_name_field_and_lists_the_rest(env):
    q = env.load("quests")
    key = next(iter(q))
    env.edit("quests", lambda d: d[key].update(name="Renamed In Voyage"))
    out = env.sync(save_of(quests={"Renamed In Voyage": "active"}))
    assert "quests matched 1 of 1 in the save" in out
    assert "save quests with no database match (0): none" in line_of(out, "save quests")
    assert key not in line_of(out, "database quests with no save match")


def test_sync_prints_the_compared_position_and_party_values(env):
    out = env.sync(save_of(members=("Aiko Tanaka", "Zed Newcomer")))
    assert line_of(out, "compared, position") == (
        f"compared, position (database vs save): Aiko Tanaka {HOME_LOC}/{HOME_AREA} vs {OTHER_LOC}/{OTHER_AREA}")
    assert line_of(out, "compared, party") == (
        "compared, party (database vs save): database player characters 1 (Aiko Tanaka); save party 2 (Aiko Tanaka, Zed Newcomer)")


def test_sync_compared_lines_are_short_and_survive_a_save_with_no_place(env):
    save = save_of()
    del save["partyState"]["currentLocation"], save["partyState"]["currentArea"]
    out = env.sync(save)
    assert "compared, position (database vs save): none (the save gives no place for any player character)" in out
    assert all(len(ln) < 200 for ln in out.splitlines() if "compared," in ln)


def test_sync_says_undone_director_turns_none_explicitly(env):
    out = env.sync(save_of(tick=3))
    assert "undone director turns: none" in out and "the ticks agree" in out
    out = env.sync(save_of(tick=5, members=("Aiko Tanaka", "Ren Kato")))  # ticks played without the director: still no undone turn
    assert "undone director turns: none" in out


def test_sync_lists_undone_turns_and_drops_the_none_line(env):
    out = env.sync(save_of(tick=1))
    assert "director turns Voyage no longer has: 2 to 3 (2)" in out
    assert "undone director turns: none" not in out


# ---- 2. no Studio cue for what the latest digest shows in Voyage -------------------------------------------------------------
def test_a_quest_in_the_latest_digest_is_no_studio_cue(env):
    env.ok("quest-start", "Gentle Hands", "--turn", 3, "--evidence", "the story showed it")
    assert 'quest started in play, not in Studio: "Gentle Hands"' in env.studio()  # no digest yet: the cue fires
    env.sync(save_of(quests={"Gentle Hands": "active"}))
    assert "Gentle Hands" not in (env.studio() or "")
    assert env.load("quests")["Gentle Hands"].get("in_studio") is not True  # the data itself is untouched


def test_a_digest_without_the_quest_still_cues_it(env):
    env.ok("quest-start", "Gentle Hands", "--turn", 3, "--evidence", "the story showed it")
    env.sync(save_of(quests={"Midterm Marks": "active"}))
    assert 'quest started in play, not in Studio: "Gentle Hands"' in env.studio()


def test_only_the_latest_digest_counts(env):
    env.ok("quest-start", "Gentle Hands", "--turn", 3, "--evidence", "the story showed it")
    env.sync(save_of(quests={"Gentle Hands": "active"}))
    assert "Gentle Hands" not in (env.studio() or "")
    env.sync(save_of(tick=3, quests={"Midterm Marks": "active"}, members=("Aiko Tanaka", "Ren Kato")))  # a newer digest, no Gentle Hands
    assert 'quest started in play, not in Studio: "Gentle Hands"' in env.studio()


def test_a_missing_or_broken_digest_file_changes_nothing(env):
    env.ok("quest-start", "Gentle Hands", "--turn", 3, "--evidence", "the story showed it")
    (env.data / "sync.json").write_text("not json", encoding="utf-8")
    assert 'quest started in play, not in Studio: "Gentle Hands"' in env.studio()
    (env.data / "sync.json").write_text('{"quests": {"Gentle Hands": "active"}}', encoding="utf-8")  # not a list of digests
    assert 'quest started in play, not in Studio: "Gentle Hands"' in env.studio()


def test_a_digest_quest_is_left_out_of_the_act_bundle_too(env):
    env.edit("state", lambda s: s.update(day=7, weekday="Friday", act=1))  # act 2 starts tomorrow
    assert "1 quest (Midterm Marks)" in env.studio()
    env.sync(save_of(quests={"Midterm Marks": "active"}))
    assert "Midterm Marks" not in (env.studio() or "")


def test_an_npc_in_the_latest_digest_party_is_no_recurring_cue(env):
    env.ok("add-npc", "Pip Baker", "--turn", 3, "--evidence", "Voyage showed them")
    for n, text in ((4, "buys bread from"), (5, "thanks"), (6, "helps")):
        env.turn(n, f"Aiko {text} Pip Baker")
    assert "recurring, not in Studio: Pip Baker (3 of 6 turns)" in env.studio()
    env.sync(save_of(tick=6, members=("Aiko Tanaka", "Pip Baker")))
    assert "Pip Baker" not in (env.studio() or "")
    env.sync(save_of(tick=6, members=("Aiko Tanaka",)))  # a newer digest without them: the cue is back
    assert "recurring, not in Studio: Pip Baker" in env.studio()


def test_an_npc_who_is_only_a_player_character_in_the_digest_changes_no_cue(env):
    env.sync(save_of(members=("Aiko Tanaka",)))
    assert env.studio() is None


# ---- 3. repeated skips counts only a Cut that skips -----------------------------------------------------------------------------
NEGATED = ["No skip.", "Stay on the pier, same moment. No skip.", "Don't skip.", "Don’t skip ahead.", "Same moment, without skipping.",
           "Same moment, not skipping.", "Do not skip.", "Stay put, no time skip.", "We never skip here."]
SKIPPING = ["Skip to the evening.", "Skipping ahead to dawn.", "The scene skipped a day.", "Do not skip the walk; skip to the market.",
            "Same moment? No: skip to the pier."]


def ten_turns(env, cuts):
    for n in range(4, 8):  # the fixture logged turns 1 to 3
        env.turn(n, inputs="a" * 40)
    for n, cut in zip((8, 9, 10), cuts):
        env.turn(n, inputs="a" * 40, cut=cut)


@pytest.mark.parametrize("cut", NEGATED)
def test_a_negated_skip_is_not_a_repeated_skip(env, cut):
    ten_turns(env, [cut, cut, "Continue at the kitchen."])
    assert "repeated skips" not in env.prep_checklist()


@pytest.mark.parametrize("cut", SKIPPING)
def test_a_real_skip_still_counts(env, cut):
    ten_turns(env, [cut, cut, "Continue at the kitchen."])
    assert "repeated skips" in env.prep_checklist()


def test_one_real_skip_among_negated_ones_is_not_enough_and_two_are(env):
    ten_turns(env, ["No skip.", "Skip to the evening.", "Stay on the pier, same moment. No skip."])
    assert "repeated skips" not in env.prep_checklist()
    env.turn(11, inputs="a" * 40, cut="Skipping to the next morning.")
    assert "repeated skips" in env.prep_checklist()


# ---- 4. the same negation handling wherever a Cut: line is read for a skip ----------------------------------------------------
@pytest.mark.parametrize("cut", ["Don't skip.", "Don’t skip ahead.", "Same moment, without skipping.", "Same moment, not skipping.",
                                 "No skip.", "Same moment, no time skip."])
def test_check_prompt_does_not_warn_about_a_negated_cut_skip(env, cut):
    r = env.check(f"Cut: Continue at {HOME}. {cut}\nCrew: Tatsuya Ōmine pours tea.\nWorld: The House Manager posts the rota.",
                  "--inputs", "Aiko: says hi to Mio and pours a cup of tea")
    assert "(CUT-2)" not in r.stdout, r.stdout


@pytest.mark.parametrize("cut", ["Skip to the evening.", "Do not skip the walk; skip to the evening."])
def test_check_prompt_still_warns_about_a_real_cut_skip(env, cut):
    r = env.check(f"Cut: Continue at {HOME}. {cut}\nCrew: Tatsuya Ōmine pours tea.\nWorld: The House Manager posts the rota.",
                  "--inputs", "Aiko: says hi to Mio and pours a cup of tea")
    assert "(CUT-2)" in r.stdout, r.stdout


# ---- 5. as <PC> chose restates the input; every other stated outcome still warns ------------------------------------------------
def outcome_warns(env, cut):
    r = env.check(f"Cut: {cut}\nCrew: Tatsuya Ōmine pours tea.\nWorld: The House Manager posts the rota.", "--inputs", "Aiko: walks back")
    assert r.returncode == 0, r.stderr
    return [ln for ln in r.stdout.splitlines() if ln.startswith("WARN") and "states a player outcome" in ln]


@pytest.mark.parametrize("cut", [f"Continue at {HOME}, late night, as Aiko chose: the walk back.",
                                 f"Continue at {HOME}, late night, as Aiko Tanaka chose: the walk back.",
                                 f"Continue at {HOME}, as Aiko would choose: the walk back."])
def test_as_pc_chose_is_not_a_stated_outcome(env, cut):
    assert outcome_warns(env, cut) == []


@pytest.mark.parametrize("cut", [f"Continue at {HOME}. Aiko chose the walk back.", f"Continue at {HOME}. Aiko decides to walk back.",
                                 f"Continue at {HOME}. As the lights dim, Aiko chose the tea.", f"Continue at {HOME}. Aiko feels tired.",
                                 f"Continue at {HOME}, late night, as Aiko chose: the walk back. Aiko decides to stay."])
def test_every_other_stated_outcome_still_warns(env, cut):
    assert outcome_warns(env, cut)


# ---- 6. D22: a contested ask in the input and an NPC's yes in the prompt ---------------------------------------------------------
ASK_INPUT = "Will you join my party?"
YES_LINE = '"Three terms, sword saint. Agree to all three and the answer is yes."'
CONDITIONAL = "If his ask lands, she names three terms and a yes; if not, she names her terms and a not yet."


def d22(env, line, inputs=ASK_INPUT, *extra):
    r = env.check(f"Cut: Continue at {HOME}.\nCrew: Tatsuya Ōmine says, {line}\nWorld: The House Manager posts the rota.", "--inputs", inputs, *extra)
    assert r.returncode == 0, r.stdout + r.stderr
    return [ln for ln in r.stdout.splitlines() if ln.startswith("WARN") and "contested ask" in ln]


def test_a_stated_yes_to_a_contested_ask_warns(env):
    w = d22(env, YES_LINE)
    assert len(w) == 1 and "AGY-3" in w[0] and "FMT-10" in w[0] and "Voyage rolls" in w[0]


def test_the_conditional_rewrite_does_not_warn(env):
    assert d22(env, CONDITIONAL) == []


def test_a_conditional_yes_in_a_quote_does_not_warn(env):
    assert d22(env, 'If it lands, "Three terms. Yes." and if not, "Not yet."') == []
    assert d22(env, "unless it fails, she accepts.") == []
    assert d22(env, "should it land, she joins.") == []


@pytest.mark.parametrize("line", ["she agrees.", "she accepts his offer.", "Yes.", "she joins the party.", "the answer is yes."])
def test_each_kind_of_acceptance_warns(env, line):
    assert d22(env, line)


@pytest.mark.parametrize("inputs", ["Aiko: persuade the guard", "Aiko: tries to bribe him", "Aiko: haggle over the price", "Aiko: intimidate the clerk",
                                    "Aiko: threaten the rival", "Aiko: negotiate the rent", "Aiko: recruit Mio", "Aiko: convince her to come"])
def test_each_contested_ask_warns(env, inputs):
    assert d22(env, "she agrees.", inputs)


def test_no_contested_ask_or_no_acceptance_means_no_warning(env):
    assert d22(env, YES_LINE, "Aiko: pours a cup of tea") == []
    assert d22(env, "she names her terms and a not yet.") == []
    r = env.check(f"Cut: Continue at {HOME}.\nCrew: Tatsuya Ōmine says, {YES_LINE}\nWorld: The House Manager posts the rota.")
    assert "contested ask" not in r.stdout  # no inputs at all: the check is skipped


def test_check_prompt_reads_the_ask_from_a_paste_file_too(env):
    paste = env.write("paste.txt", f"Voyage output...\nPlayer: {ASK_INPUT}\n")
    assert d22(env, YES_LINE, "Aiko: nods", "--paste", paste)


def test_the_contested_ask_warning_is_warn_only(env):
    r = env.check(f"Cut: Continue at {HOME}.\nCrew: Tatsuya Ōmine says, {YES_LINE}\nWorld: The House Manager posts the rota.", "--inputs", ASK_INPUT)
    assert r.returncode == 0 and "FAIL" not in r.stdout


def test_commit_turn_passes_the_payload_inputs_to_the_check(env):
    payload = {"turn": 4, "ops": [], "turn_log": {"inputs": ASK_INPUT, "summary": "She is asked."}}
    prompt = env.write("p.txt", f"Cut: Continue at {HOME}.\nCrew: Tatsuya Ōmine says, {YES_LINE}\nWorld: The House Manager posts the rota.")
    r = env.run("commit-turn", "--dry-run", "--prompt", prompt, "--payload", env.write("pl.json", json.dumps(payload)))
    assert "contested ask" in r.stdout, r.stdout + r.stderr
    payload["turn_log"]["inputs"] = "Aiko pours tea"
    r = env.run("commit-turn", "--dry-run", "--prompt", prompt, "--payload", env.write("pl.json", json.dumps(payload)))
    assert "contested ask" not in r.stdout, r.stdout + r.stderr
