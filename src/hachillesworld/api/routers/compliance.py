"""컴플라이언스 엔드포인트 — POST /v1/report/compliance, /v1/report/iso42001."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from hachillesworld.compliance.eu_ai_act import EUAIActMapper
from hachillesworld.compliance.iso42001 import ISO42001Checker

router = APIRouter(tags=["compliance"])


class ComplianceReportRequest(BaseModel):
    agent_id: str
    format: str = Field(default="html", pattern="^(html|text)$")


class EUAIActArticleSchema(BaseModel):
    article: str
    title: str
    compliance_score: float
    status: str
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    mapped_metric_names: list[str] = Field(default_factory=list)


class EUAIActReportResponse(BaseModel):
    agent_name: str
    generated_at: str
    overall_compliance_score: float
    overall_status: str
    articles: list[EUAIActArticleSchema] = Field(default_factory=list)
    html_report: str = ""


class ISO42001ClauseSchema(BaseModel):
    clause_id: str
    title: str
    score: float
    status: str
    haw_indicators: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ISO42001CheckResponse(BaseModel):
    agent_name: str
    generated_at: str
    overall_score: float
    overall_status: str
    summary: str
    clauses: list[ISO42001ClauseSchema] = Field(default_factory=list)
    markdown_report: str = ""


@router.post("/report/compliance", response_model=EUAIActReportResponse)
def generate_eu_act_report(
    req: ComplianceReportRequest, request: Request
) -> EUAIActReportResponse:
    """EU AI Act Art.13~15 매핑 보고서 1-click 생성."""
    report = request.app.state.store.get_latest_report(req.agent_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"에이전트 '{req.agent_id}' 진단 리포트가 없습니다. 먼저 /v1/scan을 실행하세요.",
        )

    mapper = EUAIActMapper()
    eu_report = mapper.map_to_articles(report)
    html_body = mapper.generate_compliance_report(report, format=req.format)

    articles = [
        EUAIActArticleSchema(
            article=art.article,
            title=art.title,
            compliance_score=art.compliance_score,
            status=art.status,
            findings=art.findings,
            recommendations=art.recommendations,
            mapped_metric_names=[m.name for m in art.mapped_metrics],
        )
        for art in eu_report.articles
    ]
    return EUAIActReportResponse(
        agent_name=eu_report.agent_name,
        generated_at=eu_report.generated_at,
        overall_compliance_score=eu_report.overall_compliance_score,
        overall_status=eu_report.overall_status,
        articles=articles,
        html_report=html_body,
    )


@router.post("/report/iso42001", response_model=ISO42001CheckResponse)
def generate_iso42001_checklist(
    req: ComplianceReportRequest, request: Request
) -> ISO42001CheckResponse:
    """ISO/IEC 42001 AI 관리시스템 체크리스트 자동 생성."""
    report = request.app.state.store.get_latest_report(req.agent_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"에이전트 '{req.agent_id}' 진단 리포트가 없습니다. 먼저 /v1/scan을 실행하세요.",
        )

    checker = ISO42001Checker()
    result = checker.check(report)
    md = checker.to_markdown(result)

    clauses = [
        ISO42001ClauseSchema(
            clause_id=c.clause_id,
            title=c.title,
            score=c.score,
            status=c.status,
            haw_indicators=c.haw_indicators,
            evidence=c.evidence,
            gaps=c.gaps,
        )
        for c in result.clauses
    ]
    return ISO42001CheckResponse(
        agent_name=result.agent_name,
        generated_at=result.generated_at,
        overall_score=result.overall_score,
        overall_status=result.overall_status,
        summary=result.summary,
        clauses=clauses,
        markdown_report=md,
    )
