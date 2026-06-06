"""인메모리 레포지토리 — 테스트·개발 환경용, 재시작 시 소실."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hachillesworld.core.models import DiagnosticReport


class InMemoryRepository:
    """인메모리 HAWRepository 구현체.

    HAW_STORAGE=memory 환경변수 또는 테스트 픽스처에서 사용.
    프로세스 재시작 시 모든 데이터가 소실된다.
    """

    def __init__(self) -> None:
        # (timestamp, report) 쌍을 누적 저장
        self._reports: dict[str, list[tuple[str, DiagnosticReport]]] = {}
        self._drift: dict[str, list[dict[str, Any]]] = {}
        self._audit: list[Any] = []

    # ── Reports ──────────────────────────────────────────────

    def save_report(self, agent_id: str, report: DiagnosticReport) -> None:
        ts = datetime.now(UTC).isoformat()
        self._reports.setdefault(agent_id, []).append((ts, report))

    def get_latest_report(self, agent_id: str) -> DiagnosticReport | None:
        records = self._reports.get(agent_id)
        return records[-1][1] if records else None

    def get_has_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        records = self._reports.get(agent_id, [])
        result = [
            {
                "timestamp": ts,
                "has_score": round(r.composite_score, 2),
                "level": r.level_label,
            }
            for ts, r in records
        ]
        # 최신순으로 반환
        return list(reversed(result))[:limit]

    # ── Drift ─────────────────────────────────────────────────

    def save_drift_record(self, agent_id: str, drift_val: float, ts: str) -> None:
        self._drift.setdefault(agent_id, []).append({"timestamp": ts, "drift_value": drift_val})

    def get_drift_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        records = self._drift.get(agent_id, [])
        return list(reversed(records))[:limit]

    # ── Audit (Sprint 6-B) ────────────────────────────────────

    def save_audit_event(self, event: Any) -> None:
        self._audit.append(event)

    def get_audit_events(
        self,
        actor: str | None = None,
        action: str | None = None,
        from_ts: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        events = list(reversed(self._audit))
        if actor:
            events = [e for e in events if getattr(e, "actor", None) == actor]
        if action:
            events = [e for e in events if getattr(e, "action", None) == action]
        if from_ts:
            events = [e for e in events if getattr(e, "timestamp", "") >= from_ts]
        return events[:limit]
