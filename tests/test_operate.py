"""Operate 모듈 테스트."""

import time
import pytest
from hachillesworld.operate.monitor import DriftMonitor
from hachillesworld.operate.replay import ReplayDebugger
from hachillesworld.operate.meta_harness import MetaHarness
from hachillesworld.core.models import AgentEvent


class TestDriftMonitor:
    def test_no_drift_in_stable_agent(self):
        monitor = DriftMonitor("stable-agent", threshold=0.15)
        for _ in range(20):
            monitor.record(
                predicted={"inventory": 100.0, "demand": 90.0},
                actual={"inventory": 100.05, "demand": 90.03},  # 차이 0.04 < 임계값 0.15
            )
        assert monitor.is_stable()

    def test_drift_detected_in_unstable_agent(self):
        monitor = DriftMonitor("unstable-agent", threshold=0.15, alert_rate_threshold=0.20)
        for _ in range(10):
            monitor.record(
                predicted={"inventory": 100.0},
                actual={"inventory": 140.0},  # 40 차이 → drift
            )
        assert not monitor.is_stable()

    def test_alert_callback_called(self):
        alerts = []
        monitor = DriftMonitor("alert-agent", threshold=0.10, alert_rate_threshold=0.10)
        monitor.on_alert = alerts.append

        for _ in range(5):
            monitor.record(
                predicted={"x": 1.0},
                actual={"x": 10.0},
            )
        assert len(alerts) > 0
        assert alerts[0].agent_name == "alert-agent"

    def test_record_returns_drift_value(self):
        monitor = DriftMonitor("test", threshold=0.15)
        drift = monitor.record({"x": 1.0}, {"x": 2.0})
        assert drift == pytest.approx(1.0)

    def test_summary_keys(self):
        monitor = DriftMonitor("summary-test")
        monitor.record({"x": 1.0}, {"x": 1.1})
        summary = monitor.summary()
        assert "agent_name" in summary
        assert "recent_drift_rate" in summary
        assert "is_stable" in summary


class TestReplayDebugger:
    @pytest.fixture
    def episode_events(self):
        return [
            AgentEvent("agent", "plan", time.time(), {"planning_depth": 10, "uncertainty": 0.08}),
            AgentEvent("agent", "execute", time.time(), {"action": "query"}),
            AgentEvent(
                "agent",
                "observe",
                time.time(),
                {"prediction_error": 0.05, "error_within_uncertainty": True},
            ),
            AgentEvent(
                "agent",
                "observe",
                time.time(),
                {"prediction_error": 0.40, "error_within_uncertainty": False},
            ),  # 이상
            AgentEvent("agent", "reflect", time.time(), {"recalibrated": True}),
        ]

    def test_loads_events(self, episode_events):
        session = ReplayDebugger().load("ep-001", episode_events)
        assert session.episode_id == "ep-001"
        assert len(session.frames) == 5

    def test_detects_anomaly(self, episode_events):
        session = ReplayDebugger().load("ep-002", episode_events)
        assert len(session.anomaly_frames) > 0

    def test_identifies_failure_step(self, episode_events):
        session = ReplayDebugger().load("ep-003", episode_events)
        assert session.failure_step >= 0

    def test_root_cause_set(self, episode_events):
        session = ReplayDebugger().load("ep-004", episode_events)
        assert len(session.root_cause) > 0

    def test_no_anomaly_in_clean_log(self):
        clean = [
            AgentEvent("agent", "plan", time.time(), {"uncertainty": 0.05}),
            AgentEvent("agent", "execute", time.time(), {}),
            AgentEvent("agent", "observe", time.time(), {"prediction_error": 0.05}),
        ]
        session = ReplayDebugger().load("ep-clean", clean)
        assert len(session.anomaly_frames) == 0
        assert session.failure_step == -1

    def test_dict_events_accepted(self):
        dict_events = [
            {"agent_name": "a", "event_type": "plan", "timestamp": time.time(), "payload": {}},
        ]
        session = ReplayDebugger().load("ep-dict", dict_events)
        assert len(session.frames) == 1


class TestMetaHarness:
    def test_records_failure_pattern(self):
        meta = MetaHarness(auto_apply_threshold=3)
        event = {"event_type": "observe:drift", "payload": {"description": "드리프트 반복"}}
        for _ in range(3):
            meta.record_failure(event)
        assert len(meta.get_pending_rules()) > 0

    def test_below_threshold_no_pending_rules(self):
        meta = MetaHarness(auto_apply_threshold=10)
        event = {"event_type": "observe:drift", "payload": {}}
        for _ in range(5):
            meta.record_failure(event)
        assert len(meta.get_pending_rules()) == 0

    def test_approve_rule(self):
        meta = MetaHarness(auto_apply_threshold=1)
        event = {"event_type": "drift", "payload": {}}
        meta.record_failure(event)
        rules = meta.get_pending_rules()
        if rules:
            ok = meta.approve_rule(rules[0].rule_id)
            assert ok

    def test_reject_rule(self):
        meta = MetaHarness(auto_apply_threshold=1)
        event = {"event_type": "drift", "payload": {}}
        meta.record_failure(event)
        rules = meta.get_pending_rules()
        if rules:
            ok = meta.reject_rule(rules[0].rule_id)
            assert ok
            assert len(meta.get_pending_rules()) == 0

    def test_summary_structure(self):
        meta = MetaHarness()
        summary = meta.summary()
        assert "total_patterns" in summary
        assert "pending_rules" in summary
        assert "applied_rules" in summary
        assert "top_patterns" in summary
