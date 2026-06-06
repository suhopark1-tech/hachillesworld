"""외부 API 전송 전 데이터 분류 및 PII 필터링.

CA(Counterfactual Accuracy) 측정 시 에이전트 로그가 Anthropic API로 전송될 수 있다.
이 모듈은 전송 전 개인식별정보(PII) 필드를 탐지하고 제거하여
GDPR Article 5(1)(c) 데이터 최소화 원칙을 준수한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# 개인식별정보(PII)로 간주되는 키 패턴
# (?<![a-zA-Z0-9]) / (?![a-zA-Z0-9]): 앞뒤에 알파숫자가 없을 때 매칭 (복합 키 포함)
_PII_KEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?<![a-zA-Z0-9])(user_?id|userid)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(email|e_?mail)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(phone|mobile|tel)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(fullname|first_?name|last_?name)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(address|addr)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(ip_?address|remote_?addr)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(ssn|rrn|주민|주민등록)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(password|passwd|pwd|secret)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(api_?token|auth_?token|access_?token|token)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(api_?key|secret_?key|private_?key)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(birth|birthday|dob|date_?of_?birth)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(gender|sex)(?![a-zA-Z0-9])", re.I),
    re.compile(r"(?<![a-zA-Z0-9])(location|gps|latitude|longitude)(?![a-zA-Z0-9])", re.I),
]

# 값 기반 PII 패턴 (값 자체가 PII인 경우)
_PII_VALUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),  # 이메일
    re.compile(r"\b\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b"),                      # 전화번호
    re.compile(r"\b\d{6}[-]\d{7}\b"),                                          # 주민등록번호
]

_REDACTED = "[REDACTED]"


@dataclass
class DataClassification:
    """데이터 분류 결과."""

    contains_pii: bool
    pii_keys: list[str] = field(default_factory=list)
    pii_value_keys: list[str] = field(default_factory=list)
    safe_to_transmit: bool = True

    @property
    def risk_level(self) -> str:
        if self.pii_keys or self.pii_value_keys:
            return "high"
        return "low"


class DataClassifier:
    """외부 API 전송 전 PII 탐지 및 제거.

    사용 예:
        classifier = DataClassifier()
        clean = classifier.sanitize_for_external(payload)
        result = anthropic_client.messages.create(..., content=str(clean))
    """

    def classify(self, payload: dict[str, Any]) -> DataClassification:
        """payload에서 PII 필드를 탐지하여 분류 결과를 반환한다."""
        pii_keys: list[str] = []
        pii_value_keys: list[str] = []

        for key, value in self._flatten(payload).items():
            # 키 기반 탐지
            if any(p.search(key) for p in _PII_KEY_PATTERNS):
                pii_keys.append(key)
                continue
            # 값 기반 탐지 (문자열 값에 한함)
            if isinstance(value, str) and any(
                p.search(value) for p in _PII_VALUE_PATTERNS
            ):
                pii_value_keys.append(key)

        contains = bool(pii_keys or pii_value_keys)
        return DataClassification(
            contains_pii=contains,
            pii_keys=pii_keys,
            pii_value_keys=pii_value_keys,
            safe_to_transmit=not contains,
        )

    def sanitize_for_external(self, payload: dict[str, Any]) -> dict[str, Any]:
        """외부 API 전송용으로 PII 필드를 제거한 복사본을 반환한다.

        원본 payload는 변경되지 않는다.
        """
        result = {}
        for key, value in payload.items():
            if any(p.search(key) for p in _PII_KEY_PATTERNS):
                result[key] = _REDACTED
            elif isinstance(value, str) and any(
                p.search(value) for p in _PII_VALUE_PATTERNS
            ):
                result[key] = _REDACTED
            elif isinstance(value, dict):
                result[key] = self.sanitize_for_external(value)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize_for_external(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def _flatten(
        self, d: dict[str, Any], prefix: str = ""
    ) -> dict[str, Any]:
        """중첩 dict를 평탄화하여 탐지 정확도를 높인다."""
        items: dict[str, Any] = {}
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(self._flatten(v, full_key))
            else:
                items[full_key] = v
        return items
