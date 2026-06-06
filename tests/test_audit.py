"""Sprint 6-B: AuditLogger + AuditMiddleware + GET /v1/audit/events 테스트."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from hachillesworld.api.server import app
from hachillesworld.audit.logger import AuditEvent, AuditLogger
from hachillesworld.storage.memory import InMemoryRepository

TEST_KEY = "dev-key-insecure"
ADMIN_KEY = "dev-admin-insecure"
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}
ADMIN_AUTH = {"Authorization": f"Bearer {ADMIN_KEY}"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _scan_payload(agent_name: str = "audit-agent") -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "logs": [{"event_type": "plan", "payload": {"uncertainty": 0.1}}],
        "config": {},
    }


# ---------------------------------------------------------------------------
# AuditEvent + AuditLogger 단위 테스트
# ---------------------------------------------------------------------------


def test_audit_event_fields():
    """AuditEvent.create()가 올바른 필드를 생성한다."""
    event = AuditEvent.create(
        actor="dev-key-",
        action="scan",
        resource="my-agent",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=128,
        response_size_bytes=0,
        duration_ms=12.5,
    )
    assert event.actor == "dev-key-"
    assert event.action == "scan"
    assert event.outcome == "success"
    assert len(event.event_id) > 0
    assert "T" in event.timestamp  # ISO8601 포함


def test_audit_logger_log_and_query():
    """AuditLogger.log() → query() 기본 동작."""
    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    event = AuditEvent.create(
        actor="actor1",
        action="scan",
        resource="agent-1",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=0,
        response_size_bytes=0,
        duration_ms=5.0,
    )
    logger.log(event)

    results = logger.query()
    assert len(results) == 1
    assert results[0].actor == "actor1"
    assert results[0].action == "scan"


def test_audit_query_by_actor():
    """actor 필터로 특정 액터의 이벤트만 조회된다."""
    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    for actor in ("alice---", "bob-----", "alice---"):
        logger.log(
            AuditEvent.create(
                actor=actor,
                action="scan",
                resource="",
                outcome="success",
                ip_address="127.0.0.1",
                request_size_bytes=0,
                response_size_bytes=0,
                duration_ms=1.0,
            )
        )

    alice_events = logger.query(actor="alice---")
    assert len(alice_events) == 2
    assert all(e.actor == "alice---" for e in alice_events)


def test_audit_query_by_action():
    """action 필터로 특정 액션만 조회된다."""
    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    for action in ("scan", "interpret", "scan", "drift.record"):
        logger.log(
            AuditEvent.create(
                actor="actor1",
                action=action,
                resource="",
                outcome="success",
                ip_address="127.0.0.1",
                request_size_bytes=0,
                response_size_bytes=0,
                duration_ms=1.0,
            )
        )

    scan_events = logger.query(action="scan")
    assert len(scan_events) == 2
    assert all(e.action == "scan" for e in scan_events)


def test_audit_query_time_range():
    """from_ts 필터로 특정 시각 이후 이벤트만 조회된다."""
    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    # 과거 이벤트 (timestamp를 직접 지정)
    past = AuditEvent(
        event_id="old-1",
        timestamp="2026-01-01T00:00:00+00:00",
        actor="a",
        action="scan",
        resource="",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=0,
        response_size_bytes=0,
        duration_ms=1.0,
    )
    recent = AuditEvent.create(
        actor="a",
        action="scan",
        resource="",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=0,
        response_size_bytes=0,
        duration_ms=1.0,
    )
    logger.log(past)
    logger.log(recent)

    filtered = logger.query(from_ts="2026-06-01T00:00:00+00:00")
    assert all(e.timestamp >= "2026-06-01T00:00:00+00:00" for e in filtered)
    assert len(filtered) >= 1


def test_audit_query_limit():
    """limit 파라미터로 반환 개수가 제한된다."""
    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    for _i in range(20):
        logger.log(
            AuditEvent.create(
                actor="x",
                action="scan",
                resource="",
                outcome="success",
                ip_address="127.0.0.1",
                request_size_bytes=0,
                response_size_bytes=0,
                duration_ms=1.0,
            )
        )

    assert len(logger.query(limit=5)) == 5
    assert len(logger.query(limit=100)) == 20


# ---------------------------------------------------------------------------
# 미들웨어 — API 호출 시 자동 로깅
# ---------------------------------------------------------------------------


def test_audit_event_logged_on_scan(client: TestClient) -> None:
    """POST /v1/scan 후 감사 이벤트가 자동 기록된다."""
    client.post("/v1/scan", json=_scan_payload("audit-scan-1"), headers=AUTH)

    resp = client.get("/v1/audit/events", headers=ADMIN_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    actions = [e["action"] for e in data["events"]]
    assert any("scan" in a for a in actions)


def test_audit_actor_extraction(client: TestClient) -> None:
    """Authorization 헤더에서 API key 앞 8자가 actor로 기록된다."""
    client.post("/v1/scan", json=_scan_payload("audit-actor-1"), headers=AUTH)

    resp = client.get("/v1/audit/events", headers=ADMIN_AUTH)
    data = resp.json()
    # TEST_KEY = "dev-key-insecure" → 앞 8자 = "dev-key-"
    actors = [e["actor"] for e in data["events"]]
    assert any(a == "dev-key-" for a in actors)


def test_audit_outcome_success(client: TestClient) -> None:
    """성공한 요청은 outcome='success'로 기록된다."""
    client.post("/v1/scan", json=_scan_payload("audit-outcome-1"), headers=AUTH)

    resp = client.get("/v1/audit/events", headers=ADMIN_AUTH)
    data = resp.json()
    scan_events = [e for e in data["events"] if e["action"] == "scan"]
    assert any(e["outcome"] == "success" for e in scan_events)


def test_audit_outcome_not_found(client: TestClient) -> None:
    """404 응답은 outcome='not_found'로 기록된다."""
    client.get("/v1/agents/nonexistent-agent-zz/next-actions", headers=AUTH)

    resp = client.get("/v1/audit/events", headers=ADMIN_AUTH)
    data = resp.json()
    not_found = [e for e in data["events"] if e["outcome"] == "not_found"]
    assert len(not_found) >= 1


# ---------------------------------------------------------------------------
# 감사 로그 엔드포인트 — admin 전용 접근 제어
# ---------------------------------------------------------------------------


def test_audit_admin_only_access(client: TestClient) -> None:
    """일반 API key로 GET /v1/audit/events 접근 시 403을 반환한다."""
    resp = client.get("/v1/audit/events", headers=AUTH)
    assert resp.status_code == 403


def test_audit_admin_access_allowed(client: TestClient) -> None:
    """admin API key로 GET /v1/audit/events 접근 시 200을 반환한다."""
    resp = client.get("/v1/audit/events", headers=ADMIN_AUTH)
    assert resp.status_code == 200


def test_audit_no_auth_returns_403(client: TestClient) -> None:
    """인증 없이 GET /v1/audit/events 접근 시 403을 반환한다."""
    resp = client.get("/v1/audit/events")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# SQLite 영구 스토리지 — 재시작 후 로그 유지
# ---------------------------------------------------------------------------


def test_audit_sqlite_persistence(tmp_path: "pytest.TempPathFactory") -> None:
    """SQLiteRepository에 저장한 감사 이벤트가 재시작 후에도 유지된다."""
    from hachillesworld.storage.sqlite import SQLiteRepository

    db_path = str(tmp_path / "audit_test.db")

    # 이벤트 저장
    repo = SQLiteRepository(db_path)
    event = AuditEvent.create(
        actor="test-act",
        action="scan",
        resource="my-agent",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=100,
        response_size_bytes=0,
        duration_ms=42.0,
    )
    repo.save_audit_event(event)
    repo.close()

    # 재연결 후 조회
    repo2 = SQLiteRepository(db_path)
    events = repo2.get_audit_events()
    repo2.close()

    assert len(events) == 1
    assert events[0].event_id == event.event_id
    assert events[0].actor == "test-act"
    assert events[0].action == "scan"
    assert events[0].duration_ms == pytest.approx(42.0)


def test_audit_sqlite_filtering(tmp_path: "pytest.TempPathFactory") -> None:
    """SQLiteRepository.get_audit_events()가 actor/action 필터를 지원한다."""
    from hachillesworld.storage.sqlite import SQLiteRepository

    db_path = str(tmp_path / "audit_filter.db")
    repo = SQLiteRepository(db_path)

    for actor, action in [
        ("alice---", "scan"),
        ("bob-----", "interpret"),
        ("alice---", "interpret"),
    ]:
        repo.save_audit_event(
            AuditEvent.create(
                actor=actor,
                action=action,
                resource="",
                outcome="success",
                ip_address="127.0.0.1",
                request_size_bytes=0,
                response_size_bytes=0,
                duration_ms=1.0,
            )
        )

    alice_events = repo.get_audit_events(actor="alice---")
    assert len(alice_events) == 2

    scan_events = repo.get_audit_events(action="scan")
    assert len(scan_events) == 1

    repo.close()
