"""Replay Debugger — 실패 에피소드 단계별 재생 + 반사실 분석 (PAT-003)."""

from __future__ import annotations

import json
from collections.abc import Callable
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

    @property
    def success(self) -> bool:
        return len(self.anomaly_frames) == 0


@dataclass
class CounterfactualScenario:
    """단일 반사실 시나리오 (PAT-003)."""

    scenario_id: int
    alternative_action: str
    expected_outcome: str
    success_probability: float


@dataclass
class CounterfactualReport:
    """반사실 분석 결과 보고서 (PAT-003 핵심 출력)."""

    failure_step: int
    failure_type: str  # "world_model_error" | "planning_failure" | "execution_failure"
    counterfactuals: list[CounterfactualScenario]
    root_cause: str
    repair_suggestion: str
    confidence: float


class RootCauseAnalyzer:
    """실패 타임스텝 자동 식별 및 실패 유형 분류 (PAT-003 내부 클래스)."""

    @staticmethod
    def identify_failure_step(session: ReplaySession) -> int:
        """예측-실제 오차 시계열에서 max 오차 위치 탐지."""
        max_error = -1.0
        max_step = session.failure_step  # 기본값: 기존 근본 원인 스텝

        for frame in session.frames:
            error = frame.payload.get("prediction_error", 0.0)
            if isinstance(error, (int, float)) and error > max_error:
                max_error = error
                max_step = frame.step

        # prediction_error 없으면 가장 이른 이상 프레임 사용
        if max_error <= 0 and session.anomaly_frames:
            max_step = session.anomaly_frames[0].step

        return max_step

    _EVENT_TYPE_MAP: dict[str, str] = {
        "observe": "world_model_error",
        "plan": "planning_failure",
        "execute": "execution_failure",
        "error": "execution_failure",
    }

    @staticmethod
    def classify_failure_type(session: ReplaySession, failure_step: int) -> str:
        """
        오차 패턴으로 실패 유형 분류:
        - observe 이벤트 이상 → world_model_error
        - plan 이벤트 이상 → planning_failure
        - execute/error → execution_failure
        시간적 위치 기반 폴백: 초반 → world_model, 중반 → planning, 후반 → execution
        """
        total = len(session.frames)
        if total == 0 or failure_step < 0:
            return "world_model_error"

        if failure_step < total:
            et = session.frames[failure_step].event_type
            by_event = RootCauseAnalyzer._EVENT_TYPE_MAP.get(et)
            if by_event is not None:
                return by_event

        rel = failure_step / max(total - 1, 1)
        if rel < 0.34:
            return "world_model_error"
        if rel < 0.67:
            return "planning_failure"
        return "execution_failure"


class CounterfactualAnalyzer:
    """PAT-003 핵심 — 실패 에피소드 반사실 시나리오 자동 생성."""

    def __init__(self, anthropic_client: Any, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic_client
        self._model = model

    def analyze(
        self,
        session: ReplaySession,
        env_fn: Callable | None = None,
    ) -> CounterfactualReport:
        """
        1. 실패 분기점 자동 탐지 (예측 오차 가장 큰 타임스텝)
        2. LLM으로 반사실 시나리오 3개 생성
        3. 근본 원인 분류 (World Model 오차? 계획 실패? 실행 실패?)
        4. 수정 코드 제안 생성
        """
        failure_step = RootCauseAnalyzer.identify_failure_step(session)
        failure_type = RootCauseAnalyzer.classify_failure_type(session, failure_step)
        counterfactuals = self._generate_counterfactuals(session, failure_step, failure_type)
        repair_suggestion = self._generate_repair_suggestion(failure_type)
        confidence = self._estimate_confidence(session, failure_step, counterfactuals)

        return CounterfactualReport(
            failure_step=failure_step,
            failure_type=failure_type,
            counterfactuals=counterfactuals,
            root_cause=session.root_cause,
            repair_suggestion=repair_suggestion,
            confidence=confidence,
        )

    def _generate_counterfactuals(
        self,
        session: ReplaySession,
        failure_step: int,
        failure_type: str,
    ) -> list[CounterfactualScenario]:
        """LLM으로 반사실 시나리오 3개 생성."""
        failure_frame = (
            session.frames[failure_step] if 0 <= failure_step < len(session.frames) else None
        )
        prompt = self._build_prompt(session, failure_step, failure_frame, failure_type)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_response(response.content[0].text)

    def _build_prompt(
        self,
        session: ReplaySession,
        failure_step: int,
        failure_frame: ReplayFrame | None,
        failure_type: str,
    ) -> str:
        ctx = {
            "episode_id": session.episode_id,
            "agent_name": session.agent_name,
            "total_steps": len(session.frames),
            "failure_step": failure_step,
            "failure_type": failure_type,
            "root_cause": session.root_cause,
            "failure_frame": {
                "event_type": failure_frame.event_type,
                "payload": failure_frame.payload,
                "anomaly_reason": failure_frame.anomaly_reason,
            }
            if failure_frame
            else None,
        }
        schema = (
            '{"scenarios": ['
            '{"scenario_id": 1, "alternative_action": "...", '
            '"expected_outcome": "...", "success_probability": 0.0},'
            '{"scenario_id": 2, ...}, {"scenario_id": 3, ...}],'
            '"repair_suggestion": "..."}'
        )
        return (
            "AI 에이전트 실패 에피소드를 분석하고 반사실 시나리오 3개를 생성해주세요.\n\n"
            f"에피소드 컨텍스트:\n{json.dumps(ctx, ensure_ascii=False, indent=2)}\n\n"
            f"정확히 3개의 반사실 시나리오를 다음 JSON 형식으로 반환해주세요:\n{schema}\n"
            "JSON만 반환하세요."
        )

    def _parse_response(self, text: str) -> list[CounterfactualScenario]:
        """LLM 응답에서 반사실 시나리오 파싱. 실패 시 폴백."""
        try:
            raw = text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            return [
                CounterfactualScenario(
                    scenario_id=int(s.get("scenario_id", i + 1)),
                    alternative_action=str(s.get("alternative_action", "")),
                    expected_outcome=str(s.get("expected_outcome", "")),
                    success_probability=float(s.get("success_probability", 0.5)),
                )
                for i, s in enumerate(data.get("scenarios", [])[:3])
            ]
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return self._fallback_scenarios()

    @staticmethod
    def _generate_repair_suggestion(failure_type: str) -> str:
        """근본 원인 유형별 수정 코드/하네스 규칙 제안."""
        if failure_type == "world_model_error":
            return (
                "하네스 규칙 추가 권장:\n"
                "  IF prediction_error > 0.15:\n"
                "    force_recalibration()\n"
                "    log_drift_event(episode_id, step, error)"
            )
        if failure_type == "planning_failure":
            return (
                "HITL 임계값 조정 권장:\n"
                "  uncertainty_threshold: 현재값 → 현재값 × 0.8\n"
                "  (더 민감한 인간 개입 트리거)"
            )
        return (
            "오류 처리 강화 권장:\n"
            "  try:\n"
            "    agent.execute(action)\n"
            "  except AgentError as e:\n"
            "    agent.rollback_to_checkpoint()\n"
            "    notify_operator(e, episode_id, step)"
        )

    @staticmethod
    def _estimate_confidence(
        session: ReplaySession,
        failure_step: int,
        counterfactuals: list[CounterfactualScenario],
    ) -> float:
        has_anomaly = failure_step >= 0 and bool(session.anomaly_frames)
        base = 0.75 if has_anomaly else 0.45
        return min(base * (len(counterfactuals) / 3.0), 1.0)

    @staticmethod
    def _fallback_scenarios() -> list[CounterfactualScenario]:
        return [
            CounterfactualScenario(
                scenario_id=1,
                alternative_action="force_immediate_recalibration",
                expected_outcome="World Model 재보정으로 예측 오차 감소",
                success_probability=0.75,
            ),
            CounterfactualScenario(
                scenario_id=2,
                alternative_action="trigger_hitl_review",
                expected_outcome="인간 검토로 잘못된 계획 수정",
                success_probability=0.85,
            ),
            CounterfactualScenario(
                scenario_id=3,
                alternative_action="rollback_to_last_checkpoint",
                expected_outcome="안전 상태로 롤백 후 재시도",
                success_probability=0.65,
            ),
        ]


class FailurePatternAccumulator:
    """복수 ReplaySession에서 반복 실패 패턴 누적 → Meta-Harness 연동 (PAT-003 §9.5)."""

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold
        self._counts: dict[str, int] = {}
        self._examples: dict[str, ReplaySession] = {}

    def ingest(self, session: ReplaySession) -> None:
        if session.failure_step < 0:
            return
        frame = session.frames[session.failure_step]
        key = f"{frame.event_type}:{frame.anomaly_reason[:30]}"
        self._counts[key] = self._counts.get(key, 0) + 1
        if key not in self._examples:
            self._examples[key] = session

    def get_recurring_patterns(self) -> list[dict[str, Any]]:
        return [
            {"pattern_key": k, "count": cnt, "example_session": self._examples[k]}
            for k, cnt in self._counts.items()
            if cnt >= self.threshold
        ]


class ReplayDebugger:
    """저장된 에이전트 이벤트 로그를 단계별로 재생해
    실패 원인을 식별한다 (PAT-003).

    사용 예:
        debugger = ReplayDebugger()
        session  = debugger.load(episode_id="ep-001", events=log_events)
        debugger.print_session(session)
    """

    def __init__(
        self,
        drift_threshold: float = 0.15,
        uncertainty_threshold: float = 0.35,
        forbidden_actions: list[str] | None = None,
    ) -> None:
        self.drift_threshold = drift_threshold
        self.uncertainty_threshold = uncertainty_threshold
        self.forbidden_actions = forbidden_actions or [
            "bulk_delete_without_confirmation",
            "external_api_write_unvalidated",
            "budget_threshold_override",
        ]

    def load(
        self,
        episode_id: str,
        events: list[AgentEvent | dict[str, Any]],
    ) -> ReplaySession:
        """이벤트 목록으로부터 재생 세션을 구성한다."""
        normalized = self._normalize_events(events)
        agent_name = normalized[0].agent_name if normalized else "unknown"

        frames = []
        for i, event in enumerate(normalized):
            frame = ReplayFrame(
                step=i,
                event_type=event.event_type,
                timestamp=event.timestamp,
                payload=dict(event.payload),
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

    def analyze_failure(
        self,
        episode_id: str,
        events: list[AgentEvent | dict[str, Any]],
        analyzer: CounterfactualAnalyzer,
    ) -> CounterfactualReport:
        """실패 에피소드를 로드하고 반사실 분석을 수행한다."""
        session = self.load(episode_id=episode_id, events=events)
        return analyzer.analyze(session)

    @classmethod
    def from_drift_monitor(
        cls,
        monitor: Any,
        episode_id: str,
        agent_name: str,
        **kwargs: Any,
    ) -> tuple[ReplayDebugger, ReplaySession]:
        """DriftMonitor의 drift_log에서 ReplaySession을 자동 구성한다.

        드리프트 구간 자동 수신 → 해당 에피소드 Replay 자동 전달 (PAT-003).
        """
        debugger = cls(**kwargs)
        drift_log = monitor.get_drift_log()
        events: list[dict[str, Any]] = [
            {
                "agent_name": agent_name,
                "event_type": "observe",
                "timestamp": dv.timestamp,
                "payload": {
                    "prediction_error": dv.value,
                    "predicted_state": dv.predicted,
                    "actual_state": dv.actual,
                },
            }
            for dv in drift_log
        ]
        session = debugger.load(episode_id=episode_id, events=events)
        return debugger, session

    @staticmethod
    def auto_pr_suggestion(report: CounterfactualReport) -> str:
        """CounterfactualReport → GitHub PR 형식 문자열 출력."""
        scenarios_md = "\n".join(
            f"  {s.scenario_id}. **{s.alternative_action}**\n"
            f"     예상 결과: {s.expected_outcome}\n"
            f"     성공 확률: {s.success_probability:.0%}"
            for s in report.counterfactuals
        )
        return (
            "## [PAT-003 자동 분석] 에이전트 실패 근본 원인 수정 제안\n\n"
            "### 실패 요약\n"
            f"- **실패 스텝**: Step {report.failure_step}\n"
            f"- **실패 유형**: `{report.failure_type}`\n"
            f"- **근본 원인**: {report.root_cause}\n"
            f"- **분석 신뢰도**: {report.confidence:.0%}\n\n"
            "### 반사실 시나리오 (대안 행동)\n"
            f"{scenarios_md}\n\n"
            "### 수정 권고\n"
            f"```python\n{report.repair_suggestion}\n```\n\n"
            "---\n"
            "*자동 생성: HAchillesWorld CounterfactualAnalyzer (PAT-003)*"
        )

    def print_session(self, session: ReplaySession) -> None:
        """재생 세션을 터미널에 출력한다."""
        print(f"\n{'━' * 64}")
        print(f"  Replay Debugger — {session.episode_id}")
        print(f"  에이전트: {session.agent_name}  |  총 스텝: {len(session.frames)}")
        if session.root_cause:
            print(f"  ⚡ 근본 원인: {session.root_cause}")
        print(f"{'━' * 64}")

        for frame in session.frames:
            marker = "🔴" if frame.is_anomaly else "  "
            payload = {k: v for k, v in frame.payload.items() if k != "trace_id"}
            print(f"\n  {marker} Step {frame.step:3d} [{frame.event_type:10s}]")
            if frame.is_anomaly:
                print(f"       ⚠ {frame.anomaly_reason}")
            for k, v in list(payload.items())[:4]:
                print(f"       {k}: {v}")

        print(
            f"\n  이상 프레임: {len(session.anomaly_frames)}건 / "
            f"실패 스텝: Step {session.failure_step}",
        )
        print(f"{'━' * 64}\n")

    def _detect_anomaly(self, frame: ReplayFrame) -> None:
        """이벤트 유형별 이상 감지 기준 적용."""
        p = frame.payload
        if frame.event_type == "observe":
            drift = p.get("prediction_error", 0.0)
            if drift > self.drift_threshold:
                frame.is_anomaly = True
                frame.anomaly_reason = (
                    f"Simulation Drift {drift:.3f} > {self.drift_threshold} "
                    "— 재보정 미실행 여부 확인"
                )
        elif frame.event_type == "plan":
            unc = p.get("uncertainty", 0.0)
            if unc > self.uncertainty_threshold:
                frame.is_anomaly = True
                frame.anomaly_reason = (
                    f"불확실성 {unc:.3f} > {self.uncertainty_threshold} — HITL 트리거 여부 확인"
                )
        elif frame.event_type == "execute":
            action = p.get("action", "")
            if action in self.forbidden_actions:
                frame.is_anomaly = True
                frame.anomaly_reason = f"금지 행동 감지: '{action}' — 하네스 위반"
        elif frame.event_type == "error":
            frame.is_anomaly = True
            frame.anomaly_reason = p.get("error_message", "오류 발생")
        elif frame.event_type == "reflect":
            if p.get("correction_success") is False:
                frame.is_anomaly = True
                frame.anomaly_reason = "자기수정 실패 — 수동 개입 필요"

    @staticmethod
    def _analyze_root_cause(session: ReplaySession) -> None:
        """가장 이른 이상 프레임을 근본 원인으로 판정한다."""
        if not session.anomaly_frames:
            session.root_cause = "명확한 이상 없음 — 추가 조사 필요"
            session.failure_step = -1
            return
        first = session.anomaly_frames[0]
        session.failure_step = first.step
        session.root_cause = f"Step {first.step} ({first.event_type}): {first.anomaly_reason}"

    @staticmethod
    def _normalize_events(events: list[Any]) -> list[AgentEvent]:
        result = []
        for e in events:
            if isinstance(e, AgentEvent):
                result.append(e)
            else:
                result.append(
                    AgentEvent(
                        agent_name=e.get("agent_name", "unknown"),
                        event_type=e.get("event_type", "unknown"),
                        timestamp=e.get("timestamp", 0.0),
                        payload=e.get("payload", {}),
                    )
                )
        return result
