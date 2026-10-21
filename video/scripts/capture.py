#!/usr/bin/env python3
"""
capture.py: run the REAL money-agent at every stage of the build and save what happened,
so the video only ever shows real output. Writes video/src/captured.js.

What it records
  * every version of every source file the video types (tools.py is built up in 4 steps)
    and the exact text edits between versions
  * the real terminal output of each command (pip install, the first crash, each run)
  * the real Flask server log and the JSON reports the dashboard receives
    (initial analysis, after a category correction, after dismissing an alert)

Run it from the repo root with the agent's dependencies installed:
    pip install -r money-agent/requirements.txt
    python video/scripts/capture.py            # add --skip-pip to reuse the last pip transcript
"""
import argparse, difflib, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "money-agent"
OUT = ROOT / "video" / "src" / "captured.js"
SHOWN = "/home/dev/projects/money-agent"        # the path the video pretends to use


# ------------------------------------------------------------------ file versions
def tools_versions():
    final = (APP / "tools.py").read_text(encoding="utf-8")
    main_at = final.index('if __name__ == "__main__":')
    s4_start = final.index("def rupees(")
    s3_start, s3_end = final.index("def merchant("), s4_start
    rules_start, rules_end = final.index("CATEGORIES = ["), final.index("def load_transactions(")
    main_block = final[main_at:]
    main3 = main_block[:main_block.index('    result = analyse(data)')]
    main1 = main3[:main3.index('    data = categorise(data)')]
    v4 = final
    v3 = final[:s4_start] + main3
    v2 = final[:rules_start] + final[rules_end:s3_start] + main1
    fix_new = ('    amount = df["amount"].str.replace(r"[₹,\\s]", "", regex=True)\n'
               '    df["amount"] = pd.to_numeric(amount, errors="coerce").abs()\n'
               '    iso = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")\n'
               '    other = pd.to_datetime(df["date"], format="mixed", dayfirst=True, errors="coerce")\n'
               '    df["date"] = iso.fillna(other)       # ISO first, then 05/09/2026, Sep 5 2026\n')
    assert fix_new in v2, "tools.py changed - update the 'fix' block in capture.py"
    fix_old = ('    df["amount"] = df["amount"].astype(float)\n'
               '    df["date"] = pd.to_datetime(df["date"])\n')
    v1 = v2.replace(fix_new, fix_old)
    return [v1, v2, v3, v4]


def hunks(old, new):
    """Line-level diff -> list of {pos, del, ins} edits, applied one after another."""
    a, b = old.splitlines(keepends=True), new.splitlines(keepends=True)
    out, shift = [], 0
    offs = [0]
    for line in a:
        offs.append(offs[-1] + len(line))
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        ins, dele = "".join(b[j1:j2]), offs[i2] - offs[i1]
        out.append({"pos": offs[i1] + shift, "del": dele, "ins": ins})
        shift += len(ins) - dele
    return out


# ------------------------------------------------------------------ helpers
def run(cmd, cwd, env=None, timeout=600):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=timeout)
    return p.stdout + p.stderr


def clean(text, work):
    text = "\n".join(l for l in text.splitlines() if not l.startswith("[notice]"))
    text = text.replace(str(work), SHOWN).replace(sys.prefix, SHOWN + "/.venv")
    text = re.sub(r"/[^\s\"']*/site-packages", SHOWN + "/.venv/lib/python3.13/site-packages", text)
    return text.rstrip("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pip", action="store_true", help="reuse the pip transcript from the last capture")
    args = ap.parse_args()
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))

    work = Path(tempfile.mkdtemp(prefix="money-agent-")) / "money-agent"
    shutil.copytree(APP, work, ignore=shutil.ignore_patterns("output", "uploads", "__pycache__", ".venv"))
    py = sys.executable
    term = {}

    # pip install (real, into a throw-away venv; uses the pip cache so it is quick the 2nd time)
    if args.skip_pip and "pip" in old.get("term", {}):
        term["pip"] = "\n".join(l for l in old["term"]["pip"].splitlines() if not l.startswith("[notice]")).rstrip()
    else:
        print("capturing pip install (one minute) ...")
        run(f'"{py}" -m venv .venv', work)
        pip = work / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "pip"
        term["pip"] = clean(run(f'"{pip}" install -r requirements.txt', work, timeout=900), work)
        shutil.rmtree(work / ".venv", ignore_errors=True)

    # what `head -6 data/transactions.csv` prints (read in Python so this also works on Windows)
    term["head"] = "".join((work / "data" / "transactions.csv").read_text(encoding="utf-8").splitlines(True)[:6]).rstrip("\n")

    versions = tools_versions()
    for i, v in enumerate(versions, 1):
        (work / "tools.py").write_text(v, encoding="utf-8")
        term[f"tools_v{i}"] = clean(run(f'"{py}" tools.py data/transactions.csv', work), work)
    assert "ValueError" in term["tools_v1"], "the first version should crash on '15,000'"

    term["main"] = clean(run(f'"{py}" main.py data/transactions.csv', work), work)

    # Flask: start the real server, drive it like the video does, keep the log + JSON
    shutil.rmtree(work / "output", ignore_errors=True)
    log = open(work / "server.log", "w", encoding="utf-8")
    srv = subprocess.Popen([py, "app.py"], cwd=work, stdout=log, stderr=subprocess.STDOUT,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1); break
            except Exception:
                time.sleep(0.25)
        boundary = "----capture"
        csv_bytes = (work / "data" / "transactions.csv").read_bytes()
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"transactions.csv\"\r\n"
                f"Content-Type: text/csv\r\n\r\n").encode() + csv_bytes + f"\r\n--{boundary}--\r\n".encode()
        def post(url, data, ctype):
            req = urllib.request.Request("http://127.0.0.1:5000" + url, data=data, headers={"Content-Type": ctype})
            return json.loads(urllib.request.urlopen(req).read())
        r1 = post("/api/analyse", body, f"multipart/form-data; boundary={boundary}")
        fix = next(t for t in r1["transactions"] if t["merchant"] == "Sri Sai Enterprises" and t["date"] > "2026-10")
        r2 = post("/api/correct", json.dumps({"txn_id": fix["txn_id"], "category": "education"}).encode(), "application/json")
        r3 = post("/api/dismiss", json.dumps({"txn_id": r2["flags"][0]["txn_id"]}).encode(), "application/json")
        time.sleep(0.5)
    finally:
        srv.terminate(); srv.wait(); log.close()
    server = (work / "server.log").read_text(encoding="utf-8")
    server = re.sub(r"\x1b\[[0-9;]*m", "", server)
    term["server"] = clean(server, work)

    files = {name: (APP / name).read_text(encoding="utf-8") for name in
             ["requirements.txt", "agent.py", "main.py", "app.py", "templates/index.html"]}
    data = {
        "files": files,
        "tools_versions": versions,
        "tools_hunks": [hunks(a, b) for a, b in zip([""] + versions[:-1], versions)],
        "term": term,
        "reports": [r1, r2, r3],
        "corrected": fix["txn_id"],
        "dashboard": (APP / "templates" / "index.html").read_text(encoding="utf-8"),
        "captured_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    OUT.write_text("// generated by video/scripts/capture.py - real output of the money-agent\nwindow.CAP = "
                   + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.0f} KB)")
    shutil.rmtree(work.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
