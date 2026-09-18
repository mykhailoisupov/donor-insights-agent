import os
from functools import cache
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.messages import ToolCallPart

from agent import metrics

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

Deps = RunContext[pd.DataFrame]
Platform = Literal["card", "paypal", "wire"]
GiftType = Literal["one_off", "recurring", "institutional"]


def monthly_revenue(ctx: Deps, start: str, end: str, max_gift: float | None = None):
    return metrics.monthly_revenue(ctx.deps, start, end, max_gift)


def breakdown(ctx: Deps, month: str, by: Literal["platform", "country", "campaign", "gift_type", "type"],
              gift_type: GiftType | None = None):
    return metrics.breakdown(ctx.deps, month, by, gift_type)


def donor_counts(ctx: Deps, month: str):
    return metrics.donor_counts(ctx.deps, month)


def recurring(ctx: Deps, month: str, platform: Platform | None = None):
    return metrics.recurring(ctx.deps, month, platform)


def lapsed_donors(ctx: Deps, month: str, n: int = 10):
    return metrics.lapsed_donors(ctx.deps, month, n=n)


def top_donors(ctx: Deps, start: str, end: str, n: int = 10):
    return metrics.top_donors(ctx.deps, start, end, n)


def largest_gifts(ctx: Deps, start: str, end: str, n: int = 10):
    return metrics.largest_gifts(ctx.deps, start, end, n)


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
    deps_type=pd.DataFrame,
    instructions=INSTRUCTIONS,
    tools=TOOLS,
)


@cache
def data():
    return metrics.load()


def ask(question):
    result = analyst.run_sync(question, deps=data())
    calls = [f"{part.tool_name}({part.args_as_dict()})"
             for message in result.all_messages() for part in message.parts
             if isinstance(part, ToolCallPart)]
    return result.output, calls
