#!/usr/bin/env python3
"""Bring a campaign's skill up to date with the generic rules in templates/voyage-director/SKILL.md.

    python3 tools/sync_skill.py NAME [--check]

Replaces the generic blocks (<!-- generic:start ID --> ... <!-- generic:end -->) of the campaign's SKILL.md with the
template's versions, by id, rendered with the campaign's placeholders and enabled modules. Fill content, the
`Skill version:` line and everything outside the blocks stay as they are; the `Generic rules:` line follows the template.
With --check nothing is written and the exit status is 1 when the skill is out of date.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skilltpl as T  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sync a campaign skill's generic rule blocks with the template.")
    ap.add_argument("name", help="campaign name (campaigns/NAME)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the skill is out of date; write nothing")
    ap.add_argument("--root", default=os.environ.get("VOYAGE_ROOT") or str(T.ROOT), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    root = Path(a.root)
    try:
        cfg = T.load_cfg(root, a.name)
    except (OSError, ValueError) as e:
        print(f"error: cannot read campaigns/{a.name}/campaign.json: {e}", file=sys.stderr)
        return 2
    skill_path = root / (cfg.get("skill_dir") or f".claude/skills/{a.name}-director") / "SKILL.md"
    try:
        skill = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read {skill_path}: {e}", file=sys.stderr)
        return 2
    template = (T.TEMPLATE_DIR / "SKILL.md").read_text(encoding="utf-8")
    new, notes = T.sync_text(skill, template, T.context(cfg), T.enabled_modules(cfg))
    left = T.fills_left(new)
    if new == skill:
        print(f"{skill_path.relative_to(root)}: generic rules up to date ({T.rules_version(new)}).")
        code = 0
    elif a.check:
        print(f"{skill_path.relative_to(root)}: OUT OF DATE")
        code = 1
    else:
        skill_path.write_text(new, encoding="utf-8")
        print(f"{skill_path.relative_to(root)}: synced.")
        code = 0
    for n in notes:
        print("  - " + n)
    if code == 1:
        print(f"Run: python3 tools/sync_skill.py {a.name}   (then bump `Skill version:` and re-upload the zip)")
    if left:
        print(f"  note: {len(left)} fill block(s) are still unfilled in this skill.")
    size = len(new.encode("utf-8"))
    if size > 15000:
        print(f"  WARNING: SKILL.md would be {size} bytes (limit 15000): trim fill text.")
    return code


if __name__ == "__main__":
    sys.exit(main())
