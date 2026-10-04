"""The Arc Planner page: a read-only, spoiler-safe HTML view of the story plan (Python 3 standard library only).

render(arcs, ctx) -> one self-contained HTML fragment for the Artifact tool: no doctype/html/head/body tags, starts with
<title>, no scripts, no storage, fonts only through fonts.googleapis.com with fallback stacks. It shows shared fields
(what the user already saw in chat), session zero, progress and player-visible state. Never hidden fields, pc_threads,
the ledger or hidden ladder steps. A provisional arc (a pivot the user has not approved) is not shown until it is approved;
a parked arc is shown as parked; off-ramps are never shown and their text is one of the hidden terms. Before returning,
every string that went on the page is scanned for hidden terms; a hit raises Leak and nothing is written.

arcs : the parsed data/arcs.json (skeleton when the file is missing)
ctx  : display, day, weekday, act, turn, acts [{n, from_day, to_day}], quests [{name, goal}], revealed [text],
       ladder_terms {term: source} (strong terms of hidden ladder steps), public_names [names of NPCs in play]
"""
import html
import re
import unicodedata

SHARED_ORDER = (("title", "Title"), ("tone", "Tone"), ("promise", "Promise"), ("premise", "Premise"),
                ("pressure", "Pressure"), ("set_pieces", "Set-piece kinds"), ("pc_tests", "PC tests"),
                ("subplot", "Subplot"), ("climax_kind", "Kind of climax"), ("ending_shape", "Ending shape"),
                ("stakes", "Stakes"), ("wins_on_offer", "Wins on offer"), ("echoes", "Echoes"), ("seeds", "Seeds"),
                ("backstory_hooks", "Backstory hooks"))
BLIND_KEYS = ("title", "promise", "tone")  # all the user approved of a blind arc
ACT_ORDER = (("title", "Title"), ("theme", "Theme"), ("question", "Big question"), ("builds_to", "Builds toward"),
             ("stakes_scale", "Stakes scale"), ("ending_shape", "Ending shape"))
STATUS_WORDS = {"draft": "Draft", "approved": "Approved", "active": "In play", "provisional": "Provisional", "parked": "Parked",
                "closed": "Closed", "set_aside": "Set aside"}
OFFRAMP_KEYS = ("thread", "promise", "front", "face", "first_move")  # the hidden sketches of an arc (hidden.offramps)
PILLAR_WORDS = ("off", "light", "regular", "heavy")  # 0 to 3

# every color is a token; dark values are written twice (system preference, and an explicit data-theme)
LIGHT = {"bg": "#F3F4F1", "surface": "#FFFFFF", "fg": "#1C2321", "muted": "#5B6661", "line": "#D5DAD5",
         "accent": "#2F6F8F", "warn": "#A8571F", "soft": "#ECEFEA", "accent-bg": "#E2EDF2", "warn-bg": "#F7E8DB",
         "on-accent": "#FFFFFF"}
DARK = {"bg": "#121614", "surface": "#1A1F1C", "fg": "#E6EAE6", "muted": "#9AA6A0", "line": "#2A322E",
        "accent": "#7DB4CF", "warn": "#E09A5F", "soft": "#202622", "accent-bg": "#1B2A32", "warn-bg": "#31261B",
        "on-accent": "#0C1A21"}


class Leak(Exception):
    """A hidden term would appear on the page. .hits is [(term, where)]."""

    def __init__(self, hits):
        super().__init__("hidden term(s) in the page text: " + ", ".join(f'"{t}" ({w})' for t, w in hits))
        self.hits = hits


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def _has_term(text, term):
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?:s|es|ed|d|ing)?(?![a-z0-9])", _norm(text)) is not None


def as_list(v):
    if v in (None, "", [], {}):
        return []
    return [x for x in v if str(x).strip()] if isinstance(v, (list, tuple)) else [v]


def visible_fields(arc):
    """[(key, label, value)] of an arc's shared fields the user may see (a blind arc: title, promise and tone only)."""
    sh = arc.get("shared") or {}
    keys = BLIND_KEYS if arc.get("blind") else None
    return [(k, lab, sh.get(k)) for k, lab in SHARED_ORDER if (keys is None or k in keys) and sh.get(k) not in (None, "", [], {})]


# ----------------------------------------------------------------------------
# page text that is recorded for the spoiler scan
# ----------------------------------------------------------------------------
class Page:
    def __init__(self, ctx):
        self.ctx = ctx
        self.texts = []  # (text, origin) of every data string written to the page
        self.origin = "shared"  # the origin of strings written without one; "adopted" inside the card of an arc a pivot made

    def e(self, s, origin=None):
        s = "" if s is None else str(s)
        if s.strip():
            self.texts.append((s, origin or self.origin))
        return html.escape(s, quote=True)


def chip(label, kind=""):
    return f'<span class="{"chip " + kind if kind else "chip"}">{label}</span>'


def label(text):
    return f'<span class="lab">{text}</span>'


def facts(rows):
    rows = [(k, v) for k, v in rows if v]
    if not rows:
        return ""
    return '<dl class="facts">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>"


def ul(pg, items, cls="list", origin=None):
    items = as_list(items)
    return f'<ul class="{cls}">' + "".join(f"<li>{pg.e(x, origin)}</li>" for x in items) + "</ul>" if items else ""


def tags(pg, items):
    items = as_list(items)
    return '<ul class="tags">' + "".join(f"<li>{pg.e(x)}</li>" for x in items) + "</ul>" if items else ""


def pips(n, name, pg):
    n = n if isinstance(n, int) and not isinstance(n, bool) else 0
    n = max(0, min(3, n))
    dots = "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(3))
    return (f'<span class="pips" role="img" aria-label="{pg.e(name)}: {n} of 3">{dots}</span>'
            f'<span class="pip-word">{PILLAR_WORDS[n]}</span>')


def progress(arc, turn, pg):
    """Bar of turns used against the budget, ticks at 60% (midpoint review) and 100% (budget)."""
    budget = arc.get("budget_turns") or 30
    start = arc.get("start_turn")
    if arc.get("status") != "active" or start is None:
        return ""
    used = max(0, turn - start)
    pct = used * 100 // budget
    over = used > budget
    note = (f"{used - budget} over budget" if over else f"{pct}% of budget")
    return (f'<div class="progress"><div class="prog-head"><span class="num">{used} of {budget} turns</span>'
            f'<span class="prog-note{" warn" if over else ""}">{note}</span></div>'
            f'<div class="track" role="progressbar" aria-label="Turns used" aria-valuemin="0" aria-valuemax="{budget}" '
            f'aria-valuenow="{min(used, budget)}"><div class="fill{" over" if over else ""}" style="width:{min(100, pct)}%"></div>'
            f'<span class="tick" style="left:60%"></span></div>'
            f'<div class="scale"><span style="left:60%">midpoint review</span><span class="end">budget</span></div></div>')


# ----------------------------------------------------------------------------
# sections
# ----------------------------------------------------------------------------
def season_rail(pg):
    c = pg.ctx
    acts, day = c.get("acts") or [], c.get("day") or 1
    if not acts:
        return ""
    segs = []
    for a in acts:
        lo, hi = a.get("from_day"), a.get("to_day")
        here = a.get("n") == c.get("act")
        span = f"Day {lo}" + (f"-{hi}" if hi else "+") if lo else ""
        today = ""
        if here and lo and hi and hi >= lo:
            pos = max(0.0, min(1.0, (day - lo + 0.5) / (hi - lo + 1)))
            today = f'<span class="today" style="left:{pos * 100:.1f}%" title="Day {day}"></span>'
        cur = ' aria-current="step"' if here else ""
        segs.append(f'<li class="seg{" here" if here else ""}"{cur}>'
                    f'<span class="seg-n">Act {a.get("n")}</span><span class="seg-d">{span}</span>{today}</li>')
    return f'<ol class="rail" aria-label="The acts of the story">{"".join(segs)}</ol>'


def header(pg):
    c = pg.ctx
    slate = [("Day", c.get("day")), ("Weekday", c.get("weekday")), ("Act", c.get("act")), ("Turn", c.get("turn"))]
    cells = "".join(f'<div class="cell"><span class="lab">{k}</span><span class="val num">{pg.e(v, "public")}</span></div>'
                    for k, v in slate if v not in (None, ""))
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (("act", "Act"), ("arc", "Arc"), ("next", "Coming up"),
                                                          ("past", "Past arcs"), ("style", "Session zero"), ("threads", "Threads")))
    return (f'<header class="top"><div class="mast"><div><span class="lab">Arc planner</span>'
            f'<h1>{pg.e(c.get("display"), "public")}</h1></div>'
            f'<p class="mast-note">Read-only. Steer the story in chat.<br><span class="num">Generated at turn {pg.e(c.get("turn"), "public")}</span></p></div>'
            f'<div class="slate">{cells}</div>{season_rail(pg)}<nav class="nav" aria-label="Sections">{nav}</nav></header>')


def section(sid, title, body):
    return f'<section id="{sid}"><h2 class="sec"><span>{title}</span></h2>{body}</section>'


def empty(text):
    return f'<p class="empty">{text}</p>'


def act_block(pg, data):
    c = pg.ctx
    act = next((a for a in data.get("acts") or [] if a.get("n") == c.get("act")), None)
    if not act:
        return section("act", f"Act {c.get('act')}", empty(
            "No pitch for this act yet. Say &ldquo;plan the act&rdquo; in chat and the director will pitch one."))
    sh, devs = act.get("shared") or {}, as_list(act.get("deviations"))
    status = act.get("status")
    bits = [chip(STATUS_WORDS.get(status, status or ""), "st-" + str(status))]
    if devs:
        bits.append(chip("Deviating from the act plan", "warn"))
    rows = [(lab, pg.e(sh.get(k))) for k, lab in ACT_ORDER[1:] if sh.get(k)]
    q = sh.get("question")
    body = (f'<article class="act"><div class="meta">{"".join(bits)}</div>'
            f'<h3 class="act-title">{pg.e(sh.get("title") or "Untitled act")}</h3>'
            + (f'<p class="act-q">{pg.e(q)}</p>' if q else "")
            + facts([r for r in rows if r[0] != "Big question"])
            + (f'<div class="devs"><h4>{label("Where it departs from the plan")}</h4><ul class="list">'
               + "".join(f'<li><span class="num turn">t{pg.e(d.get("turn"), "public")}</span> {pg.e(d.get("text"))}</li>'
                         for d in devs if isinstance(d, dict)) + "</ul></div>" if devs else "")
            + "</article>")
    return section("act", f"Act {c.get('act')}", body)


def arc_card(pg, arc, compact=False, current=False):
    """One arc's card. The strings of an arc that a pivot made (it has `adopted_turn`) carry the origin "adopted": the user approved
    that arc, so its text may echo the off-ramp it grew from (see scan)."""
    pg.origin = "adopted" if arc.get("adopted_turn") is not None else "shared"
    try:
        return _arc_card(pg, arc, compact, current)
    finally:
        pg.origin = "shared"


def _arc_card(pg, arc, compact, current):
    sh = arc.get("shared") or {}
    st = arc.get("status")
    blind = bool(arc.get("blind"))
    chips = [chip(STATUS_WORDS.get(st, st or ""), "st-" + str(st))]
    if sh.get("stakes") in ("personal", "wide") and not blind:
        chips.append(chip(f"{sh['stakes']} stakes"))
    if blind:
        chips.append(chip("Blind arc"))
    dev = [d for d in as_list(sh.get("deviations")) if isinstance(d, dict)]
    if dev and not blind:
        chips.append(chip("Deviating from the act plan", "warn"))
    head = (f'<div class="meta"><span class="lab">Arc {pg.e(arc.get("id"), "public")}'
            + (f' &middot; Act {pg.e(arc.get("act"), "public")}' if arc.get("act") else "") + f'</span>{"".join(chips)}</div>')
    title = f'<h3 class="arc-title">{pg.e(sh.get("title") or "Untitled arc")}</h3>'
    promise = sh.get("promise")
    prom = f'<p class="promise">{pg.e(promise)}</p>' if promise else '<p class="promise dim">No promise yet.</p>'
    tone = f'<p class="tone">{label("Tone")} {pg.e(sh.get("tone"))}</p>' if sh.get("tone") else ""
    out = [head, title, prom, tone]
    if current:
        out.append(progress(arc, pg.ctx.get("turn") or 0, pg))
    if blind:
        out.append(empty("The rest of this arc stays hidden, as you asked."))
        return f'<article class="arc{" current" if current else ""}">{"".join(out)}</article>'
    if sh.get("premise"):
        out.append(f'<p class="prose">{pg.e(sh["premise"])}</p>')
    tests = sh.get("pc_tests") if isinstance(sh.get("pc_tests"), dict) else {}
    rows = [("Pressure", pg.e(sh.get("pressure")) if sh.get("pressure") else ""),
            ("Set-piece kinds", tags(pg, sh.get("set_pieces"))),
            ("How each hero is tested", '<ul class="tests">' + "".join(
                f'<li><span class="who">{pg.e(k)}</span><span class="cat">{pg.e(v)}</span></li>' for k, v in tests.items() if str(v).strip()) + "</ul>" if tests else ""),
            ("Subplot", pg.e(sh.get("subplot")) if sh.get("subplot") else ""),
            ("Kind of climax", pg.e(sh.get("climax_kind")) if sh.get("climax_kind") else ""),
            ("Ending shape", pg.e(sh.get("ending_shape")) if sh.get("ending_shape") else "")]
    if not compact:
        rows += [("Wins on offer", ul(pg, sh.get("wins_on_offer"))),
                 ("Your choices that shaped this arc", ul(pg, sh.get("echoes"))),
                 ("Hooks from your backstory", ul(pg, sh.get("backstory_hooks"))),
                 ("Seeds", ul(pg, sh.get("seeds")))]
    else:
        rows = [r for r in rows if r[0] in ("Set-piece kinds", "Kind of climax", "Ending shape")]
    out.append(facts(rows))
    if dev and not compact:
        out.append(f'<div class="devs"><h4>{label("Where it departs from the act plan")}</h4><ul class="list">'
                   + "".join(f'<li><span class="num turn">t{pg.e(d.get("turn"), "public")}</span> {pg.e(d.get("text"))}</li>' for d in dev)
                   + "</ul></div>")
    return f'<article class="arc{" current" if current else ""}">{"".join(out)}</article>'


def arc_sections(pg, data):
    # a provisional arc (a pivot the user has not approved yet) is on no list: it appears only once it is approved and active
    arcs = [a for a in data.get("arcs") or [] if isinstance(a, dict) and a.get("status") != "provisional"]
    live = [a for a in arcs if a.get("status") == "active"]
    nxt = [a for a in arcs if a.get("status") in ("draft", "approved")]
    parked = [a for a in arcs if a.get("status") == "parked"]
    past = [a for a in arcs if a.get("status") in ("closed", "set_aside")]
    if live:
        body = arc_card(pg, live[0], current=True)
    elif not arcs:
        body = empty("No arc planned yet. Say &ldquo;plan the arc&rdquo; in chat.")
    else:
        body = empty("No arc is live right now. Say &ldquo;plan the arc&rdquo; in chat, or play on: the open threads keep moving.")
    if parked:
        body += (f'<p class="paused">{label("Paused for now")}</p><div class="stack">'
                 + "".join(arc_card(pg, a, compact=True) for a in parked) + "</div>")
    cur = section("arc", "Current arc", body)
    if nxt:
        nxt_html = '<div class="stack">' + "".join(arc_card(pg, a, compact=True) for a in nxt) + "</div>"
    else:
        nxt_html = empty("Nothing waiting. The next arc is planned together once this one closes.")
    if past:
        rows = []
        for a in reversed(past):
            sh, rt = a.get("shared") or {}, a.get("retro") or {}
            used, bud = rt.get("turns_used"), rt.get("budget") or a.get("budget_turns")
            turns = f'<span class="num">{pg.e(used, "public")} of {pg.e(bud, "public")} turns</span>' if used is not None and bud else ""
            bits = "".join(f'<p class="retro"><span class="lab">{k}</span> {pg.e(rt.get(f))}</p>'
                           for k, f in (("Best moment", "best"), ("Dragged", "drag")) if rt.get(f))
            rows.append(f'<li class="past"><div class="meta"><span class="lab">Arc {pg.e(a.get("id"), "public")}</span>'
                        f'{chip(STATUS_WORDS.get(a.get("status"), ""), "st-" + str(a.get("status")))}{turns}</div>'
                        f'<h3 class="past-title">{pg.e(sh.get("title") or "Untitled arc")}</h3>'
                        + (f'<p class="past-promise">{pg.e(sh.get("promise"))}</p>' if sh.get("promise") else "") + bits + "</li>")
        past_html = f'<ol class="past-list">{"".join(rows)}</ol>'
    else:
        past_html = empty("No finished arcs yet.")
    return cur, section("next", "Coming up", nxt_html), section("past", "Past arcs", past_html)


def session_zero(pg, data):
    sz = data.get("session_zero") or {}
    pillars = sz.get("pillars") if isinstance(sz.get("pillars"), dict) else {}
    has = any(sz.get(k) for k in ("tone", "lines", "veils", "pacing", "ending_hope")) or pillars
    if not has:
        return section("style", "Session zero", empty("Not recorded yet. The director asks a few questions about tone, "
                                                      "limits and style before the first arc."))
    meters = ('<ul class="pillars">' + "".join(
        f'<li><span class="pname">{pg.e(k)}</span>{pips(v, k, pg)}</li>' for k, v in pillars.items()) + "</ul>") if pillars else ""
    lines = ul(pg, sz.get("lines"), "list cross")
    veils = ul(pg, sz.get("veils"), "list veil")
    body = (facts([("Tone", pg.e(sz.get("tone")) if sz.get("tone") else ""), ("Pacing", pg.e(sz.get("pacing")) if sz.get("pacing") else ""),
                   ("The ending you hope for", pg.e(sz.get("ending_hope")) if sz.get("ending_hope") else ""),
                   ("What you like to play", meters)])
            + facts([("Lines: never happens", lines), ("Veils: offscreen only", veils)]))
    return section("style", "Session zero", f'<div class="panel">{body}</div>')


def threads(pg):
    c = pg.ctx
    qs = [q for q in c.get("quests") or [] if q.get("name")]
    rev = [r for r in c.get("revealed") or [] if str(r).strip()]
    quests = ('<ul class="quests">' + "".join(
        f'<li><span class="qname">{pg.e(q["name"], "public")}</span>'
        + (f'<span class="qgoal">{pg.e(q.get("goal"), "public")}</span>' if q.get("goal") else "") + "</li>" for q in qs) + "</ul>") if qs else ""
    revealed = ('<ul class="list">' + "".join(f"<li>{pg.e(r, 'revealed')}</li>" for r in rev) + "</ul>") if rev else ""
    if not qs and not rev:
        return section("threads", "Open threads", empty("No quests are running and nothing has come to light yet."))
    return section("threads", "Open threads", facts([("Active quests", quests), ("Come to light so far", revealed)]))


# ----------------------------------------------------------------------------
# spoiler scan
# ----------------------------------------------------------------------------
def hidden_terms(arcs, ctx):
    """[(term, where)]: twist keywords of unrevealed twists, antagonist names not yet public, the text of every stored off-ramp
    sketch (hidden.offramps; where reads "arc A1 off-ramp promise"), strong hidden-ladder terms."""
    out = []
    public = {_norm(n) for n in ctx.get("public_names") or []}
    for a in arcs:
        if not isinstance(a, dict):
            continue
        hd, sh = a.get("hidden") or {}, a.get("shared") or {}
        tw = hd.get("twist") if isinstance(hd.get("twist"), dict) else {}
        if tw.get("revealed_turn") is None:
            out += [(_norm(k), f"arc {a.get('id')} twist keyword") for k in as_list(tw.get("keywords")) if len(_norm(k)) >= 3]
        an = hd.get("antagonist") if isinstance(hd.get("antagonist"), dict) else {}
        name = _norm(an.get("name") or "")
        if len(name) >= 3 and an.get("contact_turn") is None and name not in public:
            shared_text = " ".join(str(v) for v in sh.values() if not isinstance(v, (dict, list))) + " " + \
                " ".join(str(x) for v in sh.values() if isinstance(v, (list, dict)) for x in (v.values() if isinstance(v, dict) else v))
            if not _has_term(shared_text, name):
                out.append((name, f"arc {a.get('id')} antagonist"))
        for sketch in as_list(hd.get("offramps")):  # off-ramps are never on the page: each of their texts is a term the page must not hold
            for k in OFFRAMP_KEYS:
                t = _norm(sketch.get(k) or "") if isinstance(sketch, dict) else ""
                if len(t) >= 4:
                    out.append((t, f"arc {a.get('id')} off-ramp {k}"))
    out += [(t, src) for t, src in (ctx.get("ladder_terms") or {}).items()]
    return out


def scan(pg, arcs):
    hits = []
    for term, where in hidden_terms(arcs, pg.ctx):
        skip = ("revealed", "adopted") if " off-ramp " in where else ("revealed",)  # an adopted pivot arc may echo the off-ramp it grew from
        for text, origin in pg.texts:
            if origin not in skip and _has_term(text, term):
                hits.append((term, where))
                break
    if hits:
        raise Leak(hits)


# ----------------------------------------------------------------------------
# styles
# ----------------------------------------------------------------------------
FONTS_URL = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700"
             "&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap")
FONT_STACKS = (";--display:\"Bricolage Grotesque\",\"Avenir Next\",\"Segoe UI\",system-ui,sans-serif;"
               "--body:\"Source Serif 4\",Charter,\"Iowan Old Style\",Georgia,serif;"
               "--mono:\"JetBrains Mono\",ui-monospace,\"SF Mono\",Menlo,Consolas,monospace;color-scheme:light")


def tokens(vals, extra=""):
    return ";".join(f"--{k}:{v}" for k, v in vals.items()) + extra


def root_css():
    """Color and font tokens (light; dark by system preference; dark by data-theme). The site index reuses them."""
    return (":root{" + tokens(LIGHT, FONT_STACKS) + "}\n"
            "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]){" + tokens(DARK, ";color-scheme:dark") + "}}\n"
            ":root[data-theme=\"dark\"]{" + tokens(DARK, ";color-scheme:dark") + "}")


CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1.0625rem/1.58 var(--body);font-variant-numeric:tabular-nums}
.wrap{max-width:60rem;margin-inline:auto;padding-inline:16px;padding-block:28px 72px}
.wrap>*{min-width:0}
h1,h2,h3,h4{text-wrap:balance;margin:0;min-width:0}
p{margin:0;min-width:0}
.num,.lab,.chip,.nav,.seg-n,.seg-d,.scale,.pip-word,.prog-note,.turn{font-family:var(--mono);font-variant-numeric:tabular-nums}
.lab{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);font-weight:500}
a{color:var(--accent);text-underline-offset:3px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:2px}

.top{display:flex;flex-direction:column;gap:18px}
.mast{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:10px 24px}
.mast h1{font:700 1.7rem/1.05 var(--display);letter-spacing:-.015em;margin-top:6px}
.mast-note{font-size:.88rem;color:var(--muted);line-height:1.45;max-width:30ch}
.mast-note .num{font-size:.72rem;letter-spacing:.06em}
.slate{display:grid;grid-template-columns:repeat(auto-fit,minmax(84px,1fr));border:1px solid var(--line);background:var(--surface)}
.slate .cell{display:flex;flex-direction:column;gap:2px;padding:9px 12px 10px;border-inline-start:1px solid var(--line);min-width:0}
.slate .cell:first-child{border-inline-start:0}
.slate .val{font-size:1.02rem;font-weight:500}
.rail{list-style:none;margin:0;padding:0;display:flex;gap:4px}
.seg{position:relative;flex:1 1 0;min-width:0;display:flex;flex-direction:column;gap:1px;padding:8px 8px 9px;border-top:3px solid var(--line);background:var(--soft)}
.seg.here{border-top-color:var(--accent);background:var(--accent-bg)}
.seg-n{font-size:.74rem;font-weight:500;letter-spacing:.04em;text-transform:uppercase}
.seg-d{font-size:.66rem;color:var(--muted);letter-spacing:.02em}
.today{position:absolute;bottom:-1px;width:2px;height:9px;background:var(--accent);transform:translateX(-1px)}
.nav{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.76rem;letter-spacing:.04em;text-transform:uppercase}
.nav a{text-decoration:none;color:var(--muted);padding-block:2px;border-bottom:1px solid transparent}
.nav a:hover{color:var(--accent);border-bottom-color:var(--accent)}

section{margin-top:54px;scroll-margin-top:16px}
.sec{display:flex;align-items:center;gap:14px;margin-bottom:22px;font:500 .78rem var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.sec::after{content:"";flex:1;height:1px;background:var(--line)}
.empty{color:var(--muted);font-style:italic;max-width:46ch;padding-block:6px}

.meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px}
.chip{display:inline-block;font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;padding:3px 8px 2px;border:1px solid var(--line);color:var(--muted);border-radius:3px;line-height:1.5;white-space:nowrap}
.chip.st-active{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.chip.st-approved{border-color:var(--accent);color:var(--accent)}
.chip.st-draft,.chip.st-parked{border-style:dashed}
.chip.st-closed{background:var(--soft)}
.chip.st-set_aside,.chip.warn{border-color:var(--warn);color:var(--warn);background:var(--warn-bg)}
.paused{margin:26px 0 10px}

.arc,.act,.panel{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:22px 20px;display:flex;flex-direction:column;gap:14px;min-width:0}
.arc.current{border-inline-start:5px solid var(--accent);padding-inline-start:18px}
.act{border-radius:0;border-width:1px 0 0;border-top:3px solid var(--fg);background:transparent;padding:16px 0 0}
.stack{display:flex;flex-direction:column;gap:16px}
.arc-title{font:600 1.08rem/1.25 var(--display);color:var(--muted)}
.promise{font:700 clamp(1.85rem,6.4vw + .35rem,3.2rem)/1.07 var(--display);letter-spacing:-.022em;text-wrap:balance;overflow-wrap:anywhere}
.promise.dim{color:var(--muted);font-size:1.4rem}
.tone{color:var(--muted);font-style:italic}
.tone .lab{font-style:normal;margin-inline-end:8px}
.prose{max-width:65ch}
.act-title{font:600 clamp(1.4rem,3.6vw + .6rem,1.9rem)/1.15 var(--display);letter-spacing:-.012em}
.act-q{font-size:1.28rem;line-height:1.35;font-style:italic;max-width:50ch;border-inline-start:3px solid var(--accent);padding-inline-start:14px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:20px 30px;margin:0}
.facts>div{min-width:0}
.facts dt{font:500 .72rem var(--mono);letter-spacing:.11em;text-transform:uppercase;color:var(--muted);margin-bottom:5px}
.facts dd{margin:0;max-width:65ch;overflow-wrap:anywhere}
.list{margin:0;padding-inline-start:1.1em;display:flex;flex-direction:column;gap:5px}
.list li::marker{color:var(--accent)}
.list.cross li::marker{color:var(--warn);content:"\\2715  "}
.list.veil li::marker{color:var(--muted);content:"\\25CC  "}
.tags{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px}
.tags li{font:400 .86rem/1.4 var(--mono);padding:3px 9px;background:var(--soft);border:1px solid var(--line);border-radius:3px;overflow-wrap:anywhere}
.tests{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.tests li{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;border-bottom:1px dotted var(--line);padding-bottom:5px}
.tests .who{font-weight:600}
.tests .cat{font:400 .8rem var(--mono);color:var(--accent);text-transform:uppercase;letter-spacing:.06em}
.devs{border-top:1px solid var(--line);padding-top:12px}
.devs h4{margin-bottom:8px}
.turn{color:var(--muted);font-size:.78rem;margin-inline-end:4px}

.progress{display:flex;flex-direction:column;gap:7px;padding-block:6px 4px}
.prog-head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:2px 16px}
.prog-head .num{font-size:.95rem;font-weight:500}
.prog-note{font-size:.76rem;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.prog-note.warn{color:var(--warn)}
.track{position:relative;height:12px;background:var(--soft);border:1px solid var(--line);border-radius:2px}
.fill{height:100%;background:var(--accent)}
.fill.over{background:var(--warn)}
.tick{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--fg);transform:translateX(-1px)}
.scale{position:relative;height:1.1em;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.scale span{position:absolute;top:0;transform:translateX(-50%);white-space:nowrap}
.scale .end{left:auto;right:0;transform:none}

.past-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.past{display:flex;flex-direction:column;gap:7px;padding:18px 0;border-top:1px solid var(--line)}
.past:last-child{border-bottom:1px solid var(--line)}
.past-title{font:600 1.1rem/1.25 var(--display)}
.past-promise{font-style:italic;max-width:60ch}
.retro{color:var(--muted);max-width:65ch;font-size:.97rem}
.retro .lab{margin-inline-end:6px}

.pillars{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
.pillars li{display:grid;grid-template-columns:minmax(6.5rem,1fr) auto minmax(3.6rem,auto);align-items:center;gap:10px}
.pname{text-transform:capitalize;overflow-wrap:anywhere}
.pips{display:inline-flex;gap:4px}
.pips i{width:20px;height:9px;border:1px solid var(--accent);border-radius:2px;display:block}
.pips i.on{background:var(--accent)}
.pip-word{font-size:.72rem;color:var(--muted);letter-spacing:.05em;text-transform:uppercase}
.quests{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.qname{display:block;font-weight:600}
.qgoal{display:block;color:var(--muted)}

@media (max-width:520px){
  .arc,.panel{padding:18px 14px}
  .arc.current{padding-inline-start:12px}
  .mast h1{font-size:1.45rem}
  .slate{grid-template-columns:repeat(2,1fr)}
  .slate .cell:nth-child(odd){border-inline-start:0}
  .slate .cell:nth-child(n+3){border-top:1px solid var(--line)}
  .pillars li{grid-template-columns:1fr auto}
  .pip-word{display:none}
}
@media print{body{background:#fff;color:#000}.nav{display:none}}
"""


def render(data, ctx):
    """The page as one HTML string; raises Leak when a hidden term would appear in it."""
    pg = Page(ctx)
    cur, nxt, past = arc_sections(pg, data)
    body = "".join([header(pg), act_block(pg, data), cur, nxt, past, session_zero(pg, data), threads(pg)])
    scan(pg, data.get("arcs") or [])
    display = html.escape(str(ctx.get("display") or "Campaign"))
    css = root_css() + CSS
    return (f"<title>{display} Arc Planner</title>\n"
            f'<link rel="stylesheet" href="{html.escape(FONTS_URL)}">\n'
            f"<style>{css}</style>\n"
            f'<div class="wrap">{body}</div>\n')
