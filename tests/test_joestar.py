"""The Joestar Gang campaign (migrated from voyage-memory at t480, resynced from Voyage's own save at tick 481): data integrity, skill, ladders, counts, and the verification
commands. Read-only commands run on the real data; anything that writes runs on a tmp copy (VOYAGE_DATA)."""
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
CAMP = REPO / "campaigns" / "joestar"
DATA = CAMP / "data"
SKILL = REPO / ".claude" / "skills" / "joestar-director" / "SKILL.md"
sys.path.insert(0, str(REPO / "tools"))
import skilltpl  # noqa: E402

MOODS = {"happy", "angry", "embarrassed", "lying", "hurt"}
HIDDEN = ("kiriyama", "shogo", "archivist", "still frame", "mogami", "daisuke", "replay", "rerun", "okabe", "teller", "honey trap",
          "stream phone", "dead-man", "dead man", "camera exchange", "combat data", "synthetic", "oblivion")


def jload(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def cfg():
    return json.loads((CAMP / "campaign.json").read_text(encoding="utf-8"))


def run(*args, data=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VOYAGE_", "CLASS2B_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if data:
        env["VOYAGE_DATA"] = str(data)
    return subprocess.run([sys.executable, str(DB), "--campaign", "joestar", *map(str, args)], capture_output=True, text=True, env=env, cwd=cwd or REPO)


@pytest.fixture
def copy(tmp_path):
    d = tmp_path / "data"
    shutil.copytree(DATA, d, ignore=shutil.ignore_patterns(".snapshots", ".lock", "*.tmp"))
    return d


# ---- skill ---------------------------------------------------------------------------------------
def test_skill_is_filled_in_sync_and_within_the_ceiling():
    text = SKILL.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= 15000
    assert re.search(r"^name: joestar-director$", text, re.M) and re.search(r"^Skill version: 2026-10-04\.4$", text, re.M)
    assert skilltpl.fills_left(text) == []
    c = cfg()
    tpl = skilltpl.render((REPO / "templates" / "voyage-director" / "SKILL.md").read_text(encoding="utf-8"), skilltpl.context(c), skilltpl.enabled_modules(c))
    assert skilltpl.blocks(text) == skilltpl.blocks(tpl) and skilltpl.rules_version(text) == skilltpl.rules_version(tpl)
    r = subprocess.run([sys.executable, str(REPO / "tools" / "sync_skill.py"), "joestar", "--check"], capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stdout + r.stderr
    for must in ("Kaito Arashima", "Kaito Serizawa", "Keito Takeda", "Shun", "Safehouse", "README `Players`", "hard lines".lower()):
        assert must.lower() in text.lower(), must


def test_no_unfilled_blocks_in_campaign_docs():
    for f in ("README.md", "arc-bible.md", "opening.md", "split-scenes.md", "docs/orchestration.md", "docs/studio.md", "docs/expression.md",
              "docs/migration.md", "docs/org.md", "docs/rules.md", "docs/engine.md", "docs/story-design.md"):
        t = (CAMP / f).read_text(encoding="utf-8")
        assert "<!-- fill" not in t and "{{" not in t and "module:" not in t, f


def test_campaign_config():
    c = cfg()
    assert c["name"] == "joestar" and c["display"] == "Joestar Gang" and c["prompt_limit_default"] == 840 and c["push_every"] == 5
    assert c["skill_dir"] == ".claude/skills/joestar-director" and not any(m["enabled"] for m in c["modules"].values())
    assert [a["n"] for a in c["acts"]] == [1, 2, 3] and c["start_weekday"] == "Saturday" and c["world_file"] == "worlds/joestar-save.json" and (REPO / c["world_file"]).exists()
    assert jload("state")["settings"]["prompt_limit"] == 840


# ---- state ---------------------------------------------------------------------------------------
def test_state_at_t481_synced_from_the_voyage_save():
    st = jload("state")
    assert st["turn"] == 481 and st["turn_base"] == 381 and len(jload("turns")) == 100 and st["act"] == 2
    assert (st["day"], st["weekday"], st["time_block"]) == (20, "Thursday", "Evening")
    assert [p["name"] for p in st["player_characters"]] == ["Jostin Joestar", "Jovian Joestar"]
    assert all(p["power"] and p["background"] and p["pronouns"] for p in st["player_characters"])
    assert all((p["location"], p["area"]) == ("Pulse Printworks", "front-counter") for p in st["player_characters"])
    sc = st["scene"]
    assert sc["name"] == "The sedan in the alley" and "SEDAN DRIVER" not in sc["present"] and "Ryota Kobayashi" in sc["present"] and sc["turns_used"] > sc["budget"]
    assert sc["comms"] == ["Haruto Saionji", "Nobu Takamine", "Kaito Arashima"] and "pending_prompt_notes" not in sc
    assert len(sc["pending_inputs"]) == 1 and "BACK STAIRS NOW" in sc["pending_inputs"][0]
    assert all(w in sc["card"] for w in ("Steam Lantern Alley", "Status?", "Eagle Vision", "Lookout 2", "noodle"))
    assert "After the last bell" not in json.dumps(st["scene"])
    assert len(st["open_clocks"]) == 1 and "Steam Lantern Alley" in st["open_clocks"][0]["name"]
    assert len(st["active_quests"]) == 11 and len(st["feedback"]) == 4 and len(st["introduced_npcs"]) >= 25
    L = jload("locations")
    assert sc["area"] in L[sc["location"]]["areas"] and all(p["area"] in L[p["location"]]["areas"] for p in st["player_characters"])
    assert "Steam Lantern Alley" in L and "noodle-corner" in L["Steam Lantern Alley"]["areas"]
    assert any(c["cmd"] == "resync" for c in st["changelog"])
    readme = (CAMP / "README.md").read_text(encoding="utf-8")
    assert "Day 20" in readme and "worlds/joestar-save.json" in readme


def test_voyage_world_import_keys_win_and_references_are_remapped():
    save = json.loads((REPO / "worlds" / "joestar-save.json").read_text(encoding="utf-8"))
    L = jload("locations")
    assert set(save["locations"]) <= set(L) and len(L) == len(save["locations"]) == 242
    for name in ("Club Lumière", "Tetsu Iron Palm Gym", "Ward Licensing Services", "Pulse Printworks", "Steam Lantern Alley"):
        assert name in L, name
    assert "club-lumiere" not in L["Kobuncho"]["areas"] and "Main Lounge" in L["Club Lumière"]["areas"] and "Club Kagerō" in L["Kobuncho"]["areas"]
    for ln, sl in save["locations"].items():
        assert set(L[ln]["areas"]) == set(sl.get("areas", {})), ln  # Voyage's area keys verbatim
    assert set(L["Chikara Academy"]["director_areas"]) == {"gym-corridor", "gym-storage-room"} and "gym-storage-room" not in L["Chikara Academy"]["areas"]
    F = jload("factions")
    assert set(save["factions"]) <= set(F) and "Joestar Crew" not in F and F["Joestar Gang"]["directorInfo"] and F["Primes"]["director_only"]
    assert len(F) == 23 and len(jload("lore")) == 218 and set(save["worldLore"]) <= set(jload("lore"))
    cast, wn = jload("cast"), jload("world-npcs")
    seen = {v["voyage"]["key"] for v in list(cast.values()) + list(wn.values()) if v.get("voyage")}
    assert set(save["npcs"]) <= seen  # every one of the 185 Voyage NPCs is in cast or world-npcs
    assert wn["Ryota Kobayashi"]["aliases"][0] == "SEDAN DRIVER" and "Driver" in wn["Yuji Hara"]["aliases"]
    assert "Anya" in cast["Principal Anya"]["aliases"] and cast["Principal Anya"]["voyage"]["key"] == "Anya"
    for e in list(cast.values()) + list(wn.values()):
        assert not ({"relationship", "hpCurrent", "hpMax", "level", "tier"} & set(e.get("voyage") or {})), e["name"]  # Voyage's mechanics stay in Voyage
    for q in jload("quests").values():
        assert q["location"] in L and (q["area"] is None or q["area"] in L[q["location"]]["areas"]), q["name"]
        assert all(p[0] in L and (p[1] is None or p[1] in L[p[0]]["areas"]) for p in q["places"]), q["name"]
    c = cfg()
    assert c["home"]["location"] == "Club Lumière" and c["home"]["start_area"] in L["Club Lumière"]["areas"]
    w = jload("world")
    assert w["story_start"]["name"] == save["gameConfig"]["storyStartName"] and w["resource_settings"] == [] and "Saturday, August 1, 2026" in w["story_start"]["storyStart"]


def test_turn_history_is_voyages_ticks_382_to_481():
    save = json.loads((REPO / "worlds" / "joestar-save.json").read_text(encoding="utf-8"))
    T = jload("turns")
    assert [t["turn"] for t in T] == list(range(382, 482)) == [t["tick"] for t in save["turnData"]]
    by = {t["tick"]: t for t in save["turnData"]}
    for t in T:
        src = by[t["turn"]]["playerInputs"]
        assert t["prompt"] == src["__dm__"].strip() and t["summary"] and "\n" not in t["summary"] and len(t["summary"]) <= 400
        assert "Jostin: " in t["inputs"] and "Jovian: " in t["inputs"]
    last = T[-1]
    assert last["day"] == 20 and "sedan" in last["summary"] and "Back stairs" in last["prompt"] and "eagle vision" in last["inputs"].lower()
    assert T[0]["day"] == "?" and len(jload("history")) == 64  # the old range summaries stay for earlier turns
    st = jload("state")
    assert len(T) + st["turn_base"] == st["turn"]


def test_journal_events_became_canon_facts_without_duplicates():
    save = json.loads((REPO / "worlds" / "joestar-save.json").read_text(encoding="utf-8"))
    facts = jload("canon")["facts"]
    j = [f for f in facts if f["subject"].startswith("journal t")]
    assert len(j) == 79 and len({f["fact"] for f in j}) == 79 and all(f["evidence"].startswith("Voyage save journalEvents") for f in j)
    texts = {e["text"] for e in save["journalEvents"] if e["type"] != "adventure-start"}
    assert {f["fact"] for f in j} <= texts
    assert any("companionDeath" in f["subject"] and "Iori Vale" in f["fact"] for f in j)
    txt = " ".join(f["fact"] for f in facts)
    assert "Iori Vale is dead" in txt and "Kaito Arashima is a full crew member" in txt and "Setsuko Okabe's name is known" in txt


def test_migration_flags_resolved_with_evidence():
    th = jload("threads")
    ok = th["Okabe, the Teller"]["steps"][0]
    assert ok["status"] == "revealed" and ok["revealed_turn"] == 438 and "t437" in ok["evidence"] and "Haruto" in ok["evidence"]
    assert th["The Kagero school's purpose"]["steps"][0]["status"] == "hidden"  # nothing in the story shows the school's purpose
    assert sum(1 for t in th.values() for x in t["steps"] if x["status"] == "revealed") == 1
    cast = jload("cast")
    assert cast["Setsuko Okabe"]["status"] == "in_play" and cast["Setsuko Okabe"]["first_seen_turn"] == 434
    assert "joined the crew" in cast["Kaito Arashima"]["hook"].lower() and "t115" in cast["Kaito Arashima"]["hook"]
    hw = cfg()["hidden_words"]
    assert "Okabe" not in hw["recap"] and "Okabe" not in hw["prompt"] and "Setsuko" not in hw["recap"] and "The Teller" in hw["recap"]
    f041 = next(f for f in jload("canon")["facts"] if f["id"] == "f041")
    assert "killed by accident at t182" in f041["fact"]
    assert "died in his arms" in " ".join(p["notes"] for p in jload("state")["player_characters"])
    md = (CAMP / "docs" / "migration.md").read_text(encoding="utf-8")
    for must in ("Resync from Voyage's own save", "worlds/joestar-save.json", "Flags from t480: resolved or still open", "Remaining open items", "Voyage-side status"):
        assert must in md, must


def test_history_archive_has_all_64_range_summaries():
    h = jload("history")
    assert len(h) == 64 and sum(1 for e in h if e.get("slip")) == 11
    assert all(e["summary"] and e["label"] for e in h)
    assert (h[0]["label"], h[0]["turn_from"], h[0]["turn_to"]) == ("t0-16", 0, 16) and h[-1]["label"].startswith("t467-t474")
    assert any("Harumi" in e["summary"] for e in h)


# ---- cast ----------------------------------------------------------------------------------------
def test_main_npcs_brief_depth_and_kits():
    cast, c = jload("cast"), cfg()
    mains = c["main_npcs"]
    assert len(mains) == 20 and len(set(mains)) == 20 and all(n in cast for n in mains)
    for n in mains:
        e = cast[n]
        x = e["expression"]
        assert set(x) == {"gestures", "moods", "lines", "never"} and 3 <= len(x["gestures"]) <= 4 and len(x["lines"]) >= 2, n
        assert set(x["moods"]) == MOODS and x["never"].strip(), n
        for f in ("voice_card", "want", "fear", "stress", "relationships", "arc_beats", "wont_do_yet", "aliases", "agenda", "role", "status"):
            assert e.get(f), (n, f)
        assert e["arc_beats"].get("act_2") and e["wont_do_yet"].get("act_2"), n
        assert e["voice_card"]["style"] and e["voice_card"]["sample_line"], n
    assert cast["Shogo Kiriyama"]["status"] == "planned" and cast["Daisuke Mogami"]["status"] == "planned"
    assert cast["Shogo Kiriyama"]["villain_sheet"]["weakness"] and cast["Daisuke Mogami"]["villain_sheet"]["rule"].startswith("Rerun")


def test_every_person_in_the_roster_has_a_home():
    cast, wn, st = jload("cast"), jload("world-npcs"), jload("state")
    assert len(cast) == 40 and len(wn) == 153
    names = set(cast) | set(wn) | {p["name"] for p in st["player_characters"]}
    for k, e in cast.items():
        for r in e.get("relationships") or {}:
            assert r in names, (k, r)
    L = jload("locations")
    for k, e in wn.items():
        assert not e["currentLocation"] or e["currentLocation"] in L, k  # empty = Voyage places them outside its map (voyage_where)
        assert not e["currentArea"] or e["currentArea"] in L[e["currentLocation"]]["areas"], k
    assert all(wn[k]["currentLocation"] in L for k in ("Airi Kurosawa", "Sonobe", "Old Man Koga", "Suited handler", "Natsumi Arai"))
    for key in ("Reiko Amagawa", "Haruto Saionji", "Rei Ichinose", "Principal Anya", "Rikona Mibu", "Kaito Arashima", "Kaito Serizawa", "Goki Banda", "Councilor Ohmori",
                "Noa Amemiya", "Renji Kuroba", "The records deputy", "Setsuko Okabe"):
        assert key in cast, key
    for key in ("Airi Kurosawa", "Mirei Tachibana", "Rika Saotome", "Natsumi Arai", "Tsuge", "Ginji Ozu", "Amemiya parents", "Suited handler", "Sonobe", "Old Man Koga", "Dr. Kiyose"):
        assert key in wn, key
    assert cast["Rikona Mibu"]["romance_eligible"] is False and cast["Shun"]["romance_eligible"] is False


def test_kits_and_player_facing_text_do_not_leak_hidden_terms():
    cast = jload("cast")
    for n in cfg()["main_npcs"]:
        blob = " ".join(json.dumps({k: cast[n][k] for k in ("expression", "voice_card", "intro_line") if k in cast[n]} | {"role": cast[n]["role"] if cast[n]["status"] != "planned" else ""},
                                   ensure_ascii=False).lower().split())
        if cast[n]["status"] == "planned":
            blob = " ".join(json.dumps(cast[n]["expression"], ensure_ascii=False).lower().split())
        for w in HIDDEN:
            assert w not in blob, (n, w)
    sk = SKILL.read_text(encoding="utf-8").lower()
    for w in ("kiriyama", "mogami", "okabe", "archivist", "stream phone"):
        assert w not in sk


# ---- ladders, quests, canon ------------------------------------------------------------------------
def test_ladders_are_hidden_gated_and_block_their_names():
    th = jload("threads")
    assert len(th) == 8 and sum(len(t["steps"]) for t in th.values()) == 10
    assert all(s["status"] == "hidden" for k, t in th.items() for s in t["steps"] if k != "Okabe, the Teller")
    cast = jload("cast")
    for k, t in th.items():
        assert all(n in cast or n in jload("world-npcs") for n in t["npcs"]), k
        assert [s["step"] for s in t["steps"]] == list(range(1, len(t["steps"]) + 1)), k
    assert th["The Archivist's name"]["steps"][0]["milestone_gate"].startswith("Beat 4-2")
    assert th["The Lumiere clip"]["steps"][0]["milestone_gate"].startswith("Beat 4-3")
    assert th["The combat-data buyer"]["steps"][0]["earliest_act"] == 3
    sys.path.insert(0, str(REPO / "tools"))
    r = run("thread", "Replay")
    assert r.returncode == 0 and "gate first" in r.stdout


def test_quests_cover_all_27_threads_with_surface_goals():
    Q = jload("quests")
    assert len(Q) == 27
    by = {}
    for q in Q.values():
        by[q["status"]] = by.get(q["status"], 0) + 1
    assert by == {"active": 11, "planned": 6, "completed": 10}
    act = [q for q in Q.values() if q["status"] == "active"]
    assert all(q["surface_goal"].strip() and "(none" not in q["surface_goal"] for q in act)
    assert set(jload("state")["active_quests"]) == {q["name"] for q in act}
    assert all(q["ended_turn"] for q in Q.values() if q["status"] == "completed")
    L = jload("locations")
    assert all(q["location"] in L and (q["area"] is None or q["area"] in L[q["location"]]["areas"]) for q in Q.values())


def test_canon_corrections_exclusions_and_traps_are_present():
    facts = jload("canon")["facts"]
    assert len(facts) == 159 and len({f["id"] for f in facts}) == 159
    subj = " | ".join(f["subject"] for f in facts)
    assert subj.count("correction (") == 13 and subj.count("exclusion:") == 3 and subj.count("engine rule") == 7 and subj.count("drift fix:") == 4
    txt = " ".join(f["fact"] for f in facts)
    for must in ("Keito Takeda is excluded", "Kaito Arashima (crew archer) is not Kaito Serizawa", "Kurokawa is the syndicate, not a district", "Name Shun in prompts",
                 "Safehouse fund is Yuji's raid cash", "Do not develop Daigo Renjiro directly in Act 2", "Club Lumiere is the crew's base"):
        assert must in txt, must
    slips = [f for f in facts if f["subject"].startswith("correction (standing, 2 slips)")]
    assert len(slips) == 1
    traps = " ".join(t["text"] for t in cfg()["canon_traps"])
    for must in ("Kaito Arashima", "Kaito Serizawa", "Kurokawa is the syndicate", "Keito Takeda", "Shun", "Club Lumiere", "Daigo Renjiro", "Rikona"):
        assert must in traps, must
    assert all(t["text"] for t in cfg()["canon_traps"]) and any(not t["match"] for t in cfg()["canon_traps"])


def test_org_chart_and_docs_exist():
    org = (CAMP / "docs" / "org.md").read_text(encoding="utf-8")
    for seat in ("Aether", "Phantom", "Lifeline", "Vault", "Forge", "Pulse", "HearthOps", "Arcanum", "**open**", "Jovian recruits for Spearhead seats"):
        assert seat in org, seat
    arc = (CAMP / "arc-bible.md").read_text(encoding="utf-8")
    for must in ("Arc 4: The Archivist", "4-1 Stills", "4-6 Final Frame", "Pressure curve", "Villain sheet: Shogo Kiriyama", "Villain sheet: Daisuke Mogami", "Daigo Renjiro"):
        assert must in arc, must
    readme = (CAMP / "README.md").read_text(encoding="utf-8")
    for must in ("## Players", "Feedback log", "Migrated from riggedrealm/voyage-memory at t480 (archive, read-only)", "Pending port", "Story Planner",
                 "voyage-site", "portraits", "tools/planner.py", "tools/site.py", "Spoiler policy", "Hard lines", "Wishlist", "pending port".lower()):
        assert must.lower() in readme.lower(), must
    assert len(list((CAMP / "docs" / "archive").glob("*.md"))) >= 17


def test_migration_doc_counts_match_the_data():
    md = (CAMP / "docs" / "migration.md").read_text(encoding="utf-8")
    counts = json.loads(re.search(r"```json\n(.*?)\n```", md, re.S).group(1))
    out = counts["out"]
    cast, wn, loc, q, th = jload("cast"), jload("world-npcs"), jload("locations"), jload("quests"), jload("threads")
    assert out["cast.main"] == len(cfg()["main_npcs"]) and out["cast.total"] == len(cast) and out["world-npcs"] == len(wn)
    assert out["locations"] == len(loc) and out["locations.areas"] == sum(len(v["areas"]) for v in loc.values())
    assert out["factions"] == len(jload("factions")) and out["lore"] == len(jload("lore")) and out["quests"] == len(q)
    assert out["threads(ladders)"] == len(th) and out["threads.steps"] == sum(len(t["steps"]) for t in th.values())
    assert out["canon.facts"] == len(jload("canon")["facts"]) and out["history"] == len(jload("history")) == counts["in"]["turns"]
    assert out["state.turn"] == 481 and out["state.turn_base"] == 381 and out["turns.json"] == len(jload("turns")) == 100 and out["canon_traps"] == len(cfg()["canon_traps"])
    assert counts["in"]["npcs"] == 48 and counts["in"]["threads"] == 27 and counts["in"]["profiles"] == 67
    assert "Superseded rules" in md and "Could not map cleanly" in md and "New_World.json" in md


@pytest.mark.skipif(not Path("/home/user/voyage-memory/data/npcs.json").exists(), reason="the voyage-memory archive is not on this machine")
def test_source_counts_still_match_the_archive():
    src = Path("/home/user/voyage-memory/data")
    sj = lambda n: json.loads((src / f"{n}.json").read_text(encoding="utf-8"))
    md = (CAMP / "docs" / "migration.md").read_text(encoding="utf-8")
    counts = json.loads(re.search(r"```json\n(.*?)\n```", md, re.S).group(1))["in"]
    assert counts["npcs"] == len(sj("npcs")) and counts["places"] == len(sj("places")) and counts["profiles"] == len(sj("profiles"))
    assert counts["threads"] == len(sj("threads")) and counts["turns"] == len(sj("turns")) and counts["canon.facts"] == len(sj("canon")["facts"])
    assert counts["canon.corrections"] == len(sj("canon")["corrections"])
    h = jload("history")
    assert [e["summary"] for e in h] == [e["text"] for e in sj("turns")] and [e["label"] for e in h] == [e["label"] for e in sj("turns")]
    assert {f["fact"] for f in jload("canon")["facts"]} >= {f["text"] for f in sj("canon")["facts"] if f["id"] != "f-iori"}  # f-iori was amended at the t481 resync
    src_details = {t["detail"] for t in sj("threads")}
    got = {q["notes"].split("  [GM-only")[0].split("  [migrated")[0].split(" (Location unknown")[0] for q in jload("quests").values() if q["name"] != "Print lab lead (clock)"}
    assert got <= src_details and len(src_details - got) == 1  # the print-lab quest was rewritten from the save


# ---- the verification commands ---------------------------------------------------------------------------
def test_resume_reports_the_synced_state():
    r = run("resume")
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "Turn 481 | Day 20 Thursday (Act 2) | Evening 17:00" in out and "Skill version (repo): 2026-10-04.4" in out
    assert "WARNING" not in out.replace("WARNING over budget", "")
    assert re.search(r"^Generic rules: (\S+) \(template \1\)$", out, re.M)
    assert "The sedan in the alley (Pulse Printworks/front-counter)" in out and "over budget" in out and "on comms: Haruto Saionji; Nobu Takamine; Kaito Arashima" in out
    assert "pending inputs (carried over)" in out and "BACK STAIRS NOW" in out and "Deputy at the Steam Lantern Alley storeroom" in out
    assert "Turn 479 | t479" in out and "Turn 481 | Day 20 Evening" in out and "prompt sent (" in out and "Back stairs, now." in " ".join(out.split())
    assert "After the last bell" not in out and "Stale" not in out and "STALE" not in out and "Day None" not in out
    assert "Revealed ladder steps:" in out and "Okabe, the Teller" in out


STORY_481 = (
    "Narrator: <focus:Jostin Joestar> Jostin jerks his wrists, the coiling steel of the kusarigama slackening and falling away from the driver's throat.\n\n"
    "Narrator: <focus:Jostin Joestar> He activates Eagle Vision; the driver glows a panicked red.\n\n"
    "Narrator: <focus:Jovian Joestar> Jovian leans back against the brick wall of the alley and lights a cigarette.\n\n"
    'SEDAN DRIVER: [whispering] Alley. Sedan stopped, tire blown.\n\n'
    "Narrator: <focus:lookout 2> Behind the rusted dumpster, Lookout 2 slips a second, burner-style phone from his sleeve.\n\n"
    "Nobu Takamine: [flatly] Signal's out. The driver's reply went out clean and the manifest matches the logs.\n\n"
    "SEDAN DRIVER: [gasping] He replied. It says... Who is with you? Back stairs, now.\n\n"
    "Kaito Arashima: [clearly] I'm still four minutes out from the noodle counter. If that deputy's moving to the back stairs, I'm going to lose the visual. Get moving!\n")


def test_prep_with_the_tick_481_story_excerpt(tmp_path):
    paste = tmp_path / "paste.txt"
    paste.write_text(STORY_481 + "\nJostin: EAGLE VISION FLARES, COVER HAS BEEN BLOWN, BACK STAIRS NOW\n", encoding="utf-8")
    r = run("prep", "--paste", paste)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "turn 481 (next 482)" in out and "Day 20 Thursday" in out and "Evening 17:00" in out
    assert 'Scene "The sedan in the alley" (Pulse Printworks/front-counter)' in out and "scene over budget" in out
    assert "PRESENT:" in out and "Nobu Takamine" in out and "Kaito Arashima" in out and "Ryota Kobayashi" in out and "Yuji Hara" in out
    assert "Nobu Takamine [in_play]" in out and "Kaito Arashima [in_play]" in out and "show: gesture:" in out and "won't yet:" in out
    assert "surface goal, Print lab lead (clock)" in out and "Steam Lantern Alley storeroom" in out and "limit 840" in out
    assert "Kiriyama" not in out and "Archivist" not in out  # hidden names never appear in prep


def test_brief_for_the_crew():
    for name, bit in (("Reiko Amagawa", "Sena"), ("Haruto Saionji", "Hana"), ("Mikoto Kurogane", "Jovian"), ("Hana Kisaragi", "Haruto"), ("Nobu Takamine", "Dead Air"),
                      ("Yuzuki Hoshino", "tea"), ("Kaito Arashima", "sightline"), ("Ayame Fujinami", "angle")):
        r = run("brief", name)
        assert r.returncode == 0, (name, r.stderr)
        assert "SHOW (pick one, vary):" in r.stdout and "ARC BEAT, act 2" in r.stdout and "WON'T DO YET:" in r.stdout and "(missing in cast.json)" not in r.stdout, name
        assert bit.lower() in r.stdout.lower(), (name, bit)


def test_history_and_recap_see_real_turns_and_the_archive():
    r = run("history", "sedan", "--limit", "3")
    assert r.returncode == 0 and r.stdout.startswith("T481 (Day 20 Evening)") and "T480 (t480)" in r.stdout and "more; raise --limit" in r.stdout
    assert "Day None" not in r.stdout
    r = run("history", "daigo")
    assert r.returncode == 0 and "[archive]" in r.stdout and "Daigo" in r.stdout
    r = run("history", "Kagero", "--limit", "2")
    assert "Kagero" in r.stdout and "more; raise --limit" in r.stdout
    r = run("recap")
    assert r.returncode == 0 and r.stdout.startswith("Previously on Joestar Gang:") and "Day 20 Evening: Jostin Joestar releases the sedan driver" in r.stdout
    assert re.search(r"^- t47\d: ", r.stdout, re.M) and "Day None" not in r.stdout
    for w in ("Kiriyama", "Mogami", "Archivist"):
        assert w not in r.stdout
    r = run("recap", "--turns", "5")
    assert r.returncode == 0 and r.stdout.count("\n- ") >= 5


def test_thread_lists_the_ladders_and_hides_nothing_revealed():
    r = run("thread")
    assert r.returncode == 0 and "The Archivist's name: 0/2 revealed" in r.stdout and "Okabe, the Teller: 1/1 revealed; complete" in r.stdout
    assert "The Kagero school's purpose: 0/1 revealed" in r.stdout
    r = run("thread", "The Archivist's name")
    assert "[hidden]" in r.stdout and "Beat 4-2" in r.stdout


def test_check_prompt_clean_ok_and_hidden_term_fails(tmp_path):
    ok = tmp_path / "ok.txt"
    ok.write_text("Cut: Continue in the gym corridor, the last bell long gone.\nTone: tense, quiet\n"
                  "Crew: Rei Ichinose lifts the corner of the mat with her pen, curiosity flickering under her flat voice: \"For the record, I have one open item.\" Others react in character.\n"
                  "World: Down the hall, Principal Anya's door clicks shut and her footsteps start toward the corridor.", encoding="utf-8")
    r = run("check-prompt", ok)
    assert r.returncode == 0 and "OK: length within limit, all names known, no warnings." in r.stdout and "/ 840" in r.stdout
    alley = tmp_path / "alley.txt"
    alley.write_text("Cut: Same alley, a breath later: the deputy's reply sits on the driver's phone; the van still blocks the mouth.\nTone: tense, fast\n"
                     "Crew: SEDAN DRIVER: stares at the screen, hands shaking. Nobu Takamine: reads the signal on comms. Kaito Arashima: four minutes from Steam Lantern Alley, calls the clock. Haruto Saionji: curt.\n"
                     "Facts: Eagle Vision reads hostility and tension only. Label SEDAN DRIVER's lines SEDAN DRIVER and the other VAN DRIVER.\n"
                     "World: Above the closed noodle counter on Steam Lantern Alley, a back-stair door clicks and boots start down.", encoding="utf-8")
    r = run("check-prompt", alley)
    assert r.returncode == 0 and "/ 840" in r.stdout and "FAIL" not in r.stdout and "WARN" not in r.stdout, r.stdout
    assert "ok Steam Lantern Alley  (location)" in r.stdout and "ok SEDAN DRIVER  (term)" in r.stdout
    bad = tmp_path / "bad.txt"
    bad.write_text("Cut: Cut to the print lab.\nCrew: Kiriyama, the Archivist, watches the feeds.\nWorld: A man walks a recording while Mogami waits.", encoding="utf-8")
    r = run("check-prompt", bad)
    assert r.returncode == 1 and r.stdout.count("FAIL: possible secret leak") >= 3
    for term in ("kiriyama", "archivist", "mogami"):
        assert f'"{term}"' in r.stdout
    long = tmp_path / "long.txt"
    long.write_text("Cut: x\nWorld: " + "y" * 900, encoding="utf-8")
    assert run("check-prompt", long).returncode == 1


def test_name_traps_warn(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("Cut: Continue in the corridor.\nCrew: Kaito waits; Daigo is not here; Renji and Hoshino nod.\nWorld: The hall is quiet.", encoding="utf-8")
    r = run("check-prompt", f)
    assert "AMBIGUOUS name Kaito: Kaito Arashima | Kaito Serizawa" in r.stdout
    assert re.search(r"AMBIGUOUS name Daigo: .*Daigo Kurosawa.*Daigo Renjiro", r.stdout)  # Voyage's own Daigo records join the trap
    assert re.search(r"AMBIGUOUS name Hoshino: Hoshino \(registrar\) \| Yuzuki Hoshino", r.stdout) and 'use full name "Renji Kuroba"' in r.stdout
    cast = jload("cast")
    assert cast["Daigo Renjiro"].get("use_full_name") and "Daigo Renjiro" in " ".join(t["text"] for t in cfg()["canon_traps"])
    wn = jload("world-npcs")
    assert "Renji" not in wn and "Daigo" not in wn and "Hoshino" not in wn  # Voyage's namesakes live under qualified keys


def test_commit_turn_482_on_a_copy_then_undo(copy, tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Cut: Same alley, a breath later: the deputy's reply sits on the driver's phone; the van still blocks the mouth.\nTone: tense, fast\n"
                      "Crew: SEDAN DRIVER: stares at the screen, hands shaking. Nobu Takamine: reads the signal on comms. Kaito Arashima: four minutes from Steam Lantern Alley, calls the clock. Haruto Saionji: curt.\n"
                      "Facts: Eagle Vision reads hostility and tension only. Label SEDAN DRIVER's lines SEDAN DRIVER and the other VAN DRIVER.\n"
                      "World: Above the closed noodle counter on Steam Lantern Alley, a back-stair door clicks and boots start down.", encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"ops": [{"op": "fact", "args": {"subject": "back stairs", "text": "The deputy's storeroom has a back-stair door."}, "evidence": "Back stairs, now."}],
                                   "turn_log": {"inputs": "Jostin: plan B, back stairs now; Jovian: -", "summary": "The crew moves on the back stairs.", "slips": "", "notes": ""}}), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in DATA.glob("*.json")}
    r = run("commit-turn", "--prompt", prompt, "--payload", payload, data=copy)
    assert r.returncode == 0, r.stdout + r.stderr
    st = json.loads((copy / "state.json").read_text(encoding="utf-8"))
    turns = json.loads((copy / "turns.json").read_text(encoding="utf-8"))
    assert st["turn"] == 482 and len(turns) == 101 and turns[-1]["turn"] == 482 and turns[-2]["turn"] == 481
    assert "pending_inputs" not in st["scene"] and {"Nobu Takamine", "Kaito Arashima", "Haruto Saionji"} <= set(st["scene"]["present"])
    assert "Day 20 Thursday" in run("resume", data=copy).stdout
    assert run("undo-turn", 482, data=copy).returncode == 0
    assert json.loads((copy / "state.json").read_text(encoding="utf-8"))["turn"] == 481
    assert {p.name: p.read_bytes() for p in DATA.glob("*.json")} == before  # the real data was never touched


def test_state_and_loc_and_bible_commands_work():
    assert "Prompt limit: 840" in run("state").stdout
    r = run("loc", "Club Lumière", "Main Lounge")
    assert r.returncode == 0 and "Main Lounge" in r.stdout
    assert "Kobuncho" in run("loc", "Kobuncho", "Club Kagerō").stdout
    assert "noodle-corner" in run("loc", "Steam Lantern Alley").stdout and "front-counter" in run("loc", "Pulse Printworks").stdout
    assert "combat-gym" in run("loc", "Chikara Academy").stdout and run("loc", "Tetsu Iron Palm Gym").returncode == 0
    r = run("bible", "act2")
    assert r.returncode == 0 and "Arc 4" in r.stdout and "Pressure curve" in r.stdout
    assert "Scene turn budgets" in run("bible").stdout
    assert run("quest", "Rei the liaison").returncode == 0 and run("npc", "Ayame").returncode == 0
    assert run("lore", "Kobuncho").returncode == 0 and "no lore matches" not in run("lore", "Kobuncho").stdout
    assert run("spotlight").returncode == 0
