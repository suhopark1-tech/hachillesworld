"""Sprint 5-C: 스토리지 레이어 테스트 — InMemory + SQLite."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
)
from hachillesworld.storage.base import HAWRepository
from hachillesworld.storage.memory import InMemoryRepository
from hachillesworld.storage.sqlite import SQLiteRepository

# ── 픽스처 ─────────────────────────────────────────────────────────────


def _make_report(agent_name: str = "test-agent", score: float = 70.0) -> DiagnosticReport:
    s = score
    return DiagnosticReport(
        agent_name=agent_name,
        level=Level.L2,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore(name="WMQ", score=s),
        agency_level=CategoryScore(name="ALM", score=s - 5),
        operational_health=CategoryScore(name="OHM", score=s + 5),
        recommendations=[],
    )


@pytest.fixture(params=["memory", "sqlite"])
def repo(request: pytest.FixtureRequest, tmp_path):
    """InMemoryRepository + SQLiteRepository 동일 테스트 파라미터화."""
    if request.param == "memory":
        yield InMemoryRepository()
    else:
        r = SQLiteRepository(db_path=str(tmp_path / "test_haw.db"))
        yield r
        r.close()


@pytest.fixture
def sqlite_repo(tmp_path) -> SQLiteRepository:
    """SQLiteRepository 단독 픽스처 (재연결 테스트 등)."""
    r = SQLiteRepository(db_path=str(tmp_path / "haw_test.db"))
    yield r
    r.close()


@pytest.fixture
def memory_repo() -> InMemoryRepository:
    return InMemoryRepository()


# ── 기본 CRUD ───────────────────────────────────────────────────────────


class TestSaveAndRetrieveReport:
    """test_save_and_retrieve_report: 저장-조회 기본 동작."""

    def test_save_and_get_latest(self, repo: HAWRepository) -> None:
        report = _make_report("agent-1")
        repo.save_report("agent-1", report)
        retrieved = repo.get_latest_report("agent-1")
        assert retrieved is not None
        assert retrieved.agent_name == "agent-1"

    def test_get_latest_returns_none_for_unknown(self, repo: HAWRepository) -> None:
        assert repo.get_latest_report("nonexistent") is None

    def test_get_latest_returns_last_saved(self, repo: HAWRepository) -> None:
        repo.save_report("a", _make_report("a", score=60.0))
        time.sleep(0.01)  # 타임스탬프 분리
        repo.save_report("a", _make_report("a", score=80.0))
        latest = repo.get_latest_report("a")
        assert latest is not None
        assert abs(latest.composite_score - _make_report("a", 80.0).composite_score) < 0.1

    def test_different_agents_isolated(self, repo: HAWRepository) -> None:
        repo.save_report("agent-A", _make_report("agent-A"))
        repo.save_report("agent-B", _make_report("agent-B"))
        assert repo.get_latest_report("agent-A") is not None
        assert repo.get_latest_report("agent-B") is not None
        assert repo.get_latest_report("agent-C") is None


class TestHASHistoryOrdering:
    """test_has_history_ordering: HAS 이력 최신순 반환 검증."""

    def test_history_returns_all_records(self, repo: HAWRepository) -> None:
        for _ in range(3):
            repo.save_report("agent-1", _make_report("agent-1"))
            time.sleep(0.01)
        history = repo.get_has_history("agent-1", limit=10)
        assert len(history) == 3

    def test_history_newest_first(self, repo: HAWRepository) -> None:
        for _ in range(3):
            repo.save_report("agent-1", _make_report("agent-1"))
            time.sleep(0.01)
        history = repo.get_has_history("agent-1")
        timestamps = [h["timestamp"] for h in history]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_history_limit_applied(self, repo: HAWRepository) -> None:
        for _ in range(5):
            repo.save_report("agent-1", _make_report("agent-1"))
            time.sleep(0.01)
        history = repo.get_has_history("agent-1", limit=3)
        assert len(history) == 3

    def test_history_contains_required_keys(self, repo: HAWRepository) -> None:
        repo.save_report("agent-1", _make_report("agent-1"))
        history = repo.get_has_history("agent-1")
        assert len(history) == 1
        entry = history[0]
        assert "timestamp" in entry
        assert "has_score" in entry
        assert "level" in entry

    def test_history_empty_for_unknown_agent(self, repo: HAWRepository) -> None:
        assert repo.get_has_history("unknown") == []


class TestDriftHistory:
    """test_drift_history: 드리프트 기록 저장·조회."""

    def test_save_and_retrieve_drift(self, repo: HAWRepository) -> None:
        ts = datetime.now(UTC).isoformat()
        repo.save_drift_record("agent-1", drift_val=0.08, ts=ts)
        history = repo.get_drift_history("agent-1")
        assert len(history) == 1
        assert abs(history[0]["drift_value"] - 0.08) < 1e-9
        assert history[0]["timestamp"] == ts

    def test_drift_history_empty(self, repo: HAWRepository) -> None:
        assert repo.get_drift_history("unknown") == []

    def test_multiple_drift_records(self, repo: HAWRepository) -> None:
        for i in range(3):
            ts = datetime.now(UTC).isoformat()
            repo.save_drift_record("agent-1", drift_val=float(i) * 0.01, ts=ts)
            time.sleep(0.01)
        history = repo.get_drift_history("agent-1")
        assert len(history) == 3


# ── SQLite 전용 테스트 ──────────────────────────────────────────────────


class TestSQLiteSurvivesReconnect:
    """test_sqlite_survives_reconnect: 재연결 후 데이터 유지 확인."""

    def test_data_persists_after_reconnect(self, tmp_path) -> None:
        db_path = str(tmp_path / "persist_test.db")

        # 첫 번째 연결: 데이터 저장
        repo1 = SQLiteRepository(db_path=db_path)
        report = _make_report("agent-persist")
        repo1.save_report("agent-persist", report)
        repo1.close()

        # 두 번째 연결: 데이터 복원 확인
        repo2 = SQLiteRepository(db_path=db_path)
        retrieved = repo2.get_latest_report("agent-persist")
        repo2.close()

        assert retrieved is not None
        assert retrieved.agent_name == "agent-persist"

    def test_history_persists_after_reconnect(self, tmp_path) -> None:
        db_path = str(tmp_path / "history_test.db")

        repo1 = SQLiteRepository(db_path=db_path)
        for i in range(3):
            repo1.save_report("agent-x", _make_report("agent-x", score=float(60 + i * 5)))
            time.sleep(0.01)
        repo1.close()

        repo2 = SQLiteRepository(db_path=db_path)
        history = repo2.get_has_history("agent-x")
        repo2.close()

        assert len(history) == 3

    def test_drift_persists_after_reconnect(self, tmp_path) -> None:
        db_path = str(tmp_path / "drift_test.db")

        repo1 = SQLiteRepository(db_path=db_path)
        repo1.save_drift_record("agent-d", 0.12, datetime.now(UTC).isoformat())
        repo1.close()

        repo2 = SQLiteRepository(db_path=db_path)
        history = repo2.get_drift_history("agent-d")
        repo2.close()

        assert len(history) == 1
        assert abs(history[0]["drift_value"] - 0.12) < 1e-9


# ── Protocol 준수 검증 ──────────────────────────────────────────────────


class TestRepositoryProtocolCompliance:
    """test_repository_protocol_compliance: HAWRepository Protocol 준수 확인."""

    def test_memory_repo_is_haw_repository(self) -> None:
        repo = InMemoryRepository()
        assert isinstance(repo, HAWRepository)

    def test_sqlite_repo_is_haw_repository(self, tmp_path) -> None:
        repo = SQLiteRepository(db_path=str(tmp_path / "protocol_test.db"))
        assert isinstance(repo, HAWRepository)
        repo.close()

    def test_memory_repo_has_all_methods(self) -> None:
        repo = InMemoryRepository()
        assert callable(repo.save_report)
        assert callable(repo.get_latest_report)
        assert callable(repo.get_has_history)
        assert callable(repo.save_drift_record)
        assert callable(repo.get_drift_history)
        assert callable(repo.save_audit_event)
        assert callable(repo.get_audit_events)

    def test_sqlite_repo_has_all_methods(self, tmp_path) -> None:
        repo = SQLiteRepository(db_path=str(tmp_path / "methods_test.db"))
        assert callable(repo.save_report)
        assert callable(repo.get_latest_report)
        assert callable(repo.get_has_history)
        assert callable(repo.save_drift_record)
        assert callable(repo.get_drift_history)
        assert callable(repo.save_audit_event)
        assert callable(repo.get_audit_events)
        repo.close()


# ── Audit 이벤트 (Sprint 6-B 스텁) ─────────────────────────────────────


class TestAuditEventStub:
    """save_audit_event / get_audit_events 동작 확인 (Sprint 6-B)."""

    def test_save_and_get_audit_event(self, repo: HAWRepository) -> None:
        from hachillesworld.audit.logger import AuditEvent

        event = AuditEvent.create(
            actor="test-act",
            action="scan",
            resource="agent-1",
            outcome="success",
            ip_address="127.0.0.1",
            request_size_bytes=0,
            response_size_bytes=0,
            duration_ms=5.0,
        )
        repo.save_audit_event(event)
        events = repo.get_audit_events()
        assert len(events) >= 1

    def test_empty_audit_events(self, repo: HAWRepository) -> None:
        assert repo.get_audit_events() == []


# ── AppState 통합 테스트 ─────────────────────────────────────────────────


class TestAppStateWithRepository:
    """AppState가 repository를 통해 데이터를 저장·조회하는지 확인."""

    def test_record_has_delegates_to_repo(self) -> None:
        from hachillesworld.api.state import AppState

        repo = InMemoryRepository()
        store = AppState(repository=repo)
        report = _make_report("test-agent")
        store.record_has("test-agent", report)

        # repository에 직접 저장됐는지 확인
        assert repo.get_latest_report("test-agent") is not None

    def test_get_latest_report_delegates_to_repo(self) -> None:
        from hachillesworld.api.state import AppState

        repo = InMemoryRepository()
        store = AppState(repository=repo)
        report = _make_report("agent-2")
        repo.save_report("agent-2", report)

        retrieved = store.get_latest_report("agent-2")
        assert retrieved is not None
        assert retrieved.agent_name == "agent-2"

    def test_get_latest_report_none_for_unknown(self) -> None:
        from hachillesworld.api.state import AppState

        store = AppState(repository=InMemoryRepository())
        assert store.get_latest_report("unknown") is None

    def test_has_timeseries_returns_history(self) -> None:
        from hachillesworld.api.state import AppState

        repo = InMemoryRepository()
        store = AppState(repository=repo)
        for _ in range(3):
            store.record_has("agent-3", _make_report("agent-3"))
            time.sleep(0.01)
        history = store.get_has_timeseries("agent-3")
        assert len(history) == 3
