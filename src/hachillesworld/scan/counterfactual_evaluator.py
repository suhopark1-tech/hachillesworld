"""Counterfactual Accuracy (CA) 자동 측정 — LLM-as-Judge (HAW-TR-001 §4.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import spearmanr

from hachillesworld.collect.episode import EpisodeRecord


@dataclass
class CAResult:
    ca_score: float
    n_evaluated: int
    judge_scores: list[float] = field(default_factory=list)
    cache_hit_rate: float = 0.0
    cost_usd: float = 0.0
    method: str = "proxy"  # "llm_judge" | "proxy"


class CounterfactualEvaluator:
    """CA 자동 계산: LLM-as-Judge + Prompt Caching.

    Anthropic SDK의 system-prompt Prompt Caching을 활용해
    반복 에피소드 평가 비용을 최소화한다.
    anthropic_client=None이면 max_prediction_error 기반 프록시로 fallback.
    """

    _SYSTEM_PROMPT = (
        "당신은 AI 에이전트의 반사실 추론 품질을 평가하는 전문 심사위원입니다. "
        "에이전트가 반사실 상황을 얼마나 정확히 예측했는지를 평가합니다. "
        "응답은 반드시 0.0~1.0 사이의 숫자 하나만 반환하세요. "
        "0.0은 전혀 정확하지 않음, 1.0은 완벽히 정확함을 의미합니다."
    )

    def __init__(
        self,
        anthropic_client: object | None = None,
        model: str = "claude-sonnet-4-6",
        *,
        cache_evaluations: bool = True,
    ) -> None:
        self._client = anthropic_client
        self._model = model
        self._cache_evaluations = cache_evaluations
        self._eval_cache: dict[str, float] = {}

    def evaluate(self, episodes: list[EpisodeRecord]) -> CAResult:
        """에피소드 리스트에서 CA를 계산한다.

        predicted_next_state / actual_next_state 쌍이 있는 에피소드를
        LLM-as-Judge로 평가한다. 없거나 API 키가 없으면 프록시로 fallback.
        """
        evaluable = [
            ep
            for ep in episodes
            if ep.predicted_next_state is not None and ep.actual_next_state is not None
        ]
        if not evaluable or self._client is None:
            return self._proxy_fallback(episodes)
        return self._llm_evaluate(evaluable)

    def _llm_evaluate(self, episodes: list[EpisodeRecord]) -> CAResult:
        judge_scores: list[float] = []
        actual_outcomes: list[float] = []
        total_cost = 0.0
        cache_hits = 0

        for ep in episodes:
            cache_key = ep.episode_id
            if self._cache_evaluations and cache_key in self._eval_cache:
                score = self._eval_cache[cache_key]
                cache_hits += 1
            else:
                score, cost = self._judge_single(ep)
                total_cost += cost
                if self._cache_evaluations:
                    self._eval_cache[cache_key] = score

            judge_scores.append(score)
            actual_outcomes.append(1.0 if ep.goal_achieved else 0.0)

        ca_score = self._compute_ca(judge_scores, actual_outcomes)
        cache_hit_rate = cache_hits / len(episodes) if episodes else 0.0

        return CAResult(
            ca_score=ca_score,
            n_evaluated=len(episodes),
            judge_scores=judge_scores,
            cache_hit_rate=cache_hit_rate,
            cost_usd=total_cost,
            method="llm_judge",
        )

    def _judge_single(self, ep: EpisodeRecord) -> tuple[float, float]:
        """단일 에피소드에 대한 LLM Judge 평가. (score, cost_usd) 반환."""
        predicted_str = json.dumps(ep.predicted_next_state, ensure_ascii=False)
        actual_str = json.dumps(ep.actual_next_state, ensure_ascii=False)
        cf_question = ep.metadata.get(
            "cf_question",
            "에이전트가 다른 행동을 선택했다면 결과가 달라졌을까요?",
        )

        response = self._client.messages.create(  # type: ignore[union-attr]
            model=self._model,
            max_tokens=10,
            system=[
                {
                    "type": "text",
                    "text": self._SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"에이전트 예측: {predicted_str}\n"
                        f"실제 결과: {actual_str}\n"
                        f"반사실 질문: {cf_question}\n"
                        "에이전트가 반사실 상황을 얼마나 정확히 예측했는지 0~1로 평가하세요."
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        try:
            score = max(0.0, min(1.0, float(raw)))
        except ValueError:
            score = 0.5

        input_tokens = getattr(response.usage, "input_tokens", 0)
        cost_usd = float(input_tokens) * 3e-6  # claude-sonnet-4-6 근사값

        return score, cost_usd

    def _proxy_fallback(self, episodes: list[EpisodeRecord]) -> CAResult:
        """max_prediction_error 기반 프록시 CA 계산.

        에피소드가 없으면 0.5(미측정)를 반환한다.
        """
        if not episodes:
            return CAResult(
                ca_score=0.5,
                n_evaluated=0,
                judge_scores=[],
                cache_hit_rate=0.0,
                cost_usd=0.0,
                method="proxy",
            )

        scores: list[float] = []
        for ep in episodes:
            if ep.max_prediction_error is not None:
                scores.append(max(0.0, 1.0 - ep.max_prediction_error))
            else:
                scores.append(1.0 if ep.goal_achieved else 0.0)

        ca_score = float(np.mean(scores))
        return CAResult(
            ca_score=ca_score,
            n_evaluated=len(episodes),
            judge_scores=scores,
            cache_hit_rate=0.0,
            cost_usd=0.0,
            method="proxy",
        )

    @staticmethod
    def _compute_ca(judge_scores: list[float], actual_outcomes: list[float]) -> float:
        """Judge 점수와 실제 결과의 Spearman 상관계수로 CA를 산출한다.

        샘플이 3개 미만이면 judge 점수 평균을 반환한다.
        상관계수 [-1, 1]은 [0, 1]로 정규화된다.
        """
        if len(judge_scores) < 3:
            return float(np.mean(judge_scores)) if judge_scores else 0.0
        corr, _ = spearmanr(judge_scores, actual_outcomes)
        if np.isnan(corr):
            return float(np.mean(judge_scores))
        return max(0.0, float((corr + 1.0) / 2.0))
