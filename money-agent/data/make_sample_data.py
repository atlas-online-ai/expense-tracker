"""Generate data/transactions.csv: 133 SYNTHETIC student bank/UPI transactions (Sep-Oct 2026).

Nothing here is real. The file is built deterministically (fixed seed), so everyone who runs it
gets exactly the numbers shown in the video: Rs 39,739 spent in Oct 2026 (+71.4% vs Sep),
3 rows that must be dropped, 5 recurring payments, a duplicate charge and two unusual spends.

    python data/make_sample_data.py            # writes data/transactions.csv
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
OUT = Path(__file__).with_name("transactions.csv")

FOOD = ["UPI/SWIGGY/{r}", "UPI/ZOMATO/{r}", "UPI/DOMINOS/{r}", "UPI/BLINKIT/{r}",
        "UPI/CAMPUS CANTEEN/{r}", "UPI/CHAI POINT/{r}"]
TRANSPORT = ["UPI/OLACABS/{r}", "UPI/UBERINDIA/{r}/RIDE", "UPI/RAPIDO/{r}", "UPI/BMRCL METRO/{r}"]


def fit(n, total, lo, hi, centre, median=None, fixed=()):
    """n integer amounts in [lo, hi] that sum to `total`. If `median` is given, the median of
    (amounts + fixed) is steered to it. A small deterministic hill-climb."""
    vals = [max(lo, min(hi, int(random.gauss(centre, centre * 0.35)))) for _ in range(n)]

    def cost(v):
        c = abs(sum(v) - total) * 10
        if median is not None:
            s = sorted(list(v) + list(fixed)); k = len(s)
            med = s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2
            c += abs(med - median) * 40
        return c
    best = cost(vals)
    for step in range(200000):
        if best == 0:
            break
        i, j = random.randrange(n), random.randrange(n)
        oi, oj = vals[i], vals[j]
        d = random.choice([-37, -11, -3, -1, 1, 3, 11, 37])
        vals[i] = max(lo, min(hi, oi + d))
        if step % 2:
            vals[j] = max(lo, min(hi, oj - d))       # paired moves keep the sum
        c = cost(vals)
        if c <= best:
            best = c
        else:
            vals[i], vals[j] = oi, oj
    assert best == 0, ("could not fit", total, best)
    return vals


def build_month(n_slots, fixed, fillers, last_filler_day):
    """Place `fixed` rows at their exact slot (= transaction id), fill the gaps with `fillers`
    and give every filler a date between its fixed neighbours, so the file stays in date order."""
    slots = [None] * n_slots
    for pos, row in fixed.items():
        slots[pos] = row
    free = [i for i in range(n_slots) if slots[i] is None]
    assert len(free) == len(fillers), (len(free), len(fillers))
    random.shuffle(fillers)
    for i, (kind, amount) in zip(free, fillers):
        slots[i] = [None, random.choice(FOOD if kind == "f" else TRANSPORT).format(r=random.randint(100000, 999999)),
                    str(amount), "debit"]
    # dates for fillers: between previous and next fixed date
    def d(i):
        return date.fromisoformat(slots[i][0]) if slots[i][0] and "-" in slots[i][0] else None
    prev = None
    for i in range(n_slots):
        if slots[i][0] is not None:
            if d(i): prev = d(i)
            continue
        nxt = next((d(j) for j in range(i + 1, n_slots) if slots[j][0] and d(j)), last_filler_day)
        nxt = min(nxt, last_filler_day)
        span = max(0, (nxt - prev).days)
        prev = prev + timedelta(days=random.randint(0, min(span, 1)))
        slots[i][0] = prev.isoformat()
    return [tuple(s) for s in slots]


# ---------------- September: T001-T062 (T018 and T041 are broken rows) ----------------
sep_food = fit(26, 7198 - 266, 60, 1100, 270)
sep_trans = fit(18, 2150 - 97 - 157, 30, 400, 110)
sep_fixed = {
    0: ["2026-09-01", "UPI/CR/FROM PARENT/MONTHLY", "15,000", "credit"],
    1: ["2026-09-01", "UPI/OLACABS/3987", "97", "debit"],
    2: ["2026-09-01", "UPI/UBERINDIA/7864/RIDE", "157", "debit"],
    3: ["2026-09-02", "NEFT/HOSTEL FEES/SUNRISE PG", "9500", "debit"],
    4: ["2026-09-02", "UPI/BLINKIT/325127", "266", "debit"],
    9: ["2026-09-05", "ACH/D/NETFLIX.COM/SI", "199", "debit"],
    13: ["2026-09-07", "UPI/HOTSTAR/SI 4471", "299", "debit"],
    17: ["2026-09-08", "UPI/SWIGGY/119923", "N/A", "debit"],          # T018: amount unreadable
    19: ["2026-09-09", "UPI/SPOTIFY STUDENT/SI", "59", "debit"],
    23: ["2026-09-11", "BIL/AIRTEL PREPAID/9845012345", "299", "debit"],
    25: ["2026-09-12", "UPI/BOOKMYSHOW/TKT 2231", "450", "debit"],
    29: ["2026-09-14", "UPI/CR/RAHUL SHARMA/SPLIT", "650", "credit"],
    32: ["2026-09-15", "UPI/COURSERA/882113", "399", "debit"],
    38: ["2026-09-18", "UPI/XEROX CORNER/5521", "251", "debit"],
    40: ["31/09/2026", "UPI/ZOMATO/553201", "312", "debit"],           # T041: impossible date
    44: ["2026-09-20", "POS/AMAZON SELLER SVCS/BLR", "899", "debit"],
    51: ["2026-09-24", "UPI/FLIPKART/772910", "1148", "debit"],
    57: ["2026-09-27", "UPI/SRI SAI ENTERPRISES/3310", "340", "debit"],
}
sep = build_month(62, sep_fixed, [("f", a) for a in sep_food] + [("t", a) for a in sep_trans],
                  date(2026, 9, 30))

# ---------------- October: T063-T133 (T067 is broken) ----------------
tail = [("2026-10-26", "UPI/DOMINOS/773104", "296"), ("2026-10-26", "POS/STEAM GAMES/0011", "899"),
        ("2026-10-28", "UPI/RAJU GENERAL STORE/4410", "230"), ("2026-10-29", "UPI/ZOMATO/918273", "466"),
        ("2026-10-30", "UPI/DOMINOS/662190", "501"), ("2026-10-30", "UPI/SWIGGY/553812", "279"),
        ("2026-10-30", "UPI/DOMINOS/662455", "554"), ("2026-10-30", "UPI/UBERINDIA/9031/RIDE", "73")]
fixed_food_oct = [2450, 296, 466, 501, 279, 554]
oct_food = fit(27, 11930 - sum(fixed_food_oct), 60, 1100, 270, median=278.5,
               fixed=[266] + sep_food + fixed_food_oct)          # median of ALL food spends
oct_trans = fit(16, 2489 - 73, 30, 400, 150)
o = lambda t: t - 63                                             # transaction id -> slot
oct_fixed = {
    o(63): ["2026-10-01", "UPI/CR/FROM PARENT/MONTHLY", "₹15,000", "credit"],
    o(65): ["2026-10-02", "NEFT/HOSTEL FEES/SUNRISE PG", "9500", "debit"],
    o(67): ["2026-10-02", "", "349", "debit"],                    # T067: no description
    o(71): ["2026-10-03", "POS/AMAZON SELLER SVCS/BLR", "1299", "debit"],
    o(74): ["2026-10-04", "POS/AMAZON SELLER SVCS/BLR", "1299", "debit"],   # charged twice?
    o(77): ["2026-10-05", "ACH/D/NETFLIX.COM/SI", "199", "debit"],
    o(80): ["2026-10-06", "UPI/UDEMY/551902", "449", "debit"],
    o(83): ["2026-10-07", "UPI/HOTSTAR/SI 4471", "299", "debit"],
    o(86): ["2026-10-08", "UPI/MYNTRA/223190", "1149", "debit"],
    o(89): ["2026-10-09", "UPI/SPOTIFY STUDENT/SI", "59", "debit"],
    o(92): ["2026-10-10", "UPI/BOOKMYSHOW/TKT 8812", "600", "debit"],
    o(95): ["2026-10-11", "BIL/AIRTEL PREPAID/9845012345", "299", "debit"],
    o(97): ["2026-10-12", "NEFT/CR/SCHOLARSHIP/MERIT", "2000", "credit"],
    o(100): ["2026-10-13", "UPI/FLIPKART/772911", "700", "debit"],
    o(103): ["2026-10-14", "UPI/XEROX CORNER/5521", "130", "debit"],
    o(106): ["2026-10-15", "UPI/SAPNA BOOKS/7781", "500", "debit"],
    o(110): ["2026-10-17", "POS/PVR CINEMAS/ORION", "800", "debit"],
    o(113): ["2026-10-18", "UPI/SRI SAI ENTERPRISES/3310", "410", "debit"],
    o(116): ["2026-10-20", "UPI/ZOMATO/440127", "2450", "debit"],           # big food order
    o(120): ["2026-10-23", "POS/GADGETWORLD ELECTRONICS/482910", "6499", "debit"],
}
for k, (d, desc, amt) in enumerate(tail):
    oct_fixed[o(126 + k)] = [d, desc, amt, "debit"]
octo = build_month(71, oct_fixed, [("f", a) for a in oct_food] + [("t", a) for a in oct_trans],
                   date(2026, 10, 25))

allrows = sep + octo
assert len(allrows) == 133


def no_accidental_duplicates(rows):
    """Only the Amazon pair may look like a duplicate: re-roll any filler that collides."""
    seen = {}
    for i, (d, desc, amt, kind) in enumerate(rows):
        if "-" not in d or not desc or "AMAZON" in desc:
            continue
        key = (desc.split("/")[1], amt)
        day = date.fromisoformat(d)
        if key in seen and abs((day - seen[key]).days) <= 2:
            return i
        seen[key] = day
    return None


while (i := no_accidental_duplicates(allrows)) is not None:
    d, desc, amt, kind = allrows[i]
    allrows[i] = (d, random.choice(FOOD if any(f.split("/")[1] in desc for f in FOOD) else TRANSPORT)
                  .format(r=random.randint(100000, 999999)), amt, kind)


def humanise(i, row):
    """Write some rows the way real exports look: other date formats, currency symbols."""
    d, desc, amt, kind = row
    if i in (0, 17, 40, 62, 66):
        return row
    if "-" in d and i % 9 == 4:
        y, m, dd = d.split("-"); d = f"{dd}/{m}/{y}"                    # 05/09/2026
    elif "-" in d and i % 13 == 7:
        d = date.fromisoformat(d).strftime("%b %d %Y").replace(" 0", " ")   # Sep 5 2026
    if i % 11 == 3 and amt.isdigit():
        amt = f"₹{int(amt):,}"
    return d, desc, amt, kind


with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "type"])
    for i, row in enumerate(allrows):
        w.writerow(humanise(i, row))
print(f"wrote {OUT} ({len(allrows)} rows, synthetic sample data)")
