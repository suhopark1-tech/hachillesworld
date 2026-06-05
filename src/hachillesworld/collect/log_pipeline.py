# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""StudyLogPipeline — HAW-STUDY-001 30일 로그 집계·익명화·전송."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from hachillesworld.collect.episode import EpisodeRecord

logger = logging.getLogger(__name__)

_PRIVATE_KEYS: frozenset[str] = frozenset(
    {"org_name", "user_id", "email", "name", "ip_address", "phone", "address", "user_email"}
)


class StudyLogPipeline:
    """HAW-STUDY-001 에피소드 로그 30일 집계·익명화·전송 파이프라인.

    사용 예:
        pipeline = StudyLogPipeline(
            study_id="HAW-20260101-ABCDEF",
            log_dir=".haw_study/logs",
        )

        # 30일 집계 + 완결성 검증
        result = pipeline.validate_completeness()
        if result["is_complete"]:
            pipeline.flush_to_study_server(api_key="haw-...")
    """

    def __init__(
        self,
        study_id: str,
        log_dir: str | Path = ".haw_study/logs",
        study_days: int = 30,
    ) -> None:
        self.study_id = study_id
        self.log_dir = Path(log_dir)
        self.study_days = study_days

    # ── 집계 ─────────────────────────────────────────────────────────

    def aggregate_30day(self) -> list[EpisodeRecord]:
        """지난 30일의 에피소드 로그를 집계한다."""
        from hachillesworld.collect.episode import EpisodeRecord

        cutoff = datetime.now(UTC) - timedelta(days=self.study_days)
        records: list[EpisodeRecord] = []

        if not self.log_dir.exists():
            return records

        for jsonl_file in sorted(self.log_dir.glob("**/*.jsonl")):
            with jsonl_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # study_id 필터 (None이면 모두 수집)
                        file_sid = data.get("study_id")
                        if file_sid and file_sid != self.study_id:
                            continue
                        ts_str = data.get("timestamp", "")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts.tzinfo is None:
                                ts = ts.replace(tzinfo=UTC)
                            if ts < cutoff:
                                continue
                        records.append(EpisodeRecord.from_dict(data))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        logger.info("aggregate_30day: %d records (study=%s)", len(records), self.study_id)
        return records

    # ── 익명화 ────────────────────────────────────────────────────────

    def anonymize(self, records: list[EpisodeRecord]) -> list[EpisodeRecord]:
        """개인정보 제거.

        - agent_id → SHA256(agent_id) hex (64자)
        - metadata의 민감 키 제거 (org_name, user_id, email 등)
        """
        from hachillesworld.collect.episode import EpisodeRecord

        anonymized: list[EpisodeRecord] = []
        for r in records:
            anon_id = hashlib.sha256(r.agent_id.encode()).hexdigest()
            clean_meta = {
                k: v
                for k, v in r.metadata.items()
                if k.lower() not in _PRIVATE_KEYS
            }
            d = r.to_dict()
            d["agent_id"] = anon_id
            d["metadata"] = clean_meta
            anonymized.append(EpisodeRecord.from_dict(d))
        return anonymized

    # ── 전송 ─────────────────────────────────────────────────────────

    def flush_to_study_server(
        self,
        api_key: str,
        ingest_url: str = "https://ingest.hachillesworld.ai/v1",
        timeout: float = 30.0,
    ) -> int:
        """30일 집계 데이터를 익명화하여 연구 서버로 일괄 전송한다.

        Returns:
            전송 성공한 레코드 수 (실패 시 0)
        """
        records = self.anonymize(self.aggregate_30day())
        if not records:
            logger.warning("flush_to_study_server: 전송할 레코드가 없습니다")
            return 0

        url = ingest_url.rstrip("/") + "/study/episodes"
        payload = {
            "study_id": self.study_id,
            "sent_at": datetime.now(UTC).isoformat(),
            "n_records": len(records),
            "episodes": [r.to_dict() for r in records],
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
            logger.info("flush_to_study_server: %d개 레코드 전송 완료", len(records))
            return len(records)
        except httpx.HTTPError as exc:
            logger.error("flush_to_study_server 실패: %s — 로컬 폴백 저장", exc)
            self._save_fallback(records)
            return 0

    # ── 완결성 검증 ──────────────────────────────────────────────────

    def validate_completeness(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """30일 데이터 완결성 검증.

        Returns:
            {
                "n_records": int,
                "n_days_covered": int,
                "coverage_pct": float,   # 0.0 ~ 1.0
                "missing_days": list[str],
                "is_complete": bool,     # coverage_pct >= 0.90
            }
        """
        end = end_date or datetime.now(UTC)
        start = start_date or (end - timedelta(days=self.study_days - 1))

        records = self.aggregate_30day()
        days_with_data: set[str] = set()
        for r in records:
            try:
                ts = datetime.fromisoformat(r.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if start <= ts <= end:
                    days_with_data.add(ts.strftime("%Y-%m-%d"))
            except (ValueError, AttributeError):
                continue

        total_days = (end.date() - start.date()).days + 1
        expected_days = {
            (start + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(total_days)
        }
        missing = sorted(expected_days - days_with_data)
        n_covered = len(expected_days & days_with_data)
        coverage_pct = n_covered / total_days if total_days > 0 else 0.0

        return {
            "n_records": len(records),
            "n_days_covered": n_covered,
            "coverage_pct": coverage_pct,
            "missing_days": missing,
            "is_complete": coverage_pct >= 0.90,
        }

    # ── 내부 ─────────────────────────────────────────────────────────

    def _save_fallback(self, records: list[EpisodeRecord]) -> None:
        fallback_dir = self.log_dir / "fallback"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        path = fallback_dir / f"flush_{self.study_id}_{ts}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r.to_dict()) + "\n")
        logger.info("폴백 저장: %s (%d건)", path, len(records))
