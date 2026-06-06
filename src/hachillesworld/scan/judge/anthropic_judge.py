"""AnthropicJudge — Anthropic API 기반 LLM-as-Judge.

데이터 전송 고지:
    evaluate() 호출 시 scenario / response_a / response_b가
    Anthropic API 서버로 전송됩니다. 민감 데이터 포함 여부를
    호출자가 직접 확인해야 합니다.
    외부 전송을 원하지 않으면 LocalLLMJudge 또는 RuleBasedJudge를 사용하세요.
"""

from __future__ import annotations

import json

from hachillesworld.scan.judge.base import JudgeBackend  # noqa: F401 — Protocol 참조용


class AnthropicJudge:
    """Anthropic API를 사용하는 LLM judge.

    비결정적(is_deterministic=False)이므로 논문 재현 목적에는 부적합하다.
    프로덕션 모니터링 환경에서 높은 정확도가 필요할 때 사용한다.
    """

    is_deterministic: bool = False

    _SYSTEM_PROMPT = (
        "당신은 AI 에이전트의 반사실 추론 품질을 평가하는 전문 심사위원입니다. "
        "에이전트가 반사실 상황을 얼마나 정확히 예측했는지를 평가합니다. "
        "응답은 반드시 0.0~1.0 사이의 숫자 하나만 반환하세요. "
        "0.0은 전혀 정확하지 않음, 1.0은 완벽히 정확함을 의미합니다."
    )

    def __init__(
        self,
        client: object,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        self._client = client
        self._model = model

    def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
        """Anthropic API로 반사실 예측 품질을 평가한다."""
        prompt = (
            f"에이전트 예측: {response_a}\n"
            f"실제 결과: {response_b}\n"
            f"반사실 질문: {scenario}\n"
            "에이전트가 반사실 상황을 얼마나 정확히 예측했는지 0~1로 평가하세요."
        )
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=self._model,
            max_tokens=10,
            system=[
                {
                    "type": "text",
                    "text": self._SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        try:
            return max(0.0, min(1.0, float(raw)))
        except ValueError:
            return 0.5
