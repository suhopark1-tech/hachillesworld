"""Meta-Harness — 실패 패턴으로부터 하네스 규칙을 자동 학습한다."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hachillesworld.optimize.harness_generator import HarnessRule


@dataclass
class ConflictReport:
    """규칙 충돌 감지 결과. PAT-004 §9.5."""

    conflict_type: str  # "type1" | "type2" | "type3"
    conflicting_rule_id: str
    description: str
    recommendation: str


@dataclass
class AuditEntry:
    """규칙 이력 감사 로그 단위 항목. PAT-004 종속항 9."""

    # "created" | "proposed" | "conflict_blocked" | "approved" | "rejected" | "validation_failed"
    event: str
    rule_id: str
    timestamp: float
    details: str = ""


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


class HarnessConflictDetector:
    """신규 규칙과 기존 규칙 간 충돌을 3유형으로 자동 감지한다. PAT-004 §9.5.

    Type1: 동일 조건-상반 행동 (same condition, different action)
    Type2: 완전 중복 (same condition + same action + same severity)
    Type3: hard-soft 강도 혼용 (same condition + same action, different severity)
    """

    def check(
        self,
        new_rule: HarnessRule,
        existing_rules: list[HarnessRule],
    ) -> list[ConflictReport]:
        """새 규칙과 기존 규칙 집합 간 충돌 목록을 반환한다. 없으면 빈 리스트."""
        reports: list[ConflictReport] = []

        for existing in existing_rules:
            if existing.condition != new_rule.condition:
                continue  # 조건이 다르면 충돌 없음

            same_action = existing.action == new_rule.action
            same_severity = existing.severity == new_rule.severity

            if same_action and same_severity:
                # Type2: 완전 중복
                reports.append(
                    ConflictReport(
                        conflict_type="type2",
                        conflicting_rule_id=existing.rule_id,
                        description=f"완전 중복: rule_id={existing.rule_id}와 동일",
                        recommendation="신규 규칙 추가 불필요 — 기존 규칙 재사용",
                    )
                )
            elif not same_action:
                # Type1: 동일 조건-상반 행동
                reports.append(
                    ConflictReport(
                        conflict_type="type1",
                        conflicting_rule_id=existing.rule_id,
                        description=(
                            f"동일 조건-상반 행동: rule_id={existing.rule_id} "
                            f"(기존: {existing.action[:40]})"
                        ),
                        recommendation="조건 세분화 또는 우선순위 명시 필요",
                    )
                )
            elif not same_severity:
                # Type3: 동일 조건·행동 + 강도 혼용
                reports.append(
                    ConflictReport(
                        conflict_type="type3",
                        conflicting_rule_id=existing.rule_id,
                        description=(
                            f"hard-soft 강도 혼용: rule_id={existing.rule_id} "
                            f"({existing.severity} + {new_rule.severity})"
                        ),
                        recommendation="강도 통일 또는 분리 조건 명시 필요",
                    )
                )

        return reports


class MetaHarness:
    """에이전트의 반복 실패 패턴을 자동 감지하고
    새 하네스 규칙을 제안·적용하는 Meta-Harness. PAT-004 §9.3.

    사용 예:
        meta = MetaHarness(auto_apply_threshold=5)
        meta.record_failure(event)
        new_rules = meta.get_pending_rules()
    """

    def __init__(
        self,
        auto_apply_threshold: int = 10,
        human_review_required: bool = True,
        rule_validator: Any = None,
    ) -> None:
        self.auto_apply_threshold = auto_apply_threshold
        self.human_review_required = human_review_required
        self.rule_validator = rule_validator  # Optional HarnessRuleValidator
        self.conflict_detector = HarnessConflictDetector()
        self._patterns: dict[str, FailurePattern] = {}
        self._applied_rules: list[HarnessRule] = []
        self._pending_rules: list[HarnessRule] = []
        self._audit_log: list[AuditEntry] = []

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
            and pattern.suggested_rule is not None
            and pattern.suggested_rule not in self._pending_rules
            and pattern.suggested_rule not in self._applied_rules
        ):
            # 충돌 검사 후 대기열 추가 (PAT-004 종속항 5)
            conflicts = self.conflict_detector.check(
                pattern.suggested_rule,
                self._applied_rules + self._pending_rules,
            )
            if conflicts:
                self._audit_log.append(
                    AuditEntry(
                        event="conflict_blocked",
                        rule_id=pattern.suggested_rule.rule_id,
                        timestamp=now,
                        details=f"{len(conflicts)}개 충돌 감지 (자동 생성 차단)",
                    )
                )
            else:
                self._pending_rules.append(pattern.suggested_rule)
                self._audit_log.append(
                    AuditEntry(
                        event="created",
                        rule_id=pattern.suggested_rule.rule_id,
                        timestamp=now,
                        details=f"패턴 '{key}' {pattern.occurrences}회 → 자동 생성",
                    )
                )

    def propose_rule(self, rule: HarnessRule) -> list[ConflictReport]:
        """규칙을 수동으로 제안한다. 충돌 없으면 pending에 추가.

        반환값: ConflictReport 목록 (빈 리스트 = 충돌 없음, 규칙 추가됨)
        """
        conflicts = self.conflict_detector.check(rule, self._applied_rules + self._pending_rules)
        if conflicts:
            self._audit_log.append(
                AuditEntry(
                    event="conflict_blocked",
                    rule_id=rule.rule_id,
                    timestamp=time.time(),
                    details=f"{len(conflicts)}개 충돌 감지 (수동 제안 차단)",
                )
            )
            return conflicts
        if rule not in self._pending_rules:
            self._pending_rules.append(rule)
        self._audit_log.append(
            AuditEntry(
                event="proposed",
                rule_id=rule.rule_id,
                timestamp=time.time(),
            )
        )
        return []

    def get_pending_rules(self) -> list[HarnessRule]:
        """검토 대기 중인 신규 하네스 규칙 목록."""
        return list(self._pending_rules)

    def approve_rule(
        self,
        rule_id: str,
        agent_fn: Callable | None = None,
        env_fn: Callable | None = None,
    ) -> bool:
        """규칙을 승인해 실제 하네스에 적용한다.

        rule_validator + agent_fn + env_fn 모두 제공 시 시뮬레이션 검증 후 승인.
        검증 실패 시 False 반환 (승인 거부). PAT-004 종속항 6.
        """
        for rule in self._pending_rules:
            if rule.rule_id == rule_id:
                if self.rule_validator is not None and agent_fn is not None and env_fn is not None:
                    val_result = self.rule_validator.validate(rule, agent_fn, env_fn)
                    if not val_result.passed:
                        self._audit_log.append(
                            AuditEntry(
                                event="validation_failed",
                                rule_id=rule_id,
                                timestamp=time.time(),
                                details=val_result.failure_reason or "시뮬 검증 실패",
                            )
                        )
                        return False
                self._pending_rules.remove(rule)
                self._applied_rules.append(rule)
                self._audit_log.append(
                    AuditEntry(
                        event="approved",
                        rule_id=rule_id,
                        timestamp=time.time(),
                    )
                )
                return True
        return False

    def reject_rule(self, rule_id: str) -> bool:
        """규칙 제안을 거부한다."""
        for rule in self._pending_rules:
            if rule.rule_id == rule_id:
                self._pending_rules.remove(rule)
                self._audit_log.append(
                    AuditEntry(
                        event="rejected",
                        rule_id=rule_id,
                        timestamp=time.time(),
                    )
                )
                return True
        return False

    def get_applied_rules(self) -> list[HarnessRule]:
        """현재 활성화된 하네스 규칙 목록."""
        return list(self._applied_rules)

    def get_audit_log(self) -> list[AuditEntry]:
        """전체 규칙 이력 감사 로그. PAT-004 종속항 9."""
        return list(self._audit_log)

    def get_conflict_log(self) -> list[AuditEntry]:
        """충돌로 차단된 규칙 이력."""
        return [e for e in self._audit_log if e.event == "conflict_blocked"]

    def summary(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "pending_rules": len(self._pending_rules),
            "applied_rules": len(self._applied_rules),
            "top_patterns": [
                {
                    "id": p.pattern_id,
                    "occurrences": p.occurrences,
                    "description": p.description,
                }
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
        return str(payload.get("description", f"{event_type} 이벤트에서 반복 실패 감지"))

    @staticmethod
    def _suggest_rule(key: str, event: dict[str, Any]) -> HarnessRule | None:
        """패턴 키에서 IF-THEN 하네스 규칙을 자동 생성한다."""
        rule_id_base = f"meta_{key.replace(':', '_')}"

        if "drift" in key:
            return HarnessRule(
                rule_id=rule_id_base,
                condition="IF simulation_drift_rate > recalibration_threshold",
                action="THEN force_immediate_recalibration(); log_drift_event()",
                severity="hard",
                source="MetaHarness 자동 생성",
            )
        if "cost" in key or "budget" in key:
            return HarnessRule(
                rule_id=rule_id_base,
                condition="IF daily_cost > budget_cap",
                action="THEN switch_to_lightweight_model(); send_budget_alert()",
                severity="soft",
                source="MetaHarness 자동 생성",
            )
        if "uncertainty" in key:
            return HarnessRule(
                rule_id=rule_id_base,
                condition="IF uncertainty > uncertainty_threshold",
                action="THEN require_human_approval(timeout=300)",
                severity="hard",
                source="MetaHarness 자동 생성",
            )
        if "harness" in key or "violation" in key:
            return HarnessRule(
                rule_id=rule_id_base,
                condition="IF harness_violation_detected",
                action="THEN block_action(); alert_oncall(); log_incident()",
                severity="hard",
                source="MetaHarness 자동 생성",
            )
        return None
