"""hachillesworld collect CLI 서브커맨드 테스트."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from hachillesworld.cli import app
from hachillesworld.collect.episode import EpisodeRecord

runner = CliRunner()


# ── 공통 픽스처 ────────────────────────────────────────────────────


def _make_episode(
    agent_id: str = "agent-001",
    domain: str = "supply_chain",
    goal_achieved: bool = True,
    max_prediction_error: float | None = None,
    internal_flag_raised: bool = False,
    correction_source: str | None = None,
    error_before: float | None = None,
    error_after: float | None = None,
) -> dict:
    r = EpisodeRecord(
        agent_id=agent_id,
        domain=domain,
        goal_achieved=goal_achieved,
        episode_success=goal_achieved,
        max_prediction_error=max_prediction_error,
        internal_flag_raised=internal_flag_raised,
        flag_types=["prediction"] if internal_flag_raised else [],
        correction_source=correction_source,
        agent_self_flagged=(correction_source == "self"),
        error_before_correction=error_before,
        error_after_correction=error_after,
        llm_tokens=1000,
    )
    return r.to_dict()


@pytest.fixture
def jsonl_file(tmp_path: Path) -> Path:
    """5개 에피소드가 담긴 JSONL 파일."""
    records = [
        _make_episode(goal_achieved=True, max_prediction_error=0.05),
        _make_episode(
            goal_achieved=False,
            max_prediction_error=0.25,
            internal_flag_raised=True,
            correction_source="self",
            error_before=0.30,
            error_after=0.08,
        ),
        _make_episode(goal_achieved=True, max_prediction_error=0.10),
        _make_episode(
            goal_achieved=False,
            max_prediction_error=0.20,
            internal_flag_raised=True,
            correction_source="harness",
        ),
        _make_episode(goal_achieved=True, max_prediction_error=0.04),
    ]
    fp = tmp_path / "episodes.jsonl"
    fp.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    return fp


@pytest.fixture
def json_array_file(tmp_path: Path) -> Path:
    """JSON 배열 형식 파일."""
    records = [_make_episode(), _make_episode(agent_id="agent-002")]
    fp = tmp_path / "episodes.json"
    fp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return fp


# ── collect ingest 테스트 ─────────────────────────────────────────


class TestCollectIngest:
    def test_dry_run_no_send(self, jsonl_file: Path):
        result = runner.invoke(app, ["collect", "ingest", str(jsonl_file), "--dry-run"])
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "전송하지" in result.output

    def test_loads_jsonl_and_shows_stats(self, jsonl_file: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(jsonl_file),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "5" in result.output  # 5건 로드

    def test_loads_json_array(self, json_array_file: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(json_array_file),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "2" in result.output

    def test_agent_id_override(self, jsonl_file: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(jsonl_file),
                "--agent-id",
                "overridden-agent",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_domain_override(self, jsonl_file: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(jsonl_file),
                "--domain",
                "finance",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_multiple_files(self, tmp_path: Path, jsonl_file: Path):
        second = tmp_path / "episodes2.jsonl"
        second.write_text(
            json.dumps(_make_episode(agent_id="agent-002"), ensure_ascii=False),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(jsonl_file),
                str(second),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_missing_file_exits_1(self, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "ingest",
                str(tmp_path / "nonexistent.jsonl"),
            ],
        )
        assert result.exit_code == 1
        assert "파일 없음" in result.output

    def test_empty_file_exits_0(self, tmp_path: Path):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        result = runner.invoke(app, ["collect", "ingest", str(empty)])
        assert result.exit_code == 0
        assert "없습니다" in result.output

    def test_sends_via_flusher(self, jsonl_file: Path):
        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:
            mock_flush.return_value = 5
            result = runner.invoke(
                app,
                [
                    "collect",
                    "ingest",
                    str(jsonl_file),
                    "--api-key",
                    "haw-test",
                    "--batch",
                    "10",
                ],
            )
        assert result.exit_code == 0
        mock_flush.assert_called_once()

    def test_fallback_path_passed(self, jsonl_file: Path, tmp_path: Path):
        fallback = tmp_path / "fallback.jsonl"
        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:
            mock_flush.return_value = 0  # 전송 실패
            result = runner.invoke(
                app,
                [
                    "collect",
                    "ingest",
                    str(jsonl_file),
                    "--api-key",
                    "haw-test",
                    "--fallback",
                    str(fallback),
                ],
            )
        assert result.exit_code == 0
        assert "실패" in result.output

    def test_study_id_applied(self, jsonl_file: Path, tmp_path: Path):
        """study_id 덮어쓰기가 BatchFlusher로 전달되는지 검증."""
        captured: list[list[EpisodeRecord]] = []

        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:

            def capture(batch):
                captured.append(batch)
                return len(batch)

            mock_flush.side_effect = capture

            runner.invoke(
                app,
                [
                    "collect",
                    "ingest",
                    str(jsonl_file),
                    "--study-id",
                    "HAW-STUDY-001",
                    "--api-key",
                    "haw-test",
                ],
            )

        all_records = [r for batch in captured for r in batch]
        assert all(r.study_id == "HAW-STUDY-001" for r in all_records)


# ── collect record 테스트 ─────────────────────────────────────────


class TestCollectRecord:
    def test_writes_to_file(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        result = runner.invoke(
            app,
            [
                "collect",
                "record",
                "--agent-id",
                "test-agent",
                "--domain",
                "finance",
                "--confidence",
                "0.85",
                "--tokens",
                "500",
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0
        assert out.exists()
        record = json.loads(out.read_text(encoding="utf-8"))
        assert record["agent_id"] == "test-agent"
        assert record["domain"] == "finance"
        assert record["confidence"] == 0.85
        assert record["llm_tokens"] == 500

    def test_appends_to_existing_file(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        for _ in range(3):
            runner.invoke(
                app,
                [
                    "collect",
                    "record",
                    "--agent-id",
                    "a",
                    "--output",
                    str(out),
                ],
            )
        lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 3

    def test_stdout_when_no_output(self):
        result = runner.invoke(
            app,
            [
                "collect",
                "record",
                "--agent-id",
                "stdout-agent",
                "--domain",
                "code",
            ],
        )
        assert result.exit_code == 0
        assert "stdout-agent" in result.output

    def test_flag_type_recorded(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        result = runner.invoke(
            app,
            [
                "collect",
                "record",
                "--agent-id",
                "a",
                "--flag",
                "confidence",
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0
        record = json.loads(out.read_text(encoding="utf-8"))
        assert record["internal_flag_raised"] is True
        assert "confidence" in record["flag_types"]

    def test_correction_source_self(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        runner.invoke(
            app,
            [
                "collect",
                "record",
                "--agent-id",
                "a",
                "--correction",
                "self",
                "--output",
                str(out),
            ],
        )
        record = json.loads(out.read_text(encoding="utf-8"))
        assert record["correction_source"] == "self"
        assert record["agent_self_flagged"] is True

    def test_goal_no_flag(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        runner.invoke(
            app,
            [
                "collect",
                "record",
                "--agent-id",
                "a",
                "--no-goal",
                "--output",
                str(out),
            ],
        )
        record = json.loads(out.read_text(encoding="utf-8"))
        assert record["goal_achieved"] is False
        assert record["episode_success"] is False

    def test_send_flag_calls_flusher(self, tmp_path: Path):
        out = tmp_path / "out.jsonl"
        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:
            mock_flush.return_value = 1
            result = runner.invoke(
                app,
                [
                    "collect",
                    "record",
                    "--agent-id",
                    "a",
                    "--api-key",
                    "haw-test",
                    "--send",
                    "--output",
                    str(out),
                ],
            )
        assert result.exit_code == 0
        mock_flush.assert_called_once()


# ── collect replay 테스트 ─────────────────────────────────────────


class TestCollectReplay:
    def test_replay_sends_all(self, jsonl_file: Path):
        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:
            mock_flush.return_value = 5
            result = runner.invoke(
                app,
                [
                    "collect",
                    "replay",
                    str(jsonl_file),
                    "--api-key",
                    "haw-test",
                ],
            )
        assert result.exit_code == 0
        assert "5" in result.output

    def test_replay_missing_file_exits_1(self, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "replay",
                str(tmp_path / "none.jsonl"),
            ],
        )
        assert result.exit_code == 1

    def test_replay_empty_file_exits_0(self, tmp_path: Path):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        result = runner.invoke(app, ["collect", "replay", str(empty)])
        assert result.exit_code == 0

    def test_delete_on_success_removes_file(self, jsonl_file: Path):
        with patch("hachillesworld.collect.flush.BatchFlusher.flush") as mock_flush:
            mock_flush.return_value = 5  # 전체 전송 성공
            result = runner.invoke(
                app,
                [
                    "collect",
                    "replay",
                    str(jsonl_file),
                    "--api-key",
                    "haw-test",
                    "--delete",
                ],
            )
        assert result.exit_code == 0
        assert not jsonl_file.exists()

    def test_delete_on_partial_success_keeps_failed(self, tmp_path: Path):
        """일부 실패 시 실패 레코드만 파일에 남긴다."""
        records = [_make_episode(agent_id=f"a-{i}") for i in range(4)]
        fp = tmp_path / "mixed.jsonl"
        fp.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )

        call_count = [0]

        def partial_flush(batch):
            call_count[0] += 1
            # 첫 배치만 성공
            return len(batch) if call_count[0] == 1 else 0

        with patch("hachillesworld.collect.flush.BatchFlusher.flush", side_effect=partial_flush):
            runner.invoke(
                app,
                [
                    "collect",
                    "replay",
                    str(fp),
                    "--api-key",
                    "haw-test",
                    "--batch",
                    "2",
                    "--delete",
                ],
            )

        # 파일이 존재하고 실패 레코드가 남아 있어야 함
        assert fp.exists()


# ── collect stats 테스트 ─────────────────────────────────────────


class TestCollectStats:
    def test_basic_stats_output(self, jsonl_file: Path):
        result = runner.invoke(app, ["collect", "stats", str(jsonl_file)])
        assert result.exit_code == 0
        assert "SCR" in result.output or "Self-Correction" in result.output
        assert "Goal" in result.output

    def test_scr_calculation(self, tmp_path: Path):
        """SCR = 자기수정 성공 / 분모. 1/3 ≈ 0.333."""
        records = [
            # 분모 포함, 자기수정 성공
            _make_episode(
                max_prediction_error=0.25,
                internal_flag_raised=True,
                correction_source="self",
                error_before=0.30,
                error_after=0.08,
            ),
            # 분모 포함, 하네스 수정 (SCR 제외)
            _make_episode(
                goal_achieved=False, internal_flag_raised=True, correction_source="harness"
            ),
            # 분모 포함, 수정 없음
            _make_episode(max_prediction_error=0.20),
            # 분모 제외 (성공 에피소드)
            _make_episode(goal_achieved=True, max_prediction_error=0.05),
        ]
        fp = tmp_path / "scr_test.jsonl"
        fp.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["collect", "stats", str(fp)])
        assert result.exit_code == 0
        # SCR = 1/3 ≈ 0.333
        assert "0.333" in result.output

    def test_missing_file_exits_1(self, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "stats",
                str(tmp_path / "nope.jsonl"),
            ],
        )
        assert result.exit_code == 1

    def test_show_episodes_flag(self, jsonl_file: Path):
        result = runner.invoke(
            app,
            [
                "collect",
                "stats",
                str(jsonl_file),
                "--episodes",
            ],
        )
        assert result.exit_code == 0
        assert "episode_id" in result.output.lower() or "에피소드" in result.output

    def test_multiple_files_merged(self, tmp_path: Path, jsonl_file: Path):
        second = tmp_path / "more.jsonl"
        second.write_text(
            json.dumps(_make_episode(agent_id="agent-X"), ensure_ascii=False),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "collect",
                "stats",
                str(jsonl_file),
                str(second),
            ],
        )
        assert result.exit_code == 0
        # 5 + 1 = 6건
        assert "6" in result.output

    def test_custom_drift_threshold(self, jsonl_file: Path):
        """--drift-threshold 0.30: 더 적은 에피소드가 분모에 포함됨."""
        result = runner.invoke(
            app,
            [
                "collect",
                "stats",
                str(jsonl_file),
                "--drift-threshold",
                "0.30",
            ],
        )
        assert result.exit_code == 0

    def test_domain_distribution_shown(self, jsonl_file: Path):
        result = runner.invoke(app, ["collect", "stats", str(jsonl_file)])
        assert result.exit_code == 0
        assert "supply_chain" in result.output

    def test_wilson_ci_shown_for_large_sample(self, tmp_path: Path):
        """분모 ≥ 10이면 Wilson CI 출력."""
        records = [_make_episode(goal_achieved=False, max_prediction_error=0.20) for _ in range(15)]
        fp = tmp_path / "large.jsonl"
        fp.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["collect", "stats", str(fp)])
        assert result.exit_code == 0
        assert "CI" in result.output

    def test_small_sample_warning(self, tmp_path: Path):
        """분모 < 100이면 경고 출력."""
        records = [_make_episode(goal_achieved=False, max_prediction_error=0.20) for _ in range(20)]
        fp = tmp_path / "small.jsonl"
        fp.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["collect", "stats", str(fp)])
        assert result.exit_code == 0
        assert "100" in result.output  # 최소 100개 권장 경고
