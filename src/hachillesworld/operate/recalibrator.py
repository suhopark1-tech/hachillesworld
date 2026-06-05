"""DriftCausalClassifier + RecalibrationExecutor — PAT-005 핵심 구현."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from hachillesworld.operate.monitor import DriftAlert, DriftValue


@dataclass
class CausalClassificationResult:
    """드리프트 원인 분류 결과. PAT-005 §9.4."""

    cause: str  # "env_nonstationarity" | "model_degradation" | "uncertain"
    confidence: float
    evidence: list[str]
    recalibration_strategy: str
    abruptness: float
    covariate_signal: bool
    concentration_variance: float


@dataclass
class RecalibrationResult:
    """재보정 실행 결과."""

    strategy: str
    cause: str
    confidence: float
    action: str
    timestamp: float
    skipped: bool = False
    skip_reason: str = ""


class DriftCausalClassifier:
    """드리프트 원인을 환경 비정상성과 모델 열화로 자동 분류한다.

    3신호 알고리즘 (PAT-005 §9.4):
      신호 1 — Abruptness: 최근 vs 기준 드리프트 평균 비율
      신호 2 — 외부 공변량 변화 신호 (covariate_changed)
      신호 3 — 키별 드리프트 집중도 분산
    """

    def __init__(
        self,
        abruptness_ratio_threshold: float = 2.0,
        window_recent: int = 5,
        window_baseline: int = 20,
    ) -> None:
        self.abruptness_ratio_threshold = abruptness_ratio_threshold
        self.window_recent = window_recent
        self.window_baseline = window_baseline

    def classify(
        self,
        drift_log: list[DriftValue],
        covariate_changed: bool = False,
        confidence_threshold: float = 0.75,
    ) -> CausalClassificationResult:
        """3신호 알고리즘으로 드리프트 원인을 분류한다.

        confidence < confidence_threshold 시 "uncertain" 반환 (보수적 설정).
        """
        if len(drift_log) < self.window_baseline:
            return CausalClassificationResult(
                cause="uncertain",
                confidence=0.0,
                evidence=["드리프트 이력 부족 — 추가 관측 필요"],
                recalibration_strategy="conservative_monitoring",
                abruptness=0.0,
                covariate_signal=covariate_changed,
                concentration_variance=0.0,
            )

        score = 0
        evidence: list[str] = []

        # [신호 1] 갑작스러움 (Abruptness)
        recent_values = [d.value for d in drift_log[-self.window_recent :]]
        baseline_values = [d.value for d in drift_log[-self.window_baseline : -self.window_recent]]
        recent_mean = float(np.mean(recent_values)) if recent_values else 0.0
        baseline_mean = float(np.mean(baseline_values)) if baseline_values else 1e-9
        abruptness = recent_mean / max(baseline_mean, 1e-9)

        if abruptness >= self.abruptness_ratio_threshold:
            score += 1
            evidence.append(
                f"갑작스러운 드리프트 증가: 최근 {recent_mean:.3f} / "
                f"기준 {baseline_mean:.3f} = {abruptness:.2f}배"
            )
        else:
            evidence.append(
                f"점진적 드리프트 패턴: 비율 {abruptness:.2f} "
                f"(임계 {self.abruptness_ratio_threshold}배 미만)"
            )

        # [신호 2] 외부 공변량 변화
        if covariate_changed:
            score += 1
            evidence.append("외부 공변량 변화 신호 수신 (환경 이벤트 또는 입력 스키마 변경)")
        else:
            evidence.append("외부 공변량 변화 신호 없음")

        # [신호 3] 키별 드리프트 집중도 분산
        concentration_variance = self._compute_key_drift_variance(drift_log[-self.window_recent :])
        if concentration_variance < 0.05:
            score += 1
            evidence.append(
                f"드리프트 균등 분포 (variance={concentration_variance:.4f} < 0.05) "
                f"— 환경 전반 변화"
            )
        else:
            evidence.append(
                f"드리프트 특정 키 집중 (variance={concentration_variance:.4f} >= 0.05) "
                f"— 모델 부분 열화"
            )

        # [최종 판정]
        if score >= 2:
            cause = "env_nonstationarity"
            confidence = round(min(0.95, 0.50 + score * 0.20), 4)
            strategy = "immediate_world_model_sync"
        elif score == 0:
            cause = "model_degradation"
            confidence = 0.95
            strategy = "gradual_recalibration_with_retraining_trigger"
        else:  # score == 1: 혼합 신호 — 신뢰도 임계값 미달
            cause = "model_degradation"
            confidence = 0.65
            strategy = "gradual_recalibration_with_retraining_trigger"

        if confidence < confidence_threshold:
            cause = "uncertain"
            strategy = "conservative_monitoring"

        return CausalClassificationResult(
            cause=cause,
            confidence=confidence,
            evidence=evidence,
            recalibration_strategy=strategy,
            abruptness=round(abruptness, 4),
            covariate_signal=covariate_changed,
            concentration_variance=round(concentration_variance, 4),
        )

    @staticmethod
    def _compute_key_drift_variance(drift_log: list[DriftValue]) -> float:
        """상태 키별 평균 드리프트 기여도의 분산을 산출한다.

        분산이 낮으면 드리프트가 모든 키에 고르게 분포 → 환경 변화.
        분산이 높으면 특정 키에 집중 → 모델 특정 구성요소 열화.
        """
        if not drift_log:
            return 0.0

        key_diffs: dict[str, list[float]] = {}
        for record in drift_log:
            common = set(record.predicted) & set(record.actual)
            for k in common:
                p, a = record.predicted[k], record.actual[k]
                if isinstance(p, int | float) and isinstance(a, int | float):
                    key_diffs.setdefault(k, []).append(abs(float(p) - float(a)))

        if not key_diffs:
            return 0.0

        per_key_means = [float(np.mean(v)) for v in key_diffs.values()]
        return float(np.var(per_key_means)) if len(per_key_means) > 1 else 0.0


class RecalibrationExecutor:
    """DriftCausalClassifier 분류 결과에 따라 재보정 전략을 실행한다.

    PAT-005 §9.5:
      env_nonstationarity → immediate_world_model_sync
      model_degradation   → gradual_recalibration_with_retraining_trigger
      uncertain           → conservative_monitoring (재보정 실행 안 함)
    """

    def __init__(
        self,
        world_model_updater: Any = None,
        retraining_queue: Any = None,
    ) -> None:
        self.world_model_updater = world_model_updater
        self.retraining_queue = retraining_queue
        self._recalibration_log: list[RecalibrationResult] = []

    def execute(
        self,
        result: CausalClassificationResult,
        drift_log: list[DriftValue],
        agent_interface: Any = None,
    ) -> RecalibrationResult:
        """원인 분류 결과에 따라 적합한 재보정 전략을 실행한다."""
        if result.cause == "env_nonstationarity":
            rec = self._immediate_world_model_sync(result, drift_log)
        elif result.cause == "model_degradation":
            rec = self._gradual_recalibration_with_retraining_trigger(result, drift_log)
        else:  # uncertain — 신뢰도 부족, 재보정 실행 안 함
            rec = self._conservative_monitoring(result, drift_log)
        self._recalibration_log.append(rec)
        return rec

    def get_recalibration_log(self) -> list[RecalibrationResult]:
        """전체 재보정 실행 이력. 감사·대시보드용."""
        return list(self._recalibration_log)

    def _immediate_world_model_sync(
        self,
        result: CausalClassificationResult,
        drift_log: list[DriftValue],
    ) -> RecalibrationResult:
        recent_actuals = [d.actual for d in drift_log[-10:]]
        if self.world_model_updater:
            self.world_model_updater.sync(recent_actuals)
        return RecalibrationResult(
            strategy="immediate_world_model_sync",
            cause=result.cause,
            confidence=result.confidence,
            action=f"즉시 동기화: 최근 {len(recent_actuals)}개 관측값 반영",
            timestamp=time.time(),
        )

    def _gradual_recalibration_with_retraining_trigger(
        self,
        result: CausalClassificationResult,
        drift_log: list[DriftValue],
    ) -> RecalibrationResult:
        if self.retraining_queue:
            self.retraining_queue.enqueue(drift_log)
        return RecalibrationResult(
            strategy="gradual_recalibration_with_retraining_trigger",
            cause=result.cause,
            confidence=result.confidence,
            action=f"재학습 큐 등록: {len(drift_log)}개 에피소드 데이터 추가",
            timestamp=time.time(),
        )

    def _conservative_monitoring(
        self,
        result: CausalClassificationResult,
        drift_log: list[DriftValue],
    ) -> RecalibrationResult:
        return RecalibrationResult(
            strategy="conservative_monitoring",
            cause=result.cause,
            confidence=result.confidence,
            action="관망: 추가 데이터 수집 대기",
            timestamp=time.time(),
            skipped=True,
            skip_reason=f"신뢰도 부족 또는 원인 불명 (confidence={result.confidence:.2f})",
        )


class DriftToHarnessAdapter:
    """DriftMonitor 경보 → MetaHarness 실패 이벤트 변환 어댑터.

    DriftMonitor.add_alert_callback(adapter)으로 등록하면,
    경보 발생 시 MetaHarness.record_failure()를 자동 호출하여
    드리프트 대응 하네스 규칙 생성 파이프라인을 트리거한다.
    PAT-005 §9.7.
    """

    def __init__(self, meta_harness: Any) -> None:
        self.meta_harness = meta_harness

    def __call__(self, alert: DriftAlert) -> None:
        """DriftAlert를 MetaHarness 실패 이벤트로 변환하여 전달한다."""
        self.meta_harness.record_failure(
            {
                "event_type": "observe:drift",
                "payload": {
                    "description": (
                        f"World Model 드리프트 경보: "
                        f"drift_value={alert.drift_value}, "
                        f"recent_rate={alert.recent_rate}"
                    ),
                    "prediction_error": alert.drift_value,
                    "cause": alert.cause,
                    "recalibration_strategy": alert.recalibration_strategy,
                },
            }
        )
