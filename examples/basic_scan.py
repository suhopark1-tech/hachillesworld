"""예제: 기본 Scan 사용법

에이전트 로그를 진단해 리포트를 출력하고,
최적화 로드맵을 자동 생성한다.

실행:
    cd HAchillesWorld
    pip install -e .
    python examples/basic_scan.py
"""

from hachillesworld import HAchillesWorldClient
from hachillesworld.optimize.harness_generator import HarnessGenerator
from hachillesworld.optimize.roadmap import RoadmapGenerator


def make_sample_logs(level: str = "L2") -> list[dict]:
    """진단 데모용 샘플 로그 생성."""
    base_depth = {"L1": 1, "L2": 12, "L3": 35}.get(level, 12)
    base_error = {"L1": 0.25, "L2": 0.09, "L3": 0.04}.get(level, 0.09)
    recalib = {"L1": True, "L2": False, "L3": False}.get(level, False)

    logs = []
    for i in range(20):
        logs += [
            {
                "event_type": "plan",
                "payload": {
                    "planning_depth": base_depth + (i % 5),
                    "confidence": 0.78,
                    "uncertainty": 0.10 + (i % 3) * 0.03,
                },
            },
            {"event_type": "execute", "payload": {"action": f"action_{i}"}},
            {
                "event_type": "observe",
                "payload": {
                    "prediction_error": base_error + (i % 4) * 0.01,
                    "error_within_uncertainty": base_error < 0.15,
                    "goal_achieved": i % 5 == 4,
                },
            },
            {
                "event_type": "reflect",
                "payload": {
                    "recalibrated": recalib and i % 7 == 0,
                    "correction_applied": level == "L3" and i % 8 == 0,
                },
            },
        ]
    return logs


def main():
    print("\n" + "=" * 60)
    print("  HAchillesWorld - 진단 데모")
    print("=" * 60)

    # 에이전트 설정
    agent_config = {
        "laws_domain": "digital",
        "harness_rules": [f"rule_{i}" for i in range(15)],
        "monthly_budget_usd": 800.0,
    }

    # ── 1. Scan: 진단 ─────────────────────────────────────────
    print("\n[1/3] 진단 실행 중...")
    client = HAchillesWorldClient()
    logs = make_sample_logs(level="L2")
    report = client.scan(logs=logs, config=agent_config, agent_name="demo-agent")

    print(report.summary())
    print(f"\n  레벨 진행도: {report.level_label}")
    print(f"  도메인:      {report.laws_domain.value.title()} Laws")

    if report.critical_issues:
        print("\n  🔴 즉시 조치 필요:")
        for issue in report.critical_issues:
            print(f"    - {issue.name}: {issue.description}")

    # ── 2. Optimize: 로드맵 생성 ──────────────────────────────
    print("\n[2/3] 최적화 로드맵 생성 중...")
    roadmap = RoadmapGenerator().generate(report, target_level="L3")
    RoadmapGenerator().print_roadmap(roadmap)

    # ── 3. Optimize: 하네스 자동 생성 ─────────────────────────
    print("[3/3] 하네스 규칙 자동 생성 중...")
    spec = HarnessGenerator().generate(report)
    print(f"\n  생성된 규칙: {len(spec.rules)}개")
    print(f"  금지 행동:   {len(spec.forbidden_actions)}개")
    print(f"  예산 상한:   {spec.budget_caps}")
    print("\n  --- 생성된 Python 하네스 코드 (일부) ---")
    code_lines = spec.to_python().split("\n")[:10]
    for line in code_lines:
        print(f"  {line}")
    print("  ...")

    print("\n" + "=" * 60)
    print("  데모 완료! 실제 에이전트 로그로 진단을 실행해보세요.")
    print("  hachillesworld scan --logs ./logs.json --config ./config.json")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
