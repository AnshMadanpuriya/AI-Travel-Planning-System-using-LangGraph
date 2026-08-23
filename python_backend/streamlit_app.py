from __future__ import annotations

import asyncio
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph import app

st.set_page_config(page_title="AI Travel Agent System", layout="wide")
st.title("AI Travel Agent System")
st.caption("LangGraph + MCP + supervisor routing + human approval")

with st.sidebar:
    user_id = st.text_input("User ID", value="demo_user")
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
    if st.button("New thread"):
        st.session_state.thread_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        st.session_state.pop("latest_result", None)
        st.session_state.pop("waiting_for_approval", None)
        st.rerun()
    st.caption(f"Thread: {st.session_state.thread_id}")

query = st.text_area(
    "Travel request",
    placeholder="Plan a 7-day Japan trip from Indore under ₹2 lakh. I prefer budget hotels and no overnight flights.",
    height=120,
)
config = {"configurable": {"thread_id": st.session_state.thread_id}}

if st.button("Create draft plan", type="primary"):
    if not query.strip():
        st.warning("Enter a travel request first.")
    else:
        with st.spinner("The agents are planning…"):
            result = asyncio.run(
                app.ainvoke(
                    {
                        "messages": [HumanMessage(content=query)],
                        "user_id": user_id,
                        "user_query": query,
                        "selected_agents": [],
                        "trip_constraints": {},
                        "flight_results": "",
                        "hotel_results": "",
                        "weather_results": "",
                        "budget_results": "",
                        "itinerary": "",
                        "final_response": "",
                        "llm_calls": 0,
                    },
                    config=config,
                )
            )
        st.session_state.latest_result = result
        st.session_state.waiting_for_approval = "__interrupt__" in result

result = st.session_state.get("latest_result")
if result:
    if result.get("blocked_reason"):
        st.error(result["blocked_reason"])
    else:
        st.subheader("Supervisor")
        st.write(result.get("supervisor_reasoning", ""))
        st.caption(f"Selected agents: {', '.join(result.get('selected_agents', []))}")

        left, right = st.columns(2)
        with left:
            st.subheader("Flights")
            st.markdown(result.get("flight_results", "Not requested"))
            st.subheader("Weather")
            st.markdown(result.get("weather_results", "Not requested"))
        with right:
            st.subheader("Stays")
            st.markdown(result.get("hotel_results", "Not requested"))
            st.subheader("Budget")
            st.markdown(result.get("budget_results", "Not requested"))

        st.subheader("Draft itinerary")
        if "__interrupt__" in result:
            draft = result["__interrupt__"][0].value.get("draft_itinerary", "")
        else:
            draft = result.get("itinerary", "")
        st.markdown(draft)

if st.session_state.get("waiting_for_approval"):
    st.divider()
    st.subheader("Human review")
    approved = st.radio("Approve this draft?", ["Yes", "No, revise it"], horizontal=True)
    feedback = st.text_area("Revision feedback", disabled=approved == "Yes")
    if st.button("Submit review"):
        with st.spinner("Preparing the final response…"):
            final_result = asyncio.run(
                app.ainvoke(
                    Command(
                        resume={
                            "approved": approved == "Yes",
                            "feedback": feedback,
                        }
                    ),
                    config=config,
                )
            )
        st.session_state.latest_result = final_result
        st.session_state.waiting_for_approval = False
        st.rerun()

final_result = st.session_state.get("latest_result")
if final_result and final_result.get("final_response"):
    st.divider()
    st.subheader("Final travel plan")
    st.markdown(final_result["final_response"])
    st.info("Planning guidance only. Verify prices, entry rules, safety information, and availability before payment.")
