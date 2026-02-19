from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import statistics
import os

app = FastAPI()

# 1. Explicit CORS configuration
# Using allow_origins=["*"] is required by your prompt.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Path handling for Vercel
# Vercel's file system is read-only. Ensure telemetry.json is in the root or /api folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "telemetry.json")

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.post("/api/latency")
async def analyze(payload: AnalysisRequest):
    # Load data inside the route to ensure fresh reads in serverless contexts
    if not os.path.exists(file_path):
        return {"error": "telemetry.json not found", "path_searched": file_path}

    with open(file_path, "r") as f:
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

        # Basic Stats
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes) if uptimes else 0
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        # 95th Percentile (using linear interpolation)
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        if n > 1:
            idx = 0.95 * (n - 1)
            low = int(idx)
            high = min(low + 1, n - 1)
            weight = idx - low
            p95_latency = sorted_lat[low] * (1 - weight) + sorted_lat[high] * weight
        else:
            p95_latency = sorted_lat[0]

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return {"regions": results}