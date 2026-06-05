# Copyright 2026 HAchillesWorld (박성훈)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""HAchillesWorld — HAchilles Agent Score (HAS) 계산기
15개 지표 → 범주 점수 → 복합 HAS [0, 1000]
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics.agency_level import ALMResult, compute_alm
from metrics.operational_health import OHMResult, compute_ohm
from metrics.wm_quality import WMQResult, compute_wmq

try:
    from hachillesworld.core.domain_config import DomainConfig

    _DOMAIN_CONFIG_AVAILABLE = True
except ImportError:
    _DOMAIN_CONFIG_AVAILABLE = False

# 호환성 유지용 fallback 승수 (DomainConfig 미사용 시)
DOMAIN_MULTIPLIER = {
    "healthcare": 0.85,
    "finance": 0.90,
    "supply_chain": 0.95,
    "customer_service": 1.00,
    "code_generation": 1.00,
    "research": 1.00,
    "other": 1.00,
}


def _resolve_multiplier(domain: str) -> float:
    """도메인 조정 승수를 반환한다. DomainConfig가 있으면 YAML에서 로드한다."""
    if _DOMAIN_CONFIG_AVAILABLE:
        try:
            return DomainConfig.load(domain).get_dahas_multiplier()
        except Exception:
            pass
    return DOMAIN_MULTIPLIER.get(domain, 1.00)


def _auto_detect_domain(episodes: list[dict]) -> str:
    """에피소드 목록 첫 항목에서 도메인을 자동 감지한다."""
    if not episodes:
        return "other"
    if _DOMAIN_CONFIG_AVAILABLE:
        try:
            return DomainConfig.auto_detect_from_dict(episodes[0])
        except Exception:
            pass
    return episodes[0].get("domain", "other") or "other"

# HAS 등급 해석표
HAS_GRADE_TABLE = [
    (900, "A+", "L3 인증 — 자율 운영 가능", "분기별 모니터링"),
    (800, "A", "L3 준비 — 모니터링하며 배포", "최종 튜닝"),
    (700, "B", "L2 운영 — 감독 하 배포", "상위 3개 지표 최적화"),
    (600, "C", "L2 개발 중 — 제한적 배포", "L2 최적화 완료"),
    (500, "D", "L1 관리 — 개발/테스트만", "Phase 1 캘리브레이션 필요"),
    (400, "F", "Pre-L1 — 배포 불가", "전체 진단 필요"),
    (0, "F-", "위험 — 에이전트 안전하지 않음", "아키텍처 개입 필요"),
]


@dataclass
class HASReport:
    """HAS 전체 진단 결과"""

    agent_id: str
    domain: str

    # 입력 지표 결과
    wmq: WMQResult
    alm: ALMResult
    ohm: OHMResult

    # 범주 점수 [0, 100]
    wmq_score: float
    alm_score: float
    ohm_score: float

    # 복합 점수
    composite_raw: float  # 가중 평균 [0, 100]
    has: int  # 최종 HAS [0, 1000]
    dahas: int  # 도메인 조정 HAS

    # 해석
    grade: str
    deployment_status: str
    recommended_action: str
    level_estimate: str  # 예: "L2.3 × DigLaw"

    # 상위 3개 이슈
    top_issues: list[tuple[str, float, float]]  # (지표명, 현재값, 목표값)

    def summary(self) -> str:
        lines = [
            "═══════════════════════════════════════════════",
            "  HAchillesWorld 진단 보고서",
            f"  에이전트: {self.agent_id}  |  도메인: {self.domain}",
            "═══════════════════════════════════════════════",
            f"  HAchilles Agent Score (HAS): {self.has}  [{self.grade}]",
            f"  도메인 조정 HAS (daHAS):     {self.dahas}",
            f"  예상 Level:                  {self.level_estimate}",
            "───────────────────────────────────────────────",
            "  범주 점수",
            f"  ┌ WM 품질 (40%): {self.wmq_score:5.1f}/100",
            f"  │   SDR={self.wmq.sdr:.3f}  ECE={self.wmq.ece:.3f}  PA={self.wmq.pa:.3f}",
            f"  ├ 에이전시 (35%): {self.alm_score:5.1f}/100",
            f"  │   PD={self.alm.pd:.1f}  SCR={self.alm.scr:.3f}  GAR={self.alm.gar:.3f}",
            f"  └ 운영건전성 (25%): {self.ohm_score:5.1f}/100",
            f"      LCR={self.ohm.lcr:.2f}  HC={self.ohm.hc}개  SU={self.ohm.su:.4f}",
            "───────────────────────────────────────────────",
            f"  배포 판정: {self.deployment_status}",
            f"  권고 조치: {self.recommended_action}",
            "───────────────────────────────────────────────",
            "  즉시 개선 필요 TOP 3",
        ]
        for i, (name, current, target) in enumerate(self.top_issues[:3], 1):
            lines.append(f"  {i}. {name}: 현재={current:.3f} → 목표={target:.3f}")
        lines.append("═══════════════════════════════════════════════")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# HAS 계산 핵심 함수
# ──────────────────────────────────────────────


def compute_has(
    wmq: WMQResult,
    alm: ALMResult,
    ohm: OHMResult,
    agent_id: str = "unknown",
    domain: str = "other",
) -> HASReport:
    """3개 범주 점수 → 복합 HAS 계산.

    HAS = round(10 × (0.40 × WMQ + 0.35 × ALM + 0.25 × OHM))
    daHAS = HAS × domain_multiplier
    """
    wmq_score = wmq.category_score
    alm_score = alm.category_score
    ohm_score = ohm.category_score

    composite = 0.40 * wmq_score + 0.35 * alm_score + 0.25 * ohm_score
    has = round(10 * composite)
    has = max(0, min(1000, has))

    multiplier = _resolve_multiplier(domain)
    dahas = round(has * multiplier)

    grade, status, action = _interpret_has(has)
    level = _estimate_level(alm.pd, wmq.ece)
    top_issues = _find_top_issues(wmq, alm, ohm)

    return HASReport(
        agent_id=agent_id,
        domain=domain,
        wmq=wmq,
        alm=alm,
        ohm=ohm,
        wmq_score=wmq_score,
        alm_score=alm_score,
        ohm_score=ohm_score,
        composite_raw=composite,
        has=has,
        dahas=dahas,
        grade=grade,
        deployment_status=status,
        recommended_action=action,
        level_estimate=level,
        top_issues=top_issues,
    )


def _interpret_has(has: int) -> tuple[str, str, str]:
    for threshold, grade, status, action in HAS_GRADE_TABLE:
        if has >= threshold:
            return grade, status, action
    return "F-", "위험", "아키텍처 개입 필요"


def _estimate_level(pd: float, ece: float) -> str:
    """Planning Depth와 ECE로 Level 추정"""
    if pd >= 20 and ece < 0.08:
        sublevel = min(3.0, 2.0 + (pd - 20) / 10)
        return f"L{sublevel:.1f} × DigLaw"
    if pd >= 15:
        sublevel = 2.0 + (pd - 15) / 10
        return f"L{sublevel:.1f} × DigLaw"
    if pd >= 5:
        sublevel = 1.5 + (pd - 5) / 20
        return f"L{sublevel:.1f} × DigLaw"
    sublevel = 1.0 + (pd - 1) / 8
    return f"L{sublevel:.1f} × DigLaw"


def _find_top_issues(
    wmq: WMQResult,
    alm: ALMResult,
    ohm: OHMResult,
) -> list[tuple[str, float, float]]:
    """정규화 점수가 낮은 지표 순으로 상위 이슈 반환"""
    candidates = [
        ("SDR", wmq.n_sdr, wmq.sdr, 0.05),
        ("ECE", wmq.n_ece, wmq.ece, 0.06),
        ("PA", wmq.n_pa, wmq.pa, 0.92),
        ("ODR", wmq.n_odr, wmq.odr, 0.80),
        ("PD", alm.n_pd, alm.pd, 20),
        ("SCR", alm.n_scr, alm.scr, 0.25),
        ("GAR", alm.n_gar, alm.gar, 0.88),
        ("LCR", ohm.n_lcr, ohm.lcr, 0.75),
        ("HC", ohm.n_hc, ohm.hc, 30),
        ("HR", ohm.n_hr, ohm.hr, 0.03),
    ]
    # 정규화 점수 오름차순 정렬 (낮을수록 개선 필요)
    candidates.sort(key=lambda x: x[1])
    return [(name, current, target) for name, _, current, target in candidates[:5]]


# ──────────────────────────────────────────────
# 에피소드 로그에서 HAS 일괄 계산
# ──────────────────────────────────────────────


def compute_has_from_episodes(
    episodes: list[dict],
    agent_id: str,
    domain: str | None = None,
    monthly_budget_usd: float = 0.0,
    harness_rules: list[dict] | None = None,
    incident_records: list[dict] | None = None,
    drift_events: list[dict] | None = None,
    counterfactual_records: list[dict] | None = None,
    period_days: int = 30,
) -> HASReport:
    """에피소드 로그 목록에서 전체 HAS 보고서 생성.
    연구 파이프라인의 메인 진입점.

    domain=None이면 에피소드 메타데이터에서 자동 감지한다.
    """
    if domain is None:
        domain = _auto_detect_domain(episodes)

    # 예측/실제 상태 쌍 추출
    predicted = [ep.get("predicted_next_state", {}) for ep in episodes]
    actual = [ep.get("actual_next_state", {}) for ep in episodes]
    confidences = [ep.get("prediction_confidence", 0.5) for ep in episodes]

    # OOD 정보 추출
    ood_flags = [ep.get("ood_detected", False) for ep in episodes]
    has_ood_info = any(ep.get("ood_detected") is not None for ep in episodes)

    wmq = compute_wmq(
        predicted_states=predicted,
        actual_states=actual,
        confidences=confidences,
        ood_flags=ood_flags if has_ood_info else None,
        drift_events=drift_events,
    )

    alm = compute_alm(
        episodes=episodes,
        counterfactual_records=counterfactual_records,
    )

    ohm = compute_ohm(
        episodes=episodes,
        monthly_budget_usd=monthly_budget_usd,
        harness_rules=harness_rules,
        incident_records=incident_records,
        period_days=period_days,
    )

    return compute_has(wmq, alm, ohm, agent_id=agent_id, domain=domain)
