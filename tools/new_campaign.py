#!/usr/bin/env python3
"""Create a new Voyage director campaign from templates/voyage-director.

    python3 tools/new_campaign.py NAME --display "Display Name" [--world path/to/world.json] [--module standing] [--module debt] [--setting "..."]

Creates campaigns/NAME/ (README, arc-bible, campaign.json, data/*.json in the shapes tools/db.py expects) and
.claude/skills/NAME-director/SKILL.md, fills the placeholders, applies the optional modules (hidden Standing score:
--module standing, off by default; --standing is an alias; --module debt adds a hidden debt), and, with --world, imports locations, lore, factions and world NPCs from a Voyage world
JSON into data/ in the same shapes as campaigns/classroom-2b. Prints the fill blocks that are still to be written.
Refuses if campaigns/NAME (or the skill folder) already exists. Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skilltpl as T  # noqa: E402

TEXT_FILES = ("README.md", "arc-bible.md", "opening.md", "split-scenes.md", "docs/orchestration.md", "docs/studio.md")
FILL_FILES = ("README.md", "arc-bible.md", "opening.md")


class NewCampaignError(Exception):
    pass


def slugify(s):
    """Lowercase, runs of non-word characters become one hyphen (unicode letters are kept: student-café)."""
    return re.sub(r"[^\w]+", "-", str(s).lower()).strip("-")


def sub_strings(obj, ctx):
    """Replace {{PLACEHOLDERS}} in every string of a JSON value."""
    if isinstance(obj, str):
        for k, v in ctx.items():
            obj = obj.replace("{{" + k + "}}", v)
        return obj
    if isinstance(obj, list):
        return [sub_strings(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: sub_strings(v, ctx) for k, v in obj.items()}
    return obj


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ----------------------------------------------------------------------------
# world import (tolerant: lists or dicts, a few key spellings)
# ----------------------------------------------------------------------------
def first(d, *names, default=None):
    for n in names:
        if isinstance(d, dict) and d.get(n) not in (None, ""):
            return d[n]
    return default


def as_list(v):
    if v is None or v == "":
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def entries(coll):
    """[(key or None, dict)] from a list of objects or a {name: object} dict."""
    if isinstance(coll, dict):
        return [(k, v if isinstance(v, dict) else {"text": v}) for k, v in coll.items()]
    return [(None, v) for v in (coll or []) if isinstance(v, dict)]


def find_coll(world, *names):
    for n in names:
        if world.get(n):
            return world[n]
    return None


def import_world(world, story_start=None):
    """World JSON dict -> ({file: data}, report lines). Shapes match campaigns/classroom-2b/data."""
    if isinstance(world, dict) and len(world) == 1 and isinstance(next(iter(world.values())), dict):
        world = next(iter(world.values()))  # one wrapper key
    if not isinstance(world, dict):
        raise NewCampaignError("the world file must be a JSON object")
    out, report = {}, []

    # locations (+ areas nested, or a separate top-level list with a `location` reference)
    locations = {}
    for key, e in entries(find_coll(world, "locations", "worldLocations", "Locations")):
        name = first(e, "name", "id") or key
        if not name:
            continue
        areas = {}
        for akey, a in entries(first(e, "areas", "locationAreas", default=[])):
            aid = first(a, "id", "key") or akey or slugify(first(a, "name", "title", default=""))
            if aid:
                areas[slugify(aid)] = {"description": first(a, "description", "basicInfo", default=""),
                                       "paths": [slugify(p) for p in as_list(first(a, "paths", "connections", "connectedTo"))]}
        locations[name] = {"basicInfo": first(e, "basicInfo", "description", default=""),
                           "hiddenInfo": first(e, "hiddenInfo", default=""),
                           "region": first(e, "region", default=""),
                           "factions": as_list(first(e, "factions")),
                           "visualTags": as_list(first(e, "visualTags", "tags")),
                           "areas": areas}
    for akey, a in entries(find_coll(world, "locationAreas", "areas", "location_areas")):
        loc = first(a, "location", "locationName", "locationId", "parent")
        aid = first(a, "id", "key") or akey or slugify(first(a, "name", "title", default=""))
        if loc in locations and aid:
            locations[loc]["areas"][slugify(aid)] = {
                "description": first(a, "description", "basicInfo", default=""),
                "paths": [slugify(p) for p in as_list(first(a, "paths", "connections", "connectedTo"))]}
    out["locations"] = locations
    report.append(f"locations: {len(locations)} ({sum(len(v['areas']) for v in locations.values())} areas)")

    factions = {}
    for key, e in entries(find_coll(world, "factions", "worldFactions")):
        name = first(e, "name") or key
        if name:
            factions[name] = {"name": name, "basicInfo": first(e, "basicInfo", "description", default=""),
                              "factionType": first(e, "factionType", "type", default=""),
                              "hiddenInfo": first(e, "hiddenInfo", default="")}
    out["factions"] = factions
    report.append(f"factions: {len(factions)}")

    npcs = {}
    for key, e in entries(find_coll(world, "npcs", "worldNPCs", "worldNpcs", "worldNPCS", "npcList")):
        name = first(e, "name") or key
        if name:
            npcs[name] = {"name": name, "type": first(e, "type", default=""), "faction": first(e, "faction"),
                          "currentLocation": first(e, "currentLocation", "location", default=""),
                          "currentArea": first(e, "currentArea", "area", default=""),
                          "basicInfo": first(e, "basicInfo", "description", default=""),
                          "visualDescription": first(e, "visualDescription", "visual", default=""),
                          "personality": as_list(first(e, "personality")),
                          "worldVoiceId": first(e, "worldVoiceId", default=name), "status": "world"}
    out["world-npcs"] = npcs
    report.append(f"world NPCs: {len(npcs)}")
    for n, e in npcs.items():
        loc = e["currentLocation"]
        if loc and loc not in locations:
            report.append(f"  warning: NPC '{n}' stands in unknown location '{loc}'")
        elif loc and e["currentArea"] and e["currentArea"] not in locations[loc]["areas"]:
            report.append(f"  warning: NPC '{n}' stands in unknown area '{loc}/{e['currentArea']}'")

    lore = {}
    for key, e in entries(find_coll(world, "lore", "worldLore", "loreEntries", "loreBook")):
        text = first(e, "text", "content", "body", "description")
        k = first(e, "key", "id") or key or slugify(first(e, "title", "name", default=""))
        if k and isinstance(text, str):
            lore[k] = text
    out["lore"] = lore
    report.append(f"lore entries: {len(lore)}")

    ws = {}
    start = first(world, "storyStarts", "story_starts", "storyStart", "story_start")
    if isinstance(start, dict) and start and all(isinstance(v, dict) for v in start.values()) and "storyStart" not in start:
        names = list(start)  # {name: story start}: take the one asked for (--story-start), else the first
        start = start.get(story_start) or start[names[0]]
        report.append(f"story starts: {len(names)} in the file; using '{start.get('name')}' (--story-start NAME picks another)")
    if isinstance(start, list):
        start = start[0] if start else None
    if isinstance(start, dict):
        ws["story_start"] = start
    for k, alt in (("time", ()), ("resource_settings", ("resourceSettings",)), ("relationship_stages", ("relationshipStages",)),
                   ("npc_types", ("npcTypes",)), ("narrator_style", ("narratorStyle",))):
        v = next((world[n] for n in (k,) + alt if n in world), None)
        if k == "resource_settings" and isinstance(v, dict):
            v = [{"name": r.get("name", n), "usage": r.get("usageInstructions", r.get("usage", ""))} for n, r in v.items()]
        if k == "npc_types" and isinstance(v, dict):
            v = list(v)
        if v is not None:
            ws[k] = v
    out["world"] = ws
    report.append("world.json: " + (", ".join(sorted(ws)) or "nothing to import (skeleton kept)"))
    for what, got in (("locations", locations), ("lore", lore)):
        if not got:
            report.append(f"  warning: no {what} found: check the world file's keys")
    return out, report


# ----------------------------------------------------------------------------
# scaffolding
# ----------------------------------------------------------------------------
def scaffold(root, name, display, world_path=None, modules=(), setting="", today=None, story_start=None):
    root = Path(root)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise NewCampaignError("NAME must be lowercase letters, digits and hyphens (e.g. harbor-nights)")
    cdir = root / "campaigns" / name
    ctx = T.context({"name": name, "display": display, "skill_dir": f".claude/skills/{name}-director"},
                    f" ({setting})" if setting else "")
    sdir = root / ctx["SKILL_DIR"]
    if cdir.exists():
        raise NewCampaignError(f"campaigns/{name} already exists: refusing to overwrite it")
    if sdir.exists():
        raise NewCampaignError(f"{ctx['SKILL_DIR']} already exists: refusing to overwrite it")
    world = None
    if world_path:
        try:
            world = json.loads(Path(world_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise NewCampaignError(f"cannot read the world file {world_path}: {e}")
    modules = set(modules)
    standing = "standing" in modules
    tdir = T.TEMPLATE_DIR / "campaign"

    cdir.mkdir(parents=True)
    for rel in TEXT_FILES:
        text = (tdir / rel).read_text(encoding="utf-8")
        dest = cdir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(T.render(text, ctx, modules), encoding="utf-8")
    shutil.copy(tdir / ".gitignore", cdir / ".gitignore")

    cfg = sub_strings(json.loads((tdir / "campaign.json").read_text(encoding="utf-8")), ctx)
    if "debt" in modules:
        cfg["modules"]["debt"]["enabled"] = True
    if standing:
        cfg["modules"]["standing"]["enabled"] = True
        cfg["hidden_words"] = {"prompt": ["Standing", "ledger"], "recap": ["standing", "ledger"]}
    write_json(cdir / "campaign.json", cfg)

    data = tdir / "data"
    for p in sorted(data.glob("*.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        if p.name == "ledger.json":
            if not standing:
                continue
            m = cfg["modules"]["standing"]
            obj.update({"start": m["start"], "current": m["start"], "thresholds": m["thresholds"], "hint_bands": m["bands"]})
        elif p.name == "state.json":
            obj["weekday"] = cfg["start_weekday"]
            obj["settings"]["prompt_limit"] = cfg["prompt_limit_default"]
            if "debt" in modules:
                obj["debt"] = {"principal": 0, "due": 0, "due_day": 0}
        write_json(cdir / "data" / p.name, obj)

    report = []
    if world is not None:
        imported, report = import_world(world, story_start)
        for fname, obj in imported.items():
            if fname == "world":  # merge into the skeleton
                skeleton = json.loads((cdir / "data" / "world.json").read_text(encoding="utf-8"))
                skeleton.update(obj)
                obj = skeleton
            write_json(cdir / "data" / f"{fname}.json", obj)

    skill = T.render((T.TEMPLATE_DIR / "SKILL.md").read_text(encoding="utf-8"), ctx, modules)
    today = today or datetime.date.today().isoformat()
    skill = re.sub(r"^Skill version:.*$", f"Skill version: {today}.1", skill, count=1, flags=re.M)
    sdir.mkdir(parents=True)
    (sdir / "SKILL.md").write_text(skill, encoding="utf-8")
    return cdir, sdir, report


def remaining_fills(root, cdir, sdir):
    """[(relative path, line number, fill text)] for every unfilled fill block."""
    found = []
    files = [sdir / "SKILL.md"] + [cdir / f for f in FILL_FILES]
    for p in files:
        text = p.read_text(encoding="utf-8")
        for m in T.FILL_RE.finditer(text):
            found.append((str(p.relative_to(root)), text.count("\n", 0, m.start()) + 1, " ".join(m.group(1).split())))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create campaigns/NAME and .claude/skills/NAME-director from templates/voyage-director.")
    ap.add_argument("name", help="campaign folder name: lowercase letters, digits, hyphens")
    ap.add_argument("--display", required=True, help='display name, e.g. "Harbor Nights"')
    ap.add_argument("--world", metavar="world.json", help="Voyage world JSON: import locations, lore, factions and world NPCs into data/")
    ap.add_argument("--module", action="append", default=[], choices=["standing", "debt"], metavar="NAME",
                    help="enable an optional module: standing (hidden score) or debt; repeatable; all off by default")
    ap.add_argument("--standing", action="store_true", help="alias for --module standing")
    ap.add_argument("--story-start", metavar="NAME", help="with --world: which story start to import (default: the first)")
    ap.add_argument("--setting", default="", help="short setting phrase for the skill description, e.g. 'Chikara Academy, Sakura Lane'")
    ap.add_argument("--root", default=os.environ.get("VOYAGE_ROOT") or str(T.ROOT), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        mods = set(a.module) | ({"standing"} if a.standing else set())
        cdir, sdir, report = scaffold(a.root, a.name, a.display, a.world, mods, a.setting, story_start=a.story_start)
    except NewCampaignError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    root = Path(a.root)
    print(f"Created {cdir.relative_to(root)}/ and {sdir.relative_to(root)}/SKILL.md"
          f" (modules on: {', '.join(sorted(mods)) or 'none'}; SKILL.md {len((sdir / 'SKILL.md').read_bytes())} bytes, limit 14000)")
    for line in report:
        print("  import " + line if not line.startswith("  ") else line)
    fills = remaining_fills(root, cdir, sdir)
    print(f"\n{len(fills)} fill block(s) left to write (search for '<!-- fill:'):")
    for path, line, text in fills:
        print(f"  {path}:{line}  {text[:110]}{'...' if len(text) > 110 else ''}")
    print(f"\nAlso fill in {cdir.relative_to(root)}/campaign.json: acts, start_weekday, main_npcs, home (location, start_area, rooms),"
          " hidden_words, secrets (hints, soft_terms), known_terms; then data/cast.json, quests.json and threads.json.")
    print(f"Next: python3 tools/db.py --campaign {a.name} resume    (skill: zip {sdir.relative_to(root)} and upload it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
