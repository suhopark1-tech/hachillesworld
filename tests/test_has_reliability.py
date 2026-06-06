"""Sprint 5-B: HAS 신뢰구간 + 버전 관리 + 측정 불가 정책 테스트."""

from __future__ import annotations

import math

import pytest

from hachillesworld.core.config import (
    HAS_CURRENT_VERSION,
    HAS_WEIGHT_VERSIONS,
    get_weights_for_version,
)
from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
    MetricScore,
)
from hachillesworld.scan.metrics import NOT_MEASURED_POLICY, MetricsCalculator

# ── 픽스처 ─────────────────────────────────────────────────────────────


def _make_calc(n: int = 30) -> MetricsCalculator:
    """더미 로그로 MetricsCalculator 생성."""
    logs = [
        {
            "timestamp": float(i),
            "event_type": "execute",
            "agent_name": "test",
            "payload": {
                "predicted_state": {"x": float(i)},
                "actual_state": {"x": float(i) + 0.1 * (i % 3)},
                "confidence": 0.8,
                "goal_achieved": True,
            },
        }
        for i in range(n)
    ]
    return MetricsCalculator(logs=logs, config={})


def _make_report(wmq: float = 70.0, alm: float = 65.0, ohm: float = 75.0) -> DiagnosticReport:
    return DiagnosticReport(
        agent_name="test-agent",
        level=Level.L2,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore(name="WMQ", score=wmq),
        agency_level=CategoryScore(name="ALM", score=alm),
        operational_health=CategoryScore(name="OHM", score=ohm),
        recommendations=[],
    )


# ── 작업 1: Bootstrap CI ─────────────────────────────────────────────


class TestSDRBootstrapCI:
    """test_sdr_bootstrap_ci: SDR Bootstrap 신뢰구간 검증."""

    def test_returns_three_values(self) -> None:
        calc = _make_calc(20)
        predicted = [float(i) for i in range(20)]
        actual = [float(i) + 0.05 * (i % 5) for i in range(20)]
        sdr, ci_lo, ci_hi = calc.compute_sdr_with_ci(predicted, actual)
        assert isinstance(sdr, float)
        assert isinstance(ci_lo, float)
        assert isinstance(ci_hi, float)

    def test_ci_bounds_ordered(self) -> None:
        calc = _make_calc(30)
        predicted = [float(i) for i in range(30)]
        actual = [float(i) + 0.1 * (i % 4) for i in range(30)]
        _, ci_lo, ci_hi = calc.compute_sdr_with_ci(predicted, actual)
        assert ci_lo <= ci_hi

    def test_sdr_in_zero_one(self) -> None:
        calc = _make_calc(20)
        predicted = [float(i) for i in range(20)]
        actual = [float(i) + 0.2 for i in range(20)]
        sdr, _, _ = calc.compute_sdr_with_ci(predicted, actual)
        assert 0.0 <= sdr <= 1.0

    def test_small_sample_ci_nan(self) -> None:
        calc = _make_calc(3)
        predicted = [1.0, 2.0, 3.0]
        actual = [1.1, 2.1, 3.1]
        _, ci_lo, ci_hi = calc.compute_sdr_with_ci(predicted, actual)
        assert math.isnan(ci_lo)
        assert math.isnan(ci_hi)

    def test_reproducible_with_seed(self) -> None:
        calc = _make_calc(20)
        predicted = [float(i) for i in range(20)]
        actual = [float(i) + 0.15 * (i % 3) for i in range(20)]
        r1 = calc.compute_sdr_with_ci(predicted, actual, seed=42)
        r2 = calc.compute_sdr_with_ci(predicted, actual, seed=42)
        assert r1 == r2


# ── 작업 1: 오차 전파 ───────────────────────────────────────────────


class TestHASErrorPropagation:
    """test_has_error_propagation: 델타 방법 오차 전파 검증."""

    def test_returns_three_values(self) -> None:
        calc = _make_calc()
        has, lo, hi = calc.compute_has_with_ci(70.0, 65.0, 75.0, 5.0, 4.0, 6.0)
        assert isinstance(has, float)
        assert isinstance(lo, float)
        assert isinstance(hi, float)

    def test_ci_bounds_ordered(self) -> None:
        calc = _make_calc()
        _, lo, hi = calc.compute_has_with_ci(70.0, 65.0, 75.0, 5.0, 4.0, 6.0)
        assert lo <= hi

    def test_zero_se_gives_point_ci(self) -> None:
        calc = _make_calc()
        from hachillesworld.core.config import HAS_WEIGHTS

        w = HAS_WEIGHTS
        wmq, alm, ohm = 70.0, 65.0, 75.0
        expected_has = w["wmq"] * wmq + w["alm"] * alm + w["ohm"] * ohm
        has, lo, hi = calc.compute_has_with_ci(wmq, alm, ohm, 0.0, 0.0, 0.0)
        assert abs(has - expected_has) < 0.01
        assert abs(lo - has) < 0.01
        assert abs(hi - has) < 0.01

    def test_ci_within_0_100(self) -> None:
        calc = _make_calc()
        _, lo, hi = calc.compute_has_with_ci(5.0, 5.0, 5.0, 10.0, 10.0, 10.0)
        assert lo >= 0.0
        assert hi <= 100.0

    def test_has_matches_weighted_sum(self) -> None:
        from hachillesworld.core.config import HAS_WEIGHTS

        w = HAS_WEIGHTS
        calc = _make_calc()
        wmq, alm, ohm = 80.0, 70.0, 90.0
        has, _, _ = calc.compute_has_with_ci(wmq, alm, ohm, 1.0, 1.0, 1.0)
        expected = w["wmq"] * wmq + w["alm"] * alm + w["ohm"] * ohm
        assert abs(has - expected) < 0.01


# ── 작업 1: DiagnosticReport에 CI 포함 ──────────────────────────────


class TestHASCIInReport:
    """test_has_ci_in_report: DiagnosticReport CI 필드 검증."""

    def test_has_confidence_interval_field_exists(self) -> None:
        report = _make_report()
        assert hasattr(report, "has_confidence_interval")
        assert report.has_confidence_interval is None  # 기본값

    def test_has_ci_can_be_set(self) -> None:
        report = _make_report()
        report.has_confidence_interval = (65.0, 72.0)
        lo, hi = report.has_confidence_interval
        assert lo < hi

    def test_metric_score_ci_fields(self) -> None:
        m = MetricScore(name="SDR", value=0.03, threshold=0.05, status="ok")
        assert m.confidence_lower is None
        assert m.confidence_upper is None
        assert m.measurement_error is None
        assert m.sample_size is None

    def test_metric_score_ci_assignment(self) -> None:
        m = MetricScore(
            name="SDR",
            value=0.03,
            threshold=0.05,
            status="ok",
            confidence_lower=0.01,
            confidence_upper=0.06,
            measurement_error=0.005,
            sample_size=100,
        )
        assert m.confidence_lower == 0.01
        assert m.confidence_upper == 0.06
        assert m.measurement_error == 0.005
        assert m.sample_size == 100

    def test_not_measured_metrics_field(self) -> None:
        report = _make_report()
        assert hasattr(report, "not_measured_metrics")
        assert report.not_measured_metrics == []
        report.not_measured_metrics = ["ODR", "CA"]
        assert "ODR" in report.not_measured_metrics


# ── 작업 2: HAS 버전 관리 ───────────────────────────────────────────


class TestHASVersionManagement:
    """test_has_version_management: 가중치 버전 레지스트리 검증."""

    def test_version_registry_has_20(self) -> None:
        assert "2.0" in HAS_WEIGHT_VERSIONS

    def test_version_registry_has_21(self) -> None:
        assert "2.1" in HAS_WEIGHT_VERSIONS

    def test_current_version_is_21(self) -> None:
        assert HAS_CURRENT_VERSION == "2.1"

    def test_weights_sum_to_one(self) -> None:
        for version in HAS_WEIGHT_VERSIONS:
            w = get_weights_for_version(version)
            total = w["wmq"] + w["alm"] + w["ohm"]
            assert abs(total - 1.0) < 1e-9, f"버전 {version} 가중치 합계: {total}"

    def test_get_weights_returns_floats(self) -> None:
        w = get_weights_for_version("2.1")
        assert all(isinstance(v, float) for v in w.values())

    def test_get_weights_has_required_keys(self) -> None:
        w = get_weights_for_version("2.0")
        assert "wmq" in w
        assert "alm" in w
        assert "ohm" in w

    def test_released_key_excluded(self) -> None:
        w = get_weights_for_version("2.1")
        assert "released" not in w


class TestInvalidVersionRaises:
    """test_invalid_version_raises: 없는 버전 → ValueError."""

    def test_unknown_version(self) -> None:
        with pytest.raises(ValueError, match="알 수 없는"):
            get_weights_for_version("99.0")

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError):
            get_weights_for_version("")

    def test_error_message_contains_available(self) -> None:
        with pytest.raises(ValueError, match=r"2\.0"):
            get_weights_for_version("3.0")


# ── 작업 2: composite_score_at_version ──────────────────────────────


class TestCompositeScoreAtVersion:
    """test_composite_score_at_version: 버전별 HAS 재산출 검증."""

    def test_version_21_matches_composite_score(self) -> None:
        report = _make_report(wmq=70.0, alm=65.0, ohm=75.0)
        score_21 = report.composite_score_at_version("2.1")
        # 현재 버전(2.1) == composite_score
        assert abs(score_21 - report.composite_score) < 0.01

    def test_version_20_same_weights_same_result(self) -> None:
        """v2.0과 v2.1 가중치가 동일하므로 점수도 동일해야 한다."""
        report = _make_report(wmq=80.0, alm=70.0, ohm=90.0)
        score_20 = report.composite_score_at_version("2.0")
        score_21 = report.composite_score_at_version("2.1")
        assert abs(score_20 - score_21) < 0.01

    def test_raises_on_invalid_version(self) -> None:
        report = _make_report()
        with pytest.raises(ValueError):
            report.composite_score_at_version("99.0")

    def test_result_in_valid_range(self) -> None:
        report = _make_report(wmq=100.0, alm=100.0, ohm=100.0)
        score = report.composite_score_at_version("2.1")
        assert 0.0 <= score <= 100.0

    def test_zero_scores(self) -> None:
        report = _make_report(wmq=0.0, alm=0.0, ohm=0.0)
        assert report.composite_score_at_version("2.1") == 0.0


# ── 작업 3: 측정 불가 처리 정책 ─────────────────────────────────────


class TestNotMeasuredExcludePolicy:
    """test_not_measured_exclude_policy: exclude 정책 None 반환 검증."""

    def test_exclude_returns_none(self) -> None:
        result = MetricsCalculator._handle_not_measured("ODR", policy="exclude")
        assert result is None

    def test_default_policy_is_exclude(self) -> None:
        assert NOT_MEASURED_POLICY == "exclude"
        result = MetricsCalculator._handle_not_measured("PA")
        assert result is None


class TestNotMeasuredNeutralPolicy:
    """test_not_measured_neutral_policy: neutral 정책 50.0 반환 검증."""

    def test_neutral_returns_50(self) -> None:
        result = MetricsCalculator._handle_not_measured("ODR", policy="neutral")
        assert result == 50.0

    def test_penalty_returns_25(self) -> None:
        result = MetricsCalculator._handle_not_measured("ODR", policy="penalty")
        assert result == 25.0

    def test_unknown_policy_returns_none(self) -> None:
        result = MetricsCalculator._handle_not_measured("ODR", policy="unknown_policy")
        assert result is None


# ── 측정 불가 지표 필드 통합 검증 ────────────────────────────────────


class TestMeasurementMetadataField:
    """DiagnosticReport measurement_metadata 및 has_score_version 필드 검증."""

    def test_has_score_version_default(self) -> None:
        report = _make_report()
        assert report.has_score_version == "2.1"

    def test_measurement_metadata_default_empty(self) -> None:
        report = _make_report()
        assert report.measurement_metadata == {}

    def test_measurement_metadata_settable(self) -> None:
        report = _make_report()
        report.measurement_metadata = {"bootstrap_n": 1000, "ci_level": 0.95}
        assert report.measurement_metadata["bootstrap_n"] == 1000
