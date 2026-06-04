"""HAchillesWorld — 합성 에이전트 로그 생성기
실제 데이터 없이도 전체 파이프라인을 테스트할 수 있는 시뮬레이터.
6개 도메인 × 4개 에이전트 = 24개 에이전트 시뮬레이션.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# 에이전트 프로파일 정의
# ──────────────────────────────────────────────


@dataclass
class AgentProfile:
    """에이전트의 '진짜' 품질 수준 (시뮬레이션에서 ground truth)"""

    agent_id: str
    domain: str
    true_level: float  # 1.0 ~ 3.0
    true_sdr: float  # 실제 드리프트 비율
    true_ece: float  # 실제 ECE
    true_planning_depth: int  # 실제 계획 깊이
    true_scr: float  # 실제 자기 수정률
    true_gar: float  # 실제 목표 달성률
    true_hitl_rate: float  # 실제 HITL 비율
    true_lcr: float  # 실제 비용 비율
    true_harness_count: int  # 실제 하네스 규칙 수
    # 비즈니스 성과 (HAS와의 상관관계 검증용 ground truth)
    business_outcome_score: float  # 0~100, HAS와 상관관계 있어야 함


# 6개 도메인 × 4개 수준 = 24개 에이전트 프로파일
AGENT_PROFILES = [
    # ── 공급망 ──
    AgentProfile("sc-low-01", "supply_chain", 1.4, 0.28, 0.19, 3, 0.02, 0.71, 0.15, 1.52, 4, 32.0),
    AgentProfile("sc-mid-02", "supply_chain", 1.9, 0.14, 0.11, 6, 0.08, 0.80, 0.10, 1.18, 12, 55.0),
    AgentProfile("sc-hi-03", "supply_chain", 2.4, 0.07, 0.07, 15, 0.20, 0.87, 0.05, 0.88, 24, 77.0),
    AgentProfile(
        "sc-top-04", "supply_chain", 3.0, 0.03, 0.05, 22, 0.28, 0.93, 0.02, 0.74, 34, 94.0,
    ),
    # ── 고객 서비스 ──
    AgentProfile(
        "cs-low-05", "customer_service", 1.3, 0.31, 0.22, 2, 0.01, 0.68, 0.18, 1.65, 3, 28.0,
    ),
    AgentProfile(
        "cs-mid-06", "customer_service", 1.8, 0.16, 0.12, 5, 0.07, 0.79, 0.11, 1.22, 10, 52.0,
    ),
    AgentProfile(
        "cs-hi-07", "customer_service", 2.3, 0.08, 0.08, 12, 0.18, 0.84, 0.06, 0.91, 21, 73.0,
    ),
    AgentProfile(
        "cs-top-08", "customer_service", 2.9, 0.04, 0.06, 18, 0.25, 0.90, 0.03, 0.79, 31, 90.0,
    ),
    # ── 금융 ──
    AgentProfile("fin-low-09", "finance", 1.5, 0.26, 0.17, 4, 0.03, 0.73, 0.14, 1.41, 5, 35.0),
    AgentProfile("fin-mid-10", "finance", 2.0, 0.12, 0.10, 8, 0.11, 0.82, 0.08, 1.05, 15, 59.0),
    AgentProfile("fin-hi-11", "finance", 2.5, 0.06, 0.07, 14, 0.22, 0.88, 0.04, 0.84, 26, 80.0),
    AgentProfile("fin-top-12", "finance", 3.0, 0.02, 0.04, 21, 0.30, 0.94, 0.01, 0.70, 36, 96.0),
    # ── 코드 생성 ──
    AgentProfile(
        "cg-low-13", "code_generation", 1.4, 0.29, 0.20, 3, 0.02, 0.69, 0.16, 1.58, 4, 30.0,
    ),
    AgentProfile(
        "cg-mid-14", "code_generation", 1.7, 0.18, 0.13, 5, 0.06, 0.78, 0.12, 1.25, 8, 49.0,
    ),
    AgentProfile(
        "cg-hi-15", "code_generation", 2.2, 0.09, 0.09, 11, 0.17, 0.83, 0.07, 0.94, 19, 70.0,
    ),
    AgentProfile(
        "cg-top-16", "code_generation", 2.8, 0.05, 0.06, 17, 0.24, 0.89, 0.04, 0.81, 29, 88.0,
    ),
    # ── 연구/분석 ──
    AgentProfile("ra-low-17", "research", 1.6, 0.24, 0.16, 5, 0.04, 0.74, 0.13, 1.38, 6, 38.0),
    AgentProfile("ra-mid-18", "research", 2.1, 0.11, 0.10, 10, 0.13, 0.83, 0.07, 1.00, 17, 63.0),
    AgentProfile("ra-hi-19", "research", 2.6, 0.05, 0.07, 16, 0.23, 0.89, 0.03, 0.82, 28, 83.0),
    AgentProfile("ra-top-20", "research", 3.1, 0.02, 0.04, 24, 0.31, 0.95, 0.01, 0.68, 38, 98.0),
    # ── 의료/헬스케어 (6번째 도메인 — 일반화 검증) ──
    # 고신뢰도 요구 + 강한 HITL 규제 환경: 다른 도메인과 성격이 가장 달라 일반화 주장 강화
    AgentProfile("hc-low-21", "healthcare", 1.3, 0.33, 0.24, 2, 0.01, 0.65, 0.22, 1.71, 5, 25.0),
    AgentProfile("hc-mid-22", "healthcare", 1.8, 0.17, 0.13, 6, 0.08, 0.77, 0.13, 1.28, 13, 50.0),
    AgentProfile("hc-hi-23", "healthcare", 2.4, 0.07, 0.08, 13, 0.19, 0.85, 0.06, 0.93, 25, 75.0),
    AgentProfile("hc-top-24", "healthcare", 3.0, 0.03, 0.05, 20, 0.28, 0.92, 0.02, 0.76, 35, 93.0),
]


# ──────────────────────────────────────────────
# 에피소드 로그 생성
# ──────────────────────────────────────────────


def generate_episodes(
    profile: AgentProfile,
    n_episodes: int = 500,
    noise_level: float = 0.05,
    seed: int | None = None,
) -> list[dict]:
    """에이전트 프로파일을 기반으로 현실적인 에피소드 로그 생성.
    noise_level: 측정 노이즈 (실제 연구에서의 로그 불완전성 모사)
    """
    rng = random.Random(seed)
    episodes = []
    base_time = datetime(2026, 8, 1, 9, 0, 0)

    for i in range(n_episodes):
        episode_id = f"ep-{profile.agent_id}-{i:04d}"
        ts = base_time + timedelta(minutes=i * 3)

        # 측정 노이즈 추가
        sdr_noise = rng.gauss(0, noise_level)
        conf_noise = rng.gauss(0, noise_level * 0.3)

        # 예측/실제 상태 생성
        base_inventory = rng.randint(100, 1000)
        drift_occurs = rng.random() < (profile.true_sdr + sdr_noise)
        pred_inventory = base_inventory + rng.randint(-50, 50)
        if drift_occurs:
            actual_inventory = pred_inventory + rng.randint(-300, 300)
        else:
            actual_inventory = pred_inventory + rng.randint(-20, 20)

        # 신뢰도 (ECE 기반 생성)
        is_accurate = not drift_occurs
        ideal_conf = 0.85 if is_accurate else 0.30
        confidence = max(0.01, min(0.99, ideal_conf + conf_noise + (profile.true_ece - 0.10)))

        # HITL 여부
        hitl = rng.random() < profile.true_hitl_rate

        # 하네스 트리거
        harness_triggers = []
        if drift_occurs and profile.true_harness_count >= 10:
            harness_triggers.append(
                {
                    "rule_id": f"drift-gate-{rng.randint(1, 5)}",
                    "grade": "A",
                    "action": "WARN" if rng.random() < 0.7 else "REJECT",
                    "triggered": True,
                },
            )

        # 자기 수정
        error_detected = drift_occurs or (rng.random() < 0.05)
        self_correction_applied = error_detected and (rng.random() < profile.true_scr)

        # 비용
        base_tokens = rng.randint(500, 3000)
        llm_cost = base_tokens * 0.000002 * profile.true_lcr

        # 성공 여부
        goal_achieved = rng.random() < profile.true_gar
        episode_success = goal_achieved and not (drift_occurs and not self_correction_applied)

        ep = {
            "agent_id": profile.agent_id,
            "episode_id": episode_id,
            "timestamp": ts.isoformat(),
            "domain": profile.domain,
            "predicted_next_state": {"inventory": pred_inventory, "demand": rng.randint(50, 200)},
            "actual_next_state": {"inventory": actual_inventory, "demand": rng.randint(50, 200)},
            "prediction_confidence": round(confidence, 4),
            "tools_used": ["search_api", "order_api"] if rng.random() < 0.6 else ["search_api"],
            "planning_depth_used": min(profile.true_planning_depth + rng.randint(-2, 2), 25),
            "hitl_required": hitl,
            "hitl_reason": "low_confidence" if hitl else None,
            "llm_tokens_input": base_tokens,
            "llm_tokens_output": rng.randint(100, 500),
            "llm_cost_usd": round(llm_cost, 6),
            "harness_triggers": harness_triggers,
            "self_correction_applied": self_correction_applied,
            "error_detected": error_detected,
            "ood_detected": confidence < 0.40,
            "episode_success": episode_success,
            "goal_achieved": goal_achieved,
            "step_count": rng.randint(3, 20),
            "duration_seconds": rng.uniform(1.0, 15.0),
        }
        episodes.append(ep)

    return episodes


def generate_harness_rules(profile: AgentProfile) -> list[dict]:
    """프로파일 기반 하네스 규칙 목록 생성"""
    rules = []
    for i in range(profile.true_harness_count):
        grade = (
            "A"
            if i < profile.true_harness_count // 3
            else ("B" if i < 2 * profile.true_harness_count // 3 else "C")
        )
        rules.append(
            {
                "rule_id": f"rule-{profile.agent_id}-{i:02d}",
                "grade": grade,
                "is_active": True,
                "last_triggered": (
                    datetime(2026, 8, 20) - timedelta(days=random.randint(0, 25))
                ).isoformat(),
                "trigger_count": random.randint(1, 50),
            },
        )
    return rules


def generate_incident_records(profile: AgentProfile, n: int = 3) -> list[dict]:
    """인시던트 기록 생성 (IRT 계산용)"""
    if n == 0:
        return []
    records = []
    base = datetime(2026, 8, 1)
    # 수준이 낮을수록 복구 시간이 길다
    avg_recovery_minutes = max(2.0, 60.0 / profile.true_level)
    for _ in range(n):
        t_inc = base + timedelta(days=random.randint(1, 28), hours=random.randint(0, 23))
        recovery_minutes = max(1.0, random.gauss(avg_recovery_minutes, avg_recovery_minutes * 0.3))
        t_rec = t_inc + timedelta(minutes=recovery_minutes)
        records.append(
            {
                "incident_time": t_inc.isoformat(),
                "recovery_time": t_rec.isoformat(),
            },
        )
    return records


def generate_counterfactual_records(profile: AgentProfile, n: int = 100) -> list[dict]:
    """반사실 추론 기록 생성 (CA 계산용)"""
    records = []
    # 수준이 높을수록 CF 예측 정확도 높다
    true_ca = 0.50 + (profile.true_level - 1.0) * 0.15
    for _ in range(n):
        n_alts = random.randint(2, 5)
        r_range = random.uniform(5, 50)
        alts = []
        for _ in range(n_alts):
            actual_reward = random.uniform(-r_range, r_range)
            error = random.gauss(0, r_range * (1 - true_ca))
            predicted_reward = actual_reward + error
            alts.append(
                {
                    "predicted_reward": predicted_reward,
                    "actual_reward": actual_reward,
                },
            )
        records.append({"alternatives": alts, "reward_range": r_range})
    return records


# ──────────────────────────────────────────────
# 전체 연구 데이터셋 생성
# ──────────────────────────────────────────────


def generate_study_dataset(
    output_path: str = "study_dataset.json",
    n_episodes_per_agent: int = 500,
    noise_level: float = 0.05,
    seed: int = 42,
) -> list[dict]:
    """20개 에이전트 전체 데이터셋 생성.

    Returns:
        list of {agent_id, domain, episodes, harness_rules, ...}

    """
    random.seed(seed)
    dataset = []

    print(f"[sample_data] 연구 데이터셋 생성 시작: {len(AGENT_PROFILES)}개 에이전트")

    for idx, profile in enumerate(AGENT_PROFILES):
        print(
            f"  [{idx + 1:02d}/{len(AGENT_PROFILES)}] {profile.agent_id} (L{profile.true_level:.1f})",
        )

        episodes = generate_episodes(profile, n_episodes_per_agent, noise_level, seed + idx)
        harness_rules = generate_harness_rules(profile)
        incidents = generate_incident_records(profile, n=random.randint(1, 5))
        cf_records = generate_counterfactual_records(profile, n=100)

        dataset.append(
            {
                "agent_id": profile.agent_id,
                "domain": profile.domain,
                "true_level": profile.true_level,
                "business_outcome_score": profile.business_outcome_score,
                "episodes": episodes,
                "harness_rules": harness_rules,
                "incident_records": incidents,
                "counterfactual_records": cf_records,
                "monthly_budget_usd": 200.0,
            },
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"[sample_data] 저장 완료: {output_path}")
    return dataset
