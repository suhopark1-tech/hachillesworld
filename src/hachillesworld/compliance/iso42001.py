"""ISO/IEC 42001 AI 관리시스템 자동 체크리스트 모듈."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from hachillesworld.core.models import DiagnosticReport

# 지표 미측정 조항에 적용하는 보수적 기본 점수
_UNMEASURED_CLAUSE_SCORE: float = 40.0


@dataclass
class ISO42001Clause:
    """ISO/IEC 42001 단일 조항 체크 결과."""

    clause_id: str
    title: str
    description: str
    haw_indicators: list[str]  # 연동된 HAW 지표명
    score: float  # 0~100
    status: Literal["conformant", "partial", "non_conformant", "not_applicable"]
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class ISO42001CheckResult:
    """ISO/IEC 42001 전체 체크리스트 결과."""

    agent_name: str
    generated_at: str
    clauses: list[ISO42001Clause] = field(default_factory=list)
    overall_score: float = 0.0
    overall_status: Literal["conformant", "partial", "non_conformant"] = "partial"
    summary: str = ""

    @property
    def conformant_count(self) -> int:
        return sum(1 for c in self.clauses if c.status == "conformant")

    @property
    def non_conformant_count(self) -> int:
        return sum(1 for c in self.clauses if c.status == "non_conformant")


def _status(
    score: float,
) -> Literal["conformant", "partial", "non_conformant", "not_applicable"]:
    if score >= 80:
        return "conformant"
    if score >= 50:
        return "partial"
    return "non_conformant"


class ISO42001Checker:
    """DiagnosticReport → ISO/IEC 42001 자동 체크리스트 생성."""

    def check(self, report: DiagnosticReport) -> ISO42001CheckResult:
        """HAW 진단 리포트를 ISO/IEC 42001 주요 조항에 매핑한다."""
        has_score = report.composite_score
        clauses = [
            self._check_4_1(report, has_score),
            self._check_6_1(report),
            self._check_8_4(report),
            self._check_9_1(report, has_score),
            self._check_10_2(report),
        ]

        scored = [c for c in clauses if c.status != "not_applicable"]
        overall = sum(c.score for c in scored) / len(scored) if scored else 0.0
        if overall >= 80:
            overall_status: Literal["conformant", "partial", "non_conformant"] = "conformant"
        elif overall >= 50:
            overall_status = "partial"
        else:
            overall_status = "non_conformant"

        conformant_n = sum(1 for c in clauses if c.status == "conformant")
        summary = (
            f"ISO/IEC 42001 체크리스트: {len(clauses)}개 조항 평가, "
            f"{conformant_n}개 준수, "
            f"종합 점수 {overall:.1f}/100"
        )

        return ISO42001CheckResult(
            agent_name=report.agent_name,
            generated_at=datetime.now(UTC).isoformat(),
            clauses=clauses,
            overall_score=round(overall, 2),
            overall_status=overall_status,
            summary=summary,
        )

    def _find_metric_value(self, report: DiagnosticReport, name: str) -> float | None:
        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )
        for m in all_metrics:
            if m.name.lower() == name.lower():
                return m.value
        return None

    def _check_4_1(self, report: DiagnosticReport, has_score: float) -> ISO42001Clause:
        """4.1 조직 및 배경 이해 — AI 시스템 목적·영향·이해관계자 식별."""
        evidence: list[str] = []
        gaps: list[str] = []

        # Level 분류 존재 자체가 AI 시스템 분류 증거
        evidence.append(f"AI 에이전트 역량 레벨 분류: {report.level.value}")
        evidence.append(f"운용 도메인 식별: {report.laws_domain.value}")

        if has_score >= 60:
            evidence.append(f"HAS 종합 점수 {has_score:.1f} — 시스템 능력 정량화 완료")
        else:
            gaps.append("HAS 점수 낮음 — AI 시스템 현재 능력 범위 재검토 필요")

        score = min(100.0, 50.0 + has_score * 0.5)
        return ISO42001Clause(
            clause_id="4.1",
            title="조직 및 배경 이해",
            description="조직은 AI 관리시스템 목적과 관련된 내·외부 이슈를 파악해야 한다.",
            haw_indicators=["HAS", "Level", "LawsDomain"],
            score=round(score, 2),
            status=_status(score),
            evidence=evidence,
            gaps=gaps,
        )

    def _check_6_1(self, report: DiagnosticReport) -> ISO42001Clause:
        """6.1 리스크 및 기회 대응 계획."""
        evidence: list[str] = []
        gaps: list[str] = []

        critical_count = len(report.critical_issues)
        odr = self._find_metric_value(report, "ODR")
        sdr = self._find_metric_value(report, "SDR")

        if odr is not None:
            if odr >= 0.8:
                evidence.append(f"ODR={odr:.3f} — 분포 외 입력 리스크 탐지 체계 구비")
            else:
                gaps.append(f"ODR={odr:.3f} — OOD 탐지 미흡, 배포 리스크 증가")

        if sdr is not None:
            if sdr <= 0.05:
                evidence.append(f"SDR={sdr:.4f} — 드리프트 리스크 허용 수준")
            else:
                gaps.append(f"SDR={sdr:.4f} — 드리프트 리스크 높음, 모니터링 강화 필요")

        if critical_count == 0:
            evidence.append("즉시 조치 필요 지표 없음")
            score = 85.0
        elif critical_count <= 2:
            gaps.append(f"즉시 조치 필요 지표 {critical_count}건 존재")
            score = 60.0
        else:
            gaps.append(f"심각한 지표 {critical_count}건 — 리스크 대응 계획 즉시 수립 필요")
            score = 30.0

        return ISO42001Clause(
            clause_id="6.1",
            title="리스크 및 기회 대응 계획",
            description="조직은 AI 관련 리스크와 기회를 파악하고 대응 계획을 수립해야 한다.",
            haw_indicators=["SDR", "ODR", "critical_issues"],
            score=round(score, 2),
            status=_status(score),
            evidence=evidence,
            gaps=gaps,
        )

    def _check_8_4(self, report: DiagnosticReport) -> ISO42001Clause:
        """8.4 AI 시스템 운용 — 정확성·견고성 관리."""
        evidence: list[str] = []
        gaps: list[str] = []

        ece = self._find_metric_value(report, "ECE")
        ca = self._find_metric_value(report, "CA")
        gar = self._find_metric_value(report, "GAR")

        scores: list[float] = []

        if ece is not None:
            ece_score = max(0.0, 100.0 - ece * 500)
            scores.append(ece_score)
            if ece <= 0.05:
                evidence.append(f"ECE={ece:.4f} — 모델 보정 양호")
            else:
                gaps.append(f"ECE={ece:.4f} — 보정 개선 필요")

        if ca is not None:
            scores.append(ca * 100)
            if ca >= 0.75:
                evidence.append(f"CA={ca:.3f} — 반사실 설명력 양호")
            else:
                gaps.append(f"CA={ca:.3f} — 설명 가능성 강화 필요")

        if gar is not None:
            scores.append(gar * 100)
            if gar >= 0.8:
                evidence.append(f"GAR={gar:.3f} — 목표 달성률 양호")
            else:
                gaps.append(f"GAR={gar:.3f} — 정확성 목표 미달")

        score = (sum(scores) / len(scores)) if scores else _UNMEASURED_CLAUSE_SCORE
        return ISO42001Clause(
            clause_id="8.4",
            title="AI 시스템 운용",
            description="조직은 AI 시스템이 의도된 목적에 맞게 운용되고 성과를 내는지 관리해야 한다.",  # noqa: E501
            haw_indicators=["ECE", "CA", "GAR"],
            score=round(score, 2),
            status=_status(score),
            evidence=evidence,
            gaps=gaps,
        )

    def _check_9_1(self, report: DiagnosticReport, has_score: float) -> ISO42001Clause:
        """9.1 모니터링·측정·분석·평가."""
        evidence: list[str] = []
        gaps: list[str] = []

        irt = self._find_metric_value(report, "IRT")
        lrc = self._find_metric_value(report, "LCR")

        if irt is not None:
            if irt <= 60:
                evidence.append(f"IRT={irt:.1f}s — 사고 복구 시간 목표 이내")
            else:
                gaps.append(f"IRT={irt:.1f}s — 복구 시간 초과, 모니터링 대응력 강화 필요")

        if lrc is not None:
            if lrc >= 0.9:
                evidence.append(f"LCR={lrc:.3f} — 루프 완료율 양호")
            else:
                gaps.append(f"LCR={lrc:.3f} — 루프 완료율 낮음")

        # HAS 점수를 AI 관리시스템 정량 지표로 활용
        evidence.append(f"HAS 지수 {has_score:.1f}/100 — ISO 42001 §9.1 정량 성과 지표로 활용")

        score = min(100.0, max(30.0, has_score))
        return ISO42001Clause(
            clause_id="9.1",
            title="모니터링·측정·분석·평가",
            description="조직은 AI 관리시스템 성과를 모니터링·측정·분석·평가해야 한다.",
            haw_indicators=["HAS", "IRT", "LCR"],
            score=round(score, 2),
            status=_status(score),
            evidence=evidence,
            gaps=gaps,
        )

    def _check_10_2(self, report: DiagnosticReport) -> ISO42001Clause:
        """10.2 지속적 개선."""
        evidence: list[str] = []
        gaps: list[str] = []

        wmul = self._find_metric_value(report, "WMUL")
        rec_count = len(report.recommendations)

        if wmul is not None:
            if wmul <= 100:
                evidence.append(f"WMUL={wmul:.1f}ms — World Model 업데이트 지연 양호")
            else:
                gaps.append(f"WMUL={wmul:.1f}ms — 업데이트 지연 높음, 개선 가속 필요")

        if rec_count > 0:
            evidence.append(f"HAchillesWorld가 {rec_count}건의 개선 권장사항 자동 생성")
        else:
            evidence.append("개선 권장사항 없음 — 모든 지표 목표 달성")

        score = 75.0 if wmul is None or wmul <= 100 else 55.0
        if rec_count > 3:
            score = max(40.0, score - 15.0)

        return ISO42001Clause(
            clause_id="10.2",
            title="지속적 개선",
            description="조직은 AI 관리시스템의 적합성·충족성·효과성을 지속적으로 개선해야 한다.",
            haw_indicators=["WMUL", "recommendations"],
            score=round(score, 2),
            status=_status(score),
            evidence=evidence,
            gaps=gaps,
        )

    def to_markdown(self, result: ISO42001CheckResult) -> str:
        """체크리스트 결과를 마크다운 표로 출력."""
        lines = [
            "# ISO/IEC 42001 AI 관리시스템 체크리스트",
            "",
            f"**에이전트**: {result.agent_name}  ",
            f"**생성일시**: {result.generated_at}  ",
            f"**종합 점수**: {result.overall_score:.1f}/100 [{result.overall_status}]  ",
            f"**요약**: {result.summary}",
            "",
            "| 조항 | 제목 | 점수 | 상태 | 연동 지표 |",
            "|------|------|:----:|------|-----------|",
        ]
        status_emoji = {
            "conformant": "✅",
            "partial": "⚠️",
            "non_conformant": "❌",
            "not_applicable": "—",
        }
        for clause in result.clauses:
            emoji = status_emoji.get(clause.status, "?")
            indicators = ", ".join(clause.haw_indicators)
            lines.append(
                f"| {clause.clause_id} | {clause.title} | {clause.score:.0f} | "
                f"{emoji} {clause.status} | {indicators} |"
            )
        lines.append("")
        for clause in result.clauses:
            if clause.gaps:
                lines.append(f"## {clause.clause_id} 개선 필요 사항")
                lines.extend(f"- {gap}" for gap in clause.gaps)
                lines.append("")
        return "\n".join(lines)
