"""Streamlit interface for VoyageGraph MCP."""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from travel_planner import plan_trip_sync  # noqa: E402
from travel_planner.config import Settings  # noqa: E402

st.set_page_config(
    page_title="VoyageGraph MCP",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

:root {
  --ink: #10213b;
  --muted: #65758b;
  --paper: #f7f5ef;
  --card: rgba(255,255,255,.92);
  --line: #dce4e8;
  --teal: #0e766e;
  --teal-dark: #075c57;
  --coral: #ff785a;
}

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  background:
    radial-gradient(circle at 8% 2%, rgba(255,120,90,.14), transparent 28rem),
    radial-gradient(circle at 95% 12%, rgba(14,118,110,.14), transparent 30rem),
    var(--paper);
  color: var(--ink);
}
.block-container { max-width: 1180px; padding-top: 1.4rem; padding-bottom: 4rem; }

.hero {
  position: relative;
  overflow: hidden;
  padding: 3.2rem 3.5rem;
  border-radius: 28px;
  background: linear-gradient(125deg, #0a2f3d 0%, #0e5f5b 58%, #159084 100%);
  color: white;
  box-shadow: 0 28px 70px rgba(14,57,68,.20);
  margin-bottom: 1.5rem;
}
.hero:after {
  content: "";
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  right: -100px;
  top: -170px;
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.14);
}
.eyebrow {
  display: inline-flex;
  gap: .45rem;
  align-items: center;
  padding: .42rem .75rem;
  border: 1px solid rgba(255,255,255,.28);
  background: rgba(255,255,255,.10);
  border-radius: 999px;
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.hero h1 {
  position: relative;
  z-index: 2;
  font-family: 'Manrope', sans-serif;
  font-size: clamp(2.35rem, 5vw, 4.2rem);
  line-height: 1.02;
  letter-spacing: -.055em;
  margin: 1rem 0 .7rem;
  max-width: 760px;
}
.hero p { position: relative; z-index: 2; color: #d8f5ef; max-width: 700px; font-size: 1.05rem; }
.accent { color: #ffb59f; }

.feature-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: .8rem; margin: 1rem 0 1.8rem; }
.feature-card {
  background: var(--card);
  border: 1px solid rgba(191,205,210,.8);
  border-radius: 16px;
  padding: 1rem 1.05rem;
  box-shadow: 0 8px 24px rgba(39,61,78,.06);
}
.feature-card b { display: block; color: var(--ink); margin-bottom: .18rem; }
.feature-card span { color: var(--muted); font-size: .83rem; }

.section-title { font-family: 'Manrope', sans-serif; font-size: 1.35rem; font-weight: 800; color: var(--ink); margin: .5rem 0 .25rem; }
.section-copy { color: var(--muted); margin-bottom: 1.1rem; }

[data-testid="stForm"] {
  background: rgba(255,255,255,.78);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1.25rem 1.35rem 1.4rem;
  box-shadow: 0 18px 45px rgba(39,61,78,.07);
}
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="select"] > div, [data-baseweb="input"] > div {
  background: white !important;
  border-color: #cfdadd !important;
  border-radius: 11px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--teal) !important; }
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  min-height: 46px;
  border-radius: 12px !important;
  border: 1px solid var(--teal) !important;
  background: var(--teal) !important;
  color: white !important;
  font-weight: 700 !important;
  transition: all .2s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
  background: var(--teal-dark) !important;
  transform: translateY(-1px);
}

[data-testid="stMetric"] {
  background: white;
  border: 1px solid var(--line);
  padding: .9rem 1rem;
  border-radius: 14px;
}
.answer-card {
  background: white;
  border: 1px solid var(--line);
  border-left: 5px solid var(--teal);
  border-radius: 18px;
  padding: 1.25rem 1.5rem .9rem;
  box-shadow: 0 18px 45px rgba(39,61,78,.07);
}
.st-key-answer_card {
  background: white;
  border: 1px solid var(--line);
  border-left: 5px solid var(--teal);
  border-radius: 18px;
  padding: .6rem 1.2rem;
  box-shadow: 0 18px 45px rgba(39,61,78,.07);
}
.small-note { color: var(--muted); font-size: .82rem; }

section[data-testid="stSidebar"] { background: #0b2631; border-right: 0; }
section[data-testid="stSidebar"] * { color: #e8f5f3; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.13); }
.status-row {
  display:flex; justify-content:space-between; gap:.6rem;
  padding:.52rem .65rem; margin:.35rem 0;
  border-radius:10px; background:rgba(255,255,255,.06);
  font-size:.82rem;
}
.status-on { color:#83e6bf !important; font-weight:700; }
.status-off { color:#ffb59f !important; font-weight:700; }

@media (max-width: 850px) {
  .feature-grid { grid-template-columns: repeat(2,1fr); }
  .hero { padding: 2.2rem 1.6rem; border-radius: 20px; }
}
</style>
""",
    unsafe_allow_html=True,
)


def build_query(
    origin: str,
    destination: str,
    departure: date,
    return_date: date,
    travelers: int,
    budget: int,
    interests: list[str],
    style: str,
    notes: str,
) -> str:
    days = (return_date - departure).days + 1
    interest_text = ", ".join(interests) if interests else "sightseeing and local food"
    return (
        f"Plan a complete {days}-day {style.lower()} trip from {origin} to {destination} "
        f"for {travelers} adult traveler(s). Depart on {departure.isoformat()} and return on "
        f"{return_date.isoformat()}. Total trip budget is approximately INR {budget:,}. "
        f"Interests: {interest_text}. Search outbound and return flights, suitable hotels, weather, "
        f"a realistic day-by-day itinerary, and a transparent budget. Additional preferences: "
        f"{notes.strip() or 'none'}."
    )


def destination_slug(destination: str) -> str:
    """Create a safe, readable download filename component."""

    slug = re.sub(r"[^a-z0-9]+", "-", destination.casefold()).strip("-")
    return slug or "trip"


def render_tool_trace(tool_trace: list[dict]) -> None:
    if not tool_trace:
        st.info("The agent answered without calling a tool.")
        return
    for index, item in enumerate(tool_trace, 1):
        icon = "✓" if item["status"] == "success" else "!"
        st.markdown(f"**{icon} {index}. `{item['tool']}` — {item['status']}**")
        st.json(item["arguments"], expanded=False)
        if "result" in item:
            st.json(item["result"], expanded=False)


def build_download(record: dict, follow_ups: list[dict]) -> str:
    sections = [
        "# VoyageGraph Travel Plan",
        f"**Request:** {record['query']}",
        "---",
        record["answer"],
    ]
    if follow_ups:
        sections.extend(["---", "## Follow-up planning"])
        for item in follow_ups:
            sections.extend([f"### {item['question']}", item["answer"]])
    sections.extend(
        [
            "---",
            "Generated with an MCP-powered AI agent. Verify prices and availability before booking.",
        ]
    )
    return "\n\n".join(sections) + "\n"


if "vg_plan" not in st.session_state:
    st.session_state.vg_plan = None
if "vg_history" not in st.session_state:
    st.session_state.vg_history = []
if "vg_follow_ups" not in st.session_state:
    st.session_state.vg_follow_ups = []


settings = Settings.from_env()
with st.sidebar:
    st.markdown("## ✦ VoyageGraph")
    st.caption("MCP-powered travel intelligence")
    st.markdown("---")
    st.markdown("### Service readiness")
    for label, ready in settings.capability_status().items():
        status_class = "status-on" if ready else "status-off"
        status_text = "Ready" if ready else "Add key"
        st.markdown(
            f"<div class='status-row'><span>{label}</span><span class='{status_class}'>{status_text}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.markdown("### Agent route")
    st.caption("Understand → choose MCP tools → verify results → compose plan")
    st.markdown("### Safety")
    st.caption("Prices and availability are snapshots. Always verify before payment.")

st.markdown(
    """
<section class="hero">
  <div class="eyebrow">✦ LangGraph × Model Context Protocol</div>
  <h1>Plan less.<br><span class="accent">Travel smarter.</span></h1>
  <p>One agent discovers the right MCP tools for live flights, stays, weather, local research,
  itinerary design, and budget planning—then turns the evidence into one practical trip plan.</p>
</section>
<div class="feature-grid">
  <div class="feature-card"><b>✈ Live route search</b><span>Google Flights snapshots via SerpApi</span></div>
  <div class="feature-card"><b>⌂ Stay discovery</b><span>Comparable hotel options and rates</span></div>
  <div class="feature-card"><b>☀ Weather aware</b><span>Open-Meteo current and forecast data</span></div>
  <div class="feature-card"><b>⌁ MCP transparent</b><span>Inspect every tool used by the agent</span></div>
</div>
""",
    unsafe_allow_html=True,
)

plan_tab, architecture_tab = st.tabs(["Plan a trip", "How it works"])

with plan_tab:
    st.markdown("<div class='section-title'>Build your trip brief</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-copy'>Exact dates and cities produce the most useful live results.</div>",
        unsafe_allow_html=True,
    )

    with st.form("trip_form", clear_on_submit=False):
        city_left, city_right = st.columns(2)
        with city_left:
            origin = st.text_input("From", value="Indore", placeholder="City or IATA code")
        with city_right:
            destination = st.text_input("To", value="Goa", placeholder="Destination city")

        date_left, date_right, traveler_col = st.columns([1, 1, 0.8])
        default_departure = date.today() + timedelta(days=7)
        with date_left:
            departure = st.date_input("Departure", value=default_departure, min_value=date.today())
        with date_right:
            return_date = st.date_input(
                "Return", value=default_departure + timedelta(days=4), min_value=date.today()
            )
        with traveler_col:
            travelers = st.number_input("Adults", min_value=1, max_value=9, value=2)

        pref_left, pref_right = st.columns(2)
        with pref_left:
            style = st.selectbox(
                "Travel style", ["Comfort", "Budget", "Premium", "Backpacking", "Family"]
            )
        with pref_right:
            budget = st.number_input(
                "Approx. total budget (INR)",
                min_value=5_000,
                max_value=10_000_000,
                value=80_000,
                step=5_000,
            )

        interests = st.multiselect(
            "Interests",
            [
                "Local food",
                "Nature",
                "Beaches",
                "History",
                "Nightlife",
                "Adventure",
                "Shopping",
                "Photography",
                "Relaxation",
            ],
            default=["Local food", "Nature"],
        )
        notes = st.text_area(
            "Preferences or constraints",
            placeholder="Example: direct flights preferred, vegetarian food, avoid rushed mornings",
            height=90,
        )
        submitted = st.form_submit_button(
            "Create verified travel plan  →", use_container_width=True
        )

    if submitted:
        if not origin.strip() or not destination.strip():
            st.error("Please enter both origin and destination.")
        elif origin.strip().casefold() == destination.strip().casefold():
            st.error("Origin and destination must be different.")
        elif return_date <= departure:
            st.error("Return date must be after the departure date.")
        elif (return_date - departure).days + 1 > 30:
            st.error("Please keep the trip within 30 days.")
        else:
            query = build_query(
                origin,
                destination,
                departure,
                return_date,
                int(travelers),
                int(budget),
                interests,
                style,
                notes,
            )
            try:
                with st.status("VoyageGraph is coordinating MCP tools…", expanded=True) as status:
                    st.write("Reading the trip brief")
                    st.write("Discovering available MCP tools")
                    st.write("Checking sources together; planning budget is about 55 seconds.")
                    result = plan_trip_sync(query)
                    status.update(
                        label="Partial results available"
                        if result.partial
                        else "Travel plan ready",
                        state="complete",
                        expanded=False,
                    )

                st.session_state.vg_plan = {
                    "query": query,
                    "answer": result.answer,
                    "tool_trace": result.tool_trace,
                    "destination": destination,
                    "days": (return_date - departure).days + 1,
                    "partial": result.partial,
                    "elapsed_seconds": result.elapsed_seconds,
                }
                st.session_state.vg_history = [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": result.answer},
                ]
                st.session_state.vg_follow_ups = []
            except RuntimeError as error:
                st.error(str(error))
                st.info(
                    "Copy `.env.example` to `.env`, add `GROQ_API_KEY`, then restart Streamlit."
                )
            except Exception as error:
                st.error(f"The planner could not complete this request: {error}")

    record = st.session_state.vg_plan
    if record:
        st.caption(f"Planning completed in {record.get('elapsed_seconds', 0):.1f} seconds.")
        if record.get("partial"):
            st.warning(
                "Some checks could not be completed. Review the missing checks before using this plan."
            )
        tool_count = len(record["tool_trace"])
        success_count = sum(item["status"] == "success" for item in record["tool_trace"])
        m1, m2, m3 = st.columns(3)
        m1.metric("MCP calls", tool_count)
        m2.metric("Completed calls", success_count)
        m3.metric("Trip length", f"{record['days']} days")

        st.markdown("<div class='section-title'>Your travel plan</div>", unsafe_allow_html=True)
        with st.container(border=False, key="answer_card"):
            st.markdown(record["answer"])

        if st.session_state.vg_follow_ups:
            st.markdown("#### Follow-up planning")
            for item in st.session_state.vg_follow_ups:
                with st.chat_message("user"):
                    st.write(item["question"])
                with st.chat_message("assistant"):
                    if item.get("partial"):
                        st.warning("This update has incomplete checks.")
                    st.markdown(item["answer"])
                    with st.expander("Tools used for this follow-up"):
                        render_tool_trace(item["tool_trace"])

        download_text = build_download(record, st.session_state.vg_follow_ups)
        action_left, action_middle, action_right = st.columns([1, 1, 2])
        with action_left:
            st.download_button(
                "Download plan",
                data=download_text,
                file_name=f"voyagegraph-{destination_slug(record['destination'])}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with action_middle:
            if st.button("Start new plan", use_container_width=True):
                st.session_state.vg_plan = None
                st.session_state.vg_history = []
                st.session_state.vg_follow_ups = []
                st.rerun()
        with action_right:
            with st.expander("Inspect initial MCP activity"):
                render_tool_trace(record["tool_trace"])

        st.markdown("#### Refine this plan")
        st.caption("Ask about alternatives, budget changes, timings, or a less rushed itinerary.")
        with st.form("follow_up_form", clear_on_submit=True):
            follow_up = st.text_input(
                "Follow-up question",
                placeholder="Example: Replace day 3 with a quieter nature experience",
                label_visibility="collapsed",
            )
            ask_follow_up = st.form_submit_button("Ask VoyageGraph", use_container_width=True)

        if ask_follow_up:
            if not follow_up.strip():
                st.warning("Enter a follow-up question first.")
            else:
                try:
                    with st.status("Updating your plan with MCP tools…", expanded=True) as status:
                        follow_result = plan_trip_sync(
                            follow_up,
                            history=st.session_state.vg_history,
                        )
                        status.update(
                            label="Partial update available"
                            if follow_result.partial
                            else "Plan updated",
                            state="complete",
                            expanded=False,
                        )
                    st.session_state.vg_follow_ups.append(
                        {
                            "question": follow_up.strip(),
                            "answer": follow_result.answer,
                            "tool_trace": follow_result.tool_trace,
                            "partial": follow_result.partial,
                        }
                    )
                    st.session_state.vg_history.extend(
                        [
                            {"role": "user", "content": follow_up.strip()},
                            {"role": "assistant", "content": follow_result.answer},
                        ]
                    )
                    st.rerun()
                except Exception as error:
                    st.error(f"The follow-up could not be completed: {error}")

with architecture_tab:
    st.markdown(
        "<div class='section-title'>A real MCP client/server loop</div>", unsafe_allow_html=True
    )
    st.markdown(
        """
VoyageGraph does not hard-code tool calls into the interface. The LangGraph agent asks the local
FastMCP server which tools are available, chooses tools based on your request, executes them over
MCP, and uses returned evidence to compose the final answer.

1. **Streamlit UI** creates a precise, structured trip brief.
2. **LangGraph agent** reasons over the request and available tool schemas.
3. **FastMCP client** sends validated arguments to the local MCP server.
4. **Travel tools** query flight, hotel, weather, research, itinerary, and budget services.
5. **Grounded response** separates verified results from suggestions and booking caveats.

This separation keeps the interface, agent reasoning, and external integrations independently
testable and makes new tools easy to add.
"""
    )
    st.code(
        "UI → LangGraph agent → FastMCP client → MCP server → Travel APIs\n"
        "                         ↑              ↓\n"
        "                         └── tool result ┘",
        language="text",
    )
