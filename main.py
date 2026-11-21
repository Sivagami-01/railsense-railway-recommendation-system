"""
Indian Railways Recommendation System Backend API
-------------------------------------------------
FastAPI server connecting MongoDB, route search, seat availability,
recommendation engine, and delay prediction models.

Endpoints:
  - POST /api/recommendations
  - GET  /api/stations/search
  - POST /api/predict-delay
  - GET  /api/trains/{train_number}
  - GET  /api/health
"""

from contextlib import asynccontextmanager
import re
import sys
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
import uvicorn

from delay_prediction import predict_future_delay, train_delay_models
from recommend import get_recommendations

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# -----------------------------------------------------------------
# PYDANTIC SCHEMAS FOR REQUEST & RESPONSE VALIDATION
# -----------------------------------------------------------------
class RecommendationRequest(BaseModel):
    source_code: str = Field(..., example="JAT", description="Source station code")
    destination_code: str = Field(..., example="UHP", description="Destination station code")
    scheduled_time: str = Field(..., example="2026-11-15T06:30:00", description="Scheduled arrival as ISO datetime string")
    delay_minutes: int = Field(..., ge=0, example=120, description="Delay in minutes")
    wait_tolerance_minutes: int = Field(..., ge=0, example=30, description="User delay tolerance in minutes")
    current_time: Optional[str] = Field(None, description="Optional current wall-clock datetime string")
    min_layover_minutes: Optional[int] = Field(30, description="Minimum layover buffer in minutes for transfer station")
    booked_train_number: Optional[str] = Field(None, description="Booked train number to exclude from alternative suggestions")


class StationResult(BaseModel):
    code: str
    name: str
    state: Optional[str] = None


class DelayPredictionRequest(BaseModel):
    train_number: str = Field(..., example="04601", description="Train number")
    future_date: str = Field(..., example="2026-11-15", description="Future date YYYY-MM-DD")


class DelayPredictionResponse(BaseModel):
    train_number: str
    train_name: str
    future_date: str
    delay_probability_pct: float
    predicted_delay_range_minutes: List[int]
    confidence_note: str


class HealthResponse(BaseModel):
    status: str
    mongodb_connected: bool


# -----------------------------------------------------------------
# FASTAPI LIFESPAN (MONGODB CONNECTION MANAGEMENT)
# -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and pre-load ML models
    try:
        app.state.client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        app.state.db = app.state.client["train_recommendation_system"]
        # Ping DB to verify connection
        app.state.db.command("ping")
        app.state.mongo_connected = True
        print("✓ Connected to MongoDB ('train_recommendation_system')")

        # Load ML models into memory for fast predictions
        clf, reg, fcols, _ = train_delay_models(app.state.db, force_retrain=False, verbose=False)
        app.state.model_tuple = (clf, reg, fcols)
        print("✓ ML Delay Prediction Models loaded into memory.")

    except Exception as e:
        print(f"❌ Failed to connect to MongoDB / load models: {e}")
        app.state.mongo_connected = False
        app.state.db = None
        app.state.model_tuple = None

    yield

    # Shutdown: Close MongoDB connection
    if hasattr(app.state, "client") and app.state.client:
        app.state.client.close()
        print("✓ MongoDB connection closed.")


app = FastAPI(
    title="Indian Railways Recommendation System API",
    description="Backend API powering alternative train recommendations and ML delay predictions.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware allowing React dev servers (localhost:3000 and localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Simple health check returning MongoDB connection status."""
    connected = False
    if getattr(app.state, "db", None) is not None:
        try:
            app.state.db.command("ping")
            connected = True
        except Exception:
            connected = False
    return {"status": "ok", "mongodb_connected": connected}


@app.post("/api/recommendations")
def recommendations_endpoint(req: RecommendationRequest):
    """Computes 3-level alternative train recommendations for a delayed train journey."""
    if getattr(app.state, "db", None) is None:
        raise HTTPException(status_code=500, detail="Database connection not available.")

    try:
        res = get_recommendations(
            source_code=req.source_code,
            destination_code=req.destination_code,
            scheduled_time=req.scheduled_time,
            delay_minutes=req.delay_minutes,
            wait_tolerance_minutes=req.wait_tolerance_minutes,
            db=app.state.db,
            current_time=req.current_time,
            min_layover_minutes=req.min_layover_minutes or 30,
            booked_train_number=req.booked_train_number,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error computing recommendations: {str(e)}"
        )


@app.get("/api/stations/search", response_model=List[StationResult])
def search_stations(query: str = Query(..., min_length=1, description="Station code or name partial search")):
    """Searches stations collection for matching code or name (case-insensitive partial match)."""
    if getattr(app.state, "db", None) is None:
        raise HTTPException(status_code=500, detail="Database connection not available.")

    q = str(query).strip()
    if not q:
        raise HTTPException(status_code=400, detail="Search query must not be empty.")

    try:
        regex_pattern = {"$regex": re.escape(q), "$options": "i"}
        cursor = app.state.db.stations.find(
            {"$or": [{"code": regex_pattern}, {"name": regex_pattern}]}
        ).limit(10)

        results = []
        for doc in cursor:
            results.append(
                {
                    "code": doc.get("code", ""),
                    "name": doc.get("name", ""),
                    "state": doc.get("state"),
                }
            )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Station search failed: {str(e)}")


@app.post("/api/predict-delay", response_model=DelayPredictionResponse)
def predict_delay_endpoint(req: DelayPredictionRequest):
    """Predicts future delay probability and estimated delay range for a train number and date."""
    if getattr(app.state, "db", None) is None:
        raise HTTPException(status_code=500, detail="Database connection not available.")

    try:
        res = predict_future_delay(
            train_number=req.train_number,
            future_date=req.future_date,
            db=app.state.db,
            model_tuple=app.state.model_tuple,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delay prediction failed: {str(e)}")


@app.get("/api/trains/{train_number}")
def get_train_details(train_number: str):
    """Fetches full train route document from trains collection by trainNumber."""
    if getattr(app.state, "db", None) is None:
        raise HTTPException(status_code=500, detail="Database connection not available.")

    tn = str(train_number).strip()
    try:
        train_doc = app.state.db.trains.find_one({"trainNumber": tn})
        if not train_doc:
            tn_alt = str(int(tn)) if tn.isdigit() else tn
            train_doc = app.state.db.trains.find_one({"trainNumber": tn_alt})

        if not train_doc:
            raise HTTPException(
                status_code=404, detail=f"Train number '{train_number}' not found."
            )

        # Convert _id to string for JSON serialization
        train_doc["_id"] = str(train_doc["_id"])
        return train_doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching train: {str(e)}")


def print_startup_banner():
    banner = """
=================================================================
   INDIAN RAILWAYS RECOMMENDATION & DELAY PREDICTION API
=================================================================
  Server running at: http://localhost:8000
  Interactive Docs:  http://localhost:8000/docs

  Available Endpoints:
    1. GET  /api/health
    2. POST /api/recommendations
    3. GET  /api/stations/search?query=<code_or_name>
    4. POST /api/predict-delay
    5. GET  /api/trains/{train_number}
=================================================================
"""
    print(banner)


if __name__ == "__main__":
    print_startup_banner()
    uvicorn.run(app, host="0.0.0.0", port=8000)
