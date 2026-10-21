"""Run the agent from the terminal: python main.py data/transactions.csv"""
import argparse

from agent import run

parser = argparse.ArgumentParser(description="Where Did My Money Go? (read-only)")
parser.add_argument("csv", help="exported bank / UPI transactions")
args = parser.parse_args()

print("money-agent | read-only: never moves money or contacts your bank\n")
report = run(args.csv)
a = report["analysis"]

print(f"\nSpent in {a['month']}: Rs {a['total']:,}  ({a['mom_change_pct']:+}% vs {a['prev_month']})")
for category, amount in a["by_category"].items():
    print(f"  {category:<14} Rs {amount:>7,}")

print("\nFlagged for review (unusual is not fraud - you decide):")
for f in report["flags"]:
    print(f"  {f['txn_id']}  {f['date']}  {f['merchant']:<24} Rs {f['amount']:>6,}  {f['reasons'][0]}")

print("\nInsights:")
for line in report["insights"]:
    print("  -", line)
print("\nanalysis complete")
