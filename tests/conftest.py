"""Test-suite setup: keep every db.py run away from a real session file.

`db.py use NAME` writes a git-ignored session file in the repo root, and db.py reads it as the default campaign. A file left there
by a director (or by `use` in another session) must not change any test's result, so the whole suite points db.py at a private
session file through DB_SESSION_FILE. The name has no VOYAGE_ or CLASS2B_ prefix on purpose: the test helpers drop environment
variables with those prefixes when they build a child environment, and this one has to pass through every helper unchanged.
The file is removed before each test, so a test that runs `use` cannot leak its choice into the next one."""
import os
import shutil
import tempfile

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


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_SESSION_DIR, ignore_errors=True)
