"""The state model of the revamp: inferred records (STATE-2), apparent quest ends (D7), open questions (STATE-4) and promises
(LOG-3, NPC-4). Every test runs on a tmp copy of the classroom-2b data (VOYAGE_DATA), never the real data.
No test asserts on the first line of an output: a campaign-name header line may come first."""
import fcntl
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
GOOD = ("Cut: Continue at Sakura Lane Sharehouse/shared-kitchen, Day 1 morning.\n"
        "Crew: Tatsuya Ōmine offers tea; others react in character.\n"
        "World: The House Manager posts the chore rota.")
QUEST = "Move-In Weekend"
QUOTE = "the House Manager hands out the chore rota"


class Env:
    def __init__(self, data, tmp):
        self.data, self.tmp = data, tmp

    def run(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("CLASS2B_TRIAL", "VOYAGE_TRIAL", "CLASS2B_DATA", "VOYAGE_DATA")}
        e.update({"VOYAGE_DATA": str(self.data), "VOYAGE_CAMPAIGN": "classroom-2b", "PYTHONDONTWRITEBYTECODE": "1"})
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args):
        r = self.run(*args)
        assert r.returncode == 0, r.stderr + r.stdout
        return r

    def up(self, cmd, *args, turn=1, evidence=QUOTE):
        """An update command with --turn and --evidence."""
        return self.run(cmd, *args, "--turn", turn, "--evidence", evidence)

    def load(self, name):
        return json.loads((self.data / f"{name}.json").read_text(encoding="utf-8"))

    def save_json(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def pc(self, name="Aiko Tanaka"):
        return next(p for p in self.load("state")["player_characters"] if p["name"] == name)

    def facts(self):
        return self.load("canon")["facts"]

    def quest(self, name=QUEST):
        return self.load("quests")[name]

    def mutable(self):
        return {n: (self.data / f"{n}.json").read_bytes() for n in ("state", "canon", "quests", "turns", "cast")}

    def hashes(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}

    def write(self, name, text):
        f = self.tmp / name
        f.write_text(text, encoding="utf-8")
        return f

    def payload(self, ops, turn=1, **extra):
        p = {"turn": turn, "ops": ops, "turn_log": {"inputs": "i", "summary": f"summary {turn}", "prompt": "Cut: a\nWorld: b"}, **extra}
        return self.write(f"payload{turn}.json", json.dumps(p))

    def commit(self, ops, turn=1, *args):
        p = {"turn": turn, "ops": ops, "turn_log": {"inputs": "i", "summary": f"summary {turn}"}}
        return self.run("commit-turn", "--prompt", self.write("prompt.txt", GOOD), "--payload",
                        self.write("cpayload.json", json.dumps(p)), *args)


@pytest.fixture
def env(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(REAL_DATA, data, ignore=shutil.ignore_patterns(".lock", "snapshots*", ".snap*"))
    return Env(data, tmp_path)


@pytest.fixture
def pc_env(env):
    env.ok("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom", "--turn", "1", "--evidence", "test")
    return env


MOVE = ("Sakura Lane Sharehouse", "shared-kitchen")


# ---- STATE-2: the inferred flag on position, time, quest start, fact ------------------------------
def test_pos_inferred_stores_flag_and_quote_on_the_pc(pc_env):
    assert "inferred" not in pc_env.pc() and "quote" not in pc_env.pc()
    pc_env.ok("pos", "Aiko", *MOVE, "--turn", "1", "--evidence", "Aiko walks into the kitchen", "--inferred")
    pc = pc_env.pc()
    assert pc["inferred"] is True and pc["quote"] == "Aiko walks into the kitchen"
    assert (pc["location"], pc["area"]) == MOVE


def test_pos_without_inferred_clears_the_flag_and_adds_nothing(pc_env):
    pc_env.ok("pos", "Aiko", *MOVE, "--turn", "1", "--evidence", "Aiko walks into the kitchen", "--inferred")
    pc_env.ok("pos", "Aiko", "Sakura Lane Sharehouse", "garden-bedroom", "--turn", "1", "--evidence", "the output says she is in the garden room")
    assert "inferred" not in pc_env.pc() and "quote" not in pc_env.pc()
    assert set(pc_env.pc()) == {"name", "player", "room", "location", "area", "activity", "placement", "pronouns", "power", "background", "notes"}


def test_time_inferred_stores_flag_and_quote_on_the_state_and_a_later_time_clears_it(env):
    env.ok("time", "--block", "Morning", "--turn", "1", "--evidence", "sunlight in the kitchen", "--inferred")
    st = env.load("state")
    assert st["time_inferred"] is True and st["time_quote"] == "sunlight in the kitchen" and st["time_block"] == "Morning"
    env.ok("time", "--block", "Afternoon", "--turn", "1", "--evidence", "the clock on the wall says two")
    st = env.load("state")
    assert "time_inferred" not in st and "time_quote" not in st and st["time_block"] == "Afternoon"


def test_quest_start_inferred_stores_flag_and_quote_on_the_quest(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "the rota is the move-in task", "--inferred")
    q = env.quest()
    assert q["status"] == "active" and q["started_turn"] == 1 and q["inferred"] is True and q["quote"] == "the rota is the move-in task"
    assert QUEST in env.load("state")["active_quests"]


def test_plain_quest_start_has_no_flag_and_inferred_start_cannot_repeat(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "stated in the output")
    assert "inferred" not in env.quest() and "quote" not in env.quest()
    r = env.up("quest-start", QUEST, "--inferred")
    assert r.returncode == 1 and "already active" in r.stderr


def test_quest_start_without_inferred_confirms_an_inferred_start(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "the rota is the move-in task", "--inferred")
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "the output names the quest")
    q = env.quest()
    assert "inferred" not in q and "quote" not in q and q["status"] == "active" and q["started_turn"] == 1
    assert q["log"][-1]["event"] == "start confirmed"
    assert env.up("quest-start", QUEST).returncode == 1  # a plain active quest still cannot be started again


def test_fact_inferred_stores_flag_and_quote_and_a_plain_fact_is_unchanged(env):
    env.ok("fact", "Tatsuya", "keeps", "his", "tea", "tin", "locked", "--turn", "1", "--evidence", "tin clicks shut", "--inferred")
    env.ok("fact", "Mio", "counts", "coins", "--turn", "1", "--evidence", "coins on the table")
    a, b = env.facts()
    assert a["inferred"] is True and a["quote"] == "tin clicks shut" and a["fact"] == "keeps his tea tin locked"
    assert set(b) == {"id", "turn", "subject", "fact", "evidence"}  # a fact without the new options has exactly the old shape


# ---- D7: quest-end in inferred form ---------------------------------------------------------------
def test_quest_end_inferred_notes_the_apparent_end_and_leaves_the_status(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "started")
    before = env.quest()
    r = env.ok("quest-end", QUEST, "--inferred", "--turn", "1", "--evidence", "everyone is placed, the weekend is over")
    q = env.quest()
    assert q["apparent_end"] == {"turn": 1, "quote": "everyone is placed, the weekend is over"}
    assert q["status"] == "active" and q["ended_turn"] == before["ended_turn"]
    assert QUEST in env.load("state")["active_quests"]
    assert q["log"][-1]["event"].startswith("apparent end")


def test_quest_end_inferred_replaces_an_earlier_note_and_refuses_an_ended_quest(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "started")
    env.ok("quest-end", QUEST, "--inferred", "--turn", "1", "--evidence", "first guess")
    r = env.ok("quest-end", QUEST, "--inferred", "--turn", "1", "--evidence", "second guess")
    assert env.quest()["apparent_end"]["quote"] == "second guess" and "replaces the note from turn 1" in r.stdout
    env.ok("quest-end", QUEST, "completed", "--turn", "1", "--evidence", "legacy end")
    r = env.up("quest-end", QUEST, "--inferred")
    assert r.returncode == 1 and "already completed" in r.stderr


def test_quest_end_inferred_refuses_a_result_and_the_legacy_form_needs_one(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "started")
    r = env.up("quest-end", QUEST, "completed", "--inferred")
    assert r.returncode == 2 and "takes no result" in r.stderr
    r = env.up("quest-end", QUEST)
    assert r.returncode == 2 and "completed|failed" in r.stderr
    assert "apparent_end" not in env.quest() and env.quest()["status"] == "active"


def test_legacy_quest_end_still_sets_the_status(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "started")
    env.ok("quest-end", QUEST, "failed", "--turn", "1", "--evidence", "the weekend collapses")
    q = env.quest()
    assert q["status"] == "failed" and q["ended_turn"] == 1 and "apparent_end" not in q
    assert QUEST not in env.load("state")["active_quests"]


def test_quest_lookup_shows_the_inferred_start_and_the_apparent_end(env):
    env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "the rota is the move-in task", "--inferred")
    env.ok("quest-end", QUEST, "--inferred", "--turn", "1", "--evidence", "the weekend is over")
    out = env.ok("quest", QUEST).stdout
    assert "apparent end: turn 1, inferred (status unchanged)" in out and "inferred: start, from: the rota is the move-in task" in out


# ---- STATE-4: open questions ----------------------------------------------------------------------
def test_question_adds_an_open_question_with_id_turn_text_evidence(env):
    assert "open_questions" not in env.load("state")
    env.ok("question", "Who", "owns", "the", "locked", "box?", "--turn", "1", "--evidence", "Mio eyes the box")
    env.ok("question", "Is the manager lying?", "--turn", "1", "--evidence", "her smile slips")
    qs = env.load("state")["open_questions"]
    assert qs[0] == {"id": "q1", "turn": 1, "text": "Who owns the locked box?", "evidence": "Mio eyes the box", "status": "open"}
    assert qs[1]["id"] == "q2" and qs[1]["status"] == "open"
    assert any(c["cmd"] == "question" for c in env.load("state")["changelog"])


def test_question_close_closes_it_and_ids_are_not_reused(env):
    env.ok("question", "Who owns the box?", "--turn", "1", "--evidence", "e1")
    env.ok("question", "Is the manager lying?", "--turn", "1", "--evidence", "e2")
    env.ok("question-close", "q1", "--turn", "1", "--evidence", "Mio says it is hers")
    q1, q2 = env.load("state")["open_questions"]
    assert q1["status"] == "closed" and q1["closed_turn"] == 1 and q1["close_evidence"] == "Mio says it is hers" and q2["status"] == "open"
    env.ok("question-close", "2", "--turn", "1", "--evidence", "bare numbers work")  # q2
    env.ok("question", "A third one?", "--turn", "1", "--evidence", "e3")
    assert [q["id"] for q in env.load("state")["open_questions"]] == ["q1", "q2", "q3"]


def test_question_close_refuses_unknown_and_already_closed_and_empty_text(env):
    env.ok("question", "Who owns the box?", "--turn", "1", "--evidence", "e1")
    r = env.up("question-close", "q9")
    assert r.returncode == 2 and 'no question "q9"' in r.stderr and "open: q1" in r.stderr
    env.ok("question-close", "q1", "--turn", "1", "--evidence", "answered")
    r = env.up("question-close", "q1")
    assert r.returncode == 1 and "already closed" in r.stderr
    r = env.up("question", "   ")
    assert r.returncode == 2 and "must not be empty" in r.stderr
    assert env.up("question", "A question", evidence="  ").returncode == 1  # evidence is required


def test_question_cannot_come_from_a_turn_that_has_not_happened(env):
    r = env.up("question", "Too early?", turn=5)
    assert r.returncode == 1 and "ahead of the log" in r.stderr
    assert "open_questions" not in env.load("state")


def test_state_prints_the_open_question_count_and_lists_them(env):
    assert "Open questions (director notes): 0" in env.ok("state").stdout
    env.ok("question", "Who owns the box?", "--turn", "1", "--evidence", "e1")
    env.ok("question", "Is the manager lying?", "--turn", "1", "--evidence", "e2")
    env.ok("question-close", "q1", "--turn", "1", "--evidence", "answered")
    out = env.ok("state").stdout
    assert "Open questions (director notes): 1" in out
    assert "- q2 (turn 1): Is the manager lying?" in out and "- q1 (turn" not in out  # q1 is closed, so it is not listed


def test_state_shows_which_items_are_inferred_and_prints_nothing_when_none_are(pc_env):
    assert "Inferred" not in pc_env.ok("state").stdout
    pc_env.ok("pos", "Aiko", *MOVE, "--turn", "1", "--evidence", "e", "--inferred")
    pc_env.ok("time", "--block", "Morning", "--turn", "1", "--evidence", "e", "--inferred")
    pc_env.ok("quest-start", QUEST, "--turn", "1", "--evidence", "e", "--inferred")
    pc_env.ok("fact", "Mio", "owes", "rent", "--turn", "1", "--evidence", "e", "--inferred")
    pc_env.ok("quest-end", QUEST, "--inferred", "--turn", "1", "--evidence", "e")
    line = next(ln for ln in pc_env.ok("state").stdout.splitlines() if ln.startswith("Inferred"))
    for part in ("time", "position Aiko Tanaka", f"quest start {QUEST}", f"apparent end of {QUEST}", "facts f"):
        assert part in line
    pc_env.ok("pos", "Aiko", *MOVE, "--turn", "1", "--evidence", "e")  # a plain update drops the position from the line
    assert "position" not in next(ln for ln in pc_env.ok("state").stdout.splitlines() if ln.startswith("Inferred"))


# ---- LOG-3, NPC-4: promises ---------------------------------------------------------------------
def test_fact_with_a_kind_defaults_to_open_and_takes_a_status(env):
    env.ok("fact", "Ren", "promised", "tea", "--kind", "promise", "--turn", "1", "--evidence", "I will bring tea")
    env.ok("fact", "Sam", "owes", "rent", "--kind", "debt", "--status", "paid", "--turn", "1", "--evidence", "paid up")
    env.ok("fact", "Plain", "fact", "--turn", "1", "--evidence", "e")
    a, b, c = env.facts()
    assert (a["kind"], a["status"]) == ("promise", "open") and (b["kind"], b["status"]) == ("debt", "paid")
    assert "kind" not in c and "status" not in c


def test_fact_refuses_a_status_without_a_kind_and_an_unknown_kind_or_status(env):
    r = env.up("fact", "S", "text", "--status", "paid")
    assert r.returncode == 2 and "needs --kind" in r.stderr
    for bad in (("--kind", "ledger"), ("--kind", "promise", "--status", "done")):
        r = env.up("fact", "S", "text", *bad)
        assert r.returncode == 2 and "invalid choice" in r.stderr
    assert env.facts() == []


def test_promises_lists_open_facts_with_a_kind_by_default(env):
    env.ok("fact", "Ren", "promised", "tea", "--kind", "promise", "--turn", "1", "--evidence", "e")
    env.ok("fact", "Sam", "owes", "rent", "--kind", "debt", "--status", "paid", "--turn", "1", "--evidence", "e")
    env.ok("fact", "Gate", "opens", "after", "six", "--kind", "condition", "--turn", "1", "--evidence", "e", "--inferred")
    env.ok("fact", "Plain", "no", "kind", "--turn", "1", "--evidence", "e")
    out = env.ok("promises").stdout
    assert "Open promises, conditions, debts and plants: 2" in out
    assert "f001 [promise, open] turn 1 | Ren: promised tea" in out
    assert "f003 [condition, open] turn 1, inferred | Gate: opens after six" in out
    assert "f002" not in out and "Plain" not in out
    allout = env.ok("promises", "--all").stdout
    assert "f002 [debt, paid]" in allout and "1 paid" in allout and "Plain" not in allout
    only = env.ok("promises", "--kind", "debt", "--all").stdout
    assert "f002" in only and "f001" not in only
    assert "none" in env.ok("promises", "--kind", "plant").stdout
    assert env.run("promises", "--kind", "ledger").returncode == 2


def test_promises_is_read_only(env):
    before = env.hashes()
    env.ok("promises", "--all")
    assert env.hashes() == before


def test_fact_status_marks_a_fact_paid_and_open_again(env):
    env.ok("fact", "Ren", "promised", "tea", "--kind", "promise", "--turn", "1", "--evidence", "e")
    env.ok("fact-status", "f001", "paid", "--turn", "1", "--evidence", "Ren sets down the tea")
    f = env.facts()[0]
    assert f["status"] == "paid" and f["status_turn"] == 1 and f["status_evidence"] == "Ren sets down the tea"
    assert "Open promises, conditions, debts and plants: 0" in env.ok("promises").stdout
    env.ok("fact-status", "F1", "open", "--turn", "1", "--evidence", "it was a different tea")  # id forms: F1, 1 and f001 all match
    assert env.facts()[0]["status"] == "open"
    env.ok("fact-status", "1", "paid", "--turn", "1", "--evidence", "e")
    assert env.facts()[0]["status"] == "paid"


def test_fact_status_refuses_an_unknown_id_a_fact_without_a_kind_and_a_bad_status(env):
    env.ok("fact", "Plain", "fact", "--turn", "1", "--evidence", "e")
    r = env.up("fact-status", "f099", "paid")
    assert r.returncode == 2 and 'no fact "f099"' in r.stderr
    r = env.up("fact-status", "f001", "paid")
    assert r.returncode == 2 and "has no kind" in r.stderr
    r = env.up("fact-status", "f001", "done")
    assert r.returncode == 2 and "invalid choice" in r.stderr
    assert "status" not in env.facts()[0]


def test_fact_status_takes_the_inferred_flag_and_a_plain_one_clears_it(env):
    env.ok("fact", "Ren", "promised", "tea", "--kind", "promise", "--turn", "1", "--evidence", "e", "--inferred")
    env.ok("fact-status", "f001", "paid", "--turn", "1", "--evidence", "the tea seems to arrive", "--inferred")
    f = env.facts()[0]
    assert f["inferred"] is True and f["quote"] == "the tea seems to arrive"
    env.ok("fact-status", "f001", "paid", "--turn", "1", "--evidence", "Ren says: here is your tea")
    f = env.facts()[0]
    assert "inferred" not in f and "quote" not in f


def test_canon_search_tags_a_fact_with_its_kind_status_and_inferred_flag(env):
    env.ok("fact", "Ren", "promised", "tea", "--kind", "promise", "--turn", "1", "--evidence", "e", "--inferred")
    env.ok("fact", "Ren", "likes", "tea", "--turn", "1", "--evidence", "e")
    out = env.ok("canon", "tea").stdout
    assert "(turn 1) [promise, open, inferred] Ren: promised tea" in out and "(turn 1) Ren: likes tea" in out


# ---- record and commit-turn: the new ops ---------------------------------------------------------
def all_ops():
    return [
        {"op": "pos", "args": {"pc": "Aiko", "location": MOVE[0], "area": MOVE[1], "inferred": True}, "evidence": "Aiko enters the kitchen"},
        {"op": "time", "args": {"block": "Morning", "inferred": True}, "evidence": "morning light"},
        {"op": "quest-start", "args": {"name": QUEST, "inferred": True}, "evidence": "the rota is the task"},
        {"op": "quest-end", "args": {"name": QUEST, "inferred": True}, "evidence": "the weekend seems over"},
        {"op": "fact", "args": {"subject": "Ren", "text": "promised tea", "kind": "promise", "inferred": True}, "evidence": "I will bring tea"},
        {"op": "fact", "args": {"subject": "Gate", "text": "opens after six", "kind": "condition", "status": "open"}, "evidence": "after six"},
        {"op": "fact-status", "args": {"id": "f002", "status": "paid"}, "evidence": "the gate opens"},
        {"op": "question", "args": {"text": "Who owns the box?"}, "evidence": "Mio eyes the box"},
        {"op": "question", "args": {"text": "Is the manager lying?"}, "evidence": "her smile slips"},
        {"op": "question-close", "args": {"id": "q1"}, "evidence": "Mio says it is hers"},
    ]


def check_new_state(env):
    st = env.load("state")
    pc = next(p for p in st["player_characters"] if p["name"] == "Aiko Tanaka")
    assert pc["inferred"] is True and pc["quote"] == "Aiko enters the kitchen"
    assert st["time_inferred"] is True and st["time_quote"] == "morning light" and st["time_block"] == "Morning"
    q = env.quest()
    assert q["inferred"] is True and q["quote"] == "the rota is the task" and q["status"] == "active"
    assert q["apparent_end"] == {"turn": 1, "quote": "the weekend seems over"}
    f1, f2 = env.facts()
    assert f1["kind"] == "promise" and f1["status"] == "open" and f1["inferred"] is True
    assert f2["kind"] == "condition" and f2["status"] == "paid" and "inferred" not in f2
    assert [(x["id"], x["status"]) for x in st["open_questions"]] == [("q1", "closed"), ("q2", "open")]


def test_record_applies_the_new_ops(pc_env):
    r = pc_env.ok("record", pc_env.payload(all_ops()))
    assert "record turn 1: ok" in r.stdout
    check_new_state(pc_env)


def test_record_dry_run_plans_the_new_ops_and_writes_nothing(pc_env):
    before = pc_env.hashes()
    r = pc_env.ok("record", pc_env.payload(all_ops()), "--dry-run")
    assert "dry run OK" in r.stdout and "question-close" in r.stdout and "fact-status" in r.stdout
    assert pc_env.hashes() == before


def test_commit_turn_applies_the_new_ops(pc_env):
    r = pc_env.commit(all_ops())
    assert r.returncode == 0, r.stderr + r.stdout
    assert "commit-turn 1: ok" in r.stdout
    check_new_state(pc_env)


def test_undo_turn_rewinds_the_new_fields_after_record(pc_env):
    before = pc_env.mutable()
    pc_env.ok("record", pc_env.payload(all_ops()))
    assert pc_env.mutable() != before
    assert (pc_env.data / ".snapshots" / "before-turn-1").is_dir()
    for name in ("state", "canon", "quests"):  # the snapshot covers every file the new fields live in
        assert (pc_env.data / ".snapshots" / "before-turn-1" / f"{name}.json").is_file()
    pc_env.ok("undo-turn", 1)
    assert pc_env.mutable() == before
    st = pc_env.load("state")
    assert "open_questions" not in st and "time_inferred" not in st and "inferred" not in pc_env.pc()
    assert pc_env.facts() == [] and "apparent_end" not in pc_env.quest() and pc_env.quest()["status"] == "planned"


def test_undo_turn_rewinds_the_new_fields_after_commit_turn(pc_env):
    before = pc_env.mutable()
    r = pc_env.commit(all_ops())
    assert r.returncode == 0, r.stderr + r.stdout
    pc_env.ok("undo-turn", 1)
    assert pc_env.mutable() == before


def test_the_ops_see_each_other_inside_one_payload(pc_env):
    ops = [{"op": "fact", "args": {"subject": "Ren", "text": "promised tea", "kind": "promise"}, "evidence": "e"},
           {"op": "fact-status", "args": {"id": "f001", "status": "paid"}, "evidence": "e"},
           {"op": "question", "args": {"text": "Why?"}, "evidence": "e"},
           {"op": "question-close", "args": {"id": "q1"}, "evidence": "e"}]
    pc_env.ok("record", pc_env.payload(ops))
    assert pc_env.facts()[0]["status"] == "paid" and pc_env.load("state")["open_questions"][0]["status"] == "closed"


def test_record_validates_the_args_of_the_new_ops_and_writes_nothing(pc_env):
    before = pc_env.hashes()
    bad = [
        [{"op": "question", "args": {}, "evidence": "e"}],  # missing text
        [{"op": "question-close", "args": {"id": "q4"}, "evidence": "e"}],  # unknown question
        [{"op": "fact-status", "args": {"id": "f001", "status": "paid"}, "evidence": "e"}],  # unknown fact
        [{"op": "fact", "args": {"subject": "S", "text": "t", "kind": "ledger"}, "evidence": "e"}],  # unknown kind
        [{"op": "fact", "args": {"subject": "S", "text": "t", "status": "paid"}, "evidence": "e"}],  # status without kind
        [{"op": "pos", "args": {"pc": "Aiko", "location": MOVE[0], "area": MOVE[1], "inferred": "yes"}, "evidence": "e"}],  # not a bool
        [{"op": "quest-end", "args": {"name": QUEST, "inferred": True, "result": "failed"}, "evidence": "e"}],
        [{"op": "quest-end", "args": {"name": QUEST}, "evidence": "e"}],
        [{"op": "question", "args": {"text": "ok"}, "evidence": "e"}, {"op": "question", "args": {"text": "x", "extra": 1}, "evidence": "e"}],
    ]
    for ops in bad:
        r = pc_env.run("record", pc_env.payload(ops))
        assert r.returncode != 0 and "Nothing applied" in r.stderr + r.stdout, ops
        assert pc_env.hashes() == before, ops
    r = pc_env.run("record", pc_env.payload([{"op": "pos", "args": {"pc": "Aiko", "location": MOVE[0], "area": MOVE[1], "inferred": "yes"}}]))
    assert "'inferred' must be true or false" in r.stderr


def test_commit_turn_lists_every_problem_at_once_and_writes_nothing(pc_env):
    before = pc_env.hashes()
    ops = [
        {"op": "question", "args": {}, "evidence": "e"},
        {"op": "question-close", "args": {"id": "q4"}, "evidence": "e"},
        {"op": "fact-status", "args": {"id": "f077", "status": "paid"}, "evidence": "e"},
        {"op": "fact", "args": {"subject": "S", "text": "t", "kind": "ledger"}, "evidence": "e"},
        {"op": "time", "args": {"block": "Morning", "inferred": "yes"}, "evidence": "e"},
        {"op": "quest-end", "args": {"name": QUEST}, "evidence": "e"},
        {"op": "question", "args": {"text": "A fine question"}, "evidence": "e"},  # a good op among the bad ones is not blamed
    ]
    r = pc_env.commit(ops)
    out = r.stdout
    assert r.returncode == 2 and "6 problem(s), nothing written" in out
    for part in ("missing arg 'text'", 'no question "q4"', 'no fact "f077"', "invalid choice", "'inferred' must be true or false",
                 "completed|failed"):
        assert part in out, part
    assert pc_env.hashes() == before


def test_commit_turn_dry_run_plans_the_new_ops_and_writes_nothing(pc_env):
    before = pc_env.hashes()
    r = pc_env.commit(all_ops(), 1, "--dry-run")
    assert r.returncode == 0 and "dry run OK" in r.stdout and "nothing written" in r.stdout
    assert pc_env.hashes() == before


def test_a_payload_without_the_new_options_still_records_the_old_shapes(pc_env):
    ops = [{"op": "fact", "args": {"subject": "Ren", "text": "likes tea"}, "evidence": "e"},
           {"op": "pos", "args": {"pc": "Aiko", "location": MOVE[0], "area": MOVE[1]}, "evidence": "e"},
           {"op": "time", "args": {"block": "Morning"}, "evidence": "e"},
           {"op": "quest-start", "args": {"name": QUEST}, "evidence": "e"},
           {"op": "quest-end", "args": {"name": QUEST, "result": "completed"}, "evidence": "e"}]
    pc_env.ok("record", pc_env.payload(ops))
    st = pc_env.load("state")
    assert set(pc_env.facts()[0]) == {"id", "turn", "subject", "fact", "evidence"}
    assert "inferred" not in pc_env.pc() and "time_inferred" not in st and "open_questions" not in st
    assert pc_env.quest()["status"] == "completed" and "inferred" not in pc_env.quest() and "apparent_end" not in pc_env.quest()


# ---- locks ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("cmd", [["question", "Locked out?"], ["question-close", "q1"], ["fact-status", "f001", "paid"],
                                 ["fact", "S", "t", "--kind", "promise"], ["quest-end", QUEST, "--inferred"],
                                 ["pos", "Aiko", *MOVE, "--inferred"], ["time", "--block", "Morning", "--inferred"]])
def test_the_write_commands_take_the_lock(pc_env, cmd):
    before = pc_env.hashes()
    fd = os.open(pc_env.data / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = pc_env.run(*cmd, "--turn", "1", "--evidence", "e")
        assert r.returncode == 6 and "another write is in progress" in r.stderr
        assert pc_env.ok("promises").returncode == 0  # reads never lock
    finally:
        os.close(fd)
    assert pc_env.hashes() == before


# ---- verify_data -----------------------------------------------------------------------------------
def test_verify_accepts_old_data_without_the_new_fields(env):
    r = env.ok("wrap-up")
    assert "safe to close" in r.stdout


def test_verify_accepts_every_new_field_when_well_formed(pc_env):
    pc_env.ok("record", pc_env.payload(all_ops()))
    r = pc_env.ok("wrap-up")
    assert "safe to close" in r.stdout


def corrupt(env):
    st, canon, quests = env.load("state"), env.load("canon"), env.load("quests")
    canon["facts"] = [
        {"id": "f001", "turn": 1, "subject": "a", "fact": "b", "evidence": "c", "kind": "ledger", "status": "open"},
        {"id": "f002", "turn": 1, "subject": "a", "fact": "b", "evidence": "c", "kind": "promise", "status": "done"},
        {"id": "f003", "turn": 1, "subject": "a", "fact": "b", "evidence": "c", "inferred": "yes"},
        {"id": "f004", "turn": 1, "subject": "a", "fact": "b", "evidence": "c", "inferred": True, "quote": 5},
    ]
    st["open_questions"] = [{"id": "q1", "turn": 1, "text": "ok", "status": "maybe"},
                            {"id": "q1", "turn": "x", "text": "", "status": "open"}, "not an object"]
    st["time_inferred"] = 1
    quests[QUEST]["inferred"] = "true"
    quests[QUEST]["apparent_end"] = {"turn": "one"}
    env.save_json("state", st)
    env.save_json("canon", canon)
    env.save_json("quests", quests)


def test_verify_rejects_malformed_fields_and_lists_every_problem(pc_env):
    corrupt(pc_env)
    r = pc_env.run("wrap-up")
    assert r.returncode == 1 and "not safe to close" in r.stderr
    for part in ("fact f001: kind 'ledger' is not one of promise, condition, debt, plant",
                 "fact f002: status 'done' is not one of open, paid", "fact f003: inferred must be true or false",
                 "fact f004: quote must be text", "open_questions #1: status 'maybe' is not one of open, closed",
                 "open_questions #2: duplicate id q1", "open_questions #2: turn must be an integer",
                 "open_questions #2: text must be non-empty text", "open_questions #3: must be an object",
                 "state.json time: time_inferred must be true or false", f"quests.json {QUEST}: inferred must be true or false",
                 f"quests.json {QUEST}: apparent_end must be an object with turn (integer) and quote (text)"):
        assert part in r.stderr, part


def test_verify_rejects_a_duplicate_question_id_and_a_non_list(pc_env):
    st = pc_env.load("state")
    st["open_questions"] = [{"id": "q1", "turn": 1, "text": "a", "status": "open"}, {"id": "q1", "turn": 1, "text": "b", "status": "open"}]
    pc_env.save_json("state", st)
    assert "duplicate id q1" in pc_env.run("wrap-up").stderr
    st["open_questions"] = {"q1": "x"}
    pc_env.save_json("state", st)
    assert "open_questions must be a list" in pc_env.run("wrap-up").stderr


def test_record_rolls_back_when_verification_finds_bad_data(pc_env):
    corrupt(pc_env)
    before = pc_env.mutable()
    r = pc_env.run("record", pc_env.payload([{"op": "question", "args": {"text": "Why?"}, "evidence": "e"}]))
    assert r.returncode == 1 and "verification failed" in r.stderr and "Restored the pre-turn snapshot" in r.stderr
    assert pc_env.mutable() == before
