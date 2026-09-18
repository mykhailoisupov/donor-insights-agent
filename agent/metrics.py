from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load(data_dir=DATA_DIR):
    gifts = pd.read_csv(data_dir / "gifts.csv", parse_dates=["date"])
    donors = pd.read_csv(data_dir / "donors.csv")
    gifts["month"] = gifts["date"].dt.strftime("%Y-%m")
    return gifts.merge(donors, on="donor_id", how="left")


def previous_month(month):
    return str(pd.Period(month, "M") - 1)


def between(g, start, end):
    return g[(g["month"] >= start) & (g["month"] <= end)]


def monthly_revenue(g, start, end, max_gift=None):
    g = between(g, start, end)
    if max_gift is not None:
        g = g[g["amount_usd"] <= max_gift]
    return g.groupby("month")["amount_usd"].sum().round(2).to_dict()


def breakdown(g, month, by, gift_type=None):
    g = g[g["month"] == month]
    if gift_type is not None:
        g = g[g["gift_type"] == gift_type]
    out = g.groupby(by).agg(revenue=("amount_usd", "sum"), gifts=("gift_id", "count"))
    out["revenue"] = out["revenue"].round(2)
    out["share_of_gifts"] = (out["gifts"] / out["gifts"].sum()).round(3)
    return out.reset_index().to_dict("records")


def donor_counts(g, month):
    first_month = g.groupby("donor_id")["month"].min()
    active = g.loc[g["month"] == month, "donor_id"].unique()
    new = int((first_month[active] == month).sum())
    return {"active_donors": len(active), "new_donors": new, "returning_donors": len(active) - new}


def recurring(g, month, platform=None):
    r = g[g["gift_type"] == "recurring"]
    if platform is not None:
        r = r[r["platform"] == platform]
    now = set(r.loc[r["month"] == month, "donor_id"])
    before = set(r.loc[r["month"] == previous_month(month), "donor_id"])
    churned = len(before - now)
    return {
        "active_subscribers": len(now),
        "mrr": round(float(r.loc[r["month"] == month, "amount_usd"].sum()), 2),
        "new_subscribers": len(now - before),
        "churned_subscribers": churned,
        "churn_rate": round(churned / len(before), 3) if before else None,
    }


def lapsed_donors(g, month, lookback=3, n=10):
    months = [month]
    for _ in range(lookback):
        months.insert(0, previous_month(months[0]))
    past = g[g["month"].isin(months[:-1])]
    regular = past.groupby("donor_id")["month"].nunique()
    regular = set(regular[regular == lookback].index)
    gave_now = set(g.loc[g["month"] == month, "donor_id"])
    lost = past[past["donor_id"].isin(regular - gave_now)]
    out = lost.groupby(["donor_id", "name", "type"])["amount_usd"].sum().round(2)
    out = out.rename(f"total_last_{lookback}_months").sort_values(ascending=False).head(n)
    return out.reset_index().to_dict("records")


def top_donors(g, start, end, n=10):
    g = between(g, start, end)
    out = g.groupby(["donor_id", "name", "type"]).agg(total=("amount_usd", "sum"), gifts=("gift_id", "count"))
    out["total"] = out["total"].round(2)
    return out.sort_values("total", ascending=False).head(n).reset_index().to_dict("records")


def largest_gifts(g, start, end, n=10):
    g = between(g, start, end).sort_values("amount_usd", ascending=False).head(n)
    g = g.assign(date=g["date"].dt.strftime("%Y-%m-%d"))
    return g[["gift_id", "date", "name", "amount_usd", "platform", "gift_type"]].to_dict("records")
