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


def rupees(value):
    return int(round(float(value)))


def recurring_payments(df):
    """Same merchant, about the same amount, once a month, in 2+ months."""
    spend = df[df["type"] == "debit"].assign(month=df["date"].dt.strftime("%Y-%m"))
    found = []
    for name, g in spend.groupby("merchant"):
        per_month = g.groupby("month").size()
        steady = g["amount"].std(ddof=0) <= 0.05 * g["amount"].mean()
        if len(per_month) >= 2 and per_month.max() == 1 and steady:
            found.append({"merchant": name, "amount": rupees(g["amount"].mean()),
                          "category": g["category"].iloc[0], "months": len(per_month)})
    return sorted(found, key=lambda r: -r["amount"])


def analyse(df):
    """Totals, category split, month-over-month change and recurring payments."""
    spend = df[df["type"] == "debit"].assign(month=df["date"].dt.strftime("%Y-%m"))
    months = sorted(spend["month"].unique())
    cur = months[-1]
    prev = months[-2] if len(months) > 1 else None
    pivot = spend.pivot_table(index="category", columns="month", values="amount",
                              aggfunc="sum", fill_value=0)
    by_month = {m: {c: rupees(pivot.loc[c, m]) for c in pivot.index if pivot.loc[c, m] > 0}
                for m in months}
    totals = {m: sum(v.values()) for m, v in by_month.items()}
    by_cat = dict(sorted(by_month[cur].items(), key=lambda kv: -kv[1]))
    change = round((totals[cur] - totals[prev]) / totals[prev] * 100, 1) if prev else None
    return {"month": cur, "prev_month": prev, "months": months,
            "total": totals[cur], "totals": totals, "mom_change_pct": change,
            "txn_count": int((spend["month"] == cur).sum()),
            "count_by_month": spend["month"].value_counts().to_dict(),
            "by_category": by_cat, "by_month": by_month,
            "recurring": recurring_payments(df)}


def detect_anomalies(df, dismissed=()):
    """Flag spends worth a second look. Flagged does NOT mean fraud - only
    'unusual for you'. Each flag names the rule that triggered it."""
    spend = df[df["type"] == "debit"]
    medians = spend.groupby("category")["amount"].median()
    seen = spend["merchant"].value_counts()
    flags = []
    for row in spend.itertuples():
        reasons = []
        usual = medians[row.category]
        if row.category != "rent" and row.amount >= max(3 * usual, 1500):
            reasons.append(f"{row.amount / usual:.1f}x your usual {row.category} spend")
        if seen[row.merchant] == 1 and row.amount >= 2500:
            reasons.append("first payment to this merchant, over ₹2,500")
        twin = spend[(spend["merchant"] == row.merchant) & (spend["amount"] == row.amount)
                     & ((spend["date"] - row.date).abs() <= pd.Timedelta(days=2))]
        if len(twin) > 1 and row.txn_id != twin["txn_id"].iloc[0]:
            reasons.append("same merchant and amount within 2 days - possible duplicate")
        if reasons and row.txn_id not in dismissed:
            flags.append({"txn_id": row.txn_id, "date": row.date.strftime("%d %b"),
                          "merchant": row.merchant, "amount": rupees(row.amount),
                          "category": row.category, "reasons": reasons})
    return flags


def label(month):
    return pd.Period(month).strftime("%b %Y")


def generate_insights(a, flags):
    """Short observations. Every sentence quotes the numbers behind it."""
    cats, total = a["by_category"], a["total"]
    everyday = {c: v for c, v in cats.items() if c not in ("rent", "bills", "subscriptions")}
    top = max(everyday, key=everyday.get)
    out = [f"{top.title()} is your biggest everyday expense: ₹{everyday[top]:,} "
           f"({everyday[top] / total:.0%} of {label(a['month'])} spending)."]
    if a["prev_month"]:
        before = a["by_month"][a["prev_month"]]
        rise = {c: v - before.get(c, 0) for c, v in everyday.items() if c != "other"}
        c = max(rise, key=rise.get)
        if rise[c] > 0:
            out.append(f"{c.title()} rose ₹{rise[c]:,} vs {label(a['prev_month'])} "
                       f"(₹{before.get(c, 0):,} -> ₹{cats[c]:,}).")
    monthly = sum(r["amount"] for r in a["recurring"])
    out.append(f"{len(a['recurring'])} recurring payments cost ₹{monthly:,} every month.")
    if flags:
        out.append(f"{len(flags)} payment(s) look unusual. Unusual is not fraud - "
                   "check them against your own records.")
    return out


def to_records(df):
    out = df.assign(date=df["date"].dt.strftime("%Y-%m-%d"))
    cols = ["txn_id", "date", "description", "merchant", "amount", "type", "category", "source"]
    return out[cols].to_dict(orient="records")


if __name__ == "__main__":      # quick check: python tools.py data/transactions.csv
    import sys
    data, report = load_transactions(sys.argv[1])
    print("load:", report)
    print(data[["date", "description", "amount", "type"]].head(5).to_string())
    data = categorise(data)
    print(data[["date", "merchant", "amount", "category", "source"]].tail(8).to_string())
    result = analyse(data)
    print("total", result["month"], result["total"], "| change", result["mom_change_pct"], "%")
    print("by category:", result["by_category"])
    for flag in detect_anomalies(data):
        print("REVIEW", flag["txn_id"], flag["merchant"], flag["amount"], flag["reasons"])
