"""Counterfactual Accuracy 자동 측정 테스트 — HAW-TR-001 ALM-3."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.scan.counterfactual_evaluator import CAResult, CounterfactualEvaluator
from hachillesworld.scan.engine import ScanEngine
from hachillesworld.scan.metrics import MetricsCalculator

# ── 헬퍼 ─────────────────────────────────────────────────────


def make_episode(
    predicted: dict | None = None,
    actual: dict | None = None,
    goal_achieved: bool = True,
    max_error: float | None = None,
    episode_id: str | None = None,
) -> EpisodeRecord:
    ep = EpisodeRecord(agent_id="test-agent")
    ep.predicted_next_state = predicted
    ep.actual_next_state = actual
    ep.goal_achieved = goal_achieved
    ep.max_prediction_error = max_error
    if episode_id:
        ep.episode_id = episode_id
    return ep


def make_mock_client(score_text: str = "0.8", input_tokens: int = 100) -> MagicMock:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = score_text
    mock_response.usage.input_tokens = input_tokens
    mock_client.messages.create.return_value = mock_response
    return mock_client


# ── 픽스처 ────────────────────────────────────────────────────


@pytest.fixture
def episodes_with_states():
    return [
        make_episode({"state": "done"}, {"state": "done"}, True, 0.05, "ep1"),
        make_episode({"state": "pending"}, {"state": "failed"}, False, 0.40, "ep2"),
        make_episode({"state": "done"}, {"state": "done"}, True, 0.10, "ep3"),
    ]


@pytest.fixture
def sample_config():
    return {
        "laws_domain": "digital",
        "harness_rules": ["r" + str(i) for i in range(20)],
        "monthly_budget_usd": 1000.0,
    }


# ── CA 기본 동작 테스트 ────────────────────────────────────────


class TestCABasicEvaluation:
    def test_proxy_fallback_no_client(self, episodes_with_states):
        evaluator = CounterfactualEvaluator()
        result = evaluator.evaluate(episodes_with_states)

        assert isinstance(result, CAResult)
        assert 0.0 <= result.ca_score <= 1.0
        assert result.n_evaluated == 3
        assert result.method == "proxy"
        assert len(result.judge_scores) == 3

    def test_proxy_uses_max_prediction_error(self):
        episodes = [
            make_episode(max_error=0.0),
            make_episode(max_error=0.5),
            make_episode(max_error=1.0),
        ]
        evaluator = CounterfactualEvaluator()
        result = evaluator.evaluate(episodes)

        assert result.method == "proxy"
        assert result.judge_scores[0] == pytest.approx(1.0)
        assert result.judge_scores[1] == pytest.approx(0.5)
        assert result.judge_scores[2] == pytest.approx(0.0)

    def test_proxy_uses_goal_achieved_when_no_error(self):
        episodes = [
            make_episode(goal_achieved=True),
            make_episode(goal_achieved=False),
        ]
        evaluator = CounterfactualEvaluator()
        result = evaluator.evaluate(episodes)

        assert result.judge_scores[0] == pytest.approx(1.0)
        assert result.judge_scores[1] == pytest.approx(0.0)

    def test_proxy_empty_episodes_returns_half(self):
        evaluator = CounterfactualEvaluator()
        result = evaluator.evaluate([])

        assert result.ca_score == pytest.approx(0.5)
        assert result.n_evaluated == 0

    def test_spearman_ca_high_correlation(self):
        judge_scores = [0.9, 0.8, 0.2, 0.1]
        actual_outcomes = [1.0, 1.0, 0.0, 0.0]
        ca = CounterfactualEvaluator._compute_ca(judge_scores, actual_outcomes)
        assert ca > 0.7

    def test_spearman_ca_less_than_3_uses_mean(self):
        judge_scores = [0.8, 0.6]
        actual_outcomes = [1.0, 0.0]
        ca = CounterfactualEvaluator._compute_ca(judge_scores, actual_outcomes)
        assert ca == pytest.approx(0.7)

    def test_spearman_ca_empty_returns_zero(self):
        ca = CounterfactualEvaluator._compute_ca([], [])
        assert ca == pytest.approx(0.0)

    def test_llm_judge_score_parsed_correctly(self, episodes_with_states):
        mock_client = make_mock_client("0.75")
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client)
        result = evaluator.evaluate(episodes_with_states)

        assert result.method == "llm_judge"
        assert result.n_evaluated == 3
        for score in result.judge_scores:
            assert score == pytest.approx(0.75)

    def test_llm_judge_invalid_response_defaults_to_half(self):
        mock_client = make_mock_client("invalid_score")
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client)
        episodes = [make_episode({"s": 1}, {"s": 2}, True, episode_id="ep1")]
        result = evaluator.evaluate(episodes)

        assert result.judge_scores[0] == pytest.approx(0.5)

    def test_llm_judge_cost_estimated(self, episodes_with_states):
        mock_client = make_mock_client("0.8", input_tokens=1000)
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client)
        result = evaluator.evaluate(episodes_with_states)

        assert result.cost_usd > 0.0


# ── Prompt Caching 테스트 ──────────────────────────────────────


class TestCAPromptCaching:
    def test_cache_control_ephemeral_applied(self, episodes_with_states):
        mock_client = make_mock_client()
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client)
        evaluator.evaluate(episodes_with_states)

        assert mock_client.messages.create.called
        call_kwargs = mock_client.messages.create.call_args[1]
        system_block = call_kwargs["system"][0]
        assert system_block["cache_control"] == {"type": "ephemeral"}

    def test_eval_cache_prevents_duplicate_api_calls(self, episodes_with_states):
        mock_client = make_mock_client("0.7")
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client, cache_evaluations=True)

        evaluator.evaluate(episodes_with_states)
        first_count = mock_client.messages.create.call_count

        result = evaluator.evaluate(episodes_with_states)
        assert mock_client.messages.create.call_count == first_count
        assert result.cache_hit_rate == pytest.approx(1.0)

    def test_cache_hit_rate_zero_on_first_call(self, episodes_with_states):
        mock_client = make_mock_client()
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client, cache_evaluations=True)
        result = evaluator.evaluate(episodes_with_states)
        assert result.cache_hit_rate == pytest.approx(0.0)

    def test_cache_disabled_always_calls_api(self, episodes_with_states):
        mock_client = make_mock_client()
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client, cache_evaluations=False)

        evaluator.evaluate(episodes_with_states)
        first_count = mock_client.messages.create.call_count

        evaluator.evaluate(episodes_with_states)
        assert mock_client.messages.create.call_count == first_count * 2


# ── 프록시 Fallback 테스트 ─────────────────────────────────────


class TestCAProxyFallback:
    def test_proxy_when_no_api_key(self, episodes_with_states):
        evaluator = CounterfactualEvaluator(anthropic_client=None)
        result = evaluator.evaluate(episodes_with_states)
        assert result.method == "proxy"
        assert result.cost_usd == pytest.approx(0.0)

    def test_proxy_when_no_states_available(self):
        """predicted_next_state가 없으면 LLM을 호출하지 않고 proxy로 fallback."""
        episodes = [
            EpisodeRecord(agent_id="a", goal_achieved=True),
            EpisodeRecord(agent_id="a", goal_achieved=False),
        ]
        mock_client = make_mock_client()
        evaluator = CounterfactualEvaluator(anthropic_client=mock_client)
        result = evaluator.evaluate(episodes)

        assert result.method == "proxy"
        assert not mock_client.messages.create.called

    def test_proxy_cost_is_zero(self):
        episodes = [make_episode(max_error=0.2)]
        evaluator = CounterfactualEvaluator()
        result = evaluator.evaluate(episodes)
        assert result.cost_usd == pytest.approx(0.0)


# ── ScanEngine 통합 테스트 ─────────────────────────────────────


class TestCAIntegrated:
    def test_ca_metric_in_agency_level(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        metric_names = [m.name for m in report.agency_level.metrics]
        assert "Counterfactual Accuracy" in metric_names

    def test_total_metrics_count_stays_15(self, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        all_names = [
            m.name
            for m in (
                report.world_model_quality.metrics
                + report.agency_level.metrics
                + report.operational_health.metrics
            )
        ]
        assert len(all_names) == 15

    def test_ca_metric_with_episodes(self, episodes_with_states, sample_config):
        engine = ScanEngine(config=sample_config)
        report = engine.run(
            logs=[],
            agent_name="test-agent",
            episodes=episodes_with_states,
        )

        ca_metric = next(
            m for m in report.agency_level.metrics if m.name == "Counterfactual Accuracy"
        )
        assert 0.0 <= ca_metric.value <= 1.0
        assert ca_metric.status in ("ok", "warning", "critical")

    def test_ca_metric_no_episodes_defaults_critical(self, sample_config):
        """에피소드가 없으면 CA=0.5 → critical 상태 (0.5 < warning threshold 0.60)."""
        engine = ScanEngine(config=sample_config)
        report = engine.run(logs=[], agent_name="test-agent")

        ca_metric = next(
            m for m in report.agency_level.metrics if m.name == "Counterfactual Accuracy"
        )
        assert ca_metric.value == pytest.approx(0.5)
        assert ca_metric.status == "critical"

    def test_metrics_calculator_ca_direct_call(self, episodes_with_states, sample_config):
        calc = MetricsCalculator(
            logs=[],
            config=sample_config,
            episodes=episodes_with_states,
        )
        metric = calc.counterfactual_accuracy()
        assert metric.name == "Counterfactual Accuracy"
        assert 0.0 <= metric.value <= 1.0
        assert metric.status in ("ok", "warning", "critical")

    def test_scan_engine_with_api_key_creates_evaluator(self, sample_config):
        """anthropic_api_key 제공 시 CounterfactualEvaluator가 생성되어야 한다."""
        # Anthropic 클라이언트는 초기화 시 API 호출이 없으므로 invalid key도 허용
        engine = ScanEngine(config=sample_config, anthropic_api_key="sk-ant-test-invalid")
        assert engine._ca_evaluator is not None
        assert isinstance(engine._ca_evaluator, CounterfactualEvaluator)

    def test_scan_engine_no_api_key_ca_evaluator_is_none(self, sample_config):
        """anthropic_api_key 미제공 시 _ca_evaluator는 None이어야 한다."""
        engine = ScanEngine(config=sample_config)
        assert engine._ca_evaluator is None
