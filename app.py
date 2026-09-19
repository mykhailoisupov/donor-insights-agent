import asyncio
import os
import threading

import pandas as pd
import streamlit as st

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from agent import metrics
from agent.analyst import ask, data
from data import generate

EXAMPLES = [
    "Why did recurring revenue fall in March 2025?",
    "Why was revenue so high in November 2024?",
    "Why is monthly revenue lower from May 2026 on?",
    "What changed in how donors paid for one-off gifts in February 2026?",
    "Why did Harbor Light Trust stop giving?",
]
MAX_QUESTIONS = 10


@st.cache_resource
def event_loop():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop


def run(question, use_verifier, use_context):
    coroutine = ask(question, use_verifier, use_context)
    return asyncio.run_coroutine_threadsafe(coroutine, event_loop()).result()


def show_answer(item):
    st.markdown(item["answer"].replace("$", "\\$"))
    if not item["verifier"]:
        st.info("Verifier off")
    elif item["problems"]:
        st.warning("Verifier could not resolve:\n\n" + "\n".join(f"- {p}" for p in item["problems"]))
    else:
        st.success(f"Verified: every number comes from a tool result (retries: {item['retries']})")
    with st.expander(f"{len(item['calls'])} tool calls"):
        st.code("\n".join(item["calls"]), language=None)


st.set_page_config(page_title="Donor Insights Agent")
if not (metrics.DATA_DIR / "gifts.csv").exists():
    generate.main()

with st.sidebar:
    use_verifier = st.toggle("Verifier", value=True)
    use_context = st.toggle("Context notes", value=True, help="Company background and known events from context.md")
    st.subheader("Monthly revenue")
    revenue = metrics.monthly_revenue(data(), "2023-01", "2026-08", max_gift=1_000_000)
    st.line_chart(pd.Series(revenue, name="USD"), height=200)
    st.caption("Gifts over $1M excluded.")
    st.subheader("Try")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state.question = example

st.title("Donor Insights Agent")
st.caption("An AI analyst for a synthetic nonprofit's donations, 2023-01 to 2026-08. "
           "Every answer is checked against the tool results before it is shown.")

st.session_state.setdefault("history", [])
for item in st.session_state.history:
    st.chat_message("user").write(item["question"])
    with st.chat_message("assistant"):
        show_answer(item)

if len(st.session_state.history) >= MAX_QUESTIONS:
    st.info(f"This demo allows {MAX_QUESTIONS} questions per session. Clone the repo to run it with your own key.")
    st.stop()

question = st.chat_input("Ask about the donations") or st.session_state.pop("question", None)
if question:
    st.chat_message("user").write(question)
    with st.chat_message("assistant"):
        with st.spinner("Analysing..."):
            item = {"question": question, "verifier": use_verifier, **run(question, use_verifier, use_context)}
        show_answer(item)
    st.session_state.history.append(item)
