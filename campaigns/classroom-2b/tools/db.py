#!/usr/bin/env python3
"""Class 2B director database tool (Python 3 standard library only).

The JSON files in ../data are the source of truth for the Class 2B arc.
Never read New_World.json during play: use this tool instead.

Lookups : loc, npc, quest, faction, lore, state, canon, thread, brief
Updates : add-npc, npc-seen, npc-note, agenda, quest-start, quest-obj,
          quest-end, ledger, fact, pc-add, pc-sheet, pos, time, clock-add, clock-done, turn,
          thread-reveal, add-area
          (every update except `turn` needs --turn N and --evidence "...")
Checks  : check-prompt <file or ->

Player character sheets (pronouns, power, background, notes) come from the user;
the director never derives them from story output. Set them with pc-add or pc-sheet.

Set CLASS2B_DATA=/some/dir to run against a copy of the data directory.
"""
import argparse
import difflib
import json
import os
import re
import sys
import textwrap
import unicodedata
from pathlib import Path

DATA = Path(os.environ.get("CLASS2B_DATA") or Path(__file__).resolve().parent.parent / "data")
PROMPT_LIMIT = 700
WEEKDAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]  # Day 1 = Saturday
SPECIALIZATIONS = ["Rescue", "Support", "Strike", "Investigation", "Media", "Agency Operations"]
OBJ_STATUSES = ["pending", "active", "hidden", "done", "failed", "skipped"]
OPEN_OBJ = ("pending", "active")  # objectives still to do (hidden ones are not yet revealed)
PC_SHEET_FIELDS = ("pronouns", "power", "background", "notes")
SHAREHOUSE = "Sakura Lane Sharehouse"
START_AREA = "building-entrance"
ACT_STARTS = {1: 1, 2: 8, 3: 43, 4: 78}  # first day of each act (arc-bible.md section 3)


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------
def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def norm(s):
    """Lowercase, strip accents and punctuation noise for matching."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[\"'`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def slug(s):
    return re.sub(r"[\s_]+", "-", norm(s))


class Store:
    """Loads JSON files lazily and writes only the ones that changed."""

    def __init__(self):
        self.cache = {}
        self.dirty = set()

    def get(self, name):
        if name not in self.cache:
            p = DATA / f"{name}.json"
            if not p.exists():
                die(f"missing data file: {p}")
            with open(p, encoding="utf-8") as f:
                self.cache[name] = json.load(f)
        return self.cache[name]

    def touch(self, name):
        self.get(name)
        self.dirty.add(name)

    def commit(self, cmd, turn, evidence, summary):
        """The single write path: logs the change, then writes every dirty file."""
        state = self.get("state")
        state.setdefault("changelog", []).append(
            {"turn": turn, "cmd": cmd, "summary": summary, "evidence": evidence}
        )
        self.dirty.add("state")
        for name in sorted(self.dirty):
            tmp = DATA / f"{name}.json.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.cache[name], f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, DATA / f"{name}.json")
        print(f"[{cmd}] turn {turn}: {summary}")
        if evidence:
            print(f"  evidence: {evidence}")
        print(f"  wrote: {', '.join(sorted(n + '.json' for n in self.dirty))}")
        self.dirty.clear()


S = Store()


def score(query, label):
    q, l = norm(query), norm(label)
    if not q or not l:
        return 0.0
    if q == l:
        return 1.0
    if l.startswith(q) or q.startswith(l) and len(l) >= 4:
        return 0.95
    qt, lt = q.split(), l.split()
    if all(any(t == x or x.startswith(t) for x in lt) for t in qt):
        return 0.9
    if q in l:
        return 0.85
    r = difflib.SequenceMatcher(None, q, l).ratio()
    for x in lt:
        r = max(r, difflib.SequenceMatcher(None, q, x).ratio() * 0.9)
    return r if r >= 0.6 else 0.0


def rank(query, items, labels=lambda k: [k]):
    """items: iterable of keys. labels(key) -> list of strings to match. Returns [(score, key)]."""
    out = []
    for k in items:
        best = max((score(query, lab) for lab in labels(k) if lab), default=0.0)
        if best:
            out.append((best, k))
    out.sort(key=lambda t: (-t[0], t[1]))
    return out


def pick(query, items, labels=lambda k: [k], what="match", strict=False):
    """Best single match or exit. strict: must be unambiguous (used by update commands)."""
    r = rank(query, items, labels)
    if not r:
        die(f'no {what} matches "{query}"', 2)
    if strict and len(r) > 1 and r[0][0] < 1.0 and r[1][0] >= r[0][0] - 0.05:
        die(f'"{query}" is ambiguous: ' + ", ".join(k for _, k in r[:6]), 2)
    return r[0][1], r


def others(r, n=5):
    rest = [k for _, k in r[1:n + 1]]
    if rest:
        print(f"\nOther matches: {', '.join(rest)}")


def short(s, n=110):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 3].rstrip() + "..."


def wrap(label, text, indent=2):
    if text in (None, "", [], {}):
        return
    print(f"{' ' * indent}{label}: {text}")


# ----------------------------------------------------------------------------
# domain helpers
# ----------------------------------------------------------------------------
def cast():
    return S.get("cast")


def world_npcs():
    return S.get("world-npcs")


def npc_labels(n):
    def f(key):
        e = cast().get(key) or world_npcs().get(key) or {}
        labs = [key, e.get("alias") or ""]
        if e.get("gender") or e.get("kind") in ("world",):  # individual: allow first/last name
            labs += [t for t in key.split() if len(t) >= 3]
        return labs
    return f


def find_npc(query, strict=False):
    """Returns (file_name, key, entry). Searches cast.json then world-npcs.json."""
    keys = list(cast())
    r = rank(query, keys, npc_labels(None))
    if r:
        key, rr = pick(query, keys, npc_labels(None), "NPC", strict)
        return "cast", key, cast()[key], rr
    wkeys = list(world_npcs())
    r = rank(query, wkeys, lambda k: [k])
    if r:
        key, rr = pick(query, wkeys, lambda k: [k], "NPC", strict)
        return "world-npcs", key, world_npcs()[key], rr
    die(f'no NPC matches "{query}" (cast.json, world-npcs.json)', 2)


def locations():
    return S.get("locations")


def resolve_place(loc, area=None):
    """Exact (normalized) location/area lookup. Refuses unknown places."""
    L = locations()
    names = {norm(k): k for k in L}
    key = names.get(norm(loc))
    if not key:
        sug = [k for _, k in rank(loc, L)[:5]]
        die(f'unknown location "{loc}": not in locations.json. No new locations are allowed.'
            + (f" Did you mean: {', '.join(sug)}?" if sug else ""), 3)
    if area is None:
        return key, None
    areas = L[key]["areas"]
    a = {slug(x): x for x in areas}.get(slug(area))
    if not a:
        sug = [k for _, k in rank(area, areas)[:6]]
        die(f'unknown area "{area}" in "{key}". Areas: {", ".join(areas)}'
            + (f" (did you mean: {', '.join(sug)}?)" if sug else ""), 3)
    return key, a


def act_for_day(day):
    """Act (1 to 4) that a story day falls in. Days past 112 stay in act 4."""
    return max(a for a, start in ACT_STARTS.items() if day >= start)


def current_act(st):
    """state.json `act` (kept in step with `day` by the time command); derived from the day if missing."""
    return st.get("act") or act_for_day(st["day"])


def get_state_turn():
    return S.get("state")["turn"]


def check_turn(t):
    if t < 1:
        die("--turn must be 1 or more")
    cur = get_state_turn()
    if t > cur + 1:
        die(f"--turn {t} is ahead of the log (state.turn = {cur}). A fact can only come from a turn that has happened.")


def block_for(clock, blocks):
    for b in blocks:
        s, e = b["start"], b["end"]
        if s <= clock <= e:
            return b["name"]
    return None


def minutes_since_dawn(clock):
    h, m = map(int, clock.split(":"))
    return (h * 60 + m - 5 * 60) % (24 * 60)  # Day starts at 05:00 (Dawn)


def band_for(value):
    for b in S.get("ledger")["hint_bands"]:
        lo, hi = b.get("min"), b.get("max")
        if (lo is None or value >= lo) and (hi is None or value <= hi):
            return b
    return None


def next_id(prefix, items):
    n = 1 + max([int(re.sub(r"\D", "", i["id"]) or 0) for i in items] + [0])
    return f"{prefix}{n:03d}"


# ----------------------------------------------------------------------------
# lookups
# ----------------------------------------------------------------------------
def cmd_loc(a):
    L = locations()
    key, r = pick(a.name, L, what="location")
    loc = L[key]
    if a.area:
        areas = loc["areas"]
        akey = {slug(x): x for x in areas}.get(slug(a.area))
        if not akey:
            ar = rank(a.area, areas)
            if not ar:
                die(f'no area matches "{a.area}" in {key}. Areas: {", ".join(areas)}', 2)
            akey = ar[0][1]
        ar = areas[akey]
        print(f"{key} / {akey}")
        wrap("description", ar["description"])
        if ar.get("added_turn") is not None:
            wrap("added", f"turn {ar['added_turn']}  [evidence: {ar.get('evidence')}]")
        print("  paths:")
        for p in ar["paths"]:
            mark = "" if p in areas else "  (not an area of this location)"
            print(f"    - {p}{mark}")
        here = [pc for pc in S.get("state")["player_characters"] if pc["location"] == key and pc["area"] == akey]
        if here:
            print("  player characters here: " + ", ".join(pc["name"] for pc in here))
        return
    print(key)
    wrap("region", loc["region"])
    wrap("basicInfo", loc["basicInfo"])
    wrap("hiddenInfo (director only)", loc["hiddenInfo"])
    wrap("factions", ", ".join(loc["factions"]))
    wrap("visualTags", ", ".join(loc["visualTags"]))
    print(f"  areas ({len(loc['areas'])}):")
    for aid, ar in loc["areas"].items():
        print(f"    - {aid}: {short(ar['description'], 100)}"
              + (f"  [added turn {ar['added_turn']}]" if ar.get("added_turn") is not None else ""))
    print(f'  (use: loc "{key}" <area> for one area with its paths)')
    others(r)


def print_npc(file, key, e):
    status = e.get("status", "?")
    head = f"{key}" + (f' "{e["alias"]}"' if e.get("alias") else "")
    print(f"{head}  [{status}; {file}.json]")
    if file == "cast":
        wrap("role", e.get("role"))
        bits = [x for x in (f"age {e['age']}" if e.get("age") else "", e.get("gender") or "") if x]
        wrap("who", ", ".join(bits))
        wrap("power", e.get("power"))
        wrap("room", e.get("room"))
        wrap("placement", e.get("placement"))
        if e.get("location"):
            wrap("location", f"{e['location']}/{e.get('area') or ''}")
        wrap("debut plan", e.get("debut"))
        wrap("intro_line", e.get("intro_line"))
        wrap("visual", e.get("visual"))
        wrap("hook", e.get("hook"))
        wrap("personality", e.get("personality"))
        vc = e.get("voice_card") or {}
        wrap("voice", vc.get("style"))
        wrap("sample", f'"{vc["sample_line"]}"' if vc.get("sample_line") else "")
        wrap("want", e.get("want"))
        wrap("need", e.get("need"))
        wrap("fear", e.get("fear"))
        ag = e.get("agenda") or {}
        wrap("agenda.want", ag.get("want"))
        wrap("agenda.next", ag.get("next_move"))
        if ag.get("source_turn"):
            wrap("agenda updated", f"turn {ag['source_turn']}: {ag.get('evidence', '')}")
        for n, note in (e.get("relationships") or {}).items():
            print(f"  rel {n}: {note}")
        wrap("romance_eligible", e.get("romance_eligible"))
        wrap("personal quest", e.get("personal_quest"))
        wrap("hidden (director only)", e.get("hidden"))
        wrap("notes", e.get("notes"))
        wrap("palette", ", ".join(e.get("palette") or []))
        for mv in e.get("signature_moves") or []:
            print(f"  move: {mv}")
        wrap("full release", e.get("full_release"))
        for act, beat in (e.get("arc_beats") or {}).items():
            print(f"  arc {act}: {beat}")
        for end, text in (e.get("endings") or {}).items():
            print(f"  ending {end}: {text}")
        for q in e.get("quotes") or []:
            print(f"  quote: {q}")
        wrap("portrait prompt", e.get("portrait_prompt"))
        vs = e.get("villain_sheet")
        if vs:
            print("  villain sheet:")
            for k, v in vs.items():
                wrap(k, v, 4)
        wrap("first_seen_turn", e.get("first_seen_turn"))
    else:
        for k in ("type", "faction", "currentLocation", "currentArea", "basicInfo", "visualDescription",
                  "personality", "worldVoiceId", "first_seen_turn"):
            v = e.get(k)
            wrap(k, ", ".join(v) if isinstance(v, list) else v)
    for n in e.get("canon_notes") or []:
        print(f"  note (turn {n.get('turn')}): {n.get('note')}  [evidence: {n.get('evidence')}]")


def cmd_npc(a):
    file, key, e, rr = find_npc(a.name)
    print_npc(file, key, e)
    others(rr)


def cmd_quest(a):
    Q = S.get("quests")
    key, r = pick(a.name, Q, what="quest")
    q = Q[key]
    print(f'"{key}"  [{q["status"]}]  act {q["act"]}, {q["type"]}')
    for k in ("trigger", "giver"):
        wrap(k, q[k])
    wrap("where", f"{q['location']}/{q['area']}")
    print("  objectives:")
    for o in q["objectives"]:
        print(f"    [{o['status']}] {o['id']}: {o['text']}")
    for k in ("success", "fail", "standing_effect", "reward", "seed_line", "seed_update", "notes"):
        wrap(k, q.get(k))
    wrap("started_turn", q.get("started_turn"))
    wrap("ended_turn", q.get("ended_turn"))
    for l in q.get("log") or []:
        print(f"  log turn {l['turn']}: {l['event']}  [evidence: {l.get('evidence')}]")
    others(r)


def cmd_faction(a):
    F = S.get("factions")
    key, r = pick(a.name, F, what="faction")
    f = F[key]
    print(key)
    for k, v in f.items():
        if k != "name":
            wrap(k, v)
    others(r)


def cmd_lore(a):
    lore = S.get("lore")
    if a.full:
        key, _ = pick(a.full, lore, what="lore key")
        print(f"# {key}\n")
        print(lore[key])
        return
    terms = [norm(t) for t in a.terms if norm(t)]
    if not terms:
        die("give search terms, or --full KEY")
    res = []
    for k, text in lore.items():
        lk, lt = norm(k), norm(text)
        sc, hits = 0.0, 0
        for t in terms:
            kh = lk.count(t)
            th = len(re.findall(r"\b" + re.escape(t), lt))
            if kh or th:
                hits += 1
            sc += 5 * min(kh, 2) + min(th, 6)
        if hits:
            if hits == len(terms):
                sc *= 1.5
            res.append((sc, k))
    res.sort(key=lambda t: (-t[0], t[1]))
    if not res:
        print("no lore matches")
        return
    for sc, k in res[: a.limit]:
        text = re.sub(r"\s+", " ", lore[k])
        m = None
        for t in sorted(terms, key=len, reverse=True):
            m = re.search(re.escape(t), text, re.I)
            if m:
                break
        i = m.start() if m else 0
        lo = max(0, i - 70)
        snip = ("..." if lo else "") + text[lo: lo + 190] + ("..." if lo + 190 < len(text) else "")
        print(f"- {k}  (score {sc:.1f})\n    {snip}")
    if len(res) > a.limit:
        print(f"... {len(res) - a.limit} more (use --limit)")
    print('\nFull text: lore --full KEY')


def sheet_line(pc, n=70):
    """Compact one-line view of the user-provided character sheet ('' if empty)."""
    return " | ".join(f"{k}: {short(pc[k], n)}" for k in PC_SHEET_FIELDS if pc.get(k))


def cmd_state(a):
    st, led = S.get("state"), S.get("ledger")
    print(f"Turn {st['turn']} | Day {st['day']} {st['weekday']} (Act {current_act(st)}) | {st['time_block']} {st['clock']} | "
          f"party split: {'YES' if st['party_split'] else 'no'}")
    print("Player characters:")
    if not st["player_characters"]:
        print("  (none yet: use pc-add)")
    for pc in st["player_characters"]:
        print(f"  - {pc['name']} ({pc['player']}) room {pc['room']}: {pc['location']}/{pc['area']}"
              f"{', ' + pc['activity'] if pc.get('activity') else ''}"
              f"{' [' + pc['placement'] + ']' if pc.get('placement') else ''}")
        sheet = sheet_line(pc)
        if sheet:
            print(f"      sheet: {sheet}")
    c = cast()
    inplay = [n for n, e in c.items() if e.get("status") == "in_play"]
    planned = [n for n, e in c.items() if e.get("status") == "planned"]
    print(f"NPCs in play ({len(inplay)}): {', '.join(inplay) or '-'}")
    print(f"Introduced (state): {', '.join(st['introduced_npcs']) or '-'}")
    print(f"NPCs still planned: {len(planned)}")
    Q = S.get("quests")
    print("Active quests:")
    if not st["active_quests"]:
        print("  -")
    for qn in st["active_quests"]:
        q = Q.get(qn, {})
        objs = q.get("objectives", [])
        done = sum(1 for o in objs if o["status"] == "done")
        nxt = next((o for o in objs if o["status"] in OPEN_OBJ), None)
        print(f"  - {qn} (since turn {q.get('started_turn')}, {done}/{len(objs)} objectives)"
              + (f"; next: {short(nxt['text'], 70)}" if nxt else ""))
    print("Open clocks:")
    if not st["open_clocks"]:
        print("  -")
    for ck in st["open_clocks"]:
        print(f"  - {ck['name']}: due day {ck['due_day']} ({ck['due_day'] - st['day']} days left) {ck.get('note', '')}")
    band = band_for(led["current"])
    print(f"Standing (director only): {led['current']} (start {led['start']}, {len(led['entries'])} entries)"
          + (f"; band {band['label']}" if band else ""))
    if band:
        print(f"  Shimazu would sound: {band['shimazu']}")
        print(f"  Yuto would say: {band['yuto']}")
    debt = st["debt"]
    print(f"Debt (hidden): principal {debt['principal']}, due {debt['due']} by Day {debt['due_day']}")
    upcoming = [m for m in st["calendar"] if m.get("to_day", m["day"]) >= st["day"]][:4]
    print("Next milestones:")
    for m in upcoming:
        rng = f"{m['day']}-{m['to_day']}" if m.get("to_day") else str(m["day"])
        extra = f" (latest {m['latest_day']})" if m.get("latest_day") else ""
        print(f"  - Day {rng}{extra}: {m['name']}")
    flags = {}
    for f in S.get("canon")["facts"]:
        if f["subject"].lower().startswith("flag"):
            flags[f["subject"]] = f["fact"]
    if flags:
        print("Flags: " + "; ".join(f"{k}={v}" for k, v in flags.items()))
    print(f"Canon facts: {len(S.get('canon')['facts'])}; turns logged: {len(S.get('turns'))}")
    if st.get("changelog"):
        last = st["changelog"][-1]
        print(f"Last change: turn {last['turn']} {last['cmd']}: {last['summary']}")


def cmd_canon(a):
    q = norm(" ".join(a.search))
    if not q:
        die("give a search term")
    toks = q.split()
    hits = 0

    def match(*texts):
        blob = norm(" ".join(str(t) for t in texts))
        return all(t in blob for t in toks)
    for f in S.get("canon")["facts"]:
        if match(f["subject"], f["fact"], f["evidence"]):
            hits += 1
            print(f"- {f['id']} (turn {f['turn']}) {f['subject']}: {f['fact']}\n    evidence: {f['evidence']}")
    for src in (cast(), world_npcs()):
        for n, e in src.items():
            for note in e.get("canon_notes") or []:
                if match(n, note["note"], note.get("evidence", "")):
                    hits += 1
                    print(f"- note on {n} (turn {note['turn']}): {note['note']}\n    evidence: {note.get('evidence')}")
    if not hits:
        print("no canon matches")


# ----------------------------------------------------------------------------
# brief: one compact character card for writing a turn (read-only)
# ----------------------------------------------------------------------------
BRIEF_WIDTH = 140
MISSING = "(missing in cast.json)"


def name_forms(key, alias=None):
    """Normalized names that count as a mention of a person: full name, alias, and name tokens (3+ letters).
    When the entry has an alias (e.g. Park Seo-yeon "Sunny"), the leading token is left out as too generic."""
    toks = norm(key).split()
    if alias and len(toks) > 1:
        toks = toks[1:]
    forms = {norm(key)} | {t for t in toks if len(t) >= 3}
    if alias:
        forms.add(norm(alias))
    return forms


def mentions_any(text, forms):
    t = norm(text)
    return any(re.search(r"(?<![a-z0-9])" + re.escape(f) + r"(?![a-z0-9])", t) for f in forms)


def canon_items():
    """Every canon fact and NPC canon note as (turn, order, label, text, searchable text)."""
    items, n = [], 0
    for f in S.get("canon")["facts"]:
        n += 1
        t = f"{f['subject']}: {f['fact']}"
        items.append((f["turn"], n, f"fact {f['id']}", t, t))
    for src in (cast(), world_npcs()):
        for who, e in src.items():
            for note in e.get("canon_notes") or []:
                n += 1
                items.append((note["turn"], n, f"note on {who}", note["note"], f"{who} {note['note']}"))
    return sorted(items)


def brief_row(label, text, indent=2, width=BRIEF_WIDTH):
    """One line: `label: text`, cut with an ellipsis to fit the width."""
    print(" " * indent + short(f"{label}: {text}", width - indent))


def brief_wrapped(label, text, indent=2, width=BRIEF_WIDTH, max_lines=3):
    lines = textwrap.wrap(f"{label}: {text}", width=width - indent, subsequent_indent="  ")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = short(lines[-1], width - indent - 3) + "..."
    for l in lines:
        print(" " * indent + l)


def cmd_brief(a):
    file, key, e, _ = find_npc(a.name)
    st = S.get("state")
    act, day = current_act(st), st["day"]
    forms = name_forms(key, e.get("alias"))
    print(short(f"BRIEF {key} | {e.get('role') or e.get('type') or '?'} | status {e.get('status', '?')} "
                f"| Act {act}, Day {day} {st['weekday']}", BRIEF_WIDTH))
    # where
    w = world_npcs().get(key) or {}
    if e.get("location"):
        where = f"{e['location']}/{e.get('area') or '?'} (last recorded)"
    elif w.get("currentLocation"):
        where = f"{w['currentLocation']}/{w.get('currentArea') or '?'} (world-file base; no position recorded)"
    else:
        where = "unknown"
    brief_row("where", where, 0)
    # voice
    vc = e.get("voice_card") or {}
    brief_wrapped("voice", vc.get("style") or MISSING, max_lines=4)
    brief_row("sample", f'"{vc["sample_line"]}"' if vc.get("sample_line") else MISSING)
    # psychology
    for lab, fld in (("want", "want"), ("need", "need"), ("fear", "fear"), ("lie", "lie"),
                     ("stress", "stress"), ("comfort", "comfort"), ("anger", "anger")):
        brief_row(lab, e.get(fld) or MISSING)
    lc = " | ".join(f"{lab}: {e.get(f) or 'not set'}" for lab, f in (("laughs", "laughs"), ("cries", "cries")))
    brief_row("mood", lc)
    if e.get("newcomer_stance") or e.get("trust_earned_by"):
        brief_row("newcomers", f"{(e.get('newcomer_stance') or MISSING).rstrip('.')}; trust: {e.get('trust_earned_by') or MISSING}")
    else:
        brief_row("newcomers", MISSING)
    # arc beat
    beats = e.get("arc_beats") or {}
    brief_wrapped(f"ARC BEAT, act {act}", beats.get(f"act_{act}") or "(no beat for this act in cast.json)", 0, max_lines=2)
    # ladders
    T = S.get("threads")
    mine = [(k, t) for k, t in T.items() if key in (t.get("npcs") or [])]
    if not mine:
        print("LADDERS: no arc thread tied to them (personal secrets live in cast.json `hidden`: do not say)")
    for k, t in mine:
        done = sum(1 for x in t["steps"] if x["status"] == "revealed")
        print(f"LADDER {k} [{done}/{len(t['steps'])} revealed]")
        for x in t["steps"]:
            if x["status"] == "revealed":
                print("  " + short(f"revealed {x['step']}. {x['reveal']}", BRIEF_WIDTH - 2))
            else:
                print("  " + short(f"HIDDEN {x['step']} (act {x['earliest_act']}) {x['reveal']}", BRIEF_WIDTH - 17)
                      + "  DO NOT SAY")
    # relationships
    items = canon_items()
    pcs = [p["name"] for p in st["player_characters"]]
    print("RELATIONSHIPS (bond + latest canon about the pair)")
    for other, note in (e.get("relationships") or {}).items():
        extra = ""
        oe = cast().get(other) or world_npcs().get(other)
        if oe is not None:
            of = name_forms(other, (oe or {}).get("alias"))
            hit = [i for i in items if mentions_any(i[4], forms) and mentions_any(i[4], of)]
            if hit:
                extra = f" | t{hit[-1][0]}: {hit[-1][3]}"
        brief_row(other, f"{note}{extra}", 2, BRIEF_WIDTH)
    for pc in pcs:
        pf = name_forms(pc)
        hit = [i for i in items if mentions_any(i[4], forms) and mentions_any(i[4], pf)]
        if hit:
            txt = f"t{hit[-1][0]}: {hit[-1][3]}"
        else:
            txt = f"no history yet; newcomer stance: {e.get('newcomer_stance') or MISSING}"
        brief_row(f"PC {pc}", txt)
    # recent canon
    mine_items = [i for i in items if mentions_any(i[4], forms)][-3:]
    if mine_items:
        print("LAST CANON (newest last)")
        for turn, _, label, text, _blob in mine_items:
            brief_row(f"t{turn} {label}", text)
    else:
        print("LAST CANON: none yet")
    # won't do yet
    wd = (e.get("wont_do_yet") or {}).get(f"act_{act}")
    if wd:
        brief_wrapped("WON'T DO YET", "; ".join(wd), 0, max_lines=3)
    else:
        print(f"WON'T DO YET: {MISSING} (wont_do_yet.act_{act})")


# ----------------------------------------------------------------------------
# updates
# ----------------------------------------------------------------------------
def need_ev(a):
    if not (a.evidence or "").strip():
        die("--evidence must not be empty")
    check_turn(a.turn)


def add_introduced(name):
    st = S.get("state")
    if name in st["introduced_npcs"]:
        return False
    st["introduced_npcs"].append(name)
    S.touch("state")
    return True


def cmd_add_npc(a):
    need_ev(a)
    dup = rank(a.name, list(cast()), lambda k: [k, cast()[k].get("alias") or ""])
    if dup and dup[0][0] >= 0.95:
        die(f'"{a.name}" is already in cast.json as "{dup[0][1]}"; use npc-seen / npc-note')
    if any(norm(a.name) == norm(k) for k in world_npcs()):
        die(f'"{a.name}" is already a world NPC; use npc-seen / npc-note')
    loc = area = None
    if a.area and not a.location:
        die("--area needs --location")
    if a.location:
        loc, area = resolve_place(a.location, a.area)
    e = {
        "name": a.name, "alias": a.alias, "kind": "voyage-generated", "role": "voyage-generated",
        "age": a.age, "gender": a.gender, "power": a.power, "placement": None,
        "intro_line": "", "visual": a.visual or "", "personality": a.personality or "",
        "voice_card": {"style": "", "sample_line": ""}, "want": "", "fear": "",
        "agenda": {"want": "", "next_move": ""}, "relationships": {}, "romance_eligible": False,
        "type": a.type, "faction": a.faction,
        "location": loc, "area": area,
        "status": "in_play", "first_seen_turn": a.turn, "source_turn": a.turn, "evidence": a.evidence,
        "canon_notes": [],
    }
    cast()[a.name] = e
    S.touch("cast")
    add_introduced(a.name)
    S.commit("add-npc", a.turn, a.evidence, f'added "{a.name}" (voyage-generated, in_play)')


def cmd_npc_seen(a):
    need_ev(a)
    file, key, e, _ = find_npc(a.name, strict=True)
    if e.get("status") == "in_play" and e.get("first_seen_turn") is not None:
        print(f'"{key}" is already in play since turn {e["first_seen_turn"]}; nothing changed.')
        if add_introduced(key):
            S.commit("npc-seen", a.turn, a.evidence, f'"{key}" already in play; recorded as introduced')
        return
    e["status"] = "in_play"
    if e.get("first_seen_turn") is None:
        e["first_seen_turn"] = a.turn
    S.touch(file)
    add_introduced(key)
    S.commit("npc-seen", a.turn, a.evidence, f'"{key}" -> in_play, first_seen_turn {e["first_seen_turn"]}')


def cmd_npc_note(a):
    need_ev(a)
    file, key, e, _ = find_npc(a.name, strict=True)
    e.setdefault("canon_notes", []).append({"turn": a.turn, "note": " ".join(a.text), "evidence": a.evidence})
    S.touch(file)
    S.commit("npc-note", a.turn, a.evidence, f'note added to "{key}": {short(" ".join(a.text), 80)}')


def cmd_agenda(a):
    need_ev(a)
    if a.want is None and a.next is None:
        die("give --want and/or --next")
    file, key, e, _ = find_npc(a.name, strict=True)
    ag = e.setdefault("agenda", {"want": "", "next_move": ""})
    old = dict(ag)
    if a.want is not None:
        ag["want"] = a.want
    if a.next is not None:
        ag["next_move"] = a.next
    ag["source_turn"], ag["evidence"] = a.turn, a.evidence
    S.touch(file)
    S.commit("agenda", a.turn, a.evidence,
             f'"{key}" agenda: want "{short(ag["want"], 60)}"; next "{short(ag["next_move"], 60)}" (was: {short(old.get("next_move", ""), 40)})')


def find_quest(q):
    key, _ = pick(q, S.get("quests"), what="quest", strict=True)
    return key, S.get("quests")[key]


def cmd_quest_start(a):
    need_ev(a)
    key, q = find_quest(a.name)
    if q["status"] != "planned":
        die(f'quest "{key}" is already {q["status"]}')
    q["status"], q["started_turn"] = "active", a.turn
    q["log"].append({"turn": a.turn, "event": "started", "evidence": a.evidence})
    st = S.get("state")
    if key not in st["active_quests"]:
        st["active_quests"].append(key)
    S.touch("quests")
    S.touch("state")
    S.commit("quest-start", a.turn, a.evidence, f'quest "{key}" planned -> active')


def cmd_quest_obj(a):
    need_ev(a)
    key, q = find_quest(a.name)
    if q["status"] != "active":
        die(f'quest "{key}" is {q["status"]}; start it first (quest-start)')
    ids = [o["id"] for o in q["objectives"]]
    oid = a.obj_id if a.obj_id in ids else (a.obj_id if a.obj_id.startswith("o") else f"o{a.obj_id}")
    ob = next((o for o in q["objectives"] if o["id"] == oid), None)
    if not ob:
        die(f'no objective "{a.obj_id}" in "{key}". Ids: {", ".join(ids)}')
    old = ob["status"]
    ob["status"] = a.status
    q["log"].append({"turn": a.turn, "event": f"{oid} {old} -> {a.status}", "evidence": a.evidence})
    S.touch("quests")
    S.commit("quest-obj", a.turn, a.evidence, f'"{key}" {oid}: {old} -> {a.status}')


def cmd_quest_end(a):
    need_ev(a)
    key, q = find_quest(a.name)
    if q["status"] != "active":
        die(f'quest "{key}" is {q["status"]}; only an active quest can end')
    q["status"], q["ended_turn"] = a.result, a.turn
    q["log"].append({"turn": a.turn, "event": a.result, "evidence": a.evidence})
    st = S.get("state")
    if key in st["active_quests"]:
        st["active_quests"].remove(key)
    S.touch("quests")
    S.touch("state")
    S.commit("quest-end", a.turn, a.evidence, f'quest "{key}" active -> {a.result}')


def cmd_ledger(a):
    need_ev(a)
    if not re.fullmatch(r"[+-]?\d+", a.delta):
        die('delta must look like +5 or -10')
    d = int(a.delta)
    led, st = S.get("ledger"), S.get("state")
    led["current"] += d
    led["entries"].append({"turn": a.turn, "day": st["day"], "change": d, "reason": " ".join(a.reason),
                           "total": led["current"], "evidence": a.evidence})
    S.touch("ledger")
    band = band_for(led["current"])
    S.commit("ledger", a.turn, a.evidence,
             f'Standing {d:+d} -> {led["current"]} ({" ".join(a.reason)}); hint band: {band["label"] if band else "?"}')


def cmd_fact(a):
    need_ev(a)
    c = S.get("canon")
    fid = next_id("f", c["facts"])
    c["facts"].append({"id": fid, "turn": a.turn, "subject": a.subject, "fact": " ".join(a.text), "evidence": a.evidence})
    S.touch("canon")
    S.commit("fact", a.turn, a.evidence, f'{fid} {a.subject}: {short(" ".join(a.text), 90)}')


def cmd_pc_add(a):
    need_ev(a)
    st = S.get("state")
    if any(norm(p["name"]) == norm(a.name) for p in st["player_characters"]):
        die(f'player character "{a.name}" already exists')
    L = locations()[SHAREHOUSE]["areas"]
    room = {slug(x): x for x in L}.get(slug(a.room))
    if not room or not room.endswith("-bedroom"):
        die(f'room "{a.room}" is not a bedroom of {SHAREHOUSE}. Bedrooms: '
            + ", ".join(x for x in L if x.endswith("-bedroom")), 3)
    pc_rooms = ["courtyard-bedroom", "garden-bedroom", "lilac-bedroom", "river-bedroom"]
    if room not in pc_rooms:
        print(f"warning: {room} is normally an NPC housemate's room (PC rooms: {', '.join(pc_rooms)})")
    if any(p["room"] == room for p in st["player_characters"]):
        die(f"room {room} already has a player character")
    loc, area = resolve_place(a.location or SHAREHOUSE, a.area or START_AREA)
    pc = {"name": a.name, "player": a.player, "room": room, "location": loc,
          "area": area, "activity": a.activity or "", "placement": None}
    for f in PC_SHEET_FIELDS:
        pc[f] = (getattr(a, f) or "").strip()
    st["player_characters"].append(pc)
    update_split(st)
    S.touch("state")
    S.commit("pc-add", a.turn, a.evidence, f'player character "{a.name}" ({a.player}), room {room}, at {loc}/{area}'
             + (f"; sheet: {sheet_line(pc, 40)}" if sheet_line(pc) else ""))


def cmd_pc_sheet(a):
    """Show or update a player character's sheet. The sheet comes from the user, never from story output."""
    st = S.get("state")
    if not st["player_characters"]:
        die("no player characters yet (use pc-add first)")
    pc_key, _ = pick(a.name, [p["name"] for p in st["player_characters"]], what="player character", strict=True)
    pc = next(p for p in st["player_characters"] if p["name"] == pc_key)
    given = {f: getattr(a, f) for f in PC_SHEET_FIELDS if getattr(a, f) is not None}
    if not given:
        print(f"{pc_key} ({pc['player']}), room {pc['room']}")
        for f in PC_SHEET_FIELDS:
            wrap(f, pc.get(f))
        if not any(pc.get(f) for f in PC_SHEET_FIELDS):
            print("  (no sheet yet: ask the user, then pc-sheet --pronouns/--power/--background/--notes)")
        return
    if a.turn is None:
        die("--turn is required when updating a sheet")
    if not a.evidence:
        a.evidence = "sheet provided by the user"
    need_ev(a)
    for f, v in given.items():
        pc[f] = v.strip()
    S.touch("state")
    S.commit("pc-sheet", a.turn, a.evidence, f'"{pc_key}" sheet updated ({", ".join(given)}): {sheet_line(pc, 40)}')


def update_split(st):
    locs = {pc["location"] for pc in st["player_characters"]}
    new = len(locs) > 1
    if new != st["party_split"]:
        print(f"party_split -> {new}")
    st["party_split"] = new


def cmd_pos(a):
    need_ev(a)
    loc, area = resolve_place(a.location, a.area)  # refuses unknown places first
    st = S.get("state")
    if not st["player_characters"]:
        die("no player characters yet (use pc-add first)")
    pc_key, _ = pick(a.pc, [p["name"] for p in st["player_characters"]], what="player character", strict=True)
    pc = next(p for p in st["player_characters"] if p["name"] == pc_key)
    old = f'{pc["location"]}/{pc["area"]}'
    pc["location"], pc["area"] = loc, area
    if a.activity is not None:
        pc["activity"] = a.activity
    if a.placement:
        pc["placement"] = a.placement
    update_split(st)
    S.touch("state")
    S.commit("pos", a.turn, a.evidence,
             f'{pc_key}: {old} -> {loc}/{area}' + (f', {pc["activity"]}' if pc.get("activity") else "")
             + f' | party_split={st["party_split"]}')


def cmd_time(a):
    need_ev(a)
    if a.day is None and a.block is None and a.clock is None:
        die("give --day, --block and/or --clock")
    st, w = S.get("state"), S.get("world")
    blocks = w["time"]["blocks"]
    day = a.day if a.day is not None else st["day"]
    if day < 1:
        die("--day must be 1 or more")
    block, clock = a.block, a.clock
    if clock is not None:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", clock):
            die("--clock must be HH:MM (24-hour)")
    if block is not None:
        bn = {norm(b["name"]): b for b in blocks}.get(norm(block))
        if not bn:
            die(f'unknown time block "{block}". Blocks: {", ".join(b["name"] for b in blocks)}')
        block = bn["name"]
        if clock is None:
            clock = bn["start"] if (a.day is not None or block != st["time_block"]) else st["clock"]
    if clock is not None:
        derived = block_for(clock, blocks)
        if block is None:
            block = derived
        elif derived != block:
            die(f"clock {clock} is in the {derived} block, not {block}")
    else:
        block, clock = st["time_block"], st["clock"]
    old = (st["day"], minutes_since_dawn(st["clock"]))
    new = (day, minutes_since_dawn(clock))
    if new < old and not a.allow_backward:
        die(f"time would move backward (Day {st['day']} {st['clock']} -> Day {day} {clock}); use --allow-backward only to correct a mistake")
    wd = WEEKDAYS[(day - 1) % 7]
    prev = f'Day {st["day"]} {st["weekday"]} {st["time_block"]} {st["clock"]}'
    old_act = current_act(st)
    st["day"], st["weekday"], st["time_block"], st["clock"] = day, wd, block, clock
    st["act"] = act_for_day(day)  # act always follows the day
    S.touch("state")
    S.commit("time", a.turn, a.evidence, f"{prev} -> Day {day} {wd} {block} {clock}"
             + (f" | act {old_act} -> {st['act']}" if st["act"] != old_act else ""))


def cmd_clock_add(a):
    need_ev(a)
    st = S.get("state")
    if any(norm(c["name"]) == norm(a.name) for c in st["open_clocks"]):
        die(f'clock "{a.name}" already exists')
    st["open_clocks"].append({"name": a.name, "due_day": a.due_day, "note": a.note or ""})
    S.touch("state")
    S.commit("clock-add", a.turn, a.evidence, f'clock "{a.name}" due day {a.due_day}')


def cmd_clock_done(a):
    need_ev(a)
    st = S.get("state")
    if not st["open_clocks"]:
        die("no open clocks")
    key, _ = pick(a.name, [c["name"] for c in st["open_clocks"]], what="clock", strict=True)
    st["open_clocks"] = [c for c in st["open_clocks"] if c["name"] != key]
    S.touch("state")
    S.commit("clock-done", a.turn, a.evidence, f'clock "{key}" closed')


def read_arg_text(v):
    if v is None:
        return None
    if v == "-":
        return sys.stdin.read().rstrip("\n")
    if v.startswith("@"):
        p = Path(v[1:])
        if not p.exists():
            die(f"no such file: {p}")
        return p.read_text(encoding="utf-8").rstrip("\n")
    return v


def cmd_turn(a):
    st, turns = S.get("state"), S.get("turns")
    if a.n != st["turn"] + 1:
        die(f"turns are logged in order: next is {st['turn'] + 1}, got {a.n}")
    if any(t["turn"] == a.n for t in turns):
        die(f"turn {a.n} is already logged")
    prompt = read_arg_text(a.prompt)
    is_none = (prompt or "").strip().lower().startswith("none")
    if not is_none and len(prompt) > PROMPT_LIMIT:
        die(f"prompt is {len(prompt)} characters; the limit is {PROMPT_LIMIT}. Run check-prompt and shorten it.")
    entry = {"turn": a.n, "day": st["day"], "time": f'{st["time_block"]} {st["clock"]}',
             "inputs": read_arg_text(a.inputs), "prompt": prompt, "slips": read_arg_text(a.slips) or "",
             "notes": read_arg_text(a.notes) or ""}
    turns.append(entry)
    st["turn"] = a.n
    S.touch("turns")
    S.touch("state")
    plen = 0 if is_none else len(prompt)
    S.commit("turn", a.n, "", f"logged turn {a.n} (Day {st['day']} {entry['time']}); prompt {plen}/{PROMPT_LIMIT} chars")


# ----------------------------------------------------------------------------
# reveal ladders (data/threads.json) and area additions
# ----------------------------------------------------------------------------
def find_thread(query, strict=False):
    T = S.get("threads")
    key, r = pick(query, T, what="thread", strict=strict)
    return key, T[key], r


def next_step(t):
    return next((s for s in t["steps"] if s["status"] == "hidden"), None)


def cmd_thread(a):
    st, T = S.get("state"), S.get("threads")
    act, day = current_act(st), st["day"]
    if not a.name:
        print(f"Reveal ladders (Act {act}, Day {day}; director only):")
        for k, t in T.items():
            n = next_step(t)
            done = sum(1 for s in t["steps"] if s["status"] == "revealed")
            print(f"  - {k}: {done}/{len(t['steps'])} revealed"
                  + (f"; next: step {n['step']} (act {n['earliest_act']})" if n else "; complete"))
        print('  (use: thread "<name>" for the steps)')
        return
    key, t, r = find_thread(a.name)
    done = sum(1 for s in t["steps"] if s["status"] == "revealed")
    print(f"{key}  [{done}/{len(t['steps'])} revealed; now Act {act}, Day {day}]")
    wrap("summary", t.get("summary"))
    wrap("sources", t.get("sources"))
    print("  steps:")
    for s in t["steps"]:
        gate = f"; gate: {s['milestone_gate']}" if s.get("milestone_gate") else ""
        print(f"    {s['step']}. [{s['status']}] (act {s['earliest_act']}{gate}) {s['reveal']}")
        if s["status"] == "revealed":
            print(f"        revealed turn {s.get('revealed_turn')}, Day {s.get('revealed_day')}"
                  f"{' (FORCED)' if s.get('forced') else ''}: {s.get('evidence')}")
    n = next_step(t)
    if not n:
        print("  next revealable step: none (ladder complete)")
    elif n["earliest_act"] > act:
        print(f"  next revealable step: none yet. Step {n['step']} needs Act {n['earliest_act']} "
              f"(from Day {ACT_STARTS[n['earliest_act']]}); now Act {act}, Day {day}.")
    else:
        print(f"  next revealable step: {n['step']}. {n['reveal']}")
        if n.get("milestone_gate"):
            print(f"    gate first: {n['milestone_gate']} (reveal with --gate-met once it has happened)")
    others(r)


def cmd_thread_reveal(a):
    need_ev(a)
    key, t, _ = find_thread(a.name, strict=True)
    s = next((x for x in t["steps"] if x["step"] == a.step), None)
    if not s:
        die(f'"{key}" has no step {a.step}. Steps: {", ".join(str(x["step"]) for x in t["steps"])}')
    if s["status"] != "hidden":
        die(f'"{key}" step {a.step} is already {s["status"]}')
    st = S.get("state")
    act = current_act(st)
    problems = []
    if s["earliest_act"] > act:
        problems.append(f"step {a.step} needs Act {s['earliest_act']} (from Day {ACT_STARTS[s['earliest_act']]}); "
                        f"now Act {act}, Day {st['day']}")
    early = [x["step"] for x in t["steps"] if x["step"] < a.step and x["status"] == "hidden"]
    if early:
        problems.append("earlier step(s) still hidden: " + ", ".join(map(str, early)))
    if s.get("milestone_gate") and not a.gate_met:
        problems.append(f"milestone gate not confirmed: {s['milestone_gate']} (pass --gate-met once it has happened)")
    if problems and not a.force:
        die(f'refused to reveal "{key}" step {a.step}: ' + "; ".join(problems) + ". Use --force only to override on purpose.", 4)
    if problems:
        print("warning: --force overrides: " + "; ".join(problems))
    s["status"], s["revealed_turn"], s["revealed_day"], s["evidence"] = "revealed", a.turn, st["day"], a.evidence
    if problems:
        s["forced"] = True
    S.touch("threads")
    S.commit("thread-reveal", a.turn, a.evidence,
             f'"{key}" step {a.step} revealed: {short(s["reveal"], 80)}' + (" (FORCED)" if problems else ""))


def cmd_add_area(a):
    """Add a new area inside an existing location. Locations stay fixed; areas may be added from story output."""
    need_ev(a)
    loc, _ = resolve_place(a.location)  # refuses unknown locations
    desc = (a.desc or "").strip()
    if not desc:
        die("--desc must not be empty")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.area_id):
        die(f'area id "{a.area_id}" must be lowercase words joined by hyphens, e.g. bakery-corner')
    areas = locations()[loc]["areas"]
    if slug(a.area_id) in {slug(x) for x in areas}:
        die(f'"{loc}" already has an area "{a.area_id}"', 3)
    by_slug = {slug(x): x for x in areas}
    paths = []
    for p in [x.strip() for x in (a.paths or "").split(",") if x.strip()]:
        if slug(p) not in by_slug:
            die(f'--paths: "{p}" is not an existing area of "{loc}". Areas: {", ".join(areas)}', 3)
        paths.append(by_slug[slug(p)])
    areas[a.area_id] = {"description": desc, "paths": paths, "added_turn": a.turn, "evidence": a.evidence}
    S.touch("locations")
    S.commit("add-area", a.turn, a.evidence,
             f'area "{a.area_id}" added to "{loc}": {short(desc, 70)}' + (f" (paths: {', '.join(paths)})" if paths else ""))


# ----------------------------------------------------------------------------
# prompt checking
# ----------------------------------------------------------------------------
STOP = set("""
a an the and but or nor so yet if then else when while as at in on of to for from with without by about after before
during until into onto over under up down out off not no yes all both each every only just also still even more most
some any one two three four five six one first second third last next now here there this that these those it its
he she they them his her their we us you your i me my our who whom whose what which why how where
is are was were be been being do does did can could will would shall should may might must
start update open drop say says hold holds keep continue stay let make get give take put set use try
cut tone crew facts world day days week weeks weekend hour hours minute minutes night morning afternoon evening dawn noon midnight
monday tuesday wednesday thursday friday saturday sunday january february march april may june july august september october november december
warm tense light dark quiet loud soft dry calm slow fast bright cold tired gentle sharp easy hard heavy
dinner lunch breakfast tea class classes lesson lecture exam test review bout match round final
voyage player players narrator npc npcs quest quests scene scenes split regroup standing
sorry thanks thank please okay ok well oh ah hey hi hello
""".split())

EXTRA_KNOWN = [
    "Voyage", "Tokyo", "Japan", "Korea", "Korean", "Pulse", "Wi-Fi", "Nightshade", "Chikara", "Annex Cohort", "Nine Corners",
    "Lantern Coil", "Vice Principal", "Principal", "House Manager", "Ultra Force", "Battle Test", "Hollow Dogs",
    "Rescue", "Support", "Strike", "Investigation", "Media", "Agency Operations", "Day", "Days",
    "Late Night", "After Hours", "Edge Current", "Immovable", "Exploded View", "Rewind", "Main Character", "Slipstream",
    "Bastion", "Warm Hands", "Anchor Threads", "Tally Mark", "Seismic Seam", "Static Lock", "Mirror Crowd",
    "Shiokaze", "Iron Choir", "Long Play", "Prime Time", "Exodus", "Constitution", "Kagura of a Thousand Cuts", "Sunlit Cradle",
    "Stillwater Palm", "Riverbed", "Mountain Holds", "Railpin", "Scrapforge", "Polarity Lock", "Teardown",
    "Return to Sender", "Payback", "Tape Read", "Spotlight Step", "Fan Service", "Encore", "Going Live",
    "Tailwind", "Pull-Out", "Crosswind", "Clause", "Amendment", "Jurisdiction", "Severance", "Step-Cut", "Iris Line",
]


class Known:
    """Known-name matcher for check-prompt."""

    def __init__(self):
        self.names = {}  # normalized phrase -> category
        L = locations()
        for k in L:
            self._add_with_prefixes(k, "location")
        for k in S.get("factions"):
            self._add_with_prefixes(k, "faction")
        for k, q in S.get("quests").items():
            self._add_with_prefixes(k, "quest")
        for k, e in cast().items():
            self._add_npc(k, e)
        for k, e in world_npcs().items():
            self._add(k, "world npc")
        for pc in S.get("state")["player_characters"]:
            self._add(pc["name"], "player character")
            for t in pc["name"].split():
                self._add(t, "player character")
        for t in EXTRA_KNOWN:
            self._add_with_prefixes(t, "term")

    def _add(self, phrase, cat):
        p = norm(phrase)
        if p:
            self.names.setdefault(p, cat)

    def _add_with_prefixes(self, phrase, cat):
        toks = phrase.split()
        for i in range(1, len(toks) + 1):
            if i == 1 and norm(toks[0]) in STOP:
                continue
            self._add(" ".join(toks[:i]), cat)

    def _add_npc(self, key, e):
        cat = "in-play NPC" if e.get("status") == "in_play" else ("world NPC" if e.get("status") == "world" else "planned NPC")
        self._add(key, cat)
        for al in (e.get("alias") or "").split("/"):
            self._add(al.strip(), cat)
        if e.get("gender") or e.get("kind") == "world":
            for t in key.split():
                self._add(t, cat)

    def has(self, phrase):
        return norm(phrase) in self.names

    def cat(self, phrase):
        return self.names.get(norm(phrase))


QUOTED_RE = re.compile(
    r'"[^"\n]*"'                                        # "straight double quotes"
    r"|\u201c[^\u201d]*\u201d"                           # curly double quotes
    r"|\u2018.*?\u2019(?!\w)"                            # curly single quotes (an apostrophe inside a word does not close)
    r"|(?<![\w'\u2019])'(?=\S).*?(?<=\S)'(?!\w)"        # straight single quotes used as quotes, not apostrophes
)


def strip_quoted(text):
    """Blank out quoted text (same length, newlines kept) so spoken words are not read as names."""
    return QUOTED_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


CAPW = r"[A-ZÀ-ÖØ-ÞĀ-ſ][\w'’\-]*"
PHRASE_RE = re.compile(CAPW + r"(?:(?:[ \t]+[\"“”]?|[\"“”][ \t]*)" + CAPW + r")*")


def strip_poss(t):
    return re.sub(r"(?:'s|’s|'|’)$", "", t)


SENT_START_RE = re.compile(r"(?:^|\n|[.!?][\"\u201d]?[ \t]+|\b(?:Cut|Tone|Crew|Facts|World|[ABC])[ \t]*:[ \t]*|[\u2014:;][ \t]+)[\"\u201c]?$")


def find_names(text, known, allow):
    """Return list of (phrase, category) for every capitalized phrase segment.
    category None = unknown name; "sentence-initial" = a lone unknown word at the start of a sentence."""
    found = []
    for m in PHRASE_RE.finditer(text):
        raw = m.group(0)
        toks = [strip_poss(t) for t in re.findall(CAPW, raw)]
        end = m.end()
        if end < len(text) and text[end] == ":" and len(toks) == 1 and toks[0] in ("Cut", "Tone", "Crew", "Facts", "World", "A", "B", "C"):
            continue  # a prompt label such as "Cut:"
        initial = bool(SENT_START_RE.search(text[: m.start()]))
        i = 0
        while i < len(toks):
            hit = None
            for j in range(len(toks), i, -1):
                cand = " ".join(toks[i:j])
                if known.has(cand) or norm(cand) in allow:
                    hit = j
                    break
            if hit:
                if hit == i + 1 and norm(toks[i]) in STOP:
                    i += 1
                    continue
                cand = " ".join(toks[i:hit])
                found.append((cand, known.cat(cand) or "allowed"))
                i = hit
                continue
            t = toks[i]
            if norm(t) in STOP or (t.isupper() and len(t) >= 2) or re.fullmatch(r"[A-Z]", t):
                i += 1
                continue
            j = i + 1
            while j < len(toks):
                if norm(toks[j]) in STOP:
                    break
                if any(known.has(" ".join(toks[j:k])) or norm(" ".join(toks[j:k])) in allow
                       for k in range(j + 1, len(toks) + 1)):
                    break
                j += 1
            if i == 0 and initial and j == 1:
                found.append((toks[0], "sentence-initial"))
            else:
                found.append((" ".join(toks[i:j]), None))
            i = j
    return found


def name_terms(key, e):
    terms = [key]
    for al in (e.get("alias") or "").split("/"):
        if al.strip():
            terms.append(al.strip())
    if e.get("gender"):  # individuals: also first name / surname
        terms += [t for t in key.split() if len(t) >= 3 and t not in ("Park",)]
    return terms


def mentions(text, term):
    return re.search(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text, re.I) is not None


def overlap(text, line):
    """Fraction of the content words of `line` that appear in `text`."""
    words = [w for w in re.findall(r"[\w'\-]+", norm(line)) if len(w) > 2]
    if not words:
        return 1.0
    have = set(re.findall(r"[\w'\-]+", norm(text)))
    return sum(1 for w in words if w in have) / len(words)


def cmd_check_prompt(a):
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8") \
        if Path(a.file).exists() else die(f"no such file: {a.file}")
    text = text.rstrip("\n")
    n = len(text)
    u16 = len(text.encode("utf-16-le")) // 2
    failed = False
    print(f"Length: {n} / {PROMPT_LIMIT} characters" + (f" (UTF-16 units: {u16})" if u16 != n else ""))
    if n > PROMPT_LIMIT:
        print(f"FAIL: prompt is over the {PROMPT_LIMIT}-character limit by {n - PROMPT_LIMIT}.")
        failed = True
    elif u16 > PROMPT_LIMIT:
        print(f"WARN: a counter that counts the emoji as two characters would read {u16} (> {PROMPT_LIMIT}). Keep a 10-character margin.")
    elif n > PROMPT_LIMIT - 10:
        print(f"WARN: within 10 characters of the limit ({PROMPT_LIMIT - n} to spare).")

    known = Known()
    allow = {norm(x) for x in (a.allow or "").split(",") if x.strip()}
    names = find_names(strip_quoted(text), known, allow)  # quoted text is ignored for names only
    print("\nCapitalized names/phrases:")
    seen, unknown = set(), []
    for ph, cat in names:
        if ph in seen:
            continue
        seen.add(ph)
        if cat == "sentence-initial":
            print(f"  ~ {ph}  (sentence-initial word not in the database: fine if it is an ordinary word, otherwise a name to check)")
        elif cat is None:
            unknown.append(ph)
            print(f"  ? {ph}  -> UNKNOWN (not a known location, area, NPC, faction, quest or player character)")
        else:
            print(f"  ok {ph}  ({cat})")
    if not names:
        print("  (none)")

    # place references: Location/area
    for m in re.finditer(r"((?:[A-Z][\w'\-]*)(?: [A-Z][\w'\-]*)*)\s*/\s*([a-z][a-z0-9\-]*)", text):
        toks = m.group(1).split()
        L = locations()
        loc = next((" ".join(toks[i:]) for i in range(len(toks)) if " ".join(toks[i:]) in L), None)
        if loc and m.group(2) not in L[loc]["areas"]:
            unknown.append(f"{loc}/{m.group(2)}")
            print(f"  ? {loc}/{m.group(2)}  -> UNKNOWN AREA (not an area of {loc})")
    for m in re.finditer(r"(?<![\w/])([a-z]+-[a-z]+(?:-[a-z]+)*)\b", text):
        pass  # bare area slugs are not checked: they are lowercase words

    warnings = []
    st = S.get("state")
    if st["party_split"] and "\U0001F4CD" not in text:
        warnings.append("party is split but the prompt has no \U0001F4CD positions header (see split-scenes.md)")
    for key, e in cast().items():
        if e.get("status") != "planned":
            continue
        if any(mentions(text, t) for t in name_terms(key, e)):
            il = e.get("intro_line") or ""
            if il and il.lower() not in text.lower() and overlap(text, il.split(":", 1)[-1]) < 0.7:
                warnings.append(f'planned NPC "{key}" appears without their intro_line: {il}')
    for key, q in S.get("quests").items():
        if q["status"] != "planned":
            continue
        if re.search(r"quest\s+[\"“]?" + re.escape(key), text, re.I) or mentions(text, '"' + key + '"'):
            sl = q["seed_line"]
            if sl.lower() not in text.lower() and overlap(text, sl) < 0.8:
                warnings.append(f'planned quest "{key}" appears without its seed_line: {sl}')
    for hidden in ("Standing", "ledger", "Annex Cohort"):
        if mentions(text, hidden):
            warnings.append(f'"{hidden}" is a hidden/director-only term: it should not be named in a prompt')
    for w_ in warnings:
        print(f"WARN: {w_}")
    if unknown:
        print(f"\nFLAGGED {len(unknown)} unknown name(s): {', '.join(unknown)}")
        print("  Fix the name, or (if it is a real new NPC from the story output) record it with add-npc first.")
    if not failed and not unknown and not warnings:
        print("\nOK: length within limit, all names known, no warnings.")
    sys.exit(1 if failed else (2 if unknown else 0))


# ----------------------------------------------------------------------------
# argument parser
# ----------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="db.py", description="Class 2B director database. The database is the source of truth; never read New_World.json during play.",
        epilog="Updates need --turn N --evidence \"...\" (a quote or paraphrase from the story output). See README.md.")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    def add(name, fn, help, upd=False):
        sp = sub.add_parser(name, help=help, description=help)
        sp.set_defaults(fn=fn)
        if upd:
            sp.add_argument("--turn", type=int, required=True, help="turn whose story output justifies this change")
            sp.add_argument("--evidence", required=True, help="short quote or paraphrase from the story output")
        return sp

    sp = add("loc", cmd_loc, "show a location and its areas, or one area with its paths (fuzzy match)")
    sp.add_argument("name"); sp.add_argument("area", nargs="?")
    sp = add("npc", cmd_npc, "show an NPC (cast.json first, then world-npcs.json)")
    sp.add_argument("name")
    sp = add("quest", cmd_quest, "show a quest"); sp.add_argument("name")
    sp = add("faction", cmd_faction, "show a faction"); sp.add_argument("name")
    sp = add("lore", cmd_lore, "ranked keyword search of world lore; --full KEY prints a whole entry")
    sp.add_argument("terms", nargs="*"); sp.add_argument("--full", metavar="KEY"); sp.add_argument("--limit", type=int, default=8)
    add("state", cmd_state, "compact summary of state, Standing and active quests")
    sp = add("canon", cmd_canon, "search canon facts and NPC canon notes"); sp.add_argument("search", nargs="+")
    sp = add("brief", cmd_brief, "compact character card for writing one turn (read-only): voice, psychology, current arc beat, "
             "revealed vs hidden ladder steps, relationships, last canon, won't-do-yet")
    sp.add_argument("name")

    sp = add("thread", cmd_thread, "show a reveal ladder (steps and the next revealable step for the current act/day); no name lists all")
    sp.add_argument("name", nargs="?")

    sp = add("add-npc", cmd_add_npc, "add an NPC Voyage generated (stored in cast.json, in_play, role voyage-generated)", True)
    sp.add_argument("name")
    for opt in ("alias", "gender", "visual", "personality", "location", "area", "type", "faction", "power"):
        sp.add_argument(f"--{opt}")
    sp.add_argument("--age", type=int)
    sp = add("npc-seen", cmd_npc_seen, "mark an NPC as in play (first appearance in story output)", True); sp.add_argument("name")
    sp = add("npc-note", cmd_npc_note, "append a canon note to an NPC", True); sp.add_argument("name"); sp.add_argument("text", nargs="+")
    sp = add("agenda", cmd_agenda, "rewrite an NPC's agenda", True)
    sp.add_argument("name"); sp.add_argument("--want"); sp.add_argument("--next")
    sp = add("quest-start", cmd_quest_start, "planned -> active", True); sp.add_argument("name")
    sp = add("quest-obj", cmd_quest_obj, "set an objective status (pending|done|failed|skipped)", True)
    sp.add_argument("name"); sp.add_argument("obj_id", help="objective id, e.g. o2 or 2 (or a named id such as sign_up_pulse)"); sp.add_argument("status", choices=OBJ_STATUSES)
    sp = add("quest-end", cmd_quest_end, "active -> completed|failed", True)
    sp.add_argument("name"); sp.add_argument("result", choices=["completed", "failed"])
    sp = add("ledger", cmd_ledger, "change 2B Standing, e.g. ledger +3 \"welcome dinner\"", True)
    sp.add_argument("delta", help="+N or -N"); sp.add_argument("reason", nargs="+")
    sp = add("fact", cmd_fact, "record a fact established in play that is not in any other file", True)
    sp.add_argument("subject"); sp.add_argument("text", nargs="+")
    sp = add("pc-add", cmd_pc_add, "add a player character (starts at the story start unless --location/--area)", True)
    sp.add_argument("name"); sp.add_argument("--player", required=True); sp.add_argument("--room", required=True)
    sp.add_argument("--location"); sp.add_argument("--area"); sp.add_argument("--activity")
    for f in PC_SHEET_FIELDS:
        sp.add_argument(f"--{f}", help="character sheet field, as given by the user")
    sp = add("pc-sheet", cmd_pc_sheet,
             "show a player character's sheet, or set --pronouns/--power/--background/--notes (the sheet comes from the user)")
    sp.add_argument("name"); sp.add_argument("--turn", type=int)
    sp.add_argument("--evidence", help='default: "sheet provided by the user"')
    for f in PC_SHEET_FIELDS:
        sp.add_argument(f"--{f}", help="replaces the field; pass '' to clear it")
    sp = add("pos", cmd_pos, "move a player character; refuses places not in locations.json; sets party_split", True)
    sp.add_argument("pc"); sp.add_argument("location"); sp.add_argument("area")
    sp.add_argument("--activity"); sp.add_argument("--placement", choices=SPECIALIZATIONS, help="set after the placement tournament")
    sp = add("time", cmd_time, "set day / time block / clock (weekday is recomputed; Day 1 = Saturday)", True)
    sp.add_argument("--day", type=int); sp.add_argument("--block"); sp.add_argument("--clock", help="HH:MM, 24-hour")
    sp.add_argument("--allow-backward", action="store_true")
    sp = add("clock-add", cmd_clock_add, "open a clock (deadline or waiting)", True)
    sp.add_argument("name"); sp.add_argument("--due-day", type=int, required=True); sp.add_argument("--note")
    sp = add("clock-done", cmd_clock_done, "close a clock", True); sp.add_argument("name")
    sp = add("turn", cmd_turn, "log a turn (appends to turns.json and sets state.turn)")
    sp.add_argument("n", type=int); sp.add_argument("--inputs", required=True, help="text, @file or - for stdin")
    sp.add_argument("--prompt", required=True, help='the exact prompt sent (text, @file or -); "none" for turn 1')
    sp.add_argument("--slips"); sp.add_argument("--notes")
    sp = add("thread-reveal", cmd_thread_reveal,
             "mark a reveal-ladder step as revealed; refuses a step from a later act, with earlier steps still hidden, "
             "or with an unconfirmed milestone gate, unless --force", True)
    sp.add_argument("name"); sp.add_argument("step", type=int)
    sp.add_argument("--gate-met", action="store_true", help="confirm the step's milestone gate has happened")
    sp.add_argument("--force", action="store_true", help="override the act / earlier-step / gate checks (recorded as forced)")
    sp = add("add-area", cmd_add_area,
             "add a new area inside an existing location (refuses unknown locations); pos and loc accept it afterwards", True)
    sp.add_argument("location"); sp.add_argument("area_id", help="lowercase-hyphenated, e.g. bakery-corner")
    sp.add_argument("--desc", required=True, help="one-line description of the area")
    sp.add_argument("--paths", help="comma-separated existing areas of the location this area connects to")
    sp = add("check-prompt", cmd_check_prompt, "check a prompt file (or - for stdin): 700-char limit, unknown names, split header, planned NPCs/quests")
    sp.add_argument("file"); sp.add_argument("--allow", help="comma-separated extra names to accept")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.fn(a)
    except BrokenPipeError:  # e.g. piped into head
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
