"""Sprint 3-A — HAW API 엔드포인트 테스트."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from hachillesworld.api.server import app
from hachillesworld.operate.meta_harness import MetaHarness

TEST_KEY = "dev-key-insecure"
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _scan_payload(agent_name: str = "test-agent") -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "logs": [
            {"event_type": "plan", "payload": {"uncertainty": 0.1}},
            {"event_type": "observe", "payload": {"prediction_error": 0.05}},
        ],
        "config": {"laws_domain": "digital"},
    }


def test_scan_endpoint(client) -> None:
    """POST /v1/scan → DiagnosticReport JSON 반환."""
    resp = client.post("/v1/scan", json=_scan_payload(), headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "composite_score" in data
    assert "level" in data
    assert "level_label" in data
    assert data["agent_name"] == "test-agent"
    assert isinstance(data["composite_score"], float)


def test_has_timeseries(client) -> None:
    """스캔 후 GET /v1/agents/{id}/has → HAS 시계열 반환."""
    client.post("/v1/scan", json=_scan_payload("agent-has"), headers=AUTH)
    resp = client.get("/v1/agents/agent-has/has", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "agent-has"
    assert len(data["data_points"]) >= 1
    dp = data["data_points"][0]
    assert "has_score" in dp
    assert "level" in dp
    assert "timestamp" in dp


def test_drift_record_and_alert(client) -> None:
    """POST /v1/agents/{id}/drift/record → 드리프트 기록 + 경보 확인."""
    resp = client.post(
        "/v1/agents/agent-drift/drift/record",
        json={"predicted": {"x": 1.0}, "actual": {"x": 10.0}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["exceeded_threshold"] is True
    assert data["drift_value"] > 0.15
    assert data["alert"] is not None
    assert data["alert"]["drift_value"] > 0.15
    assert "recommended_action" in data["alert"]


def test_harness_approve_workflow(client) -> None:
    """하네스 승인 워크플로우 end-to-end."""
    meta = MetaHarness(auto_apply_threshold=1)
    meta.record_failure({"event_type": "observe:drift", "payload": {}})
    app.state.store.meta_harnesses["agent-harness"] = meta

    pending_resp = client.get("/v1/agents/agent-harness/harness/pending", headers=AUTH)
    assert pending_resp.status_code == 200
    rules = pending_resp.json()["rules"]
    assert len(rules) >= 1
    assert "rule_id" in rules[0]
    assert "condition" in rules[0]

    rule_id = rules[0]["rule_id"]
    approve_resp = client.post(
        f"/v1/harness/{rule_id}/approve",
        json={"approved": True},
        headers=AUTH,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"


def test_study_enroll(client) -> None:
    """POST /v1/study/enroll → study_id 반환."""
    resp = client.post(
        "/v1/study/enroll",
        json={"agent_id": "agent-study", "domain": "digital"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "study_id" in data
    assert data["study_id"].startswith("HAW-STUDY-")
    assert data["agent_id"] == "agent-study"
    assert "enrolled_at" in data


def test_api_key_auth(client) -> None:
    """인증 없는 요청 → 401 Unauthorized."""
    resp = client.get("/v1/agents/agent-1/has")
    assert resp.status_code == 401

    resp_bad = client.get(
        "/v1/agents/agent-1/has",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp_bad.status_code == 401
