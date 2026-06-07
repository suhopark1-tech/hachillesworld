"""Sprint 4-B: HAW-STUDY-001 완료 + 실증 분석 테스트."""

from __future__ import annotations

import math

import pytest

from hachillesworld.analyze.study_analysis import (
    H1Result,
    ShapleyWeights,
    StudyAnalyzer,
    StudyDataset,
    SubgroupResult,
    _generate_synthetic_n25,
)
from hachillesworld.core.config import HAS_WEIGHTS, reset_has_weights

# ── 픽스처 ────────────────────────────────────────────────────────────


@pytest.fixture
def analyzer() -> StudyAnalyzer:
    return StudyAnalyzer()


@pytest.fixture
def synthetic_dataset(analyzer: StudyAnalyzer) -> StudyDataset:
    return analyzer.load_study_data("HAW-STUDY-001", study_base_dir="nonexistent_path")


@pytest.fixture(autouse=True)
def restore_has_weights():
    """각 테스트 후 HAS_WEIGHTS를 기본값으로 복원."""
    yield
    reset_has_weights()


# ── 테스트 1: 데이터 로드 ─────────────────────────────────────────────


class TestLoadStudyData:
    def test_synthetic_fallback_when_no_real_data(self, analyzer: StudyAnalyzer, tmp_path) -> None:
        """실제 데이터 없으면 합성 n=25 데이터로 대체된다."""
        dataset = analyzer.load_study_data("HAW-TEST", study_base_dir=tmp_path)
        assert dataset.data_source == "synthetic"
        assert dataset.n == 25

    def test_dataset_has_5_domains(self, synthetic_dataset: StudyDataset) -> None:
        """합성 데이터는 5개 도메인을 포함한다."""
        assert len(synthetic_dataset.domains) == 5
        expected = {
            "supply_chain",
            "customer_service",
            "code_generation",
            "finance",
            "healthcare",
        }
        assert set(synthetic_dataset.domains) == expected

    def test_all_records_have_valid_scores(self, synthetic_dataset: StudyDataset) -> None:
        """모든 레코드의 점수가 유효 범위에 있다."""
        for r in synthetic_dataset.records:
            assert 0 <= r.has_score <= 100, f"HAS out of range: {r.has_score}"
            assert 0 <= r.kpi_composite <= 1, f"KPI out of range: {r.kpi_composite}"
            assert 0 <= r.wmq_score <= 100
            assert 0 <= r.alm_score <= 100
            assert 0 <= r.ohm_score <= 100

    def test_dataset_n_equals_records_len(self, synthetic_dataset: StudyDataset) -> None:
        assert synthetic_dataset.n == len(synthetic_dataset.records)

    def test_category_vector_3_dim(self, synthetic_dataset: StudyDataset) -> None:
        """category_vector는 [wmq, alm, ohm] 3차원."""
        for r in synthetic_dataset.records:
            v = r.category_vector
            assert len(v) == 3
            assert v[0] == r.wmq_score
            assert v[1] == r.alm_score
            assert v[2] == r.ohm_score


# ── 테스트 2: H1 가설 검증 ────────────────────────────────────────────


class TestComputeH1Hypothesis:
    def test_h1_hypothesis_passes(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """합성 데이터에서 H1 (ρ ≥ 0.60, p < 0.01) 통과."""
        result = analyzer.compute_h1_hypothesis(synthetic_dataset, n_bootstrap=200)

        assert isinstance(result, H1Result)
        assert result.h1_passed, f"H1 미통과: ρ = {result.rho:.4f}, p = {result.p_value:.4f}"
        assert result.rho >= 0.60
        assert result.p_value < 0.01

    def test_n_matches_dataset(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        result = analyzer.compute_h1_hypothesis(synthetic_dataset, n_bootstrap=100)
        assert result.n == synthetic_dataset.n

    def test_bonferroni_correction_applied(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """Bonferroni 보정 p = p_value × n_domains."""
        result = analyzer.compute_h1_hypothesis(synthetic_dataset, n_bootstrap=100)
        expected_bonferroni = min(1.0, result.p_value * result.n_tests)
        assert abs(result.bonferroni_corrected_p - expected_bonferroni) < 1e-8

    def test_ci_is_valid(self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset) -> None:
        """95% CI가 ρ를 포함한다."""
        result = analyzer.compute_h1_hypothesis(synthetic_dataset, n_bootstrap=300)
        if not math.isnan(result.ci_lower):
            assert result.ci_lower <= result.rho
            assert result.rho <= result.ci_upper


# ── 테스트 3: Shapley 가중치 재산출 ─────────────────────────────────


class TestShapleyRecalibration:
    def test_weights_sum_to_one(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """재산출된 가중치 합계 = 1.0."""
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        assert abs(weights.wmq + weights.alm + weights.ohm - 1.0) < 1e-4

    def test_all_weights_positive(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        assert weights.wmq > 0
        assert weights.alm > 0
        assert weights.ohm > 0

    def test_metric_weights_present(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """15개 지표의 중요도가 포함된다."""
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        assert len(weights.metric_weights) == 15

    def test_source_is_synthetic(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        assert weights.source == "synthetic"

    def test_n_agents_recorded(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        assert weights.n_agents == 25


# ── 테스트 4: 도메인 부분 집단 분석 ──────────────────────────────────


class TestDomainSubgroupAnalysis:
    def test_all_domains_covered(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """5개 도메인 모두 분석된다."""
        result = analyzer.domain_subgroup_analysis(synthetic_dataset)
        assert isinstance(result, SubgroupResult)
        assert len(result.domain_results) == 5

    def test_n_per_domain_is_5(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """각 도메인당 5명의 에이전트."""
        result = analyzer.domain_subgroup_analysis(synthetic_dataset)
        for domain, n in result.n_per_domain.items():
            assert n == 5, f"{domain}: n={n} ≠ 5"

    def test_rho_in_valid_range(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """각 도메인의 ρ는 [-1, 1] 범위."""
        result = analyzer.domain_subgroup_analysis(synthetic_dataset)
        for domain, cr in result.domain_results.items():
            assert -1.0 <= cr.rho <= 1.0, f"{domain}: ρ = {cr.rho}"

    def test_summary_contains_all_domains(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        result = analyzer.domain_subgroup_analysis(synthetic_dataset)
        summary = result.summary()
        for domain in [
            "supply_chain",
            "customer_service",
            "code_generation",
            "finance",
            "healthcare",
        ]:
            assert domain in summary


# ── 테스트 5: SDK 가중치 업데이트 ─────────────────────────────────────


class TestSDKWeightUpdate:
    def test_sdk_weight_update_applies(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """sdk_weight_update() 후 HAS_WEIGHTS가 갱신된다."""
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        analyzer.sdk_weight_update(weights)

        assert abs(HAS_WEIGHTS["wmq"] - weights.wmq) < 1e-9
        assert abs(HAS_WEIGHTS["alm"] - weights.alm) < 1e-9
        assert abs(HAS_WEIGHTS["ohm"] - weights.ohm) < 1e-9

    def test_composite_score_uses_updated_weights(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """가중치 업데이트 후 composite_score가 새 가중치를 사용한다."""
        from hachillesworld.core.models import CategoryScore, DiagnosticReport, LawsDomain, Level

        # 카테고리 점수가 다른 리포트 생성
        report = DiagnosticReport(
            agent_name="test",
            level=Level.L2,
            level_progress=0.5,
            laws_domain=LawsDomain.DIGITAL,
            world_model_quality=CategoryScore(name="WMQ", score=80.0),
            agency_level=CategoryScore(name="ALM", score=70.0),
            operational_health=CategoryScore(name="OHM", score=60.0),
        )

        # v2.1 기본 가중치로 계산: 80*0.45 + 70*0.35 + 60*0.20 = 36 + 24.5 + 12 = 72.5
        score_before = report.composite_score
        assert abs(score_before - 72.5) < 0.01

        # 가중치 업데이트 (wmq 유지, ohm→alm 이동)
        new_w = ShapleyWeights(wmq=0.45, alm=0.40, ohm=0.15, study_id="test", n_agents=25)
        analyzer.sdk_weight_update(new_w)

        # 새 가중치: 80*0.45 + 70*0.40 + 60*0.15 = 36 + 28 + 9 = 73.0
        score_after = report.composite_score
        assert abs(score_after - 73.0) < 0.01
        assert score_after != score_before

    def test_invalid_weights_rejected(self, analyzer: StudyAnalyzer) -> None:
        """합계 ≠ 1.0인 가중치는 ValueError."""
        bad_weights = ShapleyWeights(wmq=0.50, alm=0.35, ohm=0.30)  # sum=1.15
        with pytest.raises(ValueError, match="합계"):
            analyzer.sdk_weight_update(bad_weights)

    def test_reset_restores_defaults(
        self, analyzer: StudyAnalyzer, synthetic_dataset: StudyDataset
    ) -> None:
        """reset_has_weights() 호출 시 기본값으로 복원된다."""
        weights = analyzer.shapley_recalibration(synthetic_dataset)
        analyzer.sdk_weight_update(weights)

        reset_has_weights()

        # v2.1 기본값: HAW-STUDY-001 실증 결과 반영 (0.45/0.35/0.20)
        assert abs(HAS_WEIGHTS["wmq"] - 0.45) < 1e-9
        assert abs(HAS_WEIGHTS["alm"] - 0.35) < 1e-9
        assert abs(HAS_WEIGHTS["ohm"] - 0.20) < 1e-9


# ── 테스트 6: 합성 데이터 재현성 ─────────────────────────────────────


class TestSyntheticDataReproducibility:
    def test_same_seed_gives_same_data(self) -> None:
        """동일 seed는 항상 같은 데이터를 생성한다."""
        records1 = _generate_synthetic_n25(seed=42)
        records2 = _generate_synthetic_n25(seed=42)
        assert len(records1) == len(records2)
        for r1, r2 in zip(records1, records2):
            assert r1.has_score == r2.has_score
            assert r1.kpi_composite == r2.kpi_composite

    def test_different_seeds_give_different_data(self) -> None:
        records1 = _generate_synthetic_n25(seed=42)
        records2 = _generate_synthetic_n25(seed=99)
        has1 = [r.has_score for r in records1]
        has2 = [r.has_score for r in records2]
        assert has1 != has2

    def test_n_equals_25(self) -> None:
        records = _generate_synthetic_n25()
        assert len(records) == 25
