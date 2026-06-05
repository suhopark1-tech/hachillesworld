"""Study / Report 엔드포인트."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from hachillesworld.api.schemas import (
    ReportGenerateRequest,
    StudyEnrollRequest,
    StudyEnrollResponse,
)

router = APIRouter(tags=["study"])


@router.post("/study/enroll", response_model=StudyEnrollResponse)
def study_enroll(req: StudyEnrollRequest, request: Request) -> StudyEnrollResponse:
    """HAW-STUDY-001 등록."""
    study_id = f"HAW-STUDY-{uuid.uuid4().hex[:8].upper()}"
    enrolled_at = datetime.now(UTC).isoformat()
    request.app.state.store.study_enrollments[study_id] = {
        "agent_id": req.agent_id,
        "domain": req.domain,
        "contact_email": req.contact_email,
        "enrolled_at": enrolled_at,
    }
    return StudyEnrollResponse(
        study_id=study_id,
        agent_id=req.agent_id,
        enrolled_at=enrolled_at,
        message=f"HAW-STUDY-001 등록 완료. study_id={study_id}",
    )


@router.post("/report/generate")
def generate_report(req: ReportGenerateRequest, request: Request) -> dict[str, Any]:
    """진단 보고서 생성 (HTML/PDF)."""
    history = request.app.state.store.get_has_timeseries(req.agent_id, req.from_ts, req.to_ts)
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    return {
        "report_id": report_id,
        "agent_id": req.agent_id,
        "format": req.format,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_points": len(history),
        "latest_has_score": history[-1]["has_score"] if history else None,
        "download_url": f"/v1/reports/{report_id}/download",
    }
