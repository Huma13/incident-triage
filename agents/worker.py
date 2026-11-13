"""RQ worker entrypoint for PostgreSQL incident triage."""

import json
import os
import sqlite3

from agents.graph import run_incident_triage

DB_PATH = os.path.join(os.getenv("DATA_DIR", "./data"), "incidents.db")


def run_triage(run_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=10)

    try:
        row = conn.execute(
            "SELECT request FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Run not found: {run_id}")

        incident = json.loads(row[0])

        conn.execute(
            "UPDATE runs SET status = 'running' WHERE run_id = ?",
            (run_id,),
        )
        conn.commit()

        result = run_incident_triage(incident, run_id)

        policy_result = result.get("policy_result", {})
        status = policy_result.get(
            "status",
            result.get("status", "human_escalation"),
        )

        conn.execute(
            "UPDATE runs SET status = ?, result = ? WHERE run_id = ?",
            (
                status,
                json.dumps(result, default=str),
                run_id,
            ),
        )
        conn.commit()

        return result

    except Exception as exc:
        conn.execute(
            "UPDATE runs SET status = ?, result = ? WHERE run_id = ?",
            (
                "human_escalation",
                json.dumps({
                    "status": "human_escalation",
                    "reason": "Worker execution failed.",
                    "error": str(exc),
                }),
                run_id,
            ),
        )
        conn.commit()
        raise

    finally:
        conn.close()
