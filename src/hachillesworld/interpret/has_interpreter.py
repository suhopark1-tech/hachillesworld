"""HASInterpreter — HAS 점수를 인간이 이해할 수 있는 언어로 번역 (Sprint 6-A).

E-1: HAS 점수 해석 가이드 없음 → 등급·배포 상태·상위 몇% 제공
E-2: 구체적 액션 아이템 없음 → 지표별 즉시 실행 가능한 조치 제공
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hachillesworld.core.models import DiagnosticReport, MetricScore


# ── 데이터 클래스 ─────────────────────────────────────────────────────


@dataclass
class ActionItem:
    """지표 개선을 위한 실행 가능한 단일 액션 아이템."""

    priority: int  # 1=즉시, 2=이번 주, 3=이번 달
    metric: str
    current_value: float
    target_value: float
    action: str
    estimated_has_gain: float  # 이 액션 수행 시 예상 HAS 상승폭
    docs_link: str


@dataclass
class ComparisonContext:
    """Study-001 동일 도메인·레벨 에이전트 대비 상대 위치."""

    peer_avg_score: float
    peer_count: int
    domain: str
    level: str
    percentile_rank: float  # 상위 몇% (낮을수록 우수)


@dataclass
class HASInterpretation:
    """HAS 점수 해석 전체 결과."""

    score: float
    grade: str  # "A+" | "A" | "B" | "C" | "D"
    grade_label: str  # "우수 에이전트" 등
    percentile: float  # 상위 몇% (Study-001 데이터 기반)
    deployment_status: str  # "전면 배포 가능" | "감독 하 운용" | ...
    top_issue: str  # 가장 시급한 단일 이슈 요약
    next_actions: list[ActionItem]  # 상위 3개 액션
    estimated_improvement: float  # 상위 3개 액션 수행 시 예상 총 HAS 상승폭
    comparison: ComparisonContext


# ── Study-001 실증 데이터 기반 percentile 테이블 ──────────────────────
# (score_threshold, top_X_percent) — 점수가 threshold 이상이면 상위 X%
_STUDY_PERCENTILE: list[tuple[float, float]] = [
    (95.0, 5.0),
    (90.0, 15.0),
    (80.0, 30.0),
    (70.0, 50.0),
    (60.0, 70.0),
    (50.0, 82.0),
    (0.0, 95.0),
]

# ── 15개 지표 액션 매핑 ───────────────────────────────────────────────
# key: MetricScore.name 과 정확히 일치해야 한다
_ACTION_TEMPLATE: dict[str, dict[str, Any]] = {
    # WMQ (World Model 품질)
    "Prediction Error Rate": {
        "action": "World Model 재학습 + 예측 오차 분석으로 핵심 오류 패턴 식별",
        "target": 0.15,
        "has_gain": 3.2,
        "docs": "https://docs.hachillesworld.ai/scan/prediction",
    },
    "Calibration ECE": {
        "action": "보정 데이터셋으로 Temperature Scaling 또는 Platt Scaling 재보정",
        "target": 0.10,
        "has_gain": 2.8,
        "docs": "https://docs.hachillesworld.ai/scan/calibration",
    },
    "Simulation Drift Rate": {
        "action": "DriftCausalClassifier 실행 → 원인별 RecalibrationExecutor 적용",
        "target": 0.05,
        "has_gain": 3.5,
        "docs": "https://docs.hachillesworld.ai/ops/drift",
    },
    "OOD Detection Rate": {
        "action": "OOD 에너지 임계값 재조정 + 에너지 기반 필터 훈련 데이터 확충",
        "target": 0.70,
        "has_gain": 2.5,
        "docs": "https://docs.hachillesworld.ai/scan/ood",
    },
    "Planning Depth": {
        "action": "MultiStepPlanner 깊이 단계적 증가 (현재→목표) + 롤아웃 테스트 추가",
        "target": 5.0,
        "has_gain": 3.0,
        "docs": "https://docs.hachillesworld.ai/scan/planning",
    },
    # ALM (에이전시 수준)
    "Self-Correction Rate": {
        "action": "자기 수정 루프 활성화: ConfidenceChecker + HITL 임계값 하향 조정",
        "target": 0.10,
        "has_gain": 3.8,
        "docs": "https://docs.hachillesworld.ai/scan/scr",
    },
    "Counterfactual Accuracy": {
        "action": "반사실 학습 데이터 증강 + CounterfactualEvaluator 점수 기반 파인튜닝",
        "target": 0.73,
        "has_gain": 4.2,
        "docs": "https://docs.hachillesworld.ai/scan/counterfactual",
    },
    "Goal Consistency": {
        "action": "목표 분해 전략 개선: SubgoalDecomposer + ProgressTracker 통합",
        "target": 0.90,
        "has_gain": 4.5,
        "docs": "https://docs.hachillesworld.ai/scan/goal",
    },
    "Env Adaptation Speed": {
        "action": "환경 변화 감지 민감도 조정 + 빠른 재보정 파이프라인 구현",
        "target": 10.0,
        "has_gain": 2.0,
        "docs": "https://docs.hachillesworld.ai/scan/adaptation",
    },
    "Harness Coverage": {
        "action": "하네스 규칙 20개 이상으로 확장 + 도메인별 안전 제약 추가",
        "target": 20.0,
        "has_gain": 2.6,
        "docs": "https://docs.hachillesworld.ai/scan/harness",
    },
    # OHM (운영 건전성)
    "WM Update Latency": {
        "action": "World Model 업데이트 파이프라인 최적화: 비동기 배치 업데이트 전환",
        "target": 24.0,
        "has_gain": 2.0,
        "docs": "https://docs.hachillesworld.ai/scan/wmul",
    },
    "Incident Recovery Time": {
        "action": "IncidentTracker 분석으로 반복 패턴 식별 → 사전 예방 로직 추가",
        "target": 5.0,
        "has_gain": 2.3,
        "docs": "https://docs.hachillesworld.ai/ops/incident",
    },
    "HITL Trigger Rate": {
        "action": "HITL 트리거 임계값 조정 + 자동화 가능 케이스 목록 작성 및 자동화",
        "target": 0.05,
        "has_gain": 1.8,
        "docs": "https://docs.hachillesworld.ai/ops/hitl",
    },
    "Harness Violation Attempts": {
        "action": "위반 패턴 분석 → 상위 3개 위반 유형별 하네스 규칙 강화",
        "target": 0.0,
        "has_gain": 2.1,
        "docs": "https://docs.hachillesworld.ai/ops/harness",
    },
    "Checkpoint Recovery Rate": {
        "action": "체크포인트 저장 빈도 높이기 + 복구 테스트 자동화 추가",
        "target": 0.98,
        "has_gain": 1.2,
        "docs": "https://docs.hachillesworld.ai/ops/checkpoint",
    },
}


# ── HASInterpreter ────────────────────────────────────────────────────


class HASInterpreter:
    """HAS 점수를 인간이 이해할 수 있는 언어로 번역.

    사용법:
        interp = HASInterpreter().interpret(report)
        print(interp.grade)            # "B"
        print(interp.deployment_status) # "감독 하 운용"
        print(interp.next_actions[0].action)
    """

    def interpret(self, report: "DiagnosticReport") -> HASInterpretation:
        """DiagnosticReport → HASInterpretation."""
        score = report.composite_score
        grade, grade_label = self._grade(score)
        actions = self._action_items(report)
        top_issue = self._top_issue(actions)

        return HASInterpretation(
            score=score,
            grade=grade,
            grade_label=grade_label,
            percentile=self._percentile(score),
            deployment_status=self._deployment_status(score),
            top_issue=top_issue,
            next_actions=actions[:3],
            estimated_improvement=sum(a.estimated_has_gain for a in actions[:3]),
            comparison=self._comparison_context(report),
        )

    def _grade(self, score: float) -> tuple[str, str]:
        if score >= 90:
            return "A+", "우수 에이전트"
        if score >= 80:
            return "A", "양호 에이전트"
        if score >= 70:
            return "B", "개선 필요"
        if score >= 60:
            return "C", "주의 에이전트"
        return "D", "즉시 개선 필요"

    def _action_items(self, report: "DiagnosticReport") -> list[ActionItem]:
        """Critical → Warning 순으로 액션 아이템 생성, estimated_has_gain 내림차순."""
        items: list[ActionItem] = []
        for metric in report.critical_issues:
            items.append(self._metric_to_action(metric, priority=1))
        for category in (
            report.world_model_quality,
            report.agency_level,
            report.operational_health,
        ):
            for metric in category.warning_metrics:
                items.append(self._metric_to_action(metric, priority=2))
        return sorted(items, key=lambda x: (-x.estimated_has_gain, x.priority))

    def _metric_to_action(self, metric: "MetricScore", priority: int) -> ActionItem:
        tmpl = _ACTION_TEMPLATE.get(
            metric.name,
            {
                "action": f"{metric.name} 지표를 기준치 이하로 개선하세요.",
                "target": metric.threshold,
                "has_gain": 1.0,
                "docs": "https://docs.hachillesworld.ai/scan",
            },
        )
        target = tmpl.get("target")
        return ActionItem(
            priority=priority,
            metric=metric.name,
            current_value=metric.value,
            target_value=float(target) if target is not None else metric.threshold,
            action=str(tmpl["action"]),
            estimated_has_gain=float(tmpl["has_gain"]),
            docs_link=str(tmpl["docs"]),
        )

    def _percentile(self, score: float) -> float:
        """Study-001 분포 기반 상위 몇% 계산."""
        for threshold, pct in _STUDY_PERCENTILE:
            if score >= threshold:
                return pct
        return 95.0

    def _deployment_status(self, score: float) -> str:
        if score >= 90:
            return "전면 배포 가능"
        if score >= 75:
            return "감독 하 운용"
        if score >= 60:
            return "제한적 운용"
        return "배포 중단 권고"

    def _top_issue(self, actions: list[ActionItem]) -> str:
        """estimated_has_gain이 가장 높은 이슈를 한 줄로 요약."""
        if not actions:
            return "개선 필요 지표 없음"
        top = actions[0]
        return f"{top.metric}={top.current_value:.3g} (임계 초과) → {top.action}"

    def _comparison_context(self, report: "DiagnosticReport") -> ComparisonContext:
        """Study-001 동일 도메인·레벨 에이전트 대비 상대 위치."""
        return ComparisonContext(
            peer_avg_score=65.0,  # Study-001 전체 평균
            peer_count=47,  # Study-001 참여 에이전트 수
            domain=report.laws_domain.value,
            level=report.level.value,
            percentile_rank=self._percentile(report.composite_score),
        )
