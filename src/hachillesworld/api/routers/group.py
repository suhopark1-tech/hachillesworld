# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""그룹 엔드포인트 — 다중 에이전트 HAS 집계 및 의존성 관리."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from hachillesworld.api.schemas import (
    GroupCreateRequest,
    GroupDependencyRequest,
    GroupHASResponse,
    IndividualAgentScore,
)
from hachillesworld.optimize.multi_agent import MultiAgentOrchestrator

router = APIRouter(tags=["group"])


@router.post("/groups", status_code=201)
def create_group(req: GroupCreateRequest, request: Request) -> dict[str, str]:
    """에이전트 그룹 생성 또는 갱신."""
    if not req.agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids는 1개 이상이어야 합니다")
    request.app.state.store.groups[req.group_id] = req.agent_ids
    return {
        "group_id": req.group_id,
        "n_agents": str(len(req.agent_ids)),
        "message": f"그룹 '{req.group_id}' 생성/갱신 완료",
    }


@router.post("/groups/{group_id}/dependencies", status_code=201)
def add_group_dependency(
    group_id: str,
    req: GroupDependencyRequest,
    request: Request,
) -> dict[str, str]:
    """그룹 내 에이전트 의존성 엣지 추가.

    사이클이 생기는 경우 409 Conflict를 반환한다.
    """
    graph = request.app.state.store.get_or_create_group_graph(group_id)
    try:
        graph.add_dependency(req.from_agent, req.to_agent, req.weight)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "group_id": group_id,
        "from_agent": req.from_agent,
        "to_agent": req.to_agent,
        "weight": str(req.weight),
        "message": "의존성 추가 완료",
    }


@router.get("/groups/{group_id}/has", response_model=GroupHASResponse)
def get_group_has(group_id: str, request: Request) -> GroupHASResponse:
    """그룹 HAS 집계 보고서 반환.

    그룹에 속한 에이전트의 최신 DiagnosticReport를 집계한다.
    아직 스캔 데이터가 없는 에이전트는 제외된다.
    """
    store = request.app.state.store

    # 그룹 정의 조회
    agent_ids = store.groups.get(group_id)
    if not agent_ids:
        raise HTTPException(status_code=404, detail=f"그룹 '{group_id}'을(를) 찾을 수 없습니다")

    # 최신 보고서 수집
    reports = [r for aid in agent_ids if (r := store.get_latest_report(aid)) is not None]
    if not reports:
        raise HTTPException(
            status_code=404,
            detail="그룹 내 에이전트의 스캔 데이터가 없습니다. POST /v1/scan으로 먼저 스캔하세요.",
        )

    # 의존성 그래프 + 오케스트레이터
    graph = store.group_graphs.get(group_id)
    orch = MultiAgentOrchestrator(dependency_graph=graph)
    group_report = orch.aggregate_has(reports)

    return GroupHASResponse(
        group_id=group_id,
        group_has=group_report.group_has,
        n_agents=group_report.n_agents,
        weakest_link=group_report.weakest_link,
        group_level=group_report.group_level,
        simultaneous_drift_detected=group_report.simultaneous_drift_detected,
        dependency_risk=group_report.dependency_risk,
        individual_scores=[
            IndividualAgentScore(
                agent_name=r.agent_name,
                composite_score=round(r.composite_score, 2),
                level=r.level.value,
                level_label=r.level_label,
            )
            for r in sorted(reports, key=lambda r: r.composite_score)
        ],
        generated_at=group_report.generated_at,
    )


@router.get("/groups", tags=["group"])
def list_groups(request: Request) -> dict[str, list[str]]:
    """등록된 그룹 목록 반환."""
    return dict(request.app.state.store.groups)
