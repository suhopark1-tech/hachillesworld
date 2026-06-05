"""StudyClient — HAW-STUDY-001 연구 참여자용 클라이언트."""

from __future__ import annotations

import functools
import hashlib
import json
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hachillesworld.collect.collector import EpisodeContext, LogCollector
from hachillesworld.collect.episode import EpisodeRecord


# ── 데이터 모델 ────────────────────────────────────────────────────


@dataclass
class StudyEnrollment:
    """HAW-STUDY-001 참여 등록 정보."""

    study_id: str
    org_hash: str       # SHA256(org_name)[:16] — 익명화
    agent_type: str
    domain: str
    consent: bool
    enrolled_at: str
    config_path: str    # haw_study_config.yaml 경로

    def to_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "org_hash": self.org_hash,
            "agent_type": self.agent_type,
            "domain": self.domain,
            "consent": self.consent,
            "enrolled_at": self.enrolled_at,
            "config_path": self.config_path,
        }


@dataclass
class KPIRecord:
    """월별 비즈니스 KPI 제출 단위."""

    study_id: str
    month: str          # YYYY-MM
    kpi_data: dict[str, Any]
    submitted_at: str


@dataclass
class InterimReport:
    """HAW-STUDY-001 중간 분석 보고서."""

    study_id: str
    generated_at: str
    n_episodes: int
    n_days_covered: int
    coverage_pct: float
    has_mean: float | None
    has_std: float | None
    kpi_months_submitted: int
    correlation_rho: float | None
    p_value: float | None
    h1_status: str      # "PASS" | "FAIL" | "INSUFFICIENT_DATA"
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"HAW-STUDY 중간 보고서 ({self.study_id})",
            f"  생성: {self.generated_at}",
            f"  에피소드: {self.n_episodes:,}건",
            f"  수집 기간: {self.n_days_covered}일 (커버리지 {self.coverage_pct:.1%})",
        ]
        if self.has_mean is not None:
            lines.append(f"  HAS 평균: {self.has_mean:.4f}  σ: {self.has_std:.4f}")
        lines.append(f"  KPI 제출 월수: {self.kpi_months_submitted}")
        if self.correlation_rho is not None:
            lines.append(
                f"  ρ(HAS, KPI) = {self.correlation_rho:.4f}  "
                f"p = {self.p_value:.4f}  [{self.h1_status}]"
            )
        else:
            lines.append(f"  H1 상태: {self.h1_status}")
        if self.recommendations:
            lines.append("  권고사항:")
            for rec in self.recommendations:
                lines.append(f"    - {rec}")
        return "\n".join(lines)


class StudyClient:
    """HAW-STUDY-001 횡단 타당도 연구 참여자를 위한 클라이언트.

    LogCollector를 내부적으로 사용하지만 인터페이스를 연구 참여에 최적화한다:
    - `enroll()` 클래스메서드로 study_id 자동 발급 및 SDK 설정 파일 생성
    - `@instrument` 데코레이터로 기존 에이전트에 3줄로 계측 추가
    - `episode()` 컨텍스트 매니저로 세밀한 데이터 수집
    - `submit_kpi()` / `generate_interim_report()`로 연구 진행 관리

    사용 예:
        # 1. 최초 등록
        enrollment = StudyClient.enroll(
            org_name="ACME Corp",
            agent_type="supply_chain_v2",
            domain="supply_chain",
        )

        # 2. 클라이언트 생성
        client = StudyClient(
            study_id=enrollment.study_id,
            agent_id="anon-007",
            domain="supply_chain",
            api_key="haw-...",
        )

        # 3. 에이전트 계측
        @client.instrument
        class SupplyChainAgent:
            def plan(self, state, goal): ...
            def execute(self, action): ...
    """

    _TRACKED_METHODS = {"plan", "execute", "observe", "reflect"}

    def __init__(
        self,
        study_id: str,
        agent_id: str,
        domain: str = "",
        api_key: str = "",
        ingest_url: str = "https://ingest.hachillesworld.ai/v1",
        flush_interval: float = 60.0,
        batch_size: int = 100,
        fallback_path: str | None = None,
        study_base_dir: str | Path = ".haw_study",
    ) -> None:
        self.study_id = study_id
        self.agent_id = agent_id
        self.domain = domain
        self._study_base_dir = Path(study_base_dir)

        self._collector = LogCollector(
            agent_id=agent_id,
            api_key=api_key,
            ingest_url=ingest_url,
            domain=domain,
            study_id=study_id,
            flush_interval=flush_interval,
            batch_size=batch_size,
            fallback_path=fallback_path,
        )
        self._collector.start()

    # ── 등록 (클래스메서드) ──────────────────────────────────────────

    @classmethod
    def enroll(
        cls,
        org_name: str,
        agent_type: str,
        domain: str,
        consent: bool = True,
        study_base_dir: str | Path = ".haw_study",
    ) -> StudyEnrollment:
        """HAW-STUDY-001 참여 등록.

        Args:
            org_name: 참여 기관명 (SHA256 익명화 후 저장)
            agent_type: 에이전트 유형 (예: "supply_chain_v2")
            domain: 운영 도메인 (예: "supply_chain")
            consent: 데이터 수집 동의 여부
            study_base_dir: 로컬 스터디 데이터 저장 디렉토리

        Returns:
            StudyEnrollment (study_id 포함)
        """
        if not consent:
            raise ValueError("데이터 수집 동의(consent=True)가 필요합니다.")

        study_id = f"HAW-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        org_hash = hashlib.sha256(org_name.encode()).hexdigest()[:16]
        enrolled_at = datetime.now(UTC).isoformat()
        base = Path(study_base_dir)

        # 등록 정보 저장
        enroll_dir = base / "enrollments"
        enroll_dir.mkdir(parents=True, exist_ok=True)
        enrollment = StudyEnrollment(
            study_id=study_id,
            org_hash=org_hash,
            agent_type=agent_type,
            domain=domain,
            consent=consent,
            enrolled_at=enrolled_at,
            config_path=str(base / "haw_study_config.yaml"),
        )
        enroll_file = enroll_dir / f"{study_id}.json"
        with enroll_file.open("w", encoding="utf-8") as f:
            json.dump(enrollment.to_dict(), f, ensure_ascii=False, indent=2)

        # SDK 설정 파일 생성
        config_path = base / "haw_study_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_content = (
            f"# HAchillesWorld Study SDK Configuration\n"
            f"# Auto-generated by StudyClient.enroll()\n"
            f"study_id: {study_id}\n"
            f"org_hash: {org_hash}\n"
            f"agent_type: {agent_type}\n"
            f"domain: {domain}\n"
            f"enrolled_at: {enrolled_at}\n"
            f"ingest_url: https://ingest.hachillesworld.ai/v1\n"
            f"flush_interval_sec: 60\n"
            f"batch_size: 100\n"
        )
        with config_path.open("w", encoding="utf-8") as f:
            f.write(config_content)

        return enrollment

    # ── KPI 제출 ─────────────────────────────────────────────────────

    def submit_kpi(
        self,
        kpi_data: dict[str, Any],
        study_id: str | None = None,
        month: str | None = None,
    ) -> KPIRecord:
        """비즈니스 KPI 월별 제출.

        Args:
            kpi_data: KPI 딕셔너리
                      {"task_completion_rate": 0.87, "time_savings_pct": 23.5, ...}
            study_id: 대상 study_id (기본: self.study_id)
            month: 제출 월 YYYY-MM (기본: 현재 월)

        Returns:
            저장된 KPIRecord
        """
        sid = study_id or self.study_id
        current_month = month or datetime.now(UTC).strftime("%Y-%m")
        record = KPIRecord(
            study_id=sid,
            month=current_month,
            kpi_data=kpi_data,
            submitted_at=datetime.now(UTC).isoformat(),
        )
        kpi_dir = self._study_base_dir / "kpi"
        kpi_dir.mkdir(parents=True, exist_ok=True)
        kpi_file = kpi_dir / f"{sid}_{current_month}.json"
        with kpi_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "study_id": record.study_id,
                    "month": record.month,
                    "kpi_data": record.kpi_data,
                    "submitted_at": record.submitted_at,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        return record

    # ── 중간 보고서 ──────────────────────────────────────────────────

    def generate_interim_report(
        self,
        study_id: str | None = None,
    ) -> InterimReport:
        """중간 분석 보고서 생성.

        수집된 에피소드 로그와 KPI 데이터를 기반으로 현재까지의
        연구 진행 상황과 H1 가설 검정 상태를 요약한다.

        Returns:
            InterimReport
        """
        from hachillesworld.collect.log_pipeline import StudyLogPipeline

        sid = study_id or self.study_id
        log_dir = self._study_base_dir / "logs"
        pipeline = StudyLogPipeline(study_id=sid, log_dir=log_dir)

        completeness = pipeline.validate_completeness()
        records = pipeline.aggregate_30day()

        # HAS 프록시: 에피소드 성공률
        success_flags = [1.0 if r.goal_achieved else 0.0 for r in records]
        has_mean: float | None = None
        has_std: float | None = None
        if success_flags:
            has_mean = sum(success_flags) / len(success_flags)
            has_std = statistics.stdev(success_flags) if len(success_flags) > 1 else 0.0

        # KPI 데이터 로드
        kpi_dir = self._study_base_dir / "kpi"
        kpi_records: list[dict[str, Any]] = []
        if kpi_dir.exists():
            for kpi_file in sorted(kpi_dir.glob(f"{sid}_*.json")):
                try:
                    with kpi_file.open(encoding="utf-8") as f:
                        kpi_records.append(json.load(f))
                except (json.JSONDecodeError, OSError):
                    continue

        # 상관 분석 (n >= 5 이상인 경우만)
        correlation_rho: float | None = None
        p_value: float | None = None
        h1_status = "INSUFFICIENT_DATA"

        if len(kpi_records) >= 3 and records:
            try:
                from hachillesworld.analyze.correlation import HASBusinessCorrelation

                # 월별 HAS 평균 vs KPI task_completion_rate
                monthly_has: dict[str, list[float]] = {}
                for r in records:
                    month = r.timestamp[:7]
                    monthly_has.setdefault(month, []).append(1.0 if r.goal_achieved else 0.0)
                monthly_has_avg = {m: sum(v) / len(v) for m, v in monthly_has.items()}

                kpi_map = {
                    kr["month"]: kr["kpi_data"].get("task_completion_rate", 0.0)
                    for kr in kpi_records
                }
                common_months = sorted(set(monthly_has_avg) & set(kpi_map))
                if len(common_months) >= 3:
                    has_series = [monthly_has_avg[m] for m in common_months]
                    kpi_series = [kpi_map[m] for m in common_months]
                    analyzer = HASBusinessCorrelation()
                    result = analyzer.compute_spearman(has_series, kpi_series)
                    correlation_rho = result.rho
                    p_value = result.p_value
                    h1_status = "PASS" if result.h1_passed else "FAIL"
            except Exception:
                pass

        # 권고사항 생성
        recommendations: list[str] = []
        if completeness["coverage_pct"] < 0.90:
            missing_n = len(completeness["missing_days"])
            recommendations.append(f"데이터 수집 공백 {missing_n}일 — SDK 연결 상태 확인 필요")
        if len(kpi_records) == 0:
            recommendations.append("KPI 미제출 — submit_kpi()로 비즈니스 지표 입력 필요")
        if has_mean is not None and has_mean < 0.7:
            recommendations.append(f"에피소드 성공률 {has_mean:.1%} 낮음 — 에이전트 품질 점검 권장")
        if h1_status == "FAIL":
            recommendations.append("H1 가설 미충족 — HAS 지표와 KPI 간 상관관계 재검토 필요")

        return InterimReport(
            study_id=sid,
            generated_at=datetime.now(UTC).isoformat(),
            n_episodes=len(records),
            n_days_covered=completeness["n_days_covered"],
            coverage_pct=completeness["coverage_pct"],
            has_mean=has_mean,
            has_std=has_std,
            kpi_months_submitted=len(kpi_records),
            correlation_rho=correlation_rho,
            p_value=p_value,
            h1_status=h1_status,
            recommendations=recommendations,
        )

    # ── @instrument 데코레이터 ────────────────────────────────────

    def instrument(self, cls: type) -> type:
        """에이전트 클래스에 자동 계측을 추가하는 클래스 데코레이터.

        plan / execute / observe / reflect 메서드를 래핑해
        호출 시간, 오류, 토큰 수(있는 경우)를 자동 수집한다.
        에피소드 경계는 execute 호출 시작/종료로 정의한다.

        사용 예:
            @client.instrument
            class MyAgent:
                def plan(self, state, goal): ...
                def execute(self, action): ...
        """
        collector = self._collector

        for method_name in self._TRACKED_METHODS:
            original = getattr(cls, method_name, None)
            if original is None:
                continue

            if method_name == "execute":
                # execute를 에피소드 경계로 사용
                @functools.wraps(original)
                def _wrapped_execute(
                    self_agent: Any,
                    *args: Any,
                    _orig: Any = original,
                    **kwargs: Any,
                ) -> Any:
                    with collector.episode() as ep:
                        start = time.time()
                        error: str | None = None
                        try:
                            result = _orig(self_agent, *args, **kwargs)
                            return result
                        except Exception as exc:
                            error = str(exc)
                            ep.set_goal(achieved=False, success=False)
                            raise
                        finally:
                            duration_ms = (time.time() - start) * 1000
                            ep.set_metadata("method", "execute")
                            ep.set_metadata("duration_ms", round(duration_ms, 2))
                            if error:
                                ep.set_metadata("error", error)
                            # 결과에 토큰 수가 있으면 자동 추출
                            if hasattr(self_agent, "_last_token_count"):
                                ep.set_tokens(self_agent._last_token_count)

                setattr(cls, method_name, _wrapped_execute)

            else:
                # plan / observe / reflect: AgentEvent로 기록
                @functools.wraps(original)
                def _wrapped(
                    self_agent: Any,
                    *args: Any,
                    _orig: Any = original,
                    _name: str = method_name,
                    **kwargs: Any,
                ) -> Any:
                    start = time.time()
                    error: str | None = None
                    try:
                        result = _orig(self_agent, *args, **kwargs)
                        return result
                    except Exception as exc:
                        error = str(exc)
                        raise
                    finally:
                        duration_ms = (time.time() - start) * 1000
                        # AgentEvent로 기존 client에도 전달 (하위 호환)
                        collector.add(
                            EpisodeRecord(
                                agent_id=collector.agent_id,
                                study_id=collector.study_id,
                                domain=collector.domain,
                                episode_success=(error is None),
                                goal_achieved=(error is None),
                                duration_ms=round(duration_ms, 2),
                                metadata={"method": _name, "error": error},
                            ),
                        )

                setattr(cls, method_name, _wrapped)

        return cls

    # ── 에피소드 컨텍스트 ─────────────────────────────────────────

    def episode(
        self,
        episode_id: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> EpisodeContext:
        """에피소드 컨텍스트 매니저를 반환한다."""
        return self._collector.episode(
            episode_id=episode_id,
            initial_state=initial_state,
        )

    # ── 직접 레코드 추가 ─────────────────────────────────────────

    def add(self, record: EpisodeRecord) -> None:
        """EpisodeRecord를 직접 추가한다."""
        self._collector.add(record)

    # ── 상태 및 flush ─────────────────────────────────────────────

    def flush(self) -> int:
        """버퍼를 즉시 flush한다."""
        return self._collector.flush()

    @property
    def stats(self) -> dict[str, int]:
        return self._collector.stats

    def close(self) -> None:
        """남은 버퍼를 flush하고 클라이언트를 종료한다."""
        self._collector.stop()

    # ── 컨텍스트 매니저 ──────────────────────────────────────────

    def __enter__(self) -> StudyClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
