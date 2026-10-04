"""check-prompt and commit-turn agency warnings (handoff 4.6.6): FMT-7, TONE-1, AGY-2/AGY-3, CUT-2, session zero, cross-campaign names.
Every warning is WARN only: it never prints FAIL and never changes the exit code. Tests run on a tmp copy of the classroom-2b data
(VOYAGE_DATA); the other campaigns are read from the repo (read-only). Assertions search the whole output, never its first line."""
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
HOME = "Sakura Lane Sharehouse/shared-kitchen"
WARN_MARKS = ("(FMT-7)", "(TONE-1)", "(CUT-2)", "player outcome", "session zero", "wrong campaign")


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, stdin=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": CAMPAIGN, "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, input=stdin, env=e, cwd=self.tmp)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def file(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def check(self, prompt, *args):
        return self.run("check-prompt", self.file("prompt.txt", prompt), *args)

    def log_turns(self, tones, cut="Continue at Sakura Lane Sharehouse"):
        """Log one turn per tone (Tone: line of its prompt), numbered from the next turn."""
        n = self.load("state")["turn"]
        for tone in tones:
            n += 1
            r = self.run("turn", n, "--inputs", "chat", "--summary", f"s{n}", "--prompt", f"Cut: {cut}.\nTone: {tone}\nWorld: x")
            assert r.returncode == 0, r.stdout + r.stderr

    def commit(self, prompt, inputs):
        t = self.load("state")["turn"] + 1
        payload = {"turn": t, "ops": [], "turn_log": {"inputs": inputs, "summary": f"summary {t}"}}
        return self.run("commit-turn", "--prompt", self.file("prompt.txt", prompt), "--payload", self.file("payload.json", json.dumps(payload)))


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    e = Env(data, tmp_path)
    r = e.run("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    assert r.returncode == 0, r.stderr + r.stdout
    return e


def warns(r):
    return [ln for ln in r.stdout.splitlines() if ln.startswith("WARN: ")]


def agency(r, mark):
    return [w for w in warns(r) if mark in w]


def clean(r):
    """No agency warning at all, no FAIL, exit code 0."""
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
    assert not [w for w in warns(r) if any(m in w for m in WARN_MARKS)], r.stdout


def only_warn(r, mark):
    """The output has the agency warning `mark` (one line), no FAIL, and the exit code is untouched (0)."""
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
    assert len(agency(r, mark)) == 1, r.stdout


def prompt(cut=f"Continue at {HOME}, same moment.", crew="Tatsuya Ōmine pours tea.", facts=None, tone=None, world="The House Manager hums."):
    parts = [f"Cut: {cut}"]
    if tone:
        parts.append(f"Tone: {tone}")
    parts.append(f"Crew: {crew}")
    if facts:
        parts.append(f"Facts: {facts}")
    parts.append(f"World: {world}")
    return "\n".join(parts)


def test_baseline_prompt_is_clean(env):
    r = env.check(prompt(), "--inputs", "say hi to Mio")
    assert r.returncode == 0 and "OK:" in r.stdout


# ---- 1. a place or rule that is not in the database (FMT-7) -------------------------------------------------------------
def test_place_reference_to_unknown_location_warns(env):
    r = env.check(prompt(cut="Continue at Zorblax Wharf/dock, same moment."))
    assert any("Zorblax Wharf/dock" in w for w in agency(r, "(FMT-7)")), r.stdout
    assert "FAIL" not in r.stdout


def test_place_reference_to_known_place_is_quiet(env):
    clean(env.check(prompt(world="The House Manager hums in Sakura Lane Sharehouse/building-entrance.")))


def test_unknown_area_of_known_location_keeps_the_existing_flag_only(env):
    r = env.check(prompt(cut="Continue at Sakura Lane Sharehouse/no-such-area, same moment."))
    assert r.returncode == 2 and "UNKNOWN AREA" in r.stdout  # exit code and flag as before
    assert not agency(r, "(FMT-7)"), r.stdout  # no second line for the same problem


def test_cut_place_that_is_not_in_the_database_warns(env):
    r = env.check(prompt(cut="Continue at Zorblax Wharf, same moment."))
    assert any("`Cut:` place" in w and "Zorblax Wharf" in w for w in warns(r)), r.stdout
    assert "FAIL" not in r.stdout


def test_cut_place_that_is_known_is_quiet(env):
    clean(env.check(prompt(cut="Continue at Sakura Lane Sharehouse, same moment.")))
    clean(env.check(prompt(cut=f"Continue at {HOME}, Day 1 morning.")))
    clean(env.check(prompt(cut="Continue at Chikara Academy, same moment.")))  # no inputs given: the skip check is not run


def test_cut_place_with_an_unknown_area_name_warns(env):
    r = env.check(prompt(cut="Continue at Sakura Lane Sharehouse Cellar, same moment."))
    assert any("`Cut:` place" in w and "Sakura Lane Sharehouse Cellar" in w for w in warns(r)), r.stdout


def test_facts_rule_without_canon_warns(env):
    r = env.check(prompt(facts="Students must wear the uniform on campus."))
    only_warn(r, "states a rule")
    assert "(FMT-7)" in agency(r, "states a rule")[0]


@pytest.mark.parametrize("word", ["cannot", "only", "requires", "not allowed", "forbidden"])
def test_facts_rule_words(env, word):
    sentence = {"cannot": "Guests cannot enter the lab.", "only": "Only seniors enter the lab.", "requires": "The lab requires a keycard.",
                "not allowed": "Guests are not allowed in the lab.", "forbidden": "Guests are forbidden in the lab."}[word]
    only_warn(env.check(prompt(facts=sentence)), "states a rule")


def test_facts_rule_backed_by_a_canon_fact_is_quiet(env):
    text = prompt(facts="Students must wear the uniform on campus.")
    assert agency(env.check(text), "states a rule")
    r = env.run("fact", "Uniform rule", "Uniforms are required on campus for all students.", "--turn", "1", "--evidence", "Voyage output")
    assert r.returncode == 0, r.stdout + r.stderr
    clean(env.check(text))


def test_facts_rule_backed_by_an_npc_canon_note_is_quiet(env):
    text = prompt(facts="Mio Tachibana cannot enter the vault without Kenji Arimura.")
    assert agency(env.check(text), "states a rule")
    r = env.run("npc-note", "Mio Tachibana", "Mio cannot enter the vault without Kenji Arimura", "--turn", "1", "--evidence", "Voyage output")
    assert r.returncode == 0, r.stdout + r.stderr
    clean(env.check(text))


def test_facts_without_a_rule_word_is_quiet(env):
    clean(env.check(prompt(facts="The chore rota is on the fridge. Tatsuya Ōmine owns the blue mug.")))


def test_facts_unrelated_canon_does_not_back_a_rule(env):
    env.run("fact", "Garden", "The courtyard garden has lilac bushes by the river bedroom.", "--turn", "1", "--evidence", "Voyage output")
    only_warn(env.check(prompt(facts="Students must wear the uniform on campus.")), "states a rule")


# ---- 2. a Tone: fix older than 3 turns (TONE-1) --------------------------------------------------------------------------
def test_tone_unchanged_for_three_logged_turns_warns(env):
    env.log_turns(["quiet, warm. Short lines.", "quiet, warm. Short lines.", "quiet, warm. Short lines."])
    r = env.check(prompt(tone="quiet, warm. Short lines."))
    only_warn(r, "(TONE-1)")
    assert "last 3 prompts" in agency(r, "(TONE-1)")[0]


def test_tone_nearly_the_same_warns(env):
    env.log_turns(["quiet, warm, short lines", "warm, quiet. Short lines.", "Quiet and warm, short lines"])
    only_warn(env.check(prompt(tone="warm, quiet, short lines")), "(TONE-1)")


def test_tone_changed_within_the_window_is_quiet(env):
    env.log_turns(["quiet, warm", "quiet, warm", "tense, fast"])
    clean(env.check(prompt(tone="quiet, warm")))
    clean(env.check(prompt(tone="tense, fast")))  # the same as only the last turn


def test_tone_with_fewer_than_three_logged_turns_is_quiet(env):
    env.log_turns(["quiet, warm", "quiet, warm"])
    clean(env.check(prompt(tone="quiet, warm")))


def test_tone_missing_in_a_logged_prompt_or_in_this_one_is_quiet(env):
    env.log_turns(["quiet, warm", "quiet, warm"])
    n = env.load("state")["turn"] + 1
    env.run("turn", n, "--inputs", "chat", "--summary", "s", "--prompt", "Cut: Continue at Sakura Lane Sharehouse.\nWorld: x")
    clean(env.check(prompt(tone="quiet, warm")))  # the last logged prompt has no Tone: line
    env.log_turns(["quiet, warm", "quiet, warm", "quiet, warm"])
    clean(env.check(prompt()))  # this prompt has no Tone: line


# ---- 3. a stated player-character condition or outcome (AGY-2, AGY-3) ----------------------------------------------------
@pytest.mark.parametrize("crew", [
    "Tatsuya Ōmine pours tea; Aiko limps in.",
    "Tatsuya Ōmine pours tea while Aiko is hurt.",
    "Tatsuya Ōmine pours tea. Aiko is fine.",
    "Tatsuya Ōmine pours tea; Aiko Tanaka bleeds a little.",
    "Tatsuya Ōmine pours tea; Aiko feels cold.",
    "Tatsuya Ōmine pours tea; Aiko just feels sick.",
    "Tatsuya Ōmine pours tea; Aiko thinks of home.",
    "Tatsuya Ōmine pours tea; Aiko decides to stay.",
    "Tatsuya Ōmine pours tea; Aiko says nothing.",
    "Tatsuya Ōmine pours tea; Aiko passes the test.",
    "Tatsuya Ōmine pours tea; Aiko succeeds at the lock.",  # the existing outcome words are still caught, by the same warning
])
def test_pc_condition_or_outcome_warns_once_per_snippet(env, crew):
    r = env.check(prompt(crew=crew))
    only_warn(r, "states a player outcome")
    assert "player condition" not in r.stdout  # one warning, not a second kind


@pytest.mark.parametrize("crew", [
    "Tatsuya Ōmine pours tea; Aiko's tea feels cold.",  # a possessive thing, not the character
    'Tatsuya Ōmine pours tea and says "Aiko feels cold".',  # quoted speech is ignored
    "Tatsuya Ōmine pours tea. If Aiko asks, he answers in one short line.",  # a condition for an NPC to answer
    "Tatsuya Ōmine hands Aiko a mug and says hi.",
    "Tatsuya Ōmine asks Aiko what she wants.",
    "Tatsuya Ōmine pours tea; Aiko passes the salt.",
    "Tatsuya Ōmine pours tea; Aiko and Mio Tachibana sit.",
    "Mio Tachibana watches Aiko closely; Tatsuya Ōmine pours tea.",
])
def test_pc_condition_negatives(env, crew):
    clean(env.check(prompt(crew=crew)))


def test_pc_condition_two_snippets_two_lines(env):
    r = env.check(prompt(crew="Tatsuya Ōmine pours tea; Aiko limps in and Aiko decides to stay."))
    assert r.returncode == 0 and len(agency(r, "states a player outcome")) == 2, r.stdout


# ---- 4. a Cut: that skips when the input shows no travel, waiting or leaving (CUT-2) -------------------------------------
SKIPS = ["Skip to Sakura Lane Sharehouse/shared-kitchen, early afternoon.", f"Continue at {HOME}, the next morning.",
         f"Continue at {HOME}, hours later.", f"Continue at {HOME}, tomorrow after class.", f"Continue at {HOME}, later that evening.",
         f"Continue at {HOME}, three days later.", f"Continue at {HOME}. Time passes.", f"Continue at {HOME}, minutes later."]


@pytest.mark.parametrize("cut", SKIPS)
def test_cut_skip_without_travel_in_the_inputs_warns(env, cut):
    r = env.check(prompt(cut=cut), "--inputs", "Aiko: says hi to Mio and pours a cup of tea")
    only_warn(r, "(CUT-2)")


@pytest.mark.parametrize("cut", SKIPS)
def test_cut_skip_is_quiet_when_the_inputs_show_travel_waiting_or_leaving(env, cut):
    for inputs in ("Aiko: heads to the academy", "Aiko: waits until tomorrow", "Aiko: leaves the house", "Aiko: sleeps in",
                   "Aiko: walks to the station"):
        clean(env.check(prompt(cut=cut), "--inputs", inputs))


def test_cut_skip_is_not_judged_without_inputs(env):
    clean(env.check(prompt(cut=SKIPS[0])))
    clean(env.check(prompt(cut=SKIPS[0]), "--inputs", "   "))


@pytest.mark.parametrize("cut", [f"Continue at {HOME}, same moment.", f"Stay at {HOME}, same moment. No skip.",
                                 f"Continue at {HOME}, seconds later.", f"Continue at {HOME}, a moment later.",
                                 f"Continue at {HOME}, a minute later.", f"Continue at {HOME}, Day 1 morning.",
                                 f"Continue at {HOME}, same moment, no time skip."])
def test_cut_that_stays_is_quiet(env, cut):
    clean(env.check(prompt(cut=cut), "--inputs", "Aiko: pours a cup of tea"))


def test_cut_to_a_new_place_without_travel_in_the_inputs_warns(env):
    r = env.check(prompt(cut="Continue at Chikara Academy, same moment."), "--inputs", "Aiko: says hi to Mio")
    only_warn(r, "(CUT-2)")
    assert "new place Chikara Academy" in agency(r, "(CUT-2)")[0]
    clean(env.check(prompt(cut="Continue at Chikara Academy, same moment."), "--inputs", "Aiko: heads out to the academy"))
    clean(env.check(prompt(cut="Continue at Sakura Lane Sharehouse, same moment."), "--inputs", "Aiko: says hi to Mio"))  # where she is


def test_cut_skip_reads_the_paste_file_too(env):
    paste = env.file("paste.txt", "Voyage: Mio pours tea.\nAiko: says hi to Mio and pours a cup of tea\n")
    only_warn(env.check(prompt(cut=SKIPS[1]), "--paste", paste), "(CUT-2)")
    travel = env.file("paste2.txt", "Aiko: walks to the academy\n")
    clean(env.check(prompt(cut=SKIPS[1]), "--paste", travel))
    r = env.check(prompt(cut=SKIPS[1]), "--paste", env.tmp / "missing.txt")
    assert r.returncode == 1 and "no such paste file" in r.stderr + r.stdout


# ---- commit-turn shows the same warnings, still records ---------------------------------------------------------------------
def test_commit_turn_shows_the_warnings_and_still_records(env):
    text = prompt(cut=SKIPS[1], crew="Tatsuya Ōmine pours tea; Aiko limps in.", facts="Students must wear the uniform on campus.")
    r = env.commit(text, "Aiko: says hi to Mio")
    assert r.returncode == 0, r.stdout + r.stderr
    for mark in ("(CUT-2)", "player outcome", "states a rule"):
        assert len(agency(r, mark)) == 1, r.stdout
    assert "FAIL" not in r.stdout and "commit-turn 1: ok" in r.stdout
    assert env.load("state")["turn"] == 1 and env.load("turns")[-1]["inputs"] == "Aiko: says hi to Mio"


def test_commit_turn_cut_skip_uses_the_payload_inputs(env):
    r = env.commit(prompt(cut=SKIPS[1]), "Aiko: heads to the academy tomorrow")
    assert r.returncode == 0 and not agency(r, "(CUT-2)") and "commit-turn 1: ok" in r.stdout, r.stdout
    r = env.commit(prompt(cut=SKIPS[1]), "Aiko: pours a cup of tea")
    assert r.returncode == 0 and len(agency(r, "(CUT-2)")) == 1 and "commit-turn 2: ok" in r.stdout, r.stdout


def test_commit_turn_tone_warning(env):
    env.log_turns(["quiet, warm", "quiet, warm", "quiet, warm"])
    r = env.commit(prompt(tone="quiet, warm"), "chat")
    assert r.returncode == 0 and len(agency(r, "(TONE-1)")) == 1 and "commit-turn 4: ok" in r.stdout, r.stdout


def test_commit_turn_dry_run_shows_warnings_and_writes_nothing(env):
    t = env.load("state")["turn"] + 1
    payload = {"turn": t, "ops": [], "turn_log": {"inputs": "Aiko: pours tea", "summary": "s"}}
    r = env.run("commit-turn", "--dry-run", "--prompt", env.file("p.txt", prompt(cut=SKIPS[1])), "--payload", env.file("pl.json", json.dumps(payload)))
    assert r.returncode == 0 and len(agency(r, "(CUT-2)")) == 1 and "dry run OK" in r.stdout, r.stdout
    assert env.load("state")["turn"] == t - 1


# ---- 5. session zero's lines and veils -----------------------------------------------------------------------------------------
def test_session_zero_line_in_the_prompt_warns(env):
    r = env.run("session-zero", "--lines", "no harm to the cat", "--veils", "a bomb threat")
    assert r.returncode == 0, r.stdout + r.stderr
    only_warn(env.check(prompt(world="The cat takes harm in the storm.")), 'session zero line "no harm to the cat"')
    only_warn(env.check(prompt(world="A bomb threat reaches the house.")), 'session zero veil "a bomb threat"')


def test_session_zero_partial_match_is_quiet(env):
    env.run("session-zero", "--lines", "no harm to the cat", "--veils", "a bomb threat")
    clean(env.check(prompt(world="The cat naps in the sun; a threat of rain.")))
    clean(env.check(prompt(world="Harm is not the word; the House Manager hums.")))


def test_session_zero_empty_is_quiet(env):
    clean(env.check(prompt(world="The cat takes harm in the storm.")))


def test_session_zero_warning_shows_in_commit_turn(env):
    env.run("session-zero", "--lines", "no harm to the cat")
    r = env.commit(prompt(world="The cat takes harm in the storm."), "chat")
    assert r.returncode == 0 and len(agency(r, "session zero line")) == 1 and "commit-turn 1: ok" in r.stdout, r.stdout


# ---- 6. cross-campaign names (handoff 4.2) -------------------------------------------------------------------------------------
def other_names(campaign):
    base = REPO / "campaigns" / campaign / "data"
    out = set()
    for f in ("cast.json", "world-npcs.json"):
        out |= set(json.loads((base / f).read_text(encoding="utf-8")))
    return out


def test_cross_campaign_name_unknown_here_warns_and_names_the_campaign(env):
    assert "Haruto Saionji" in other_names("joestar")
    r = env.check(prompt(crew="Haruto Saionji pours tea."))
    ws = agency(r, "wrong campaign")
    assert len(ws) == 1 and "joestar" in ws[0] and "Haruto Saionji" in ws[0] and "classroom-2b" in ws[0], r.stdout
    assert "FAIL" not in r.stdout and r.returncode == 2  # the unknown-name flag is as before; the warning adds nothing to it


def test_cross_campaign_lone_first_name_at_the_start_of_a_clause_warns_without_changing_the_exit_code(env):
    assert any(k.startswith("Haruto") for k in other_names("joestar"))
    r = env.check(prompt(crew="Haruto nods."))
    only_warn(r, "wrong campaign")
    assert "joestar" in agency(r, "wrong campaign")[0]


def test_cross_campaign_names_group_by_campaign(env):
    assert "Yumi Aokiba" in other_names("luxcellia") and "Haruto Saionji" in other_names("joestar")
    r = env.check(prompt(crew="Haruto Saionji pours tea; Yumi Aokiba watches."))
    ws = agency(r, "wrong campaign")
    assert len(ws) == 2 and any("joestar" in w and "Haruto Saionji" in w for w in ws) and any("luxcellia" in w and "Yumi Aokiba" in w for w in ws)


def test_name_known_here_never_warns_even_if_another_campaign_has_it(env):
    shared = [t for t in ("Kenji", "Reiko", "Tatsuya", "Ayame") if any(t in k.split() for k in other_names("joestar") | other_names("luxcellia"))]
    assert shared, "the repo's other campaigns no longer share a first name with classroom-2b: pick another"
    r = env.check(prompt(crew="Kenji Arimura, Reiko Shimazu, Tatsuya Ōmine, Ayame Kujō and Mio Tachibana sit; Kenji nods and Ayame waves."))
    clean(r)


def test_cross_campaign_allowed_name_is_quiet(env):
    clean(env.check(prompt(crew="Tatsuya Ōmine pours tea; Haruto nods."), "--allow", "Haruto"))


def test_cross_campaign_unknown_name_in_no_other_campaign_is_not_a_cross_campaign_warning(env):
    r = env.check(prompt(crew="Zorblax Quenth pours tea."))
    assert not agency(r, "wrong campaign") and r.returncode == 2


def test_cross_campaign_warning_shows_in_commit_turn(env):
    r = env.commit(prompt(crew="Tatsuya Ōmine pours tea; Haruto Saionji nods."), "chat")
    assert r.returncode == 0 and len(agency(r, "wrong campaign")) == 1 and "joestar" in r.stdout and "commit-turn 1: ok" in r.stdout, r.stdout


# ---- all warnings together change nothing about the exit code or the FAIL lines --------------------------------------------------
def test_all_warnings_at_once_never_fail(env):
    env.run("session-zero", "--lines", "no harm to the cat")
    env.log_turns(["quiet, warm", "quiet, warm", "quiet, warm"])
    text = prompt(cut=SKIPS[1], tone="quiet, warm", crew="Tatsuya Ōmine pours tea; Aiko limps in; Haruto nods.",
                  facts="Students must wear the uniform on campus.", world="The cat takes harm. Sakura Lane Sharehouse/shared-kitchen hums.")
    r = env.check(text, "--inputs", "Aiko: pours tea")
    assert r.returncode == 0 and "FAIL" not in r.stdout, r.stdout
    for mark in ("(CUT-2)", "(TONE-1)", "player outcome", "states a rule", "session zero line", "wrong campaign"):
        assert len(agency(r, mark)) == 1, (mark, r.stdout)
    assert all(len(w) < 330 for w in warns(r))  # compact: one line each
