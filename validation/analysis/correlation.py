"""HAchillesWorld — 횡단 타당도 분석 모듈

H1: ρ(HAS, Q_composite) ≥ 0.60, p < 0.01
H2: 각 지표의 Shapley 값 계산
H3: 도메인별 편상관계수
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from itertools import combinations


@dataclass
class CorrelationResult:
    rho: float  # Spearman 순위 상관계수
    p_value: float  # p-값 (근사)
    n: int  # 표본 크기
    significant: bool  # p < 0.05 여부
    h1_passed: bool  # ρ ≥ 0.60 and p < 0.01

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


# ──────────────────────────────────────────────
# Spearman 순위 상관계수 계산
# ──────────────────────────────────────────────


def spearman_rho(x: list[float], y: list[float]) -> tuple[float, float]:
    """Spearman 순위 상관계수 및 근사 p-값 계산.

    Returns:
        (rho, p_value)

    """
    n = len(x)
    assert len(y) == n and n >= 3, f"표본이 너무 적습니다 (n={n})"

    rx = _rank(x)
    ry = _rank(y)

    # Pearson r on ranks
    rho = _pearson(rx, ry)

    # t-통계량 근사 (n >= 10 권장)
    if abs(rho) >= 1.0:
        p_value = 0.0
    else:
        t_stat = rho * math.sqrt((n - 2) / (1 - rho**2))
        # Student t 분포 (df = n-2) 양측 p-값 근사
        p_value = _t_pvalue(t_stat, df=n - 2)

    return rho, p_value


def _rank(values: list[float]) -> list[float]:
    """평균 순위 계산 (동점 처리 포함)"""
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
    """Pearson 상관계수"""
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=False))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)


def _t_pvalue(t: float, df: int) -> float:
    """Student t 분포 양측 p-값 (수치 근사, SciPy 불필요)"""
    # Abramowitz & Stegun 근사
    x = df / (df + t * t)
    # 불완전 베타 함수 근사 (간단한 연속 분수 방법)
    p = _ibeta(x, df / 2, 0.5)
    return min(1.0, p)


def _ibeta(x: float, a: float, b: float) -> float:
    """불완전 베타 함수 정규화 근사 (Lanczos 방법의 간소화)"""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # 로그 베타 함수 계산
    lbeta = _lgamma(a) + _lgamma(b) - _lgamma(a + b)
    # 연속 분수 근사
    cf = _betacf(x, a, b)
    return math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) * cf / a


def _betacf(x: float, a: float, b: float, max_iter: int = 100) -> float:
    """불완전 베타 함수용 연속 분수 (Lentz 알고리즘)"""
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = fpmin if abs(d) < fpmin else d
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = fpmin if abs(d) < fpmin else d
        c = 1.0 + aa / c
        c = fpmin if abs(c) < fpmin else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = fpmin if abs(d) < fpmin else d
        c = 1.0 + aa / c
        c = fpmin if abs(c) < fpmin else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-7:
            break
    return h


def _lgamma(x: float) -> float:
    """로그 감마 함수 (Stirling 근사)"""
    return math.lgamma(x)


# ──────────────────────────────────────────────
# Shapley 값 계산 (특성 중요도)
# ──────────────────────────────────────────────


def compute_shapley_values(
    features: list[list[float]],  # shape: [n_agents, n_features]
    outcomes: list[float],  # shape: [n_agents]
    feature_names: list[str],
) -> ShapleyResult:
    """선형 회귀 기반 Shapley 값 근사.
    각 특성이 outcome 예측에 기여하는 평균 기여도를 계산.

    정확한 Shapley 값은 지수 시간이 필요하므로,
    순열 샘플링 방식으로 근사 (n_features ≤ 15에서 정확).
    """
    n_features = len(features[0])
    assert len(feature_names) == n_features

    # 각 특성을 z-점수 정규화
    normed = _z_normalize(features)

    # 순열 기반 Shapley 근사
    shapley = [0.0] * n_features

    # 모든 부분집합에 대해 marginal contribution 계산
    # n_features = 15이면 2^15 = 32768 → 완전 열거 가능
    all_subsets = list(_all_subsets(n_features))

    for feat_idx in range(n_features):
        marginal_total = 0.0
        count = 0
        for subset in all_subsets:
            if feat_idx in subset:
                continue
            subset_with = tuple(sorted(subset + (feat_idx,)))
            subset_without = subset
            val_with = _regression_r2(normed, outcomes, list(subset_with))
            val_without = _regression_r2(normed, outcomes, list(subset_without))
            weight = _shapley_weight(n_features, len(subset))
            marginal_total += weight * (val_with - val_without)
            count += 1
        shapley[feat_idx] = marginal_total

    # 음수 보정 및 상대적 중요도 계산
    shapley = [max(0.0, s) for s in shapley]
    total = sum(shapley) or 1.0
    relative = [100.0 * s / total for s in shapley]

    return ShapleyResult(
        metric_names=feature_names,
        shapley_values=shapley,
        relative_importance=relative,
    )


def _all_subsets(n: int):
    """0..n-1 원소의 모든 부분집합 생성 (빈 집합 포함)"""
    for r in range(n):
        for combo in combinations(range(n), r):
            yield combo
    yield tuple(range(n))  # 전체 집합


def _shapley_weight(n: int, subset_size: int) -> float:
    """Shapley 가중치: |S|! (n-|S|-1)! / n!"""
    from math import factorial

    k = subset_size
    return factorial(k) * factorial(n - k - 1) / factorial(n)


def _z_normalize(features: list[list[float]]) -> list[list[float]]:
    n_feat = len(features[0])
    result = [list(row) for row in features]
    for j in range(n_feat):
        col = [features[i][j] for i in range(len(features))]
        mu = sum(col) / len(col)
        sd = statistics.stdev(col) if len(col) > 1 else 1.0
        if sd == 0:
            sd = 1.0
        for i in range(len(features)):
            result[i][j] = (features[i][j] - mu) / sd
    return result


def _regression_r2(
    features: list[list[float]],
    outcomes: list[float],
    feat_indices: list[int],
) -> float:
    """지정된 특성만 사용한 OLS 회귀의 R² 반환"""
    if not feat_indices:
        return 0.0

    n = len(features)
    X = [[features[i][j] for j in feat_indices] + [1.0] for i in range(n)]
    y = outcomes

    # 정규 방정식 (X^T X)^{-1} X^T y
    try:
        beta = _ols(X, y)
        y_pred = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        y_mean = sum(y) / n
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except Exception:
        return 0.0


def _ols(X: list[list[float]], y: list[float]) -> list[float]:
    """최소제곱법 (정규 방정식) — 소규모 행렬용"""
    n = len(X)
    p = len(X[0])
    # X^T X
    XtX = [[sum(X[i][k] * X[i][j] for i in range(n)) for j in range(p)] for k in range(p)]
    # X^T y
    Xty = [sum(X[i][k] * y[i] for i in range(n)) for k in range(p)]
    # 가우스 소거법
    return _gauss_elimination(XtX, Xty)


def _gauss_elimination(A: list[list[float]], b: list[float]) -> list[float]:
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
            factor = M[row][col] / M[col][col]
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


# ──────────────────────────────────────────────
# 도메인별 편상관계수
# ──────────────────────────────────────────────


def partial_correlation_controlling_domain(
    has_scores: list[float],
    outcomes: list[float],
    domains: list[str],
) -> tuple[float, float]:
    """도메인을 통제변수로 한 HAS-성과 편상관계수 계산.

    Returns:
        (partial_rho, p_value)

    """
    unique_domains = sorted(set(domains))
    n_domains = len(unique_domains)

    if n_domains <= 1:
        return spearman_rho(has_scores, outcomes)

    # 도메인 더미 변수 생성
    domain_dummies = [
        [1.0 if domains[i] == d else 0.0 for d in unique_domains[:-1]] for i in range(len(domains))
    ]

    # HAS의 도메인 잔차
    X_has = [
        [domain_dummies[i][j] for j in range(n_domains - 1)] + [1.0] for i in range(len(has_scores))
    ]
    beta_has = _ols(X_has, has_scores)
    res_has = [
        has_scores[i] - sum(X_has[i][j] * beta_has[j] for j in range(len(beta_has)))
        for i in range(len(has_scores))
    ]

    # 성과의 도메인 잔차
    X_out = X_has
    beta_out = _ols(X_out, outcomes)
    res_out = [
        outcomes[i] - sum(X_out[i][j] * beta_out[j] for j in range(len(beta_out)))
        for i in range(len(outcomes))
    ]

    return spearman_rho(res_has, res_out)


# ──────────────────────────────────────────────
# 부트스트랩 신뢰구간
# ──────────────────────────────────────────────


def bootstrap_ci(
    has_scores: list[float],
    outcomes: list[float],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """부트스트랩으로 Spearman ρ의 신뢰구간 계산.

    Returns:
        (rho_mean, ci_lower, ci_upper)

    """
    import random

    rng = random.Random(seed)
    n = len(has_scores)
    bootstrap_rhos = []

    for _ in range(n_bootstrap):
        indices = [rng.randint(0, n - 1) for _ in range(n)]
        boot_has = [has_scores[i] for i in indices]
        boot_out = [outcomes[i] for i in indices]
        try:
            rho, _ = spearman_rho(boot_has, boot_out)
            bootstrap_rhos.append(rho)
        except Exception:
            pass

    if not bootstrap_rhos:
        return float("nan"), float("nan"), float("nan")

    bootstrap_rhos.sort()
    alpha = (1 - ci_level) / 2
    lower_idx = int(alpha * len(bootstrap_rhos))
    upper_idx = int((1 - alpha) * len(bootstrap_rhos))
    return (
        sum(bootstrap_rhos) / len(bootstrap_rhos),
        bootstrap_rhos[lower_idx],
        bootstrap_rhos[min(upper_idx, len(bootstrap_rhos) - 1)],
    )
