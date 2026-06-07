# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""다중 에이전트 HAS 집계 및 의존성 드리프트 전파 추적.

HAW-TR-001 §10.4 Future Work 구현.

주요 클래스:
    AgentDependencyGraph       — 에이전트 간 의존성 DAG (사이클 자동 탐지)
    CrossAgentDriftCorrelator  — 동시 드리프트 감지 (환경 vs 개별)
    MultiAgentOrchestrator     — 그룹 HAS 집계 오케스트레이터
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime

from hachillesworld.core.models import DiagnosticReport, Level

_LEVEL_ORDER: dict[Level, int] = {Level.L1: 1, Level.L2: 2, Level.L3: 3}
_ORDER_LEVEL: dict[int, Level] = {1: Level.L1, 2: Level.L2, 3: Level.L3}


# ── 데이터 모델 ─────────────────────────────────────────────────────


@dataclass
class SimultaneousDriftResult:
    """다중 에이전트 동시 드리프트 분석 결과."""

    detected: bool
    cause: str  # "environment" | "individual" | "unknown"
    correlated_pairs: list[tuple[str, str, float]]  # (agent1, agent2, rho)
    mean_correlation: float
    n_agents_affected: int


@dataclass
class GroupHASReport:
    """에이전트 그룹 종합 진단 보고서.

    group_has               — 가중 평균 그룹 HAS [0, 100]
    individual_reports      — 개별 에이전트 DiagnosticReport 목록
    weakest_link            — 최저 점수 에이전트 이름
    dependency_risk         — {agent_name: 드리프트 전파 위험도 [0, 1]}
    simultaneous_drift_detected — 동시 드리프트 감지 여부
    group_level             — "L1" | "L2" | "L3" (최저 레벨 기준)
    """

    group_has: float
    individual_reports: list[DiagnosticReport]
    weakest_link: str
    dependency_risk: dict[str, float]
    simultaneous_drift_detected: bool
    group_level: str
    generated_at: str
    n_agents: int

    def summary(self) -> str:
        emoji = "🟢" if self.group_has >= 80 else "🟡" if self.group_has >= 60 else "🔴"
        lines = [
            f"{emoji} [그룹 HAS] {self.group_has:.1f}/100  "
            f"레벨: {self.group_level}  에이전트: {self.n_agents}개",
            f"   최저 점수 (Weakest Link): {self.weakest_link}",
        ]
        if self.simultaneous_drift_detected:
            lines.append("   ⚠ 동시 드리프트 감지 — 환경 레벨 변화 점검 필요")
        if self.dependency_risk:
            top = max(self.dependency_risk, key=lambda k: self.dependency_risk[k])
            lines.append(f"   최고 전파 위험: {top}  (위험도 {self.dependency_risk[top]:.1%})")
        lines.append(f"   생성: {self.generated_at}")
        return "\n".join(lines)


# ── AgentDependencyGraph ────────────────────────────────────────────


class AgentDependencyGraph:
    """에이전트 간 의존성 방향 비순환 그래프(DAG).

    특징:
    - 의존성 추가 시 사이클 자동 탐지 → 거부 (R5 리스크 대응)
    - BFS 기반 드리프트 전파 위험도 계산
    - 자기 참조 의존성 차단

    사용 예:
        g = AgentDependencyGraph()
        g.add_dependency("planner", "executor", weight=0.9)
        g.add_dependency("executor", "reporter", weight=0.7)

        risks = g.propagation_risk("planner")
        # {"executor": 0.72, "reporter": 0.504}

        # 사이클 시도 → ValueError
        g.add_dependency("reporter", "planner")  # raises ValueError
    """

    def __init__(self) -> None:
        self._adj: dict[str, dict[str, float]] = {}  # {from: {to: weight}}
        self._nodes: set[str] = set()

    # ── 엣지 조작 ─────────────────────────────────────────────────

    def add_dependency(
        self,
        from_agent: str,
        to_agent: str,
        weight: float = 1.0,
    ) -> None:
        """의존성 엣지를 추가한다.

        Args:
            from_agent: 의존성 출처 에이전트
            to_agent: 의존성 대상 에이전트
            weight: 전파 강도 (0 < weight ≤ 1.0)

        Raises:
            ValueError: 자기 참조 또는 사이클이 생기는 경우
        """
        if from_agent == to_agent:
            raise ValueError(f"자기 참조 의존성 불허: {from_agent}")
        if not (0 < weight <= 1.0):
            raise ValueError(f"가중치는 (0, 1] 범위여야 합니다: {weight}")

        # 사이클 사전 검사: to_agent가 이미 from_agent에 도달 가능한가?
        if self._is_reachable(to_agent, from_agent):
            raise ValueError(
                f"사이클 감지: {from_agent} → {to_agent} 추가 시 순환 의존성 발생 "
                f"(이미 {to_agent} → ··· → {from_agent} 경로 존재)"
            )

        self._nodes.update({from_agent, to_agent})
        self._adj.setdefault(from_agent, {})[to_agent] = weight
        if to_agent not in self._adj:
            self._adj[to_agent] = {}

    def remove_dependency(self, from_agent: str, to_agent: str) -> None:
        """의존성 엣지를 제거한다."""
        if from_agent in self._adj:
            self._adj[from_agent].pop(to_agent, None)

    # ── 전파 위험도 ────────────────────────────────────────────────

    def propagation_risk(
        self,
        source_agent: str,
        decay: float = 0.8,
    ) -> dict[str, float]:
        """source_agent 드리프트 발생 시 각 하위 에이전트의 위험도.

        BFS로 최대 위험도 경로를 탐색한다:
            risk(v) = max over all paths: Π(edge_weights) × decay^hops

        Args:
            source_agent: 드리프트 발원 에이전트
            decay: 홉당 감쇠 계수 (기본 0.8)

        Returns:
            {agent_name: risk_value (0~1)}  — source 에이전트 제외
        """
        if source_agent not in self._nodes and source_agent not in self._adj:
            return {}

        dist: dict[str, float] = {source_agent: 1.0}
        queue: deque[tuple[str, float]] = deque([(source_agent, 1.0)])

        while queue:
            current, current_risk = queue.popleft()
            for neighbor, edge_weight in self._adj.get(current, {}).items():
                propagated = current_risk * edge_weight * decay
                if propagated > dist.get(neighbor, 0.0):
                    dist[neighbor] = propagated
                    queue.append((neighbor, propagated))

        dist.pop(source_agent, None)
        return {k: round(v, 4) for k, v in dist.items()}

    # ── 조회 ──────────────────────────────────────────────────────

    def agents(self) -> list[str]:
        """그래프에 등록된 모든 에이전트 이름 (정렬)."""
        return sorted(self._nodes)

    def edges(self) -> list[tuple[str, str, float]]:
        """(from, to, weight) 형태의 엣지 목록."""
        return [(src, dst, w) for src, nbrs in self._adj.items() for dst, w in nbrs.items()]

    # ── 내부 ──────────────────────────────────────────────────────

    def _is_reachable(self, start: str, target: str) -> bool:
        """BFS로 start에서 target이 도달 가능한지 확인."""
        if start == target:
            return True
        visited: set[str] = set()
        q: deque[str] = deque([start])
        while q:
            node = q.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in self._adj.get(node, {}):
                if neighbor == target:
                    return True
                if neighbor not in visited:
                    q.append(neighbor)
        return False


# ── CrossAgentDriftCorrelator ───────────────────────────────────────


class CrossAgentDriftCorrelator:
    """여러 에이전트의 드리프트 동시 발생 감지.

    분류:
    - "environment": 전체 에이전트 드리프트 상관 ≥ threshold → 환경 변화
    - "individual": 일부 에이전트만 드리프트 → 개별 모델 열화

    사용 예:
        correlator = CrossAgentDriftCorrelator()
        for step in range(50):
            for name, drift in agent_drifts.items():
                correlator.record_drift(name, drift)

        result = correlator.detect_simultaneous_drift()
        if result.detected and result.cause == "environment":
            print("환경 레벨 드리프트 — 전체 재보정 필요")
    """

    def __init__(self, correlation_threshold: float = 0.60) -> None:
        self.correlation_threshold = correlation_threshold
        self._histories: dict[str, list[float]] = {}

    def record_drift(self, agent_name: str, drift_value: float) -> None:
        """에이전트 드리프트 값을 기록한다."""
        self._histories.setdefault(agent_name, []).append(float(drift_value))

    def detect_simultaneous_drift(self) -> SimultaneousDriftResult:
        """여러 에이전트 드리프트의 상관관계를 분석한다."""
        agents = list(self._histories.keys())
        n = len(agents)

        if n < 2:
            return SimultaneousDriftResult(
                detected=False,
                cause="unknown",
                correlated_pairs=[],
                mean_correlation=0.0,
                n_agents_affected=0,
            )

        correlated_pairs: list[tuple[str, str, float]] = []
        all_abs_rhos: list[float] = []

        for i in range(n):
            for j in range(i + 1, n):
                a1, a2 = agents[i], agents[j]
                rho = _pearson(self._histories[a1], self._histories[a2])
                if not math.isnan(rho):
                    all_abs_rhos.append(abs(rho))
                    if abs(rho) >= self.correlation_threshold:
                        correlated_pairs.append((a1, a2, round(rho, 4)))

        mean_corr = sum(all_abs_rhos) / len(all_abs_rhos) if all_abs_rhos else 0.0
        total_pairs = n * (n - 1) // 2
        high_frac = len(correlated_pairs) / total_pairs if total_pairs > 0 else 0.0
        detected = high_frac >= 0.5

        if not detected:
            cause = "individual"
            affected = {a for a1, a2, _ in correlated_pairs for a in (a1, a2)}
            n_affected = len(affected)
        else:
            cause = "environment"
            n_affected = n

        return SimultaneousDriftResult(
            detected=detected,
            cause=cause,
            correlated_pairs=correlated_pairs,
            mean_correlation=round(mean_corr, 4),
            n_agents_affected=n_affected,
        )


# ── MultiAgentOrchestrator ──────────────────────────────────────────


class MultiAgentOrchestrator:
    """복수 AI 에이전트 그룹의 HAS 집계 및 드리프트 전파 추적 오케스트레이터.

    사용 예:
        graph = AgentDependencyGraph()
        graph.add_dependency("planner", "executor", weight=0.9)
        graph.add_dependency("executor", "reporter", weight=0.7)

        correlator = CrossAgentDriftCorrelator()
        for drift_val in drift_stream:
            correlator.record_drift("planner", drift_val)

        orch = MultiAgentOrchestrator(
            dependency_graph=graph,
            drift_correlator=correlator,
        )

        group_report = orch.aggregate_has([r_planner, r_executor, r_reporter])
        print(group_report.summary())
    """

    def __init__(
        self,
        dependency_graph: AgentDependencyGraph | None = None,
        drift_correlator: CrossAgentDriftCorrelator | None = None,
    ) -> None:
        self.dependency_graph = dependency_graph or AgentDependencyGraph()
        self.drift_correlator = drift_correlator or CrossAgentDriftCorrelator()

    def aggregate_has(
        self,
        agent_reports: list[DiagnosticReport],
        weights: dict[str, float] | None = None,
    ) -> GroupHASReport:
        """복수 에이전트의 HAS를 집계하여 그룹 진단 보고서를 반환한다.

        Args:
            agent_reports: DiagnosticReport 목록 (1개 이상)
            weights: {agent_name: weight}. None이면 균등 가중치.

        Returns:
            GroupHASReport
        """
        if not agent_reports:
            raise ValueError("집계할 에이전트 보고서가 없습니다")

        w = weights or {r.agent_name: 1.0 for r in agent_reports}
        total_w = sum(w.get(r.agent_name, 1.0) for r in agent_reports)
        group_has = (
            sum(r.composite_score * w.get(r.agent_name, 1.0) for r in agent_reports) / total_w
        )

        weakest = min(agent_reports, key=lambda r: r.composite_score)
        dep_risk = self.dependency_graph.propagation_risk(weakest.agent_name)
        drift_result = self.drift_correlator.detect_simultaneous_drift()

        min_level_order = min(_LEVEL_ORDER[r.level] for r in agent_reports)
        group_level = _ORDER_LEVEL[min_level_order].value

        return GroupHASReport(
            group_has=round(group_has, 2),
            individual_reports=list(agent_reports),
            weakest_link=weakest.agent_name,
            dependency_risk=dep_risk,
            simultaneous_drift_detected=drift_result.detected,
            group_level=group_level,
            generated_at=datetime.now(UTC).isoformat(),
            n_agents=len(agent_reports),
        )


# ── 내부 수학 유틸 ──────────────────────────────────────────────────


def _pearson(x: list[float], y: list[float]) -> float:
    """두 시계열의 Pearson 상관계수 (길이가 다르면 짧은 쪽에 맞춤)."""
    n = min(len(x), len(y))
    if n < 3:
        return float("nan")
    x, y = x[:n], y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    return 0.0 if sx == 0 or sy == 0 else cov / (sx * sy)
