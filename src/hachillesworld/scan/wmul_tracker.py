"""World Model Update Latency (WMUL) 자동 추적 — HAW-TR-001 WMQ-5."""

from __future__ import annotations

from dataclasses import dataclass

from hachillesworld.scan.incident_tracker import _parse_ts


@dataclass
class WMULResult:
    wmul_hours: float
    n_drift_events: int
    wmul_ok: bool


class WMULTracker:
    """SDR 초과 감지 → ECE 회복까지 레이턴시 자동 측정기 (HAW-TR-001 WMQ-5).

    EpisodeRecord 시퀀스에서 max_prediction_error가 sdr_threshold를 초과하는
    시점(드리프트 시작)부터 ece_recovery 이하로 회복되는 시점까지의
    경과 시간을 측정한다. 로그 기반 fallback도 지원한다.
    """

    def __init__(
        self,
        sdr_threshold: float = 0.15,
        ece_recovery: float = 0.10,
        wmul_ok_hours: float = 24.0,
    ) -> None:
        self.sdr_threshold = sdr_threshold
        self.ece_recovery = ece_recovery
        self.wmul_ok_hours = wmul_ok_hours

    def compute_wmul(
        self,
        episodes: list,  # list[EpisodeRecord]
        logs: list[dict] | None = None,
    ) -> WMULResult:
        """WMUL을 자동 계산한다.

        우선순위: episodes → logs → default(0.0)
        """
        if episodes:
            return self._from_episodes(episodes)
        if logs:
            return self._from_logs(logs)
        return WMULResult(wmul_hours=0.0, n_drift_events=0, wmul_ok=True)

    def _from_episodes(self, episodes: list) -> WMULResult:
        """EpisodeRecord 시퀀스에서 SDR→ECE 회복 레이턴시 측정."""
        sorted_eps = sorted(episodes, key=lambda e: e.timestamp)

        drift_ts: float | None = None
        wmul_values: list[float] = []
        n_drift_events = 0

        for ep in sorted_eps:
            ts = _parse_ts(ep.timestamp)
            err = ep.max_prediction_error

            has_sdr_spike = err is not None and err > self.sdr_threshold
            has_recovered = err is not None and err <= self.ece_recovery

            if has_sdr_spike and drift_ts is None:
                drift_ts = ts
                n_drift_events += 1
            elif has_recovered and drift_ts is not None:
                wmul_h = (ts - drift_ts) / 3600.0
                if wmul_h >= 0:
                    wmul_values.append(wmul_h)
                drift_ts = None

        wmul_mean = float(sum(wmul_values) / len(wmul_values)) if wmul_values else 0.0
        return WMULResult(
            wmul_hours=round(wmul_mean, 3),
            n_drift_events=n_drift_events,
            wmul_ok=wmul_mean < self.wmul_ok_hours,
        )

    def _from_logs(self, logs: list[dict]) -> WMULResult:
        """로그에서 recalibrated 이벤트 수를 n_drift_events로 반환한다.

        로그에 타임스탬프가 없으면 wmul_hours=0.0으로 반환한다.
        """
        drift_ts: float | None = None
        wmul_values: list[float] = []
        n_drift_events = 0

        for event in logs:
            et = event.get("event_type", "")
            payload = event.get("payload", {})
            ts = float(payload.get("ts") or payload.get("timestamp") or event.get("ts", 0.0))

            if et == "reflect" and payload.get("recalibrated"):
                n_drift_events += 1
                if ts > 0 and drift_ts is None:
                    drift_ts = ts
            elif et == "reflect" and not payload.get("recalibrated"):
                if drift_ts is not None and ts > drift_ts:
                    wmul_h = (ts - drift_ts) / 3600.0
                    wmul_values.append(wmul_h)
                    drift_ts = None

        wmul_mean = float(sum(wmul_values) / len(wmul_values)) if wmul_values else 0.0
        return WMULResult(
            wmul_hours=round(wmul_mean, 3),
            n_drift_events=n_drift_events,
            wmul_ok=wmul_mean < self.wmul_ok_hours,
        )
