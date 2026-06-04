"""EpisodeRecord — HAW-STUDY-001 스키마 호환 에피소드 로그 단위."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EpisodeRecord:
    """
    에이전트 에피소드 1회 실행의 완전한 로그 단위.

    HAW-STUDY-001 JSON 스키마와 1:1 대응한다.
    SCR 계산(조건 1·2·3)과 PD 측정(예측-관측 쌍)에 필요한
    모든 필드를 포함한다.
    """

    # ── 식별자 ──────────────────────────────────────────────────
    agent_id: str
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    study_id: str | None = None          # HAW-STUDY-001 참여 시 설정
    domain: str = ""                     # supply_chain | customer_service | ...

    # ── SCR 조건 1: 내부 플래그 ─────────────────────────────────
    confidence: float | None = None      # 행동 확신도 [0, 1]
    internal_flag_raised: bool = False
    flag_types: list[str] = field(default_factory=list)
    # 가능한 값: "confidence" | "prediction" | "counterfactual"

    # ── SCR 조건 2: 수정 출처 ────────────────────────────────────
    agent_self_flagged: bool = False
    human_intervened: bool = False
    human_approval_required: bool = False
    harness_reject_triggered: bool = False
    correction_source: str | None = None
    # 가능한 값: "self" | "harness" | "hitl" | "unknown" | None

    # ── SCR 조건 3: 개선 검증 ────────────────────────────────────
    original_action: str | None = None
    corrected_action: str | None = None
    error_before_correction: float | None = None
    error_after_correction: float | None = None

    # ── PD 측정: 예측-관측 쌍 ────────────────────────────────────
    predicted_next_state: dict[str, Any] | None = None
    actual_next_state: dict[str, Any] | None = None
    max_prediction_error: float | None = None   # 정규화 거리 [0, 1]
    planning_depth_used: int | None = None      # 이 에피소드에서 사용한 계획 깊이

    # ── 에피소드 결과 ─────────────────────────────────────────────
    goal_achieved: bool = True
    episode_success: bool = True
    infrastructure_failure: bool = False
    ood_flagged: bool = False           # Out-of-Distribution 입력 여부

    # ── 운영 건전성 ───────────────────────────────────────────────
    hitl_required: bool = False
    llm_tokens: int = 0
    harness_triggers: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    duration_ms: float | None = None

    # ── 확장 필드 ─────────────────────────────────────────────────
    confidence_history: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── 직렬화 ────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "episode_id": self.episode_id,
            "timestamp": self.timestamp,
            "study_id": self.study_id,
            "domain": self.domain,
            "confidence": self.confidence,
            "internal_flag_raised": self.internal_flag_raised,
            "flag_types": self.flag_types,
            "agent_self_flagged": self.agent_self_flagged,
            "human_intervened": self.human_intervened,
            "human_approval_required": self.human_approval_required,
            "harness_reject_triggered": self.harness_reject_triggered,
            "correction_source": self.correction_source,
            "original_action": self.original_action,
            "corrected_action": self.corrected_action,
            "error_before_correction": self.error_before_correction,
            "error_after_correction": self.error_after_correction,
            "predicted_next_state": self.predicted_next_state,
            "actual_next_state": self.actual_next_state,
            "max_prediction_error": self.max_prediction_error,
            "planning_depth_used": self.planning_depth_used,
            "goal_achieved": self.goal_achieved,
            "episode_success": self.episode_success,
            "infrastructure_failure": self.infrastructure_failure,
            "ood_flagged": self.ood_flagged,
            "hitl_required": self.hitl_required,
            "llm_tokens": self.llm_tokens,
            "harness_triggers": self.harness_triggers,
            "tools_used": self.tools_used,
            "duration_ms": self.duration_ms,
            "confidence_history": self.confidence_history,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EpisodeRecord":
        return cls(
            agent_id=d["agent_id"],
            episode_id=d.get("episode_id", str(uuid.uuid4())),
            timestamp=d.get("timestamp", datetime.now(timezone.utc).isoformat()),
            study_id=d.get("study_id"),
            domain=d.get("domain", ""),
            confidence=d.get("confidence"),
            internal_flag_raised=d.get("internal_flag_raised", False),
            flag_types=d.get("flag_types", []),
            agent_self_flagged=d.get("agent_self_flagged", False),
            human_intervened=d.get("human_intervened", False),
            human_approval_required=d.get("human_approval_required", False),
            harness_reject_triggered=d.get("harness_reject_triggered", False),
            correction_source=d.get("correction_source"),
            original_action=d.get("original_action"),
            corrected_action=d.get("corrected_action"),
            error_before_correction=d.get("error_before_correction"),
            error_after_correction=d.get("error_after_correction"),
            predicted_next_state=d.get("predicted_next_state"),
            actual_next_state=d.get("actual_next_state"),
            max_prediction_error=d.get("max_prediction_error"),
            planning_depth_used=d.get("planning_depth_used"),
            goal_achieved=d.get("goal_achieved", True),
            episode_success=d.get("episode_success", True),
            infrastructure_failure=d.get("infrastructure_failure", False),
            ood_flagged=d.get("ood_flagged", False),
            hitl_required=d.get("hitl_required", False),
            llm_tokens=d.get("llm_tokens", 0),
            harness_triggers=d.get("harness_triggers", []),
            tools_used=d.get("tools_used", []),
            duration_ms=d.get("duration_ms"),
            confidence_history=d.get("confidence_history", []),
            metadata=d.get("metadata", {}),
        )

    def has_detectable_error(self, theta_drift: float = 0.15) -> bool:
        """SCR 분모 판단: 감지 가능한 오류가 있는 에피소드인가."""
        if (self.max_prediction_error or 0.0) > theta_drift:
            return True
        if not self.goal_achieved:
            return True
        if self.internal_flag_raised:
            return True
        return False

    def is_self_correction(self, min_improvement: float = 0.05) -> bool:
        """SCR 분자 판단: 조건 1+2+3을 모두 충족하는 자기 수정 에피소드인가."""
        if not self.internal_flag_raised:
            return False
        if self.correction_source != "self":
            return False
        if self.error_before_correction is None or self.error_after_correction is None:
            return False
        if self.error_before_correction <= 0:
            return False
        improvement = (
            (self.error_before_correction - self.error_after_correction)
            / self.error_before_correction
        )
        return improvement >= min_improvement
