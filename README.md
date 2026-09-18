# Donor Insights Agent

An AI analyst for nonprofit fundraising teams. Staff ask plain-language questions
("why did revenue drop in March 2025?", "which recurring donors did we lose this quarter?")
and the agent answers with numbers, charts and an explanation. Every number it states must
come from a tool call, and a verifier rejects any answer that contains a number it cannot
trace.

## Why synthetic data

Real donor data is confidential. `data/generate.py` builds a realistic fake dataset
(about 7k donors and 25k gifts, Jan 2023 to Aug 2026): one-off gifts, recurring
subscriptions with churn, institutional wires, seasonality, and heavy-tailed gift sizes.

The generator also plants known events. Since we know the true cause of every anomaly,
we can grade the agent's explanations instead of just eyeballing them.

| Month   | Planted event                                               |
|---------|-------------------------------------------------------------|
| 2024-11 | $5M one-off wire from Northbridge Family Foundation          |
| 2025-03 | Card processor outage, recurring card churn 6x normal        |
| 2025-12 | Year-end campaign doubles new donor acquisition              |
| 2026-02 | PayPal becomes default, share of one-off gifts 20% -> 50%    |
| 2026-05 | Harbor Light Trust ($40k/month) stops giving                 |

## Architecture

```
question -> agent (LLM) -> tools -> pandas over gifts.csv / donors.csv
                  |
                  v
             draft answer -> verifier (every number traced to a tool result?) -> answer
                                   | no
                                   v
                           retry with feedback
```

- `data/`: synthetic data generator and planted-event ground truth
- `agent/metrics.py`: deterministic metric functions (revenue, donors, retention, churn,
  platform mix, top donors). No LLM here; unit tested.
- `agent/tools.py`: metrics exposed as typed agent tools
- `agent/verify.py`: numeric grounding check
- `agent/agent.py`: the agent loop (PydanticAI)
- `evals/`: question set with expected answers, scoring script

## Plan (application deadline 2026-10-05)

1. **Data** (done): generator with planted events, signals checked.
2. **Metrics** (Sep 19-21): `metrics.py` + pytest tests against known values.
3. **Agent v0** (Sep 22-24): tools + agent loop, CLI `python -m agent "question"`.
4. **Verifier** (Sep 25-26): extract numbers from the answer, match against tool outputs,
   retry on failure.
5. **Evals** (Sep 27-30): about 30 questions in three groups: lookups (exact numbers),
   explanations (did it find the planted cause?), traps (questions the data cannot answer,
   so the agent should say so). Report accuracy with and without the verifier.
6. **Demo** (Oct 1-4): Streamlit chat UI, traces (Logfire), short video, README results.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python data/generate.py
```
