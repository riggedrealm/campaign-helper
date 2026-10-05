"""`db.py sync EXPORT [--apply]` (SYNC-1 to SYNC-8, D15, D19, STATE-2): Voyage's exported state against the database.
Every test builds a small synthetic save of the shape the tool reads (engineState.ticks, partyState.day / timeOfDay / partyMembers /
currentLocation / currentArea, a quest list, turnData with playerInputs and stories) in a tmp folder and runs sync on a tmp copy of the
classroom-2b campaign (VOYAGE_ROOT for campaign.json, VOYAGE_DATA for the data). No test opens a real world file or export, and no
test asserts on the first line of an output: a campaign line comes first."""
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "tools" / "db.py"
CAMPAIGN = "classroom-2b"
HOME_LOC, HOME_AREA = "Sakura Lane Sharehouse", "building-entrance"
OTHER_LOC, OTHER_AREA = "Midnight Diner", "counter"
QUEST = "Move-In Weekend"
QUEST2 = "Midterm Marks"
QUEST3 = "Final Review"
LOG_KEYS = ["turn", "at", "tick", "mismatches", "applied"]
MISMATCH_KEYS = ["position", "time", "quest", "party", "drift"]
MUTABLE = ("state", "canon", "cast", "quests", "turns", "locations", "world-npcs", "threads")


class Env:
    def __init__(self, tmp):
        self.tmp = tmp
        self.root = tmp / "root"
        shutil.copytree(REPO / "campaigns" / CAMPAIGN, self.root / "campaigns" / CAMPAIGN,
                        ignore=shutil.ignore_patterns(".lock", ".snapshots", "snapshots*", "*.tmp"))
        self.real = self.root / "campaigns" / CAMPAIGN / "data"   # what a run without VOYAGE_DATA writes to
        self.data = tmp / "data"                                   # the VOYAGE_DATA copy every other test works on
        shutil.copytree(self.real, self.data)
        self.n = 0

    def run(self, *args, env=None, data=True):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
        e.update({"VOYAGE_ROOT": str(self.root), "VOYAGE_CAMPAIGN": CAMPAIGN, "PYTHONDONTWRITEBYTECODE": "1"})
        if data:
            e["VOYAGE_DATA"] = str(self.data)
        e.update(env or {})
        return subprocess.run([sys.executable, str(DB), *map(str, args)], capture_output=True, text=True, env=e, cwd=self.tmp)

    def ok(self, *args, **kw):
        r = self.run(*args, **kw)
        assert r.returncode == 0, r.stderr + r.stdout
        return r

    def up(self, cmd, *args, turn=1, evidence="setup quote"):
        return self.ok(cmd, *args, "--turn", turn, "--evidence", evidence)

    def load(self, name, where=None):
        return json.loads(((where or self.data) / f"{name}.json").read_text(encoding="utf-8"))

    def dump(self, name, obj):
        (self.data / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def files(self, where=None):
        d = where or self.data
        return {p.name: p.read_bytes() for p in sorted(d.glob("*.json"))}

    def mutable(self):
        return {n: (self.data / f"{n}.json").read_bytes() for n in MUTABLE}

    def logged(self, n):
        """state.turn = n with n director turns in turns.json."""
        st = self.load("state")
        st["turn"] = n
        self.dump("state", st)
        self.dump("turns", [{"turn": i, "day": 1, "time": "Dawn 05:00", "inputs": f"input {i}", "summary": f"summary {i}",
                             "prompt": f"prompt {i}", "slips": "", "notes": ""} for i in range(1, n + 1)])

    def pc(self, name="Aiko Tanaka"):
        return next(p for p in self.load("state")["player_characters"] if p["name"] == name)

    def export(self, save, name="export.json"):
        self.n += 1
        d = self.tmp / f"ex{self.n}"
        d.mkdir()
        f = d / name
        f.write_text(json.dumps(save), encoding="utf-8")
        return f


def make_save(tick=3, day=1, tod="Dawn", members=("Aiko Tanaka",), place=(HOME_LOC, HOME_AREA), quests=None, ticks=(), member_places=None):
    ps = {"day": day, "timeOfDay": tod,
          "partyMembers": [m if isinstance(m, dict) else {"name": m, **({"currentLocation": member_places[m][0], "currentArea": member_places[m][1]}
                                                                   if member_places and m in member_places else {})} for m in members]}
    if place:
        ps["currentLocation"], ps["currentArea"] = place
    save = {"engineState": {"ticks": tick}, "partyState": ps, "journalEvents": [], "storyStarts": {}, "npcs": {}, "locations": {},
            "turnData": [tick_entry(t) for t in ticks]}
    if quests is not None:
        save["quests"] = quests
    return save


def tick_entry(t, story=None):
    return {"tick": t, "playerInputs": {"Aiko": f"Aiko does thing {t}.\nThen waits.", "Ren": f"Ren answers {t}", "__dm__": f"Cut: prompt {t}"},
            "stories": story if story is not None else [f"Tick {t} story sentence one. Tick {t} story sentence two."]}


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    e.up("pc-add", "Aiko Tanaka", "--player", "Sam", "--room", "maple-bedroom")
    e.up("pos", "Aiko Tanaka", HOME_LOC, HOME_AREA)
    e.logged(3)
    return e


def sync_log(env):
    return env.load("state").get("sync_log", [])


def digests(env):
    return json.loads((env.data / "sync.json").read_text(encoding="utf-8"))


# ---- the dry run: the digest, the checksum and the log entry are the only writes ------------------------------------
def test_dry_run_writes_only_the_digest_and_the_log_entry(env):
    save = make_save(tick=3, members=("Aiko Tanaka",), quests={"q1": {"name": QUEST, "status": "active"}})
    f = env.export(save, "voyage-export.json")
    before, state0 = env.files(), env.load("state")
    r = env.ok("sync", f)
    after = env.files()
    assert set(after) - set(before) == {"sync.json"}
    for name, raw in before.items():
        if name != "state.json":
            assert after[name] == raw, f"{name} changed in a dry run"
    state1 = env.load("state")
    assert {k: v for k, v in state1.items() if k != "sync_log"} == {k: v for k, v in state0.items() if k != "sync_log"}
    assert "changelog" in state1 and state1["changelog"] == state0["changelog"]  # no changelog entry either
    # the digest: what it extracted, the checksum, the file name and the date; never the raw export
    d = digests(env)
    assert isinstance(d, list) and len(d) == 1
    d = d[0]
    assert d["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest() and d["file"] == "voyage-export.json"
    assert d["tick"] == 3 and d["day"] == 1 and d["time_block"] == "Dawn" and d["party"] == ["Aiko Tanaka"]
    assert d["positions"] == {"Aiko Tanaka": f"{HOME_LOC}/{HOME_AREA}"} and d["quests"] == {QUEST: "active"}
    assert re.fullmatch(r"\d{4}-\d\d-\d\d", d["date"])
    assert d["sha256"] in r.stdout
    assert str(f.parent) not in (env.data / "sync.json").read_text(encoding="utf-8")  # only the file name
    assert not [p for p in env.data.rglob("*") if p.is_file() and p.read_bytes() == f.read_bytes()]  # the export is not copied
    # the log entry, in exactly the agreed format
    log = state1["sync_log"]
    assert len(log) == 1 and list(log[0]) == LOG_KEYS and list(log[0]["mismatches"]) == MISMATCH_KEYS
    e = log[0]
    assert e["turn"] == state0["turn"] == 3 and e["tick"] == 3 and e["applied"] is False
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", e["at"])
    assert e["mismatches"] == {"position": 0, "time": 0, "quest": 1, "party": 0, "drift": 0}  # Voyage has the planned quest active
    assert "nothing else changed" in r.stdout


def test_a_second_dry_run_of_the_same_export_replaces_its_digest(env):
    f = env.export(make_save())
    env.ok("sync", f)
    env.ok("sync", f)
    assert len(digests(env)) == 1 and len(sync_log(env)) == 2  # one digest per export, one log entry per run
    env.ok("sync", env.export(make_save(day=2)))
    assert len(digests(env)) == 2


def test_the_report_has_the_three_classes_in_order(env):
    r = env.ok("sync", env.export(make_save()))
    out = r.stdout
    i1, i2, i3 = out.index("CLASS 1"), out.index("CLASS 2"), out.index("CLASS 3")
    assert i1 < i2 < i3 < out.index("MISMATCHES BY TYPE")
    assert "left untouched" in out[i3:] and "none: position, time, quest status and party agree" in out
    assert "MISMATCHES BY TYPE: position 0, time 0, quest 0, party 0, drift 0" in out


# ---- class 1: Voyage-owned state, with the proposed patch ------------------------------------------------------------
def class1_save(**kw):
    return make_save(tick=3, day=3, tod="evening", place=(OTHER_LOC, OTHER_AREA),
                     members=("Aiko Tanaka", "Tatsuya Ōmine", "Zed Newcomer"),
                     quests={"a": {"name": QUEST, "status": "active"}, "b": {"title": QUEST2, "status": "completed"},
                             "c": {"name": "A Voyage-made Errand", "status": "active"}}, **kw)


def test_class_1_reports_each_mismatch_with_its_patch(env):
    f = env.export(class1_save())
    r = env.ok("sync", f)
    out = r.stdout
    c1 = out[out.index("CLASS 1"):out.index("CLASS 2")]
    assert f"position: Aiko Tanaka: database {HOME_LOC}/{HOME_AREA}, Voyage {OTHER_LOC}/{OTHER_AREA}" in c1
    assert "time: database Day 1 Dawn, Voyage Day 3 Evening" in c1
    assert f'quest: "{QUEST}": database planned, Voyage active' in c1
    assert f'quest: "{QUEST2}": database planned, Voyage completed' in c1
    assert "A Voyage-made Errand" not in c1  # a Voyage-generated quest the database does not know is not a mismatch (the report lists it by name above)
    assert "save quests with no database match (1): A Voyage-made Errand" in out
    assert 'party: party member "Tatsuya Ōmine" is world in the database' in c1
    assert 'party: party member "Zed Newcomer" is not in the database' in c1
    q = shlex.quote
    for cmd in (f'pos {q("Aiko Tanaka")} {q(OTHER_LOC)} {OTHER_AREA} --turn 3',
                'time --day 3 --block Evening --allow-backward --turn 3',
                f'quest-start {q(QUEST)} --turn 3', f'quest-start {q(QUEST2)} --turn 3', f'quest-end {q(QUEST2)} completed --turn 3',
                f'npc-seen {q("Tatsuya Ōmine")} --turn 3', f'add-npc {q("Zed Newcomer")} --turn 3'):
        assert any(ln.strip().startswith(f"python3 tools/db.py --campaign {CAMPAIGN} {cmd}") for ln in c1.splitlines()), cmd
    assert "MISMATCHES BY TYPE: position 1, time 1, quest 2, party 2, drift 0" in out
    e = sync_log(env)[0]
    assert e["mismatches"] == {"position": 1, "time": 1, "quest": 2, "party": 2, "drift": 0} and e["applied"] is False
    # the dry run changed none of the records
    assert env.pc()["location"] == HOME_LOC and env.load("quests")[QUEST]["status"] == "planned"


def test_a_player_character_missing_from_the_save_party_is_a_party_mismatch(env):
    env.up("pc-add", "Ren Sato", "--player", "Kim", "--room", "river-bedroom")
    r = env.ok("sync", env.export(make_save(members=("Aiko Tanaka",))))
    assert 'party: player character "Ren Sato" is not in Voyage' in r.stdout and "party 1" in r.stdout


def test_positions_read_each_members_own_place_when_the_save_gives_one(env):
    env.up("pc-add", "Ren Sato", "--player", "Kim", "--room", "river-bedroom")
    env.up("pos", "Ren Sato", HOME_LOC, HOME_AREA)
    f = env.export(make_save(members=("Aiko Tanaka", "Ren Sato"), place=(HOME_LOC, HOME_AREA),
                             member_places={"Ren Sato": (OTHER_LOC, OTHER_AREA)}))
    r = env.ok("sync", f)
    assert f"position: Ren Sato: database {HOME_LOC}/{HOME_AREA}, Voyage {OTHER_LOC}/{OTHER_AREA}" in r.stdout
    assert "position: Aiko Tanaka" not in r.stdout and "position 1" in r.stdout


def test_apply_changes_class_1_only_and_reports_it(env):
    env.ok("sync", env.export(class1_save()))   # the dry run first, as the playbook says
    f = env.export(class1_save())
    r = env.ok("sync", f, "--apply")
    assert "APPLIED" in r.stdout and "classes 2 and 3 untouched" in r.stdout
    pc, st = env.pc(), env.load("state")
    assert (pc["location"], pc["area"]) == (OTHER_LOC, OTHER_AREA)
    assert (st["day"], st["time_block"], st["clock"], st["weekday"]) == (3, "Evening", "17:00", "Monday")
    q = env.load("quests")
    assert q[QUEST]["status"] == "active" and q[QUEST]["started_turn"] == 3 and "inferred" not in q[QUEST]
    assert q[QUEST2]["status"] == "completed" and q[QUEST2]["ended_turn"] == 3
    assert QUEST in st["active_quests"] and QUEST2 not in st["active_quests"]
    cast = env.load("cast")
    assert cast["Tatsuya Ōmine"]["status"] == "in_play" and cast["Zed Newcomer"]["status"] == "in_play"
    assert "Zed Newcomer" in st["introduced_npcs"]
    assert "sync" in {c["cmd"] for c in st["changelog"]} or {"pos", "time", "quest-start"} <= {c["cmd"] for c in st["changelog"]}
    # the log entry the dry run wrote is now the applied one; a second sync of the same state finds nothing
    log = st["sync_log"]
    assert len(log) == 1 and list(log[0]) == LOG_KEYS and log[0]["applied"] is True
    assert log[0]["mismatches"] == {"position": 1, "time": 1, "quest": 2, "party": 2, "drift": 0}
    assert len(digests(env)) == 1
    r2 = env.ok("sync", f)
    assert "MISMATCHES BY TYPE: position 0, time 0, quest 0, party 0, drift 0" in r2.stdout
    assert [e["applied"] for e in env.load("state")["sync_log"]] == [True, False]


def test_apply_without_a_dry_run_logs_one_applied_entry(env):
    env.ok("sync", env.export(make_save(day=2, tod="Morning")), "--apply")
    log = sync_log(env)
    assert len(log) == 1 and log[0]["applied"] is True and log[0]["mismatches"]["time"] == 1
    st = env.load("state")
    assert (st["day"], st["time_block"]) == (2, "Morning")


# ---- inferred records: would confirm, then confirm-and-clear ---------------------------------------------------------
def inferred_env(env):
    env.up("pos", "Aiko Tanaka", OTHER_LOC, OTHER_AREA, "--inferred", evidence="Aiko sits at the diner counter")
    env.up("time", "--day", "2", "--block", "Evening", "--inferred", evidence="the lanterns come on")
    env.up("quest-start", QUEST, "--inferred", evidence="the House Manager hands out the chore rota")
    env.up("quest-start", QUEST2, "--inferred", evidence="marks are posted")
    env.up("quest-end", QUEST2, "--inferred", evidence="the marks board is taken down")
    env.up("quest-start", QUEST3, "--inferred", evidence="the review sheets come out")
    env.up("quest-end", QUEST3, "--inferred", evidence="the sheets are collected")
    return make_save(day=2, tod="Evening", place=(OTHER_LOC, OTHER_AREA),
                     quests={"a": {"name": QUEST, "status": "active"}, "b": {"name": QUEST2, "status": "completed"},
                             "c": {"name": QUEST3, "status": "active"}})


def test_inferred_records_the_export_confirms_are_listed_as_would_confirm(env):
    f = env.export(inferred_env(env))
    r = env.ok("sync", f)
    out = r.stdout
    assert "would confirm (inferred records the export confirms" in out
    w = out[out.index("would confirm"):out.index("CLASS 2")]
    assert "position of Aiko Tanaka" in w and "Aiko sits at the diner counter" in w
    assert "time (Day 2 Evening)" in w and "the lanterns come on" in w
    assert f'quest "{QUEST}" is active (inferred start)' in w
    assert f'quest "{QUEST2}" apparent end' in w and "is confirmed: Voyage has it completed" in w
    assert QUEST3 not in w  # Voyage still has it active: the apparent end is contradicted, which is a class 1 item
    c1 = out[out.index("CLASS 1"):out.index("CLASS 2")]
    assert f'quest: "{QUEST2}": database active, Voyage completed (confirms the apparent end' in c1
    assert f'quest: "{QUEST3}": apparent end noted at turn 1, but Voyage still has it active' in c1
    assert "MISMATCHES BY TYPE: position 0, time 0, quest 2, party 0, drift 0" in out
    assert env.pc()["inferred"] is True and env.load("state")["time_inferred"] is True  # a dry run clears nothing


def test_apply_confirms_and_clears_inferred_records(env):
    f = env.export(inferred_env(env))
    r = env.ok("sync", f, "--apply")
    assert "cleared inferred" in r.stdout
    pc, st, q = env.pc(), env.load("state"), env.load("quests")
    assert "inferred" not in pc and "quote" not in pc
    assert "time_inferred" not in st and "time_quote" not in st
    assert (st["day"], st["time_block"], st["clock"]) == (2, "Evening", "17:00")  # confirmed, so the clock keeps its value
    assert q[QUEST]["status"] == "active" and "inferred" not in q[QUEST] and "quote" not in q[QUEST]
    assert q[QUEST2]["status"] == "completed" and q[QUEST2]["ended_turn"] == 3
    assert "inferred" not in q[QUEST2] and "apparent_end" not in q[QUEST2]
    assert any("apparent end confirmed" in x["event"] for x in q[QUEST2]["log"])
    assert q[QUEST3]["status"] == "active" and "apparent_end" not in q[QUEST3] and "inferred" not in q[QUEST3]  # contradicted: cleared
    assert any("apparent end contradicted" in x["event"] for x in q[QUEST3]["log"])
    assert QUEST2 not in st["active_quests"] and QUEST3 in st["active_quests"]


def test_inferred_records_the_export_does_not_settle_stay_inferred(env):
    env.up("pos", "Aiko Tanaka", OTHER_LOC, OTHER_AREA, "--inferred", evidence="at the counter")
    env.up("time", "--day", "2", "--block", "Evening", "--inferred", evidence="lanterns")
    # the export puts the PC elsewhere, at an unknown hour name, so neither record is confirmed
    save = make_save(day=2, tod="Teatime", place=("Nowhere Plaza", None))
    env.ok("sync", env.export(save), "--apply")
    assert env.pc()["inferred"] is True and env.load("state")["time_inferred"] is True


def test_a_corrected_position_clears_its_inferred_flag(env):
    env.up("pos", "Aiko Tanaka", OTHER_LOC, OTHER_AREA, "--inferred", evidence="at the counter")
    env.ok("sync", env.export(make_save(place=(HOME_LOC, HOME_AREA))), "--apply")
    pc = env.pc()
    assert (pc["location"], pc["area"]) == (HOME_LOC, HOME_AREA) and "inferred" not in pc and "quote" not in pc


# ---- ticks: Voyage's numbering wins ----------------------------------------------------------------------------------
def test_ticks_played_without_the_director_are_listed_and_imported(env):
    save = make_save(tick=6, day=2, tod="Morning", ticks=(4, 6))  # tick 5 is missing from turnData
    f = env.export(save)
    r = env.ok("sync", f)
    assert "ticks played without the director: 4 to 6 (3)" in r.stdout and "no turnData for tick(s) 5" in r.stdout
    assert env.load("state")["turn"] == 3 and len(env.load("turns")) == 3  # the dry run imports nothing
    r = env.ok("sync", f, "--apply")
    st, turns = env.load("state"), env.load("turns")
    assert st["turn"] == 6 and [t["turn"] for t in turns] == [1, 2, 3, 4, 5, 6]
    t4, t5, t6 = turns[3], turns[4], turns[5]
    assert t4["imported"] is True and "imported" not in turns[2]
    assert t4["inputs"] == "Aiko: Aiko does thing 4. Then waits. | Ren: Ren answers 4" and "__dm__" not in t4["inputs"]
    assert t4["prompt"] == "Cut: prompt 4" and t4["summary"] == "Tick 4 story sentence one. Tick 4 story sentence two."
    assert "\n" not in t4["inputs"] and "\n" not in t4["summary"]
    assert t5["imported"] is True and t5["inputs"] == "" and t5["summary"].startswith("(Voyage's save has no story text")
    assert t4["day"] == "?" and t6["day"] == 2 and t6["time"].startswith("Morning")  # the last tick takes the export's day and block
    assert any(c["cmd"] == "sync" and "imported 3 tick(s)" in c["summary"] for c in st["changelog"])
    assert env.ok("state").returncode == 0  # state reads cleanly after the import (verify_data passed inside the apply)


def test_an_imported_summary_is_cut_at_a_sentence_under_400_characters(env):
    long_story = " ".join(f"Sentence number {i} is here." for i in range(40))
    save = make_save(tick=4, ticks=(4,))
    save["turnData"][0]["stories"] = {"tier1": long_story}
    env.ok("sync", env.export(save), "--apply")
    s = env.load("turns")[3]["summary"]
    assert len(s) <= 400 and s.endswith(".") and s.startswith("Sentence number 0 is here.") and "\n" not in s


def test_director_turns_voyage_no_longer_has_are_marked_undone_not_deleted(env):
    env.logged(5)
    f = env.export(make_save(tick=3))
    r = env.ok("sync", f)
    assert "director turns Voyage no longer has: 4 to 5 (2)" in r.stdout
    assert [t.get("undone") for t in env.load("turns")] == [None] * 5
    env.ok("sync", f, "--apply")
    st, turns = env.load("state"), env.load("turns")
    assert st["turn"] == 3 and len(turns) == 5  # nothing deleted
    assert [t.get("undone") for t in turns] == [None, None, None, True, True]
    assert turns[3]["summary"] == "summary 4"
    assert env.ok("state").returncode == 0
    # the next turn follows Voyage's numbering, even though turns 4 and 5 stay in the log, marked
    env.ok("turn", 4, "--inputs", "x", "--summary", "A new turn four.", "--prompt", "Cut: a")
    st, turns = env.load("state"), env.load("turns")
    assert st["turn"] == 4 and len(turns) == 6 and turns[-1]["turn"] == 4 and "undone" not in turns[-1]


def test_equal_ticks_import_nothing_and_mark_nothing(env):
    r = env.ok("sync", env.export(make_save(tick=3)), "--apply")
    assert "the ticks agree" in r.stdout and len(env.load("turns")) == 3
    assert all("undone" not in t and "imported" not in t for t in env.load("turns"))


# ---- --apply under lock, with a snapshot undo-turn can rewind ---------------------------------------------------------
def test_apply_can_be_rewound_with_undo_turn(env):
    env.ok("sync", env.export(make_save(tick=3)))  # a dry run first
    save = class1_save(ticks=(4, 5))
    save["engineState"]["ticks"] = 5
    f = env.export(save)
    before = env.mutable()
    r = env.ok("sync", f, "--apply")
    assert "undo-turn 4" in r.stdout and (env.data / ".snapshots" / "before-turn-4").is_dir()
    assert env.mutable() != before and env.load("state")["turn"] == 5
    u = env.ok("undo-turn", 4)
    assert env.mutable() == before   # every mutable file is back, byte for byte
    assert env.load("state")["turn"] == 3 and len(env.load("turns")) == 3
    assert "restored" in u.stdout


def test_apply_without_an_import_snapshots_before_the_latest_turn(env):
    env.ok("sync", env.export(make_save(day=2, tod="Morning")), "--apply")
    assert (env.data / ".snapshots" / "before-turn-4").is_dir()
    before_time = (env.load("state")["day"], env.load("state")["time_block"])
    assert before_time == (2, "Morning")
    env.ok("undo-turn", 4)
    st = env.load("state")
    assert (st["day"], st["time_block"], st["turn"]) == (1, "Dawn", 3)


def test_apply_undone_marks_are_rewound_by_undo_turn(env):
    env.logged(5)
    before = env.mutable()
    env.ok("sync", env.export(make_save(tick=3)), "--apply")
    assert (env.data / ".snapshots" / "before-turn-6").is_dir()
    env.ok("undo-turn", 6)
    assert env.mutable() == before


def test_sync_takes_the_write_lock_for_a_dry_run_and_for_apply(env):
    f = env.export(make_save(day=2))
    before = env.files()
    fd = os.open(env.data / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for args in ((), ("--apply",)):
            r = env.run("sync", f, *args)
            assert r.returncode == 6 and "another write is in progress" in r.stderr
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert {k: v for k, v in env.files().items()} == before and not (env.data / "sync.json").exists()
    assert not (env.data / ".lock").read_bytes()  # a clean release leaves the lock empty


def test_a_failed_apply_restores_the_snapshot(env):
    # a quest name the save marks completed while the database has it completed too: no change; force a failure instead with a
    # corrupt turns.json entry count, so verification fails after the changes
    st = env.load("state")
    st["turn"] = 3
    env.dump("state", st)
    turns = env.load("turns")
    env.dump("turns", turns[:2])  # state.turn 3 but two entries: verify_data fails after the apply
    before = env.mutable()
    r = env.run("sync", env.export(make_save(day=2)), "--apply")
    assert r.returncode == 1 and "Restored the pre-sync snapshot" in r.stderr
    assert env.mutable() == before and not (env.data / ".snapshots" / "before-turn-4").exists()


def test_recover_restores_a_crashed_sync_apply(env):
    env.ok("sync", env.export(make_save(day=2, tod="Morning")), "--apply")  # leaves before-turn-4
    st = env.load("state")
    st["day"] = 9  # the half-applied state a crash would leave
    env.dump("state", st)
    (env.data / ".lock").write_text(json.dumps({"pid": 99999999, "cmd": "sync-apply", "turn": 4, "ts": 1.0}), encoding="utf-8")
    r = env.ok("recover")
    assert "interrupted sync --apply did not count" in r.stdout and env.load("state")["day"] == 1


# ---- trial runs and VOYAGE_DATA copies (D19) -------------------------------------------------------------------------
def test_apply_is_refused_in_a_trial_run_even_on_a_copy(env):
    f = env.export(make_save(day=2))
    before = env.files()
    r = env.run("sync", f, "--apply", env={"VOYAGE_TRIAL": "1"})
    assert r.returncode == 4 and "trial run" in r.stderr
    assert env.files() == before and not (env.data / ".snapshots").exists()


def test_a_trial_dry_run_is_allowed_on_a_voyage_data_copy_and_refused_on_real_data(env):
    f = env.export(make_save(day=2))
    real_before = env.files(env.real)
    r = env.run("sync", f, env={"VOYAGE_TRIAL": "1"})
    assert r.returncode == 0 and (env.data / "sync.json").exists() and len(sync_log(env)) == 1
    r = env.run("sync", f, env={"VOYAGE_TRIAL": "1"}, data=False)
    assert r.returncode == 4 and "VOYAGE_DATA" in r.stderr
    assert env.files(env.real) == real_before and not (env.real / "sync.json").exists() and not (env.real / ".lock").exists()


def test_apply_works_on_a_voyage_data_copy_and_leaves_the_real_data_alone(env):
    real_before = env.files(env.real)
    env.ok("sync", env.export(make_save(day=2, tod="Morning")), "--apply")
    assert env.load("state")["day"] == 2 and env.files(env.real) == real_before


# ---- class 2: Voyage drift, reported and never applied ----------------------------------------------------------------
def add_trap(env, match, text):
    p = env.root / "campaigns" / CAMPAIGN / "campaign.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["canon_traps"].append({"match": match, "text": text})
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def test_a_canon_trap_conflict_is_reported_as_drift_and_not_applied(env):
    add_trap(env, ["Rikona"], "Rikona Mibu is NOT in the crew; she helps with one case only.")
    facts = env.load("canon")
    facts["facts"].append({"id": "f901", "turn": 1, "subject": "org", "fact": "Open seats are goals; Rikona has NOT joined (never assume).", "evidence": "x"})
    env.dump("canon", facts)
    save = make_save(members=("Aiko Tanaka", "Rikona Mibu"), day=2, tod="Morning")
    f = env.export(save)
    r = env.ok("sync", f)
    out = r.stdout
    c2 = out[out.index("CLASS 2"):out.index("CLASS 3")]
    assert "drift: Voyage's party lists Rikona Mibu" in c2 and "are not in the crew (or are excluded)" in c2
    assert "Studio-fix candidate" in c2 and "Rikona Mibu is NOT in the crew" in c2 and "canon fact f901" in c2
    assert c2.count("drift:") == 1  # the trap and the fact give one item, not two
    assert "party member" not in out[out.index("CLASS 1"):out.index("CLASS 2")]  # drift is not also a class 1 party item
    assert "add-npc" not in out
    assert "MISMATCHES BY TYPE: position 0, time 1, quest 0, party 0, drift 1" in out
    assert sync_log(env)[0]["mismatches"] == {"position": 0, "time": 1, "quest": 0, "party": 0, "drift": 1}
    canon_before = env.load("canon")
    r = env.ok("sync", f, "--apply")
    assert "Rikona" not in json.dumps(env.load("cast")) and "Rikona" not in json.dumps(env.load("world-npcs"))
    assert env.load("canon") == canon_before and "Rikona" not in json.dumps(env.load("state")["introduced_npcs"])
    assert env.load("state")["day"] == 2  # the class 1 item beside it was applied
    assert (env.root / "campaigns" / CAMPAIGN / "campaign.json").read_text(encoding="utf-8").count("Rikona") == 2  # traps untouched


def test_a_canon_fact_conflict_is_drift_too(env):
    facts = env.load("canon")
    facts["facts"].append({"id": "f900", "turn": 1, "subject": "test", "fact": "Mio Tachibana is dead. The house mourns.", "evidence": "x"})
    env.dump("canon", facts)
    r = env.ok("sync", env.export(make_save(members=("Aiko Tanaka", "Mio Tachibana"))))
    c2 = r.stdout[r.stdout.index("CLASS 2"):r.stdout.index("CLASS 3")]
    assert "Voyage's party lists Mio Tachibana" in c2 and "canon fact f900" in c2 and "are dead" in c2 and "new trap if it recurs" in c2
    assert 'party member "Mio Tachibana"' not in r.stdout


def test_a_party_member_the_canon_does_not_contradict_is_not_drift(env):
    add_trap(env, ["Rikona"], "Rikona Mibu is NOT in the crew; she helps with one case only.")
    r = env.ok("sync", env.export(make_save(members=("Aiko Tanaka", "Tatsuya Ōmine"))))
    assert "drift 0" in r.stdout and "none: nothing in the export conflicts" in r.stdout


def test_a_place_the_database_does_not_know_is_drift_and_not_a_position_patch(env):
    r = env.ok("sync", env.export(make_save(place=("Nowhere Plaza", "bench"))))
    c2 = r.stdout[r.stdout.index("CLASS 2"):r.stdout.index("CLASS 3")]
    assert 'Aiko Tanaka is at Nowhere Plaza/bench in Voyage, but location "Nowhere Plaza" is not in locations.json' in c2
    assert "position 0" in r.stdout and " pos " not in r.stdout
    env.ok("sync", env.export(make_save(place=("Nowhere Plaza", "bench"))), "--apply")
    assert env.pc()["location"] == HOME_LOC


def test_an_unknown_time_block_is_drift(env):
    r = env.ok("sync", env.export(make_save(day=2, tod="Teatime")))
    assert 'Voyage time of day "Teatime" is not a time block of this world' in r.stdout and "time 0" in r.stdout and "drift 1" in r.stdout


def test_apply_never_touches_the_director_layer(env):
    layer = ("threads", "arcs", "lore", "factions")
    before = {n: (env.data / f"{n}.json").read_bytes() for n in layer}
    cast_before = env.load("cast")
    env.ok("sync", env.export(class1_save()), "--apply")
    assert {n: (env.data / f"{n}.json").read_bytes() for n in layer} == before
    cast_after = env.load("cast")
    changed = {k for k in cast_after if cast_after[k] != cast_before.get(k)}
    assert changed == {"Tatsuya Ōmine", "Zed Newcomer"}  # only the two party records class 1 names
    cfg = json.loads((env.root / "campaigns" / CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))
    assert cfg == json.loads((REPO / "campaigns" / CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))


# ---- the save's shape: a wrapper key, a quest list, bad files -----------------------------------------------------------
def test_a_one_key_wrapper_and_a_quest_list_are_read(env):
    save = make_save(day=2, tod="Morning", quests=[{"name": QUEST, "status": "In Progress"}, "junk", {"name": "No Status"}])
    r = env.ok("sync", env.export({"My Save": save}))
    assert 'quest: "Move-In Weekend": database planned, Voyage active' in r.stdout and "time: database Day 1 Dawn" in r.stdout


@pytest.mark.parametrize("content,msg", [("not json {", "not valid JSON"), ("[1, 2]", "not a Voyage state file"),
                                         ('{"partyState": {}}', "no engineState.ticks")])
def test_a_bad_export_is_refused_and_nothing_is_written(env, content, msg):
    f = env.tmp / "bad.json"
    f.write_text(content, encoding="utf-8")
    before = env.files()
    r = env.run("sync", f)
    assert r.returncode == 2 and msg in r.stderr and env.files() == before


def test_a_missing_export_is_refused(env):
    r = env.run("sync", env.tmp / "nope.json")
    assert r.returncode == 2 and "cannot read the export" in r.stderr and not (env.data / "sync.json").exists()


def test_the_tick_falls_back_to_turn_data(env):
    save = make_save(ticks=(1, 2, 3, 4))
    del save["engineState"]
    r = env.ok("sync", env.export(save))
    assert "Voyage tick 4" in r.stdout and "ticks played without the director: 4 to 4 (1)" in r.stdout


# ---- git: the exports folder is ignored, the digest is committed ------------------------------------------------------
def test_exports_folders_are_git_ignored_and_the_digest_is_not():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "campaigns/*/exports/" in lines
    for path, ignored in (("campaigns/joestar/exports/save.json", True), ("campaigns/classroom-2b/exports/a/b.json", True),
                          ("campaigns/joestar/data/sync.json", False)):
        r = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO)
        assert (r.returncode == 0) == ignored, path


# ---- the real Joestar save, on a copy of the Joestar data: the shape of the report only ------------------------------------
def test_the_real_joestar_save_syncs_on_a_copy_of_the_data(tmp_path):
    save = REPO / "worlds" / "joestar-save.json"
    real = REPO / "campaigns" / "joestar" / "data"
    if not save.exists() or not real.is_dir():
        pytest.skip("the Joestar save is not in this checkout")
    before = {p.name: p.read_bytes() for p in real.glob("*.json")}
    data = tmp_path / "data"
    shutil.copytree(real, data, ignore=shutil.ignore_patterns(".lock", ".snapshots", "*.tmp"))
    e = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    e.update({"VOYAGE_DATA": str(data), "PYTHONDONTWRITEBYTECODE": "1"})
    r = subprocess.run([sys.executable, str(DB), "--campaign", "joestar", "sync", str(save)], capture_output=True, text=True, env=e, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    for part in ("export: sha256 ", "TICKS", "CLASS 1", "CLASS 2", "CLASS 3", "MISMATCHES BY TYPE:"):
        assert part in out, part
    d = json.loads((data / "sync.json").read_text(encoding="utf-8"))
    assert len(d) == 1 and re.fullmatch(r"[0-9a-f]{64}", d[0]["sha256"]) and d[0]["sha256"] in out
    assert d[0]["file"] == "joestar-save.json" and isinstance(d[0]["tick"], int) and d[0]["tick"] >= 1
    log = json.loads((data / "state.json").read_text(encoding="utf-8"))["sync_log"]
    assert len(log) == 1 and list(log[0]) == LOG_KEYS and list(log[0]["mismatches"]) == MISMATCH_KEYS and log[0]["applied"] is False
    assert {p.name: p.read_bytes() for p in real.glob("*.json")} == before  # the real Joestar data was not touched
    assert not (real / "sync.json").exists()
