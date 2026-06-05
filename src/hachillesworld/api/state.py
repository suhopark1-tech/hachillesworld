"""HAW API 인메모리 상태 저장소 (Sprint 3-A: Redis/ClickHouse 교체 예정)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from hachillesworld.core.models import DiagnosticReport
from hachillesworld.operate.meta_harness import MetaHarness
from hachillesworld.operate.monitor import DriftMonitor


@dataclass
class AppState:
    """런타임 인메모리 상태."""

    has_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    drift_monitors: dict[str, DriftMonitor] = field(default_factory=dict)
    meta_harnesses: dict[str, MetaHarness] = field(default_factory=dict)
    study_enrollments: dict[str, dict[str, Any]] = field(default_factory=dict)
    replay_events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def get_or_create_drift_monitor(self, agent_id: str) -> DriftMonitor:
        if agent_id not in self.drift_monitors:
            self.drift_monitors[agent_id] = DriftMonitor(agent_name=agent_id)
        return self.drift_monitors[agent_id]

    def get_or_create_meta_harness(self, agent_id: str) -> MetaHarness:
        if agent_id not in self.meta_harnesses:
            self.meta_harnesses[agent_id] = MetaHarness()
        return self.meta_harnesses[agent_id]

    def record_has(self, agent_id: str, report: DiagnosticReport) -> None:
        if agent_id not in self.has_history:
            self.has_history[agent_id] = []
        self.has_history[agent_id].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "has_score": round(report.composite_score, 2),
                "level": report.level_label,
            }
        )

    def get_has_timeseries(
        self,
        agent_id: str,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list[dict[str, Any]]:
        history = self.has_history.get(agent_id, [])
        if from_ts is not None:
            history = [p for p in history if p["timestamp"] >= from_ts]
        if to_ts is not None:
            history = [p for p in history if p["timestamp"] <= to_ts]
        return history
