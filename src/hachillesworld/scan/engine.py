"""Scan 엔진 — 진단 실행 및 리포트 생성."""

from __future__ import annotations

from typing import Any

from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
    MetricScore,
)
from hachillesworld.scan.metrics import MetricsCalculator


class ScanEngine:
    """Levels × Laws 진단 엔진.
    로그 + 설정 → DiagnosticReport
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def run(self, logs: list[dict[str, Any]], agent_name: str) -> DiagnosticReport:
        calc = MetricsCalculator(logs=logs, config=self.config)

        # ── Category A: World Model 품질 ──────────────────────
        wm_metrics = [
            calc.prediction_error_rate(),
            calc.calibration_ece(),
            calc.simulation_drift_rate(),
            calc.uncertainty_coverage(),
            calc.planning_depth(),
        ]
        wm_score = self._category_score("World Model 품질", wm_metrics)

        # ── Category B: 에이전시 수준 ─────────────────────────
        agency_metrics = [
            calc.self_correction_capability(),
            calc.uncertainty_awareness(),
            calc.goal_consistency(),
            calc.env_adaptation_speed(),
            calc.harness_coverage(),
        ]
        agency_score = self._category_score("에이전시 수준", agency_metrics)

        # ── Category C: 운영 건전성 ───────────────────────────
        ops_metrics = [
            calc.recalibration_frequency(),
            calc.cost_efficiency(),
            calc.hitl_trigger_rate(),
            calc.harness_violation_rate(),
            calc.checkpoint_recovery_rate(),
        ]
        ops_score = self._category_score("운영 건전성", ops_metrics)

        # ── Level 및 Laws 도메인 판정 ─────────────────────────
        level, progress = self._classify_level(wm_metrics, agency_metrics)
        laws_domain = self._classify_laws(self.config)

        # ── 권장 사항 생성 ─────────────────────────────────────
        all_metrics = wm_metrics + agency_metrics + ops_metrics
        recommendations = self._generate_recommendations(all_metrics, level, laws_domain)

        return DiagnosticReport(
            agent_name=agent_name,
            level=level,
            level_progress=progress,
            laws_domain=laws_domain,
            world_model_quality=wm_score,
            agency_level=agency_score,
            operational_health=ops_score,
            recommendations=recommendations,
            metadata={
                "total_log_events": len(logs),
                "config_keys": list(self.config.keys()),
            },
        )

    # ── 내부 메서드 ────────────────────────────────────────────

    def _category_score(self, name: str, metrics: list[MetricScore]) -> CategoryScore:
        """지표 목록을 0~100 점수로 변환."""
        if not metrics:
            return CategoryScore(name=name, score=0.0)

        ok_weight = 1.0
        warning_weight = 0.5
        critical_weight = 0.0

        total = sum(
            ok_weight
            if m.status == "ok"
            else warning_weight
            if m.status == "warning"
            else critical_weight
            for m in metrics
        )
        score = (total / len(metrics)) * 100
        return CategoryScore(name=name, score=round(score, 1), metrics=metrics)

    def _classify_level(
        self,
        wm_metrics: list[MetricScore],
        agency_metrics: list[MetricScore],
    ) -> tuple[Level, float]:
        """지표 기반 Level 자동 판정."""
        planning_depth = next((m.value for m in wm_metrics if m.name == "Planning Depth"), 1.0)
        self_correction = next(
            (m.value for m in agency_metrics if m.name == "Self-Correction Rate"),
            0.0,
        )
        uncertainty_ok = next(
            (m.value for m in agency_metrics if m.name == "Uncertainty Awareness"),
            0.0,
        )

        if self_correction >= 0.30 and planning_depth >= 20:
            level = Level.L3
            progress = min(1.0, self_correction / 0.50)
        elif planning_depth >= 5 or uncertainty_ok >= 1.0:
            level = Level.L2
            progress = min(1.0, (planning_depth - 5) / 45) if planning_depth >= 5 else 0.1
        else:
            level = Level.L1
            progress = min(1.0, planning_depth / 5)

        return level, round(progress, 2)

    def _classify_laws(self, config: dict[str, Any]) -> LawsDomain:
        """설정 기반 Laws 도메인 자동 판정."""
        domain = config.get("laws_domain", "").lower()
        mapping = {
            "physical": LawsDomain.PHYSICAL,
            "robot": LawsDomain.PHYSICAL,
            "digital": LawsDomain.DIGITAL,
            "api": LawsDomain.DIGITAL,
            "social": LawsDomain.SOCIAL,
            "multi": LawsDomain.SOCIAL,
            "science": LawsDomain.SCIENTIFIC,
            "research": LawsDomain.SCIENTIFIC,
        }
        for key, val in mapping.items():
            if key in domain:
                return val
        return LawsDomain.DIGITAL  # 기본값

    def _generate_recommendations(
        self,
        metrics: list[MetricScore],
        level: Level,
        domain: LawsDomain,
    ) -> list[str]:
        """임계값 위반 지표 기반 권장 사항 생성."""
        recs: list[str] = []
        for m in metrics:
            if m.status == "critical":
                recs.append(f"[즉시] {m.name}: {m.description}")
            elif m.status == "warning":
                recs.append(f"[단기] {m.name}: {m.description}")

        if level == Level.L1:
            recs.append("[로드맵] L2 진입: 앙상블 역학 모델 + MCTS 계획기 구현 권장")
        elif level == Level.L2:
            recs.append("[로드맵] L3 준비: 자기 수정 루프 + Meta-Harness 설계 권장")

        return recs
