import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from agent import metrics, verify

load_dotenv()

INSTRUCTIONS = """
You are a data analyst for a nonprofit's fundraising team. Answer questions about donations
using only the tools. The data covers every month from 2023-01 through 2026-08, both included.
Months are strings like "2025-03".

Every number in your answer must appear in a tool result. Never estimate or do arithmetic
yourself; use the change tool for differences and percentages.

To explain why something changed in a month, compare it with the month before and check all of:
- revenue with and without gifts over $1,000,000, and the largest gifts
- lapsed_donors for the month the drop starts: a large regular donor who stopped explains a lasting drop
- recurring for platform "card" and for platform "paypal": churn limited to one platform points to that platform
- breakdown by platform for one_off gifts: a shift in payment mix
- donor_counts and breakdown by campaign: a jump in new donors
For a period like "in 2026" or "from May 2026 on", find the month where the change starts first.
Name the specific cause the numbers support: the donor, platform or campaign.

The data only has gifts: amount, date, platform, gift type, campaign, and donor name, type and
country. It says nothing about costs, fees, emails, satisfaction, age or cities, and nothing about months
before 2023-01 or after 2026-08. For those questions, say the data cannot answer.
If asked why a specific donor gave or stopped giving, state what the data shows (for example their
last gift) and say the data does not show their reasons. Never guess a donor's motives.
Answer exactly what was asked first, in a few short sentences. Use per-platform or other
breakdowns only to explain a change, not in place of the number that was asked for.
"""

CONTEXT_FILE = Path(__file__).resolve().parent.parent / "context.md"
CONTEXT = CONTEXT_FILE.read_text(encoding="utf-8") if CONTEXT_FILE.exists() else ""
CONTEXT_RULES = """
Below are context notes written by the organisation. First find the pattern in the data, then check
the notes: if a known event matches the month and the pattern, name it as the likely cause and say it
comes from the notes. If the notes give a donor's reason, you may cite
it. Numbers must still come from tool results. If the notes and the data disagree, trust the data
and point out the difference.
"""

MAX_RETRIES = 2


@dataclass
class Deps:
    gifts: pd.DataFrame
    use_verifier: bool = True
    use_context: bool = True
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


@analyst.instructions
def context_notes(ctx: Ctx) -> str:
    return CONTEXT_RULES + CONTEXT if ctx.deps.use_context and CONTEXT else ""


@analyst.output_validator
def check_answer(ctx: Ctx, answer: str) -> str:
    given = ctx.prompt + (CONTEXT if ctx.deps.use_context else "")
    ctx.deps.problems = verify.check(answer, given, tool_calls(ctx.messages))
    if ctx.deps.use_verifier and ctx.deps.problems and ctx.deps.retries < MAX_RETRIES:
        ctx.deps.retries += 1
        raise ModelRetry("Fix these problems and answer again:\n" + "\n".join(ctx.deps.problems))
    return answer


@cache
def data():
    return metrics.load()


async def ask(question, use_verifier=True, use_context=True):
    deps = Deps(data(), use_verifier, use_context)
    result = await analyst.run(question, deps=deps)
    calls = [f"{name}({args})" for name, args, _ in tool_calls(result.all_messages())]
    return {"answer": result.output, "calls": calls, "problems": deps.problems, "retries": deps.retries}
