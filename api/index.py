from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import json
import statistics
import os

app = FastAPI()

# 1. CORS Configuration
# Note: If your frontend uses 'credentials: include',
# change ["*"] to specific domains and set allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Robust File Pathing
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure this path is exactly where your file lives relative to this script
file_path = os.path.join(BASE_DIR, "..", "telemetry.json")


def load_telemetry():
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int


@app.post("/api/latency")
async def analyze(payload: AnalysisRequest):
    telemetry_data = load_telemetry()

    if not telemetry_data:
        raise HTTPException(status_code=500, detail="Telemetry data source not found or empty.")

    results = {}

    for region in payload.regions:
        region_data = [r for r in telemetry_data if r.get("region") == region]

        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data if "latency_ms" in r]
        uptimes = [r["uptime_pct"] for r in region_data if "uptime_pct" in r]

        if not latencies:
            continue

        # Calculations
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes) if uptimes else 0

        # P95 Calculation
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        # Using a more standard linear interpolation for p95
        idx = 0.95 * (n - 1)
        low = int(idx)
        high = min(low + 1, n - 1)
        weight = idx - low
        p95_latency = sorted_lat[low] * (1 - weight) + sorted_lat[high] * weight

        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return {"regions": results}