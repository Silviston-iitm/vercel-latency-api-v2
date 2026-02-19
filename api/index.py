import os
import json
import statistics
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# 1. Broad CORS for Vercel Serverless
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Vercel-friendly pathing
# This looks for the file in the same directory as this script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure your file name matches exactly what you downloaded
FILE_PATH = os.path.join(BASE_DIR, "q-vercel-latency.json")


class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int


@app.post("/api/latency")
async def analyze(payload: AnalysisRequest):
    # 3. Defensive File Loading
    if not os.path.exists(FILE_PATH):
        # We return a 200 with an error msg so you can see the path in the browser
        return {"error": "File not found", "searched_at": FILE_PATH}

    try:
        with open(FILE_PATH, "r") as f:
            telemetry_data = json.load(f)
    except Exception as e:
        return {"error": "Failed to parse JSON", "details": str(e)}

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

        # P95 Calculation (Linear Interpolation)
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        idx = 0.95 * (n - 1)
        low = int(idx)
        high = min(low + 1, n - 1)
        weight = idx - low
        p95_latency = sorted_lat[low] * (1 - weight) + sorted_lat[high] * weight

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return {"regions": results}