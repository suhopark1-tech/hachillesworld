"""OOD Detection Rate 자동 측정 모듈.

HAW-TR-001 WMQ-4 (OOD Detection Rate) 자동화 구현.
직접 측정 모드(agent_fn + 섭동 테스트셋)와
로그 기반 프록시 모드를 모두 지원한다.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class OODResult:
    """ODR 측정 결과."""

    odr: float
    method: str  # "direct" | "proxy" | "log_based"
    n_ood_tested: int
    confidence: float  # 측정 신뢰도 [0, 1]


class OODDetector:
    """OOD Detection Rate 자동 측정기.

    두 가지 측정 모드:
    1. proxy  : 로그의 uncertainty/confidence 데이터 기반 (항상 사용 가능)
    2. direct : agent_fn + 섭동 생성 OOD 테스트셋으로 직접 측정

    측정 우선순위 (compute 메서드 기준):
      agent_fn 있으면 → direct, 없으면 → proxy
    """

    def __init__(self, confidence_threshold: float = 0.5) -> None:
        self.confidence_threshold = confidence_threshold

    # ── 공개 API ────────────────────────────────────────────────

    def generate_ood_test_set(
        self,
        in_dist_logs: list[dict[str, Any]],
        perturbation_ratio: float = 0.2,
    ) -> list[dict[str, Any]]:
        """정상 분포 로그에서 섭동을 가한 OOD 테스트셋을 생성한다.

        plan/observe 이벤트 페이로드를 추출하여 3가지 섭동 방식을 순환 적용한다:
          extreme    : 수치 필드를 10배 증폭 (분포 범위 초과)
          noise      : ±3σ 가우시안 노이즈 추가
          null_inject: 무작위 필드에 None 삽입 (결측값 OOD)
        """
        payloads = [
            e.get("payload", {})
            for e in in_dist_logs
            if e.get("event_type") in ("plan", "observe") and e.get("payload")
        ]
        if not payloads:
            return []

        n_ood = max(1, int(len(payloads) * perturbation_ratio))
        sample = payloads[:n_ood]
        fns = [self._perturb_extreme, self._perturb_noise, self._perturb_null_inject]
        return [fns[i % len(fns)](p) for i, p in enumerate(sample)]

    def measure_odr(
        self,
        agent_fn: Callable[[dict[str, Any]], float],
        ood_states: list[dict[str, Any]],
    ) -> OODResult:
        """OOD 상태 목록에 대해 에이전트를 직접 실행하여 ODR을 측정한다.

        agent_fn(state) → confidence [0, 1].
        confidence < threshold 이면 TP (OOD 감지 성공).
        """
        if not ood_states:
            return OODResult(odr=0.5, method="direct", n_ood_tested=0, confidence=0.0)

        tp = sum(1 for state in ood_states if agent_fn(state) < self.confidence_threshold)
        return OODResult(
            odr=round(tp / len(ood_states), 4),
            method="direct",
            n_ood_tested=len(ood_states),
            confidence=0.85,
        )

    def proxy_odr(
        self,
        logs: list[dict[str, Any]],
        confidence_threshold: float | None = None,
    ) -> OODResult:
        """에피소드 로그 기반 프록시 ODR 계산.

        우선순위:
        1. observe 이벤트의 ood_flagged + confidence → 직접 계산 (log_based)
        2. observe 이벤트의 error_within_uncertainty → 불확실성 커버리지 프록시
        3. plan 이벤트 confidence → 저신뢰도 비율 프록시
        4. 데이터 없음 → 0.5 반환
        """
        threshold = (
            confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        )

        # Strategy 1: ood_flagged observe 이벤트 + confidence
        ood_events = [
            e
            for e in logs
            if e.get("event_type") == "observe" and e.get("payload", {}).get("ood_flagged", False)
        ]
        if ood_events:
            tp = sum(
                1 for e in ood_events if e.get("payload", {}).get("confidence", 1.0) < threshold
            )
            return OODResult(
                odr=round(tp / len(ood_events), 4),
                method="log_based",
                n_ood_tested=len(ood_events),
                confidence=0.85,
            )

        # Strategy 2: error_within_uncertainty 기반 프록시
        observe_events = [e for e in logs if e.get("event_type") == "observe"]
        if observe_events:
            covered = sum(
                1
                for e in observe_events
                if e.get("payload", {}).get("error_within_uncertainty", False)
            )
            return OODResult(
                odr=round(covered / len(observe_events), 4),
                method="proxy",
                n_ood_tested=len(observe_events),
                confidence=0.60,
            )

        # Strategy 3: plan confidence 기반 프록시
        plan_events = [
            e
            for e in logs
            if e.get("event_type") == "plan" and "confidence" in e.get("payload", {})
        ]
        if plan_events:
            uncertain = sum(
                1 for e in plan_events if e.get("payload", {}).get("confidence", 1.0) < threshold
            )
            return OODResult(
                odr=round(uncertain / len(plan_events), 4),
                method="proxy",
                n_ood_tested=len(plan_events),
                confidence=0.40,
            )

        return OODResult(odr=0.5, method="proxy", n_ood_tested=0, confidence=0.0)

    def compute(
        self,
        logs: list[dict[str, Any]],
        agent_fn: Callable[[dict[str, Any]], float] | None = None,
    ) -> OODResult:
        """가능한 최선의 ODR 계산 방법을 선택한다.

        agent_fn 있으면 섭동 테스트셋 생성 후 직접 측정,
        없으면 proxy_odr 사용.
        """
        if agent_fn is not None:
            ood_states = self.generate_ood_test_set(logs)
            if ood_states:
                return self.measure_odr(agent_fn, ood_states)
        return self.proxy_odr(logs)

    # ── 섭동 방법 ────────────────────────────────────────────────

    @staticmethod
    def _perturb_extreme(payload: dict[str, Any]) -> dict[str, Any]:
        """수치 필드를 10배 증폭하여 분포 범위 초과 OOD를 생성한다."""
        perturbed = dict(payload)
        for key, value in payload.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                perturbed[key] = float(value) * 10.0
        return perturbed

    @staticmethod
    def _perturb_noise(payload: dict[str, Any]) -> dict[str, Any]:
        """수치 필드에 ±3σ 가우시안 노이즈를 추가한다."""
        perturbed = dict(payload)
        for key, value in payload.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sigma = abs(float(value)) * 3.0 + 0.1
                perturbed[key] = float(value) + random.gauss(0, sigma)
        return perturbed

    @staticmethod
    def _perturb_null_inject(payload: dict[str, Any]) -> dict[str, Any]:
        """무작위 키 하나에 None을 삽입하여 결측값 OOD를 생성한다."""
        perturbed = dict(payload)
        candidates = [k for k, v in payload.items() if not isinstance(v, bool)]
        if candidates:
            perturbed[random.choice(candidates)] = None
        return perturbed
