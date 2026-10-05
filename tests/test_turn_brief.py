"""`db.py turn-brief` (LOOP-2, LOOP-6, D21): the lean brief of every turn. Each line kind appears when due and is absent when not; a quiet
turn stays short; --full is prep's screen; the command writes nothing; nothing hidden reaches the output (the existing scan).
Every test runs on a tmp copy of real campaign data (VOYAGE_DATA); the real data dir is never written. No test asserts on the first
line of an output: every campaign command's output starts with a campaign line."""
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

CHARTER = {  # arc A1: antagonist and twist keyword are hidden; budget 10 turns
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
        "fronts": [{"name": "The Lender", "goal": "Get paid", "moves": ["A polite offer", "A second visit", "A written deadline"]}],
        "antagonist": {"name": "Sōichi Tamaru", "face": "a polite broker", "first_contact": "an offer at the gate"},
        "clues": ["a thick envelope", "a neighbor's story", "a cash payment", "a card in a coat"],
        "surprises": ["the inspector knows Arimura"], "climax_options": ["a house vote"], "pc_test_situations": {"Aiko Tanaka": "two opposite promises"},
        "cast": ["Mio Tachibana"], "new_npcs": [], "notes": "keep it offscreen"}}
OFFRAMPS = [
    {"thread": "went to the net menders instead of the guild clerk", "promise": "Can the net menders be repaid before the tide turns?",
     "front": "a broker who wants the menders hut", "face": "Haru Ebisu, a tide broker", "first_move": "A net mender hands over a tide table at dusk"},
    {"thread": "kept returning to the rota drawer", "promise": "Who has been moving the chore rota?", "front": "the house manager quiet audit",
     "face": "Teruko Kuroda, the rota keeper", "first_move": "The rota drawer is found emptied at breakfast"}]

PASTE = "Tatsuya Ōmine stirs the pot while Mio Tachibana counts the chore coins at the shared kitchen table."
FOOTER = ("Voyage owns every mechanic and outcome", "only the player moves their character", "every prompt ends with a `World:` move")


class Env:
    def __init__(self, data, tmp, campaign="classroom-2b"):
        self.data, self.tmp, self.campaign = data, tmp, campaign

    def run(self, *args):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": self.campaign, "PYTHONDONTWRITEBYTECODE": "1"})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, f"{args}: {r.stderr}{r.stdout}"
        return r.stdout

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def edit(self, name, fn):
        d = self.load(name)
        fn(d)
        self.save(name, d)

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def op(self, name, *args, turn, ev="the story showed it"):
        return self.ok(name, *args, "--turn", turn, "--evidence", ev)

    def turn(self, n, inputs="Aiko chats with the housemates in the kitchen", flag=False):
        self.ok("turn", n, "--inputs", inputs, "--summary", f"Turn {n}.", "--prompt", "Cut: Continue at the kitchen.\nWorld: Quiet.",
                *(["--arc-contact"] if flag else []))

    def advance(self, to, inputs="Aiko chats with the housemates in the kitchen"):
        for n in range(self.load("state")["turn"] + 1, to + 1):
            self.turn(n, inputs)

    def day(self, d):
        self.ok("time", "--day", d, "--block", "Morning", "--clock", "09:00", "--turn", max(1, self.load("state")["turn"]), "--evidence", "test")

    def brief(self, *args, paste=None):
        extra = ["--paste", self.write("paste.txt", paste)] if paste is not None else []
        return self.ok("turn-brief", *extra, *args).splitlines()

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.data.rglob("*") if p.is_file() and p.name != ".turn-clock"}  # the clock (turn-brief --full) is no data file


def make_env(tmp_path, campaign="classroom-2b"):
    data = tmp_path / "data"
    shutil.copytree(REPO / "campaigns" / campaign / "data", data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    return Env(data, tmp_path, campaign)


@pytest.fixture
def env(tmp_path):
    """Classroom 2B copy without its arcs file, Aiko added, three turns logged, Day 5 morning (no milestone, no act start today)."""
    e = make_env(tmp_path)
    (e.data / "arcs.json").unlink(missing_ok=True)
    e.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "garden-bedroom", "--turn", "1", "--evidence", "test",
         "--background", "Grew up above a repair shop", "--power", "Mend")
    e.day(5)
    e.advance(3)
    return e


@pytest.fixture
def quiet(env):
    """A quiet turn: one scene open (talk, budget 4, 2 used), two housemates present."""
    env.ok("scene-start", "Kitchen supper", "--budget", 4, "--kind", "talk", "--turn", 3, "--evidence", "test")
    env.edit("state", lambda s: s["scene"].update(turns_used=2))
    return env


def lines_with(out, start):
    return [ln for ln in out if ln.startswith(start)]


def has(out, start):
    return bool(lines_with(out, start))


# ---- the quiet turn: short, footer, nothing due --------------------------------------------------------------------------
def test_quiet_turn_is_short_and_has_only_the_expected_lines(quiet):
    out = quiet.brief(paste=PASTE)
    assert len(out) <= 13, "\n".join(out)  # the campaign line plus about twelve
    text = "\n".join(out)
    assert out[0].startswith("==") and "classroom-2b" in out[0]
    assert "Turn 3 (next 4), Day 5 Wednesday (Act 1)" in text and 'scene "Kitchen supper" 2/4 turns, talk' in text
    assert has(out, "Present: Tatsuya Ōmine")
    for absent in ("Due:", "Canon traps:", "Promises:", "Questions", "Variety:", "Studio:", "WARN"):
        assert not has(out, absent), (absent, text)
    assert all(f in text for f in FOOTER)
    assert len(lines_with(out, "Rules:")) == 1 and len([ln for ln in out if "Never state a PC's condition" in ln or "`Cut:`" in ln]) == 2


def test_no_scene_open_and_budget_states(env):
    assert "no scene open" in "\n".join(env.brief(paste=PASTE))
    env.ok("scene-start", "Supper", "--budget", 2, "--turn", 3, "--evidence", "test")
    assert "0/2 turns" in "\n".join(env.brief()) and "budget" not in lines_with(env.brief(), "Turn")[0]
    env.edit("state", lambda s: s["scene"].update(turns_used=2))
    assert "2/2 turns (AT budget)" in "\n".join(env.brief())
    env.edit("state", lambda s: s["scene"].update(turns_used=4))
    assert "4/2 turns (OVER budget by 2)" in "\n".join(env.brief())


def test_time_inferred_and_split_party_tags(env):
    env.edit("state", lambda s: s.update(time_inferred=True, party_split=True))
    head = lines_with(env.brief(), "Turn")[0]
    assert "(time inferred)" in head and head.endswith("party split")


# ---- present NPCs and the rotated gesture picks ----------------------------------------------------------------------------
def kit(env, who):
    return env.load("cast")[who]["expression"]["gestures"]


def test_present_npcs_get_one_rotated_gesture_for_at_most_two_spotlight_candidates(env):
    paste = "Tatsuya Ōmine, Mio Tachibana and Shin Asakura sit at the table with Kenji Arimura."
    line = lines_with(env.brief(paste=paste), "Present:")[0]
    for who in ("Tatsuya Ōmine", "Mio Tachibana", "Shin Asakura", "Kenji Arimura"):
        assert who in line
    picks = [who for who in ("Tatsuya Ōmine", "Mio Tachibana", "Shin Asakura", "Kenji Arimura") if f"{who} (" in line]
    assert len(picks) == 2 and sum(g in line for who in picks for g in kit(env, who)) == 2


def test_the_least_featured_present_npcs_are_the_spotlight_candidates(env):
    for n in (4, 5, 6):
        env.turn(n, "Tatsuya Ōmine jokes with Aiko")
    line = lines_with(env.brief(paste="Tatsuya Ōmine, Mio Tachibana and Shin Asakura."), "Present:")[0]
    assert "Tatsuya Ōmine (" not in line and "Mio Tachibana (" in line and "Shin Asakura (" in line


def test_the_pick_rotates_away_from_what_the_last_turns_used(env):
    g = kit(env, "Tatsuya Ōmine")
    first = lines_with(env.brief(paste="Tatsuya Ōmine waits."), "Present:")[0]
    assert g[0] in first
    env.edit("state", lambda s: s.setdefault("expression", {}).update({"Tatsuya Ōmine": {"recent": [[g[0]]], "cursor": 1}}))
    second = lines_with(env.brief(paste="Tatsuya Ōmine waits."), "Present:")[0]
    assert g[0] not in second and any(x in second for x in g[1:])


def test_a_present_npc_without_a_kit_is_named_only_and_a_planned_npc_is_tagged(env):
    line = lines_with(env.brief(paste="Jun Kurose watches while Tatsuya Ōmine waits."), "Present:")[0]
    assert "Jun Kurose [planned: intro_line once]" in line and "Jun Kurose [planned: intro_line once] (" not in line
    assert "Tatsuya Ōmine (" in line


def test_present_comes_from_scene_present_and_names_and_warns_on_a_bad_name(env):
    env.ok("scene-start", "Supper", "--budget", 3, "--turn", 3, "--evidence", "test")
    env.edit("state", lambda s: s["scene"].update(present=["Kenji Arimura"]))
    assert "Kenji Arimura" in lines_with(env.brief(), "Present:")[0]
    out = env.brief("--names", "Reiko,Nobody Atall")
    assert "Reiko Shimazu" in lines_with(out, "Present:")[0] and has(out, "WARN: --names: no NPC matches")
    env.edit("state", lambda s: s.update(scene=None))
    assert "nobody detected" in lines_with(env.brief(), "Present:")[0]


# ---- due ------------------------------------------------------------------------------------------------------------------
def test_clocks_due_and_overdue_but_not_future_ones(env):
    env.ok("clock-add", "Rent letter", "--due-day", 5, "--turn", 3, "--evidence", "t")
    env.ok("clock-add", "Old deadline", "--due-day", 4, "--turn", 3, "--evidence", "t")
    env.ok("clock-add", "Later", "--due-day", 9, "--turn", 3, "--evidence", "t")
    due = lines_with(env.brief(), "Due:")[0]
    assert 'clock "Rent letter" due today' in due and 'clock "Old deadline" overdue by 1 day' in due and "Later" not in due


def test_a_milestone_today_names_it_and_its_place_not_its_note(env):
    env.day(6)
    due = lines_with(env.brief(), "Due:")[0]
    assert "milestone Day 6-7: Placement tournament (Chikara Battle Arena)" in due and "Round 1" not in due
    env.day(8)
    assert "milestone" not in "\n".join(env.brief())


def test_the_day_turnover_hint_after_a_day_change(env):
    assert not has(env.brief(), "Due:")
    env.day(6)  # moved after the last logged turn (6 also holds a milestone)
    assert "day changed (Day 5 -> 6): run `db.py day-turnover`" in lines_with(env.brief(), "Due:")[0]
    env.turn(4)  # logged on Day 6; the day moved inside this last logged turn
    assert "day changed (Day 5 -> 6)" in lines_with(env.brief(), "Due:")[0]
    env.turn(5)
    assert "day changed" not in "\n".join(env.brief())


@pytest.fixture
def pv(env):
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore")
    env.ok("arc-plan", "--file", env.write("charter.json", json.dumps(CHARTER)))
    env.ok("arc-approve", "A1", "--lines-checked")
    env.op("arc-start", "A1", turn=3)
    return env


def test_arc_lines_midpoint_budget_and_130_percent(pv):
    assert not has(pv.brief(), "Due:")
    pv.advance(9)  # 6 of 10 turns used
    assert "arc A1 midpoint review due" in lines_with(pv.brief(), "Due:")[0]
    pv.advance(13)
    due = lines_with(pv.brief(), "Due:")[0]
    assert "arc A1 at 100% of budget" in due and "130%" not in due
    pv.advance(16)
    due = lines_with(pv.brief(), "Due:")[0]
    assert "arc A1 at 130% of budget: ask the user once" in due and "at 100%" not in due


def test_drift_asks_to_re_aim_and_contact_clears_it(pv):
    pv.edit("arcs", lambda d: d["arcs"][0].update(budget_turns=40))
    pv.advance(11)  # eight turns after the start, none with arc contact
    assert "arc A1 drifting (8 turns without contact): Re-aim?" in lines_with(pv.brief(), "Due:")[0]
    pv.turn(12, flag=True)
    assert "drifting" not in "\n".join(pv.brief())


def test_a_pivot_is_one_line_pointing_at_arc_pivot_and_never_an_off_ramp(pv):
    pv.edit("arcs", lambda d: d["arcs"][0].update(budget_turns=40))
    pv.ok("arc-offramps", "A1", "--file", pv.write("off.json", json.dumps(OFFRAMPS)))
    pv.op("pc-thread", "went to the net menders instead of the guild clerk", turn=4)
    pv.advance(7)
    out = pv.brief()
    text = "\n".join(out)
    assert "pivot detected: run `db.py arc-pivot`" in lines_with(out, "Due:")[0]
    for hidden in ("net menders", "tide", "Haru Ebisu", "rota", "first_move", "off-ramp"):
        assert hidden not in text, hidden
    assert not json.dumps(pv.load("arcs")["pc_threads"][0]["text"]) in text


# ---- canon traps, promises, questions, variety -------------------------------------------------------------------------------
def test_canon_traps_appear_for_present_names_and_places_only(env):
    out = env.brief(paste="Reiko Shimazu stands at the door of the sharehouse.")
    assert "vice principal" in lines_with(out, "Canon traps:")[0]
    assert not has(env.brief(paste=PASTE), "Canon traps:")  # Tatsuya and Mio match no trap
    assert "Shin uses surnames" in lines_with(env.brief("--names", "Shin"), "Canon traps:")[0]


def test_a_trap_without_match_terms_is_not_in_the_lean_brief_but_prep_keeps_it(tmp_path):
    e = make_env(tmp_path, "joestar")
    traps = json.loads((REPO / "campaigns" / "joestar" / "campaign.json").read_text(encoding="utf-8"))["canon_traps"]
    generic = next(t["text"] for t in traps if not t["match"])
    assert generic[:40] not in "\n".join(e.brief(paste="The crew sits quietly."))
    assert generic[:40] in e.ok("prep")


def test_traps_are_capped_and_counted(tmp_path):
    e = make_env(tmp_path, "joestar")
    out = e.brief(paste="Kaito Arashima, Kurokawa, Shun, Nobu and Reiko meet the students at the Academy by the Safehouse.")
    line = lines_with(out, "Canon traps:")[0]
    assert line.count(" | ") == 2 and "(+" in line and "more)" in line


def promise(env, subject, text, kind="promise", turn=3):
    env.ok("fact", subject, text, "--kind", kind, "--turn", turn, "--evidence", "said it")


def test_open_promises_for_present_npcs_or_places_at_most_three_and_not_paid(env):
    promise(env, "Mio Tachibana", "Mio promised to repay the kitchen fund by Friday.")
    promise(env, "Kenji Arimura", "Kenji owes Aiko a signed late slip.", "debt")
    out = env.brief(paste=PASTE)
    line = lines_with(out, "Promises:")[0]
    assert "promise: Mio promised" in line and "Kenji" not in line
    env.ok("fact-status", env.load("canon")["facts"][0]["id"], "paid", "--turn", 3, "--evidence", "paid")
    assert not has(env.brief(paste=PASTE), "Promises:")
    for i in range(4):
        promise(env, "Mio Tachibana", f"Mio will keep a secret number {i}.", "condition", 4)
    line = lines_with(env.brief(paste=PASTE), "Promises:")[0]
    assert line.count(" | ") == 2 and "(+1 more; `db.py promises`)" in line


def test_a_promise_about_a_named_place_counts(env):
    promise(env, "Chikara Academy", "The lab door stays unlocked for Aiko until Friday.", "condition")
    assert "lab door" in lines_with(env.brief(paste="Aiko walks into Chikara Academy."), "Promises:")[0]
    assert not has(env.brief(paste="Aiko stays at the kitchen table."), "Promises:")  # the PC stands in the sharehouse, not the academy


def test_open_questions_three_of_five_with_the_rest_counted(env):
    assert not has(env.brief(), "Questions")
    for i in range(5):
        env.op("question", f"Who left the note number {i}?", turn=3)
    line = lines_with(env.brief(), "Questions")[0]
    assert line.startswith("Questions (5):") and line.count(" | ") == 2 and "(+2 more)" in line
    env.ok("question-close", "q1", "--turn", 3, "--evidence", "settled")
    assert lines_with(env.brief(), "Questions")[0].startswith("Questions (4):")


def test_variety_line_only_when_flags_exist(env):
    for i, kind in enumerate(("talk", "talk", "talk"), 1):
        env.ok("scene-start", f"S{i}", "--budget", 2, "--kind", kind, "--turn", 3, "--evidence", "t")
        env.ok("scene-end", "--turn", 3)
    line = lines_with(env.brief(), "Variety:")[0]
    assert "three talk scenes in a row" in line
    env.ok("scene-start", "S4", "--budget", 2, "--kind", "fight", "--turn", 3, "--evidence", "t")
    env.ok("scene-end", "--turn", 3)
    assert not has(env.brief(), "Variety:")


# ---- Studio cues (D21) ----------------------------------------------------------------------------------------------------------
def studio_line(env, **kw):
    out = env.brief(**kw)
    got = lines_with(out, "Studio:")
    return got[0] if got else None


def test_no_studio_line_when_nothing_applies(env):
    assert studio_line(env) is None


def test_pending_studio_requests_are_listed(env):
    env.ok("studio-request", "--kind", "npc", "--target", "Corner Baker", "--text-file", env.write("r.txt", "Name: Corner Baker\nRole: baker"),
           "--turn", 3)
    assert 'pending S1 npc "Corner Baker"' in studio_line(env)
    env.ok("studio-done", "S1", "--turn", 3)
    assert studio_line(env) is None


def test_an_act_starting_lists_planned_quests_and_npcs_not_in_studio(env):
    env.edit("state", lambda s: s.update(day=7, weekday="Friday", act=1))  # act 2 starts tomorrow
    env.edit("cast", lambda c: c["Takumi Hoshino"].update(arc_beats={"act_1": "(none)", "act_2": "Joins the house as a partner"}))
    assert "act 2 starts, not yet in Studio: 1 NPC (Takumi Hoshino) and 1 quest (Midterm Marks)" in studio_line(env)
    env.edit("quests", lambda q: q["Midterm Marks"].update(in_studio=True))
    assert "act 2 starts, not yet in Studio: 1 NPC (Takumi Hoshino)" in studio_line(env) and "quest" not in studio_line(env)
    env.edit("cast", lambda c: c["Takumi Hoshino"].update(in_studio=True))
    assert studio_line(env) is None


def test_an_act_bundle_already_requested_is_not_listed_and_day_five_has_none(env):
    env.edit("state", lambda s: s.update(day=7, weekday="Friday"))
    assert "act 2 starts" in studio_line(env)
    env.ok("studio-request", "--kind", "quest", "--target", "Midterm Marks", "--text-file", env.write("q.txt", "Name: Midterm Marks\nGoal: pass."),
           "--turn", 3)
    assert "act 2 starts" not in (studio_line(env) or "")
    env.edit("state", lambda s: s.update(day=5, weekday="Wednesday"))
    assert "act 2 starts" not in (studio_line(env) or "") and "act 1 starts" not in (studio_line(env) or "")


def test_act_one_starts_on_day_one(tmp_path):
    e = make_env(tmp_path)
    line = [ln for ln in e.brief() if ln.startswith("Studio:")][0]
    assert "act 1 starts, not yet in Studio: 2 quests (Move-In Weekend, Ability and Pulse Tutorial)" in line


def test_a_planned_npc_whose_name_is_hidden_is_counted_but_not_named(env):
    env.ok("session-zero", "--tone", "warm", "--lines", "no harm to kids", "--veils", "gore")
    env.ok("arc-plan", "--file", env.write("charter.json", json.dumps(CHARTER)))  # antagonist Sōichi Tamaru, not yet on screen
    env.edit("state", lambda s: s.update(day=7, weekday="Friday"))
    env.edit("cast", lambda c: (c["Sōichi Tamaru"].update(arc_beats={"act_2": "The polite broker makes his offer"}),
                                c["Takumi Hoshino"].update(arc_beats={"act_2": "Joins the house"})))
    line = studio_line(env)
    assert "2 NPCs (Takumi Hoshino)" in line and "Tamaru" not in line and "Sōichi" not in line


def add_npc(env, name, turn=3):
    env.ok("add-npc", name, "--turn", turn, "--evidence", "Voyage showed them")


def test_an_npc_named_in_three_of_the_last_ten_turns_who_is_not_in_studio(env):
    add_npc(env, "Pip Baker")
    env.turn(4, "Aiko buys bread from Pip Baker")
    env.turn(5, "Aiko thanks Pip Baker")
    assert studio_line(env) is None
    env.turn(6, "Aiko helps Pip Baker carry crates")
    assert "recurring, not in Studio: Pip Baker (3 of 6 turns)" in studio_line(env)
    env.edit("cast", lambda c: c["Pip Baker"].update(in_studio=True))
    assert studio_line(env) is None


def test_a_recurring_main_npc_is_no_studio_cue(env):
    for n in (4, 5, 6, 7):
        env.turn(n, "Tatsuya Ōmine and Aiko cook")
    assert studio_line(env) is None


def test_the_recurrence_window_is_the_last_ten_turns(env):
    add_npc(env, "Pip Baker")
    for n in (4, 5, 6):
        env.turn(n, "Aiko meets Pip Baker")
    env.advance(16)
    assert studio_line(env) is None


def test_a_quest_started_in_play_that_is_not_in_studio(env):
    env.op("quest-start", "Gentle Hands", turn=3)
    assert 'quest started in play, not in Studio: "Gentle Hands"' in studio_line(env)
    env.edit("quests", lambda q: q["Gentle Hands"].update(in_studio=True))
    assert studio_line(env) is None
    env.edit("quests", lambda q: q["Gentle Hands"].update(in_studio=False))
    env.advance(14)  # a quest started long ago is no cue
    assert studio_line(env) is None


def test_areas_added_since_the_last_studio_area_request(env):
    env.ok("add-area", "Sakura Lane Sharehouse", "pantry-nook", "--desc", "A narrow pantry.", "--turn", 3, "--evidence", "Voyage showed it")
    assert "new areas, no Studio area request since: Sakura Lane Sharehouse/pantry-nook" in studio_line(env)
    env.ok("studio-request", "--kind", "area", "--target", "Pantry Nook", "--text-file", env.write("a.txt", "Pantry nook off the kitchen."), "--turn", 3)
    line = studio_line(env)
    assert "pending S1" in line and "new areas" not in line
    env.turn(4)
    env.ok("add-area", "Sakura Lane Sharehouse", "boot-room", "--desc", "Where shoes pile.", "--turn", 4, "--evidence", "Voyage showed it")
    assert "Sakura Lane Sharehouse/boot-room" in studio_line(env) and "pantry-nook" not in studio_line(env)


# ---- --full, read-only, hidden material -----------------------------------------------------------------------------------------
def no_planner(out):
    return "".join(ln for ln in out.splitlines(keepends=True) if not ln.startswith("planner: "))


def test_full_prints_prep_screen_unchanged(quiet):
    paste_file = quiet.write("p.txt", PASTE)
    full = quiet.ok("turn-brief", "--full", "--paste", paste_file, "--names", "Shin")
    prep = quiet.ok("prep", "--paste", paste_file, "--names", "Shin")
    # the brief may add a "planner: ..." line when real planner output waits on origin; the prep screen itself is unchanged
    assert no_planner(full) == prep and "LIVE CHECKLIST" in full and "PREP " in full
    assert no_planner(quiet.ok("turn-brief", "--full")) == quiet.ok("prep")


def test_the_command_writes_nothing(quiet):
    quiet.ok("question", "Who left the note?", "--turn", 3, "--evidence", "e")
    quiet.edit("state", lambda s: s["scene"].update(present=["Kenji Arimura"]))
    before = quiet.snapshot()
    for args in ((), ("--names", "Reiko,Shin"), ("--full",)):
        for paste in (None, PASTE, "Jun Kurose and Tatsuya Ōmine at the Pantry"):
            quiet.brief(*args, paste=paste)
    assert quiet.snapshot() == before  # no data file changed, none added (no scene.present or rotation write, no snapshot)
    st = quiet.load("state")
    assert st["scene"]["present"] == ["Kenji Arimura"] and not st.get("expression")


def test_missing_paste_file_is_an_error_and_unknown_option_is_refused(env):
    r = env.run("turn-brief", "--paste", str(env.tmp / "nope.txt"))
    assert r.returncode != 0 and "no such paste file" in r.stderr
    assert env.run("turn-brief", "--full", "Tatsuya").returncode != 0  # --full is a flag here, not prep's NAME option


def brief_text(e, paste):
    return "\n".join(e.brief(paste=paste))


def scan_clean(e, text):
    r = e.run("scan", e.write("out.txt", text))
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_hidden_material_with_arcs_ladders_and_off_ramps(pv):
    pv.edit("arcs", lambda d: d["arcs"][0].update(budget_turns=40))
    pv.ok("arc-offramps", "A1", "--file", pv.write("off.json", json.dumps(OFFRAMPS)))
    pv.op("pc-thread", "went to the net menders instead of the guild clerk", turn=4)
    pv.advance(10)
    pv.op("pc-thread", "keeps asking the net menders about the tide table", turn=10)
    pv.advance(11)
    pv.ok("clock-add", "Rent letter", "--due-day", 5, "--turn", 3, "--evidence", "t")
    pv.op("question", "Who left the note?", turn=3)
    text = brief_text(pv, "Tatsuya Ōmine, Mio Tachibana, Shin Asakura and Jun Kurose gather at Chikara Academy.")
    assert "pivot detected" in text and "drifting" in text
    scan_clean(pv, text)
    # a planted hidden term is caught by the same scan, so the check is not vacuous
    r = pv.run("scan", pv.write("bad.txt", text + "\nThe glass lantern is the key."))
    assert r.returncode != 0
    for secret in ("glass lantern", "Sōichi Tamaru", "Haru Ebisu", "polite broker", "Mio's secret", "took the money"):
        assert secret not in text


@pytest.mark.parametrize("campaign,paste", [
    ("classroom-2b", "Tatsuya Ōmine, Mio Tachibana, Shin Asakura and Jun Kurose wait at Chikara Academy."),
    ("joestar", "Kaito Arashima, Reiko, Nobu and Shun talk with Haruto Saionji at Club Lumière."),
    ("luxcellia", "Serika Amamiya and Suzuha Sumeragi wait at the palace."),
])
def test_real_campaign_data_runs_clean_and_passes_the_scan(tmp_path, campaign, paste):
    e = make_env(tmp_path, campaign)
    before = e.snapshot()
    for args in ((), ("--names", "Kenji")):
        text = brief_text(e, paste) if not args else "\n".join(e.brief(*args, paste=paste))
        assert any(f in text for f in FOOTER[:1])
        scan_clean(e, text)
    scan_clean(e, "\n".join(e.brief()))
    assert e.snapshot() == before
