"""Operate 엔드포인트 — HAS 시계열, 드리프트, 하네스, Replay."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from hachillesworld.api.schemas import (
    DriftAlertSchema,
    DriftRecordRequest,
    DriftRecordResponse,
    HarnessApproveRequest,
    HarnessPendingResponse,
    HarnessRuleSchema,
    HasDataPoint,
    HasTimeseriesResponse,
)
from hachillesworld.operate.replay import ReplayDebugger

router = APIRouter(tags=["operate"])


@router.get("/agents/{agent_id}/has", response_model=HasTimeseriesResponse)
def get_has_timeseries(
    agent_id: str,
    request: Request,
    from_ts: str | None = None,
    to_ts: str | None = None,
    interval: str | None = None,
) -> HasTimeseriesResponse:
    """에이전트 HAS 시계열 반환."""
    data = request.app.state.store.get_has_timeseries(agent_id, from_ts, to_ts)
    return HasTimeseriesResponse(
        agent_id=agent_id,
        data_points=[HasDataPoint(**p) for p in data],
        from_ts=from_ts,
        to_ts=to_ts,
    )


@router.post("/agents/{agent_id}/drift/record", response_model=DriftRecordResponse)
def record_drift(
    agent_id: str,
    req: DriftRecordRequest,
    request: Request,
) -> DriftRecordResponse:
    """드리프트 값 기록 + 임계값 초과 시 경보 반환."""
    monitor = request.app.state.store.get_or_create_drift_monitor(agent_id)
    drift_val = monitor.record(predicted=req.predicted, actual=req.actual)
    exceeded = drift_val > monitor.threshold

    alert_schema = None
    rate = monitor.recent_drift_rate()
    if exceeded and rate >= monitor.alert_rate_threshold:
        alert_schema = DriftAlertSchema(
            agent_name=agent_id,
            drift_value=round(drift_val, 4),
            threshold=monitor.threshold,
            recent_rate=round(rate, 4),
            recommended_action=(
                "즉시 재보정 필요: World Model 동기화"
                if drift_val > monitor.threshold * 2
                else "재보정 권장: 불확실성 임계값 검토"
            ),
        )
        meta = request.app.state.store.get_or_create_meta_harness(agent_id)
        meta.record_failure(
            {
                "event_type": "observe:drift",
                "payload": {"description": f"Drift {drift_val:.3f} > {monitor.threshold}"},
            }
        )

    return DriftRecordResponse(
        agent_id=agent_id,
        drift_value=round(drift_val, 4),
        exceeded_threshold=exceeded,
        alert=alert_schema,
    )


@router.get("/agents/{agent_id}/harness/pending", response_model=HarnessPendingResponse)
def get_harness_pending(agent_id: str, request: Request) -> HarnessPendingResponse:
    """승인 대기 하네스 규칙 목록."""
    meta = request.app.state.store.get_or_create_meta_harness(agent_id)
    return HarnessPendingResponse(
        agent_id=agent_id,
        rules=[
            HarnessRuleSchema(
                rule_id=r.rule_id,
                condition=r.condition,
                action=r.action,
                severity=r.severity,
                source=r.source,
            )
            for r in meta.get_pending_rules()
        ],
    )


@router.post("/harness/{rule_id}/approve")
def approve_harness_rule(
    rule_id: str,
    req: HarnessApproveRequest,
    request: Request,
) -> dict[str, Any]:
    """하네스 규칙 승인/거부."""
    for meta in request.app.state.store.meta_harnesses.values():
        if req.approved:
            if meta.approve_rule(rule_id):
                return {"rule_id": rule_id, "status": "approved"}
        elif meta.reject_rule(rule_id):
            return {"rule_id": rule_id, "status": "rejected"}
    raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")


@router.get("/agents/{agent_id}/replay/{episode_id}")
def get_replay(
    agent_id: str,
    episode_id: str,
    request: Request,
) -> dict[str, Any]:
    """에피소드 Replay + CounterfactualReport 반환."""
    events = request.app.state.store.replay_events.get(episode_id, [])
    if not events:
        return {
            "episode_id": episode_id,
            "agent_id": agent_id,
            "failure_step": -1,
            "failure_type": "none",
            "root_cause": "에피소드 이벤트 없음",
            "counterfactuals": [],
            "repair_suggestion": "",
            "confidence": 0.0,
        }
    debugger = ReplayDebugger()
    session = debugger.load(episode_id=episode_id, events=events)
    return {
        "episode_id": episode_id,
        "agent_id": agent_id,
        "failure_step": session.failure_step,
        "failure_type": "unknown",
        "root_cause": session.root_cause,
        "counterfactuals": [],
        "repair_suggestion": "",
        "confidence": 0.5 if session.anomaly_frames else 0.0,
    }
