"""Incident Recovery Time (IRT) 자동 추적 — HAW-TR-001 OHM-4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Incident:
    """인시던트 단위 레코드."""

    incident_id: str
    start_ts: float
    severity: str = "medium"
    recovery_ts: float | None = None

    @property
    def irt_minutes(self) -> float | None:
        if self.recovery_ts is None:
            return None
        return (self.recovery_ts - self.start_ts) / 60.0

    @property
    def is_resolved(self) -> bool:
        return self.recovery_ts is not None


@dataclass
class IRTResult:
    irt_minutes: float
    n_incidents: int
    irt_ok: bool
    incidents: list[dict] = field(default_factory=list)


class IncidentTracker:
    """인시던트 발생~회복 시간 자동 추적기 (HAW-TR-001 OHM-4).

    EpisodeRecord 시퀀스에서 infrastructure_failure 또는 예측 오류 임계값
    초과 구간을 인시던트로 자동 탐지하고 회복 시간을 측정한다.
    logs dict에 incident_start / incident_recovery 이벤트가 있으면
    그것도 활용한다.
    """

    def __init__(
        self,
        ece_crit: float = 0.20,
        ece_warn: float = 0.10,
        irt_ok_minutes: float = 5.0,
    ) -> None:
        self.ece_crit = ece_crit
        self.ece_warn = ece_warn
        self.irt_ok_minutes = irt_ok_minutes
        self._manual: dict[str, Incident] = {}

    # ── 수동 기록 API ─────────────────────────────────────────────

    def record_incident(self, incident_id: str, start_ts: float, severity: str = "medium") -> None:
        """인시던트를 수동으로 기록한다."""
        self._manual[incident_id] = Incident(
            incident_id=incident_id, start_ts=start_ts, severity=severity
        )

    def record_recovery(self, incident_id: str, recovery_ts: float) -> None:
        """인시던트 회복을 수동으로 기록한다."""
        if incident_id in self._manual:
            self._manual[incident_id].recovery_ts = recovery_ts

    # ── 자동 계산 ─────────────────────────────────────────────────

    def compute_irt(
        self,
        episodes: list,  # list[EpisodeRecord]
        logs: list[dict] | None = None,
    ) -> IRTResult:
        """IRT를 자동 계산한다.

        우선순위: episodes → logs → manual → default(0.0)
        """
        if episodes:
            return self._from_episodes(episodes)
        if logs:
            return self._from_logs(logs)
        if self._manual:
            return self._from_manual()
        return IRTResult(irt_minutes=0.0, n_incidents=0, irt_ok=True)

    def _from_episodes(self, episodes: list) -> IRTResult:
        """EpisodeRecord 시퀀스에서 인시던트 자동 탐지·IRT 측정."""
        sorted_eps = sorted(episodes, key=lambda e: e.timestamp)

        incidents_found: list[dict] = []
        irt_values: list[float] = []
        incident_start_ts: float | None = None

        for ep in sorted_eps:
            ts = _parse_ts(ep.timestamp)
            err = ep.max_prediction_error

            is_incident = ep.infrastructure_failure or (err is not None and err > self.ece_crit)
            is_recovery = ep.goal_achieved and (err is None or err <= self.ece_warn)

            if is_incident and incident_start_ts is None:
                incident_start_ts = ts
            elif is_recovery and incident_start_ts is not None:
                irt = (ts - incident_start_ts) / 60.0
                irt_values.append(irt)
                incidents_found.append(
                    {
                        "start_ts": incident_start_ts,
                        "recovery_ts": ts,
                        "irt_minutes": round(irt, 2),
                    }
                )
                incident_start_ts = None

        # 미회복 인시던트: 카운트에 포함하되 IRT 평균에서 제외
        if incident_start_ts is not None:
            incidents_found.append(
                {"start_ts": incident_start_ts, "recovery_ts": None, "irt_minutes": None}
            )

        irt_mean = float(sum(irt_values) / len(irt_values)) if irt_values else 0.0
        return IRTResult(
            irt_minutes=round(irt_mean, 2),
            n_incidents=len(incidents_found),
            irt_ok=irt_mean < self.irt_ok_minutes,
            incidents=incidents_found,
        )

    def _from_logs(self, logs: list[dict]) -> IRTResult:
        """로그에서 incident_start / incident_recovery 이벤트를 탐지한다."""
        starts: dict[str, float] = {}
        irt_values: list[float] = []
        incidents_found: list[dict] = []

        for event in logs:
            et = event.get("event_type", "")
            payload = event.get("payload", {})
            ts = float(payload.get("ts") or payload.get("timestamp") or event.get("ts", 0.0))

            if et == "incident_start":
                inc_id = str(payload.get("incident_id", f"inc_{len(starts)}"))
                if ts > 0:
                    starts[inc_id] = ts
            elif et == "incident_recovery":
                inc_id = str(payload.get("incident_id", ""))
                if inc_id in starts and ts > 0:
                    irt = (ts - starts[inc_id]) / 60.0
                    irt_values.append(irt)
                    incidents_found.append({"incident_id": inc_id, "irt_minutes": round(irt, 2)})
                    del starts[inc_id]

        irt_mean = float(sum(irt_values) / len(irt_values)) if irt_values else 0.0
        return IRTResult(
            irt_minutes=round(irt_mean, 2),
            n_incidents=len(incidents_found) + len(starts),  # 미회복 포함
            irt_ok=irt_mean < self.irt_ok_minutes,
            incidents=incidents_found,
        )

    def _from_manual(self) -> IRTResult:
        """수동 기록된 인시던트에서 IRT 계산."""
        resolved = [inc for inc in self._manual.values() if inc.is_resolved]
        irt_values = [inc.irt_minutes for inc in resolved if inc.irt_minutes is not None]
        irt_mean = float(sum(irt_values) / len(irt_values)) if irt_values else 0.0
        incidents = [
            {
                "incident_id": inc.incident_id,
                "irt_minutes": round(inc.irt_minutes, 2) if inc.irt_minutes else None,
            }
            for inc in self._manual.values()
        ]
        return IRTResult(
            irt_minutes=round(irt_mean, 2),
            n_incidents=len(self._manual),
            irt_ok=irt_mean < self.irt_ok_minutes,
            incidents=incidents,
        )


def _parse_ts(ts_str: str) -> float:
    """ISO 타임스탬프 문자열을 Unix timestamp (float)으로 변환한다."""
    try:
        return datetime.fromisoformat(ts_str).timestamp()
    except (ValueError, TypeError, AttributeError):
        return 0.0
