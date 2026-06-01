"""HAchillesWorld 메인 클라이언트."""

from __future__ import annotations

import time
from typing import Any

import httpx

from hachillesworld.core.config import settings
from hachillesworld.core.models import (
    AgentEvent, DiagnosticReport, LawsDomain, Level,
)


class HAchillesWorldClient:
    """
    HAchillesWorld 플랫폼 클라이언트.

    사용 예:
        client = HAchillesWorldClient(api_key="haw-...")
        report = client.scan(logs=logs, config=config)
        print(report.summary())
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key   = api_key or settings.api_key
        self._base_url  = (base_url or settings.api_base_url).rstrip("/")
        self._http      = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}",
                     "Content-Type": "application/json"},
            timeout=timeout,
        )
        self._event_buffer: list[AgentEvent] = []

    # ── Scan API ───────────────────────────────────────────────

    def scan(
        self,
        logs: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
        agent_name: str = "unnamed-agent",
    ) -> DiagnosticReport:
        """
        에이전트 로그와 설정을 분석해 진단 리포트를 반환한다.
        API 서버가 없는 로컬 환경에서는 로컬 엔진을 사용한다.
        """
        from hachillesworld.scan.engine import ScanEngine
        engine = ScanEngine(config=config or {})
        return engine.run(logs=logs or [], agent_name=agent_name)

    # ── 이벤트 수집 ────────────────────────────────────────────

    def emit(self, event: AgentEvent) -> None:
        """에이전트 이벤트를 버퍼에 추가한다."""
        self._event_buffer.append(event)
        if len(self._event_buffer) >= 100:
            self.flush()

    def flush(self) -> int:
        """버퍼의 이벤트를 인제스트 엔드포인트로 전송한다."""
        if not self._event_buffer:
            return 0
        batch = self._event_buffer[:]
        self._event_buffer.clear()
        # 실제 전송은 서버 연결 시 활성화
        # self._http.post("/events", json=[e.__dict__ for e in batch])
        return len(batch)

    def track(
        self,
        agent_name: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """단순 이벤트 추적 헬퍼."""
        self.emit(AgentEvent(
            agent_name=agent_name,
            event_type=event_type,
            timestamp=time.time(),
            payload=payload or {},
        ))

    def __enter__(self) -> "HAchillesWorldClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.flush()
        self._http.close()
