import os
from dataclasses import dataclass, field
from functools import cache
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from agent import metrics, verify

load_dotenv()

INSTRUCTIONS = """
You are a data analyst for a nonprofit's fundraising team. Answer questions about donations
using only the tools. The data covers 2023-01 to 2026-08. Months are strings like "2025-03".

Every number in your answer must appear in a tool result. Never estimate or do arithmetic
yourself; use the change tool for differences and percentages.

To explain why a month changed, compare it with the month before: check revenue with and
without gifts over $1,000,000, the largest gifts, donor counts, recurring churn per platform,
the platform mix, and lapsed donors. Name the cause the numbers support.

If the tools cannot answer the question, say so instead of guessing.
Answer in a few short sentences.
"""

MAX_RETRIES = 2


@dataclass
class Deps:
    gifts: pd.DataFrame
    use_verifier: bool = True
    problems: list = field(default_factory=list)
    retries: int = 0


Ctx = RunContext[Deps]
Platform = Literal["card", "paypal", "wire"]
GiftType = Literal["one_off", "recurring", "institutional"]


def monthly_revenue(ctx: Ctx, start: str, end: str, max_gift: float | None = None):
    return metrics.monthly_revenue(ctx.deps.gifts, start, end, max_gift)


def breakdown(ctx: Ctx, month: str, by: Literal["platform", "country", "campaign", "gift_type", "type"],
              gift_type: GiftType | None = None):
    return metrics.breakdown(ctx.deps.gifts, month, by, gift_type)


def donor_counts(ctx: Ctx, month: str):
    return metrics.donor_counts(ctx.deps.gifts, month)


def recurring(ctx: Ctx, month: str, platform: Platform | None = None):
    return metrics.recurring(ctx.deps.gifts, month, platform)


def lapsed_donors(ctx: Ctx, month: str, n: int = 10):
    return metrics.lapsed_donors(ctx.deps.gifts, month, n=n)


def top_donors(ctx: Ctx, start: str, end: str, n: int = 10):
    return metrics.top_donors(ctx.deps.gifts, start, end, n)


def largest_gifts(ctx: Ctx, start: str, end: str, n: int = 10):
    return metrics.largest_gifts(ctx.deps.gifts, start, end, n)


def change(before: float, after: float):
    return {"difference": round(after - before, 2),
            "percent_change": round((after - before) / before * 100, 1) if before else None}


TOOLS = [
    Tool(monthly_revenue, description="Total revenue per month from start to end. "
         "Set max_gift to exclude gifts above that amount."),
    Tool(breakdown, description="Revenue, gift count and share of gifts in one month, split by a column. "
         "Optionally only one gift type."),
    Tool(donor_counts, description="Active, new and returning donors in one month."),
    Tool(recurring, description="Recurring subscribers, monthly recurring revenue (mrr), new subscribers, "
         "churned subscribers and churn rate versus the previous month. Optionally one platform."),
    Tool(lapsed_donors, description="Donors who gave in each of the previous 3 months but not in this month, "
         "largest first."),
    Tool(top_donors, description="Donors with the highest total giving between start and end."),
    Tool(largest_gifts, description="Largest single gifts between start and end."),
    Tool(change, description="Difference and percent change from before to after."),
]

analyst = Agent(
    f"openai:{os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}",
    deps_type=Deps,
    retries=MAX_RETRIES + 1,
    instructions=INSTRUCTIONS,
    tools=TOOLS,
)


def tool_calls(messages):
    calls, results = {}, {}
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                calls[part.tool_call_id] = (part.tool_name, part.args_as_dict())
            elif isinstance(part, ToolReturnPart):
                results[part.tool_call_id] = part.content
    return [(name, args, results.get(call_id)) for call_id, (name, args) in calls.items()]


@analyst.output_validator
def check_answer(ctx: Ctx, answer: str) -> str:
    if not ctx.deps.use_verifier:
        return answer
    ctx.deps.problems = verify.check(answer, ctx.prompt, tool_calls(ctx.messages))
    if ctx.deps.problems and ctx.deps.retries < MAX_RETRIES:
        ctx.deps.retries += 1
        raise ModelRetry("Fix these problems and answer again:\n" + "\n".join(ctx.deps.problems))
    return answer


@cache
def data():
    return metrics.load()


def ask(question, use_verifier=True):
    deps = Deps(data(), use_verifier)
    result = analyst.run_sync(question, deps=deps)
    calls = [f"{name}({args})" for name, args, _ in tool_calls(result.all_messages())]
    return {"answer": result.output, "calls": calls, "problems": deps.problems, "retries": deps.retries}
