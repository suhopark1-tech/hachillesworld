"""Sprint 3-C: HAW-STUDY-001 파이프라인 테스트."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from hachillesworld.analyze.correlation import CorrelationResult, HASBusinessCorrelation
from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.collect.log_pipeline import StudyLogPipeline
from hachillesworld.collect.study_client import StudyClient, StudyEnrollment

# ── 헬퍼 ─────────────────────────────────────────────────────────────


def _make_episodes(
    n: int,
    study_id: str,
    agent_id: str = "real-agent-identifier",
    domain: str = "supply_chain",
    days_back: int = 0,
) -> list[EpisodeRecord]:
    records = []
    for i in range(n):
        ts = (datetime.now(UTC) - timedelta(days=days_back) + timedelta(hours=i)).isoformat()
        r = EpisodeRecord(
            agent_id=agent_id,
            study_id=study_id,
            domain=domain,
            goal_achieved=(i % 5 != 0),
            episode_success=(i % 5 != 0),
        )
        r.timestamp = ts
        records.append(r)
    return records


def _write_jsonl(path: Path, records: list[EpisodeRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()) + "\n")


# ── 테스트 1: 등록 흐름 ───────────────────────────────────────────────


class TestEnrollmentFlow:
    def test_enrollment_flow(self, tmp_path: Path) -> None:
        """등록 → study_id 자동 발급 + SDK 설정 파일 생성."""
        enrollment = StudyClient.enroll(
            org_name="ACME Corp",
            agent_type="supply_chain_v2",
            domain="supply_chain",
            consent=True,
            study_base_dir=tmp_path,
        )

        assert isinstance(enrollment, StudyEnrollment)
        assert enrollment.study_id.startswith("HAW-")
        assert len(enrollment.study_id) == len("HAW-20260101-AAAAAA")
        assert enrollment.domain == "supply_chain"
        assert enrollment.agent_type == "supply_chain_v2"
        assert enrollment.consent is True

        # 익명화: org_name 원문이 저장되지 않아야 함
        assert "ACME" not in enrollment.org_hash
        assert len(enrollment.org_hash) == 16  # SHA256[:16]

        # haw_study_config.yaml 생성 확인
        config_path = tmp_path / "haw_study_config.yaml"
        assert config_path.exists(), "haw_study_config.yaml이 생성되어야 합니다"
        content = config_path.read_text(encoding="utf-8")
        assert enrollment.study_id in content
        assert "domain: supply_chain" in content

        # 등록 정보 JSON 저장 확인
        enroll_file = tmp_path / "enrollments" / f"{enrollment.study_id}.json"
        assert enroll_file.exists()
        saved = json.loads(enroll_file.read_text())
        assert saved["study_id"] == enrollment.study_id

    def test_enroll_requires_consent(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="consent"):
            StudyClient.enroll(
                org_name="ACME",
                agent_type="v1",
                domain="supply_chain",
                consent=False,
                study_base_dir=tmp_path,
            )

    def test_enroll_unique_study_ids(self, tmp_path: Path) -> None:
        e1 = StudyClient.enroll("OrgA", "v1", "supply_chain", study_base_dir=tmp_path / "a")
        e2 = StudyClient.enroll("OrgB", "v1", "supply_chain", study_base_dir=tmp_path / "b")
        assert e1.study_id != e2.study_id


# ── 테스트 2: 30일 로그 수집 파이프라인 ────────────────────────────────


class TestLogCollection30Days:
    def test_log_collection_30days(self, tmp_path: Path) -> None:
        """30일에 걸쳐 분산된 에피소드 로그를 집계한다."""
        log_dir = tmp_path / "logs"
        study_id = "HAW-TEST-30D"

        # 30일 치 에피소드를 JSONL로 기록
        for day in range(30):
            ts = datetime.now(UTC) - timedelta(days=29 - day)
            r = EpisodeRecord(
                agent_id="anon-001",
                study_id=study_id,
                domain="supply_chain",
                goal_achieved=True,
            )
            r.timestamp = ts.isoformat()
            _write_jsonl(log_dir / f"day_{day:02d}.jsonl", [r])

        pipeline = StudyLogPipeline(study_id=study_id, log_dir=log_dir)
        records = pipeline.aggregate_30day()

        assert len(records) == 30

    def test_completeness_validation_full(self, tmp_path: Path) -> None:
        """30일 모두 커버 → is_complete=True."""
        log_dir = tmp_path / "logs"
        study_id = "HAW-TEST-FULL"
        records = []
        for day in range(30):
            ts = datetime.now(UTC) - timedelta(days=29 - day)
            r = EpisodeRecord(agent_id="anon-001", study_id=study_id, domain="supply_chain")
            r.timestamp = ts.isoformat()
            records.append(r)
        _write_jsonl(log_dir / "all.jsonl", records)

        pipeline = StudyLogPipeline(study_id=study_id, log_dir=log_dir)
        result = pipeline.validate_completeness()

        assert result["n_records"] == 30
        assert result["coverage_pct"] >= 0.90
        assert result["is_complete"] is True

    def test_completeness_validation_partial(self, tmp_path: Path) -> None:
        """10일 누락 시 is_complete=False."""
        log_dir = tmp_path / "logs"
        study_id = "HAW-TEST-PARTIAL"
        records = []
        for day in range(20):  # 30일 중 20일만
            ts = datetime.now(UTC) - timedelta(days=29 - day)
            r = EpisodeRecord(agent_id="anon-001", study_id=study_id, domain="supply_chain")
            r.timestamp = ts.isoformat()
            records.append(r)
        _write_jsonl(log_dir / "partial.jsonl", records)

        pipeline = StudyLogPipeline(study_id=study_id, log_dir=log_dir)
        result = pipeline.validate_completeness()

        assert result["is_complete"] is False
        assert len(result["missing_days"]) >= 5

    def test_filters_other_study_episodes(self, tmp_path: Path) -> None:
        """다른 study_id의 에피소드는 제외한다."""
        log_dir = tmp_path / "logs"
        r_mine = EpisodeRecord(agent_id="anon-001", study_id="HAW-MINE", domain="supply_chain")
        r_other = EpisodeRecord(agent_id="anon-002", study_id="HAW-OTHER", domain="supply_chain")
        _write_jsonl(log_dir / "mixed.jsonl", [r_mine, r_other])

        pipeline = StudyLogPipeline(study_id="HAW-MINE", log_dir=log_dir)
        records = pipeline.aggregate_30day()

        assert len(records) == 1
        assert records[0].study_id == "HAW-MINE"


# ── 테스트 3: KPI 제출 ────────────────────────────────────────────────


class TestKPISubmission:
    def test_kpi_submission(self, tmp_path: Path) -> None:
        """KPI 제출 → JSON 파일 저장 확인."""
        with patch("hachillesworld.collect.flush.httpx.Client"):
            client = StudyClient(
                study_id="HAW-TEST-001",
                agent_id="anon-001",
                domain="supply_chain",
                api_key="haw-test",
                study_base_dir=tmp_path,
            )

        kpi_data = {
            "task_completion_rate": 0.87,
            "time_savings_pct": 23.5,
            "error_rate": 0.03,
            "cost_reduction_pct": 12.0,
            "csat_score": 4.2,
        }
        record = client.submit_kpi(kpi_data=kpi_data)
        client.close()

        assert record.study_id == "HAW-TEST-001"
        assert record.kpi_data["task_completion_rate"] == 0.87

        kpi_files = list((tmp_path / "kpi").glob("*.json"))
        assert len(kpi_files) == 1
        with kpi_files[0].open() as f:
            saved = json.load(f)
        assert saved["kpi_data"]["csat_score"] == 4.2
        assert saved["study_id"] == "HAW-TEST-001"

    def test_kpi_month_format(self, tmp_path: Path) -> None:
        """월 지정 KPI 제출이 올바른 파일명으로 저장된다."""
        with patch("hachillesworld.collect.flush.httpx.Client"):
            client = StudyClient(
                study_id="HAW-TEST-MONTH",
                agent_id="anon-001",
                domain="finance",
                api_key="haw-test",
                study_base_dir=tmp_path,
            )
        client.submit_kpi({"task_completion_rate": 0.9}, month="2026-07")
        client.submit_kpi({"task_completion_rate": 0.91}, month="2026-08")
        client.close()

        kpi_files = sorted((tmp_path / "kpi").glob("*.json"))
        assert len(kpi_files) == 2
        filenames = [f.name for f in kpi_files]
        assert any("2026-07" in n for n in filenames)
        assert any("2026-08" in n for n in filenames)


# ── 테스트 4: Spearman ρ 계산 ─────────────────────────────────────────


class TestCorrelationComputation:
    def test_correlation_computation(self) -> None:
        """단조 증가 데이터에서 높은 ρ를 반환한다."""
        import random

        rng = random.Random(42)
        has_scores = [rng.uniform(0.5, 0.9) for _ in range(15)]
        kpi_scores = [h * 100 + rng.gauss(0, 3) for h in has_scores]

        analyzer = HASBusinessCorrelation()
        result = analyzer.compute_spearman(has_scores, kpi_scores)

        assert isinstance(result, CorrelationResult)
        assert -1.0 <= result.rho <= 1.0
        assert 0.0 <= result.p_value <= 1.0
        assert result.n == 15
        assert result.rho > 0.5, "강한 양의 관계에서 ρ > 0.5 기대"

    def test_correlation_negative(self) -> None:
        """역관계 데이터에서 음의 ρ를 반환한다."""
        has_scores = [float(i) for i in range(1, 16)]
        kpi_scores = [float(16 - i) for i in range(1, 16)]

        analyzer = HASBusinessCorrelation()
        result = analyzer.compute_spearman(has_scores, kpi_scores)

        assert result.rho < -0.9
        assert result.p_value < 0.001

    def test_correlation_perfect_positive(self) -> None:
        """완전 양의 상관에서 ρ ≈ 1.0."""
        data = [float(i) for i in range(1, 11)]
        analyzer = HASBusinessCorrelation()
        result = analyzer.compute_spearman(data, data)

        assert abs(result.rho - 1.0) < 1e-9

    def test_h1_criterion(self) -> None:
        """H1 기준: ρ ≥ 0.60 and p < 0.01."""
        has_scores = [float(i) for i in range(1, 21)]
        kpi_scores = [float(i) + 0.1 * (i % 3) for i in range(1, 21)]

        analyzer = HASBusinessCorrelation()
        result = analyzer.compute_spearman(has_scores, kpi_scores)

        assert result.h1_passed is True
        assert result.significant is True

    def test_shapley_weights_sum_100(self) -> None:
        """Shapley 가중치 합계가 100%."""
        import random

        rng = random.Random(0)
        n = 10
        # 3개 지표만 사용 (2^3 = 8 부분집합, 빠름)
        has_data = [
            {
                "SDR": rng.uniform(0.6, 0.9),
                "PD": rng.uniform(0.5, 0.8),
                "SCR": rng.uniform(0.4, 0.7),
            }
            for _ in range(n)
        ]
        kpi_data = [sum(row.values()) / 3 + rng.gauss(0, 0.05) for row in has_data]

        analyzer = HASBusinessCorrelation()
        weights = analyzer.shapley_weights(has_data, kpi_data)

        assert set(weights.keys()) == {"SDR", "PD", "SCR"}
        assert abs(sum(weights.values()) - 100.0) < 0.01


# ── 테스트 5: 익명화 ─────────────────────────────────────────────────


class TestAnonymization:
    def test_anonymization(self, tmp_path: Path) -> None:
        """agent_id SHA256 익명화 및 민감 메타데이터 제거."""
        records = [
            EpisodeRecord(
                agent_id="real-agent-identifier",
                study_id="HAW-TEST-001",
                domain="supply_chain",
                metadata={
                    "org_name": "ACME Corp",
                    "user_id": "john@example.com",
                    "task_type": "reorder",  # 민감하지 않은 필드
                },
            )
        ]

        pipeline = StudyLogPipeline(study_id="HAW-TEST-001", log_dir=tmp_path)
        anonymized = pipeline.anonymize(records)

        assert len(anonymized) == 1
        r = anonymized[0]

        # agent_id가 SHA256으로 대체됨
        assert r.agent_id != "real-agent-identifier"
        assert len(r.agent_id) == 64  # SHA256 hex 길이

        # 민감 메타데이터 제거됨
        assert "org_name" not in r.metadata
        assert "user_id" not in r.metadata

        # 비민감 메타데이터 보존됨
        assert r.metadata.get("task_type") == "reorder"

    def test_anonymization_deterministic(self, tmp_path: Path) -> None:
        """동일 agent_id는 항상 동일 해시값을 반환한다."""
        records = [
            EpisodeRecord(agent_id="same-agent", study_id="HAW-TEST", domain="supply_chain")
            for _ in range(3)
        ]
        pipeline = StudyLogPipeline(study_id="HAW-TEST", log_dir=tmp_path)
        anonymized = pipeline.anonymize(records)

        hashes = [r.agent_id for r in anonymized]
        assert len(set(hashes)) == 1, "같은 agent_id는 항상 같은 해시"

    def test_anonymization_different_agents(self, tmp_path: Path) -> None:
        """다른 agent_id는 다른 해시값을 반환한다."""
        records = [
            EpisodeRecord(agent_id=f"agent-{i}", study_id="HAW-TEST", domain="supply_chain")
            for i in range(3)
        ]
        pipeline = StudyLogPipeline(study_id="HAW-TEST", log_dir=tmp_path)
        anonymized = pipeline.anonymize(records)

        hashes = [r.agent_id for r in anonymized]
        assert len(set(hashes)) == 3, "다른 agent_id는 다른 해시"
