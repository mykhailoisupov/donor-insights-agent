# Donor Insights Agent

An AI analyst for nonprofit fundraising data. Ask a question in plain language ("why did revenue drop in March 2025?") and the agent calls analysis tools, then answers.

A verifier checks every answer before it is returned:
- every number must come from a tool result
- comparisons must go from the earlier month to the later one

If a check fails, the agent gets the problems back and retries (up to 2 times).

## Data

All data is synthetic (`data/generate.py`): about 7k donors and 25k gifts from 2023-01 to 2026-08. The generator plants five events, which serve as ground truth for the evals:

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
- `evals/`: 30 questions (lookups, explanations, unanswerable traps) and the eval runner
- `tests/`: unit tests and checks that each planted event is detectable

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
```

## Results

30 questions, 3 runs each, gpt-4o-mini ([details](evals/results.md)):

| | Verifier off | Verifier on |
|---|---|---|
| Lookups correct | 100% | 97% |
| Explanations correct | 57% | 60% |
| Unanswerable questions refused | 90% | 87% |
| Answers with unsupported numbers | 6% | 2% |

- The verifier cuts unsupported numbers in explanations from 17% to 3%, but does not make the reasoning better.
- Explanations are the weak spot: the agent often misses that the March 2025 churn was card-only and that the May 2026 drop was one lapsed donor.
- Asked why a donor stopped giving, the agent speculates in every run instead of saying the data cannot tell.

## Status

- [x] Synthetic data
- [x] Metrics
- [x] Agent
- [x] Verifier
- [x] Evals
- [ ] Demo
