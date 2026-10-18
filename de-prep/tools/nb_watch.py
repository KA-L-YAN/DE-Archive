#!/usr/bin/env python3
"""Run a headless Claude when a notebook code cell is added or edited.

Start with `python tools/nb_watch.py --loop` (checks every 10s). Fires once the
file has been still for SETTLE seconds. Claude only edits markdown cells, so its
own saves never re-trigger this. First sight of a notebook only records its cells.
"""
import hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

try:
    import fcntl  # ponytail: no lock on Windows; --loop is a single process, do not start two
except ImportError:
    fcntl = None

REPO = Path(__file__).resolve().parent.parent
STATE = Path.home() / ".nb-watch/state.json"
LOG = Path.home() / ".nb-watch/nb-watch.log"
SETTLE = 15     # seconds the file must be still before reacting to new/edited code cells
CLAUDE = shutil.which("claude")

PROMPT = """The notebook {nb} has new or changed code cell(s): {ids} (the code may have been half-typed earlier; judge it as it is now).
For each of those cells, AND ALSO for the code cell directly above it (the previous problem, which the owner has probably just finished):
if it has no markdown cell above it, add one; otherwise fact-check the existing one against the code as it is NOW and rewrite it if stale or wrong.
Style: review-sheet. A "### Title", one bold takeaway, a few short bullets, and a warning line for any bug. No long prose.
Fact-check against the cell's code, its saved output and Python 3.12 semantics.
Rules: edit ONLY markdown cells (insert/modify), never code cells, outputs or metadata. Do not run the notebook or use git.
Re-read the file right before writing (the owner edits it live) and write with python -I json, indent=1, ensure_ascii=False, trailing newline.
Finish with a one-line summary."""


def code_cells(nb):
    cells = json.loads(nb.read_text(encoding="utf-8"))["cells"]
    return {c["id"]: hashlib.md5("".join(c["source"]).encode()).hexdigest()
            for c in cells if c["cell_type"] == "code" and "".join(c["source"]).strip()}


def run(nb, ids, log):
    log.write(f"{time.ctime()} {nb.name}: triggering for {ids}\n")
    log.flush()
    subprocess.run(
        [CLAUDE, "-p",  # prompt via stdin: multi-line args break through claude.cmd
         "--allowedTools", "Read,Edit,Bash(python -I:*)",
         "--permission-mode", "acceptEdits", "--max-budget-usd", "0.50"],
        cwd=REPO, input=PROMPT.format(nb=nb, ids=", ".join(ids)), text=True, encoding="utf-8", stdout=log, stderr=log, timeout=600)


def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if fcntl:
        lock = open(STATE.parent / "lock", "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # a previous run is still going
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    now = time.time()
    for nb in sorted((REPO).rglob("*.ipynb")):
        idle = now - nb.stat().st_mtime
        if idle < SETTLE:
            continue
        try:
            cur = code_cells(nb)
        except Exception as e:  # half-written JSON: try next tick
            print(f"{time.ctime()} skip {nb.name}: {e}", file=open(LOG, "a", encoding="utf-8"))
            continue
        st = state.get(str(nb))
        if not isinstance(st, dict):  # first sight (or old list-format state): baseline only
            state[str(nb)] = {"hash": cur, "recent": {}}
            continue
        known = st["hash"]
        changed = [i for i in cur if known.get(i) != cur[i]]  # new or edited
        # mark seen BEFORE running: a failing run must not retry in a loop
        state[str(nb)] = {"hash": cur, "recent": {}}
        STATE.write_text(json.dumps(state), encoding="utf-8")
        if changed:
            with open(LOG, "a", encoding="utf-8") as log:
                run(nb, changed, log)
    STATE.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    while "--loop" in sys.argv:
        main()
        time.sleep(10)
    sys.exit(main())
