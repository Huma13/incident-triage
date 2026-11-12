import pytest
from pydantic import ValidationError

from api.schemas import IncidentRequest

VALID = {
    "schema_version": "1.0",
    "source": "manual",
    "source_event_id": "demo-incident-0001",
    "occurred_at": "2026-11-12T13:00:00Z",
    "service": "postgresql",
    "postgres_version": "17.6",
    "environment": "local-test",
    "alert": {
        "name": "DiskUsageHigh",
        "summary": "Disk usage on primary is increasing steadily.",
        "labels": {"instance": "pg-primary-01", "role": "primary"},
        "metrics": [{"name": "disk_used_percent", "value": 88.2, "unit": "percent", "threshold": 85.0}],
    },
    "on_call_note": "Table and index sizes are not growing; cause unknown.",
}


def test_valid_request():
    IncidentRequest.model_validate(VALID)


def test_percent_out_of_range():
    bad = {**VALID, "alert": {**VALID["alert"], "metrics": [{"name": "d", "value": 140, "unit": "percent"}]}}
    with pytest.raises(ValidationError):
        IncidentRequest.model_validate(bad)


def test_wrong_major_version():
    with pytest.raises(ValidationError):
        IncidentRequest.model_validate({**VALID, "postgres_version": "15.2"})


def test_naive_timestamp():
    with pytest.raises(ValidationError):
        IncidentRequest.model_validate({**VALID, "occurred_at": "2026-11-12T13:00:00"})


def test_bad_service():
    with pytest.raises(ValidationError):
        IncidentRequest.model_validate({**VALID, "service": "mysql"})
