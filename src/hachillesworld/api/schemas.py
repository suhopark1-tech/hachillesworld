"""HAW API Pydantic v2 요청/응답 스키마."""

from __future__ import annotations

from typing import Any

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
    logs: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    episodes: list[dict[str, Any]] | None = None


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
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    predicted: dict[str, Any]
    actual: dict[str, Any]


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


# ── 그룹 스키마 ────────────────────────────────────────────────────


class GroupCreateRequest(BaseModel):
    group_id: str
    agent_ids: list[str]


class GroupDependencyRequest(BaseModel):
    from_agent: str
    to_agent: str
    weight: float = 1.0


class IndividualAgentScore(BaseModel):
    agent_name: str
    composite_score: float
    level: str
    level_label: str


class GroupHASResponse(BaseModel):
    group_id: str
    group_has: float
    n_agents: int
    weakest_link: str
    group_level: str
    simultaneous_drift_detected: bool
    dependency_risk: dict[str, float] = Field(default_factory=dict)
    individual_scores: list[IndividualAgentScore] = Field(default_factory=list)
    generated_at: str


# ── HAS 해석 스키마 (Sprint 6-A) ─────────────────────────────────────


class ActionItemSchema(BaseModel):
    priority: int
    metric: str
    current_value: float
    target_value: float
    action: str
    estimated_has_gain: float
    docs_link: str


class ComparisonContextSchema(BaseModel):
    peer_avg_score: float
    peer_count: int
    domain: str
    level: str
    percentile_rank: float


class HASInterpretationSchema(BaseModel):
    score: float
    grade: str
    grade_label: str
    percentile: float
    deployment_status: str
    top_issue: str
    next_actions: list[ActionItemSchema] = Field(default_factory=list)
    estimated_improvement: float
    comparison: ComparisonContextSchema


class InterpretRequest(BaseModel):
    report_id: str | None = None  # 없으면 최신 보고서 사용


class NextActionsResponse(BaseModel):
    agent_id: str
    actions: list[ActionItemSchema] = Field(default_factory=list)
    total_estimated_gain: float


# ── 감사 로그 스키마 (Sprint 6-B) ─────────────────────────────────────


class AuditEventSchema(BaseModel):
    event_id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    outcome: str
    ip_address: str
    request_size_bytes: int
    response_size_bytes: int
    duration_ms: float


class AuditEventsResponse(BaseModel):
    events: list[AuditEventSchema] = Field(default_factory=list)
    total: int
