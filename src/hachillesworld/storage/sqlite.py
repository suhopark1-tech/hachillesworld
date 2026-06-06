"""SQLite 기반 영구 레포지토리 — 로컬·개발 환경 기본 스토리지."""

from __future__ import annotations

import pickle
import sqlite3
from datetime import UTC, datetime
from typing import Any

from hachillesworld.core.models import DiagnosticReport

_DDL = """
CREATE TABLE IF NOT EXISTS has_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    has_score   REAL    NOT NULL,
    has_version TEXT    NOT NULL,
    level       TEXT    NOT NULL,
    report_blob BLOB
);
CREATE TABLE IF NOT EXISTS drift_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    drift_value REAL    NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id             TEXT    UNIQUE NOT NULL,
    timestamp            TEXT    NOT NULL,
    actor                TEXT    NOT NULL,
    action               TEXT    NOT NULL,
    resource             TEXT    DEFAULT '',
    outcome              TEXT    NOT NULL,
    ip_address           TEXT    DEFAULT '',
    request_size_bytes   INTEGER DEFAULT 0,
    response_size_bytes  INTEGER DEFAULT 0,
    duration_ms          REAL    DEFAULT 0.0
);
CREATE INDEX IF NOT EXISTS idx_has_agent    ON has_history(agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_drift_agent  ON drift_history(agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_actor  ON audit_events(actor, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action, timestamp);
"""


class SQLiteRepository:
    """SQLite 기반 영구 스토리지.

    설치 없이 바로 사용 가능. 기본 파일: haw_data.db.
    thread-safe (check_same_thread=False).
    """

    def __init__(self, db_path: str = "haw_data.db") -> None:
        self._path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        self._migrate_audit_table()

    def _create_tables(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    def _migrate_audit_table(self) -> None:
        """구 스키마(event_blob 방식)에서 신 스키마로 자동 마이그레이션."""
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(audit_events)").fetchall()]
        if "event_blob" in cols:
            self._conn.execute("DROP TABLE IF EXISTS audit_events")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id             TEXT    UNIQUE NOT NULL,
                    timestamp            TEXT    NOT NULL,
                    actor                TEXT    NOT NULL,
                    action               TEXT    NOT NULL,
                    resource             TEXT    DEFAULT '',
                    outcome              TEXT    NOT NULL,
                    ip_address           TEXT    DEFAULT '',
                    request_size_bytes   INTEGER DEFAULT 0,
                    response_size_bytes  INTEGER DEFAULT 0,
                    duration_ms          REAL    DEFAULT 0.0
                );
                CREATE INDEX IF NOT EXISTS idx_audit_actor  ON audit_events(actor, timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action, timestamp);
                """
            )
            self._conn.commit()

    # ── Reports ──────────────────────────────────────────────

    def save_report(self, agent_id: str, report: DiagnosticReport) -> None:
        ts = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO has_history "
            "(agent_id, timestamp, has_score, has_version, level, report_blob) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                agent_id,
                ts,
                report.composite_score,
                report.has_score_version,
                report.level_label,
                pickle.dumps(report),
            ),
        )
        self._conn.commit()

    def get_latest_report(self, agent_id: str) -> DiagnosticReport | None:
        row = self._conn.execute(
            "SELECT report_blob FROM has_history WHERE agent_id=? ORDER BY timestamp DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])  # type: ignore[no-any-return]  # noqa: S301

    def get_has_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT timestamp, has_score, level FROM has_history "
            "WHERE agent_id=? ORDER BY timestamp DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [{"timestamp": r[0], "has_score": r[1], "level": r[2]} for r in rows]

    # ── Drift ─────────────────────────────────────────────────

    def save_drift_record(self, agent_id: str, drift_val: float, ts: str) -> None:
        self._conn.execute(
            "INSERT INTO drift_history (agent_id, timestamp, drift_value) VALUES (?, ?, ?)",
            (agent_id, ts, drift_val),
        )
        self._conn.commit()

    def get_drift_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT timestamp, drift_value FROM drift_history "
            "WHERE agent_id=? ORDER BY timestamp DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [{"timestamp": r[0], "drift_value": r[1]} for r in rows]

    # ── Audit (Sprint 6-B) ────────────────────────────────────

    def save_audit_event(self, event: Any) -> None:
        from hachillesworld.audit.logger import AuditEvent

        if not isinstance(event, AuditEvent):
            return
        self._conn.execute(
            "INSERT OR IGNORE INTO audit_events "
            "(event_id, timestamp, actor, action, resource, outcome, "
            "ip_address, request_size_bytes, response_size_bytes, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.timestamp,
                event.actor,
                event.action,
                event.resource,
                event.outcome,
                event.ip_address,
                event.request_size_bytes,
                event.response_size_bytes,
                event.duration_ms,
            ),
        )
        self._conn.commit()

    def get_audit_events(
        self,
        actor: str | None = None,
        action: str | None = None,
        from_ts: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        from hachillesworld.audit.logger import AuditEvent

        clauses: list[str] = []
        params: list[Any] = []
        if actor:
            clauses.append("actor = ?")
            params.append(actor)
        if action:
            clauses.append("action = ?")
            params.append(action)
        if from_ts:
            clauses.append("timestamp >= ?")
            params.append(from_ts)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self._conn.execute(
            f"SELECT event_id, timestamp, actor, action, resource, outcome, "  # noqa: S608
            f"ip_address, request_size_bytes, response_size_bytes, duration_ms "
            f"FROM audit_events {where} ORDER BY timestamp DESC LIMIT ?",
            params,
        ).fetchall()
        return [
            AuditEvent(
                event_id=r[0],
                timestamp=r[1],
                actor=r[2],
                action=r[3],
                resource=r[4],
                outcome=r[5],
                ip_address=r[6],
                request_size_bytes=r[7],
                response_size_bytes=r[8],
                duration_ms=r[9],
            )
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
