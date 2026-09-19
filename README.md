# Donor Insights Agent

An AI analyst for nonprofit fundraising data. Ask a question in plain language ("why did revenue drop in March 2025?") and the agent calls analysis tools, then answers.

A verifier checks every answer before it is returned:
- every number must come from a tool result
- comparisons must go from the earlier month to the later one

If a check fails, the agent gets the problems back and retries (up to 2 times).

`context.md` holds company background and known events (campaigns, outages, product changes). The agent uses it to name causes, but numbers still have to come from the data. Edit it to add your own context.

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
- `context.md`: company background and known events
- `app.py`: Streamlit demo
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
streamlit run app.py
```

## Results

30 questions, 3 runs each, gpt-4o-mini, verifier on, without context notes ([details](evals/results.md)):

| | Before | After |
|---|---|---|
| Lookups correct | 97% | 97% |
| Explanations correct | 60% | 100% |
| Unanswerable questions refused | 87% | 97% |
| Answers with unsupported numbers | 2% | 4% |

"After" is the same agent with more specific instructions, written from the first eval's failures:
- check lapsed donors and churn per payment platform when explaining a change
- list what the data does not contain, and never guess why a donor acted

What the evals show:
- The verifier catches made-up numbers, swapped months and the model's own arithmetic, but does not improve reasoning. The instructions did that.
- Longer explanations made more `change()` calls, and the model sometimes calls it with guessed values before the data tools return. The verifier flags these, but the model does not always fix them within 2 retries.
- Asked for the overall churn rate in March 2025, the agent sometimes gives only the per-platform rates.

## Status

- [x] Synthetic data
- [x] Metrics
- [x] Agent
- [x] Verifier
- [x] Evals
- [x] Demo
