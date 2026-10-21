# Build-along: build the "Where Did My Money Go?" agent yourself

This guide follows the video **scene by scene**. In each step you type the same code the developer types on screen,
run the same command, and compare your output with the real output. At the end you have the same working app as `money-agent/`.

* **The code in this guide is the real code.** It is generated from `money-agent/`, the folder the video was made from,
  so it is exactly what appears on screen.
* **Every step has a checkpoint folder** (`build-along/step-N-…/`) holding the complete project as it is at the end of that step,
  plus `EXPECTED_OUTPUT.txt` with that step's real output. If you get stuck, compare with it or copy it.
* **`check_step.py` checks your work.** Run it after each step. It runs your code and tells you what's right, what's not,
  and how your file differs from the checkpoint.

| Step | Video | You build | Run | Checkpoint |
|---|---|---|---|---|
| 1 | 0:00 – 0:11 | project folders, venv, `requirements.txt`, install | `pip install -r requirements.txt` | [`step-1-setup`](step-1-setup) |
| 2 | 0:11 – 0:18 | `tools.py` v1: load the CSV, which **crashes** | `python tools.py data/transactions.csv` | [`step-2-load-crash`](step-2-load-crash) |
| 3 | 0:18 – 0:24 | fix the loader: amounts, 3 date formats, bad rows | same | [`step-3-fix-loader`](step-3-fix-loader) |
| 4 | 0:24 – 0:34 | categorise: rules → optional LLM → `other` | same | [`step-4-categorise`](step-4-categorise) |
| 5 | 0:34 – 0:42 | analysis + transparent anomaly rules + insights | same | [`step-5-analyse`](step-5-analyse) |
| 6 | 0:42 – 0:50 | `agent.py`: the LangGraph workflow | print the graph | [`step-6-agent-workflow`](step-6-agent-workflow) |
| 7 | 0:50 – 0:56 | `main.py`: the command line | `python main.py data/transactions.csv` | [`step-7-run-cli`](step-7-run-cli) |
| 8 | 0:56 – 1:27 | `app.py` + `templates/index.html`: the dashboard | `python app.py` | [`step-8-dashboard`](step-8-dashboard) |

**You need:** Python **3.10 or newer** (`python --version`), a code editor (the video uses VS Code), and this repo downloaded or cloned.
No API key is needed.

> **Typing it yourself is the point.** Copy-pasting works, but you'll learn far more by typing the code, making mistakes and fixing them.
> The checker shows you exactly which lines differ.

---

## Step 0: where to build

Build in a new folder **inside this repo**, so the checker and the sample data are easy to reach:

```
where-did-my-money-go-video/      ← this repo
├── build-along/                  ← this guide, checkpoints, check_step.py
├── money-agent/                  ← the finished app (the answer key)
└── my-build/                     ← you create this
    └── money-agent/              ← you build the app here
```

Open a terminal in the repo folder (in VS Code: **Terminal → New Terminal**) and run:

```bash
mkdir my-build
cd my-build
```

Commands below are for **macOS / Linux**. Where Windows is different, the **PowerShell** version is given too.

---

## Step 1: Set up the project · video 0:00 – 0:11

The video starts in an empty terminal and creates the project, a virtual environment and the (still empty) files.

**macOS / Linux**
```bash
mkdir money-agent && cd money-agent
python3 -m venv .venv && source .venv/bin/activate
mkdir data templates && touch main.py agent.py tools.py app.py requirements.txt templates/index.html
cp ../../money-agent/data/transactions.csv data/transactions.csv
```

**Windows (PowerShell)**
```powershell
mkdir money-agent; cd money-agent
python -m venv .venv; .venv\Scripts\Activate.ps1
mkdir data, templates
New-Item main.py, agent.py, tools.py, app.py, requirements.txt, templates\index.html
Copy-Item ..\..\money-agent\data\transactions.csv data\transactions.csv
```

> If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.
> When the venv is active your prompt starts with `(.venv)`.

**Why a venv?** It gives this project its own copy of Python packages, so it can't break (or be broken by) other projects.

The video copies `sample_transactions.csv` from Downloads; here you take it from the repo. It holds 133 **synthetic** transactions
for a student, September–October 2026, including three deliberately broken rows.

Now open `requirements.txt` and type:

{{file step-1-setup requirements.txt}}

| Package | Used for |
|---|---|
| `pandas` | reading and cleaning the CSV, totals, grouping |
| `langgraph` | the agent workflow (step 6) |
| `flask` | the web dashboard (step 8) |

Install them (the video does this at 0:08):

```bash
pip install -r requirements.txt
```

**Check:**

```bash
python ../../build-along/check_step.py 1
```

{{out step-1-setup}}

---

## Step 2: Load the transactions (and hit a real error) · video 0:11 – 0:18

Open `tools.py` and type the first version: one function that loads the CSV, plus a quick test at the bottom.

{{file step-2-load-crash tools.py}}

What it does:

* `dtype=str` reads **every column as text** first. We decide how to convert them, instead of letting pandas guess.
* `txn_id` numbers the rows `T001, T002, …` in file order, so problems can be reported by ID.
* `bad = …` marks rows we can't trust (no amount, no date or no description) and drops them. **Dropped, never guessed.**
* The `if __name__ == "__main__":` block only runs when you start this file directly. It's a quick way to test as you build.

Look at the data first (video 0:15):

```bash
head -6 data/transactions.csv                      # Windows: Get-Content data\transactions.csv -Head 6
```

{{csvhead}}

Now run it (video 0:16):

```bash
python tools.py data/transactions.csv
```

It **crashes**, just like in the video:

{{out step-2-load-crash}}

**Read the last line of the traceback first.** `astype(float)` can't turn the text `'15,000'` into a number because of the comma.
The CSV also has `₹9,500`, and dates in three formats (`2026-09-02`, `02/09/2026`, `Sep 5 2026`). Real bank exports are messy;
that's the problem step 3 solves.

**Check** (in this step the checker expects the crash):

```bash
python ../../build-along/check_step.py 2
```

---

## Step 3: Fix the loader properly · video 0:18 – 0:24

Replace the two lines that crashed with these five (lines starting with `-` are removed, `+` are added):

{{diff step-2-load-crash step-3-fix-loader tools.py}}

Line by line:

1. `str.replace(r"[₹,\s]", "", regex=True)` removes the rupee sign, commas and spaces: `"₹9,500"` → `"9500"`.
2. `pd.to_numeric(…, errors="coerce")` converts to numbers; anything that still isn't a number (like `N/A`) becomes `NaN`
   instead of crashing. `.abs()` makes amounts positive (the `type` column says whether money came in or went out).
3. Dates are parsed **twice** on purpose. First as ISO `YYYY-MM-DD`, which is unambiguous. Then everything else with
   `dayfirst=True`, because in India `05/09/2026` means 5 September, not May 9. `iso.fillna(other)` keeps the ISO result when there is one.
4. Anything still missing (`NaN` amount, `NaT` date) is caught by the existing `bad = …` line and reported.

Run it again (video 0:22):

```bash
python tools.py data/transactions.csv
```

{{out step-3-fix-loader}}

Three rows were dropped, and you know exactly which ones and why:
`T018` has the amount `N/A`, `T041` has the date `31/09/2026` (September has 30 days) and `T067` has no description.

```bash
python ../../build-along/check_step.py 3
```

---

## Step 4: Categorise expenses · video 0:24 – 0:34

Add the category rules at the top and four functions below `load_transactions`, and extend the quick test:

{{diff step-3-fix-loader step-4-categorise tools.py}}

<details><summary>Full <code>tools.py</code> after this step ({{lines step-4-categorise tools.py}} lines)</summary>

{{file step-4-categorise tools.py}}

</details>

How a category is decided, in this order (`categorise`):

| Order | Source | Example |
|---|---|---|
| 1 | **you**: your correction (from the dashboard, step 8) | always wins |
| 2 | **type**: credits are `income` | `UPI/CR/FROM PARENT/MONTHLY` |
| 3 | **rule**: a keyword in `RULES` | `swiggy` → food |
| 4 | **llm**: only if `ANTHROPIC_API_KEY` is set, and only if the answer is one of `CATEGORIES` | optional |
| 5 | **fallback**: `other`, so you can see it and fix it | `Raju General Store` |

Things to notice:

* `merchant()` turns `UPI/SWIGGY/442141` into `Swiggy`: split on `/`, spaces and `-`, then drop numbers and noise words (`NOISE`).
* `elif cat := rule_category(desc):` uses the **walrus operator** (Python 3.8+): assign and test in one line.
* The LLM is **optional and validated**. With no key it returns `None` straight away, so the app works offline and gives the same result every time.
  If a model answers something that isn't a known category, the answer is ignored.

Run (video 0:32):

```bash
python tools.py data/transactions.csv
```

{{out step-4-categorise}}

```bash
python ../../build-along/check_step.py 4
```

---

## Step 5: Build the analysis tools · video 0:34 – 0:42

Add `rupees`, `recurring_payments`, `analyse`, `detect_anomalies`, `label`, `generate_insights` and `to_records`, and extend the quick test:

{{diff step-4-categorise step-5-analyse tools.py}}

<details><summary>Full <code>tools.py</code> after this step ({{lines step-5-analyse tools.py}} lines): the final version</summary>

{{file step-5-analyse tools.py}}

</details>

* `analyse` uses a **pivot table** (category × month) to get every month's totals at once. It returns plain numbers in a dict,
  so the same result can be printed (`main.py`), sent as JSON (`app.py`) or checked in a test.
* `recurring_payments`: the same merchant, roughly the same amount (standard deviation ≤ 5% of the mean), at most once a month, in 2+ months.
* `detect_anomalies` uses **three transparent rules**, and every flag says which rule fired:

  | Rule | Why |
  |---|---|
  | amount ≥ 3× your median for that category (and ≥ ₹1,500), except rent | unusual *for you* |
  | first payment to a merchant, ≥ ₹2,500 | new and large |
  | same merchant + same amount within 2 days | possible duplicate charge |

  **Unusual ≠ fraud.** The agent flags for *you* to review. It never blocks anything.
* `generate_insights`: every sentence quotes the numbers it's based on, so you can check it.

Run (video 0:40):

```bash
python tools.py data/transactions.csv
```

{{out step-5-analyse}}

```bash
python ../../build-along/check_step.py 5
```

---

## Step 6: Connect the agent workflow · video 0:42 – 0:50

Open `agent.py` (the video uses **Ctrl+P** → `agent`) and type:

{{file step-6-agent-workflow agent.py}}

How it fits together:

* **`State`** is the agent's shared memory: one dict that flows through the graph. `total=False` means keys can be added along the way.
* **Each node** is a small function: read what it needs from `state`, call one tool, `log()` what happened, and return **only the keys it changed**.
  LangGraph merges that into the state.
* **`build_graph()`** adds the six functions in `STEPS` as nodes and connects them `START → … → END`. To change the order or add a step,
  you change one list.
* **`run()`** is the single entry point used by both `main.py` and `app.py`. Your corrections (`overrides`) and dismissed alerts go in
  as input, so they are re-applied every time.

The video doesn't run anything here, but you can check the graph:

```bash
python -c "from agent import build_graph; print(' -> '.join(build_graph().get_graph().nodes))"
```

{{out step-6-agent-workflow}}

```bash
python ../../build-along/check_step.py 6
```

---

## Step 7: Run the agent · video 0:50 – 0:56

Open `main.py` and type:

{{file step-7-run-cli main.py}}

`argparse` gives you `python main.py --help` for free. `f"{a['mom_change_pct']:+}"` always shows the sign (`+71.4`), and `:>7,` right-aligns numbers with thousands separators.

Run it (video 0:52):

```bash
python main.py data/transactions.csv
```

{{out step-7-run-cli}}

Each log line is one node of the graph running. The full report is also saved in `output/report.json`; open it and look.

```bash
python ../../build-along/check_step.py 7
```

---

## Step 8: Build the dashboard · video 0:56 – 1:27

Open `app.py` and type:

{{file step-8-dashboard app.py}}

* `GET /` serves the page. `POST /api/analyse` saves the uploaded CSV and runs the agent.
* `POST /api/correct` stores your category in `output/state.json` and **re-runs the agent**, so totals recalculate.
  Unknown categories are rejected with `400`.
* `POST /api/dismiss` remembers the alert you reviewed. It is not deleted, just hidden from the review list.

Then open `templates/index.html` (Ctrl+P → `index`) and type the dashboard. It's plain HTML, CSS and JavaScript with no build step.
The donut and month-over-month charts are SVG, drawn by a few lines of JavaScript (`donut()` and `mom()`):

<details><summary><code>templates/index.html</code> ({{lines step-8-dashboard templates/index.html}} lines)</summary>

{{file step-8-dashboard templates/index.html}}

</details>

Start the server (video 1:02):

```bash
python app.py
```

Open **http://localhost:5000** and do what the video does:

1. Click **Choose CSV…**, pick `data/transactions.csv`, and click **Run analysis**. (video 1:05)
2. In **Check these categories**, change the October **Sri Sai Enterprises** row from `other` to `education`. (video 1:13)
   The toast says *Recalculated · education: ₹1,079 → ₹1,489 · other: ₹7,139 → ₹6,729*.
3. In **Flagged for review**, click **Dismiss** on the Amazon alert. (video 1:16) *Alert T074 dismissed · 2 left to review.*

Your terminal shows the same server log as the video (right-hand window at 1:21):

{{out step-8-dashboard}}

Stop the server with **Ctrl+C**, then run the last check (it starts and stops the server by itself):

```bash
python ../../build-along/check_step.py 8
```

---

## You're done 🎉

Your `my-build/money-agent/` now matches `money-agent/` in this repo. Compare them any time:

```bash
python ../../build-along/check_step.py 8 --diff
```

**Next:**

* Try it on your own bank / UPI export (columns `date, description, amount, type`). Everything stays on your computer.
* Turn on the optional LLM step: `pip install anthropic`, then set `ANTHROPIC_API_KEY`.
* Do the exercises in [`docs/HOW_IT_WORKS.md`](../docs/HOW_IT_WORKS.md#4-exercises): a new anomaly rule, a branch in the graph, a budget insight.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pandas'` | the venv isn't active. Run `source .venv/bin/activate` (Windows: `.venv\Scripts\Activate.ps1`) |
| `python3` / `python` not found | on Windows use `python` (or `py`); on macOS / Linux use `python3` to create the venv, then `python` inside it |
| `pip install` fails on Python 3.9 or older | install Python 3.10+ (langgraph needs it) |
| `IndentationError` / `SyntaxError` | Python is strict about spaces: use 4 spaces, not tabs. Run the checker with `--diff` to see the exact line |
| `KeyError: 'description'` | your CSV doesn't have the header `date,description,amount,type`; copy the sample again |
| macOS: `Address already in use` on port 5000 | AirPlay Receiver uses 5000. Turn it off (System Settings → General → AirDrop & Handoff) or change `port=5000` in `app.py` |
| Windows: `UnicodeEncodeError` with `₹` | run `set PYTHONUTF8=1` (cmd) or `$env:PYTHONUTF8=1` (PowerShell), then run again |
| `check_step.py` says "Run this from inside your money-agent folder" | `cd` into `my-build/money-agent` first; adjust `../../build-along/` if your folder is somewhere else |
| Totals differ from the video | you edited `RULES` or the CSV. Fine for learning; `--diff` shows what changed |

*All data is synthetic. The agent is read-only: no bank logins, no payments. Not financial advice.*
