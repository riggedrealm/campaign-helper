# Failures: what each exit code means and what to do

Open this playbook when a `db.py` command exits non-zero or prints an error or a push warning.

The exit codes are: 0 ok; 1, 2 or 3 a bad payload, prompt or op; 4 refused; 5 saved locally but the push failed; 6 lock busy; 7 stale lock; 8 not on `main`. Find the symptom below. A payload error found after the prompt is out is fixed and rerun off the clock, as LOOP-5 says (`core.md`, The turn).

## Bad input: nothing was applied

- **Exit 1, 2 or 3 from `record` or `commit-turn`.** The prompt or the payload is bad: a FAIL in the prompt (length, labels, hidden ladder-step words) gives exit 1, and a bad payload or op gives exit 2 or 3. The message names the problem and nothing was applied. Fix it and rerun the same call. Run alone, `check-prompt` exits 1 on a FAIL and 2 when only names are unknown (a warning); `scan` exits 4 on a hidden-term hit and 1 when its file is missing. <!-- FAIL-1 -->
- **Exit 4, "payload turn is X but the next turn is Y".** The turn was already recorded, or the payload's number is wrong. Check `db.py resume`, and never rerun a turn that was applied. (Exit 4 also appears when a write is refused during a trial run; see TRIAL-1 in the bootstrap skill.) <!-- FAIL-2 -->

## Locks

- **Exit 6, "another write is in progress".** A writer is running. Wait for it to finish, and do not start another write. If it looks hung (more than 10 minutes), kill that process and run `db.py recover`. <!-- FAIL-3 -->
- **Exit 7, or `resume` or `state` prints "stale write lock".** A writer crashed. Run `db.py recover`: if a crashed `record` left the data half-applied it restores the pre-turn snapshot, otherwise it only clears the lock. Then rerun the payload. <!-- FAIL-4 -->

## Saving and pushing

- **Exit 5, "saved locally, push failed", or `WARN push failed` after `commit-turn`.** The data is applied and committed locally. Do not rerun the payload. Run `db.py save` when the network is back (it retries and rebases); the next `commit-turn` or `wrap-up` retries the push too. If `wrap-up` exits 5, the commits are kept but it is not safe to close: rerun `wrap-up` when the network is back. <!-- FAIL-5 -->
- **Exit 8.** The checkout is not on `main`. Check out `main` (as in REPO-1 in the bootstrap skill) and rerun. <!-- FAIL-6 -->

## Repairs

- **A turn was recorded wrongly.** `db.py undo-turn N` restores the snapshot taken before turn N (the last 5 turns are kept) and rewinds `state.turn`. Fix the payload, record the turn again, then run `db.py save` to commit the rewind. <!-- FAIL-7 -->
- **A Planner card or charter breaks a rule.** Do not use it. Rewrite the weak parts yourself, or reuse an earlier card. The Planner wrote nothing to the data, so there is nothing to undo. <!-- FAIL-8 -->
- **Which tool repairs.** Use `record` (all or nothing; it also covers turn 1) and `save`. By hand, commit `campaigns/<name>/data` with the message "<Display name> save: turn N" and push to `main`. <!-- FAIL-9 -->
- **Scratch files.** The snapshots in `data/.snapshots/` and the lock file `data/.lock` are git-ignored scratch files. Never commit them. <!-- FAIL-10 -->
