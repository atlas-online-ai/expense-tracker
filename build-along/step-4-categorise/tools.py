"""Tools for the 'Where Did My Money Go?' agent.

Read-only: these functions take an exported CSV and return numbers and text.
Nothing here can log in to a bank, move money or start a payment.
"""
import os
import re

import pandas as pd

CATEGORIES = ["food", "transport", "shopping", "rent", "bills", "subscriptions",
              "education", "entertainment", "other"]

RULES = {
    "food": ["swiggy", "zomato", "canteen", "chai", "dominos", "blinkit"],
    "transport": ["uber", "ola", "rapido", "metro", "irctc"],
    "shopping": ["amazon", "flipkart", "myntra", "ajio"],
    "rent": ["hostel", "pg rent"],
    "bills": ["airtel", "jio", "bescom", "fibernet"],
    "subscriptions": ["netflix", "spotify", "hotstar", "icloud"],
    "education": ["coursera", "udemy", "books", "xerox"],
    "entertainment": ["bookmyshow", "pvr", "steam"],
}
NOISE = {"upi", "pos", "ach", "d", "bil", "neft", "cr", "pay", "ride", "si", "tkt", "ord"}


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


def merchant(description):
    words = re.split(r"[/\s\-]+", description.lower().replace(".com", ""))
    keep = [w for w in words if w and not w.isdigit() and w not in NOISE]
    return " ".join(keep[:3]).title() or "Unknown"


def rule_category(description):
    text = description.lower()
    for category, keywords in RULES.items():
        if any(k in text for k in keywords):
            return category
    return None


def llm_category(description):
    """Ask an LLM only when the rules can't decide. The answer is validated."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None                      # not configured -> deterministic fallback
    try:
        import anthropic
        reply = anthropic.Anthropic().messages.create(
            model=os.getenv("MONEY_AGENT_MODEL", "claude-haiku-4-5"), max_tokens=10,
            messages=[{"role": "user", "content": f"Classify this bank transaction into "
                       f"one of {CATEGORIES}. Reply with the category only.\n{description}"}])
        answer = reply.content[0].text.strip().lower()
    except Exception:
        return None
    return answer if answer in CATEGORIES else None


def categorise(df, overrides=None):
    """Your corrections win, then rules, then the LLM, then 'other'."""
    overrides = overrides or {}
    cats, sources = [], []
    for txn_id, desc, kind in zip(df["txn_id"], df["description"], df["type"]):
        if txn_id in overrides:
            cat, src = overrides[txn_id], "you"
        elif kind == "credit":
            cat, src = "income", "type"
        elif cat := rule_category(desc):
            src = "rule"
        elif cat := llm_category(desc):
            src = "llm"
        else:
            cat, src = "other", "fallback"
        cats.append(cat)
        sources.append(src)
    df = df.assign(category=cats, source=sources)
    df["merchant"] = df["description"].map(merchant)
    return df


if __name__ == "__main__":      # quick check: python tools.py data/transactions.csv
    import sys
    data, report = load_transactions(sys.argv[1])
    print("load:", report)
    print(data[["date", "description", "amount", "type"]].head(5).to_string())
    data = categorise(data)
    print(data[["date", "merchant", "amount", "category", "source"]].tail(8).to_string())
