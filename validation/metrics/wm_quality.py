"""HAchillesWorld — WMQ(World Model Quality) 지표 계산 모듈
WMQ-1: Simulation Drift Rate (SDR)
WMQ-2: Calibration ECE
WMQ-3: Prediction Accuracy (PA)
WMQ-4: OOD Detection Rate (ODR)
WMQ-5: World Model Update Latency (WMUL)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WMQResult:
    sdr: float  # Simulation Drift Rate
    ece: float  # Expected Calibration Error
    pa: float  # Prediction Accuracy
    odr: float  # OOD Detection Rate
    wmul_hours: float  # WM Update Latency (hours), NaN if no drift event

    # 정규화 점수 [0, 100]
    n_sdr: float = field(init=False)
    n_ece: float = field(init=False)
    n_pa: float = field(init=False)
    n_odr: float = field(init=False)
    n_wmul: float = field(init=False)
    category_score: float = field(init=False)

    # 임계값 (도메인 기본값)
    DRIFT_THRESHOLD: float = 0.15
    ECE_L3_TARGET: float = 0.06
    ECE_CRITICAL: float = 0.20

    def __post_init__(self):
        self.n_sdr = self._normalize_lower_better(self.sdr, good=0.05, bad=0.30)
        self.n_ece = self._normalize_lower_better(self.ece, good=0.04, bad=0.25)
        self.n_pa = self._normalize_higher_better(self.pa, good=0.95, bad=0.70)
        self.n_odr = self._normalize_higher_better(self.odr, good=0.90, bad=0.40)
        if math.isnan(self.wmul_hours):
            self.n_wmul = 100.0  # 드리프트 이벤트 없음 = 최고점
        else:
            self.n_wmul = self._normalize_lower_better(self.wmul_hours, good=12, bad=168)

        weights = [0.30, 0.25, 0.20, 0.15, 0.10]
        scores = [self.n_sdr, self.n_ece, self.n_pa, self.n_odr, self.n_wmul]
        self.category_score = sum(w * s for w, s in zip(weights, scores, strict=False))

    @staticmethod
    def _normalize_lower_better(value: float, good: float, bad: float) -> float:
        """낮을수록 좋은 지표 정규화 [0,100]"""
        if value <= good:
            return 100.0
        if value >= bad:
            return 0.0
        return 100.0 * (bad - value) / (bad - good)

    @staticmethod
    def _normalize_higher_better(value: float, good: float, bad: float) -> float:
        """높을수록 좋은 지표 정규화 [0,100]"""
        if value >= good:
            return 100.0
        if value <= bad:
            return 0.0
        return 100.0 * (value - bad) / (good - bad)


# ──────────────────────────────────────────────
# WMQ-1: Simulation Drift Rate
# ──────────────────────────────────────────────


def compute_sdr(
    predicted_states: list[dict],
    actual_states: list[dict],
    drift_threshold: float = 0.15,
    distance_fn=None,
) -> float:
    """SDR = (1/T) Σ 𝟙[d(â_{t+1}, s_{t+1}) > θ_drift]

    Args:
        predicted_states: 에이전트가 예측한 다음 상태 목록
        actual_states:    실제 관측된 다음 상태 목록
        drift_threshold:  드리프트 판정 임계값 (기본 0.15 = 15% 상대 오차)
        distance_fn:      상태 간 거리 함수 (None이면 기본 상대 오차 사용)

    """
    assert len(predicted_states) == len(actual_states), "예측/실제 상태 수 불일치"
    T = len(predicted_states)
    if T == 0:
        return float("nan")

    if distance_fn is None:
        distance_fn = _default_relative_error

    drift_count = sum(
        1
        for p, a in zip(predicted_states, actual_states, strict=False)
        if distance_fn(p, a) > drift_threshold
    )
    return drift_count / T


def _default_relative_error(pred: dict, actual: dict) -> float:
    """수치 키들의 평균 상대 오차. 키 집합이 다르면 1.0 반환."""
    common_keys = set(pred.keys()) & set(actual.keys())
    if not common_keys:
        return 1.0

    errors = []
    for k in common_keys:
        p_val = float(pred[k]) if isinstance(pred[k], (int, float)) else None
        a_val = float(actual[k]) if isinstance(actual[k], (int, float)) else None
        if p_val is None or a_val is None:
            continue
        denom = max(1e-09, abs(a_val))
        errors.append(abs(p_val - a_val) / denom)

    return sum(errors) / len(errors) if errors else 0.0


# ──────────────────────────────────────────────
# WMQ-2: Calibration ECE
# ──────────────────────────────────────────────


def compute_ece(
    confidences: list[float],
    is_correct: list[bool],
    n_bins: int = 10,
) -> float:
    """ECE = Σ_{m=1}^{M} (|B_m|/n) × |acc(B_m) - conf(B_m)|

    Args:
        confidences: 각 예측의 신뢰도 p̂ ∈ [0,1]
        is_correct:  예측이 정확했는지 여부 (d(â, s̃) ≤ θ_drift)
        n_bins:      등폭 구간 수 (기본 10)

    """
    assert len(confidences) == len(is_correct), "신뢰도/정확도 수 불일치"
    n = len(confidences)
    if n == 0:
        return float("nan")

    bin_size = 1.0 / n_bins
    ece = 0.0

    for m in range(n_bins):
        lower = m * bin_size
        upper = (m + 1) * bin_size
        # 마지막 bin은 upper bound 포함
        in_bin = [
            (c, r)
            for c, r in zip(confidences, is_correct, strict=False)
            if lower <= c < upper or (m == n_bins - 1 and c == 1.0)
        ]
        if not in_bin:
            continue
        bin_n = len(in_bin)
        acc = sum(r for _, r in in_bin) / bin_n
        conf = sum(c for c, _ in in_bin) / bin_n
        ece += (bin_n / n) * abs(acc - conf)

    return ece


def build_correctness_labels(
    predicted_states: list[dict],
    actual_states: list[dict],
    drift_threshold: float = 0.15,
    distance_fn=None,
) -> list[bool]:
    """예측-실제 쌍에서 정확도 레이블 생성 (ECE 입력용)"""
    if distance_fn is None:
        distance_fn = _default_relative_error
    return [
        distance_fn(p, a) <= drift_threshold
        for p, a in zip(predicted_states, actual_states, strict=False)
    ]


# ──────────────────────────────────────────────
# WMQ-3: Prediction Accuracy
# ──────────────────────────────────────────────


def compute_pa(is_correct: list[bool]) -> float:
    """PA = 정확한 예측 수 / 전체 예측 수"""
    if not is_correct:
        return float("nan")
    return sum(is_correct) / len(is_correct)


# ──────────────────────────────────────────────
# WMQ-4: OOD Detection Rate
# ──────────────────────────────────────────────


def compute_odr(
    ood_flags: list[bool],
    is_actually_ood: list[bool],
    confidence_threshold: float = 0.50,
    confidences: list[float] | None = None,
) -> float:
    """ODR = TP_ood / (TP_ood + FN_ood)

    Args:
        ood_flags:       에이전트가 OOD로 표시한 여부 (또는 confidence 기반 도출)
        is_actually_ood: 실제 OOD 여부 (사후 판정)
        confidence_threshold: confidence < 이 값이면 OOD 표시로 간주
        confidences:     confidence 기반 판정 시 사용 (ood_flags 대신)

    """
    if confidences is not None:
        ood_flags = [c < confidence_threshold for c in confidences]

    assert len(ood_flags) == len(is_actually_ood)

    tp = sum(1 for flag, actual in zip(ood_flags, is_actually_ood, strict=False) if flag and actual)
    fn = sum(
        1
        for flag, actual in zip(ood_flags, is_actually_ood, strict=False)
        if not flag and actual
    )

    if tp + fn == 0:
        return float("nan")  # OOD 샘플 없음
    return tp / (tp + fn)


# ──────────────────────────────────────────────
# WMQ-5: World Model Update Latency
# ──────────────────────────────────────────────


def compute_wmul(drift_events: list[dict]) -> float:
    """WMUL = E[t_update - t_detect | drift_event]  (단위: 시간)

    drift_events 각 원소 형식:
    {
        "detect_time": datetime,   # SDR 임계값 초과 시각
        "update_time": datetime,   # WM 업데이트 완료 시각
    }
    """
    if not drift_events:
        return float("nan")

    latencies = []
    for ev in drift_events:
        detect = ev.get("detect_time")
        update = ev.get("update_time")
        if detect is None or update is None:
            continue
        if isinstance(detect, str):
            detect = datetime.fromisoformat(detect)
        if isinstance(update, str):
            update = datetime.fromisoformat(update)
        delta_hours = (update - detect).total_seconds() / 3600
        if delta_hours >= 0:
            latencies.append(delta_hours)

    return sum(latencies) / len(latencies) if latencies else float("nan")


# ──────────────────────────────────────────────
# 통합 WMQ 계산
# ──────────────────────────────────────────────


def compute_wmq(
    predicted_states: list[dict],
    actual_states: list[dict],
    confidences: list[float],
    ood_flags: list[bool] | None = None,
    is_actually_ood: list[bool] | None = None,
    drift_events: list[dict] | None = None,
    drift_threshold: float = 0.15,
    n_ece_bins: int = 10,
) -> WMQResult:
    """15개 지표 중 WMQ 5개를 한 번에 계산.

    Returns:
        WMQResult: 5개 지표 + 정규화 점수 + 범주 점수

    """
    is_correct = build_correctness_labels(predicted_states, actual_states, drift_threshold)

    sdr = compute_sdr(predicted_states, actual_states, drift_threshold)
    ece = compute_ece(confidences, is_correct, n_ece_bins)
    pa = compute_pa(is_correct)

    if ood_flags is not None and is_actually_ood is not None:
        odr = compute_odr(ood_flags, is_actually_ood)
    else:
        odr = float("nan")

    wmul = compute_wmul(drift_events) if drift_events else float("nan")

    # nan 값은 중간값으로 대체 (측정 불가 시 페널티 없음)
    odr_safe = odr if not math.isnan(odr) else 0.65
    wmul_safe = wmul if not math.isnan(wmul) else float("nan")

    return WMQResult(
        sdr=sdr,
        ece=ece,
        pa=pa,
        odr=odr_safe,
        wmul_hours=wmul_safe if not math.isnan(wmul_safe) else float("nan"),
    )
