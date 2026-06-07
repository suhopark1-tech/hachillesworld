"""RuleBasedJudge — 규칙·휴리스틱 기반 완전 오프라인 judge.

외부 의존성 없음. 네트워크 호출 없음. 순수 Python.
정확도는 낮지만 CI/CD 파이프라인, 오프라인 환경, GDPR 최고 규제 환경에 적합하다.
"""

from __future__ import annotations

import re

_SUCCESS_KEYWORDS = frozenset(
    {
        "success",
        "correct",
        "optimal",
        "achieved",
        "completed",
        "accurate",
        "valid",
        "right",
        "better",
        "improved",
        "성공",
        "정확",
        "달성",
        "완료",
        "올바른",
        "최적",
    }
)

_FAILURE_KEYWORDS = frozenset(
    {
        "fail",
        "wrong",
        "incorrect",
        "error",
        "missed",
        "inaccurate",
        "invalid",
        "worse",
        "degraded",
        "실패",
        "오류",
        "잘못",
        "부정확",
    }
)

_CF_INDICATORS = frozenset(
    {
        "if",
        "would",
        "could",
        "should",
        "had",
        "were",
        "might",
        "hypothetically",
        "alternatively",
        "만약",
        "했다면",
        "경우",
        "대신",
    }
)


class RuleBasedJudge:
    """키워드·휴리스틱 기반 오프라인 judge.

    세 가지 신호를 결합한다:
    1. 구조적 유사성 — response_a / response_b 간 공통 토큰 비율
    2. 목표 달성 키워드 — success·correct·optimal 등 탐지
    3. 반사실 일관성 — if·would 등 조건절 지시어 포함 여부
    """

    is_deterministic: bool = True

    def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
        """규칙 기반으로 반사실 예측 품질을 평가한다."""
        structural = self._structural_similarity(response_a, response_b)
        goal = self._goal_achievement_score(response_a)
        cf_consistency = self._counterfactual_consistency(response_a, scenario)
        return round((structural * 0.4 + goal * 0.4 + cf_consistency * 0.2), 4)

    def _structural_similarity(self, text_a: str, text_b: str) -> float:
        tokens_a = set(self._tokenize(text_a))
        tokens_b = set(self._tokenize(text_b))
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def _goal_achievement_score(self, text: str) -> float:
        tokens = set(self._tokenize(text))
        hits = tokens & _SUCCESS_KEYWORDS
        misses = tokens & _FAILURE_KEYWORDS
        if not hits and not misses:
            return 0.5
        total = len(hits) + len(misses)
        return len(hits) / total

    def _counterfactual_consistency(self, response: str, scenario: str) -> float:
        combined = self._tokenize(response) + self._tokenize(scenario)
        cf_present = any(tok in _CF_INDICATORS for tok in combined)
        return 0.8 if cf_present else 0.3

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [tok.lower() for tok in re.findall(r"\b\w+\b", text)]
