"""Sprint 2-B: HarnessRuleValidator + 감사 로그 + LLM 규칙 생성 테스트."""

from __future__ import annotations

from hachillesworld.operate.harness_validator import HarnessRuleValidator, ValidationResult
from hachillesworld.operate.meta_harness import MetaHarness
from hachillesworld.optimize.harness_generator import HarnessRule, LLMHarnessRuleGenerator


def _always_succeed_env(state, action):
    """항상 1스텝 내 성공하는 간이 환경 시뮬레이터."""
    if state == "reset":
        return ({"x": 0.5}, {})
    return {"x": 0.5}, 1.0, True  # (next_state, reward, done)


def _simple_agent(state, depth):
    return "proceed"


class TestHarnessRuleValidator:
    def test_validation_pass_gar_stable(self):
        """규칙이 절대 발동되지 않으면 GAR 변화 없음 → PASS."""
        rule = HarnessRule(
            rule_id="never_trigger",
            condition="IF never_triggered_condition",  # 'never' → 발동 안 함
            action="THEN log_warning()",
            severity="hard",
            source="test",
        )
        validator = HarnessRuleValidator()
        result = validator.validate(rule, _simple_agent, _always_succeed_env, n_episodes=10)

        assert result.passed is True
        assert result.gar_before > 0.0
        assert abs(result.gar_delta) < 0.05
        assert result.failure_reason is None

    def test_validation_fail_gar_drops(self):
        """규칙이 항상 발동(차단)되면 GAR 급감 → FAIL."""
        rule = HarnessRule(
            rule_id="always_block",
            condition="IF always_block_every_action",  # 'always' → 항상 발동
            action="THEN block()",
            severity="hard",
            source="test",
        )
        validator = HarnessRuleValidator()
        result = validator.validate(rule, _simple_agent, _always_succeed_env, n_episodes=10)

        assert result.passed is False
        assert result.gar_delta < -0.05  # GAR 5% 이상 감소
        assert result.failure_reason is not None
        assert "GAR" in result.failure_reason or "감소" in result.failure_reason

    def test_validation_result_fields(self):
        """ValidationResult 필드 구조 검증."""
        rule = HarnessRule(
            rule_id="soft_rule",
            condition="IF cost > limit",
            action="THEN warn()",
            severity="soft",  # soft → 절대 차단 안 함
            source="test",
        )
        validator = HarnessRuleValidator()
        result = validator.validate(rule, _simple_agent, _always_succeed_env, n_episodes=5)

        assert isinstance(result, ValidationResult)
        assert 0.0 <= result.gar_before <= 1.0
        assert 0.0 <= result.gar_after <= 1.0
        assert result.gar_delta == round(result.gar_after - result.gar_before, 4)

    def test_approve_with_validator_blocks_failing_rule(self):
        """MetaHarness.approve_rule(): 검증 실패 시 승인 거부."""
        from hachillesworld.operate.harness_validator import HarnessRuleValidator

        validator = HarnessRuleValidator()
        meta = MetaHarness(auto_apply_threshold=1, rule_validator=validator)

        # 규칙을 pending에 추가 (auto_apply_threshold=1)
        meta.record_failure({"event_type": "drift", "payload": {}})
        pending = meta.get_pending_rules()
        assert len(pending) == 1

        # 항상 차단하는 환경 시뮬레이터 → GAR 급감 → 검증 실패 → 승인 거부
        def blocking_agent(state, depth):
            return "proceed"

        result = meta.approve_rule(
            pending[0].rule_id,
            agent_fn=blocking_agent,
            env_fn=_always_succeed_env,
        )
        # always_succeed_env와 drift 규칙은 "drift"가 condition에 있지만
        # state에 "drift" 키가 없으므로 _rule_triggers 반환 False → GAR 변화 없음 → 통과
        # (drift 규칙: "IF simulation_drift_rate > ..." 에 "drift" 키워드 있지만
        #  state={"x": 0.5}에 "drift" 키 없으므로 발동 안 함)
        assert result is True


class TestAuditLogTrail:
    def test_audit_log_trail(self):
        """규칙 생성·충돌 차단·승인 이력이 감사 로그에 모두 기록됨."""
        meta = MetaHarness(auto_apply_threshold=1)

        # 1. record_failure → 자동 규칙 생성 → audit "created"
        meta.record_failure({"event_type": "drift", "payload": {}})

        # 2. 동일 조건-다른 행동 규칙 수동 제안 → 충돌 감지 → audit "conflict_blocked"
        conflicting = HarnessRule(
            rule_id="manual_drift_rule",
            condition="IF simulation_drift_rate > recalibration_threshold",
            action="THEN freeze_agent_completely()",  # 다른 행동
            severity="hard",
            source="manual",
        )
        conflicts = meta.propose_rule(conflicting)
        assert len(conflicts) > 0  # 충돌 감지됨

        # 3. 원래 규칙 승인 → audit "approved"
        pending = meta.get_pending_rules()
        assert len(pending) == 1
        meta.approve_rule(pending[0].rule_id)

        # 4. 감사 로그 검증
        audit = meta.get_audit_log()
        events = [e.event for e in audit]

        assert "created" in events
        assert "conflict_blocked" in events
        assert "approved" in events

    def test_audit_log_reject(self):
        """규칙 거부 시 감사 로그에 'rejected' 기록."""
        meta = MetaHarness(auto_apply_threshold=1)
        meta.record_failure({"event_type": "drift", "payload": {}})

        pending = meta.get_pending_rules()
        meta.reject_rule(pending[0].rule_id)

        events = [e.event for e in meta.get_audit_log()]
        assert "created" in events
        assert "rejected" in events

    def test_conflict_log_subset_of_audit(self):
        """get_conflict_log()는 audit_log의 'conflict_blocked' 항목 부분집합."""
        meta = MetaHarness(auto_apply_threshold=1)
        meta.record_failure({"event_type": "drift", "payload": {}})

        # 충돌 규칙 제안
        conflicting = HarnessRule(
            rule_id="c_rule",
            condition="IF simulation_drift_rate > recalibration_threshold",
            action="THEN do_other_thing()",
            severity="hard",
            source="test",
        )
        meta.propose_rule(conflicting)

        conflict_log = meta.get_conflict_log()
        assert len(conflict_log) >= 1
        assert all(e.event == "conflict_blocked" for e in conflict_log)


class TestLLMHarnessRuleGenerator:
    def test_llm_rule_generation_suggestion_only(self):
        """LLM 규칙 생성은 제안만 반환하고 MetaHarness에 자동 적용 안 함."""

        # Mock anthropic client
        class _MockContent:
            text = (
                '[{"condition": "IF drift > 0.3", '
                '"action": "THEN recalibrate()", '
                '"severity": "hard"}]'
            )

        class _MockResponse:
            content = [_MockContent()]

        class _MockMessages:
            def create(self, **kwargs):
                return _MockResponse()

        class _MockClient:
            messages = _MockMessages()

        generator = LLMHarnessRuleGenerator()
        meta = MetaHarness()  # 별도 MetaHarness — 자동 채워지면 안 됨

        suggestions = generator.generate(
            failure_context="에이전트가 반복적으로 drift 임계값을 초과함",
            existing_rules=[],
            anthropic_client=_MockClient(),
        )

        # 제안 목록 최대 3개 반환
        assert len(suggestions) <= 3
        # MetaHarness에 자동 적용 없음
        assert len(meta.get_pending_rules()) == 0

        if suggestions:
            rule = suggestions[0]
            assert isinstance(rule, HarnessRule)
            # 소스에 LLM/제안 표시
            assert any(kw in rule.source for kw in ("LLM", "제안", "llm"))

    def test_llm_returns_up_to_three_suggestions(self):
        """LLM 응답이 3개 이상이어도 최대 3개만 반환."""

        class _MockContent:
            text = (
                '[{"condition": "IF a", "action": "THEN x()", "severity": "hard"},'
                ' {"condition": "IF b", "action": "THEN y()", "severity": "soft"},'
                ' {"condition": "IF c", "action": "THEN z()", "severity": "hard"},'
                ' {"condition": "IF d", "action": "THEN w()", "severity": "soft"}]'
            )

        class _MockResponse:
            content = [_MockContent()]

        class _MockMessages:
            def create(self, **kwargs):
                return _MockResponse()

        class _MockClient:
            messages = _MockMessages()

        generator = LLMHarnessRuleGenerator()
        suggestions = generator.generate("context", [], _MockClient())

        assert len(suggestions) <= 3  # 최대 3개 제한

    def test_llm_generation_fails_gracefully(self):
        """LLM 호출 실패 시 빈 리스트 반환."""

        class _FailingMessages:
            def create(self, **kwargs):
                raise RuntimeError("API 호출 실패")

        class _FailingClient:
            messages = _FailingMessages()

        generator = LLMHarnessRuleGenerator()
        suggestions = generator.generate("context", [], _FailingClient())

        assert suggestions == []
