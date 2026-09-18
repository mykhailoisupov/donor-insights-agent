"""Generate a synthetic nonprofit donations dataset with planted events.

Every donor, gift and organisation here is fake. The planted events in EVENTS
are the ground truth that the agent's explanations are graded against.

Run: python data/generate.py
Writes: data/donors.csv, data/gifts.csv, data/events.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
MONTHS = pd.period_range("2023-01", "2026-08", freq="M")
OUT = Path(__file__).parent

FIRST = ["Olena", "Andrii", "Maria", "John", "Sarah", "David", "Iryna", "Taras", "Emma",
         "Michael", "Sofia", "Petro", "Laura", "James", "Natalia", "Oleh", "Anna", "Robert"]
LAST = ["Kovalenko", "Smith", "Bondar", "Miller", "Shevchuk", "Brown", "Melnyk", "Wilson",
        "Tkachenko", "Moore", "Kravets", "Taylor", "Lysenko", "Clark", "Hnatyuk", "Walker"]
COUNTRIES = ["US", "UA", "DE", "GB", "PL", "CA"]
COUNTRY_P = [0.40, 0.25, 0.10, 0.10, 0.08, 0.07]

# (name, gift size in USD, months between gifts)
INSTITUTIONS = [
    ("Northbridge Family Foundation", 150_000, 12),
    ("Harbor Light Trust", 40_000, 1),
    ("Meridian Giving Fund", 60_000, 3),
    ("Aster Education Foundation", 250_000, 12),
    ("Blue Ridge Community Fund", 25_000, 6),
    ("Kestrel Partners LLC", 80_000, 12),
    ("Open Future Initiative", 30_000, 3),
    ("Linden Charitable Trust", 120_000, 12),
]

EVENTS = [
    {"id": "mega_gift", "month": "2024-11",
     "description": "Northbridge Family Foundation gives a one-off $5,000,000 wire."},
    {"id": "card_outage", "month": "2025-03",
     "description": "Card processor outage: recurring card subscriptions churn at 3x the normal rate."},
    {"id": "year_end_campaign", "month": "2025-12",
     "description": "Year-end campaign doubles new donor acquisition (one-off and recurring)."},
    {"id": "paypal_default", "month": "2026-02",
     "description": "New checkout makes PayPal the default: PayPal share of new one-off gifts "
                    "jumps from about 20% to about 50% from this month on."},
    {"id": "major_donor_lapse", "month": "2026-05",
     "description": "Harbor Light Trust, which gave $40,000 every month, stops giving."},
]

BASE_NEW_ONE_OFF = 120      # new one-off donors per month
BASE_NEW_RECURRING = 25     # new recurring subscriptions per month
REPEAT_RATE = 0.02          # monthly chance a past one-off donor gives again
CHURN = 0.035               # monthly churn of recurring subscriptions
RECURRING_AMOUNTS = [10, 20, 25, 50, 100]
RECURRING_P = [0.25, 0.30, 0.20, 0.18, 0.07]


def season(month):
    return {11: 1.2, 12: 1.8}.get(month.month, 1.0)


def random_date(rng, month):
    return month.start_time + pd.Timedelta(days=int(rng.integers(0, month.days_in_month)))


def main():
    rng = np.random.default_rng(SEED)
    donors, gifts = [], []

    def new_donor(kind, name=None):
        donor_id = f"D{len(donors) + 1:05d}"
        if name is None:
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        country = "US" if kind == "organization" else rng.choice(COUNTRIES, p=COUNTRY_P)
        donors.append({"donor_id": donor_id, "name": name, "type": kind, "country": country})
        return donor_id

    def add_gift(donor_id, month, amount, platform, gift_type):
        gifts.append({"donor_id": donor_id, "date": random_date(rng, month),
                      "amount_usd": round(float(amount), 2), "platform": platform,
                      "gift_type": gift_type,
                      "campaign": "year_end" if month.month == 12 else "general"})

    institutions = {name: new_donor("organization", name) for name, _, _ in INSTITUTIONS}
    one_off_donors = []
    subscriptions = []  # dicts: donor_id, amount, platform

    for i, month in enumerate(MONTHS):
        m = str(month)
        campaign = 2.0 if m == "2025-12" else 1.0
        paypal_p = 0.5 if month >= pd.Period("2026-02", "M") else 0.2

        # Institutional wires
        for j, (name, size, every) in enumerate(INSTITUTIONS):
            if name == "Harbor Light Trust" and month >= pd.Period("2026-05", "M"):
                continue
            if i % every == j % every:
                add_gift(institutions[name], month, size * rng.uniform(0.8, 1.2), "wire",
                         "institutional")
        if m == "2024-11":
            add_gift(institutions["Northbridge Family Foundation"], month, 5_000_000, "wire",
                     "institutional")

        # One-off gifts: new donors, then repeat donors
        for _ in range(rng.poisson(BASE_NEW_ONE_OFF * season(month) * campaign)):
            donor_id = new_donor("individual")
            one_off_donors.append(donor_id)
            platform = "paypal" if rng.random() < paypal_p else "card"
            add_gift(donor_id, month, max(5, rng.lognormal(np.log(60), 1.0)), platform, "one_off")
        repeaters = rng.random(len(one_off_donors)) < REPEAT_RATE * season(month)
        for donor_id in np.array(one_off_donors)[repeaters]:
            platform = "paypal" if rng.random() < paypal_p else "card"
            add_gift(donor_id, month, max(5, rng.lognormal(np.log(60), 1.0)), platform, "one_off")

        # Recurring: existing subscriptions churn or charge, then new ones start
        churn_card = CHURN * 3 if m == "2025-03" else CHURN
        still_active = []
        for sub in subscriptions:
            p = churn_card if sub["platform"] == "card" else CHURN
            if rng.random() >= p:
                still_active.append(sub)
                add_gift(sub["donor_id"], month, sub["amount"], sub["platform"], "recurring")
        subscriptions = still_active
        for _ in range(rng.poisson(BASE_NEW_RECURRING * season(month) * campaign)):
            sub = {"donor_id": new_donor("individual"),
                   "amount": rng.choice(RECURRING_AMOUNTS, p=RECURRING_P),
                   "platform": "card" if rng.random() < 0.75 else "paypal"}
            subscriptions.append(sub)
            add_gift(sub["donor_id"], month, sub["amount"], sub["platform"], "recurring")

    gifts_df = pd.DataFrame(gifts).sort_values("date").reset_index(drop=True)
    gifts_df.insert(0, "gift_id", [f"G{i + 1:06d}" for i in range(len(gifts_df))])
    pd.DataFrame(donors).to_csv(OUT / "donors.csv", index=False)
    gifts_df.to_csv(OUT / "gifts.csv", index=False)
    (OUT / "events.json").write_text(json.dumps(EVENTS, indent=2))

    monthly = gifts_df.groupby(gifts_df["date"].dt.to_period("M"))["amount_usd"].sum()
    print(f"{len(donors)} donors, {len(gifts_df)} gifts, ${gifts_df['amount_usd'].sum():,.0f} total")
    print(monthly.describe().apply(lambda x: f"{x:,.0f}"))


if __name__ == "__main__":
    main()
