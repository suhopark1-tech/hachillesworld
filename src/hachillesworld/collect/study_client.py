"""StudyClient — HAW-STUDY-001 연구 참여자용 간소화 클라이언트."""

from __future__ import annotations

import functools
import time
from typing import Any

from hachillesworld.collect.collector import EpisodeContext, LogCollector
from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.core.models import AgentEvent


class StudyClient:
    """
    HAW-STUDY-001 횡단 타당도 연구 참여자를 위한 클라이언트.

    LogCollector를 내부적으로 사용하지만 인터페이스를 연구 참여에 최적화한다:
    - `@instrument` 데코레이터로 기존 에이전트에 3줄로 계측 추가
    - `episode()` 컨텍스트 매니저로 세밀한 데이터 수집

    사용 예:
        from hachillesworld import StudyClient

        client = StudyClient(
            study_id="HAW-STUDY-001",
            agent_id="anon-007",
            domain="supply_chain",
            api_key="haw-...",
        )

        @client.instrument
        class SupplyChainAgent:
            def plan(self, state, goal): ...
            def execute(self, action): ...

        # 또는 세밀한 제어:
        with client.episode() as ep:
            ep.set_confidence(0.82)
            ...
    """

    _TRACKED_METHODS = {"plan", "execute", "observe", "reflect"}

    def __init__(
        self,
        study_id: str,
        agent_id: str,
        domain: str = "",
        api_key: str = "",
        ingest_url: str = "https://ingest.hachillesworld.ai/v1",
        flush_interval: float = 60.0,
        batch_size: int = 100,
        fallback_path: str | None = None,
    ) -> None:
        self.study_id = study_id
        self.agent_id = agent_id
        self.domain = domain

        self._collector = LogCollector(
            agent_id=agent_id,
            api_key=api_key,
            ingest_url=ingest_url,
            domain=domain,
            study_id=study_id,
            flush_interval=flush_interval,
            batch_size=batch_size,
            fallback_path=fallback_path,
        )
        self._collector.start()

    # ── @instrument 데코레이터 ────────────────────────────────────

    def instrument(self, cls: type) -> type:
        """
        에이전트 클래스에 자동 계측을 추가하는 클래스 데코레이터.

        plan / execute / observe / reflect 메서드를 래핑해
        호출 시간, 오류, 토큰 수(있는 경우)를 자동 수집한다.
        에피소드 경계는 execute 호출 시작/종료로 정의한다.

        사용 예:
            @client.instrument
            class MyAgent:
                def plan(self, state, goal): ...
                def execute(self, action): ...
        """
        collector = self._collector

        for method_name in self._TRACKED_METHODS:
            original = getattr(cls, method_name, None)
            if original is None:
                continue

            if method_name == "execute":
                # execute를 에피소드 경계로 사용
                @functools.wraps(original)
                def _wrapped_execute(
                    self_agent: Any,
                    *args: Any,
                    _orig=original,
                    **kwargs: Any,
                ) -> Any:
                    with collector.episode() as ep:
                        start = time.time()
                        error: str | None = None
                        try:
                            result = _orig(self_agent, *args, **kwargs)
                            return result
                        except Exception as exc:
                            error = str(exc)
                            ep.set_goal(achieved=False, success=False)
                            raise
                        finally:
                            duration_ms = (time.time() - start) * 1000
                            ep.set_metadata("method", "execute")
                            ep.set_metadata("duration_ms", round(duration_ms, 2))
                            if error:
                                ep.set_metadata("error", error)
                            # 결과에 토큰 수가 있으면 자동 추출
                            if hasattr(self_agent, "_last_token_count"):
                                ep.set_tokens(self_agent._last_token_count)

                setattr(cls, method_name, _wrapped_execute)

            else:
                # plan / observe / reflect: AgentEvent로 기록
                @functools.wraps(original)
                def _wrapped(
                    self_agent: Any,
                    *args: Any,
                    _orig=original,
                    _name=method_name,
                    **kwargs: Any,
                ) -> Any:
                    start = time.time()
                    error: str | None = None
                    try:
                        result = _orig(self_agent, *args, **kwargs)
                        return result
                    except Exception as exc:
                        error = str(exc)
                        raise
                    finally:
                        duration_ms = (time.time() - start) * 1000
                        # AgentEvent로 기존 client에도 전달 (하위 호환)
                        collector.add(EpisodeRecord(
                            agent_id=collector.agent_id,
                            study_id=collector.study_id,
                            domain=collector.domain,
                            episode_success=(error is None),
                            goal_achieved=(error is None),
                            duration_ms=round(duration_ms, 2),
                            metadata={"method": _name, "error": error},
                        ))

                setattr(cls, method_name, _wrapped)

        return cls

    # ── 에피소드 컨텍스트 ─────────────────────────────────────────

    def episode(
        self,
        episode_id: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> EpisodeContext:
        """에피소드 컨텍스트 매니저를 반환한다."""
        return self._collector.episode(
            episode_id=episode_id,
            initial_state=initial_state,
        )

    # ── 직접 레코드 추가 ─────────────────────────────────────────

    def add(self, record: EpisodeRecord) -> None:
        """EpisodeRecord를 직접 추가한다."""
        self._collector.add(record)

    # ── 상태 및 flush ─────────────────────────────────────────────

    def flush(self) -> int:
        """버퍼를 즉시 flush한다."""
        return self._collector.flush()

    @property
    def stats(self) -> dict[str, int]:
        return self._collector.stats

    def close(self) -> None:
        """남은 버퍼를 flush하고 클라이언트를 종료한다."""
        self._collector.stop()

    # ── 컨텍스트 매니저 ──────────────────────────────────────────

    def __enter__(self) -> "StudyClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
