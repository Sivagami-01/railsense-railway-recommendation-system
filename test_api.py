"""
FastAPI Backend API Test Suite
-------------------------------
Tests all 5 endpoints of main.py via HTTP requests and prints request/response payloads.
"""

import json
import time
import urllib.request
import urllib.parse


BASE_URL = "http://localhost:8000"


def make_request(method: str, endpoint: str, data: dict = None) -> tuple:
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    req_body = None
    if data is not None:
        req_body = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.status
            response_json = json.loads(resp.read().decode("utf-8"))
            return status_code, response_json
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_json = json.loads(e.read().decode("utf-8"))
        return status_code, response_json


def run_tests():
    print("=================================================================")
    print("       FASTAPI BACKEND API ENDPOINTS VERIFICATION SUITE         ")
    print("=================================================================")

    # 1. Health Check Endpoint
    print("\n1. GET /api/health")
    status, body = make_request("GET", "/api/health")
    print(f"Status: {status}")
    print(f"Response:\n{json.dumps(body, indent=2)}")

    # 2. Recommendations Endpoint (Overnight Scenario: SSA -> HSR)
    print("\n2. POST /api/recommendations (Overnight Past-Midnight Datetime Test)")
    rec_payload = {
        "source_code": "SSA",
        "destination_code": "HSR",
        "scheduled_time": "2026-11-16T00:10:00",
        "delay_minutes": 60,
        "wait_tolerance_minutes": 10
    }
    print(f"Request Payload:\n{json.dumps(rec_payload, indent=2)}")
    status, body = make_request("POST", "/api/recommendations", rec_payload)
    print(f"Status: {status}")
    print(f"Response:\n{json.dumps(body, indent=2)}")

    # 3. Station Search Endpoint
    print("\n3. GET /api/stations/search?query=jammu")
    status, body = make_request("GET", "/api/stations/search?query=jammu")
    print(f"Status: {status}")
    print(f"Response:\n{json.dumps(body, indent=2)}")

    # 4. Predict Delay Endpoint
    print("\n4. POST /api/predict-delay")
    delay_payload = {
        "train_number": "04601",
        "future_date": "2026-11-15"
    }
    print(f"Request Payload:\n{json.dumps(delay_payload, indent=2)}")
    status, body = make_request("POST", "/api/predict-delay", delay_payload)
    print(f"Status: {status}")
    print(f"Response:\n{json.dumps(body, indent=2)}")

    # 5. Train Details Endpoint
    print("\n5. GET /api/trains/04601")
    status, body = make_request("GET", "/api/trains/04601")
    print(f"Status: {status}")
    # Truncate completeOrderedRoute for clean log display
    if "completeOrderedRoute" in body and len(body["completeOrderedRoute"]) > 3:
        body["completeOrderedRoute"] = body["completeOrderedRoute"][:3] + ["... (truncated for display)"]
    print(f"Response:\n{json.dumps(body, indent=2)}")

    print("\n=================================================================")


if __name__ == "__main__":
    time.sleep(2)  # Short pause to ensure FastAPI server is initialized
    run_tests()
