"""HAWRepository Protocol — 스토리지 추상 인터페이스."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from hachillesworld.core.models import DiagnosticReport


@runtime_checkable
class HAWRepository(Protocol):
    """HAchillesWorld 영구 스토리지 추상 인터페이스.

    구현체: InMemoryRepository (테스트), SQLiteRepository (로컬), PostgreSQLRepository (프로덕션).
    """

    def save_report(self, agent_id: str, report: DiagnosticReport) -> None:
        """진단 보고서 저장. 동일 agent_id의 이력으로 누적된다."""
        ...

    def get_latest_report(self, agent_id: str) -> DiagnosticReport | None:
        """에이전트의 가장 최근 진단 보고서 반환. 없으면 None."""
        ...

    def get_has_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """HAS 시계열 이력 반환 (최신순). 각 항목: {timestamp, has_score, level}."""
        ...

    def save_drift_record(self, agent_id: str, drift_val: float, ts: str) -> None:
        """드리프트 측정값 저장."""
        ...

    def get_drift_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """드리프트 이력 반환 (최신순). 각 항목: {timestamp, drift_value}."""
        ...

    def save_audit_event(self, event: Any) -> None:
        """감사 이벤트 저장. event는 AuditEvent 인스턴스여야 한다."""
        ...

    def get_audit_events(
        self,
        actor: str | None = None,
        action: str | None = None,
        from_ts: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        """감사 이벤트 목록 반환 (최신순). actor/action/from_ts로 필터링 가능."""
        ...
