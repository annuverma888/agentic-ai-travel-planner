# ✈️ Agentic AI Travel Planning Assistant

An AI travel agent built with **LangChain** that takes a trip request (route, dates, budget, interests) and automatically produces a complete plan: flight, hotel, day-wise itinerary, weather for each day, and a budget breakdown. The agent decides on its own which tools to call, reads the results, and writes a justified plan in both readable text and JSON.

**Live demo:** [https://travelagent-planner.streamlit.app/](https://travelagent-planner.streamlit.app/)

---

## Problem Statement

Planning a trip means switching between many websites to compare flights, hotels, attractions and weather, then building an itinerary by hand that is often inefficient or unrealistic. This project replaces that with a single assistant that handles the research, reasons over the results, and returns an optimized plan.

## Business Use Case

Travel agencies, hotel platforms and airline aggregators can use an AI travel agent to:

- Reduce customer support workload
- Give personalized recommendations
- Automate itinerary design
- Improve customer satisfaction
- Save users time and money

## Features

- **Agentic workflow:** a LangChain tool-calling agent chooses which tools to use and in what order.
- **Five tools:** flight search, hotel recommendation, places discovery, live weather, and budget estimation.
- **Round-trip planning:** the agent searches both the outward and return flight.
- **Live weather:** daily forecast from the free Open-Meteo API (no API key needed).
- **Structured output:** trip summary, flight, hotel, day-wise itinerary with weather, budget breakdown, and reasoning ("Why I chose these").
- **JSON export:** the same plan as clean JSON, with a download button.
- **Safe handling of bad input:** invalid dates, unknown cities, routes with no flights and budgets that are too low give a clear message instead of an invented plan.
- **Transparency:** an "Agent steps" tab shows every tool call the agent made.

## Architecture

```
User  ──►  Streamlit UI (app.py)
              │
              ▼
        Agent (agent.py)  ◄──►  LLM (Groq, openai/gpt-oss-120b)
              │
     ┌────────┼─────────┬──────────────┬───────────────┐
     ▼        ▼         ▼              ▼               ▼
  Flight    Hotel     Places        Weather         Budget
  search    search    search      (Open-Meteo)     estimator
     │        │         │
     ▼        ▼         ▼
 flights.json hotels.json places.json
              │
              ▼
   Trip plan (text + JSON)  ──►  Streamlit tabs
```

## Tech Stack

- Python 3.10+
- LangChain (agent and tools)
- Groq API (LLM: `openai/gpt-oss-120b`)
- Streamlit (user interface)
- Open-Meteo API (weather and geocoding)
- Requests, python-dotenv

## Project Structure

```
travel_agent/
├── data/
│   ├── flights.json
│   ├── hotels.json
│   └── places.json
├── travel_tools.py      # data loading, search functions, LangChain tools
├── agent.py             # system prompt, model, plan_trip(), JSON extraction
├── app.py               # Streamlit interface
├── travel_agent.ipynb   # development notebook (step-by-step build and tests)
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Mac / Linux
   ```

3. **Install the dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your Groq API key.** Get a free key at [console.groq.com](https://console.groq.com), then create a file named `.env` in the project folder:
 

5. **Run the app**
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.

## How to Use

1. Choose the source and destination cities.
2. Pick the start and end dates.
3. Set the budget, number of travelers, flight priority (cheapest or fastest) and interests.
4. Click **Generate trip plan**.
5. Read the plan in the **Trip plan** tab, download the **JSON output**, or inspect the tool calls in **Agent steps**.

## Example

**Input:** Mumbai to Goa, 12 to 14 Nov 2026, budget ₹25,000, 1 traveler, cheapest flight, interests: forts and museums.

**Output (summary):**

- Flight: SpiceJet ₹3,304 out, Air India ₹7,533 back
- Hotel: Royal Heritage (5 stars, ₹1,232 per night)
- Day 1: arrival and check-in. Day 2: fort and museum visits. Day 3: check-out and return flight
- Budget: flights ₹10,837 + hotel ₹2,464 + food and local travel ₹2,400 = **₹15,701**

`<add a screenshot of the app here>`

## Deployment (Streamlit Community Cloud)

1. Push the project to GitHub (without `.env`).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app from the repository, branch `main`, main file `app.py`.
3. In **Advanced settings, Secrets**, add:
   ```
   GROQ_API_KEY = "your_key_here"
   ```
4. Deploy.

## Testing

Each component was tested separately before the agent was built: the five search and calculation functions, the weather API (including failure cases), and the LangChain tools. The agent was then tested on edge cases:

| Scenario | Expected behavior |
|---|---|
| Very low budget | Says the budget is too low and stops |
| City with no data (for example Paris) | Says there is no data and does not invent a plan |
| Route with no flight | Says no flight exists on that route |
| End date before start date | Asks for corrected dates without calling any tool |
| Dates beyond the 15-day forecast range | Plans the trip and states that the forecast is unavailable |

## Assumptions and Limitations

- The flights, hotels and places datasets are **sample data** (8 Indian cities, limited records), so names and types can look unrealistic. Each route has only one flight, so "cheapest" and "fastest" often return the same flight.
- Flights are treated as **one-way**, so a round trip is two separate flights. The dates inside `flights.json` are ignored, and the user's travel dates are used instead.
- Hotel price is per room per night. Food and local travel are estimated at ₹800 per person per day.
- Open-Meteo gives forecasts only for about the next 15 days. For later dates the app reports that weather is unavailable.
- The free Groq tier has rate limits, so many requests in a short time can return an error. Wait a minute and try again.

## Future Improvements

- Connect real flight and hotel APIs for live prices
- Multi-city trips and maps for the itinerary
- Hotel and flight booking links
- Support for more cities and currencies
- Save and share generated plans

## Author

`<Annu Verma>`
