from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List
import json
import statistics
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
file_path = os.path.join(BASE_DIR, "telemetry.json")

with open(file_path, "r") as f:
    telemetry_data = json.load(f)


class RequestModel(BaseModel):
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
def analyze(payload: RequestModel, response: Response):

    response.headers["Access-Control-Allow-Origin"] = "*"

    results = {}

    for region in payload.regions:
        region_data = [r for r in telemetry_data if r["region"] == region]

        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        avg_latency = statistics.mean(latencies)

        sorted_lat = sorted(latencies)
        index = int(0.95 * (len(sorted_lat) - 1))
        p95_latency = sorted_lat[index]

        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return results
