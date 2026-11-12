"""Worker entrypoint. Stage 3 placeholder: replace with the LangGraph workflow."""
import json
import os
import sqlite3

DB_PATH = os.path.join(os.getenv("DATA_DIR", "./data"), "incidents.db")


def run_triage(run_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("UPDATE runs SET status='running' WHERE run_id=?", (run_id,))
    conn.commit()
    # TODO (Neeraj/Huma): Triage agent -> Investigation agent -> verification -> policy engine
    result = {"status": "escalated", "reason": "agent graph not implemented yet"}
    conn.execute(
        "UPDATE runs SET status=?, result=? WHERE run_id=?",
        ("escalated", json.dumps(result), run_id),
    )
    conn.commit()
