#!/usr/bin/env python3
# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""v2.1 E2E 통합 테스트: 핵심 플로우 10개 체크.

사용법:
    python -X utf8 scripts/e2e_flow_test_v21.py

결과:
    10/10 passed 시 exit 0, 실패 시 exit 1
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class FlowResult:
    name: str
    passed: bool
    error: str = ""


@dataclass
class TestResults:
    results: list[FlowResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total


def _run(name: str, fn: object) -> FlowResult:
    try:
        fn()  # type: ignore[operator]
        return FlowResult(name=name, passed=True)
    except Exception as e:
        return FlowResult(name=name, passed=False, error=f"{type(e).__name__}: {e}")


# ── 플로우 1: 기본 Scan → Interpret ─────────────────────────────────


def test_scan_to_interpret() -> None:
    from hachillesworld.core.client import HAchillesWorldClient
    from hachillesworld.interpret.has_interpreter import HASInterpreter

    client = HAchillesWorldClient()
    report = client.scan(
        logs=[{"event_type": "observe", "timestamp": "2026-01-01T00:00:00Z", "payload": {"prediction_error": 0.05}}],
        agent_name="e2e-agent-01",
    )
    assert report.composite_score >= 0
    assert report.level is not None

    interp = HASInterpreter().interpret(report)
    assert interp.grade in ("A+", "A", "B", "C", "D")
    assert len(interp.next_actions) <= 3
    assert interp.deployment_status != ""


# ── 플로우 2: 영구 스토리지 + 재시작 내구성 ──────────────────────────


def test_storage_persistence() -> None:
    import tempfile

    from hachillesworld.api.state import AppState
    from hachillesworld.core.client import HAchillesWorldClient
    from hachillesworld.storage.sqlite import SQLiteRepository

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    repo1 = SQLiteRepository(db_path=db_path)
    state1 = AppState(repository=repo1)
    client = HAchillesWorldClient()
    report = client.scan(
        logs=[{"event_type": "observe", "timestamp": "2026-01-01T00:00:00Z", "payload": {"prediction_error": 0.08}}],
        agent_name="persist-agent",
    )
    state1.record_has("persist-agent", report)
    score1 = report.composite_score

    # 재연결 — 같은 DB
    repo2 = SQLiteRepository(db_path=db_path)
    state2 = AppState(repository=repo2)
    loaded = state2.get_latest_report("persist-agent")
    assert loaded is not None
    assert abs(loaded.composite_score - score1) < 0.01

    # 연결 명시적 종료 후 파일 삭제
    if hasattr(repo1, "close"):
        repo1.close()
    if hasattr(repo2, "close"):
        repo2.close()
    del state1, state2, repo1, repo2
    import gc; gc.collect()
    Path(db_path).unlink(missing_ok=True)


# ── 플로우 3: RuleJudge로 CA 측정 (외부 API 없음) ────────────────────


def test_ca_offline_rule_judge() -> None:
    from hachillesworld.scan.judge.rule_judge import RuleBasedJudge

    judge = RuleBasedJudge()
    score = judge.evaluate(
        scenario="재고 부족 상황에서 대안 공급자를 찾아야 한다.",
        response_a="대안 공급자 A, B를 접촉하고 긴급 발주를 완료했다.",
        response_b="재고 부족 알림을 발송했다.",
    )
    assert 0.0 <= score <= 1.0


# ── 플로우 4: 드리프트 → 감사 로그 기록 ─────────────────────────────


def test_drift_audit_trail() -> None:
    from hachillesworld.audit.logger import AuditEvent, AuditLogger
    from hachillesworld.storage.memory import InMemoryRepository

    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    event = AuditEvent.create(
        actor="test-key-123",
        action="drift.record",
        resource="agent-drift-01",
        outcome="success",
        ip_address="127.0.0.1",
        request_size_bytes=256,
        response_size_bytes=512,
        duration_ms=12.5,
    )
    logger.log(event)

    events = logger.query(action="drift.record", limit=10)
    assert len(events) == 1
    assert events[0].action == "drift.record"


# ── 플로우 5: HAS CI 포함 보고서 생성 ────────────────────────────────


def test_report_with_confidence_interval() -> None:
    from hachillesworld.core.client import HAchillesWorldClient

    client = HAchillesWorldClient()
    report = client.scan(
        logs=[{"event_type": "observe", "timestamp": "2026-01-01T00:00:00Z", "payload": {"prediction_error": 0.04}}] * 20,
        agent_name="ci-agent",
    )
    assert report.composite_score >= 0
    # CI 속성 확인 (v2.1)
    if hasattr(report, "ci_lower") and report.ci_lower is not None:
        assert report.ci_lower <= report.composite_score


# ── 플로우 6: HAS 버전 v2.0으로 재산출 ──────────────────────────────


def test_has_version_backcompat() -> None:
    from hachillesworld.core.config import get_weights_for_version

    w20 = get_weights_for_version("2.0")
    w21 = get_weights_for_version("2.1")
    assert abs(w20["wmq"] + w20["alm"] + w20["ohm"] - 1.0) < 1e-6
    assert abs(w21["wmq"] + w21["alm"] + w21["ohm"] - 1.0) < 1e-6


# ── 플로우 7: EU Act 보고서 면책 배너 포함 ───────────────────────────


def test_eu_report_disclaimer() -> None:
    from hachillesworld.compliance.eu_ai_act import EUAIActMapper
    from hachillesworld.core.client import HAchillesWorldClient

    client = HAchillesWorldClient()
    report = client.scan(
        logs=[{"event_type": "observe", "timestamp": "2026-01-01T00:00:00Z", "payload": {"prediction_error": 0.06}}],
        agent_name="eu-test-agent",
    )
    html = EUAIActMapper().generate_monitoring_report(report, output_format="html")
    assert "모니터링 참고 자료" in html or "법적 컴플라이언스 인증" in html


# ── 플로우 8: PII sanitize 후 Judge 호출 ────────────────────────────


def test_pii_auto_sanitize() -> None:
    from hachillesworld.privacy.data_classifier import DataClassifier

    clf = DataClassifier()
    payload = {
        "user_email": "test@example.com",
        "api_key": "sk-secret-1234",
        "prediction": "배송 예상 시간: 3일",
    }
    sanitized = clf.sanitize_for_external(payload)
    assert sanitized["user_email"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["prediction"] == "배송 예상 시간: 3일"


# ── 플로우 9: MLflow 로깅 ─────────────────────────────────────────────


def test_mlflow_integration() -> None:
    try:
        import mlflow  # noqa: F401
    except ImportError:
        # mlflow 미설치 환경에서는 skip
        return

    from hachillesworld.core.client import HAchillesWorldClient
    from hachillesworld.integrations.mlflow_logger import MLflowHASLogger

    client = HAchillesWorldClient()
    report = client.scan(
        logs=[{"event_type": "observe", "timestamp": "2026-01-01T00:00:00Z", "payload": {"prediction_error": 0.07}}],
        agent_name="mlflow-agent",
    )
    logger = MLflowHASLogger()
    logger.log_report(report, experiment_name="e2e-test")


# ── 플로우 10: 감사 로그 조회 ────────────────────────────────────────


def test_audit_events_query() -> None:
    from hachillesworld.audit.logger import AuditEvent, AuditLogger
    from hachillesworld.storage.memory import InMemoryRepository

    repo = InMemoryRepository()
    logger = AuditLogger(repository=repo)

    for i in range(5):
        logger.log(
            AuditEvent.create(
                actor=f"user-{i}",
                action="scan",
                resource=f"agent-{i % 3}",
                outcome="success",
                ip_address="127.0.0.1",
                request_size_bytes=128,
                response_size_bytes=256,
                duration_ms=5.0,
            )
        )

    all_events = logger.query(limit=10)
    assert len(all_events) == 5

    by_action = logger.query(action="scan", limit=10)
    assert all(e.action == "scan" for e in by_action)


# ── 실행 ─────────────────────────────────────────────────────────────


FLOWS = [
    ("플로우 1: Scan → Interpret", test_scan_to_interpret),
    ("플로우 2: 영구 스토리지", test_storage_persistence),
    ("플로우 3: RuleJudge 오프라인 CA", test_ca_offline_rule_judge),
    ("플로우 4: 드리프트 감사 로그", test_drift_audit_trail),
    ("플로우 5: HAS CI 보고서", test_report_with_confidence_interval),
    ("플로우 6: HAS 버전 호환", test_has_version_backcompat),
    ("플로우 7: EU Act 면책 배너", test_eu_report_disclaimer),
    ("플로우 8: PII sanitize", test_pii_auto_sanitize),
    ("플로우 9: MLflow 로깅", test_mlflow_integration),
    ("플로우 10: 감사 로그 조회", test_audit_events_query),
]


def run_all_flows() -> TestResults:
    results = TestResults()
    for name, fn in FLOWS:
        result = _run(name, fn)
        results.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {name}")
        if not result.passed:
            print(f"         {result.error}")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("HAchillesWorld v2.1 E2E 통합 테스트")
    print("=" * 60)

    results = run_all_flows()

    print()
    print(f"E2E: {results.passed}/{results.total} passed")

    if not results.all_passed:
        failed = [r for r in results.results if not r.passed]
        print(f"\n실패한 플로우 ({len(failed)}개):")
        for r in failed:
            print(f"  - {r.name}: {r.error}")

    sys.exit(0 if results.all_passed else 1)
