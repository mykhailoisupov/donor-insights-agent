# Donor Insights Agent

An AI analyst for nonprofit fundraising data. Ask a question in plain language ("why did revenue drop in March 2025?") and the agent calls analysis tools, then answers. A verifier rejects any answer containing a number that did not come from a tool.

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
```

## Status

- [x] Synthetic data
- [x] Metrics
- [x] Agent
- [ ] Verifier
- [ ] Evals
- [ ] Demo
