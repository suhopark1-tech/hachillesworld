"""HAchillesWorld 핵심 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Level(StrEnum):
    """Levels × Laws 분류 체계의 역량 레벨."""

    L1 = "L1"  # Predictor: 단일 스텝 예측
    L2 = "L2"  # Simulator: 멀티스텝 롤아웃
    L3 = "L3"  # Evolver:   자율 루프·자기 수정


class LawsDomain(StrEnum):
    """에이전트가 작동하는 지배 법칙 도메인."""

    PHYSICAL = "physical"  # 로봇·자율주행·물리 세계
    DIGITAL = "digital"  # 소프트웨어·API·데이터
    SOCIAL = "social"  # 멀티에이전트·협상·규범
    SCIENTIFIC = "scientific"  # 연구·실험·가설 검증


@dataclass
class MetricScore:
    """단일 지표의 측정 결과."""

    name: str
    value: float
    threshold: float
    unit: str = ""
    status: str = "ok"  # ok | warning | critical
    description: str = ""
    # v2.1: 측정 신뢰성 필드
    confidence_lower: float | None = None  # 95% CI 하한
    confidence_upper: float | None = None  # 95% CI 상한
    measurement_error: float | None = None  # 측정 표준오차
    sample_size: int | None = None  # 산출 기반 샘플 수

    def __post_init__(self) -> None:
        pass  # status는 각 메트릭 생성자가 명시적으로 설정한다


@dataclass
class CategoryScore:
    """카테고리(World Model 품질 / 에이전시 수준 / 운영 건전성) 종합 점수."""

    name: str
    score: float  # 0~100
    metrics: list[MetricScore] = field(default_factory=list)

    @property
    def critical_metrics(self) -> list[MetricScore]:
        return [m for m in self.metrics if m.status == "critical"]

    @property
    def warning_metrics(self) -> list[MetricScore]:
        return [m for m in self.metrics if m.status == "warning"]


@dataclass
class DiagnosticReport:
    """HAchillesWorld Scan 모듈이 생성하는 진단 리포트."""

    agent_name: str
    level: Level
    level_progress: float  # 0.0~1.0: 해당 Level 내 진행도 (예: L2 = 0.3 → "L2.3")
    laws_domain: LawsDomain

    world_model_quality: CategoryScore
    agency_level: CategoryScore
    operational_health: CategoryScore

    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # v2.1: 측정 신뢰성 필드
    has_confidence_interval: tuple[float, float] | None = None  # HAS 95% CI (lower, upper)
    has_score_version: str = "2.1"  # 가중치 버전 (A-7)
    measurement_metadata: dict[str, Any] = field(default_factory=dict)
    not_measured_metrics: list[str] = field(default_factory=list)  # 측정 불가 지표 목록 (A-9)

    @property
    def composite_score(self) -> float:
        """세 카테고리의 가중 평균 종합 점수 (0~100).

        가중치는 config.HAS_WEIGHTS를 따른다.
        HAW-STUDY-001 실증 결과 후 StudyAnalyzer.sdk_weight_update()로 갱신된다.
        """
        from hachillesworld.core.config import HAS_WEIGHTS

        return (
            self.world_model_quality.score * HAS_WEIGHTS["wmq"]
            + self.agency_level.score * HAS_WEIGHTS["alm"]
            + self.operational_health.score * HAS_WEIGHTS["ohm"]
        )

    def composite_score_at_version(self, version: str) -> float:
        """특정 가중치 버전으로 HAS 재산출 — 시계열 비교가능성 보장."""
        from hachillesworld.core.config import get_weights_for_version

        weights = get_weights_for_version(version)
        return (
            self.world_model_quality.score * weights["wmq"]
            + self.agency_level.score * weights["alm"]
            + self.operational_health.score * weights["ohm"]
        )

    @property
    def level_label(self) -> str:
        """예: 'L2.3' (Level + 소수점 진행도)."""
        progress_digit = round(self.level_progress * 9)
        return f"{self.level.value}.{progress_digit}"

    @property
    def critical_issues(self) -> list[MetricScore]:
        all_metrics = (
            self.world_model_quality.metrics
            + self.agency_level.metrics
            + self.operational_health.metrics
        )
        return [m for m in all_metrics if m.status == "critical"]

    def summary(self) -> str:
        """CLI·로그에 바로 출력할 수 있는 한 줄 요약 (HASInterpreter 기반)."""
        from hachillesworld.interpret.has_interpreter import HASInterpreter

        interp = HASInterpreter().interpret(self)
        emoji = "🟢" if interp.grade in ("A+", "A") else "🟡" if interp.grade == "B" else "🔴"
        return (
            f"{emoji} [{self.agent_name}] {self.level_label}"
            f" × {self.laws_domain.value.title()} Laws\n"
            f"   종합 점수: {self.composite_score:.0f}/100"
            f" ({interp.grade}등급 — {interp.grade_label},"
            f" 상위 {interp.percentile:.0f}%) | {interp.deployment_status}\n"
            f"   즉시 조치: {interp.top_issue}"
        )


@dataclass
class OptimizationRoadmap:
    """HAchillesWorld Optimize 모듈이 생성하는 최적화 로드맵."""

    from_level: str
    to_level: str
    laws_domain: LawsDomain
    phases: list[RoadmapPhase] = field(default_factory=list)
    estimated_cost_saving_usd: float = 0.0
    estimated_duration_weeks: int = 0


@dataclass
class RoadmapPhase:
    """로드맵의 단계별 실행 계획."""

    phase_number: int
    name: str
    duration_weeks: int
    tasks: list[str] = field(default_factory=list)
    expected_score_delta: float = 0.0
    priority_tasks: list[str] = field(default_factory=list)


@dataclass
class AgentEvent:
    """에이전트가 생성하는 이벤트 (Operate 모듈 수집 대상)."""

    agent_name: str
    event_type: str  # plan | execute | observe | reflect | recalibrate | error
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    span_id: str = ""
