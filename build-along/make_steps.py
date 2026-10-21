#!/usr/bin/env python3
"""
make_steps.py: (maintainers only) regenerate the build-along snapshots and the guide.

    python build-along/make_steps.py

For every step of the video it writes build-along/step-N-.../ (the money-agent folder exactly as it is
at the end of that step) plus EXPECTED_OUTPUT.txt, produced by really running that step's code.
It then fills build-along/GUIDE.template.md with that code and output and writes build-along/README.md.

Everything is derived from the finished money-agent/, using the same tools.py versions the video types
(video/scripts/capture.py), so the guide, the snapshots and the video can never disagree.
Run it with the agent's requirements installed (pip install -r money-agent/requirements.txt).
"""
import difflib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
APP = ROOT / "money-agent"
SHOWN = "/home/dev/projects/money-agent"

spec = importlib.util.spec_from_file_location("capture", ROOT / "video" / "scripts" / "capture.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

read = lambda p: (APP / p).read_text(encoding="utf-8")
V1, V2, V3, V4 = capture.tools_versions()
GRAPH = "from agent import build_graph; print(' -> '.join(build_graph().get_graph().nodes))"
RUN_TOOLS = ("python tools.py data/transactions.csv", ["tools.py", "data/transactions.csv"])
RUN_GRAPH = (f'python -c "{GRAPH}"', ["-c", GRAPH])
RUN_MAIN = ("python main.py data/transactions.csv", ["main.py", "data/transactions.csv"])

BASE = {"requirements.txt": read("requirements.txt"), "data/transactions.csv": read("data/transactions.csv"),
        "main.py": "", "agent.py": "", "tools.py": "", "app.py": "", "templates/index.html": ""}
STEPS = [
    ("step-1-setup", {}, None),
    ("step-2-load-crash", {"tools.py": V1}, RUN_TOOLS),
    ("step-3-fix-loader", {"tools.py": V2}, RUN_TOOLS),
    ("step-4-categorise", {"tools.py": V3}, RUN_TOOLS),
    ("step-5-analyse", {"tools.py": V4}, RUN_TOOLS),
    ("step-6-agent-workflow", {"agent.py": read("agent.py")}, RUN_GRAPH),
    ("step-7-run-cli", {"main.py": read("main.py")}, RUN_MAIN),
    ("step-8-dashboard", {"app.py": read("app.py"), "templates/index.html": read("templates/index.html")}, ("python app.py", None)),
]


def py_env():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)                 # snapshots show the deterministic, offline behaviour
    return env


def run_step_command(folder, argv):
    p = subprocess.run([sys.executable] + argv, cwd=folder, capture_output=True, text=True, encoding="utf-8", env=py_env())
    return capture.clean(p.stdout + p.stderr, folder)


def drive_dashboard(folder):
    """Start the real app.py, then do what the video does: upload, correct a category, dismiss an alert."""
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 5000)) == 0:
            sys.exit("port 5000 is busy - stop the other server first")
    log = open(folder / "server.log", "w", encoding="utf-8")
    srv = subprocess.Popen([sys.executable, "app.py"], cwd=folder, stdout=log, stderr=subprocess.STDOUT, env=py_env())
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1); break
            except Exception:
                time.sleep(0.25)
        b = "----build-along"
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"transactions.csv\"\r\n"
                "Content-Type: text/csv\r\n\r\n").encode() + (folder / "data/transactions.csv").read_bytes() + f"\r\n--{b}--\r\n".encode()
        def post(url, data, ctype):
            req = urllib.request.Request("http://127.0.0.1:5000" + url, data=data, headers={"Content-Type": ctype})
            return json.loads(urllib.request.urlopen(req).read())
        r1 = post("/api/analyse", body, f"multipart/form-data; boundary={b}")
        fix = next(t for t in r1["transactions"] if t["merchant"] == "Sri Sai Enterprises" and t["date"] > "2026-10")
        r2 = post("/api/correct", json.dumps({"txn_id": fix["txn_id"], "category": "education"}).encode(), "application/json")
        r3 = post("/api/dismiss", json.dumps({"txn_id": r2["flags"][0]["txn_id"]}).encode(), "application/json")
        time.sleep(0.4)
    finally:
        srv.terminate(); srv.wait(); log.close()
    server = re.sub(r"\x1b\[[0-9;]*m", "", (folder / "server.log").read_text(encoding="utf-8"))
    (folder / "server.log").unlink()
    m = r1["analysis"]["month"]
    cat = lambda r, c: r["analysis"]["by_month"][m].get(c, 0)
    rs = lambda n: f"₹{n:,}"
    summary = (
        "What the dashboard shows (same as the video)\n"
        f"  after Run analysis    : {rs(r1['analysis']['total'])} spent in {m}, {len(r1['flags'])} flagged "
        f"{[f['txn_id'] for f in r1['flags']]}\n"
        f"  after correcting {fix['txn_id']} (Sri Sai Enterprises) -> education:\n"
        f"      education {rs(cat(r1, 'education'))} -> {rs(cat(r2, 'education'))} · other {rs(cat(r1, 'other'))} -> {rs(cat(r2, 'other'))}\n"
        f"  after dismissing {r2['flags'][0]['txn_id']}   : {len(r3['flags'])} left to review\n")
    return capture.clean(server, folder) + "\n\n" + summary


def write_snapshot(i, name, files, cmd):
    out = HERE / name
    shutil.rmtree(out, ignore_errors=True)
    for path, text in files.items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(text, encoding="utf-8", newline="\n")
    work = Path(tempfile.mkdtemp(prefix="build-along-")) / "money-agent"
    shutil.copytree(out, work)
    if cmd is None:
        import pandas, langgraph, flask  # noqa: F401  (step 1: are the packages installed?)
        from importlib.metadata import version
        text = ("$ python -c \"import pandas, langgraph, flask; print('ready')\"\nready\n\n"
                "tested with: " + ", ".join(f"{p}=={version(p)}" for p in ("pandas", "langgraph", "flask")))
        cmd_shown = "pip install -r requirements.txt"
    elif cmd[1] is None:
        text, cmd_shown = drive_dashboard(work), cmd[0]
    else:
        text, cmd_shown = run_step_command(work, cmd[1]), cmd[0]
    shutil.rmtree(work.parent, ignore_errors=True)
    head = (f"# Expected output of step {i} ({name})\n# command: {cmd_shown}\n"
            "# Times and file paths will be different on your computer; everything else should match.\n\n")
    (out / "EXPECTED_OUTPUT.txt").write_text(head + text.rstrip() + "\n", encoding="utf-8", newline="\n")
    return text


# --------------------------------------------------------------------------- guide
def lang(path):
    return {"py": "python", "html": "html", "txt": "text", "csv": "text"}[path.rsplit(".", 1)[1]]


def fill_template(snap, outputs):
    tpl = (HERE / "GUIDE.template.md").read_text(encoding="utf-8")

    def file_block(m):
        step, path = m.group(1), m.group(2)
        text = snap[step][path]
        return f"```{lang(path)}\n{text.rstrip()}\n```"

    def diff_block(m):
        a, b, path = m.group(1), m.group(2), m.group(3)
        d = difflib.unified_diff(snap[a][path].splitlines(True), snap[b][path].splitlines(True),
                                 f"{path} (before)", f"{path} (after)", n=2)
        return "```diff\n" + "".join(d).rstrip() + "\n```"

    def out_block(m):
        return "```text\n" + outputs[m.group(1)].rstrip() + "\n```"

    def lines(m):
        return str(len(snap[m.group(1)][m.group(2)].splitlines()))

    tpl = re.sub(r"\{\{file (\S+) (\S+)\}\}", file_block, tpl)
    tpl = re.sub(r"\{\{diff (\S+) (\S+) (\S+)\}\}", diff_block, tpl)
    tpl = re.sub(r"\{\{out (\S+)\}\}", out_block, tpl)
    tpl = re.sub(r"\{\{lines (\S+) (\S+)\}\}", lines, tpl)
    head = "".join(BASE["data/transactions.csv"].splitlines(True)[:6])
    tpl = tpl.replace("{{csvhead}}", "```text\n" + head.rstrip() + "\n```")
    assert "{{" not in tpl, "unknown placeholder in GUIDE.template.md"
    (HERE / "README.md").write_text("<!-- generated by make_steps.py from GUIDE.template.md: edit the template, not this file -->\n"
                                    + tpl, encoding="utf-8", newline="\n")


def main():
    files, snap, outputs = dict(BASE), {}, {}
    for i, (name, changes, cmd) in enumerate(STEPS, 1):
        files.update(changes)
        snap[name] = dict(files)
        outputs[name] = write_snapshot(i, name, files, cmd)
        print(f"✓ {name}")
    assert snap[STEPS[-1][0]]["tools.py"] == read("tools.py")
    fill_template(snap, outputs)
    print("✓ README.md")


if __name__ == "__main__":
    main()
