"""LogCollector — 스레드 안전 에피소드 로그 수집기."""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.collect.flush import BatchFlusher

logger = logging.getLogger(__name__)


class EpisodeContext:
    """
    `with collector.episode()` 블록 안에서 에피소드 데이터를 누적한다.
    `__exit__` 시 EpisodeRecord를 완성해 LogCollector 버퍼에 추가한다.

    사용 예:
        with collector.episode(state=initial_state) as ep:
            ep.set_confidence(0.78)
            action = agent.act(state)
            ep.set_predicted_state({"inventory": 820})
            ep.add_tool("order_api")
            ep.set_tokens(1847)
        # __exit__ 에서 자동으로 record 생성 및 버퍼 추가
    """

    def __init__(
        self,
        collector: "LogCollector",
        episode_id: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self._collector = collector
        self._episode_id = episode_id or str(uuid.uuid4())
        self._initial_state = initial_state
        self._start_time: float = 0.0

        # 누적 데이터
        self._confidence: float | None = None
        self._confidence_history: list[float] = []
        self._predicted_state: dict[str, Any] | None = None
        self._actual_state: dict[str, Any] | None = None
        self._flag_types: list[str] = []
        self._internal_flag_raised: bool = False
        self._agent_self_flagged: bool = False
        self._human_intervened: bool = False
        self._human_approval_required: bool = False
        self._harness_reject_triggered: bool = False
        self._correction_source: str | None = None
        self._original_action: str | None = None
        self._corrected_action: str | None = None
        self._error_before: float | None = None
        self._error_after: float | None = None
        self._goal_achieved: bool = True
        self._episode_success: bool = True
        self._infrastructure_failure: bool = False
        self._ood_flagged: bool = False
        self._hitl_required: bool = False
        self._llm_tokens: int = 0
        self._harness_triggers: list[str] = []
        self._tools_used: list[str] = []
        self._planning_depth: int | None = None
        self._metadata: dict[str, Any] = {}

    # ── 컨텍스트 매니저 ──────────────────────────────────────────

    def __enter__(self) -> "EpisodeContext":
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        duration_ms = (time.time() - self._start_time) * 1000

        if exc_type is not None:
            self._episode_success = False
            if not self._infrastructure_failure:
                self._metadata["exception"] = str(exc_val)

        max_prediction_error: float | None = None
        if self._predicted_state and self._actual_state:
            max_prediction_error = _state_distance(
                self._predicted_state, self._actual_state
            )

        record = EpisodeRecord(
            agent_id=self._collector.agent_id,
            episode_id=self._episode_id,
            timestamp=datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat(),
            study_id=self._collector.study_id,
            domain=self._collector.domain,
            confidence=self._confidence,
            internal_flag_raised=self._internal_flag_raised,
            flag_types=self._flag_types,
            agent_self_flagged=self._agent_self_flagged,
            human_intervened=self._human_intervened,
            human_approval_required=self._human_approval_required,
            harness_reject_triggered=self._harness_reject_triggered,
            correction_source=self._correction_source,
            original_action=self._original_action,
            corrected_action=self._corrected_action,
            error_before_correction=self._error_before,
            error_after_correction=self._error_after,
            predicted_next_state=self._predicted_state,
            actual_next_state=self._actual_state,
            max_prediction_error=max_prediction_error,
            planning_depth_used=self._planning_depth,
            goal_achieved=self._goal_achieved,
            episode_success=self._episode_success,
            infrastructure_failure=self._infrastructure_failure,
            ood_flagged=self._ood_flagged,
            hitl_required=self._hitl_required,
            llm_tokens=self._llm_tokens,
            harness_triggers=list(self._harness_triggers),
            tools_used=list(self._tools_used),
            duration_ms=round(duration_ms, 2),
            confidence_history=list(self._confidence_history),
            metadata=self._metadata,
        )
        self._collector.add(record)
        return False  # 예외를 억제하지 않는다

    # ── 데이터 설정 메서드 ────────────────────────────────────────

    def set_confidence(self, value: float) -> "EpisodeContext":
        """행동 확신도 설정. 여러 번 호출하면 마지막 값이 최종 confidence."""
        self._confidence = float(value)
        self._confidence_history.append(float(value))
        return self

    def set_predicted_state(self, state: dict[str, Any]) -> "EpisodeContext":
        """에이전트가 예측한 다음 상태."""
        self._predicted_state = state
        return self

    def set_actual_state(self, state: dict[str, Any]) -> "EpisodeContext":
        """실제 관측된 다음 상태. max_prediction_error는 자동 계산."""
        self._actual_state = state
        return self

    def set_flag(self, flag_type: str) -> "EpisodeContext":
        """
        내부 일관성 플래그 추가.
        flag_type: "confidence" | "prediction" | "counterfactual"
        """
        if flag_type not in self._flag_types:
            self._flag_types.append(flag_type)
        self._internal_flag_raised = True
        return self

    def set_correction(
        self,
        source: str,
        original: str,
        corrected: str,
        error_before: float | None = None,
        error_after: float | None = None,
    ) -> "EpisodeContext":
        """
        자기 수정 이벤트 기록.
        source: "self" | "harness" | "hitl" | "unknown"
        """
        self._correction_source = source
        self._original_action = original
        self._corrected_action = corrected
        self._error_before = error_before
        self._error_after = error_after

        if source == "self":
            self._agent_self_flagged = True
        elif source == "harness":
            self._harness_reject_triggered = True
        elif source == "hitl":
            self._human_intervened = True
            self._hitl_required = True
        return self

    def set_goal(self, achieved: bool, success: bool | None = None) -> "EpisodeContext":
        self._goal_achieved = achieved
        self._episode_success = success if success is not None else achieved
        return self

    def add_tool(self, tool_name: str) -> "EpisodeContext":
        if tool_name not in self._tools_used:
            self._tools_used.append(tool_name)
        return self

    def add_harness_trigger(self, rule_name: str) -> "EpisodeContext":
        self._harness_triggers.append(rule_name)
        return self

    def set_tokens(self, count: int) -> "EpisodeContext":
        self._llm_tokens += count
        return self

    def set_planning_depth(self, depth: int) -> "EpisodeContext":
        self._planning_depth = depth
        return self

    def set_ood(self, flagged: bool = True) -> "EpisodeContext":
        self._ood_flagged = flagged
        return self

    def set_infrastructure_failure(self, failed: bool = True) -> "EpisodeContext":
        self._infrastructure_failure = failed
        self._episode_success = not failed
        return self

    def set_human_approval_required(self, required: bool = True) -> "EpisodeContext":
        self._human_approval_required = required
        self._hitl_required = required
        return self

    def set_metadata(self, key: str, value: Any) -> "EpisodeContext":
        self._metadata[key] = value
        return self


class LogCollector:
    """
    HAchillesWorld 에피소드 로그 수집기.

    스레드 안전 deque 버퍼에 EpisodeRecord를 누적하고,
    백그라운드 스레드가 주기적으로 BatchFlusher를 통해 전송한다.

    사용 예:
        collector = LogCollector(
            api_key="haw-...",
            agent_id="supply-chain-v2",
            domain="supply_chain",
        )
        collector.start()

        with collector.episode() as ep:
            ep.set_confidence(0.82)
            ep.set_predicted_state({"inventory": 820})
            ...

        collector.stop()  # 남은 버퍼 flush 후 종료
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str = "",
        ingest_url: str = "https://ingest.hachillesworld.ai/v1",
        domain: str = "",
        study_id: str | None = None,
        flush_interval: float = 30.0,
        batch_size: int = 50,
        fallback_path: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.domain = domain
        self.study_id = study_id

        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: deque[EpisodeRecord] = deque()
        self._lock = threading.Lock()
        self._flusher = BatchFlusher(
            api_key=api_key,
            ingest_url=ingest_url,
            fallback_path=fallback_path,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._total_flushed: int = 0
        self._total_added: int = 0

    # ── 에피소드 컨텍스트 ─────────────────────────────────────────

    def episode(
        self,
        episode_id: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> EpisodeContext:
        """에피소드 컨텍스트 매니저를 반환한다."""
        return EpisodeContext(
            collector=self,
            episode_id=episode_id,
            initial_state=initial_state,
        )

    # ── 버퍼 조작 ─────────────────────────────────────────────────

    def add(self, record: EpisodeRecord) -> None:
        """EpisodeRecord를 버퍼에 추가한다."""
        with self._lock:
            self._buffer.append(record)
            self._total_added += 1
            if len(self._buffer) >= self._batch_size:
                self._flush_locked()

    def flush(self) -> int:
        """버퍼의 모든 레코드를 즉시 전송한다. 전송된 레코드 수 반환."""
        with self._lock:
            return self._flush_locked()

    def _flush_locked(self) -> int:
        """_lock이 이미 획득된 상태에서 호출해야 한다."""
        if not self._buffer:
            return 0
        batch = list(self._buffer)
        self._buffer.clear()
        # 락 해제 후 IO (데드락 방지)
        count = self._flusher.flush(batch)
        self._total_flushed += count
        return count

    # ── 백그라운드 flush 스레드 ───────────────────────────────────

    def start(self) -> "LogCollector":
        """백그라운드 flush 스레드를 시작한다."""
        if self._thread and self._thread.is_alive():
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._flush_loop,
            name=f"haw-flusher-{self.agent_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("LogCollector started (agent=%s, interval=%.1fs)", self.agent_id, self._flush_interval)
        return self

    def stop(self, timeout: float = 10.0) -> None:
        """백그라운드 스레드를 종료하고 남은 버퍼를 flush한다."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self.flush()
        self._flusher.close()
        logger.info(
            "LogCollector stopped (agent=%s, added=%d, flushed=%d)",
            self.agent_id, self._total_added, self._total_flushed,
        )

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(timeout=self._flush_interval):
            self.flush()

    # ── 상태 조회 ─────────────────────────────────────────────────

    @property
    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total_added": self._total_added,
            "total_flushed": self._total_flushed,
            "buffered": self.buffer_size,
        }

    # ── 컨텍스트 매니저 ──────────────────────────────────────────

    def __enter__(self) -> "LogCollector":
        return self.start()

    def __exit__(self, *_: Any) -> None:
        self.stop()


# ── 내부 유틸리티 ─────────────────────────────────────────────────

def _state_distance(predicted: dict[str, Any], actual: dict[str, Any]) -> float:
    """
    두 상태 딕셔너리의 정규화 거리를 계산한다.

    숫자형 값이 있는 공통 키의 RMSE를 값 범위로 정규화한다.
    키가 없거나 비숫자이면 0.0 반환.
    """
    common_keys = set(predicted) & set(actual)
    diffs: list[float] = []
    for k in common_keys:
        p, a = predicted[k], actual[k]
        if isinstance(p, (int, float)) and isinstance(a, (int, float)):
            scale = max(abs(float(a)), abs(float(p)), 1.0)
            diffs.append(abs(float(p) - float(a)) / scale)
    if not diffs:
        return 0.0
    return round(math.sqrt(sum(d * d for d in diffs) / len(diffs)), 4)
