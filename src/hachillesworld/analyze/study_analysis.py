# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""HAW-STUDY-001 실증 연구 분석 모듈.

StudyAnalyzer 클래스로 다음을 수행한다:
  - n ≥ 25 수집 데이터 로드 (없으면 합성 데이터 생성)
  - H1 가설 검증: ρ(HAS, Q_실제) ≥ 0.60, p < 0.01
  - Shapley 가중치 재산출 (3범주 카테고리 레벨)
  - 도메인별 부분 집단 분석
  - SDK HAS 계산 가중치 업데이트
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hachillesworld.analyze.correlation import (
    CorrelationResult,
    HASBusinessCorrelation,
    _bootstrap_ci,
    _compute_shapley,
    _spearman_rho,
)


# ── 도메인 상수 ─────────────────────────────────────────────────────

STUDY_DOMAINS = [
    "supply_chain",
    "customer_service",
    "code_generation",
    "finance",
    "healthcare",
]

# 15개 HAS 지표 (WMQ 5개 + ALM 5개 + OHM 5개)
WMQ_METRICS = ["SDR", "ECE", "PA", "ODR", "WMUL"]
ALM_METRICS = ["PD", "SCR", "CA", "GAR", "AS"]
OHM_METRICS = ["LCR", "HC", "HR", "IRT", "SU"]
ALL_METRICS = WMQ_METRICS + ALM_METRICS + OHM_METRICS


# ── 데이터 모델 ─────────────────────────────────────────────────────


@dataclass
class AgentRecord:
    """HAW-STUDY-001 단일 에이전트 관측 레코드."""

    agent_id: str            # SHA256 익명화 해시 [:16]
    domain: str
    has_score: float         # 종합 HAS [0, 100]
    wmq_score: float         # WMQ 카테고리 점수 [0, 100]
    alm_score: float         # ALM 카테고리 점수 [0, 100]
    ohm_score: float         # OHM 카테고리 점수 [0, 100]
    kpi_composite: float     # 비즈니스 KPI 종합 [0, 1]
    metric_scores: dict[str, float] = field(default_factory=dict)  # 개별 지표 점수
    month: str = ""          # YYYY-MM

    @property
    def category_vector(self) -> list[float]:
        """Shapley 계산용 3차원 카테고리 벡터."""
        return [self.wmq_score, self.alm_score, self.ohm_score]


@dataclass
class StudyDataset:
    """HAW-STUDY-001 전체 데이터셋."""

    study_id: str
    records: list[AgentRecord]
    n: int
    domains: list[str]
    months: list[str]
    loaded_at: str
    data_source: str  # "real" | "synthetic"

    @property
    def has_scores(self) -> list[float]:
        return [r.has_score for r in self.records]

    @property
    def kpi_scores(self) -> list[float]:
        return [r.kpi_composite for r in self.records]

    def by_domain(self, domain: str) -> list[AgentRecord]:
        return [r for r in self.records if r.domain == domain]


@dataclass
class H1Result:
    """H1 가설 검증 결과: ρ(HAS, Q_실제) ≥ 0.60, p < 0.01."""

    rho: float
    p_value: float
    bonferroni_corrected_p: float
    ci_lower: float
    ci_upper: float
    n: int
    h1_passed: bool          # ρ ≥ 0.60 and p < 0.01
    h1_bonferroni_passed: bool   # ρ ≥ 0.60 and bonferroni_p < 0.01
    n_tests: int             # Bonferroni 보정 검정 수

    def summary(self) -> str:
        status = "[PASS ✓]" if self.h1_passed else "[FAIL ✗]"
        lines = [
            f"H1 검증 결과  {status}",
            f"  Spearman ρ = {self.rho:.4f}  p = {self.p_value:.4f}  n = {self.n}",
            f"  95% CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}]",
            f"  Bonferroni 보정 p (×{self.n_tests}) = {self.bonferroni_corrected_p:.4f}  "
            f"{'[PASS]' if self.h1_bonferroni_passed else '[FAIL]'}",
        ]
        return "\n".join(lines)


@dataclass
class ShapleyWeights:
    """실증 기반 재산출 Shapley 카테고리 가중치."""

    wmq: float   # WMQ 카테고리 가중치
    alm: float   # ALM 카테고리 가중치
    ohm: float   # OHM 카테고리 가중치
    metric_weights: dict[str, float] = field(default_factory=dict)  # 지표 → 상대 중요도 %
    source: str = "empirical"
    study_id: str = ""
    n_agents: int = 0

    @property
    def category_dict(self) -> dict[str, float]:
        return {"wmq": self.wmq, "alm": self.alm, "ohm": self.ohm}

    def summary(self) -> str:
        lines = [
            f"Shapley 가중치 재산출 ({self.source}, n={self.n_agents})",
            f"  WMQ: {self.wmq:.3f} ({self.wmq*100:.1f}%)",
            f"  ALM: {self.alm:.3f} ({self.alm*100:.1f}%)",
            f"  OHM: {self.ohm:.3f} ({self.ohm*100:.1f}%)",
        ]
        if self.metric_weights:
            top = sorted(self.metric_weights.items(), key=lambda x: x[1], reverse=True)[:5]
            lines.append("  상위 5개 지표:")
            for name, imp in top:
                lines.append(f"    {name:6s} {imp:5.1f}%")
        return "\n".join(lines)


@dataclass
class SubgroupResult:
    """도메인별 부분 집단 분석 결과."""

    domain_results: dict[str, CorrelationResult]
    n_per_domain: dict[str, int]
    overall_rho: float

    def summary(self) -> str:
        lines = [f"도메인별 Spearman ρ (전체 ρ = {self.overall_rho:.4f}):"]
        for domain, result in sorted(self.domain_results.items()):
            n = self.n_per_domain.get(domain, 0)
            sig = "*" if result.significant else " "
            lines.append(
                f"  {domain:20s}  ρ = {result.rho:+.4f}  "
                f"p = {result.p_value:.4f}{sig}  n = {n}"
            )
        lines.append("  * p < 0.05")
        return "\n".join(lines)


# ── StudyAnalyzer ───────────────────────────────────────────────────


class StudyAnalyzer:
    """HAW-STUDY-001 실증 연구 데이터 분석기.

    사용 예:
        analyzer = StudyAnalyzer()
        dataset = analyzer.load_study_data("HAW-STUDY-001")

        h1 = analyzer.compute_h1_hypothesis(dataset)
        print(h1.summary())

        weights = analyzer.shapley_recalibration(dataset)
        analyzer.sdk_weight_update(weights)

        subgroup = analyzer.domain_subgroup_analysis(dataset)
        print(subgroup.summary())
    """

    N_BONFERRONI_TESTS: int = len(STUDY_DOMAINS)  # 5 도메인 = 5 비교

    def load_study_data(
        self,
        study_id: str,
        study_base_dir: str | Path = ".haw_study",
    ) -> StudyDataset:
        """수집된 연구 데이터를 로드한다.

        실제 데이터(.haw_study/kpi/)가 n < 10 이면 합성 n=25 데이터로 대체한다.

        Returns:
            StudyDataset
        """
        base = Path(study_base_dir)
        real_records = self._try_load_real_data(study_id, base)

        if len(real_records) >= 10:
            records = real_records
            source = "real"
        else:
            records = _generate_synthetic_n25(seed=42)
            source = "synthetic"

        domains_found = sorted({r.domain for r in records})
        months_found = sorted({r.month for r in records if r.month})

        return StudyDataset(
            study_id=study_id,
            records=records,
            n=len(records),
            domains=domains_found,
            months=months_found,
            loaded_at=datetime.now(UTC).isoformat(),
            data_source=source,
        )

    def compute_h1_hypothesis(
        self,
        dataset: StudyDataset,
        n_bootstrap: int = 1000,
    ) -> H1Result:
        """H1 가설 검증: ρ(HAS, Q_실제) ≥ 0.60, p < 0.01.

        Bonferroni 보정: p_corrected = min(1.0, p × n_domains)
        """
        rho, p_value = _spearman_rho(dataset.has_scores, dataset.kpi_scores)
        _, ci_lower, ci_upper = _bootstrap_ci(
            dataset.has_scores,
            dataset.kpi_scores,
            n_bootstrap=n_bootstrap,
        )
        bonferroni_p = min(1.0, p_value * self.N_BONFERRONI_TESTS)

        return H1Result(
            rho=round(rho, 4),
            p_value=round(p_value, 6),
            bonferroni_corrected_p=round(bonferroni_p, 6),
            ci_lower=round(ci_lower, 4) if not math.isnan(ci_lower) else float("nan"),
            ci_upper=round(ci_upper, 4) if not math.isnan(ci_upper) else float("nan"),
            n=dataset.n,
            h1_passed=(rho >= 0.60 and p_value < 0.01),
            h1_bonferroni_passed=(rho >= 0.60 and bonferroni_p < 0.01),
            n_tests=self.N_BONFERRONI_TESTS,
        )

    def shapley_recalibration(
        self,
        dataset: StudyDataset,
    ) -> ShapleyWeights:
        """실제 데이터 기반 3범주 Shapley 가중치 재산출.

        카테고리 레벨 (3 features: WMQ, ALM, OHM) 기준으로 계산한다.
        개별 지표(15개) Shapley는 카테고리 비율을 15분할하여 근사한다.
        """
        features = [r.category_vector for r in dataset.records]
        outcomes = dataset.kpi_scores
        feature_names = ["wmq", "alm", "ohm"]

        shapley_result = _compute_shapley(features, outcomes, feature_names)
        weights_pct = dict(
            zip(shapley_result.metric_names, shapley_result.relative_importance, strict=False)
        )

        # 카테고리 가중치를 0~1 정규화 (합계=1.0)
        total = sum(weights_pct.values()) or 100.0
        wmq = round(weights_pct.get("wmq", 40.0) / total, 4)
        alm = round(weights_pct.get("alm", 35.0) / total, 4)
        ohm = round(1.0 - wmq - alm, 4)  # 합계 1.0 보장

        # 개별 지표 중요도 (카테고리 가중치 × 1/5 균등 분배 근사)
        metric_weights: dict[str, float] = {}
        for m in WMQ_METRICS:
            metric_weights[m] = round(weights_pct.get("wmq", 40.0) / 5, 2)
        for m in ALM_METRICS:
            metric_weights[m] = round(weights_pct.get("alm", 35.0) / 5, 2)
        for m in OHM_METRICS:
            metric_weights[m] = round(weights_pct.get("ohm", 25.0) / 5, 2)

        return ShapleyWeights(
            wmq=wmq,
            alm=alm,
            ohm=ohm,
            metric_weights=metric_weights,
            source="empirical" if dataset.data_source == "real" else "synthetic",
            study_id=dataset.study_id,
            n_agents=dataset.n,
        )

    def domain_subgroup_analysis(
        self,
        dataset: StudyDataset,
    ) -> SubgroupResult:
        """6개 도메인별 ρ 산출.

        n < 3 인 도메인은 건너뜀.
        """
        analyzer = HASBusinessCorrelation()
        domain_results: dict[str, CorrelationResult] = {}
        n_per_domain: dict[str, int] = {}

        for domain in sorted({r.domain for r in dataset.records}):
            subset = dataset.by_domain(domain)
            n_per_domain[domain] = len(subset)
            if len(subset) < 3:
                continue
            has_sub = [r.has_score for r in subset]
            kpi_sub = [r.kpi_composite for r in subset]
            try:
                domain_results[domain] = analyzer.compute_spearman(has_sub, kpi_sub)
            except ValueError:
                pass

        overall_rho, _ = _spearman_rho(dataset.has_scores, dataset.kpi_scores)
        return SubgroupResult(
            domain_results=domain_results,
            n_per_domain=n_per_domain,
            overall_rho=round(overall_rho, 4),
        )

    def sdk_weight_update(self, new_weights: ShapleyWeights) -> None:
        """SDK의 HAS 계산 가중치를 실증 기반으로 업데이트한다.

        hachillesworld.core.config.HAS_WEIGHTS 를 인메모리에서 갱신하며,
        이후 모든 DiagnosticReport.composite_score 계산에 반영된다.

        Args:
            new_weights: shapley_recalibration()이 반환한 ShapleyWeights

        Raises:
            ValueError: wmq + alm + ohm ≠ 1.0 인 경우
        """
        total = new_weights.wmq + new_weights.alm + new_weights.ohm
        if abs(total - 1.0) > 1e-4:
            raise ValueError(
                f"가중치 합계가 1.0이 아닙니다: {total:.6f}. "
                "wmq + alm + ohm = 1.0 이어야 합니다."
            )

        import hachillesworld.core.config as _cfg

        _cfg.HAS_WEIGHTS["wmq"] = new_weights.wmq
        _cfg.HAS_WEIGHTS["alm"] = new_weights.alm
        _cfg.HAS_WEIGHTS["ohm"] = new_weights.ohm

    # ── 내부 헬퍼 ─────────────────────────────────────────────────

    def _try_load_real_data(
        self,
        study_id: str,
        base: Path,
    ) -> list[AgentRecord]:
        """실제 수집 데이터 로드 시도. 없으면 빈 목록 반환."""
        kpi_dir = base / "kpi"
        if not kpi_dir.exists():
            return []

        records: list[AgentRecord] = []
        for kpi_file in sorted(kpi_dir.glob(f"{study_id}_*.json")):
            try:
                with kpi_file.open(encoding="utf-8") as f:
                    kpi_rec = json.load(f)
                kpi_data = kpi_rec.get("kpi_data", {})
                # KPI 종합: 제출된 값들의 평균 (정규화)
                kpi_vals = [
                    v for v in kpi_data.values()
                    if isinstance(v, int | float) and 0 <= v <= 1
                ]
                if not kpi_vals:
                    continue
                kpi_composite = sum(kpi_vals) / len(kpi_vals)

                # 에피소드 로그에서 HAS 추정 (HAS 미기록 시 0.75 기본값)
                has_score = kpi_data.get("has_score", 75.0)
                wmq = kpi_data.get("wmq_score", has_score)
                alm = kpi_data.get("alm_score", has_score)
                ohm = kpi_data.get("ohm_score", has_score)
                domain = kpi_data.get("domain", "supply_chain")

                records.append(
                    AgentRecord(
                        agent_id=hashlib.sha256(kpi_rec.get("study_id", "").encode()).hexdigest()[:16],
                        domain=domain,
                        has_score=float(has_score),
                        wmq_score=float(wmq),
                        alm_score=float(alm),
                        ohm_score=float(ohm),
                        kpi_composite=round(kpi_composite, 4),
                        month=kpi_rec.get("month", ""),
                    )
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return records


# ── 합성 데이터 생성기 ─────────────────────────────────────────────


def _generate_synthetic_n25(seed: int = 42) -> list[AgentRecord]:
    """HAW-STUDY-001 프로토타입용 합성 n=25 데이터 생성.

    설계 원칙:
    - 5 도메인 × 5 품질 계층 = 25 에이전트
    - HAS ↔ KPI 상관이 실제 연구에서 기대되는 수준(ρ ≈ 0.73)을 반영
    - 도메인별 특성 반영 (healthcare는 HITL로 KPI 분산 큼)
    """
    rng = random.Random(seed)

    # 품질 계층별 기본값 (tier=1 lowest → tier=5 highest)
    tier_config = [
        (35.0,  0.0, 0.28),   # tier 1: HAS_base, HAS_noise_seed, KPI_base
        (50.0,  1.0, 0.43),   # tier 2
        (65.0,  2.0, 0.57),   # tier 3
        (80.0,  3.0, 0.70),   # tier 4
        (93.0,  4.0, 0.82),   # tier 5
    ]

    # 도메인별 KPI 편차 (도메인 특성 반영)
    domain_kpi_offset = {
        "supply_chain":     +0.03,
        "customer_service": -0.04,
        "code_generation":  +0.02,
        "finance":          -0.01,
        "healthcare":       -0.05,  # 높은 HITL 요건으로 KPI 낮음
    }

    records: list[AgentRecord] = []

    for tier_idx, (has_base, _, kpi_base) in enumerate(tier_config):
        for domain_idx, domain in enumerate(STUDY_DOMAINS):
            # HAS 구성 요소 (카테고리별 분산 추가)
            has_noise = rng.gauss(0, 5.0)
            has_score = max(20.0, min(100.0, has_base + has_noise))

            # 카테고리 점수 (HAS 기준으로 편차 추가)
            wmq_score = max(10.0, min(100.0, has_score + rng.gauss(0, 4.0)))
            alm_score = max(10.0, min(100.0, has_score + rng.gauss(0, 5.0)))
            ohm_score = max(10.0, min(100.0, has_score + rng.gauss(0, 6.0)))

            # KPI: HAS와 상관 + 도메인 효과 + 개별 노이즈
            kpi_noise = rng.gauss(0, 0.09)  # 큰 노이즈 → ρ ≈ 0.73 설계
            kpi_dom_offset = domain_kpi_offset[domain]
            kpi = max(0.10, min(0.99, kpi_base + kpi_dom_offset + kpi_noise))

            # 개별 지표 점수 (카테고리 점수 기반 근사)
            metric_scores: dict[str, float] = {}
            for m in WMQ_METRICS:
                metric_scores[m] = max(0.0, min(1.0, wmq_score / 100 + rng.gauss(0, 0.04)))
            for m in ALM_METRICS:
                metric_scores[m] = max(0.0, min(1.0, alm_score / 100 + rng.gauss(0, 0.04)))
            for m in OHM_METRICS:
                metric_scores[m] = max(0.0, min(1.0, ohm_score / 100 + rng.gauss(0, 0.04)))

            agent_key = f"agent-tier{tier_idx+1}-{domain}"
            records.append(
                AgentRecord(
                    agent_id=hashlib.sha256(agent_key.encode()).hexdigest()[:16],
                    domain=domain,
                    has_score=round(has_score, 2),
                    wmq_score=round(wmq_score, 2),
                    alm_score=round(alm_score, 2),
                    ohm_score=round(ohm_score, 2),
                    kpi_composite=round(kpi, 4),
                    metric_scores={k: round(v, 4) for k, v in metric_scores.items()},
                    month="2026-07" if tier_idx < 3 else "2026-08",
                )
            )

    return records
