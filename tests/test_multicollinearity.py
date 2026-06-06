# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""tests/test_multicollinearity.py — Sprint 6-C: 다중공선성 분석 테스트."""

from __future__ import annotations

import random

import pytest

from hachillesworld.analyze.multicollinearity import (
    _HIGH_CORR_THRESHOLD,
    MulticollinearityAnalyzer,
)

# ── 공통 픽스처 ──────────────────────────────────────────────────────


def _make_metric_names(n: int = 15) -> list[str]:
    """n개 지표명 생성."""
    return [f"M{i:02d}" for i in range(n)]


def _make_independent_matrix(
    n_agents: int = 30, n_metrics: int = 15, seed: int = 0
) -> list[list[float]]:
    """무상관(독립) 지표 행렬 생성."""
    rng = random.Random(seed)
    return [[rng.uniform(0.0, 1.0) for _ in range(n_metrics)] for _ in range(n_agents)]


def _make_correlated_matrix(n_agents: int = 30, seed: int = 42) -> list[list[float]]:
    """3개 카테고리 내 고상관 구조를 가진 15지표 행렬 생성.

    M00~M04(WMQ), M05~M09(ALM), M10~M14(OHM) 각 범주 내
    지표들은 공통 신호를 공유해 |r| ≈ 0.9.
    """
    rng = random.Random(seed)
    matrix: list[list[float]] = []
    for _ in range(n_agents):
        wmq_base = rng.uniform(0.2, 0.9)
        alm_base = rng.uniform(0.2, 0.9)
        ohm_base = rng.uniform(0.2, 0.9)
        row: list[float] = [
            *[max(0.0, min(1.0, wmq_base + rng.gauss(0, 0.04))) for _ in range(5)],
            *[max(0.0, min(1.0, alm_base + rng.gauss(0, 0.04))) for _ in range(5)],
            *[max(0.0, min(1.0, ohm_base + rng.gauss(0, 0.04))) for _ in range(5)],
        ]
        matrix.append(row)
    return matrix


def _make_collinear_matrix(n_agents: int = 30, seed: int = 7) -> list[list[float]]:
    """완전 선형 종속 지표 포함 행렬: M02 = M00 + M01."""
    rng = random.Random(seed)
    matrix: list[list[float]] = []
    for _ in range(n_agents):
        m0 = rng.uniform(0.0, 0.5)
        m1 = rng.uniform(0.0, 0.5)
        m2 = m0 + m1  # 선형 종속
        m3 = rng.uniform(0.0, 1.0)
        m4 = rng.uniform(0.0, 1.0)
        matrix.append([m0, m1, m2, m3, m4])
    return matrix


# ── 테스트 ──────────────────────────────────────────────────────────


class TestCorrelationMatrixShape:
    def test_15x15_shape(self) -> None:
        """analyze() 결과 상관 행렬이 (15, 15)인지 확인."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(30, 15)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        assert len(report.correlation_matrix) == 15
        for row in report.correlation_matrix:
            assert len(row) == 15

    def test_diagonal_is_one(self) -> None:
        """대각 원소 = 1.0"""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(25, 15)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        for i in range(15):
            assert report.correlation_matrix[i][i] == pytest.approx(1.0, abs=1e-4)

    def test_symmetric(self) -> None:
        """상관 행렬은 대칭."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(25, 15, seed=3)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        for i in range(15):
            for j in range(15):
                assert report.correlation_matrix[i][j] == pytest.approx(
                    report.correlation_matrix[j][i], abs=1e-6
                )

    def test_smaller_matrix_shape(self) -> None:
        """3개 지표 → (3, 3) 행렬."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(20, 3)
        names = _make_metric_names(3)
        report = analyzer.analyze(matrix, names)

        assert len(report.correlation_matrix) == 3
        assert all(len(row) == 3 for row in report.correlation_matrix)


class TestHighCorrelationPairDetection:
    def test_detects_high_correlation(self) -> None:
        """|r| > 0.6인 고상관 쌍을 식별해야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_correlated_matrix(50)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        assert len(report.high_correlation_pairs) > 0

    def test_pair_structure(self) -> None:
        """각 쌍은 (지표A, 지표B, r) 형식."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_correlated_matrix(50)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        for pair in report.high_correlation_pairs:
            assert len(pair) == 3
            a, b, r = pair
            assert isinstance(a, str)
            assert isinstance(b, str)
            assert isinstance(r, float)
            assert abs(r) > _HIGH_CORR_THRESHOLD

    def test_no_self_pairs(self) -> None:
        """동일 지표 쌍은 포함되지 않아야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_correlated_matrix(40)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        for a, b, _ in report.high_correlation_pairs:
            assert a != b

    def test_independent_data_has_no_high_pairs(self) -> None:
        """무상관 데이터에서는 고상관 쌍이 드물어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(100, 15, seed=99)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        # 독립 데이터에서 우연히 |r|>0.6 쌍이 나올 수 있으나 드물어야 함
        assert len(report.high_correlation_pairs) < 10


class TestVIFComputation:
    def test_vif_positive(self) -> None:
        """VIF는 모두 양수여야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(30, 5)
        names = _make_metric_names(5)
        report = analyzer.analyze(matrix, names)

        for name, vif in report.vif_scores.items():
            assert vif > 0, f"{name}의 VIF가 양수가 아님: {vif}"

    def test_vif_dict_keys_match_names(self) -> None:
        """vif_scores의 키는 metric_names와 일치해야 한다."""
        analyzer = MulticollinearityAnalyzer()
        names = _make_metric_names(7)
        matrix = _make_independent_matrix(25, 7)
        report = analyzer.analyze(matrix, names)

        assert set(report.vif_scores.keys()) == set(names)

    def test_independent_vif_near_one(self) -> None:
        """독립 지표들의 VIF는 1에 가까워야 한다 (큰 n에서)."""
        analyzer = MulticollinearityAnalyzer()
        rng = random.Random(0)
        n_agents = 200
        n_metrics = 4
        # 진정한 독립 데이터
        matrix = [[rng.gauss(0, 1) for _ in range(n_metrics)] for _ in range(n_agents)]
        names = _make_metric_names(n_metrics)
        report = analyzer.analyze(matrix, names)

        for name, vif in report.vif_scores.items():
            assert vif < 5.0, f"{name}의 VIF가 너무 높음: {vif} (독립 데이터)"


class TestProblematicMetricsFlagged:
    def test_collinear_metric_flagged(self) -> None:
        """선형 종속 지표(M02 = M00 + M01)는 VIF > 10으로 표시되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_collinear_matrix(30)
        names = ["M00", "M01", "M02", "M03", "M04"]
        report = analyzer.analyze(matrix, names)

        # M00, M01, M02 중 적어도 하나가 problematic
        assert len(report.problematic_metrics) > 0

    def test_high_corr_causes_high_vif(self) -> None:
        """고상관 데이터는 VIF > 10 지표를 포함해야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_correlated_matrix(40)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        # 높은 상관 → 높은 VIF
        assert len(report.problematic_metrics) > 0

    def test_problematic_metrics_subset_of_names(self) -> None:
        """problematic_metrics는 metric_names의 부분집합이어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_correlated_matrix(40)
        names = _make_metric_names(15)
        report = analyzer.analyze(matrix, names)

        for m in report.problematic_metrics:
            assert m in names


class TestRecommendationGenerated:
    def test_recommendation_not_empty(self) -> None:
        """권고문은 항상 비어있지 않아야 한다."""
        analyzer = MulticollinearityAnalyzer()
        for matrix_fn in [
            lambda: _make_independent_matrix(30, 5),
            lambda: _make_correlated_matrix(30),
            lambda: _make_collinear_matrix(30),
        ]:
            matrix = matrix_fn()
            names = _make_metric_names(len(matrix[0]))
            report = analyzer.analyze(matrix, names)
            assert len(report.recommendation) > 0

    def test_no_problem_recommendation(self) -> None:
        """문제 없는 경우 '유지' 권고가 포함되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_independent_matrix(200, 3, seed=1)
        names = _make_metric_names(3)
        report = analyzer.analyze(matrix, names)

        if not report.problematic_metrics:
            assert "유지" in report.recommendation

    def test_problem_recommendation_mentions_pca(self) -> None:
        """VIF > 10 있을 때 권고문에 'PCA' 또는 '통합'이 포함되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        matrix = _make_collinear_matrix(30)
        names = ["M00", "M01", "M02", "M03", "M04"]
        report = analyzer.analyze(matrix, names)

        if report.problematic_metrics:
            assert "PCA" in report.recommendation or "통합" in report.recommendation


class TestMarkdownReportGeneration:
    def test_markdown_is_string(self) -> None:
        """generate_report_markdown()은 문자열을 반환해야 한다."""
        analyzer = MulticollinearityAnalyzer()
        report = analyzer.analyze(
            _make_independent_matrix(25, 5),
            _make_metric_names(5),
        )
        md = report.generate_report_markdown()
        assert isinstance(md, str)
        assert len(md) > 100

    def test_markdown_has_sections(self) -> None:
        """마크다운에 필수 섹션 헤더가 포함되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        report = analyzer.analyze(
            _make_correlated_matrix(30),
            _make_metric_names(15),
        )
        md = report.generate_report_markdown()

        assert "## 1. VIF" in md
        assert "## 2. 고상관" in md
        assert "## 3. Spearman" in md
        assert "## 4. 권고사항" in md

    def test_markdown_contains_metric_names(self) -> None:
        """마크다운에 지표 이름이 포함되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        names = ["SDR", "ECE", "PA"]
        report = analyzer.analyze(
            _make_independent_matrix(20, 3),
            names,
        )
        md = report.generate_report_markdown()

        for name in names:
            assert name in md

    def test_markdown_problematic_section(self) -> None:
        """VIF > 10 있을 때 문제 지표 상세 섹션이 포함되어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        report = analyzer.analyze(
            _make_collinear_matrix(30),
            ["M00", "M01", "M02", "M03", "M04"],
        )
        md = report.generate_report_markdown()

        if report.problematic_metrics:
            assert "문제 지표 상세" in md


class TestCleanDataNoIssues:
    def test_orthogonal_no_high_pairs(self) -> None:
        """직교(무상관) 데이터에서 고상관 쌍이 없어야 한다."""
        # 완전 직교 데이터 생성 (정사각 행렬 기반)
        n = 4
        matrix: list[list[float]] = []
        # 4개 직교 벡터 (각도 90도)
        for i in range(20):
            row = [
                1.0 if i % 4 == 0 else -1.0,
                1.0 if i % 4 == 1 else -1.0,
                1.0 if i % 4 == 2 else -1.0,
                1.0 if i % 4 == 3 else -1.0,
            ]
            # 노이즈 추가로 비완전 직교화
            rng = random.Random(i)
            row = [v + rng.gauss(0, 0.3) for v in row]
            matrix.append(row)

        analyzer = MulticollinearityAnalyzer()
        report = analyzer.analyze(matrix, _make_metric_names(n))

        # 약한 상관 → VIF 낮음
        for vif in report.vif_scores.values():
            assert vif < 20.0

    def test_independent_no_problematic(self) -> None:
        """n=100, n_metrics=3 독립 데이터 → problematic_metrics 없거나 드물어야 한다."""
        analyzer = MulticollinearityAnalyzer()
        rng = random.Random(555)
        # 진짜 독립 균등 분포
        matrix = [[rng.uniform(0.0, 1.0) for _ in range(3)] for _ in range(100)]
        report = analyzer.analyze(matrix, ["A", "B", "C"])

        # 독립 데이터에서 VIF > 10은 없어야 함
        assert report.problematic_metrics == []


class TestEdgeCases:
    def test_too_few_samples_raises(self) -> None:
        """n < 3 이면 ValueError를 발생시켜야 한다."""
        analyzer = MulticollinearityAnalyzer()
        with pytest.raises(ValueError, match="표본이 너무 적"):
            analyzer.analyze([[0.1, 0.2], [0.3, 0.4]], ["A", "B"])

    def test_mismatched_names_raises(self) -> None:
        """metric_names 수와 열 수가 다르면 ValueError."""
        analyzer = MulticollinearityAnalyzer()
        with pytest.raises(ValueError, match="불일치"):
            analyzer.analyze([[0.1, 0.2, 0.3]] * 10, ["A", "B"])

    def test_single_metric(self) -> None:
        """지표 1개 → VIF = 1.0, 고상관 쌍 없음."""
        analyzer = MulticollinearityAnalyzer()
        matrix = [[float(i) / 10] for i in range(20)]
        report = analyzer.analyze(matrix, ["SOLO"])

        assert report.vif_scores["SOLO"] == pytest.approx(1.0, abs=1e-3)
        assert report.high_correlation_pairs == []
        assert report.problematic_metrics == []
