"""HAW API Pydantic v2 요청/응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricScoreSchema(BaseModel):
    name: str
    value: float
    threshold: float
    unit: str = ""
    status: str = "ok"
    description: str = ""


class CategoryScoreSchema(BaseModel):
    name: str
    score: float
    metrics: list[MetricScoreSchema] = Field(default_factory=list)


class ScanRequest(BaseModel):
    agent_name: str
    logs: list[dict] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    episodes: list[dict] | None = None


class ScanResponse(BaseModel):
    agent_name: str
    level: str
    level_label: str
    laws_domain: str
    composite_score: float
    world_model_quality: CategoryScoreSchema
    agency_level: CategoryScoreSchema
    operational_health: CategoryScoreSchema
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class HasDataPoint(BaseModel):
    timestamp: str
    has_score: float
    level: str


class HasTimeseriesResponse(BaseModel):
    agent_id: str
    data_points: list[HasDataPoint] = Field(default_factory=list)
    from_ts: str | None = None
    to_ts: str | None = None


class DriftRecordRequest(BaseModel):
    predicted: dict
    actual: dict


class DriftAlertSchema(BaseModel):
    agent_name: str
    drift_value: float
    threshold: float
    recent_rate: float
    recommended_action: str


class DriftRecordResponse(BaseModel):
    agent_id: str
    drift_value: float
    exceeded_threshold: bool
    alert: DriftAlertSchema | None = None


class HarnessRuleSchema(BaseModel):
    rule_id: str
    condition: str
    action: str
    severity: str
    source: str


class HarnessPendingResponse(BaseModel):
    agent_id: str
    rules: list[HarnessRuleSchema] = Field(default_factory=list)


class HarnessApproveRequest(BaseModel):
    approved: bool = True


class StudyEnrollRequest(BaseModel):
    agent_id: str
    domain: str
    contact_email: str | None = None


class StudyEnrollResponse(BaseModel):
    study_id: str
    agent_id: str
    enrolled_at: str
    message: str


class ReportGenerateRequest(BaseModel):
    agent_id: str
    format: str = "html"
    from_ts: str | None = None
    to_ts: str | None = None
