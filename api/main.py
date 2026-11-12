"""FastAPI entrypoint: validate -> quarantine or enqueue. Returns 202 immediately (A4)."""
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis import Redis
from rq import Queue

from api.schemas import IncidentRequest

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "incidents.db")
MAX_BODY_BYTES = 64 * 1024

app = FastAPI(title="Incident Triage Assistant", version="1.0")
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
queue = Queue("triage", connection=redis_conn)


def db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, source_event_id TEXT UNIQUE, "
        "status TEXT, request TEXT, result TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS quarantine (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "received_at TEXT, raw TEXT, errors TEXT)"
    )
    return conn


@app.get("/health")
def health():
    try:
        redis_conn.ping()
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "degraded", "redis": "down"}, status_code=503)


@app.post("/api/v1/runs", status_code=202)
async def submit(request: Request):
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return JSONResponse({"error": "payload too large"}, status_code=413)
    try:
        req = IncidentRequest.model_validate_json(raw)
    except ValidationError as e:
        errors = [
            {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
            for err in e.errors()
        ]
        conn = db()
        conn.execute(
            "INSERT INTO quarantine (received_at, raw, errors) VALUES (?,?,?)",
            (datetime.now(timezone.utc).isoformat(), raw.decode("utf-8", "replace"), json.dumps(errors)),
        )
        conn.commit()
        # No run_id allocated and nothing enqueued: no agent run starts.
        return JSONResponse({"status": "rejected", "errors": errors}, status_code=422)

    conn = db()
    existing = conn.execute(
        "SELECT run_id, status FROM runs WHERE source_event_id=?", (req.source_event_id,)
    ).fetchone()
    if existing:  # idempotency
        return {"run_id": existing[0], "status": existing[1], "duplicate": True}

    run_id = f"INC-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    conn.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?)",
        (run_id, req.source_event_id, "queued", req.model_dump_json(), None,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    queue.enqueue("agents.worker.run_triage", run_id, job_id=run_id, job_timeout=120)
    return {
        "run_id": run_id,
        "status": "queued",
        "status_url": f"/api/v1/runs/{run_id}",
        "result_url": f"/api/v1/runs/{run_id}/result",
    }


@app.get("/api/v1/runs/{run_id}")
def status(run_id: str):
    row = db().execute("SELECT status, result FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    body = {"run_id": run_id, "status": row[0]}
    if row[1]:
        body["result"] = json.loads(row[1])
    return body
