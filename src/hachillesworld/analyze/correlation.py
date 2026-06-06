# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""HASBusinessCorrelation — HAS와 비즈니스 KPI 간 상관 분석.

H1: ρ(HAS, Q_composite) ≥ 0.60, p < 0.01
H2: 각 지표의 Shapley 가중치 재산출
H3: 도메인 통제 편상관계수
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations


@dataclass
class CorrelationResult:
    rho: float
    p_value: float
    n: int
    significant: bool
    h1_passed: bool

    def summary(self) -> str:
        sig = "[SIG]" if self.significant else "[N.S.]"
        h1 = "[PASS] H1 accepted" if self.h1_passed else "[FAIL] H1 rejected"
        return f"  Spearman ρ = {self.rho:.4f}  p = {self.p_value:.4f}  n = {self.n}  {sig}  {h1}"


@dataclass
class ShapleyResult:
    metric_names: list[str]
    shapley_values: list[float]
    relative_importance: list[float]  # 합이 100%

    def summary(self) -> str:
        lines = ["  지표별 Shapley 중요도:"]
        pairs = sorted(
            zip(self.metric_names, self.shapley_values, self.relative_importance, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        for name, sv, rel in pairs:
            bar = "#" * int(rel / 5)
            lines.append(f"  {name:8s} | {bar:<20s} {rel:5.1f}%  (phi={sv:.4f})")
        return "\n".join(lines)


@dataclass
class CorrelationReport:
    study_id: str
    n_agents: int
    spearman: CorrelationResult
    shapley: ShapleyResult
    ci_lower: float
    ci_upper: float
    generated_at: str

    def summary(self) -> str:
        lines = [
            f"HAW-STUDY 상관 분석 보고서 ({self.study_id})",
            f"  표본: n = {self.n_agents}",
            self.spearman.summary(),
            f"  95% CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}]",
        ]
        if self.shapley.metric_names:
            lines += ["", self.shapley.summary()]
        return "\n".join(lines)


class HASBusinessCorrelation:
    """HAS ↔ 비즈니스 KPI 상관 분석기.

    사용 예:
        analyzer = HASBusinessCorrelation()

        result = analyzer.compute_spearman(has_scores, kpi_scores)
        print(result.summary())

        weights = analyzer.shapley_weights(has_data_per_agent, kpi_scores)
        # {"SDR": 8.2, "PD": 15.1, ...}

        report = analyzer.generate_report("HAW-STUDY-001", has_scores, kpi_scores)
        print(report.summary())
    """

    HAS_METRICS: list[str] = [
        "SDR",
        "ECE",
        "PA",
        "ODR",
        "WMUL",
        "PD",
        "SCR",
        "CA",
        "GAR",
        "AS",
        "LCR",
        "HC",
        "HR",
        "IRT",
        "SU",
    ]

    def compute_spearman(
        self,
        has_series: list[float],
        kpi_series: list[float],
    ) -> CorrelationResult:
        """Spearman ρ(HAS, KPI) 산출."""
        rho, p_value = _spearman_rho(has_series, kpi_series)
        return CorrelationResult(
            rho=rho,
            p_value=p_value,
            n=len(has_series),
            significant=(p_value < 0.05),
            h1_passed=(rho >= 0.60 and p_value < 0.01),
        )

    def shapley_weights(
        self,
        has_data: list[dict[str, float]],
        kpi_data: list[float],
    ) -> dict[str, float]:
        """Shapley 가중치 재산출 (실제 데이터 기반).

        Args:
            has_data: 에이전트별 지표 점수 dict 리스트
                      [{"SDR": 0.8, "ECE": 0.7, ...}, ...]
            kpi_data: 에이전트별 비즈니스 KPI 스칼라 리스트

        Returns:
            지표명 → 상대적 중요도 (0~100%, 합계 100%)
        """
        if not has_data or not kpi_data:
            return {}
        feature_names = list(has_data[0].keys())
        features = [[row.get(k, 0.0) for k in feature_names] for row in has_data]
        result = _compute_shapley(features, kpi_data, feature_names)
        return dict(zip(result.metric_names, result.relative_importance, strict=False))

    def compute_partial_correlation(
        self,
        has_scores: list[float],
        kpi_scores: list[float],
        domains: list[str],
    ) -> CorrelationResult:
        """도메인을 통제변수로 한 편상관계수."""
        rho, p_value = _partial_correlation(has_scores, kpi_scores, domains)
        return CorrelationResult(
            rho=rho,
            p_value=p_value,
            n=len(has_scores),
            significant=(p_value < 0.05),
            h1_passed=(rho >= 0.60 and p_value < 0.01),
        )

    def generate_report(
        self,
        study_id: str,
        has_series: list[float],
        kpi_series: list[float],
        has_data: list[dict[str, float]] | None = None,
        n_bootstrap: int = 500,
    ) -> CorrelationReport:
        """1차 상관 분석 결과 자동 리포트 생성."""
        spearman = self.compute_spearman(has_series, kpi_series)
        _, ci_lower, ci_upper = _bootstrap_ci(has_series, kpi_series, n_bootstrap=n_bootstrap)

        if has_data:
            features = [[row.get(k, 0.0) for k in self.HAS_METRICS] for row in has_data]
            shapley = _compute_shapley(features, kpi_series, self.HAS_METRICS)
        else:
            shapley = ShapleyResult(metric_names=[], shapley_values=[], relative_importance=[])

        return CorrelationReport(
            study_id=study_id,
            n_agents=len(has_series),
            spearman=spearman,
            shapley=shapley,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            generated_at=datetime.now(UTC).isoformat(),
        )


# ── 내부 수학 함수 ─────────────────────────────────────────────────


def _spearman_rho(x: list[float], y: list[float]) -> tuple[float, float]:
    n = len(x)
    if len(y) != n or n < 3:
        raise ValueError(f"표본이 너무 적습니다 (n={n})")
    rho = _pearson(_rank(x), _rank(y))
    if abs(rho) >= 1.0:
        return rho, 0.0
    t_stat = rho * math.sqrt((n - 2) / (1 - rho**2))
    return rho, min(1.0, _t_pvalue(t_stat, df=n - 2))


def _rank(values: list[float]) -> list[float]:
    n = len(values)
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and sorted_vals[j + 1][1] == sorted_vals[i][1]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[sorted_vals[k][0]] = avg_rank
        i = j + 1
    return ranks


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=False))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    return 0.0 if sx == 0 or sy == 0 else cov / (sx * sy)


def _t_pvalue(t: float, df: int) -> float:
    x = df / (df + t * t)
    return _ibeta(x, df / 2.0, 0.5)


def _ibeta(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    cf = _betacf(x, a, b)
    return math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) * cf / a


def _betacf(x: float, a: float, b: float, max_iter: int = 100) -> float:
    fpmin = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = fpmin if abs(d) < fpmin else d
    h = d = 1.0 / d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = fpmin if abs(d) < fpmin else d
        c = 1.0 + aa / c
        c = fpmin if abs(c) < fpmin else c
        h *= (1.0 / d) * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = fpmin if abs(d) < fpmin else d
        c = 1.0 + aa / c
        c = fpmin if abs(c) < fpmin else c
        delta = (1.0 / d) * c
        h *= delta
        if abs(delta - 1.0) < 3e-7:
            break
    return h


def _compute_shapley(
    features: list[list[float]],
    outcomes: list[float],
    feature_names: list[str],
) -> ShapleyResult:
    n_features = len(features[0])
    normed = _z_normalize(features)
    shapley = [0.0] * n_features
    all_subsets = list(_all_subsets(n_features))
    for feat_idx in range(n_features):
        total = 0.0
        for subset in all_subsets:
            if feat_idx in subset:
                continue
            subset_with = tuple(sorted(subset + (feat_idx,)))
            val_with = _regression_r2(normed, outcomes, list(subset_with))
            val_without = _regression_r2(normed, outcomes, list(subset))
            k = len(subset)
            weight = (
                math.factorial(k) * math.factorial(n_features - k - 1) / math.factorial(n_features)
            )
            total += weight * (val_with - val_without)
        shapley[feat_idx] = total
    shapley = [max(0.0, s) for s in shapley]
    total_s = sum(shapley) or 1.0
    return ShapleyResult(
        metric_names=feature_names,
        shapley_values=shapley,
        relative_importance=[100.0 * s / total_s for s in shapley],
    )


def _all_subsets(n: int) -> Iterator[tuple[int, ...]]:
    for r in range(n):
        yield from combinations(range(n), r)
    yield tuple(range(n))


def _z_normalize(features: list[list[float]]) -> list[list[float]]:
    n_feat = len(features[0])
    result = [list(row) for row in features]
    for j in range(n_feat):
        col = [features[i][j] for i in range(len(features))]
        mu = sum(col) / len(col)
        sd = statistics.stdev(col) if len(col) > 1 else 1.0
        sd = sd or 1.0
        for i in range(len(features)):
            result[i][j] = (features[i][j] - mu) / sd
    return result


def _regression_r2(
    features: list[list[float]],
    outcomes: list[float],
    feat_indices: list[int],
) -> float:
    if not feat_indices:
        return 0.0
    n = len(features)
    X = [[features[i][j] for j in feat_indices] + [1.0] for i in range(n)]
    try:
        beta = _ols(X, outcomes)
        y_pred = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(n)]
        ss_res = sum((outcomes[i] - y_pred[i]) ** 2 for i in range(n))
        y_mean = sum(outcomes) / n
        ss_tot = sum((outcomes[i] - y_mean) ** 2 for i in range(n))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except Exception:
        return 0.0


def _ols(X: list[list[float]], y: list[float]) -> list[float]:
    n, p = len(X), len(X[0])
    XtX = [[sum(X[i][k] * X[i][j] for i in range(n)) for j in range(p)] for k in range(p)]
    Xty = [sum(X[i][k] * y[i] for i in range(n)) for k in range(p)]
    return _gauss(XtX, Xty)


def _gauss(A: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        if abs(M[col][col]) < 1e-12:
            continue
        for row in range(n):
            if row == col:
                continue
            f = M[row][col] / M[col][col]
            for j in range(col, n + 1):
                M[row][j] -= f * M[col][j]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def _partial_correlation(
    has_scores: list[float],
    outcomes: list[float],
    domains: list[str],
) -> tuple[float, float]:
    unique_domains = sorted(set(domains))
    if len(unique_domains) <= 1:
        return _spearman_rho(has_scores, outcomes)
    X = [
        [1.0 if domains[i] == d else 0.0 for d in unique_domains[:-1]] + [1.0]
        for i in range(len(has_scores))
    ]
    beta_has = _ols(X, has_scores)
    res_has = [
        has_scores[i] - sum(X[i][j] * beta_has[j] for j in range(len(beta_has)))
        for i in range(len(has_scores))
    ]
    beta_out = _ols(X, outcomes)
    res_out = [
        outcomes[i] - sum(X[i][j] * beta_out[j] for j in range(len(beta_out)))
        for i in range(len(outcomes))
    ]
    return _spearman_rho(res_has, res_out)


def _bootstrap_ci(
    has_scores: list[float],
    outcomes: list[float],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    import random

    rng = random.Random(seed)
    n = len(has_scores)
    rhos: list[float] = []
    for _ in range(n_bootstrap):
        idx = [rng.randint(0, n - 1) for _ in range(n)]
        try:
            rho, _ = _spearman_rho([has_scores[i] for i in idx], [outcomes[i] for i in idx])
            rhos.append(rho)
        except ValueError:
            pass
    if not rhos:
        return float("nan"), float("nan"), float("nan")
    rhos.sort()
    alpha = (1 - ci_level) / 2
    lo = int(alpha * len(rhos))
    hi = min(int((1 - alpha) * len(rhos)), len(rhos) - 1)
    return sum(rhos) / len(rhos), rhos[lo], rhos[hi]
