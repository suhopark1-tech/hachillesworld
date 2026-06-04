"""Meta-Harness — 실패 패턴으로부터 하네스 규칙을 자동 학습한다."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hachillesworld.optimize.harness_generator import HarnessRule


@dataclass
class FailurePattern:
    """감지된 실패 패턴."""

    pattern_id: str
    description: str
    occurrences: int
    first_seen: float
    last_seen: float
    example_payload: dict[str, Any] = field(default_factory=dict)
    suggested_rule: HarnessRule | None = None


class MetaHarness:
    """
    에이전트의 반복 실패 패턴을 자동 감지하고
    새 하네스 규칙을 제안·적용하는 Meta-Harness.

    사용 예:
        meta = MetaHarness(auto_apply_threshold=5)
        meta.record_failure(event)
        new_rules = meta.get_pending_rules()
    """

    def __init__(
        self,
        auto_apply_threshold: int = 10,
        human_review_required: bool = True,
    ) -> None:
        self.auto_apply_threshold = auto_apply_threshold
        self.human_review_required = human_review_required
        self._patterns: dict[str, FailurePattern] = {}
        self._applied_rules: list[HarnessRule] = []
        self._pending_rules: list[HarnessRule] = []

    def record_failure(self, event: dict[str, Any]) -> None:
        """실패 이벤트를 기록하고 패턴을 업데이트한다."""
        key = self._extract_pattern_key(event)
        now = time.time()

        if key in self._patterns:
            self._patterns[key].occurrences += 1
            self._patterns[key].last_seen = now
        else:
            self._patterns[key] = FailurePattern(
                pattern_id=key,
                description=self._describe_pattern(event),
                occurrences=1,
                first_seen=now,
                last_seen=now,
                example_payload=event.get("payload", {}),
                suggested_rule=self._suggest_rule(key, event),
            )

        pattern = self._patterns[key]
        if (
            pattern.occurrences >= self.auto_apply_threshold
            and pattern.suggested_rule
            and pattern.suggested_rule not in self._pending_rules
            and pattern.suggested_rule not in self._applied_rules
        ):
            self._pending_rules.append(pattern.suggested_rule)

    def get_pending_rules(self) -> list[HarnessRule]:
        """검토 대기 중인 신규 하네스 규칙 목록."""
        return list(self._pending_rules)

    def approve_rule(self, rule_id: str) -> bool:
        """규칙을 승인해 실제 하네스에 적용한다."""
        for rule in self._pending_rules:
            if rule.rule_id == rule_id:
                self._pending_rules.remove(rule)
                self._applied_rules.append(rule)
                return True
        return False

    def reject_rule(self, rule_id: str) -> bool:
        """규칙 제안을 거부한다."""
        for rule in self._pending_rules:
            if rule.rule_id == rule_id:
                self._pending_rules.remove(rule)
                return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "pending_rules": len(self._pending_rules),
            "applied_rules": len(self._applied_rules),
            "top_patterns": [
                {"id": p.pattern_id, "occurrences": p.occurrences, "description": p.description}
                for p in sorted(self._patterns.values(), key=lambda x: x.occurrences, reverse=True)[
                    :5
                ]
            ],
        }

    @staticmethod
    def _extract_pattern_key(event: dict[str, Any]) -> str:
        """이벤트에서 패턴 식별 키를 추출한다."""
        event_type = event.get("event_type", "unknown")
        error_type = event.get("payload", {}).get("error_type", "")
        return f"{event_type}:{error_type}" if error_type else event_type

    @staticmethod
    def _describe_pattern(event: dict[str, Any]) -> str:
        payload = event.get("payload", {})
        event_type = event.get("event_type", "unknown")
        return payload.get("description", f"{event_type} 이벤트에서 반복 실패 감지")

    @staticmethod
    def _suggest_rule(key: str, event: dict[str, Any]) -> HarnessRule | None:
        """패턴 키에서 하네스 규칙을 자동 생성한다."""
        if "drift" in key:
            return HarnessRule(
                rule_id=f"meta_{key.replace(':', '_')}",
                condition="IF simulation_drift_rate > recalibration_threshold",
                action="THEN force_immediate_recalibration(); log_drift_event()",
                severity="hard",
                source="MetaHarness 자동 생성",
            )
        if "cost" in key or "budget" in key:
            return HarnessRule(
                rule_id=f"meta_{key.replace(':', '_')}",
                condition="IF daily_cost > budget_cap",
                action="THEN switch_to_lightweight_model(); send_budget_alert()",
                severity="soft",
                source="MetaHarness 자동 생성",
            )
        return None
