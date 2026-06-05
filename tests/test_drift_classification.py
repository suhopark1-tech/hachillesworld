"""Sprint 2-A: DriftCausalClassifier + RecalibrationExecutor 테스트."""

from __future__ import annotations

import time

from hachillesworld.operate.meta_harness import MetaHarness
from hachillesworld.operate.monitor import DriftMonitor, DriftValue
from hachillesworld.operate.recalibrator import (
    CausalClassificationResult,
    DriftCausalClassifier,
    DriftToHarnessAdapter,
    RecalibrationExecutor,
)


def _make_dv(
    value: float,
    step: int = 0,
    predicted: dict | None = None,
    actual: dict | None = None,
) -> DriftValue:
    pred = predicted or {"x": 1.0}
    act = actual or {"x": 1.0 + value}
    return DriftValue(
        predicted=pred,
        actual=act,
        value=value,
        exceeded_threshold=value > 0.15,
        timestamp=time.time(),
        step_index=step,
    )


class TestDriftCausalClassifier:
    def test_abrupt_drift_classified_as_env(self):
        """갑작스러운 드리프트 + 공변량 + 균등 분포 → env_nonstationarity."""
        baseline = [
            _make_dv(0.05, i, {"x": 100.0, "y": 50.0}, {"x": 100.5, "y": 50.25}) for i in range(15)
        ]
        # 최근 5개: 값 급증 + x/y 모두 균등 드리프트 (분산 낮음)
        recent = [
            _make_dv(0.50, 15 + i, {"x": 100.0, "y": 50.0}, {"x": 110.0, "y": 60.0})
            for i in range(5)
        ]
        drift_log = baseline + recent

        classifier = DriftCausalClassifier()
        result = classifier.classify(drift_log, covariate_changed=True)

        assert result.cause == "env_nonstationarity"
        assert result.confidence >= 0.75
        assert result.abruptness >= 2.0
        assert result.covariate_signal is True
        assert result.concentration_variance < 0.05

    def test_gradual_drift_classified_as_model(self):
        """점진적 드리프트 + 공변량 없음 + 특정 키 집중 → model_degradation."""
        baseline = [
            _make_dv(0.10, i, {"x": 100.0, "y": 50.0}, {"x": 105.0, "y": 50.5}) for i in range(15)
        ]
        # 최근 5개: 완만한 증가 + x키에만 집중된 드리프트 (분산 높음)
        recent = [
            _make_dv(0.15, 15 + i, {"x": 100.0, "y": 50.0}, {"x": 150.0, "y": 51.0})
            for i in range(5)
        ]
        drift_log = baseline + recent

        classifier = DriftCausalClassifier()
        result = classifier.classify(drift_log, covariate_changed=False)

        assert result.cause == "model_degradation"
        assert result.confidence >= 0.75
        assert result.abruptness < 2.0
        assert result.covariate_signal is False
        assert result.concentration_variance >= 0.05

    def test_uncertain_low_confidence(self):
        """데이터 부족 (window_baseline 미만) → uncertain, confidence=0.0."""
        drift_log = [_make_dv(0.20, i) for i in range(5)]  # < window_baseline=20

        classifier = DriftCausalClassifier()
        result = classifier.classify(drift_log)

        assert result.cause == "uncertain"
        assert result.confidence < 0.75
        assert result.confidence == 0.0
        assert result.recalibration_strategy == "conservative_monitoring"


class TestRecalibrationExecutor:
    def test_recalibration_strategy_selection(self):
        """원인별 재보정 전략 자동 선택 검증."""
        executor = RecalibrationExecutor()

        # env_nonstationarity → immediate_world_model_sync
        result_env = CausalClassificationResult(
            cause="env_nonstationarity",
            confidence=0.90,
            evidence=["test"],
            recalibration_strategy="immediate_world_model_sync",
            abruptness=3.0,
            covariate_signal=True,
            concentration_variance=0.01,
        )
        rec = executor.execute(result_env, [])
        assert rec.strategy == "immediate_world_model_sync"
        assert rec.skipped is False
        assert rec.cause == "env_nonstationarity"

        # model_degradation → gradual_recalibration_with_retraining_trigger
        result_model = CausalClassificationResult(
            cause="model_degradation",
            confidence=0.95,
            evidence=["test"],
            recalibration_strategy="gradual_recalibration_with_retraining_trigger",
            abruptness=1.0,
            covariate_signal=False,
            concentration_variance=0.5,
        )
        rec = executor.execute(result_model, [])
        assert rec.strategy == "gradual_recalibration_with_retraining_trigger"
        assert rec.skipped is False

        # uncertain (신뢰도 < 0.75) → conservative_monitoring, 재보정 실행 안 함
        result_uncertain = CausalClassificationResult(
            cause="uncertain",
            confidence=0.0,
            evidence=["데이터 부족"],
            recalibration_strategy="conservative_monitoring",
            abruptness=0.0,
            covariate_signal=False,
            concentration_variance=0.0,
        )
        rec = executor.execute(result_uncertain, [])
        assert rec.strategy == "conservative_monitoring"
        assert rec.skipped is True
        assert "신뢰도" in rec.skip_reason or "원인" in rec.skip_reason

        # 이력 기록 확인
        assert len(executor.get_recalibration_log()) == 3


class TestMultiCallbackChain:
    def test_multicallback_chain(self):
        """멀티 콜백 체인 — 경보 발생 시 등록된 모든 콜백 호출."""
        buckets: list[list] = [[], [], []]
        monitor = DriftMonitor("multi-cb", threshold=0.10, alert_rate_threshold=0.10)
        for bucket in buckets:
            monitor.add_alert_callback(bucket.append)

        for _ in range(5):
            monitor.record({"x": 1.0}, {"x": 10.0})  # drift=9.0 >> threshold

        assert all(len(b) > 0 for b in buckets), "모든 콜백이 호출되어야 한다"
        assert all(b[0].agent_name == "multi-cb" for b in buckets)
        # 세 버킷 모두 같은 횟수로 호출됨
        assert len(buckets[0]) == len(buckets[1]) == len(buckets[2])


class TestDriftToHarnessAdapter:
    def test_drift_to_harness_adapter(self):
        """DriftMonitor 경보 → MetaHarness 실패 이벤트 전달."""
        meta = MetaHarness(auto_apply_threshold=100)  # 자동 규칙 생성은 억제
        adapter = DriftToHarnessAdapter(meta)
        monitor = DriftMonitor("harness-agent", threshold=0.10, alert_rate_threshold=0.10)
        monitor.add_alert_callback(adapter)

        for _ in range(5):
            monitor.record({"x": 1.0}, {"x": 10.0})

        # MetaHarness가 "observe:drift" 패턴을 기록했는지 확인
        assert "observe:drift" in meta._patterns
        pattern = meta._patterns["observe:drift"]
        assert pattern.occurrences > 0
        assert "World Model 드리프트 경보" in pattern.description
