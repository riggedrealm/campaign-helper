#!/usr/bin/env python3
"""Compatibility stub: the shared tool now lives at tools/db.py (repo root).

`python3 campaigns/classroom-2b/tools/db.py ...` keeps working: it runs the shared tool with
`--campaign classroom-2b` as the default campaign (an explicit --campaign or VOYAGE_CAMPAIGN wins).
"""
import os
import sys
from pathlib import Path

shared = Path(__file__).resolve().parents[3] / "tools" / "db.py"
args = sys.argv[1:]
if not any(a == "--campaign" or a.startswith("--campaign=") for a in args) and not os.environ.get("VOYAGE_CAMPAIGN"):
    args = ["--campaign", "classroom-2b"] + args
os.execv(sys.executable, [sys.executable, str(shared)] + args)
