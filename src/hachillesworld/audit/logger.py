"""AuditLogger — 모든 API 호출을 감사 로그에 기록 (Sprint 6-B, C-7).

누가(actor) 언제(timestamp) 무엇을(action) 어떤 리소스에(resource)
어떤 결과로(outcome) 접근했는지를 불변 로그로 보존한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hachillesworld.storage.base import HAWRepository


@dataclass
class AuditEvent:
    """단일 API 호출에 대한 감사 이벤트."""

    event_id: str  # UUID4
    timestamp: str  # UTC ISO8601
    actor: str  # API key prefix (앞 8자) or "anonymous"
    action: str  # "scan" | "interpret" | "drift.record" | "harness.approve" | ...
    resource: str  # agent_id or group_id (없으면 "")
    outcome: str  # "success" | "not_found" | "unauthorized" | "forbidden" | "error"
    ip_address: str
    request_size_bytes: int
    response_size_bytes: int
    duration_ms: float

    @classmethod
    def create(
        cls,
        actor: str,
        action: str,
        resource: str,
        outcome: str,
        ip_address: str,
        request_size_bytes: int,
        response_size_bytes: int,
        duration_ms: float,
    ) -> "AuditEvent":
        """현재 시각으로 AuditEvent를 생성한다."""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            actor=actor,
            action=action,
            resource=resource,
            outcome=outcome,
            ip_address=ip_address,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            duration_ms=duration_ms,
        )


class AuditLogger:
    """모든 API 호출을 Repository에 감사 이벤트로 저장.

    AuditMiddleware가 자동으로 호출하므로 직접 사용할 필요는 없다.
    감사 로그 조회는 GET /v1/audit/events 엔드포인트를 사용한다.
    """

    def __init__(self, repository: "HAWRepository") -> None:
        self._repo = repository

    def log(self, event: AuditEvent) -> None:
        """감사 이벤트를 Repository에 저장한다."""
        self._repo.save_audit_event(event)

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        from_ts: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """감사 이벤트를 조회한다. 모든 파라미터는 선택적 필터다."""
        return self._repo.get_audit_events(
            actor=actor,
            action=action,
            from_ts=from_ts,
            limit=limit,
        )
