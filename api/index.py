import os
import json
import statistics
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# 1. CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Pathing logic for Vercel
# Assumes telemetry.json is in the same folder as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "telemetry.json")

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.post("/api/latency")
async def analyze(payload: AnalysisRequest):
    # If the file is missing, return a JSON error instead of crashing
    if not os.path.exists(FILE_PATH):
        return {"error": f"telemetry.json not found at {FILE_PATH}"}

    with open(FILE_PATH, "r") as f:
        telemetry_data = json.load(f)

    results = {}

    for region in payload.regions:
        region_data = [r for r in telemetry_data if r.get("region") == region]
        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data if "latency_ms" in r]
        uptimes = [r["uptime_pct"] for r in region_data if "uptime_pct" in r]

        if not latencies:
            continue

        # Statistics
        avg_latency = sum(latencies) / len(latencies)
        avg_uptime = sum(uptimes) / len(uptimes) if uptimes else 0
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        # 95th Percentile
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        idx = 0.95 * (n - 1)
        low = int(idx)
        high = min(low + 1, n - 1)
        w = idx - low
        p95_latency = sorted_lat[low] * (1 - w) + sorted_lat[high] * w

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return {"regions": results}