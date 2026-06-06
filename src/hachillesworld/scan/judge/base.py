"""JudgeBackend Protocol — 반사실 평가 Judge 추상 인터페이스."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class JudgeBackend(Protocol):
    """반사실 시나리오 평가 Judge의 추상 인터페이스.

    구현체는 evaluate()와 is_deterministic을 반드시 제공해야 한다.
    is_deterministic=False인 judge를 연구·재현 목적으로 쓰면
    CounterfactualEvaluator가 UserWarning을 발생시킨다.
    """

    def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
        """반사실 시나리오에서 두 응답의 품질을 비교해 0.0~1.0을 반환한다.

        Args:
            scenario: 반사실 시나리오 설명.
            response_a: 에이전트의 예측 상태 (predicted_next_state).
            response_b: 실제 결과 상태 (actual_next_state).

        Returns:
            0.0 ~ 1.0. 1.0에 가까울수록 response_a가 반사실 예측을 잘 한 것.
        """
        ...

    @property
    def is_deterministic(self) -> bool:
        """동일 입력에 대해 항상 동일 출력을 보장하는지 여부."""
        ...
