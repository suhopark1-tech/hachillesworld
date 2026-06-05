"""Planning Depth 행동 프로빙 측정 모듈.

HAW-PAT-001 핵심 구현:
  에이전트 내부 구조에 접근하지 않고 외부 행동 관찰만으로
  Planning Depth를 정량 산출한다.
"""

from __future__ import annotations

import abc
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

State = Any
Action = Any


# ─────────────────────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────────────────────


@dataclass
class PlanningDepthResult:
    """Planning Depth 측정 결과."""

    depth: int
    level: str  # "L1" | "L2" | "L3"
    confidence: float  # [0, 1]: 측정 신뢰도
    series: list[float]  # H별 (agent_value - random_value - delta) 마진


@dataclass
class DegradationAlert:
    """Planning Depth 저하 경보."""

    agent_name: str
    timestamp: float
    current_depth: int
    baseline_depth: float
    drop_ratio: float


@dataclass
class PlanningDepthSnapshot:
    """단일 시점의 PD 기록."""

    timestamp: float
    depth: int
    level: str


# ─────────────────────────────────────────────────────────────
# 환경 인터페이스
# ─────────────────────────────────────────────────────────────


class ProbingEnvironment(abc.ABC):
    """PlanningDepthProber가 사용하는 환경 추상 인터페이스."""

    @abc.abstractmethod
    def reset(self) -> State:
        """초기 상태를 반환한다."""

    @abc.abstractmethod
    def step(self, action: Action) -> tuple[State, float, bool]:
        """행동을 실행하고 (다음 상태, 보상, 종료 여부)를 반환한다."""

    @abc.abstractmethod
    def sample_random_action(self) -> Action:
        """균일 무작위 행동을 반환한다."""


class SupplyChainProbingEnvironment(ProbingEnvironment):
    """공급망 도메인 표준 프로빙 환경.

    재고 관리 시뮬레이터로 Planning Depth 측정에 사용된다.
    수요가 2-스텝 주기 패턴을 따르므로 H≥2 계획 시 개선 가능.
    """

    ACTIONS: list[int] = [0, 5, 10, 20]
    _DEMAND_CYCLE: list[int] = [8, 4, 8, 4, 8, 4, 8, 4, 8, 4]

    def __init__(self, max_steps: int = 30) -> None:
        self._max_steps = max_steps
        self._inventory = 15
        self._step = 0

    def reset(self) -> dict[str, Any]:
        self._inventory = 15
        self._step = 0
        return self._observe()

    def step(self, action: int) -> tuple[dict[str, Any], float, bool]:
        self._inventory += action
        demand = self._DEMAND_CYCLE[self._step % len(self._DEMAND_CYCLE)]
        shortfall = max(0, demand - self._inventory)
        excess = max(0, self._inventory - demand)
        self._inventory = max(0, self._inventory - demand)
        self._step += 1

        reward = 1.0 - shortfall * 0.5 - excess * 0.05
        done = self._step >= self._max_steps
        return self._observe(), reward, done

    def sample_random_action(self) -> int:
        return random.choice(self.ACTIONS)

    def _observe(self) -> dict[str, Any]:
        return {
            "inventory": self._inventory,
            "next_demand": self._DEMAND_CYCLE[self._step % len(self._DEMAND_CYCLE)],
            "step": self._step,
        }


# ─────────────────────────────────────────────────────────────
# 레거시 env_fn 어댑터 (agency_level.py 하위 호환)
# ─────────────────────────────────────────────────────────────


class _LegacyEnvAdapter(ProbingEnvironment):
    """기존 `env_fn(state, action)` 방식을 ProbingEnvironment로 변환한다."""

    def __init__(self, env_fn: Callable) -> None:
        self._env_fn = env_fn
        self._state: State = None

    def reset(self) -> State:
        self._state = self._env_fn("reset", None)[0]
        return self._state

    def step(self, action: Action) -> tuple[State, float, bool]:
        result = self._env_fn(self._state, action)
        self._state = result[0]
        return result

    def sample_random_action(self) -> Action:
        return self._env_fn("sample_action", self._state)


# ─────────────────────────────────────────────────────────────
# 핵심 프로버
# ─────────────────────────────────────────────────────────────


class PlanningDepthProber:
    """에이전트 구조에 무관한 외부 행동 프로빙 기반 PD 측정기.

    HAW-PAT-001 핵심 구현.

    알고리즘:
      H = 1 ~ max_depth를 순차 증가시키며,
      agent_value(H) > random_value(H) + delta 조건이 유지되는
      최대 H를 Planning Depth로 결정한다.
    """

    def __init__(
        self,
        max_depth: int = 25,
        n_trials: int = 20,
        significance_margin: float = 0.05,
        random_baseline_trials: int = 50,
        discount_factor: float = 0.95,
    ) -> None:
        self.max_depth = max_depth
        self.n_trials = n_trials
        self.significance_margin = significance_margin
        self.random_baseline_trials = random_baseline_trials
        self.discount_factor = discount_factor

    def probe(
        self,
        agent_fn: Callable[[State, int], Action],
        env_fn: Callable,
    ) -> PlanningDepthResult:
        """레거시 env_fn 방식으로 PD를 측정한다.

        Args:
            agent_fn: (state, depth_hint) -> action
            env_fn:   (state, action) -> (next_state, reward, done)
        """
        return self._probe_impl(agent_fn, _LegacyEnvAdapter(env_fn))

    def probe_env(
        self,
        agent_fn: Callable[[State, int], Action],
        env: ProbingEnvironment,
    ) -> PlanningDepthResult:
        """ProbingEnvironment 인터페이스로 PD를 측정한다."""
        return self._probe_impl(agent_fn, env)

    def probe_with_neural_rollout(
        self,
        agent_fn: Callable[[State, int], Action],
        env: ProbingEnvironment,
        rollout_policy_fn: Callable[[State], Action],
    ) -> PlanningDepthResult:
        """L3 신경망 롤아웃 정책을 사용해 PD를 측정한다.

        D≥18인 에이전트에서 랜덤 롤아웃 대신 학습된 정책으로
        가치 추정 정확도를 높인다(논문 §5.4).
        """
        return self._probe_impl(agent_fn, env, rollout_policy_fn=rollout_policy_fn)

    # ── 내부 구현 ─────────────────────────────────────────────

    def _probe_impl(
        self,
        agent_fn: Callable,
        env: ProbingEnvironment,
        rollout_policy_fn: Callable | None = None,
    ) -> PlanningDepthResult:
        value_range = self._estimate_value_range(env)
        delta = self.significance_margin * value_range

        best_depth = 1
        series: list[float] = []

        for h in range(1, self.max_depth + 1):
            agent_val = self._rollout_agent(agent_fn, env, h)
            baseline_val = self._rollout_baseline(rollout_policy_fn, env, h)
            margin = agent_val - baseline_val - delta
            series.append(round(margin, 4))

            if agent_val > baseline_val + delta:
                best_depth = h
            else:
                break

        positive_margins = [m for m in series if m > 0]
        if positive_margins and delta > 1e-9:
            confidence = min(1.0, positive_margins[-1] / delta)
        else:
            confidence = 0.0

        return PlanningDepthResult(
            depth=best_depth,
            level=classify_level(best_depth),
            confidence=round(float(confidence), 4),
            series=series,
        )

    def _rollout_agent(
        self,
        agent_fn: Callable,
        env: ProbingEnvironment,
        depth: int,
    ) -> float:
        total = 0.0
        for _ in range(self.n_trials):
            state = env.reset()
            cumulative = 0.0
            for step in range(depth):
                action = agent_fn(state, depth)
                state, reward, done = env.step(action)
                cumulative += (self.discount_factor**step) * reward
                if done:
                    break
            total += cumulative
        return total / self.n_trials

    def _rollout_baseline(
        self,
        policy_fn: Callable | None,
        env: ProbingEnvironment,
        depth: int,
    ) -> float:
        total = 0.0
        for _ in range(self.random_baseline_trials):
            state = env.reset()
            cumulative = 0.0
            for step in range(depth):
                action = policy_fn(state) if policy_fn is not None else env.sample_random_action()
                state, reward, done = env.step(action)
                cumulative += (self.discount_factor**step) * reward
                if done:
                    break
            total += cumulative
        return total / self.random_baseline_trials

    def _estimate_value_range(self, env: ProbingEnvironment) -> float:
        rewards: list[float] = []
        for _ in range(self.random_baseline_trials):
            env.reset()
            for _ in range(10):
                action = env.sample_random_action()
                _, reward, done = env.step(action)
                rewards.append(reward)
                if done:
                    break
        if not rewards:
            return 1.0
        return max(rewards) - min(rewards) or 1.0


# ─────────────────────────────────────────────────────────────
# 레벨 분류
# ─────────────────────────────────────────────────────────────


def classify_level(depth: int) -> str:
    """Planning Depth → Level 분류 (논문 §3.2 기준).

    L1: PD < 5   (Predictor)
    L2: 5 ≤ PD < 18  (Simulator)
    L3: PD ≥ 18  (Evolver)
    """
    if depth >= 18:
        return "L3"
    if depth >= 5:
        return "L2"
    return "L1"


# ─────────────────────────────────────────────────────────────
# 시계열 추적
# ─────────────────────────────────────────────────────────────


class PlanningDepthTimeSeries:
    """시계열 Planning Depth 추적 + 저하 경보.

    PAT-001 종속항 9: 주기적 측정 후 기준선 대비 0.8 이하 저하 시 경보 발생.
    """

    def __init__(
        self,
        agent_name: str,
        baseline_window: int = 5,
        degradation_threshold: float = 0.8,
    ) -> None:
        self.agent_name = agent_name
        self.baseline_window = baseline_window
        self.degradation_threshold = degradation_threshold
        self._snapshots: list[PlanningDepthSnapshot] = []
        self.on_degradation: Callable[[DegradationAlert], None] | None = None

    def record(self, result: PlanningDepthResult) -> DegradationAlert | None:
        """측정 결과를 기록하고 저하 경보가 있으면 반환한다."""
        snapshot = PlanningDepthSnapshot(
            timestamp=time.time(),
            depth=result.depth,
            level=result.level,
        )
        self._snapshots.append(snapshot)

        if len(self._snapshots) <= self.baseline_window:
            return None

        baseline = (
            sum(s.depth for s in self._snapshots[: self.baseline_window]) / self.baseline_window
        )
        if baseline == 0:
            return None

        ratio = result.depth / baseline
        if ratio < self.degradation_threshold:
            alert = DegradationAlert(
                agent_name=self.agent_name,
                timestamp=snapshot.timestamp,
                current_depth=result.depth,
                baseline_depth=round(baseline, 2),
                drop_ratio=round(ratio, 4),
            )
            if self.on_degradation is not None:
                self.on_degradation(alert)
            return alert
        return None

    @property
    def snapshots(self) -> list[PlanningDepthSnapshot]:
        return list(self._snapshots)

    def latest(self) -> PlanningDepthSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def summary(self) -> dict[str, Any]:
        if not self._snapshots:
            return {"agent_name": self.agent_name, "count": 0}
        latest = self._snapshots[-1]
        return {
            "agent_name": self.agent_name,
            "count": len(self._snapshots),
            "latest_depth": latest.depth,
            "latest_level": latest.level,
        }


# ─────────────────────────────────────────────────────────────
# 로그 기반 PD 추출 (기존 compute_planning_depth_from_logs 호환)
# ─────────────────────────────────────────────────────────────


def extract_pd_from_logs(episodes: list[dict[str, Any]]) -> float | None:
    """에피소드 로그의 planning_depth_used 필드 평균을 반환한다.

    필드가 없으면 None을 반환하여 행동 프로빙 폴백을 유도한다.
    """
    depths = [
        ep["planning_depth_used"] for ep in episodes if ep.get("planning_depth_used") is not None
    ]
    if not depths:
        return None
    return sum(depths) / len(depths)
