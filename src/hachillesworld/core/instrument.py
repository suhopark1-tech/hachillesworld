"""@instrument 데코레이터 — 에이전트 클래스를 자동으로 계측한다."""

from __future__ import annotations

import functools
import time
from typing import Any

from hachillesworld.core.models import AgentEvent


def instrument(client: Any, agent_name: str):
    """
    에이전트 클래스에 HAchillesWorld 계측을 자동 추가하는 클래스 데코레이터.

    계측 대상 메서드: plan / execute / observe / reflect
    나머지 메서드는 원본 그대로 유지된다.

    사용 예:
        @instrument(client, agent_name="my-agent")
        class MyAgent:
            def plan(self, state, goal): ...
            def execute(self, action): ...
    """
    TRACKED_METHODS = {"plan", "execute", "observe", "reflect"}

    def decorator(cls: type) -> type:
        for method_name in TRACKED_METHODS:
            original = getattr(cls, method_name, None)
            if original is None:
                continue

            @functools.wraps(original)
            def _wrapped(
                self: Any, *args: Any, _orig=original, _name=method_name, **kwargs: Any
            ) -> Any:
                start = time.time()
                error: str | None = None
                try:
                    result = _orig(self, *args, **kwargs)
                    return result
                except Exception as exc:
                    error = str(exc)
                    raise
                finally:
                    duration_ms = (time.time() - start) * 1000
                    client.emit(
                        AgentEvent(
                            agent_name=agent_name,
                            event_type=_name,
                            timestamp=start,
                            payload={
                                "duration_ms": round(duration_ms, 2),
                                "error": error,
                            },
                        )
                    )

            setattr(cls, method_name, _wrapped)

        return cls

    return decorator
