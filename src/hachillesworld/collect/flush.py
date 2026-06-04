"""BatchFlusher — HTTP 전송, 지수 백오프 재시도, JSONL 폴백."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from hachillesworld.collect.episode import EpisodeRecord

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # 지수 백오프: 1 → 2 → 4초


class BatchFlusher:
    """
    EpisodeRecord 배치를 인제스트 엔드포인트로 전송한다.

    전송 실패 시 지수 백오프로 최대 3회 재시도한다.
    모든 재시도 소진 시 fallback_path JSONL 파일에 기록한다.
    """

    def __init__(
        self,
        api_key: str,
        ingest_url: str,
        fallback_path: str | Path | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._ingest_url = ingest_url.rstrip("/") + "/episodes"
        self._fallback_path = Path(fallback_path) if fallback_path else None
        self._http = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-HAW-Version": "1.0",
            },
            timeout=timeout,
        )

    def flush(self, records: list[EpisodeRecord]) -> int:
        """
        records를 인제스트 엔드포인트로 전송한다.
        반환값: 성공적으로 전송된 레코드 수 (실패 시 0).
        """
        if not records:
            return 0

        payload = [r.to_dict() for r in records]

        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                resp = self._http.post(self._ingest_url, json=payload)
                if resp.status_code == 200:
                    logger.debug("Flushed %d records (attempt %d)", len(records), attempt)
                    return len(records)
                if resp.status_code < 500:
                    # 4xx: 재시도해도 의미 없음 → 즉시 폴백
                    logger.warning(
                        "Ingest rejected (HTTP %d). Writing to fallback.",
                        resp.status_code,
                    )
                    break
                logger.warning(
                    "Ingest HTTP %d, retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    delay,
                    attempt,
                    len(_RETRY_DELAYS),
                )
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning(
                    "Ingest unreachable (%s), retrying in %.1fs (attempt %d/%d)",
                    exc,
                    delay,
                    attempt,
                    len(_RETRY_DELAYS),
                )

            time.sleep(delay)

        # 모든 재시도 소진 → JSONL 폴백
        self._write_fallback(records)
        return 0

    def _write_fallback(self, records: list[EpisodeRecord]) -> None:
        """로컬 JSONL 파일에 기록. fallback_path가 없으면 haw_fallback.jsonl 사용."""
        path = self._fallback_path or Path("haw_fallback.jsonl")
        try:
            with path.open("a", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            logger.info("Wrote %d records to fallback: %s", len(records), path)
        except OSError as exc:
            logger.error("Fallback write failed: %s", exc)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BatchFlusher":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
