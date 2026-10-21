#!/usr/bin/env python3
"""
check_step.py: check YOUR money-agent after each step of the build-along.

Run it from inside the money-agent folder you are building, with your venv active:

    python ../build-along/check_step.py 3          # adjust the path to where the repo is
    python ../build-along/check_step.py 3 --diff   # also show how your files differ from the reference

It runs your code the way the video does and checks for the results the video shows.
If something is wrong it tells you what it expected and shows the difference between your file and
the reference snapshot in build-along/step-N-.../
"""
import difflib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = {1: "step-1-setup", 2: "step-2-load-crash", 3: "step-3-fix-loader", 4: "step-4-categorise",
         5: "step-5-analyse", 6: "step-6-agent-workflow", 7: "step-7-run-cli", 8: "step-8-dashboard"}
CHANGED = {1: ["requirements.txt"], 2: ["tools.py"], 3: ["tools.py"], 4: ["tools.py"], 5: ["tools.py"],
           6: ["agent.py"], 7: ["main.py"], 8: ["app.py", "templates/index.html"]}
CHAIN = ("__start__ -> load_transactions -> categorise_expenses -> analyse_spending -> detect_anomalies"
         " -> generate_insights -> prepare_report -> __end__")
if os.name == "nt":
    os.system("")                                   # turn on colour codes in the Windows console
try:
    sys.stdout.reconfigure(errors="replace")        # never crash on ✓ / ₹ in an old console
except Exception:
    pass
GREEN, RED, DIM, END = ("\033[32m", "\033[31m", "\033[2m", "\033[0m") if sys.stdout.isatty() else ("",) * 4
results = []


def env():
    e = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    e.pop("ANTHROPIC_API_KEY", None)               # the checks use the offline, deterministic path
    return e


def py(*args, timeout=180):
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env(), timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def check(ok, what, hint=""):
    results.append(ok)
    print(f"  {GREEN + '✓' if ok else RED + '✗'}{END} {what}")
    if not ok and hint:
        print(f"    {DIM}{hint}{END}")
    return ok


def contains(out, *needles):
    return all(n in out for n in needles)


def show_diff(step):
    ref = HERE / STEPS[step]
    for name in CHANGED[step]:
        mine = Path(name)
        if not mine.exists():
            print(f"\n  {RED}{name} is missing{END}")
            continue
        a = (ref / name).read_text(encoding="utf-8").splitlines()
        b = mine.read_text(encoding="utf-8").splitlines()
        d = list(difflib.unified_diff(a, b, f"reference {STEPS[step]}/{name}", f"yours {name}", n=1, lineterm=""))
        if not d:
            print(f"\n  {GREEN}{name} is identical to the reference{END}")
            continue
        print(f"\n  {name}: lines starting with - are in the reference, + are in your file")
        for line in d[:80]:
            print("   ", (GREEN if line.startswith("+") else RED if line.startswith("-") else DIM) + line + END)
        if len(d) > 80:
            print(f"    … {len(d) - 80} more lines")


# --------------------------------------------------------------------------- the checks
def step1():
    for f in ["requirements.txt", "main.py", "agent.py", "tools.py", "app.py", "templates/index.html", "data/transactions.csv"]:
        check(Path(f).exists(), f"{f} exists", "create it (step 1, 'Create the project files')")
    req = Path("requirements.txt").read_text(encoding="utf-8").lower() if Path("requirements.txt").exists() else ""
    check(contains(req, "pandas", "langgraph", "flask"), "requirements.txt lists pandas, langgraph and flask")
    if Path("data/transactions.csv").exists():
        rows = Path("data/transactions.csv").read_text(encoding="utf-8").splitlines()
        check(len(rows) == 134 and rows[0].startswith("date,description,amount,type"),
              f"data/transactions.csv has the header + 133 rows (found {len(rows) - 1})",
              "copy money-agent/data/transactions.csv from the repo")
    code, out = py("-c", "import pandas, langgraph, flask; print('ready')")
    check(code == 0, "pandas, langgraph and flask are installed in this Python",
          "activate your venv, then: pip install -r requirements.txt")
    check(".venv" in sys.prefix or sys.prefix != sys.base_prefix, f"running inside a virtual environment ({sys.prefix})",
          "activate it: source .venv/bin/activate  (Windows: .venv\\Scripts\\activate)")


def run_tools():
    return py("tools.py", "data/transactions.csv")


def step2():
    code, out = run_tools()
    check(code != 0 and "ValueError" in out and "15,000" in out,
          "tools.py crashes with ValueError on '15,000' (this is the bug the video fixes next)",
          "in this step load_transactions must still use .astype(float) and pd.to_datetime(...)"
          + (" - your file already runs, so you may have done step 3 already" if code == 0 else ""))


def step3():
    code, out = run_tools()
    check(code == 0, "tools.py runs without an error", out.strip().splitlines()[-1] if out.strip() else "")
    check(contains(out, "'rows_read': 133", "'rows_dropped': 3", "['T018', 'T041', 'T067']", "'rows_clean': 130"),
          "133 rows read, 3 dropped (T018, T041, T067), 130 clean")
    code, res = py("-c", "import tools; d, _ = tools.load_transactions('data/transactions.csv'); "
                         "a = dict(zip(d.txn_id, d.amount)); "
                         "print('AMT', a.get('T001'), a.get('T004')); print('DATES', d.date.min().date(), d.date.max().date())")
    check("AMT 15000.0 9500.0" in res, "amounts cleaned: '15,000' → 15000.0 and '₹9,500' → 9500.0", res.strip()[-300:])
    check("DATES 2026-09-01 2026-10-30" in res, "all three date formats parsed day-first (dates run 1 Sep → 30 Oct 2026)",
          "check the two pd.to_datetime lines: ISO format first, then format=\"mixed\", dayfirst=True" + 
          (f"  (found {res.split('DATES')[1].strip()})" if "DATES" in res else ""))
    return out


def step4():
    out = step3()
    check(contains(out, "Raju General Store", "fallback", "Steam Games", "entertainment"),
          "categories and sources printed (Raju General Store -> other / fallback)")
    code, src = py("-c", "import tools; d, _ = tools.load_transactions('data/transactions.csv'); "
                         "print(tools.categorise(d)['source'].value_counts().to_dict())")
    check(code == 0 and contains(src, "'rule': 122", "'type': 4", "'fallback': 4"),
          "sources: 122 rule, 4 type (credits), 4 fallback", src.strip()[-300:])
    return out


def step5():
    out = step4()
    check(contains(out, "total 2026-10 39739", "change 71.4 %"), "Oct 2026 total ₹39,739, +71.4% vs Sep")
    check(contains(out, "'food': 11930", "'other': 7139"), "category totals match (food 11,930 · other 7,139)")
    check(contains(out, "REVIEW T074", "REVIEW T116", "REVIEW T120"), "3 flagged for review: T074, T116, T120")
    check(contains(out, "possible duplicate", "8.8x your usual food spend", "17.3x your usual other spend"),
          "each flag explains its rule")


def step6():
    code, out = py("-c", "from agent import build_graph; print(' -> '.join(build_graph().get_graph().nodes))")
    check(code == 0 and CHAIN in out, "the LangGraph graph is START -> 6 nodes -> END", out.strip()[-300:])
    code, out = py("-c", "from agent import run; r = run('data/transactions.csv'); "
                         "print('RESULT', r['analysis']['total'], [f['txn_id'] for f in r['flags']], len(r['insights']))")
    check(code == 0 and "RESULT 39739 ['T074', 'T116', 'T120'] 4" in out,
          "run() returns the report: ₹39,739, 3 flags, 4 insights", out.strip()[-300:])
    check(Path("output/report.json").exists(), "output/report.json was written")


def step7():
    code, out = py("main.py", "data/transactions.csv")
    check(code == 0, "python main.py data/transactions.csv runs", out.strip()[-300:])
    check(contains(out, "Spent in 2026-10: Rs 39,739  (+71.4% vs 2026-09)"), "summary line matches the video")
    check(contains(out, "food           Rs  11,930", "T120  23 Oct  Gadgetworld Electronics"), "categories and flags printed")
    check(contains(out, "5 recurring payments cost ₹10,356 every month.", "analysis complete"), "insights printed")


def step8():
    for f in ["app.py", "templates/index.html"]:
        check(Path(f).exists() and Path(f).stat().st_size > 0, f"{f} is written")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 5000)) == 0:
            return check(False, "port 5000 is free", "stop your own `python app.py` (Ctrl+C) and run the check again")
    srv = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env())
    try:
        up = False
        for _ in range(60):
            try:
                html = urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1).read().decode("utf-8"); up = True; break
            except Exception:
                time.sleep(0.25)
        if not check(up, "python app.py serves http://localhost:5000"):
            return
        check("Where Did My Money Go?" in html and 'id="run"' in html, "the dashboard page loads (templates/index.html)")
        b = "----check"
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"transactions.csv\"\r\n"
                "Content-Type: text/csv\r\n\r\n").encode() + Path("data/transactions.csv").read_bytes() + f"\r\n--{b}--\r\n".encode()

        def post(url, data, ctype):
            req = urllib.request.Request("http://127.0.0.1:5000" + url, data=data, headers={"Content-Type": ctype})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        r1 = post("/api/analyse", body, f"multipart/form-data; boundary={b}")
        check(r1["analysis"]["total"] == 39739 and len(r1["flags"]) == 3, "upload → analysis: ₹39,739 and 3 flags")
        fix = next(t for t in r1["transactions"] if t["merchant"] == "Sri Sai Enterprises" and t["date"] > "2026-10")
        r2 = post("/api/correct", json.dumps({"txn_id": fix["txn_id"], "category": "education"}).encode(), "application/json")
        bm = r2["analysis"]["by_month"]["2026-10"]
        check((bm["education"], bm["other"]) == (1489, 6729), "correcting Sri Sai → education: education ₹1,489, other ₹6,729")
        r3 = post("/api/dismiss", json.dumps({"txn_id": r2["flags"][0]["txn_id"]}).encode(), "application/json")
        check(len(r3["flags"]) == 2, "dismissing an alert leaves 2 to review")
        saved = json.loads(Path("output/state.json").read_text(encoding="utf-8"))
        check(saved["overrides"].get(fix["txn_id"]) == "education" and saved["dismissed"],
              "your correction and dismissal are saved in output/state.json")
    except Exception as e:
        check(False, f"the dashboard API answered ({e.__class__.__name__}: {e})")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args or not args[0].isdigit() or int(args[0]) not in STEPS:
        sys.exit(__doc__)
    step = int(args[0])
    if not Path("data").is_dir() and step > 1:
        sys.exit("Run this from inside your money-agent folder (the one with tools.py and data/).")
    print(f"\nChecking step {step}: {STEPS[step]}   (Python: {sys.executable})")
    {1: step1, 2: step2, 3: step3, 4: step4, 5: step5, 6: step6, 7: step7, 8: step8}[step]()
    ok = all(results)
    if not ok or "--diff" in sys.argv:
        show_diff(step)
    print(f"\n{GREEN}Step {step} done ✓ - on to step {step + 1}!{END}" if ok and step < 8 else
          f"\n{GREEN}All 8 steps done ✓ - you built the whole app. Open http://localhost:5000 after: python app.py{END}" if ok else
          f"\n{RED}Not yet - fix the ✗ items above.{END} The reference for this step is in build-along/{STEPS[step]}/")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
