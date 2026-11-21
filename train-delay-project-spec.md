# Train Delay Prediction & Alternative Train Recommendation System

## 1. Core Problem Statement
When a passenger's booked train gets delayed, they currently have no smart way to know whether to wait or catch a different train. This system solves that by taking the user's delay information and personal wait-tolerance, then recommending faster alternative trains — ranked by train type and seat availability — with the exact route path shown.

---

## 2. Main Dashboard — Input Fields
The user manually enters (this is a demo-friendly design — no live delay feed needed):

| Field | Example |
|---|---|
| Source station | Trichy |
| Destination station | Tirunelveli |
| Booked train name + number | Vaigai Express – 12635 |
| Scheduled time | 1:00 PM |
| Delay time (informed via SMS/app in real life) | 2 hours |
| Wait tolerance (user's own patience threshold) | 15 minutes |

---

## 3. Core Decision Logic

**Step 1 — Calculate delayed arrival:**
```
Delayed Arrival Time = Scheduled Time + Delay Time
Example: 1:00 PM + 2 hrs = 3:00 PM
```

**Step 2 — Check against wait tolerance:**
```
IF Delay Time ≤ Wait Tolerance:
    → "Continue with your booked train"
ELSE:
    → Trigger alternative train search
```

**Step 3 — Strict timing window for alternatives (critical rule):**
Any alternative train must arrive **strictly between** the original scheduled time and the new delayed arrival time — not after it. A train arriving at or after 3:00 PM offers zero benefit over just waiting, so it's excluded.

```
Valid window:  Scheduled Time  <  Alternative Arrival Time  <  Delayed Arrival Time
Example:            1:00 PM    <         X                <        3:00 PM
```

Departure time of the alternative should also be checked against the current time, so the user can realistically still catch it.

**Step 4 — Seat availability filter:**
Every candidate alternative train, at every level below, must also have seat availability — timing alone doesn't qualify a train for recommendation.

---

## 4. Three-Level Recommendation Engine

Once a train passes the timing window + seat availability check, it's ranked by level:

**Level 1 — Direct Express/Superfast train**
Best case: a single direct Express or Superfast train exists within the valid window with seats available. Recommend this first.

**Level 2 — Direct Local/Passenger train**
If no Express/Superfast is available, fall back to a direct Local or Passenger train that still fits the timing window and has seats.

**Level 3 — Multi-hop combination (Local/Passenger + Local/Passenger)**
If neither Level 1 nor Level 2 has a direct option, construct a combo route: the user catches one Local/Passenger train to an intermediate station, then a second Local/Passenger train onward to the destination — as long as the total journey still arrives within the valid window, with a realistic layover/connection buffer between the two legs.

---

## 5. Output Display Format

Alternative trains must be shown as a **station-sequence route path**, not just origin→destination:

```
Source → Intermediate Station(s) → Destination
Example: Trichy → Madurai → Tirunelveli
```

Where possible, show departure and arrival times for each leg of the journey, plus train name/number and class-wise seat availability.

---

## 6. Future Delay Prediction (Sidebar Feature)

Separate from the main reactive flow — this is a planning/precaution tool:

- User selects a train + a **future date** (before the actual travel day)
- System shows a **predicted delay probability/range** based on historical patterns (day of week, season, route history, etc.) — e.g., "70% chance of 30–60 min delay"
- This is **informational only** by default — it does not auto-trigger anything

**Feedback loop (agreed extension):**
If the predicted delay probability is high, the system can *proactively* suggest more reliable alternative trains for that future date — using the same 3-level recommendation engine, just triggered by *predicted* delay instead of *confirmed* delay. This lets users book a less delay-prone train in advance, as a precaution.

---

## 7. Two Separate Data Pipelines Needed

| Pipeline | Purpose | Feeds |
|---|---|---|
| **Real-time / manual-entry pipeline** | Main dashboard — reactive alternative recommendation | Train timetable, route/station sequence, seat availability |
| **Historical pattern pipeline** | Sidebar — future delay prediction (ML/regression) | Past delay logs by train, route, day-of-week, season |

## 8. Candidate Data Sources (for timetable, seat availability, and historical delay data)
- **RailRadar** (railradar.in) — REST API: live status, delay-in-minutes, seat availability forecasts, timetables
- **RailKit** (railkit.in) — Node.js SDK: PNR status, live tracking, seat availability, train-between-stations search
- **IndianRailAPI** (via RapidAPI or direct) — station-by-station schedule with actual vs scheduled times, delay-in-minutes per stop
- **Apify Indian Railways Scraper** — pay-per-use, covers 13,000+ trains and 7,300+ stations (schedules, fares, seat availability, live status)

*Recommendation: since the main dashboard uses manual delay entry (not live feed), a one-time downloaded/sample dataset for timetables + historical delays may be safer and more demo-reliable than depending on a live third-party API during a presentation.*

---

## 9. Open Questions to Finalize Before Building
1. Should **travel class** (Sleeper, 3A, 2A, etc.) be a user input, or should the system scan all classes and show whichever has availability?
2. For Level 3 multi-hop, what's the **minimum layover buffer** between the two legs at the connecting station?
3. Confirmed: departure time of alternatives should be checked against current time (not just arrival time against the window) — build this into Step 3's filter.

---

## 10. Recommended Tech Stack

**Frontend**
- **React.js** (with Vite, not CRA) — component-based, perfect for your reusable "recommendation card" UI (Option 1, Option 2 style from the reference screenshot)
- **Tailwind CSS** — fast to theme, easy to build the dark card layout with rounded borders/badges you showed
- **Recharts** (optional) — for the delay-prediction sidebar if you want a probability chart

**Backend**
- **Node.js + Express.js** — simplest fit if you're already looking at Node-based rail APIs like RailKit; handles your recommendation logic (timing window filter → level ranking → seat check) as REST endpoints
- Alternative: **Python + FastAPI/Flask** — worth it *only* if your delay-prediction model is Python-based (scikit-learn/pandas), since then backend and ML share one language. This is the stronger choice if the prediction feature is a major grading component.

**Database**
- **MongoDB** — flexible schema, good fit for nested route data (a train "document" can hold its full array of stops/timings inline, which matches your station-sequence output format naturally)
- Alternative: **PostgreSQL** — better if your college/guide prefers relational DBs, or if you want strict joins between trains, stations, seat_inventory, and delay_logs tables

**Delay Prediction (ML)**
- **Python + pandas + scikit-learn** (Linear Regression / Random Forest / simple time-series model) — trained on historical delay logs (train, route, day-of-week, season) to output a probability/range
- Exposed as its own small Flask/FastAPI microservice if your main backend is Node, so the two responsibilities stay decoupled

**Suggested overall combo (simplest to build + demo):**
```
React + Tailwind  →  Node.js/Express (main API)  →  MongoDB
                              ↓
                   Python microservice (delay prediction ML)
```
This keeps your core recommendation logic fast and simple in Node, while isolating the ML work in Python where the libraries actually live — a very common and defensible architecture for a college project.

---

## 11. Suggested Color Scheme

Matching the dark, modern reference card you shared:

| Element | Color | Use |
|---|---|---|
| Background | `#0B1120` (deep navy) | Page background |
| Card background | `#111827` / `#0F172A` | Recommendation cards, panels |
| Primary accent | `#2DD4BF` (teal/mint green) | Borders, highlights, "Level 1" badges, active states |
| Secondary accent | `#38BDF8` (sky blue) | Links, secondary buttons, station-code tags |
| Success/availability | `#4ADE80` (green) | Seat availability counts, "on time" states |
| Warning | `#FBBF24` (amber) | Transfer counts, delay warnings |
| Text primary | `#F8FAFC` (near-white) | Headings, train names |
| Text secondary | `#94A3B8` (slate gray) | Labels like "Departs", "Arrives", timestamps |

This dark theme with teal/green accents reads as modern and "transit-app" appropriate, and it directly matches the reference screenshot's visual language, so your UI will look consistent with the mockup you already like.

---

## 12. Suggested Next Build Steps
1. Database schema — trains, stations, routes/station-sequences, seat inventory, historical delay logs
2. Recommendation algorithm — pseudocode for the 3-level filter + ranking logic
3. Delay prediction model approach — what historical features to use, simple regression vs. more advanced ML
4. UI wireframe — main dashboard form + results (route path display) + sidebar prediction panel
