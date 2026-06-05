"""IRT·WMUL 자동 추적 테스트 — HAW-TR-001 OHM-4 & WMQ-5."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.scan.engine import ScanEngine
from hachillesworld.scan.incident_tracker import IncidentTracker, _parse_ts
from hachillesworld.scan.metrics import MetricsCalculator
from hachillesworld.scan.wmul_tracker import WMULTracker

# ── 헬퍼 ─────────────────────────────────────────────────────


def make_episode(
    offset_minutes: float = 0.0,
    *,
    base: datetime | None = None,
    infrastructure_failure: bool = False,
    goal_achieved: bool = True,
    max_prediction_error: float | None = None,
) -> EpisodeRecord:
    if base is None:
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    ts = base + timedelta(minutes=offset_minutes)
    ep = EpisodeRecord(agent_id="test-agent")
    ep.timestamp = ts.isoformat()
    ep.infrastructure_failure = infrastructure_failure
    ep.goal_achieved = goal_achieved
    ep.max_prediction_error = max_prediction_error
    return ep


@pytest.fixture
def sample_config():
    return {
        "laws_domain": "digital",
        "harness_rules": ["r" + str(i) for i in range(20)],
        "monthly_budget_usd": 1000.0,
    }


# ── IRT 자동 탐지 테스트 ──────────────────────────────────────


class TestIRTAutoDetection:
    def test_no_incidents_returns_zero(self):
        episodes = [
            make_episode(0, goal_achieved=True, max_prediction_error=0.05),
            make_episode(5, goal_achieved=True, max_prediction_error=0.03),
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt(episodes)
        assert result.n_incidents == 0
        assert result.irt_minutes == pytest.approx(0.0)
        assert result.irt_ok is True

    def test_infrastructure_failure_detected_as_incident(self):
        episodes = [
            make_episode(0, infrastructure_failure=True, goal_achieved=False),
            make_episode(10, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt(episodes)
        assert result.n_incidents == 1
        assert len(result.incidents) == 1

    def test_high_prediction_error_detected_as_incident(self):
        episodes = [
            make_episode(0, max_prediction_error=0.30),  # > ece_crit=0.20
            make_episode(7, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker(ece_crit=0.20)
        result = tracker.compute_irt(episodes)
        assert result.n_incidents == 1

    def test_multiple_incidents_detected(self):
        episodes = [
            make_episode(0, infrastructure_failure=True, goal_achieved=False),
            make_episode(5, goal_achieved=True, max_prediction_error=0.05),
            make_episode(30, infrastructure_failure=True, goal_achieved=False),
            make_episode(40, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt(episodes)
        assert result.n_incidents == 2

    def test_unresolved_incident_counted_but_not_in_mean(self):
        episodes = [
            make_episode(0, infrastructure_failure=True, goal_achieved=False),
            make_episode(5, infrastructure_failure=True, goal_achieved=False),
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt(episodes)
        assert result.n_incidents >= 1
        assert result.irt_minutes == pytest.approx(0.0)  # 회복 없으니 평균 0

    def test_empty_episodes_returns_default(self):
        tracker = IncidentTracker()
        result = tracker.compute_irt([])
        assert result.irt_minutes == pytest.approx(0.0)
        assert result.n_incidents == 0
        assert result.irt_ok is True


# ── IRT 회복 시간 측정 테스트 ─────────────────────────────────


class TestIRTRecoveryTiming:
    def test_5_minute_recovery(self):
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, infrastructure_failure=True, goal_achieved=False),
            make_episode(5, base=base, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker(ece_warn=0.10)
        result = tracker.compute_irt(episodes)
        assert result.irt_minutes == pytest.approx(5.0, abs=0.05)

    def test_10_minute_recovery_is_not_ok(self):
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, infrastructure_failure=True, goal_achieved=False),
            make_episode(10, base=base, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker(irt_ok_minutes=5.0)
        result = tracker.compute_irt(episodes)
        assert result.irt_minutes == pytest.approx(10.0, abs=0.05)
        assert result.irt_ok is False

    def test_average_over_multiple_incidents(self):
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, infrastructure_failure=True, goal_achieved=False),
            make_episode(4, base=base, goal_achieved=True, max_prediction_error=0.05),
            make_episode(30, base=base, infrastructure_failure=True, goal_achieved=False),
            make_episode(36, base=base, goal_achieved=True, max_prediction_error=0.05),
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt(episodes)
        assert result.n_incidents == 2
        assert result.irt_minutes == pytest.approx(5.0, abs=0.1)  # (4+6)/2 = 5

    def test_manual_record_api(self):
        tracker = IncidentTracker(irt_ok_minutes=5.0)
        tracker.record_incident("inc-1", start_ts=1000.0, severity="high")
        tracker.record_recovery("inc-1", recovery_ts=1180.0)  # 3분
        result = tracker.compute_irt([])
        assert result.n_incidents == 1
        assert result.irt_minutes == pytest.approx(3.0, abs=0.05)
        assert result.irt_ok is True

    def test_log_based_incident_events(self):
        logs = [
            {
                "event_type": "incident_start",
                "payload": {"incident_id": "i1", "ts": 1000.0},
            },
            {
                "event_type": "incident_recovery",
                "payload": {"incident_id": "i1", "ts": 1300.0},  # 5분
            },
        ]
        tracker = IncidentTracker()
        result = tracker.compute_irt([], logs)
        assert result.n_incidents == 1
        assert result.irt_minutes == pytest.approx(5.0, abs=0.05)


# ── WMUL SDR→ECE 회복 레이턴시 테스트 ────────────────────────


class TestWMULDriftToRecovery:
    def test_no_drift_returns_zero(self):
        episodes = [
            make_episode(0, max_prediction_error=0.05),
            make_episode(60, max_prediction_error=0.03),
        ]
        tracker = WMULTracker()
        result = tracker.compute_wmul(episodes)
        assert result.wmul_hours == pytest.approx(0.0)
        assert result.n_drift_events == 0
        assert result.wmul_ok is True

    def test_sdr_spike_then_recovery(self):
        base = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, max_prediction_error=0.30),  # SDR spike
            make_episode(12 * 60, base=base, max_prediction_error=0.05),  # 12시간 후 회복
        ]
        tracker = WMULTracker(sdr_threshold=0.15, ece_recovery=0.10)
        result = tracker.compute_wmul(episodes)
        assert result.n_drift_events == 1
        assert result.wmul_hours == pytest.approx(12.0, abs=0.01)
        assert result.wmul_ok is True  # 12h < ok_hours=24h

    def test_wmul_above_ok_threshold(self):
        base = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, max_prediction_error=0.25),
            make_episode(30 * 60, base=base, max_prediction_error=0.05),  # 30시간
        ]
        tracker = WMULTracker(wmul_ok_hours=24.0)
        result = tracker.compute_wmul(episodes)
        assert result.wmul_hours == pytest.approx(30.0, abs=0.01)
        assert result.wmul_ok is False

    def test_multiple_drift_events_averaged(self):
        base = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, max_prediction_error=0.20),  # drift 1 시작
            make_episode(12 * 60, base=base, max_prediction_error=0.05),  # 12h 회복
            make_episode(24 * 60, base=base, max_prediction_error=0.25),  # drift 2 시작
            make_episode(48 * 60, base=base, max_prediction_error=0.05),  # 24h 회복
        ]
        tracker = WMULTracker()
        result = tracker.compute_wmul(episodes)
        assert result.n_drift_events == 2
        assert result.wmul_hours == pytest.approx(18.0, abs=0.01)  # (12+24)/2 = 18

    def test_empty_episodes_returns_default(self):
        tracker = WMULTracker()
        result = tracker.compute_wmul([])
        assert result.wmul_hours == pytest.approx(0.0)
        assert result.n_drift_events == 0

    def test_log_based_drift_count(self):
        logs = [
            {"event_type": "reflect", "payload": {"recalibrated": True}},
            {"event_type": "reflect", "payload": {"recalibrated": True}},
            {"event_type": "reflect", "payload": {"recalibrated": False}},
        ]
        tracker = WMULTracker()
        result = tracker.compute_wmul([], logs)
        assert result.n_drift_events == 2  # recalibrated=True 이벤트 수


# ── MetricsCalculator 통합 테스트 ─────────────────────────────


class TestMetricsCalculatorIntegration:
    def test_irt_method_exists_and_returns_metric_score(self, sample_config):
        calc = MetricsCalculator(logs=[], config=sample_config)
        metric = calc.incident_recovery_time()
        assert metric.name == "Incident Recovery Time"
        assert metric.value >= 0.0
        assert metric.unit == "minutes"
        assert metric.status in ("ok", "warning", "critical")

    def test_wmul_method_exists_and_returns_metric_score(self, sample_config):
        calc = MetricsCalculator(logs=[], config=sample_config)
        metric = calc.world_model_update_latency()
        assert metric.name == "WM Update Latency"
        assert metric.value >= 0.0
        assert metric.unit == "hours"

    def test_irt_with_episodes(self, sample_config):
        base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, infrastructure_failure=True, goal_achieved=False),
            make_episode(3, base=base, goal_achieved=True, max_prediction_error=0.05),
        ]
        calc = MetricsCalculator(logs=[], config=sample_config, episodes=episodes)
        metric = calc.incident_recovery_time()
        assert metric.value == pytest.approx(3.0, abs=0.05)
        assert metric.status == "ok"  # 3 min < 5 min threshold

    def test_wmul_with_episodes(self, sample_config):
        base = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        episodes = [
            make_episode(0, base=base, max_prediction_error=0.20),
            make_episode(10 * 60, base=base, max_prediction_error=0.05),
        ]
        calc = MetricsCalculator(logs=[], config=sample_config, episodes=episodes)
        metric = calc.world_model_update_latency()
        assert metric.value == pytest.approx(10.0, abs=0.01)
        assert metric.status == "ok"  # 10h < 24h threshold


# ── 15개 지표 100% 자동화 확인 테스트 ─────────────────────────


class TestFifteenMetrics100Percent:
    def test_scan_engine_returns_15_metrics(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )
        assert len(all_metrics) == 15

    def test_all_metrics_have_values(self, sample_config):
        """15개 지표 모두 None이 아닌 값을 가져야 한다 (수동 입력 0개)."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )
        for m in all_metrics:
            assert m.value is not None, f"Metric '{m.name}' has None value"

    def test_irt_in_operational_health(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")
        names = [m.name for m in report.operational_health.metrics]
        assert "Incident Recovery Time" in names

    def test_wmul_in_operational_health(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")
        names = [m.name for m in report.operational_health.metrics]
        assert "WM Update Latency" in names

    def test_no_duplicate_metrics(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        all_names = [
            m.name
            for m in (
                report.world_model_quality.metrics
                + report.agency_level.metrics
                + report.operational_health.metrics
            )
        ]
        assert len(all_names) == len(set(all_names)), "중복 지표 이름 발견"

    def test_default_irt_status_ok(self, sample_config):
        """인시던트 없으면 IRT = 0분 → ok 상태."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")
        irt_metric = next(
            m for m in report.operational_health.metrics if m.name == "Incident Recovery Time"
        )
        assert irt_metric.value == pytest.approx(0.0)
        assert irt_metric.status == "ok"

    def test_default_wmul_status_ok(self, sample_config):
        """드리프트 없으면 WMUL = 0시간 → ok 상태."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")
        wmul_metric = next(
            m for m in report.operational_health.metrics if m.name == "WM Update Latency"
        )
        assert wmul_metric.value == pytest.approx(0.0)
        assert wmul_metric.status == "ok"

    def test_parse_ts_utility(self):
        ts_str = "2026-06-01T12:00:00+00:00"
        ts = _parse_ts(ts_str)
        assert ts > 0
        assert ts == pytest.approx(datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC).timestamp())

    def test_parse_ts_invalid_returns_zero(self):
        assert _parse_ts("invalid") == pytest.approx(0.0)
        assert _parse_ts("") == pytest.approx(0.0)
