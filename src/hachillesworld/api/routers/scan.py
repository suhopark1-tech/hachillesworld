"""스캔 엔드포인트 — POST /v1/scan."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hachillesworld.api.schemas import (
    CategoryScoreSchema,
    MetricScoreSchema,
    ScanRequest,
    ScanResponse,
)
from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.core.models import CategoryScore
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
