"""Tools for the 'Where Did My Money Go?' agent.

Read-only: these functions take an exported CSV and return numbers and text.
Nothing here can log in to a bank, move money or start a payment.
"""
import os
import re

import pandas as pd

def load_transactions(path):
    """Load a bank/UPI export. Rows we can't trust are dropped, never guessed."""
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["txn_id"] = [f"T{i + 1:03d}" for i in range(len(df))]
    df["description"] = df["description"].fillna("").str.strip()
    df["type"] = df["type"].fillna("debit").str.strip().str.lower()

    amount = df["amount"].str.replace(r"[₹,\s]", "", regex=True)
    df["amount"] = pd.to_numeric(amount, errors="coerce").abs()
    iso = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    other = pd.to_datetime(df["date"], format="mixed", dayfirst=True, errors="coerce")
    df["date"] = iso.fillna(other)       # ISO first, then 05/09/2026, Sep 5 2026

    bad = df["amount"].isna() | df["date"].isna() | (df["description"] == "")
    clean = df[~bad].sort_values("date").reset_index(drop=True)
    report = {"rows_read": len(df), "rows_dropped": int(bad.sum()),
              "dropped_ids": df.loc[bad, "txn_id"].tolist(), "rows_clean": len(clean)}
    return clean, report


if __name__ == "__main__":      # quick check: python tools.py data/transactions.csv
    import sys
    data, report = load_transactions(sys.argv[1])
    print("load:", report)
    print(data[["date", "description", "amount", "type"]].head(5).to_string())
