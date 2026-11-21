# Indian Railways Delay & Alternative Recommendation System

This is the simple English explanation of our project. You can copy this into Word and use it for presentation or viva.

---

## 1) Real-world problem we are solving

When a passenger is already travelling or has a booked ticket, and the train gets delayed, there is no smart system that tells them:

- Should I wait for the same train?
- Or should I catch another train?
- Which train is safer and faster?
- Which alternative has seats available?

In real life, railway passengers often face confusion when a train is delayed by 1 hour, 2 hours, or more. They do not know which other train can reach the destination in time. Our project solves this problem.

We built a system that:

- takes the source station, destination station, scheduled time, and delay time,
- checks whether the delay is acceptable or not,
- finds better alternative trains,
- filters them by time and seat availability,
- shows the route path with intermediate stations,
- and also predicts future delay risk for a train on a future date.

This is useful for passengers, travel planners, and even railway decision support systems.

---

## 2) What we actually built

We built a railway decision support website with two main features:

1. Real-time / manual delay decision engine
   - User enters the trip details.
   - If the train delay is within the passenger's wait tolerance, system says: continue with your booked train.
   - If delay is beyond tolerance, the system searches for better alternative trains.

2. Future delay prediction panel
   - User selects a train and future date.
   - System predicts the chance of delay and the expected delay range.
   - If the predicted risk is high, it can suggest alternatives.

So the website is not only a search page. It is a decision system that helps a passenger decide the best travel plan.

---

## 3) How the whole website works

The flow is:

1. User enters source station and destination station.
2. User enters scheduled time and actual delay time.
3. User sets wait tolerance, meaning how long they are willing to wait.
4. Frontend sends this data to the backend API.
5. Backend checks the delay rule.
6. It searches for direct trains between the two stations.
7. It filters trains by:
   - arrival should be between scheduled time and delayed arrival time,
   - departure should be in the future,
   - seat availability should be greater than zero,
   - and multi-hop trains should have reasonable layover time.
8. The best alternatives are ranked as Level 1, Level 2, and Level 3.
9. Frontend shows the alternatives in cards with route paths and seat availability.

This whole process is implemented in:

- [src/App.jsx](src/App.jsx)
- [src/components/RecommendationForm.jsx](src/components/RecommendationForm.jsx)
- [src/components/AlternativeCard.jsx](src/components/AlternativeCard.jsx)
- [src/components/DecisionBanner.jsx](src/components/DecisionBanner.jsx)
- [src/lib/api.js](src/lib/api.js)

---

## 4) What is the exact decision logic?

Our logic is designed to imitate a practical railway decision.

### Rule 1: If delay is small, do not change train

If delay minutes are less than or equal to the user’s wait tolerance, the system says:

- Continue with the booked train.

That means the passenger is okay to wait for the same train.

### Rule 2: Delayed arrival time is calculated

The backend computes:

- delayed arrival = scheduled time + delay time

Example:

- scheduled arrival = 1:00 PM
- delay = 2 hours
- delayed arrival = 3:00 PM

### Rule 3: Alternative train should arrive only in the valid window

A candidate train is valid only if its arrival is:

- strictly after scheduled arrival,
- strictly before delayed arrival,
- and not equal to or after the delayed arrival time.

This is very important because if the alternative train arrives at or after the delayed arrival, it is not useful.

### Rule 4: Alternative train should be realistically catchable

The candidate train should also leave after the current time and leave enough time for the passenger to board.

### Rule 5: Seats should be available

Even if the timing is perfect, the train must have seats available in at least one class. Otherwise it is rejected.

This logic is implemented in:

- [recommend.py](recommend.py)
- [recommendation_engine.py](recommendation_engine.py)
- [route_search.py](route_search.py)

---

## 5) Why we use 3-level recommendation system

We do not simply give one random train option. We rank alternatives in levels.

### Level 1: Direct Express / Superfast / Premium trains

These are the best options because they are faster and usually more comfortable.

Examples: Superfast, Rajdhani, Shatabdi, Vande Bharat, Duronto, Garib Rath.

### Level 2: Direct Local / Passenger / DEMU / MEMU trains

If premium trains are not available, then local or regional train options are considered.

### Level 3: Multi-hop transfer train

If no direct option qualifies, the system checks a two-leg route:

- source → intermediate station → destination

This is useful when a direct train is not available but a two-train combination can still reach the destination before the delayed arrival time.

This is exactly the major idea of our project.

---

## 6) What is the algorithm we are using?

The main recommendation algorithm is a rule-based logic system. It is not a random AI recommendation; it is a structured logic engine.

### Main algorithm steps

1. Convert scheduled time and delay into exact date-time values.
2. Find all direct trains from source to destination.
3. Remove trains that are before the current time.
4. Remove trains whose arrival is not between the scheduled and delayed time window.
5. Check seat availability.
6. Classify trains into Level 1 or Level 2.
7. If no direct options work, search multi-hop combinations.
8. Sort results by travel time and return the best options.

This is a practical algorithm because it is transparent and easy to explain in a demo or viva.

### Why this algorithm is suitable

- It matches real railway decision-making.
- It is easy to understand.
- It is fast and explainable.
- It gives results that human users can trust.
- It is perfect for a college project because it is simple but strong.

We use rule-based logic + route filtering + seat availability checks instead of only AI because in bus/train travel, explainability matters more than just prediction.

---

## 7) How the future delay prediction works

This is the second major feature of the website.

The future delay feature is built in [delay_prediction.py](delay_prediction.py).

It uses historical delay data and machine learning.

### What it does

- User selects a train number and future date.
- System loads historical railway delay records from MongoDB.
- It trains a classifier and a regressor model.
- The classifier predicts whether the train is likely to be delayed.
- The regressor predicts the delay range (for example, 30–60 minutes).
- It returns:
  - probability of delay,
  - predicted delay range,
  - confidence note.

### Model used

We use:

- HistGradientBoostingClassifier
- HistGradientBoostingRegressor

These are from scikit-learn.

### Why this model?

Because:

- it handles tabular data well,
- it works with mixed features,
- it is robust for real project use,
- it is easy to train on historical delay data,
- and it gives good prediction performance.

This model uses historical features such as:

- train type,
- month,
- day of week,
- season,
- route distance,
- source and destination categories,
- track condition,
- congestion score,
- historical on-time percentage,
- zone, and similar railway-related information.

The dataset structure for these features is defined in [dataset/ir_data_dictionary.csv](dataset/ir_data_dictionary.csv).

---

## 8) How the backend is working

The backend is built using FastAPI in [main.py](main.py).

### Main responsibilities of backend

- connect to MongoDB,
- accept frontend requests,
- validate request data,
- search stations,
- compute recommendations,
- call the delay prediction model,
- return JSON responses to the frontend.

### Important API endpoints

- POST /api/recommendations
  - gives recommendation results
- GET /api/stations/search
  - searches station names and codes
- POST /api/predict-delay
  - returns predicted delay info
- GET /api/trains/{train_number}
  - fetches train route details
- GET /api/health
  - checks server and database status

This is the heart of the application.

---

## 9) How the station names and intermediate stations are visible in results

This is very important for the project. The user wants to know how intermediate stations appear in the result.

The route is not shown as just source → destination. It is shown as a full sequence, such as:

- Jammu Tawi → Udhampur → X → Destination

This is possible because each train record contains a full ordered route in MongoDB. The route is stored in a list like:

- station code,
- station name,
- arrival time,
- departure time,
- sequence,
- journey day,
- distance.

The functions that extract this route are in:

- [route_search.py](route_search.py)

Then the frontend uses [src/components/AlternativeCard.jsx](src/components/AlternativeCard.jsx) to render these station codes and names as a horizontal sequence with arrows.

So the user can clearly see the exact route path.

---

## 10) How the dataset is used and where it came from

We used railway-related datasets stored in the [dataset](dataset) folder.

### Main datasets in this project

- [dataset/stations_clean.json](dataset/stations_clean.json)
  - station codes and names
  - cleaned station list for the frontend and backend search

- [dataset/stations.json](dataset/stations.json)
  - original station data before cleaning

- [dataset/trains.json](dataset/trains.json)
  - train route information and station sequence

- [dataset/ir_train.csv](dataset/ir_train.csv)
  - historical delay dataset used for ML prediction

- [dataset/ir_data_dictionary.csv](dataset/ir_data_dictionary.csv)
  - explains every field in the delay dataset

### Where we collected / planned the data from

The project plan in [train-delay-project-spec.md](train-delay-project-spec.md) lists realistic railway data sources such as:

- RailRadar
- RailKit
- IndianRailAPI
- Apify Indian Railways Scraper

These are the real-world sources that inspired the project. In this repository, we use a local dataset version of learned/train/test data so the project can run and demo reliably without depending on live external APIs.

### Data preparation process

We used the scripts:

- [clean_stations.py](clean_stations.py)
- [import_to_mongo.py](import_to_mongo.py)
- [generate_dropdown_data.py](generate_dropdown_data.py)

They do the following:

- clean invalid station entries,
- remove duplicates,
- import data into MongoDB,
- create searchable station and train dropdown data for the website.

---

## 11) Why our website is useful for the public

This system is useful because it gives passengers better travel confidence.

### Real public use

- A passenger knows whether to wait for their delayed train.
- They can compare the delayed train with other profitable alternatives.
- They can choose a train with seats available.
- They can plan a connection route if no direct option exists.
- They can understand the risk of a future delay before booking.

This saves time, reduces stress, and helps passengers make faster decisions.

In short, our project is a smart travel assistant for Indian Railways passengers.

---

## 12) Tools and technologies used

### Frontend

- React.js
- Vite
- JavaScript / JSX
- Tailwind CSS

### Backend

- Python
- FastAPI
- Pydantic
- MongoDB
- PyMongo

### Machine Learning

- Python
- pandas
- scikit-learn
- HistGradientBoostingClassifier
- HistGradientBoostingRegressor

### Data processing

- JSON
- CSV
- Python scripts
- MongoDB import tools

### Deployment / local run

- Node.js / npm
- Python environment
- Local MongoDB instance

This is exactly the modern practical stack used for a demo-worthy software project.

---

## 13) What files are important in the project

Here are the most important files:

- [main.py](main.py) — backend API entry point
- [recommend.py](recommend.py) — recommendation logic
- [recommendation_engine.py](recommendation_engine.py) — route-level recommendation logic
- [route_search.py](route_search.py) — direct and multi-hop route detection
- [seat_availability.py](seat_availability.py) — mock seat availability logic
- [delay_prediction.py](delay_prediction.py) — ML delay prediction
- [train-delay-project-spec.md](train-delay-project-spec.md) — project plan / requirement document
- [src/App.jsx](src/App.jsx) — main React page
- [src/components/RecommendationForm.jsx](src/components/RecommendationForm.jsx) — input form
- [src/components/AlternativeCard.jsx](src/components/AlternativeCard.jsx) — result cards
- [src/components/DelayPredictionPanel.jsx](src/components/DelayPredictionPanel.jsx) — future delay prediction UI
- [dataset](dataset) — data files

---

## 14) Simple summary in one sentence

Our project helps railway passengers decide whether to wait for a delayed train or switch to a better alternative by using route filtering, seat checks, time-window logic, and machine learning-based future delay prediction.

---

## 15) Presentation-ready points

If the judge asks a quick viva question, say:

- “Our project solves the problem of passengers not knowing what to do when their booked train gets delayed.”
- “We built a rule-based recommendation engine that filters better alternative trains by timing and seat availability.”
- “We ranked alternatives as Level 1, Level 2, and Level 3.”
- “We used MongoDB to store station and train route data.”
- “We used a machine learning model to predict future train delay probability and delay range.”
- “The system shows the full intermediate route path so passengers know exactly what route they would take.”
- “This is useful for real-world railway travel planning and reduces uncertainty for passengers.”

---

## 16) Final note

This project is a good combination of:

- backend logic,
- data processing,
- route search,
- practical recommendation engine,
- and ML prediction.

It is a complete practical demo of how a smart railway decision system can help passengers in real life.
