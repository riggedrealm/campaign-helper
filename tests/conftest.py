"""Test-suite setup: keep every db.py run away from a real session file.

`db.py use NAME` writes a git-ignored session file in the repo root, and db.py reads it as the default campaign. A file left there
by a director (or by `use` in another session) must not change any test's result, so the whole suite points db.py at a private
session file through DB_SESSION_FILE. The name has no VOYAGE_ or CLASS2B_ prefix on purpose: the test helpers drop environment
variables with those prefixes when they build a child environment, and this one has to pass through every helper unchanged.
The file is removed before each test, so a test that runs `use` cannot leak its choice into the next one.

Some tests run `check-prompt` or `turn-brief --full` on the real campaign data, and those write the git-ignored timing clock
(`campaigns/*/data/.turn-clock`, SES-9). A second fixture puts every clock file back as it was before the test."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_SESSION_DIR = tempfile.mkdtemp(prefix="voyage-test-session-")
SESSION_FILE = os.path.join(_SESSION_DIR, "session.json")
os.environ["DB_SESSION_FILE"] = SESSION_FILE


@pytest.fixture(autouse=True)
def _no_session_file():
    try:
        os.remove(SESSION_FILE)
    except FileNotFoundError:
        pass
    yield


_CAMPAIGNS = Path(__file__).resolve().parent.parent / "campaigns"


@pytest.fixture(autouse=True)
def _no_clock_in_real_campaigns():
    """Leave the real campaigns' `.turn-clock` files (and their `.tmp`) as they were: remove new ones, restore changed ones."""
    def snap():
        return {p: p.read_bytes() for p in _CAMPAIGNS.glob("*/data/.turn-clock*") if p.is_file()}
    before = snap()
    yield
    after = snap()
    for p in after:
        if p not in before:
            p.unlink(missing_ok=True)
    for p, data in before.items():
        if after.get(p) != data:
            p.write_bytes(data)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_SESSION_DIR, ignore_errors=True)
