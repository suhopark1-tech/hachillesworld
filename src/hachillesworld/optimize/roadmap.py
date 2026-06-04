"""최적화 로드맵 자동 생성."""

from __future__ import annotations

from hachillesworld.core.models import (
    DiagnosticReport,
    Level,
    OptimizationRoadmap,
    RoadmapPhase,
)


class RoadmapGenerator:
    """
    진단 리포트를 입력받아 단계별 최적화 로드맵을 생성한다.

    사용 예:
        report = client.scan(logs=logs, config=config)
        roadmap = RoadmapGenerator().generate(report, target_level="L3")
    """

    # 각 Level 전환별 표준 태스크 템플릿
    _PHASE_TEMPLATES: dict[str, list[dict]] = {
        "L1→L2": [
            {
                "phase": 1,
                "name": "즉각적 안정화",
                "weeks": 4,
                "tasks": [
                    "재보정 임계값 검토 및 최적화",
                    "ECE 측정 파이프라인 구축",
                    "앙상블 불확실성 표현 추가",
                    "비용 라우팅 재조정 (CostAwareRouter)",
                ],
                "priority": ["재보정 임계값 검토 및 최적화"],
                "score_delta": 12.0,
            },
            {
                "phase": 2,
                "name": "L2 핵심 역량 구축",
                "weeks": 8,
                "tasks": [
                    "앙상블 역학 모델 구현 (EnsembleDynamics)",
                    "MCTS 계획기 구현 (계획 깊이 5→20스텝)",
                    "Simulation Drift 감지 + 자동 재보정 루프",
                    "하네스 규칙 5→20개 확장",
                    "HITL 트리거 기준 문서화",
                ],
                "priority": ["앙상블 역학 모델 구현", "MCTS 계획기 구현"],
                "score_delta": 18.0,
            },
            {
                "phase": 3,
                "name": "L2 심화 및 운영 안정화",
                "weeks": 8,
                "tasks": [
                    "Replay Debugging 파이프라인 구축",
                    "OpenTelemetry 전체 계측",
                    "Circuit Breaker + 헬스체크 구현",
                    "Chaos Engineering 테스트",
                    "비용 목표 달성 검증",
                ],
                "priority": ["Replay Debugging 파이프라인 구축"],
                "score_delta": 10.0,
            },
        ],
        "L2→L3": [
            {
                "phase": 1,
                "name": "L3 기반 준비",
                "weeks": 6,
                "tasks": [
                    "Self-Correction Engine 프로토타입 구현",
                    "EWC(Elastic Weight Consolidation) 적용",
                    "DEOR 자율 루프 설계",
                    "Meta-Harness 초안 작성",
                ],
                "priority": ["Self-Correction Engine 프로토타입"],
                "score_delta": 8.0,
            },
            {
                "phase": 2,
                "name": "자율 루프 구현",
                "weeks": 10,
                "tasks": [
                    "온라인 학습 루프 구현",
                    "World Model 자동 업데이트 파이프라인",
                    "Meta-Harness 규칙 자동 생성 연결",
                    "자율 목표 재설정 로직 구현",
                    "안전 경계(Safety Boundary) 정의 및 검증",
                ],
                "priority": ["온라인 학습 루프 구현", "안전 경계 정의 및 검증"],
                "score_delta": 15.0,
            },
            {
                "phase": 3,
                "name": "L3 검증 및 안전 보강",
                "weeks": 8,
                "tasks": [
                    "L3 에이전트 Red-teaming",
                    "Reward Hacking 방어 검증",
                    "장기 실행 안정성 테스트 (1,000+ 스텝)",
                    "거버넌스 체크리스트 완료",
                ],
                "priority": ["L3 에이전트 Red-teaming"],
                "score_delta": 7.0,
            },
        ],
    }

    def generate(
        self,
        report: DiagnosticReport,
        target_level: str | None = None,
    ) -> OptimizationRoadmap:
        """
        진단 리포트 기반 최적화 로드맵 생성.

        Args:
            report: Scan 결과 리포트
            target_level: 목표 Level ("L2" 또는 "L3"). None이면 자동 결정.
        """
        current = report.level.value
        target = target_level or self._auto_target(report.level)
        key = f"{current}→{target}"

        templates = self._PHASE_TEMPLATES.get(key, self._default_phases(report))
        phases = [
            RoadmapPhase(
                phase_number=t["phase"],
                name=t["name"],
                duration_weeks=t["weeks"],
                tasks=t["tasks"],
                expected_score_delta=t["score_delta"],
                priority_tasks=t.get("priority", []),
            )
            for t in templates
        ]

        total_weeks = sum(p.duration_weeks for p in phases)
        cost_saving = self._estimate_cost_saving(report)

        return OptimizationRoadmap(
            from_level=report.level_label,
            to_level=target,
            laws_domain=report.laws_domain,
            phases=phases,
            estimated_cost_saving_usd=cost_saving,
            estimated_duration_weeks=total_weeks,
        )

    def print_roadmap(self, roadmap: OptimizationRoadmap) -> None:
        """터미널에 로드맵을 출력한다."""
        print(f"\n{'━' * 60}")
        print("  HAchillesWorld Optimize — 로드맵")
        print(
            f"  {roadmap.from_level} → {roadmap.to_level}  ({roadmap.laws_domain.value.title()} Laws)"
        )
        print(f"  총 기간: {roadmap.estimated_duration_weeks}주")
        if roadmap.estimated_cost_saving_usd > 0:
            print(f"  예상 비용 절감: ${roadmap.estimated_cost_saving_usd:,.0f}/년")
        print(f"{'━' * 60}")

        for phase in roadmap.phases:
            print(f"\n  Phase {phase.phase_number}: {phase.name} ({phase.duration_weeks}주)")
            print(f"  예상 점수 향상: +{phase.expected_score_delta:.0f}점")
            for task in phase.tasks:
                marker = "★" if task in phase.priority_tasks else "•"
                print(f"    {marker} {task}")

        print(f"\n{'━' * 60}\n")

    @staticmethod
    def _auto_target(current: Level) -> str:
        return {Level.L1: "L2", Level.L2: "L3", Level.L3: "L3"}.get(current, "L2")

    @staticmethod
    def _estimate_cost_saving(report: DiagnosticReport) -> float:
        cost_metric = next(
            (m for m in report.operational_health.metrics if m.name == "Cost Efficiency"),
            None,
        )
        if cost_metric and cost_metric.value > 1.0:
            excess_ratio = cost_metric.value - 1.0
            return excess_ratio * 12_000  # 연간 초과분 추정
        return 0.0

    @staticmethod
    def _default_phases(report: DiagnosticReport) -> list[dict]:
        return [
            {
                "phase": 1,
                "name": "현황 최적화",
                "weeks": 6,
                "tasks": [f"개선: {r}" for r in report.recommendations[:5]],
                "priority": [],
                "score_delta": 10.0,
            }
        ]
