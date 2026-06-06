"""LocalLLMJudge — Ollama 기반 로컬 LLM judge.

외부 API 전송 없음. seed=42, temperature=0으로 결정론적 평가를 보장한다.
논문 재현, 연구 환경, GDPR 규제 환경에 적합하다.

사전 조건:
    Ollama가 로컬에서 실행 중이어야 한다.
    기본 호스트: http://localhost:11434
    기본 모델: llama3.1:8b
    모델 설치: ollama pull llama3.1:8b
"""

from __future__ import annotations

import re


class LocalLLMJudge:
    """Ollama HTTP API를 통한 로컬 LLM judge.

    seed=42, temperature=0으로 결정론적 평가를 보장한다.
    외부 네트워크로 데이터를 전송하지 않는다.
    """

    is_deterministic: bool = True

    _SYSTEM_PROMPT = (
        "You are an expert judge evaluating counterfactual reasoning quality of AI agents. "
        "Assess how accurately the agent predicted the counterfactual outcome. "
        "Return only a single number between 0 and 10. "
        "0 means completely wrong, 10 means perfectly accurate."
    )

    def __init__(
        self,
        model: str = "llama3.1:8b",
        host: str = "http://localhost:11434",
        timeout: float = 30.0,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._timeout = timeout

    def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
        """Ollama 로컬 모델로 반사실 예측 품질을 평가한다."""
        import httpx

        prompt = (
            f"{self._SYSTEM_PROMPT}\n\n"
            f"Agent prediction: {response_a}\n"
            f"Actual outcome: {response_b}\n"
            f"Counterfactual question: {scenario}\n"
            "Score (0-10):"
        )
        resp = httpx.post(
            f"{self._host}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "options": {"seed": 42, "temperature": 0},
                "stream": False,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return self._parse_score(resp.json().get("response", "5"))

    def _parse_score(self, text: str) -> float:
        """0~10 응답 텍스트를 0.0~1.0으로 정규화한다."""
        match = re.search(r"\b(\d+(?:\.\d+)?)\b", text.strip())
        if not match:
            return 0.5
        raw = float(match.group(1))
        return max(0.0, min(1.0, raw / 10.0))
