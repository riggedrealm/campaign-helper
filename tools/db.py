#!/usr/bin/env python3
"""Voyage director database tool, shared by every campaign (Python 3 standard library only).

The JSON files in campaigns/NAME/data are the source of truth for a campaign; everything specific to a
campaign (display name, acts, main NPCs, secret terms, optional hidden-score modules) lives in
campaigns/NAME/campaign.json. Never read the Voyage world export during play: use this tool instead.

Campaign : --campaign NAME (global option), else env VOYAGE_CAMPAIGN, else the session file written by `use NAME` (git-ignored,
           .voyage-session.json in the repo root; env DB_SESSION_FILE names another file), else the only campaign.
           Every command that runs for a campaign prints `== Display name (folder) ==` as its first stdout line.
Select   : use [NAME | --title TEXT | --clear] [--role director|planner|all-in-one|auto] (set, show or clear the session campaign and
           role), menu (campaigns and main menu; no campaign needed)
           VOYAGE_DATA (alias CLASS2B_DATA) points at a copy of the data dir; VOYAGE_TRIAL=1 (alias CLASS2B_TRIAL) = trial run.
Lookups : loc, npc, quest, faction, lore, state, resume, canon, thread, brief, bible, scene-card, arc, plan-brief, promises
Updates : add-npc, npc-seen, npc-note, agenda, quest-start, quest-obj,
          quest-end, ledger (optional module), fact, fact-status, question, question-close, pc-add, pc-sheet, pos, time,
          clock-add, clock-done, turn, thread-reveal, add-area, scene-start, scene-obstacle, scene-surprise, scene-end
          (every update except `turn` and the scene-* follow-ups needs --turn N and --evidence "...")
          pos, time, quest-start and fact take --inferred (stores inferred: true and the quote, the evidence, on the record);
          quest-end --inferred notes an apparent end and leaves the quest's status alone
Checks  : check-prompt <file or ->, scan <file or -> (read-only hidden-term scan of any user-facing text: exit 0 clean, exit 4 on a hit)
Saving  : save (validate JSON, commit data/, push with retries; refuses in a trial run)
Planner : planner [--all | --show FILE] (planner output waiting in campaigns/NAME/planner/), planner-done FILE... (the director marks it
          applied), planner-save [-m TEXT] (planner or all-in-one session: commit and push only that folder); a session whose role is
          planner refuses every command that writes campaign data (exit 4)
History : optional data/history.json (read-only range summaries of turns played before a migration; state.turn_base counts
          them) is read by history, recap and resume
Arc plan: session-zero, act-plan, act-approve, act-close, arc-plan, arc-approve, arc-offramps, arc (read), arc-pivot (read),
          plan-brief (read), planner-page;
          in play (turn ops, also valid in record/commit-turn payloads): arc-start, arc-move, arc-clue, arc-contact, arc-reveal,
          arc-review, arc-deviation, arc-close, arc-adopt, arc-unpark, act-deviation, pc-thread
          (data/arcs.json is optional; the first write creates it)
Per turn: prep [--paste F] [--names A,B] [--full N] (read-only screen), commit-turn --prompt F --payload F (check + record + local
          git commit, push every push_every turns), wrap-up (push everything, "safe to close")
Campfire: (campaign.json campfire_room) prep --packet F reads the round packet; precheck --scene F --packet F [--rulings F]
          [--ops F] checks the post before it goes out (hidden words, speaker blocks); commit-turn --scene F --rulings F --ops F
          --payload F records the posted scene after the hidden-words check (director/playbooks/campfire.md)
Batch   : record <payload.json> [--dry-run]  (a whole turn in one locked, all-or-nothing write; see docs/orchestration.md)
Sync    : sync EXPORT [--apply] (Voyage's exported state against the database: digest in data/sync.json, report in three
          classes; --apply applies class 1 only; the ticks follow Voyage's numbering)
Safety  : undo-turn N (restore the snapshot taken before turn N), recover (stale lock), scene-card
          (every write command takes an exclusive lock on data/.lock; reads never lock)

Player character sheets (pronouns, power, background, notes) come from the user;
the director never derives them from story output. Set them with pc-add or pc-sheet.
"""
import argparse
import contextlib
import copy
import datetime
import difflib
import fcntl
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time as _time
import textwrap
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planner_page  # noqa: E402
import campfire_check as CK  # noqa: E402

ROOT = Path(os.environ.get("VOYAGE_ROOT") or Path(__file__).resolve().parent.parent)
TEMPLATE_SKILL = ROOT / "templates" / "voyage-director" / "SKILL.md"
if not TEMPLATE_SKILL.is_file():  # VOYAGE_ROOT pointing at a bare tree: fall back to this checkout's template
    TEMPLATE_SKILL = Path(__file__).resolve().parent.parent / "templates" / "voyage-director" / "SKILL.md"
BOOTSTRAP_SKILL = ROOT / ".claude" / "skills" / "voyage-director" / "SKILL.md"  # the one director skill of the revamp (VER-1)
if not BOOTSTRAP_SKILL.is_file():  # VOYAGE_ROOT pointing at a bare tree: fall back to this checkout's skill
    BOOTSTRAP_SKILL = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "voyage-director" / "SKILL.md"
DEFAULT_PROMPT_LIMIT = 840
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# campaign state, filled by init_campaign()
CAMPAIGN = None          # campaign name
CAMPAIGN_DIR = None      # Path of campaigns/NAME
CFG = {}                 # parsed campaign.json
DATA = Path("/nonexistent-voyage-data")
PROMPT_LIMIT = DEFAULT_PROMPT_LIMIT
MUTABLE = []             # files a turn can change (ledger only when the standing module is on)
OPTIONAL_DATA = ("arcs",)  # data files that may be absent: readers get a skeleton, the first write creates the file
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
FACT_KINDS = ("promise", "condition", "debt", "plant")  # a fact with a kind is a promise-style record (STATE, LOG-3, NPC-4)
FACT_STATUSES = ("open", "paid")
QUESTION_STATUSES = ("open", "closed")
SCENE_KINDS = ("fight", "talk", "explore", "mystery", "downtime")  # the variety tag of a scene (SCN-1, SCN-7)
KIND_PILLAR = {"fight": "combat", "talk": "social", "explore": "exploration", "mystery": "mystery"}  # D10; downtime is reported on its own
MIX_SCENES = 10  # plan-brief's fallback window when the act's first turn is unknown: the last N scenes


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


SESSION_FILE_NAME = ".voyage-session.json"
NO_CAMPAIGN_CMDS = ("use", "menu")  # run without (or before) a campaign, so no campaign line is printed first


def session_path():
    """The session file: env DB_SESSION_FILE when set (tests point it at a temp path; the name avoids the VOYAGE_ and CLASS2B_
    prefixes that test helpers strip), else .voyage-session.json in the repo root (it is git-ignored)."""
    p = os.environ.get("DB_SESSION_FILE")
    return Path(p) if p else ROOT / SESSION_FILE_NAME


SESSION_ROLES = ("director", "planner", "all-in-one")  # the role of this chat (SES-5); absent in the file = not chosen yet
ROLE_NOT_CHOSEN = "Session role: not chosen (director, planner or all-in-one: db.py use --role ROLE)"


def read_session():
    """{"campaign": NAME, "set_at": TIMESTAMP or None, "role": ROLE or None} from the session file, or None when there is no file.
    Raises ValueError (with a message) when the file exists but cannot be used (not valid, or a role outside SESSION_ROLES)."""
    p = session_path()
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as e:
        raise ValueError(f"cannot read the session file {p}: {e}")
    try:
        d = json.loads(text)
        name = d["campaign"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("campaign is not a name")
    except (ValueError, KeyError, TypeError):
        raise ValueError(f'the session file {p} is not valid (it holds {{"campaign": NAME, "set_at": TIMESTAMP, "role": ROLE}})')
    role = d.get("role")
    if role is not None and not (isinstance(role, str) and role in SESSION_ROLES):
        raise ValueError(f"the session file {p} holds the role {role!r}, which is not one of {', '.join(SESSION_ROLES)}")
    at = d.get("set_at")
    return {"campaign": name.strip(), "set_at": at if isinstance(at, str) else None, "role": role}


def current_role():
    """This session's role from the session file (env VOYAGE_CAMPAIGN and --campaign do not change it); None when it is not chosen
    or the file cannot be used."""
    try:
        sess = read_session()
    except ValueError:
        return None
    return sess["role"] if sess else None


def role_line(sess):
    return f"Session role: {sess['role']}" if sess and sess.get("role") else ROLE_NOT_CHOSEN


def role_gate(cmd):
    """The planner's write gate (SES-4): a session whose role is `planner` writes no campaign data. Called by write_lock, the one
    place every writing command passes, and by `recover`, which writes without the lock."""
    if current_role() == "planner":
        die(f"{cmd} refused: this session is the planner; only the director session writes campaign data. "
            f"Put the output under campaigns/{CAMPAIGN or 'NAME'}/planner/ and run `db.py planner-save`.", EXIT_REFUSED)


def campaign_cfg(name):
    """The parsed campaign.json of a campaign by name ({} when it cannot be read); no campaign needs to be selected."""
    try:
        d = json.loads((ROOT / "campaigns" / name / "campaign.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def campaign_label(name, cfg):
    shown = cfg.get("display") or name
    return f"{shown} ({name})" if shown != name else name


def campaign_line(name, cfg):
    """The one-line campaign header that every command running for a campaign prints first, e.g. `== Class 2B (classroom-2b) ==`."""
    return f"== {campaign_label(name, cfg)} =="


def module_on(name):
    """True when the optional module (`standing`, `debt`) is enabled in campaign.json. Off by default."""
    return bool(((CFG.get("modules") or {}).get(name) or {}).get("enabled"))


def module_cfg(name):
    return (CFG.get("modules") or {}).get(name) or {}


CAMPFIRE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # the alphabet of a Campfire room code (playbooks/campfire.md)


def campfire_room_problem(v):
    """Why a campaign.json `campfire_room` value is not a room code (six characters of CAMPFIRE_ALPHABET), or None when it is one."""
    if not isinstance(v, str) or len(v) != 6 or any(c not in CAMPFIRE_ALPHABET for c in v):
        return f"campfire_room {v!r} is not a Campfire room code (six characters of {CAMPFIRE_ALPHABET})"
    return None


def campfire_room(cfg=None):
    """The campaign's Campfire room code (campaign.json `campfire_room`), or None when it names none or a malformed one. A room code
    is the Campfire mode signal (playbooks/campfire.md): the turn then starts only on the GM's "send" or "draft". The GM token is
    never stored in campaign-helper."""
    v = (CFG if cfg is None else cfg).get("campfire_room")
    return v if v and campfire_room_problem(v) is None else None


def init_campaign(name=None, strict=False):
    """Select the campaign (name, else VOYAGE_CAMPAIGN, else the session file, else the only one) and load its campaign.json.
    strict=False (import time): problems leave the module unconfigured instead of raising."""
    global CAMPAIGN, CAMPAIGN_DIR, CFG, DATA, PROMPT_LIMIT, MUTABLE, BIBLE, SKILL_FILE, WEEKDAYS, ACT_STARTS
    global MAIN_NPCS, SPECIALIZATIONS, SHAREHOUSE, START_AREA, HIDDEN_WORDS, SOFT_TERMS, SECRET_HINTS, PUBLIC_OK, EXTRA_KNOWN
    name = name or env_first("VOYAGE_CAMPAIGN")
    problem = None
    from_session = False
    if not name:
        try:
            sess = read_session()
        except ValueError as e:
            sess, problem = None, f"{e}: run `db.py use NAME` to replace it or `db.py use --clear` to remove it"
        if sess:
            name, from_session = sess["campaign"], True
    if not name and problem is None:
        have = list_campaigns()
        if len(have) == 1:
            name = have[0]
        else:
            problem = ("no campaign found under campaigns/" if not have else
                       "several campaigns exist (" + ", ".join(have) + "): pass --campaign NAME, set VOYAGE_CAMPAIGN, "
                       "or run `db.py use NAME` to choose one for this chat")
    if problem is None:
        cdir = ROOT / "campaigns" / name
        if not (cdir / "campaign.json").is_file():
            problem = (f"the session file {session_path()} names campaign '{name}', which no longer exists "
                       f"(campaigns: {', '.join(list_campaigns()) or 'none'}): run `db.py use NAME` to choose another or `db.py use --clear`"
                       if from_session else
                       f"campaign '{name}' not found: {cdir / 'campaign.json'} is missing (campaigns: {', '.join(list_campaigns()) or 'none'})")
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
    MUTABLE = ["state", "canon", "cast", "quests"] + (["ledger"] if module_on("standing") else []) + ["threads", "turns", "locations", "world-npcs", "arcs"]
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
            if not p.exists() and name in OPTIONAL_DATA:
                self.cache[name] = arcs_skeleton()
            elif not p.exists():
                die(f"missing data file: {p}")
            else:
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


def arcs_skeleton():
    """What data/arcs.json holds when the file does not exist yet (the first arc-planner write creates it)."""
    return {"version": 1, "page_url": None,
            "session_zero": {"tone": "", "lines": [], "veils": [], "pillars": {}, "pacing": "", "ending_hope": "", "notes": "",
                             "updated_turn": None},
            "pc_threads": [], "acts": [], "arcs": []}


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


def turn_base(st=None):
    """Turns that happened before turns.json starts (state.turn_base, default 0): a campaign migrated mid-play keeps its
    earlier history in the read-only archive (data/history.json) and turns.json holds only the turns logged since."""
    v = (st or S.get("state")).get("turn_base", 0)
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


def when(t):
    """'Day 20 Evening' for a logged turn; 't479' for a turn imported without a known day (Voyage's save keeps no per-turn day)."""
    d = t.get("day")
    if not isinstance(d, int) or isinstance(d, bool):
        return f"t{t.get('turn')}"
    return f"Day {d} {t.get('time') or ''}".strip()


def archive():
    """Entries of the optional read-only archive data/history.json (migrated range summaries); [] when there is none.
    Each entry: label, summary, optional turn_from / turn_to / kind / slip. Never written by play."""
    p = DATA / "history.json"
    if not p.exists():
        return []
    v = S.get("history")
    return [e for e in v if isinstance(e, dict)] if isinstance(v, list) else []


def archive_line(e, n=150):
    return f"[archive {e.get('label') or '?'}] " + short(re.sub(r"\s+", " ", e.get("summary") or "").strip(), n)


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
    writer (exit 7) blocks writes until `recover`. A session whose role is `planner` is refused first (exit 4)."""
    role_gate("sync" if cmd == "sync-apply" else cmd)
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
        if name in OPTIONAL_DATA and not (DATA / f"{name}.json").exists():
            continue  # restore_snapshot deletes it again: the snapshot had none
        shutil.copyfile(DATA / f"{name}.json", d / f"{name}.json")
    (d / "meta.json").write_text(json.dumps({"turn": n, "ts": _time.time()}) + "\n", encoding="utf-8")
    for old in snap_numbers()[:-SNAP_KEEP]:
        shutil.rmtree(snap_dir(old), ignore_errors=True)


def restore_snapshot(d):
    """Put the snapshot's files back (atomic per file) and drop the in-memory cache."""
    names = [n for n in MUTABLE if n not in OPTIONAL_DATA and (n != "world-npcs" or (d / f"{n}.json").exists())]  # older snapshots lack world-npcs
    for name in names:
        src = d / f"{name}.json"
        if not src.exists():
            die(f"snapshot {d.name} is missing {name}.json")
    for name in names:
        tmp = DATA / f"{name}.json.tmp"
        shutil.copyfile(d / f"{name}.json", tmp)
        os.replace(tmp, DATA / f"{name}.json")
    for name in OPTIONAL_DATA:  # an optional file the snapshot did not have is removed again
        if name not in MUTABLE:
            continue
        if (d / f"{name}.json").exists():
            tmp = DATA / f"{name}.json.tmp"
            shutil.copyfile(d / f"{name}.json", tmp)
            os.replace(tmp, DATA / f"{name}.json")
        else:
            (DATA / f"{name}.json").unlink(missing_ok=True)
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


INTENT_TEXT_FIELDS = ("want", "fear", "trigger", "refusal", "last_gesture")  # the NPC's intent in a Campfire turn (GDD v2, the NPC brief)
INTENT_FIELD_LIMIT = 240  # characters of one intent field or voice line


def intent_problems(x):
    """Problems with an optional cast `intent`: want, fear, trigger (the one active now), refusal and last_gesture, each a non-empty
    string of at most INTENT_FIELD_LIMIT characters, and voice_lines, 3 to 5 non-empty strings. Every field is optional."""
    if not isinstance(x, dict):
        return ["intent must be an object"]
    bad = [f"intent.{k} is not a known field ({', '.join(INTENT_TEXT_FIELDS)}, voice_lines)" for k in x
           if k not in INTENT_TEXT_FIELDS + ("voice_lines",)]
    for k in INTENT_TEXT_FIELDS:
        v = x.get(k)
        if k in x and not (isinstance(v, str) and v.strip() and len(v) <= INTENT_FIELD_LIMIT):
            bad.append(f"intent.{k} must be a non-empty string of at most {INTENT_FIELD_LIMIT} characters")
    vl = x.get("voice_lines")
    if "voice_lines" in x and not (_nonempty_strs(vl) and 3 <= len(vl) <= 5 and all(len(v) <= INTENT_FIELD_LIMIT for v in vl)):
        bad.append(f"intent.voice_lines must be 3 to 5 non-empty strings of at most {INTENT_FIELD_LIMIT} characters")
    return bad


def intent_lines(e, width=None):
    """Lines of a brief for an NPC's intent (nothing when the cast entry has none)."""
    it = e.get("intent") if isinstance(e, dict) else None
    if not isinstance(it, dict) or not it:
        return []
    width = width or PICK_WIDTH
    out = []
    for k, label in (("want", "wants"), ("fear", "fears"), ("trigger", "trigger now"), ("refusal", "refuses"), ("last_gesture", "last gesture")):
        if it.get(k):
            out.append(f"  {label}: " + short(it[k], width - 8))
    if it.get("voice_lines"):
        out.append("  voice lines: " + short(" | ".join(f'"{v}"' for v in it["voice_lines"]), width - 8))
    return out


def _plain_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def state_model_problems(st, canon, quests):
    """Problems with the optional fields of the state model: inferred flags and quotes, open questions, apparent ends and fact
    kinds and statuses. Data without these fields is valid."""
    bad = []

    def flag(where, rec, key="inferred", quote="quote"):
        if key in rec and not isinstance(rec[key], bool):
            bad.append(f"{where}: {key} must be true or false")
        if quote in rec and not isinstance(rec[quote], str):
            bad.append(f"{where}: {quote} must be text")

    for pc in st.get("player_characters") or []:
        if isinstance(pc, dict):
            flag(f"state.json player {pc.get('name')}", pc)
    flag("state.json time", st, "time_inferred", "time_quote")
    oq = st.get("open_questions", [])
    if not isinstance(oq, list):
        bad.append("state.json open_questions must be a list")
        oq = []
    seen = set()
    for i, q in enumerate(oq, 1):
        where = f"state.json open_questions #{i}"
        if not isinstance(q, dict):
            bad.append(f"{where}: must be an object")
            continue
        if not (isinstance(q.get("id"), str) and q["id"].strip()):
            bad.append(f"{where}: id must be text")
        elif q["id"] in seen:
            bad.append(f"{where}: duplicate id {q['id']}")
        else:
            seen.add(q["id"])
        if not (isinstance(q.get("text"), str) and q["text"].strip()):
            bad.append(f"{where}: text must be non-empty text")
        if not _plain_int(q.get("turn")):
            bad.append(f"{where}: turn must be an integer")
        if q.get("status") not in QUESTION_STATUSES:
            bad.append(f"{where}: status {q.get('status')!r} is not one of {', '.join(QUESTION_STATUSES)}")
    for f in (canon.get("facts") if isinstance(canon, dict) else None) or []:
        if not isinstance(f, dict):
            continue
        where = f"canon.json fact {f.get('id')}"
        if "kind" in f and f["kind"] not in FACT_KINDS:
            bad.append(f"{where}: kind {f['kind']!r} is not one of {', '.join(FACT_KINDS)}")
        if "status" in f and f["status"] not in FACT_STATUSES:
            bad.append(f"{where}: status {f['status']!r} is not one of {', '.join(FACT_STATUSES)}")
        flag(where, f)
    for name, q in (quests.items() if isinstance(quests, dict) else []):
        if not isinstance(q, dict):
            continue
        where = f"quests.json {name}"
        flag(where, q)
        ae = q.get("apparent_end")
        if "apparent_end" in q and not (isinstance(ae, dict) and _plain_int(ae.get("turn")) and isinstance(ae.get("quote"), str)):
            bad.append(f"{where}: apparent_end must be an object with turn (integer) and quote (text)")
    return bad


def scene_problems(st):
    """Problems with the optional scene fields (SCN-1, SCN-7): the open scene's kind and the finished-scene history
    state.scene_log. Data without them is valid."""
    bad = []
    sc = st.get("scene")
    if isinstance(sc, dict) and "kind" in sc and sc["kind"] not in SCENE_KINDS:
        bad.append(f"state.json scene: kind {sc['kind']!r} is not one of {', '.join(SCENE_KINDS)}")
    log = st.get("scene_log", [])
    if not isinstance(log, list):
        return bad + ["state.json scene_log must be a list"]
    for i, e in enumerate(log, 1):
        where = f"state.json scene_log #{i}"
        if not isinstance(e, dict):
            bad.append(f"{where}: must be an object")
            continue
        if not (isinstance(e.get("name"), str) and e["name"].strip()):
            bad.append(f"{where}: name must be non-empty text")
        if "kind" in e and e["kind"] not in SCENE_KINDS:
            bad.append(f"{where}: kind {e['kind']!r} is not one of {', '.join(SCENE_KINDS)}")
        for k in ("start_turn", "end_turn"):
            if k in e and not _plain_int(e[k]):
                bad.append(f"{where}: {k} must be an integer")
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
        live = [t for t in turns if not (isinstance(t, dict) and t.get("undone"))]  # a turn Voyage undid stays in the log, marked (SYNC-5)
        if len(live) + turn_base(st) != st["turn"]:
            bad.append(f"state.turn is {st['turn']} but turns.json has {len(live)} entries"
                       + (f" (+ turn_base {turn_base(st)})" if turn_base(st) else ""))
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
        bad += state_model_problems(st, S.get("canon"), S.get("quests"))
        bad += scene_problems(st)
        bad += planner_problems(st) + timing_problems(turns)
        for who, e in S.get("cast").items():
            if isinstance(e, dict) and "expression" in e:
                bad += [f"cast.json {who}: {m}" for m in expression_problems(e["expression"])]
            if isinstance(e, dict) and "intent" in e:
                bad += [f"cast.json {who}: {m}" for m in intent_problems(e["intent"])]
        if (DATA / "arcs.json").exists():
            bad += arcs_problems(S.get("arcs"))
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
    if q.get("inferred"):
        wrap("inferred", f"start, from: {short(q.get('quote'), 90)}")
    if q.get("apparent_end"):
        ae = q["apparent_end"]
        wrap("apparent end", f"turn {ae.get('turn')}, inferred (status unchanged), from: {short(ae.get('quote'), 90)}")
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


SCENE_EXTRAS = (("comms", "on comms"), ("elsewhere", "elsewhere"), ("pending_inputs", "pending inputs (carried over)"),
                ("pending_prompt_notes", "pending prompt notes (carried over)"))


def scene_lines(st):
    """Lines describing the open scene (or none), with an over-budget warning."""
    sc = st.get("scene")
    if not sc:
        return ["Scene: none open (scene-start <name> --budget N)"]
    used, budget = sc["turns_used"], sc["budget"]
    obs = "; ".join(sc["obstacles_used"]) or "none"
    out = [f"Scene {sc['name']} ({sc['location']}/{sc['area']}): {used}/{budget} turns, obstacles: {obs}, "
           f"surprise: {'yes' if sc['surprise_used'] else 'no'} (started turn {sc['started_turn']}" + (f", kind {sc['kind']}" if sc.get("kind") else "") + ")"]
    if used > budget:
        out.append(f"  WARNING over budget by {used - budget}: cut to the next beat on the next quiet input.")
    elif used == budget:
        out.append("  NOTE budget used up: the next quiet input gets a time skip to the next beat.")
    for key, label in SCENE_EXTRAS:  # optional carried-over scene context (migrated campaigns)
        v = sc.get(key)
        if v:
            text = "; ".join(f"{k}: {', '.join(x) if isinstance(x, list) else x}" for k, x in v.items()) if isinstance(v, dict) \
                else ("; ".join(map(str, v)) if isinstance(v, list) else str(v))
            out.append(f"  {label}: " + short(re.sub(r"\s+", " ", text), 220))
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


def inferred_items(st, max_facts=5):
    """Short labels of the records that carry the `inferred` flag (STATE-2): the time, a PC's position, an active quest's start,
    an apparent quest end, and facts (the newest few)."""
    out = []
    if st.get("time_inferred"):
        out.append("time")
    out += [f"position {pc['name']}" for pc in st["player_characters"] if pc.get("inferred")]
    Q = S.get("quests")
    for qn in st["active_quests"]:
        q = Q.get(qn) or {}
        if q.get("inferred"):
            out.append(f"quest start {qn}")
    for qn, q in Q.items():
        if isinstance(q, dict) and q.get("apparent_end") and q.get("status") not in ("completed", "failed"):
            out.append(f"apparent end of {qn} (turn {q['apparent_end'].get('turn')})")
    ids = [f["id"] for f in S.get("canon")["facts"] if f.get("inferred")]
    if ids:
        out.append("facts " + ", ".join(ids[-max_facts:]) + (f" (+{len(ids) - max_facts} older)" if len(ids) > max_facts else ""))
    return out


def cmd_state(a):
    st = S.get("state")
    print(state_header(st))
    if stale_warning():
        print(stale_warning())
    print(f"Prompt limit: {PROMPT_LIMIT} characters (data/state.json settings.prompt_limit)" + (" (skipped in Campfire mode)" if campfire_room() else ""))
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
    oq = [q for q in question_items(st) if q.get("status") == "open"]
    print(f"Open questions (director notes): {len(oq)}")
    for q in oq:
        print(f"  - {q.get('id')} (turn {q.get('turn')}): {short(str(q.get('text')), 110)}")
    inf = inferred_items(st)
    if inf:
        print("Inferred (quote on record, not confirmed): " + "; ".join(inf))
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


def director_skill_version():
    """Version line of the bootstrap skill (.claude/skills/voyage-director/SKILL.md), or a note when unreadable."""
    try:
        m = re.search(r"^Skill version:\s*(\S+)", BOOTSTRAP_SKILL.read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "unknown (no version line in the bootstrap SKILL.md)"
    except OSError:
        return "unknown (bootstrap SKILL.md not found)"


def generic_skill_campaign():
    """True when campaigns/NAME/director.md exists: the campaign runs under the generic voyage-director skill, which retires the
    old per-campaign skill pointers (fast-turn.md, player-agency.md, the repo skill version line; rule X-15)."""
    return (CAMPAIGN_DIR / "director.md").is_file()


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


RESUME_SYNC_KINDS = ("position", "time", "quest", "party", "drift")


def resume_latest_sync(st):
    """The newest well-formed entry of state.sync_log ({turn, at, tick, mismatches, applied}), or None (absent means never synced)."""
    log = st.get("sync_log")
    rows = [x for x in log if isinstance(x, dict)] if isinstance(log, list) else []
    return rows[-1] if rows else None


def sync_resume_line(st):
    """One line on the latest sync (SYNC-7): when, and the mismatch counts by type. Tolerates a missing or odd sync_log."""
    e = resume_latest_sync(st)
    if e is None:
        return "Last sync: never (no sync_log; ask for Voyage's state export, then run `sync`)"
    mm = e.get("mismatches") if isinstance(e.get("mismatches"), dict) else {}
    counts = ", ".join(f"{k} {len(mm[k]) if isinstance(mm.get(k), (list, dict)) else mm.get(k, 0)}" for k in RESUME_SYNC_KINDS)
    t = e.get("turn")
    ap = e.get("applied")
    applied = "applied" if ap is True else "dry run" if ap in (False, None) else f"applied {len(ap) if isinstance(ap, (list, dict)) else ap}"
    ago = f", {st['turn'] - t} turn(s) ago" if isinstance(t, int) and not isinstance(t, bool) and st["turn"] >= t else ""
    return (f"Last sync: turn {t if t is not None else '?'}{ago}" + (f", {e['at']}" if e.get("at") else "")
            + (f", tick {e['tick']}" if e.get("tick") is not None else "") + f"; mismatches {counts}; {applied}")


def resume_campaign_lines(st):
    """Canon traps, main NPCs and act days from campaign.json, compactly (CHAT-1)."""
    out = []
    traps = [t for t in CFG.get("canon_traps") or [] if isinstance(t, dict) and t.get("text")]
    if traps:
        out.append(f"Canon traps ({len(traps)}, from campaign.json):")
        out += ["  - " + short(t["text"], 110) for t in traps[:15]]
        if len(traps) > 15:
            out.append(f"  (+{len(traps) - 15} more: campaign.json canon_traps)")
    mains = [str(n) for n in MAIN_NPCS]
    if mains:
        out += textwrap.wrap("Main NPCs: " + ", ".join(mains), 118, subsequent_indent="  ")
    acts = [x for x in CFG.get("acts") or [] if isinstance(x, dict) and "n" in x]
    if acts:
        def span(x):
            lo, hi = x.get("from_day"), x.get("to_day")
            return f"d{lo}" + (f"-{hi}" if hi not in (None, lo) else "")
        out += textwrap.wrap("Acts: " + "; ".join(" ".join(p for p in (str(x["n"]), x.get("name") or "", span(x)) if p) for x in acts)
                             + f" (now act {current_act(st)})", 118, subsequent_indent="  ")
    if CFG.get("hard_noes"):
        bad = CK.hard_noe_problems(CFG["hard_noes"])
        out.append(f"WARN: {'; '.join(bad)}" if bad else f"Hard noes: {len(CFG['hard_noes'])} phrase(s) (campaign.json hard_noes; `hard-noes` lists them)")
    if CFG.get("campfire_room"):
        bad = campfire_room_problem(CFG["campfire_room"])
        out.append(f"WARN: {bad}: Campfire mode is off until it is fixed" if bad else
                   f"Campfire room: {CFG['campfire_room']} (a turn starts only on \"send\" or \"draft\": director/playbooks/campfire.md)")
    return out


def resume_question_lines(st):
    oq = [q for q in question_items(st) if q.get("status") == "open"]
    if not oq:
        return ["Open questions: none"]
    return [f"Open questions ({len(oq)}):"] + [f"  - {q.get('id')} (turn {q.get('turn')}): {short(str(q.get('text')), 110)}" for q in oq]


def cmd_resume(a):
    """Compact start-of-chat summary (about 60 lines at most)."""
    st = S.get("state")
    turns = S.get("turns")
    act = current_act(st)
    print(state_header(st))
    generic = generic_skill_campaign()
    if not generic:
        print(f"Skill version (repo): {skill_version()}")
    print(f"Director skill version (repo): {director_skill_version()}")
    print(generic_rules_line())
    try:
        print(role_line(read_session()))
    except ValueError:
        print(ROLE_NOT_CHOSEN)
    if not generic and (CAMPAIGN_DIR / "docs" / "fast-turn.md").exists():
        print(f"Fast turn protocol (user-set, wins over the turn loop): read campaigns/{CAMPAIGN}/docs/fast-turn.md")
    if not generic and (CAMPAIGN_DIR / "docs" / "player-agency.md").exists():
        print(f"Player agency rules (user-set, win over SKILL.md and the bible): read campaigns/{CAMPAIGN}/docs/player-agency.md")
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
    for line in arc_resume_lines(st):
        print(line)
    for line in resume_campaign_lines(st) + resume_question_lines(st):
        print(line)
    print(sync_resume_line(st))
    if st["turn"] <= 1 or find_act(current_act(st)):  # play is starting, or the campaign plans its acts
        print(preflight_summary_line())
    arch = archive()
    if turns:
        print("Last turns:")
    elif arch:
        print(f"Last turns: none logged since the migration (turn_base {turn_base(st)}); archive has {len(arch)} range summaries "
              "(history / recap read them):")
        for e in arch[-2:]:
            print("  - " + archive_line(e, 230))
    else:
        print("Last turns: none logged yet")
    for t in turns[-3:]:
        p = t.get("prompt") or ""
        full = t is turns[-1]
        print(f"- Turn {t['turn']} | {when(t)}")
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
    speed = speed_line(turns)
    if speed:
        print(speed)
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
    try:  # the first turn of a chat takes its brief from here (LOOP-2); the later ones from the end of commit-turn
        brief = next_brief_lines()
    except DbError as e:
        print(f"Next brief unavailable ({short(e.msg, 120)}): run `db.py turn-brief`")
    else:
        print()
        print("\n".join(brief))


def cmd_recap(a):
    """Short 'Previously on' for the start of a session; only public story (turn summaries and canon), never hidden data."""
    turns = S.get("turns")
    arch = archive()
    if not turns and not arch:
        print(f"Previously on {display()}: nothing yet (no turns logged).")
        return
    n = max(1, min(a.turns, 5))
    leaks = secret_terms()
    recent = turns[-n:]
    older = arch[-(n - len(recent)):] if len(recent) < n and arch else []  # fill from the migrated archive
    print(f"Previously on {display()}:")
    for e in older:
        text = re.sub(r"\s+", " ", e.get("summary") or "(no summary)").strip()
        line = f"{e.get('label') or '?'}: {text}"
        if HIDDEN_WORDS.search(line) or find_secrets(line, leaks):
            line = f"{e.get('label') or '?'}: (summary withheld: hidden terms; see `history`)"
        print("- " + short(line, 150))
    for t in recent:
        text = re.sub(r"\s+", " ", t.get("summary") or "(no summary logged)").strip()
        print(f"- {when(t)}: " + short(text, 150))
    covered = " ".join([t.get("summary") or "" for t in recent] + [e.get("summary") or "" for e in older])
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
            tags = ", ".join(x for x in (f.get("kind"), f.get("kind") and (f.get("status") or "open"), f.get("inferred") and "inferred") if x)
            print(f"- {f['id']} (turn {f['turn']}){' [' + tags + ']' if tags else ''} {f['subject']}: {f['fact']}\n    evidence: {f['evidence']}")
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


def print_turn_full(t):
    """One logged turn in full, for the director review: nothing is shortened."""
    print(f"Turn {t['turn']} | {when(t)}" + (" | arc contact" if t.get("arc_contact") else ""))
    for label, key in (("inputs", "inputs"), ("prompt", "prompt"), ("summary", "summary"), ("slips", "slips"), ("notes", "notes")):
        v = t.get(key)
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v)
        print(f"  {label}: " + (re.sub(r"\s*\n\s*", " / ", str(v).strip()) if str(v or "").strip() else "-"))
    rs = review_slips(t)
    if rs:
        print("  review slips: " + "; ".join(f"{c}: {x}" for c, x in rs))


def history_last(n):
    """`history --last N`: the last N logged turns in full, oldest first."""
    if n < 1:
        die("--last must be at least 1")
    turns = sorted(S.get("turns"), key=lambda t: t["turn"])
    if not turns:
        print("no turns logged yet")
        return
    shown = turns[-n:]
    print(f"Last {len(shown)} logged turn(s), oldest first (turn {shown[0]['turn']} to {shown[-1]['turn']}):")
    for t in shown:
        print_turn_full(t)


def cmd_history(a):
    if a.last is not None:
        if a.words:
            die("give either words to search for or --last N, not both", 2)
        history_last(a.last)
        return
    words = [w for w in (norm(x) for x in a.words) if w]
    if not words:
        die("give at least one word to search for (or --last N)")
    if a.limit < 1:
        die("--limit must be at least 1")
    turns = S.get("turns")
    arch = archive()
    if not turns and not arch:
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
    for e in reversed(arch):  # migrated range summaries, newest first, after the logged turns
        blob = norm(" ".join(str(e.get(f) or "") for f in ("label", "summary")))
        if all(w in blob for w in words):
            found.append((e, None))
    if not found:
        print("no match")
        return
    for t, fields in found[: a.limit]:
        if fields is None:
            print(f"[archive] {t.get('label')}: {snippet_around(t.get('summary'), words)}")
            continue
        first = fields[0]
        print(f"T{t['turn']} ({when(t)}): {snippet_around(t.get(first), words)}")
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
    if e.get("intent"):
        print("INTENT (Campfire; secret):")
        for ln in intent_lines(e, BRIEF_WIDTH):
            print(ln)
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


def mark_inferred(rec, a, prefix=""):
    """STATE-2: an inferred update stores `inferred: true` and the quote (the update's evidence) on the record it changes; a later
    update of the same record without --inferred clears both. `prefix` names the pair on a shared record (state: `time_`)."""
    if getattr(a, "inferred", False):
        rec[prefix + "inferred"], rec[prefix + "quote"] = True, a.evidence.strip()
    else:
        rec.pop(prefix + "inferred", None)
        rec.pop(prefix + "quote", None)


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


def cmd_npc_intent(a):
    """Set the intent fields of a cast NPC (Campfire briefs): only the fields given change."""
    need_ev(a)
    file, key, e, _ = find_npc(a.name, strict=True)
    if file != "cast":
        die(f'"{key}" is a world NPC; the intent fields belong to cast.json entries (add the NPC to the cast first)')
    new = {k: getattr(a, k) for k in INTENT_TEXT_FIELDS if getattr(a, k) is not None}
    if a.voice:
        new["voice_lines"] = a.voice
    if not new:
        die("give at least one of --want, --fear, --trigger, --refusal, --gesture (last gesture), --voice (3 to 5 lines)", 2)
    merged = {**(e.get("intent") or {}), **new}
    bad = intent_problems(merged)
    if bad:
        die("; ".join(bad), 2)
    e["intent"] = merged
    S.touch(file)
    S.commit("npc-intent", a.turn, a.evidence, f'"{key}" intent: {", ".join(sorted(new))}')


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
    if q["status"] == "active" and q.get("inferred") and not a.inferred:  # the output now states the start: confirm it
        mark_inferred(q, a)
        q["log"].append({"turn": a.turn, "event": "start confirmed", "evidence": a.evidence})
        S.touch("quests")
        S.commit("quest-start", a.turn, a.evidence, f'quest "{key}" start confirmed (no longer inferred)')
        return
    if q["status"] != "planned":
        die(f'quest "{key}" is already {q["status"]}')
    q["status"], q["started_turn"] = "active", a.turn
    q["log"].append({"turn": a.turn, "event": "started", "evidence": a.evidence})
    mark_inferred(q, a)
    st = S.get("state")
    if key not in st["active_quests"]:
        st["active_quests"].append(key)
    S.touch("quests")
    S.touch("state")
    S.commit("quest-start", a.turn, a.evidence, f'quest "{key}" planned -> active' + (" (inferred)" if a.inferred else ""))


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
    if a.inferred:  # D7: only a note; Voyage owns quest progress, `sync` confirms the end from its own status
        if a.result:
            die(f"quest-end --inferred takes no result ({a.result}): it notes an apparent end and leaves the status alone", 2)
        key, q = find_quest(a.name)
        if q["status"] in ("completed", "failed"):
            die(f'quest "{key}" is already {q["status"]}; an apparent end can only be noted on a quest that is not over')
        old = q.get("apparent_end")
        q["apparent_end"] = {"turn": a.turn, "quote": a.evidence.strip()}
        q.setdefault("log", []).append({"turn": a.turn, "event": "apparent end (inferred)", "evidence": a.evidence})
        S.touch("quests")
        S.commit("quest-end", a.turn, a.evidence,
                 f'quest "{key}" apparent end noted (inferred; status stays {q["status"]})'
                 + (f" (replaces the note from turn {old.get('turn')})" if isinstance(old, dict) else ""))
        return
    if not a.result:
        die("quest-end needs completed|failed (legacy), or --inferred to note an apparent end without changing the status", 2)
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
    if a.status and not a.kind:
        die(f"--status {a.status} needs --kind (promise, condition, debt or plant); a fact without a kind has no status", 2)
    c = S.get("canon")
    fid = next_id("f", c["facts"])
    rec = {"id": fid, "turn": a.turn, "subject": a.subject, "fact": " ".join(a.text), "evidence": a.evidence}
    if a.kind:
        rec["kind"], rec["status"] = a.kind, a.status or "open"
    mark_inferred(rec, a)
    c["facts"].append(rec)
    S.touch("canon")
    S.commit("fact", a.turn, a.evidence, f'{fid} {a.subject}: {short(" ".join(a.text), 90)}'
             + (f" [{a.kind}, {rec['status']}]" if a.kind else "") + (" (inferred)" if a.inferred else ""))


def find_fact(ident):
    """A canon fact by id: `f012`, `F12` or `12` all find f012."""
    facts = S.get("canon")["facts"]
    want = str(ident).strip().lower()
    for f in facts:
        if str(f.get("id", "")).lower() == want:
            return f
    m = re.fullmatch(r"f?0*(\d+)", want)
    if m:
        for f in facts:
            mm = re.fullmatch(r"f0*(\d+)", str(f.get("id", "")), re.I)
            if mm and int(mm.group(1)) == int(m.group(1)):
                return f
    die(f'no fact "{ident}" (ids look like f012; `promises --all` lists the facts that have a kind)', 2)


def cmd_fact_status(a):
    need_ev(a)
    f = find_fact(a.id)
    if not f.get("kind"):
        die(f"fact {f['id']} has no kind, so it is not a promise, condition, debt or plant; record it with `fact --kind` first", 2)
    old = f.get("status") or "open"
    f["status"], f["status_turn"], f["status_evidence"] = a.status, a.turn, a.evidence
    mark_inferred(f, a)
    S.touch("canon")
    S.commit("fact-status", a.turn, a.evidence,
             f'{f["id"]} {f["kind"]}: {old} -> {a.status} ({short(f["fact"], 70)})' + (" (inferred)" if a.inferred else ""))


def cmd_promises(a):
    """The promises view over facts (one store, LOG-3, NPC-4): facts that have a kind, the open ones unless --all."""
    mine = [f for f in S.get("canon")["facts"] if f.get("kind") and (not a.kind or f["kind"] == a.kind)]
    shown = [f for f in mine if a.all or (f.get("status") or "open") == "open"]
    what = f"{a.kind} facts" if a.kind else "promises, conditions, debts and plants"
    n_open = sum(1 for f in mine if (f.get("status") or "open") == "open")
    print(f"Open {what}: {n_open}" + (f" (all shown, {len(mine) - n_open} paid)" if a.all else ""))
    if not shown:
        print("  none")
    for f in shown:
        print(f"  {f['id']} [{f['kind']}, {f.get('status') or 'open'}] turn {f['turn']}" + (", inferred" if f.get("inferred") else "")
              + f" | {f['subject']}: {short(f['fact'], 130)}")


def question_items(st):
    """The well-formed entries of state.open_questions, open and closed (verify_data reports the malformed ones)."""
    v = st.get("open_questions")
    return [q for q in v if isinstance(q, dict)] if isinstance(v, list) else []


def next_question_id(items):
    return "q" + str(1 + max([int(re.sub(r"\D", "", str(i.get("id"))) or 0) for i in items] + [0]))


def cmd_question(a):
    need_ev(a)
    text = " ".join(a.text).strip()
    if not text:
        die("the question text must not be empty", 2)
    st = S.get("state")
    items = st.setdefault("open_questions", [])
    if not isinstance(items, list):
        die("state.json open_questions is not a list: fix the data (`wrap-up` names the problem) before adding a question")
    qid = next_question_id(question_items(st))
    items.append({"id": qid, "turn": a.turn, "text": text, "evidence": a.evidence, "status": "open"})
    S.touch("state")
    S.commit("question", a.turn, a.evidence, f"{qid} opened: {short(text, 90)}")


def cmd_question_close(a):
    need_ev(a)
    st = S.get("state")
    items = question_items(st)
    want = str(a.id).strip().lower()
    q = next((x for x in items if str(x.get("id")).lower() == want), None)
    if q is None and re.fullmatch(r"\d+", want):
        q = next((x for x in items if str(x.get("id")).lower() == "q" + want), None)
    if q is None:
        openq = [str(x.get("id")) for x in items if x.get("status") == "open"]
        die(f'no question "{a.id}" (open: {", ".join(openq) or "none"})', 2)
    if q.get("status") != "open":
        die(f'question {q.get("id")} is already closed (turn {q.get("closed_turn")})')
    q["status"], q["closed_turn"], q["close_evidence"] = "closed", a.turn, a.evidence
    S.touch("state")
    S.commit("question-close", a.turn, a.evidence, f'{q.get("id")} closed: {short(str(q.get("text")), 90)}')


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
    mark_inferred(pc, a)
    update_split(st)
    S.touch("state")
    S.commit("pos", a.turn, a.evidence,
             f'{pc_key}: {old} -> {loc}/{area}' + (f', {pc["activity"]}' if pc.get("activity") else "")
             + f' | party_split={st["party_split"]}' + (" | inferred" if a.inferred else ""))


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
    mark_inferred(st, a, "time_")
    S.touch("state")
    S.commit("time", a.turn, a.evidence, f"{prev} -> Day {day} {wd} {block} {clock}"
             + (f" | act {old_act} -> {st['act']}" if st["act"] != old_act else "") + (" | inferred" if a.inferred else ""))
    if day > old[0]:  # WLD-3: a new day means the world moves
        print(f"Day changed (Day {old[0]} -> Day {day}): run `db.py day-turnover`")


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


# ----------------------------------------------------------------------------
# day-turnover: what the world does on a new in-game day (read-only; WLD-2, WLD-3, PIV-6)
# ----------------------------------------------------------------------------
COLD_DAYS = 7        # WLD-2: a thread with no story contact for about 7 in-game days goes cold
OFFSCREEN_DAYS = 3   # a main NPC who has not been on screen for 3 or more in-game days moves their agenda off screen
OFFSCREEN_MAX = 8    # most off-screen agendas listed (the longest off screen first)


def _int_day(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


class StoryDays:
    """The turn log seen as days: which in-game day each logged turn fell on, and which turns name a person or a quest.
    A turn imported without a day, and a turn before state.turn_base (kept only in the history archive), has no day, so a
    contact on it cannot be dated; the turn in progress (state.turn + 1) is on the current day."""

    def __init__(self, st):
        turns = [t for t in S.get("turns") if _is_turn(t.get("turn"))]
        self.cur_turn, self.cur_day = st["turn"], st["day"]
        self.days = {t["turn"]: _int_day(t.get("day")) for t in turns}
        self.texts = [(t["turn"], norm(" ".join(str(t.get(k) or "") for k in ("inputs", "summary", "prompt")))) for t in turns]
        self.clean = turn_base(st) == 0 and all(d is not None for d in self.days.values())  # every turn since the start is dated

    def day_of(self, turn):
        if turn in self.days:
            return self.days[turn]
        return self.cur_day if turn == self.cur_turn + 1 else None

    def mentions(self, forms):
        """Turns whose inputs, summary or prompt name the person or thing (any of the normalized forms, word-bounded)."""
        forms = sorted((f for f in forms if len(f) >= 3), key=len, reverse=True)
        if not forms:
            return []
        rx = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(f) for f in forms) + r")(?![a-z0-9])")
        return [n for n, text in self.texts if rx.search(text)]

    def last_contact(self, turns, upto):
        """(day, how) of the latest of these contact turns that is not after day `upto`. how is "ok" (the day is known), "undated"
        (the latest contact turn has no day on record) or "none" (no contact at all)."""
        keep = []
        for n in turns:
            d = self.day_of(n) if _is_turn(n) else None
            if _is_turn(n) and not (d is not None and d > upto):
                keep.append(n)
        if not keep:
            return None, "none"
        d = self.day_of(max(keep))
        return (d, "ok") if d is not None else (None, "undated")


def turnover_npc_forms(key, e):
    """Normalized names that count as a main NPC being on screen (the same forms `spotlight` uses)."""
    forms = name_forms(key, e.get("alias"))
    first = norm(key).split()[0]
    if len(first) >= 3 and first not in {t.lower() for t in CFG.get("name_skip_tokens") or []}:
        forms.add(first)
    return forms


def days_text(n):
    return "today" if n == 0 else f"{n} day{'s' if n != 1 else ''}"


def turnover_clocks(st, day):
    due = sorted((c for c in st["open_clocks"] if _int_day(c.get("due_day")) is not None and c["due_day"] <= day),
                 key=lambda c: c["due_day"])
    lines = []
    for c in due:
        late = f"{days_text(day - c['due_day'])} overdue" if day > c["due_day"] else "today"
        lines.append(f"  - {c['name']}: due Day {c['due_day']} ({late})" + (f" {short(c['note'], 80)}" if c.get("note") else ""))
    return lines


def turnover_milestones(st, day):
    """Milestones whose day (or day range) holds `day`: name and place only, because a milestone's note can hold hidden values."""
    lines = []
    for m in st.get("calendar") or []:
        d = _int_day(m.get("day"))
        to = _int_day(m.get("to_day")) or d
        if d is not None and d <= day <= to:
            rng = str(d) if to == d else f"{d}-{to}"
            lines.append(f"  - Day {rng}: {m.get('name')}" + (f" ({m['place']})" if m.get("place") else ""))
    return lines


def turnover_cold(st, day, sd, undated):
    """Active quests (dated by their log and by the turns that name them) and ladders (dated by their latest revealed step)
    whose last story contact is COLD_DAYS or more days before `day`. A ladder line never carries a step."""
    cold, Q = [], S.get("quests")
    for qn in st["active_quests"]:
        q = Q.get(qn) if isinstance(Q.get(qn), dict) else {}
        end = q.get("apparent_end")
        hints = [q.get("started_turn"), end.get("turn") if isinstance(end, dict) else None]
        hints += [e.get("turn") for e in q.get("log") or [] if isinstance(e, dict)]
        d, how = sd.last_contact(hints + sd.mentions({norm(qn)}), day)
        if how != "ok":
            undated["quests"] += 1
        elif day - d >= COLD_DAYS:
            cold.append((day - d, f'  - quest "{qn}": last story contact Day {d} ({days_text(day - d)} ago)'))
    for tn, t in S.get("threads").items():
        steps = t.get("steps") or []
        if all(s.get("status") == "revealed" for s in steps):
            continue  # a finished ladder has nothing left to move
        seen = [s["revealed_day"] for s in steps if s.get("status") == "revealed" and _int_day(s.get("revealed_day")) is not None
                and s["revealed_day"] <= day]
        if seen and day - max(seen) >= COLD_DAYS:
            cold.append((day - max(seen), f'  - ladder "{tn}": last step revealed Day {max(seen)} ({days_text(day - max(seen))} ago); '
                                          f'`thread "{tn}"` shows whether a step is revealable now'))
    return [ln for _, ln in sorted(cold, key=lambda x: -x[0])]


def turnover_fronts():
    """The next front move not yet done, for every front of the live arc and of every parked arc (PIV-6)."""
    lines = []
    for arc in [x for x in arcs()["arcs"] if x.get("status") in ARC_LIVE] + parked_arcs():
        mine = []
        for fr in (arc.get("hidden") or {}).get("fronts") or []:
            moves = fr.get("moves") or []
            nxt = next((i for i, m in enumerate(moves, 1) if isinstance(m, dict) and m.get("done_turn") is None), None)
            if nxt:
                mine.append(f"    - {fr.get('name')}, move {nxt} of {len(moves)}: {short(moves[nxt - 1].get('text'), 130)}")
        if mine:
            lines.append(f'  {arc["id"]} [{arc.get("status")}] "{short(arc_title(arc), 40)}":')
            lines += mine
    return lines


def turnover_agendas(day, sd, undated):
    """Main NPCs with an agenda (cast.json) who have not been on screen for OFFSCREEN_DAYS or more days, with the agenda's next
    move. A planned NPC has not entered the story yet, so none is listed."""
    away = []  # (days off screen, name, day last on screen or None, next move)
    for n in MAIN_NPCS:
        e = cast().get(n)
        ag = (e or {}).get("agenda")
        step = str((ag or {}).get("next_move") or "").strip() if isinstance(ag, dict) else ""
        if not step or e.get("status") == "planned":
            continue
        seen = sd.mentions(turnover_npc_forms(n, e)) + ([e["first_seen_turn"]] if _is_turn(e.get("first_seen_turn")) else [])
        d, how = sd.last_contact(seen, day)
        if how == "none" and sd.clean:
            away_days = day - 1  # a complete, dated log never names them: off screen since the story began
            d, how = None, "never"
        elif how == "ok":
            away_days = day - d
        else:
            undated["npcs"] += 1
            continue
        if away_days >= OFFSCREEN_DAYS:
            away.append((away_days, n, d, step))
    away.sort(key=lambda x: (-x[0], x[1]))
    lines = []
    for away_days, n, d, step in away[:OFFSCREEN_MAX]:
        seen = "not on screen yet" if d is None else f"last on screen Day {d}, {days_text(away_days)} ago"
        lines.append(f"  - {n} ({seen}): {short(step, 110)}")
    if len(away) > OFFSCREEN_MAX:
        lines.append(f"  - (+{len(away) - OFFSCREEN_MAX} more main NPCs off screen)")
    return lines


def cmd_day_turnover(a):
    st = S.get("state")
    day = a.day if a.day is not None else st["day"]
    if day < 1:
        die("--day must be 1 or more")
    sd, undated = StoryDays(st), {"quests": 0, "npcs": 0}
    sections = [
        (f"Clocks due (open, due on or before Day {day}):", turnover_clocks(st, day)),
        (f"Milestones on Day {day} (they happen as the world acting, wherever the PC is, WLD-1):", turnover_milestones(st, day)),
        (f"Threads going cold (no story contact for {COLD_DAYS}+ days; the world moves each one a step, WLD-2):",
         turnover_cold(st, day, sd, undated)),
        ("Front moves due (the live arc and every parked arc keep moving, WLD-3, PIV-6):", turnover_fronts()),
        (f"Off-screen agendas (main NPCs not on screen for {OFFSCREEN_DAYS}+ days; each takes a step, WLD-3):",
         turnover_agendas(day, sd, undated)),
    ]
    sections = [(h, lines) for h, lines in sections if lines]
    note = ", ".join(f"{n} {what}" for n, what in ((undated["quests"], "active quest(s)"), (undated["npcs"], "main NPC(s) with an agenda"))
                     if n)
    label = f"Day {day} ({WEEKDAYS[(day - 1) % 7]}, Act {act_for_day(day)})"
    if not sections:
        print(f"Day turnover, {label}: nothing is due and nothing has gone cold or off screen."
              + (f" Not checked, no turn day on record: {note}." if note else ""))
        return
    print(f"Day turnover, {label}; read-only, one world move per prompt:")
    for head, lines in sections:
        print(head)
        print("\n".join(lines))
    if note:
        print(f"(Not checked, no turn day on record: {note}.)")


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


def review_slips(t):
    """[(category, text)] of a turn's director-review findings (`review_slips`, written by `review-add`); malformed entries are skipped."""
    v = t.get("review_slips")
    return [(x["category"], str(x.get("text") or "")) for x in v
            if isinstance(x, dict) and x.get("category") in SLIP_CATS] if isinstance(v, list) else []


def slip_stats(turns):
    """([(category, count)] most common first, most recent (turn, text) of the top category) over all logged turns,
    the turn's own slips and the director-review findings alike (REVIEW-1)."""
    counts, last = {}, {}
    for t in turns:
        for cat, text in parse_slips(t.get("slips")) + review_slips(t):
            counts[cat] = counts.get(cat, 0) + 1
            last[cat] = (t["turn"], text)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0] == "other", kv[0]))
    return ranked, (last[ranked[0][0]] if ranked else None)


def print_slip_stats(turns):
    ranked, ex = slip_stats(turns)
    if not ranked:
        return
    from_reviews = sum(len(review_slips(t)) for t in turns)
    print("Repeat slips: " + ", ".join(f"{c} x{n}" for c, n in ranked[:3])
          + (f" ({from_reviews} of {sum(n for _, n in ranked)} from director reviews)" if from_reviews else ""))
    print(f"  latest {ranked[0][0]}: T{ex[0]}: {short(ex[1], 150)}")


def cmd_turn(a):
    st, turns = S.get("state"), S.get("turns")
    if a.n != st["turn"] + 1:
        die(f"turns are logged in order: next is {st['turn'] + 1}, got {a.n}")
    if any(t["turn"] == a.n and not t.get("undone") for t in turns):
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
    if getattr(a, "arc_contact", False):
        entry["arc_contact"] = True  # the PC engaged the active arc's pressure this turn
    timing = None
    if getattr(a, "timing", None):  # commit-turn's own timing (SES-9), given as JSON text
        try:
            timing = json.loads(a.timing)
        except ValueError:
            die("--timing must be JSON text")
    if getattr(a, "escalated", False):  # the turn took the slow path; without commit-turn's timing only this is known
        timing = {**(timing or {"received": None, "checked": None, "committed": now_iso()}), "escalated": True}
    if timing is not None:
        bad = timing_problems([{"turn": a.n, "timing": timing}])
        if bad:
            die("; ".join(bad))
        entry["timing"] = timing
    if getattr(a, "scene_text", None):  # commit-turn --scene's record (Campfire mode), set after validation like timing
        entry["scene"] = a.scene_text
    for key, raw in (("rulings", getattr(a, "rulings_json", None)), ("campfire_ops", getattr(a, "campfire_ops_json", None))):
        if raw:
            try:
                entry[key] = json.loads(raw)
            except ValueError:
                die(f"--{key.replace('_', '-')}-json must be JSON text")
    for tag in unknown_slip_tags(entry["slips"]):
        print(f"warning: slip category '{tag}' is not one of {'|'.join(SLIP_CATS)}; counted as other")
    turns.append(entry)
    st["turn"] = a.n
    sc = st.get("scene")
    if sc:
        sc["turns_used"] += 1
        for k in ("pending_inputs", "pending_prompt_notes"):  # carried-over items are superseded by this turn's paste
            sc.pop(k, None)
    S.touch("turns")
    S.touch("state")
    plen = 0 if is_none else len(prompt)
    S.commit("turn", a.n, "", f"logged turn {a.n} (Day {st['day']} {entry['time']}); "
             + (f"scene {len(entry['scene'])} chars" if "scene" in entry else f"prompt {plen}/{PROMPT_LIMIT} chars"))
    if sc:
        for line in scene_lines(st):
            print(line)


def parse_review_slips(v):
    """[(category, text)] from a `review-add --slips` value: findings separated by `;` or a new line, each `category: text` with one
    of the five slip tags. Any other tag, a missing tag or empty text is refused (the review's `other` findings are never recorded)."""
    out = []
    for part in re.split(r"[;\n]", v or ""):
        part = part.strip()
        if not part:
            continue
        m = _SLIP_TAG.match(part)
        if not m:
            die(f'review finding "{short(part, 60)}" has no tag: write "category: text" with category {"|".join(SLIP_CATS)}', 2)
        tag, text = m.group(1).lower(), m.group(2).strip()
        if tag not in SLIP_CATS:
            die(f'review finding tag "{m.group(1)}" is not one of {"|".join(SLIP_CATS)}: decide "other" findings yourself, never record them', 2)
        if not text:
            die(f'review finding "{tag}:" has no text', 2)
        out.append((tag, text))
    if not out:
        die('give --slips "category: text; category: text" (category ' + "|".join(SLIP_CATS) + ")", 2)
    return out


def cmd_review_add(a):
    """Record director-review findings on a logged turn, apart from the turn's own slips (`review_slips`, source review). Runs under
    the write lock; the review subagent itself stays read-only (D8)."""
    found = parse_review_slips(read_arg_text(a.slips))
    turns = S.get("turns")
    t = next((x for x in turns if x.get("turn") == a.turn), None)
    if t is None:
        have = [x["turn"] for x in turns]
        die(f"turn {a.turn} is not in the turn log (logged: " + (f"{have[0]} to {have[-1]}" if have else "none") + ")", 2)
    cur = t.get("review_slips")
    if cur is None:
        cur = t["review_slips"] = []
    if not isinstance(cur, list):
        die(f"turn {a.turn}: review_slips in turns.json is not a list: fix the data first")
    added = []
    for cat, text in found:
        if not any(isinstance(x, dict) and x.get("category") == cat and x.get("text") == text for x in cur):
            cur.append({"category": cat, "text": text, "source": "review"})
            added.append(cat)
    if not added:
        print(f"review-add: turn {a.turn} already holds these findings; nothing written.")
        return
    S.touch("turns")
    S.commit("review-add", get_state_turn(), "director review",
             f"turn {a.turn}: {len(added)} review finding(s) ({', '.join(added)})")


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


def scene_history(st):
    """Every scene in order, oldest first: the finished ones (state.scene_log, written at scene-end) and then the open one.
    Each is {name, kind, start_turn, end_turn}; kind is None for a scene without a tag (untagged), end_turn None while open."""
    log = st.get("scene_log")
    out = [{"name": e.get("name"), "kind": e.get("kind"), "start_turn": e.get("start_turn"), "end_turn": e.get("end_turn")}
           for e in (log if isinstance(log, list) else []) if isinstance(e, dict)]
    sc = st.get("scene")
    if isinstance(sc, dict):
        out.append({"name": sc.get("name"), "kind": sc.get("kind"), "start_turn": sc.get("started_turn"), "end_turn": None})
    return out


def same_kind_run(st):
    """The kind shared by the last three scenes (the open scene counts), or None (SCN-7). Untagged scenes never match."""
    kinds = [x["kind"] for x in scene_history(st)[-3:]]
    return kinds[0] if len(kinds) == 3 and kinds[0] and len(set(kinds)) == 1 else None


def cmd_scene_start(a):
    need_ev(a)
    st = S.get("state")
    if st.get("scene"):
        die(f'scene "{st["scene"]["name"]}" is still open: scene-end it first')
    if a.budget < 1:
        die("--budget must be 1 or more (see `db.py bible budgets`)")
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
    if a.kind:
        st["scene"]["kind"] = a.kind
    if card:
        st["scene"]["card"] = card
    S.touch("state")
    S.commit("scene-start", a.turn, a.evidence,
             f'scene "{a.name}" at {loc}/{area}, budget {a.budget}' + (f", kind {a.kind}" if a.kind else "")
             + (f", card {len(card)} chars" if card else ""))
    run = same_kind_run(st)
    if run:  # SCN-7: three of a kind in a row, counting this scene
        names = ", ".join(f'"{short(x["name"], 30)}"' for x in scene_history(st)[-3:])
        print(f"WARNING variety: three {run} scenes in a row ({names}); give the next beat a different kind")


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
    entry = {"name": sc["name"]}  # the compact history of finished scenes: the variety check and plan-brief read it
    if sc.get("kind"):
        entry["kind"] = sc["kind"]
    if _plain_int(sc.get("started_turn")):
        entry["start_turn"] = sc["started_turn"]
    if _plain_int(turn):
        entry["end_turn"] = turn
    st.setdefault("scene_log", []).append(entry)
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
                  f"{' (FORCED)' if s.get('forced') else ''}{' (PLAYER-DRIVEN)' if s.get('player_driven') else ''}: {s.get('evidence')}")
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
    act_problem = None
    if s["earliest_act"] > act:
        act_problem = (f"step {a.step} needs Act {s['earliest_act']} (from Day {ACT_STARTS[s['earliest_act']]}); "
                       f"now Act {act}, Day {st['day']}")
        problems.append(act_problem)
    early = [x["step"] for x in t["steps"] if x["step"] < a.step and x["status"] == "hidden"]
    if early:
        problems.append("earlier step(s) still hidden: " + ", ".join(map(str, early)))
    if s.get("milestone_gate") and not a.gate_met:
        problems.append(f"milestone gate not confirmed: {s['milestone_gate']} (pass --gate-met once it has happened)")
    pulled = False
    if getattr(a, "player_driven", False) and act_problem and s["earliest_act"] == act + 1:
        rest = [p for p in problems if p is not act_problem]
        if not rest:  # no unmet gate, every earlier step revealed: one act early is allowed
            problems, pulled = [], True
            print(f"player-driven pull-forward: step {a.step} moves up from Act {s['earliest_act']} to Act {act}.")
        else:
            problems.append("--player-driven covers only the act, not gates or earlier steps")
    elif getattr(a, "player_driven", False) and act_problem:
        problems.append("--player-driven moves a step up only ONE act")
    if problems and not a.force:
        die(f'refused to reveal "{key}" step {a.step}: ' + "; ".join(problems) + ". Use --force only to override on purpose.", 4)
    if problems:
        print("warning: --force overrides: " + "; ".join(problems))
    s["status"], s["revealed_turn"], s["revealed_day"], s["evidence"] = "revealed", a.turn, st["day"], a.evidence
    if problems:
        s["forced"] = True
    if pulled:
        s["player_driven"] = True
    S.touch("threads")
    S.commit("thread-reveal", a.turn, a.evidence,
             f'"{key}" step {a.step} revealed: {short(s["reveal"], 80)}'
             + (" (FORCED)" if problems else " (PLAYER-DRIVEN, one act early)" if pulled else ""))


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
    for arc in arcs()["arcs"]:  # twists of live arcs that are not yet revealed (a twist tied to a ladder is covered above)
        tw = (arc.get("hidden") or {}).get("twist") or {}
        if arc.get("status") in ARC_DONE or tw.get("revealed_turn") is not None:
            continue
        for kw in tw.get("keywords") or []:
            n = norm(kw)
            old = out.get(n)
            if len(n) >= 4 and n not in PUBLIC_OK and (old is None or (n not in SOFT_TERMS and not old[1])):
                out[n] = (f"arc {arc['id']} twist", n not in SOFT_TERMS)
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


# A player character's condition, feeling, thought, decision or words (AGY-2): a rough lexical net. The name must be followed closely:
# only an auxiliary or adverb may sit between it and the word, and a possessive ("Aiko's tea feels cold") never matches.
COND_GAP = (r"(?:[ \t]+(?:is|was|are|were|has|had|will|would|can|could|does|did|do|just|now|then|still|also|already|suddenly|visibly|"
            r"clearly|really|quite|very|badly|slightly|barely|only|even|always|finally|somehow|simply|quietly|softly|never|not))")
COND_VERBS = (r"limps?|limped|limping|bleeds?|bled|bleeding|winces?|flinches?|trembles?|shivers?|stumbles?|collapses?|faints?|hurts?|aches?|"
              r"feels?|felt|thinks?|thought|wonders?|wondered|reali[sz]es?|reali[sz]ed|knows?|knew|wants?|wanted|wishes|hopes?|fears?|"
              r"decides?|decided|chooses?|chose|resolves?|resolved|agrees?|agreed|refuses?|refused|accepts?|accepted|"
              r"says?|said|replies|replied|answers?|answered|asks?|asked|whispers?|shouts?|admits?|confesses?|promises?|"
              r"pass(?:es|ed)?(?:[ \t]+(?:the|her|his|their|a)\b)?[ \t]+(?:check|test|roll|trial|exam|evaluation|audition|inspection|interview)|"
              r"pass(?:es|ed)(?=[ \t]*(?:[.,;:!?)]|$))")
COND_ADJ = (r"hurt|injured|wounded|bleeding|limping|unhurt|unharmed|fine|okay|ok|safe|dead|dying|unconscious|exhausted|tired|scared|afraid|"
            r"terrified|angry|furious|nervous|anxious|happy|sad|calm|embarrassed|ashamed|worried|relieved|hungry|sick|ill|drunk|dizzy|numb|shaken")
COND_BE = r"(?:is|was|are|were|looks?|seems?|appears?|gets?|got|becomes?|became|stays?|remains?)"
COND_LEAD = re.compile(r"\b(?:if|when|whenever|unless|once|until|should|whether|after|before)\s+(?:[\w'\u2019\-]+\s+)?$", re.I)


AS_PC_CHOSE_RE = re.compile(r"\b(?:chose|choose)$", re.I)
AS_LEAD_RE = re.compile(r"\b(?i:as)[ \t]+(?:[A-Z][\w'\u2019\-]*[ \t]+){0,2}$")  # "as " or "as Alistair " right before the matched name part


def stated_outcomes(text, pcs):
    """Sentences-ish snippets where a player character is told to succeed/fail/hit/... or is given a condition, feeling, thought,
    decision or words (limps, is hurt, feels, decides, says, passes ...). Quoted text is ignored."""
    plain, out = strip_quoted(text), []
    names = set()
    for n in pcs:
        names.add(n)
        names.update(t for t in n.split() if len(t) >= 3)
    for n in sorted(names, key=len, reverse=True):
        nm = r"(?<!\w)" + re.escape(n)
        for i, pat in enumerate((nm + r"(?:['\u2019]s)?(?:[ \t,]+[\w'\u2019\-]+){0,3}?[ \t,]+(?:" + OUTCOME_VERBS + r")\b",
                                 nm + r"(?![\w'\u2019])" + COND_GAP + r"{0,2}[ \t]+(?:" + COND_VERBS + r")\b",
                                 nm + r"(?![\w'\u2019])[ \t]+" + COND_BE + COND_GAP + r"*[ \t]+(?:" + COND_ADJ + r")\b")):
            for m in re.finditer(pat, plain, re.I):
                if i and COND_LEAD.search(plain[max(0, m.start() - 30): m.start()]):
                    continue  # "If Aiko asks ...": a condition for an NPC to answer, not a stated act
                if i == 1 and AS_PC_CHOSE_RE.search(m.group(0)) and AS_LEAD_RE.search(plain[max(0, m.start() - 60): m.start()]):
                    continue  # "as Alistair chose": the Cut restating the player's own input, not a decision the prompt makes
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


# ---- agency warnings of check-prompt (HO 4.6.6): WARN only, never a FAIL, never a change of the exit code ----
def _label_re(label):
    others = "|".join(x for x in LABELS if x != label)
    return re.compile(r"^[ \t]*" + label + r"[ \t]*:(.*?)(?=^[ \t]*(?:" + others + r")[ \t]*:|\Z)", re.M | re.S)


CUT_RE, TONE_RE, FACTS_RE = _label_re("Cut"), _label_re("Tone"), _label_re("Facts")
PLACE_PREP = r"(?i:\b(?:at|in|into|inside|outside|to|near|toward|towards|onto|beside|behind|around))"
SLASH_PLACE_RE = re.compile(r"((?:[A-Z][\w'\-]*)(?: [A-Z][\w'\-]*)*)\s*/\s*([a-z][a-z0-9\-]*)")
CUT_PLACE_RE = re.compile(PLACE_PREP + r"[ \t]+(?:(?i:the)[ \t]+)?(" + CAPW + r"(?:[ \t]+(?:(?:of|the|and|de|no)[ \t]+)?" + CAPW + r")*)")


def place_known(toks, known, L):
    """A place phrase (tokens) is a known location, or a known location followed by one of its areas, or any other known name."""
    for j in range(len(toks), 0, -1):
        cand = " ".join(toks[:j])
        cat = known.cat(cand)
        if cat is None:
            continue
        if j == len(toks) or cat != "location":
            return True
        loc = next((k for k in L if norm(k) == norm(cand)), None)
        return bool(loc and any(slug(a) == slug(" ".join(toks[j:])) for a in L[loc]["areas"]))
    return False


def place_warnings(text, known):
    """FMT-7: a `Location/area` reference whose location is not in the database (an unknown area of a known location is
    flagged by the name check already), and a capitalised place in `Cut:` that is no location, area or other known name."""
    out, L, seen = [], locations(), set()
    for m in SLASH_PLACE_RE.finditer(text):
        toks = m.group(1).split()
        if any(" ".join(toks[i:]) in L for i in range(len(toks))):
            continue  # a known location: an unknown area is already flagged as UNKNOWN AREA
        if any(known.cat(" ".join(toks[i:])) not in (None, "location") for i in range(len(toks))):
            continue  # a person, faction or quest, not a place
        ref = f"{m.group(1)}/{m.group(2)}"
        seen.add(m.group(1))  # the Cut check below must not repeat the same place
        if ref not in seen:
            seen.add(ref)
            out.append(f'place "{ref}" is not a location in the database (FMT-7): use an existing location and area; add-area only inside an existing location')
    cm = CUT_RE.search(text)
    for m in CUT_PLACE_RE.finditer(strip_quoted(cm.group(1)) if cm else ""):
        toks = m.group(1).split()
        while toks and norm(strip_poss(toks[-1])) in STOP:
            toks.pop()
        while toks and norm(toks[0]) in STOP:
            toks.pop(0)
        if not toks:
            continue
        toks[-1] = strip_poss(toks[-1])
        phrase = " ".join(toks)
        if phrase not in seen and not place_known(toks, known, L):
            seen.add(phrase)
            out.append(f'`Cut:` place "{phrase}" is not a location or area in the database (FMT-7): use an existing place; add-area only inside an existing location')
    return out


RULE_RE = re.compile(r"\b(?:must|cannot|can['\u2019]t|can\s+not|may\s+not|requires?|required|not\s+(?:allowed|permitted)|"
                     r"(?:is|are)(?:n['\u2019]t)\s+(?:allowed|permitted)|forbidden|prohibited|banned|off[- ]limits|(?:has|have)\s+to)\b"
                     r"|\bonly\b(?![ \t]*(?:[,.;:!?]|$))(?![ \t]+(?:a|an|one|two|three|just|about)\b)", re.I)
RULE_SKIP = {"cannot", "only", "require", "requires", "required", "forbidden", "prohibited", "banned", "allowed", "permitted", "limits", "have", "has"}


def unbacked_rules(text):
    """Sentences of `Facts:` that state a rule (must, cannot, only, requires, not allowed, forbidden ...) while no canon fact
    (or NPC canon note) shares more than half of their content words."""
    fm = FACTS_RE.search(text)
    if not fm:
        return []
    pool = [content_stems(f"{f.get('subject', '')} {f.get('fact', '')}") for f in S.get("canon")["facts"]]
    for src in (cast(), world_npcs()):
        for e in src.values():
            pool += [content_stems(n.get("note", "")) for n in (e.get("canon_notes") or []) if isinstance(n, dict)]
    out = []
    for sent in re.split(r"(?<=[.!?;])\s+|\n+", fm.group(1)):
        sent = sent.strip()
        want = content_stems(sent, RULE_SKIP) if RULE_RE.search(sent) else set()
        if want and max((len(want & have) / len(want) for have in pool), default=0) <= 0.5:
            out.append(sent)
    return out


TONE_REPEAT = 3
TONE_FILLER = {"the", "and", "but", "with", "then", "her", "his", "their", "its", "for", "not", "one", "two"}


def tone_words(s):
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", norm(s)) if len(w) > 2 and w not in TONE_FILLER}


def stale_tone(text):
    """The `Tone:` line when it is (nearly) the same as in each of the last 3 logged prompts: a fix is reviewed after 3 turns (TONE-1)."""
    cur = TONE_RE.search(text)
    cw = tone_words(cur.group(1)) if cur else set()
    last = sorted(S.get("turns"), key=lambda t: t.get("turn", 0))[-TONE_REPEAT:]
    if not cw or len(last) < TONE_REPEAT:
        return None
    for t in last:
        m = TONE_RE.search(t.get("prompt") or "")
        w = tone_words(m.group(1)) if m else set()
        if not w or len(cw & w) / len(cw | w) < 0.7:
            return None
    return " ".join(cur.group(1).split())


NEG_SKIP_RE = re.compile(r"\b(?:no|not|never|without|\w+n['\u2019]t|do\s+not|does\s+not|did\s+not)\s+(?:a\s+|any\s+)?(?:time\s+)?(?:skip\w*|jump\w*|later|cut\s+to)\b", re.I)
SKIP_WORD_RE = re.compile(r"\bskip(?:s|ped|ping)?\b", re.I)


def cut_skips(cut):
    """True when a `Cut:` line text actually skips (the word skip, skipped, skipping), not when it only negates one ("No skip.",
    "don't skip", "without skipping", "not skipping")."""
    return bool(SKIP_WORD_RE.search(NEG_SKIP_RE.sub(" ", cut or "")))
SKIP_RE = re.compile(r"\bskip(?:s|ped|ping)?\b|\b(?:next|following)\s+(?:morning|day|evening|afternoon|night|week|weekend|month)\b|\btomorrow\b"
                     r"|\b(?:hours?|days?|weeks?|months?|years?)\s+(?:later|on|pass)\b|\bthat\s+(?:night|evening|afternoon|morning|day)\b"
                     r"|(?<!second\s)(?<!seconds\s)(?<!moment\s)(?<!beat\s)(?<!breath\s)(?<!minute\s)(?<!instant\s)\blater\b"
                     r"|\btime\s+(?:passes|skip|jump)\b|\bfast[- ]forward|\bjump(?:s|ed)?\s+(?:ahead|to|forward)\b|\bcut\s+to\b|\bmove\s+(?:on\s+)?to\b", re.I)
TRAVEL_RE = re.compile(r"\b(?:go|goes|going|went|gone|walk\w*|head(?:s|ed|ing)?|leav(?:e|es|ing)|left|depart\w*|travel\w*|trip|driv(?:e|es|ing)|drove|"
                       r"rid(?:e|es|ing)|rode|run|runs|running|ran|rush\w*|hurr(?:y|ies|ied)|follow\w*|enter\w*|exit\w*|return\w*|come|comes|coming|"
                       r"came|wait\w*|until|till|tomorrow|tonight|sleep\w*|slept|bed|nap\w*|rest\w*|home|toward\w*|off\s+to|set\s+(?:off|out)|"
                       r"arriv\w*|visit\w*|meet\w*|escort\w*|mov(?:e|es|ed|ing)|skip\w*|later|morning|evening|afternoon|night|next\s+day|"
                       r"take\s+(?:me|us)|step(?:s|ped|ping)?|check(?:s|ed)?\s+(?:out|in)|stay\w*|eat\w*|dinner|lunch|to\s+the|"
                       r"breakfast|class|school|back\s+(?:to|at|in))\b", re.I)


def cut_move(seg):
    """What a `Cut:` line moves: a time skip (the phrase), or a new place (a known location that no player character is in), else None."""
    s = NEG_SKIP_RE.sub(" ", seg)
    m = SKIP_RE.search(s)
    if m:
        return f'"{m.group(0).strip()}"'
    here = {norm(pc.get("location") or "") for pc in S.get("state")["player_characters"]} - {""}
    named = [k for k in locations() if mentions(s, k)]
    named = [k for k in named if not any(k != o and norm(k) in norm(o) for o in named)]
    if here and named and not any(norm(k) in here for k in named):
        return f"new place {named[0]}"
    return None


def cut_warnings(text, inputs):
    """CUT-2, rough: the `Cut:` moves time or place and the player inputs show no travel, waiting or leaving. Skipped without inputs."""
    cm = CUT_RE.search(text)
    if not (inputs and inputs.strip() and cm) or TRAVEL_RE.search(inputs):
        return []
    move = cut_move(strip_quoted(cm.group(1)))
    return [f"`Cut:` moves time or place ({move}) but the inputs show no travel, waiting or leaving (CUT-2): "
            "stay in the moment, or move only as far as the input reaches"] if move else []


def sz_prompt_warnings(text):
    """Session zero's lines (never happen) and veils (offscreen only) whose content words all appear in the prompt (the sz_matches test)."""
    sz, have, out = arcs()["session_zero"], content_stems(text), []
    for kind, entries in (("line", sz.get("lines") or []), ("veil", sz.get("veils") or [])):
        for e in entries:
            want = content_stems(e, SZ_SKIP)
            if want and want <= have:
                out.append(f'session zero {kind} "{e}": all its content words are in the prompt; check it does not cross the {kind}')
    return out


_OTHER_NAMES = {}


def other_campaign_names():
    """{normalized name: [campaign, ...]}: the cast and world NPC names of every other campaign under campaigns/ (full names, aliases,
    and for individuals the title-less name, first and last name). Read-only; never touches the world files."""
    if _OTHER_NAMES:
        return _OTHER_NAMES
    for c in list_campaigns():
        if c == CAMPAIGN:
            continue
        base = ROOT / "campaigns" / c
        try:
            cfg = json.loads((base / "campaign.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        skip = {norm(t) for t in cfg.get("name_skip_tokens") or []} | STOP
        for fname in ("cast", "world-npcs"):
            try:
                data = json.loads((base / "data" / f"{fname}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for key, e in (data.items() if isinstance(data, dict) else []):
                e = e if isinstance(e, dict) else {}
                forms = {norm(key)} | {norm(x) for x in npc_aliases(e)}
                if is_individual(e):
                    toks = key.split()
                    core = [t for t in toks if norm(t) not in skip]
                    if core:
                        forms |= {norm(core[0]), norm(core[-1])}
                        if 2 <= len(core) < len(toks):
                            forms.add(norm(" ".join(core)))
                for f in forms:
                    if len(f) >= 3 and f not in STOP and c not in _OTHER_NAMES.setdefault(f, []):
                        _OTHER_NAMES[f].append(c)
    return _OTHER_NAMES


def cross_campaign_warnings(names):
    """Handoff 4.2: a name unknown to this campaign (find_names: unknown, or a lone unknown sentence opener) that is a cast or world NPC
    in another campaign: probably the wrong campaign. A name known here never gets here."""
    cand = {norm(ph): ph for ph, cat in names if cat is None or cat == "sentence-initial"}
    if not cand:
        return []
    other, by = other_campaign_names(), {}
    for n, ph in cand.items():
        for c in other.get(n, []):
            by.setdefault(c, []).append(ph)
    return [f'not a name in {CAMPAIGN} but a cast/world NPC in {c}: {", ".join(v)}; wrong campaign? (check the name and the campaign)'
            for c, v in sorted(by.items())]


# D22 (AGY-3, FMT-10): a contested social ask (recruiting, persuading, bargaining, intimidating) is an attempt Voyage rolls. WARN only.
ASK_RE = re.compile(r"\b(?:join(?:s|ed|ing)?|recruit\w*|persuad\w*|convinc\w*|bargain\w*|haggl\w*|brib\w*|intimidat\w*|threaten\w*|negotiat\w*|"
                    r"party\s+up|(?:in|into|to)\s+(?:my|our)\s+party)\b", re.I)
ACCEPT_RE = re.compile(r"\b(?:yes|agrees|accepts|joins|consents|(?:will|would|shall)\s+(?:agree|accept|join|consent)|"
                       r"(?:answer|reply|response)\s+is\s+(?:a\s+)?yes)\b", re.I)
COND_CLAUSE_RE = re.compile(r"\b(?:if|unless|should)\b", re.I)


def contested_ask_warnings(text, inputs):
    """D22: the players' inputs make a contested social ask and the prompt states an NPC's acceptance outside a conditional clause
    (if, unless or should earlier in the same sentence or clause). Quoted lines count: the NPC's words are the prompt's too."""
    ask = ASK_RE.search(inputs or "")
    if not ask:
        return []
    flat = re.sub(r'"[^"\n]*"|\u201c[^\u201d\n]*\u201d', lambda m: re.sub(r"[.!?]", ",", m.group(0)), text)  # a quote is part of its sentence
    for sent in re.split(r"(?<=[.!?;])\s+|;|\n+", flat):
        acc = ACCEPT_RE.search(sent)
        if acc and not COND_CLAUSE_RE.search(sent[:acc.start()]):
            return [f'the input makes a contested ask ("{ask.group(0).strip()}") and the prompt states the NPC\'s acceptance ("{acc.group(0).strip()}"): '
                    "the ask is an attempt Voyage rolls, so write the NPC's answer as conditional on the roll (AGY-3, FMT-10)"]
    return []


def agency_warnings(text, names, known, inputs=None):
    """The WARN-only agency checks of check-prompt and commit-turn (FMT-7, TONE-1, CUT-2, session zero, cross-campaign names)."""
    out = place_warnings(text, known)
    out += [f'`Facts:` states a rule that no canon fact backs ("{short(s, 70)}"): record it with `fact` first, or drop it (FMT-7)' for s in unbacked_rules(text)]
    tone = stale_tone(text)
    if tone:
        tone = short(tone, 50).rstrip(".")
        out.append(f'`Tone:` is the same as in the last {TONE_REPEAT} prompts ("{tone}"): a fix is for {TONE_REPEAT} turns; review or change it (TONE-1)')
    return out + cut_warnings(text, inputs) + contested_ask_warnings(text, inputs) + sz_prompt_warnings(text) + cross_campaign_warnings(names)


NPC_CATS = ("in-play NPC", "world NPC", "planned NPC", "world npc", "player character")


def run_check(text, allow=(), verbose=True, inputs=None):
    """The check-prompt analysis. Prints its report (verbose=False: only Length, FAIL, WARN and unknown-name lines)
    and returns (failed, unknown, warnings). `inputs` (the players' inputs, optional) enables the `Cut:` skip check."""
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
    # the Facts: line is not used in Campfire mode (no steering prompt); this warning only serves prompt mode
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
    warnings += agency_warnings(text, names, known, inputs)
    for w_ in warnings:
        print(f"WARN: {w_}")
    if unknown:
        print(f"\nFLAGGED {len(unknown)} unknown name(s): {', '.join(unknown)}")
        print("  Fix the name, or (if it is a real new NPC from the story output) record it with add-npc first.")
    if not failed and not unknown and not warnings and verbose:
        print("\nOK: length within limit, all names known, no warnings.")
    return failed, unknown, warnings


def cmd_check_prompt(a):
    if campfire_room():
        print("NOTE: Campfire mode (campaign.json campfire_room): check-prompt and the prompt limit are skipped; commit-turn --scene runs "
              "the hidden-words check on the scene and the stakes lines (director/playbooks/campfire.md).")
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8") \
        if Path(a.file).exists() else die(f"no such file: {a.file}")
    inputs = []
    if a.paste:
        if not Path(a.paste).is_file():
            die(f"no such paste file: {a.paste}")
        inputs.append(Path(a.paste).read_text(encoding="utf-8"))
    if a.inputs:
        inputs.append(a.inputs)
    clock_note("checked")  # SES-9: when the check first ran for the coming turn (no network, nothing in a trial run)
    failed, unknown, _warnings = run_check(text.rstrip("\n"), (a.allow or "").split(","), inputs="\n".join(inputs) or None)
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
# arc planner (data/arcs.json, optional): session zero, act pitches, arc charters, pressure in play
# ----------------------------------------------------------------------------
ARC_STATUSES = ("draft", "approved", "active", "provisional", "parked", "closed", "set_aside")
ACT_STATUSES = ("draft", "approved", "closed")
ARC_DONE = ("closed", "set_aside")
ARC_LIVE = ("active", "provisional")  # one live arc at a time; a provisional arc is the pivot arc, live but not yet approved
PIVOT_TURNS = 3                       # logged turns on a new thread with no arc contact that signal a pivot (PIV-2)
PIVOT_BUDGET = (10, 15)               # turns a pivot arc may budget (PIV-4, PIV-5)
OFFRAMP_KEYS = ("thread", "promise", "front", "face", "first_move")
ACT_REQUIRED = ("title", "theme", "question", "builds_to", "stakes_scale", "ending_shape")
ARC_REQUIRED = ("title", "tone", "promise", "premise", "pressure", "climax_kind", "ending_shape")
PLAN_EVIDENCE = "planning session with the user"
DEFAULT_ARC_BUDGET = 30
DRIFT_TURNS = 8
SZ_TEXT, SZ_LISTS = ("tone", "pacing", "ending_hope", "notes"), ("lines", "veils")
SHARED_TEXT = ("title", "tone", "promise", "premise", "pressure", "subplot", "climax_kind", "ending_shape", "stakes")
SHARED_LISTS = ("set_pieces", "seeds", "wins_on_offer", "echoes", "backstory_hooks")
HIDDEN_LISTS = ("surprises", "climax_options", "cast", "new_npcs")


def arcs():
    """data/arcs.json (the skeleton when the file does not exist yet), with every top-level key present."""
    d = S.get("arcs")
    for k, v in arcs_skeleton().items():
        d.setdefault(k, v)
    return d


def offramp_problems(v):
    """Shape problems of a list of off-ramp sketches: a list of objects with exactly OFFRAMP_KEYS, each a non-empty string."""
    if not isinstance(v, list):
        return ["off-ramps must be a list of sketches (objects with the keys " + ", ".join(OFFRAMP_KEYS) + ")"]
    bad = []
    for i, x in enumerate(v, 1):
        if not isinstance(x, dict):
            bad.append(f"sketch {i} must be an object with the keys {', '.join(OFFRAMP_KEYS)}")
            continue
        missing = [k for k in OFFRAMP_KEYS if k not in x]
        extra = [k for k in x if k not in OFFRAMP_KEYS]
        if missing:
            bad.append(f"sketch {i} lacks {', '.join(missing)}")
        if extra:
            bad.append(f"sketch {i} has unknown key(s) {', '.join(map(str, extra))} (allowed: {', '.join(OFFRAMP_KEYS)})")
        bad += [f"sketch {i}: {k} must be a non-empty string" for k in OFFRAMP_KEYS if k in x and not (isinstance(x[k], str) and x[k].strip())]
    return bad


def arcs_problems(d):
    """Shape problems of data/arcs.json: statuses, unique ids and act numbers, at most one live (active or provisional) arc,
    the turns a provisional or parked arc must carry, and the shape of any off-ramps."""
    if not isinstance(d, dict):
        return ["arcs.json must be an object"]
    bad = []
    for k, typ in (("session_zero", dict), ("pc_threads", list), ("acts", list), ("arcs", list)):
        if k in d and not isinstance(d[k], typ):
            bad.append(f"arcs.json: {k} must be a {'list' if typ is list else 'object'}")
    acts = d.get("acts") if isinstance(d.get("acts"), list) else []
    seen = set()
    for x in acts:
        if not isinstance(x, dict) or not isinstance(x.get("n"), int):
            bad.append("arcs.json: every act needs an integer n")
        elif x["n"] in seen:
            bad.append(f"arcs.json: act {x['n']} appears twice")
        elif x.get("status") not in ACT_STATUSES:
            bad.append(f"arcs.json: act {x['n']} status must be one of {', '.join(ACT_STATUSES)}")
        if isinstance(x, dict):
            seen.add(x.get("n"))
    rows = d.get("arcs") if isinstance(d.get("arcs"), list) else []
    ids = set()
    for x in rows:
        if not isinstance(x, dict) or not isinstance(x.get("id"), str) or not x["id"]:
            bad.append("arcs.json: every arc needs an id")
            continue
        if x["id"] in ids:
            bad.append(f"arcs.json: arc id {x['id']} appears twice")
        ids.add(x["id"])
        if x.get("status") not in ARC_STATUSES:
            bad.append(f"arcs.json: arc {x['id']} status must be one of {', '.join(ARC_STATUSES)}")
        if x.get("status") == "provisional":
            for k in ("start_turn", "adopted_turn"):
                if not _is_turn(x.get(k)):
                    bad.append(f"arcs.json: provisional arc {x['id']} needs an integer {k} (set by arc-adopt)")
        if x.get("status") == "parked" and not _is_turn(x.get("parked_turn")):
            bad.append(f"arcs.json: parked arc {x['id']} needs an integer parked_turn (set by arc-adopt)")
        hd = x.get("hidden")
        if isinstance(hd, dict) and "offramps" in hd:
            bad += [f"arcs.json: arc {x['id']} hidden.offramps: {m}" for m in offramp_problems(hd["offramps"])]
    live = [x for x in rows if isinstance(x, dict) and x.get("status") in ARC_LIVE]
    if len(live) > 1:
        word = "active" if all(x["status"] == "active" for x in live) else "live (active or provisional)"
        bad.append(f"arcs.json: more than one {word} arc ({', '.join(x['id'] for x in live)})")
    return bad


def _is_turn(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def arc_num(a):
    m = re.search(r"\d+", str(a.get("id")))
    return int(m.group()) if m else 0


def find_arc(ident):
    key = norm(ident)
    key = f"a{key}" if key.isdigit() else key
    rows = arcs()["arcs"]
    for a in rows:
        if norm(a["id"]) == key:
            return a
    die(f'no arc "{ident}" (arcs: {", ".join(a["id"] for a in rows) or "none yet: arc-plan --file F.json"})', 2)


def find_act(n):
    return next((x for x in arcs()["acts"] if x.get("n") == n), None)


def live_arc():
    """The live arc (active, or provisional after a pivot); None when there is none. Only one is live at a time."""
    return next((a for a in arcs()["arcs"] if a.get("status") in ARC_LIVE), None)


def parked_arcs():
    return sorted((a for a in arcs()["arcs"] if a.get("status") == "parked"), key=arc_num)


def current_arc():
    """The live arc (active or provisional), else the newest draft or approved one (None when there is none)."""
    live = live_arc()
    if live:
        return live
    waiting = sorted((a for a in arcs()["arcs"] if a.get("status") in ("draft", "approved")), key=arc_num)
    return waiting[-1] if waiting else None


def arc_title(a):
    return (a.get("shared") or {}).get("title") or "untitled"


def arc_budget(a):
    v = a.get("budget_turns")
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else DEFAULT_ARC_BUDGET


def arc_used(a, turn):
    s = a.get("start_turn")
    return max(0, turn - s) if isinstance(s, int) else 0


def arc_at(a, turn, pct):
    """True when the arc has used at least pct percent of its budget at this turn."""
    return arc_used(a, turn) * 100 >= pct * arc_budget(a)


def arc_progress(a, turn):
    used, bud = arc_used(a, turn), arc_budget(a)
    return f"t{used}/{bud} ({used * 100 // bud}%)"


def arc_line(a, turn):
    sh = a.get("shared") or {}
    bits = [f'{a["id"]} [{a.get("status")}] act {a.get("act")}: "{short(arc_title(a), 50)}"']
    if a.get("status") in ARC_LIVE:
        bits.append(arc_progress(a, turn))
    elif a.get("status") == "parked":
        bits.append(f"parked since turn {a.get('parked_turn')}")
    elif a.get("status") in ARC_DONE and isinstance(a.get("retro"), dict):
        bits.append(f"{a['retro'].get('turns_used')}/{a['retro'].get('budget')} turns")
    if a.get("blind"):
        bits.append("blind")
    if sh.get("promise"):
        bits.append("promise: " + short(sh["promise"], 70))
    return " | ".join(bits)


def plan_meta(a):
    """--turn / --evidence are optional on the planning commands (default: the current turn, 'planning session with the user')."""
    if a.turn is not None:
        check_turn(a.turn)
    turn = a.turn if a.turn is not None else get_state_turn()
    return turn, (a.evidence or "").strip() or PLAN_EVIDENCE


def load_json_file(path, what):
    p = Path(path)
    if not p.is_file():
        die(f"no such file: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"{what}: {path} is not valid JSON: {e}", 2)


def clean(v):
    """The value with every string stripped."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    return v


def split_list(v):
    return [x.strip() for x in re.split(r";", v) if x.strip()] if isinstance(v, str) else v


def nonempty(v):
    return [x for x in v if (str(x.get("text") if isinstance(x, dict) else x) or "").strip()] if isinstance(v, list) else []


def charter_shape_errors(shared, hidden):
    """Type problems of a charter's shared/hidden objects (everything else is checked at approval)."""
    bad = []
    for what, v in (("shared", shared), ("hidden", hidden)):
        if v is not None and not isinstance(v, dict):
            bad.append(f"{what} must be an object")
    sh, hd = shared if isinstance(shared, dict) else {}, hidden if isinstance(hidden, dict) else {}
    for k in SHARED_TEXT:
        if k in sh and not isinstance(sh[k], str):
            bad.append(f"shared.{k} must be a string")
    for k in SHARED_LISTS:
        if k in sh and not isinstance(sh[k], list):
            bad.append(f"shared.{k} must be a list")
    if "pc_tests" in sh and not isinstance(sh["pc_tests"], dict):
        bad.append('shared.pc_tests must be an object {"<PC name>": "category"}')
    if "deviations" in sh and not isinstance(sh["deviations"], list):
        bad.append("shared.deviations must be a list")
    for k in HIDDEN_LISTS:
        if k in hd and not isinstance(hd[k], list):
            bad.append(f"hidden.{k} must be a list")
    if "twist" in hd and not isinstance(hd["twist"], (dict, str)):
        bad.append("hidden.twist must be an object (or a string)")
    if "antagonist" in hd and not isinstance(hd["antagonist"], dict):
        bad.append("hidden.antagonist must be an object")
    if "checklist" in hd and not (isinstance(hd["checklist"], list) and all(isinstance(x, str) for x in hd["checklist"])):
        bad.append("hidden.checklist must be a list of strings")
    if "refine" in hd and not (isinstance(hd["refine"], list) and all(isinstance(x, str) for x in hd["refine"])):
        bad.append("hidden.refine must be a list of strings")
    if "pending_ops" in hd and not (isinstance(hd["pending_ops"], list)
                                    and all(isinstance(x, dict) and isinstance(x.get("op"), str) for x in hd["pending_ops"])):
        bad.append('hidden.pending_ops must be a list of payload ops ({"op": ..., "args": {...}, "evidence": ...})')
    if "pc_test_situations" in hd and not isinstance(hd["pc_test_situations"], dict):
        bad.append("hidden.pc_test_situations must be an object")
    if "notes" in hd and not isinstance(hd["notes"], str):
        bad.append("hidden.notes must be a string")
    if "offramps" in hd:
        bad += [f"hidden.offramps: {m}" for m in offramp_problems(hd["offramps"])]
    for k in ("fronts", "clues"):
        if k in hd and not isinstance(hd[k], list):
            bad.append(f"hidden.{k} must be a list")
    if isinstance(hd.get("fronts"), list):
        for i, f in enumerate(hd["fronts"], 1):
            if not isinstance(f, dict):
                bad.append(f"hidden.fronts[{i}] must be an object {{name, goal, moves}}")
            elif "moves" in f and not isinstance(f["moves"], list):
                bad.append(f"hidden.fronts[{i}].moves must be a list")
    return bad


def norm_shared(sh, turn):
    sh = clean(sh)
    for k in SHARED_TEXT:
        sh.setdefault(k, "")
    for k in SHARED_LISTS + ("deviations",):
        sh.setdefault(k, [])
    sh.setdefault("pc_tests", {})
    sh["deviations"] = [x if isinstance(x, dict) else {"turn": turn, "text": str(x)} for x in sh["deviations"]]
    return sh


def norm_hidden(h):
    """Fill the hidden charter's defaults: twist, fronts (moves with done_turn), antagonist, clues (found_turn)."""
    h = clean(h)
    tw = h.get("twist")
    tw = {"text": tw} if isinstance(tw, str) else dict(tw or {})
    tw.setdefault("text", "")
    tw["ladder"] = tw.get("ladder") or None
    tw["keywords"] = [x for x in (split_list(tw.get("keywords")) or []) if str(x).strip()]
    tw.setdefault("revealed_turn", None)
    h["twist"] = tw
    fronts = []
    for f in h.get("fronts") or []:
        f = dict(f)
        f.setdefault("name", "")
        f.setdefault("goal", "")
        f["moves"] = [dict(m) if isinstance(m, dict) else {"text": m} for m in f.get("moves") or []]
        for m in f["moves"]:
            m.setdefault("text", "")
            m.setdefault("done_turn", None)
        fronts.append(f)
    h["fronts"] = fronts
    an = dict(h.get("antagonist") or {})
    for k in ("name", "face", "first_contact"):
        an.setdefault(k, "")
    an.setdefault("contact_turn", None)
    h["antagonist"] = an
    clues = [dict(c) if isinstance(c, dict) else {"text": c} for c in h.get("clues") or []]
    for c in clues:
        c.setdefault("text", "")
        c.setdefault("found_turn", None)
    h["clues"] = clues
    for k in HIDDEN_LISTS:
        h.setdefault(k, [])
    h.setdefault("pc_test_situations", {})
    h.setdefault("notes", "")
    return h


def carry_progress(old, new):
    """An updated charter keeps what already happened: revealed twist, antagonist contact, found clues, done moves."""
    for sect, key in (("twist", "revealed_turn"), ("antagonist", "contact_turn")):
        if new[sect].get(key) is None and (old.get(sect) or {}).get(key) is not None:
            new[sect][key] = old[sect][key]
    found = {norm(c.get("text")): c.get("found_turn") for c in old.get("clues") or [] if c.get("found_turn") is not None}
    for c in new["clues"]:
        if c.get("found_turn") is None:
            c["found_turn"] = found.get(norm(c.get("text")))
    done = {(norm(f.get("name")), norm(m.get("text"))): m.get("done_turn")
            for f in old.get("fronts") or [] for m in f.get("moves") or [] if m.get("done_turn") is not None}
    for f in new["fronts"]:
        for m in f["moves"]:
            if m.get("done_turn") is None:
                m["done_turn"] = done.get((norm(f.get("name")), norm(m.get("text"))))
    return new


def _unknown_keys(f, allowed, what, path):
    if not isinstance(f, dict):
        die(f"{what}: {path} must hold a JSON object with the keys {', '.join(allowed)}", 2)
    bad = [k for k in f if k not in allowed]
    if bad:
        die(f"{what}: unknown key(s) in {path}: {', '.join(bad)} (allowed: {', '.join(allowed)})", 2)


def acts_known(n):
    if n not in ACT_STARTS:
        die(f"act {n} is not in campaign.json acts (acts: {', '.join(map(str, sorted(ACT_STARTS)))})", 2)


# ---- session zero ------------------------------------------------------------
def parse_pillars(v):
    out = {}
    for part in [x.strip() for x in v.split(",") if x.strip()]:
        k, _, n = part.partition("=")
        if not k.strip() or not re.fullmatch(r"\s*[0-3]\s*", n):
            die(f'--pillars: "{part}" must look like combat=3 (0 to 3)', 2)
        out[k.strip().lower()] = int(n)
    return out


def print_session_zero(sz):
    empty = not (any(sz.get(k) for k in SZ_TEXT + SZ_LISTS) or sz.get("pillars"))
    if empty:
        print("Session zero: not recorded: fill it this session (session-zero --tone ... --lines ... --veils ... --pillars ...)")
        return
    print(f"Session zero (updated turn {sz.get('updated_turn')}):")
    wrap("tone", sz.get("tone"))
    if sz.get("players"):
        wrap("players (PCs at the table)", str(sz["players"]))
    wrap("lines (never happens)", "; ".join(sz.get("lines") or []))
    wrap("veils (offscreen only)", "; ".join(sz.get("veils") or []))
    wrap("play styles (0 to 3)", ", ".join(f"{k} {v}" for k, v in (sz.get("pillars") or {}).items()))
    wrap("pacing", sz.get("pacing"))
    wrap("ending hope", sz.get("ending_hope"))
    wrap("notes", sz.get("notes"))


def cmd_session_zero(a):
    given = {"file": a.file, "players": a.players, **{k: getattr(a, k) for k in SZ_TEXT + SZ_LISTS + ("pillars",)}}
    sz = arcs()["session_zero"]
    if all(v is None for v in given.values()):
        print_session_zero(sz)
        return
    turn, ev = plan_meta(a)
    upd = {}
    if a.file:
        f = load_json_file(a.file, "session-zero")
        _unknown_keys(f, SZ_TEXT + SZ_LISTS + ("pillars", "players"), "session-zero", a.file)
        upd.update(clean(f))
    for k in SZ_TEXT:
        if getattr(a, k) is not None:
            upd[k] = getattr(a, k).strip()
    for k in SZ_LISTS:
        if getattr(a, k) is not None:
            upd[k] = split_list(getattr(a, k))
    if a.pillars is not None:
        upd["pillars"] = parse_pillars(a.pillars)
    if a.players is not None:
        upd["players"] = a.players
    bad = [f"{k} must be a string" for k in SZ_TEXT if k in upd and not isinstance(upd[k], str)]
    bad += [f"{k} must be a list of strings" for k in SZ_LISTS if k in upd and not (isinstance(upd[k], list) and all(isinstance(x, str) for x in upd[k]))]
    if "pillars" in upd and not (isinstance(upd["pillars"], dict) and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 3 for v in upd["pillars"].values())):
        bad.append("pillars must be an object of integers 0 to 3")
    if "players" in upd and not (isinstance(upd["players"], int) and not isinstance(upd["players"], bool) and 1 <= upd["players"] <= 8):
        bad.append("players must be an integer 1 to 8")
    if bad:
        die("session-zero: " + "; ".join(bad), 2)
    pill = upd.pop("pillars", None)
    sz.update({k: v for k, v in upd.items()})
    if pill is not None:
        sz.setdefault("pillars", {}).update(pill)
    sz["updated_turn"] = turn
    S.touch("arcs")
    S.commit("session-zero", turn, ev, "session zero updated (" + ", ".join(list(upd) + (["pillars"] if pill is not None else [])) + ")")


# ---- act pitches -------------------------------------------------------------
def cmd_act_plan(a):
    turn, ev = plan_meta(a)
    acts_known(a.n)
    f = load_json_file(a.file, "act-plan")
    _unknown_keys(f, ("shared", "hidden"), "act-plan", a.file)
    bad = charter_shape_errors(f.get("shared"), f.get("hidden"))
    if bad:
        die("act-plan: " + "; ".join(bad), 2)
    act = find_act(a.n)
    if act and act["status"] == "closed":
        die(f"act {a.n} is closed: its pitch cannot be replaced", EXIT_REFUSED)
    sh, hd = clean(f.get("shared") or {}), clean(f.get("hidden") or {})
    for k in ACT_REQUIRED:
        sh.setdefault(k, "")
    hd.setdefault("turning_point", "")
    hd.setdefault("notes", "")
    if act is None:
        act = {"n": a.n, "status": "draft", "shared": sh, "hidden": hd, "deviations": [], "approved_turn": None,
               "closed_turn": None, "retro": None}
        arcs()["acts"].append(act)
        arcs()["acts"].sort(key=lambda x: x["n"])
        msg = f'act {a.n} pitch drafted: "{short(sh.get("title"), 50)}"'
    else:
        act["shared"], act["hidden"] = sh, hd
        msg = f'act {a.n} pitch replaced: "{short(sh.get("title"), 50)}"' + (" (stays approved)" if act["status"] == "approved" else "")
    S.touch("arcs")
    S.commit("act-plan", turn, ev, msg)


def cmd_act_approve(a):
    turn, ev = plan_meta(a)
    act = find_act(a.n)
    if not act:
        die(f"no pitch for act {a.n} yet (act-plan {a.n} --file F.json)", 2)
    if act["status"] == "closed":
        die(f"act {a.n} is closed", EXIT_REFUSED)
    if act["status"] == "approved":
        print(f"act {a.n} pitch is already approved (turn {act.get('approved_turn')}); nothing changed.")
        return
    sh = act.get("shared") or {}
    bad = [f"shared.{k} is empty" for k in ACT_REQUIRED if not str(sh.get(k) or "").strip()]
    if bad and not a.force:
        die(f"act {a.n} pitch cannot be approved:\n  - " + "\n  - ".join(bad) + "\nFix it with act-plan, or --force to approve anyway (recorded).", EXIT_REFUSED)
    if bad:
        print("warning: --force overrides: " + "; ".join(bad))
        act["approved_forced"] = bad
    act["status"], act["approved_turn"] = "approved", turn
    S.touch("arcs")
    S.commit("act-approve", turn, ev, f'act {a.n} pitch approved: "{short(sh.get("title"), 50)}"' + (" (FORCED)" if bad else ""))


def cmd_act_deviation(a):
    need_ev(a)
    act = find_act(a.n)
    if not act:
        die(f"no pitch for act {a.n} yet (act-plan {a.n} --file F.json)", 2)
    text = " ".join(a.text).strip()
    act.setdefault("deviations", []).append({"turn": a.turn, "text": text})
    S.touch("arcs")
    S.commit("act-deviation", a.turn, a.evidence, f"act {a.n} deviates from the bible: {short(text, 90)}")


def cmd_act_close(a):
    turn, ev = plan_meta(a)
    act = find_act(a.n)
    if not act:
        die(f"no pitch for act {a.n} (act-plan {a.n} --file F.json)", 2)
    if act["status"] == "closed":
        die(f"act {a.n} is already closed", EXIT_REFUSED)
    retro = (read_arg_text(a.retro) or "").strip()
    if not retro:
        die("--retro must not be empty")
    act["status"], act["closed_turn"], act["retro"] = "closed", turn, retro
    S.touch("arcs")
    S.commit("act-close", turn, ev, f"act {a.n} closed; retro: {short(retro, 80)}")


# ---- arc charters ------------------------------------------------------------
def cmd_arc_plan(a):
    turn, ev = plan_meta(a)
    f = load_json_file(a.file, "arc-plan")
    _unknown_keys(f, ("act", "budget_turns", "blind", "shared", "hidden"), "arc-plan", a.file)
    bad = charter_shape_errors(f.get("shared"), f.get("hidden"))
    if "budget_turns" in f and not (isinstance(f["budget_turns"], int) and not isinstance(f["budget_turns"], bool) and f["budget_turns"] > 0):
        bad.append("budget_turns must be a whole number above 0")
    if "blind" in f and not isinstance(f["blind"], bool):
        bad.append("blind must be true or false")
    if "act" in f and not (isinstance(f["act"], int) and not isinstance(f["act"], bool)):
        bad.append("act must be an act number")
    if bad:
        die("arc-plan: " + "; ".join(bad), 2)
    if "act" in f:
        acts_known(f["act"])
    d = arcs()
    if a.id:
        arc = find_arc(a.id)
        if arc["status"] in ARC_DONE:
            die(f"arc {arc['id']} is {arc['status']}: it cannot be edited (plan a new arc)", EXIT_REFUSED)
        old_h = arc.get("hidden") or {}
        if "shared" in f:
            sh = norm_shared({**(arc.get("shared") or {}), **clean(f["shared"])}, turn)
            if "deviations" in f["shared"]:  # keep what is already logged, add the new entries
                have = {norm(x.get("text")) for x in (arc["shared"].get("deviations") or [])}
                sh["deviations"] = list(arc["shared"].get("deviations") or []) + [x for x in sh["deviations"] if norm(x.get("text")) not in have]
            else:
                sh["deviations"] = list((arc.get("shared") or {}).get("deviations") or [])
            arc["shared"] = sh
        if "hidden" in f:
            arc["hidden"] = carry_progress(old_h, norm_hidden({**old_h, **clean(f["hidden"])}))
        for k in ("act", "budget_turns", "blind"):
            if k in f:
                arc[k] = f[k]
        msg = f'arc {arc["id"]} updated: "{short(arc_title(arc), 50)}"' + (f" (stays {arc['status']})" if arc["status"] in ("approved", "active", "provisional", "parked") else "")
    else:
        n = 1 + max([arc_num(x) for x in d["arcs"]] + [0])
        act_n = f.get("act", current_act(S.get("state")))
        acts_known(act_n)
        arc = {"id": f"A{n}", "act": act_n, "status": "draft", "blind": bool(f.get("blind", False)),
               "budget_turns": f.get("budget_turns", DEFAULT_ARC_BUDGET), "start_turn": None, "approved_turn": None,
               "closed_turn": None, "shared": norm_shared(f.get("shared") or {}, turn), "hidden": norm_hidden(f.get("hidden") or {}),
               "reviews": [], "retro": None}
        d["arcs"].append(arc)
        msg = f'arc {arc["id"]} drafted: "{short(arc_title(arc), 50)}" (act {act_n}, budget {arc["budget_turns"]} turns{", blind" if arc["blind"] else ""})'
    S.touch("arcs")
    S.commit("arc-plan", turn, ev, msg)


def pc_has_test(tests, name):
    toks = norm(name).split()
    return any(str(v).strip() and (norm(k) == norm(name) or norm(k) in toks) for k, v in tests.items())


def previous_arc(arc):
    prev = [x for x in arcs()["arcs"] if arc_num(x) < arc_num(arc) and x.get("status") in ("approved", "active", "provisional", "parked", "closed")]
    return max(prev, key=arc_num) if prev else None


def strings_in(v):
    """Every string inside a value (a string, or a list/dict of them, at any depth)."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [s for x in v for s in strings_in(x)]
    if isinstance(v, dict):
        return [s for x in v.values() for s in strings_in(x)]
    return []


def arc_approval_problems(arc, pivot=False):
    """Every reason an arc charter cannot be approved yet (empty list = ready). pivot: a provisional arc, which has no twist
    (PIV-5), so the twist checks are skipped; every other check applies."""
    sh, hd = arc.get("shared") or {}, arc.get("hidden") or {}
    bad = []
    refine = [str(x).strip() for x in hd.get("refine") or [] if str(x).strip()] if isinstance(hd.get("refine"), list) else []
    if refine:
        bad.append(f'hidden.refine has {len(refine)} open item(s): ' + "; ".join(refine))
    bad += [f"shared.{k} still holds a PENDING placeholder" for k, v in sh.items() if any("PENDING" in s for s in strings_in(v))]
    players = arcs()["session_zero"].get("players")
    recorded = len(S.get("state")["player_characters"])
    if players and recorded < players:
        bad.append(f"only {recorded} of {players} PC sheets recorded: pc_tests cannot be checked yet (pc-add)")
    bad += [f"shared.{k} is empty" for k in ARC_REQUIRED if not str(sh.get(k) or "").strip()]
    if sh.get("stakes") not in ("personal", "wide"):
        bad.append("shared.stakes must be personal or wide")
    for k, what in (("set_pieces", "set-piece kind"), ("wins_on_offer", "win on offer"), ("backstory_hooks", "backstory hook")):
        if not nonempty(sh.get(k)):
            bad.append(f"shared.{k} needs at least one {what}")
    tests = sh.get("pc_tests") if isinstance(sh.get("pc_tests"), dict) else {}
    for pc in S.get("state")["player_characters"]:
        if not pc_has_test(tests, pc["name"]):
            bad.append(f'shared.pc_tests has no test for player character "{pc["name"]}"')
    tw = hd.get("twist") or {}
    has_twist = bool(str(tw.get("text") or "").strip() or tw.get("ladder") or nonempty(tw.get("keywords")))
    if has_twist or not pivot:  # a pivot arc has no twist (PIV-5): nothing to check; one that gained a twist is checked like any
        if not str(tw.get("text") or "").strip():
            bad.append("hidden.twist.text is empty")
        ladder = tw.get("ladder")
        if ladder and norm(ladder) not in {norm(k) for k in S.get("threads")}:
            bad.append(f'hidden.twist.ladder "{ladder}" is not a key of threads.json (keys: {", ".join(S.get("threads"))})')
        elif not ladder and not nonempty(tw.get("keywords")):
            bad.append("hidden.twist needs a ladder (a threads.json key) or its own keywords")
    fronts = hd.get("fronts") or []
    if not fronts:
        bad.append("hidden.fronts needs at least one front")
    for i, fr in enumerate(fronts, 1):
        who = f'front {i} "{fr.get("name") or "?"}"'
        if not str(fr.get("name") or "").strip():
            bad.append(f"front {i} has no name")
        if not str(fr.get("goal") or "").strip():
            bad.append(f"{who} has no goal")
        moves = nonempty(fr.get("moves"))
        if not 2 <= len(moves) <= 4 or len(moves) != len(fr.get("moves") or []):
            bad.append(f"{who} needs 2 to 4 escalating moves with text (has {len(fr.get('moves') or [])})")
    if not str((hd.get("antagonist") or {}).get("first_contact") or "").strip():
        bad.append("hidden.antagonist.first_contact is empty (the face must reach the PC on screen by the midpoint)")
    if len(nonempty(hd.get("clues"))) < 3:
        bad.append(f"hidden.clues needs at least 3 (three-clue rule; has {len(nonempty(hd.get('clues')))})")
    if len(hd.get("new_npcs") or []) > 3:
        bad.append(f"hidden.new_npcs has {len(hd['new_npcs'])}: at most 3")
    prev = previous_arc(arc)
    if prev:
        used = {norm(x) for x in (prev.get("shared") or {}).get("set_pieces") or []}
        same = [x for x in sh.get("set_pieces") or [] if norm(x) in used]
        if same:
            bad.append(f"set pieces repeat arc {prev['id']}'s: {', '.join(same)} (vary the kinds)")
    return bad


def cmd_arc_approve(a):
    turn, ev = plan_meta(a)
    arc = find_arc(a.id)
    if arc["status"] in ARC_DONE:
        die(f"arc {arc['id']} is {arc['status']}", EXIT_REFUSED)
    if arc["status"] in ("approved", "active"):
        print(f"arc {arc['id']} is already {arc['status']} (approved turn {arc.get('approved_turn')}); nothing changed.")
        return
    if arc["status"] == "parked":
        die(f"arc {arc['id']} is parked: arc-unpark {arc['id']} --notes ... brings it back (it was approved before it was parked)", EXIT_REFUSED)
    pivot = arc["status"] == "provisional"  # approving a pivot arc makes it active at once: it is already live, so no arc-start (D16)
    bad = arc_approval_problems(arc, pivot=pivot)
    sz = arcs()["session_zero"]
    lines, veils = sz.get("lines") or [], sz.get("veils") or []
    if (lines or veils) and not a.lines_checked:
        bad.append("session zero has lines/veils: check the charter against them, then pass --lines-checked")
        print("Check the charter against session zero:")
        for x in lines:
            print(f"  [ ] line (never happens): {x}")
        for x in veils:
            print(f"  [ ] veil (offscreen only): {x}")
    if bad and not a.force:
        die(f"arc {arc['id']} cannot be approved:\n  - " + "\n  - ".join(bad) + "\nFix it with arc-plan --id " + arc["id"]
            + ", or --force to approve anyway (recorded).", EXIT_REFUSED)
    if bad:
        print("warning: --force overrides: " + "; ".join(bad))
        arc["approved_forced"] = bad
    act = find_act(arc.get("act"))
    if not act or act["status"] not in ("approved", "closed"):
        print(f"warning: act {arc.get('act')} has no approved pitch (act-plan, act-approve)")
    arc["status"], arc["approved_turn"] = ("active" if pivot else "approved"), turn
    S.touch("arcs")
    S.commit("arc-approve", turn, ev, f'arc {arc["id"]} approved: "{short(arc_title(arc), 50)}"' + (" (now active; no arc-start needed)" if pivot else "")
             + (" (FORCED)" if bad else ""))


# ---- turn ops: the arc in play -----------------------------------------------
def open_arc(ident, *statuses):
    arc = find_arc(ident)
    if arc["status"] not in statuses:
        die(f"arc {arc['id']} is {arc['status']}; this needs it {' or '.join(statuses)}", EXIT_REFUSED)
    return arc


def cmd_arc_start(a):
    need_ev(a)
    arc = find_arc(a.id)
    live = [x for x in arcs()["arcs"] if x.get("status") in ARC_LIVE and x is not arc]
    if live:
        die(f"arc {live[0]['id']} is still {live[0]['status']}: arc-close it first (one arc at a time)", EXIT_REFUSED)
    if arc["status"] == "active":
        print(f"arc {arc['id']} is already active since turn {arc.get('start_turn')}; nothing changed.")
        return
    if arc["status"] == "provisional":
        die(f"arc {arc['id']} is provisional: it is already live (arc-approve makes it active; no arc-start)", EXIT_REFUSED)
    if arc["status"] == "parked":
        die(f"arc {arc['id']} is parked: arc-unpark {arc['id']} --notes ... brings it back (no arc-start)", EXIT_REFUSED)
    if arc["status"] != "approved":
        die(f"arc {arc['id']} is {arc['status']}: only an approved arc can start (arc-approve first)", EXIT_REFUSED)
    arc["status"], arc["start_turn"] = "active", a.turn
    S.touch("arcs")
    S.commit("arc-start", a.turn, a.evidence, f'arc {arc["id"]} "{short(arc_title(arc), 50)}" active from turn {a.turn} (budget {arc_budget(arc)})')


def cmd_arc_move(a):
    need_ev(a)
    arc = open_arc(a.id, *ARC_LIVE)
    fronts = (arc.get("hidden") or {}).get("fronts") or []
    if not fronts:
        die(f"arc {arc['id']} has no fronts")
    name, _ = pick(a.front, [f["name"] for f in fronts], what="front", strict=True)
    fr = next(f for f in fronts if f["name"] == name)
    if not 1 <= a.n <= len(fr["moves"]):
        die(f'front "{name}" has {len(fr["moves"])} moves (1 to {len(fr["moves"])}), not {a.n}')
    mv = fr["moves"][a.n - 1]
    if mv.get("done_turn") is not None:
        print(f'arc {arc["id"]} front "{name}" move {a.n} is already done (turn {mv["done_turn"]}); nothing changed.')
        return
    skipped = [i for i, m in enumerate(fr["moves"][:a.n - 1], 1) if m.get("done_turn") is None]
    if skipped:
        print(f"note: earlier move(s) {', '.join(map(str, skipped))} of this front are not marked done")
    mv["done_turn"] = a.turn
    S.touch("arcs")
    S.commit("arc-move", a.turn, a.evidence, f'arc {arc["id"]} front "{name}" move {a.n} done: {short(mv["text"], 80)}')


def cmd_arc_clue(a):
    need_ev(a)
    arc = open_arc(a.id, *ARC_LIVE)
    clues = (arc.get("hidden") or {}).get("clues") or []
    if not 1 <= a.n <= len(clues):
        die(f"arc {arc['id']} has {len(clues)} clues (1 to {len(clues)}), not {a.n}")
    c = clues[a.n - 1]
    if c.get("found_turn") is not None:
        print(f"arc {arc['id']} clue {a.n} was already found (turn {c['found_turn']}); nothing changed.")
        return
    c["found_turn"] = a.turn
    S.touch("arcs")
    found = sum(1 for x in clues if x.get("found_turn") is not None)
    S.commit("arc-clue", a.turn, a.evidence, f'arc {arc["id"]} clue {a.n} found ({found} of {len(clues)}): {short(c["text"], 80)}')


def cmd_arc_contact(a):
    need_ev(a)
    arc = open_arc(a.id, *ARC_LIVE)
    an = (arc.get("hidden") or {}).setdefault("antagonist", {})
    if an.get("contact_turn") is not None:
        print(f"arc {arc['id']} antagonist already on screen (turn {an['contact_turn']}); nothing changed.")
        return
    an["contact_turn"] = a.turn
    S.touch("arcs")
    S.commit("arc-contact", a.turn, a.evidence, f'arc {arc["id"]} antagonist {an.get("name") or "?"} reached the PC on screen')


def cmd_arc_reveal(a):
    need_ev(a)
    arc = open_arc(a.id, *ARC_LIVE)
    tw = (arc.get("hidden") or {}).setdefault("twist", {})
    if tw.get("revealed_turn") is not None:
        print(f"arc {arc['id']} twist was already revealed (turn {tw['revealed_turn']}); nothing changed.")
        return
    tw["revealed_turn"] = a.turn
    S.touch("arcs")
    if tw.get("ladder"):
        print(f'note: the twist is linked to ladder "{tw["ladder"]}": record the matching step with thread-reveal')
    S.commit("arc-reveal", a.turn, a.evidence, f'arc {arc["id"]} twist revealed (its keywords are no longer blocked)')


def cmd_arc_review(a):
    need_ev(a)
    arc = open_arc(a.id, *ARC_LIVE)
    notes = (a.notes or "").strip()
    if not notes:
        die("--notes must not be empty")
    arc.setdefault("reviews", []).append({"turn": a.turn, "kind": a.kind, "notes": notes})
    S.touch("arcs")
    S.commit("arc-review", a.turn, a.evidence, f'arc {arc["id"]} {a.kind} review: {short(notes, 90)}')


def cmd_arc_deviation(a):
    need_ev(a)
    arc = open_arc(a.id, "draft", "approved", *ARC_LIVE)
    text = " ".join(a.text).strip()
    arc.setdefault("shared", {}).setdefault("deviations", []).append({"turn": a.turn, "text": text})
    S.touch("arcs")
    S.commit("arc-deviation", a.turn, a.evidence, f'arc {arc["id"]} deviates from the act plan: {short(text, 90)}')


RETRO_TEXT = ("best", "drag", "wins", "spotlight", "threads_closed", "weakest", "notes")


def arc_retro(arc, end_turn, **given):
    """The retro of an arc that ends at end_turn: the text fields given, with the turns used against the budget and the clues
    found against the clues placed computed from the data."""
    f = {k: given.get(k) or "" for k in RETRO_TEXT}
    clues = (arc.get("hidden") or {}).get("clues") or []
    used = max(0, end_turn - arc["start_turn"]) if isinstance(arc.get("start_turn"), int) else 0
    return {"best": f["best"], "drag": f["drag"], "wins": f["wins"], "spotlight": f["spotlight"],
            "threads_closed": f["threads_closed"], "clues_found": sum(1 for c in clues if c.get("found_turn") is not None),
            "clues_placed": len(clues), "turns_used": used, "budget": arc_budget(arc), "weakest": f["weakest"], "notes": f["notes"]}


def cmd_arc_close(a):
    need_ev(a)
    arc = find_arc(a.id)
    ok = ("active",) if a.status == "closed" else ("draft", "approved", "active", "provisional", "parked")  # set_aside: also a pivot arc or a parked one
    if arc["status"] not in ok:
        die(f"arc {arc['id']} is {arc['status']}; arc-close --status {a.status} needs it {' or '.join(ok)}", EXIT_REFUSED)
    f = {k: (read_arg_text(getattr(a, k)) or "").strip() for k in RETRO_TEXT}
    if not (f["best"] or f["drag"] or f["notes"] or f["weakest"]):
        die("give at least one of --best, --drag, --weakest, --notes (the retro is written from the turn log)")
    end = arc["parked_turn"] if arc["status"] == "parked" and _is_turn(arc.get("parked_turn")) else a.turn  # a parked arc stopped when it was parked
    arc["retro"] = arc_retro(arc, end, **f)
    arc["status"], arc["closed_turn"] = a.status, a.turn
    S.touch("arcs")
    r = arc["retro"]
    S.commit("arc-close", a.turn, a.evidence,
             f'arc {arc["id"]} {a.status.replace("_", " ")}: {r["turns_used"]}/{r["budget"]} turns, clues {r["clues_found"]}/{r["clues_placed"]}'
             + (f"; weakest: {short(r['weakest'], 60)}" if r["weakest"] else ""))


def cmd_pc_thread(a):
    need_ev(a)
    text = " ".join(a.text).strip()
    if not text:
        die("give the text: what the PC did, e.g. \"went back to the cart three times\"")
    pcs = [p["name"] for p in S.get("state")["player_characters"]]
    who = None
    if a.pc is not None:
        if not pcs:
            die("no player characters yet (use pc-add first)", 2)
        who, _ = pick(a.pc, pcs, what="player character", strict=True)
    elif len(pcs) == 1:
        who = pcs[0]
    elif len(pcs) > 1:
        die(f"this campaign has {len(pcs)} player characters: give --pc NAME ({', '.join(pcs)})", 2)
    note = {"turn": a.turn, "text": text, "evidence": a.evidence}
    if who:
        note["pc"] = who
    arcs()["pc_threads"].append(note)
    S.touch("arcs")
    S.commit("pc-thread", a.turn, a.evidence, f"PC thread noted{f' ({who})' if who else ''}: {short(text, 90)}")


# ---- the pivot: off-ramps, detection, adopt, unpark (director/playbooks/pivot.md) ---------------------------------------
def arc_functions_on():
    """Arc functions (and so pivots) are on when the campaign has a session zero and a charter (PIV-10)."""
    d = arcs()
    sz = d["session_zero"]
    return bool(any(sz.get(k) for k in SZ_TEXT + SZ_LISTS) or sz.get("pillars")) and bool(d["arcs"])


def cmd_arc_offramps(a):
    """Store the Planner's hidden off-ramp sketches on an arc; replaces the earlier list. Never echoes their text."""
    turn, ev = plan_meta(a)
    arc = find_arc(a.id)
    if arc["status"] in ARC_DONE:
        die(f"arc {arc['id']} is {arc['status']}: off-ramps belong to an arc that is still going", EXIT_REFUSED)
    f = load_json_file(a.file, "arc-offramps")
    bad = offramp_problems(f)
    if bad:
        die("arc-offramps: " + "; ".join(bad), 2)
    hd = arc.setdefault("hidden", {})
    had = len(hd.get("offramps") or [])
    hd["offramps"] = [{k: x[k].strip() for k in OFFRAMP_KEYS} for x in f]
    S.touch("arcs")
    S.commit("arc-offramps", turn, ev, f"arc {arc['id']}: {len(f)} off-ramp sketch(es) stored (hidden)" + (f", replacing {had}" if had else ""))


def pc_contact_turns(arc, turns):
    """Turn numbers in which the PC was in contact with the arc: flagged `arc_contact` in the turn log, a clue found, the antagonist
    met, the twist out. A front move or a review is the world's or the director's own move, so it does not count as contact here."""
    hd = arc.get("hidden") or {}
    out = {t["turn"] for t in turns if t.get("arc_contact")}
    out |= {c.get("found_turn") for c in hd.get("clues") or [] if isinstance(c, dict)}
    out |= {(hd.get("antagonist") or {}).get("contact_turn"), (hd.get("twist") or {}).get("revealed_turn")}
    return {x for x in out if isinstance(x, int)}


def pivot_status(thread=None):
    """Read-only. Is a pivot detected (PIV-2)? Yes when `thread` is given (the director saw an input that plainly commits the PC to a
    new goal), or when the last PIVOT_TURNS logged turns all lack arc contact and a pc-thread note was added in or just before them.
    Returns {fired, why, thread, arc}; `arc` is the live arc the PC would leave."""
    out = {"fired": False, "why": "", "thread": None, "arc": None, "pc": None}
    if not arc_functions_on():
        out["why"] = "arc functions are off: a pivot needs a session zero and a charter"
        return out
    arc = out["arc"] = live_arc()
    if arc is None:
        out["why"] = "no live arc to leave"
        return out
    if thread:
        out.update(fired=True, why="the input plainly commits the PC to a new goal", thread=thread)
        return out
    turns = S.get("turns")
    if len(turns) < PIVOT_TURNS:
        out["why"] = f"fewer than {PIVOT_TURNS} turns logged"
        return out
    first, last = turns[-PIVOT_TURNS]["turn"], turns[-1]["turn"]
    marks = [(word, arc.get(k)) for word, k in (("started", "start_turn"), ("returned", "unparked_turn")) if _is_turn(arc.get(k))]
    if marks:  # the window must lie after the arc began, or came back from parking: it cannot have been left before
        word, began = max(marks, key=lambda m: m[1])
        if first <= began:
            out["why"] = f"the last {PIVOT_TURNS} turns are not all after the arc {word} (turn {began})"
            return out
    met = sorted(n for n in pc_contact_turns(arc, turns) if first <= n <= last)
    if met:
        out["why"] = f"arc contact at turn {met[-1]} within the last {PIVOT_TURNS} turns"
        return out
    notes = [x for x in arcs()["pc_threads"] if isinstance(x, dict) and isinstance(x.get("turn"), int) and x["turn"] >= first - 1]
    if not notes:
        out["why"] = f"no pc-thread note in or just before turns {first} to {last}"
        return out
    out.update(fired=True, why=f"{PIVOT_TURNS} turns without arc contact on a thread the PC chose", thread=str(notes[-1].get("text") or "").strip(),
               pc=notes[-1].get("pc") or None)
    return out


def _stem(w):
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def content_stems(text, skip=()):
    """The content words of a text (no stop words, no short words, none in `skip`), lightly stemmed: the unit of the simple word overlap."""
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", norm(text)) if len(w) > 2 and w not in STOP and w not in skip}


def match_offramp(text, sketches):
    """Index of the sketch whose `thread` shares the most content words with text (ties: the larger share, then more words of the
    whole sketch); None when no sketch shares a word."""
    have = content_stems(text)
    best = None
    for i, sk in enumerate(sketches):
        want = content_stems(sk.get("thread") or "")
        shared = len(want & have)
        if not shared:
            continue
        key = (shared, shared / len(want), len(content_stems(" ".join(str(sk.get(k) or "") for k in OFFRAMP_KEYS)) & have))
        if best is None or key > best[0]:
            best = (key, i)
    return None if best is None else best[1]


def cmd_arc_pivot(a):
    """Read-only. Prints a stored off-ramp only when a pivot is detected; otherwise says none is, and shows no off-ramp."""
    thread = None
    if a.thread is not None:
        thread = " ".join(a.thread.split())
        if not thread:
            die("--thread must not be empty", 2)
    print("arc functions: " + ("on" if arc_functions_on() else "off (they need a session zero and a charter)"))
    r = pivot_status(thread)
    if not r["fired"]:
        print(f"no pivot detected ({r['why']})")
        return
    arc = r["arc"]
    print(f'pivot detected ({r["why"]}); live arc {arc["id"]} "{short(arc_title(arc), 50)}"')
    wrap("thread", r["thread"])
    wrap("pc", r["pc"])
    turns = S.get("turns")
    if turns and turns[-1].get("arc_contact"):
        print("  note: the last logged turn has arc contact; if another PC is still in the arc this is a split party and the arc stays active (PIV-8)")
    sketches = (arc.get("hidden") or {}).get("offramps") or []
    i = match_offramp(r["thread"], sketches)
    if i is None:
        print("no stored off-ramp matches this thread: draft the mini-charter from scratch" + (f" ({len(sketches)} stored)" if sketches else ""))
    else:
        print(f"off-ramp {i + 1} of {len(sketches)} (director only: never in a prompt, never to the user):")
        for k in OFFRAMP_KEYS:
            wrap(k, sketches[i][k], 4)
    print("next: the bridge card now, the mini-charter in the background (director/agents/pivot.md), then arc-plan and arc-adopt")


SZ_SKIP = {"never", "dont", "nothing", "nobody", "none", "ever", "anyone", "anything"}  # negations of a session-zero line carry no content


def sz_matches(arc, sz):
    """Problems for each session-zero line or veil whose content words all appear in one shared or hidden string of the arc.
    A lexical check: it flags a possible crossing for the director to judge (--force overrides)."""

    def strings_at(v, path):
        if isinstance(v, str):
            return [(path, v)]
        if isinstance(v, list):
            return [p for i, x in enumerate(v, 1) for p in strings_at(x, f"{path}[{i}]")]
        if isinstance(v, dict):
            return [p for k, x in v.items() for p in strings_at(x, f"{path}.{k}")]
        return []
    texts = [(p, content_stems(s)) for p, s in strings_at(arc.get("shared") or {}, "shared") + strings_at(arc.get("hidden") or {}, "hidden")]
    bad = []
    for kind, entries in (("line", sz.get("lines") or []), ("veil", sz.get("veils") or [])):
        for e in entries:
            want = content_stems(e, SZ_SKIP)
            if not want:
                continue
            where = [p for p, have in texts if want <= have]
            if where:
                bad.append(f'session zero {kind} "{e}" matches {", ".join(where[:3])}' + (f" (+{len(where) - 3} more)" if len(where) > 3 else ""))
    return bad


def pivot_adopt_problems(arc):
    """Every way a draft breaks the pivot limits of PIV-5 (empty list = it may be adopted)."""
    hd = arc.get("hidden") or {}
    bad = []
    tw = hd.get("twist") or {}
    if str(tw.get("text") or "").strip() or tw.get("ladder") or nonempty(tw.get("keywords")):
        bad.append("hidden.twist: a pivot arc has no twist (empty text, no ladder, no keywords)")
    npcs = hd.get("new_npcs") or []
    if len(npcs) > 1:
        bad.append(f"hidden.new_npcs has {len(npcs)}: at most one new NPC, the face")
    fronts = hd.get("fronts") or []
    if len(fronts) != 1:
        bad.append(f"hidden.fronts has {len(fronts)}: a pivot arc has exactly one front")
    for fr in fronts:
        moves = nonempty(fr.get("moves"))
        if not 2 <= len(moves) <= 3 or len(moves) != len(fr.get("moves") or []):
            bad.append(f'front "{fr.get("name") or "?"}" needs 2 or 3 moves with text (has {len(fr.get("moves") or [])})')
    if len(nonempty(hd.get("clues"))) < 3:
        bad.append(f"hidden.clues needs at least 3 (has {len(nonempty(hd.get('clues')))})")
    lo, hi = PIVOT_BUDGET
    b = arc.get("budget_turns")
    if not (isinstance(b, int) and not isinstance(b, bool) and lo <= b <= hi):
        bad.append(f"budget_turns is {b}: a pivot arc takes {lo} to {hi} turns")
    return bad + sz_matches(arc, arcs()["session_zero"])


def cmd_arc_adopt(a):
    """A pivot draft becomes provisional (live, off the planner page) and the live arc is parked, in one write (PIV-5, PIV-6)."""
    need_ev(a)
    arc = find_arc(a.id)
    if arc["status"] != "draft":
        die(f"arc {arc['id']} is {arc['status']}: only a draft (arc-plan --file F.json) can be adopted as a pivot arc", EXIT_REFUSED)
    old = live_arc()
    bad = pivot_adopt_problems(arc)
    if old is None:
        bad.append("no live arc to park: a pivot leaves a live arc (a new charter starts with arc-approve and arc-start)")
    if bad and not a.force:
        die(f"arc {arc['id']} cannot be adopted as a pivot arc:\n  - " + "\n  - ".join(bad) + f"\nFix it with arc-plan --id {arc['id']}, "
            "or --force to adopt anyway (recorded).", EXIT_REFUSED)
    if bad:
        print("warning: --force overrides: " + "; ".join(bad))
        arc["adopted_forced"] = bad
    left = ""
    if old is not None and old["status"] == "provisional":  # a re-aim: the earlier pivot draft is replaced; the arc left first stays parked
        old["retro"] = arc_retro(old, a.turn, notes=f"re-aimed: replaced by {arc['id']}")
        old["status"], old["closed_turn"] = "set_aside", a.turn
        left = f"; earlier pivot arc {old['id']} set aside (re-aim)"
    elif old is not None:
        old["status"], old["parked_turn"], old["parked_for"] = "parked", a.turn, arc["id"]
        left = f"; arc {old['id']} parked"
    arc["status"], arc["start_turn"], arc["adopted_turn"] = "provisional", a.turn, a.turn
    S.touch("arcs")
    S.commit("arc-adopt", a.turn, a.evidence, f'arc {arc["id"]} "{short(arc_title(arc), 50)}" adopted as the pivot arc, provisional from turn {a.turn} '
             f'(budget {arc_budget(arc)}){left}' + (" (FORCED)" if bad else ""))


def cmd_arc_unpark(a):
    """Go back, in one write: the parked arc is active again and the provisional pivot arc closes as set_aside with the notes as its retro."""
    need_ev(a)
    old = find_arc(a.id)
    notes = (a.notes or "").strip()
    if not notes:
        die("--notes must not be empty: it is the short retro of the provisional arc (what the PC did there)")
    if old["status"] != "parked":
        die(f"arc {old['id']} is {old['status']}; arc-unpark needs it parked", EXIT_REFUSED)
    live = live_arc()
    if live is not None and live["status"] != "provisional":
        die(f"arc {live['id']} is {live['status']}, not a provisional pivot arc: arc-close it first if the story really goes back "
            "(arc-unpark closes only the provisional arc)", EXIT_REFUSED)
    if live is not None:
        live["retro"] = arc_retro(live, a.turn, notes=notes)
        live["status"], live["closed_turn"] = "set_aside", a.turn
    since = old.get("parked_turn")
    pause = max(0, a.turn - since) if _is_turn(since) else 0
    old["status"], old["unparked_turn"] = "active", a.turn
    old["paused_turns"] = (old.get("paused_turns") if _is_turn(old.get("paused_turns")) else 0) + pause  # the pause is not spent from its budget
    if isinstance(old.get("start_turn"), int):
        old["start_turn"] += pause
    S.touch("arcs")
    S.commit("arc-unpark", a.turn, a.evidence, f'arc {old["id"]} is active again (parked from turn {since}); '
             + (f'pivot arc {live["id"]} set aside: {short(notes, 60)}' if live else "no provisional arc was live"))


# ---- reading -----------------------------------------------------------------
def jn(v):
    return "; ".join(str(x.get("text") if isinstance(x, dict) else x) for x in v) if isinstance(v, list) else v


def print_arc(arc, turn, shared_only=False, offramps=False):
    sh, hd = arc.get("shared") or {}, arc.get("hidden") or {}
    head = f'{arc["id"]} "{arc_title(arc)}" [{arc.get("status")}] act {arc.get("act")}' + (", blind arc" if arc.get("blind") else "")
    if arc.get("status") in ARC_LIVE:
        head += ", " + arc_progress(arc, turn) + f", started turn {arc.get('start_turn')}"
        if arc.get("status") == "provisional":
            head += " (pivot arc: off the planner page until approved)"
    elif arc.get("status") == "parked":
        head += f", parked turn {arc.get('parked_turn')}" + (f" (taken over by {arc['parked_for']})" if arc.get("parked_for") else "")
    elif arc.get("status") in ARC_DONE and isinstance(arc.get("retro"), dict):
        head += f", {arc['retro'].get('turns_used')}/{arc['retro'].get('budget')} turns"
    else:
        head += f", budget {arc_budget(arc)} turns"
    print(head + (f", approved turn {arc['approved_turn']}" if arc.get("approved_turn") is not None else ""))
    if shared_only:
        print("  (shared fields only: what the user sees" + ("; blind arc: title, promise, tone" if arc.get("blind") else "") + ")")
    for key, lab, v in planner_page.visible_fields(arc) if shared_only else [
            (k, lab, sh.get(k)) for k, lab in planner_page.SHARED_ORDER if sh.get(k) not in (None, "", [], {})]:
        if key == "title":
            continue
        wrap(lab.lower(), "; ".join(f"{k}: {x}" for k, x in v.items()) if isinstance(v, dict) else jn(v))
    devs = [] if (shared_only and arc.get("blind")) else sh.get("deviations") or []
    for dv in devs:
        print(f"  deviation (turn {dv.get('turn')}): {dv.get('text')}")
    if shared_only:
        return
    print("hidden (director only):")
    tw = hd.get("twist") or {}
    if arc.get("status") == "provisional" and not (tw.get("text") or tw.get("ladder") or tw.get("keywords")):
        wrap("twist", "none (a pivot arc has no twist)")
    else:
        wrap("twist", f"{tw.get('text')} | ladder: {tw.get('ladder') or '-'} | keywords: {', '.join(tw.get('keywords') or []) or '-'}"
             + (f" | revealed turn {tw['revealed_turn']}" if tw.get("revealed_turn") is not None else " | not revealed"))
    for fr in hd.get("fronts") or []:
        print(f"  front {fr.get('name')}: {fr.get('goal')}")
        for i, m in enumerate(fr.get("moves") or [], 1):
            print(f"    {i}. [{'done t' + str(m['done_turn']) if m.get('done_turn') is not None else ' '}] {m.get('text')}")
    an = hd.get("antagonist") or {}
    wrap("antagonist", f"{an.get('name')} | face: {an.get('face')} | first contact: {an.get('first_contact')}"
         + (f" | on screen turn {an['contact_turn']}" if an.get("contact_turn") is not None else " | not on screen yet"))
    for i, c in enumerate(hd.get("clues") or [], 1):
        print(f"  clue {i}. [{'found t' + str(c['found_turn']) if c.get('found_turn') is not None else ' '}] {c.get('text')}")
    for k in ("surprises", "climax_options", "cast", "new_npcs"):
        wrap(k.replace("_", " "), jn(hd.get(k)))
    wrap("pc test situations", "; ".join(f"{k}: {v}" for k, v in (hd.get("pc_test_situations") or {}).items()))
    wrap("notes", hd.get("notes"))
    for r in arc.get("reviews") or []:
        print(f"  review turn {r.get('turn')} ({r.get('kind')}): {r.get('notes')}")
    if arc.get("approved_forced"):
        print("  approved with --force: " + "; ".join(arc["approved_forced"]))
    if arc.get("adopted_forced"):
        print("  adopted with --force: " + "; ".join(arc["adopted_forced"]))
    rt = arc.get("retro")
    if isinstance(rt, dict):
        print("  retro: " + "; ".join(f"{k.replace('_', ' ')} {v}" for k, v in rt.items() if v not in ("", None)))
    if offramps:  # only on request: off-ramps are hidden material (PIV-1)
        sk = hd.get("offramps") or []
        print("off-ramps (director only; never in a prompt, never to the user):" + ("" if sk else " none stored (arc-offramps ID --file F.json)"))
        for i, x in enumerate(sk, 1):
            for k in OFFRAMP_KEYS:
                print(f"  {i}. {k}: {x.get(k)}" if k == OFFRAMP_KEYS[0] else f"     {k}: {x.get(k)}")


def cmd_arc(a):
    turn = get_state_turn()
    rows = arcs()["arcs"]
    if a.list:
        print("\n".join(arc_line(x, turn) for x in rows) if rows else "no arcs yet (arc-plan --file F.json)")
        return
    if a.shared and a.offramps:
        die("--offramps is director-only: --shared never shows hidden fields", 2)
    arc = find_arc(a.id) if a.id else current_arc()
    if not arc:
        print("no arc yet: plan one with the user (docs/arc-planning.md; plan-brief, then arc-plan --file F.json)")
        return
    print_arc(arc, turn, a.shared, a.offramps)


def cut_line(prompt):
    m = re.search(r"^[ \t]*Cut[ \t]*:(.*)$", prompt or "", re.M)
    return m.group(1) if m else ""


def boredom_flags(st, turns):
    """Names of the boredom flags raised (only with 10 or more logged turns)."""
    if len(turns) < 10:
        return []
    flags = []

    def mean(ts):
        return sum(len(str(t.get("inputs") or "")) for t in ts) / len(ts)
    before = mean(turns[-10:-3])
    if before > 0 and mean(turns[-3:]) < 0.5 * before:
        flags.append("shorter inputs")
    if sum(1 for t in turns[-3:] if cut_skips(cut_line(t.get("prompt")))) >= 2:
        flags.append("repeated skips")
    fb = st.get("feedback") or []
    if fb and str(fb[-1].get("drag") or "").strip():
        flags.append("drag in the latest feedback")
    return flags


def variety_flags(st, turns):
    """The one variety check (SCN-7): the boredom flags (shorter inputs, repeated skips, a drag note; each as before, with
    10 or more logged turns) and three scenes of one kind in a row. Names of the flags raised."""
    flags = boredom_flags(st, turns)
    run = same_kind_run(st)
    if run:
        flags.append(f"three {run} scenes in a row")
    return flags


def variety_lines(st, turns):
    """Prep's variety lines: all flags in one place with their count; two or more call for the one-line check with the user."""
    flags = variety_flags(st, turns)
    if not flags:
        return []
    out = [f"variety flags ({len(flags)}): " + ", ".join(flags)]
    if len(flags) >= 2:
        out.append("two or more variety flags: one-line check with the user; next pressure card adds variety")
    return out


def arc_activity_turns(arc, turns):
    """Turn numbers in which the arc was touched: contact flagged in the log, a move, clue, contact, reveal or review."""
    hd = arc.get("hidden") or {}
    out = {t["turn"] for t in turns if t.get("arc_contact")}
    out |= {m.get("done_turn") for f in hd.get("fronts") or [] for m in f.get("moves") or []}
    out |= {c.get("found_turn") for c in hd.get("clues") or []}
    out |= {(hd.get("antagonist") or {}).get("contact_turn"), (hd.get("twist") or {}).get("revealed_turn")}
    out |= {r.get("turn") for r in arc.get("reviews") or []}
    return {x for x in out if isinstance(x, int)}


def arc_drifting(arc, turns):
    start = arc.get("start_turn")
    if not isinstance(start, int):
        return False
    if _is_turn(arc.get("unparked_turn")):  # an arc that came back from parking drifts only from its return
        start = max(start, arc["unparked_turn"])
    recent = [t["turn"] for t in turns if t["turn"] > start][-DRIFT_TURNS:]
    if len(recent) < DRIFT_TURNS:
        return False
    touched = arc_activity_turns(arc, turns)
    return not any(recent[0] <= n <= recent[-1] for n in touched)


def arc_checklist(st):
    """Arc lines of prep's LIVE CHECKLIST."""
    out, turns, turn = [], S.get("turns"), st["turn"]
    arc = live_arc()  # active, or provisional after a pivot: both count as live
    if not arc:
        wait = [x for x in arcs()["arcs"] if x.get("status") == "approved"]
        if wait:
            out.append(f"arc {wait[0]['id']} approved, not started: arc-start when its first pressure shows in Voyage's output")
        else:
            out.append("no arc live: one line under the prompt offers a planning session")
    else:
        hd = arc.get("hidden") or {}
        out.append(f'arc {arc["id"]} "{short((arc.get("shared") or {}).get("promise") or arc_title(arc), 60)}" {arc_progress(arc, turn)}'
                   + (" provisional (pivot arc: approve, re-aim or go back)" if arc["status"] == "provisional" else ""))
        an = hd.get("antagonist") or {}
        if arc_at(arc, turn, 60) and not any(r.get("kind") == "midpoint" for r in arc.get("reviews") or []):
            out.append("midpoint review due (arc-review --kind midpoint)")
        if arc_at(arc, turn, 50) and (an.get("name") or an.get("first_contact")) and an.get("contact_turn") is None:
            out.append("antagonist not on screen yet: contact due by the midpoint")
        if arc_at(arc, turn, 100):
            out.append("arc at budget: no new pressure; climax hooks where the PC is")
        if arc_at(arc, turn, 130):
            out.append("arc at 130%: ask the user once: extend or wrap up")
        clues = hd.get("clues") or []
        if clues:
            out.append(f"clues found {sum(1 for c in clues if c.get('found_turn') is not None)} of {len(clues)}")
        if arc_drifting(arc, turns):
            out.append(f"arc drifting ({DRIFT_TURNS} turns without contact): the front moves on; one line: re-aim?")
    for pk in parked_arcs():
        out.append(f'arc {pk["id"]} "{short(arc_title(pk), 50)}" parked since turn {pk.get("parked_turn")}: its clocks and fronts keep moving '
                   f"(arc-unpark {pk['id']} to go back)")
    out += variety_lines(st, turns)
    return out


def arc_resume_lines(st):
    d = arcs()
    act = current_act(st)
    pitch = find_act(act)
    arc = current_arc()
    if not pitch and not arc:
        line = "Arc planner: no plan yet: offer a planning session (docs/arc-planning.md)"
    else:
        bits = [f"act {act} pitch {pitch['status'] if pitch else 'none'}"]
        if arc:
            bits.append(f'arc {arc["id"]} "{short(arc_title(arc), 50)}" {arc["status"]}'
                        + (f" {arc_progress(arc, st['turn'])}" if arc["status"] in ARC_LIVE else ""))
        else:
            bits.append("no arc live (docs/arc-planning.md)")
        bits += [f'parked arc {pk["id"]} "{short(arc_title(pk), 40)}"' for pk in parked_arcs()]
        line = "Arc planner: " + "; ".join(bits)
    out = [line]
    url = d.get("page_url") or pages_url()
    if url:
        out.append(f"Planner page: {url}")
    return out


def pages_url():
    """Default GitHub Pages address of this campaign's planner page: pages_base from the repo-level site.json + NAME/ (None if unset)."""
    try:
        base = json.loads((ROOT / "site.json").read_text(encoding="utf-8")).get("pages_base")
    except (OSError, ValueError, AttributeError):
        return None
    return str(base).rstrip("/") + f"/{CAMPAIGN}/" if base and CAMPAIGN else None


def act_first_turn(st, turns):
    """First logged turn of the current act: the first turn on or after the act's first day. None when the act's first day or
    the days of the logged turns are not known; st.turn + 1 when no turn has been logged in the act yet."""
    start = ACT_STARTS.get(current_act(st))
    if start is None or not any(_plain_int(t.get("day")) for t in turns):
        return None
    return next((t["turn"] for t in turns if _plain_int(t.get("day")) and t["day"] >= start), st["turn"] + 1)


def scene_mix_lines(st, turns, sz):
    """plan-brief's scene mix (SCN-7, D10): scenes started since the current act began (the last MIX_SCENES scenes when the
    act's first turn is unknown), counted by variety tag against session zero's pillars. Downtime is reported on its own;
    scenes without a tag are untagged."""
    hist, t0 = scene_history(st), act_first_turn(st, turns)
    if t0 is None:
        label, scenes = f", the last {MIX_SCENES} scenes at most (the act's first turn is unknown)", hist[-MIX_SCENES:]
    else:
        label = f" since act {current_act(st)} began (turn {t0})"
        scenes = [x for x in hist if _plain_int(x.get("start_turn")) and x["start_turn"] >= t0]
    head = f"SCENE MIX{label}, {len(scenes)} scene{'' if len(scenes) == 1 else 's'}"
    if not scenes:
        return [head + " (tag each scene: scene-start --kind " + "|".join(SCENE_KINDS) + ")"]
    pill = sz.get("pillars") or {}
    kinds = [x["kind"] for x in scenes]
    bits = [f"{pillar} ({kind}) {kinds.count(kind)}" + (f" [session zero {pill[pillar]}]" if pillar in pill else "") for kind, pillar in KIND_PILLAR.items()]
    untagged = sum(1 for k in kinds if k not in SCENE_KINDS)
    extra = [f"{k} {v}" for k, v in pill.items() if k not in KIND_PILLAR.values()]
    return [head + ": " + ", ".join(bits),
            f"  downtime {kinds.count('downtime')} (on its own); untagged {untagged}"
            + (f"; session-zero play styles with no scene tag: {', '.join(extra)}" if extra else "")]


def cmd_plan_brief(a):
    """Planning brief (read-only, director view): everything a planning session or the Planner needs, in about 80 lines."""
    st, d = S.get("state"), arcs()
    turns, act = S.get("turns"), current_act(st)
    print(f"PLAN BRIEF {display()} | turn {st['turn']} | Day {st['day']} {st['weekday']} | Act {act}")
    print_session_zero(d["session_zero"])
    for line in scene_mix_lines(st, turns, d["session_zero"]):
        print(line)
    pitch = find_act(act)
    print(f"ACT {act}: pitch {pitch['status'] if pitch else 'none'}; the bible's plan: `db.py bible act{act}`")
    if pitch:
        for k, lab in (("title", "title"), ("theme", "theme"), ("question", "question"), ("builds_to", "builds to"), ("stakes_scale", "stakes scale"), ("ending_shape", "ending shape")):
            brief_row(lab, (pitch.get("shared") or {}).get(k) or "-", 2)
        for dv in pitch.get("deviations") or []:
            brief_row(f"deviation t{dv.get('turn')}", dv.get("text"), 2)
    rows = sorted(d["arcs"], key=arc_num)
    done = [x for x in rows if x.get("status") in ARC_DONE]
    if done:
        last = done[-1]
        print(f'LAST ARC: {arc_line(last, st["turn"])}')
        rt = last.get("retro") if isinstance(last.get("retro"), dict) else {}
        for k in ("best", "drag", "wins", "spotlight", "threads_closed", "weakest", "notes"):
            if rt.get(k):
                brief_row(k.replace("_", " "), rt[k], 2)
        if rt:
            brief_row("clues found/placed", f"{rt.get('clues_found')}/{rt.get('clues_placed')}", 2)
        print("  the next charter must respond to the weakest point; the deferred retro question (Best moment? Anything drag?) is asked now")
    else:
        print("LAST ARC: none yet")
    fb = st.get("feedback") or []
    print("FEEDBACK (last 5):" + ("" if fb else " none"))
    for f in fb[-5:]:
        brief_row(f"T{f['turn']} {f['kind']}", f"best {f.get('best') or '-'}; drag {f.get('drag') or '-'}" + (f"; {f['notes']}" if f.get("notes") else ""), 2)
    past = [x for x in rows if x.get("status") in ("approved", "active", "provisional", "parked", "closed", "set_aside")][-2:]
    print("VARIETY (last two charters; choose different set-piece kinds):" + ("" if past else " none yet"))
    for x in past:
        sh = x.get("shared") or {}
        brief_row(x["id"], f"{', '.join(sh.get('set_pieces') or []) or '-'} | stakes {sh.get('stakes') or '-'} | climax {sh.get('climax_kind') or '-'}", 2)
    print("PCs (backstory hooks come from these sheets):" + ("" if st["player_characters"] else " none yet"))
    for pc in st["player_characters"]:
        brief_row(pc["name"], " | ".join(f"{k}: {pc[k]}" for k in ("background", "power", "notes") if pc.get(k)) or "(no sheet yet)", 2)
    pt = d["pc_threads"][-10:]
    print("PC THREADS (what each PC keeps returning to; last 10):" + ("" if pt else " none yet"))
    order = [pc["name"] for pc in st["player_characters"]]
    for who in order + [w for w in dict.fromkeys(x.get("pc") for x in pt if x.get("pc")) if w not in order] + [None]:
        rows = [x for x in pt if (x.get("pc") or None) == who]
        if rows:
            print(f"  {who or '(no PC)'}:")
            for x in rows:
                brief_row(f"t{x.get('turn')}", x.get("text"), 4)
    print("LADDERS (director only):")
    for k, t in S.get("threads").items():
        n = next_step(t)
        got = sum(1 for s in t["steps"] if s["status"] == "revealed")
        brief_row(k, f"{got}/{len(t['steps'])} revealed" + (f"; next hidden step {n['step']} (act {n['earliest_act']}): {n['reveal']}" if n else "; complete"), 2)
    Q = S.get("quests")
    print("ACTIVE QUESTS:" + ("" if st["active_quests"] else " none"))
    for q in st["active_quests"]:
        brief_row(q, surface_goal(Q.get(q, {})) or "(no surface goal)", 2)
    print("OPEN CLOCKS:" + ("" if st["open_clocks"] else " none"))
    for ck in st["open_clocks"]:
        brief_row(ck["name"], f"due day {ck['due_day']} ({ck['due_day'] - st['day']} left)", 2)
    c = cast()
    mains = [n for n in MAIN_NPCS if n in c and c[n].get("status") == "in_play"]
    print("MAIN NPCS IN PLAY (agenda):" + ("" if mains else " none yet"))
    for n in mains:
        ag = c[n].get("agenda") or {}
        brief_row(n, f"{ag.get('want') or c[n].get('want') or '-'}; next: {ag.get('next_move') or '-'}", 2)
    recent = S.get("canon")["facts"][-8:]
    print("CANON (last 8; echo candidates):" + ("" if recent else " none yet"))
    for f in recent:
        brief_row(f"t{f['turn']} {f['subject']}", f["fact"], 2)
    since = max([x.get("start_turn") for x in rows if isinstance(x.get("start_turn"), int)] + [0])
    inv = [(t["turn"], txt) for t in turns if t["turn"] > since for cat, txt in parse_slips(t.get("slips")) if cat == "invention"]
    print(f"VOYAGE INVENTIONS since turn {since} (fold into fronts, yes-and):" + ("" if inv else " none"))
    for n, txt in inv[-8:]:
        brief_row(f"t{n}", txt, 2)
    sz = d["session_zero"]
    if sz.get("lines") or sz.get("veils"):
        print("RESPECT: lines " + "; ".join(sz.get("lines") or ["-"]) + " | veils " + "; ".join(sz.get("veils") or ["-"]))


# ---- preflight: the readiness check before play ------------------------------
def pending_op_done(op, act):
    """True when a deferred op is already in the data (act-deviation: the same text on the pitch); None when it cannot be told."""
    if op.get("op") == "act-deviation":
        args = op.get("args") or {}
        text = args.get("text")
        text = " ".join(text) if isinstance(text, list) else str(text or "")
        return any(norm(d.get("text")) == norm(text) for d in act.get("deviations") or [])
    return None


def preflight_items():
    """[(level, text)] for the readiness check; level is FAIL, WARN or OK. Read-only."""
    st, d = S.get("state"), arcs()
    act_n = current_act(st)
    items = []
    ctx = git_ctx()
    if ctx:
        br = git_branch(ctx[0])
        items.append(("OK", "git: on main") if br == "main" else ("FAIL", f"git: on {br or '?'}, not main (git fetch origin main && git checkout -B main origin/main)"))
        n = unpushed_count(*ctx)
        if n:
            items.append(("WARN", f"git: {n} unpushed commit(s) (db.py save)"))
    if stale_warning():
        items.append(("FAIL", stale_warning()))
    mine, tpl = rules_version(SKILL_FILE), rules_version(TEMPLATE_SKILL)
    if mine and tpl and version_key(mine) < version_key(tpl):
        items.append(("WARN", f"skill generic rules {mine} are behind the template {tpl} (tools/sync_skill.py {CAMPAIGN})"))
    items.append(("OK", f"skill version (repo) {skill_version()}: if the loaded skill's line differs, the user re-uploads the zip"))
    dv = director_skill_version()
    items.append(("WARN" if dv.startswith("unknown") else "OK",
                  f"director skill version (repo) {dv}: if the loaded bootstrap skill's line differs, the user re-uploads it"))
    arc_on = arc_functions_on()
    sz = d["session_zero"]
    if arc_on:
        items.append(("OK", "session zero recorded"))
    else:
        items.append(("OK", "arc functions are off (no session zero and charter yet): session zero, act pitch, charter and act checklist are not checked"))
    players = sz.get("players")
    pcs = st["player_characters"]
    if not pcs:
        items.append(("FAIL", "no PC sheets yet: run the README intake, then pc-add / pc-sheet" + (f" ({players} expected)" if players else "")))
    elif players and len(pcs) < players:
        items.append(("FAIL", f"{len(pcs)} of {players} PC sheets recorded (intake: pc-add)"))
    elif players and len(pcs) > players:
        items.append(("WARN", f"{len(pcs)} PCs recorded but session zero says {players} players"))
    else:
        items.append(("OK", f"{len(pcs)} PC sheet(s) recorded" + ("" if players else " (session-zero --players N would let preflight count them)")))
    for pc in pcs:
        miss = [k for k in ("pronouns", "power", "background") if not str(pc.get(k) or "").strip()]
        if miss:
            items.append(("WARN", f"PC {pc['name']}: sheet lacks {', '.join(miss)} (from the user only: pc-sheet)"))
    act = find_act(act_n)
    if not arc_on:
        pass  # CHAT-4, K14: the arc checks below apply only when arc functions are on
    elif not act:
        items.append(("FAIL", f"act {act_n}: no pitch (planning session: act-plan {act_n})"))
    elif act["status"] != "approved":
        items.append(("FAIL", f"act {act_n}: pitch is {act['status']}, not approved (act-approve {act_n})"))
    else:
        items.append(("OK", f'act {act_n}: pitch approved: "{short((act.get("shared") or {}).get("title"), 50)}"'))
    rows = sorted((x for x in d["arcs"] if x.get("act") in (None, act_n) and x.get("status") not in ARC_DONE), key=arc_num) if arc_on else []
    if arc_on and not rows:
        items.append(("WARN", "no arc charter for this act yet: plan it (docs/arc-planning.md) or play on the open threads"))
    for x in rows:
        if x.get("status") == "active":
            items.append(("OK", f"arc {x['id']} is active (turn {arc_used(x, st['turn'])} of budget {arc_budget(x)})"))
        elif x.get("status") == "provisional":
            items.append(("OK", f"arc {x['id']} is provisional, a pivot arc (turn {arc_used(x, st['turn'])} of budget {arc_budget(x)}): arc-approve when the user approves it"))
        elif x.get("status") == "parked":
            items.append(("OK", f"arc {x['id']} is parked since turn {x.get('parked_turn')} (arc-unpark to go back, arc-close --status set_aside to drop it)"))
        elif x.get("status") == "approved" and x is rows[0]:
            items.append(("OK", f"arc {x['id']} is approved: next to start (arc-start when its first pressure shows)"))
        elif x.get("status") == "approved":
            items.append(("OK", f"arc {x['id']} is approved (starts when the previous arc closes)"))
        else:
            refine = [str(r).strip() for r in (x.get("hidden") or {}).get("refine") or [] if str(r).strip()]
            items.append(("WARN", f"arc {x['id']} is a draft" + (": refine first: " + "; ".join(refine) if refine else " (review, then arc-approve)")))
    for op in (((act or {}).get("hidden") or {}).get("pending_ops") or []) if arc_on else []:
        done = pending_op_done(op, act)
        if done:
            continue
        when = "the turn 1 record payload (Voyage's story start; turn ops need turn 1 or later)" if st["turn"] < 1 else "the next commit-turn payload"
        items.append(("WARN", f"deferred op from the act pitch, add it to {when}: " + json.dumps(op, ensure_ascii=False)))
    try:
        planner_page.render(d, page_ctx())
        items.append(("OK", "planner page renders spoiler-safe"))
    except planner_page.Leak as e:
        items.append(("FAIL", f"planner page would leak a hidden term: {e}"))
    if st["turn"] == 0:
        items.append(("OK", "turn 0: turn 1 is Voyage's story start (record it with prompt \"none\"); the first director prompt is turn 2"))
    return items


def cmd_preflight(a):
    """Readiness check before the first turn of a chat (and at each act start). Read-only; exit 4 on any FAIL."""
    st = S.get("state")
    act_n = current_act(st)
    items = preflight_items()
    print(f"PREFLIGHT {display()} | turn {st['turn']} | Day {st['day']} {st['weekday']} | Act {act_n}")
    for lvl, text in items:
        for i, ln in enumerate(textwrap.wrap(text, 110) or [""]):
            print(f"  {lvl:<4} {ln}" if i == 0 else f"       {ln}")
    for doc in (() if generic_skill_campaign() else ("fast-turn.md", "player-agency.md")):
        if (CAMPAIGN_DIR / "docs" / doc).exists():
            print(f"  READ campaigns/{CAMPAIGN}/docs/{doc}")
    act = find_act(act_n)
    checks = (((act or {}).get("hidden") or {}).get("checklist") or []) if arc_functions_on() else []
    if checks:
        print(f"ACT {act_n} PLAN (agreed with the user; confirm each before the first prompt):")
        for c in checks:
            for i, ln in enumerate(textwrap.wrap(c, 108)):
                print(f"  [ ] {ln}" if i == 0 else f"      {ln}")
    fails = sum(1 for lvl, _ in items if lvl == "FAIL")
    warns = sum(1 for lvl, _ in items if lvl == "WARN")
    print(f"RESULT: {fails} FAIL, {warns} WARN: " + ("not ready, fix the FAIL lines first" if fails else "ready to play"))
    if fails:
        sys.exit(EXIT_REFUSED)


def preflight_summary_line():
    items = preflight_items()
    fails = sum(1 for lvl, _ in items if lvl == "FAIL")
    warns = sum(1 for lvl, _ in items if lvl == "WARN")
    return f"Preflight: {fails} FAIL, {warns} WARN" + (": run `db.py preflight` before the first prompt" if fails or warns else ": ready")


def page_ctx(secrets=None):
    """The planner page's context. `secrets` is secret_terms() when the caller already has it."""
    st = S.get("state")
    Q, T = S.get("quests"), S.get("threads")
    secrets = secret_terms() if secrets is None else secrets
    acts = [{"n": x.get("n"), "from_day": x.get("from_day"), "to_day": x.get("to_day")} for x in CFG.get("acts") or []]
    return {"display": display(), "day": st["day"], "weekday": st["weekday"], "act": current_act(st), "turn": st["turn"], "acts": acts,
            "quests": [{"name": q, "goal": re.sub(r"^Start quest .*?\):\s*", "", surface_goal(Q.get(q, {})))} for q in st["active_quests"]],
            "revealed": [s["reveal"] for t in T.values() for s in t["steps"] if s["status"] == "revealed"],
            "ladder_terms": {t: src for t, (src, strong) in secrets.items() if strong and not src.startswith("arc ")},
            "public_names": [n for n, e in cast().items() if e.get("status") == "in_play"]}


def cmd_planner_page(a):
    if a.out is None and a.set_url is None:
        die("give --out FILE (render the page) and/or --set-url URL (remember where it is published)")
    if a.set_url is not None:
        turn, ev = plan_meta(a)
        url = a.set_url.strip()
        if not re.match(r"https?://\S+$", url):
            die("--set-url must be an http(s) URL", 2)
        arcs()["page_url"] = url
        S.touch("arcs")
        S.commit("planner-page", turn, ev, f"planner page url set: {url}")
    if a.out is not None:
        try:
            page = planner_page.render(arcs(), page_ctx())
        except planner_page.Leak as e:
            die("planner page refused, nothing written: " + str(e) + ". Reword the shared field, or mark the twist revealed.", EXIT_REFUSED)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print(f"planner page: wrote {out} ({len(page.encode('utf-8'))} bytes; read-only, spoiler-safe)")


# ----------------------------------------------------------------------------
# scan: the hidden-term scan for any text the user may see (ORCH-5, SEC-1)
# ----------------------------------------------------------------------------
EXIT_SCAN = EXIT_REFUSED  # `scan` found a hidden term: exit 4, the code the director and the subagent briefs rely on (0 = clean)


def hidden_score_words():
    """The words that name an enabled hidden-score module: the Standing label and its ledger file, the Debt label."""
    words = []
    if module_on("standing"):
        words += [module_cfg("standing").get("label") or "Standing", module_cfg("standing").get("file") or "ledger"]
    if module_on("debt"):
        words.append(module_cfg("debt").get("label") or "Debt")
    return words


def scan_text(text):
    """(hits, n_terms): the hidden terms a user-facing text holds, hits being [(term, where, excerpt)], and how many terms were checked.
    A hit is a term the planner page refuses (planner_page.hidden_terms: twist keywords of unrevealed twists, antagonist names not yet
    public, the text of every off-ramp sketch, strong terms of hidden ladder steps), a strong secret term of check-prompt (secret_terms),
    a campaign hidden word (campaign.json hidden_words, recap and prompt lists) or the name of a hidden-score module. Soft secret terms
    only warn in check-prompt and are not a hit here. Revealed ladder steps and public_ok terms are no secret (secret_terms leaves them
    out), exactly as in check-prompt and the planner page. Each term is matched the way its own check matches it."""
    secrets = secret_terms()
    strong = {t: v for t, v in secrets.items() if v[1]}
    words = (CFG.get("hidden_words") or {})
    terms = planner_page.hidden_terms(arcs()["arcs"], page_ctx(secrets)) \
        + planner_page.word_terms(list(words.get("recap") or []) + list(words.get("prompt") or []), "campaign hidden word") \
        + planner_page.word_terms(hidden_score_words(), "hidden-score word")
    found = {}  # term -> where; the first source of a term wins
    for term, where in planner_page.term_hits([(text, "shared")], terms):
        found.setdefault(term, where)
    for term, src, _strong in find_secrets(text, strong):
        found.setdefault(term, src)
    hits = [(t, w, planner_page.excerpt(text, t) or planner_page.excerpt(text, t, normalize=norm)) for t, w in found.items()]
    return hits, len({t for t, _ in terms} | set(strong))


def cmd_scan(a):
    """Read-only. Exit 0 and one line when the text is clean; exit 4 and one line per hit when it holds a hidden term."""
    if a.file == "-":
        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    elif Path(a.file).is_file():
        text = Path(a.file).read_text(encoding="utf-8", errors="replace")
    else:
        die(f"no such file: {a.file}")
    hits, checked = scan_text(text)
    if not hits:
        print(f"scan: clean, no hidden term found ({checked} terms checked)")
        return
    print(f"scan: {len(hits)} hidden term(s) found: do not show this text to the user. "
          "These lines name hidden material, for the director only; reword the text and scan it again.")
    for term, where, ex in hits:
        print(f'  HIT "{short(term, 60)}" ({where}): {ex}')
    sys.exit(EXIT_SCAN)


# ----------------------------------------------------------------------------
# record: one whole turn as a single locked, all-or-nothing write
# ----------------------------------------------------------------------------
RECORD_OPS = ["add-npc", "npc-seen", "npc-note", "agenda", "fact", "pc-add", "pc-sheet", "pos", "time",
              "question", "question-close", "fact-status",
              "quest-start", "quest-obj", "quest-end", "ledger", "clock-add", "clock-done", "thread-reveal",
              "add-area", "scene-start", "scene-obstacle", "scene-surprise", "scene-end", "feedback", "studio-request", "studio-done",
              "arc-start", "arc-move", "arc-clue", "arc-contact", "arc-reveal", "arc-review", "arc-deviation", "arc-close",
              "arc-adopt", "arc-unpark", "act-deviation", "pc-thread"]
SHEET_ARGS = ("pronouns", "power", "background", "notes")
TURN_LOG_KEYS = ("inputs", "summary", "prompt", "slips", "notes", "arc_contact", "escalated")


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
                if d == "inferred" and not isinstance(v, bool):
                    raise ArgError("arg 'inferred' must be true or false")
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


def check_payload(p, prompt_required=True):
    """Structure problems of a payload. turn_log.prompt is required unless prompt_required is False (commit-turn --scene)."""
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
        errs.append("'turn_log' is required: {inputs, summary, prompt, slips, notes, arc_contact, escalated}")
    else:
        for k in tl:
            if k not in TURN_LOG_KEYS:
                errs.append(f"turn_log: unknown key '{k}'")
        for k in ("arc_contact", "escalated"):
            if k in tl and not isinstance(tl[k], bool):
                errs.append(f"turn_log.{k} must be true or false")
        for k in ("inputs", "summary", "prompt"):
            if k == "prompt" and not prompt_required:
                continue
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


def day_change_lines(steps):
    """The `time` op's "Day changed" line of a recorded turn (WLD-3), so a day change inside a payload also tells the director
    to run day-turnover."""
    return ["  " + n for _, _, notes in steps for n in notes if n.startswith("Day changed")]


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
        for ln in day_change_lines(steps):
            print(ln)
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


def restore_review_slips(kept):
    """After a snapshot restore: put back the review findings of turns that stay (`review-add` may have written them after the snapshot
    was taken; only the turns being undone lose theirs). Returns the turns changed."""
    if not kept:
        return []
    S.reset()
    turns, changed = S.get("turns"), []
    for t in turns:
        if t.get("turn") in kept and t.get("review_slips") != kept[t["turn"]]:
            t["review_slips"] = kept[t["turn"]]
            changed.append(t["turn"])
    if changed:
        tmp = DATA / "turns.json.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(turns, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, DATA / "turns.json")
        S.reset()
    return changed


def cmd_undo_turn(a):
    with write_lock("undo-turn", a.n):
        S.reset()
        st = S.get("state")
        # a snapshot named for the next turn is the one `sync --apply` takes when it logs no turn (or marks turns undone): allowed
        if a.n < 1 or (a.n > st["turn"] and not snap_dir(a.n).is_dir()):
            die(f"turn {a.n} is not logged (state.turn = {st['turn']})")
        d = snap_dir(a.n)
        if not d.is_dir():
            have = snap_numbers()
            die(f"no snapshot before turn {a.n}. Snapshots exist for turns: {', '.join(map(str, have)) or 'none'}")
        kept_reviews = {t["turn"]: t["review_slips"] for t in S.get("turns") if t.get("turn", a.n) < a.n and t.get("review_slips")}
        restore_snapshot(d)
        for n in snap_numbers():
            if n >= a.n:
                shutil.rmtree(snap_dir(n), ignore_errors=True)
        regained = restore_review_slips(kept_reviews)
        bad = verify_data(a.n - 1)
        if bad:
            die("restored, but verification failed: " + "; ".join(bad))
        print(f"undo-turn {a.n}: restored the snapshot taken before turn {a.n}; state.turn is now {S.get('state')['turn']}.")
        if regained:
            print(f"  kept the director-review findings on turn(s) {', '.join(map(str, regained))} (they were added after the snapshot).")
        print("Run `db.py save` to commit the rewind if the later turns were already saved.")


def cmd_recover(a):
    """Clear a stale write lock; restore the pre-turn snapshot if a crashed `record` left the data half-applied."""
    role_gate("recover")
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
        torn = len([x for x in turns if not x.get("undone")]) + turn_base(st) != st["turn"]
        if info.get("cmd") == "sync-apply" and snap is not None and snap.is_dir():  # a crashed `sync --apply`: put the pre-sync data back
            restore_snapshot(snap)
            shutil.rmtree(snap, ignore_errors=True)
            print(f"  restored the snapshot taken before the sync (state.turn was {st['turn']}); the interrupted sync --apply did not count.")
            print(f"  state.turn is now {S.get('state')['turn']}. Run the sync again if you still want it.")
        elif info.get("cmd") == "record" and snap is not None and snap.is_dir() and (st["turn"] < t or torn):
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
# sync: Voyage's exported state against the database (SYNC-1 to SYNC-8, D15, D19, STATE-2)
# ----------------------------------------------------------------------------
SYNC_FILE = "sync.json"  # data/sync.json: the list of digests, one per export (never the export itself)
SYNC_ACTIVE = {"active", "in progress", "in-progress", "inprogress", "ongoing", "started", "accepted"}
SYNC_DONE = {"completed", "complete", "done", "finished", "success", "succeeded", "resolved"}
SYNC_FAILED = {"failed", "fail", "abandoned"}
# a clause of a canon fact or trap that says someone is not in the crew (or is excluded)
SYNC_EXCLUDED_RE = re.compile(r"\b(?:not|never)\b[^.;]{0,40}?\b(?:in the (?:crew|party|group|gang)|joined|a member|crew member|part of the (?:crew|party))\b"
                              r"|\b(?:excluded|has not joined)\b", re.I)
SYNC_PLACE_KEYS = (("currentLocation", "currentArea"), ("location", "area"), ("locationName", "areaName"), ("loc", "area"))
SYNC_DEAD_STATUS = ("dead", "deceased", "killed")


def utc_now():
    return _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())


def _write_json_atomic(path, obj):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def sync_read_export(path):
    """(save dict, sha256 hex of the file, file name). Never prints or stores anything from the file."""
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as e:
        die(f"cannot read the export {p.name}: {e.strerror or e}", 2)
    try:
        save = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        die(f"the export {p.name} is not valid JSON", 2)
    if isinstance(save, dict) and len(save) == 1 and "engineState" not in save and isinstance(next(iter(save.values())), dict):
        save = next(iter(save.values()))  # one wrapper key, as import_world accepts
    if not isinstance(save, dict):
        die(f"the export {p.name} is not a Voyage state file (not a JSON object)", 2)
    return save, hashlib.sha256(raw).hexdigest(), p.name


def _sync_name(x, keys=("name", "properName", "key", "id", "label")):
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        for k in keys:
            if isinstance(x.get(k), str) and x[k].strip():
                return x[k].strip()
    return ""


def _sync_place_of(d, depth=0):
    """(location, area or None) from a save record, trying Voyage's usual field names; None when it names no place."""
    if not isinstance(d, dict) or depth > 2:
        return None
    for lk, ak in SYNC_PLACE_KEYS:
        loc = d.get(lk)
        if isinstance(loc, str) and loc.strip():
            ar = d.get(ak)
            return loc.strip(), (ar.strip() if isinstance(ar, str) and ar.strip() else None)
    for k in ("position", "currentPosition", "place", "where"):
        v = d.get(k)
        if isinstance(v, dict):
            r = _sync_place_of(v, depth + 1)
            if r:
                return r
        elif isinstance(v, str) and v.strip():
            loc, _, ar = v.partition("/")
            return loc.strip(), (ar.strip() or None)
    return None


def _sync_status_class(v):
    s = norm(v) if isinstance(v, str) else ""
    return "active" if s in SYNC_ACTIVE else "completed" if s in SYNC_DONE else "failed" if s in SYNC_FAILED else None


def sync_extract(save):
    """What the sync reads from a save (engineState.ticks, partyState.day / timeOfDay / partyMembers, the quest list, turnData)."""
    eng = save.get("engineState") if isinstance(save.get("engineState"), dict) else {}
    party = save.get("partyState") if isinstance(save.get("partyState"), dict) else {}
    td = save.get("turnData")
    ticks = {}
    for e in (td.values() if isinstance(td, dict) else td if isinstance(td, list) else []):
        if isinstance(e, dict) and _plain_int(e.get("tick")):
            ticks[e["tick"]] = e
    tick = eng.get("ticks") if _plain_int(eng.get("ticks")) else (max(ticks) if ticks else None)
    if tick is None:
        die("the export has no engineState.ticks: this does not look like a Voyage state file", 2)
    members, places = [], {}
    pm = party.get("partyMembers")
    for m in (pm.values() if isinstance(pm, dict) else pm if isinstance(pm, list) else []):
        n = _sync_name(m)
        if n and n not in members:
            members.append(n)
            p = _sync_place_of(m)
            if p:
                places[n] = p
    quests = {}  # normalized name -> (name, status class)
    for src in (save.get("quests"), party.get("quests")):
        its = src.items() if isinstance(src, dict) else (((None, x) for x in src) if isinstance(src, list) else ())
        for key, q in its:
            if not isinstance(q, dict):
                continue
            name = _sync_name(q, ("name", "title", "questName", "label")) or (key if isinstance(key, str) else "")
            cls = _sync_status_class(q.get("status") if q.get("status") is not None else q.get("state"))
            if name and cls:
                quests.setdefault(norm(name), (name, cls))
    return {"tick": tick, "day": party.get("day") if _plain_int(party.get("day")) else None,
            "tod": party.get("timeOfDay") if isinstance(party.get("timeOfDay"), str) and party["timeOfDay"].strip() else None,
            "members": members, "places": places, "party_place": _sync_place_of(party), "quests": quests, "ticks": ticks}


def _sync_find_place(loc, area):
    """(location key, area key or None, problem or None) for a place named by the save; never raises."""
    L = locations()
    key = {norm(k): k for k in L}.get(norm(loc))
    if not key:
        return None, None, f'location "{loc}" is not in locations.json'
    if not area:
        return key, None, None
    ak = {slug(x): x for x in L[key].get("areas", {})}.get(slug(area))
    if not ak:
        return key, None, f'area "{area}" is not in "{key}"'
    return key, ak, None


def _sync_clauses(text):
    return [c for c in re.split(r"[.;\n]+", str(text or "")) if c.strip()]


def _sync_tokens(*names):
    skip = {norm(t) for t in CFG.get("name_skip_tokens") or []} | STOP
    out = set()
    for n in names:
        for t in re.findall(r"[^\W\d_][\w'’\-]*", n or ""):
            if len(t) >= 4 and norm(t) not in skip:
                out.add(norm(t))
    return out


def sync_member_drift(name, key, entry):
    """Class 2 for one party member: what a canon trap or canon fact (or the cast record) says cannot be true of them.
    [(why, source)]. Heuristics: a clause that names them and says not in the crew / excluded / not them; a name followed by
    'is dead' or 'died'; a cast or world record whose status is dead."""
    toks = _sync_tokens(name, key)
    out = []
    if not toks:
        return out
    full = norm(name)
    sources = [("trap", None, tr.get("text")) for tr in CFG.get("canon_traps") or [] if isinstance(tr, dict)]
    sources += [("fact", f.get("id"), f.get("fact")) for f in S.get("canon").get("facts", []) if isinstance(f, dict)]
    for kind, fid, text in sources:
        for cl in _sync_clauses(text):
            n = norm(cl)
            if not any(re.search(r"\b" + re.escape(t) + r"\b", n) for t in toks):
                continue
            src = f'canon trap "{short(cl, 70)}"' if kind == "trap" else f"canon fact {fid}"
            if SYNC_EXCLUDED_RE.search(cl):
                out.append(("are not in the crew (or are excluded)", src))
            elif re.search(r"\bnot (?:the )?" + re.escape(full) + r"\b", n):
                out.append(("are named as someone else", src))
            elif any(re.search(r"\b" + re.escape(t) + r"\b[\w\s'\-]{0,30}?\b(?:(?:is|was|are) (?:dead|deceased)|died)\b", n) for t in toks):
                out.append(("are dead", src))
    if isinstance(entry, dict) and norm(entry.get("status") or "") in SYNC_DEAD_STATUS:
        out.append(("are dead", f"the {entry.get('status')} cast record"))
    grouped = {}  # one drift item per reason, with every source that gives it
    for why, src in out:
        if src not in grouped.setdefault(why, []):
            grouped[why].append(src)
    return [(why, srcs[:3]) for why, srcs in grouped.items()]


def sync_plan(ex, sha, fname):
    """Compare the export with the database. Reads only; returns the report as data."""
    st = S.get("state")
    turns = S.get("turns")
    blocks = S.get("world")["time"]["blocks"]
    live = [t for t in turns if isinstance(t, dict) and not t.get("undone")]
    S_turn, T = st["turn"], ex["tick"]
    p = {"tick": T, "state_turn": S_turn, "sha": sha, "file": fname, "live_turns": len(live),
         "import": [], "import_missing": [], "undone": [], "pos": [], "time": None, "quests": [], "party": [],
         "drift": [], "confirm": [], "cmds": [], "digest_quests": {}, "digest_pos": {}, "pos_confirm": [], "time_confirm": False,
         "pos_cmp": [], "save_unmatched": [], "db_unmatched": [], "db_pcs": []}
    if T > S_turn:
        p["import"] = list(range(S_turn + 1, T + 1))
        p["import_missing"] = [t for t in p["import"] if t not in ex["ticks"]]
    elif T < S_turn:
        p["undone"] = [t["turn"] for t in live if _plain_int(t.get("turn")) and t["turn"] > T]
    ev = f'sync: Voyage export {fname} (sha256 {sha[:12]}), tick {T}'
    p["evidence"] = ev
    base = f"python3 tools/db.py --campaign {CAMPAIGN}"
    q = lambda s: shlex.quote(str(s))

    # ---- class 1: PC positions ----
    idx = NameIndex()
    members_pc = {}
    for m in ex["members"]:
        keys, _ = idx.resolve(m)
        if len(keys) == 1 and idx.is_pc(keys[0]):
            members_pc[keys[0]] = m
    for pc in st["player_characters"]:
        sp = ex["places"].get(members_pc.get(pc["name"], "")) or ex["party_place"]
        if not sp:
            continue
        loc, area, problem = _sync_find_place(*sp)
        p["pos_cmp"].append((pc["name"], f'{pc.get("location")}/{pc.get("area")}', f"{sp[0]}/{sp[1]}" if sp[1] else sp[0]))
        p["digest_pos"][pc["name"]] = f"{sp[0]}/{sp[1]}" if sp[1] else sp[0]
        if problem:
            p["drift"].append({"what": f"{pc['name']} is at {sp[0]}" + (f"/{sp[1]}" if sp[1] else "") + f" in Voyage, but {problem}",
                               "src": "the location data", "advice": "new-trap candidate or a Studio import: the database never invents a place"})
            continue
        old = f'{pc.get("location")}/{pc.get("area")}'
        same = norm(pc.get("location") or "") == norm(loc) and (area is None or slug(pc.get("area") or "") == slug(area))
        if same:
            if pc.get("inferred"):
                p["pos_confirm"].append(pc["name"])
                p["confirm"].append(f'position of {pc["name"]} ({old}) from turn quote "{short(pc.get("quote") or "", 50)}"')
            continue
        new = f"{loc}/{area}" if area else loc
        p["pos"].append({"pc": pc["name"], "old": old, "new": new, "loc": loc, "area": area})
        if area:
            p["cmds"].append(f'{base} pos {q(pc["name"])} {q(loc)} {q(area)} --turn {T} --evidence {q(ev)}')

    # ---- class 1: day and time of day ----
    if ex["day"] is not None and ex["tod"]:
        blk = {norm(b["name"]): b["name"] for b in blocks}.get(norm(ex["tod"]))
        if not blk:
            p["drift"].append({"what": f'Voyage time of day "{ex["tod"]}" is not a time block of this world',
                               "src": "world.json time blocks", "advice": "new-trap candidate; check the block names"})
        else:
            now = (st["day"], st["time_block"])
            if now != (ex["day"], blk):
                p["time"] = {"old": f'Day {now[0]} {now[1]}', "new": f'Day {ex["day"]} {blk}', "day": ex["day"], "block": blk}
                p["cmds"].append(f'{base} time --day {ex["day"]} --block {q(blk)} --allow-backward --turn {T} --evidence {q(ev)}')
            elif st.get("time_inferred"):
                p["time_confirm"] = True
                p["confirm"].append(f'time (Day {ex["day"]} {blk}) from quote "{short(st.get("time_quote") or "", 50)}"')

    # ---- class 1: quest status ----
    matched_save = set()
    for key, qq in S.get("quests").items():
        hk = norm(key) if norm(key) in ex["quests"] else norm(qq.get("name") or key)
        hit = ex["quests"].get(hk)
        if not hit:
            p["db_unmatched"].append(key)
            continue
        matched_save.add(hk)
        sv = hit[1]
        p["digest_quests"][key] = sv
        db, ae = qq.get("status"), qq.get("apparent_end")
        ev_c = f'--turn {T} --evidence {q(ev)}'
        if db == sv:
            if sv == "active" and ae:
                p["quests"].append({"key": key, "kind": "contradicted", "db": db, "save": sv,
                                    "text": f'"{key}": apparent end noted at turn {ae.get("turn")}, but Voyage still has it active'})
            elif qq.get("inferred") or ae:
                p["confirm"].append(f'quest "{key}" is {sv}' + (" (inferred start)" if qq.get("inferred") else "")
                                    + (f' (apparent end t{ae.get("turn")})' if ae else ""))
            continue
        if db == "planned" and sv == "active":
            p["quests"].append({"key": key, "kind": "start", "db": db, "save": sv, "text": f'"{key}": database planned, Voyage active'})
            p["cmds"].append(f'{base} quest-start {q(key)} {ev_c}')
        elif db == "planned" and sv in ("completed", "failed"):
            p["quests"].append({"key": key, "kind": "start_end", "db": db, "save": sv, "text": f'"{key}": database planned, Voyage {sv}'})
            p["cmds"] += [f'{base} quest-start {q(key)} {ev_c}', f'{base} quest-end {q(key)} {sv} {ev_c}']
        elif db == "active" and sv in ("completed", "failed"):
            p["quests"].append({"key": key, "kind": "end", "db": db, "save": sv, "text": f'"{key}": database active, Voyage {sv}'
                                + (f' (confirms the apparent end at t{ae.get("turn")})' if ae else "")})
            p["cmds"].append(f'{base} quest-end {q(key)} {sv} {ev_c}')
            if ae:
                p["confirm"].append(f'quest "{key}" apparent end (t{ae.get("turn")}, "{short(ae.get("quote") or "", 50)}") is confirmed: Voyage has it {sv}')
        else:
            p["quests"].append({"key": key, "kind": "review", "db": db, "save": sv,
                                "text": f'"{key}": database {db}, Voyage {sv} (no automatic patch: check by hand)'})

    p["save_unmatched"] = [v[0] for k, v in ex["quests"].items() if k not in matched_save]

    # ---- class 1: party (and class 2: party members the canon says cannot be there) ----
    pc_names = [pc["name"] for pc in st["player_characters"]]
    p["db_pcs"] = list(pc_names)
    in_party_pcs = set()
    for m in ex["members"]:
        keys, _ = idx.resolve(m)
        key = keys[0] if len(keys) == 1 else None
        entry = None if key is None else (cast().get(key) or world_npcs().get(key))
        drift = sync_member_drift(m, key, entry)
        if drift:
            for why, srcs in drift:
                p["drift"].append({"what": f"Voyage's party lists {m}, but {' and '.join(srcs)} say{'s' if len(srcs) == 1 else ''} they {why}",
                                   "src": srcs,
                                   "advice": "Studio-fix candidate" + (" (the trap exists; add a new one only if it keeps coming back)"
                                                                         if any(s.startswith("canon trap") for s in srcs) else "; a new trap if it recurs")})
            continue
        if key and idx.is_pc(key):
            in_party_pcs.add(key)
        elif len(keys) > 1:
            p["party"].append({"text": f'party member "{m}" matches several people ({", ".join(keys[:4])}): no automatic patch', "cmd": None})
        elif key is None:
            p["party"].append({"text": f'party member "{m}" is not in the database', "kind": "add", "name": m})
            p["cmds"].append(f'{base} add-npc {q(m)} --turn {T} --evidence {q(ev)}')
        elif entry.get("status") != "in_play":
            p["party"].append({"text": f'party member "{key}" is {entry.get("status")} in the database, in the party in Voyage', "kind": "seen", "name": key})
            p["cmds"].append(f'{base} npc-seen {q(key)} --turn {T} --evidence {q(ev)}')
    for n in pc_names:
        if n not in in_party_pcs and ex["members"]:
            p["party"].append({"text": f'player character "{n}" is not in Voyage\'s party list: no automatic patch (ask the user)', "kind": None})
    return p


def sync_counts(p):
    return {"position": len(p["pos"]), "time": 1 if p["time"] else 0,
            "quest": len(p["quests"]), "party": len(p["party"]), "drift": len(p["drift"])}


def sync_print(p, ex, apply):
    T, S_turn = p["tick"], p["state_turn"]
    print(f"sync {'--apply' if apply else '(dry run)'} of {p['file']}")
    print(f"export: sha256 {p['sha']}")
    print(f"export state: tick {T}; Day {ex['day'] if ex['day'] is not None else '?'} {ex['tod'] or '?'}; party {len(ex['members'])}; "
          f"positions found {len(p['digest_pos'])}; quests matched {len(p['digest_quests'])} of {len(ex['quests'])} in the save")
    print("  compared, position (database vs save): "
          + ("; ".join(f"{short(n, 24)} {short(o, 40)} vs {short(v, 40)}" for n, o, v in p["pos_cmp"][:6])
             + more_text(len(p["pos_cmp"]) - 6) if p["pos_cmp"] else "none (the save gives no place for any player character)"))
    print(f"  compared, party (database vs save): database player characters {len(p['db_pcs'])} ({short(', '.join(p['db_pcs']), 70)}); "
          f"save party {len(ex['members'])} ({short(', '.join(ex['members']), 70)})")
    for label, names in (("save quests with no database match", p["save_unmatched"]),
                         ("database quests with no save match", p["db_unmatched"])):
        print(f"  {label} ({len(names)}): " + ("; ".join(short(n, 60) for n in names[:12]) + more_text(len(names) - 12) if names else "none"))
    print("TICKS")
    cov = sorted(ex["ticks"])
    print(f"  Voyage tick {T}; the database is at turn {S_turn} ({p['live_turns']} director turn(s) logged)"
          + (f"; the save has turnData for ticks {cov[0]} to {cov[-1]} ({len(cov)})" if cov else ""))
    if p["import"]:
        a, b = p["import"][0], p["import"][-1]
        print(f"  ticks played without the director: {a} to {b} ({len(p['import'])}); --apply imports them into turns.json "
              "(inputs and a summary from the save, marked imported)"
              + (f"; no turnData for tick(s) {', '.join(map(str, p['import_missing']))}: they import empty" if p["import_missing"] else ""))
    elif p["undone"]:
        print(f"  director turns Voyage no longer has: {p['undone'][0]} to {p['undone'][-1]} ({len(p['undone'])}); --apply marks them "
              f"undone: true in turns.json (never deleted) and sets state.turn to {T}")
    else:
        print("  the ticks agree: nothing to import and no turn to mark undone")
    if not p["undone"]:
        print("  undone director turns: none")
    print("CLASS 1, Voyage-owned state (the only class --apply changes)")
    n1 = 0
    for x in p["pos"]:
        print(f"  position: {x['pc']}: database {x['old']}, Voyage {x['new']}"
              + ("" if x["area"] else " (the save gives no area: no automatic patch, set it by hand)"))
        n1 += 1
    if p["time"]:
        print(f"  time: database {p['time']['old']}, Voyage {p['time']['new']}")
        n1 += 1
    for x in p["quests"]:
        print(f"  quest: {x['text']}")
        n1 += 1
    for x in p["party"]:
        print(f"  party: {x['text']}")
        n1 += 1
    if not n1:
        print("  none: position, time, quest status and party agree with Voyage")
    if p["cmds"]:
        print("  proposed patch (run in this order after the tick import; --apply does exactly this):")
        for c in p["cmds"]:
            print("    " + c)
    print("  would confirm (inferred records the export confirms; --apply clears their inferred flag):" if p["confirm"]
          else "  would confirm: nothing")
    for c in p["confirm"]:
        print("    " + c)
    print("CLASS 2, Voyage drift (never applied)")
    if p["drift"]:
        for x in p["drift"]:
            print(f"  drift: {x['what']} -> {x['advice']}")
    else:
        print("  none: nothing in the export conflicts with a canon fact or a canon trap")
    print("CLASS 3, director layer: cast bibles, ladders, traps, promises and arc plans were left untouched.")
    c = sync_counts(p)
    print("MISMATCHES BY TYPE: " + ", ".join(f"{k} {v}" for k, v in c.items()))


def sync_summary_text(text, limit=400):
    s = re.sub(r"\s+", " ", text or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    ends = list(re.finditer(r"[.!?…][\"'”’)]*(?=\s|$)", cut))
    return cut[:ends[-1].end()].strip() if ends else cut[:limit - 3].rstrip() + "..."


def _sync_story(v, depth=0):
    if isinstance(v, str):
        return v.strip()
    if depth > 3:
        return ""
    if isinstance(v, dict):
        for k in ("tier1", "tier-1", "tier_1", "summary", "text", "story", "content", "narration"):
            if k in v:
                t = _sync_story(v[k], depth + 1)
                if t:
                    return t
        for x in v.values():
            t = _sync_story(x, depth + 1)
            if t:
                return t
        return ""
    if isinstance(v, list):
        return " ".join(t for t in (_sync_story(x, depth + 1) for x in v) if t)
    return ""


def sync_import_entry(tick, e):
    """A turns.json entry for a tick played without the director: inputs per player and the __dm__ prompt from the save's
    turnData, a summary cut from its story text. Day and time are unknown ('?') except where the caller knows them."""
    pi = e.get("playerInputs") if isinstance(e, dict) and isinstance(e.get("playerInputs"), dict) else {}
    def one_line(v):
        return re.sub(r"[ \t]*[\r\n]+[ \t]*", " ", str(v)).strip()
    inputs = " | ".join(f"{k}: {one_line(v)}" for k, v in pi.items() if k != "__dm__" and str(v).strip())
    prompt = str(pi.get("__dm__") or "").strip()
    story = ""
    if isinstance(e, dict):
        for k in ("stories", "story", "summary"):
            if k in e:
                story = _sync_story(e[k])
                if story:
                    break
    summary = sync_summary_text(story) or "(Voyage's save has no story text for this tick)"
    return {"turn": tick, "day": "?", "time": "", "inputs": inputs, "summary": summary, "prompt": prompt, "slips": "",
            "notes": "imported from Voyage's export by sync", "imported": True}


def sync_record(p, applied):
    """Write the digest (data/sync.json) and the state.sync_log entry. These are the only writes of a dry run."""
    st = S.get("state")
    now = utc_now()
    path = DATA / SYNC_FILE
    digests = []
    if path.exists():
        try:
            digests = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            die(f"{path.name} is not valid JSON: fix or remove it", 1)
        if not isinstance(digests, list):
            die(f"{path.name} must be a list of digests", 1)
    old = next((d for d in digests if isinstance(d, dict) and d.get("sha256") == p["sha"]), None)
    log = st.setdefault("sync_log", [])
    entry = {"turn": p["state_turn"], "at": now, "tick": p["tick"], "mismatches": sync_counts(p), "applied": bool(applied)}
    at = None
    if applied and old:  # --apply after the dry run of the same export: that dry run's log entry becomes the applied one
        at = next((i for i in range(len(log) - 1, -1, -1) if isinstance(log[i], dict) and log[i].get("at") == old.get("log_at")
                   and not log[i].get("applied")), None)
    if at is None:
        log.append(entry)
    else:
        log[at] = entry
    ex = p["ex"]
    digest = {"file": p["file"], "sha256": p["sha"], "date": now[:10], "at": now, "log_at": now, "tick": p["tick"],
              "state_turn": p["state_turn"], "day": ex["day"], "time_block": ex["tod"], "party": list(ex["members"]),
              "positions": dict(p["digest_pos"]), "quests": dict(p["digest_quests"]), "quests_in_save": len(ex["quests"])}
    digests = [digest if d is old else d for d in digests] if old else digests + [digest]
    _write_json_atomic(path, digests)
    _write_json_atomic(DATA / "state.json", st)
    return entry


def sync_apply(p, ex):
    """Apply class 1 (plus the tick import and the undone marks) under the lock the caller holds. One snapshot first."""
    T, S_turn, ev = p["tick"], p["state_turn"], p["evidence"]
    n = S_turn + 1  # the snapshot `undo-turn N` restores: the data as it stood after turn N-1, before this sync
    take_snapshot(n)
    done = []
    try:
        S.reset()
        st, turns = S.get("state"), S.get("turns")
        changed = []
        if p["import"]:
            for t in p["import"]:
                turns.append(sync_import_entry(t, ex["ticks"].get(t)))
            st["turn"] = T
            S.touch("turns")
            S.touch("state")
            changed.append(f"imported {len(p['import'])} tick(s) {p['import'][0]} to {p['import'][-1]} into turns.json")
        elif p["undone"]:
            for t in turns:
                if isinstance(t, dict) and _plain_int(t.get("turn")) and t["turn"] > T and not t.get("undone"):
                    t["undone"] = True
            st["turn"] = T
            S.touch("turns")
            S.touch("state")
            changed.append(f"marked {len(p['undone'])} director turn(s) {p['undone'][0]} to {p['undone'][-1]} undone (kept in turns.json); state.turn is now {T}")
        if changed:
            S.commit("sync", T, ev, "; ".join(changed))
        ns = argparse.Namespace
        for x in (x for x in p["pos"] if x["area"]):
            cmd_pos(ns(pc=x["pc"], location=x["loc"], area=x["area"], activity=None, placement=None, inferred=False, turn=T, evidence=ev))
            done.append(f"position {x['pc']} -> {x['new']}")
        if p["time"]:
            t_ = p["time"]
            old_day = st["day"]
            cmd_time(ns(day=t_["day"] if t_["day"] != old_day else None, block=t_["block"], clock=None, allow_backward=True,
                        inferred=False, turn=T, evidence=ev))
            done.append(f"time -> {t_['new']}")
        for x in p["quests"]:
            if x["kind"] in ("start", "start_end"):
                cmd_quest_start(ns(name=x["key"], inferred=False, turn=T, evidence=ev))
            if x["kind"] in ("end", "start_end"):
                cmd_quest_end(ns(name=x["key"], result=x["save"], inferred=False, turn=T, evidence=ev))
            if x["kind"] not in ("review", "contradicted"):
                done.append(f'quest "{x["key"]}" -> {x["save"]}')
        for x in p["party"]:
            if x.get("kind") == "seen":
                cmd_npc_seen(ns(name=x["name"], turn=T, evidence=ev))
                done.append(f'party member "{x["name"]}" -> in_play')
            elif x.get("kind") == "add":
                cmd_add_npc(ns(name=x["name"], alias=None, age=None, gender=None, power=None, visual=None, personality=None,
                               type=None, faction=None, location=None, area=None, turn=T, evidence=ev))
                done.append(f'party member "{x["name"]}" added (voyage-generated, in_play)')
        # confirm and clear: inferred flags and apparent-end notes the export settles
        cleared = []
        for pc in st["player_characters"]:
            if pc.get("inferred") and pc["name"] in p["pos_confirm"]:
                pc.pop("inferred", None)
                pc.pop("quote", None)
                cleared.append(f"position of {pc['name']}")
        if st.get("time_inferred") and p["time_confirm"]:
            st.pop("time_inferred", None)
            st.pop("time_quote", None)
            cleared.append("time")
        quests = S.get("quests")
        for key, sv in p["digest_quests"].items():
            qq = quests[key]
            if qq.get("status") != sv:
                continue
            if qq.get("inferred"):
                qq.pop("inferred", None)
                qq.pop("quote", None)
                cleared.append(f'quest "{key}" start')
            ae = qq.get("apparent_end")
            if ae:
                qq.pop("apparent_end", None)
                qq.setdefault("log", []).append({"turn": T, "event": "apparent end " + ("confirmed" if sv != "active" else "contradicted")
                                                 + " by Voyage's export", "evidence": ev})
                cleared.append(f'quest "{key}" apparent end ({"confirmed" if sv != "active" else "contradicted"})')
                S.touch("quests")
        if cleared:
            S.touch("state")
            S.touch("quests")
            S.commit("sync", T, ev, "confirmed or corrected (inferred cleared): " + "; ".join(cleared))
            done.append("cleared inferred: " + ", ".join(cleared))
        if p["import"] and ex["day"] is not None and turns and turns[-1].get("turn") == T and turns[-1].get("imported"):
            turns[-1]["day"], turns[-1]["time"] = st["day"], f'{st["time_block"]} {st["clock"]}'  # the export's own day and block, for its last tick
            S.touch("turns")
            S.touch("state")
            S.commit("sync", T, ev, f"tick {T} dated from the export (Day {st['day']} {st['time_block']})")
        bad = verify_data(T)
        if bad:
            raise DbError("verification failed: " + "; ".join(bad))
    except BaseException as e:  # noqa: BLE001 - restore on ANY error, including Ctrl-C
        restore_snapshot(snap_dir(n))
        shutil.rmtree(snap_dir(n), ignore_errors=True)
        if isinstance(e, DbError):
            raise DbError(f"{e.msg.rstrip('.')}. Restored the pre-sync snapshot; nothing applied.", e.code)
        raise
    S.reset()
    return done, changed, n


def cmd_sync(a):
    if a.apply and trial_run():
        die("sync --apply refused: this is a trial run (VOYAGE_TRIAL=1 / CLASS2B_TRIAL=1). A dry run on a VOYAGE_DATA copy is allowed.", EXIT_REFUSED)
    if trial_run() and not data_override():
        die("sync refused: this is a trial run and VOYAGE_DATA / CLASS2B_DATA does not point at a copy; the dry run writes a digest "
            "into the real data. Run it on a VOYAGE_DATA copy.", EXIT_REFUSED)
    save, sha, fname = sync_read_export(a.export)
    ex = sync_extract(save)
    del save
    S.reset()
    s0, T = S.get("state")["turn"], ex["tick"]
    n = s0 + 1
    with write_lock("sync-apply" if a.apply else "sync", n if a.apply else s0):
        S.reset()
        p = sync_plan(ex, sha, fname)
        p["ex"] = ex
        sync_print(p, ex, a.apply)
        if not a.apply:
            sync_record(p, False)
            print(f"dry run: wrote {SYNC_FILE} (the digest) and one state.sync_log entry; nothing else changed. "
                  "The raw export is not copied anywhere: keep it out of git (campaigns/*/exports/ is ignored).")
            return
        done, changed, snap = sync_apply(p, ex)
        entry = sync_record(p, True)
        print("APPLIED (class 1 only; classes 2 and 3 untouched)")
        for line in changed + done:
            print("  " + line)
        if not (changed or done):
            print("  nothing to change: the database already agrees with Voyage")
        print(f"  state.sync_log: applied true (tick {entry['tick']}); digest in {SYNC_FILE}; snapshot before-turn-{snap} kept: "
              f"`undo-turn {snap}` rewinds this sync")
        print("  Run `db.py save` (or wrap-up) to commit data/, including sync.json.")


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
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 1 else 1  # SAVE-1: push every turn unless a campaign says otherwise


FETCH_TIMEOUT = 20  # seconds the commit-turn tail waits for `git fetch origin main` (off the clock)


def planner_fetch(root, timeout=None):
    """`git fetch origin main` in root with a timeout, so origin/main shows what the planner pushed (SES-2). None when it worked,
    else a short reason. Only commit-turn's tail calls it: nothing on the clock touches the network."""
    timeout = timeout or FETCH_TIMEOUT
    try:
        r = subprocess.run(["git", "fetch", "origin", "main"], cwd=root, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        return f"timed out after {timeout} s"
    except OSError as e:
        return short(str(e), 100)
    if r.returncode == 0:
        return None
    lines = (r.stderr or r.stdout).strip().splitlines()
    return short(lines[-1] if lines else f"git exited {r.returncode}", 100)


# ----------------------------------------------------------------------------
# planner output (campaigns/NAME/planner/), the session roles' channel (SES-2, SES-4)
# ----------------------------------------------------------------------------
PLANNER_KINDS = (("card-", "card ready"), ("pivot-", "pivot draft ready"), ("offramps-", "off-ramps ready"), ("arc-", "arc plan ready"),
                 ("review-", "review ready"), ("audit-", "audit ready"), ("retro-", "retro draft ready"), ("recap-", "recap ready"),
                 ("studio-", "Studio draft ready"))  # file name prefix -> how the brief names it; anything else is a "note"
PLANNER_NOTE = "note"
PLANNER_SHOWN = 3  # files named per kind in the brief line


def planner_kind(fname):
    return next((label for pre, label in PLANNER_KINDS if fname.startswith(pre)), PLANNER_NOTE)


def planner_dir(name):
    return f"campaigns/{name}/planner"


def git_text(args, cwd=None):
    """stdout of a local git command (UTF-8), None when git is missing or the command fails. Never used for the network."""
    try:
        r = subprocess.run(["git"] + args, cwd=cwd or ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def planner_view(name):
    """(ref, [(file name, blob hash)]) of the planner folder in the newest local view of origin/main (HEAD when there is no such
    ref), by local git only; README.md is ignored. None when git cannot say (no git, no repository, no commit)."""
    ref = "origin/main" if (git_text(["rev-parse", "--verify", "-q", "origin/main"]) or "").strip() else "HEAD"
    out = git_text(["ls-tree", "-z", ref, "--", planner_dir(name) + "/"])
    if out is None:
        return None
    files = []
    for ent in out.split("\0"):
        meta, _, path = ent.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            fname = path.rsplit("/", 1)[-1]
            if fname.lower() != "readme.md":
                files.append((fname, parts[2]))
    return ref, sorted(files)


def state_file(name):
    """The parsed state.json of a campaign by name ({} when it cannot be read); no campaign needs to be selected."""
    try:
        d = json.loads((Path(data_override() or ROOT / "campaigns" / name / "data") / "state.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def planner_items(name, st=None):
    """(ref, [{file, blob, label, applied}]) for the planner folder, or None when git cannot say. A file is applied when
    state.planner_applied holds its name with its current blob hash; an edited file has a new hash and waits again."""
    view = planner_view(name)
    if view is None:
        return None
    st = st if isinstance(st, dict) else state_file(name)
    done = {(e.get("file"), e.get("blob")) for e in st.get("planner_applied") or [] if isinstance(e, dict)}
    return view[0], [{"file": f, "blob": b, "label": planner_kind(f), "applied": (f, b) in done} for f, b in view[1]]


def planner_brief_line(name=None, st=None):
    """The brief's planner line, or None (nothing waiting, no planner folder, no git): SES-2."""
    items = planner_items(name or CAMPAIGN, st if st is not None else S.get("state"))
    waiting = [i for i in items[1] if not i["applied"]] if items else []
    if not waiting:
        return None
    parts = []
    for label in [k for _, k in PLANNER_KINDS] + [PLANNER_NOTE]:
        names = [i["file"] for i in waiting if i["label"] == label]
        if names:
            parts.append(f"{label} (" + ", ".join(names[:PLANNER_SHOWN]) + (f", +{len(names) - PLANNER_SHOWN} more" if len(names) > PLANNER_SHOWN else "") + ")")
    return "planner: " + "; ".join(parts) + ". Apply at a break, then db.py planner-done FILE"


def planner_name(arg, name):
    """A planner file as the user typed it (its name, or its path under the repo or the planner folder) -> its name in the folder."""
    x = str(arg).strip().replace("\\", "/")
    for pre in (planner_dir(name) + "/", "planner/"):
        if x.startswith(pre):
            x = x[len(pre):]
    return x


def planner_first_line(blob):
    text = git_text(["cat-file", "blob", blob]) or ""
    for ln in text.splitlines():
        ln = ln.strip().lstrip("#").strip()
        if ln:
            return short(ln, 90)
    return "(empty)"


def cmd_planner(a):
    """Read-only: the planner's files waiting for the director (kind, name, first line); --all adds the applied ones; --show prints one."""
    items = planner_items(CAMPAIGN, S.get("state"))
    if items is None:
        print("Planner output: not available (no git history here).")
        return
    ref, files = items
    if a.show:
        want = planner_name(a.show, CAMPAIGN)
        hit = next((i for i in files if i["file"] == want), None)
        if not hit:
            die(f"no planner file '{a.show}' in {planner_dir(CAMPAIGN)}/ on {ref} ("
                + (", ".join(i["file"] for i in files) or "the folder is empty or missing") + ")", 2)
        text = git_text(["cat-file", "blob", hit["blob"]])
        print(text if text is not None else "", end="" if text and text.endswith("\n") else "\n")
        return
    waiting = [i for i in files if not i["applied"]]
    print(f"Planner output on {ref}: " + (f"{len(waiting)} waiting" if waiting else "nothing waiting") + f" ({planner_dir(CAMPAIGN)}/)")
    for i in waiting:
        print(f"  {i['label']}: {i['file']}: {planner_first_line(i['blob'])}")
    if a.all:
        rec = {(e.get("file"), e.get("blob")): e for e in S.get("state").get("planner_applied") or [] if isinstance(e, dict)}
        for i in files:
            if i["applied"]:
                e = rec[(i["file"], i["blob"])]
                print(f"  applied (turn {e.get('turn')}): {i['file']}: {planner_first_line(i['blob'])}" + (f" [{short(e['note'], 60)}]" if e.get("note") else ""))
    if not files:
        print("  (no files: the planner writes here, then runs `db.py planner-save`)")


def cmd_planner_done(a):
    """Director: mark planner files applied (state.planner_applied gets {file, blob, turn, at, note}); an edited file waits again."""
    st = S.get("state")
    items = planner_items(CAMPAIGN, st)
    if items is None:
        die("cannot read the planner output: git has no history here")
    ref, files = items
    byname = {i["file"]: i for i in files}
    picked = []
    for f in a.files:
        n = planner_name(f, CAMPAIGN)
        if n not in byname:
            die(f"no planner file '{f}' in {planner_dir(CAMPAIGN)}/ on {ref} (db.py planner lists them). Nothing was changed.", 2)
        if n not in [p["file"] for p in picked]:
            picked.append(byname[n])
    new = [i for i in picked if not i["applied"]]
    for i in picked:
        if i["applied"]:
            print(f"  {i['file']}: already applied, skipped")
    if not new:
        return
    at = now_iso()
    st.setdefault("planner_applied", []).extend({"file": i["file"], "blob": i["blob"], "turn": st["turn"], "at": at, "note": a.note or ""} for i in new)
    S.touch("state")
    S.commit("planner-done", st["turn"], a.note or "director applied the planner output",
             "planner output applied: " + ", ".join(i["file"] for i in new))


def cmd_planner_save(a):
    """Planner or all-in-one session: commit only campaigns/NAME/planner/ and push main (retry and rebase as `save` does)."""
    if trial_run():
        die("planner-save refused: this is a trial run (VOYAGE_TRIAL=1 / CLASS2B_TRIAL=1). Trial runs write nothing.", EXIT_REFUSED)
    if data_override():
        die("planner-save refused: VOYAGE_DATA / CLASS2B_DATA points at a copy, not the real data/ directory.", EXIT_REFUSED)
    if current_role() == "director":
        die("planner-save refused: this session is the director; the planner session (or an all-in-one session) saves planner files.", EXIT_REFUSED)
    rel = planner_dir(CAMPAIGN)
    if not (ROOT / rel).is_dir():
        die(f"nothing to save: {rel}/ does not exist yet. Write the planner's files there first.", 2)
    root = Path(run_git(["rev-parse", "--show-toplevel"], ROOT).stdout.strip())
    branch = git_branch(root)
    if branch != "main":
        die(f"planner-save refused: on branch {branch!r}, not main. All commits go to main only (nothing was committed or pushed). "
            "Run `git fetch origin main && git checkout -B main origin/main`, then rerun.", EXIT_BRANCH)
    msg = a.message or f"{display()} planner output"
    if a.dry_run:
        print(f"dry run: would commit {rel}/ on {branch} as \"{msg}\" and push with up to {a.retries} tries")
        return
    run_git(["add", "-A", "--", rel], root)
    if run_git(["diff", "--cached", "--quiet", "--", rel], root, check=False).returncode == 0:
        print(f"nothing new to commit in {rel}/")
    else:
        run_git(["commit", "-m", msg, "--", rel], root)
        print(f"committed: {msg}")
    i = push_main(root, a.retries)
    print(f"pushed main (attempt {i})")


# ----------------------------------------------------------------------------
# timing (SES-9): DATA/.turn-clock holds, per coming turn, when check-prompt first ran and when turn-brief --full ran
# ----------------------------------------------------------------------------
def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def clock_path():
    return DATA / ".turn-clock"  # no .json extension on purpose: no JSON glob or check picks it up; .gitignore keeps it out of git


def clock_read():
    try:
        d = json.loads(clock_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def clock_write(d):
    p = clock_path()
    try:
        if not d:
            p.unlink(missing_ok=True)
            return
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass  # the clock is a measuring aid: never stop play for it


def clock_note(key):
    """Record the time `key` (checked | full_at) first happened for the coming turn (state.turn + 1); later runs keep the first time.
    Nothing is written in a trial run."""
    if trial_run() or not DATA.is_dir():
        return
    try:
        nxt = S.get("state")["turn"] + 1
    except (DbError, KeyError, TypeError):
        return
    d = {k: v for k, v in clock_read().items() if str(k).isdigit() and int(k) >= nxt and isinstance(v, dict)}  # drop turns already committed
    ent = d.setdefault(str(nxt), {})
    if key not in ent:
        ent[key] = now_iso()
    clock_write(d)


CLOCK_FRESH_MINUTES = 60  # a clock time more than this long before the commit (or after it) belongs to some other moment: commit-turn ignores it


def clock_fresh(stamp, now):
    """True when the clock time `stamp` (ISO 8601) lies at most CLOCK_FRESH_MINUTES before `now` (a datetime) and not after it."""
    try:
        t = datetime.datetime.fromisoformat(str(stamp)).astimezone()
    except ValueError:
        return False
    return datetime.timedelta(0) <= now - t <= datetime.timedelta(minutes=CLOCK_FRESH_MINUTES)


def clock_clear(turn):
    d = {k: v for k, v in clock_read().items() if str(k).isdigit() and int(k) > turn}
    if d != clock_read():
        clock_write(d)


def parse_received(text):
    """--received TIME: ISO 8601 (no zone = local time), or HH:MM / HH:MM:SS meaning today in local time. -> ISO string with offset."""
    s = str(text).strip()
    try:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
        if m:
            dt = datetime.datetime.now().astimezone().replace(hour=int(m.group(1)), minute=int(m.group(2)), second=int(m.group(3) or 0), microsecond=0)
        else:
            dt = datetime.datetime.fromisoformat(s).astimezone()
    except ValueError:
        die(f"--received '{text}' is not a time: give ISO 8601 (2026-10-05T14:03:00) or HH:MM or HH:MM:SS (today, local time)", 2)
    return dt.isoformat(timespec="seconds")


def timing_problems(turns):
    """Problems with the optional turn_log timing of each turn: {received: ISO or null, checked: ISO or null, committed: ISO,
    escalated: true or false}. Turns without it are valid."""
    bad = []
    for t in turns:
        tm = t.get("timing") if isinstance(t, dict) else None
        if tm is None:
            continue
        where = f"turns.json turn {t.get('turn')} timing"
        if not isinstance(tm, dict):
            bad.append(f"{where}: must be an object")
            continue
        for k in ("received", "checked", "committed"):
            v = tm.get(k)
            try:
                if v is not None:
                    datetime.datetime.fromisoformat(v)
                elif k == "committed":
                    raise ValueError
            except (ValueError, TypeError):
                bad.append(f"{where}: {k} must be an ISO 8601 time" + ("" if k == "committed" else " or null"))
        if not isinstance(tm.get("escalated"), bool):
            bad.append(f"{where}: escalated must be true or false")
    return bad


def planner_problems(st):
    """Problems with the optional state.planner_applied list ({file, blob, turn, at, note}); state files without it are valid."""
    v = st.get("planner_applied", [])
    if not isinstance(v, list):
        return ["state.json planner_applied must be a list"]
    bad = []
    for i, e in enumerate(v, 1):
        where = f"state.json planner_applied #{i}"
        if not isinstance(e, dict):
            bad.append(f"{where}: must be an object")
            continue
        for k in ("file", "blob"):
            if not (isinstance(e.get(k), str) and e[k].strip()):
                bad.append(f"{where}: {k} must be non-empty text")
        if not _plain_int(e.get("turn")):
            bad.append(f"{where}: turn must be an integer")
        if not isinstance(e.get("at"), str):
            bad.append(f"{where}: at must be text")
        if e.get("note") is not None and not isinstance(e.get("note"), str):
            bad.append(f"{where}: note must be text")
    return bad


def fmt_secs(x):
    x = int(round(x))
    return f"{x}s" if x < 120 else f"{x // 60}m{x % 60:02d}s"


def speed_line(turns):
    """resume's `Speed (last 20): ...` over the last 20 turns that have timing, routine and escalated apart (SES-9); None when no turn has it."""
    rows = [t["timing"] for t in turns if isinstance(t, dict) and isinstance(t.get("timing"), dict)][-20:]

    def gap(x, a, b):
        try:
            d = (datetime.datetime.fromisoformat(x[b]) - datetime.datetime.fromisoformat(x[a])).total_seconds()
        except (KeyError, TypeError, ValueError):
            return None
        return d if d >= 0 else None
    parts = []
    for label, esc in (("routine", False), ("escalated", True)):
        g = [x for x in rows if bool(x.get("escalated")) == esc]
        if not g:
            continue
        bits = [f"{label} {len(g)} turn{'' if len(g) == 1 else 's'}"]
        i2c = [d for d in (gap(x, "received", "checked") for x in g) if d is not None]
        if i2c:
            bits.append(f"input to check median {fmt_secs(statistics.median(i2c))} ({len(i2c)} with --received)")
        c2c = [d for d in (gap(x, "checked", "committed") for x in g) if d is not None]
        if c2c:
            bits.append(f"check to commit median {fmt_secs(statistics.median(c2c))}")
        parts.append(", ".join(bits))
    return ("Speed (last 20): " + "; ".join(parts)) if parts else None


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


def update_presence(turn, prompt, present_override, idx, scene_text=None):
    """Inside the record lock: store scene.present and the expression rotation. Returns a one-line summary. With scene_text (Campfire
    mode: no Crew: line) the NPCs named in the scene text stand in for the Crew names and the rotation is left alone."""
    st = S.get("state")
    campfire = scene_text is not None
    if campfire:
        found, _ = idx.detect(scene_text)
        names = [k for k, _p in sorted(found.items(), key=lambda kv: kv[1]) if not idx.is_pc(k)]
    else:
        names = crew_names(prompt, idx)
    sc = st.get("scene")
    if sc:
        if present_override is not None:
            sc["present"] = present_override
        elif names:
            sc["present"] = names
    exp = st.setdefault("expression", {})
    for k in [] if campfire else names:
        e = idx.ents.get(k) or {}
        rec = exp.setdefault(k, {"recent": [], "cursor": 0})
        rec["recent"] = (rec.get("recent") or []) + [used_items(k, e, prompt, idx)]
        rec["recent"] = rec["recent"][-2:]
        rec["cursor"] = int(rec.get("cursor") or 0) + 1
    S.touch("state")
    summary = ("present: " + ", ".join((sc or {}).get("present") or []) if sc else "no open scene") + \
        ("" if campfire else f"; rotation for {len(names)} NPC(s)")
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
            + ("; split party: the position header counts too" if S.get("state")["party_split"] else "")
            + (" (skipped in Campfire mode)" if campfire_room() else ""))


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
    out += intent_lines(e)
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


def canon_trap_hits(watch, generic=True):
    """Texts of the canon traps (campaign.json) whose match terms appear, word-bounded, in the normalized `watch` text. A trap
    with no match terms always applies when `generic` is true (prep); the lean turn brief leaves those out."""
    out = []
    for tr in CFG.get("canon_traps") or []:
        terms = [norm(t) for t in tr.get("match") or []]
        if not terms and generic or any(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", watch) for t in terms):
            out.append(tr.get("text", ""))
    return out


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
    for text in canon_trap_hits(watch)[:6]:
        out.append("canon trap: " + short(text, PICK_WIDTH - 12))
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
    out += arc_checklist(st)
    return out


def surface_goal(q):
    """The quest's visible goal: `surface_goal` if present, else the seed_line (placeholders like "(none: ...)" do not count)."""
    for f in ("surface_goal", "seed_line"):
        v = (q.get(f) or "").strip()
        if v and not v.startswith("(none"):
            return v
    return ""


def detect_present(st, idx, paste, names_arg):
    """({NPC key: [sources]}, [warnings]): who is on screen this turn, from names in the paste, last turn's scene.present and
    --names. Read-only; player characters are left out."""
    present, warns = {}, []

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
    for nm in [x.strip() for x in (names_arg or "").split(",") if x.strip()]:
        key, amb = idx.lookup(nm)
        if key:
            add(key, "--names")
        elif amb:
            warns.append(f"AMBIGUOUS name {nm}: " + " | ".join(sorted(amb)[:4]))
        else:
            warns.append(f'--names: no NPC matches "{nm}"')
    return present, warns


def read_paste(path):
    if not path:
        return ""
    pf = Path(path)
    if not pf.is_file():
        die(f"no such paste file: {path}")
    return pf.read_text(encoding="utf-8")


def read_packet(path):
    """The Campfire round packet (`gm pull --json`) from FILE; dies (exit 2) naming the problem when it is missing, not JSON or the wrong shape."""
    pf = Path(path)
    if not pf.is_file():
        die(f"no such packet file: {path}", 2)
    try:
        p = json.loads(pf.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        die(f"packet {path} is not valid JSON: {e}", 2)
    if not isinstance(p, dict):
        die(f"packet {path}: expected a JSON object, got {type(p).__name__}", 2)
    for k in ("room", "scene"):
        if not isinstance(p.get(k), dict):
            die(f"packet {path}: `{k}` must be an object", 2)
    for k in ("party", "threats", "inputs"):
        if not isinstance(p.get(k), list):
            die(f"packet {path}: `{k}` must be a list", 2)
        if not all(isinstance(x, dict) for x in p[k]):
            die(f"packet {path}: every `{k}` entry must be an object", 2)
    for k in ("quests", "missing"):
        if k in p and not isinstance(p[k], list):
            die(f"packet {path}: `{k}` must be a list", 2)
    for i, x in enumerate(p["inputs"]):
        if not isinstance(x.get("name"), str) or not isinstance(x.get("text"), str):
            die(f"packet {path}: inputs[{i}] needs a string `name` and `text`", 2)
    return p


def packet_names(packet):
    """[(NPC name, where it came from)]: the scene NPCs and the declared npc targets of the inputs. Data only, never prose."""
    out = [(str(n["name"]), "scene NPC") for n in packet["scene"].get("npcs") or [] if isinstance(n, dict) and n.get("name")]
    for x in packet["inputs"]:
        t = x["declared"].get("target") if isinstance(x.get("declared"), dict) else None
        if isinstance(t, dict) and t.get("kind") == "npc" and t.get("name"):
            out.append((str(t["name"]), f"declared target of {x['name']}"))
    return out


def packet_present(idx, packet, names_arg):
    """({NPC key: [sources]}, [warnings], [(unmatched name, where)]): who is on screen from the packet's data and --names."""
    present, warns, unknown = {}, [], []
    for nm, where in packet_names(packet) + [(x.strip(), "--names") for x in (names_arg or "").split(",") if x.strip()]:
        key, amb = idx.lookup(nm)
        src = "scene" if where == "scene NPC" else where.split(" ")[0]
        if key:
            if not idx.is_pc(key) and src not in present.setdefault(key, []):
                present[key].append(src)
        elif amb:
            w = f"AMBIGUOUS name {nm}: " + " | ".join(sorted(amb)[:4])
            if w not in warns:
                warns.append(w)
        elif where == "--names":
            warns.append(f'--names: no NPC matches "{nm}"')
        elif (norm(nm), where) not in [(norm(n), w) for n, w in unknown]:
            unknown.append((nm, where))
    return present, warns, unknown


def packet_precedent_lines(packet, st):
    """Seam for Campfire v0.2, not part of this approval: it will list the last recorded ruling for each skill in play, as
    precedent so similar actions get similar difficulty words. Returns [] for now."""
    return []


def packet_input_line(x):
    """One input in the CLI's own form: `name: "text"`, the declarations, the target attitude, (early)."""
    d = x.get("declared") if isinstance(x.get("declared"), dict) else {}
    bits = [f"{k} {d[k]}" for k in ("skill", "ability") if d.get(k)]
    t = d.get("target")
    if isinstance(t, dict):
        bits.append("target " + (str(t.get("name")) if t.get("kind") == "npc" else f"threat {t.get('id')}"))
    return (f'{x["name"]}: "{x["text"]}"' + (f" [declared: {', '.join(bits)}]" if bits else "")
            + (f" (target attitude: {x['target_attitude']})" if x.get("target_attitude") else "") + (" (early)" if x.get("early") else ""))


def packet_quests(packet, Q):
    """([quest keys of S.get('quests') the packet's quests match], [titles with no match]): by `title` or `id`, normalized."""
    byn = {norm(k): k for k in Q}
    keys, unknown = [], []
    for q in packet.get("quests") or []:
        if not isinstance(q, dict):
            continue
        k = next((byn[n] for n in (norm(q.get("title") or ""), norm(q.get("id") or "")) if n in byn), None)
        if k:
            if k not in keys:
                keys.append(k)
        else:
            unknown.append(str(q.get("title") or q.get("id") or "?"))
    return keys, unknown


def present_lines(st, idx, present, warns):
    """The PRESENT line, the warnings and the briefs: compact briefs for up to 4 main NPCs, one-liners for the rest."""
    main = [k for k in present if k in MAIN_NPCS or (idx.ents[k].get("kind") == "main")]
    mains, others_ = main[:4], [k for k in present if k not in main[:4]]
    out = ["PRESENT: " + (", ".join(f"{k} ({'+'.join(v)})" for k, v in present.items()) or "nobody detected (pass --paste / --names)")]
    for w in warns:
        out.append("WARN: " + w)
    for k in mains:
        out += compact_npc(k, idx.ents[k], st, idx)
    if others_:
        out += [one_line_npc(k, idx.ents[k]) for k in others_]
    if len(main) > 4:
        out.append(f"(+{len(main) - 4} more main NPCs shown as one-liners; --full NAME for a whole brief)")
    return out


def packet_lines(packet, st, unknown_names, quest_unknown):
    """The packet-only block: party, inputs, missing, fight state, what the database does not know, the v0.2 seam."""
    out, pcs, bad_pc = [], set(), []
    for pc in st["player_characters"]:
        pcs |= {norm(pc["name"]), norm(pc["name"].split()[0])}
    for m in packet["party"]:
        known = norm(m.get("name") or "") in pcs
        if not known:
            bad_pc.append(str(m.get("name") or "?"))
        out.append("PC " + str(m.get("words") or m.get("name") or "?") + ("" if known else " (not in the database: pc-add)"))
    out += [packet_input_line(x) for x in packet["inputs"]]
    miss = [str(m.get("name") or m.get("player")) for m in packet.get("missing") or [] if isinstance(m, dict)]
    if miss:
        out.append("Missing: " + ", ".join(miss))
    out += [f"Fight: {t.get('words') or t.get('name') or t.get('id')} [{t.get('status', '?')}]" for t in packet["threats"]] or ["Fight: no live threat"]
    loc = str(packet["scene"].get("location") or "")
    L = {norm(k) for k in locations()}
    unk = [f"NPC {n} ({w})" for n, w in unknown_names]
    if loc and not any(norm(c) in L for c in (loc, re.split(r"\s*[/,]\s*", loc, maxsplit=1)[0])):
        unk.append(f"location {loc} (packet scene)")
    unk += [f"quest {t} (packet)" for t in quest_unknown]
    unk += [f"party member {n}" for n in bad_pc]
    if unk:
        out += ["Not in the database:"] + ["  - " + u for u in unk]
    return out + packet_precedent_lines(packet, st)


def packet_head(packet):
    """The room warnings and the one packet line of prep's header."""
    rm, sc = packet["room"], packet["scene"]
    out, mine = [], campfire_room()
    if not mine:
        out.append("WARN: campaign.json names no Campfire room code (campfire_room): Campfire mode is off for this campaign")
    elif rm.get("code") != mine:
        out.append(f"WARN: packet room {rm.get('code')} is not this campaign's room {mine}")
    npcs = ", ".join(f"{n.get('name')} ({n.get('attitude') or '?'})" for n in sc.get("npcs") or [] if isinstance(n, dict)) or "none"
    out.append(f"Packet: round {rm.get('round', '?')}, phase {rm.get('phase', '?')}, room {rm.get('code', '?')} | scene \"{sc.get('name', '?')}\" @ "
               f"{sc.get('location', '?')}, {sc.get('day', '?')}, {sc.get('time', '?')}, mood {sc.get('mood', '?')}, surprise used: "
               f"{'yes' if sc.get('surprise_used') else 'no'} | NPCs: {npcs}")
    return out


def cmd_prep(a):
    st = S.get("state")
    idx = NameIndex()
    pk = None
    if a.packet:
        if a.paste:
            die("--packet and --paste cannot be combined: the packet's data replaces the pasted text", 2)
        pk = read_packet(a.packet)
        present, warns, unknown_names = packet_present(idx, pk, a.names)
        sc_ = pk["scene"]
        paste = " ".join([x["text"] for x in pk["inputs"]] + [str(sc_.get(k) or "") for k in ("name", "location", "mood")]
                          + [str(q.get("title") or "") for q in pk.get("quests") or [] if isinstance(q, dict)])  # the watch text
    else:
        paste = read_paste(a.paste)
        present, warns = detect_present(st, idx, paste, a.names)
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
                   f"{'yes' if sc['surprise_used'] else 'no'}" + (f" | kind: {sc['kind']}" if sc.get("kind") else ""))
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
    out += packet_head(pk) if pk else [prompt_budget()]
    out += present_lines(st, idx, present, warns)
    Q = S.get("quests")
    qkeys, qunk = packet_quests(pk, Q) if pk else ([], [])
    if pk:
        out += packet_lines(pk, st, unknown_names, qunk)
    places, bad = place_mentions(paste, st)
    out.append("Places: " + ("; ".join(places) if places else "none named") + (" | UNKNOWN AREA: " + ", ".join(bad) if bad else ""))
    low = norm(re.sub(r"['\u2019]s\b", "", paste))
    ment = ([q for q in qkeys if q in st["active_quests"]] if pk else
            [q for q in st["active_quests"] if q in Q and re.search(r"(?<![a-z0-9])" + re.escape(norm(q)) + r"(?![a-z0-9])", low)])
    if ment:
        for q in ment:
            nxt = next((o for o in Q[q]["objectives"] if o["status"] in OPEN_OBJ), None)
            out.append(f"Quest mentioned: {q}" + (f" | next: {short(nxt['text'], 80)}" if nxt else ""))
    else:
        out.append("Active quests: " + (", ".join(st["active_quests"]) or "none"))
    in_scene = [q for q in st["active_quests"] if q in Q and q not in ment and sc and sc.get("location")
                and Q[q].get("location") == sc["location"] and Q[q].get("area") in (None, sc.get("area"))]
    goal_quests = ment + in_scene
    if paste and not pk:
        known = Known()
        unk = []
        for ph, cat in find_names(paste, known, set()):
            if cat is None and ph not in unk:
                unk.append(ph)
        if unk:
            out.append("New names in paste (not in the database): " + ", ".join(unk[:8]))
    out.append("LIVE CHECKLIST")
    chk = live_checklist(st, idx, list(present), [p.split(" (")[0] for p in places], paste)
    for q in goal_quests:
        g = surface_goal(Q[q])
        chk.append(f"surface goal, {short(q, 40)}: {short(g, 140)}" if g else f"quest {short(q, 40)}: no surface goal set (give a visible what / for whom / reward / risk)")
    fs = "" if pk else next((l.strip() for l in paste.splitlines() if re.match(r"\s*fight status:", l, re.I)), "")
    sc0 = st.get("scene") or {}
    if fs:
        chk.append(short(fs, PICK_WIDTH))
    elif sc0 and not pk and (sc0.get("fight") or re.search(r"fight|battle|combat|brawl|ambush", f"{sc0.get('name', '')} {sc0.get('card', '')}", re.I)):
        chk.append("fight status unknown: write conditional prompt")
    out += ["  - " + c for c in chk] or ["  - (nothing live)"]
    print("\n".join(out))
    if a.full:
        key, amb = idx.lookup(a.full)
        if not key:
            die(f'--full "{a.full}": ' + ("ambiguous: " + " | ".join(sorted(amb)) if amb else "no NPC matches"), 2)
        print()
        cmd_brief(argparse.Namespace(name=key))


# ----------------------------------------------------------------------------
# turn-brief: the lean brief at the start of every turn (LOOP-2); --full is prep's screen (LOOP-6)
# ----------------------------------------------------------------------------
BRIEF_RECENT = 10        # logged turns the spotlight and the Studio recurrence cue look back over
BRIEF_RECUR = 3          # an NPC named in this many of those turns is a Studio candidate (D21)
BRIEF_CAP = 3            # most promises, questions and traps listed; the rest is counted
BRIEF_PICK = 110         # a gesture of the expression kits is at most about 100 characters
BRIEF_FOOTER = (
    "Rules: Voyage owns every mechanic and outcome.",
    "       Never state a PC's condition, feelings, words or results; only the player moves their character.",
    "       `Cut:` goes only as far as the input; every prompt ends with a `World:` move.",
)


def turn_text(t):
    return " ".join(str(t.get(k) or "") for k in ("inputs", "summary", "prompt", "scene"))


def npc_mention_forms(idx, key):
    return {f for f in idx.owned(key) | {norm(key)} if len(f) >= 3}


def more_text(n, what=""):
    return f" (+{n} more{what})" if n > 0 else ""


def brief_visible(names):
    """(names that carry no hidden term, how many were held back): a name from the director's plans only reaches the brief when
    the existing scan finds nothing hidden in it (SEC-1)."""
    names = list(names)
    if not names or not scan_text("; ".join(names))[0]:
        return names, 0
    keep = [n for n in names if not scan_text(n)[0]]
    return keep, len(names) - len(keep)


def npc_entry_act(e):
    """The act a planned NPC enters: an explicit `act`, else the first act whose arc beat says more than offstage or none."""
    v = e.get("act")
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    first = None
    for k, text in (e.get("arc_beats") or {}).items():
        m = re.fullmatch(r"act_(\d+)", str(k))
        t = str(text or "").strip()
        if m and t and not t.startswith("(") and not re.match(r"(?:offstage|none)\b", t, re.I):
            first = int(m.group(1)) if first is None else min(first, int(m.group(1)))
    return first


def latest_sync_digest():
    """The newest digest of data/sync.json (the last one written), or None when the file is missing or unreadable."""
    try:
        digests = json.loads((DATA / SYNC_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ds = [d for d in digests if isinstance(d, dict)] if isinstance(digests, list) else []
    return ds[-1] if ds else None


def voyage_has(idx):
    """(quest keys normalized, npc keys) that the latest sync digest shows in Voyage's save: a quest the save has, an NPC in its party.
    Voyage already owns these, so they need no Studio request. quests.json has no flag for a quest that is Voyage's own: the digest is
    the only source."""
    d = latest_sync_digest() or {}
    qs = {norm(k) for k in (d.get("quests") or {})} if isinstance(d.get("quests"), dict) else set()
    npcs = set()
    for m in d.get("party") or []:
        if isinstance(m, str):
            keys, _ = idx.resolve(m)
            npcs |= {k for k in keys if not idx.is_pc(k)}
    return qs, npcs


def studio_cues(st, idx, turns):
    """Studio moments (D21, TRIG-8) the data shows: parts of the brief's one Studio line. Mechanical only; the director decides."""
    items = studio_items()
    have_q, have_npc = voyage_has(idx)
    asked = {(r.get("kind"), norm(r.get("target"))) for r in items}
    out = []
    pend = [r for r in items if r.get("status") == "pending"]
    if pend:
        out.append("pending " + ", ".join(f'{r["id"]} {r["kind"]} "{short(str(r["target"]), 30)}"' for r in pend[:2]) + more_text(len(pend) - 2))
    day = st["day"]
    for act in CFG.get("acts") or []:  # an act starts today or tomorrow, or began yesterday: its bundle is due
        fd = _int_day(act.get("from_day"))
        if fd is None or not day - 1 <= fd <= day + 1:
            continue
        npcs = [k for k, e in cast().items() if e.get("status") == "planned" and not e.get("in_studio") and npc_entry_act(e) == act["n"]
                and ("npc", norm(k)) not in asked and k not in have_npc]
        qs = [k for k, q in S.get("quests").items() if q.get("status") == "planned" and not q.get("in_studio") and q.get("act") == act["n"]
              and ("quest", norm(k)) not in asked and norm(k) not in have_q]
        if not npcs and not qs:
            continue
        bits = []
        for what, names in (("NPC", npcs), ("quest", qs)):
            shown, held = brief_visible(names[:3])
            if names:
                bits.append(f"{len(names)} {what}{'s' if len(names) != 1 else ''}"
                            + (f" ({', '.join(short(n, 28) for n in shown)}{more_text(len(names) - len(shown) - held)})" if shown else ""))
        out.append(f"act {act['n']} starts, not yet in Studio: " + " and ".join(bits))
    recent = turns[-BRIEF_RECENT:]
    texts = [turn_text(t) for t in recent]
    recur = []
    for k, e in cast().items():
        if (idx.is_pc(k) or e.get("in_studio") or e.get("status") not in ("in_play", "planned") or ("npc", norm(k)) in asked or k in have_npc
                or ((k in MAIN_NPCS or e.get("kind") == "main") and e.get("status") != "planned")):
            continue
        forms = npc_mention_forms(idx, k)
        n = sum(1 for t in texts if mentions_any(t, forms))
        if n >= BRIEF_RECUR:
            recur.append((n, k))
    recur.sort(key=lambda x: (-x[0], x[1]))
    if recur:
        out.append("recurring, not in Studio: " + ", ".join(f"{k} ({n} of {len(recent)} turns)" for n, k in recur[:2]) + more_text(len(recur) - 2))
    Q = S.get("quests")
    started = [qn for qn in st["active_quests"] if isinstance(Q.get(qn), dict) and not Q[qn].get("in_studio") and ("quest", norm(qn)) not in asked
               and norm(qn) not in have_q and _is_turn(Q[qn].get("started_turn")) and st["turn"] - Q[qn]["started_turn"] < BRIEF_RECENT]
    if started:
        out.append("quest started in play, not in Studio: " + ", ".join(f'"{short(q, 36)}"' for q in started[:2]) + more_text(len(started) - 2))
    last_req = max([max(r.get("created_turn") or 0, r.get("applied_turn") or 0) for r in items if r.get("kind") == "area"] + [0])
    new = [f"{loc}/{aid}" for loc, v in locations().items() for aid, ar in (v.get("areas") or {}).items()
           if isinstance(ar, dict) and _is_turn(ar.get("added_turn")) and ar["added_turn"] > last_req]
    if new:
        out.append("new areas, no Studio area request since: " + ", ".join(new[:2]) + more_text(len(new) - 2))
    return out


def brief_due(st, turns):
    """What is due now: clocks, a milestone today, the day-turnover hint, arc lines and a pivot (one line, no off-ramp)."""
    day, out = st["day"], []
    out += [f'clock "{c["name"]}" ' + (f"overdue by {day - c['due_day']} day(s)" if day > c["due_day"] else "due today")
            for c in sorted(st["open_clocks"], key=lambda c: c["due_day"]) if _int_day(c.get("due_day")) is not None and c["due_day"] <= day]
    out += ["milestone " + ln.strip(" -") for ln in turnover_milestones(st, day)]
    days = [_int_day(t.get("day")) for t in turns[-2:]]
    frm = None
    if days and days[-1] is not None and day > days[-1]:
        frm = days[-1]  # the day moved after the last logged turn
    elif len(days) == 2 and None not in days and days[1] > days[0]:
        frm = days[0]  # the day moved inside the last logged turn
    if frm is not None:
        out.append(f"day changed (Day {frm} -> {day}): run `db.py day-turnover`")
    arc = live_arc()
    if arc:
        aid, turn = arc["id"], st["turn"]
        if arc_at(arc, turn, 60) and not any(r.get("kind") == "midpoint" for r in arc.get("reviews") or []):
            out.append(f"arc {aid} midpoint review due")
        if arc_at(arc, turn, 130):
            out.append(f"arc {aid} at 130% of budget: ask the user once, extend or wrap up")
        elif arc_at(arc, turn, 100):
            out.append(f"arc {aid} at 100% of budget: no new pressure, climax hooks where the PC is")
        if arc_drifting(arc, S.get("turns")):
            out.append(f"arc {aid} drifting ({DRIFT_TURNS} turns without contact): Re-aim?")
    if pivot_status()["fired"]:
        out.append("pivot detected: run `db.py arc-pivot`")
    return out


def cmd_turn_brief(a):
    if campfire_room():
        print("NOTE: Campfire mode: the steering brief is skipped; run prep --packet on the round packet (director/playbooks/campfire.md).")
    if a.full:  # LOOP-6: the escalation view is prep's screen, unchanged (plus the planner line); it marks the turn escalated (SES-9)
        clock_note("full_at")
        cmd_prep(argparse.Namespace(paste=a.paste, names=a.names, full=None, packet=None))
        line = planner_brief_line()
        if line:
            print(line)
        return
    print("\n".join(turn_brief_lines(a.paste, a.names)))


def next_brief_lines():
    """The brief for the turn after the recorded one, as commit-turn and resume print it: `NEXT BRIEF (turn N+1):` and the plain
    turn-brief output (no paste), planner line included. Read-only and off the network."""
    n = S.get("state")["turn"]
    return [f"NEXT BRIEF (turn {n + 1}):"] + turn_brief_lines(None, None)


def turn_brief_lines(paste_path, names):
    """The plain turn-brief as a list of lines (cmd_turn_brief prints it; commit-turn and resume reuse it)."""
    st, turns = S.get("state"), S.get("turns")
    idx = NameIndex()
    paste = read_paste(paste_path)
    present, warns = detect_present(st, idx, paste, names)
    out = []
    if stale_warning():
        out.append(stale_warning())
    sc = st.get("scene")
    head = (f"Turn {st['turn']} (next {st['turn'] + 1}), Day {st['day']} {st['weekday']} (Act {current_act(st)}), "
            f"{st['time_block']} {st['clock']}" + (" (time inferred)" if st.get("time_inferred") else ""))
    if sc:
        left = sc["turns_used"] - sc["budget"]
        head += (f"; scene \"{short(sc['name'], 40)}\" {sc['turns_used']}/{sc['budget']} turns" + (f", {sc['kind']}" if sc.get("kind") else "")
                 + (f" ({'OVER budget by ' + str(left) if left > 0 else 'AT budget'})" if left >= 0 else ""))
    else:
        head += "; no scene open"
    if st["party_split"]:
        head += "; party split"
    out.append(head)
    # present NPCs: one rotated gesture each for the one or two spotlight candidates, the rest by name
    recent = turns[-BRIEF_RECENT:]
    texts = [turn_text(t) for t in recent]

    def featured(k):
        forms = npc_mention_forms(idx, k)
        return sum(1 for t in texts if mentions_any(t, forms))
    ranked = sorted(present, key=lambda k: (not (k in MAIN_NPCS or idx.ents[k].get("kind") == "main"), featured(k)))
    spot = {}
    for k in ranked:
        g = [p for p in expression_picks(k, idx.ents[k], st) if p[0] == "gesture"]
        if g and len(spot) < 2:
            spot[k] = g[0][1]
    tag = lambda k: " [planned: intro_line once]" if idx.ents[k].get("status") == "planned" and not idx.ents[k].get("in_studio") else ""
    order = [k for k in present if k in spot] + [k for k in present if k not in spot]
    names = [f"{k}{tag(k)}" + (f" ({short(spot[k], BRIEF_PICK)})" if k in spot else "") for k in order]
    out.append("Present: " + (" | ".join(names[:6]) + more_text(len(names) - 6) if names else "nobody detected (pass --paste or --names)"))
    out += ["WARN: " + w for w in warns]
    due = brief_due(st, turns)
    if due:
        out.append("Due: " + "; ".join(due))
    places, _bad = place_mentions(paste, st)
    place_names = [p.split(" (")[0] for p in places]
    forms = set()
    for k in present:
        forms |= idx.owned(k) | {norm(k)}
    forms |= {norm(p) for p in place_names}
    traps = canon_trap_hits(norm(paste) + " " + " ".join(forms), generic=False)
    if traps:
        out.append("Canon traps: " + " | ".join(short(t, 110) for t in traps[:BRIEF_CAP]) + more_text(len(traps) - BRIEF_CAP))
    prom = [f for f in S.get("canon")["facts"] if f.get("kind") and (f.get("status") or "open") == "open"
            and forms and mentions_any(f"{f['subject']} {f['fact']}", forms)]
    prom.sort(key=lambda f: -(f["turn"] if _is_turn(f.get("turn")) else 0))
    if prom:
        out.append("Promises: " + " | ".join(f"{f['id']} {f['kind']}: {short(str(f['fact']), 80)}" for f in prom[:BRIEF_CAP])
                   + more_text(len(prom) - BRIEF_CAP, "; `db.py promises`"))
    oq = [q for q in question_items(st) if q.get("status") == "open"]
    if oq:
        out.append(f"Questions ({len(oq)}): " + " | ".join(f"{q.get('id')} {short(str(q.get('text')), 70)}" for q in oq[:BRIEF_CAP])
                   + more_text(len(oq) - BRIEF_CAP))
    var = variety_lines(st, turns)
    if var:
        out.append("Variety: " + "; ".join(var))
    cues = studio_cues(st, idx, turns)
    if cues:
        out.append("Studio: " + "; ".join(cues))
    pl = planner_brief_line(st=st)
    if pl:
        out.append(pl)
    out += BRIEF_FOOTER
    return out


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


def collect_payload_errors(p, prompt_required=True):
    """Every problem of a payload at once: structure, then each op and the turn log simulated in memory."""
    errs = check_payload(p, prompt_required)
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
        if (isinstance(tl, dict) and all(k in TURN_LOG_KEYS for k in tl) and isinstance(tl.get("arc_contact", False), bool)
                and isinstance(tl.get("escalated", False), bool)):
            try:
                run_step("turn log", "turn", {"n": turn, **tl}, turn, None)
            except DbError as e:
                if e.msg not in errs and not any(x.endswith(e.msg.split(": ", 1)[-1]) for x in errs):
                    errs.append(e.msg)
    finally:
        S.sim = False
        S.reset()
    return errs, 2


CAMPFIRE_SCENE_LIMIT = 12000  # characters of a Campfire scene (playbooks/campfire.md)
CAMPFIRE_NO_PROMPT = "none (Campfire mode: the posted scene is the record)"  # turn_log.prompt of a Campfire turn


def campfire_inputs(a, what="commit-turn"):
    """(scene text, rulings object, ops list) of commit-turn --scene, or of precheck, where --rulings and --ops may be absent (None).
    Every problem is listed at once (exit 2, nothing written). Campfire's own closed lists (ruling and op names) are not re-checked:
    the server already did."""
    errs, out = [], [None, None, None]

    def read(path, what):
        try:
            return Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            errs.append(f"cannot read the {what} file {path}: {e}")

    def load(path, what):
        raw = read(path, what)
        if raw is not None:
            try:
                return json.loads(raw)
            except ValueError as e:
                errs.append(f"the {what} file is not valid JSON: {e}")
        return None
    raw = read(a.scene, "scene")
    if raw is not None:
        out[0] = raw.rstrip("\n")
        if not out[0].strip():
            errs.append("the scene file is empty")
        elif len(out[0]) > CAMPFIRE_SCENE_LIMIT:
            errs.append(f"the scene is {len(out[0])} characters; the limit is {CAMPFIRE_SCENE_LIMIT}")
    rul = load(a.rulings, "rulings") if a.rulings is not None else None
    if rul is not None:
        if not isinstance(rul, dict) or not isinstance(rul.get("rulings"), list):
            errs.append('the rulings file must be an object with a "rulings" list')
        else:
            out[1] = rul
            for i, r in enumerate(rul["rulings"]):
                if not isinstance(r, dict):
                    errs.append(f"rulings[{i}] must be an object")
                elif "stakes" in r and not isinstance(r["stakes"], str):
                    errs.append(f"rulings[{i}].stakes must be a string")
            if "threat_moves" in rul and not isinstance(rul["threat_moves"], list):
                errs.append('"threat_moves" must be a list')
    ops = load(a.ops, "ops") if a.ops is not None else None
    if ops is not None:
        if not isinstance(ops, list):
            errs.append("the ops file must be a JSON list")
        else:
            out[2] = ops
            for i, o in enumerate(ops):
                if not isinstance(o, dict) or not isinstance(o.get("op"), str):
                    errs.append(f"ops[{i}] must be an object with a string 'op'")
    if errs:
        print(f"{what}: {len(errs)} problem(s) in the Campfire files, nothing written:")
        for e in errs:
            print("  - " + e)
        sys.exit(2)
    return tuple(out)


def campfire_hidden_check(texts, allow=()):
    """(fails, warns) of the hidden-words check on [(label, text)]: lines naming the term, its source and the label. As strict as
    `scan` (the pre-post check of the Campfire playbook): FAIL on every hit scan_text reports (strong secret terms, planner-page hidden
    terms, campaign hidden words, hidden-score words). WARN on a soft secret term (it is also an ordinary word). Terms in `allow` are skipped."""
    allow = {norm(x) for x in allow if str(x).strip()}
    soft = {t: v for t, v in secret_terms().items() if not v[1] and t not in allow}
    fails, warns = [], []
    for label, text in texts:
        hits = [(t, w) for t, w, _ex in scan_text(text)[0] if norm(t) not in allow]
        fails += [f'FAIL: hidden term "{short(t, 60)}" ({w}) in {label}' for t, w in hits]
        warns += [f'WARN: "{short(t, 60)}" is also a term in {src} (still hidden) in {label}: check you are not hinting at the secret'
                  for t, src, _s in find_secrets(text, soft) if t not in {h for h, _ in hits}]
    return fails, warns


SPEAKER_NOTE_LIMIT = 60  # characters of a speaker block's delivery note (playbooks/campfire.md, speaker blocks)


def speaker_blocks(text):
    """The speaker blocks of a Campfire scene, as the client's formatter reads them: a paragraph (blank-line separated) whose first
    line starts with `@` (not `\\@`) is a block when at least one line follows; the speaker is the rest of that line with a trailing
    bracketed delivery note stripped. Returns [(speaker, note, [spoken lines], paragraph number, bare)], bare meaning an `@` line
    with nothing after it, which the client renders as ordinary text."""
    out, n = [], 0
    for para in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n")):
        lines = [ln.rstrip() for ln in para.strip("\n").splitlines() if ln.strip()]
        if not lines:
            continue
        n += 1
        head = lines[0].lstrip()
        if not head.startswith("@"):
            continue
        head = head[1:].strip()
        m = re.fullmatch(r"(.*?)\s*\(([^()]*)\)", head)
        name, note = (m.group(1).strip(), m.group(2).strip()) if m else (head, None)
        if not name:
            continue
        out.append((name, note, [ln.strip() for ln in lines[1:]], n, len(lines) == 1))
    return out


def packet_room_names(packet, ops=None):
    """{exact name: what it is} of everyone a speaker block may name: the party, the scene's NPCs, the threats on the table (not
    retired) and, from the ops of the same post, the NPCs a `scene` op adds and the threat a `threat-add` op adds."""
    names = {}
    for t in packet.get("threats") or []:
        if isinstance(t, dict) and t.get("name") and t.get("status") != "retired":
            names.setdefault(str(t["name"]).strip(), "a threat on the table")
    for m in packet.get("party") or []:
        if isinstance(m, dict) and m.get("name"):
            names.setdefault(str(m["name"]).strip(), "a character")
    for npc in (packet.get("scene") or {}).get("npcs") or []:
        if isinstance(npc, dict) and npc.get("name"):
            names.setdefault(str(npc["name"]).strip(), "a scene NPC")
    for o in ops or []:
        if not isinstance(o, dict):
            continue
        if o.get("op") == "scene":
            for npc in o.get("npcs") or []:
                if isinstance(npc, dict) and npc.get("name"):
                    names.setdefault(str(npc["name"]).strip(), "an NPC the post's scene op adds")
        elif o.get("op") == "threat-add" and o.get("name"):
            names.setdefault(str(o["name"]).strip(), "a threat the post adds")
    return names


def speaker_warnings(text, packet, ops=None, idx=None):
    """WARN lines (playbook pre-check question 1 and the client's name rule) for the speaker blocks of a scene: a block naming nobody in
    the room (not a character, a scene NPC or a threat on the table, nor added by the post's ops), a player character's block whose
    lines are not a quote from that player's input this round, a bare `@` line, a delivery note over the limit."""
    known = packet_room_names(packet, ops)
    loose = lambda x: re.sub(r"[^a-z0-9 ]+", "", norm(x)).strip()  # noqa: E731 - case, accents and punctuation aside
    by_loose = {}
    for nm in known:
        by_loose.setdefault(loose(nm), nm)

    def near_name(name):
        """The one room name the block most likely means: the same name apart from case, accents or punctuation, or the only
        room name holding it as whole words ("Oda" for "Station Master Oda"); None when there is none or several."""
        lo = loose(name)
        if lo in by_loose:
            return by_loose[lo]
        held = [nm for lk, nm in by_loose.items() if lo and re.search(r"(?<![a-z0-9])" + re.escape(lo) + r"(?![a-z0-9])", lk)]
        return held[0] if len(held) == 1 else None
    party = {str(m["name"]).strip() for m in packet.get("party") or [] if isinstance(m, dict) and m.get("name")}
    inputs = {}
    for x in packet.get("inputs") or []:
        if isinstance(x, dict) and x.get("name") and isinstance(x.get("text"), str):
            inputs[str(x["name"]).strip()] = x["text"]
    warns = []
    for name, note, lines, n, bare in speaker_blocks(text):
        where = f'speaker block "@{name}" (paragraph {n})'
        if bare:
            warns.append(f"{where} has no line after it: the client renders it as ordinary text; put the spoken line on the next line")
            continue
        if name not in known:
            near = near_name(name)
            if near:
                hint = f'the room lists "{near}": the name must match exactly'
            else:
                key = idx.lookup(name)[0] if idx else None
                if key and not idx.is_pc(key):
                    hint = f'"{key}" is in the database but not in the scene: add them with a scene op (name and attitude) in this post'
                else:
                    hint = "add them with a scene op in this post, or use the name the room lists"
            warns.append(f"{where} names nobody in the room (not a character, a scene NPC or a threat on the table); {hint}")
        elif name in party:
            text_in = norm(inputs.get(name, ""))
            missing = [ln for ln in lines if norm(ln) not in text_in]
            if not inputs.get(name):
                warns.append(f"{where} is a player character's block, and {name} wrote no input this round: never give a player "
                             "character words their player did not write")
            elif missing:
                warns.append(f"{where} is a player character's block, and this line is not a quote from their input: "
                             f"{short(missing[0].strip(chr(34) + chr(0x201C) + chr(0x201D)), 60)}. Set only their own words, word for word, or "
                             "report what they did in narration")
        if note and len(note) > SPEAKER_NOTE_LIMIT:
            warns.append(f"{where}: the delivery note is {len(note)} characters; keep it under {SPEAKER_NOTE_LIMIT}")
    return warns


def cmd_precheck(a):
    """Read-only. The mechanical part of the Campfire playbook's five-question pre-check, before the post: the hidden-words check on
    the scene and the stakes lines (question 3, as strict as commit-turn's), and the speaker-block warnings (question 1 and the
    client's name rule). Exit 0 when clean or with warnings only, EXIT_SCAN on a hidden term, 2 on a bad file."""
    scene, rulings, ops = campfire_inputs(argparse.Namespace(scene=a.scene, rulings=a.rulings, ops=a.ops), "pre-check")
    pk = read_packet(a.packet)
    for ln in packet_head(pk)[:-1]:  # the room warnings, without prep's packet line
        print(ln)
    rm = pk["room"]
    print(f"pre-check: round {rm.get('round', '?')} of room {rm.get('code', '?')}, scene {len(scene)} characters"
          + (f", {len(rulings['rulings'])} ruling(s)" if rulings else "") + (f", {len(ops)} op(s)" if ops is not None else ""))
    texts = [("scene", scene)] + ([(f"rulings[{i}].stakes", r["stakes"]) for i, r in enumerate(rulings["rulings"]) if r.get("stakes")]
                                  if rulings else [])
    print("hidden-words check:")
    fails, warns = campfire_hidden_check(texts, (a.allow or "").split(","))
    for ln in fails + warns:
        print(ln)
    if not fails and not warns:
        print(f"  ok: scene and {len(texts) - 1} stakes line(s) carry no hidden term" + ("" if rulings else " (no --rulings: stakes not checked)"))
    blocks = speaker_blocks(scene)
    print("speaker blocks: " + (", ".join(f'"@{b[0]}"' for b in blocks) if blocks else "none"))
    sw = speaker_warnings(scene, pk, ops, NameIndex())
    for ln in sw:
        print("WARN: " + ln)
    if fails:
        print("\npre-check: FAIL, a hidden term is in the scene or a stakes line; do not post. Reword it and run the pre-check again. "
              "--allow TERM only for a term that is public.")
        sys.exit(EXIT_SCAN)
    print(f"\npre-check: ok{' with ' + str(len(sw) + len(warns)) + ' warning(s)' if sw or warns else ''}; "
          "the five questions are yours to answer before gm post.")


EXIT_STOP = 9  # check: three rewrites are done and the draft is still flagged; show the GM


def hard_noes():
    """The campaign's hard noes (campaign.json `hard_noes`, phrases agreed at the table); an invalid value counts as none and resume warns."""
    v = CFG.get("hard_noes")
    return [p for p in v if isinstance(p, str)] if isinstance(v, list) and not CK.hard_noe_problems(v) else []


def cmd_hard_noes(a):
    """List, add or remove the campaign's hard noes. The list lives in campaign.json on the GM's machine and never reaches Campfire."""
    cur = [p for p in CFG.get("hard_noes") or [] if isinstance(p, str)]
    if not a.add and not a.remove:
        print(f"hard noes ({len(cur)}): " + ("; ".join(f'"{p}"' for p in cur) if cur else "none"))
        return
    new = [p for p in cur if not any(CK.words(p) == CK.words(x) for x in a.remove or [])]
    gone = len(cur) - len(new)
    for x in a.add or []:
        if not any(CK.words(x) == CK.words(p) for p in new):
            new.append(x.strip())
    bad = CK.hard_noe_problems(new)
    if bad:
        die("; ".join(bad) + ". Nothing written.", 2)
    role_gate("hard-noes")
    path = CAMPAIGN_DIR / "campaign.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["hard_noes"] = new
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    CFG["hard_noes"] = new
    print(f"hard noes now {len(new)}: " + ("; ".join(f'"{p}"' for p in new) if new else "none") + f" ({len(a.add or [])} added, {gone} removed)")


def campfire_dir():
    return CAMPAIGN_DIR / "campfire"


def read_json_file(path, what):
    pf = Path(path)
    if not pf.is_file():
        die(f"no such {what} file: {path}", 2)
    try:
        return json.loads(pf.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        die(f"{what} file {path} is not valid JSON: {e}", 2)


def zone_name(z):
    return str(z.get("name") if isinstance(z, dict) else z).strip()


def reacted_positions(pk, reactions, ops):
    """({name: zone after the round}, [zone names]) from a reacted packet: party, scene NPCs and threats with a `zone`, then each
    reaction's move or leave and the post's `move` ops. Both are empty when the packet carries no zones (the zone checks then skip)."""
    zones = [zone_name(z) for z in (pk.get("scene") or {}).get("zones") or [] if zone_name(z)]
    pos = {}
    for grp in (pk.get("party") or [], (pk.get("scene") or {}).get("npcs") or [], pk.get("threats") or []):
        for m in grp:
            if isinstance(m, dict) and m.get("name") and m.get("zone"):
                pos[str(m["name"]).strip()] = str(m["zone"]).strip()
    ids = {str(m.get("player")): str(m["name"]).strip() for m in pk.get("party") or [] if isinstance(m, dict) and m.get("name")}
    for r_ in reactions or []:
        if not isinstance(r_, dict) or not r_.get("npc"):
            continue
        to = ((r_.get("applied") or {}).get("zone") or {}).get("to") if isinstance(r_.get("applied"), dict) else None
        if r_.get("kind") == "move":
            pos[str(r_["npc"]).strip()] = str(to or r_.get("to") or "").strip()
        elif r_.get("kind") == "leave":
            pos.pop(str(r_["npc"]).strip(), None)
    for o in ops or []:
        if not isinstance(o, dict):
            continue
        if o.get("op") == "move" and o.get("to"):
            who = o.get("npc") or ids.get(str(o.get("player")), o.get("player"))
            if who:
                pos[str(who).strip()] = str(o["to"]).strip()
        elif o.get("op") == "scene":
            zones += [zone_name(z) for z in o.get("zones_add") or [] if zone_name(z) not in zones]
    return {k: v for k, v in pos.items() if v}, zones


def cast_name_flags(scene, pk, ops, idx):
    """State check 2: a cast NPC named in the scene who is neither in the room nor arriving by this post's ops."""
    found, _ = idx.detect(scene)
    room = packet_room_names(pk, ops)
    here = set()
    for nm in room:
        k, _amb = idx.lookup(nm)
        if k:
            here.add(k)
    out = []
    for k in found:
        if k not in here and not idx.is_pc(k):
            out.append(CK.flag("cast_not_present", "state", "flag",
                               f'"{k}" is named in the scene but is not in the room and no op of this post brings them; add a scene op '
                               "or take the name out", None, k))
    return out


def speaker_flags(scene, pk, ops, idx):
    """State check 1 (and the pre-check's speaker rules) as flags: a block naming nobody in the room and a player character's block that
    is not a quote of their input are flags; a bare @ line and a long delivery note are warns."""
    out = []
    for w in speaker_warnings(scene, pk, ops, idx):
        n = re.search(r"paragraph (\d+)", w)
        para = int(n.group(1)) if n else None
        hard = "names nobody in the room" in w or "player character's block" in w
        out.append(CK.flag("speaker_unknown" if "nobody" in w else ("pc_block" if hard else "speaker_form"), "state",
                           "flag" if hard else "warn", w, para))
    return out


def code_check_flags(scene, pk, ops, reactions, mapping, allow=()):
    """Every code check of the check stage on a draft, in the GDD's order: hidden words, the hard noes, then the state checks 1 to 7 and the
    input-to-paragraph map. Returns [flags]."""
    idx = NameIndex()
    out = []
    fails, warns = campfire_hidden_check([("scene", scene)], allow)
    out += [CK.flag("hidden_word", "state", "flag", f.replace("FAIL: ", ""), quote="") for f in fails]
    out += [CK.flag("hidden_word_soft", "state", "warn", w.replace("WARN: ", "")) for w in warns]
    out += CK.phrase_flags(scene, hard_noes())
    out += speaker_flags(scene, pk, ops, idx)
    out += cast_name_flags(scene, pk, ops, idx)
    pos, zones = reacted_positions(pk, reactions, ops)
    known = list(zones) + [(pk.get("scene") or {}).get("location") or ""]
    for o in ops or []:
        if isinstance(o, dict) and o.get("op") == "scene" and o.get("location"):
            known.append(o["location"])
    L = locations()
    known += list(L) + [a_ for loc in L.values() if isinstance(loc, dict) for a_ in (loc.get("areas") or {})]
    out += CK.place_flags(scene, known)
    out += CK.zone_flags(scene, pos, zones)
    out += CK.evidence_flags(scene, ops)
    out += CK.reaction_line_flags(scene, reactions)
    if mapping is not None:
        inputs = [x for x in pk.get("inputs") or [] if isinstance(x, dict)]
        out += CK.map_flags(scene, inputs, mapping, lambda x: [str(x.get("name") or "")] + str(x.get("name") or "").split()[:1])
    return out


def reactions_of(pk, given):
    """The reactions list: the reacted packet's own when it has one, else the reactions file's (an object with `reactions`, or a list)."""
    if isinstance(pk.get("reactions"), list):
        return pk["reactions"]
    if isinstance(given, dict):
        given = given.get("reactions")
    return given if isinstance(given, list) else []


def cmd_check(a):
    """The check stage: every code check on a draft scene, plus the checker's answers when given. Appends the run to the round's check
    log; after three rewrites (four checks) with the draft still flagged it stops (exit 9) and the draft goes to the GM."""
    scene, _r, ops = campfire_inputs(argparse.Namespace(scene=a.scene, rulings=None, ops=a.ops), "check")
    pk = read_packet(a.packet)
    reactions = reactions_of(pk, read_json_file(a.reactions, "reactions") if a.reactions else None)
    mapping = read_json_file(a.map, "input-to-paragraph map") if a.map else None
    if a.map and not isinstance(mapping, dict):
        die("the input-to-paragraph map must be an object with an \"inputs\" list", 2)
    rnd = a.round if a.round is not None else (pk["room"].get("round") if isinstance(pk["room"].get("round"), int) else None)
    if rnd is None and not a.log:
        die("--round N is required (the packet names no round), or give --log FILE", 2)
    log_path = Path(a.log) if a.log else campfire_dir() / f"check-{rnd}.json"
    log = {"round": rnd, "attempts": [], "overruled": []}
    if log_path.is_file() and not a.reset:
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
        except ValueError:
            die(f"{log_path} is not valid JSON; move it aside or run with --reset", 2)
    sha = hashlib.sha256(scene.encode("utf-8")).hexdigest()[:12]
    done = log["attempts"]
    if done and done[-1].get("stopped"):
        print(f"check: round {rnd} already stopped after {CK.WRITE_RETRIES} rewrites. Show the GM the draft and the flags below, and wait for the GM.")
        for f in done[-1]["flags"]:
            print(f"  {f['severity'].upper()} [{f['code']}] {f['text']}")
        print("When the GM says what to do, run check again with --reset to start a fresh log.")
        sys.exit(EXIT_STOP)
    flags = code_check_flags(scene, pk, ops, reactions, mapping, (a.allow or "").split(","))
    checker = "not run"
    if a.answers:
        flags += CK.answer_flags(read_json_file(a.answers, "checker answers"), scene)
        checker = "answered"
    hard = [f for f in flags if f["severity"] == "flag"]
    n = len(done) + 1
    stopped = bool(hard) and n > CK.WRITE_RETRIES
    done.append({"attempt": n, "scene_sha": sha, "checker": checker, "flags": flags, "stopped": stopped})
    campfire_dir().mkdir(parents=True, exist_ok=True) if not a.log else None
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"check: round {rnd}, draft {sha}, check {n} (rewrite {n - 1} of {CK.WRITE_RETRIES}), checker {checker}")
    for f in flags:
        print(f"  {f['severity'].upper()} [{f['code']}] {f['text']}" + (f' | "{f["quote"]}"' if f.get("quote") else ""))
    if not flags:
        print("  no flags")
    if a.json:
        Path(a.json).write_text(json.dumps({"round": rnd, "attempt": n, "flags": flags}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not hard:
        print("\ncheck: passed" + ("" if checker == "answered" else " the code checks; the checker has not run: run check-brief and answer it, then check again with --answers")
              + (f" with {len(flags)} warning(s)" if flags else ""))
        return
    if any(f["code"] == "hidden_word" for f in hard):
        print("\ncheck: FAIL, a hidden term is in the scene; do not post. Reword it and check again.")
    if stopped:
        print(f"\ncheck: STOP. The draft is still flagged after {CK.WRITE_RETRIES} rewrites. Show the GM the draft and these flags and wait.")
        sys.exit(EXIT_STOP)
    print(f"\ncheck: {len(hard)} flag(s). Rewrite from them, then check again ({CK.WRITE_RETRIES - (n - 1)} rewrite(s) left).")
    sys.exit(EXIT_SCAN if any(f["code"] == "hidden_word" for f in hard) else 1)


def cmd_check_brief(a):
    """Print the checker subagent's whole brief for a draft: the fixed questions, the hard noes, the reacted packet and the draft."""
    scene, _r, _o = campfire_inputs(argparse.Namespace(scene=a.scene, rulings=None, ops=None), "check-brief")
    pk = read_packet(a.packet)
    sys.stdout.write(CK.checker_brief(scene, pk, hard_noes()))


def cmd_commit_turn(a):
    campfire = a.scene is not None
    if campfire == (a.prompt is not None):
        die("give exactly one of --prompt FILE (Browser/paste mode) or --scene FILE --rulings FILE --ops FILE (Campfire mode)", 2)
    if campfire and (a.rulings is None or a.ops is None):
        die("--scene needs --rulings FILE and --ops FILE", 2)
    if not campfire and (a.rulings is not None or a.ops is not None or a.allow is not None):
        die("--rulings, --ops and --allow belong to Campfire mode: give them with --scene, not --prompt", 2)
    if campfire:
        if not campfire_room():
            die("commit-turn --scene refused: campaign.json names no Campfire room code (campfire_room), so Campfire mode is off. "
                "Nothing was written.", EXIT_REFUSED)
        scene, rulings, cf_ops = campfire_inputs(a)
        prompt = CAMPFIRE_NO_PROMPT
    else:
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
    if not a.dry_run:
        role_gate("commit-turn")  # the planner session writes no turn data (it would be refused at the lock anyway: say so first)
    received = parse_received(a.received) if a.received else None
    if campfire:
        texts = [("scene", scene)] + [(f"rulings[{i}].stakes", r["stakes"]) for i, r in enumerate(rulings["rulings"]) if r.get("stakes")]
        print("hidden-words check:")
        fails, warns = campfire_hidden_check(texts, (a.allow or "").split(","))
        for ln in fails + warns:
            print(ln)
        if fails:
            print("\ncommit-turn: FAIL in the scene or a stakes line; nothing written. The scene may already be posted: tell the GM. "
                  "--allow TERM only for a term that is public.")
            sys.exit(1)
        if not warns:
            print(f"  ok: scene and {len(texts) - 1} stakes line(s) carry no hidden term")
    else:
        print("check-prompt:")
        tl0 = payload.get("turn_log") if isinstance(payload, dict) else None
        inputs = tl0.get("inputs") if isinstance(tl0, dict) else None
        failed, unknown, warns = run_check(prompt, [], verbose=False, inputs=inputs if isinstance(inputs, str) else None)
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
                notes.append("turn_log.prompt replaced by " + ("the Campfire record text" if campfire else "the prompt file"))
            tl["prompt"] = prompt
    errs, code = collect_payload_errors(payload, prompt_required=not campfire)
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
    if campfire:  # the Campfire record reaches the turn entry only from here, after validation (a hand-written turn_log cannot carry it)
        payload = {**payload, "turn_log": {**payload["turn_log"], "scene_text": scene, "rulings_json": json.dumps(rulings),
                                           "campfire_ops_json": json.dumps(cf_ops)}}
        what = f"scene {len(scene)} chars, {len(rulings['rulings'])} ruling(s), {len(cf_ops)} Campfire op(s)"
    else:
        what = f"prompt {len(prompt)}/{PROMPT_LIMIT}"
    if a.dry_run:
        S.reset()
        S.sim = True
        try:
            plan = run_payload(payload)
        finally:
            S.sim = False
            S.reset()
        print(f"\ncommit-turn {turn}: dry run OK, {len(plan) - 1} op(s) + turn log; {what}. Plan:")
        for ln in plan_lines(plan):
            print(ln)
        print("nothing written.")
        return
    ctx = git_ctx()
    if ctx and git_branch(ctx[0]) != "main":
        die(f"commit-turn refused: on branch {git_branch(ctx[0])!r}, not main. Nothing was written. "
            "Run `git fetch origin main && git checkout -B main origin/main`, then rerun.", EXIT_BRANCH)
    clock = clock_read().get(str(turn))
    clock = clock if isinstance(clock, dict) else {}
    tl = dict(payload["turn_log"])  # SES-9: the turn's timing goes into its log entry (set after validation, so a hand-written payload cannot carry it)
    committed = datetime.datetime.now().astimezone()  # a check-prompt or --full run long before the real turn must not colour its timing
    checked = clock.get("checked") if clock_fresh(clock.get("checked"), committed) else None
    tl["timing"] = json.dumps({"received": received, "checked": checked, "committed": committed.isoformat(timespec="seconds"),
                               "escalated": bool(tl.pop("escalated", False)) or clock_fresh(clock.get("full_at"), committed)})
    payload = {**payload, "turn_log": tl}
    with write_lock("commit-turn", turn):
        S.reset()
        before = {r["id"] for r in studio_items()}
        take_snapshot(turn)
        try:
            S.reset()
            steps = run_payload(payload)
            idx = NameIndex()
            present_line = update_presence(turn, prompt, present_override, idx, scene if campfire else None)
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
    print(f"\ncommit-turn {turn}: ok, {len(steps) - 1} op(s) + turn log; {what}")
    for ln in plan_lines(steps, 8):
        print(ln)
    print("  " + present_line)
    for ln in day_change_lines(steps):
        print(ln)
    clock_clear(turn)  # the turn is recorded: its clock entry has done its job
    msg = f"{display()} save: turn {turn}"
    pushed = False
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
                    pushed = True
                except PushFailed as e:
                    print(f"  WARN push failed ({short(e.msg, 140)}); data is saved and committed locally; the next push or `wrap-up` retries.")
    if ctx and not pushed:  # SES-2: see what the planner pushed (a push that just worked already refreshed origin/main); a failure only warns
        why = planner_fetch(ctx[0])
        if why:
            print(f"WARN planner fetch failed ({why}); play on, the next turn retries")
    for r in studio_items():
        if r["id"] not in before:
            print(f"\nSTUDIO request {r['id']} (paste each batch into Studio):")
            print_studio_batches(r)
    if campfire:  # the steering brief is not used in Campfire mode
        print("Next: on the GM's next \"send\" or \"draft\", run prep --packet on the new round packet (director/playbooks/campfire.md).")
        return
    try:  # last of all: the brief for the next turn, so the director holds it before the next input arrives (LOOP-2)
        S.reset()
        brief = next_brief_lines()
    except Exception as e:  # noqa: BLE001 - the turn is recorded; a brief that cannot be built must not turn that into a failure
        print(f"\nWARN next brief unavailable ({short(str(getattr(e, 'msg', e)), 120)}); run `db.py turn-brief`")
    else:
        print()
        print("\n".join(brief))


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
    # reminders only: neither blocks "safe to close" (SAVE-2, REVIEW-1)
    log = st.get("sync_log") if isinstance(st.get("sync_log"), list) else []
    if not any(isinstance(x, dict) and x.get("turn") == st["turn"] for x in log):
        print(f"Reminder: no sync for turn {st['turn']}. Ask the user for Voyage's state export and run `sync` on it (the user may skip it).")
    print("Reminder: run the director review on the last turns of this scene or session, then record its findings with `review-add`.")
    print(f"safe to close: {safe or 'yes (nothing in git to push)'}.")


# ----------------------------------------------------------------------------
# campaign choice: use (the session file) and menu (SEL-1, SEL-2, MENU-1)
# ----------------------------------------------------------------------------
# Main menu: (item, who does it). Paraphrased from the ORCH-1 table in director/core.md; tests/test_session.py checks it against that table.
MENU_ITEMS = [
    ("Play a turn (paste or browser)", "director session"),
    ("Resume digest and recap", "planner session, Sonnet subagent (all-in-one: Sonnet subagent at a break)"),
    ("Plan an act or arc", "planner session, Opus (all-in-one: Opus subagent at a break); you review it"),
    ("Pressure card for a showcase scene", "planner session, Opus (all-in-one: Opus subagent at a break)"),
    ("Pivot mini-charter", "planner session, Opus (all-in-one: Opus subagent at a break)"),
    ("Studio, cast and world work", "planner session, Sonnet subagent (all-in-one: Sonnet subagent at a break)"),
    ("Sync from the save file", "director session (Sonnet subagent; you confirm)"),
    ("Director review, canon audit, act retro", "planner session (review Opus, audit and retro Sonnet)"),
    ("Tool, test and doc changes", "planner session, Sonnet subagent (you review the diff)"),
    ("New campaign", "planner session, Sonnet subagent (scaffold)"),
    ("Apply planner files", "director session"),
    ("Wrap-up and repairs", "director session"),
]


def last_save_times(names):
    """{campaign: unix time of the newest git commit touching campaigns/NAME/data, or None}. Used only to order the menu.
    None when git is missing, this is not a repository, the history is shallow or empty for that path, or git is slow."""
    out = {}
    for n in names:
        ts = None
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", f"campaigns/{n}/data"], cwd=ROOT,
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout.strip().isdigit():
                ts = int(r.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        out[n] = ts
    return out


def order_campaigns(names, times):
    """Newest save first; campaigns with no known save time follow, by name."""
    return sorted(names, key=lambda n: (times.get(n) is None, -(times.get(n) or 0), n))


def env_choice_note():
    v = env_first("VOYAGE_CAMPAIGN")
    return f"note: env VOYAGE_CAMPAIGN={v} is set and takes precedence over the session file" if v else None


def match_voyage_title(text):
    """The campaigns whose voyage_title (campaign.json, optional) matches a Voyage browser tab title, case-insensitively: an
    exact match, else a title that the tab text contains (tab titles often carry a site suffix), leaving out a contained title
    that is only part of another contained title ("Class 2B" inside "Class 2B Retest"). Returns (matches, candidates),
    each a list of (campaign, voyage_title)."""
    want = norm(text)
    cands = []
    for n in list_campaigns():
        t = campaign_cfg(n).get("voyage_title")
        if isinstance(t, str) and norm(t):
            cands.append((n, t.strip()))
    exact = [c for c in cands if norm(c[1]) == want]
    if exact:
        return exact, cands
    inside = [c for c in cands if norm(c[1]) in want]
    return [c for c in inside if not any(norm(c[1]) != norm(o[1]) and norm(c[1]) in norm(o[1]) for o in inside)], cands


def write_session(name, role=None, set_at=None):
    """Write the session file: the campaign, when it was chosen (set_at, default now) and the role (left out when not chosen)."""
    p = session_path()
    tmp = p.with_name(p.name + ".tmp")
    d = {"campaign": name, "set_at": set_at or _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())}
    if role:
        d["role"] = role
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError as e:
        die(f"cannot write the session file {p}: {e}")


def resolve_role(role, name):
    """(role, why) for a `--role` value: `auto` is director when planner output is waiting for campaign `name`, else all-in-one (SES-5)."""
    if role != "auto":
        return role, None
    items = planner_items(name)
    if items and any(not i["applied"] for i in items[1]):
        return "director", "auto: planner output is waiting"
    return "all-in-one", "auto: no planner output is waiting"


def cmd_use(a):
    """use NAME / use --title TEXT: write the session file; use --role ROLE: change its role; use: show the choice and role; use --clear: remove it."""
    path = session_path()
    if sum(x is not None and x is not False for x in (a.name, a.title, a.clear)) > 1:
        die("give only one of NAME, --title TEXT and --clear", 2)
    if a.clear and a.role:
        die("give only one of --clear and --role", 2)
    if a.clear:
        try:
            old = read_session()
        except ValueError:
            old = None
        try:
            path.unlink()
        except FileNotFoundError:
            print("no session campaign was set")
            return
        except OSError as e:
            die(f"cannot remove the session file {path}: {e}")
        print("session campaign cleared" + (f" (was {old['campaign']})" if old else ""))
        return
    note = env_choice_note()
    if a.title is not None or a.name is not None:
        names = list_campaigns()
        if a.title is not None:
            if not norm(a.title):
                die("--title needs the Voyage tab title text", 2)
            hits, cands = match_voyage_title(a.title)
            if not hits:
                known = "; ".join(f"{n} = '{t}'" for n, t in cands)
                die(f"no campaign has a voyage_title matching '{a.title}' (" + (f"voyage_title set for: {known}" if known else
                    "no campaign sets voyage_title in campaign.json") + "): run `db.py use NAME` instead", 2)
            if len(hits) > 1:
                die(f"several campaigns match '{a.title}': " + "; ".join(f"{n} = '{t}'" for n, t in hits) + ": run `db.py use NAME`", 2)
            name = hits[0][0]
        else:
            name = a.name
            if name not in names:
                die(f"campaign '{name}' not found (campaigns: {', '.join(names) or 'none'})", 2)
        try:
            old = read_session()
        except ValueError:
            old = None
        role, why = resolve_role(a.role, name) if a.role else (old["role"] if old else None, None)  # no --role: the chat keeps its role
        write_session(name, role)
        print(campaign_line(name, campaign_cfg(name)))
        print(f"session campaign set: {name} (commands now default to it; override with --campaign or env VOYAGE_CAMPAIGN)")
        print(role_line({"role": role}) + (f" ({why})" if why else ""))
        if note:
            print(note)
        return
    try:
        sess = read_session()
    except ValueError as e:
        die(f"{e}: run `db.py use NAME` to replace it or `db.py use --clear` to remove it", 2)
    if sess and sess["campaign"] not in list_campaigns():
        die(f"the session file {path} names campaign '{sess['campaign']}', which no longer exists "
            f"(campaigns: {', '.join(list_campaigns()) or 'none'}): run `db.py use NAME` to choose another or `db.py use --clear`", 2)
    if a.role:  # change the role of the current choice
        if not sess:
            die("no session campaign set, so there is no role to change: run `db.py use NAME --role ROLE`", 2)
        role, why = resolve_role(a.role, sess["campaign"])
        write_session(sess["campaign"], role, sess["set_at"])
        sess = {**sess, "role": role}
        print(campaign_line(sess["campaign"], campaign_cfg(sess["campaign"])))
        print(f"session campaign: {sess['campaign']}" + (f", set {sess['set_at']}" if sess["set_at"] else ""))
        print(role_line(sess) + (f" ({why})" if why else ""))
    elif not sess:
        print("no session campaign set: run `db.py use NAME` (`db.py menu` lists the campaigns)")
    else:
        print(campaign_line(sess["campaign"], campaign_cfg(sess["campaign"])))
        print(f"session campaign: {sess['campaign']}" + (f", set {sess['set_at']}" if sess["set_at"] else ""))
        print(role_line(sess))
    if note:
        print(note)


def cmd_menu(a):
    """The campaigns (most recently saved first, ordering only), the session choice and the main menu; needs no campaign."""
    names = list_campaigns()
    order = order_campaigns(names, last_save_times(names))
    try:
        sess, bad = read_session(), None
    except ValueError as e:
        sess, bad = None, str(e)
    chosen = sess["campaign"] if sess else None
    print("Voyage director: main menu")
    if order:
        print("Campaigns, most recently saved first:")
        for i, n in enumerate(order, 1):
            print(f"  {i}. {campaign_label(n, campaign_cfg(n))}" + ("   <- session choice" if n == chosen else ""))
    else:
        print("No campaigns found under campaigns/.")
    if bad:
        print(f"Session choice: unusable ({bad}). Run `db.py use NAME` or `db.py use --clear`.")
    elif chosen and chosen not in names:
        print(f"Session choice: '{chosen}' no longer exists. Run `db.py use NAME` or `db.py use --clear`.")
    elif chosen:
        print(f"Session choice: {chosen}" + (f", set {sess['set_at']}" if sess["set_at"] else "") + ".")
    else:
        print("Session choice: none. Choose one with `db.py use NAME`.")
    if not bad:
        print(role_line(sess))
    note = env_choice_note()
    if note:
        print(note[0].upper() + note[1:] + ".")
    print("Roles: director plays the turns, planner plans and does one-off jobs, all-in-one does both (`db.py use --role ROLE`).")
    print("Menu (who does it):")
    width = max(len(item) for item, _ in MENU_ITEMS)
    for i, (item, who) in enumerate(MENU_ITEMS, 1):
        print(f"  {i:>2}. {item.ljust(width)}  {who}")


# ----------------------------------------------------------------------------
# argument parser
# ----------------------------------------------------------------------------
def build_parser():
    p = Parser(
        prog="db.py [--campaign NAME]", description=f"{display()} director database. The database is the source of truth; never read the Voyage world export during play.",
        epilog="Updates need --turn N --evidence \"...\" (a quote or paraphrase from the story output). See README.md.")
    p.add_argument("--campaign", metavar="NAME", help="campaign under campaigns/ (default: env VOYAGE_CAMPAIGN, else the session "
                   "campaign set by `use NAME`, else the only campaign)")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    def add(name, fn, help, upd=False):
        sp = sub.add_parser(name, help=help, description=help)
        SUBS[name] = sp
        sp.set_defaults(fn=fn)
        if upd:
            sp.add_argument("--turn", type=int, required=True, help="turn whose story output justifies this change")
            sp.add_argument("--evidence", required=True, help="short quote or paraphrase from the story output")
        return sp

    sp = add("use", cmd_use, "choose the campaign for this chat: `use NAME` writes the git-ignored session file that later commands default to "
             "(after --campaign and env VOYAGE_CAMPAIGN); `use --title TEXT` picks the campaign whose campaign.json voyage_title matches a "
             "Voyage tab title (case-insensitive); `use` shows the choice and the role; `use --clear` removes it; `--role ROLE` sets the chat's role")
    sp.add_argument("name", nargs="?"); sp.add_argument("--title", metavar="TEXT"); sp.add_argument("--clear", action="store_true")
    sp.add_argument("--role", choices=SESSION_ROLES + ("auto",), help="this chat's role, stored with the campaign choice (alone: changes the role of "
                    "the current choice); auto = director when planner output is waiting for the campaign, else all-in-one. A planner session "
                    "writes no campaign data")
    add("menu", cmd_menu, "list the campaigns (most recently saved first), the session choice and the main menu with who does each item; needs no campaign")

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
    sp = add("day-turnover", cmd_day_turnover,
             f"what the world does on a new in-game day (read-only; WLD-2, WLD-3, PIV-6). Lists only what applies: open clocks due on or "
             f"before the day; milestones on the day; threads going cold (active quests and ladders with no story contact for "
             f"{COLD_DAYS}+ days, dated from quest logs, turns that name the quest and the turns' days); the next move of every front of the "
             f"live arc and of each parked arc; main NPCs with an agenda who have not been on screen for {OFFSCREEN_DAYS}+ days "
             f"(up to {OFFSCREEN_MAX}, longest off screen first), with the agenda's next move. Anything without a day on record is "
             f"counted, not guessed. Never prints ladder steps or hidden scores.")
    sp.add_argument("--day", type=int, metavar="N", help="the day to check (default: the current day)")
    sp = add("canon", cmd_canon, "search canon facts and NPC canon notes"); sp.add_argument("search", nargs="+")
    sp = add("recap", cmd_recap, "'Previously on <campaign>' (read-only): 3 to 5 short lines from the last N turn summaries plus up to 2 fresh canon facts; "
             "never hidden data")
    sp.add_argument("--turns", type=int, default=5, metavar="N", help="how many recent turns to recap (default 5, at most 5 lines)")
    sp = add("history", cmd_history, "search logged turns (inputs, summary, prompt, notes, slips) and the migrated archive (data/history.json) for all words, newest first (read-only); "
             "`--last N` instead prints the last N logged turns in full, oldest first (for the director review)")
    sp.add_argument("words", nargs="*"); sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--last", type=int, default=None, metavar="N", help="print the last N logged turns in full (turn, day and time, inputs, prompt, summary, slips, review slips, notes), oldest first; no search words")
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
    sp = add("npc-intent", cmd_npc_intent, "set a cast NPC's intent for Campfire briefs (only the fields given change): --want, --fear, --trigger "
             "(the one active now), --refusal, --gesture (the last gesture), --voice LINE (repeat 3 to 5 times)", True)
    sp.add_argument("name")
    for f_, h_ in (("want", "what they want now"), ("fear", "what they fear now"), ("trigger", "the trigger active now"),
                   ("refusal", "what they would refuse"), ("last_gesture", "the gesture they used last (the scene avoids repeating it)")):
        sp.add_argument("--" + ("gesture" if f_ == "last_gesture" else f_), dest=f_, metavar="TEXT", help=h_)
    sp.add_argument("--voice", action="append", metavar="LINE", help="an example line in their voice; give it 3 to 5 times (replaces the set)")
    sp = add("npc-note", cmd_npc_note, "append a canon note to an NPC", True); sp.add_argument("name"); sp.add_argument("text", nargs="+")
    sp = add("agenda", cmd_agenda, "rewrite an NPC's agenda", True)
    sp.add_argument("name"); sp.add_argument("--want"); sp.add_argument("--next")
    def inferred_flag(sp, what):
        sp.add_argument("--inferred", action="store_true",
                        help=f"the {what} is inferred from the output, not stated: stores inferred: true with the quote (--evidence); "
                             "a later update without --inferred clears it")
    sp = add("quest-start", cmd_quest_start, "planned -> active (--inferred: the start is inferred from the output)", True)
    sp.add_argument("name"); inferred_flag(sp, "quest start")
    sp = add("quest-obj", cmd_quest_obj, "set an objective status (pending|done|failed|skipped)", True)
    sp.add_argument("name"); sp.add_argument("obj_id", help="objective id, e.g. o2 or 2 (or a named id such as sign_up_pulse)"); sp.add_argument("status", choices=OBJ_STATUSES)
    sp = add("quest-end", cmd_quest_end, "note that a quest apparently ended (--inferred: the turn and the quote, status unchanged); "
             "legacy form: active -> completed|failed", True)
    sp.add_argument("name"); sp.add_argument("result", nargs="?", choices=["completed", "failed"], help="legacy: the new status (not with --inferred)")
    sp.add_argument("--inferred", action="store_true", help="record an apparent end as a note with the quote (--evidence); Voyage owns quest "
                    "progress, so the status stays and `sync` confirms the end")
    sp = add("ledger", cmd_ledger, "change the hidden Standing score (optional module `standing`; refused when it is off), e.g. ledger +3 \"welcome dinner\"", True)
    sp.add_argument("delta", help="+N or -N"); sp.add_argument("reason", nargs="+")
    sp = add("fact", cmd_fact, "record a fact established in play that is not in any other file; --kind makes it a promise, condition, debt or plant", True)
    sp.add_argument("subject"); sp.add_argument("text", nargs="+")
    sp.add_argument("--kind", choices=FACT_KINDS, help="promise-style fact players may raise later (listed by `promises`)")
    sp.add_argument("--status", choices=FACT_STATUSES, help="open (default when --kind is given) or paid; needs --kind")
    inferred_flag(sp, "fact")
    sp = add("fact-status", cmd_fact_status, "set a promise-style fact (one with a kind) to open or paid", True)
    sp.add_argument("id", help="fact id, e.g. f012"); sp.add_argument("status", choices=FACT_STATUSES)
    inferred_flag(sp, "status change")
    sp = add("promises", cmd_promises, "list the facts that have a kind (promise, condition, debt, plant): open ones, or all with --all (read-only)")
    sp.add_argument("--all", action="store_true", help="include the paid ones"); sp.add_argument("--kind", choices=FACT_KINDS)
    sp = add("question", cmd_question, "add an open question to state (a director note about something unclear that matters)", True)
    sp.add_argument("text", nargs="+")
    sp = add("question-close", cmd_question_close, "close an open question the output has settled", True)
    sp.add_argument("id", help="question id, e.g. q1")
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
    inferred_flag(sp, "position")
    sp = add("time", cmd_time, f"set day / time block / clock (weekday is recomputed; Day 1 = {WEEKDAYS[0]})", True)
    sp.add_argument("--day", type=int); sp.add_argument("--block"); sp.add_argument("--clock", help="HH:MM, 24-hour")
    sp.add_argument("--allow-backward", action="store_true")
    inferred_flag(sp, "time")
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
    sp.add_argument("--arc-contact", action="store_true", help="the PC engaged the active arc's pressure this turn (stored on the turn; resets arc drift)")
    sp.add_argument("--escalated", action="store_true", help="the turn took the slow path (turn-brief --full, lookups): stored in the turn's timing (SES-9)")
    sp.add_argument("--timing", help=argparse.SUPPRESS)  # commit-turn's timing as JSON; not for hand use
    sp.add_argument("--scene-text", help=argparse.SUPPRESS)  # commit-turn --scene's scene text; not for hand use
    sp.add_argument("--rulings-json", help=argparse.SUPPRESS)  # commit-turn --rulings as JSON; not for hand use
    sp.add_argument("--campfire-ops-json", help=argparse.SUPPRESS)  # commit-turn --ops as JSON; not for hand use
    sp = add("thread-reveal", cmd_thread_reveal,
             "mark a reveal-ladder step as revealed; refuses a step from a later act, with earlier steps still hidden, "
             "or with an unconfirmed milestone gate, unless --force (--player-driven allows one act early)", True)
    sp.add_argument("name"); sp.add_argument("step", type=int)
    sp.add_argument("--gate-met", action="store_true", help="confirm the step's milestone gate has happened")
    sp.add_argument("--player-driven", action="store_true", help="the player reached this thread early: allow a step exactly one act ahead "
                    "(no unmet gate, all earlier steps revealed); recorded as player_driven with the evidence")
    sp.add_argument("--force", action="store_true", help="override the act / earlier-step / gate checks (recorded as forced)")
    sp = add("add-area", cmd_add_area,
             "add a new area inside an existing location (refuses unknown locations); pos and loc accept it afterwards", True)
    sp.add_argument("location"); sp.add_argument("area_id", help="lowercase-hyphenated, e.g. bakery-corner")
    sp.add_argument("--desc", required=True, help="one-line description of the area")
    sp.add_argument("--paths", help="comma-separated existing areas of the location this area connects to")
    sp = add("scene-start", cmd_scene_start, "open a scene (validates location and area; default: the first player character's place)", True)
    sp.add_argument("name"); sp.add_argument("--budget", type=int, required=True, help="turn budget (the campaign's scene budgets: `db.py bible budgets`)")
    sp.add_argument("--location"); sp.add_argument("--area")
    sp.add_argument("--card", help="scene card from the Planner (text or @file), stored in state.scene.card")
    sp.add_argument("--kind", choices=SCENE_KINDS, help="variety tag (SCN-1, SCN-7): " + "|".join(SCENE_KINDS)
                    + "; three of one kind in a row warns; plan-brief compares the mix with session zero's pillars")
    def meta(sp):
        sp.add_argument("--turn", type=int, help="turn (default: the current turn)")
        sp.add_argument("--evidence", help='default: "director log"')
    sp = add("scene-card", cmd_scene_card, "print the open scene's full card (resume shows a 400-character excerpt)")
    sp = add("scene-obstacle", cmd_scene_obstacle, "record an obstacle used in the open scene")
    sp.add_argument("text", nargs="+"); meta(sp)
    sp = add("scene-surprise", cmd_scene_surprise, "mark the open scene's one surprise as used")
    sp.add_argument("--force", action="store_true"); meta(sp)
    sp = add("scene-end", cmd_scene_end, "close the open scene"); meta(sp)
    sp = add("feedback", cmd_feedback, "store player feedback in state.feedback: scene feedback only when the player raises it (never ask for it at scene end); "
             "act feedback is the act retro")
    sp.add_argument("--kind", required=True, choices=FEEDBACK_KINDS)
    sp.add_argument("--best", help="best moment (text or @file)"); sp.add_argument("--drag", help="what dragged (text or @file)")
    sp.add_argument("--scene", help="scene name (default: the open scene; give it if scene-end already ran)")
    sp.add_argument("--notes"); sp.add_argument("--turn", type=int, required=True, help="current turn (not ahead of the log)")
    sp = add("review-add", cmd_review_add, "record director-review findings on a logged turn (write, under the lock): kept apart from the turn's own slips "
             "as review_slips with source review; resume's repeat slips count them. The review subagent stays read-only; the main chat runs this (D8)")
    sp.add_argument("--turn", type=int, required=True, help="the reviewed turn (it must be in the turn log)")
    sp.add_argument("--slips", required=True, help='findings "category: text; category: text" (text, @file or -); category is one of '
                    + "|".join(SLIP_CATS) + "; any other tag is refused")
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
    sp = add("planner", cmd_planner, "read-only: the planner's files waiting for the director in campaigns/NAME/planner/ (newest local view of origin/main, "
             "else HEAD; local git only): kind, file and first line; --all adds the applied ones; --show FILE prints one")
    sp.add_argument("--all", action="store_true", help="also list the files already applied"); sp.add_argument("--show", metavar="FILE", help="print this planner file")
    sp = add("planner-done", cmd_planner_done, "director: mark planner files applied (state.planner_applied gets file, blob hash, turn, time, note); "
             "a file edited later waits again; refused in the planner role")
    sp.add_argument("files", nargs="+", metavar="FILE"); sp.add_argument("--note", help="what was done with it")
    sp = add("planner-save", cmd_planner_save, "planner or all-in-one session: commit only campaigns/NAME/planner/ and push to origin main with retries "
             "(rebasing on a rejected push); refused in a trial run, on a VOYAGE_DATA copy, off main (exit 8) and in the director role (exit 4)")
    sp.add_argument("-m", "--message", metavar="TEXT"); sp.add_argument("--retries", type=int, default=4); sp.add_argument("--dry-run", action="store_true")
    sp = add("check-prompt", cmd_check_prompt, "check a prompt file (or - for stdin): the prompt limit (state.settings.prompt_limit, default 840), unknown names, split header, planned NPCs/quests")
    sp.add_argument("file"); sp.add_argument("--allow", help="comma-separated extra names to accept")
    sp.add_argument("--paste", metavar="FILE", help="the last exchange (Voyage's output and the players' inputs) saved to a file: lets the check judge a Cut: skip (CUT-2)")
    sp.add_argument("--inputs", metavar="TEXT", help="the players' inputs as text: lets the check judge a Cut: skip (CUT-2); without inputs that check is skipped")
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
             "--names; with --packet, a Campfire round packet instead of --paste) with compact briefs and rotated expression picks, places, quests, LIVE CHECKLIST")
    sp.add_argument("--paste", metavar="FILE", help="the last exchange (Voyage's output and the players' inputs) saved to a file")
    sp.add_argument("--packet", metavar="FILE", help="a Campfire round packet (the JSON file `gm pull --json` writes): names, declarations and the fight state come from its data")
    sp.add_argument("--names", help="comma-separated extra NPC names (aliases and short names work)")
    sp.add_argument("--full", metavar="NAME", help="also print the full brief of this NPC")
    sp = add("turn-brief", cmd_turn_brief,
             "read-only lean brief for the start of every turn (about 10 lines): turn and scene, present NPCs with rotated gesture picks, "
             "what is due, canon traps, open promises, open questions, variety, Studio cues, rules footer; --full prints prep's screen")
    sp.add_argument("--paste", metavar="FILE", help="the last exchange (Voyage's output and the players' inputs) saved to a file")
    sp.add_argument("--names", help="comma-separated extra NPC names (aliases and short names work)")
    sp.add_argument("--full", action="store_true", help="print prep's full screen instead (escalation, LOOP-6)")
    sp = add("commit-turn", cmd_commit_turn,
             "check the prompt file, then record a whole turn from a payload ({turn, ops, turn_log}; the prompt comes from the file) "
             "all or nothing, store scene.present and expression rotation, commit data/ locally and push every turn (push_every, default 1); "
             "FAIL in the prompt or any payload error writes nothing. After the push it fetches origin/main (a failure only warns), prints any "
             "Studio request and ends with NEXT BRIEF, the brief for the next turn; it records the turn's timing. Campfire mode "
             "(campaign.json campfire_room) takes --scene --rulings --ops instead of --prompt: the hidden-words check runs on the scene and the "
             "stakes lines, the three are recorded with the turn, and no NEXT BRIEF is printed")
    sp.add_argument("--prompt", metavar="FILE", help="the prompt file (Browser/paste mode); give this or --scene")
    sp.add_argument("--payload", required=True, metavar="FILE")
    sp.add_argument("--scene", metavar="FILE", help="Campfire mode: the scene text posted to the players (campfire/scene-N.md); needs --rulings and --ops")
    sp.add_argument("--rulings", metavar="FILE", help='Campfire mode: the rulings file ({"rulings": [...], "threat_moves": [...]}); with --scene')
    sp.add_argument("--ops", metavar="FILE", help="Campfire mode: the Campfire ops file (a JSON list of {op, evidence}); with --scene")
    sp.add_argument("--allow", metavar="TEXT", help="Campfire mode: comma-separated terms the director confirmed are public (skipped by the hidden-words check)")
    sp.add_argument("--dry-run", action="store_true", help="check and print the plan; write nothing (allowed in a trial run)")
    sp.add_argument("--push-every", type=int, default=None, help="push when this many commits are unpushed (default: campaign.json push_every, else 1: push every turn)")
    sp.add_argument("--retries", type=int, default=3, help="push attempts")
    sp.add_argument("--received", metavar="TIME", help="when the turn's input arrived: ISO 8601, or HH:MM / HH:MM:SS meaning today in local time "
                    "(stored in the turn log's timing; SES-9)")
    sp = add("wrap-up", cmd_wrap_up, "end of session: commit stray data changes, push every unpushed commit (retries), list pending Studio requests "
             "and open items, say 'safe to close' or why not")
    sp.add_argument("--retries", type=int, default=4)
    sp = add("undo-turn", cmd_undo_turn, "restore the snapshot taken before turn N and rewind state.turn (last 5 turns are kept)")
    sp.add_argument("n", type=int)
    sp = add("recover", cmd_recover, "clear a stale write lock; restore the pre-turn snapshot if a crashed record left the data half-applied")
    sp = add("sync", cmd_sync, "compare Voyage's exported state file with the database (SYNC-1 to SYNC-8). Dry run by default: writes a small "
             "digest (data/sync.json, with the export's SHA-256) and one state.sync_log entry, and prints the report in three classes "
             "(class 1 Voyage-owned state with its proposed patch, class 2 Voyage drift, class 3 director layer untouched). "
             "--apply applies class 1 only, plus the tick import and the undone marks, under the write lock with a snapshot "
             "(`undo-turn` rewinds it); refused in a trial run. Never reads the export for you: only the tool opens it")
    sp.add_argument("export", metavar="EXPORT", help="path to Voyage's exported state file (a full save); keep it out of git")
    sp.add_argument("--apply", action="store_true", help="apply class 1 (and the tick import, the undone marks); needs the user's yes first")

    # ---- arc planner (data/arcs.json, optional) ----
    def pmeta(sp):
        sp.add_argument("--turn", type=int, help="turn (default: the current turn)")
        sp.add_argument("--evidence", help=f'default: "{PLAN_EVIDENCE}"')
    sp = add("session-zero", cmd_session_zero,
             "show session zero (no options) or merge options into it: tone, lines (never happens), veils (offscreen only), play-style "
             "pillars 0-3, pacing, the hoped-for ending; --lines/--veils replace the whole list, --pillars merges per style")
    sp.add_argument("--file", metavar="F.json", help="JSON with any of tone, lines, veils, pillars, pacing, ending_hope, notes")
    sp.add_argument("--tone"); sp.add_argument("--lines", help='"a;b;c" (replaces the list)'); sp.add_argument("--veils", help='"a;b" (replaces the list)')
    sp.add_argument("--pillars", help="combat=3,social=2,exploration=1,mystery=2 (each 0 to 3; merged)")
    sp.add_argument("--pacing"); sp.add_argument("--ending-hope"); sp.add_argument("--notes")
    sp.add_argument("--players", type=int, help="how many PCs sit at the table (1 to 8); preflight checks the PC sheets against it"); pmeta(sp)
    sp = add("act-plan", cmd_act_plan, "create or replace act N's draft pitch from a JSON file {shared: {title, theme, question, builds_to, "
             "stakes_scale, ending_shape}, hidden: {turning_point, notes}}; refuses a closed act; an approved pitch stays approved")
    sp.add_argument("n", type=int); sp.add_argument("--file", required=True, metavar="F.json"); pmeta(sp)
    sp = add("act-approve", cmd_act_approve, "approve act N's pitch (needs title, theme, question, builds_to, stakes_scale, ending_shape; exit 4 otherwise)")
    sp.add_argument("n", type=int); sp.add_argument("--force", action="store_true", help="approve anyway (recorded)"); pmeta(sp)
    sp = add("act-deviation", cmd_act_deviation, "log a deviation from the bible's act plan on act N's pitch (shown on the planner page)", True)
    sp.add_argument("n", type=int); sp.add_argument("text", nargs="+")
    sp = add("act-close", cmd_act_close, "close act N with its retro (text or @file); the act retro feeds the next act pitch")
    sp.add_argument("n", type=int); sp.add_argument("--retro", required=True, metavar="TEXT|@FILE"); pmeta(sp)
    sp = add("arc-plan", cmd_arc_plan, "draft a new arc charter from a JSON file {act?, budget_turns?, blind?, shared, hidden}, or with --id update that "
             "arc (given keys merge; progress is kept; an approved or active arc stays so; closed ones are refused)")
    sp.add_argument("--file", required=True, metavar="F.json"); sp.add_argument("--id", metavar="A2"); pmeta(sp)
    sp = add("arc-approve", cmd_arc_approve, "approve an arc charter after checking every rule at once (exit 4 with the full list unless --force); "
             "needs --lines-checked once session zero holds lines or veils")
    sp.add_argument("id"); sp.add_argument("--force", action="store_true", help="approve anyway (recorded)")
    sp.add_argument("--lines-checked", action="store_true", help="confirm the charter respects session zero's lines and veils"); pmeta(sp)
    sp = add("arc", cmd_arc, "show an arc (default: the live one, else the newest draft or approved): director view with hidden fields, "
             "--shared for what the user sees, --list for one line per arc, --offramps to read its hidden off-ramp sketches (director only)")
    sp.add_argument("id", nargs="?"); sp.add_argument("--list", action="store_true"); sp.add_argument("--shared", action="store_true")
    sp.add_argument("--offramps", action="store_true", help="also print the arc's off-ramp sketches (hidden; director only, never in a prompt)")
    sp = add("arc-offramps", cmd_arc_offramps, "store the Planner's hidden off-ramp sketches on an arc from a JSON list (each sketch: thread, promise, "
             "front, face, first_move, all non-empty strings); replaces the earlier list; `arc ID --offramps` reads them")
    sp.add_argument("id"); sp.add_argument("--file", required=True, metavar="F.json"); pmeta(sp)
    sp = add("arc-pivot", cmd_arc_pivot, "read-only: is a pivot detected? Yes with --thread TEXT (an input plainly commits the PC to a new goal), or when the "
             f"last {PIVOT_TURNS} logged turns all lack arc contact and a pc-thread note is in or just before them; prints the live arc's best "
             "matching off-ramp only then (director only)")
    sp.add_argument("--thread", metavar="TEXT", help="the new goal the PC just committed to (what the PC did or said)")
    add("plan-brief", cmd_plan_brief, "planning brief for a planning session or the Planner (read-only, director view): session zero, act pitch, last "
        "retro, feedback, last two charters, PC sheets, pc_threads, ladders, quests, clocks, NPC agendas, canon, Voyage's inventions")
    add("preflight", cmd_preflight, "readiness check before the first turn of a chat and at each act start (read-only; exit 4 on any FAIL): "
        "git, skill version, session zero, PC sheets against the player count, act pitch approved, arc charter, deferred ops "
        "from the act pitch, planner page, then the act's agreed checklist")
    sp = add("planner-page", cmd_planner_page, "render the read-only, spoiler-safe Arc Planner page (--out FILE; exit 4 and nothing written when a hidden "
             "term would show) and/or remember where it is published (--set-url URL)")
    sp.add_argument("--out", metavar="FILE"); sp.add_argument("--set-url", metavar="URL"); pmeta(sp)
    sp = add("scan", cmd_scan, "read-only hidden-term scan of a text the user may see (a recap, a pivot line, a sync report, a subagent's result): "
             "the file, or - for stdin. Exit 0 and one line when clean; exit 4 and a line per hit (term, source, excerpt) when it holds a hidden "
             "arc field, off-ramp, hidden ladder step word, campaign hidden word or hidden-score word; revealed steps and public_ok terms pass")
    sp.add_argument("file", help="the text file, or - for stdin")
    sp = add("precheck", cmd_precheck,
             "read-only pre-check of a Campfire post before gm post (director/playbooks/campfire.md step 6): the hidden-words check on the "
             "scene and the stakes lines (exit 4 on a hit, as scan), and WARN lines for the speaker blocks (a paragraph starting with "
             "@Name): one that names nobody in the room (not a character, a scene NPC or a threat on the table, nor added by the post's "
             "ops), a player character's block that is not a quote from their input, a bare @ line, a long delivery note")
    sp.add_argument("--scene", metavar="FILE", required=True, help="the scene text about to be posted (campfire/scene-N.md)")
    sp.add_argument("--packet", metavar="FILE", required=True,
                    help="the round or result packet of this round (campfire/round-N.json or result-N.json): the party, the scene NPCs, the threats and the inputs")
    sp.add_argument("--rulings", metavar="FILE", help="the rulings file, for the stakes lines")
    sp.add_argument("--ops", metavar="FILE", help="the ops file about to be posted: a scene op or threat-add op here counts as in the room")
    sp.add_argument("--allow", metavar="TEXT", help="comma-separated terms the director confirmed are public (skipped by the hidden-words check)")
    sp = add("check", cmd_check,
             "the check stage of a Campfire post (director/playbooks/campfire-pipeline.md): every code check on the draft scene (hidden words, the "
             "hard noes, speaker blocks, cast names, places, zones, op evidence, approved reaction lines, the input-to-paragraph map) and, with "
             "--answers, the checker's flags. Exit 0 passed (warnings allowed), 1 flags to fix, 4 a hidden term, 9 STOP after three rewrites: "
             "show the GM. Each run is appended to campfire/check-N.json")
    sp.add_argument("--scene", metavar="FILE", required=True, help="the draft scene")
    sp.add_argument("--packet", metavar="FILE", required=True, help="the reacted packet (gm react --json), or the result packet")
    sp.add_argument("--ops", metavar="FILE", help="the ops file about to be posted")
    sp.add_argument("--reactions", metavar="FILE", help="the reactions file, when the packet carries no reactions list")
    sp.add_argument("--map", metavar="FILE", help='the input-to-paragraph map: {"inputs": [{"player": ID, "paragraphs": [N, ...]}]} (paragraphs numbered from 1)')
    sp.add_argument("--answers", metavar="FILE", help="the checker subagent's JSON answers to check-brief's questions")
    sp.add_argument("--round", type=int, metavar="N", help="the round (default: the packet's)")
    sp.add_argument("--log", metavar="FILE", help="the check log (default campaigns/NAME/campfire/check-N.json)")
    sp.add_argument("--json", metavar="FILE", help="also write this run's flags to FILE")
    sp.add_argument("--allow", metavar="TEXT", help="comma-separated terms the director confirmed are public (skipped by the hidden-words check)")
    sp.add_argument("--reset", action="store_true", help="start a fresh log (the GM has said what to do after a STOP)")
    sp = add("check-brief", cmd_check_brief,
             "print the checker subagent's whole brief for a draft: the fixed questions, the hard noes, the reacted packet and the draft, and nothing else")
    sp.add_argument("--scene", metavar="FILE", required=True, help="the draft scene")
    sp.add_argument("--packet", metavar="FILE", required=True, help="the reacted packet")
    sp = add("hard-noes", cmd_hard_noes,
             "list, add (--add PHRASE) or remove (--remove PHRASE) the campaign's hard noes: phrases agreed at the table, kept in campaign.json on "
             "this machine; prep matches the players' inputs against them and check matches the draft, both in code")
    sp.add_argument("--add", action="append", metavar="PHRASE")
    sp.add_argument("--remove", action="append", metavar="PHRASE")
    sp = add("arc-start", cmd_arc_start, "approved -> active; start_turn = this turn (when its first pressure shows in Voyage's output); one active arc at a time", True)
    sp.add_argument("id")
    sp = add("arc-move", cmd_arc_move, "mark move N (1-based) of a front done (the world moved it on, or the PC stopped it)", True)
    sp.add_argument("id"); sp.add_argument("front", help="front name (fuzzy)"); sp.add_argument("n", type=int)
    sp = add("arc-clue", cmd_arc_clue, "mark clue N (1-based) found", True); sp.add_argument("id"); sp.add_argument("n", type=int)
    sp = add("arc-contact", cmd_arc_contact, "the antagonist's face reached the PC on screen", True); sp.add_argument("id")
    sp = add("arc-reveal", cmd_arc_reveal, "the twist was revealed in play (its keywords stop being blocked by check-prompt)", True); sp.add_argument("id")
    sp = add("arc-review", cmd_arc_review, "log a midpoint, drift or scene review of the arc", True)
    sp.add_argument("id"); sp.add_argument("--kind", required=True, choices=("midpoint", "drift", "scene")); sp.add_argument("--notes", required=True)
    sp = add("arc-deviation", cmd_arc_deviation, "log a deviation of the arc from the act plan (shown on the planner page)", True)
    sp.add_argument("id"); sp.add_argument("text", nargs="+")
    sp = add("arc-close", cmd_arc_close, "close an arc with its retro (turns used, budget, clues found/placed are computed from the data); "
             "needs one of --best --drag --weakest --notes", True)
    sp.add_argument("id"); sp.add_argument("--status", choices=("closed", "set_aside"), default="closed")
    for f in ("best", "drag", "wins", "spotlight", "threads-closed", "weakest", "notes"):
        sp.add_argument(f"--{f}", help="text or @file")
    sp = add("arc-adopt", cmd_arc_adopt, "a pivot draft becomes provisional (live, off the planner page until approved) after the PIV-5 limits are checked "
             "(no twist; at most one new NPC; one front with 2 or 3 moves; 3 clues; budget 10 to 15; no session-zero line or veil), and the live arc is "
             "parked; lists every problem and exits 4 unless --force", True)
    sp.add_argument("id"); sp.add_argument("--force", action="store_true", help="adopt anyway (recorded)")
    sp = add("arc-unpark", cmd_arc_unpark, "go back: the parked arc is active again and the provisional pivot arc closes as set_aside, its short retro "
             "being --notes, in one write", True)
    sp.add_argument("id", metavar="OLD_ID"); sp.add_argument("--notes", required=True, help="what the PC did in the pivot arc (its short retro)")
    sp = add("pc-thread", cmd_pc_thread, "note what the PC keeps returning to, as what the PC did (private; feeds the next charter)", True)
    sp.add_argument("text", nargs="+")
    sp.add_argument("--pc", help="the player character (needed when the campaign has two or more; one PC is the default)")
    return p


WRITE_CMDS = {"review-add", "add-npc", "npc-seen", "npc-note", "agenda", "quest-start", "quest-obj", "quest-end", "ledger", "fact",
              "fact-status", "question", "question-close",
              "pc-add", "pos", "time", "clock-add", "clock-done", "turn", "thread-reveal", "add-area", "scene-start",
              "scene-obstacle", "scene-surprise", "scene-end", "feedback", "studio-request", "studio-done", "save",
              "session-zero", "act-plan", "act-approve", "act-deviation", "act-close", "arc-plan", "arc-approve", "arc-start", "arc-move",
              "arc-clue", "arc-contact", "arc-reveal", "arc-review", "arc-deviation", "arc-close", "arc-offramps", "arc-adopt", "arc-unpark",
              "pc-thread", "planner-page", "planner-done"}


def is_write(a):
    if a.cmd == "pc-sheet":  # show mode (no fields given) is a read
        return any(getattr(a, f) is not None for f in PC_SHEET_FIELDS)
    if a.cmd == "session-zero":  # no options: show it
        return any(getattr(a, f) is not None for f in ("file", "tone", "lines", "veils", "pillars", "pacing", "ending_hope", "notes", "players"))
    if a.cmd == "planner-page":  # only --set-url writes
        return a.set_url is not None
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
    cmd = next((x for x in argv if not x.startswith("-")), None)
    if cmd not in NO_CAMPAIGN_CMDS and not {"-h", "--help"} & set(argv) and (name or CAMPAIGN is None):
        init_campaign(name, strict=True)
    a = build_parser().parse_args(argv)
    try:
        if a.cmd not in NO_CAMPAIGN_CMDS:
            print(campaign_line(CAMPAIGN, CFG))  # SEL-1: every output starts with the campaign's name
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
