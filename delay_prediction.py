"""
Future Train Delay Prediction Module
------------------------------------
Trains a machine learning model on historical delay records in MongoDB ("delay_history")
to predict train delay probabilities and expected delay ranges for future dates.

Features preventing data leakage:
  Uses ONLY features known in advance (date/time, train static properties, route history, zone congestion).
  EXCLUDES all same-day runtime variables (seat utilization, late incoming rake, loco age, etc.).

Saves trained models to:
  - delay_classifier.pkl
  - delay_regressor.pkl
  - delay_feature_columns.pkl

Uses scikit-learn, pandas, joblib, pymongo, and Python standard library.
"""

from datetime import datetime
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import joblib
import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Model File Paths
CLASSIFIER_PATH = "delay_classifier.pkl"
REGRESSOR_PATH = "delay_regressor.pkl"
FEATURES_PATH = "delay_feature_columns.pkl"

# Categorical columns to one-hot encode
CATEGORICAL_COLS = [
    "train_type",
    "season",
    "zone",
    "zone_abbr",
    "source_station_category",
    "destination_station_category",
    "traction_type",
]

# Explicit list of excluded same-day runtime leakage fields
EXCLUDE_LEAKAGE_COLS = [
    "seat_utilisation_pct",
    "is_overloaded",
    "late_incoming_rake",
    "loco_age_years",
    "coach_age_years",
    "is_rake_shared",
    "maintenance_score",
    "primary_delay_cause",
    "is_monsoon_season",
    "is_fog_risk",
    "fog_risk_score",
    "journey_id",
    "departure_date",
    "year",
    "delay_minutes",  # target for regressor
    "is_delayed",     # target for classifier
    "_id",
]


def train_delay_models(
    db: Any, sample_size: int = 250000, force_retrain: bool = True, verbose: bool = True
) -> Tuple[HistGradientBoostingClassifier, HistGradientBoostingRegressor, List[str], Dict[str, float]]:
    """
    Loads historical delay data from MongoDB, trains Classifier & Regressor models,
    evaluates performance metrics, and saves the models with joblib.

    Args:
        db: PyMongo database instance.
        sample_size: Number of records to load for training (default 250,000).
        force_retrain: If True, retrains models from scratch.
        verbose: If True, prints progress and metric messages.

    Returns:
        Tuple: (classifier, regressor, feature_columns_list, metrics_dict)
    """
    if (
        not force_retrain
        and os.path.exists(CLASSIFIER_PATH)
        and os.path.exists(REGRESSOR_PATH)
        and os.path.exists(FEATURES_PATH)
    ):
        if verbose:
            print("[OK] Loading pre-trained delay prediction models from disk...")
        clf = joblib.load(CLASSIFIER_PATH)
        reg = joblib.load(REGRESSOR_PATH)
        feature_cols = joblib.load(FEATURES_PATH)
        metrics = {"status": "loaded_from_disk"}
        return clf, reg, feature_cols, metrics

    if verbose:
        print(f"\n[ML Pipeline] Sampling {sample_size:,} records from 'delay_history' collection...")
    t0 = time.time()

    sample_records = list(db.delay_history.find({}, {"_id": 0}).limit(sample_size))
    if not sample_records:
        raise ValueError("No records found in 'delay_history' collection.")

    df = pd.DataFrame(sample_records)
    if verbose:
        print(f"✓ Loaded {len(df):,} records into DataFrame in {time.time() - t0:.2f}s.")

    # Convert numeric train_number
    df["train_number"] = pd.to_numeric(df["train_number"], errors="coerce").fillna(0)

    # One-hot encode categorical features
    df_encoded = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=False)

    # Determine final feature column names (excluding targets and leakage fields)
    feature_cols = [c for c in df_encoded.columns if c not in EXCLUDE_LEAKAGE_COLS]
    if verbose:
        print(f"✓ Selected {len(feature_cols)} leak-free features for model training.")

    X = df_encoded[feature_cols]
    y_cls = df["is_delayed"].astype(int)

    # 1. Train Classifier (predicts is_delayed 0/1)
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X, y_cls, test_size=0.2, random_state=42, stratify=y_cls
    )

    if verbose:
        print("  Training Delay Classifier (HistGradientBoostingClassifier)...")
    clf = HistGradientBoostingClassifier(max_iter=120, random_state=42)
    clf.fit(X_train_c, y_train_c)

    preds_c = clf.predict(X_test_c)
    acc = accuracy_score(y_test_c, preds_c)
    f1 = f1_score(y_test_c, preds_c)

    # 2. Train Regressor (predicts delay_minutes for delayed trains where is_delayed == 1)
    delayed_mask = df["is_delayed"] == 1
    df_delayed = df_encoded[delayed_mask]

    X_reg = df_delayed[feature_cols]
    y_reg = df_delayed["delay_minutes"].astype(float)

    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42
    )

    if verbose:
        print("  Training Delay Regressor (HistGradientBoostingRegressor)...")
    reg = HistGradientBoostingRegressor(max_iter=120, random_state=42)
    reg.fit(X_train_r, y_train_r)

    preds_r = reg.predict(X_test_r)
    mae = mean_absolute_error(y_test_r, preds_r)
    rmse = root_mean_squared_error(y_test_r, preds_r)

    metrics = {
        "classifier_accuracy": float(acc),
        "classifier_f1": float(f1),
        "regressor_mae": float(mae),
        "regressor_rmse": float(rmse),
        "training_time_sec": float(time.time() - t0),
    }

    if verbose:
        print(f"✓ Training complete in {metrics['training_time_sec']:.2f}s.")

    # Save models to disk
    joblib.dump(clf, CLASSIFIER_PATH)
    joblib.dump(reg, REGRESSOR_PATH)
    joblib.dump(feature_cols, FEATURES_PATH)

    if verbose:
        print(f"✓ Saved model artifacts to '{CLASSIFIER_PATH}', '{REGRESSOR_PATH}', '{FEATURES_PATH}'.")

    return clf, reg, feature_cols, metrics


def get_season_name(month: int) -> str:
    """Approximates season name based on month number."""
    if month in (12, 1, 2):
        return "Winter/Fog"
    elif month in (3, 4, 5):
        return "Summer"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    else:
        return "Autumn"


def predict_future_delay(
    train_number: Any,
    future_date: str,
    db: Any,
    model_tuple: Optional[Tuple[HistGradientBoostingClassifier, HistGradientBoostingRegressor, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Predicts the delay probability and estimated delay range for a train on a future date.

    Args:
        train_number: Train number (int or str, e.g. "04601" or 12445).
        future_date: Future date string in "YYYY-MM-DD" format (e.g. "2026-11-15").
        db: PyMongo database instance.
        model_tuple: Optional tuple of (classifier, regressor, feature_cols) to reuse in-memory objects.

    Returns:
        Dict[str, Any]: Prediction results containing delay probability, range, and confidence note.
    """
    if model_tuple is not None:
        clf, reg, feature_cols = model_tuple
    else:
        clf, reg, feature_cols, _ = train_delay_models(db, force_retrain=False, verbose=False)

    # Parse Future Date
    dt = datetime.strptime(future_date.strip(), "%Y-%m-%d")
    month = dt.month
    day_of_week = dt.weekday()  # Monday=0, Sunday=6
    is_weekend = 1 if day_of_week in (5, 6) else 0

    # Approximate Festival Season (Oct/Nov Diwali/Durga Puja or March Holi)
    is_festival_season = 1 if month in (3, 10, 11) else 0
    season_name = get_season_name(month)

    tn_raw = str(train_number).strip().lstrip("0")
    tn_num = int(tn_raw) if tn_raw.isdigit() else 0

    # Query static train metadata from trains collection or delay_history
    train_doc = db.trains.find_one({"trainNumber": str(train_number)})
    train_name = train_doc.get("trainName") if train_doc else None

    hist_sample = db.delay_history.find_one(
        {"$or": [{"train_number": tn_num}, {"train_number": str(train_number)}]}
    )

    if not hist_sample:
        hist_sample = db.delay_history.find_one() or {}

    if not train_name:
        train_name = hist_sample.get("train_name", f"Train #{train_number}")

    # Build raw feature row
    raw_feature_dict = {
        "train_number": tn_num,
        "month": month,
        "day_of_week": day_of_week,
        "departure_hour": hist_sample.get("departure_hour", 12),
        "is_weekend": is_weekend,
        "is_night_departure": hist_sample.get("is_night_departure", 0),
        "is_peak_hour": hist_sample.get("is_peak_hour", 0),
        "is_festival_season": is_festival_season,
        "distance_km": hist_sample.get("distance_km", 500),
        "num_scheduled_stops": hist_sample.get("num_scheduled_stops", 10),
        "scheduled_travel_hours": hist_sample.get("scheduled_travel_hours", 8.0),
        "track_doubled": hist_sample.get("track_doubled", 1),
        "is_hdn_route": hist_sample.get("is_hdn_route", 0),
        "is_electrified": hist_sample.get("is_electrified", 1),
        "psr_count": hist_sample.get("psr_count", 2),
        "is_circular_route": hist_sample.get("is_circular_route", 0),
        "zone_fog_index": hist_sample.get("zone_fog_index", 0.2),
        "zone_congestion_index": hist_sample.get("zone_congestion_index", 0.5),
        "season_severity_score": hist_sample.get("season_severity_score", 0.3),
        "has_lhb_coaches": hist_sample.get("has_lhb_coaches", 1),
        "route_historical_ontime_pct": hist_sample.get("route_historical_ontime_pct", 75.0),
        "train_type": hist_sample.get("train_type", "Superfast Express"),
        "season": season_name,
        "zone": hist_sample.get("zone", "Northern Railway (NR)"),
        "zone_abbr": hist_sample.get("zone_abbr", "NR"),
        "source_station_category": hist_sample.get("source_station_category", "A1"),
        "destination_station_category": hist_sample.get("destination_station_category", "A1"),
        "traction_type": hist_sample.get("traction_type", "Electric"),
    }

    # One-hot encode input row and align with training feature columns
    row_df = pd.DataFrame([raw_feature_dict])
    row_encoded = pd.get_dummies(row_df, columns=CATEGORICAL_COLS, drop_first=False)

    # Reindex columns to match training features exactly (fill missing one-hot dummies with 0)
    aligned_input = row_encoded.reindex(columns=feature_cols, fill_value=0)

    # Run Predictions
    prob_delay = float(clf.predict_proba(aligned_input)[0][1])
    delay_probability_pct = round(prob_delay * 100, 1)

    predicted_delay_mins = float(reg.predict(aligned_input)[0])

    if delay_probability_pct < 35.0:
        low_bound = 0
        high_bound = max(0, int(round(predicted_delay_mins * 0.5)))
        note = "High likelihood of on-time arrival based on historical route reliability."
    elif delay_probability_pct < 70.0:
        low_bound = max(0, int(round(predicted_delay_mins * 0.7)))
        high_bound = int(round(predicted_delay_mins * 1.2)) + 5
        note = "Moderate risk of minor delay expected due to seasonal congestion factors."
    else:
        low_bound = max(10, int(round(predicted_delay_mins * 0.8)))
        high_bound = int(round(predicted_delay_mins * 1.3)) + 15
        note = "High probability of delay expected based on seasonal and zone congestion indices."

    return {
        "train_number": str(train_number),
        "train_name": train_name,
        "future_date": future_date,
        "delay_probability_pct": delay_probability_pct,
        "predicted_delay_range_minutes": [low_bound, high_bound],
        "confidence_note": note,
    }


if __name__ == "__main__":
    print("=================================================================")
    print("      FUTURE TRAIN DELAY PREDICTION MODULE DEMO")
    print("=================================================================")

    client = MongoClient("mongodb://localhost:27017")
    db = client["train_recommendation_system"]

    # 1. ALWAYS retrain from scratch in one continuous run
    clf, reg, feature_cols, metrics = train_delay_models(
        db, sample_size=250000, force_retrain=True, verbose=True
    )

    print("\n=== MODEL TEST-SET PERFORMANCE METRICS ===")
    print(f"  Classifier Accuracy : {metrics['classifier_accuracy'] * 100:.2f}%")
    print(f"  Classifier F1-Score : {metrics['classifier_f1']:.4f}")
    print(f"  Regressor MAE       : {metrics['regressor_mae']:.2f} minutes")
    print(f"  Regressor RMSE      : {metrics['regressor_rmse']:.2f} minutes")
    print(f"  Training Duration   : {metrics['training_time_sec']:.2f} seconds")

    # 2. Test predictions using the in-memory model objects from THIS run
    in_memory_models = (clf, reg, feature_cols)
    test_cases = [
        ("04601", "2026-11-15"),  # Jammu Tawi Udhampur Special in Winter/Fog season
        ("12636", "2026-10-24"),  # Vaigai Express during Diwali festival season
        ("04741", "2026-07-20"),  # Sirsa Hisar Passenger in Monsoon season
    ]

    print("\n=== FUTURE DATE DELAY PREDICTIONS (IN-MEMORY MODEL EVALUATION) ===")
    for train_num, fut_date in test_cases:
        pred_res = predict_future_delay(train_num, fut_date, db, model_tuple=in_memory_models)
        print(f"\nTrain #{pred_res['train_number']} ({pred_res['train_name']}) on {pred_res['future_date']}:")
        print(f"  - Delay Probability : {pred_res['delay_probability_pct']}%")
        print(f"  - Expected Delay    : {pred_res['predicted_delay_range_minutes'][0]} to {pred_res['predicted_delay_range_minutes'][1]} minutes")
        print(f"  - Note              : {pred_res['confidence_note']}")

    print("\n=================================================================")
