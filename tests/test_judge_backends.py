"""Sprint 5-D: Judge 백엔드 단위 테스트."""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import pytest

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator
from hachillesworld.scan.judge.anthropic_judge import AnthropicJudge
from hachillesworld.scan.judge.base import JudgeBackend
from hachillesworld.scan.judge.local_judge import LocalLLMJudge
from hachillesworld.scan.judge.rule_judge import RuleBasedJudge

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rule_judge() -> RuleBasedJudge:
    return RuleBasedJudge()


@pytest.fixture
def sample_episode() -> EpisodeRecord:
    return EpisodeRecord(
        episode_id="test-ep-001",
        agent_id="agent-a",
        goal_achieved=True,
        predicted_next_state={"status": "success", "value": 42},
        actual_next_state={"status": "success", "value": 40},
        metadata={"cf_question": "What if the agent had chosen a different path?"},
    )


@pytest.fixture
def episode_no_states() -> EpisodeRecord:
    return EpisodeRecord(
        episode_id="test-ep-002",
        agent_id="agent-b",
        goal_achieved=False,
    )


# ---------------------------------------------------------------------------
# Protocol 준수
# ---------------------------------------------------------------------------


def test_judge_protocol_compliance_rule():
    """RuleBasedJudge가 JudgeBackend Protocol을 만족하는지 확인한다."""
    judge = RuleBasedJudge()
    assert isinstance(judge, JudgeBackend)


def test_judge_protocol_compliance_local():
    """LocalLLMJudge가 JudgeBackend Protocol을 만족하는지 확인한다."""
    judge = LocalLLMJudge()
    assert isinstance(judge, JudgeBackend)


def test_judge_protocol_compliance_anthropic():
    """AnthropicJudge가 JudgeBackend Protocol을 만족하는지 확인한다."""
    mock_client = MagicMock()
    judge = AnthropicJudge(client=mock_client)
    assert isinstance(judge, JudgeBackend)


# ---------------------------------------------------------------------------
# is_deterministic
# ---------------------------------------------------------------------------


def test_anthropic_judge_is_not_deterministic():
    """AnthropicJudge는 비결정적이어야 한다."""
    mock_client = MagicMock()
    judge = AnthropicJudge(client=mock_client)
    assert judge.is_deterministic is False


def test_local_judge_is_deterministic():
    """LocalLLMJudge는 결정론적이어야 한다."""
    judge = LocalLLMJudge()
    assert judge.is_deterministic is True


def test_rule_judge_is_deterministic():
    """RuleBasedJudge는 결정론적이어야 한다."""
    judge = RuleBasedJudge()
    assert judge.is_deterministic is True


# ---------------------------------------------------------------------------
# RuleBasedJudge 동작
# ---------------------------------------------------------------------------


def test_rule_judge_no_external_calls(rule_judge: RuleBasedJudge):
    """RuleBasedJudge는 네트워크 호출 없이 동작한다."""
    with patch("socket.socket") as mock_socket:
        score = rule_judge.evaluate(
            scenario="Would the outcome differ?",
            response_a="The agent successfully completed the task.",
            response_b="The task was completed correctly.",
        )
        mock_socket.assert_not_called()
    assert 0.0 <= score <= 1.0


def test_rule_judge_same_input_same_output(rule_judge: RuleBasedJudge):
    """동일 입력에 대해 RuleBasedJudge는 항상 동일한 점수를 반환한다."""
    args = (
        "If the agent had retried, would it succeed?",
        "success achieved optimal",
        "correct result obtained",
    )
    score1 = rule_judge.evaluate(*args)
    score2 = rule_judge.evaluate(*args)
    assert score1 == score2


def test_rule_judge_score_range(rule_judge: RuleBasedJudge):
    """RuleBasedJudge 점수는 항상 0.0~1.0 범위다."""
    score = rule_judge.evaluate(
        "What if?",
        "fail error wrong",
        "success correct optimal",
    )
    assert 0.0 <= score <= 1.0


def test_rule_judge_empty_inputs(rule_judge: RuleBasedJudge):
    """빈 문자열 입력에도 오류 없이 0.0~1.0을 반환한다."""
    score = rule_judge.evaluate("", "", "")
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# LocalLLMJudge — _parse_score
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("8", 0.8),
        ("10", 1.0),
        ("0", 0.0),
        ("7.5", 0.75),
        ("Score: 6", 0.6),
        ("no number here", 0.5),
    ],
)
def test_local_judge_parse_score(text: str, expected: float):
    """LocalLLMJudge._parse_score가 0~10 응답을 0.0~1.0으로 정규화한다."""
    judge = LocalLLMJudge()
    assert judge._parse_score(text) == pytest.approx(expected, abs=1e-4)


# ---------------------------------------------------------------------------
# 비결정성 경고
# ---------------------------------------------------------------------------


def test_nondeterministic_warning():
    """비결정적 judge 직접 주입 시 UserWarning이 발생한다."""

    class FakeNonDeterministicJudge:
        is_deterministic = False

        def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
            return 0.5

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        CounterfactualEvaluator(
            judge=FakeNonDeterministicJudge(),
            judge_type="custom",
        )
    assert any("비결정적" in str(w.message) for w in caught)


def test_no_warning_for_deterministic_judge():
    """결정론적 judge는 비결정성 경고를 발생시키지 않는다."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        CounterfactualEvaluator(judge_type="rule")
    nondeterminism_warnings = [w for w in caught if "비결정적" in str(w.message)]
    assert len(nondeterminism_warnings) == 0


# ---------------------------------------------------------------------------
# CounterfactualEvaluator — judge 직접 주입
# ---------------------------------------------------------------------------


def test_evaluator_judge_injection(sample_episode: EpisodeRecord):
    """judge= 파라미터로 직접 주입한 judge가 사용된다."""
    custom_judge = RuleBasedJudge()
    evaluator = CounterfactualEvaluator(judge=custom_judge)
    result = evaluator.evaluate([sample_episode])
    assert result.n_evaluated == 1
    assert 0.0 <= result.ca_score <= 1.0


# ---------------------------------------------------------------------------
# CounterfactualEvaluator — judge_type 파라미터
# ---------------------------------------------------------------------------


def test_evaluator_judge_type_rule(sample_episode: EpisodeRecord):
    """judge_type='rule'로 초기화하면 RuleBasedJudge가 사용된다."""
    evaluator = CounterfactualEvaluator(judge_type="rule")
    assert isinstance(evaluator._judge, RuleBasedJudge)
    result = evaluator.evaluate([sample_episode])
    # type(RuleBasedJudge).__name__.lower().replace("judge","") → "rulebased"
    assert result.method == "rulebased_judge"


def test_evaluator_judge_type_selection_local():
    """judge_type='local'로 초기화하면 LocalLLMJudge 인스턴스가 생성된다."""
    evaluator = CounterfactualEvaluator(judge_type="local")
    assert isinstance(evaluator._judge, LocalLLMJudge)


def test_evaluator_judge_type_anthropic_default():
    """기본(anthropic) judge_type은 _judge=None, _client 방식을 유지한다."""
    evaluator = CounterfactualEvaluator(judge_type="anthropic")
    assert evaluator._judge is None


# ---------------------------------------------------------------------------
# CounterfactualEvaluator — 오프라인 동작 (rule judge)
# ---------------------------------------------------------------------------


def test_evaluator_rule_offline(sample_episode: EpisodeRecord):
    """CounterfactualEvaluator(judge_type='rule')는 외부 호출 없이 동작한다."""
    evaluator = CounterfactualEvaluator(judge_type="rule")
    with patch("httpx.post") as mock_post:
        result = evaluator.evaluate([sample_episode])
        mock_post.assert_not_called()
    assert 0.0 <= result.ca_score <= 1.0


def test_evaluator_proxy_fallback_no_states(episode_no_states: EpisodeRecord):
    """predicted/actual_next_state가 없으면 proxy fallback이 사용된다."""
    evaluator = CounterfactualEvaluator(judge_type="rule")
    result = evaluator.evaluate([episode_no_states])
    assert result.method == "proxy"


# ---------------------------------------------------------------------------
# AnthropicJudge — API 호출 구조
# ---------------------------------------------------------------------------


def test_anthropic_judge_evaluate_calls_api():
    """AnthropicJudge.evaluate()가 Anthropic client를 올바르게 호출한다."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="0.8")]
    mock_client.messages.create.return_value = mock_response

    judge = AnthropicJudge(client=mock_client)
    score = judge.evaluate("What if?", "predicted", "actual")

    mock_client.messages.create.assert_called_once()
    assert score == pytest.approx(0.8)
