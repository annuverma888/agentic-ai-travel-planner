"""LangChain agent setup: prompt, model, and the plan_trip entry point."""

import json
import os
import re
from datetime import date
from functools import lru_cache

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

from travel_tools import ALL_TOOLS, AVAILABLE_CITIES

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def build_system_prompt() -> str:
    """Build the system prompt, including today's date and the cities in the dataset."""
    return f"""You are an expert travel planner. Build a complete trip plan using ONLY the provided tools.
Today's date is {date.today()}. The dataset covers only these cities: {", ".join(AVAILABLE_CITIES)}.

Input validation (do this BEFORE calling any tool):
- If the end date is before the start date, or the start date is in the past, do NOT call any tool and do NOT swap or fix the dates yourself. Reply only with a short message explaining the problem and asking for corrected dates.

Process:
1. flight_search for the outward flight AND the return flight (swap source and destination). Pick the cheapest by default, the fastest if the user asks.
2. hotel_search in the destination within the user's budget. Pick the best option (high stars, fair price).
3. places_search for attractions in the destination.
4. weather_lookup for the travel dates.
5. budget_estimator for the cost breakdown. Nights = number of days minus 1. Use the number of travelers given by the user.
6. Make a day-wise itinerary. Group places sensibly, do not overload a day, adapt to weather.

Rules:
- Never invent flights, hotels or places. Use only what the tools return.
- If a tool says nothing was found, tell the user clearly what is missing and do not make up a plan. Suggest only alternatives from the dataset cities listed above.
- If the weather tool returns an error, mention that the forecast is unavailable.
- The flight data has fixed dates from the past. Ignore those dates and use the user's travel dates.
- If the total exceeds the user's budget, say so and suggest cheaper options. If even the cheapest flights exceed the budget, say so and stop.
- Do NOT write weekday names (Mon, Tue, ...). Use dates only, like 12 Nov 2026.
- Use the 'arrives_at' time of the outbound flight as the arrival time on Day 1 and plan only activities AFTER it. If arrival is after 17:00, Day 1 is only check-in and dinner.
- Use the 'departs_at' time of the return flight on the last day. Plan nothing within 3 hours before departure except check-out and airport transfer.
- Hotels have 'stars', not ratings. Places have 'rating'.
- Do not invent restaurant or attraction names. Generic meal suggestions are fine.

Final answer format:
## Trip Summary
## Flight Selected
## Hotel Recommendation
## Day-wise Itinerary (with weather for each day)
## Budget Breakdown (with total)
## Why I chose these

After the readable plan, add a ```json code block with keys:
trip_summary, flight, hotel, itinerary, weather, budget, reasoning.
"""


def content_to_text(content) -> str:
    """Convert a model reply (plain string or list of blocks) into plain text."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def extract_json(answer: str):
    """Return the trip JSON from the agent's answer as a dict, or None."""
    fenced = re.search(r"```json\s*(\{.*\})\s*```", answer, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        marker = answer.find('"trip_summary"')
        brace = answer.rfind("{", 0, marker) if marker != -1 else -1
        if brace == -1:
            return None
        candidate = answer[brace:]
    try:
        obj, _ = json.JSONDecoder().raw_decode(candidate)
        return obj
    except json.JSONDecodeError:
        return None


@lru_cache(maxsize=1)
def get_agent():
    """Create the agent once and reuse it."""
    llm = ChatGroq(model=MODEL_NAME, temperature=0, timeout=90, max_retries=1,
                   max_tokens=4000, reasoning_effort="low")
    return create_agent(model=llm, tools=ALL_TOOLS, system_prompt=build_system_prompt())


def plan_trip(query: str) -> dict:
    """Run the agent on a travel request.

    Returns a dict with keys: text (readable plan), json (dict or None),
    tool_calls (list of names and arguments) and error (str or None).
    """
    if not os.getenv("GROQ_API_KEY"):
        return {"text": "", "json": None, "tool_calls": [],
                "error": "GROQ_API_KEY is missing. Add it to your .env file."}
    try:
        result = get_agent().invoke(
            {"messages": [{"role": "user", "content": query}]},
            config={"recursion_limit": 25},
        )
    except Exception as error:
        return {"text": "", "json": None, "tool_calls": [], "error": str(error)[:500]}

    tool_calls = [
        {"tool": call["name"], "args": call["args"]}
        for message in result["messages"]
        for call in (getattr(message, "tool_calls", None) or [])
    ]
    text = content_to_text(result["messages"][-1].content)
    readable = text.split("```json")[0].strip()
    return {"text": readable, "json": extract_json(text), "tool_calls": tool_calls, "error": None}


if __name__ == "__main__":
    demo = plan_trip("Plan a trip from Mumbai to Goa, from 2026-11-12 to 2026-11-14. Budget 25000 INR.")
    print(demo["error"] or demo["text"])