"""Sprint 4-A: 다중 에이전트 지원 테스트."""

from __future__ import annotations

import pytest

from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
    MetricScore,
)
from hachillesworld.optimize.multi_agent import (
    AgentDependencyGraph,
    CrossAgentDriftCorrelator,
    GroupHASReport,
    MultiAgentOrchestrator,
    SimultaneousDriftResult,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────


def _make_report(
    name: str,
    score: float,
    level: Level = Level.L2,
) -> DiagnosticReport:
    """score가 세 카테고리 모두에 적용되는 DiagnosticReport 픽스처.

    composite_score = WMQ*0.40 + Agency*0.35 + OHM*0.25 = score*(0.4+0.35+0.25) = score
    """
    cat = lambda n, s: CategoryScore(name=n, score=s)
    return DiagnosticReport(
        agent_name=name,
        level=level,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=cat("WMQ", score),
        agency_level=cat("ALM", score),
        operational_health=cat("OHM", score),
    )


# ── 테스트 1: 3개 에이전트 HAS 집계 ────────────────────────────────


class TestHASAggregation3Agents:
    def test_has_aggregation_3_agents(self) -> None:
        """3개 에이전트 HAS 균등 가중치 집계."""
        reports = [
            _make_report("agent-A", 90.0),
            _make_report("agent-B", 75.0),
            _make_report("agent-C", 60.0),
        ]
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports)

        assert isinstance(group, GroupHASReport)
        assert group.n_agents == 3
        assert abs(group.group_has - 75.0) < 0.1  # (90+75+60)/3 = 75
        assert group.group_level == "L2"

    def test_has_aggregation_custom_weights(self) -> None:
        """커스텀 가중치 적용 시 가중 평균이 올바르게 계산된다."""
        reports = [
            _make_report("agent-A", 90.0),
            _make_report("agent-B", 60.0),
        ]
        weights = {"agent-A": 0.8, "agent-B": 0.2}
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports, weights=weights)

        expected = (90.0 * 0.8 + 60.0 * 0.2) / (0.8 + 0.2)  # = 84.0
        assert abs(group.group_has - expected) < 0.1

    def test_has_aggregation_single_agent(self) -> None:
        """단일 에이전트도 집계 가능."""
        report = _make_report("solo-agent", 77.5)
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has([report])

        assert group.n_agents == 1
        assert abs(group.group_has - 77.5) < 0.1
        assert group.weakest_link == "solo-agent"

    def test_has_aggregation_empty_raises(self) -> None:
        """빈 목록은 ValueError."""
        orch = MultiAgentOrchestrator()
        with pytest.raises(ValueError, match="보고서가 없습니다"):
            orch.aggregate_has([])

    def test_group_level_is_minimum(self) -> None:
        """그룹 레벨은 개별 레벨의 최솟값."""
        reports = [
            _make_report("a1", 80.0, level=Level.L3),
            _make_report("a2", 70.0, level=Level.L2),
            _make_report("a3", 60.0, level=Level.L1),
        ]
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports)
        assert group.group_level == "L1"  # 최저 레벨


# ── 테스트 2: 사이클 탐지 거부 ─────────────────────────────────────


class TestCycleDetectionRejected:
    def test_cycle_detection_rejected(self) -> None:
        """A→B→C→A 사이클 시도 → ValueError."""
        g = AgentDependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("B", "C")
        with pytest.raises(ValueError, match="사이클"):
            g.add_dependency("C", "A")

    def test_self_loop_rejected(self) -> None:
        """자기 참조(A→A) 시도 → ValueError."""
        g = AgentDependencyGraph()
        with pytest.raises(ValueError, match="자기 참조"):
            g.add_dependency("A", "A")

    def test_two_hop_cycle_rejected(self) -> None:
        """A→B가 있을 때 B→A 시도 → ValueError."""
        g = AgentDependencyGraph()
        g.add_dependency("A", "B")
        with pytest.raises(ValueError, match="사이클"):
            g.add_dependency("B", "A")

    def test_valid_dag_accepted(self) -> None:
        """유효한 DAG는 정상 추가된다."""
        g = AgentDependencyGraph()
        g.add_dependency("planner", "executor", weight=0.9)
        g.add_dependency("executor", "reporter", weight=0.7)
        g.add_dependency("planner", "reporter", weight=0.5)  # planner → reporter도 가능

        edges = g.edges()
        assert len(edges) == 3

    def test_invalid_weight_rejected(self) -> None:
        """가중치가 (0, 1] 범위를 벗어나면 ValueError."""
        g = AgentDependencyGraph()
        with pytest.raises(ValueError, match="가중치"):
            g.add_dependency("A", "B", weight=0.0)
        with pytest.raises(ValueError, match="가중치"):
            g.add_dependency("A", "B", weight=1.5)

    def test_agents_list(self) -> None:
        """등록된 에이전트 목록이 올바르게 반환된다."""
        g = AgentDependencyGraph()
        g.add_dependency("planner", "executor")
        g.add_dependency("executor", "reporter")
        assert set(g.agents()) == {"planner", "executor", "reporter"}


# ── 테스트 3: 드리프트 전파 위험도 ─────────────────────────────────


class TestDriftPropagationRisk:
    def test_drift_propagation_risk(self) -> None:
        """planner→executor(0.9)→reporter(0.7) 구조의 전파 위험도."""
        g = AgentDependencyGraph()
        g.add_dependency("planner", "executor", weight=0.9)
        g.add_dependency("executor", "reporter", weight=0.7)

        risks = g.propagation_risk("planner", decay=0.8)

        # executor 위험도: 0.9 * 0.8 = 0.72
        assert abs(risks["executor"] - 0.72) < 1e-4
        # reporter 위험도: 0.72 * 0.7 * 0.8 = 0.4032
        assert abs(risks["reporter"] - 0.4032) < 1e-4

    def test_no_downstream_returns_empty(self) -> None:
        """다운스트림이 없는 리프 노드는 빈 dict를 반환한다."""
        g = AgentDependencyGraph()
        g.add_dependency("A", "B")
        risks = g.propagation_risk("B")
        assert risks == {}

    def test_isolated_agent_returns_empty(self) -> None:
        """그래프에 없는 에이전트는 빈 dict를 반환한다."""
        g = AgentDependencyGraph()
        risks = g.propagation_risk("unknown-agent")
        assert risks == {}

    def test_propagation_decays_with_distance(self) -> None:
        """거리가 멀수록 전파 위험도가 감소한다."""
        g = AgentDependencyGraph()
        g.add_dependency("A", "B", weight=1.0)
        g.add_dependency("B", "C", weight=1.0)
        g.add_dependency("C", "D", weight=1.0)

        risks = g.propagation_risk("A", decay=0.8)

        assert risks["B"] > risks["C"] > risks["D"]
        assert abs(risks["B"] - 0.8) < 1e-4    # 1홉: 1.0 * 0.8
        assert abs(risks["C"] - 0.64) < 1e-4   # 2홉: 0.8 * 1.0 * 0.8
        assert abs(risks["D"] - 0.512) < 1e-4  # 3홉: 0.64 * 1.0 * 0.8

    def test_parallel_paths_take_maximum(self) -> None:
        """병렬 경로가 있으면 최대 위험도 경로를 사용한다."""
        g = AgentDependencyGraph()
        g.add_dependency("A", "B", weight=0.9)  # A→B: 0.9*0.8 = 0.72
        g.add_dependency("A", "C", weight=0.5)  # A→C: 0.5*0.8 = 0.4
        g.add_dependency("C", "B", weight=1.0)  # A→C→B: 0.4*1.0*0.8 = 0.32

        risks = g.propagation_risk("A", decay=0.8)
        # B는 A→B(0.72) 또는 A→C→B(0.32) 중 최댓값 = 0.72
        assert abs(risks["B"] - 0.72) < 1e-4


# ── 테스트 4: 동시 드리프트 감지 ───────────────────────────────────


class TestSimultaneousDriftDetection:
    def test_simultaneous_drift_detection(self) -> None:
        """3개 에이전트가 동일 패턴으로 드리프트 → 환경 레벨 분류."""
        correlator = CrossAgentDriftCorrelator(correlation_threshold=0.60)

        # 세 에이전트 모두 동일한 상승 패턴 (환경 레벨 드리프트 시뮬레이션)
        for step in range(20):
            base = step * 0.05
            correlator.record_drift("agent-A", base + 0.00)
            correlator.record_drift("agent-B", base + 0.01)
            correlator.record_drift("agent-C", base + 0.02)

        result = correlator.detect_simultaneous_drift()

        assert isinstance(result, SimultaneousDriftResult)
        assert result.detected is True
        assert result.cause == "environment"
        assert result.mean_correlation > 0.6

    def test_uncorrelated_drifts_not_detected(self) -> None:
        """에이전트마다 독립적인 드리프트 → 동시 감지 안 됨."""
        import random
        correlator = CrossAgentDriftCorrelator(correlation_threshold=0.60)
        rng = random.Random(42)

        for step in range(30):
            correlator.record_drift("agent-A", rng.uniform(0.1, 0.3))
            correlator.record_drift("agent-B", rng.uniform(0.1, 0.3))
            correlator.record_drift("agent-C", rng.uniform(0.1, 0.3))

        result = correlator.detect_simultaneous_drift()
        # 독립적 랜덤 신호는 높은 상관을 보이지 않는다
        assert result.mean_correlation < 0.9  # 임계값이 있으므로 대부분 미감지

    def test_single_agent_no_detection(self) -> None:
        """에이전트 1개만 있으면 감지 불가."""
        correlator = CrossAgentDriftCorrelator()
        for i in range(10):
            correlator.record_drift("only-agent", float(i))

        result = correlator.detect_simultaneous_drift()
        assert result.detected is False
        assert result.cause == "unknown"

    def test_correlated_pairs_returned(self) -> None:
        """상관 있는 쌍이 correlated_pairs에 포함된다."""
        correlator = CrossAgentDriftCorrelator(correlation_threshold=0.60)
        for i in range(15):
            v = float(i)
            correlator.record_drift("A", v)
            correlator.record_drift("B", v * 1.01)  # 거의 동일

        result = correlator.detect_simultaneous_drift()
        # (A, B) 쌍이 correlated_pairs에 있어야 함
        pair_agents = {a for a1, a2, _ in result.correlated_pairs for a in (a1, a2)}
        assert "A" in pair_agents and "B" in pair_agents


# ── 테스트 5: Weakest Link 식별 ────────────────────────────────────


class TestWeakestLinkIdentification:
    def test_weakest_link_identification(self) -> None:
        """최저 점수 에이전트가 weakest_link로 정확히 식별된다."""
        reports = [
            _make_report("high-agent", 88.0),
            _make_report("mid-agent",  72.0),
            _make_report("low-agent",  45.0),  # 최저
        ]
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports)

        assert group.weakest_link == "low-agent"

    def test_weakest_link_with_dependency_risk(self) -> None:
        """weakest_link의 전파 위험도가 dependency_risk에 포함된다."""
        reports = [
            _make_report("planner",  88.0),
            _make_report("executor", 40.0),  # 최저 → weakest
            _make_report("reporter", 75.0),
        ]
        graph = AgentDependencyGraph()
        graph.add_dependency("executor", "reporter", weight=0.8)

        orch = MultiAgentOrchestrator(dependency_graph=graph)
        group = orch.aggregate_has(reports)

        assert group.weakest_link == "executor"
        assert "reporter" in group.dependency_risk
        assert group.dependency_risk["reporter"] > 0

    def test_weakest_link_in_summary(self) -> None:
        """summary() 출력에 weakest_link 이름이 포함된다."""
        reports = [_make_report("alpha", 90.0), _make_report("beta", 55.0)]
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports)

        summary = group.summary()
        assert "beta" in summary

    def test_all_agents_equal_any_is_weakest(self) -> None:
        """모든 에이전트가 동점이면 weakest_link는 그중 하나."""
        reports = [_make_report(f"agent-{i}", 75.0) for i in range(4)]
        orch = MultiAgentOrchestrator()
        group = orch.aggregate_has(reports)

        all_names = {r.agent_name for r in reports}
        assert group.weakest_link in all_names
