"""Sprint 2-B: HarnessConflictDetector 3유형 충돌 감지 테스트."""

from __future__ import annotations

from hachillesworld.operate.meta_harness import (
    HarnessConflictDetector,
    MetaHarness,
)
from hachillesworld.optimize.harness_generator import HarnessRule


def _make_rule(
    rule_id: str,
    condition: str = "IF drift > threshold",
    action: str = "THEN recalibrate()",
    severity: str = "hard",
) -> HarnessRule:
    return HarnessRule(
        rule_id=rule_id,
        condition=condition,
        action=action,
        severity=severity,
        source="test",
    )


class TestHarnessConflictDetector:
    def test_conflict_type1_same_condition_opposite_action(self):
        """Type1: 동일 조건-상반 행동 → type1 충돌 감지."""
        detector = HarnessConflictDetector()

        existing = _make_rule(
            "rule_a",
            condition="IF simulation_drift_rate > recalibration_threshold",
            action="THEN force_recalibration()",
            severity="hard",
        )
        new_rule = _make_rule(
            "rule_b",
            condition="IF simulation_drift_rate > recalibration_threshold",  # same
            action="THEN freeze_agent()",  # different
            severity="hard",  # same severity → Type1, not Type3
        )

        reports = detector.check(new_rule, [existing])

        assert len(reports) == 1
        assert reports[0].conflict_type == "type1"
        assert reports[0].conflicting_rule_id == "rule_a"
        assert "상반 행동" in reports[0].description or "type1" in reports[0].conflict_type

    def test_conflict_type2_duplicate_rule(self):
        """Type2: 완전 중복 (조건·행동·강도 모두 동일) → type2 충돌 감지."""
        detector = HarnessConflictDetector()

        existing = _make_rule(
            "rule_a",
            condition="IF daily_cost > budget_cap",
            action="THEN alert_budget()",
            severity="soft",
        )
        new_rule = _make_rule(
            "rule_b",
            condition="IF daily_cost > budget_cap",  # same
            action="THEN alert_budget()",  # same
            severity="soft",  # same → complete duplicate
        )

        reports = detector.check(new_rule, [existing])

        assert len(reports) == 1
        assert reports[0].conflict_type == "type2"
        assert reports[0].conflicting_rule_id == "rule_a"

    def test_conflict_type3_hard_soft_mix(self):
        """Type3: 동일 조건·행동 + hard-soft 강도 혼용 → type3 충돌 감지."""
        detector = HarnessConflictDetector()

        existing = _make_rule(
            "rule_hard",
            condition="IF uncertainty > 0.35",
            action="THEN require_human_approval()",
            severity="hard",
        )
        new_rule = _make_rule(
            "rule_soft",
            condition="IF uncertainty > 0.35",  # same
            action="THEN require_human_approval()",  # same
            severity="soft",  # different severity → Type3
        )

        reports = detector.check(new_rule, [existing])

        assert len(reports) == 1
        assert reports[0].conflict_type == "type3"
        assert reports[0].conflicting_rule_id == "rule_hard"
        assert "hard" in reports[0].description or "soft" in reports[0].description

    def test_no_conflict_clean_rule(self):
        """완전히 다른 조건의 규칙 → 충돌 없음."""
        detector = HarnessConflictDetector()

        existing = _make_rule(
            "rule_drift",
            condition="IF simulation_drift_rate > 0.20",
            action="THEN recalibrate()",
            severity="hard",
        )
        new_rule = _make_rule(
            "rule_budget",
            condition="IF daily_cost > budget_cap",  # completely different condition
            action="THEN alert_budget()",
            severity="soft",
        )

        reports = detector.check(new_rule, [existing])

        assert reports == []

    def test_no_conflict_against_empty_list(self):
        """기존 규칙 없을 때 → 충돌 없음."""
        detector = HarnessConflictDetector()
        new_rule = _make_rule("rule_new")

        reports = detector.check(new_rule, [])

        assert reports == []

    def test_meta_harness_propose_rule_blocks_on_conflict(self):
        """MetaHarness.propose_rule(): 충돌 있으면 차단, 없으면 pending 추가."""
        meta = MetaHarness(auto_apply_threshold=100)

        # 첫 번째 규칙 제안 → 충돌 없음 → pending 추가
        rule_a = _make_rule("rule_a", condition="IF x > 1", action="THEN a()")
        conflicts = meta.propose_rule(rule_a)
        assert conflicts == []
        assert len(meta.get_pending_rules()) == 1

        # 동일 조건 다른 행동 규칙 제안 → Type1 충돌 → 차단
        rule_b = _make_rule("rule_b", condition="IF x > 1", action="THEN b()")
        conflicts = meta.propose_rule(rule_b)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "type1"
        assert len(meta.get_pending_rules()) == 1  # 여전히 1개 (차단됨)
