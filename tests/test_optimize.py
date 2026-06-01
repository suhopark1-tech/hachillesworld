"""Optimize 모듈 테스트."""

import pytest
from hachillesworld.core.models import (
    CategoryScore, DiagnosticReport, LawsDomain, Level, MetricScore,
)
from hachillesworld.optimize.roadmap import RoadmapGenerator
from hachillesworld.optimize.harness_generator import HarnessGenerator


@pytest.fixture
def l1_report():
    return DiagnosticReport(
        agent_name="l1-agent",
        level=Level.L1,
        level_progress=0.7,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore("World Model 품질", 55.0, [
            MetricScore("Simulation Drift Rate", 0.25, 0.05, status="critical"),
            MetricScore("Calibration ECE", 0.22, 0.10, status="critical"),
        ]),
        agency_level=CategoryScore("에이전시 수준", 40.0, [
            MetricScore("Harness Coverage", 3.0, 20.0, status="critical"),
            MetricScore("Uncertainty Awareness", 0.0, 1.0, status="critical"),
        ]),
        operational_health=CategoryScore("운영 건전성", 60.0, [
            MetricScore("HITL Trigger Rate", 0.28, 0.05, status="critical"),
        ]),
    )


@pytest.fixture
def l2_report():
    return DiagnosticReport(
        agent_name="l2-agent",
        level=Level.L2,
        level_progress=0.4,
        laws_domain=LawsDomain.PHYSICAL,
        world_model_quality=CategoryScore("World Model 품질", 72.0, []),
        agency_level=CategoryScore("에이전시 수준", 65.0, []),
        operational_health=CategoryScore("운영 건전성", 70.0, []),
    )


class TestRoadmapGenerator:

    def test_l1_to_l2_roadmap(self, l1_report):
        roadmap = RoadmapGenerator().generate(l1_report)
        assert roadmap.from_level.startswith("L1")
        assert roadmap.to_level == "L2"
        assert len(roadmap.phases) == 3
        assert roadmap.estimated_duration_weeks > 0

    def test_l2_to_l3_roadmap(self, l2_report):
        roadmap = RoadmapGenerator().generate(l2_report, target_level="L3")
        assert roadmap.to_level == "L3"
        assert len(roadmap.phases) == 3

    def test_total_weeks_sum(self, l1_report):
        roadmap = RoadmapGenerator().generate(l1_report)
        total   = sum(p.duration_weeks for p in roadmap.phases)
        assert total == roadmap.estimated_duration_weeks

    def test_phases_have_tasks(self, l1_report):
        roadmap = RoadmapGenerator().generate(l1_report)
        for phase in roadmap.phases:
            assert len(phase.tasks) > 0

    def test_print_roadmap_runs(self, l1_report, capsys):
        roadmap = RoadmapGenerator().generate(l1_report)
        RoadmapGenerator().print_roadmap(roadmap)
        captured = capsys.readouterr()
        assert "HAchillesWorld Optimize" in captured.out


class TestHarnessGenerator:

    def test_generates_rules_for_critical_metrics(self, l1_report):
        spec = HarnessGenerator().generate(l1_report)
        assert len(spec.rules) > 0

    def test_forbidden_actions_not_empty(self, l1_report):
        spec = HarnessGenerator().generate(l1_report)
        assert len(spec.forbidden_actions) > 0

    def test_budget_caps_set(self, l1_report):
        spec = HarnessGenerator().generate(l1_report)
        assert "daily_usd" in spec.budget_caps
        assert spec.budget_caps["daily_usd"] > 0

    def test_to_python_generates_code(self, l1_report):
        spec = HarnessGenerator().generate(l1_report)
        code = spec.to_python()
        assert "class GeneratedHarness" in code
        assert "FORBIDDEN_ACTIONS" in code
        assert "def allow" in code
