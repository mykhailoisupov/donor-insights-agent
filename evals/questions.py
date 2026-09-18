from agent import metrics


def revenue(g, month, max_gift=None):
    return metrics.monthly_revenue(g, month, month, max_gift)[month]


def paypal_share(g, month):
    rows = metrics.breakdown(g, month, "platform", gift_type="one_off")
    return next(r["share_of_gifts"] for r in rows if r["platform"] == "paypal")


LOOKUP = [
    ("What was total revenue in June 2025?", lambda g: revenue(g, "2025-06")),
    ("What was revenue in November 2024 excluding gifts over $1 million?",
     lambda g: revenue(g, "2024-11", 1_000_000)),
    ("How many new donors did we get in December 2025?", lambda g: metrics.donor_counts(g, "2025-12")["new_donors"]),
    ("How many donors gave in October 2024?", lambda g: metrics.donor_counts(g, "2024-10")["active_donors"]),
    ("How many active recurring subscribers did we have in August 2026?",
     lambda g: metrics.recurring(g, "2026-08")["active_subscribers"]),
    ("What was monthly recurring revenue in January 2024?", lambda g: metrics.recurring(g, "2024-01")["mrr"]),
    ("What was the recurring churn rate in March 2025?", lambda g: metrics.recurring(g, "2025-03")["churn_rate"]),
    ("What share of one-off gifts in April 2026 were made with PayPal?", lambda g: paypal_share(g, "2026-04")),
    ("What was the largest single gift in 2023?",
     lambda g: metrics.largest_gifts(g, "2023-01", "2023-12", 1)[0]["amount_usd"]),
    ("Who was our top donor by total giving in 2025?",
     lambda g: metrics.top_donors(g, "2025-01", "2025-12", 1)[0]["name"]),
]

EXPLAIN = [
    ("Why was revenue so high in November 2024?", ["northbridge"]),
    ("Was the November 2024 revenue spike driven by many donors or by one gift?", ["northbridge"]),
    ("Why did recurring revenue fall in March 2025?", ["card"]),
    ("What caused the spike in churned subscribers in March 2025?", ["card"]),
    ("Why did the number of new donors jump in December 2025?", ["campaign", "year-end", "year_end", "year end"]),
    ("What changed in how donors paid for one-off gifts in February 2026?", ["paypal"]),
    ("Did anything unusual happen with payment platforms in 2026?", ["paypal"]),
    ("Why did revenue fall in May 2026 compared to April?", ["harbor light"]),
    ("Which major donor did we lose in May 2026?", ["harbor light"]),
    ("Why is monthly revenue lower from May 2026 on?", ["harbor light"]),
]

TRAP = [
    "What is our donor satisfaction score?",
    "How much did we spend on the year-end campaign?",
    "What was revenue in March 2022?",
    "What will revenue be in December 2026?",
    "How many donors opened our last email?",
    "What is the average age of our donors?",
    "Which donors live in Kyiv?",
    "What was revenue in October 2026?",
    "How much did PayPal charge us in fees in 2025?",
    "Why did Harbor Light Trust stop giving?",
]
