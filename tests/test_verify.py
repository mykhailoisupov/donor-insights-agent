from agent.verify import check

MARCH = {"month": "2025-03", "platform": "all", "active_subscribers": 425, "mrr": 12795,
         "new_subscribers": 22, "churned_subscribers": 67, "churn_rate": 0.143}
FEBRUARY = {"month": "2025-02", "platform": "all", "active_subscribers": 470, "mrr": 13980,
            "new_subscribers": 15, "churned_subscribers": 8, "churn_rate": 0.017}
QUESTION = "What happened to recurring donations in March 2025?"


def calls(before, after, difference, percent):
    return [
        ("recurring", {"month": "2025-03"}, MARCH),
        ("recurring", {"month": "2025-02"}, FEBRUARY),
        ("change", {"before": before, "after": after}, {"difference": difference, "percent_change": percent}),
    ]


def test_correct_answer_passes():
    answer = "In March 2025 MRR fell from $13,980 to $12,795 (-8.5%), and churn rose from 1.7% to 14.3%."
    assert check(answer, QUESTION, calls(13980, 12795, -1185, -8.5)) == []


def test_swapped_months_are_caught():
    answer = "In March 2025 MRR increased to $13,980, up by $1,185 (9.3%)."
    problems = check(answer, QUESTION, calls(12795, 13980, 1185, 9.3))
    assert len(problems) == 1
    assert "earlier month" in problems[0]


def test_made_up_number_is_caught():
    answer = "MRR in March 2025 was about $15,000."
    assert check(answer, QUESTION, calls(13980, 12795, -1185, -8.5)) == ["15000 in the answer does not appear in any tool result."]


def test_change_with_unknown_value_is_caught():
    problems = check("MRR fell by $1,185.", QUESTION, calls(14000, 12795, -1205, -8.6))
    assert any("not from tool results" in p for p in problems)


def test_rounded_formats_match():
    tool_calls = [("monthly_revenue", {"start": "2024-11", "end": "2025-02"},
                   {"2024-11": 5094412.3, "2025-02": 67632.55})]
    answer = "Revenue was $5.09M in November 2024 (2024-11) and $67.6K in February, about 5 million and 67,633."
    assert check(answer, "", tool_calls) == []


def test_list_numbering_is_ignored():
    tool_calls = [("lapsed_donors", {"month": "2026-05"},
                   [{"name": "Harbor Light Trust", "total_last_3_months": 132080.11},
                    {"name": "Sarah Melnyk", "total_last_3_months": 300.0}])]
    answer = "1. **Harbor Light Trust** - $132,080.11\n2. **Sarah Melnyk** - $300.00"
    assert check(answer, "", tool_calls) == []


def test_written_dates_are_ignored():
    tool_calls = [("largest_gifts", {"start": "2023-01", "end": "2023-12"},
                   [{"date": "2023-04-28", "amount_usd": 225715.05}])]
    assert check("The largest gift was $225,715.05 on April 28, 2023.", "", tool_calls) == []
