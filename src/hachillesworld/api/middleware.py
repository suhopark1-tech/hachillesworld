"""AuditMiddleware — 모든 API 호출을 자동으로 감사 로그에 기록 (Sprint 6-B)."""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from hachillesworld.audit.logger import AuditEvent


class AuditMiddleware(BaseHTTPMiddleware):
    """FastAPI 미들웨어 — 모든 HTTP 요청/응답을 감사 로그에 기록한다.

    request.app.state.audit_logger 가 설정되어 있어야 한다.
    미설정 시 로깅 없이 요청을 통과시킨다 (startup 전 요청 등).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        audit_logger = getattr(request.app.state, "audit_logger", None)
        if audit_logger is None:
            return response

        outcome = _status_to_outcome(response.status_code)
        ip = request.client.host if request.client else "unknown"

        event = AuditEvent.create(
            actor=_extract_actor(request),
            action=_path_to_action(request.url.path),
            resource=_extract_resource(request.url.path),
            outcome=outcome,
            ip_address=ip,
            request_size_bytes=int(request.headers.get("content-length", 0)),
            response_size_bytes=0,  # body 소비 없이 측정 불가
            duration_ms=round(duration_ms, 2),
        )
        audit_logger.log(event)
        return response


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────


def _extract_actor(request: Request) -> str:
    """Authorization 헤더에서 API key prefix(앞 8자)를 추출한다."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
        return token[:8] if len(token) >= 8 else token
    return "anonymous"


_PATH_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^/v1/scan$"), "scan"),
    (re.compile(r"/agents/[^/]+/interpret$"), "interpret"),
    (re.compile(r"/agents/[^/]+/next-actions$"), "next_actions"),
    (re.compile(r"/agents/[^/]+/has$"), "has.timeseries"),
    (re.compile(r"/agents/[^/]+/drift/record$"), "drift.record"),
    (re.compile(r"/agents/[^/]+/harness/pending$"), "harness.pending"),
    (re.compile(r"/agents/[^/]+/replay/"), "replay"),
    (re.compile(r"/harness/[^/]+/approve$"), "harness.approve"),
    (re.compile(r"^/v1/audit/events$"), "audit.events"),
    (re.compile(r"^/v1/compliance/"), "compliance"),
    (re.compile(r"^/v1/groups/"), "group"),
    (re.compile(r"^/v1/study/"), "study"),
    (re.compile(r"^/health$"), "health"),
]


def _path_to_action(path: str) -> str:
    """URL path를 의미 있는 action 문자열로 변환한다."""
    for pattern, action in _PATH_RULES:
        if pattern.search(path):
            return action
    # fallback: /v1/foo/bar → "foo.bar"
    cleaned = re.sub(r"^/v1/", "", path).replace("/", ".")
    return cleaned or path


def _extract_resource(path: str) -> str:
    """URL path에서 agent_id 또는 group_id를 추출한다."""
    m = re.search(r"/agents/([^/]+)", path)
    if m:
        return m.group(1)
    m = re.search(r"/groups/([^/]+)", path)
    if m:
        return m.group(1)
    return ""


def _status_to_outcome(status_code: int) -> str:
    if status_code < 400:
        return "success"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    return "error"
