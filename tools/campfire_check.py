"""Pure checks for a Campfire scene (GDD v2: the check stage, the hard noes, the checker's brief). No file, no database, no network:
every function takes plain data and returns plain data, so tests drive them directly and `db.py` supplies the campaign's facts.

A flag is a dict: {code, check ("phrase", "state" or "checker"), severity ("flag" or "warn"), para, text, quote}. A flag goes back to
the director to fix; a warn is shown and never forces a rewrite. Nothing here reaches the Campfire server."""
import json
import re
import unicodedata

# Rewrites after the first draft; a draft still flagged after the third rewrite goes to the GM. This is the one place campaign-helper holds the
# limit. It mirrors Campfire's LIMITS.write_retries (GDD v2) by value only: campaign-helper never imports Campfire code, and
# tests/test_campfire_check.py pins it to 3, so a change on either side is a deliberate edit here.
WRITE_RETRIES = 3
INVISIBLE = re.compile("[­​-‏‪-‮⁠-⁤⁦-⁩﻿]")
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")  # a run of letters and digits, an apostrophe inside it included
QUOTES = "\"“”"
HARD_NOE_LIMIT, HARD_NOE_CHARS = 30, 60  # phrases in the list, characters in a phrase (the limits GDD v2 gives the consent lists)


def clean(text):
    """Invisible and zero-width characters removed, then Unicode NFKC: what every match runs on."""
    return unicodedata.normalize("NFKC", INVISIBLE.sub("", str(text)))


def words(text):
    """The words of a text, cleaned, lower case, curly apostrophes made straight."""
    return [w.lower().replace("’", "'") for w in WORD.findall(clean(text))]


def squash(text):
    """A text for a findable-in-the-scene test: whitespace collapsed, case folded."""
    return re.sub(r"\s+", " ", clean(text)).strip().lower()


def excerpt(text, start, end, pad=30):
    s, e = max(0, start - pad), min(len(text), end + pad)
    return ("..." if s else "") + re.sub(r"\s+", " ", text[s:e]).strip() + ("..." if e < len(text) else "")


def paragraphs(scene):
    """[(number, text)] of the non-empty blank-line-separated paragraphs, numbered from 1 as the speaker-block check numbers them."""
    out, n = [], 0
    for para in re.split(r"\n[ \t]*\n", str(scene).replace("\r\n", "\n")):
        if para.strip():
            n += 1
            out.append((n, para.strip("\n")))
    return out


def quoted_mask(text):
    """A list of bools, one per character: True inside a pair of double quotation marks (straight or curly) on the same paragraph."""
    mask, inside = [], False
    for i, ch in enumerate(text):
        if ch in QUOTES:
            if ch == "”":
                inside = False
            elif ch == "“":
                inside = True
            else:
                inside = not inside
            mask.append(True)
        else:
            mask.append(inside)
    return mask


def hard_noe_problems(value):
    """Problems with the campaign.json hard_noes value: a list of at most HARD_NOE_LIMIT phrases of 1 to HARD_NOE_CHARS characters,
    each with at least one word, no phrase twice."""
    if not isinstance(value, list):
        return ["hard_noes must be a list of phrases"]
    bad = []
    if len(value) > HARD_NOE_LIMIT:
        bad.append(f"hard_noes holds {len(value)} phrases; the limit is {HARD_NOE_LIMIT}")
    seen = set()
    for i, p in enumerate(value):
        if not isinstance(p, str) or not words(p):
            bad.append(f"hard_noes[{i}] must be a phrase with at least one word")
        elif len(p) > HARD_NOE_CHARS:
            bad.append(f"hard_noes[{i}] is {len(p)} characters; the limit is {HARD_NOE_CHARS}")
        elif tuple(words(p)) in seen:
            bad.append(f"hard_noes[{i}] repeats an earlier phrase")
        else:
            seen.add(tuple(words(p)))
    return bad


def phrase_spans(text, phrase):
    """[(start, end)] character spans (in clean(text)) where the phrase's words appear contiguously, in order, as whole words, ignoring
    case. Code matches phrases only: a paraphrase is the director's and the checker's to catch."""
    pw = words(phrase)
    if not pw:
        return []
    c = clean(text)
    toks = [(m.start(), m.end(), m.group().lower().replace("’", "'")) for m in WORD.finditer(c)]
    out = []
    for i in range(len(toks) - len(pw) + 1):
        if [t[2] for t in toks[i:i + len(pw)]] == pw:
            out.append((toks[i][0], toks[i + len(pw) - 1][1]))
    return out


def hard_noes_in(text, phrases):
    """The phrases of the list that occur in a text (prep's match against a player's input)."""
    return [p for p in phrases if phrase_spans(text, p)]


def flag(code, check, severity, text, para=None, quote=""):
    return {"code": code, "check": check, "severity": severity, "para": para, "text": text, "quote": quote}


def phrase_flags(scene, phrases):
    """The phrase check: a hard no in narration is a flag; inside quoted dialogue it is a warn (a character may say it)."""
    out = []
    for n, para in paragraphs(scene):
        c = clean(para)
        mask = quoted_mask(c)
        for p in phrases:
            for s, e in phrase_spans(para, p):
                spoken = all(mask[s:e])
                out.append(flag("hard_no_dialogue" if spoken else "hard_no", "phrase", "warn" if spoken else "flag",
                                f'hard no "{p}" is in {"quoted dialogue" if spoken else "the narration"} (paragraph {n})'
                                + ("; a character may say it, check it is meant" if spoken else "; take it out"),
                                n, excerpt(c, s, e)))
    return out


def evidence_flags(scene, ops):
    """State check 6: every op's evidence appears in the scene text, up to whitespace and case."""
    hay = squash(scene)
    out = []
    for i, o in enumerate(ops or []):
        ev = o.get("evidence") if isinstance(o, dict) else None
        if not isinstance(ev, str) or not ev.strip():
            out.append(flag("evidence_missing", "state", "flag", f"ops[{i}] ({o.get('op') if isinstance(o, dict) else '?'}) has no evidence"))
        elif squash(ev) not in hay:
            out.append(flag("evidence_not_in_scene", "state", "flag",
                            f"ops[{i}] ({o.get('op')}): the evidence is not in the scene text; quote the scene or change the evidence",
                            quote=ev[:80]))
    return out


def reaction_line_flags(scene, reactions):
    """State check 7: every quoted NPC line of an approved reaction appears in the scene unchanged (up to whitespace and case)."""
    hay = squash(scene)
    out = []
    for r in reactions or []:
        line = r.get("line") if isinstance(r, dict) else None
        if isinstance(line, str) and line.strip() and squash(line) not in hay:
            out.append(flag("reaction_line_missing", "state", "flag",
                            f'{r.get("npc", "an NPC")}\'s approved line is not in the scene unchanged; set it word for word',
                            quote=line[:80]))
    return out


TITLES = {"the", "a", "an", "mr", "mrs", "ms", "miss", "dr", "sir", "mister", "madam", "old", "young"}


def name_forms(name):
    """The ways a scene may name someone: the full name, and its first and last word when the name has several (not an article or a title)."""
    ws = [w for w in words(name)]
    forms = [str(name)]
    if len(ws) > 1:
        forms += [w for w in (ws[0], ws[-1]) if len(w) >= 3 and w not in TITLES]
    return forms


def zone_flags(scene, positions, zones):
    """State check 4: a character named in the same sentence as a zone is in that zone after the round. positions is {name: zone} after
    the round's moves; zones the scene's zone names. A sentence naming several zones accepts any of them (a move across them)."""
    out = []
    zl = [z for z in zones or [] if isinstance(z, str) and z.strip()]
    if not zl or not positions:
        return out
    for n, para in paragraphs(scene):
        for sent in re.split(r"(?<=[.!?])\s+|\n", para):
            named_z = [z for z in zl if phrase_spans(sent, z)]
            if not named_z:
                continue
            for who, where in positions.items():
                if where and any(phrase_spans(sent, f) for f in name_forms(who)) and where not in named_z:
                    out.append(flag("wrong_zone", "state", "flag",
                                    f"{who} is in {where} after the round, but paragraph {n} puts them with {', '.join(named_z)}",
                                    n, excerpt(sent, 0, len(sent), 0)))
    return out


PLACE = re.compile(r"\b(?:in|at|into|inside|outside|to|toward|towards|from|behind|beyond|near|across)\s+the\s+"
                   r"((?:[A-Z][\w'’-]*)(?:\s+(?:of\s+)?[A-Z][\w'’-]*)*)")


def place_flags(scene, known):
    """State check 3: a place the scene names is its location, one of its zones, or a place the database knows. A place is a capitalised
    phrase after 'in the', 'at the', 'to the' and the like; `known` is the set of names that pass."""
    k = {squash(x) for x in known if isinstance(x, str)}
    out = []
    for n, para in paragraphs(scene):
        for m in PLACE.finditer(clean(para)):
            name = m.group(1)
            if squash(name) not in k and not any(squash(name) in x or x in squash(name) for x in k if len(x) > 3):
                out.append(flag("unknown_place", "state", "flag",
                                f'paragraph {n} names a place, "{name}", that is neither the scene\'s location, one of its zones nor in the '
                                "database; add it with a scene op (zones_add) or use a known place", n, excerpt(para, m.start(), m.end())))
    return out


def map_flags(scene, inputs, mapping, names_of):
    """The input-to-paragraph map: every input has an entry, every paragraph number exists, and a mapped paragraph names the
    character. inputs [{player, name}]; mapping {"inputs": [{"player": id-or-name, "paragraphs": [n...]}]}; names_of(input) the forms
    of the character's name."""
    paras = dict(paragraphs(scene))
    out = []
    entries = {}
    for e in (mapping or {}).get("inputs") or []:
        if isinstance(e, dict):
            entries[str(e.get("player"))] = e
    for x in inputs or []:
        e = entries.get(str(x.get("player"))) or entries.get(str(x.get("name")))
        who = x.get("name") or x.get("player")
        if e is None:
            out.append(flag("input_unmapped", "state", "flag", f"{who}'s input has no entry in the input-to-paragraph map; every input needs its outcome paragraph"))
            continue
        ps = e.get("paragraphs")
        if not (isinstance(ps, list) and ps and all(isinstance(p, int) and not isinstance(p, bool) for p in ps)):
            out.append(flag("input_unmapped", "state", "flag", f"{who}'s map entry needs a non-empty list of paragraph numbers"))
            continue
        gone = [p for p in ps if p not in paras]
        if gone:
            out.append(flag("map_bad_paragraph", "state", "flag", f"{who}'s map entry names paragraph(s) {gone} that the scene does not have ({len(paras)} paragraphs)"))
            continue
        if not any(phrase_spans(paras[p], f) for p in ps for f in names_of(x)):
            out.append(flag("input_outcome_missing", "state", "flag",
                            f"none of the paragraphs {ps} named for {who}'s input mentions {who}; map the paragraph that shows the outcome"))
    return out


QUESTIONS = (
    ("player_voice", "Does any line state a player character's words, thoughts, feelings or choices beyond what their input wrote?", "yes"),
    ("tier_mismatch", "Does any line describe an input's outcome better or worse than its tier, or leave an input's outcome out?", "yes"),
    ("number_mismatch", "Does any number in the prose contradict the packet?", "yes"),
    ("npc_off_reaction", "Does any NPC act against its approved reaction, or any threat against its move?", "yes"),
    ("wrong_place", "Is anyone somewhere the packet's zones do not put them?", "yes"),
    ("hard_no_reworded", "Does any line touch one of the campaign's hard noes, in any wording?", "yes"),
    ("no_decision", "Does the scene end on something the players can act on?", "no"),
)


def checker_brief(scene, reacted_packet, hard_noes):
    """The checker subagent's whole brief: the draft, the reacted packet and the hard noes, the fixed questions and the answer format,
    and nothing else (no brief, no memory, no database). The checker flags and never rewrites."""
    qs = "\n".join(f"{i}. {q}" for i, (_c, q, _a) in enumerate(QUESTIONS, 1))
    return (
        "You check a draft scene for a tabletop story. You flag; you never rewrite. You see only this brief: the draft, the reacted packet "
        "(what the dice and the characters' reactions decided) and the table's hard noes. Do not look anything else up.\n\n"
        "Answer each question below with \"yes\" or \"no\". For every \"yes\" on questions 1 to 6 and for a \"no\" on question 7, quote "
        "the line of the draft that shows it (a short exact quote). Reply with JSON only, in this shape:\n"
        '{"answers": [{"q": 1, "answer": "yes" | "no", "quote": "exact words from the draft, or an empty string"}, ... one per question]}\n\n'
        f"QUESTIONS\n{qs}\n\n"
        "HARD NOES (phrases the table agreed never to put on the page; question 6 asks for these in any wording)\n"
        + ("\n".join(f"- {p}" for p in hard_noes) if hard_noes else "(none)")
        + "\n\nREACTED PACKET\n" + json.dumps(reacted_packet, indent=1, ensure_ascii=False)
        + "\n\nDRAFT\n" + str(scene).rstrip("\n") + "\n")


def answer_flags(obj, scene):
    """Flags from the checker's JSON answers: a yes on questions 1 to 6, a no on question 7. A malformed reply is itself a flag (the
    checker has not checked), and a quote that is not in the draft is noted. Returns [flags]."""
    if not isinstance(obj, dict) or not isinstance(obj.get("answers"), list):
        return [flag("checker_bad_reply", "checker", "flag", 'the checker\'s reply must be an object with an "answers" list; ask the checker again')]
    by_q, out = {}, []
    for a in obj["answers"]:
        if isinstance(a, dict) and isinstance(a.get("q"), int) and a.get("answer") in ("yes", "no"):
            by_q[a["q"]] = a
    missing = [i for i in range(1, len(QUESTIONS) + 1) if i not in by_q]
    if missing:
        return [flag("checker_bad_reply", "checker", "flag", f"the checker did not answer question(s) {missing} with yes or no; ask the checker again")]
    hay = squash(scene)
    for i, (code, q, bad) in enumerate(QUESTIONS, 1):
        a = by_q[i]
        if a["answer"] != bad:
            continue
        quote = a.get("quote") if isinstance(a.get("quote"), str) else ""
        note = "" if not quote or squash(quote) in hay else " (the quote is not in the draft: check it)"
        out.append(flag(code, "checker", "flag", f"checker question {i} ({code}): {q}{note}", quote=quote[:120]))
    return out


STOP_WORDS = frozenset("a an the of to and in on at for with by from as is was were be it its that this he she they them his her their "
                       "i you we not no but or so then than there here".split())
STOCK_N, STOCK_MIN_SCENES, STOCK_KEEP, RECENT_SCENES = 4, 3, 15, 6


def narration_words(scene):
    """The words of a scene outside quoted dialogue, one list per paragraph's narration run (quotes cut the run)."""
    out = []
    for _n, para in paragraphs(scene):
        c = clean(para)
        mask = quoted_mask(c)
        run = []
        for m in WORD.finditer(c):
            if mask[m.start()]:
                if run:
                    out.append(run)
                run = []
            else:
                run.append(m.group().lower().replace("\u2019", "'"))
        if run:
            out.append(run)
    return out


def scene_grams(scene, n=STOCK_N):
    """The distinct n-word sequences of a scene's narration that carry at least two content words (not all articles and pronouns)."""
    grams = set()
    for run in narration_words(scene):
        for i in range(len(run) - n + 1):
            g = run[i:i + n]
            if sum(1 for w in g if w not in STOP_WORDS) >= 2:
                grams.add(" ".join(g))
    return grams


def repetition_snapshot(scenes):
    """The repetition tracker from the latest posted scenes [(turn, text)], oldest first (at most RECENT_SCENES are read): stock phrases
    (narration sequences that recur in at least STOCK_MIN_SCENES of them, most frequent first, at most STOCK_KEEP) and each scene's
    opening and closing words, so the next scene can avoid repeating them."""
    scenes = list(scenes)[-RECENT_SCENES:]
    seen = {}
    for t, text in scenes:
        for g in scene_grams(text):
            seen.setdefault(g, []).append(t)
    stock = sorted(({"phrase": g, "turns": ts} for g, ts in seen.items() if len(ts) >= STOCK_MIN_SCENES),
                   key=lambda x: (-len(x["turns"]), x["phrase"]))[:STOCK_KEEP]
    openings, closings = [], []
    for t, text in scenes:
        allw = words(text)
        if allw:
            openings.append({"turn": t, "text": " ".join(allw[:6])})
            closings.append({"turn": t, "text": " ".join(allw[-6:])})
    return {"stock": stock, "openings": openings, "closings": closings}


def repetition_flags(scene, tracker):
    """Warns for a draft that repeats the tracker: a stock phrase in its narration, an opening or closing used before. Never a flag."""
    out = []
    if not isinstance(tracker, dict):
        return out
    grams = scene_grams(scene)
    for s_ in tracker.get("stock") or []:
        if s_.get("phrase") in grams:
            out.append(flag("repeated_phrase", "state", "warn", f'"{s_["phrase"]}" is a stock phrase of the last scenes (turns '
                            f'{", ".join(map(str, s_.get("turns") or []))}); say it another way'))
    allw = words(scene)
    if allw:
        for key, label, mine in (("openings", "opening", " ".join(allw[:6])), ("closings", "closing", " ".join(allw[-6:]))):
            for o in tracker.get(key) or []:
                if o.get("text") == mine:
                    out.append(flag("repeated_" + label, "state", "warn", f"the scene's {label} words repeat turn {o.get('turn')}'s: {mine}"))
    return out


ATTITUDES = ("friendly", "neutral", "wary", "hostile")
MOVE_KINDS = ("press", "press all", "hold", "flee")
REACTION_KINDS = ("stay", "move", "leave", "attitude", "give", "refuse", "turn")
REACTION_FIELDS = {"stay": (), "move": ("to",), "leave": (), "attitude": ("word",), "give": ("player", "item", "qty"), "refuse": ("player",),
                   "turn": ("id", "tier", "reach", "rules")}
LINE_LIMIT = 200
THREAT_TIERS = ("trivial", "minor", "standard", "elite", "boss", "mythic")


def reaction_problems(obj, packet):
    """Problems with a react file ({"threat_moves": [...], "reactions": [...]}) against the result packet, as Campfire's server will judge
    them (the server stays the authority; this saves the refused round trip). Returns (problems, texts) where texts is [(label, text)] of
    every line and rules text the players will read, for the hidden-words check."""
    bad, texts = [], []
    if not isinstance(obj, dict):
        return ["the react file must be an object with \"threat_moves\" and \"reactions\" lists"], texts
    bad += [f'unknown key "{k}" (allowed: threat_moves, reactions)' for k in obj if k not in ("threat_moves", "reactions")]
    moves, reacts = obj.get("threat_moves", []), obj.get("reactions", [])
    if not isinstance(moves, list) or not isinstance(reacts, list):
        return bad + ["threat_moves and reactions must be lists"], texts
    party = [m for m in packet.get("party") or [] if isinstance(m, dict)]
    by_id = {str(m.get("player")): m for m in party}
    cond = lambda m: {str(c.get("name")) for c in m.get("conditions") or [] if isinstance(c, dict)}  # noqa: E731
    threats = {str(t.get("id")): t for t in packet.get("threats") or [] if isinstance(t, dict)}
    need = {i for i, t in threats.items() if t.get("status") in ("active", "full")}
    seen = set()
    for i, m in enumerate(moves):
        w = f"threat_moves[{i}]"
        if not isinstance(m, dict):
            bad.append(f"{w} must be an object")
            continue
        tid, kind = str(m.get("threat")), m.get("kind")
        extra = [k for k in m if k not in ("threat", "kind", "target", "to")]
        if extra:
            bad.append(f"{w} has unknown field(s): {', '.join(extra)}")
        if tid not in threats:
            bad.append(f"{w}: no threat \"{tid}\" on the table")
            continue
        if tid in seen:
            bad.append(f"{w}: threat \"{tid}\" has two moves; each gets exactly one")
        seen.add(tid)
        if tid not in need:
            bad.append(f"{w}: threat \"{tid}\" is {threats[tid].get('status')} and gets no move")
        if kind not in MOVE_KINDS:
            bad.append(f"{w}: kind must be one of {', '.join(MOVE_KINDS)}")
            continue
        if threats[tid].get("status") == "full" and kind not in ("hold", "flee"):
            bad.append(f"{w}: a full threat may only hold or flee")
        if kind == "press":
            tg = by_id.get(str(m.get("target")))
            if tg is None:
                bad.append(f"{w}: press needs a target that is a character in the lock (a player id)")
            elif tg.get("status") not in (None, "active") or "Out" in cond(tg):
                bad.append(f"{w}: {tg.get('name')} cannot be pressed (not active, or Out)")
        elif "target" in m:
            bad.append(f"{w}: only press takes a target")
        if "to" in m and not (isinstance(m["to"], str) and m["to"].strip()):
            bad.append(f"{w}: to must be a zone name")
    bad += [f'threat "{t}" is {threats[t].get("status")} and needs exactly one move' for t in sorted(need - seen)]
    npcs = {squash(n.get("name")): n for n in (packet.get("scene") or {}).get("npcs") or [] if isinstance(n, dict) and n.get("name")}
    named = set()
    for i, r in enumerate(reacts):
        w = f"reactions[{i}]"
        if not isinstance(r, dict):
            bad.append(f"{w} must be an object")
            continue
        who = squash(r.get("npc") or "")
        if who not in npcs:
            bad.append(f"{w}: {r.get('npc')!r} is not an NPC in the scene")
        elif who in named:
            bad.append(f"{w}: {r.get('npc')} has two reactions; each NPC gets at most one")
        named.add(who)
        kind = r.get("kind")
        if kind == "relationship":
            bad.append(f"{w}: relationship reactions are not in the first playtest")
            continue
        if kind not in REACTION_KINDS:
            bad.append(f"{w}: kind must be one of {', '.join(REACTION_KINDS)}")
            continue
        allowed = ("npc", "kind", "line") + REACTION_FIELDS[kind]
        bad += [f"{w}: {k} is not a field of a {kind} reaction" for k in r if k not in allowed]
        bad += [f"{w}: a {kind} reaction needs {k}" for k in REACTION_FIELDS[kind] if k not in r]
        ln = r.get("line")
        if ln is not None:
            if not (isinstance(ln, str) and ln.strip() and len(ln) <= LINE_LIMIT):
                bad.append(f"{w}: line must be 1 to {LINE_LIMIT} characters")
            else:
                texts.append((f"reactions[{i}].line", ln))
        if kind == "attitude" and "word" in r:
            cur = (npcs.get(who) or {}).get("attitude")
            if r["word"] not in ATTITUDES:
                bad.append(f"{w}: word must be one of {', '.join(ATTITUDES)}")
            elif cur in ATTITUDES and abs(ATTITUDES.index(r["word"]) - ATTITUDES.index(cur)) != 1:
                bad.append(f"{w}: {r['word']} is not one step from {cur}")
        if kind in ("give", "refuse") and str(r.get("player")) not in by_id:
            bad.append(f"{w}: player {r.get('player')!r} is not in the party")
        if kind == "give" and not (isinstance(r.get("qty"), int) and not isinstance(r.get("qty"), bool) and 1 <= r["qty"] <= 3):
            bad.append(f"{w}: qty must be a whole number from 1 to 3")
        if kind == "turn":
            if r.get("tier") not in THREAT_TIERS:
                bad.append(f"{w}: tier must be one of {', '.join(THREAT_TIERS)}")
            if isinstance(r.get("rules"), str):
                texts.append((f"reactions[{i}].rules", r["rules"]))
        zl = [str(z.get("name") if isinstance(z, dict) else z) for z in (packet.get("scene") or {}).get("zones") or []]
        if kind == "move" and zl and r.get("to") not in zl:
            bad.append(f"{w}: {r.get('to')!r} is not one of the scene's zones ({', '.join(zl)})")
        nums = [k for k, v in r.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and not (kind == "give" and k == "qty")]
        bad += [f"{w}: {k} is a number; reactions carry no number except a give's qty" for k in nums]
    return bad, texts
