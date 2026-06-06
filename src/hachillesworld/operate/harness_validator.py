"""HarnessRuleValidator — 시뮬레이션 기반 하네스 규칙 사전 검증. PAT-004 §9.6."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hachillesworld.optimize.harness_generator import HarnessRule


@dataclass
class ValidationResult:
    """시뮬레이션 검증 결과."""

    passed: bool
    gar_before: float
    gar_after: float
    gar_delta: float  # 음수 = 감소
    failure_reason: str | None = None


class HarnessRuleValidator:
    """신규 하네스 규칙을 시뮬레이터에서 사전 검증한다. PAT-004 §9.6.

    신규 규칙 적용 전후의 GAR(Goal Achievement Rate)을 비교하여
    GAR 감소가 5% 미만이면 PASS 판정한다.
    """

    GAR_DROP_THRESHOLD: float = 0.05  # GAR 허용 감소 임계값

    def validate(
        self,
        new_rule: HarnessRule,
        agent_fn: Callable[..., Any],
        env_fn: Callable[..., Any],
        n_episodes: int = 50,
    ) -> ValidationResult:
        """신규 규칙 적용 전후 시뮬레이션 비교 검증.

        env_fn 인터페이스:
          env_fn("reset", None)       → (initial_state, info)
          env_fn(state, action)       → (next_state, reward, done)

        agent_fn 인터페이스:
          agent_fn(state, depth: int) → action
        """
        gar_before = self._run_simulation(None, agent_fn, env_fn, n_episodes)
        gar_after = self._run_simulation(new_rule, agent_fn, env_fn, n_episodes)
        gar_delta = round(gar_after - gar_before, 4)  # 음수 = 감소
        passed = gar_delta >= -self.GAR_DROP_THRESHOLD

        return ValidationResult(
            passed=passed,
            gar_before=round(gar_before, 4),
            gar_after=round(gar_after, 4),
            gar_delta=gar_delta,
            failure_reason=(
                None
                if passed
                else f"GAR {abs(gar_delta):.1%} 감소 — 허용 임계 {self.GAR_DROP_THRESHOLD:.0%} 초과"
            ),
        )

    def _run_simulation(
        self,
        rule: HarnessRule | None,
        agent_fn: Callable[..., Any],
        env_fn: Callable[..., Any],
        n_episodes: int,
    ) -> float:
        """n_episodes 실행 후 GAR(목표 달성률)을 반환한다."""
        achieved = 0

        for _ in range(n_episodes):
            state = env_fn("reset", None)[0]

            for _ in range(25):  # 에피소드당 최대 25스텝
                action = agent_fn(state, 10)

                if rule is not None and self._rule_triggers(rule, action, state):
                    break  # hard 규칙 발동 → 에피소드 중단 (목표 미달성)

                result = env_fn(state, action)
                state, reward, done = result[0], result[1], result[2]

                if done:
                    if reward > 0:
                        achieved += 1
                    break

        return achieved / n_episodes

    def _rule_triggers(self, rule: HarnessRule, action: Any, state: Any) -> bool:
        """규칙 발동 여부를 판정한다. 키워드 기반 간이 평가.

        테스트 시 조건 문자열에 "always" / "never" 키워드로 강제 제어 가능:
          "IF always_block_..." → 항상 발동
          "IF never_triggered_..." → 절대 미발동
        """
        if rule.severity != "hard":
            return False  # soft 규칙은 차단하지 않음

        condition_lower = rule.condition.lower()
        if "always" in condition_lower:
            return True
        if "never" in condition_lower:
            return False
        if isinstance(state, dict) and "drift" in condition_lower:
            return float(state.get("drift", 0.0)) > 0.15
        return False
