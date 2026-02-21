import os
import json
import statistics
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(BASE_DIR, "vercel.json")

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.options("/api/latency")
def options_handler():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )

@app.post("/api/latency")
def analyze(payload: AnalysisRequest):

    with open(FILE_PATH) as f:
        telemetry_data = json.load(f)

    results = {}

    for region in payload.regions:
        region_data = [r for r in telemetry_data if r["region"] == region]

        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        idx = 0.95 * (n - 1)
        low = int(idx)
        weight = idx - low
        p95 = sorted_lat[low]*(1-weight) + sorted_lat[min(low+1,n-1)]*weight

        results[region] = {
            "avg_latency": round(avg_latency,2),
            "p95_latency": round(p95,2),
            "avg_uptime": round(avg_uptime,2),
            "breaches": breaches
        }

    return JSONResponse(
        content={"regions": results},
        headers={"Access-Control-Allow-Origin": "*"}
    )