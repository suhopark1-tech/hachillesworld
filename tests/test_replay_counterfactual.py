"""Sprint 2-C — PAT-003 CounterfactualAnalyzer + RCA 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from hachillesworld.operate.monitor import DriftMonitor
from hachillesworld.operate.replay import (
    CounterfactualAnalyzer,
    CounterfactualReport,
    CounterfactualScenario,
    ReplayDebugger,
    ReplaySession,
    RootCauseAnalyzer,
)

# ─── 픽스처 헬퍼 ─────────────────────────────────────────────────────────────


def _make_events(
    include_drift: bool = True,
    include_plan_unc: bool = True,
    include_error: bool = True,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [
        {
            "agent_name": "test-agent",
            "event_type": "plan",
            "timestamp": 1000.0,
            "payload": {"uncertainty": 0.18, "goal": "test"},
        },
        {
            "agent_name": "test-agent",
            "event_type": "execute",
            "timestamp": 1001.0,
            "payload": {"action": "normal_action"},
        },
    ]
    if include_drift:
        events.append(
            {
                "agent_name": "test-agent",
                "event_type": "observe",
                "timestamp": 1002.0,
                "payload": {
                    "prediction_error": 0.31,
                    "predicted_state": {},
                    "actual_state": {},
                },
            }
        )
    if include_plan_unc:
        events.append(
            {
                "agent_name": "test-agent",
                "event_type": "plan",
                "timestamp": 1003.0,
                "payload": {"uncertainty": 0.62},
            }
        )
    if include_error:
        events.append(
            {
                "agent_name": "test-agent",
                "event_type": "error",
                "timestamp": 1010.0,
                "payload": {"error_message": "주문 실패"},
            }
        )
    return events


def _make_mock_client(scenarios_json: str | None = None) -> MagicMock:
    """Anthropic 클라이언트 Mock — 3개 시나리오 반환."""
    if scenarios_json is None:
        scenarios_json = (
            '{"scenarios": ['
            '{"scenario_id": 1, "alternative_action": "force_recalibration",'
            ' "expected_outcome": "드리프트 감소", "success_probability": 0.80},'
            '{"scenario_id": 2, "alternative_action": "trigger_hitl",'
            ' "expected_outcome": "인간 검토로 계획 수정", "success_probability": 0.90},'
            '{"scenario_id": 3, "alternative_action": "rollback_checkpoint",'
            ' "expected_outcome": "안전 상태 복구", "success_probability": 0.70}'
            '], "repair_suggestion": "IF prediction_error > 0.15: force_recalibration()"}'
        )
    mock = MagicMock()
    mock.messages.create.return_value.content = [MagicMock(text=scenarios_json)]
    return mock


# ─── 테스트 ───────────────────────────────────────────────────────────────────


def test_failure_step_detection() -> None:
    """실패 분기점 정확히 탐지 — max prediction_error 스텝."""
    debugger = ReplayDebugger()
    session = debugger.load(episode_id="ep-001", events=_make_events())

    # observe 이벤트(prediction_error=0.31)가 step 2에 위치
    failure_step = RootCauseAnalyzer.identify_failure_step(session)
    assert failure_step == 2


def test_counterfactual_generation_3_scenarios() -> None:
    """반사실 시나리오 정확히 3개 생성, 형식 검증."""
    debugger = ReplayDebugger()
    session = debugger.load(episode_id="ep-002", events=_make_events())

    analyzer = CounterfactualAnalyzer(anthropic_client=_make_mock_client())
    report = analyzer.analyze(session)

    assert isinstance(report, CounterfactualReport)
    assert len(report.counterfactuals) == 3
    for i, s in enumerate(report.counterfactuals, start=1):
        assert isinstance(s, CounterfactualScenario)
        assert s.scenario_id == i
        assert s.alternative_action != ""
        assert s.expected_outcome != ""
        assert 0.0 <= s.success_probability <= 1.0


def test_root_cause_world_model_error() -> None:
    """observe 이벤트 이상 → world_model_error 분류."""
    debugger = ReplayDebugger()
    events = [
        {
            "agent_name": "a",
            "event_type": "observe",
            "timestamp": 1.0,
            "payload": {"prediction_error": 0.5},
        }
    ]
    session = debugger.load(episode_id="ep-wm", events=events)

    failure_type = RootCauseAnalyzer.classify_failure_type(session, failure_step=0)
    assert failure_type == "world_model_error"


def test_root_cause_planning_failure() -> None:
    """plan 이벤트 이상 → planning_failure 분류."""
    debugger = ReplayDebugger()
    events = [
        {
            "agent_name": "a",
            "event_type": "plan",
            "timestamp": 1.0,
            "payload": {"uncertainty": 0.8},
        }
    ]
    session = debugger.load(episode_id="ep-plan", events=events)

    failure_type = RootCauseAnalyzer.classify_failure_type(session, failure_step=0)
    assert failure_type == "planning_failure"


def test_repair_suggestion_format() -> None:
    """수정 제안이 PAT-003 PR 형식을 포함하고, 코드 블록이 있다."""
    debugger = ReplayDebugger()
    session = debugger.load(episode_id="ep-repair", events=_make_events())

    analyzer = CounterfactualAnalyzer(anthropic_client=_make_mock_client())
    report = analyzer.analyze(session)

    assert report.repair_suggestion != ""
    pr_text = ReplayDebugger.auto_pr_suggestion(report)

    assert "```python" in pr_text
    assert "PAT-003" in pr_text
    assert f"Step {report.failure_step}" in pr_text
    assert report.failure_type in pr_text


def test_drift_to_replay_auto_link() -> None:
    """DriftMonitor → ReplayDebugger 자동 연동 — drift_log → ReplaySession."""
    monitor = DriftMonitor(agent_name="link-agent", threshold=0.15)
    monitor.record(predicted={"x": 1.0}, actual={"x": 1.5})  # drift=0.5 > 0.15 → 이상
    monitor.record(predicted={"x": 2.0}, actual={"x": 2.1})  # drift=0.1 — 정상

    debugger, session = ReplayDebugger.from_drift_monitor(
        monitor=monitor,
        episode_id="ep-drift",
        agent_name="link-agent",
    )

    assert isinstance(debugger, ReplayDebugger)
    assert isinstance(session, ReplaySession)
    assert session.episode_id == "ep-drift"
    assert len(session.frames) == 2

    # 첫 번째 observe 프레임: drift=0.5 > 0.15 → 이상 감지
    assert session.frames[0].is_anomaly
    assert not session.frames[1].is_anomaly
    assert session.failure_step == 0
