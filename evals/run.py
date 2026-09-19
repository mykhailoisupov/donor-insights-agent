import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from agent.analyst import ask, data
from agent.verify import matches, numbers
from evals.questions import EXPLAIN, LOOKUP, TRAP

OUT = Path(__file__).parent
REFUSALS = ["does not", "doesn't", "do not", "don't", "cannot", "can't", "could not", "couldn't",
            "unable", "no data", "no information", "not available", "only covers", "only includes",
            "only provide", "only have", "outside"]


def cases():
    g = data()
    for question, expected in LOOKUP:
        value = expected(g)
        yield "lookup", question, value if isinstance(value, str) else float(value)
    for question, keywords in EXPLAIN:
        yield "explain", question, keywords
    for question in TRAP:
        yield "trap", question, None


def score(group, answer, expected):
    text = answer.lower()
    if group == "trap":
        return any(r in text for r in REFUSALS)
    if group == "explain" or isinstance(expected, str):
        return any(k.lower() in text for k in ([expected] if isinstance(expected, str) else expected))
    return any(matches(v, d, u, expected) for v, d, u in numbers(answer))


async def run(case, limit):
    group, question, expected, use_verifier = case
    row = {"group": group, "question": question, "expected": expected, "verifier": use_verifier}
    for attempt in range(3):
        try:
            async with limit:
                result = await ask(question, use_verifier, use_context=False)
            return row | {"answer": result["answer"], "passed": score(group, result["answer"], expected),
                          "unsupported": bool(result["problems"]), "problems": result["problems"],
                          "retries": result["retries"]}
        except Exception as error:
            last_error = error
            await asyncio.sleep(5 * (attempt + 1))
    return row | {"error": str(last_error)}


def summary(rows):
    lines = ["| Questions | Verifier | Correct | Unsupported numbers | Avg retries |",
             "|---|---|---|---|---|"]
    for group in ["lookup", "explain", "trap", "all"]:
        for use_verifier in [False, True]:
            sel = [r for r in rows if "error" not in r
                   and r["verifier"] == use_verifier and group in ("all", r["group"])]
            n = len(sel)
            lines.append(f"| {group} | {'on' if use_verifier else 'off'} "
                         f"| {sum(r['passed'] for r in sel) / n:.0%} "
                         f"| {sum(r['unsupported'] for r in sel) / n:.0%} "
                         f"| {sum(r['retries'] for r in sel) / n:.2f} |")
    return "\n".join(lines)


async def main(repeats=1):
    todo = [(*case, v) for case in cases() for v in [False, True] for _ in range(repeats)]
    limit = asyncio.Semaphore(4)
    rows = await asyncio.gather(*(run(case, limit) for case in todo))
    (OUT / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    errors = sum("error" in r for r in rows)
    table = summary(rows)
    header = f"{len(todo)} runs ({repeats} per question and mode), {errors} failed to connect and are excluded"
    (OUT / "results.md").write_text(f"{header}\n\n{table}\n", encoding="utf-8")
    print(f"{header}\n{table}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
