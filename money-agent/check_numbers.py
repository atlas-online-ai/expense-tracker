"""Self-check: run the real agent on the sample CSV and confirm the numbers shown in the video.

    python check_numbers.py

Works offline and needs no API key (the LLM step is optional and skipped when not configured).
"""
import os

os.environ.pop("ANTHROPIC_API_KEY", None)        # keep the run deterministic

import tools                                       # noqa: E402
from agent import run                              # noqa: E402

report = run("data/transactions.csv")
a, load = report["analysis"], report["load"]
checks = [
    ("rows read / dropped / clean", (load["rows_read"], load["rows_dropped"], load["rows_clean"]), (133, 3, 130)),
    ("dropped rows", load["dropped_ids"], ["T018", "T041", "T067"]),
    ("Oct 2026 spend", a["total"], 39739),
    ("Sep 2026 spend", a["totals"]["2026-09"], 23191),
    ("change vs Sep", a["mom_change_pct"], 71.4),
    ("debits in Oct", a["txn_count"], 68),
    ("food in Oct", a["by_category"]["food"], 11930),
    ("recurring per month", sum(r["amount"] for r in a["recurring"]), 10356),
    ("flagged", [f["txn_id"] for f in report["flags"]], ["T074", "T116", "T120"]),
]
ok = True
for name, got, want in checks:
    good = got == want
    ok &= good
    print(f"{'✓' if good else '✗'} {name:<26} {got}" + ("" if good else f"   (expected {want})"))

# your correction wins and totals recalculate (scene 8 of the video)
fix = next(t["txn_id"] for t in report["transactions"]
           if t["merchant"] == "Sri Sai Enterprises" and t["date"].startswith("2026-10"))
after = run("data/transactions.csv", overrides={fix: "education"})["analysis"]["by_category"]
good = (after["education"], after["other"]) == (1489, 6729)
ok &= good
print(f"{'✓' if good else '✗'} correction -> education/other  {after['education']} / {after['other']}")
print("\nAll numbers match the video." if ok else "\nSomething differs - did you edit tools.py or the sample data?")
raise SystemExit(0 if ok else 1)
