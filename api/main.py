"""FastAPI entrypoint: validate -> quarantine or enqueue."""

import json
import os
import sqlite3
import uuid

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from redis import Redis
from rq import Queue
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from api.schemas import IncidentRequest

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "incidents.db")
MAX_BODY_BYTES = 64 * 1024

app = FastAPI(title="Incident Triage Assistant", version="1.0")

redis_conn = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0")
)
queue = Queue("triage", connection=redis_conn)

incident_submissions = Counter(
    "incident_submissions_total",
    "Incident submissions by outcome.",
    ["outcome"],
)

http_requests = Counter(
    "http_requests_total",
    "HTTP requests by method, route, and status.",
    ["method", "route", "status"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request processing duration in seconds.",
    ["method", "route"],
)


@app.middleware("http")
async def record_http_metrics(request: Request, call_next):
    import time

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    route = request.scope.get("route")
    route_path = getattr(route, "path", "unmatched")
    method = request.method

    http_requests.labels(
        method=method,
        route=route_path,
        status=str(response.status_code),
    ).inc()

    http_request_duration.labels(
        method=method,
        route=route_path,
    ).observe(duration)

    return response


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs ("
        "run_id TEXT PRIMARY KEY, source_event_id TEXT UNIQUE, "
        "status TEXT, request TEXT, result TEXT, created_at TEXT)"
    )

    conn.execute(
        "CREATE TABLE IF NOT EXISTS quarantine ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "received_at TEXT, raw TEXT, errors TEXT)"
    )

    return conn


@app.get("/health")
def health():
    try:
        redis_conn.ping()
        return {"status": "ok"}
    except Exception:
        return JSONResponse(
            {"status": "degraded", "redis": "down"},
            status_code=503,
        )


@app.post("/api/v1/runs", status_code=202)
async def submit(request: Request):
    raw = await request.body()

    if len(raw) > MAX_BODY_BYTES:
        incident_submissions.labels(outcome="oversized").inc()
        return JSONResponse(
            {"error": "payload too large"},
            status_code=413,
        )

    try:
        req = IncidentRequest.model_validate_json(raw)
    except ValidationError as exc:
        incident_submissions.labels(outcome="rejected").inc()
        errors = [
            {
                "field": ".".join(str(part) for part in err["loc"]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]

        conn = db()
        try:
            conn.execute(
                "INSERT INTO quarantine (received_at, raw, errors) "
                "VALUES (?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    raw.decode("utf-8", "replace"),
                    json.dumps(errors),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return JSONResponse(
            {"status": "rejected", "errors": errors},
            status_code=422,
        )

    conn = db()
    try:
        existing = conn.execute(
            "SELECT run_id, status FROM runs WHERE source_event_id = ?",
            (req.source_event_id,),
        ).fetchone()

        if existing:
            incident_submissions.labels(outcome="duplicate").inc()
            return {
                "run_id": existing[0],
                "status": existing[1],
                "duplicate": True,
            }

        run_id = (
            f"INC-{datetime.now(timezone.utc):%Y%m%d}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        conn.execute(
            "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                req.source_event_id,
                "queued",
                req.model_dump_json(),
                None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    incident_submissions.labels(outcome="accepted").inc()
    queue.enqueue(
        "agents.worker.run_triage",
        run_id,
        job_id=run_id,
        job_timeout=120,
    )

    return {
        "run_id": run_id,
        "status": "queued",
        "status_url": f"/api/v1/runs/{run_id}",
        "result_url": f"/api/v1/runs/{run_id}/result",
    }


@app.get("/api/v1/runs/{run_id}")
def status(run_id: str):
    conn = db()
    try:
        row = conn.execute(
            "SELECT status, result FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return JSONResponse(
            {"error": "not found"},
            status_code=404,
        )

    body = {
        "run_id": run_id,
        "status": row[0],
    }

    if row[1]:
        body["result"] = json.loads(row[1])

    return body


@app.get("/api/v1/runs/{run_id}/result")
def get_result(run_id: str):
    conn = db()
    try:
        row = conn.execute(
            "SELECT status, result FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return JSONResponse(
            {"error": "not found"},
            status_code=404,
        )

    if row[1] is None:
        return JSONResponse(
            {
                "run_id": run_id,
                "status": row[0],
                "message": "Result is not ready yet.",
            },
            status_code=409,
        )

    return {
        "run_id": run_id,
        "status": row[0],
        "result": json.loads(row[1]),
    }
