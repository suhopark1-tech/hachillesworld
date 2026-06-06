"""진단 지표 15개 계산 로직."""

from __future__ import annotations

from typing import Any

import numpy as np

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.core.models import MetricScore
from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator
from hachillesworld.scan.incident_tracker import IncidentTracker
from hachillesworld.scan.ood_detector import OODDetector
from hachillesworld.scan.wmul_tracker import WMULTracker

# ── 측정 불가 지표 처리 정책 ─────────────────────────────────────────
# "exclude": HAS 계산에서 해당 지표 제외 (분모 조정)
# "neutral": 카테고리 중간값(50.0)으로 대체
# "penalty": 보수적 하한(25.0)으로 대체
NOT_MEASURED_POLICY: str = "exclude"

# ── SDK v1.1: 15개 지표 100% 자동화 완성 ─────────────────────────────────
# WMQ (A): PA, ECE, SDR, ODR, PD
# ALM (B): SCR, CA, GAR, AS, HC
# OHM (C): WMUL, IRT, HITL, HR, SU
# 수동 입력 필요 항목 0개


class MetricsCalculator:
    """로그와 설정으로부터 15개 진단 지표를 계산한다.

    Category A (5개): World Model 품질
    Category B (5개): 에이전시 수준
    Category C (5개): 운영 건전성
    """

    def __init__(
        self,
        logs: list[dict[str, Any]],
        config: dict[str, Any],
        *,
        episodes: list[EpisodeRecord] | None = None,
        ca_evaluator: CounterfactualEvaluator | None = None,
    ) -> None:
        self.logs = logs
        self.config = config
        self.episodes: list[EpisodeRecord] = episodes or []
        self.ca_evaluator = ca_evaluator

    # ── Category A: World Model 품질 ──────────────────────────

    def prediction_error_rate(self) -> MetricScore:
        """예측-현실 괴리 평균 (낮을수록 좋음, 기준: < 0.15)."""
        errors = [
            e["payload"].get("prediction_error", 0.0)
            for e in self.logs
            if e.get("event_type") == "observe" and "prediction_error" in e.get("payload", {})
        ]
        value = float(np.mean(errors)) if errors else 0.0
        return MetricScore(
            name="Prediction Error Rate",
            value=round(value, 4),
            threshold=0.15,
            status="ok" if value < 0.15 else "warning" if value < 0.30 else "critical",
            description="World Model 예측-현실 괴리 평균. 0.15 미만이 목표.",
        )

    def calibration_ece(self) -> MetricScore:
        """Expected Calibration Error (낮을수록 좋음, 기준: < 0.10)."""
        confidences = [
            e["payload"].get("confidence", 0.5) for e in self.logs if e.get("event_type") == "plan"
        ]
        actuals = [
            1.0 if e["payload"].get("goal_achieved") else 0.0
            for e in self.logs
            if e.get("event_type") == "observe"
        ]
        ece = self._compute_ece(confidences, actuals)
        return MetricScore(
            name="Calibration ECE",
            value=round(ece, 4),
            threshold=0.10,
            status="ok" if ece < 0.10 else "warning" if ece < 0.20 else "critical",
            description="모델 신뢰도와 실제 정확도의 일치 정도.",
        )

    def simulation_drift_rate(self) -> MetricScore:
        """Simulation Drift 발생률 (낮을수록 좋음, 기준: < 5%)."""
        total = sum(1 for e in self.logs if e.get("event_type") == "observe")
        drifted = sum(
            1
            for e in self.logs
            if e.get("event_type") == "reflect" and e.get("payload", {}).get("recalibrated")
        )
        rate = drifted / total if total > 0 else 0.0
        return MetricScore(
            name="Simulation Drift Rate",
            value=round(rate, 4),
            threshold=0.05,
            unit="%",
            status="ok" if rate < 0.05 else "warning" if rate < 0.20 else "critical",
            description="드리프트 임계값 초과로 재보정이 발생한 스텝 비율.",
        )

    def odr(self) -> MetricScore:
        """OOD Detection Rate — OOD 입력 자동 감지율 (높을수록 좋음, 기준: > 0.70).

        OODDetector.proxy_odr()으로 자동 계산한다.
        우선순위: ood_flagged 이벤트 → uncertainty coverage → confidence proxy
        """
        detector = OODDetector()
        result = detector.proxy_odr(self.logs)
        return MetricScore(
            name="OOD Detection Rate",
            value=round(result.odr, 4),
            threshold=0.70,
            unit="%",
            status=("ok" if result.odr > 0.70 else "warning" if result.odr > 0.60 else "critical"),
            description=f"OOD 입력 감지율 ({result.method}, n={result.n_ood_tested}).",
        )

    def planning_depth(self) -> MetricScore:
        """평균 계획 깊이(스텝 수, 높을수록 L2에 가까움)."""
        depths = [
            e["payload"].get("planning_depth", 1)
            for e in self.logs
            if e.get("event_type") == "plan"
        ]
        value = float(np.mean(depths)) if depths else 1.0
        # L1: 1스텝, L2: 5~50스텝
        status = "ok" if value >= 5 else "warning" if value >= 2 else "critical"
        return MetricScore(
            name="Planning Depth",
            value=round(value, 1),
            threshold=5.0,
            unit="steps",
            status=status,
            description="에이전트가 내부 시뮬레이션으로 내다보는 평균 스텝 수.",
        )

    def counterfactual_accuracy(self) -> MetricScore:
        """Counterfactual Accuracy (CA) — LLM-as-Judge 또는 프록시 (높을수록 좋음, 기준: ≥ 0.73)."""
        evaluator = self.ca_evaluator or CounterfactualEvaluator()
        result = evaluator.evaluate(self.episodes)
        value = round(result.ca_score, 4)
        status = "ok" if value >= 0.73 else "warning" if value >= 0.60 else "critical"
        return MetricScore(
            name="Counterfactual Accuracy",
            value=value,
            threshold=0.73,
            unit="corr",
            status=status,
            description=f"반사실 추론 정확도 ({result.method}, n={result.n_evaluated}).",
        )

    # ── Category B: 에이전시 수준 ─────────────────────────────

    def self_correction_capability(self) -> MetricScore:
        """자기 수정 루프 존재 여부 및 빈도."""
        reflect_events = [e for e in self.logs if e.get("event_type") == "reflect"]
        corrections = [e for e in reflect_events if e.get("payload", {}).get("correction_applied")]
        ratio = len(corrections) / len(reflect_events) if reflect_events else 0.0
        return MetricScore(
            name="Self-Correction Rate",
            value=round(ratio, 4),
            threshold=0.10,
            unit="%",
            status="ok" if ratio >= 0.10 else "warning" if ratio > 0 else "critical",
            description="반성 단계에서 실제 수정이 적용된 비율.",
        )

    def uncertainty_awareness(self) -> MetricScore:
        """불확실성을 명시적으로 표현하는지 여부."""
        has_uncertainty = any(
            "uncertainty" in e.get("payload", {})
            for e in self.logs
            if e.get("event_type") == "plan"
        )
        value = 1.0 if has_uncertainty else 0.0
        return MetricScore(
            name="Uncertainty Awareness",
            value=value,
            threshold=1.0,
            status="ok" if has_uncertainty else "critical",
            description="계획 단계에서 불확실성을 명시적으로 표현하는가.",
        )

    def goal_consistency(self) -> MetricScore:
        """목표 유지 일관성 (목표 변경 횟수가 낮을수록 좋음)."""
        goal_changes = sum(
            1
            for e in self.logs
            if e.get("event_type") == "reflect" and e.get("payload", {}).get("goal_changed")
        )
        total_episodes = max(1, sum(1 for e in self.logs if e.get("event_type") == "plan"))
        rate = goal_changes / total_episodes
        return MetricScore(
            name="Goal Consistency",
            value=round(1.0 - rate, 4),
            threshold=0.90,
            status="ok" if rate < 0.10 else "warning" if rate < 0.25 else "critical",
            description="목표가 에피소드 내에서 일관되게 유지되는 비율.",
        )

    def env_adaptation_speed(self) -> MetricScore:
        """환경 변화 후 재보정까지 소요 스텝 수 (낮을수록 좋음)."""
        adaptation_delays = [
            e["payload"].get("steps_to_recalibrate", 999)
            for e in self.logs
            if e.get("event_type") == "reflect" and e.get("payload", {}).get("recalibrated")
        ]
        value = float(np.mean(adaptation_delays)) if adaptation_delays else 999.0
        return MetricScore(
            name="Env Adaptation Speed",
            value=round(value, 1),
            threshold=10.0,
            unit="steps",
            status="ok" if value <= 10 else "warning" if value <= 30 else "critical",
            description="환경 드리프트 감지 후 재보정까지 걸리는 평균 스텝 수.",
        )

    def harness_coverage(self) -> MetricScore:
        """하네스 규칙 적용 범위 (정의된 규칙 수)."""
        rule_count = len(self.config.get("harness_rules", []))
        return MetricScore(
            name="Harness Coverage",
            value=float(rule_count),
            threshold=20.0,
            unit="rules",
            status="ok" if rule_count >= 20 else "warning" if rule_count >= 5 else "critical",
            description="적용 중인 하네스 제약 규칙 수. 20개 이상 권장.",
        )

    def incident_recovery_time(self) -> MetricScore:
        """IRT — 인시던트 발생~회복 평균 시간 (낮을수록 좋음, 기준: < 5분)."""
        tracker = IncidentTracker()
        result = tracker.compute_irt(self.episodes, self.logs)
        value = round(result.irt_minutes, 2)
        status = "ok" if value < 5.0 else "warning" if value < 10.0 else "critical"
        return MetricScore(
            name="Incident Recovery Time",
            value=value,
            threshold=5.0,
            unit="minutes",
            status=status,
            description=f"인시던트 평균 회복 시간 (n={result.n_incidents}).",
        )

    def world_model_update_latency(self) -> MetricScore:
        """WMUL — SDR 초과→ECE 회복까지 레이턴시 (낮을수록 좋음, 기준: < 24시간)."""
        tracker = WMULTracker()
        result = tracker.compute_wmul(self.episodes, self.logs)
        value = round(result.wmul_hours, 2)
        status = "ok" if value < 24.0 else "warning" if value < 72.0 else "critical"
        return MetricScore(
            name="WM Update Latency",
            value=value,
            threshold=24.0,
            unit="hours",
            status=status,
            description=f"SDR 초과→ECE 회복 평균 레이턴시 (n={result.n_drift_events}).",
        )

    # ── Category C: 운영 건전성 ───────────────────────────────

    def recalibration_frequency(self) -> MetricScore:
        """재보정 빈도 (낮을수록 안정적, 기준: < 10%)."""
        return self.simulation_drift_rate()  # 동일 지표, 다른 관점

    def cost_efficiency(self) -> MetricScore:
        """비용 효율 (예산 대비 사용률)."""
        budget = self.config.get("monthly_budget_usd", 0)
        spent = sum(
            e["payload"].get("cost_usd", 0.0)
            for e in self.logs
            if "cost_usd" in e.get("payload", {})
        )
        if budget <= 0:
            ratio = 0.5  # 예산 미설정 → 중립
        else:
            ratio = spent / budget
        return MetricScore(
            name="Cost Efficiency",
            value=round(ratio, 4),
            threshold=1.0,
            unit="ratio",
            status="ok" if ratio <= 0.80 else "warning" if ratio <= 1.0 else "critical",
            description="월 예산 대비 실제 사용 비율.",
        )

    def hitl_trigger_rate(self) -> MetricScore:
        """인간 개입(HITL) 요청 빈도 (낮을수록 자율화 수준 높음, 기준: < 5%)."""
        hitl = sum(1 for e in self.logs if e.get("event_type") == "hitl_request")
        total = sum(1 for e in self.logs if e.get("event_type") in ("plan", "execute"))
        rate = hitl / total if total > 0 else 0.0
        return MetricScore(
            name="HITL Trigger Rate",
            value=round(rate, 4),
            threshold=0.05,
            unit="%",
            status="ok" if rate < 0.05 else "warning" if rate < 0.20 else "critical",
            description="전체 의사결정 중 인간 개입이 요청된 비율.",
        )

    def harness_violation_rate(self) -> MetricScore:
        """하네스 위반 시도 횟수 (0이어야 이상적)."""
        violations = sum(1 for e in self.logs if e.get("event_type") == "harness_violation")
        return MetricScore(
            name="Harness Violation Attempts",
            value=float(violations),
            threshold=0.0,
            unit="count/day",
            status="ok" if violations == 0 else "warning" if violations < 5 else "critical",
            description="하루 기준 하네스 제약 위반 시도 횟수.",
        )

    def checkpoint_recovery_rate(self) -> MetricScore:
        """체크포인트 복구 성공률 (높을수록 좋음, 기준: > 98%)."""
        recoveries = [
            e["payload"].get("recovery_success")
            for e in self.logs
            if e.get("event_type") == "checkpoint_recovery"
        ]
        rate = sum(recoveries) / len(recoveries) if recoveries else 1.0
        return MetricScore(
            name="Checkpoint Recovery Rate",
            value=round(rate, 4),
            threshold=0.98,
            unit="%",
            status="ok" if rate >= 0.98 else "warning" if rate >= 0.90 else "critical",
            description="장애 발생 후 체크포인트에서 성공적으로 복구된 비율.",
        )

    # ── 신뢰구간 및 측정 불가 처리 ────────────────────────────

    @staticmethod
    def _handle_not_measured(metric_name: str, policy: str = NOT_MEASURED_POLICY) -> float | None:
        """측정 불가 지표 처리 정책.

        - exclude: None 반환 (HAS 분모에서 제외)
        - neutral: 50.0 (카테고리 중간값)
        - penalty: 25.0 (임계값의 50%)
        """
        if policy == "neutral":
            return 50.0
        if policy == "penalty":
            return 25.0
        return None  # exclude (기본)

    @staticmethod
    def _compute_sdr(predicted: list[float], actual: list[float]) -> float:
        """예측-실제 리스트로 SDR 계산 (Bootstrap 재사용용 내부 메서드)."""
        if not predicted or not actual:
            return 0.0
        errors = [abs(p - a) for p, a in zip(predicted, actual, strict=False)]
        if len(errors) < 2:
            return 0.0
        mu = float(np.mean(errors))
        sigma = float(np.std(errors))
        threshold = mu + 2.0 * sigma
        return sum(1 for e in errors if e > threshold) / len(errors)

    def compute_sdr_with_ci(
        self,
        predicted: list[float],
        actual: list[float],
        n_bootstrap: int = 1000,
        seed: int = 42,
    ) -> tuple[float, float, float]:
        """SDR + Bootstrap 95% CI. (sdr, ci_lower, ci_upper) 반환.

        샘플 < 5이면 CI = (nan, nan).
        """
        n = len(predicted)
        point_sdr = self._compute_sdr(predicted, actual)
        if n < 5:
            return point_sdr, float("nan"), float("nan")

        rng = np.random.default_rng(seed)
        bootstrap_sdrs: list[float] = []
        for _ in range(n_bootstrap):
            idx = rng.integers(0, n, size=n)
            p_boot = [predicted[i] for i in idx]
            a_boot = [actual[i] for i in idx]
            bootstrap_sdrs.append(self._compute_sdr(p_boot, a_boot))

        ci_lower = float(np.percentile(bootstrap_sdrs, 2.5))
        ci_upper = float(np.percentile(bootstrap_sdrs, 97.5))
        return round(point_sdr, 4), round(ci_lower, 4), round(ci_upper, 4)

    @staticmethod
    def compute_has_with_ci(
        wmq: float,
        alm: float,
        ohm: float,
        wmq_se: float,
        alm_se: float,
        ohm_se: float,
    ) -> tuple[float, float, float]:
        """HAS + 오차 전파 95% CI (델타 방법, 독립성 가정).

        Returns (has, ci_lower, ci_upper).
        """
        from hachillesworld.core.config import HAS_WEIGHTS

        w = HAS_WEIGHTS
        has = w["wmq"] * wmq + w["alm"] * alm + w["ohm"] * ohm
        has_se = (
            (w["wmq"] * wmq_se) ** 2 + (w["alm"] * alm_se) ** 2 + (w["ohm"] * ohm_se) ** 2
        ) ** 0.5
        ci_lower = max(0.0, has - 1.96 * has_se)
        ci_upper = min(100.0, has + 1.96 * has_se)
        return round(has, 2), round(ci_lower, 2), round(ci_upper, 2)

    # ── 유틸리티 ──────────────────────────────────────────────

    @staticmethod
    def _compute_ece(confidences: list[float], actuals: list[float], n_bins: int = 10) -> float:
        """Expected Calibration Error 계산."""
        if not confidences or not actuals:
            return 0.0
        bins = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        n = len(actuals)
        for i in range(n_bins):
            in_bin = [
                (c, a)
                for c, a in zip(confidences, actuals, strict=False)
                if bins[i] <= c < bins[i + 1]
            ]
            if not in_bin:
                continue
            avg_conf = np.mean([c for c, _ in in_bin])
            avg_acc = np.mean([a for _, a in in_bin])
            ece += float((len(in_bin) / n) * abs(avg_conf - avg_acc))
        return float(ece)
