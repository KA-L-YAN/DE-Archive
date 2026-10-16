#!/usr/bin/env python3
"""Run a headless Claude when a notebook gains a new non-empty code cell.

Polled every 10s by nb-watch.timer. VS Code autosave (2s) writes the file while
you type, so a new cell fires ~5s after the file goes quiet. The first trigger
may see half-typed code, so a cell triggered within the last hour is re-checked
once it has been idle RECHECK seconds after its source changed.
Claude only edits markdown cells, so its own saves never re-trigger this.
First sight of a notebook only records its cells (no trigger).
"""
import fcntl, hashlib, json, subprocess, sys, time
from pathlib import Path

ROOT = Path.home() / "Downloads/Archive"
NOTEBOOKS = sorted((ROOT / "de-prep").rglob("*.ipynb"))
STATE = Path.home() / ".local/state/nb-watch/state.json"
LOG = Path.home() / ".local/share/nb-watch.log"
SETTLE = 5      # seconds of quiet before reacting to a NEW cell
RECHECK = 30    # seconds of quiet before re-checking a recently triggered cell
RECENT = 3600   # how long a triggered cell stays eligible for re-check
CLAUDE = str(Path.home() / ".local/bin/claude")

PROMPT = """The notebook {nb} has new or changed code cell(s): {ids} (the code may have been half-typed earlier; judge it as it is now).
For each of those cells, AND ALSO for the code cell directly above it (the previous problem, which the owner has probably just finished):
if it has no markdown cell above it, add one; otherwise fact-check the existing one against the code as it is NOW and rewrite it if stale or wrong.
Style: review-sheet. A "### Title", one bold takeaway, a few short bullets, and a warning line for any bug. No long prose.
Fact-check against the cell's code, its saved output and Python 3.12 semantics.
Rules: edit ONLY markdown cells (insert/modify), never code cells, outputs or metadata. Do not run the notebook or use git.
Re-read the file right before writing (the owner edits it live) and write with python3 -I json, indent=1, ensure_ascii=False, trailing newline.
Finish with a one-line summary."""


def code_cells(nb):
    cells = json.loads(nb.read_text())["cells"]
    return {c["id"]: hashlib.md5("".join(c["source"]).encode()).hexdigest()
            for c in cells if c["cell_type"] == "code" and "".join(c["source"]).strip()}


def run(nb, ids, log):
    log.write(f"{time.ctime()} {nb.name}: triggering for {ids}\n")
    log.flush()
    subprocess.run(
        [CLAUDE, "-p", PROMPT.format(nb=nb, ids=", ".join(ids)),
         "--allowedTools", "Read,Edit,Bash(python3 -I:*)",
         "--permission-mode", "acceptEdits", "--max-budget-usd", "0.50"],
        cwd=ROOT, stdout=log, stderr=log, timeout=600)


def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    lock = open(STATE.parent / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # a previous run is still going
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = time.time()
    for nb in NOTEBOOKS:
        idle = now - nb.stat().st_mtime
        if idle < SETTLE:
            continue
        try:
            cur = code_cells(nb)
        except Exception as e:  # half-written JSON: try next tick
            print(f"{time.ctime()} skip {nb.name}: {e}", file=open(LOG, "a"))
            continue
        st = state.get(str(nb))
        if not isinstance(st, dict):  # first sight (or old list-format state): baseline only
            state[str(nb)] = {"hash": cur, "recent": {}}
            continue
        known, recent = st["hash"], {k: t for k, t in st["recent"].items() if now - t < RECENT}
        new = [i for i in cur if i not in known]
        changed = [i for i in cur if i in recent and known.get(i) != cur[i]] if idle >= RECHECK else []
        for i in new + changed:
            recent[i] = now
        # mark seen BEFORE running: a failing run must not retry in a loop
        state[str(nb)] = {"hash": {**{i: h for i, h in known.items() if i in cur}, **cur}, "recent": recent}
        STATE.write_text(json.dumps(state))
        if new or changed:
            with open(LOG, "a") as log:
                run(nb, new + changed, log)
    STATE.write_text(json.dumps(state))


if __name__ == "__main__":
    sys.exit(main())
