"""Sprint 5-A: PII 필터링 및 데이터 전송 고지 테스트."""

from __future__ import annotations

import warnings

import pytest

from hachillesworld.privacy.data_classifier import DataClassifier, DataClassification


class TestDataClassification:
    """DataClassifier.classify() — PII 탐지 테스트."""

    def test_clean_payload_no_pii(self) -> None:
        payload = {"predicted_state": {"x": 0.5, "velocity": 1.2}, "score": 0.8}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is False
        assert result.safe_to_transmit is True
        assert result.risk_level == "low"

    def test_detects_user_id_key(self) -> None:
        payload = {"user_id": "abc123", "state": {"x": 0.5}}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True
        assert result.safe_to_transmit is False
        assert any("user_id" in k for k in result.pii_keys)

    def test_detects_email_key(self) -> None:
        payload = {"email": "test@example.com", "data": 1}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True

    def test_detects_nested_pii_key(self) -> None:
        payload = {"metadata": {"user_info": {"email": "test@test.com"}}}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True

    def test_detects_email_in_value(self) -> None:
        payload = {"agent_info": "Contact: user@domain.com for support"}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True
        assert len(result.pii_value_keys) >= 1

    def test_detects_phone_in_value(self) -> None:
        payload = {"description": "Call 010-1234-5678 for help"}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True

    def test_detects_password_key(self) -> None:
        payload = {"password": "secret123"}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True

    def test_detects_token_key(self) -> None:
        payload = {"api_token": "sk-abc", "data": 0}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is True

    def test_numeric_values_not_flagged(self) -> None:
        payload = {"sdr": 0.03, "ece": 0.04, "latency_ms": 120}
        result = DataClassifier().classify(payload)
        assert result.contains_pii is False

    def test_risk_level_high_when_pii(self) -> None:
        payload = {"email": "x@x.com"}
        result = DataClassifier().classify(payload)
        assert result.risk_level == "high"


class TestDataSanitization:
    """DataClassifier.sanitize_for_external() — PII 제거 테스트."""

    def test_pii_key_redacted(self) -> None:
        payload = {"user_id": "u123", "state": {"x": 0.5}}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean["user_id"] == "[REDACTED]"
        assert clean["state"]["x"] == 0.5  # 비PII 값 보존

    def test_email_value_redacted(self) -> None:
        payload = {"contact": "admin@corp.com", "score": 0.9}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean["contact"] == "[REDACTED]"
        assert clean["score"] == 0.9

    def test_original_not_mutated(self) -> None:
        payload = {"email": "a@b.com", "val": 1}
        original_email = payload["email"]
        DataClassifier().sanitize_for_external(payload)
        assert payload["email"] == original_email  # 원본 불변

    def test_nested_pii_redacted(self) -> None:
        payload = {"meta": {"user_id": "u1", "score": 0.5}}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean["meta"]["user_id"] == "[REDACTED]"
        assert clean["meta"]["score"] == 0.5

    def test_list_of_dicts_sanitized(self) -> None:
        payload = {"items": [{"email": "x@x.com", "val": 1}, {"val": 2}]}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean["items"][0]["email"] == "[REDACTED]"
        assert clean["items"][0]["val"] == 1
        assert clean["items"][1]["val"] == 2

    def test_clean_payload_unchanged(self) -> None:
        payload = {"sdr": 0.03, "predicted": {"x": 0.1, "y": 0.2}}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean == payload

    def test_multiple_pii_fields_all_redacted(self) -> None:
        payload = {"email": "a@b.com", "phone": "010-0000-0000", "score": 0.5}
        clean = DataClassifier().sanitize_for_external(payload)
        assert clean["email"] == "[REDACTED]"
        assert clean["phone"] == "[REDACTED]"
        assert clean["score"] == 0.5


class TestCounterfactualEvaluatorConsent:
    """CounterfactualEvaluator 데이터 전송 고지 및 PII 필터링 통합 테스트."""

    def test_warns_when_anthropic_client_provided(self) -> None:
        """Anthropic 클라이언트 제공 시 데이터 전송 경고가 발생해야 한다."""
        from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

        mock_client = object()  # 실제 API 호출 없는 더미 클라이언트
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CounterfactualEvaluator(anthropic_client=mock_client)
            assert len(w) == 1
            assert "데이터 전송 고지" in str(w[0].message)
            assert issubclass(w[0].category, UserWarning)

    def test_no_warning_when_consent_acknowledged(self) -> None:
        """consent_acknowledged=True 시 경고가 발생하지 않아야 한다."""
        from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

        mock_client = object()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CounterfactualEvaluator(
                anthropic_client=mock_client,
                consent_acknowledged=True,
            )
            data_warnings = [x for x in w if "데이터 전송 고지" in str(x.message)]
            assert len(data_warnings) == 0

    def test_no_warning_when_no_client(self) -> None:
        """anthropic_client=None 시 경고가 발생하지 않아야 한다."""
        from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CounterfactualEvaluator(anthropic_client=None)
            data_warnings = [x for x in w if "데이터 전송 고지" in str(x.message)]
            assert len(data_warnings) == 0

    def test_pii_filter_enabled_by_default(self) -> None:
        """pii_filter 기본값이 True여야 한다."""
        from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

        ev = CounterfactualEvaluator(anthropic_client=None)
        assert ev._pii_filter is True
        assert ev._classifier is not None

    def test_pii_filter_disabled(self) -> None:
        """pii_filter=False 시 classifier가 None이어야 한다."""
        from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

        ev = CounterfactualEvaluator(anthropic_client=None, pii_filter=False)
        assert ev._classifier is None
