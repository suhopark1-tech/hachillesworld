"""
예제: SDK 통합 — @instrument 데코레이터 사용법

에이전트 클래스에 @instrument를 붙이면
모든 plan / execute / observe / reflect 호출이
자동으로 HAchillesWorld에 기록된다.

실행:
    python examples/sdk_integration.py
"""

import random
import time
from hachillesworld import HAchillesWorldClient, instrument
from hachillesworld.operate.monitor import DriftMonitor


# ── 에이전트 클래스 정의 ──────────────────────────────────────

client  = HAchillesWorldClient(api_key="haw-demo")
monitor = DriftMonitor("demo-agent", threshold=0.15)

# 드리프트 경보 핸들러 등록
monitor.on_alert = lambda alert: print(
    f"\n  ⚡ [Drift Alert] {alert.recommended_action}"
)


@instrument(client, agent_name="demo-agent")
class DemoAgent:
    """HAchillesWorld SDK가 계측하는 데모 에이전트."""

    def __init__(self):
        self.step_count = 0

    def plan(self, state: dict, goal: str) -> str:
        """계획 단계: World Model로 최적 행동 선택."""
        self.step_count += 1
        # 시뮬레이션: 불규칙한 행동 선택
        return random.choice(["action_a", "action_b", "action_c"])

    def execute(self, action: str) -> dict:
        """실행 단계: 실제 환경에서 행동 실행."""
        time.sleep(0.01)
        return {"result": f"{action}_done", "reward": random.uniform(-0.1, 1.0)}

    def observe(self, result: dict) -> dict:
        """관측 단계: 실행 결과로 상태 업데이트."""
        predicted = {"value": random.uniform(0, 10)}
        actual    = {"value": random.uniform(0, 10)}

        # DriftMonitor에 예측-현실 괴리 기록
        drift = monitor.record(predicted, actual)
        return {"state": "updated", "drift": round(drift, 4)}

    def reflect(self, observation: dict) -> None:
        """반성 단계: World Model 업데이트 여부 결정."""
        if observation.get("drift", 0) > 0.15:
            print(f"  ↺ 재보정 (step {self.step_count}, drift={observation['drift']})")


# ── 에이전트 실행 ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  HAchillesWorld SDK 통합 데모")
    print("=" * 60)

    agent = DemoAgent()
    state = {"inventory": 100, "demand": 90}
    goal  = "재고 최적화"

    print(f"\n  에이전트 실행 시작 (20 스텝)")
    print(f"  목표: {goal}\n")

    for step in range(20):
        action      = agent.plan(state, goal)
        result      = agent.execute(action)
        observation = agent.observe(result)
        agent.reflect(observation)

        if step % 5 == 4:
            print(f"  Step {step+1:2d}: drift={observation['drift']:.4f} | "
                  f"stable={monitor.is_stable()}")

    # 버퍼 플러시 (이벤트 전송)
    flushed = client.flush()
    print(f"\n  이벤트 전송: {flushed}건")

    # 드리프트 모니터 요약
    summary = monitor.summary()
    print(f"\n  Drift Monitor 요약:")
    print(f"    총 기록:          {summary['total_records']}건")
    print(f"    경보 횟수:        {summary['alert_count']}건")
    print(f"    최근 드리프트율:  {summary['recent_drift_rate']:.2%}")
    print(f"    안정 상태:        {'✅' if summary['is_stable'] else '⚠️'}")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
