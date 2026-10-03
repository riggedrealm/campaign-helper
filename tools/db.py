#!/usr/bin/env python3
"""Voyage director database tool, shared by every campaign (Python 3 standard library only).

The JSON files in campaigns/NAME/data are the source of truth for a campaign; everything specific to a
campaign (display name, acts, main NPCs, secret terms, optional hidden-score modules) lives in
campaigns/NAME/campaign.json. Never read the Voyage world export during play: use this tool instead.

Campaign : --campaign NAME (global option) or env VOYAGE_CAMPAIGN; if only one campaign exists it is the default.
           VOYAGE_DATA (alias CLASS2B_DATA) points at a copy of the data dir; VOYAGE_TRIAL=1 (alias CLASS2B_TRIAL) = trial run.
Lookups : loc, npc, quest, faction, lore, state, resume, canon, thread, brief, bible, scene-card
Updates : add-npc, npc-seen, npc-note, agenda, quest-start, quest-obj,
          quest-end, ledger (optional module), fact, pc-add, pc-sheet, pos, time, clock-add, clock-done, turn,
          thread-reveal, add-area, scene-start, scene-obstacle, scene-surprise, scene-end
          (every update except `turn` and the scene-* follow-ups needs --turn N and --evidence "...")
Checks  : check-prompt <file or ->
Saving  : save (validate JSON, commit data/, push with retries; refuses in a trial run)
Per turn: prep [--paste F] [--names A,B] [--full N] (read-only screen), commit-turn --prompt F --payload F (check + record + local
          git commit, push every push_every turns), wrap-up (push everything, "safe to close")
Batch   : record <payload.json> [--dry-run]  (a whole turn in one locked, all-or-nothing write; see docs/orchestration.md)
Safety  : undo-turn N (restore the snapshot taken before turn N), recover (stale lock), scene-card
          (every write command takes an exclusive lock on data/.lock; reads never lock)

Player character sheets (pronouns, power, background, notes) come from the user;
the director never derives them from story output. Set them with pc-add or pc-sheet.
"""
import argparse
import contextlib
import copy
import difflib
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time as _time
import textwrap
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("VOYAGE_ROOT") or Path(__file__).resolve().parent.parent)
TEMPLATE_SKILL = ROOT / "templates" / "voyage-director" / "SKILL.md"
if not TEMPLATE_SKILL.is_file():  # VOYAGE_ROOT pointing at a bare tree: fall back to this checkout's template
    TEMPLATE_SKILL = Path(__file__).resolve().parent.parent / "templates" / "voyage-director" / "SKILL.md"
DEFAULT_PROMPT_LIMIT = 840
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# campaign state, filled by init_campaign()
CAMPAIGN = None          # campaign name
CAMPAIGN_DIR = None      # Path of campaigns/NAME
CFG = {}                 # parsed campaign.json
DATA = Path("/nonexistent-voyage-data")
PROMPT_LIMIT = DEFAULT_PROMPT_LIMIT
MUTABLE = []             # files a turn can change (ledger only when the standing module is on)
BIBLE = Path("arc-bible.md")
SKILL_FILE = Path("SKILL.md")
WEEKDAYS = list(WEEKDAY_NAMES)
ACT_STARTS = {1: 1}
MAIN_NPCS = []
SPECIALIZATIONS = []
SHAREHOUSE = None        # the home location of the player characters (config "home.location")
START_AREA = None
HIDDEN_WORDS = re.compile(r"(?!x)x")
SOFT_TERMS = set()
SECRET_HINTS = {}
PUBLIC_OK = set()
EXTRA_KNOWN = []

SNAP_KEEP = 5
LOCK_STALE_SECONDS = 600
EXIT_REFUSED, EXIT_PUSH, EXIT_LOCKED, EXIT_STALE = 4, 5, 6, 7
EXIT_BRANCH = 8  # save refused: not on main (all commits go to main only)
OBJ_STATUSES = ["pending", "active", "hidden", "done", "failed", "skipped"]
OPEN_OBJ = ("pending", "active")  # objectives still to do (hidden ones are not yet revealed)
PC_SHEET_FIELDS = ("pronouns", "power", "background", "notes")
FEEDBACK_KINDS = ("scene", "act")


def env_first(*names):
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    return None


def trial_run():
    return env_first("VOYAGE_TRIAL", "CLASS2B_TRIAL") == "1"


def data_override():
    return env_first("VOYAGE_DATA", "CLASS2B_DATA")


def list_campaigns():
    d = ROOT / "campaigns"
    return sorted(p.name for p in d.iterdir() if (p / "campaign.json").is_file()) if d.is_dir() else []


def module_on(name):
    """True when the optional module (`standing`, `debt`) is enabled in campaign.json. Off by default."""
    return bool(((CFG.get("modules") or {}).get(name) or {}).get("enabled"))


def module_cfg(name):
    return (CFG.get("modules") or {}).get(name) or {}


def init_campaign(name=None, strict=False):
    """Select the campaign (name, else VOYAGE_CAMPAIGN, else the only one) and load its campaign.json.
    strict=False (import time): problems leave the module unconfigured instead of raising."""
    global CAMPAIGN, CAMPAIGN_DIR, CFG, DATA, PROMPT_LIMIT, MUTABLE, BIBLE, SKILL_FILE, WEEKDAYS, ACT_STARTS
    global MAIN_NPCS, SPECIALIZATIONS, SHAREHOUSE, START_AREA, HIDDEN_WORDS, SOFT_TERMS, SECRET_HINTS, PUBLIC_OK, EXTRA_KNOWN
    name = name or env_first("VOYAGE_CAMPAIGN")
    problem = None
    if not name:
        have = list_campaigns()
        if len(have) == 1:
            name = have[0]
        else:
            problem = ("no campaign found under campaigns/" if not have else
                       "several campaigns exist (" + ", ".join(have) + "): pass --campaign NAME or set VOYAGE_CAMPAIGN")
    if problem is None:
        cdir = ROOT / "campaigns" / name
        if not (cdir / "campaign.json").is_file():
            problem = f"campaign '{name}' not found: {cdir / 'campaign.json'} is missing (campaigns: {', '.join(list_campaigns()) or 'none'})"
    if problem:
        if strict:
            print(f"error: {problem}", file=sys.stderr)
            sys.exit(2)
        return False
    try:
        cfg = json.loads((cdir / "campaign.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        if strict:
            print(f"error: cannot read {cdir / 'campaign.json'}: {e}", file=sys.stderr)
            sys.exit(2)
        return False
    CAMPAIGN, CAMPAIGN_DIR, CFG = name, cdir, cfg
    DATA = Path(data_override() or cdir / "data")
    BIBLE = cdir / "arc-bible.md"
    SKILL_FILE = ROOT / cfg.get("skill_dir", f".claude/skills/{name}-director") / "SKILL.md"
    start = cfg.get("start_weekday", "Saturday")
    i = WEEKDAY_NAMES.index(start) if start in WEEKDAY_NAMES else 5
    WEEKDAYS = WEEKDAY_NAMES[i:] + WEEKDAY_NAMES[:i]  # Day 1 = start_weekday
    acts = cfg.get("acts") or [{"n": 1, "from_day": 1}]
    ACT_STARTS = {int(a["n"]): int(a["from_day"]) for a in acts}  # first day of each act
    MAIN_NPCS = list(cfg.get("main_npcs") or [])
    SPECIALIZATIONS = list(cfg.get("placements") or [])
    home = cfg.get("home") or {}
    SHAREHOUSE, START_AREA = home.get("location"), home.get("start_area")
    words = (cfg.get("hidden_words") or {}).get("recap") or []
    HIDDEN_WORDS = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.I) if words else re.compile(r"(?!x)x")
    sec = cfg.get("secrets") or {}
    SOFT_TERMS = set(sec.get("soft_terms") or [])
    SECRET_HINTS = {k: {int(n): list(v) for n, v in steps.items()} for k, steps in (sec.get("hints") or {}).items()}
    PUBLIC_OK = {t.lower() for t in (cfg.get("public_ok") or [])}
    EXTRA_KNOWN = list(cfg.get("known_terms") or [])
    MUTABLE = ["state", "canon", "cast", "quests"] + (["ledger"] if module_on("standing") else []) + ["threads", "turns", "locations", "world-npcs"]
    PROMPT_LIMIT = _read_prompt_limit()
    return True


def display():
    return CFG.get("display") or CAMPAIGN or "Campaign"


def _read_prompt_limit():
    """Voyage prompt limit from data/state.json `settings.prompt_limit`; the campaign default if absent or invalid."""
    default = CFG.get("prompt_limit_default")
    default = default if isinstance(default, int) and not isinstance(default, bool) and default > 0 else DEFAULT_PROMPT_LIMIT
    try:
        with open(DATA / "state.json", encoding="utf-8") as f:
            v = json.load(f)["settings"]["prompt_limit"]
        return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else default
    except Exception:  # noqa: BLE001 - missing file/key must never stop a read command
        return default


def need_module(name, what):
    if not module_on(name):
        die(f"{what} is an optional module that is off for campaign '{CAMPAIGN}' "
            f"(campaign.json modules.{name}.enabled is not true). Nothing was changed.", EXIT_REFUSED)


init_campaign()


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------
class DbError(Exception):
    """A user-facing failure. main() prints it and exits with `code`; record catches it per op."""

    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.msg, self.code = msg, code


def die(msg, code=1):
    raise DbError(msg, code)


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
        self.sim = False          # True: apply to the in-memory copy only (record --dry-run and validation)
        self.last_summary = None  # summary of the latest commit (record prints it instead of the chatty lines)

    def reset(self):
        self.cache.clear()
        self.dirty.clear()
        self.last_summary = None

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
        self.last_summary = summary
        if self.sim:
            print(f"[{cmd}] turn {turn}: {summary}")
            self.dirty.clear()
            return
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


def npc_aliases(e):
    """Explicit aliases of a cast/world NPC entry: the legacy `alias` string (split on /) plus the `aliases` list."""
    out = [x.strip() for x in str(e.get("alias") or "").split("/") if x.strip()]
    v = e.get("aliases")
    if isinstance(v, list):
        out += [str(x).strip() for x in v if str(x).strip()]
    return out


def is_individual(e):
    """A person (not a group): first and last names may stand for them."""
    return bool(e.get("gender")) or e.get("kind") in ("world", "main")


def derived_forms(key, e):
    """Default short forms of an individual's name: title-less full name, first and last token (titles from
    campaign.json name_skip_tokens and stop words are skipped). Normalized, 3+ letters."""
    if not is_individual(e):
        return set()
    toks = key.split()
    skip = {norm(t) for t in CFG.get("name_skip_tokens") or []} | STOP
    core = [t for t in toks if norm(t) not in skip]
    out = set()
    if core:
        out |= {norm(core[0]), norm(core[-1])}
        if 2 <= len(core) < len(toks):
            out.add(norm(" ".join(core)))
    return {f for f in out if len(f) >= 3 and f not in STOP}


def npc_labels(n):
    def f(key):
        e = cast().get(key) or world_npcs().get(key) or {}
        labs = [key] + npc_aliases(e)
        if is_individual(e):  # individual: allow first/last name
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
    sh, sm = map(int, (CFG.get("day_start") or "05:00").split(":"))
    return (h * 60 + m - (sh * 60 + sm)) % (24 * 60)  # a day starts at config day_start (default 05:00, Dawn)


def band_for(value):
    for b in S.get("ledger").get("hint_bands", []):
        lo, hi = b.get("min"), b.get("max")
        if (lo is None or value >= lo) and (hi is None or value <= hi):
            return b
    return None


def next_id(prefix, items):
    n = 1 + max([int(re.sub(r"\D", "", i["id"]) or 0) for i in items] + [0])
    return f"{prefix}{n:03d}"


# ----------------------------------------------------------------------------
# write lock and snapshots (reads never lock)
# ----------------------------------------------------------------------------
def lock_path():
    return DATA / ".lock"


def snap_root():
    return DATA / ".snapshots"


def snap_dir(n):
    return snap_root() / f"before-turn-{n}"


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return False
    return True


def read_lock_info():
    """Metadata a writer left in data/.lock ({pid, cmd, turn, ts}); None when the lock is clean."""
    try:
        txt = lock_path().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not txt:
        return None
    try:
        info = json.loads(txt)
        return info if isinstance(info, dict) else {"pid": 0, "cmd": "unknown", "turn": None, "ts": 0}
    except ValueError:
        return {"pid": 0, "cmd": "unknown", "turn": None, "ts": 0}


def lock_age(info):
    return max(0.0, _time.time() - float(info.get("ts") or 0))


def lock_is_stale(info):
    """Stale: the writer is dead, or the lock is older than 10 minutes."""
    return bool(info) and (not pid_alive(info.get("pid")) or lock_age(info) > LOCK_STALE_SECONDS)


def describe_lock(info):
    age = int(lock_age(info))
    return f"pid {info.get('pid')}, {info.get('cmd')}, turn {info.get('turn')}, started {age // 60} min {age % 60} s ago"


def stale_warning():
    info = read_lock_info()
    if lock_is_stale(info):
        return f"WARNING stale write lock ({describe_lock(info)}): run `db.py recover` before writing."
    return None


_HELD = {"fd": None}


@contextlib.contextmanager
def write_lock(cmd, turn=None):
    """Exclusive, non-blocking lock on data/.lock for one write command (re-entrant inside a process).
    A second writer fails at once (exit 6) instead of overwriting. Leftover metadata from a crashed
    writer (exit 7) blocks writes until `recover`."""
    if _HELD["fd"] is not None:
        yield
        return
    if not DATA.is_dir():
        die(f"data directory not found: {DATA}")
    fd = os.open(lock_path(), os.O_RDWR | os.O_CREAT, 0o644)
    locked = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            info = read_lock_info()
            who = describe_lock(info) if info else "unknown writer"
            hint = (" It looks hung (over 10 minutes): kill it, then run `db.py recover`."
                    if info and lock_is_stale(info) else " Nothing was written; wait for it to finish.")
            die(f"another write is in progress ({who}).{hint}", EXIT_LOCKED)
        info = read_lock_info()
        if info:  # a clean release truncates the file, so leftovers mean the previous writer crashed
            die(f"stale write lock left by a crashed writer ({describe_lock(info)}). Run `db.py recover` first.", EXIT_STALE)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps({"pid": os.getpid(), "cmd": cmd, "turn": turn, "ts": _time.time(),
                                 "started": _time.strftime("%Y-%m-%d %H:%M:%S")}).encode())
        _HELD["fd"] = fd
        try:
            yield
        finally:
            _HELD["fd"] = None
            try:
                os.ftruncate(fd, 0)
            except OSError:
                pass
    finally:
        if locked:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def snap_numbers():
    out = []
    if snap_root().is_dir():
        for d in snap_root().iterdir():
            m = re.fullmatch(r"before-turn-(\d+)", d.name)
            if m and d.is_dir():
                out.append(int(m.group(1)))
    return sorted(out)


def take_snapshot(n):
    """Copy the mutable data files to data/.snapshots/before-turn-N and keep only the last 5."""
    d = snap_dir(n)
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for name in MUTABLE:
        shutil.copyfile(DATA / f"{name}.json", d / f"{name}.json")
    (d / "meta.json").write_text(json.dumps({"turn": n, "ts": _time.time()}) + "\n", encoding="utf-8")
    for old in snap_numbers()[:-SNAP_KEEP]:
        shutil.rmtree(snap_dir(old), ignore_errors=True)


def restore_snapshot(d):
    """Put the snapshot's files back (atomic per file) and drop the in-memory cache."""
    names = [n for n in MUTABLE if n != "world-npcs" or (d / f"{n}.json").exists()]  # older snapshots lack world-npcs
    for name in names:
        src = d / f"{name}.json"
        if not src.exists():
            die(f"snapshot {d.name} is missing {name}.json")
    for name in names:
        tmp = DATA / f"{name}.json.tmp"
        shutil.copyfile(d / f"{name}.json", tmp)
        os.replace(tmp, DATA / f"{name}.json")
    S.reset()


EXPRESSION_MOODS = ("happy", "angry", "embarrassed", "lying", "hurt")


def _nonempty_strs(v):
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def expression_problems(x):
    """Problems with an optional cast `expression` kit: gestures (3-4), moods (happy/angry/embarrassed/lying/hurt),
    lines (2 or more), never (one thing)."""
    if not isinstance(x, dict):
        return ["expression must be an object"]
    bad = [f"expression.{k} is not a known field (gestures, moods, lines, never)" for k in x
           if k not in ("gestures", "moods", "lines", "never")]
    g = x.get("gestures")
    if g is not None and not (_nonempty_strs(g) and 3 <= len(g) <= 4):
        bad.append("expression.gestures must be a list of 3 to 4 non-empty strings")
    m = x.get("moods")
    if m is not None:
        if not (isinstance(m, dict) and all(isinstance(v, str) and v.strip() for v in m.values())):
            bad.append("expression.moods must be an object of non-empty strings")
        else:
            bad += [f"expression.moods.{k} is not one of {', '.join(EXPRESSION_MOODS)}" for k in m if k not in EXPRESSION_MOODS]
    ln = x.get("lines")
    if ln is not None and not (_nonempty_strs(ln) and len(ln) >= 2):
        bad.append("expression.lines must be a list of at least 2 non-empty strings")
    nv = x.get("never")
    if nv is not None and not (isinstance(nv, str) and nv.strip()):
        bad.append("expression.never must be a non-empty string")
    return bad


def verify_data(turn=None):
    """Problems found in data/*.json: unparsable files, or state.turn / turns.json out of step."""
    bad = []
    for p in sorted(DATA.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                json.load(f)
        except Exception as e:  # noqa: BLE001
            bad.append(f"{p.name}: {e}")
    if not bad:
        S.reset()
        st, turns = S.get("state"), S.get("turns")
        if len(turns) != st["turn"]:
            bad.append(f"state.turn is {st['turn']} but turns.json has {len(turns)} entries")
        if turn is not None and st["turn"] != turn:
            bad.append(f"state.turn is {st['turn']}, expected {turn}")
        fb = st.get("feedback", [])
        if not isinstance(fb, list) or not all(isinstance(x, dict) for x in fb):
            bad.append("state.feedback must be a list of objects")
        sr = st.get("studio", [])
        if not isinstance(sr, list) or not all(
                isinstance(r, dict) and r.get("id") and r.get("status") in ("pending", "applied")
                and isinstance(r.get("batches"), list) and all(isinstance(b, dict) and "text" in b for b in r["batches"])
                for r in sr):
            bad.append("state.studio must be a list of requests with id, status (pending|applied) and batches")
        for who, e in S.get("cast").items():
            if isinstance(e, dict) and "expression" in e:
                bad += [f"cast.json {who}: {m}" for m in expression_problems(e["expression"])]
    return bad


def hash_data():
    """sha256 per data file (used by tests and the failure report)."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob("*.json"))}


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
        if k == "standing_effect" and not module_on("standing"):
            continue
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


def state_header(st):
    return (f"Turn {st['turn']} | Day {st['day']} {st['weekday']} (Act {current_act(st)}) | {st['time_block']} {st['clock']} | "
            f"party split: {'YES' if st['party_split'] else 'no'}")


def scene_lines(st):
    """Lines describing the open scene (or none), with an over-budget warning."""
    sc = st.get("scene")
    if not sc:
        return ["Scene: none open (scene-start <name> --budget N)"]
    used, budget = sc["turns_used"], sc["budget"]
    obs = "; ".join(sc["obstacles_used"]) or "none"
    out = [f"Scene {sc['name']} ({sc['location']}/{sc['area']}): {used}/{budget} turns, obstacles: {obs}, "
           f"surprise: {'yes' if sc['surprise_used'] else 'no'} (started turn {sc['started_turn']})"]
    if used > budget:
        out.append(f"  WARNING over budget by {used - budget}: cut to the next beat on the next quiet input.")
    elif used == budget:
        out.append("  NOTE budget used up: the next quiet input gets a time skip to the next beat.")
    return out


def print_feedback(st):
    fb = st.get("feedback") or []
    if fb:
        print("Recent feedback:")
        for f in fb[-3:]:
            print("  - " + short(f"T{f['turn']} D{f.get('day')} {f['kind']}"
                                  + (f" {f['scene']}" if f.get("scene") else "")
                                  + f": best {f.get('best') or '-'}; drag {f.get('drag') or '-'}"
                                  + (f"; {f['notes']}" if f.get("notes") else ""), 150))


def cmd_state(a):
    st = S.get("state")
    print(state_header(st))
    if stale_warning():
        print(stale_warning())
    print(f"Prompt limit: {PROMPT_LIMIT} characters (data/state.json settings.prompt_limit)")
    for line in scene_lines(st):
        print(line)
    print("Player characters:")
    if not st["player_characters"]:
        print("  (none yet: use pc-add)")
    for pc in st["player_characters"]:
        print(f"  - {pc['name']} ({pc['player']})" + (f" room {pc['room']}" if pc.get("room") else "") + f": {pc['location']}/{pc['area']}"
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
    print_feedback(st)
    print_slip_stats(S.get("turns"))
    print("Open clocks:")
    if not st["open_clocks"]:
        print("  -")
    for ck in st["open_clocks"]:
        print(f"  - {ck['name']}: due day {ck['due_day']} ({ck['due_day'] - st['day']} days left) {ck.get('note', '')}")
    if module_on("standing"):
        led = S.get("ledger")
        label = module_cfg("standing").get("label", "Standing")
        band = band_for(led["current"])
        print(f"{label} (director only): {led['current']} (start {led['start']}, {len(led['entries'])} entries)"
              + (f"; band {band['label']}" if band else ""))
        if band:
            for key, lab in module_cfg("standing").get("band_lines") or []:
                if band.get(key):
                    print(f"  {lab}: {band[key]}")
    if module_on("debt") and st.get("debt"):
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


def skill_version():
    """Version line of the repo's SKILL.md ("Skill version: YYYY-MM-DD.n"), or a note when unreadable."""
    try:
        m = re.search(r"^Skill version:\s*(\S+)", SKILL_FILE.read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "unknown (no version line in SKILL.md)"
    except OSError:
        return "unknown (SKILL.md not found)"


def rules_version(path):
    """The `Generic rules: X` line of a SKILL.md, or None."""
    try:
        m = re.search(r"^Generic rules:\s*(\S+)", Path(path).read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def version_key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or ""))


def generic_rules_line():
    """'Generic rules: X (template Y)', with a warning when the campaign skill is behind the template."""
    mine, tpl = rules_version(SKILL_FILE), rules_version(TEMPLATE_SKILL)
    line = f"Generic rules: {mine or 'unknown'} (template {tpl or 'unknown'})"
    if mine and tpl and version_key(mine) < version_key(tpl):
        line += f"\n  WARNING generic rules are behind the template: run `python3 tools/sync_skill.py {CAMPAIGN}`, then re-upload the skill zip."
    elif tpl and not mine:
        line += f"\n  WARNING the skill has no `Generic rules:` line: run `python3 tools/sync_skill.py {CAMPAIGN}`."
    return line


def cmd_resume(a):
    """Compact start-of-chat summary (about 60 lines at most)."""
    st = S.get("state")
    turns = S.get("turns")
    act = current_act(st)
    print(state_header(st))
    print(f"Skill version (repo): {skill_version()}")
    print(generic_rules_line())
    print(unpushed_text())
    if stale_warning():
        print(stale_warning())
    for pc in st["player_characters"]:
        print(f"  PC {pc['name']}: {pc['location']}/{pc['area']}"
              + (f", {short(pc['activity'], 50)}" if pc.get("activity") else "")
              + (f" [{pc['placement']}]" if pc.get("placement") else ""))
    if not st["player_characters"]:
        print("  PCs: none yet (pc-add)")
    if module_on("standing"):
        led = S.get("ledger")
        band = band_for(led["current"])
        print(f"{module_cfg('standing').get('label', 'Standing')} (director only): {led['current']}"
              + (f", band {band['label']}" if band else ""))
    for line in scene_lines(st):
        print(line)
    card = (st.get("scene") or {}).get("card")
    if card:
        flat = re.sub(r"\s+", " ", card).strip()
        print("  card: " + short(flat, 400) + (" (db.py scene-card for the full card)" if len(flat) > 400 else ""))
    print("Last turns:" if turns else "Last turns: none logged yet")
    for t in turns[-3:]:
        p = t.get("prompt") or ""
        full = t is turns[-1]
        print(f"- Turn {t['turn']} | Day {t.get('day')} {t.get('time')}")
        print("    inputs: " + short(t.get("inputs") or "-", 230))
        print("    summary: " + (short(t["summary"], 400) if t.get("summary") else "(none logged)"))
        if full and p.strip().lower() != "none":
            body = textwrap.wrap(p.replace("\n", " / "), 108)
            print(f"    prompt sent ({len(p)} chars):")
            for ln in body:
                print("      " + ln)
        else:
            print("    prompt: " + short(p.replace("\n", " / "), 200))
    print_feedback(st)
    print_slip_stats(turns)
    pend = [r["id"] for r in st.get("studio") or [] if r.get("status") == "pending"]
    if pend:
        print(f"Studio: {len(pend)} pending ({', '.join(pend)})")
    print("Open clocks:")
    if not st["open_clocks"]:
        print("  -")
    for ck in st["open_clocks"]:
        print(f"  - {ck['name']}: due day {ck['due_day']} ({ck['due_day'] - st['day']} days left)")
    ms = [m for m in st["calendar"] if m.get("to_day", m["day"]) >= st["day"]][:3]
    print("Next milestones: " + ("; ".join(
        f"Day {m['day']}{'-' + str(m['to_day']) if m.get('to_day') else ''} {m['name']}" for m in ms) or "-"))
    Q = S.get("quests")
    print("Active quests:")
    if not st["active_quests"]:
        print("  -")
    for qn in st["active_quests"]:
        objs = Q.get(qn, {}).get("objectives", [])
        nxt = next((o for o in objs if o["status"] in OPEN_OBJ), None)
        print(f"  - {qn}" + (f": next {short(nxt['text'], 90)}" if nxt else ""))
    c = cast()
    print(f"Main NPCs in play (act {act} beat):")
    inplay = [n for n in MAIN_NPCS if n in c and c[n].get("status") == "in_play"]
    if not inplay:
        print("  none yet")
    for n in inplay:
        beat = (c[n].get("arc_beats") or {}).get(f"act_{act}") or "(no beat)"
        print("  - " + short(f"{n}: {beat}", 150))
    print("Revealed ladder steps:")
    any_rev = False
    for k, t in S.get("threads").items():
        rev = [x for x in t["steps"] if x["status"] == "revealed"]
        if rev:
            any_rev = True
            print("  - " + short(f"{k}: " + "; ".join(f"{x['step']}. {x['reveal']}" for x in rev), 150))
    if not any_rev:
        print("  none")


def cmd_recap(a):
    """Short 'Previously on' for the start of a session; only public story (turn summaries and canon), never hidden data."""
    turns = S.get("turns")
    if not turns:
        print(f"Previously on {display()}: nothing yet (no turns logged).")
        return
    n = max(1, min(a.turns, 5))
    leaks = secret_terms()
    recent = turns[-n:]
    print(f"Previously on {display()}:")
    for t in recent:
        text = re.sub(r"\s+", " ", t.get("summary") or "(no summary logged)").strip()
        print(f"- Day {t.get('day')} {t.get('time')}: " + short(text, 150))
    covered = " ".join(t.get("summary") or "" for t in recent)
    extra = []
    for f in reversed(S.get("canon")["facts"]):
        line = f"{f['subject']}: {f['fact']}"
        if HIDDEN_WORDS.search(line) or str(f["subject"]).lower().startswith("flag") or [h for h in find_secrets(line, leaks)]:
            continue
        if overlap(covered, f["fact"]) >= 0.6:
            continue
        extra.append(line)
        if len(extra) == 2:
            break
    for line in reversed(extra):
        print("- Canon: " + short(line, 150))


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


HISTORY_FIELDS = ("inputs", "summary", "prompt", "notes", "slips")


def snippet_around(text, words, n=140):
    flat = re.sub(r"\s+", " ", text or "").strip()
    low = flat.lower()
    pos = min((i for i in (low.find(w) for w in words) if i >= 0), default=0)
    if len(flat) <= n:
        return flat
    start = max(0, min(pos - n // 3, len(flat) - n))
    end = min(len(flat), start + n)
    return ("..." if start else "") + flat[start:end].strip() + ("..." if end < len(flat) else "")


def cmd_history(a):
    words = [w for w in (norm(x) for x in a.words) if w]
    if not words:
        die("give at least one word to search for")
    if a.limit < 1:
        die("--limit must be at least 1")
    turns = S.get("turns")
    if not turns:
        print("no turns logged yet")
        return
    found = []
    for t in sorted(turns, key=lambda t: t["turn"], reverse=True):
        # every word must appear somewhere in the turn; report fields holding any word
        blob = norm(" ".join(str(t.get(f) or "") for f in HISTORY_FIELDS))
        if not all(w in blob for w in words):
            continue
        fields = [f for f in HISTORY_FIELDS if any(w in norm(t.get(f) or "") for w in words)]
        found.append((t, fields))
    if not found:
        print("no match")
        return
    for t, fields in found[: a.limit]:
        first = fields[0]
        print(f"T{t['turn']} (Day {t.get('day')}, {t.get('time')}): {snippet_around(t.get(first), words)}")
        print(f"    matched in: {', '.join(fields)}")
    if len(found) > a.limit:
        print(f"({len(found) - a.limit} more; raise --limit)")


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


def spotlight_rows(last):
    """([(mentions, kind, name)] least featured first, turns used) over the last N logged turns."""
    turns = S.get("turns")[-last:] if last > 0 else []
    c = cast()
    who = [(pc["name"], name_forms(pc["name"]), "PC") for pc in S.get("state")["player_characters"]]
    for n in MAIN_NPCS:
        e = c.get(n)
        if not e:
            continue
        forms = name_forms(n, e.get("alias"))
        first = norm(n).split()[0]
        if len(first) >= 3 and first not in {t.lower() for t in CFG.get("name_skip_tokens") or []}:
            forms.add(first)
        who.append((n, forms, "NPC"))
    rows = []
    for name, forms, kind in who:
        cnt = sum(1 for t in turns if mentions_any(" ".join(
            str(t.get(k) or "") for k in ("inputs", "summary", "prompt")), forms))
        rows.append((cnt, kind, name))
    rows.sort(key=lambda r: (r[0], r[1] != "PC", r[2]))
    return rows, turns


def cmd_spotlight(a):
    """Mentions of each player character and main NPC over the last N logged turns, least featured first."""
    rows, turns = spotlight_rows(a.last)
    if not turns:
        print("spotlight: no turns logged yet")
        return
    print(f"Spotlight over the last {len(turns)} logged turn(s) (turns {turns[0]['turn']}-{turns[-1]['turn']}); "
          "turns mentioning each, least featured first:")
    for cnt, kind, name in rows:
        print(f"  {cnt:>2}  {kind}  {name}" + ("   <- 0: spotlight due" if cnt == 0 else ""))


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


def brief_show(x):
    """Compact expression kit: gestures, moods, sample lines, never."""
    if not isinstance(x, dict) or not x:
        brief_row("expression", "not set")
        return
    print("SHOW (pick one, vary):")
    if x.get("gestures"):
        brief_wrapped("gestures", " | ".join(x["gestures"]), max_lines=3)
    if x.get("moods"):
        brief_wrapped("moods", " | ".join(f"{k}: {v}" for k, v in x["moods"].items()), max_lines=5)
    if x.get("lines"):
        brief_wrapped("lines", " | ".join(f'"{l}"' for l in x["lines"]), max_lines=2)
    if x.get("never"):
        brief_row("never", x["never"])


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
    brief_show(e.get("expression"))
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
# arc bible lookup
# ----------------------------------------------------------------------------
def bible_headings():
    """[(line_index, level, title, dotted_number)] for every markdown heading outside code fences."""
    lines = BIBLE.read_text(encoding="utf-8").split("\n")
    out, fence, counters = [], False, [0] * 7
    cur2 = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            fence = not fence
        if fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", ln)
        if not m:
            continue
        lvl, title = len(m.group(1)), m.group(2)
        if lvl == 1:
            continue
        num = None
        if lvl == 2:
            mm = re.match(r"^(\d+)\.\s", title)
            cur2 = mm.group(1) if mm else str(counters[2] + 1)
            counters[2] = int(cur2)
            counters[3:] = [0] * 4
            num = cur2
        else:
            counters[lvl] += 1
            counters[lvl + 1:] = [0] * (6 - lvl)
            num = ".".join([cur2 or "0"] + [str(counters[l]) for l in range(3, lvl + 1)])
        out.append((i, lvl, title, num))
    return lines, out


def cmd_bible(a):
    lines, hs = bible_headings()
    if not a.section:
        print("arc-bible.md sections (db.py bible <number | actN | keyword>):")
        for _, lvl, title, num in hs:
            label = re.sub(r"^\d+\.\s+", "", title)
            print(f"{'  ' * (lvl - 2)}{num:<8} {label}")
        return
    q = " ".join(a.section).strip()
    hit = [h for h in hs if h[3] == q]
    if not hit:
        m = re.fullmatch(r"act\s*(\d)", q, re.I)
        if m:
            hit = [h for h in hs if h[1] == 2 and re.match(rf"^(\d+\.\s*)?Act {m.group(1)}\b", h[2])]
    if not hit:
        hit = [h for h in hs if norm(q) in norm(h[2])]
        if not hit:
            hit = [h for _, h in rank(q, hs, lambda h: [h[2]])]
            hit = hit[:3]
    if not hit:
        die(f'no arc-bible section matches "{q}" (run: db.py bible)', 2)
    i0, lvl, title, num = hit[0]
    end = len(lines)
    for i, l2, _, _ in hs:
        if i > i0 and l2 <= lvl:
            end = i
            break
    print("\n".join(lines[i0:end]).rstrip())
    if len(hit) > 1:
        print("\n(other matches: " + ", ".join(f"{h[3]} {h[2]}" for h in hit[1:6]) + ")")


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
    need_module("standing", "the hidden score (ledger)")
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
             f'{module_cfg("standing").get("label", "Standing")} {d:+d} -> {led["current"]} ({" ".join(a.reason)}); hint band: {band["label"] if band else "?"}')


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
    home = CFG.get("home") or {}
    suffix = home.get("room_suffix")
    room = (a.room or "").strip() or None
    if SHAREHOUSE and suffix:  # the campaign has numbered or named rooms at a home location: validate them
        if not room:
            die("--room is required for this campaign", 2)
        L = locations()[SHAREHOUSE]["areas"]
        room = {slug(x): x for x in L}.get(slug(room))
        if not room or not room.endswith(suffix):
            word = home.get("room_word") or "room"
            die(f'room "{a.room}" is not a {word} of {SHAREHOUSE}. {word.capitalize()}s: '
                + ", ".join(x for x in L if x.endswith(suffix)), 3)
        pc_rooms = home.get("pc_rooms") or []
        if pc_rooms and room not in pc_rooms:
            print(f"warning: {room} is normally an NPC housemate's room (PC rooms: {', '.join(pc_rooms)})")
    if room and any(p.get("room") == room for p in st["player_characters"]):
        die(f"room {room} already has a player character")
    if not (a.location or SHAREHOUSE):
        die("give --location and --area (this campaign has no default start place)", 2)
    if not (a.area or START_AREA):
        die("give --area (this campaign has no default start area)", 2)
    loc, area = resolve_place(a.location or SHAREHOUSE, a.area or START_AREA)
    pc = {"name": a.name, "player": a.player, "room": room or "", "location": loc,
          "area": area, "activity": a.activity or "", "placement": None}
    for f in PC_SHEET_FIELDS:
        pc[f] = (getattr(a, f) or "").strip()
    st["player_characters"].append(pc)
    update_split(st)
    S.touch("state")
    S.commit("pc-add", a.turn, a.evidence, f'player character "{a.name}" ({a.player}), ' + (f"room {room}, " if room else "") + f"at {loc}/{area}"
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


SLIP_CATS = ("fact", "invention", "teleport", "outcome", "dropped")
_SLIP_SPLIT = re.compile(r";\s*(?=(?:" + "|".join(SLIP_CATS) + r")\s*:)", re.I)
_SLIP_TAG = re.compile(r"^\s*([A-Za-z][\w\-]{0,15})\s*:\s*(.*)$", re.S)


def parse_slips(v):
    """Slips of one turn as [(category, text)]. `v` is a string (one slip per line, or `;` before a tag) or a list.
    Untagged slips (and unknown tags) are category "other", so old data still counts."""
    if not v:
        return []
    parts = []
    for item in (v if isinstance(v, list) else [v]):
        for line in str(item).splitlines():
            parts += _SLIP_SPLIT.split(line)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = _SLIP_TAG.match(p)
        if m and m.group(1).lower() in SLIP_CATS:
            out.append((m.group(1).lower(), m.group(2).strip()))
        else:
            out.append(("other", p))
    return out


def unknown_slip_tags(v):
    """Leading `word:` tags in a slips value that are not a known category (a warning, never an error)."""
    bad = []
    for item in ([v] if not isinstance(v, list) else v):
        for line in str(item or "").splitlines():
            for p in _SLIP_SPLIT.split(line):
                m = _SLIP_TAG.match(p)
                if m and m.group(1).lower() not in SLIP_CATS and " " not in m.group(1) and m.group(1) not in bad:
                    bad.append(m.group(1))
    return bad


def slip_stats(turns):
    """([(category, count)] most common first, most recent (turn, text) of the top category) over all logged turns."""
    counts, last = {}, {}
    for t in turns:
        for cat, text in parse_slips(t.get("slips")):
            counts[cat] = counts.get(cat, 0) + 1
            last[cat] = (t["turn"], text)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0] == "other", kv[0]))
    return ranked, (last[ranked[0][0]] if ranked else None)


def print_slip_stats(turns):
    ranked, ex = slip_stats(turns)
    if not ranked:
        return
    print("Repeat slips: " + ", ".join(f"{c} x{n}" for c, n in ranked[:3]))
    print(f"  latest {ranked[0][0]}: T{ex[0]}: {short(ex[1], 150)}")


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
    summary = (read_arg_text(a.summary) or "").strip()
    if not summary:
        die('--summary is required: two lines max on what Voyage\'s story output established this turn')
    if len(summary.splitlines()) > 2 or len(summary) > 400:
        die("--summary must be two lines max (400 characters at most)")
    entry = {"turn": a.n, "day": st["day"], "time": f'{st["time_block"]} {st["clock"]}',
             "inputs": read_arg_text(a.inputs), "summary": summary, "prompt": prompt,
             "slips": read_arg_text(a.slips) or "", "notes": read_arg_text(a.notes) or ""}
    for tag in unknown_slip_tags(entry["slips"]):
        print(f"warning: slip category '{tag}' is not one of {'|'.join(SLIP_CATS)}; counted as other")
    turns.append(entry)
    st["turn"] = a.n
    sc = st.get("scene")
    if sc:
        sc["turns_used"] += 1
    S.touch("turns")
    S.touch("state")
    plen = 0 if is_none else len(prompt)
    S.commit("turn", a.n, "", f"logged turn {a.n} (Day {st['day']} {entry['time']}); prompt {plen}/{PROMPT_LIMIT} chars")
    if sc:
        for line in scene_lines(st):
            print(line)


def cmd_feedback(a):
    check_turn(a.turn)
    st = S.get("state")
    best, drag = (read_arg_text(a.best) or "").strip(), (read_arg_text(a.drag) or "").strip()
    if not best and not drag:
        die("give --best and/or --drag")
    sc = st.get("scene")
    entry = {"turn": a.turn, "day": st["day"], "kind": a.kind, "scene": a.scene or (sc["name"] if (sc and a.kind == "scene") else ""),
             "best": best, "drag": drag, "notes": (read_arg_text(a.notes) or "").strip()}
    st.setdefault("feedback", []).append(entry)
    S.touch("state")
    S.commit("feedback", a.turn, "", f'{a.kind} feedback (Day {st["day"]}): best "{short(best, 50)}"; drag "{short(drag, 50)}"')


# ----------------------------------------------------------------------------
# scenes (state.scene)
# ----------------------------------------------------------------------------
def open_scene(st):
    if not st.get("scene"):
        die("no scene is open (use scene-start <name> --budget N --turn N --evidence ...)")
    return st["scene"]


def scene_meta(a):
    """--turn / --evidence are optional on the scene follow-ups (director-side bookkeeping)."""
    turn = a.turn if a.turn is not None else get_state_turn()
    return turn, (a.evidence or "director log")


def cmd_scene_start(a):
    need_ev(a)
    st = S.get("state")
    if st.get("scene"):
        die(f'scene "{st["scene"]["name"]}" is still open: scene-end it first')
    if a.budget < 1:
        die("--budget must be 1 or more (see arc-bible.md section 14)")
    if a.location:
        loc, area = resolve_place(a.location, a.area)
        if area is None:
            die("give --area with --location")
    else:
        pcs = st["player_characters"]
        if not pcs:
            die("no player characters yet: give --location and --area")
        loc, area = resolve_place(pcs[0]["location"], a.area or pcs[0]["area"])
    card = (read_arg_text(a.card) or "").strip()
    st["scene"] = {"name": a.name, "location": loc, "area": area, "budget": a.budget, "turns_used": 0,
                   "obstacles_used": [], "surprise_used": False, "started_turn": a.turn}
    if card:
        st["scene"]["card"] = card
    S.touch("state")
    S.commit("scene-start", a.turn, a.evidence,
             f'scene "{a.name}" at {loc}/{area}, budget {a.budget}' + (f", card {len(card)} chars" if card else ""))


def cmd_scene_card(a):
    sc = (S.get("state").get("scene") or None)
    if not sc:
        die("no scene is open")
    print(f"Scene {sc['name']} ({sc['location']}/{sc['area']}): card")
    print(sc.get("card") or "(no card stored: scene-start --card @file)")


def cmd_scene_obstacle(a):
    st = S.get("state")
    sc = open_scene(st)
    turn, ev = scene_meta(a)
    sc["obstacles_used"].append(" ".join(a.text))
    S.touch("state")
    S.commit("scene-obstacle", turn, ev, f'scene "{sc["name"]}": obstacle "{" ".join(a.text)}" ({len(sc["obstacles_used"])} used)')


def cmd_scene_surprise(a):
    st = S.get("state")
    sc = open_scene(st)
    if sc["surprise_used"] and not a.force:
        die("this scene already used its one surprise (arc-bible.md section 13); --force to override")
    turn, ev = scene_meta(a)
    sc["surprise_used"] = True
    S.touch("state")
    S.commit("scene-surprise", turn, ev, f'scene "{sc["name"]}": surprise used')


def cmd_scene_end(a):
    st = S.get("state")
    sc = open_scene(st)
    turn, ev = scene_meta(a)
    st["scene"] = None
    S.touch("state")
    S.commit("scene-end", turn, ev,
             f'scene "{sc["name"]}" ended at {sc["turns_used"]}/{sc["budget"]} turns, '
             f'{len(sc["obstacles_used"])} obstacles, surprise {"yes" if sc["surprise_used"] else "no"}')


# ----------------------------------------------------------------------------
# save (commit and push the play data)
# ----------------------------------------------------------------------------
def run_git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r


class PushFailed(DbError):
    """The commit is saved locally but the push failed (exit code 5)."""


def save_gate(trial=False):
    if trial or trial_run():
        die("save refused: this is a trial run (--trial or VOYAGE_TRIAL=1 / CLASS2B_TRIAL=1). Trial runs write nothing.", EXIT_REFUSED)
    if data_override():
        die("save refused: VOYAGE_DATA / CLASS2B_DATA points at a copy, not the real data/ directory.", EXIT_REFUSED)


def do_save(retries=4, dry_run=False):
    """Validate the JSON, commit the data directory and push to origin main. Refuses off main (exit 8, even for --dry-run).
    PushFailed keeps the local commit (exit 5)."""
    bad = verify_data()
    if bad:
        die("save refused: " + "; ".join(bad))
    st = S.get("state")
    print(f"JSON valid ({len(list(DATA.glob('*.json')))} files); turn {st['turn']}")
    here = DATA.parent
    root = Path(run_git(["rev-parse", "--show-toplevel"], here).stdout.strip())
    rel = str(DATA.resolve().relative_to(root.resolve()))
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    msg = f"{display()} save: turn {st['turn']}"
    if branch != "main":
        die(f"save refused: on branch {branch!r}, not main. All commits go to main only (nothing was committed or pushed). "
            "Run `git fetch origin main && git checkout -B main origin/main`, then rerun `db.py save`.", EXIT_BRANCH)
    if dry_run:
        print(f"dry run: would commit {rel} on {branch} as \"{msg}\" and push with up to {retries} tries")
        return
    run_git(["add", "--", rel], root)
    if run_git(["diff", "--cached", "--quiet", "--", rel], root, check=False).returncode == 0:
        print("nothing new to commit in data/")
    else:
        run_git(["commit", "-m", msg, "--", rel], root)
        print(f"committed: {msg}")
    i = push_main(root, retries)
    print(f"pushed main (attempt {i})")


def push_main(root, retries=4):
    """Push main to origin with retries (rebasing on a rejected push). Returns the successful attempt number;
    PushFailed (exit 5) when every attempt failed: the local commits are kept."""
    err = ""
    for i in range(1, retries + 1):
        r = run_git(["push", "-u", "origin", "main"], root, check=False)
        if r.returncode == 0:
            return i
        err = (r.stderr or r.stdout).strip()
        print(f"push attempt {i}/{retries} failed: {short(err, 200)}", file=sys.stderr)
        if re.search(r"non-fast-forward|fetch first|rejected", err):
            run_git(["pull", "--rebase", "origin", "main"], root, check=False)
        if i < retries:
            _time.sleep(2 ** i)
    raise PushFailed(f"saved locally, push failed after {retries} attempt(s) (last error: {short(err.splitlines()[0] if err else '?', 120)}). "
                     "The commit is kept and the data stays applied; run `db.py save` once the network is back.", EXIT_PUSH)


def cmd_save(a):
    save_gate(a.trial)
    do_save(a.retries, a.dry_run)


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


def apply_add_area(location, area_id, desc, paths_csv, turn, evidence):
    """Add the area to the in-memory data (no commit); returns the summary line."""
    loc, _ = resolve_place(location)  # refuses unknown locations
    desc = (desc or "").strip()
    if not desc:
        die("--desc must not be empty")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", area_id):
        die(f'area id "{area_id}" must be lowercase words joined by hyphens, e.g. bakery-corner')
    areas = locations()[loc]["areas"]
    if slug(area_id) in {slug(x) for x in areas}:
        die(f'"{loc}" already has an area "{area_id}"', 3)
    by_slug = {slug(x): x for x in areas}
    paths = []
    for p in [x.strip() for x in (paths_csv or "").split(",") if x.strip()]:
        if slug(p) not in by_slug:
            die(f'--paths: "{p}" is not an existing area of "{loc}". Areas: {", ".join(areas)}', 3)
        paths.append(by_slug[slug(p)])
    areas[area_id] = {"description": desc, "paths": paths, "added_turn": turn, "evidence": evidence}
    S.touch("locations")
    return f'area "{area_id}" added to "{loc}": {short(desc, 70)}' + (f" (paths: {', '.join(paths)})" if paths else "")


def cmd_add_area(a):
    """Add a new area inside an existing location. Locations stay fixed; areas may be added from story output."""
    need_ev(a)
    S.commit("add-area", a.turn, a.evidence, apply_add_area(a.location, a.area_id, a.desc, a.paths, a.turn, a.evidence))


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
        for al in npc_aliases(e):
            self._add(al, cat)
        if is_individual(e):
            for t in key.split():
                self._add(t, cat)
        for f in derived_forms(key, e):
            self._add(f, cat)

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
    terms = [key] + npc_aliases(e)
    if e.get("gender"):  # individuals: also first name / surname
        skip = set(CFG.get("name_skip_tokens") or [])
        terms += [t for t in key.split() if len(t) >= 3 and t not in skip]
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


LABELS = ("Cut", "Tone", "Crew", "Facts", "World")
LABEL_RE = re.compile(r"^[ \t]*(" + "|".join(LABELS) + r")[ \t]*:", re.M)


def hidden_steps():
    """[(thread key, step dict)] for every ladder step still hidden."""
    return [(k, s) for k, t in S.get("threads").items() for s in t["steps"] if s.get("status") == "hidden"]


def secret_terms():
    """{normalized term: ('thread step N', strong)} for every still-hidden ladder step. Sources, most to least trusted:
    an explicit `keywords` list on the step or thread; SECRET_HINTS (curated distinctive phrases per ladder step);
    capitalized proper nouns of the step text that are not main NPCs, locations, factions, cast or player characters.
    Plain lowercase words are never derived (too many false FAILs): a new ladder should give `keywords`."""
    known = Known()
    skip = {"player character", "location", "faction", "in-play NPC", "world NPC", "planned NPC", "quest", "world npc"}
    out = {}

    def put(term, k, s, strong=False):
        n = norm(term)
        if len(n) >= 4 and n not in PUBLIC_OK:
            if n in SOFT_TERMS:
                strong = False
            old = out.get(n)
            if old is None or (strong and not old[1]):
                out[n] = (f"{k} step {s['step']}", strong)
    for k, s in hidden_steps():
        who = f"{k}"
        for kw in (s.get("keywords") or []) + (S.get("threads")[k].get("keywords") or []):
            put(kw, who, s, True)
        for kw in SECRET_HINTS.get(k, {}).get(s["step"], []):
            put(kw, who, s, True)
        for m in PHRASE_RE.finditer(s["reveal"]):
            toks = [strip_poss(t) for t in re.findall(CAPW, m.group(0))]
            if SENT_START_RE.search(s["reveal"][: m.start()]) and len(toks) == 1:
                continue  # a lone capitalized sentence opener is an ordinary word
            i = 0
            while i < len(toks):  # runs of tokens that are neither stop words nor known people/places/factions
                j = next((j for j in range(len(toks), i, -1) if known.cat(" ".join(toks[i:j])) in skip), None)
                if j:
                    i = j
                    continue
                if norm(toks[i]) in STOP or len(toks[i]) < 3 or known.cat(toks[i]) in skip:
                    i += 1
                    continue
                j = i + 1
                while j < len(toks) and norm(toks[j]) not in STOP and known.cat(toks[j]) not in skip:
                    j += 1
                run = toks[i:j]
                if len(run) >= 2 or not known.has(run[0]):
                    put(" ".join(run), who, s)
                i = j
    return out


def find_secrets(text, terms):
    """[(term, source, strong)] of secret terms present in text (word-bounded, simple plural/past endings allowed)."""
    low = norm(text)
    hits = []
    for term, (src, strong) in terms.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?:s|es|ed|d|ing)?(?![a-z0-9])", low):
            hits.append((term, src, strong))
    return hits


OUTCOME_VERBS = (r"succeeds?|succeeded|fails?|failed|hits?|lands?|dodges?|dodged|defeats?|defeated|beats?|wins?|won|"
                 r"loses?|lost|misses?|missed|is\s+knocked|takes?\s+damage")


def stated_outcomes(text, pcs):
    """Sentences-ish snippets where a player character is told to succeed/fail/hit/... (quoted text ignored)."""
    plain, out = strip_quoted(text), []
    names = set()
    for n in pcs:
        names.add(n)
        names.update(t for t in n.split() if len(t) >= 3)
    for n in sorted(names, key=len, reverse=True):
        for m in re.finditer(r"(?<!\w)" + re.escape(n) + r"(?:['\u2019]s)?(?:[ \t,]+[\w'\u2019\-]+){0,3}?[ \t,]+(?:" + OUTCOME_VERBS + r")\b",
                             plain, re.I):
            snip = re.sub(r"\s+", " ", m.group(0))
            if not any(snip in o or o in snip for o in out):
                out.append(snip)
    return out


FLAT_VERBS = {"react", "reacts", "reacted", "agree", "agrees", "agreed", "watch", "watches", "watched", "nod", "nods", "nodded",
              "listen", "listens", "listened", "look", "looks", "looked", "say", "says", "said", "smile", "smiles", "smiled"}
FLAT_FILLER = set("a an the and to at in on of with them him her it its his their they back up along then also too just "
                  "softly quietly politely warmly silently gently briefly newcomer newcomers player players".split())
CREW_RE = re.compile(r"^[ \t]*Crew[ \t]*:(.*?)(?=^[ \t]*(?:Cut|Tone|Facts|World)[ \t]*:|\Z)", re.M | re.S)
OTHERS_RE = re.compile(r"\b(?:others?|everyone else|the rest|rest of)\b|\breacts? in character\b", re.I)


def flat_crew_clauses(text):
    """[(NPC, clause)] for `Crew:` clauses about a named NPC whose only content is a flat verb (reacts, agrees, watches,
    nods, listens, looks, says, smiles) with at most one other word and no quote. 'Others react in character' is exempt."""
    m = CREW_RE.search(text)
    if not m:
        return []
    out = []
    people = {**world_npcs(), **cast()}
    for clause in re.split(r";|\.(?:\s|$)|\n", m.group(1)):
        clause = clause.strip(" \t,")
        if not clause or OTHERS_RE.search(clause) or re.search(r"[\"\u201c\u201d]", clause):
            continue
        hits = [(k, t) for k, e in people.items() for t in name_terms(k, e) if mentions(clause, t)]
        if not hits:
            continue
        words = re.findall(r"[\w'\u2019\-]+", norm(clause))
        if not any(w in FLAT_VERBS for w in words):
            continue
        namew = {w for _, t in hits for w in re.findall(r"[\w'\-]+", norm(t))}
        rest = [w for w in words if w not in namew and w not in FLAT_VERBS and w not in FLAT_FILLER]
        if len(rest) <= 1:
            out.append((hits[0][0], clause))
    return out


NPC_CATS = ("in-play NPC", "world NPC", "planned NPC", "world npc", "player character")


def run_check(text, allow=(), verbose=True):
    """The check-prompt analysis. Prints its report (verbose=False: only Length, FAIL, WARN and unknown-name lines)
    and returns (failed, unknown, warnings)."""
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
    allow = {norm(x) for x in allow}
    idx = NameIndex()

    # label structure: Cut first (after an optional position header), World last, the rest optional and in order
    labels = [m.group(1) for m in LABEL_RE.finditer(text)]
    body = [ln for ln in text.splitlines() if ln.strip() and "\U0001F4CD" not in ln]
    first_ok = bool(body) and LABEL_RE.match(body[0]) is not None and body[0].lstrip().startswith("Cut")
    order = [LABELS.index(x) for x in labels]
    if "Cut" not in labels or not first_ok or labels[:1] != ["Cut"]:
        print("FAIL: `Cut:` must be the first label (after an optional \U0001F4CD header line).")
        failed = True
    if "World" not in labels:
        print("FAIL: `World:` label is missing.")
        failed = True
    elif labels[-1] != "World":
        print("FAIL: `World:` must be the last label.")
        failed = True
    if order != sorted(set(order)) and "Cut" in labels and "World" in labels:
        print(f"FAIL: labels out of order or repeated ({', '.join(labels)}); the order is {', '.join(LABELS)}.")
        failed = True

    # secrets from ladder steps that are still hidden
    secret_warns = []
    for term, src, strong in find_secrets(text, {t: v for t, v in secret_terms().items() if t not in allow}):
        if strong:
            print(f'FAIL: possible secret leak "{term}" from {src} (still hidden). Reword, or pass --allow "{term}" if it is public.')
            failed = True
        else:
            secret_warns.append(f'"{term}" is also a term in {src} (still hidden): check you are not hinting at the secret')

    names = find_names(strip_quoted(text), known, allow)  # quoted text is ignored for names only
    if verbose:
        print("\nCapitalized names/phrases:")
    seen, unknown, name_warns = set(), [], []
    for ph, cat in names:
        if ph in seen:
            continue
        seen.add(ph)
        if cat == "sentence-initial":
            if verbose:
                print(f"  ~ {ph}  (sentence-initial word not in the database: fine if it is an ordinary word, otherwise a name to check)")
        elif cat is None:
            unknown.append(ph)
            if verbose:
                print(f"  ? {ph}  -> UNKNOWN (not a known location, area, NPC, faction, quest or player character)")
        else:
            if verbose:
                print(f"  ok {ph}  ({cat})")
            if cat in NPC_CATS:
                keys, _tier = idx.resolve(norm(ph))
                if len(keys) > 1:
                    name_warns.append(f"AMBIGUOUS name {ph}: " + " | ".join(sorted(keys)[:4]))
                elif len(keys) == 1 and idx.ents[keys[0]].get("use_full_name") and norm(ph) != norm(keys[0]):
                    name_warns.append(f'use full name "{keys[0]}" (canon trap), not "{ph}"')
    if not names and verbose:
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
        if e.get("status") != "planned" or e.get("in_studio"):
            continue  # Studio-injected NPCs need no intro_line
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
    warnings += secret_warns + name_warns
    fm = re.search(r"^[ \t]*Facts[ \t]*:(.*?)(?=^[ \t]*(?:Cut|Tone|Crew|World)[ \t]*:|\Z)", text, re.M | re.S)
    if fm and re.search(r"correct(?:ion|ing|s|ed)?\b|\bnot\s+\w+|\b(?:isn|wasn|aren|didn|doesn|don)['\u2019]t\b", fm.group(1), re.I):
        warnings.append('the Facts: line states a correction or a negation ("not X", "isn\'t"): state what is true instead of what is wrong')
    for who, clause in flat_crew_clauses(text):
        warnings.append(f'`Crew:` clause for {who} uses only flat verbs ("{clause}"): add one gesture, the feeling under it, '
                        'their way of talking (`brief` SHOW; docs/expression.md)')
    for snip in stated_outcomes(text, [pc["name"] for pc in st["player_characters"]]):
        warnings.append(f'states a player outcome ("{snip}"): the player decides it, Voyage rolls it')
    for hidden in (CFG.get("hidden_words") or {}).get("prompt") or []:
        if mentions(text, hidden):
            warnings.append(f'"{hidden}" is a hidden/director-only term: it should not be named in a prompt')
    for w_ in warnings:
        print(f"WARN: {w_}")
    if unknown:
        print(f"\nFLAGGED {len(unknown)} unknown name(s): {', '.join(unknown)}")
        print("  Fix the name, or (if it is a real new NPC from the story output) record it with add-npc first.")
    if not failed and not unknown and not warnings and verbose:
        print("\nOK: length within limit, all names known, no warnings.")
    return failed, unknown, warnings


def cmd_check_prompt(a):
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8") \
        if Path(a.file).exists() else die(f"no such file: {a.file}")
    failed, unknown, _warnings = run_check(text.rstrip("\n"), (a.allow or "").split(","))
    sys.exit(1 if failed else (2 if unknown else 0))


# ----------------------------------------------------------------------------
# Studio requests (world content the user injects through Voyage's Studio)
# ----------------------------------------------------------------------------
STUDIO_KINDS = ("npc", "quest", "faction", "area", "story-start", "story-fix", "canon", "other")
DEFAULT_STUDIO_LIMIT = 2000
_SENT_RE = re.compile(r"(?<=[.!?…])[\"'”’)]*\s+")


def studio_limit():
    v = CFG.get("studio_limit")
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 200 else DEFAULT_STUDIO_LIMIT


def studio_items():
    return S.get("state").get("studio") or []


def batch_prefix(i, n, target, edit=False):
    return f"Batch {i}/{n} — {'Update ' if edit else ''}{target}: "


def studio_known(kind, target):
    """Canonical key of an existing world entity (npc, quest, faction) matching target, else None."""
    pools = {"npc": [cast, world_npcs], "quest": [lambda: S.get("quests")], "faction": [lambda: S.get("factions")]}.get(kind, [])
    for pool in pools:
        keys = list(pool())
        hit = rank(target, keys, lambda k: [k, (pool().get(k) or {}).get("alias") or ""] if kind == "npc" else [k])
        if hit and hit[0][0] >= 0.95:
            return hit[0][1]
    return None


def _pack(units, sep, budget, finer):
    """Greedy-pack units joined by sep into chunks of at most budget characters; an oversize unit is split finer."""
    out, cur = [], ""
    for u in units:
        if len(u) > budget:
            if cur:
                out.append(cur)
                cur = ""
            out += split_chunks(u, budget, finer)
        elif not cur:
            cur = u
        elif len(cur) + len(sep) + len(u) <= budget:
            cur += sep + u
        else:
            out.append(cur)
            cur = u
    if cur:
        out.append(cur)
    return out


def split_chunks(text, budget, level=0):
    """Chunks of at most budget characters: blank-line (entity) boundaries first, then lines (paragraphs), then
    sentences, then words. Never splits inside a word."""
    text = text.strip()
    if len(text) <= budget:
        return [text] if text else []
    if level == 0:
        return _pack([x.strip() for x in re.split(r"\n[ \t]*\n+", text) if x.strip()], "\n\n", budget, 1)
    if level == 1:
        return _pack([x.strip() for x in text.split("\n") if x.strip()], "\n", budget, 2)
    if level == 2:
        return _pack([x.strip() for x in _SENT_RE.split(text) if x.strip()], " ", budget, 3)
    words = text.split()
    if any(len(w) > budget for w in words):
        die(f"a single word is longer than the {budget}-character batch budget; reword it")
    return _pack(words, " ", budget, 4)


def make_batches(text, target, limit, edit=False):
    """[{n, text, applied}] where every text starts with 'Batch i/n — target: ' and is at most limit characters."""
    guess = 1
    while True:
        budget = limit - len(batch_prefix(guess, guess, target, edit))
        if budget < 60:
            die(f"studio_limit {limit} leaves no room after the batch prefix; shorten the target name")
        chunks = split_chunks(text, budget)
        if len(chunks) <= guess:
            break
        guess = len(chunks)
    n = len(chunks)
    out = []
    for i, c in enumerate(chunks, 1):
        t = batch_prefix(i, n, target, edit) + c
        assert len(t) <= limit
        out.append({"n": i, "text": t, "applied": False})
    return out


def studio_find(sid):
    items = studio_items()
    for r in items:
        if r["id"].lower() == str(sid).lower():
            return r
    die(f'no Studio request "{sid}" (ids: {", ".join(r["id"] for r in items) or "none"})', 2)


def cmd_studio_request(a):
    check_turn(a.turn)
    if a.kind == "canon":
        a.kind = "story-fix"  # old name
    target = (a.target or "").strip()
    if not target:
        die("--target must not be empty")
    if a.text_file == "-":
        text = sys.stdin.read()
    else:
        if not Path(a.text_file).exists():
            die(f"no such file: {a.text_file}")
        text = Path(a.text_file).read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").strip()
    if not text:
        die("the text file is empty")
    strong, soft = [], []
    for term, src, is_strong in find_secrets(text, secret_terms()):
        (strong if is_strong else soft).append((term, src))
    for term, src in strong:
        print(f'{"WARN (allowed)" if a.allow else "FAIL"}: possible secret "{term}" from {src} (still hidden); '
              "hidden ladder steps never go into Studio.")
    if strong and not a.allow:
        die("Studio request refused: reword the hidden-secret terms above, or pass --allow if they are public.")
    for term, src in soft:
        print(f'WARN: "{term}" is also a term in {src} (still hidden): check the text is not hinting at the secret')
    edit = bool(getattr(a, "edit", False))
    known = studio_known(a.kind, target)
    if edit and a.kind in ("npc", "quest", "faction") and not known:
        print(f'WARN: --edit target "{target}" is not a known {a.kind} in the world; check the name (the edit may not match anything)')
    elif edit and a.kind not in ("npc", "quest", "faction"):
        print(f"WARN: --edit is meant for npc, quest or faction targets (kind is {a.kind})")
    if known and not edit:
        print(f'WARN: {a.kind} "{known}" already exists in the world; use --edit to update it with only the changed fields (cheaper than re-injecting)')
    batches = make_batches(text, target, studio_limit(), edit)
    st = S.get("state")
    items = st.setdefault("studio", [])
    sid = "S" + str(1 + max([int(re.sub(r"\D", "", r["id"]) or 0) for r in items] + [0]))
    items.append({"id": sid, "kind": a.kind, "target": target, "why": (a.why or "").strip(), "created_turn": a.turn,
                  "created_day": st["day"], "status": "pending", "applied_turn": None, "batches": batches,
                  **({"edit": True} if edit else {})})
    S.touch("state")
    S.commit("studio-request", a.turn, (a.why or "").strip() or "director log",
             f'{sid} {a.kind}{" (edit)" if edit else ""} "{target}": {len(text)} chars in {len(batches)} batch(es) (limit {studio_limit()})')
    print(f"Next: studio-show {sid} (paste each batch into Studio), then studio-done {sid} --turn N once the user confirms.")


def cmd_studio(a):
    items = [r for r in studio_items() if a.all or r["status"] == "pending"]
    if not items:
        print("Studio: no " + ("requests" if a.all else "pending requests"))
        return
    for r in items:
        done = sum(1 for b in r["batches"] if b["applied"])
        print(f'{r["id"]} [{r["status"]}] {r["kind"]}{" (edit)" if r.get("edit") else ""} "{r["target"]}": {done}/{len(r["batches"])} batch(es) applied, '
              f'asked turn {r["created_turn"]} (day {r["created_day"]})' + (f" - {short(r['why'], 80)}" if r.get("why") else ""))


def cmd_studio_show(a):
    r = studio_find(a.id)
    sel = [b for b in r["batches"] if a.batch is None or b["n"] == a.batch]
    if not sel:
        die(f'{r["id"]} has no batch {a.batch} (1 to {len(r["batches"])})', 2)
    print_studio_batches(r, sel)


def print_studio_batches(r, sel=None):
    """A Studio request's batches ready to paste, with character counts (studio-show; commit-turn prints new requests)."""
    sel = r["batches"] if sel is None else sel
    print(f'{r["id"]} [{r["status"]}] {r["kind"]}{" (edit)" if r.get("edit") else ""} "{r["target"]}" (limit {studio_limit()})')
    for b in sel:
        print(f'\n--- Batch {b["n"]}/{len(r["batches"])}: {len(b["text"])} chars' + (" (applied)" if b["applied"] else "") + " ---")
        print(b["text"])
    print()


def studio_effect_npc(r, turn, evidence):
    keys = list(cast())
    hit = rank(r["target"], keys, lambda k: [k, cast()[k].get("alias") or ""])
    if hit and hit[0][0] >= 0.95:
        k = hit[0][1]
        cast()[k]["in_studio"] = True
        S.touch("cast")
        return f'"{k}" flagged in_studio (cast)'
    wk = list(world_npcs())
    hit = rank(r["target"], wk, lambda k: [k])
    if hit and hit[0][0] >= 0.95:
        k = hit[0][1]
        world_npcs()[k]["in_studio"] = True
        S.touch("world-npcs")
        return f'"{k}" flagged in_studio (world-npcs)'
    name = r["target"]
    cast()[name] = {
        "name": name, "alias": None, "kind": "voyage-generated", "role": "voyage-generated", "age": None, "gender": None,
        "power": None, "placement": None, "intro_line": "", "visual": "", "personality": "",
        "voice_card": {"style": "", "sample_line": ""}, "want": "", "fear": "", "agenda": {"want": "", "next_move": ""},
        "relationships": {}, "romance_eligible": False, "type": None, "faction": None, "location": None, "area": None,
        "status": "in_play", "first_seen_turn": turn, "source_turn": turn, "evidence": evidence, "canon_notes": [],
        "in_studio": True}
    S.touch("cast")
    add_introduced(name)
    return f'"{name}" added to cast (in_play, in_studio)'


def studio_effect_quest(r, turn, evidence):
    Q, st = S.get("quests"), S.get("state")
    hit = rank(r["target"], list(Q))
    if hit and hit[0][0] >= 0.95:
        key, q = hit[0][1], Q[hit[0][1]]
        q["in_studio"] = True
        if q["status"] == "planned":
            q["status"], q["started_turn"] = "active", turn
            q.setdefault("log", []).append({"turn": turn, "event": "started (Studio)", "evidence": evidence})
        if q["status"] == "active" and key not in st["active_quests"]:
            st["active_quests"].append(key)
        msg = f'quest "{key}" is {q["status"]}, in_studio'
    else:
        key = r["target"]
        Q[key] = {"name": key, "act": current_act(st), "type": "side", "trigger": "", "giver": "", "location": None,
                  "area": None, "objectives": [], "success": "", "fail": "", "seed_line": "", "status": "active",
                  "started_turn": turn, "ended_turn": None, "places": [],
                  "log": [{"turn": turn, "event": "started (Studio)", "evidence": evidence}], "in_studio": True}
        st["active_quests"].append(key)
        msg = f'quest "{key}" created active, in_studio'
    S.touch("quests")
    S.touch("state")
    return msg


def cmd_studio_done(a):
    check_turn(a.turn)
    r = studio_find(a.id)
    if r["status"] == "applied":
        print(f'{r["id"]} is already applied (turn {r["applied_turn"]}); nothing changed.')
        return
    sel = [b for b in r["batches"] if a.batch is None or b["n"] == a.batch]
    if not sel:
        die(f'{r["id"]} has no batch {a.batch} (1 to {len(r["batches"])})', 2)
    ev = (a.evidence or "").strip() or "user confirmed the Studio batch was applied"
    for b in sel:
        if not b["applied"]:
            b["applied"], b["applied_turn"] = True, a.turn
    left = [b["n"] for b in r["batches"] if not b["applied"]]
    msg = f'{r["id"]}: batch(es) {", ".join(str(b["n"]) for b in sel)} applied'
    if left:
        msg += f"; still pending: {', '.join(map(str, left))}"
    else:
        r["status"], r["applied_turn"] = "applied", a.turn
        msg += f'; {r["kind"]} "{r["target"]}" applied'
        eff = None
        if r.get("edit"):
            eff = "edit logged; no creation effects"
            if r["kind"] == "npc":
                k = studio_known("npc", r["target"])
                for pool, nm in ((cast(), "cast"), (world_npcs(), "world-npcs")):
                    if k in pool:
                        pool[k]["in_studio"] = True
                        S.touch(nm)
                        eff += f' ("{k}" in_studio kept/set)'
                        break
        elif r["kind"] == "npc":
            eff = studio_effect_npc(r, a.turn, ev)
        elif r["kind"] == "quest":
            eff = studio_effect_quest(r, a.turn, ev)
        elif r["kind"] in ("story-fix", "canon"):
            if a.fact:
                lines = [ln.strip() for b in r["batches"] for ln in
                         re.sub(r"^Batch \d+/\d+ \u2014 .*?: ", "", b["text"], count=1).splitlines() if ln.strip()]
                c = S.get("canon")
                for ln in lines:
                    c["facts"].append({"id": next_id("f", c["facts"]), "turn": a.turn, "subject": a.fact, "fact": ln, "evidence": ev})
                S.touch("canon")
                eff = f'story-fix logged; {len(lines)} canon fact(s) recorded under "{a.fact}"'
            else:
                eff = "story-fix logged only (--fact KEY records each line as a canon fact)"
        elif r["kind"] == "area":
            if a.location:
                body = re.sub(r"^Batch \d+/\d+ — .*?: ", "", r["batches"][0]["text"], count=1)
                eff = apply_add_area(a.location, a.area_id or slug(r["target"]), a.desc or short(body, 160), a.paths, a.turn, ev)
            else:
                eff = "no --location given: logged only (add-area when the story shows it)"
        if eff:
            msg += f"; {eff}"
    S.touch("state")
    S.commit("studio-done", a.turn, ev, msg)


# ----------------------------------------------------------------------------
# record: one whole turn as a single locked, all-or-nothing write
# ----------------------------------------------------------------------------
RECORD_OPS = ["add-npc", "npc-seen", "npc-note", "agenda", "fact", "pc-add", "pc-sheet", "pos", "time",
              "quest-start", "quest-obj", "quest-end", "ledger", "clock-add", "clock-done", "thread-reveal",
              "add-area", "scene-start", "scene-obstacle", "scene-surprise", "scene-end", "feedback", "studio-request", "studio-done"]
SHEET_ARGS = ("pronouns", "power", "background", "notes")


class ArgError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    raise_errors = False  # record parses op args through the real subparsers and wants an exception, not exit(2)

    def error(self, message):
        if Parser.raise_errors:
            raise ArgError(message)
        super().error(message)


SUBS = {}  # command name -> its argparse subparser (filled by build_parser)


def op_argv(name, args, turn, evidence):
    """Turn a payload op into the argv of the matching CLI command, so record reuses the exact same parsing,
    validation and cmd_* function as the command line. Positionals go after `--` so values like -5 are safe."""
    sp = SUBS.get(name)
    if sp is None:
        raise ArgError(f"unknown op (supported: {', '.join(RECORD_OPS)})")
    args = {str(k).replace("-", "_"): v for k, v in (args or {}).items()}
    turn = args.pop("turn", turn)
    evidence = args.pop("evidence", None) or evidence
    opts, pos = [], []
    for act in sp._actions:
        if isinstance(act, argparse._HelpAction):
            continue
        d = act.dest
        if d == "turn":
            opts.append(f"--turn={turn}")
        elif d == "evidence":
            if evidence:
                opts.append(f"--evidence={evidence}")
        elif not act.option_strings:  # positional
            if d not in args:
                if act.nargs in (None, "+"):
                    raise ArgError(f"missing arg '{d}'")
                continue
            v = args.pop(d)
            if isinstance(v, list):
                if act.nargs not in ("+", "*"):
                    raise ArgError(f"arg '{d}' takes one value, got a list")
                pos += [str(x) for x in v]
            else:
                pos.append(str(v))
        elif d in args:
            v = args.pop(d)
            if isinstance(act, argparse._StoreTrueAction):
                if v:
                    opts.append(act.option_strings[0])
            elif v is not None:
                if isinstance(v, list):  # e.g. slips as a list: one entry per line
                    v = "\n".join(str(x) for x in v)
                opts.append(f"{act.option_strings[0]}={v}")
    if args:
        raise ArgError("unknown arg(s): " + ", ".join(sorted(args)))
    if name == "pc-sheet" and not any(o.split("=", 1)[0][2:] in SHEET_ARGS for o in opts):
        raise ArgError("pc-sheet in a payload must set at least one of pronouns, power, background, notes")
    return [name] + opts + (["--"] + pos if pos else [])


def run_step(label, name, args, turn, evidence):
    """Run one op through its real cmd_* function; returns (summary, notes)."""
    try:
        Parser.raise_errors = True
        try:
            ns = SUBS[name].parse_args(op_argv(name, args, turn, evidence)[1:])
        finally:
            Parser.raise_errors = False
        for v in vars(ns).values():
            if v == "-":
                raise ArgError("'-' (stdin) is not allowed in a payload")
        S.last_summary = None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ns.fn(ns)
    except ArgError as e:
        raise DbError(f"{label}: {e}", 2)
    except DbError as e:
        raise DbError(f"{label}: {e.msg}", e.code)
    notes = [ln.strip() for ln in buf.getvalue().splitlines()
             if ln.strip() and not ln.startswith("[") and not ln.startswith("  evidence:") and not ln.startswith("  wrote:")]
    return S.last_summary or (notes.pop(0) if notes else "(no change)"), notes


def check_payload(p):
    errs = []
    if not isinstance(p, dict):
        return ["payload must be a JSON object"]
    for k in p:
        if k not in ("turn", "ops", "turn_log", "save"):
            errs.append(f"unknown top-level key '{k}'")
    if not isinstance(p.get("turn"), int) or isinstance(p.get("turn"), bool) or p["turn"] < 1:
        errs.append("'turn' must be an integer of 1 or more")
    ops = p.get("ops", [])
    if not isinstance(ops, list):
        errs.append("'ops' must be a list")
        ops = []
    for i, op in enumerate(ops, 1):
        if not isinstance(op, dict) or not isinstance(op.get("op"), str):
            errs.append(f"op {i}: must be an object with an 'op' name")
        elif op["op"] not in RECORD_OPS:
            errs.append(f"op {i}: unknown op '{op['op']}' (supported: {', '.join(RECORD_OPS)})")
        elif not isinstance(op.get("args", {}), dict):
            errs.append(f"op {i} ({op['op']}): 'args' must be an object")
    tl = p.get("turn_log")
    if not isinstance(tl, dict):
        errs.append("'turn_log' is required: {inputs, summary, prompt, slips, notes}")
    else:
        for k in tl:
            if k not in ("inputs", "summary", "prompt", "slips", "notes"):
                errs.append(f"turn_log: unknown key '{k}'")
        for k in ("inputs", "summary", "prompt"):
            if not str(tl.get(k) or "").strip():
                errs.append(f"turn_log.{k} is required" + (" (use \"none\" for turn 1)" if k == "prompt" else ""))
    if "save" in p and not isinstance(p["save"], bool):
        errs.append("'save' must be true or false")
    return errs


def run_payload(p, fail_after=None):
    """Apply (or, with S.sim, simulate) every op and then the turn log. Returns [(label, summary, notes)].
    fail_after is a hidden test hook: raise after that many ops were really written (proves the restore)."""
    out, turn = [], p["turn"]
    for i, op in enumerate(p.get("ops", []), 1):
        label = f"op {i} ({op['op']})"
        summary, notes = run_step(label, op["op"], op.get("args", {}), turn, op.get("evidence"))
        out.append((f"{i}. {op['op']}", summary, notes))
        if fail_after == i:
            raise DbError(f"injected test failure after op {i}", 9)
    tl = dict(p["turn_log"])
    summary, notes = run_step("turn log", "turn", {"n": turn, **tl}, turn, None)
    out.append(("turn", summary, notes))
    return out


def plan_lines(steps, cap=None):
    lines = []
    for label, summary, notes in steps[:cap] if cap else steps:
        lines.append("  " + short(f"{label}: {summary}", 118))
    if cap and len(steps) > cap:
        lines.append(f"  ... +{len(steps) - cap} more")
    return lines


def cmd_record(a):
    try:
        payload = json.loads(Path(a.payload).read_text(encoding="utf-8"))
    except OSError as e:
        die(f"cannot read payload: {e}")
    except ValueError as e:
        die(f"payload is not valid JSON: {e}")
    errs = check_payload(payload)
    if errs:
        die("payload rejected, nothing applied:\n  " + "\n  ".join(errs), 2)
    turn = payload["turn"]
    if not a.dry_run and trial_run():
        die("record refused: this is a trial run (VOYAGE_TRIAL=1 / CLASS2B_TRIAL=1). Use --dry-run to check a payload.", EXIT_REFUSED)

    def simulate():
        S.reset()
        nxt = S.get("state")["turn"] + 1
        if turn != nxt:
            die(f"payload turn is {turn} but the next turn is {nxt} (already recorded? nothing applied)", EXIT_REFUSED)
        S.sim = True
        try:
            return run_payload(payload)
        except DbError as e:
            raise DbError(f"{e.msg.rstrip('.')}. Nothing applied.", e.code)
        finally:
            S.sim = False
            S.reset()

    if a.dry_run:
        plan = simulate()
        print(f"record turn {turn}: dry run OK, {len(plan) - 1} op(s) + turn log. Plan:")
        for ln in plan_lines(plan):
            print(ln)
        print("nothing written.")
        return

    with write_lock("record", turn):
        simulate()  # validates the whole payload against current data before anything is written
        take_snapshot(turn)
        try:
            if a.sleep:  # hidden test flag: hold the lock to prove contention is rejected
                _time.sleep(a.sleep)
            S.reset()
            steps = run_payload(payload, a.fail_after)
            bad = verify_data(turn)
            if bad:
                raise DbError("verification failed: " + "; ".join(bad))
        except BaseException as e:  # noqa: BLE001 - restore on ANY error, including Ctrl-C
            restore_snapshot(snap_dir(turn))
            shutil.rmtree(snap_dir(turn), ignore_errors=True)
            if isinstance(e, DbError):
                raise DbError(f"{e.msg.rstrip('.')}. Restored the pre-turn snapshot; nothing applied.", e.code)
            raise
        S.reset()
        print(f"record turn {turn}: ok, {len(steps) - 1} op(s) + turn log")
        for ln in plan_lines(steps, 8):
            print(ln)
        extra = [n for _, _, notes in steps for n in notes if re.search(r"WARNING|NOTE|warning|party_split|already", n)][:2]
        for n in extra:
            print("  note: " + short(n, 110))
        print(f"  verified: {len(list(DATA.glob('*.json')))} JSON files parse; state.turn {turn}; snapshot before-turn-{turn} kept")
        if payload.get("save"):
            if data_override():
                print("  save: skipped (VOYAGE_DATA / CLASS2B_DATA points at a copy)")
            else:
                save_gate()
                try:
                    do_save(a.retries)
                except PushFailed as e:
                    print(f"  {e.msg}", file=sys.stderr)
                    print("  data applied; commit kept locally.")
                    sys.exit(e.code)
                except DbError as e:
                    print(f"  data applied but save failed: {e.msg}", file=sys.stderr)
                    sys.exit(e.code if e.code != 1 else 1)


def cmd_undo_turn(a):
    with write_lock("undo-turn", a.n):
        S.reset()
        st = S.get("state")
        if a.n < 1 or a.n > st["turn"]:
            die(f"turn {a.n} is not logged (state.turn = {st['turn']})")
        d = snap_dir(a.n)
        if not d.is_dir():
            have = snap_numbers()
            die(f"no snapshot before turn {a.n}. Snapshots exist for turns: {', '.join(map(str, have)) or 'none'}")
        restore_snapshot(d)
        for n in snap_numbers():
            if n >= a.n:
                shutil.rmtree(snap_dir(n), ignore_errors=True)
        bad = verify_data(a.n - 1)
        if bad:
            die("restored, but verification failed: " + "; ".join(bad))
        print(f"undo-turn {a.n}: restored the snapshot taken before turn {a.n}; state.turn is now {S.get('state')['turn']}.")
        print("Run `db.py save` to commit the rewind if the later turns were already saved.")


def cmd_recover(a):
    """Clear a stale write lock; restore the pre-turn snapshot if a crashed `record` left the data half-applied."""
    if not DATA.is_dir():
        die(f"data directory not found: {DATA}")
    fd = os.open(lock_path(), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            info = read_lock_info()
            if info and lock_is_stale(info):
                die(f"a writer is still holding the lock but looks hung ({describe_lock(info)}). "
                    f"Kill pid {info.get('pid')} and run recover again.", EXIT_LOCKED)
            die(f"a writer is still running ({describe_lock(info) if info else 'unknown'}); recover is for a dead lock.", EXIT_LOCKED)
        info = read_lock_info()
        if not info:
            print("recover: no stale lock; nothing to do.")
            return
        print(f"recover: stale lock found ({describe_lock(info)})")
        S.reset()
        st, turns = S.get("state"), S.get("turns")
        t = info.get("turn")
        snap = snap_dir(t) if isinstance(t, int) else None
        torn = len(turns) != st["turn"]
        if info.get("cmd") == "record" and snap is not None and snap.is_dir() and (st["turn"] < t or torn):
            restore_snapshot(snap)
            shutil.rmtree(snap, ignore_errors=True)
            print(f"  restored the snapshot taken before turn {t} (state.turn was {st['turn']}); the interrupted record did not count.")
            print(f"  state.turn is now {S.get('state')['turn']}. Re-run the record payload for turn {t}.")
        elif info.get("cmd") == "record" and isinstance(t, int) and st["turn"] >= t:
            print(f"  turn {t} was fully applied (state.turn {st['turn']}); data kept. If it was not saved, run `db.py save`.")
        else:
            print("  no partial turn to undo (each update is written atomically); data kept.")
        os.ftruncate(fd, 0)
        print("  lock cleared.")
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


# ----------------------------------------------------------------------------
# names: one index of every person (aliases, short forms, ambiguity)
# ----------------------------------------------------------------------------
HONORIFIC_RE = re.compile(r"-(?:san|kun|chan|sama|sensei|senpai|sempai|dono)$", re.I)


class NameIndex:
    """Every NPC (cast.json, world-npcs.json) and player character by name form. Forms, strongest first:
    tier 0 the full name, tier 1 an explicit alias (`alias` / `aliases`), tier 2 a derived short form (first token, last
    token, title-less name). A form is ambiguous when two or more entities share its strongest tier."""

    def __init__(self):
        self.ents, self.tiers = {}, {}
        for src in (cast(), world_npcs()):
            for k, e in src.items():
                if k not in self.ents:
                    self.ents[k] = e
                    self._put(k, 0, k)
                    for al in npc_aliases(e):
                        self._put(al, 1, k)
                    for f in derived_forms(k, e):
                        self._put(f, 2, k)
        for pc in S.get("state")["player_characters"]:
            k = pc["name"]
            if k not in self.ents:
                self.ents[k] = {"_pc": True}
                self._put(k, 0, k)
                for t in k.split():
                    if len(t) >= 3 and norm(t) not in STOP:
                        self._put(t, 2, k)

    def _put(self, form, tier, key):
        f = norm(form)
        if f:
            t = self.tiers.setdefault(f, {}).setdefault(tier, [])
            if key not in t:
                t.append(key)

    def is_pc(self, key):
        return bool(self.ents.get(key, {}).get("_pc"))

    def resolve(self, form):
        """([owner keys at the strongest tier], tier); ([], None) when the form is unknown."""
        t = self.tiers.get(norm(form))
        if not t:
            return [], None
        tier = min(t)
        return list(t[tier]), tier

    def lookup(self, name):
        """(key or None, ambiguous keys): exact form first, then fuzzy matching on NPC names."""
        keys, _ = self.resolve(name)
        if len(keys) == 1:
            return keys[0], []
        if keys:
            return None, keys
        r = rank(name, [k for k in self.ents if not self.is_pc(k)], lambda k: [k] + npc_aliases(self.ents[k]))
        return (r[0][1], []) if r and r[0][0] >= 0.85 else (None, [])

    def owned(self, key):
        """Forms that point at this entity alone (what counts as a mention of it)."""
        return {f for f, t in self.tiers.items() if self.resolve(f)[0] == [key]}

    def detect(self, text):
        """({key: first position}, {form as written: [keys]}) for capitalized names found in text."""
        found, ambig = {}, {}
        for m in PHRASE_RE.finditer(text):
            toks = [HONORIFIC_RE.sub("", strip_poss(t)) for t in re.findall(CAPW, m.group(0))]
            i = 0
            while i < len(toks):
                hit = None
                for j in range(len(toks), i, -1):
                    keys, _ = self.resolve(" ".join(toks[i:j]))
                    if keys:
                        hit = (j, keys)
                        break
                if not hit:
                    i += 1
                    continue
                j, keys = hit
                if len(keys) == 1:
                    found.setdefault(keys[0], m.start())
                else:
                    ambig.setdefault(" ".join(toks[i:j]), keys)
                i = j
        return found, ambig


# ----------------------------------------------------------------------------
# git helpers for commit-turn / wrap-up / prep
# ----------------------------------------------------------------------------
def git_ctx():
    """(repo root, data dir relative to it) when git applies to this data dir; None when it is not in a git repo, or is a
    VOYAGE_DATA copy inside this very checkout (copies never touch the real history)."""
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=DATA, capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    root = Path(r.stdout.strip()).resolve()
    if data_override() and root in {Path(ROOT).resolve(), Path(__file__).resolve().parent.parent}:
        return None
    return root, str(DATA.resolve().relative_to(root))


def data_spec(rel):
    return (rel + "/*.json") if rel not in ("", ".") else "*.json"


def git_branch(root):
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"], root, check=False).stdout.strip()


def unpushed_count(root, rel):
    """Commits touching the data dir that origin/main does not have; None when it cannot be told."""
    r = run_git(["rev-list", "--count", "origin/main..HEAD", "--", rel], root, check=False)
    try:
        return int(r.stdout.strip()) if r.returncode == 0 else None
    except ValueError:
        return None


def unpushed_text():
    ctx = git_ctx()
    if not ctx:
        return "unpushed: n/a (data is not in a git repo)"
    n = unpushed_count(*ctx)
    return "unpushed: " + ("?" if n is None else str(n))


def commit_data(root, rel, msg):
    """Commit the data JSON files only. True when a commit was made."""
    spec = data_spec(rel)
    run_git(["add", "--", spec], root)
    if run_git(["diff", "--cached", "--quiet", "--", spec], root, check=False).returncode == 0:
        return False
    run_git(["commit", "-m", msg, "--", spec], root)
    return True


def push_every():
    v = CFG.get("push_every")
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 1 else 5


# ----------------------------------------------------------------------------
# expression rotation and scene presence (state.expression, state.scene.present)
# ----------------------------------------------------------------------------
def kit_items(e):
    """[(kind label, text)] of an NPC's expression kit: gestures, moods, lines."""
    x = e.get("expression") if isinstance(e.get("expression"), dict) else {}
    g = [("gesture", t) for t in x.get("gestures") or []]
    m = [(f"mood {k}", v) for k, v in (x.get("moods") or {}).items()]
    ln = [("line", t) for t in x.get("lines") or []]
    return g, m, ln


def expression_picks(key, e, st):
    """Two picks from the kit for this turn, rotating: skip what the last 2 turns used for this NPC."""
    g, m, ln = kit_items(e)
    rec = (st.get("expression") or {}).get(key) or {}
    banned = {t for turn in (rec.get("recent") or [])[-2:] for t in turn}
    cur = int(rec.get("cursor") or 0)

    def choose(pool, start):
        for off in range(len(pool)):
            it = pool[(start + off) % len(pool)]
            if it[1] not in banned:
                return it
        return pool[start % len(pool)] if pool else None
    p1 = choose(g, cur)
    second = (m, ln) if cur % 2 == 0 else (ln, m)
    p2 = choose(second[0], cur // 2) if second[0] else None
    if not p2 or p2[1] in banned:
        alt = choose(second[1], cur // 2) if second[1] else None
        p2 = alt if alt and alt[1] not in banned else p2
    return [p for p in (p1, p2) if p]


def crew_text(prompt):
    m = CREW_RE.search(prompt)
    return m.group(1) if m else ""


def crew_names(prompt, idx):
    """NPC keys named in the prompt's Crew: line (quoted words ignored), in order of appearance."""
    found, _ = idx.detect(strip_quoted(crew_text(prompt)))
    return [k for k, _p in sorted(found.items(), key=lambda kv: kv[1]) if not idx.is_pc(k)]


def used_items(key, e, prompt, idx):
    """Kit items the prompt's Crew clauses about this NPC seem to use (most of the item's words appear)."""
    forms = idx.owned(key) | {norm(key)}
    clauses = [c for c in re.split(r";|\.(?:\s|$)|\n", crew_text(prompt)) if mentions_any(c, forms)]
    blob = " ".join(clauses)
    return [t for kind_items in kit_items(e) for _k, t in kind_items if blob and overlap(blob, t) >= 0.6]


def update_presence(turn, prompt, present_override, idx):
    """Inside the record lock: store scene.present and the expression rotation. Returns a one-line summary."""
    st = S.get("state")
    names = crew_names(prompt, idx)
    sc = st.get("scene")
    if sc:
        if present_override is not None:
            sc["present"] = present_override
        elif names:
            sc["present"] = names
    exp = st.setdefault("expression", {})
    for k in names:
        e = idx.ents.get(k) or {}
        rec = exp.setdefault(k, {"recent": [], "cursor": 0})
        rec["recent"] = (rec.get("recent") or []) + [used_items(k, e, prompt, idx)]
        rec["recent"] = rec["recent"][-2:]
        rec["cursor"] = int(rec.get("cursor") or 0) + 1
    S.touch("state")
    summary = ("present: " + ", ".join((sc or {}).get("present") or []) if sc else "no open scene") + \
        f"; rotation for {len(names)} NPC(s)"
    with contextlib.redirect_stdout(io.StringIO()):
        S.commit("present", turn, "", summary)
    return summary


# ----------------------------------------------------------------------------
# prep: one compact, read-only screen before writing a turn
# ----------------------------------------------------------------------------
SLIP_RULES = {
    "fact": "check canon before stating a fact (`canon <topic>`); guard only facts at risk",
    "invention": "no invented places, NPCs or details: only what the database holds",
    "teleport": "player characters stay where they are unless the input moves them (prompt says `Continue at ...`)",
    "outcome": "never state player-character or combat outcomes; Voyage rolls them",
    "dropped": "re-send the essential ignored parts of the last prompt, as actions",
}
PICK_WIDTH = 140


def prompt_budget():
    labels = len("Cut: ") + len("Crew: ") + len("World: ") + 2
    facts = len("Facts: ") + 1
    margin = 10
    return (f"Prompt budget: limit {PROMPT_LIMIT}; labels Cut:/Crew:/World: cost {labels} (+{facts} with Facts:), keep a "
            f"{margin}-char margin: write at most {PROMPT_LIMIT - labels - margin} chars of content "
            f"({PROMPT_LIMIT - labels - facts - margin} with Facts:)"
            + ("; split party: the position header counts too" if S.get("state")["party_split"] else ""))


def compact_npc(key, e, st, idx):
    """Lines for one main NPC: voice, want, current act beat, won't-do-yet, 2 rotated expression picks."""
    act = current_act(st)
    out = [f"{key} [{e.get('status', '?')}]" + (f" @ {e['location']}/{e.get('area') or '?'}" if e.get("location") else "")]
    vc = e.get("voice_card") or {}
    out.append("  voice: " + short(vc.get("style") or MISSING, 110))
    out.append("  want: " + short(e.get("want") or MISSING, PICK_WIDTH - 8))
    out.append(f"  beat A{act}: " + short((e.get("arc_beats") or {}).get(f"act_{act}") or "(no beat for this act)", PICK_WIDTH - 12))
    wd = (e.get("wont_do_yet") or {}).get(f"act_{act}")
    out.append("  won't yet: " + short("; ".join(wd) if wd else MISSING, PICK_WIDTH - 14))
    picks = expression_picks(key, e, st)
    if picks:
        for n, (k, t) in enumerate(picks):
            out.append(("  show: " if n == 0 else "        ") + short(f'{k}: "{t}"' if k == "line" else f"{k}: {t}", PICK_WIDTH - 8))
    else:
        out.append("  show: (no expression kit)")
    return out


def one_line_npc(key, e):
    w = e.get("role") or e.get("type") or e.get("basicInfo") or ""
    where = (f"{e['location']}/{e.get('area') or '?'}" if e.get("location")
             else (f"{e['currentLocation']}/{e.get('currentArea') or '?'}" if e.get("currentLocation") else ""))
    extra = "; planned: if Voyage showed them, record npc-seen / add-npc" if e.get("status") == "planned" else ""
    return "- " + short(f"{key} [{e.get('status', 'world')}]: {w}" + (f" ({where})" if where else "") + extra, PICK_WIDTH - 2)


def place_mentions(text, st):
    """([lines], unknown 'Loc/area' refs): locations and areas named in the text, plus the PCs' positions."""
    low = " " + norm(re.sub(r"['\u2019]s\b", "", text)) + " "
    L = locations()
    lines, seen = [], set()
    for k, loc in L.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(norm(k)) + r"(?![a-z0-9])", low):
            areas = []
            for aid in loc["areas"]:
                vs = {aid, " ".join(aid.split("-")), re.sub(r"-s(?=-|$)", "s", aid).replace("-", " ")}
                if any(re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", low) for v in vs):
                    areas.append(aid)
            lines.append(f"{k}" + (f" (areas named: {', '.join(areas[:4])})" if areas else ""))
            seen.add(k)
    for pc in st["player_characters"]:
        if pc["location"] not in seen:
            lines.append(f"{pc['location']} (PC {pc['name']} is at {pc['area']})")
            seen.add(pc["location"])
    bad = []
    for m in re.finditer(r"((?:[A-Z][\w'\-]*)(?: [A-Z][\w'\-]*)*)\s*/\s*([a-z][a-z0-9\-]*)", text):
        toks = m.group(1).split()
        loc = next((" ".join(toks[i:]) for i in range(len(toks)) if " ".join(toks[i:]) in L), None)
        if loc and m.group(2) not in L[loc]["areas"]:
            bad.append(f"{loc}/{m.group(2)}")
    return lines, bad


def live_checklist(st, idx, present, places, paste):
    """Only what is live this turn. Never prints hidden ladder step text."""
    out = []
    forms = set()
    for k in present:
        forms |= idx.owned(k) | {norm(k)}
    forms |= {norm(p.split(" (")[0]) for p in places}
    watch = norm(paste) + " " + " ".join(forms)
    # canon facts and NPC notes about present names or places
    hits = [i for i in canon_items() if forms and mentions_any(i[4], forms)][-4:]
    for turn, _n, label, text, _blob in hits:
        out.append("fact at risk: " + short(f"t{turn} {label}: {text}", PICK_WIDTH - 15))
    shown = 0
    for tr in CFG.get("canon_traps") or []:
        terms = [norm(t) for t in tr.get("match") or []]
        if not terms or any(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", watch) for t in terms):
            out.append("canon trap: " + short(tr.get("text", ""), PICK_WIDTH - 12))
            shown += 1
            if shown >= 6:
                break
    # reveal ladders of present NPCs
    act = current_act(st)
    for k, t in S.get("threads").items():
        if not any(n in present for n in t.get("npcs") or []):
            continue
        rev = [x for x in t["steps"] if x["status"] == "revealed"]
        nxt = next_step(t)
        bits = []
        if rev:
            bits.append(f"public: {short(rev[-1]['reveal'], 60)}")
        if nxt:
            bits.append(f"next hidden step: {k} step {nxt['step']}" + ("" if nxt["earliest_act"] <= act else f" (act {nxt['earliest_act']})") + " - keep out")
        else:
            bits.append("ladder complete")
        out.append("ladder: " + short(" | ".join(bits), PICK_WIDTH - 8))
    # repeat slips and a reminder
    ranked, ex = slip_stats(S.get("turns"))
    if ranked:
        out.append("repeat slips: " + ", ".join(f"{c} x{n}" for c, n in ranked[:3]) + f" (latest {ranked[0][0]} T{ex[0]}: {short(ex[1], 70)})")
        top, n = ranked[0]
        if n >= 2 and top in SLIP_RULES:
            out.append(f"reminder: {top} slips are common: {SLIP_RULES[top]}")
    # scene budget
    sc = st.get("scene")
    if sc:
        if sc["turns_used"] > sc["budget"]:
            out.append(f"scene over budget by {sc['turns_used'] - sc['budget']}: `Cut:` to the next beat on a quiet input, then scene-end")
        elif sc["turns_used"] == sc["budget"]:
            out.append("scene budget used up: next quiet input gets a time skip to the next beat")
        if sc["obstacles_used"]:
            out.append(f"obstacle already used ({short('; '.join(sc['obstacles_used']), 50)}): no second one this beat")
        if sc["surprise_used"]:
            out.append("surprise already spent (one per scene)")
    for k in present:
        e = idx.ents.get(k) or {}
        if e.get("status") == "planned" and not e.get("in_studio") and e.get("intro_line"):
            out.append(f"planned NPC {k}: give the intro_line once: {short(e['intro_line'], 90)}")
    if st["party_split"]:
        out.append("party split: \U0001F4CD header and compact `Cut:` (split-scenes.md)")
    rows, turns = spotlight_rows(10)
    due = [name for cnt, _k, name in rows if cnt == 0]
    if turns and due:
        out.append("spotlight due (0 of last 10 turns): " + ", ".join(due[:4]))
    return out


def cmd_prep(a):
    st = S.get("state")
    idx = NameIndex()
    paste = ""
    if a.paste:
        pf = Path(a.paste)
        if not pf.is_file():
            die(f"no such paste file: {a.paste}")
        paste = pf.read_text(encoding="utf-8")
    present, why, warns = {}, {}, []

    def add(key, src):
        if key and not idx.is_pc(key):
            present.setdefault(key, [])
            if src not in present[key]:
                present[key].append(src)
    found, ambig = idx.detect(paste)
    for k, _pos in sorted(found.items(), key=lambda kv: kv[1]):
        add(k, "paste")
    for form, keys in ambig.items():
        warns.append(f"AMBIGUOUS name {form}: " + " | ".join(sorted(keys)[:4]) + " (name the full one or pass --names)")
    for k in (st.get("scene") or {}).get("present") or []:
        if k in idx.ents:
            add(k, "scene")
    for nm in [x.strip() for x in (a.names or "").split(",") if x.strip()]:
        key, amb = idx.lookup(nm)
        if key:
            add(key, "--names")
        elif amb:
            warns.append(f"AMBIGUOUS name {nm}: " + " | ".join(sorted(amb)[:4]))
        else:
            warns.append(f'--names: no NPC matches "{nm}"')
    main = [k for k in present if k in MAIN_NPCS or (idx.ents[k].get("kind") == "main")]
    mains, others_ = main[:4], [k for k in present if k not in main[:4]]
    act = current_act(st)
    out = [f"PREP {display()} | turn {st['turn']} (next {st['turn'] + 1}) | Day {st['day']} {st['weekday']} (Act {act}) | "
           f"{st['time_block']} {st['clock']} | {unpushed_text()}"]
    if stale_warning():
        out.append(stale_warning())
    pcs = "; ".join(f"{pc['name']} @ {pc['location']}/{pc['area']}" + (f" ({short(pc['activity'], 40)})" if pc.get("activity") else "")
                    for pc in st["player_characters"]) or "no PCs yet (pc-add)"
    out.append("PCs: " + pcs + f" | split: {'YES' if st['party_split'] else 'no'}")
    sc = st.get("scene")
    if sc:
        out.append(f"Scene \"{sc['name']}\" ({sc['location']}/{sc['area']}): {sc['turns_used']}/{sc['budget']} turns used | obstacle used: "
                   f"{'yes (' + str(len(sc['obstacles_used'])) + ')' if sc['obstacles_used'] else 'no'} | surprise used: "
                   f"{'yes' if sc['surprise_used'] else 'no'}")
    else:
        out.append("Scene: none open (scene-start when a new beat starts)")
    due = []
    for ck in sorted(st["open_clocks"], key=lambda c: c["due_day"]):
        left = ck["due_day"] - st["day"]
        if left <= 2:
            due.append(f"\"{ck['name']}\" " + (f"OVERDUE by {-left} day(s)" if left < 0 else f"due day {ck['due_day']} ({left} left)"))
    nm = next((m for m in st["calendar"] if m.get("to_day", m["day"]) >= st["day"]), None)
    out.append("Clocks: " + ("; ".join(due) if due else f"none due ({len(st['open_clocks'])} open)")
               + (f" | next milestone: Day {nm['day']}{'-' + str(nm['to_day']) if nm.get('to_day') else ''} {short(nm['name'], 60)}" if nm else ""))
    pend = [r for r in st.get("studio") or [] if r.get("status") == "pending"]
    if pend:
        out.append("Studio pending: " + "; ".join(f"{r['id']} {r['kind']} \"{r['target']}\"" for r in pend))
    out.append(prompt_budget())
    out.append("PRESENT: " + (", ".join(f"{k} ({'+'.join(v)})" for k, v in present.items()) or "nobody detected (pass --paste / --names)"))
    for w in warns:
        out.append("WARN: " + w)
    for k in mains:
        out += compact_npc(k, idx.ents[k], st, idx)
    if others_:
        out += [one_line_npc(k, idx.ents[k]) for k in others_]
    if len(main) > 4:
        out.append(f"(+{len(main) - 4} more main NPCs shown as one-liners; --full NAME for a whole brief)")
    places, bad = place_mentions(paste, st)
    out.append("Places: " + ("; ".join(places) if places else "none named") + (" | UNKNOWN AREA: " + ", ".join(bad) if bad else ""))
    Q = S.get("quests")
    low = norm(re.sub(r"['\u2019]s\b", "", paste))
    ment = [q for q in st["active_quests"] if q in Q and re.search(r"(?<![a-z0-9])" + re.escape(norm(q)) + r"(?![a-z0-9])", low)]
    if ment:
        for q in ment:
            nxt = next((o for o in Q[q]["objectives"] if o["status"] in OPEN_OBJ), None)
            out.append(f"Quest mentioned: {q}" + (f" | next: {short(nxt['text'], 80)}" if nxt else ""))
    else:
        out.append("Active quests: " + (", ".join(st["active_quests"]) or "none"))
    if paste:
        known = Known()
        unk = []
        for ph, cat in find_names(paste, known, set()):
            if cat is None and ph not in unk:
                unk.append(ph)
        if unk:
            out.append("New names in paste (not in the database): " + ", ".join(unk[:8]))
    out.append("LIVE CHECKLIST")
    chk = live_checklist(st, idx, list(present), [p.split(" (")[0] for p in places], paste)
    out += ["  - " + c for c in chk] or ["  - (nothing live)"]
    print("\n".join(out))
    if a.full:
        key, amb = idx.lookup(a.full)
        if not key:
            die(f'--full "{a.full}": ' + ("ambiguous: " + " | ".join(sorted(amb)) if amb else "no NPC matches"), 2)
        print()
        cmd_brief(argparse.Namespace(name=key))


# ----------------------------------------------------------------------------
# commit-turn and wrap-up
# ----------------------------------------------------------------------------
TIME_WORDS = {
    "dawn": "05:30", "daybreak": "05:30", "sunrise": "06:00", "first light": "05:30", "early morning": "06:30",
    "morning": "09:00", "mid morning": "10:00", "midmorning": "10:00", "late morning": "11:00", "noon": "12:00",
    "midday": "12:00", "lunch": "12:30", "lunchtime": "12:30", "afternoon": "14:00", "early afternoon": "13:00",
    "late afternoon": "16:00", "dusk": "18:30", "sunset": "18:30", "twilight": "18:30", "early evening": "17:30",
    "evening": "19:30", "nightfall": "20:00", "night": "22:30", "late evening": "21:00", "late night": "23:00",
    "midnight": "00:00", "after hours": "02:00", "small hours": "02:00", "dead of night": "02:00", "pre dawn": "04:00",
    "predawn": "04:00", "before dawn": "04:00",
}


def tidy_clock(v):
    """'6:30', '18:30:00', '6:30 pm' to HH:MM; None when it is not a clock."""
    m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})(?::\d{2})?\s*([ap]\.?m\.?)?\s*", str(v), re.I)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower().replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else None


def normalise_time_args(label, args, st, blocks, notes):
    """Forgive time words ('Dusk', 'late morning'), 'Day 5', '6:30': map to the campaign's blocks and clock."""
    if "day" in args and not isinstance(args["day"], int):
        m = re.search(r"\d+", str(args["day"]))
        if m:
            notes.append(f'{label}: day "{args["day"]}" -> {int(m.group())}')
            args["day"] = int(m.group())
    if args.get("clock") is not None:
        c = tidy_clock(args["clock"])
        if c and c != args["clock"]:
            notes.append(f'{label}: clock "{args["clock"]}" -> "{c}"')
            args["clock"] = c
    b = args.get("block")
    if not isinstance(b, str):
        return
    if {norm(x["name"]) for x in blocks} & {norm(b)}:
        want = next(x["name"] for x in blocks if norm(x["name"]) == norm(b))
        if want != b:
            notes.append(f'{label}: block "{b}" -> "{want}"')
            args["block"] = want
        return
    word = re.sub(r"[\s_\-]+", " ", norm(b))
    rep = TIME_WORDS.get(word) or TIME_WORDS.get(word.replace(" ", ""))
    if not rep:
        return
    name = block_for(rep, blocks)
    if not name:
        return
    if args.get("clock"):
        derived = block_for(args["clock"], blocks)
        if derived and derived != name:
            notes.append(f'{label}: block "{b}" dropped, clock {args["clock"]} decides ({derived})')
            args.pop("block")
            return
    args["block"] = name
    extra = ""
    if not args.get("clock") and (args.get("day") is not None or name != st["time_block"]):
        blk = next(x for x in blocks if x["name"] == name)
        args["clock"] = rep if blk["start"] <= rep <= blk["end"] else blk["start"]
        extra = f' (clock {args["clock"]})'
    notes.append(f'{label}: block "{b}" -> "{name}"{extra}')


def normalise_payload(p, st, blocks, notes):
    """Forgiving clean-up of a commit-turn payload (each change goes into notes). Returns the cleaned copy."""
    p = copy.deepcopy(p)
    if not isinstance(p, dict):
        return p
    if "save" in p:
        p.pop("save")
        notes.append("'save' ignored: commit-turn commits locally and pushes every push_every turns")
    if p.get("turn") is None:
        p["turn"] = st["turn"] + 1
        notes.append(f"turn missing -> {p['turn']}")
    elif isinstance(p["turn"], str) and p["turn"].strip().isdigit():
        p["turn"] = int(p["turn"])
        notes.append(f"turn \"{p['turn']}\" -> {p['turn']}")
    for i, op in enumerate(p.get("ops") if isinstance(p.get("ops"), list) else [], 1):
        if not isinstance(op, dict) or not isinstance(op.get("op"), str):
            continue
        name = re.sub(r"[\s_]+", "-", op["op"].strip().lower())
        if name != op["op"]:
            notes.append(f'op {i}: "{op["op"]}" -> "{name}"')
            op["op"] = name
        if "args" not in op:
            flat = {k: v for k, v in op.items() if k not in ("op", "evidence", "turn")}
            if flat:
                op["args"] = flat
                for k in flat:
                    op.pop(k)
                notes.append(f"op {i} ({name}): arguments given beside 'op' moved into 'args'")
        if name == "time" and isinstance(op.get("args"), dict):
            op["args"] = {str(k).replace("-", "_"): v for k, v in op["args"].items()}
            for old, new in (("time_block", "block"), ("time", "block"), ("when", "block")):
                if old in op["args"] and new not in op["args"]:
                    op["args"][new] = op["args"].pop(old)
                    notes.append(f"op {i} (time): '{old}' -> '{new}'")
            normalise_time_args(f"op {i} (time)", op["args"], st, blocks, notes)
    return p


def collect_payload_errors(p):
    """Every problem of a payload at once: structure, then each op and the turn log simulated in memory."""
    errs = check_payload(p)
    if not isinstance(p, dict):
        return errs, 2
    S.reset()
    nxt = S.get("state")["turn"] + 1
    if isinstance(p.get("turn"), int) and p["turn"] != nxt:
        return errs + [f"payload turn is {p['turn']} but the next turn is {nxt} (already committed?)"], EXIT_REFUSED
    S.sim = True
    try:
        turn = p.get("turn") if isinstance(p.get("turn"), int) else nxt
        for i, op in enumerate(p.get("ops") if isinstance(p.get("ops"), list) else [], 1):
            if not (isinstance(op, dict) and op.get("op") in RECORD_OPS and isinstance(op.get("args", {}), dict)):
                continue
            try:
                run_step(f"op {i} ({op['op']})", op["op"], op.get("args", {}), turn, op.get("evidence"))
            except DbError as e:
                errs.append(e.msg)
        tl = p.get("turn_log")
        if isinstance(tl, dict) and all(k in ("inputs", "summary", "prompt", "slips", "notes") for k in tl):
            try:
                run_step("turn log", "turn", {"n": turn, **tl}, turn, None)
            except DbError as e:
                if e.msg not in errs and not any(x.endswith(e.msg.split(": ", 1)[-1]) for x in errs):
                    errs.append(e.msg)
    finally:
        S.sim = False
        S.reset()
    return errs, 2


def cmd_commit_turn(a):
    pf = Path(a.prompt)
    if not pf.is_file():
        die(f"no such prompt file: {a.prompt}")
    prompt = pf.read_text(encoding="utf-8").rstrip("\n")
    try:
        payload = json.loads(Path(a.payload).read_text(encoding="utf-8"))
    except OSError as e:
        die(f"cannot read payload: {e}")
    except ValueError as e:
        die(f"payload is not valid JSON: {e}")
    if not a.dry_run and trial_run():
        die("commit-turn refused: this is a trial run (VOYAGE_TRIAL=1). Use --dry-run to check.", EXIT_REFUSED)
    print("check-prompt:")
    failed, unknown, warns = run_check(prompt, [], verbose=False)
    if failed:
        print("\ncommit-turn: FAIL in the prompt; nothing written. Fix the FAIL lines and rerun (name WARNs alone never force a rewrite).")
        sys.exit(1)
    if unknown:
        print(f"  (unknown names are a warning only: {', '.join(unknown)})")
    S.reset()
    st = S.get("state")
    blocks = S.get("world")["time"]["blocks"]
    notes = []
    present_override = None
    if isinstance(payload, dict) and "present" in payload:
        pr = payload.pop("present")
        present_override = [pr] if isinstance(pr, str) else pr
    payload = normalise_payload(payload, st, blocks, notes)
    if isinstance(payload, dict):
        tl = payload.get("turn_log")
        if isinstance(tl, dict):
            if tl.get("prompt") not in (None, "", prompt):
                notes.append("turn_log.prompt replaced by the prompt file")
            tl["prompt"] = prompt
    errs, code = collect_payload_errors(payload)
    idx = NameIndex()
    if present_override is not None:
        keys = []
        for nm in present_override if isinstance(present_override, list) else []:
            k, _amb = idx.lookup(str(nm))
            if k:
                keys.append(k)
            else:
                errs.append(f'present: no NPC matches "{nm}"')
        present_override = keys
    if notes:
        print("normalised:")
        for n in notes:
            print("  ~ " + n)
    if errs:
        print(f"\ncommit-turn: {len(errs)} problem(s), nothing written:")
        for e in errs:
            print("  - " + e.replace("\n", " "))
        sys.exit(code)
    turn = payload["turn"]
    if a.dry_run:
        S.reset()
        S.sim = True
        try:
            plan = run_payload(payload)
        finally:
            S.sim = False
            S.reset()
        print(f"\ncommit-turn {turn}: dry run OK, {len(plan) - 1} op(s) + turn log; prompt {len(prompt)}/{PROMPT_LIMIT}. Plan:")
        for ln in plan_lines(plan):
            print(ln)
        print("nothing written.")
        return
    ctx = git_ctx()
    if ctx and git_branch(ctx[0]) != "main":
        die(f"commit-turn refused: on branch {git_branch(ctx[0])!r}, not main. Nothing was written. "
            "Run `git fetch origin main && git checkout -B main origin/main`, then rerun.", EXIT_BRANCH)
    with write_lock("commit-turn", turn):
        S.reset()
        before = {r["id"] for r in studio_items()}
        take_snapshot(turn)
        try:
            S.reset()
            steps = run_payload(payload)
            idx = NameIndex()
            present_line = update_presence(turn, prompt, present_override, idx)
            bad = verify_data(turn)
            if bad:
                raise DbError("verification failed: " + "; ".join(bad))
        except BaseException as e:  # noqa: BLE001 - restore on ANY error, including Ctrl-C
            restore_snapshot(snap_dir(turn))
            shutil.rmtree(snap_dir(turn), ignore_errors=True)
            if isinstance(e, DbError):
                raise DbError(f"{e.msg.rstrip('.')}. Restored the pre-turn snapshot; nothing applied.", e.code)
            raise
        S.reset()
    print(f"\ncommit-turn {turn}: ok, {len(steps) - 1} op(s) + turn log; prompt {len(prompt)}/{PROMPT_LIMIT}")
    for ln in plan_lines(steps, 8):
        print(ln)
    print("  " + present_line)
    msg = f"{display()} save: turn {turn}"
    if not ctx:
        print("  git: skipped (data dir is not in a git repo, or is a VOYAGE_DATA copy of this checkout)")
    else:
        root, rel = ctx
        try:
            made = commit_data(root, rel, msg)
        except DbError as e:
            print(f"  WARN git commit failed ({short(e.msg, 160)}); data is saved, run `wrap-up` later.")
            made = None
        if made is not None:
            n = unpushed_count(root, rel)
            every = a.push_every or push_every()
            print(f"  git: {'committed' if made else 'nothing to commit'} \"{msg}\"; unpushed {'?' if n is None else n}/{every}")
            if n is None or n >= every:
                try:
                    i = push_main(root, a.retries)
                    print(f"  pushed main (attempt {i}); unpushed 0")
                except PushFailed as e:
                    print(f"  WARN push failed ({short(e.msg, 140)}); data is saved and committed locally; the next push or `wrap-up` retries.")
    for r in studio_items():
        if r["id"] not in before:
            print(f"\nSTUDIO request {r['id']} (paste each batch into Studio):")
            print_studio_batches(r)


def cmd_wrap_up(a):
    if trial_run():
        die("wrap-up refused: this is a trial run (VOYAGE_TRIAL=1).", EXIT_REFUSED)
    S.reset()
    bad = verify_data()
    if bad:
        die("wrap-up: data problems, not safe to close: " + "; ".join(bad))
    st = S.get("state")
    ctx = git_ctx()
    safe = None
    if not ctx:
        print("git: data dir is not in a git repo (or is a VOYAGE_DATA copy): nothing to push.")
    else:
        root, rel = ctx
        if git_branch(root) != "main":
            die(f"wrap-up refused: on branch {git_branch(root)!r}, not main. Run `git fetch origin main && git checkout -B main origin/main`.", EXIT_BRANCH)
        with write_lock("wrap-up", st["turn"]):
            if run_git(["status", "--porcelain", "--", data_spec(rel)], root, check=False).stdout.strip():
                if commit_data(root, rel, f"{display()} save: turn {st['turn']} (wrap-up)"):
                    print(f"committed uncommitted data changes (turn {st['turn']})")
            n = unpushed_count(root, rel)
            if n == 0:
                print("unpushed: 0, nothing to push.")
                safe = "all commits are on origin/main"
            else:
                print(f"unpushed: {'?' if n is None else n}; pushing...")
                try:
                    i = push_main(root, a.retries)
                    print(f"pushed main (attempt {i})")
                    safe = "pushed"
                except PushFailed as e:
                    print(f"push failed: {e.msg}", file=sys.stderr)
                    print("NOT safe to close: the data is committed locally but not pushed. Rerun `wrap-up` when the network is back.")
                    sys.exit(e.code)
    pend = [r for r in st.get("studio") or [] if r.get("status") == "pending"]
    print("Studio pending: " + ("; ".join(f"{r['id']} {r['kind']} \"{r['target']}\" ({len(r['batches'])} batch(es): `studio-show {r['id']}`)" for r in pend) if pend else "none"))
    items = []
    sc = st.get("scene")
    if sc:
        items.append(f"scene \"{sc['name']}\" open ({sc['turns_used']}/{sc['budget']})")
    for ck in st["open_clocks"]:
        left = ck["due_day"] - st["day"]
        items.append(f"clock \"{ck['name']}\" " + (f"OVERDUE {-left}d" if left < 0 else f"due day {ck['due_day']}"))
    if st["active_quests"]:
        items.append("active quests: " + ", ".join(st["active_quests"]))
    print("Open items: " + ("; ".join(items) if items else "none"))
    print(f"safe to close: {safe or 'yes (nothing in git to push)'}.")


# ----------------------------------------------------------------------------
# argument parser
# ----------------------------------------------------------------------------
def build_parser():
    p = Parser(
        prog="db.py [--campaign NAME]", description=f"{display()} director database. The database is the source of truth; never read the Voyage world export during play.",
        epilog="Updates need --turn N --evidence \"...\" (a quote or paraphrase from the story output). See README.md.")
    p.add_argument("--campaign", metavar="NAME", help="campaign under campaigns/ (default: env VOYAGE_CAMPAIGN, or the only campaign)")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    def add(name, fn, help, upd=False):
        sp = sub.add_parser(name, help=help, description=help)
        SUBS[name] = sp
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
    add("state", cmd_state, "compact summary of state, optional hidden-score modules and active quests")
    add("resume", cmd_resume, "start-of-chat summary: state header, scene, last 3 turns, clocks, milestones, quests, main NPC beats, revealed ladder steps")
    sp = add("bible", cmd_bible, "list arc-bible.md headings, or print one section (number like 6, act like act3, or a heading keyword like retest)")
    sp.add_argument("section", nargs="*")
    sp = add("spotlight", cmd_spotlight, "who got airtime (read-only): mentions of each player character and main NPC in the last N logged turns "
             "(inputs, summary, prompt), least featured first, 0 flagged")
    sp.add_argument("--last", type=int, default=10, metavar="N", help="how many recent turns to count (default 10)")
    sp = add("canon", cmd_canon, "search canon facts and NPC canon notes"); sp.add_argument("search", nargs="+")
    sp = add("recap", cmd_recap, "'Previously on <campaign>' (read-only): 3 to 5 short lines from the last N turn summaries plus up to 2 fresh canon facts; "
             "never hidden data")
    sp.add_argument("--turns", type=int, default=5, metavar="N", help="how many recent turns to recap (default 5, at most 5 lines)")
    sp = add("history", cmd_history, "search logged turns (inputs, summary, prompt, notes, slips) for all words, newest first (read-only)")
    sp.add_argument("words", nargs="+"); sp.add_argument("--limit", type=int, default=10)
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
    sp = add("ledger", cmd_ledger, "change the hidden Standing score (optional module `standing`; refused when it is off), e.g. ledger +3 \"welcome dinner\"", True)
    sp.add_argument("delta", help="+N or -N"); sp.add_argument("reason", nargs="+")
    sp = add("fact", cmd_fact, "record a fact established in play that is not in any other file", True)
    sp.add_argument("subject"); sp.add_argument("text", nargs="+")
    sp = add("pc-add", cmd_pc_add, "add a player character (starts at the story start unless --location/--area)", True)
    sp.add_argument("name"); sp.add_argument("--player", required=True); sp.add_argument("--room")
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
    sp.add_argument("--activity"); sp.add_argument("--placement", choices=SPECIALIZATIONS or None, help="specialization / placement label set after the placement event (the campaign's `placements` list, if any)")
    sp = add("time", cmd_time, f"set day / time block / clock (weekday is recomputed; Day 1 = {WEEKDAYS[0]})", True)
    sp.add_argument("--day", type=int); sp.add_argument("--block"); sp.add_argument("--clock", help="HH:MM, 24-hour")
    sp.add_argument("--allow-backward", action="store_true")
    sp = add("clock-add", cmd_clock_add, "open a clock (deadline or waiting)", True)
    sp.add_argument("name"); sp.add_argument("--due-day", type=int, required=True); sp.add_argument("--note")
    sp = add("clock-done", cmd_clock_done, "close a clock", True); sp.add_argument("name")
    sp = add("turn", cmd_turn, "log a turn (appends to turns.json, sets state.turn, counts toward an open scene)")
    sp.add_argument("n", type=int); sp.add_argument("--inputs", required=True, help="text, @file or - for stdin")
    sp.add_argument("--summary", help="REQUIRED: two lines max on what Voyage's story output established this turn")
    sp.add_argument("--prompt", required=True, help='the exact prompt sent (text, @file or -); "none" for turn 1')
    sp.add_argument("--slips", help="slips, one per line or `;`-separated, each ideally 'category: text' "
                    "(category fact|invention|teleport|outcome|dropped; untagged counts as other)")
    sp.add_argument("--notes")
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
    sp = add("scene-start", cmd_scene_start, "open a scene (validates location and area; default: the first player character's place)", True)
    sp.add_argument("name"); sp.add_argument("--budget", type=int, required=True, help="turn budget (arc-bible.md section 14)")
    sp.add_argument("--location"); sp.add_argument("--area")
    sp.add_argument("--card", help="scene card from the Planner (text or @file), stored in state.scene.card")
    def meta(sp):
        sp.add_argument("--turn", type=int, help="turn (default: the current turn)")
        sp.add_argument("--evidence", help='default: "director log"')
    sp = add("scene-card", cmd_scene_card, "print the open scene's full card (resume shows a 400-character excerpt)")
    sp = add("scene-obstacle", cmd_scene_obstacle, "record an obstacle used in the open scene")
    sp.add_argument("text", nargs="+"); meta(sp)
    sp = add("scene-surprise", cmd_scene_surprise, "mark the open scene's one surprise as used")
    sp.add_argument("--force", action="store_true"); meta(sp)
    sp = add("scene-end", cmd_scene_end, "close the open scene"); meta(sp)
    sp = add("feedback", cmd_feedback, "store player feedback (scene end: ask 'Best moment? Anything drag?'; act end: retro) in state.feedback")
    sp.add_argument("--kind", required=True, choices=FEEDBACK_KINDS)
    sp.add_argument("--best", help="best moment (text or @file)"); sp.add_argument("--drag", help="what dragged (text or @file)")
    sp.add_argument("--scene", help="scene name (default: the open scene; give it if scene-end already ran)")
    sp.add_argument("--notes"); sp.add_argument("--turn", type=int, required=True, help="current turn (not ahead of the log)")
    sp = add("studio-request", cmd_studio_request,
             "store a Studio request: the text file is split into batches of at most studio_limit characters (campaign.json, default 2000) at "
             "entity, paragraph, then sentence boundaries; hidden secret terms are refused unless --allow")
    sp.add_argument("--kind", required=True, choices=STUDIO_KINDS); sp.add_argument("--target", required=True, help="NPC, quest, faction or area name")
    sp.add_argument("--text-file", required=True, help="file with the request text (- for stdin)"); sp.add_argument("--why")
    sp.add_argument("--edit", action="store_true", help="update an entity already in the world (npc, quest, faction): send only the changed fields; batches start 'Update <target>:'; studio-done applies no creation effects")
    sp.add_argument("--turn", type=int, required=True); sp.add_argument("--allow", action="store_true", help="accept strong hidden-term hits (public terms only)")
    sp = add("studio", cmd_studio, "list pending Studio requests with batch counts (--all: applied ones too)")
    sp.add_argument("--all", action="store_true")
    sp = add("studio-show", cmd_studio_show, "print a request's batches ready to paste into Studio, with character counts")
    sp.add_argument("id"); sp.add_argument("--batch", type=int)
    sp = add("studio-done", cmd_studio_done,
             "mark a batch (or all) applied; when all are, the request is applied: npc -> cast entry flagged in_studio, quest -> active + in_studio, "
             "area -> add-area when --location is given, story-fix -> logged, plus a canon fact per line with --fact KEY")
    sp.add_argument("id"); sp.add_argument("--batch", type=int); sp.add_argument("--turn", type=int, required=True)
    sp.add_argument("--evidence", help='default: "user confirmed the Studio batch was applied"')
    sp.add_argument("--location"); sp.add_argument("--area-id", help="area kind: new area id (default: the target as a slug)")
    sp.add_argument("--desc"); sp.add_argument("--paths")
    sp.add_argument("--fact", metavar="KEY", help="story-fix kind: record each line as a canon fact with this subject")
    sp = add("save", cmd_save, "validate the JSON, commit data/ as '<display name> save: turn N' and push to origin main with retries; refuses in a trial run (exit 4) or off main (exit 8)")
    sp.add_argument("--trial", action="store_true", help="trial run: refuse (also refused when VOYAGE_TRIAL=1)")
    sp.add_argument("--retries", type=int, default=4); sp.add_argument("--dry-run", action="store_true")
    sp = add("check-prompt", cmd_check_prompt, "check a prompt file (or - for stdin): the prompt limit (state.settings.prompt_limit, default 840), unknown names, split header, planned NPCs/quests")
    sp.add_argument("file"); sp.add_argument("--allow", help="comma-separated extra names to accept")
    sp = add("record", cmd_record,
             "apply a whole turn from a JSON payload ({turn, ops, turn_log, save}) under the write lock, all or nothing; "
             "refuses unless turn == state.turn + 1; --dry-run validates and prints the plan; see docs/orchestration.md")
    sp.add_argument("payload", help="path to the payload JSON file")
    sp.add_argument("--dry-run", action="store_true", help="validate and print the plan; write nothing (allowed in a trial run)")
    sp.add_argument("--retries", type=int, default=4, help="push attempts when the payload says save: true")
    sp.add_argument("--sleep", type=float, default=0, help=argparse.SUPPRESS)  # test flag: hold the lock this many seconds
    sp.add_argument("--fail-after", type=int, default=None, help=argparse.SUPPRESS)  # test flag: fail after N written ops
    sp = add("prep", cmd_prep,
             "read-only one-screen prep for a turn: state, scene, clocks, present NPCs (names found in --paste, last turn's scene.present, "
             "--names) with compact briefs and rotated expression picks, places, quests, LIVE CHECKLIST")
    sp.add_argument("--paste", metavar="FILE", help="the last exchange (Voyage's output and the players' inputs) saved to a file")
    sp.add_argument("--names", help="comma-separated extra NPC names (aliases and short names work)")
    sp.add_argument("--full", metavar="NAME", help="also print the full brief of this NPC")
    sp = add("commit-turn", cmd_commit_turn,
             "check the prompt file, then record a whole turn from a payload ({turn, ops, turn_log}; the prompt comes from the file) "
             "all or nothing, store scene.present and expression rotation, commit data/ locally and push every push_every turns; "
             "FAIL in the prompt or any payload error writes nothing")
    sp.add_argument("--prompt", required=True, metavar="FILE"); sp.add_argument("--payload", required=True, metavar="FILE")
    sp.add_argument("--dry-run", action="store_true", help="check and print the plan; write nothing (allowed in a trial run)")
    sp.add_argument("--push-every", type=int, default=None, help="push when this many commits are unpushed (default: campaign.json push_every, 5)")
    sp.add_argument("--retries", type=int, default=3, help="push attempts")
    sp = add("wrap-up", cmd_wrap_up, "end of session: commit stray data changes, push every unpushed commit (retries), list pending Studio requests "
             "and open items, say 'safe to close' or why not")
    sp.add_argument("--retries", type=int, default=4)
    sp = add("undo-turn", cmd_undo_turn, "restore the snapshot taken before turn N and rewind state.turn (last 5 turns are kept)")
    sp.add_argument("n", type=int)
    sp = add("recover", cmd_recover, "clear a stale write lock; restore the pre-turn snapshot if a crashed record left the data half-applied")
    return p


WRITE_CMDS = {"add-npc", "npc-seen", "npc-note", "agenda", "quest-start", "quest-obj", "quest-end", "ledger", "fact",
              "pc-add", "pos", "time", "clock-add", "clock-done", "turn", "thread-reveal", "add-area", "scene-start",
              "scene-obstacle", "scene-surprise", "scene-end", "feedback", "studio-request", "studio-done", "save"}


def is_write(a):
    if a.cmd == "pc-sheet":  # show mode (no fields given) is a read
        return any(getattr(a, f) is not None for f in PC_SHEET_FIELDS)
    return a.cmd in WRITE_CMDS and not getattr(a, "dry_run", False)


def split_campaign_arg(argv):
    """Pull a global `--campaign NAME` / `--campaign=NAME` out of argv (anywhere before or after the command)."""
    out, name, i = [], None, 0
    while i < len(argv):
        x = argv[i]
        if x == "--campaign" and i + 1 < len(argv):
            name, i = argv[i + 1], i + 2
        elif x.startswith("--campaign="):
            name, i = x.split("=", 1)[1], i + 1
        else:
            out.append(x)
            i += 1
    return name, out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    name, argv = split_campaign_arg(argv)
    if name or CAMPAIGN is None:
        init_campaign(name, strict=True)
    a = build_parser().parse_args(argv)
    try:
        if is_write(a):
            turn = getattr(a, "n", None) if a.cmd == "turn" else getattr(a, "turn", None)
            with write_lock(a.cmd, turn):
                S.reset()
                a.fn(a)
        else:
            a.fn(a)
    except DbError as e:
        print(f"error: {e.msg}", file=sys.stderr)
        sys.exit(e.code)
    except BrokenPipeError:  # e.g. piped into head
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
