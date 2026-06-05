"""하네스 규칙 자동 생성기."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from hachillesworld.core.models import DiagnosticReport


@dataclass
class HarnessRule:
    """단일 하네스 제약 규칙."""

    rule_id: str
    condition: str  # "IF ..." 형식의 자연어 조건
    action: str  # "THEN ..." 형식의 대응 행동
    severity: str  # "hard" | "soft"
    source: str  # 생성 근거 (진단 지표 이름)
    generated_code: str = ""


@dataclass
class HarnessSpec:
    """하네스 전체 규칙 세트."""

    agent_name: str
    rules: list[HarnessRule] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    budget_caps: dict[str, float] = field(default_factory=dict)

    def to_python(self) -> str:
        """Python 클래스 코드로 변환."""
        rules_code = "\n        ".join(
            f'"{r.rule_id}": {{"condition": "{r.condition}", '
            f'"action": "{r.action}", "severity": "{r.severity}"}},'
            for r in self.rules
        )
        forbidden_code = ", ".join(f'"{a}"' for a in self.forbidden_actions)
        return f'''\
class GeneratedHarness:
    """HAchillesWorld가 진단 데이터 기반으로 자동 생성한 하네스.
    에이전트: {self.agent_name}
    규칙 수:  {len(self.rules)}개
    """

    RULES = {{
        {rules_code}
    }}

    FORBIDDEN_ACTIONS = [{forbidden_code}]

    BUDGET_CAPS = {self.budget_caps!r}

    def allow(self, action: str, context: dict) -> bool:
        if action in self.FORBIDDEN_ACTIONS:
            return False
        for rule in self.RULES.values():
            if self._matches_condition(rule["condition"], action, context):
                if rule["severity"] == "hard":
                    return False
        return True

    def _matches_condition(self, condition: str, action: str, context: dict) -> bool:
        # 실제 구현에서는 조건 파서 사용
        return False
'''


class HarnessGenerator:
    """진단 리포트의 임계값 위반 지표로부터 하네스 규칙을 자동 생성한다.

    사용 예:
        report = client.scan(...)
        spec = HarnessGenerator().generate(report)
        print(spec.to_python())
    """

    def generate(self, report: DiagnosticReport) -> HarnessSpec:
        spec = HarnessSpec(agent_name=report.agent_name)
        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )

        for metric in all_metrics:
            if metric.status in ("warning", "critical"):
                rule = self._metric_to_rule(metric)
                if rule:
                    spec.rules.append(rule)

        # 기본 필수 금지 행동
        spec.forbidden_actions = [
            "bulk_delete_without_confirmation",
            "external_api_write_unvalidated",
            "budget_threshold_override",
            "harness_rule_bypass",
        ]

        # 비용 상한
        spec.budget_caps = {
            "daily_usd": 50.0,
            "monthly_usd": 1_200.0,
            "per_task_usd": 0.50,
        }

        return spec

    @staticmethod
    def _metric_to_rule(metric: Any) -> HarnessRule | None:
        """지표 이름과 상태에서 하네스 규칙을 생성한다."""
        mapping: dict[str, tuple[str, str, str]] = {
            "Simulation Drift Rate": (
                "IF simulation_drift > threshold",
                "THEN force_recalibration(); flag_for_review()",
                "hard",
            ),
            "Calibration ECE": (
                "IF ece_score > 0.20",
                "THEN reduce_confidence(); request_additional_observation()",
                "soft",
            ),
            "Harness Violation Attempts": (
                "IF harness_violation_detected",
                "THEN block_action(); alert_oncall(); log_incident()",
                "hard",
            ),
            "HITL Trigger Rate": (
                "IF uncertainty > 0.35 OR irreversible_action",
                "THEN require_human_approval(timeout=300)",
                "hard",
            ),
            "Cost Efficiency": (
                "IF daily_cost > budget_cap * 0.80",
                "THEN downgrade_model_tier(); notify_budget_alert()",
                "soft",
            ),
            "Checkpoint Recovery Rate": (
                "IF recovery_failure_detected",
                "THEN escalate_to_l2_support(); freeze_agent()",
                "hard",
            ),
        }
        if metric.name not in mapping:
            return None
        condition, action, severity = mapping[metric.name]
        return HarnessRule(
            rule_id=f"auto_{metric.name.lower().replace(' ', '_')}",
            condition=condition,
            action=action,
            severity=severity,
            source=metric.name,
        )


class LLMHarnessRuleGenerator:
    """LLM 기반 하네스 규칙 생성기. PAT-004 §13.4.

    실패 컨텍스트 → 규칙 후보 최대 3개 제안 (제안 전용, 자동 적용 없음).
    반드시 인간 감독자 승인 후 MetaHarness.propose_rule()로 추가할 것.
    """

    MAX_SUGGESTIONS: int = 3

    def generate(
        self,
        failure_context: str,
        existing_rules: list[HarnessRule],
        anthropic_client: Any,
    ) -> list[HarnessRule]:
        """실패 컨텍스트로부터 하네스 규칙 후보를 최대 3개 반환한다.

        반환된 규칙은 제안 상태이며, MetaHarness에 자동 추가되지 않는다.
        """
        existing_summary = "\n".join(
            f"- {r.rule_id}: {r.condition} → {r.action} [{r.severity}]" for r in existing_rules
        )
        prompt = (
            f"다음 AI 에이전트 실패 컨텍스트에 대한 안전 하네스 규칙을 "
            f"{self.MAX_SUGGESTIONS}개 제안하시오.\n"
            f"각 규칙을 JSON 배열로 반환: "
            f'[{{"condition": "IF ...", "action": "THEN ...", "severity": "hard|soft"}}]\n\n'
            f"실패 컨텍스트:\n{failure_context}\n\n"
            f"기존 규칙:\n{existing_summary or '없음'}"
        )

        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            return self._parse_rules(raw)
        except Exception:
            return []

    def _parse_rules(self, raw: str) -> list[HarnessRule]:
        """LLM 응답에서 HarnessRule 목록을 파싱한다."""
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return []

        rules: list[HarnessRule] = []
        for i, item in enumerate(data[: self.MAX_SUGGESTIONS]):
            if not isinstance(item, dict):
                continue
            severity = item.get("severity", "soft")
            if severity not in ("hard", "soft"):
                severity = "soft"
            rules.append(
                HarnessRule(
                    rule_id=f"llm_suggestion_{i + 1}",
                    condition=str(item.get("condition", "")),
                    action=str(item.get("action", "")),
                    severity=severity,
                    source="LLMHarnessRuleGenerator (제안 전용 — 인간 승인 필수)",
                )
            )
        return rules
