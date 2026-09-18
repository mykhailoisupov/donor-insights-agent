import pytest

from agent import metrics
from data import generate


@pytest.fixture(scope="module")
def g():
    if not (metrics.DATA_DIR / "gifts.csv").exists():
        generate.main()
    return metrics.load()


def test_mega_gift(g):
    assert metrics.monthly_revenue(g, "2024-11", "2024-11")["2024-11"] > 5_000_000
    assert metrics.monthly_revenue(g, "2024-11", "2024-11", max_gift=1_000_000)["2024-11"] < 1_000_000


def test_card_outage(g):
    before = metrics.recurring(g, "2025-02", platform="card")["churn_rate"]
    during = metrics.recurring(g, "2025-03", platform="card")["churn_rate"]
    assert during > 3 * before


def test_year_end_campaign(g):
    assert metrics.donor_counts(g, "2025-12")["new_donors"] > 2 * metrics.donor_counts(g, "2025-10")["new_donors"]


def paypal_share(g, month):
    rows = metrics.breakdown(g, month, "platform", gift_type="one_off")
    return next(r["share_of_gifts"] for r in rows if r["platform"] == "paypal")


def test_paypal_default(g):
    assert paypal_share(g, "2026-01") < 0.3
    assert paypal_share(g, "2026-02") > 0.4


def test_major_donor_lapse(g):
    assert metrics.lapsed_donors(g, "2026-05")[0]["name"] == "Harbor Light Trust"
