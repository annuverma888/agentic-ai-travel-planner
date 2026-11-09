"""Streamlit interface for the AI travel planning assistant."""

import json
from datetime import date, timedelta

import streamlit as st

from agent import plan_trip
from travel_tools import AVAILABLE_CITIES, PLACE_TYPES

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️")
st.title("✈️ AI Travel Planning Assistant")
st.caption("Plans flights, hotel, day-wise itinerary, weather and budget using a LangChain agent.")

today = date.today()

col1, col2 = st.columns(2)
source = col1.selectbox("From", AVAILABLE_CITIES, index=AVAILABLE_CITIES.index("Mumbai"))
destination = col2.selectbox("To", AVAILABLE_CITIES, index=AVAILABLE_CITIES.index("Goa"))
start_date = col1.date_input("Start date", today + timedelta(days=3), min_value=today)
end_date = col2.date_input("End date", today + timedelta(days=5), min_value=today)

budget = col1.number_input("Budget (₹)", min_value=1000, value=25000, step=1000)
travelers = col2.number_input("Travelers", min_value=1, max_value=10, value=1)
priority = st.radio("Flight priority", ["Cheapest flight", "Fastest flight"], horizontal=True)
interests = st.multiselect("Interests (place types)", PLACE_TYPES, default=["fort", "museum"])

if st.button("Generate trip plan", type="primary"):
    if source == destination:
        st.error("Source and destination must be different.")
    elif end_date < start_date:
        st.error("End date must not be before the start date.")
    else:
        query = (
            f"Plan a trip from {source} to {destination}, from {start_date} to {end_date}. "
            f"Budget {budget} INR. Travelers: {travelers}. Priority: {priority.lower()}. "
            f"Interests: {', '.join(interests) if interests else 'any'}."
        )
        with st.spinner("The agent is planning your trip..."):
            st.session_state["result"] = plan_trip(query)

result = st.session_state.get("result")
if result:
    if result["error"]:
        st.error(f"Something went wrong: {result['error']}")
    else:
        tab_plan, tab_json, tab_steps = st.tabs(["Trip plan", "JSON output", "Agent steps"])
        with tab_plan:
            st.markdown(result["text"])
        with tab_json:
            if result["json"]:
                st.json(result["json"])
                st.download_button(
                    "Download JSON",
                    data=json.dumps(result["json"], indent=2, ensure_ascii=False),
                    file_name="trip_plan.json",
                    mime="application/json",
                )
            else:
                st.info("No structured JSON was produced for this request.")
        with tab_steps:
            if result["tool_calls"]:
                for number, call in enumerate(result["tool_calls"], start=1):
                    st.write(f"{number}. **{call['tool']}**")
                    st.code(json.dumps(call["args"], ensure_ascii=False), language="json")
            else:
                st.info("The agent answered without calling any tools.")