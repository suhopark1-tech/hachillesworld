"""스캔 엔드포인트 — POST /v1/scan + HAS 해석."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from hachillesworld.api.schemas import (
    ActionItemSchema,
    CategoryScoreSchema,
    ComparisonContextSchema,
    HASInterpretationSchema,
    InterpretRequest,
    MetricScoreSchema,
    NextActionsResponse,
    ScanRequest,
    ScanResponse,
)
from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.core.models import CategoryScore
from hachillesworld.interpret.has_interpreter import ActionItem, HASInterpretation, HASInterpreter
from hachillesworld.scan.engine import ScanEngine

router = APIRouter(tags=["scan"])


def _cat(cat: CategoryScore) -> CategoryScoreSchema:
    return CategoryScoreSchema(
        name=cat.name,
        score=cat.score,
        metrics=[
            MetricScoreSchema(
                name=m.name,
                value=m.value,
                threshold=m.threshold,
                unit=m.unit,
                status=m.status,
                description=m.description,
            )
            for m in cat.metrics
        ],
    )


@router.post("/scan", response_model=ScanResponse)
def scan_episode(req: ScanRequest, request: Request) -> ScanResponse:
    """에피소드 로그 제출 → DiagnosticReport 반환."""
    episodes = [EpisodeRecord.from_dict(e) for e in req.episodes] if req.episodes else None
    engine = ScanEngine(config=req.config)
    report = engine.run(logs=req.logs, agent_name=req.agent_name, episodes=episodes)
    request.app.state.store.record_has(req.agent_name, report)
    return ScanResponse(
        agent_name=report.agent_name,
        level=report.level.value,
        level_label=report.level_label,
        laws_domain=report.laws_domain.value,
        composite_score=round(report.composite_score, 2),
        world_model_quality=_cat(report.world_model_quality),
        agency_level=_cat(report.agency_level),
        operational_health=_cat(report.operational_health),
        recommendations=report.recommendations,
        metadata=report.metadata,
    )


def _action_schema(a: ActionItem) -> ActionItemSchema:
    return ActionItemSchema(
        priority=a.priority,
        metric=a.metric,
        current_value=a.current_value,
        target_value=a.target_value,
        action=a.action,
        estimated_has_gain=a.estimated_has_gain,
        docs_link=a.docs_link,
    )


def _interp_schema(interp: HASInterpretation) -> HASInterpretationSchema:
    return HASInterpretationSchema(
        score=round(interp.score, 2),
        grade=interp.grade,
        grade_label=interp.grade_label,
        percentile=interp.percentile,
        deployment_status=interp.deployment_status,
        top_issue=interp.top_issue,
        next_actions=[_action_schema(a) for a in interp.next_actions],
        estimated_improvement=round(interp.estimated_improvement, 2),
        comparison=ComparisonContextSchema(
            peer_avg_score=interp.comparison.peer_avg_score,
            peer_count=interp.comparison.peer_count,
            domain=interp.comparison.domain,
            level=interp.comparison.level,
            percentile_rank=interp.comparison.percentile_rank,
        ),
    )


@router.post("/agents/{agent_id}/interpret", response_model=HASInterpretationSchema)
def interpret_agent(
    agent_id: str,
    body: InterpretRequest,
    request: Request,
) -> HASInterpretationSchema:
    """최신 DiagnosticReport를 HAS 해석 결과로 변환한다."""
    report = request.app.state.store.get_latest_report(agent_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"에이전트 '{agent_id}'의 진단 보고서가 없습니다."
            " 먼저 POST /v1/scan을 호출하세요.",
        )
    interp = HASInterpreter().interpret(report)
    return _interp_schema(interp)


@router.get("/agents/{agent_id}/next-actions", response_model=NextActionsResponse)
def get_next_actions(agent_id: str, request: Request) -> NextActionsResponse:
    """에이전트의 우선순위별 즉시 실행 가능한 액션 아이템 목록을 반환한다."""
    report = request.app.state.store.get_latest_report(agent_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"에이전트 '{agent_id}'의 진단 보고서가 없습니다."
            " 먼저 POST /v1/scan을 호출하세요.",
        )
    interp = HASInterpreter().interpret(report)
    return NextActionsResponse(
        agent_id=agent_id,
        actions=[_action_schema(a) for a in interp.next_actions],
        total_estimated_gain=round(interp.estimated_improvement, 2),
    )
