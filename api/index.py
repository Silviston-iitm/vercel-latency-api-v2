import os
import json
import statistics
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from fastapi.responses import Response
from fastapi.responses import JSONResponse

app = FastAPI()
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Use the EXACT filename from your prompt
FILE_NAME = "q-vercel-latency.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, FILE_NAME)

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.get("/")
def health():
    return {"status": "ok", "file_exists": os.path.exists(FILE_PATH)}
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
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )

from fastapi import Response

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
async def analyze(payload: AnalysisRequest):
    if not os.path.exists(FILE_PATH):
        return {"error": f"File {FILE_NAME} not found at {FILE_PATH}"}

    with open(FILE_PATH, "r") as f:
        telemetry_data = json.load(f)

    results = {}
    for region in payload.regions:
        region_data = [r for r in telemetry_data if r.get("region") == region]
        if not region_data: continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        # P95
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        idx = 0.95 * (n - 1)
        low, weight = int(idx), idx % 1
        p95 = sorted_lat[low] * (1-weight) + sorted_lat[min(low+1, n-1)] * weight

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }
    return JSONResponse(
        content={"regions": results},
        headers={"Access-Control-Allow-Origin": "*"}
    )