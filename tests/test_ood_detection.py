"""OOD Detection Rate 자동 측정 테스트 — HAW-TR-001 WMQ-4."""

from __future__ import annotations

import pytest

from hachillesworld.scan.engine import ScanEngine
from hachillesworld.scan.metrics import MetricsCalculator
from hachillesworld.scan.ood_detector import OODDetector, OODResult

# ── 공통 픽스처 ───────────────────────────────────────────────


@pytest.fixture
def logs_with_uncertainty_coverage():
    """error_within_uncertainty 필드가 있는 로그 (Strategy 2 프록시 테스트용)."""

    def _obs(err, covered):
        return {
            "event_type": "observe",
            "payload": {
                "prediction_error": err,
                "error_within_uncertainty": covered,
            },
        }

    return [
        {"event_type": "plan", "payload": {"confidence": 0.8}},
        _obs(0.05, True),
        {"event_type": "plan", "payload": {"confidence": 0.7}},
        _obs(0.12, True),
        {"event_type": "plan", "payload": {"confidence": 0.9}},
        _obs(0.25, False),
        {"event_type": "plan", "payload": {"confidence": 0.6}},
        _obs(0.08, True),
    ]


@pytest.fixture
def logs_with_ood_flagged():
    """ood_flagged=True 이벤트가 포함된 로그 (Strategy 1 직접 계산 테스트용)."""
    return [
        {
            "event_type": "observe",
            "payload": {"ood_flagged": True, "confidence": 0.2, "prediction_error": 0.4},
        },
        {
            "event_type": "observe",
            "payload": {"ood_flagged": True, "confidence": 0.3, "prediction_error": 0.5},
        },
        {
            "event_type": "observe",
            "payload": {"ood_flagged": True, "confidence": 0.8, "prediction_error": 0.1},
        },
        {"event_type": "plan", "payload": {"confidence": 0.85}},
    ]


@pytest.fixture
def logs_confidence_only():
    """plan 이벤트에만 confidence가 있는 로그 (Strategy 3 프록시 테스트용)."""
    return [
        {"event_type": "plan", "payload": {"confidence": 0.9, "planning_depth": 5}},
        {"event_type": "plan", "payload": {"confidence": 0.3, "planning_depth": 3}},
        {"event_type": "plan", "payload": {"confidence": 0.85, "planning_depth": 7}},
        {"event_type": "plan", "payload": {"confidence": 0.4, "planning_depth": 4}},
    ]


@pytest.fixture
def sample_config():
    return {
        "laws_domain": "digital",
        "harness_rules": ["r" + str(i) for i in range(20)],
        "monthly_budget_usd": 1000.0,
    }


# ── OODDetector 단위 테스트 ────────────────────────────────────


class TestOODDirectMeasurement:
    def test_odr_direct_measurement_perfect_detector(self, logs_with_uncertainty_coverage):
        """완벽한 OOD 감지기는 ODR=1.0을 반환해야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        ood_states = detector.generate_ood_test_set(
            logs_with_uncertainty_coverage, perturbation_ratio=1.0
        )
        assert len(ood_states) >= 1

        # 항상 낮은 신뢰도를 반환하는 완벽한 OOD 감지기
        def perfect_ood_agent(state: dict) -> float:
            return 0.1  # 항상 threshold(0.5) 미만

        result = detector.measure_odr(perfect_ood_agent, ood_states)

        assert isinstance(result, OODResult)
        assert result.odr == pytest.approx(1.0)
        assert result.method == "direct"
        assert result.n_ood_tested == len(ood_states)
        assert result.confidence > 0.0

    def test_odr_direct_measurement_blind_agent(self, logs_with_uncertainty_coverage):
        """OOD를 전혀 감지하지 못하는 에이전트는 ODR=0.0을 반환해야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        ood_states = detector.generate_ood_test_set(
            logs_with_uncertainty_coverage, perturbation_ratio=1.0
        )

        def blind_agent(state: dict) -> float:
            return 0.9  # 항상 threshold(0.5) 이상

        result = detector.measure_odr(blind_agent, ood_states)

        assert result.odr == pytest.approx(0.0)
        assert result.method == "direct"

    def test_odr_direct_measurement_empty_states(self):
        """OOD 테스트셋이 비어있으면 기본값(0.5)을 반환해야 한다."""
        detector = OODDetector()
        result = detector.measure_odr(lambda s: 0.3, [])

        assert result.odr == pytest.approx(0.5)
        assert result.n_ood_tested == 0
        assert result.confidence == pytest.approx(0.0)

    def test_odr_direct_measurement_partial(self, logs_with_uncertainty_coverage):
        """일부만 감지하는 에이전트의 ODR은 0과 1 사이여야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        ood_states = detector.generate_ood_test_set(
            logs_with_uncertainty_coverage, perturbation_ratio=1.0
        )
        n = len(ood_states)
        call_count = [0]

        def alternating_agent(state: dict) -> float:
            call_count[0] += 1
            return 0.2 if call_count[0] % 2 == 1 else 0.8

        result = detector.measure_odr(alternating_agent, ood_states)
        assert 0.0 < result.odr < 1.0
        assert result.n_ood_tested == n


class TestOODProxyMode:
    def test_odr_proxy_strategy1_ood_flagged(self, logs_with_ood_flagged):
        """ood_flagged 이벤트가 있으면 log_based 방식으로 계산해야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        result = detector.proxy_odr(logs_with_ood_flagged)

        # 3개 ood_flagged 중 2개가 confidence < 0.5 (0.2, 0.3)
        assert result.method == "log_based"
        assert result.n_ood_tested == 3
        assert result.odr == pytest.approx(2 / 3, rel=1e-3)
        assert result.confidence == pytest.approx(0.85)

    def test_odr_proxy_strategy2_uncertainty_coverage(self, logs_with_uncertainty_coverage):
        """ood_flagged 없고 observe 있으면 uncertainty coverage를 프록시로 쓴다."""
        detector = OODDetector()
        result = detector.proxy_odr(logs_with_uncertainty_coverage)

        # 4개 observe 중 3개 error_within_uncertainty=True → 0.75
        assert result.method == "proxy"
        assert result.n_ood_tested == 4
        assert result.odr == pytest.approx(0.75)
        assert result.confidence == pytest.approx(0.60)

    def test_odr_proxy_strategy3_confidence_only(self, logs_confidence_only):
        """observe 없고 plan confidence만 있으면 Strategy 3을 사용해야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        result = detector.proxy_odr(logs_confidence_only)

        # 4개 plan 중 2개 confidence < 0.5 (0.3, 0.4) → 0.5
        assert result.method == "proxy"
        assert result.n_ood_tested == 4
        assert result.odr == pytest.approx(0.5)
        assert result.confidence == pytest.approx(0.40)

    def test_odr_proxy_empty_logs(self):
        """빈 로그는 기본값 0.5를 반환해야 한다."""
        detector = OODDetector()
        result = detector.proxy_odr([])

        assert result.odr == pytest.approx(0.5)
        assert result.n_ood_tested == 0
        assert result.confidence == pytest.approx(0.0)

    def test_odr_proxy_custom_threshold(self, logs_with_ood_flagged):
        """사용자 정의 threshold가 적용되어야 한다."""
        detector = OODDetector(confidence_threshold=0.5)
        # threshold=0.9로 올리면: 3개 ood_flagged 중 2개(0.2, 0.3)가 < 0.9 → 아니라 3개 모두 < 0.9
        result = detector.proxy_odr(logs_with_ood_flagged, confidence_threshold=0.9)

        assert result.method == "log_based"
        assert result.odr == pytest.approx(1.0)  # 0.2, 0.3, 0.8 모두 < 0.9

    def test_odr_strategy1_takes_priority(self):
        """ood_flagged와 observe가 모두 있을 때 Strategy 1이 우선이어야 한다."""
        logs = [
            {"event_type": "observe", "payload": {"ood_flagged": True, "confidence": 0.2}},
            {"event_type": "observe", "payload": {"error_within_uncertainty": True}},
            {"event_type": "observe", "payload": {"error_within_uncertainty": False}},
        ]
        detector = OODDetector(confidence_threshold=0.5)
        result = detector.proxy_odr(logs)

        assert result.method == "log_based"
        assert result.n_ood_tested == 1


class TestOODTestSetGeneration:
    def test_ood_test_set_generation_basic(self, logs_with_uncertainty_coverage):
        """OOD 테스트셋이 비어있지 않아야 한다."""
        detector = OODDetector()
        ood_set = detector.generate_ood_test_set(logs_with_uncertainty_coverage)

        assert len(ood_set) >= 1

    def test_ood_test_set_generation_perturbation_ratio(self, logs_with_uncertainty_coverage):
        """perturbation_ratio에 비례하는 크기의 테스트셋을 생성해야 한다."""
        detector = OODDetector()
        n_events = sum(
            1 for e in logs_with_uncertainty_coverage if e.get("event_type") in ("plan", "observe")
        )

        ood_full = detector.generate_ood_test_set(
            logs_with_uncertainty_coverage, perturbation_ratio=1.0
        )
        ood_half = detector.generate_ood_test_set(
            logs_with_uncertainty_coverage, perturbation_ratio=0.5
        )

        assert len(ood_full) == n_events
        assert len(ood_half) == max(1, n_events // 2)

    def test_ood_extreme_perturbation_multiplies_values(self):
        """_perturb_extreme은 수치값을 10배로 만들어야 한다."""
        detector = OODDetector()
        original = {"confidence": 0.8, "planning_depth": 5, "label": "ok"}
        perturbed = detector._perturb_extreme(original)

        assert perturbed["confidence"] == pytest.approx(8.0)
        assert perturbed["planning_depth"] == pytest.approx(50.0)
        assert perturbed["label"] == "ok"  # 비수치 필드는 그대로

    def test_ood_null_inject_creates_none_field(self):
        """_perturb_null_inject는 하나의 필드를 None으로 만들어야 한다."""
        detector = OODDetector()
        original = {"confidence": 0.8, "planning_depth": 5, "prediction_error": 0.1}
        perturbed = detector._perturb_null_inject(original)

        none_count = sum(1 for v in perturbed.values() if v is None)
        assert none_count == 1

    def test_ood_noise_perturbation_changes_values(self):
        """_perturb_noise는 수치 필드를 원본과 다르게 만들어야 한다."""
        detector = OODDetector()
        original = {"confidence": 0.8, "planning_depth": 5}
        perturbed = detector._perturb_noise(original)

        # 노이즈가 충분히 크므로 값이 변해야 함
        assert perturbed["confidence"] != pytest.approx(original["confidence"])

    def test_ood_test_set_empty_logs(self):
        """빈 로그는 빈 OOD 테스트셋을 반환해야 한다."""
        detector = OODDetector()
        result = detector.generate_ood_test_set([])
        assert result == []

    def test_ood_test_set_3_perturbation_types_cycle(self):
        """3가지 섭동 방식이 순환 적용되어야 한다."""
        detector = OODDetector()
        # 3개 이상 이벤트로 순환 확인
        logs = [
            {"event_type": "plan", "payload": {"confidence": 0.8}},
            {"event_type": "observe", "payload": {"prediction_error": 0.1}},
            {"event_type": "plan", "payload": {"confidence": 0.7}},
        ]
        ood_set = detector.generate_ood_test_set(logs, perturbation_ratio=1.0)
        assert len(ood_set) == 3


class TestComputeMethod:
    def test_compute_uses_direct_when_agent_fn_provided(self, logs_with_uncertainty_coverage):
        """agent_fn이 있으면 direct 방식을 사용해야 한다."""
        detector = OODDetector(confidence_threshold=0.5)

        def low_conf_agent(state: dict) -> float:
            return 0.1

        result = detector.compute(logs_with_uncertainty_coverage, agent_fn=low_conf_agent)
        assert result.method == "direct"

    def test_compute_falls_back_to_proxy(self, logs_with_uncertainty_coverage):
        """agent_fn이 없으면 proxy를 사용해야 한다."""
        detector = OODDetector()
        result = detector.compute(logs_with_uncertainty_coverage)
        assert result.method == "proxy"


class TestODRIntegratedWithScan:
    def test_odr_metric_in_scan_report(self, logs_with_uncertainty_coverage, sample_config):
        """ScanEngine 보고서에 'OOD Detection Rate' 지표가 포함되어야 한다."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=logs_with_uncertainty_coverage, agent_name="test-agent")

        metric_names = [m.name for m in report.world_model_quality.metrics]
        assert "OOD Detection Rate" in metric_names
        assert "Uncertainty Coverage" not in metric_names

    def test_odr_metric_value_correct(self, logs_with_uncertainty_coverage, sample_config):
        """ODR 지표값이 프록시 계산 결과와 일치해야 한다."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=logs_with_uncertainty_coverage, agent_name="test-agent")

        odr_metric = next(
            m for m in report.world_model_quality.metrics if m.name == "OOD Detection Rate"
        )
        # 4개 observe 중 3개 error_within_uncertainty=True → 0.75
        assert odr_metric.value == pytest.approx(0.75)
        assert odr_metric.status == "ok"  # 0.75 > 0.70

    def test_odr_metric_status_critical_for_empty_logs(self, sample_config):
        """로그가 없으면 ODR 기본값(0.5)은 critical 상태여야 한다."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="empty-agent")

        odr_metric = next(
            m for m in report.world_model_quality.metrics if m.name == "OOD Detection Rate"
        )
        assert odr_metric.value == pytest.approx(0.5)
        assert odr_metric.status == "critical"  # 0.5 < 0.60

    def test_metrics_calculator_odr_method(self, logs_with_uncertainty_coverage, sample_config):
        """MetricsCalculator.odr()가 직접 호출 가능해야 한다."""
        calc = MetricsCalculator(logs_with_uncertainty_coverage, sample_config)
        metric = calc.odr()

        assert metric.name == "OOD Detection Rate"
        assert 0.0 <= metric.value <= 1.0
        assert metric.status in ("ok", "warning", "critical")

    def test_backward_compat_full_scan(self, sample_config):
        """기존 test_scan.py 호환: 15개 지표 포함 전체 스캔이 동작해야 한다."""
        logs = [
            {
                "event_type": "plan",
                "payload": {"planning_depth": 12, "confidence": 0.75, "uncertainty": 0.10},
            },
            {
                "event_type": "observe",
                "payload": {"prediction_error": 0.08, "error_within_uncertainty": True},
            },
            {
                "event_type": "reflect",
                "payload": {"recalibrated": False, "correction_applied": False},
            },
        ] * 3

        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=logs, agent_name="compat-agent")

        assert report.composite_score >= 0.0
        all_names = [
            m.name
            for m in (
                report.world_model_quality.metrics
                + report.agency_level.metrics
                + report.operational_health.metrics
            )
        ]
        assert "OOD Detection Rate" in all_names
        assert len(all_names) == 15
