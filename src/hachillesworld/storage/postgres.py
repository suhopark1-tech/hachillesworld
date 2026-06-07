"""PostgreSQL 기반 레포지토리 — 프로덕션 환경용 (sqlalchemy 필요)."""

from __future__ import annotations

import pickle
from datetime import UTC, datetime
from typing import Any

from hachillesworld.core.models import DiagnosticReport

try:
    from sqlalchemy import create_engine, text  # type: ignore[import-not-found]

    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

_DDL = """
CREATE TABLE IF NOT EXISTS has_history (
    id          SERIAL PRIMARY KEY,
    agent_id    TEXT   NOT NULL,
    timestamp   TEXT   NOT NULL,
    has_score   REAL   NOT NULL,
    has_version TEXT   NOT NULL,
    level       TEXT   NOT NULL,
    report_blob BYTEA
);
CREATE TABLE IF NOT EXISTS drift_history (
    id          SERIAL PRIMARY KEY,
    agent_id    TEXT   NOT NULL,
    timestamp   TEXT   NOT NULL,
    drift_value REAL   NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id          SERIAL PRIMARY KEY,
    timestamp   TEXT   NOT NULL,
    event_blob  BYTEA
);
CREATE INDEX IF NOT EXISTS idx_has_agent   ON has_history(agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_drift_agent ON drift_history(agent_id, timestamp);
"""


class PostgreSQLRepository:
    """PostgreSQL 기반 영구 스토리지.

    필요: pip install hachillesworld[full]
    환경변수: HAW_DATABASE_URL=postgresql://user:pass@host/dbname
    """

    def __init__(self, dsn: str | None = None) -> None:
        if not _SA_AVAILABLE:
            raise ImportError(
                "PostgreSQL 스토리지는 sqlalchemy가 필요합니다: pip install hachillesworld[full]"
            )
        if not dsn:
            raise ValueError(
                "dsn 또는 HAW_DATABASE_URL 환경변수가 필요합니다. "
                "예: postgresql://user:pass@localhost/haw"
            )
        self._engine = create_engine(dsn, pool_pre_ping=True)
        self._create_tables()

    def _create_tables(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(text(_DDL))
            conn.commit()

    # ── Reports ──────────────────────────────────────────────

    def save_report(self, agent_id: str, report: DiagnosticReport) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO has_history "
                    "(agent_id, timestamp, has_score, has_version, level, report_blob) "
                    "VALUES (:aid, :ts, :score, :ver, :lvl, :blob)"
                ),
                {
                    "aid": agent_id,
                    "ts": ts,
                    "score": report.composite_score,
                    "ver": report.has_score_version,
                    "lvl": report.level_label,
                    "blob": pickle.dumps(report),
                },
            )
            conn.commit()

    def get_latest_report(self, agent_id: str) -> DiagnosticReport | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT report_blob FROM has_history "
                    "WHERE agent_id=:aid ORDER BY timestamp DESC LIMIT 1"
                ),
                {"aid": agent_id},
            ).fetchone()
        return pickle.loads(row[0]) if row else None  # noqa: S301

    def get_has_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT timestamp, has_score, level FROM has_history "
                    "WHERE agent_id=:aid ORDER BY timestamp DESC LIMIT :lim"
                ),
                {"aid": agent_id, "lim": limit},
            ).fetchall()
        return [{"timestamp": r[0], "has_score": r[1], "level": r[2]} for r in rows]

    # ── Drift ─────────────────────────────────────────────────

    def save_drift_record(self, agent_id: str, drift_val: float, ts: str) -> None:
        with self._engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO drift_history (agent_id, timestamp, drift_value) "
                    "VALUES (:aid, :ts, :val)"
                ),
                {"aid": agent_id, "ts": ts, "val": drift_val},
            )
            conn.commit()

    def get_drift_history(self, agent_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT timestamp, drift_value FROM drift_history "
                    "WHERE agent_id=:aid ORDER BY timestamp DESC LIMIT :lim"
                ),
                {"aid": agent_id, "lim": limit},
            ).fetchall()
        return [{"timestamp": r[0], "drift_value": r[1]} for r in rows]

    # ── Audit (Sprint 6-B 대비) ───────────────────────────────

    def save_audit_event(self, event: Any) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._engine.connect() as conn:
            conn.execute(
                text("INSERT INTO audit_events (timestamp, event_blob) VALUES (:ts, :blob)"),
                {"ts": ts, "blob": pickle.dumps(event)},
            )
            conn.commit()

    def get_audit_events(self, **kwargs: Any) -> list[Any]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT event_blob FROM audit_events ORDER BY timestamp DESC")
            ).fetchall()
        return [pickle.loads(r[0]) for r in rows]  # noqa: S301
