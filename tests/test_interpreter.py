"""Sprint 6-A: HASInterpreter + MLflow + API 엔드포인트 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from hachillesworld.api.server import app
from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
    MetricScore,
)
from hachillesworld.interpret.has_interpreter import (
    ActionItem,
    HASInterpretation,
    HASInterpreter,
)

TEST_KEY = "dev-key-insecure"
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _metric(name: str, value: float, threshold: float, status: str = "ok") -> MetricScore:
    return MetricScore(name=name, value=value, threshold=threshold, status=status)


def _make_report(
    wmq_score: float = 85.0,
    alm_score: float = 80.0,
    ohm_score: float = 75.0,
    *,
    extra_metrics: list[MetricScore] | None = None,
    agent_name: str = "test-agent",
) -> DiagnosticReport:
    """テスト用 DiagnosticReport を生成する."""
    base_metrics = extra_metrics or []
    return DiagnosticReport(
        agent_name=agent_name,
        level=Level.L2,
        level_progress=0.3,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore(
            name="World Model 품질",
            score=wmq_score,
            metrics=base_metrics + [_metric("Simulation Drift Rate", 0.03, 0.05, "ok")],
        ),
        agency_level=CategoryScore(
            name="에이전시 수준",
            score=alm_score,
            metrics=[_metric("Goal Consistency", 0.92, 0.90, "ok")],
        ),
        operational_health=CategoryScore(
            name="운영 건전성",
            score=ohm_score,
            metrics=[_metric("HITL Trigger Rate", 0.03, 0.05, "ok")],
        ),
    )


def _make_report_with_issues(
    critical: list[tuple[str, float, float]] | None = None,
    warning: list[tuple[str, float, float]] | None = None,
) -> DiagnosticReport:
    """critical/warning 지표가 포함된 보고서."""
    critical_metrics = [_metric(name, val, thr, "critical") for name, val, thr in (critical or [])]
    warning_metrics = [_metric(name, val, thr, "warning") for name, val, thr in (warning or [])]
    return DiagnosticReport(
        agent_name="issue-agent",
        level=Level.L1,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore(
            name="World Model 품질",
            score=55.0,
            metrics=critical_metrics,
        ),
        agency_level=CategoryScore(
            name="에이전시 수준",
            score=60.0,
            metrics=warning_metrics,
        ),
        operational_health=CategoryScore(
            name="운영 건전성",
            score=65.0,
            metrics=[],
        ),
    )


# ---------------------------------------------------------------------------
# HASInterpreter — 등급 판정
# ---------------------------------------------------------------------------


def test_grade_a_plus():
    """score=92 → A+ 등급, 우수 에이전트."""
    report = _make_report(wmq_score=92.0, alm_score=92.0, ohm_score=92.0)
    interp = HASInterpreter().interpret(report)
    assert interp.grade == "A+"
    assert interp.grade_label == "우수 에이전트"


def test_grade_a():
    """score=82 → A 등급."""
    report = _make_report(wmq_score=82.0, alm_score=82.0, ohm_score=82.0)
    interp = HASInterpreter().interpret(report)
    assert interp.grade == "A"


def test_grade_b():
    """score=73 → B 등급, 개선 필요."""
    report = _make_report(wmq_score=73.0, alm_score=73.0, ohm_score=73.0)
    interp = HASInterpreter().interpret(report)
    assert interp.grade == "B"
    assert interp.grade_label == "개선 필요"


def test_grade_c():
    """score=63 → C 등급."""
    report = _make_report(wmq_score=63.0, alm_score=63.0, ohm_score=63.0)
    interp = HASInterpreter().interpret(report)
    assert interp.grade == "C"


def test_grade_d():
    """score=45 → D 등급, 즉시 개선 필요."""
    report = _make_report(wmq_score=45.0, alm_score=45.0, ohm_score=45.0)
    interp = HASInterpreter().interpret(report)
    assert interp.grade == "D"
    assert interp.grade_label == "즉시 개선 필요"


# ---------------------------------------------------------------------------
# 배포 상태
# ---------------------------------------------------------------------------


def test_deployment_status_full():
    """score=92 → 전면 배포 가능."""
    report = _make_report(wmq_score=92.0, alm_score=92.0, ohm_score=92.0)
    interp = HASInterpreter().interpret(report)
    assert interp.deployment_status == "전면 배포 가능"


def test_deployment_status_supervised():
    """score=77 → 감독 하 운용."""
    report = _make_report(wmq_score=77.0, alm_score=77.0, ohm_score=77.0)
    interp = HASInterpreter().interpret(report)
    assert interp.deployment_status == "감독 하 운용"


def test_deployment_status_limited():
    """score=62 → 제한적 운용."""
    report = _make_report(wmq_score=62.0, alm_score=62.0, ohm_score=62.0)
    interp = HASInterpreter().interpret(report)
    assert interp.deployment_status == "제한적 운용"


def test_deployment_status_halt():
    """score=45 → 배포 중단 권고."""
    report = _make_report(wmq_score=45.0, alm_score=45.0, ohm_score=45.0)
    interp = HASInterpreter().interpret(report)
    assert interp.deployment_status == "배포 중단 권고"


# ---------------------------------------------------------------------------
# 액션 아이템 우선순위
# ---------------------------------------------------------------------------


def test_action_items_priority_critical_first():
    """critical 지표는 priority=1, warning은 priority=2로 생성된다."""
    report = _make_report_with_issues(
        critical=[("Simulation Drift Rate", 0.25, 0.05)],
        warning=[("Goal Consistency", 0.75, 0.90)],
    )
    interp = HASInterpreter().interpret(report)
    priorities = [a.priority for a in interp.next_actions]
    assert 1 in priorities  # critical 포함
    assert all(p in (1, 2) for p in priorities)


def test_action_items_max_three():
    """next_actions는 최대 3개까지만 반환한다."""
    report = _make_report_with_issues(
        critical=[
            ("Simulation Drift Rate", 0.30, 0.05),
            ("Calibration ECE", 0.25, 0.10),
            ("Counterfactual Accuracy", 0.40, 0.73),
            ("Planning Depth", 1.0, 5.0),
        ]
    )
    interp = HASInterpreter().interpret(report)
    assert len(interp.next_actions) <= 3


# ---------------------------------------------------------------------------
# top_issue — estimated_has_gain 최대 지표 선택
# ---------------------------------------------------------------------------


def test_top_issue_is_max_gain():
    """top_issue는 estimated_has_gain이 가장 높은 지표를 선택한다."""
    # Goal Consistency has_gain=4.5, Simulation Drift Rate has_gain=3.5
    report = _make_report_with_issues(
        critical=[
            ("Simulation Drift Rate", 0.25, 0.05),  # has_gain=3.5
            ("Goal Consistency", 0.50, 0.90),  # has_gain=4.5 (higher)
        ]
    )
    interp = HASInterpreter().interpret(report)
    assert "Goal Consistency" in interp.top_issue


def test_top_issue_no_issues():
    """이슈가 없으면 '개선 필요 지표 없음'을 반환한다."""
    report = _make_report(wmq_score=95.0, alm_score=95.0, ohm_score=95.0)
    interp = HASInterpreter().interpret(report)
    assert interp.top_issue == "개선 필요 지표 없음"


# ---------------------------------------------------------------------------
# percentile
# ---------------------------------------------------------------------------


def test_percentile_top_5():
    """score=96 → 상위 5%."""
    report = _make_report(wmq_score=96.0, alm_score=96.0, ohm_score=96.0)
    interp = HASInterpreter().interpret(report)
    assert interp.percentile == 5.0


def test_percentile_top_50():
    """score=72 → 상위 50%."""
    report = _make_report(wmq_score=72.0, alm_score=72.0, ohm_score=72.0)
    interp = HASInterpreter().interpret(report)
    assert interp.percentile == 50.0


# ---------------------------------------------------------------------------
# estimated_improvement
# ---------------------------------------------------------------------------


def test_estimated_improvement_sum():
    """estimated_improvement는 상위 3개 액션의 has_gain 합이다."""
    report = _make_report_with_issues(
        critical=[
            ("Counterfactual Accuracy", 0.40, 0.73),
            ("Goal Consistency", 0.50, 0.90),
            ("Simulation Drift Rate", 0.25, 0.05),
        ]
    )
    interp = HASInterpreter().interpret(report)
    expected = sum(a.estimated_has_gain for a in interp.next_actions)
    assert interp.estimated_improvement == pytest.approx(expected)


# ---------------------------------------------------------------------------
# report.summary()
# ---------------------------------------------------------------------------


def test_summary_output_format():
    """report.summary()가 등급·배포 상태·즉시 조치를 포함하는지 확인."""
    report = _make_report(wmq_score=82.0, alm_score=82.0, ohm_score=82.0)
    summary = report.summary()
    assert "A등급" in summary or "A" in summary
    assert "양호 에이전트" in summary
    assert "즉시 조치" in summary


def test_summary_green_emoji():
    """A/A+ 등급은 🟢 이모지를 사용한다."""
    report = _make_report(wmq_score=92.0, alm_score=92.0, ohm_score=92.0)
    assert "🟢" in report.summary()


def test_summary_yellow_emoji():
    """B 등급은 🟡 이모지를 사용한다."""
    report = _make_report(wmq_score=73.0, alm_score=73.0, ohm_score=73.0)
    assert "🟡" in report.summary()


def test_summary_red_emoji():
    """C/D 등급은 🔴 이모지를 사용한다."""
    report = _make_report(wmq_score=45.0, alm_score=45.0, ohm_score=45.0)
    assert "🔴" in report.summary()


# ---------------------------------------------------------------------------
# API 엔드포인트 — POST /v1/agents/{id}/interpret
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    with TestClient(app) as c:
        yield c


def _scan_payload(agent_name: str = "interp-agent") -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "logs": [
            {"event_type": "plan", "payload": {"uncertainty": 0.2}},
            {"event_type": "observe", "payload": {"prediction_error": 0.08}},
        ],
        "config": {"laws_domain": "digital"},
    }


def test_interpretation_api_success(api_client: TestClient) -> None:
    """POST /v1/scan → POST /v1/agents/{id}/interpret 정상 동작."""
    api_client.post("/v1/scan", json=_scan_payload("interp-agent-01"), headers=AUTH)
    resp = api_client.post(
        "/v1/agents/interp-agent-01/interpret",
        json={},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "grade" in data
    assert "deployment_status" in data
    assert "next_actions" in data
    assert "estimated_improvement" in data
    assert data["grade"] in ("A+", "A", "B", "C", "D")


def test_interpretation_api_not_found(api_client: TestClient) -> None:
    """보고서 없는 에이전트에 interpret 요청 시 404 반환."""
    resp = api_client.post(
        "/v1/agents/nonexistent-agent-xyz/interpret",
        json={},
        headers=AUTH,
    )
    assert resp.status_code == 404


def test_next_actions_api(api_client: TestClient) -> None:
    """GET /v1/agents/{id}/next-actions 정상 동작."""
    api_client.post("/v1/scan", json=_scan_payload("actions-agent-01"), headers=AUTH)
    resp = api_client.get("/v1/agents/actions-agent-01/next-actions", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    assert "total_estimated_gain" in data
    assert data["agent_id"] == "actions-agent-01"
    assert isinstance(data["total_estimated_gain"], float)


def test_next_actions_api_not_found(api_client: TestClient) -> None:
    """보고서 없는 에이전트에 next-actions 요청 시 404 반환."""
    resp = api_client.get("/v1/agents/ghost-agent-xyz/next-actions", headers=AUTH)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# MLflow 로깅
# ---------------------------------------------------------------------------


def _make_mlflow_mock() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """mlflow 모듈 mock과 주요 함수 mock을 반환한다."""
    mock_mlflow = MagicMock()
    mock_run_ctx = MagicMock()
    mock_run_ctx.__enter__ = MagicMock(return_value=mock_run_ctx)
    mock_run_ctx.__exit__ = MagicMock(return_value=False)
    mock_mlflow.start_run.return_value = mock_run_ctx
    return mock_mlflow, mock_mlflow.log_metric, mock_mlflow.log_param, mock_mlflow.start_run


def test_mlflow_logging() -> None:
    """MLflowHASLogger.log_report()가 mlflow API를 올바르게 호출한다."""
    import sys

    from hachillesworld.integrations.mlflow_logger import MLflowHASLogger

    report = _make_report(
        wmq_score=80.0,
        alm_score=75.0,
        ohm_score=70.0,
        agent_name="mlflow-agent",
    )

    mock_mlflow, mock_metric, mock_param, mock_start = _make_mlflow_mock()
    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        MLflowHASLogger().log_report(report)

    mock_start.assert_called_once()
    # HAS 종합 점수 기록 확인
    metric_keys = [c[0][0] for c in mock_metric.call_args_list]
    assert "has_score" in metric_keys
    assert "wmq_score" in metric_keys
    assert "alm_score" in metric_keys
    assert "ohm_score" in metric_keys

    # 파라미터 기록 확인
    param_keys = [c[0][0] for c in mock_param.call_args_list]
    assert "level" in param_keys
    assert "domain" in param_keys
    assert "has_version" in param_keys


def test_mlflow_logging_no_mlflow() -> None:
    """mlflow 미설치 시 ImportError가 발생한다."""
    import sys

    from hachillesworld.integrations.mlflow_logger import MLflowHASLogger

    report = _make_report()
    with patch.dict(sys.modules, {"mlflow": None}):  # type: ignore[dict-item]
        with pytest.raises((ImportError, TypeError)):
            MLflowHASLogger().log_report(report)


def test_mlflow_logs_all_15_metrics() -> None:
    """15개 개별 지표가 모두 haw_ 접두어로 기록된다."""
    import sys

    from hachillesworld.integrations.mlflow_logger import MLflowHASLogger

    metrics_wmq = [
        _metric("Prediction Error Rate", 0.1, 0.15),
        _metric("Calibration ECE", 0.05, 0.10),
        _metric("Simulation Drift Rate", 0.03, 0.05),
        _metric("OOD Detection Rate", 0.8, 0.70),
        _metric("Planning Depth", 6.0, 5.0),
    ]
    metrics_alm = [
        _metric("Self-Correction Rate", 0.15, 0.10),
        _metric("Counterfactual Accuracy", 0.8, 0.73),
        _metric("Goal Consistency", 0.92, 0.90),
        _metric("Env Adaptation Speed", 8.0, 10.0),
        _metric("Harness Coverage", 22.0, 20.0),
    ]
    metrics_ohm = [
        _metric("WM Update Latency", 12.0, 24.0),
        _metric("Incident Recovery Time", 3.0, 5.0),
        _metric("HITL Trigger Rate", 0.03, 0.05),
        _metric("Harness Violation Attempts", 0.0, 0.0),
        _metric("Checkpoint Recovery Rate", 0.99, 0.98),
    ]
    report = DiagnosticReport(
        agent_name="full-agent",
        level=Level.L2,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore("World Model 품질", 85.0, metrics_wmq),
        agency_level=CategoryScore("에이전시 수준", 82.0, metrics_alm),
        operational_health=CategoryScore("운영 건전성", 80.0, metrics_ohm),
    )

    mock_mlflow, mock_metric, _, _ = _make_mlflow_mock()
    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        MLflowHASLogger().log_report(report)

    metric_keys = [c[0][0] for c in mock_metric.call_args_list]
    haw_keys = [k for k in metric_keys if k.startswith("haw_")]
    assert len(haw_keys) == 15
