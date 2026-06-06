"""EU AI Act 관련 지표 모니터링 모듈.

Art.13 투명성, Art.14 인간 감독, Art.15 정확성·견고성과 관련된
HAchillesWorld 진단 지표를 연계하여 모니터링 참고 보고서를 생성한다.

중요 고지:
    본 모듈의 출력물은 법적 컴플라이언스 인증이 아니며, 전문 법률 검토를
    대체하지 않습니다. EU AI Act 준수 여부의 최종 판단은 공인된 적합성
    평가 기관(Notified Body) 및 자격을 갖춘 법률 전문가의 검토가 필요합니다.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from hachillesworld.core.models import DiagnosticReport, MetricScore


@dataclass
class ArticleMapping:
    """단일 EU AI Act 조항과 연계된 HAW 지표 모니터링 결과."""

    article: str
    title: str
    description: str
    mapped_metrics: list[MetricScore] = field(default_factory=list)
    compliance_score: float = 0.0  # 0~100
    status: Literal["compliant", "partial", "non_compliant", "not_assessed"] = "not_assessed"
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EUAIActReport:
    """EU AI Act 관련 HAW 지표 모니터링 보고서 (참고 자료)."""

    agent_name: str
    generated_at: str
    article_13: ArticleMapping
    article_14: ArticleMapping
    article_15: ArticleMapping
    overall_compliance_score: float = 0.0
    overall_status: Literal["compliant", "partial", "non_compliant"] = "partial"

    @property
    def articles(self) -> list[ArticleMapping]:
        return [self.article_13, self.article_14, self.article_15]


_THRESHOLDS = {
    "transparency": 80.0,
    "human_oversight": 75.0,
    "accuracy": 70.0,
}


def _score_to_status(
    score: float, threshold: float
) -> Literal["compliant", "partial", "non_compliant", "not_assessed"]:
    if score >= threshold:
        return "compliant"
    if score >= threshold * 0.6:
        return "partial"
    return "non_compliant"


class EUAIActMapper:
    """HAW 진단 지표를 EU AI Act Art.13~15와 연계하는 모니터링 보고서 생성기.

    참고: 본 클래스의 출력은 법적 컴플라이언스 인증이 아닌 모니터링 참고 자료입니다.
    """

    def map_to_articles(self, report: DiagnosticReport) -> EUAIActReport:
        """HAW 진단 지표를 EU AI Act 조항별로 연계하여 모니터링 참고 보고서를 반환한다."""
        art13 = self._map_art13(report)
        art14 = self._map_art14(report)
        art15 = self._map_art15(report)

        overall = (art13.compliance_score + art14.compliance_score + art15.compliance_score) / 3.0
        if overall >= 80:
            overall_status: Literal["compliant", "partial", "non_compliant"] = "compliant"
        elif overall >= 50:
            overall_status = "partial"
        else:
            overall_status = "non_compliant"

        return EUAIActReport(
            agent_name=report.agent_name,
            generated_at=datetime.now(timezone.utc).isoformat(),
            article_13=art13,
            article_14=art14,
            article_15=art15,
            overall_compliance_score=round(overall, 2),
            overall_status=overall_status,
        )

    def _find_metric(self, report: DiagnosticReport, name: str) -> MetricScore | None:
        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )
        for m in all_metrics:
            if m.name.lower() == name.lower():
                return m
        return None

    def _map_art13(self, report: DiagnosticReport) -> ArticleMapping:
        """Art.13 — 투명성 및 정보 제공 의무."""
        ece = self._find_metric(report, "ECE")
        ca = self._find_metric(report, "CA")
        mapped = [m for m in [ece, ca] if m is not None]

        scores: list[float] = []
        findings: list[str] = []
        recommendations: list[str] = []

        if ece:
            # ECE가 낮을수록 보정이 잘 됨 (0이 최선) → 투명성 점수로 변환
            ece_score = max(0.0, 100.0 - ece.value * 500)
            scores.append(ece_score)
            if ece.status == "critical":
                findings.append(f"ECE={ece.value:.4f}: 모델 보정 불량으로 예측 신뢰도 투명성 훼손")
                recommendations.append("보정(calibration) 재훈련 또는 Temperature Scaling 적용 권장")
            elif ece.status == "warning":
                findings.append(f"ECE={ece.value:.4f}: 보정 상태 경계 수준")
        else:
            findings.append("ECE 미측정 — Art.13 완전 준수 확인 불가")
            recommendations.append("ECE 측정 파이프라인 구축 필요")

        if ca:
            ca_score = ca.value * 100
            scores.append(ca_score)
            if ca.status == "critical":
                findings.append(f"CA={ca.value:.3f}: 반사실 설명력 부족 (Art.13 투명성 위험)")
                recommendations.append("LLM-as-Judge 반사실 분석 강화 및 설명 가능성 향상 필요")
        else:
            findings.append("CA(반사실 정확도) 미측정 — 설명 가능성 증거 부족")

        compliance_score = (sum(scores) / len(scores)) if scores else 40.0
        compliance_score = round(compliance_score, 2)

        return ArticleMapping(
            article="Art.13",
            title="투명성 및 정보 제공 의무",
            description=(
                "고위험 AI 시스템은 배포 전 충분한 투명성을 갖춰야 하며, "
                "사용자가 AI 출력을 적절히 해석할 수 있도록 정보를 제공해야 한다."
            ),
            mapped_metrics=mapped,
            compliance_score=compliance_score,
            status=_score_to_status(compliance_score, _THRESHOLDS["transparency"]),
            findings=findings,
            recommendations=recommendations,
        )

    def _map_art14(self, report: DiagnosticReport) -> ArticleMapping:
        """Art.14 — 인간 감독."""
        irt = self._find_metric(report, "IRT")
        hc = self._find_metric(report, "HC")
        mapped = [m for m in [irt, hc] if m is not None]

        scores: list[float] = []
        findings: list[str] = []
        recommendations: list[str] = []

        if irt:
            # IRT는 낮을수록 좋음 (초 단위) — 임계값 기준 변환
            irt_score = max(0.0, 100.0 - (irt.value / irt.threshold) * 50)
            scores.append(irt_score)
            if irt.status == "critical":
                findings.append(
                    f"IRT={irt.value:.1f}s: 사고 복구 시간 초과 → 인간 감독 개입 지연 위험"
                )
                recommendations.append("자동 에스컬레이션 트리거 및 인간 개입 절차(HITL) 강화 필요")
            elif irt.status == "warning":
                findings.append(f"IRT={irt.value:.1f}s: 복구 시간 경계")
        else:
            findings.append("IRT 미측정 — Art.14 인간 감독 검증 불가")
            recommendations.append("IRT 추적 모듈 활성화 필요")

        if hc:
            hc_score = hc.value * 100
            scores.append(hc_score)
            if hc.status == "critical":
                findings.append(f"HC={hc.value:.3f}: 인간 제어율 임계 미달")
                recommendations.append("HITL 검사 빈도 증가 및 자동 중단 임계값 재설정")
        else:
            findings.append("HC(Human Control Rate) 미측정")

        compliance_score = (sum(scores) / len(scores)) if scores else 40.0
        compliance_score = round(compliance_score, 2)

        return ArticleMapping(
            article="Art.14",
            title="인간 감독",
            description=(
                "고위험 AI 시스템은 자연인이 효과적으로 감독할 수 있도록 설계·개발되어야 하며, "
                "필요 시 개입·중단·재지시가 가능해야 한다."
            ),
            mapped_metrics=mapped,
            compliance_score=compliance_score,
            status=_score_to_status(compliance_score, _THRESHOLDS["human_oversight"]),
            findings=findings,
            recommendations=recommendations,
        )

    def _map_art15(self, report: DiagnosticReport) -> ArticleMapping:
        """Art.15 — 정확성·견고성·사이버보안."""
        sdr = self._find_metric(report, "SDR")
        odr = self._find_metric(report, "ODR")
        gar = self._find_metric(report, "GAR")
        mapped = [m for m in [sdr, odr, gar] if m is not None]

        scores: list[float] = []
        findings: list[str] = []
        recommendations: list[str] = []

        if sdr:
            # SDR은 낮을수록 좋음
            sdr_score = max(0.0, 100.0 - sdr.value * 400)
            scores.append(sdr_score)
            if sdr.status == "critical":
                findings.append(f"SDR={sdr.value:.4f}: 시뮬레이션 드리프트 심각 → 견고성 위험")
                recommendations.append("드리프트 원인 분석(DriftCausalClassifier) 후 재보정 실행")
            elif sdr.status == "warning":
                findings.append(f"SDR={sdr.value:.4f}: 드리프트 경계 수준")
        else:
            findings.append("SDR 미측정 — 견고성 검증 불완전")

        if odr:
            odr_score = odr.value * 100
            scores.append(odr_score)
            if odr.status == "critical":
                findings.append(f"ODR={odr.value:.3f}: OOD 탐지율 낮음 → 분포 외 입력 대응 취약")
                recommendations.append("OOD 탐지 모델 재훈련 또는 에너지 점수 임계값 재조정")
        else:
            findings.append("ODR 미측정")

        if gar:
            gar_score = gar.value * 100
            scores.append(gar_score)
            if gar.status == "critical":
                findings.append(f"GAR={gar.value:.3f}: 목표 달성률 임계 미달 → 정확성 부족")
        else:
            findings.append("GAR(목표 달성률) 미측정")

        compliance_score = (sum(scores) / len(scores)) if scores else 40.0
        compliance_score = round(compliance_score, 2)

        return ArticleMapping(
            article="Art.15",
            title="정확성·견고성·사이버보안",
            description=(
                "고위험 AI 시스템은 적절한 수준의 정확성, 견고성, 사이버보안을 달성해야 하며, "
                "오류·결함·불일치에 대해 복원력 있게 동작해야 한다."
            ),
            mapped_metrics=mapped,
            compliance_score=compliance_score,
            status=_score_to_status(compliance_score, _THRESHOLDS["accuracy"]),
            findings=findings,
            recommendations=recommendations,
        )

    def generate_compliance_report(
        self, report: DiagnosticReport, format: str = "html"
    ) -> str:
        """EU AI Act 관련 지표 모니터링 참고 보고서 생성 (HTML 또는 텍스트).

        반환값은 참고 자료이며 법적 컴플라이언스 인증 효력이 없습니다.
        """
        eu_report = self.map_to_articles(report)
        if format == "html":
            return self._render_html(eu_report)
        return self._render_text(eu_report)

    def _status_badge(self, status: str) -> str:
        colors = {
            "compliant": ("#22c55e", "준수"),
            "partial": ("#f59e0b", "부분준수"),
            "non_compliant": ("#ef4444", "미준수"),
            "not_assessed": ("#94a3b8", "미평가"),
        }
        color, label = colors.get(status, ("#94a3b8", status))
        return (
            f'<span style="background:{color};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:0.8em">{label}</span>'
        )

    def _render_html(self, eu_report: EUAIActReport) -> str:
        parts: list[str] = []
        parts.append(
            f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>EU AI Act 지표 모니터링 참고 보고서 — {html.escape(eu_report.agent_name)}</title>
<style>
  body{{font-family:'Segoe UI',sans-serif;max-width:900px;margin:40px auto;
        color:#1e293b;line-height:1.6}}
  h1{{color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:8px}}
  h2{{color:#1e40af;margin-top:32px}}
  .summary-box{{background:#f1f5f9;border-left:4px solid #1e40af;
               padding:16px;border-radius:4px;margin:16px 0}}
  .article{{border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin:16px 0}}
  .metric-chip{{display:inline-block;background:#e0e7ff;color:#3730a3;
               padding:2px 8px;border-radius:12px;margin:2px;font-size:0.85em}}
  .finding{{color:#7c2d12;margin:4px 0}}
  .rec{{color:#14532d;margin:4px 0}}
  .score-bar{{background:#e2e8f0;border-radius:4px;height:12px;margin:8px 0}}
  .score-fill{{height:12px;border-radius:4px;background:#1e40af}}
  footer{{color:#94a3b8;font-size:0.8em;margin-top:40px;border-top:1px solid #e2e8f0;
          padding-top:16px}}
  .legal-notice{{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;
                 border-radius:4px;margin-bottom:24px;font-size:0.9em}}
</style>
</head>
<body>
<div class="legal-notice">
  <strong>&#9888; 법적 고지 — 참고 자료 안내</strong><br>
  본 보고서는 HAchillesWorld SDK가 측정한 AI 에이전트 지표를 EU AI Act 조항과
  연계하여 제시한 <strong>모니터링 참고 자료</strong>입니다.
  실제 EU AI Act 법적 준수 여부 확인은 공인된 적합성 평가 기관(Notified Body) 및
  자격을 갖춘 법률 전문가의 검토가 필요합니다.
  <strong>본 보고서는 어떠한 법적 효력도 없으며 특정 결과를 보증하지 않습니다.</strong>
</div>
<h1>EU AI Act 지표 모니터링 참고 보고서</h1>
<div class="summary-box">
  <strong>에이전트:</strong> {html.escape(eu_report.agent_name)}<br>
  <strong>생성일시:</strong> {eu_report.generated_at}<br>
  <strong>종합 모니터링 점수:</strong> {eu_report.overall_compliance_score:.1f}/100
  &nbsp;{self._status_badge(eu_report.overall_status)}<br>
  <strong>HAchillesWorld SDK</strong> 자동 생성 (참고 자료)
</div>
"""
        )

        for art in eu_report.articles:
            fill_width = int(art.compliance_score)
            metrics_html = " ".join(
                f'<span class="metric-chip">{html.escape(m.name)}={m.value:.4f}</span>'
                for m in art.mapped_metrics
            )
            findings_html = "".join(
                f'<div class="finding">⚠ {html.escape(f)}</div>'
                for f in art.findings
            )
            recs_html = "".join(
                f'<div class="rec">→ {html.escape(r)}</div>'
                for r in art.recommendations
            )
            parts.append(
                f"""<div class="article">
<h2>{html.escape(art.article)} — {html.escape(art.title)}</h2>
<p>{html.escape(art.description)}</p>
<p><strong>모니터링 점수:</strong> {art.compliance_score:.1f}/100 &nbsp;{self._status_badge(art.status)}</p>
<div class="score-bar"><div class="score-fill" style="width:{fill_width}%"></div></div>
<p><strong>매핑 지표:</strong> {metrics_html if metrics_html else "없음"}</p>
<p><strong>주요 발견사항:</strong></p>{findings_html}
<p><strong>권장 조치:</strong></p>{recs_html}
</div>
"""
            )

        parts.append(
            """<footer>
본 보고서는 HAchillesWorld SDK EUAIActMapper가 자동 생성한 <strong>모니터링 참고 자료</strong>입니다.<br>
EU AI Act 법적 준수 여부의 최종 판단은 공인된 적합성 평가 기관 및 법률 전문가 검토가 필요합니다.<br>
본 보고서를 규제 기관 제출용 법적 증거 자료로 단독 사용하지 마십시오.
</footer>
</body></html>"""
        )
        return "\n".join(parts)

    def _render_text(self, eu_report: EUAIActReport) -> str:
        lines = [
            "=" * 60,
            "[참고 자료] EU AI Act 지표 모니터링 보고서",
            "경고: 본 보고서는 법적 컴플라이언스 인증이 아닙니다.",
            "=" * 60,
            f"에이전트: {eu_report.agent_name}",
            f"생성일시: {eu_report.generated_at}",
            f"종합 모니터링 점수: {eu_report.overall_compliance_score:.1f}/100 [{eu_report.overall_status}]",
            "=" * 60,
        ]
        for art in eu_report.articles:
            lines += [
                "",
                f"[{art.article}] {art.title}",
                f"준수 점수: {art.compliance_score:.1f}/100 [{art.status}]",
                f"매핑 지표: {', '.join(m.name for m in art.mapped_metrics) or '없음'}",
            ]
            for f in art.findings:
                lines.append(f"  ⚠ {f}")
            for r in art.recommendations:
                lines.append(f"  → {r}")
        return "\n".join(lines)
