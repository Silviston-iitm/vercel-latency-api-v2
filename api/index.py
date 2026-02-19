from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import statistics

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

with open("q-vercel-latency.json") as f:
    data = json.load(f)


class RequestModel(BaseModel):
    regions: List[str]
    threshold_ms: int


@app.post("/api/latency")
def analyze(payload: RequestModel):
    results = {}

    for region in payload.regions:
        region_data = [r for r in data if r["region"] == region]

        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=100)[94]
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return results
