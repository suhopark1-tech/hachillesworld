"""HAW API 런타임 상태 — 영구 데이터는 Repository에 위임 (Sprint 5-C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from hachillesworld.core.models import DiagnosticReport
from hachillesworld.operate.meta_harness import MetaHarness
from hachillesworld.operate.monitor import DriftMonitor
from hachillesworld.optimize.multi_agent import AgentDependencyGraph
from hachillesworld.storage.memory import InMemoryRepository


@dataclass
class AppState:
    """런타임 상태.

    영구 데이터(reports, HAS 이력, 드리프트 기록)는 repository에 위임.
    에피메랄 상태(모니터, 하네스, 그룹)는 인메모리에서 유지.
    """

    # 영구 스토리지 — server.py _lifespan에서 주입 (기본: InMemory)
    repository: Any = field(default_factory=InMemoryRepository)

    # 에피메랄 상태 (재시작 시 초기화 허용)
    drift_monitors: dict[str, DriftMonitor] = field(default_factory=dict)
    meta_harnesses: dict[str, MetaHarness] = field(default_factory=dict)
    study_enrollments: dict[str, dict[str, Any]] = field(default_factory=dict)
    replay_events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    groups: dict[str, list[str]] = field(default_factory=dict)
    group_graphs: dict[str, AgentDependencyGraph] = field(default_factory=dict)

    # ── 에피메랄 상태 헬퍼 ────────────────────────────────────

    def get_or_create_group_graph(self, group_id: str) -> AgentDependencyGraph:
        if group_id not in self.group_graphs:
            self.group_graphs[group_id] = AgentDependencyGraph()
        return self.group_graphs[group_id]

    def get_or_create_drift_monitor(self, agent_id: str) -> DriftMonitor:
        if agent_id not in self.drift_monitors:
            self.drift_monitors[agent_id] = DriftMonitor(agent_name=agent_id)
        return self.drift_monitors[agent_id]

    def get_or_create_meta_harness(self, agent_id: str) -> MetaHarness:
        if agent_id not in self.meta_harnesses:
            self.meta_harnesses[agent_id] = MetaHarness()
        return self.meta_harnesses[agent_id]

    # ── 영구 데이터 — repository 위임 ────────────────────────

    def record_has(self, agent_id: str, report: DiagnosticReport) -> None:
        """진단 보고서를 repository에 저장."""
        self.repository.save_report(agent_id, report)

    def get_latest_report(self, agent_id: str) -> DiagnosticReport | None:
        """에이전트의 최신 진단 보고서 반환 (재시작 후에도 유지)."""
        return cast("DiagnosticReport | None", self.repository.get_latest_report(agent_id))

    def get_has_timeseries(
        self,
        agent_id: str,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list[dict[str, Any]]:
        """HAS 시계열 이력 반환 (최신순). from_ts/to_ts로 구간 필터링."""
        history: list[dict[str, Any]] = cast(
            "list[dict[str, Any]]", self.repository.get_has_history(agent_id, limit=10_000)
        )
        if from_ts is not None:
            history = [p for p in history if p["timestamp"] >= from_ts]
        if to_ts is not None:
            history = [p for p in history if p["timestamp"] <= to_ts]
        return history
