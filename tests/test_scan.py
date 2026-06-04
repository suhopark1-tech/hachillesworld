"""Scan 모듈 테스트."""

import pytest

from hachillesworld.core.models import LawsDomain, Level
from hachillesworld.scan.engine import ScanEngine
from hachillesworld.scan.metrics import MetricsCalculator

# ── 공통 픽스처 ───────────────────────────────────────────────


@pytest.fixture
def sample_logs():
    """L2 수준의 에이전트 로그 샘플."""
    return [
        {
            "event_type": "plan",
            "payload": {"planning_depth": 12, "confidence": 0.75, "uncertainty": 0.10},
        },
        {"event_type": "execute", "payload": {"action": "query_api"}},
        {
            "event_type": "observe",
            "payload": {"prediction_error": 0.08, "error_within_uncertainty": True},
        },
        {"event_type": "reflect", "payload": {"recalibrated": False, "correction_applied": False}},
        {
            "event_type": "plan",
            "payload": {"planning_depth": 15, "confidence": 0.80, "uncertainty": 0.12},
        },
        {"event_type": "execute", "payload": {"action": "update_state"}},
        {
            "event_type": "observe",
            "payload": {
                "prediction_error": 0.11,
                "error_within_uncertainty": True,
                "goal_achieved": True,
            },
        },
        {"event_type": "reflect", "payload": {"recalibrated": False, "correction_applied": True}},
    ]


@pytest.fixture
def sample_config():
    return {
        "laws_domain": "digital",
        "harness_rules": [
            "rule_1",
            "rule_2",
            "rule_3",
            "rule_4",
            "rule_5",
            "rule_6",
            "rule_7",
            "rule_8",
            "rule_9",
            "rule_10",
            "rule_11",
            "rule_12",
            "rule_13",
            "rule_14",
            "rule_15",
            "rule_16",
            "rule_17",
            "rule_18",
            "rule_19",
            "rule_20",
        ],
        "monthly_budget_usd": 1000.0,
    }


# ── MetricsCalculator 테스트 ──────────────────────────────────


class TestMetricsCalculator:
    def test_prediction_error_rate_normal(self, sample_logs, sample_config):
        calc = MetricsCalculator(sample_logs, sample_config)
        metric = calc.prediction_error_rate()
        assert metric.value < 0.15
        assert metric.status == "ok"

    def test_planning_depth_extracted(self, sample_logs, sample_config):
        calc = MetricsCalculator(sample_logs, sample_config)
        metric = calc.planning_depth()
        assert metric.value >= 5.0  # 평균 12.5
        assert metric.status == "ok"

    def test_harness_coverage_full(self, sample_logs, sample_config):
        calc = MetricsCalculator(sample_logs, sample_config)
        metric = calc.harness_coverage()
        assert metric.value == 20.0
        assert metric.status == "ok"

    def test_harness_coverage_insufficient(self, sample_logs):
        calc = MetricsCalculator(sample_logs, {"harness_rules": ["r1", "r2"]})
        metric = calc.harness_coverage()
        assert metric.status == "critical"

    def test_uncertainty_awareness_detected(self, sample_logs, sample_config):
        calc = MetricsCalculator(sample_logs, sample_config)
        metric = calc.uncertainty_awareness()
        assert metric.value == 1.0
        assert metric.status == "ok"

    def test_empty_logs(self):
        calc = MetricsCalculator([], {})
        metric = calc.prediction_error_rate()
        assert metric.value == 0.0

    def test_ece_computation(self):
        ece = MetricsCalculator._compute_ece(
            confidences=[0.9, 0.8, 0.7, 0.6],
            actuals=[1.0, 1.0, 0.0, 0.0],
        )
        assert 0.0 <= ece <= 1.0


# ── ScanEngine 테스트 ─────────────────────────────────────────


class TestScanEngine:
    def test_basic_scan(self, sample_logs, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=sample_logs, agent_name="test-agent")

        assert report.agent_name == "test-agent"
        assert report.level in (Level.L1, Level.L2, Level.L3)
        assert report.laws_domain == LawsDomain.DIGITAL
        assert 0.0 <= report.composite_score <= 100.0

    def test_level_classification_l2(self, sample_logs, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=sample_logs, agent_name="test-agent")
        assert report.level == Level.L2

    def test_laws_domain_digital(self, sample_logs, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=sample_logs, agent_name="test-agent")
        assert report.laws_domain == LawsDomain.DIGITAL

    def test_laws_domain_physical(self, sample_logs):
        engine = ScanEngine(config={"laws_domain": "physical"})
        report = engine.run(logs=sample_logs, agent_name="robot-agent")
        assert report.laws_domain == LawsDomain.PHYSICAL

    def test_report_summary_format(self, sample_logs, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=sample_logs, agent_name="test-agent")
        summary = report.summary()
        assert "test-agent" in summary
        assert "/100" in summary

    def test_empty_logs_default_level(self):
        engine = ScanEngine(config={})
        report = engine.run(logs=[], agent_name="empty-agent")
        assert report.level == Level.L1
        assert report.composite_score >= 0.0

    def test_recommendations_generated(self, sample_config):
        # 드리프트가 많은 로그로 권장 사항 생성 확인
        bad_logs = [
            {
                "event_type": "observe",
                "payload": {"prediction_error": 0.35, "error_within_uncertainty": False},
            },
            {"event_type": "reflect", "payload": {"recalibrated": True}},
        ] * 10
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=bad_logs, agent_name="bad-agent")
        assert len(report.recommendations) > 0
