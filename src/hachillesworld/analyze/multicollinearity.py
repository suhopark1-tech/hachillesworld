# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""HAchillesWorld — 다중공선성 분석 모듈 (Sprint 6-C, A-3)

HAS 15개 지표 간 Spearman 상관·VIF를 산출해
가중치의 통계적 근거를 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations

from hachillesworld.analyze.correlation import (
    _regression_r2,
    _spearman_rho,
)

_HIGH_CORR_THRESHOLD: float = 0.6
_HIGH_VIF_THRESHOLD: float = 10.0


@dataclass
class MulticollinearityReport:
    """다중공선성 분석 결과."""

    metric_names: list[str]
    correlation_matrix: list[list[float]]
    vif_scores: dict[str, float]
    high_correlation_pairs: list[tuple[str, str, float]]
    recommendation: str
    problematic_metrics: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def generate_report_markdown(self) -> str:
        """분석 결과 마크다운 보고서 자동 생성."""
        n = len(self.metric_names)
        lines: list[str] = [
            "# 다중공선성 분석 보고서",
            "",
            f"- **생성일**: {self.generated_at}",
            f"- **분석 지표 수**: {n}개",
            f"- **고상관 쌍 수** (|r| > {_HIGH_CORR_THRESHOLD}):"
            f" {len(self.high_correlation_pairs)}개",
            f"- **문제 지표 수** (VIF > {_HIGH_VIF_THRESHOLD}): {len(self.problematic_metrics)}개",
            "",
            "---",
            "",
            "## 1. VIF (분산팽창인수)",
            "",
            "| 지표 | VIF | 평가 |",
            "| :--- | ---: | :--- |",
        ]
        for name, vif in sorted(self.vif_scores.items(), key=lambda x: -x[1]):
            vif_str = "∞" if vif == float("inf") else f"{vif:.2f}"
            if vif == float("inf"):
                status = "⛔ 완전 공선성"
            elif vif > _HIGH_VIF_THRESHOLD:
                status = "⚠️ 문제"
            else:
                status = "✅ 정상"
            lines.append(f"| {name} | {vif_str} | {status} |")

        lines += [
            "",
            "---",
            "",
            "## 2. 고상관 지표 쌍 (|r| > 0.6)",
            "",
        ]
        if self.high_correlation_pairs:
            lines += ["| 지표 A | 지표 B | Spearman r |", "| :--- | :--- | ---: |"]
            for a, b, r in sorted(self.high_correlation_pairs, key=lambda x: -abs(x[2])):
                lines.append(f"| {a} | {b} | {r:+.4f} |")
        else:
            lines.append("> 고상관 지표 쌍 없음")

        lines += [
            "",
            "---",
            "",
            "## 3. Spearman 상관 행렬",
            "",
        ]
        header = "| 지표 | " + " | ".join(self.metric_names) + " |"
        sep = "|:---|" + "|".join(" :---: " for _ in self.metric_names) + "|"
        lines += [header, sep]
        for i, name in enumerate(self.metric_names):
            row_str = " | ".join(f"{self.correlation_matrix[i][j]:+.2f}" for j in range(n))
            lines.append(f"| **{name}** | {row_str} |")

        lines += [
            "",
            "---",
            "",
            "## 4. 권고사항",
            "",
            self.recommendation,
        ]
        if self.problematic_metrics:
            lines += [
                "",
                "### 문제 지표 상세",
                "",
                "| 지표 | 조치 권고 |",
                "| :--- | :--- |",
            ]
            for m in self.problematic_metrics:
                lines.append(f"| {m} | PCA 통합 또는 대표 지표 1개 선택 검토 |")
        return "\n".join(lines)


class MulticollinearityAnalyzer:
    """HAS 15개 지표 다중공선성 분석기.

    사용 예:
        analyzer = MulticollinearityAnalyzer()
        # metric_matrix: shape (n_agents, n_metrics)
        report = analyzer.analyze(metric_matrix, metric_names)
        print(report.generate_report_markdown())
    """

    HIGH_CORR_THRESHOLD: float = _HIGH_CORR_THRESHOLD
    HIGH_VIF_THRESHOLD: float = _HIGH_VIF_THRESHOLD

    def analyze(
        self,
        metric_matrix: list[list[float]],
        metric_names: list[str],
    ) -> MulticollinearityReport:
        """다중공선성 분석 실행.

        Args:
            metric_matrix: (n_agents, n_metrics) 형태의 지표 점수 행렬
            metric_names: 열 이름 (지표 코드 목록)

        Returns:
            MulticollinearityReport
        """
        n_samples = len(metric_matrix)
        n_metrics = len(metric_names)

        if n_samples < 3:
            msg = f"표본이 너무 적습니다 (n={n_samples}, 최소 3 필요)"
            raise ValueError(msg)
        if not metric_matrix or len(metric_matrix[0]) != n_metrics:
            actual = len(metric_matrix[0]) if metric_matrix else 0
            msg = f"metric_matrix 열 수({actual})와 metric_names 수({n_metrics})가 불일치"
            raise ValueError(msg)

        corr_matrix = self._compute_correlation_matrix(metric_matrix, n_metrics)
        vif_values = self._compute_vif(metric_matrix, n_metrics)
        vif_scores = dict(zip(metric_names, vif_values, strict=False))

        high_pairs: list[tuple[str, str, float]] = [
            (metric_names[i], metric_names[j], corr_matrix[i][j])
            for i, j in combinations(range(n_metrics), 2)
            if abs(corr_matrix[i][j]) > self.HIGH_CORR_THRESHOLD
        ]

        problematic = [name for name, vif in vif_scores.items() if vif > self.HIGH_VIF_THRESHOLD]

        return MulticollinearityReport(
            metric_names=metric_names,
            correlation_matrix=corr_matrix,
            vif_scores=vif_scores,
            high_correlation_pairs=high_pairs,
            recommendation=self._recommend(vif_scores),
            problematic_metrics=problematic,
        )

    def _compute_correlation_matrix(
        self,
        metric_matrix: list[list[float]],
        n_metrics: int,
    ) -> list[list[float]]:
        """Spearman 상관 행렬 계산 (모든 지표 쌍)."""
        corr: list[list[float]] = [[0.0] * n_metrics for _ in range(n_metrics)]
        for i in range(n_metrics):
            corr[i][i] = 1.0
        for i, j in combinations(range(n_metrics), 2):
            col_i = [row[i] for row in metric_matrix]
            col_j = [row[j] for row in metric_matrix]
            try:
                rho, _ = _spearman_rho(col_i, col_j)
            except (ValueError, ZeroDivisionError):
                rho = 0.0
            corr[i][j] = round(rho, 4)
            corr[j][i] = round(rho, 4)
        return corr

    def _compute_vif(
        self,
        metric_matrix: list[list[float]],
        n_metrics: int,
    ) -> list[float]:
        """VIF 계산: VIF_i = 1 / (1 - R²_i).

        R²_i: i번째 지표를 나머지 지표로 OLS 회귀한 결정계수.
        """
        vifs: list[float] = []
        for i in range(n_metrics):
            feat_indices = [j for j in range(n_metrics) if j != i]
            if not feat_indices:
                vifs.append(1.0)
                continue
            y_i = [row[i] for row in metric_matrix]
            r2 = _regression_r2(metric_matrix, y_i, feat_indices)
            r2 = max(0.0, min(r2, 1.0 - 1e-10))
            vifs.append(round(1.0 / (1.0 - r2), 4))
        return vifs

    def _recommend(self, vif_scores: dict[str, float]) -> str:
        """VIF 기반 권고사항 자동 생성."""
        problematic = [name for name, vif in vif_scores.items() if vif > self.HIGH_VIF_THRESHOLD]
        if not problematic:
            return "모든 지표의 VIF < 10: 다중공선성 문제 없음. 현재 15개 지표 체계를 유지한다."
        names_str = ", ".join(problematic)
        return (
            f"다음 지표에서 VIF > 10이 확인됨: **{names_str}**. "
            "PCA 또는 지표 통합 검토 필요. "
            "고상관 쌍 중 대표 지표만 선택하거나 "
            "Owen value 기반 연합 Shapley로 가중치를 재산출할 것을 권고한다. "
            "단, 카테고리(WMQ·ALM·OHM) 레벨 집계 후에는 공선성이 해소되므로 "
            "현행 3범주 HAS 가중치 산출에는 즉각적 영향이 없다."
        )
