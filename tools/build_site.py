#!/usr/bin/env python3
"""Build the static GitHub Pages site: one Arc Planner page per campaign plus an index (Python 3 standard library only).

    python3 tools/build_site.py [--out DIR]        (default: _site)

Each campaign page comes from `db.py --campaign NAME planner-page`, which scans every string for hidden terms and exits 4
without writing when one would leak. Here the page is wrapped in a full HTML document. If any campaign fails, the reason is
printed, the exit code is non-zero and nothing is copied into DIR, so a deploy never sees a partial or leaky site.

Site layout: DIR/index.html, DIR/NAME/index.html for every campaign, DIR/.nojekyll.
Reads campaigns/*/campaign.json, data/state.json and data/arcs.json (read-only). VOYAGE_ROOT picks another tree, as in db.py.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import planner_page  # noqa: E402

ROOT = Path(os.environ.get("VOYAGE_ROOT") or HERE.parent)
DB = HERE / "db.py"

# what the artifact host used to add around the page, so the page looks the same on its own
RESET = ("html{color-scheme:light}body{margin:0;font:14px/1.4 system-ui,-apple-system,\"Segoe UI\",Roboto,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")
HEAD_START = ('<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              '<meta name="robots" content="noindex">\n')

# the fragment starts with <title>, the fonts <link> and one <style>; those go to <head>, the rest to <body>
FRAGMENT = re.compile(r"\A\s*(<title>[^<]*</title>)\s*((?:<link\b[^>]*>\s*)*)(<style>.*?</style>)\s*(.*)\Z", re.S)


class BuildError(Exception):
    pass


def campaigns(root):
    d = root / "campaigns"
    return sorted(p.name for p in d.iterdir() if (p / "campaign.json").is_file()) if d.is_dir() else []


def render_fragment(name, tmp):
    """Run planner-page for one campaign; return (html_fragment, exit_code, message)."""
    env = {k: v for k, v in os.environ.items() if k not in ("VOYAGE_DATA", "CLASS2B_DATA", "VOYAGE_CAMPAIGN", "VOYAGE_TRIAL", "CLASS2B_TRIAL")}
    env["VOYAGE_ROOT"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = Path(tmp) / f"{name}.fragment.html"
    r = subprocess.run([sys.executable, str(DB), "--campaign", name, "planner-page", "--out", str(out)],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return None, r.returncode, (r.stderr.strip() or r.stdout.strip() or "no output")
    return out.read_text(encoding="utf-8"), 0, ""


def wrap_page(fragment):
    """The artifact fragment as a full document. Raises BuildError if it is not the shape the planner page promises."""
    if re.search(r"<(?:!doctype|html|head|body)\b", fragment, re.I):
        raise BuildError("planner page already has document tags")
    m = FRAGMENT.match(fragment)
    if not m or fragment.count("<title>") != 1:
        raise BuildError("planner page does not start with one <title>, fonts <link> and <style>")
    title, links, style, body = m.groups()
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n" + HEAD_START + title + "\n" + links.strip() + ("\n" if links.strip() else "") +
            f"<style>{RESET}</style>\n{style}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def act_for(cfg, day):
    n = 1
    for a in cfg.get("acts") or []:
        if isinstance(day, int) and isinstance(a.get("from_day"), int) and day >= a["from_day"]:
            n = a.get("n", n)
    return n


def summary(name, fragment):
    """What the index shows for a campaign: display name, act/day/turn and the current arc. Everything comes from public
    state; an arc title is used only when it also appears on the (already scanned) planner page."""
    cdir = ROOT / "campaigns" / name
    cfg = read_json(cdir / "campaign.json") or {}
    st = read_json(cdir / "data" / "state.json") or {}
    data = read_json(cdir / "data" / "arcs.json") or {}
    rows = [a for a in data.get("arcs") or [] if isinstance(a, dict)]
    arc = next((a for a in rows if a.get("status") == "active"), None)
    if arc is None:
        waiting = [a for a in rows if a.get("status") in ("draft", "approved")]
        arc = waiting[-1] if waiting else None
    title = None
    if arc:
        t = str((arc.get("shared") or {}).get("title") or "").strip()
        if t and html.escape(t, quote=True) in fragment:
            title = t
    word = planner_page.STATUS_WORDS.get(arc.get("status")) if arc else None
    return {"name": name, "display": cfg.get("display") or name, "act": st.get("act") or act_for(cfg, st.get("day")),
            "day": st.get("day"), "turn": st.get("turn"), "arc_title": title, "arc_status": word if arc else None}


INDEX_CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1.0625rem/1.58 var(--body)}
.wrap{max-width:46rem;margin-inline:auto;padding-inline:16px;padding-block:32px 72px}
.lab,.num,.chip{font-family:var(--mono);font-variant-numeric:tabular-nums}
.lab{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);font-weight:500}
h1{font:700 1.7rem/1.05 var(--display);letter-spacing:-.015em;margin:6px 0 10px;text-wrap:balance}
.lede{color:var(--muted);font-size:.95rem;line-height:1.45;max-width:46ch;margin:0 0 26px}
.list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.card{display:block;text-decoration:none;color:inherit;border:1px solid var(--line);background:var(--surface);padding:14px 16px 15px;min-width:0}
.card:hover{border-color:var(--accent)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.card h2{font:700 1.25rem/1.15 var(--display);letter-spacing:-.01em;margin:0 0 8px;overflow-wrap:anywhere}
.stamp{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.82rem;color:var(--muted)}
.arc{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin-top:10px;padding-top:10px;border-top:1px solid var(--line);min-width:0}
.arc .t{font-size:1rem;overflow-wrap:anywhere}
.arc .none{color:var(--muted);font-style:italic}
.chip{font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--accent);color:var(--accent);background:var(--accent-bg);padding:1px 7px;border-radius:999px}
.foot{margin-top:28px;font-size:.82rem;color:var(--muted);line-height:1.5}
"""


def index_page(items):
    cards = []
    for it in items:
        stamp = "".join(f'<span class="num">{k} {html.escape(str(v))}</span>'
                        for k, v in (("Act", it["act"]), ("Day", it["day"]), ("Turn", it["turn"])) if v not in (None, ""))
        if it["arc_title"]:
            chip = f'<span class="chip">{html.escape(it["arc_status"])}</span>' if it["arc_status"] else ""
            arc = f'{chip}<span class="t">{html.escape(it["arc_title"])}</span>'
        else:
            arc = '<span class="t none">No arc planned yet</span>'
        cards.append(f'<li><a class="card" href="{html.escape(it["name"], quote=True)}/"><h2>{html.escape(it["display"])}</h2>'
                     f'<div class="stamp">{stamp}</div><div class="arc">{arc}</div></a></li>')
    fonts = html.escape(planner_page.FONTS_URL)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n" + HEAD_START + "<title>Arc Planner</title>\n"
            f'<link rel="stylesheet" href="{fonts}">\n<style>{RESET}</style>\n<style>{planner_page.root_css()}{INDEX_CSS}</style>\n</head>\n<body>\n'
            '<div class="wrap"><span class="lab">Campaign helper</span><h1>Arc Planner</h1>'
            '<p class="lede">One read-only page per campaign. Each shows the story plan the players have already seen, never the hidden parts.</p>'
            f'<ul class="list">{"".join(cards)}</ul>'
            '<p class="foot">Public pages. Rebuilt on every push to main.</p></div>\n</body>\n</html>\n')


def build(out_dir):
    """Build the whole site into a scratch dir; copy it to out_dir only when every campaign worked. Returns the list of failures."""
    names = campaigns(ROOT)
    if not names:
        return [("(none)", 1, f"no campaigns found under {ROOT / 'campaigns'}")]
    failures, pages, items = [], {}, []
    with tempfile.TemporaryDirectory(prefix="site-build-") as tmp:
        for name in names:
            fragment, code, msg = render_fragment(name, tmp)
            if fragment is None:
                failures.append((name, code, msg))
                continue
            try:
                pages[name] = wrap_page(fragment)
            except BuildError as e:
                failures.append((name, 1, str(e)))
                continue
            items.append(summary(name, fragment))
        if failures:
            return failures
        stage = Path(tmp) / "site"
        for name, page in pages.items():
            (stage / name).mkdir(parents=True)
            (stage / name / "index.html").write_text(page, encoding="utf-8")
        (stage / "index.html").write_text(index_page(items), encoding="utf-8")
        (stage / ".nojekyll").write_text("", encoding="utf-8")
        shutil.copytree(stage, out_dir, dirs_exist_ok=True)
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the Arc Planner static site.")
    ap.add_argument("--out", default="_site", help="output directory (default _site)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    failures = build(out)
    if failures:
        for name, code, msg in failures:
            print(f"build_site: {name} failed (exit {code}): {msg}", file=sys.stderr)
        print(f"build_site: no site written to {out}. Fix the problem above and build again.", file=sys.stderr)
        return failures[0][1] or 1
    n = len(campaigns(ROOT))
    print(f"build_site: wrote {out} ({n} campaign page{'s' if n != 1 else ''} and an index)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
