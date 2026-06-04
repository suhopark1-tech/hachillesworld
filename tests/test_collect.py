"""Log Collector SDK 테스트."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from hachillesworld.collect.collector import LogCollector, _state_distance
from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.collect.flush import BatchFlusher
from hachillesworld.collect.study_client import StudyClient


# ── EpisodeRecord 테스트 ──────────────────────────────────────────


class TestEpisodeRecord:
    def test_defaults(self):
        r = EpisodeRecord(agent_id="agent-001")
        assert r.agent_id == "agent-001"
        assert r.episode_id != ""  # UUID 자동 생성
        assert r.goal_achieved is True
        assert r.episode_success is True
        assert r.llm_tokens == 0
        assert r.flag_types == []

    def test_to_dict_round_trip(self):
        r = EpisodeRecord(
            agent_id="agent-001",
            domain="supply_chain",
            confidence=0.78,
            predicted_next_state={"inventory": 820},
            actual_next_state={"inventory": 620},
            goal_achieved=False,
            llm_tokens=1847,
        )
        d = r.to_dict()
        r2 = EpisodeRecord.from_dict(d)
        assert r2.agent_id == r.agent_id
        assert r2.domain == r.domain
        assert r2.confidence == r.confidence
        assert r2.predicted_next_state == r.predicted_next_state
        assert r2.goal_achieved == r.goal_achieved
        assert r2.llm_tokens == r.llm_tokens

    def test_has_detectable_error_prediction(self):
        r = EpisodeRecord(agent_id="a", max_prediction_error=0.20)
        assert r.has_detectable_error(theta_drift=0.15) is True

    def test_has_detectable_error_goal_failure(self):
        r = EpisodeRecord(agent_id="a", goal_achieved=False)
        assert r.has_detectable_error() is True

    def test_has_detectable_error_flag(self):
        r = EpisodeRecord(agent_id="a", internal_flag_raised=True)
        assert r.has_detectable_error() is True

    def test_has_detectable_error_clean(self):
        r = EpisodeRecord(agent_id="a", max_prediction_error=0.05, goal_achieved=True)
        assert r.has_detectable_error() is False

    def test_is_self_correction_true(self):
        r = EpisodeRecord(
            agent_id="a",
            internal_flag_raised=True,
            correction_source="self",
            error_before_correction=0.30,
            error_after_correction=0.10,
        )
        assert r.is_self_correction() is True

    def test_is_self_correction_not_enough_improvement(self):
        r = EpisodeRecord(
            agent_id="a",
            internal_flag_raised=True,
            correction_source="self",
            error_before_correction=0.30,
            error_after_correction=0.28,  # 6.7% — 5% 기준 통과하지만 edge case
        )
        assert r.is_self_correction(min_improvement=0.10) is False

    def test_is_self_correction_harness_excluded(self):
        r = EpisodeRecord(
            agent_id="a",
            internal_flag_raised=True,
            correction_source="harness",  # HARNESS → SCR 제외
            error_before_correction=0.30,
            error_after_correction=0.10,
        )
        assert r.is_self_correction() is False

    def test_is_self_correction_no_flag(self):
        r = EpisodeRecord(
            agent_id="a",
            internal_flag_raised=False,
            correction_source="self",
            error_before_correction=0.30,
            error_after_correction=0.10,
        )
        assert r.is_self_correction() is False


# ── _state_distance 테스트 ────────────────────────────────────────


class TestStateDistance:
    def test_identical_states(self):
        d = _state_distance({"inventory": 820}, {"inventory": 820})
        assert d == 0.0

    def test_simple_difference(self):
        # |820 - 620| / max(820, 620) = 200/820 ≈ 0.2439
        d = _state_distance({"inventory": 820}, {"inventory": 620})
        assert 0.20 < d < 0.30

    def test_multiple_keys_average(self):
        pred = {"inventory": 100, "demand": 50}
        actual = {"inventory": 80, "demand": 50}
        d = _state_distance(pred, actual)
        assert d > 0.0

    def test_no_common_numeric_keys(self):
        d = _state_distance({"status": "ok"}, {"status": "ok"})
        assert d == 0.0

    def test_empty_dicts(self):
        assert _state_distance({}, {}) == 0.0


# ── EpisodeContext 테스트 ─────────────────────────────────────────


class TestEpisodeContext:
    def _make_collector(self) -> LogCollector:
        """API 없이 로컬 테스트용 collector."""
        return LogCollector(
            agent_id="test-agent",
            api_key="",
            domain="supply_chain",
        )

    def test_basic_context_creates_record(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.set_confidence(0.78)
            ep.set_tokens(1000)
            ep.add_tool("search_api")
            ep.set_goal(achieved=True)

        assert collector.buffer_size == 1
        record = list(collector._buffer)[0]
        assert record.confidence == 0.78
        assert record.llm_tokens == 1000
        assert "search_api" in record.tools_used
        assert record.goal_achieved is True

    def test_predicted_vs_actual_state_auto_error(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.set_predicted_state({"inventory": 820})
            ep.set_actual_state({"inventory": 620})

        record = list(collector._buffer)[0]
        assert record.max_prediction_error is not None
        assert record.max_prediction_error > 0

    def test_flag_sets_internal_flag(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.set_flag("confidence")
            ep.set_flag("prediction")

        record = list(collector._buffer)[0]
        assert record.internal_flag_raised is True
        assert "confidence" in record.flag_types
        assert "prediction" in record.flag_types

    def test_self_correction(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.set_flag("confidence")
            ep.set_correction(
                source="self",
                original="order_100",
                corrected="order_150",
                error_before=0.30,
                error_after=0.08,
            )

        record = list(collector._buffer)[0]
        assert record.correction_source == "self"
        assert record.agent_self_flagged is True
        assert record.original_action == "order_100"
        assert record.corrected_action == "order_150"
        assert record.is_self_correction() is True

    def test_exception_in_context_sets_failure(self):
        collector = self._make_collector()
        with pytest.raises(ValueError):
            with collector.episode():
                raise ValueError("agent error")

        record = list(collector._buffer)[0]
        assert record.episode_success is False
        assert "exception" in record.metadata

    def test_duration_ms_is_set(self):
        collector = self._make_collector()
        with collector.episode():
            time.sleep(0.01)

        record = list(collector._buffer)[0]
        assert record.duration_ms is not None
        assert record.duration_ms >= 10.0

    def test_confidence_history_accumulated(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.set_confidence(0.80)
            ep.set_confidence(0.65)
            ep.set_confidence(0.72)

        record = list(collector._buffer)[0]
        assert record.confidence == 0.72  # 마지막 값
        assert record.confidence_history == [0.80, 0.65, 0.72]

    def test_harness_trigger_recorded(self):
        collector = self._make_collector()
        with collector.episode() as ep:
            ep.add_harness_trigger("rule_bulk_delete")
            ep.set_correction(source="harness", original="delete_all", corrected="none")

        record = list(collector._buffer)[0]
        assert "rule_bulk_delete" in record.harness_triggers
        assert record.harness_reject_triggered is True


# ── LogCollector 테스트 ───────────────────────────────────────────


class TestLogCollector:
    def test_add_and_buffer_size(self):
        collector = LogCollector(agent_id="a", api_key="")
        r = EpisodeRecord(agent_id="a")
        collector.add(r)
        assert collector.buffer_size == 1
        assert collector.stats["total_added"] == 1

    def test_batch_flush_trigger(self):
        """배치 크기 도달 시 자동 flush 호출."""
        flushed: list[int] = []

        class TrackingFlusher(BatchFlusher):
            def flush(self, records):
                flushed.append(len(records))
                return len(records)

        collector = LogCollector(agent_id="a", api_key="", batch_size=5)
        collector._flusher = TrackingFlusher("", "http://localhost")

        for _ in range(5):
            collector.add(EpisodeRecord(agent_id="a"))

        assert len(flushed) == 1
        assert flushed[0] == 5
        assert collector.buffer_size == 0

    def test_flush_empties_buffer(self):
        collector = LogCollector(agent_id="a", api_key="")
        for _ in range(3):
            collector.add(EpisodeRecord(agent_id="a"))

        # flusher를 mock으로 교체 (HTTP 없이 테스트)
        collector._flusher = MagicMock()
        collector._flusher.flush.return_value = 3

        count = collector.flush()
        assert count == 3
        assert collector.buffer_size == 0

    def test_background_thread_start_stop(self):
        collector = LogCollector(agent_id="a", api_key="", flush_interval=0.1)
        collector._flusher = MagicMock()
        collector._flusher.flush.return_value = 0

        collector.start()
        assert collector._thread is not None
        assert collector._thread.is_alive()

        collector.stop()
        assert not collector._thread.is_alive()

    def test_thread_safety(self):
        """여러 스레드에서 동시 add가 안전한지 검증."""
        collector = LogCollector(agent_id="a", api_key="", batch_size=1000)
        collector._flusher = MagicMock()
        collector._flusher.flush.return_value = 0

        def add_records():
            for _ in range(50):
                collector.add(EpisodeRecord(agent_id="a"))

        threads = [threading.Thread(target=add_records) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 500개가 손실 없이 추가됨
        assert collector.stats["total_added"] == 500

    def test_context_manager(self):
        collector = LogCollector(agent_id="a", api_key="", flush_interval=60)
        collector._flusher = MagicMock()
        collector._flusher.flush.return_value = 0

        with collector as c:
            c.add(EpisodeRecord(agent_id="a"))

        # stop() 호출됨 → flush됨
        collector._flusher.flush.assert_called()


# ── BatchFlusher 테스트 ───────────────────────────────────────────


class TestBatchFlusher:
    def test_successful_flush(self):
        records = [EpisodeRecord(agent_id="a"), EpisodeRecord(agent_id="b")]

        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            flusher = BatchFlusher(api_key="haw-test", ingest_url="http://localhost")
            count = flusher.flush(records)

        assert count == 2

    def test_empty_flush_returns_zero(self):
        flusher = BatchFlusher(api_key="", ingest_url="http://localhost")
        assert flusher.flush([]) == 0

    def test_fallback_on_failure(self, tmp_path: Path):
        records = [EpisodeRecord(agent_id="x", domain="test")]
        fallback = tmp_path / "fallback.jsonl"

        with patch("httpx.Client.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("connection refused")
            flusher = BatchFlusher(
                api_key="",
                ingest_url="http://localhost:9999",
                fallback_path=fallback,
            )
            count = flusher.flush(records)

        assert count == 0
        assert fallback.exists()
        lines = fallback.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded["agent_id"] == "x"

    def test_4xx_skips_retry_goes_to_fallback(self, tmp_path: Path):
        records = [EpisodeRecord(agent_id="y")]
        fallback = tmp_path / "fallback.jsonl"

        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=401)
            flusher = BatchFlusher(
                api_key="bad-key",
                ingest_url="http://localhost",
                fallback_path=fallback,
            )
            count = flusher.flush(records)

        assert count == 0
        # 4xx는 재시도 없이 바로 fallback → post 1회만 호출
        assert mock_post.call_count == 1
        assert fallback.exists()


# ── StudyClient 테스트 ────────────────────────────────────────────


class TestStudyClient:
    def _make_client(self) -> StudyClient:
        client = StudyClient(
            study_id="HAW-STUDY-001",
            agent_id="anon-007",
            domain="supply_chain",
            api_key="",
        )
        client._collector._flusher = MagicMock()
        client._collector._flusher.flush.return_value = 0
        client._collector._flusher.close = MagicMock()
        return client

    def test_episode_context(self):
        client = self._make_client()
        with client.episode() as ep:
            ep.set_confidence(0.90)
            ep.set_goal(achieved=True)

        assert client._collector.stats["total_added"] == 1
        client.close()

    def test_study_id_propagated(self):
        client = self._make_client()
        with client.episode() as ep:
            ep.set_tokens(500)

        record = list(client._collector._buffer)[0]
        assert record.study_id == "HAW-STUDY-001"
        assert record.agent_id == "anon-007"
        client.close()

    def test_instrument_decorator(self):
        client = self._make_client()

        @client.instrument
        class DummyAgent:
            def execute(self, action: str) -> str:
                return f"done:{action}"

        agent = DummyAgent()
        result = agent.execute("order_100")

        assert result == "done:order_100"
        assert client._collector.stats["total_added"] >= 1
        client.close()

    def test_instrument_on_failure(self):
        client = self._make_client()

        @client.instrument
        class FailingAgent:
            def execute(self, action: str) -> None:
                raise RuntimeError("api timeout")

        agent = FailingAgent()
        with pytest.raises(RuntimeError):
            agent.execute("order")

        record = list(client._collector._buffer)[0]
        assert record.episode_success is False
        client.close()

    def test_context_manager(self):
        with StudyClient(
            study_id="HAW-STUDY-001",
            agent_id="anon-008",
            api_key="",
        ) as client:
            client._collector._flusher = MagicMock()
            client._collector._flusher.flush.return_value = 0
            client._collector._flusher.close = MagicMock()
            with client.episode() as ep:
                ep.set_confidence(0.75)

        # __exit__ 호출 시 close() → stop() 실행됨
        assert not client._collector._thread.is_alive()
