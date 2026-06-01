"""Replay Debugger — 실패 에피소드 단계별 재생."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hachillesworld.core.models import AgentEvent


@dataclass
class ReplayFrame:
    """재생 프레임 — 단일 스텝의 상태 스냅샷."""
    step: int
    event_type: str
    timestamp: float
    payload: dict[str, Any]
    is_anomaly: bool = False
    anomaly_reason: str = ""


@dataclass
class ReplaySession:
    """하나의 에피소드 재생 세션."""
    episode_id: str
    agent_name: str
    frames: list[ReplayFrame] = field(default_factory=list)
    root_cause: str = ""
    failure_step: int = -1

    @property
    def anomaly_frames(self) -> list[ReplayFrame]:
        return [f for f in self.frames if f.is_anomaly]


class ReplayDebugger:
    """
    저장된 에이전트 이벤트 로그를 단계별로 재생해
    실패 원인을 식별한다.

    사용 예:
        debugger = ReplayDebugger()
        session  = debugger.load(episode_id="ep-001", events=log_events)
        debugger.print_session(session)
    """

    def load(
        self,
        episode_id: str,
        events: list[AgentEvent | dict[str, Any]],
    ) -> ReplaySession:
        """이벤트 목록으로부터 재생 세션을 구성한다."""
        normalized = [
            e if isinstance(e, AgentEvent)
            else AgentEvent(
                agent_name=e.get("agent_name", "unknown"),
                event_type=e.get("event_type", "unknown"),
                timestamp=e.get("timestamp", 0.0),
                payload=e.get("payload", {}),
            )
            for e in events
        ]

        agent_name = normalized[0].agent_name if normalized else "unknown"
        frames     = []
        for i, event in enumerate(normalized):
            frame = ReplayFrame(
                step=i,
                event_type=event.event_type,
                timestamp=event.timestamp,
                payload=event.payload,
            )
            self._detect_anomaly(frame)
            frames.append(frame)

        session = ReplaySession(
            episode_id=episode_id,
            agent_name=agent_name,
            frames=frames,
        )
        self._analyze_root_cause(session)
        return session

    def print_session(self, session: ReplaySession) -> None:
        """재생 세션을 터미널에 출력한다."""
        print(f"\n{'━'*64}")
        print(f"  Replay Debugger — {session.episode_id}")
        print(f"  에이전트: {session.agent_name}  |  총 스텝: {len(session.frames)}")
        if session.root_cause:
            print(f"  ⚡ 근본 원인: {session.root_cause}")
        print(f"{'━'*64}")

        for frame in session.frames:
            marker  = "🔴" if frame.is_anomaly else "  "
            payload = {k: v for k, v in frame.payload.items() if k != "trace_id"}
            print(f"\n  {marker} Step {frame.step:3d} [{frame.event_type:10s}]")
            if frame.is_anomaly:
                print(f"       ⚠ {frame.anomaly_reason}")
            for k, v in list(payload.items())[:4]:
                print(f"       {k}: {v}")

        print(f"\n  이상 프레임: {len(session.anomaly_frames)}건 / "
              f"실패 스텝: Step {session.failure_step}")
        print(f"{'━'*64}\n")

    @staticmethod
    def _detect_anomaly(frame: ReplayFrame) -> None:
        """단일 프레임에서 이상 신호를 감지한다."""
        p = frame.payload
        if frame.event_type == "observe":
            drift = p.get("prediction_error", 0.0)
            if drift > 0.15:
                frame.is_anomaly   = True
                frame.anomaly_reason = (
                    f"Simulation Drift {drift:.3f} > 0.15 — 재보정 미실행 여부 확인"
                )
        elif frame.event_type == "plan":
            unc = p.get("uncertainty", 0.0)
            if unc > 0.35:
                frame.is_anomaly   = True
                frame.anomaly_reason = (
                    f"불확실성 {unc:.3f} > 0.35 — HITL 트리거 여부 확인"
                )
        elif frame.event_type == "error":
            frame.is_anomaly   = True
            frame.anomaly_reason = p.get("error_message", "오류 발생")

    @staticmethod
    def _analyze_root_cause(session: ReplaySession) -> None:
        """가장 이른 이상 프레임을 근본 원인으로 판정한다."""
        if not session.anomaly_frames:
            session.root_cause  = "명확한 이상 없음 — 추가 조사 필요"
            session.failure_step = -1
            return

        first = session.anomaly_frames[0]
        session.failure_step = first.step
        session.root_cause   = (
            f"Step {first.step} ({first.event_type}): {first.anomaly_reason}"
        )
