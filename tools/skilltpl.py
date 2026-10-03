"""Shared helpers for the Voyage director template (templates/voyage-director): rendering and generic-block sync.

Template syntax
  {{NAME}} {{SLUG}} {{SKILL_DIR}} {{DISPLAY}} {{PROMPT_LIMIT}} {{SETTING}}   placeholders
  <!-- generic:start ID --> ... <!-- generic:end -->                        generic rules, owned by the template (sync replaces them)
  <!-- fill: what goes here -->                                             world-specific part, written once per campaign
  <!-- module:NAME:start --> ... <!-- module:NAME:end -->                   optional module text, kept when the module is on
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates" / "voyage-director"

BLOCK_RE = re.compile(r"^<!-- generic:start ([\w-]+) -->\n(.*?)^<!-- generic:end -->\n", re.S | re.M)
FILL_RE = re.compile(r"<!-- fill: (.*?) -->", re.S)
RULES_RE = re.compile(r"^Generic rules:[ \t]*(\S*)[ \t]*$", re.M)
MODULES = ("standing", "debt")


def slug_of(skill_dir):
    return Path(skill_dir).name


def context(cfg, setting=""):
    """Placeholder values for a campaign.json dict."""
    name = cfg["name"]
    skill_dir = cfg.get("skill_dir") or f".claude/skills/{name}-director"
    limit = cfg.get("prompt_limit_default") or 840
    return {"NAME": name, "SLUG": slug_of(skill_dir), "SKILL_DIR": skill_dir, "DISPLAY": cfg.get("display") or name,
            "PROMPT_LIMIT": str(limit), "SETTING": setting}


def enabled_modules(cfg):
    return {m for m in MODULES if ((cfg.get("modules") or {}).get(m) or {}).get("enabled")}


def render(text, ctx, modules):
    """Apply modules (drop text of disabled ones, strip the markers of enabled ones), then placeholders."""
    for m in MODULES:
        pair = rf"<!-- module:{m}:start -->.*?<!-- module:{m}:end -->\n?"
        if m in modules:
            text = re.sub(rf"(?m)^<!-- module:{m}:(?:start|end) -->\n", "", text)
            text = re.sub(rf"<!-- module:{m}:(?:start|end) -->", "", text)
        else:
            text = re.sub(pair, "", text, flags=re.S)
    for k, v in ctx.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def blocks(text):
    """{id: inner text} of the generic blocks, in file order."""
    return {m.group(1): m.group(2) for m in BLOCK_RE.finditer(text)}


def rules_version(text):
    m = RULES_RE.search(text)
    return m.group(1) if m else None


def fills_left(text):
    return [m.group(1).strip() for m in FILL_RE.finditer(text)]


def sync_text(skill, template, ctx, modules):
    """Return (new skill text, list of change notes). Generic blocks are replaced by the template's (rendered) versions
    by id; everything else (fill content, version line) is kept; the `Generic rules:` line follows the template."""
    notes = []
    tpl = render(template, ctx, modules)
    tblocks = blocks(tpl)
    have = blocks(skill)

    def swap(m):
        bid = m.group(1)
        if bid not in tblocks:
            notes.append(f"block '{bid}' is not in the template: kept as is")
            return m.group(0)
        if tblocks[bid] != m.group(2):
            notes.append(f"block '{bid}' updated")
        return f"<!-- generic:start {bid} -->\n{tblocks[bid]}<!-- generic:end -->\n"

    out = BLOCK_RE.sub(swap, skill)
    prev = None
    for bid in tblocks:  # blocks the template gained: insert after the previous template block
        if bid not in have:
            piece = f"<!-- generic:start {bid} -->\n{tblocks[bid]}<!-- generic:end -->\n"
            if prev is not None:
                m = re.search(rf"^<!-- generic:start {re.escape(prev)} -->\n.*?^<!-- generic:end -->\n", out, re.S | re.M)
                out = out[:m.end()] + "\n" + piece + out[m.end():]
                notes.append(f"block '{bid}' added after '{prev}'")
            else:
                notes.append(f"block '{bid}' is new in the template but has no anchor: add it by hand")
        prev = bid
    tv = rules_version(tpl)
    if tv:
        if RULES_RE.search(out):
            if rules_version(out) != tv:
                notes.append(f"Generic rules {rules_version(out) or 'unknown'} -> {tv}")
            out = RULES_RE.sub(f"Generic rules: {tv}", out, count=1)
        else:
            out = re.sub(r"^(Skill version:.*)$", rf"\1\nGeneric rules: {tv}", out, count=1, flags=re.M)
            notes.append(f"Generic rules line added ({tv})")
    return out, notes


def load_cfg(root, name):
    p = Path(root) / "campaigns" / name / "campaign.json"
    return json.loads(p.read_text(encoding="utf-8"))
