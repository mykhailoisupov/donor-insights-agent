import pandas as pd
import pytest

from agent import metrics

ROWS = [
    ("D1", "Alice", "individual", "2025-01-05", 10, "card", "recurring"),
    ("D1", "Alice", "individual", "2025-02-05", 10, "card", "recurring"),
    ("D1", "Alice", "individual", "2025-03-05", 10, "card", "recurring"),
    ("D1", "Alice", "individual", "2025-04-05", 10, "card", "recurring"),
    ("D2", "Bob", "individual", "2025-01-10", 20, "card", "recurring"),
    ("D2", "Bob", "individual", "2025-02-10", 20, "card", "recurring"),
    ("D3", "Carol", "individual", "2025-03-15", 100, "paypal", "one_off"),
    ("D4", "Trust", "organization", "2025-01-20", 1000, "wire", "institutional"),
    ("D4", "Trust", "organization", "2025-02-20", 1000, "wire", "institutional"),
    ("D4", "Trust", "organization", "2025-03-20", 1000, "wire", "institutional"),
    ("D5", "Big Fund", "organization", "2025-02-25", 5_000_000, "wire", "institutional"),
]


@pytest.fixture
def g():
    df = pd.DataFrame(ROWS, columns=["donor_id", "name", "type", "date", "amount_usd", "platform", "gift_type"])
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["gift_id"] = [f"G{i}" for i in range(len(df))]
    return df


def test_monthly_revenue(g):
    assert metrics.monthly_revenue(g, "2025-01", "2025-03") == {
        "2025-01": 1030, "2025-02": 5_001_030, "2025-03": 1110}


def test_monthly_revenue_without_large_gifts(g):
    assert metrics.monthly_revenue(g, "2025-02", "2025-02", max_gift=1_000_000) == {"2025-02": 1030}


def test_breakdown(g):
    rows = {r["platform"]: r for r in metrics.breakdown(g, "2025-03", "platform")}
    assert rows["paypal"]["revenue"] == 100
    assert rows["wire"]["gifts"] == 1
    assert rows["card"]["share_of_gifts"] == 0.333


def test_breakdown_filters_gift_type(g):
    rows = metrics.breakdown(g, "2025-03", "platform", gift_type="one_off")
    assert rows == [{"platform": "paypal", "revenue": 100, "gifts": 1, "share_of_gifts": 1.0}]


def test_donor_counts(g):
    assert metrics.donor_counts(g, "2025-03") == {"active_donors": 3, "new_donors": 1, "returning_donors": 2}


def test_recurring(g):
    assert metrics.recurring(g, "2025-03") == {
        "active_subscribers": 1, "mrr": 10, "new_subscribers": 0,
        "churned_subscribers": 1, "churn_rate": 0.5}


def test_lapsed_donors(g):
    lapsed = metrics.lapsed_donors(g, "2025-04")
    assert [d["name"] for d in lapsed] == ["Trust"]
    assert lapsed[0]["total_last_3_months"] == 3000


def test_top_donors(g):
    assert metrics.top_donors(g, "2025-01", "2025-04", n=1)[0]["name"] == "Big Fund"


def test_largest_gifts_sorted_by_amount(g):
    amounts = [x["amount_usd"] for x in metrics.largest_gifts(g, "2025-01", "2025-04", n=3)]
    assert amounts == [5_000_000, 1000, 1000]
