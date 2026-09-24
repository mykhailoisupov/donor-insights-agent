# Donor Insights Agent

![tests](https://github.com/mykhailoisupov/donor-insights-agent/actions/workflows/tests.yml/badge.svg)

An AI analyst for nonprofit fundraising data. Ask a question in plain language and the agent calls analysis tools, then answers. Fundraising teams ask "why did revenue drop?" every month, and a model that invents numbers is worse than no answer, so every answer is checked before it is shown.

The verifier rejects an answer when:
- a number in it does not come from a tool result
- a comparison does not run from the earlier month to the later one, for the same metric

A rejected answer goes back to the agent with the reasons, and it retries (up to 2 times).

`context.md` holds company background and known events (campaigns, outages, product changes). The agent uses it to name causes, but numbers still have to come from the data.

## Example

```
$ python -m agent "Why did recurring revenue fall in March 2025?"
> recurring({'month': '2025-03', 'platform': 'card'})
> recurring({'month': '2025-02', 'platform': 'card'})
> recurring({'month': '2025-03', 'platform': 'paypal'})
> lapsed_donors({'month': '2025-03'})
> largest_gifts({'start': '2025-03', 'end': '2025-03'})

Recurring revenue fell in March 2025 primarily due to a significant increase in churned
subscribers on the card platform. MRR from card subscriptions decreased from $10,910 in
February to $9,605 in March, with 63 subscribers churning against 6 in February. On PayPal,
MRR rose from $3,070 to $3,190, so the problem was specific to cards. Given the card processor
outage from March 3rd to 5th, it likely caused failed renewals.

verifier: passed, retries: 1
```

The first attempt compared card MRR with PayPal MRR and called it February versus March. The verifier caught it, and the retry fixed it.

## Data

All data is synthetic (`data/generate.py`): about 7k donors and 25k gifts from 2023-01 to 2026-08, with recurring subscriptions, churn, foundation wires and seasonality. The generator plants five events, which are the ground truth for the evals:

| Month   | Event                                          |
|---------|------------------------------------------------|
| 2024-11 | $5M one-off gift                               |
| 2025-03 | Card processor outage, card churn 6x normal    |
| 2025-12 | Year-end campaign doubles new donors           |
| 2026-02 | PayPal becomes default, share 20% to 50%       |
| 2026-05 | A $40k/month donor stops giving                |

## Structure

- `data/generate.py`: synthetic data and planted events
- `agent/metrics.py`: analysis functions the agent calls as tools
- `agent/analyst.py`: the agent (PydanticAI + gpt-4o-mini)
- `agent/verify.py`: the verifier
- `context.md`: company background and known events
- `app.py`: Streamlit demo
- `evals/`: 30 questions (lookups, explanations, unanswerable traps) and the runner
- `tests/`: unit tests, and checks that each planted event is detectable

## Run

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python data/generate.py
python -m pytest
python -m agent "What happened to recurring donations in March 2025?"
python -m evals.run 3
streamlit run app.py
```

## Results

30 questions, 3 runs each with the verifier on and off, gpt-4o-mini, without context notes ([details](evals/results.md)).

| | First version | Now |
|---|---|---|
| Lookups correct | 97% | 100% |
| Explanations correct | 60% | 100% |
| Unanswerable questions refused | 87% | 100% |
| Answers with unsupported numbers | 2% | 2% |

Two rounds of changes, each written from the failures of the previous eval run:
1. Specific instructions: check lapsed donors and churn per payment platform, say what the data does not contain, never guess why a donor acted.
2. A stricter verifier: a comparison must use the same metric in two different months.

What the evals show:
- The verifier catches made-up numbers, swapped months, cross-platform comparisons and the model's own arithmetic. It does not improve reasoning; the instructions did that.
- Turning the verifier off changes the scores very little. Its value is that answers are trustworthy, not that they are more often right.

Limits worth knowing:
- Explanations are scored by keyword, so 100% means the agent named the right cause, not that every sentence is right.
- The data is synthetic and the causes were planted, which makes them cleaner than real fundraising data.
- 30 questions and 3 runs is small: a single bad run moves a group by 3 points.
