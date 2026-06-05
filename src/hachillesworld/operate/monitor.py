"""실시간 Simulation Drift 모니터링."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class DriftValue:
    """단일 타임스텝의 예측-관측 괴리 기록. PAT-005 §9.2."""

    predicted: dict[str, Any]
    actual: dict[str, Any]
    value: float
    exceeded_threshold: bool
    timestamp: float
    step_index: int = 0


@dataclass
class DriftAlert:
    """드리프트 경보 이벤트."""

    agent_name: str
    timestamp: float
    drift_value: float
    threshold: float
    recent_rate: float
    recommended_action: str
    cause: str = "unknown"
    recalibration_strategy: str = ""


class DriftMonitor:
    """에이전트의 Simulation Drift를 실시간으로 감시한다.
    임계값 초과 시 등록된 모든 콜백(alert_callbacks)을 호출한다.

    사용 예:
        monitor = DriftMonitor(agent_name="my-agent", threshold=0.15)
        monitor.add_alert_callback(lambda alert: print(alert.recommended_action))
        monitor.record(predicted=pred_state, actual=actual_state)
    """

    def __init__(
        self,
        agent_name: str,
        threshold: float = 0.15,
        window_size: int = 20,
        alert_rate_threshold: float = 0.20,
    ) -> None:
        self.agent_name = agent_name
        self.threshold = threshold
        self.window_size = window_size
        self.alert_rate_threshold = alert_rate_threshold

        self._history: deque[float] = deque(maxlen=window_size)
        self._drift_log: list[DriftValue] = []
        self._alert_count = 0
        self._total_count = 0
        self._step_index = 0
        self.alert_callbacks: list[Callable[[DriftAlert], None]] = []

    def add_alert_callback(self, cb: Callable[[DriftAlert], None]) -> None:
        """드리프트 경보 콜백을 추가한다. 복수 등록 지원."""
        self.alert_callbacks.append(cb)

    def record(
        self,
        predicted: dict[str, Any],
        actual: dict[str, Any],
    ) -> float:
        """예측-관측 괴리를 기록하고 드리프트 값을 반환한다."""
        drift = self._compute_drift(predicted, actual)
        self._history.append(drift)
        self._total_count += 1

        exceeded = drift > self.threshold
        self._drift_log.append(
            DriftValue(
                predicted=predicted,
                actual=actual,
                value=round(drift, 6),
                exceeded_threshold=exceeded,
                timestamp=time.time(),
                step_index=self._step_index,
            )
        )
        self._step_index += 1

        if exceeded:
            self._alert_count += 1
            self._maybe_alert(drift)

        return drift

    def get_drift_log(self) -> list[DriftValue]:
        """전체 드리프트 이력 반환. DriftCausalClassifier·Replay Debugger 연동용."""
        return list(self._drift_log)

    def recent_drift_rate(self) -> float:
        """최근 윈도우에서 임계값 초과 비율."""
        if not self._history:
            return 0.0
        return sum(1 for d in self._history if d > self.threshold) / len(self._history)

    def is_stable(self) -> bool:
        """현재 드리프트 수준이 안정적인가."""
        return self.recent_drift_rate() < self.alert_rate_threshold

    def summary(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "total_records": self._total_count,
            "alert_count": self._alert_count,
            "recent_drift_rate": round(self.recent_drift_rate(), 4),
            "is_stable": self.is_stable(),
            "threshold": self.threshold,
            "window_size": self.window_size,
        }

    def _maybe_alert(self, drift: float) -> None:
        rate = self.recent_drift_rate()
        if rate >= self.alert_rate_threshold and self.alert_callbacks:
            alert = DriftAlert(
                agent_name=self.agent_name,
                timestamp=time.time(),
                drift_value=round(drift, 4),
                threshold=self.threshold,
                recent_rate=round(rate, 4),
                recommended_action=(
                    "즉시 재보정 필요: 실제 관측값으로 World Model 동기화"
                    if drift > self.threshold * 2
                    else "재보정 권장: 불확실성 임계값 검토"
                ),
            )
            for cb in self.alert_callbacks:
                cb(alert)

    @staticmethod
    def _compute_drift(predicted: dict[str, Any], actual: dict[str, Any]) -> float:
        """두 상태 딕셔너리의 괴리를 스칼라로 계산한다."""
        common_keys = set(predicted) & set(actual)
        if not common_keys:
            return 0.0
        diffs = []
        for k in common_keys:
            p, a = predicted[k], actual[k]
            if isinstance(p, int | float) and isinstance(a, int | float):
                diffs.append(abs(float(p) - float(a)))
        return sum(diffs) / len(diffs) if diffs else 0.0
