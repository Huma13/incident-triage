"""Data contract v1 for the incident triage API (requirement D1/F2)."""
import math
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

CORPUS_MAJOR = os.getenv("POSTGRES_DOC_VERSION", "17")


class Source(str, Enum):
    manual = "manual"
    prometheus = "prometheus"
    replay = "replay"


class Environment(str, Enum):
    local_test = "local-test"
    staging = "staging"
    production = "production"


class Unit(str, Enum):
    percent = "percent"
    bytes = "bytes"
    seconds = "seconds"
    count = "count"


class Metric(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: float
    unit: Unit
    threshold: Optional[float] = None

    @field_validator("value", "threshold")
    @classmethod
    def finite(cls, v):
        if v is not None and not math.isfinite(v):
            raise ValueError("must be a finite number")
        return v

    @model_validator(mode="after")
    def range_checks(self):
        if self.unit == Unit.percent:
            for label, v in (("value", self.value), ("threshold", self.threshold)):
                if v is not None and not 0 <= v <= 100:
                    raise ValueError(f"{label} must be between 0 and 100 for percent metrics")
        elif self.value < 0:
            raise ValueError("non-percent metric value cannot be negative")
        return self


class Alert(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=2000)
    labels: Dict[str, str] = Field(default_factory=dict, max_length=32)
    metrics: List[Metric] = Field(min_length=1, max_length=50)


class IncidentRequest(BaseModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    source: Source
    source_event_id: str = Field(min_length=1, max_length=100)
    occurred_at: datetime
    service: str
    postgres_version: str = Field(pattern=r"^\d{1,2}(\.\d{1,2})?$")
    environment: Environment
    alert: Alert
    on_call_note: str = Field(default="", max_length=8000)

    @field_validator("occurred_at")
    @classmethod
    def tz_aware(cls, v):
        if v.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware ISO 8601")
        return v

    @field_validator("service")
    @classmethod
    def allowed_service(cls, v):
        if v != "postgresql":
            raise ValueError("service must be 'postgresql'")
        return v

    @model_validator(mode="after")
    def cross_field(self):
        major = self.postgres_version.split(".")[0]
        if major != CORPUS_MAJOR:
            raise ValueError(
                f"postgres_version major {major} does not match corpus version {CORPUS_MAJOR}"
            )
        return self


class CauseClass(str, Enum):
    saturation = "saturation"
    contention = "contention"
    configuration = "configuration"
    dependency_failure = "dependency_failure"
    data_volume = "data_volume"


class Route(str, Enum):
    self_serve = "self-serve-runbook"
    page_secondary = "page-secondary"
    incident_commander = "incident-commander"
    human_escalation = "human-escalation"
