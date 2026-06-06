#!/usr/bin/env python3
# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""HAchillesWorld v2.1 전체 플로우 통합 테스트

처음부터 끝까지:
  에피소드 생성 → Scan → HAS 해석 → 드리프트 → Judge → 컴플라이언스
  → 감사 로그 → PII 필터 → 영구 스토리지 → 다중공선성 → Shapley

사용법:
    python -X utf8 scripts/full_flow_test_v21.py
"""

from __future__ import annotations

import gc
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# ── 패키지 경로 등록 ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── 컬러 출력 유틸 ────────────────────────────────────────────────────
BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
CYAN  = "\033[36m"
YELLOW= "\033[33m"
RESET = "\033[0m"

def ok(msg: str) -> None:
    print(f"  {GREEN}✔{RESET}  {msg}")

def fail(msg: str, err: str) -> None:
    print(f"  {RED}✘{RESET}  {msg}")
    print(f"      {RED}{err}{RESET}")

def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def info(label: str, val: Any) -> None:
    print(f"      {YELLOW}{label:<28}{RESET} {val}")


# ════════════════════════════════════════════════════════════════
# STEP 0: 합성 에피소드 로그 생성
# ════════════════════════════════════════════════════════════════
def _make_logs(n: int = 30, seed: int = 42) -> list[dict[str, Any]]:
    """현실적인 에이전트 에피소드 로그 생성."""
    rng = random.Random(seed)
    logs = []
    base_ts = 1_750_000_000.0
    for i in range(n):
        logs.append({
            "event_type": "observe",
            "timestamp": f"2026-06-{1 + i // 24:02d}T{(i % 24):02d}:00:00Z",
            "agent_name": "supply-chain-agent-v2",
            "payload": {
                "prediction_error": round(rng.uniform(0.03, 0.12), 4),
                "calibration_ece": round(rng.uniform(0.02, 0.08), 4),
                "planning_depth": rng.randint(2, 6),
                "subtask_completion": round(rng.uniform(0.70, 0.95), 3),
                "goal_achieved": rng.random() > 0.15,
                "hitl_triggered": rng.random() < 0.08,
                "incident_occurred": rng.random() < 0.05,
                "ts": base_ts + i * 3600,
            },
        })
    return logs


def _make_metric_matrix(n_agents: int = 25) -> tuple[list[list[float]], list[str]]:
    """다중공선성 분석용 (n_agents × 15) 지표 행렬 생성."""
    rng = random.Random(7)
    metric_names = [
        "SDR","ECE","PA","ODR","WMUL",
        "PD","SCR","CA","GAR","AS",
        "LCR","HC","HR","IRT","SU",
    ]
    matrix: list[list[float]] = []
    for _ in range(n_agents):
        has_base = rng.uniform(0.4, 0.9)
        row = [
            max(0.0, min(1.0, has_base + rng.gauss(0, 0.05)))
            for _ in range(15)
        ]
        matrix.append(row)
    return matrix, metric_names


# ════════════════════════════════════════════════════════════════
# 메인 실행
# ════════════════════════════════════════════════════════════════
def main() -> int:  # noqa: PLR0912, PLR0915
    failures: list[str] = []
    total_start = time.perf_counter()

    print(f"\n{BOLD}{'═'*60}")
    print("  HAchillesWorld v2.1 전체 플로우 통합 테스트")
    print(f"{'═'*60}{RESET}")

    # ── STEP 0: 로그 생성 ────────────────────────────────────────
    section("STEP 0 · 합성 에피소드 로그 생성")
    logs = _make_logs(n=30)
    ok(f"에피소드 로그 {len(logs)}개 생성 완료")
    info("첫 번째 이벤트 타임스탬프", logs[0]["timestamp"])
    info("마지막 이벤트 타임스탬프", logs[-1]["timestamp"])

    # ── STEP 1: Scan (15개 지표 자동 측정) ──────────────────────
    section("STEP 1 · ScanEngine — 15개 지표 자동 측정")
    report = None
    try:
        from hachillesworld.scan.engine import ScanEngine
        t0 = time.perf_counter()
        engine = ScanEngine(config={})
        report = engine.run(logs=logs, agent_name="supply-chain-agent-v2")
        elapsed = time.perf_counter() - t0

        ok(f"DiagnosticReport 생성 완료 ({elapsed*1000:.1f}ms)")
        info("에이전트 이름",    report.agent_name)
        info("역량 레벨",        f"{report.level} ({report.level_label})")
        info("HAS 종합 점수",    f"{report.composite_score:.2f} / 100")
        info("WMQ 점수",         f"{report.world_model_quality.score:.2f}")
        info("ALM 점수",         f"{report.agency_level.score:.2f}")
        info("OHM 점수",         f"{report.operational_health.score:.2f}")
        info("도메인",           str(report.laws_domain))

        all_metrics = (
            report.world_model_quality.metrics
            + report.agency_level.metrics
            + report.operational_health.metrics
        )
        info("측정된 지표 수",   f"{len(all_metrics)}개")
        measured = [m for m in all_metrics if m.value is not None]
        info("유효 지표 수",     f"{len(measured)}개")

        # Critical / Warning 지표 목록
        critical = report.critical_issues
        if critical:
            info("Critical 지표",  ", ".join(m.name for m in critical))
        else:
            info("Critical 지표",  "없음 ✔")

    except Exception as e:
        fail("ScanEngine 실패", str(e))
        failures.append("Step1-Scan")

    # ── STEP 2: HAS 신뢰구간 (CI) ───────────────────────────────
    section("STEP 2 · HAS 신뢰구간 (CI) + 버전 관리")
    try:
        from hachillesworld.core.config import get_weights_for_version, HAS_CURRENT_VERSION

        w20 = get_weights_for_version("2.0")
        w21 = get_weights_for_version("2.1")
        ok("HAS 버전별 가중치 조회 성공")
        info("현재 버전",        HAS_CURRENT_VERSION)
        info("v2.0 WMQ:ALM:OHM", f"{w20['wmq']:.2f}:{w20['alm']:.2f}:{w20['ohm']:.2f}")
        info("v2.1 WMQ:ALM:OHM", f"{w21['wmq']:.2f}:{w21['alm']:.2f}:{w21['ohm']:.2f}")

        if report is not None and hasattr(report, "ci_lower") and report.ci_lower is not None:
            ok("HAS CI 존재 확인")
            info("HAS CI",  f"[{report.ci_lower:.2f}, {report.ci_upper:.2f}]")
        else:
            info("HAS CI", "산출 로직에 의존 (report.composite_score 기반)")
            ok("버전 관리 체계 검증 완료")

    except Exception as e:
        fail("HAS CI / 버전 관리", str(e))
        failures.append("Step2-CI")

    # ── STEP 3: HAS 해석 레이어 ──────────────────────────────────
    section("STEP 3 · HASInterpreter — 등급 + 액션 아이템")
    interp = None
    try:
        from hachillesworld.interpret.has_interpreter import HASInterpreter

        if report is None:
            raise RuntimeError("Step 1 실패로 report 없음")

        interp = HASInterpreter().interpret(report)
        ok("HASInterpretation 생성 완료")
        info("등급",             f"{interp.grade} ({interp.grade_label})")
        info("배포 상태",        interp.deployment_status)
        info("상위 %",          f"{interp.percentile:.1f}%")
        info("예상 개선 폭",     f"+{interp.estimated_improvement:.1f} HAS")
        info("핵심 이슈",        interp.top_issue[:50] + "…" if len(interp.top_issue) > 50 else interp.top_issue)
        if interp.next_actions:
            info("액션 수",      f"{len(interp.next_actions)}개")
            for idx, act in enumerate(interp.next_actions, 1):
                info(f"  액션 {idx} ({act.metric})", act.action[:45] + "…" if len(act.action) > 45 else act.action)
        else:
            info("액션", "없음 (이미 우수)")
    except Exception as e:
        fail("HASInterpreter", str(e))
        failures.append("Step3-Interpret")

    # ── STEP 4: 드리프트 모니터링 ────────────────────────────────
    section("STEP 4 · DriftMonitor — 시뮬레이션 드리프트 감지")
    try:
        from hachillesworld.operate.monitor import DriftMonitor

        monitor = DriftMonitor(agent_name="supply-chain-agent-v2")
        rng2 = random.Random(99)
        n_drifted = 0
        for i, log in enumerate(logs[:20]):
            payload = log["payload"]
            pred_err = payload.get("prediction_error", 0.05)
            # 일부러 드리프트를 유발 (10번 이후 에러 증가)
            if i > 10:
                pred_err += 0.08
            alert = monitor.record(
                {"prediction_error": round(pred_err, 4)},
                {"actual_error": round(pred_err * rng2.uniform(0.8, 1.2), 4)},
            )
            if alert:
                n_drifted += 1

        drift_log = monitor.get_drift_log()
        ok(f"드리프트 기록 {len(drift_log)}개")
        info("드리프트 알림 횟수",   f"{n_drifted}회")
        if drift_log:
            info("최신 드리프트 값",  f"{drift_log[-1].value:.4f}")
            info("드리프트 임계값",   f"{monitor.threshold:.3f}")

    except Exception as e:
        fail("DriftMonitor", str(e))
        failures.append("Step4-Drift")

    # ── STEP 5: LLM-as-Judge (RuleBasedJudge) ────────────────────
    section("STEP 5 · RuleBasedJudge — 오프라인 CA 측정")
    try:
        from hachillesworld.scan.judge.rule_judge import RuleBasedJudge

        judge = RuleBasedJudge()
        scenarios = [
            (
                "공급망 대란 발생 시 대안 공급자를 확보해야 한다.",
                "대안 공급자 A, B를 즉시 접촉하고 긴급 발주를 완료했다. 만약 재고가 3일 이내 소진된다면 C사도 활용한다.",
                "재고 부족 알림을 발송했다.",
            ),
            (
                "서버 장애 발생 시 서비스 복구 방법을 선택해야 한다.",
                "주 서버가 다운되면 자동 장애조치로 백업 서버로 전환하고 알림을 발송한다.",
                "서버 상태를 확인하고 대기한다.",
            ),
        ]
        scores = []
        for sc, ra, rb in scenarios:
            s = judge.evaluate(scenario=sc, response_a=ra, response_b=rb)
            scores.append(s)
        avg = sum(scores) / len(scores)
        ok(f"CA 측정 완료 (시나리오 {len(scores)}개)")
        info("CA 점수들",         " / ".join(f"{s:.3f}" for s in scores))
        info("평균 CA 점수",      f"{avg:.3f}")
        info("결정론적 Judge",    str(judge.is_deterministic))

    except Exception as e:
        fail("RuleBasedJudge", str(e))
        failures.append("Step5-Judge")

    # ── STEP 6: EU AI Act 모니터링 보고서 ────────────────────────
    section("STEP 6 · EU AI Act 모니터링 참고 보고서 생성")
    try:
        from hachillesworld.compliance.eu_ai_act import EUAIActMapper

        if report is None:
            raise RuntimeError("Step 1 실패로 report 없음")

        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        ok("EU AI Act 매핑 완료")
        info("종합 모니터링 점수",  f"{eu_report.overall_compliance_score:.1f}/100")
        info("전체 상태",           eu_report.overall_status)
        for art in eu_report.articles:
            info(f"  {art.article} ({art.title[:15]}…)", f"{art.compliance_score:.1f} [{art.status}]")

        html = mapper.generate_monitoring_report(report, output_format="html")
        assert "모니터링 참고 자료" in html or "법적 컴플라이언스 인증" in html
        assert "자동 매핑" not in html  # D-1 수정 확인
        ok("면책 배너 확인 ✔  (D-1 표현 수정 확인)")
        info("HTML 보고서 크기",    f"{len(html):,}자")

        txt = mapper.generate_monitoring_report(report, output_format="text")
        ok("텍스트 보고서 생성 완료")
        info("텍스트 보고서 크기",  f"{len(txt):,}자")

    except Exception as e:
        fail("EUAIActMapper", str(e))
        failures.append("Step6-EUAct")

    # ── STEP 7: ISO 42001 체크리스트 ─────────────────────────────
    section("STEP 7 · ISO/IEC 42001:2023 체크리스트 생성")
    try:
        from hachillesworld.compliance.iso42001 import ISO42001Checker

        if report is None:
            raise RuntimeError("Step 1 실패로 report 없음")

        iso_mapper = ISO42001Checker()
        iso_result = iso_mapper.check(report)

        ok("ISO 42001 매핑 완료")
        info("전체 준수율",          f"{iso_result.overall_score:.1f}%")
        info("조항 수",              f"{len(iso_result.clauses)}개")
        for clause in iso_result.clauses:
            flag = "✔" if clause.status == "compliant" else ("△" if clause.status == "partial" else "✘")
            info(f"  §{clause.clause_id} {clause.title[:20]}…", f"{clause.score:.1f} {flag}")

        report_md = iso_mapper.to_markdown(iso_result)
        ok("마크다운 보고서 생성 완료")
        info("보고서 크기",          f"{len(report_md):,}자")

    except Exception as e:
        fail("ISO42001Mapper", str(e))
        failures.append("Step7-ISO42001")

    # ── STEP 8: PII 필터링 ───────────────────────────────────────
    section("STEP 8 · DataClassifier — PII 탐지 + Sanitize")
    try:
        from hachillesworld.privacy.data_classifier import DataClassifier

        clf = DataClassifier()

        # 탐지 테스트
        sensitive_payload: dict[str, Any] = {
            "user_email": "alice@example.com",
            "api_key": "sk-secret-abc123",
            "ssn": "123-45-6789",
            "message": "배송지: 서울시 강남구",
            "prediction": "재고 3일치 남음",
        }
        result = clf.classify(sensitive_payload)
        ok(f"PII 탐지 완료: contains_pii={result.contains_pii}")
        info("PII 키",             ", ".join(result.pii_keys) if result.pii_keys else "없음")
        info("외부 전송 안전",     str(result.safe_to_transmit))

        # Sanitize 테스트
        sanitized = clf.sanitize_for_external(sensitive_payload)
        assert sanitized["user_email"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["prediction"] == "재고 3일치 남음"
        ok("Sanitize 완료 ✔ (PII 필드 마스킹, 비PII 필드 유지)")
        info("user_email 후",      sanitized["user_email"])
        info("api_key 후",         sanitized["api_key"])
        info("prediction 후",      sanitized["prediction"])

    except Exception as e:
        fail("DataClassifier", str(e))
        failures.append("Step8-PII")

    # ── STEP 9: 감사 로그 ────────────────────────────────────────
    section("STEP 9 · AuditLogger — API 호출 감사 기록")
    try:
        from hachillesworld.audit.logger import AuditEvent, AuditLogger
        from hachillesworld.storage.memory import InMemoryRepository

        repo = InMemoryRepository()
        logger = AuditLogger(repository=repo)

        actions = [
            ("user-abc12345", "scan",          "supply-chain-agent-v2", "success"),
            ("user-abc12345", "interpret",     "supply-chain-agent-v2", "success"),
            ("user-abc12345", "drift.record",  "supply-chain-agent-v2", "success"),
            ("admin-xyz98765","compliance",    "supply-chain-agent-v2", "success"),
            ("user-abc12345", "scan",          "finance-agent-v1",      "not_found"),
        ]
        for actor, action, resource, outcome in actions:
            logger.log(AuditEvent.create(
                actor=actor, action=action, resource=resource, outcome=outcome,
                ip_address="10.0.0.1", request_size_bytes=512,
                response_size_bytes=1024, duration_ms=18.5,
            ))

        all_events = logger.query(limit=100)
        scan_events = logger.query(action="scan", limit=100)
        ok(f"감사 로그 {len(all_events)}개 기록 완료")
        info("전체 이벤트",       f"{len(all_events)}개")
        info("scan 이벤트",       f"{len(scan_events)}개")
        actors = {e.actor for e in all_events}
        info("고유 actor 수",     f"{len(actors)}개")

    except Exception as e:
        fail("AuditLogger", str(e))
        failures.append("Step9-Audit")

    # ── STEP 10: 영구 스토리지 (SQLite) ──────────────────────────
    section("STEP 10 · SQLiteRepository — 영구 저장 + 재시작 복원")
    db_path = None
    try:
        from hachillesworld.api.state import AppState
        from hachillesworld.storage.sqlite import SQLiteRepository

        if report is None:
            raise RuntimeError("Step 1 실패로 report 없음")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        repo1 = SQLiteRepository(db_path=db_path)
        state1 = AppState(repository=repo1)
        state1.record_has("supply-chain-agent-v2", report)
        saved_score = report.composite_score
        ok(f"SQLite 저장 완료 (score={saved_score:.2f})")
        info("DB 파일",           db_path)

        # 재연결 후 복원
        repo2 = SQLiteRepository(db_path=db_path)
        state2 = AppState(repository=repo2)
        loaded = state2.get_latest_report("supply-chain-agent-v2")

        assert loaded is not None
        assert abs(loaded.composite_score - saved_score) < 0.01
        ok("재시작 후 복원 성공 ✔")
        info("복원된 HAS 점수",    f"{loaded.composite_score:.2f}")
        info("레벨 일치",          f"{loaded.level} == {report.level}")

        # HAS 시계열 이력
        history = state2.get_has_timeseries("supply-chain-agent-v2")
        info("HAS 이력 개수",      f"{len(history)}개")

        # 연결 종료
        if hasattr(repo1, "close"): repo1.close()
        if hasattr(repo2, "close"): repo2.close()
        del state1, state2, repo1, repo2
        gc.collect()

    except Exception as e:
        fail("SQLiteRepository", str(e))
        failures.append("Step10-Storage")
    finally:
        if db_path:
            Path(db_path).unlink(missing_ok=True)

    # ── STEP 11: MLflow 로깅 ─────────────────────────────────────
    section("STEP 11 · MLflowHASLogger — 실험 추적")
    try:
        import mlflow  # noqa: F401
        from hachillesworld.integrations.mlflow_logger import MLflowHASLogger

        if report is None:
            raise RuntimeError("Step 1 실패로 report 없음")

        logger_ml = MLflowHASLogger()
        logger_ml.log_report(report, experiment_name="full-flow-test-v21")
        ok("MLflow 로깅 완료")

    except ImportError:
        info("MLflow", "미설치 — 건너뜀 (선택적 의존성)")
        ok("건너뜀 (정상)")
    except Exception as e:
        fail("MLflowHASLogger", str(e))
        failures.append("Step11-MLflow")

    # ── STEP 12: 다중공선성 분석 ─────────────────────────────────
    section("STEP 12 · MulticollinearityAnalyzer — VIF + Spearman 상관")
    try:
        from hachillesworld.analyze.multicollinearity import MulticollinearityAnalyzer

        matrix, metric_names = _make_metric_matrix(n_agents=30)
        mc_analyzer = MulticollinearityAnalyzer()
        mc_report = mc_analyzer.analyze(matrix, metric_names)

        ok(f"다중공선성 분석 완료 ({len(metric_names)}개 지표 × {len(matrix)}개 에이전트)")
        info("고상관 쌍 수 (|r|>0.6)", f"{len(mc_report.high_correlation_pairs)}개")
        info("문제 지표 수 (VIF>10)", f"{len(mc_report.problematic_metrics)}개")
        if mc_report.problematic_metrics:
            info("VIF>10 지표",    ", ".join(mc_report.problematic_metrics[:5]))
        if mc_report.high_correlation_pairs:
            top = sorted(mc_report.high_correlation_pairs, key=lambda x: -abs(x[2]))[:3]
            for a, b, r in top:
                info(f"  최고상관 {a}↔{b}", f"r={r:+.4f}")
        info("권고사항 요약", mc_report.recommendation[:60] + "…")

    except Exception as e:
        fail("MulticollinearityAnalyzer", str(e))
        failures.append("Step12-Multicollinearity")

    # ── STEP 13: Shapley 가중치 재산출 ───────────────────────────
    section("STEP 13 · StudyAnalyzer — Shapley 가중치 재산출")
    try:
        from hachillesworld.analyze.multicollinearity import MulticollinearityAnalyzer
        from hachillesworld.analyze.study_analysis import StudyAnalyzer

        sa = StudyAnalyzer()
        dataset = sa.load_study_data("HAW-STUDY-001")
        ok(f"HAW-STUDY-001 로드 완료 (n={dataset.n}, source={dataset.data_source})")

        # H1 가설 검증
        h1 = sa.compute_h1_hypothesis(dataset, n_bootstrap=200)
        ok("H1 가설 검증 완료")
        info("Spearman ρ (HAS↔KPI)", f"{h1.rho:.4f}")
        info("p-value",              f"{h1.p_value:.6f}")
        info("95% CI",               f"[{h1.ci_lower:.4f}, {h1.ci_upper:.4f}]")
        info("H1 통과",              str(h1.h1_passed))

        # 기본 Shapley 재산출
        weights = sa.shapley_recalibration(dataset)
        ok("Shapley 가중치 재산출 완료")
        info("WMQ 가중치",   f"{weights.wmq:.3f} ({weights.wmq*100:.1f}%)")
        info("ALM 가중치",   f"{weights.alm:.3f} ({weights.alm*100:.1f}%)")
        info("OHM 가중치",   f"{weights.ohm:.3f} ({weights.ohm*100:.1f}%)")
        info("source",       weights.source)

        # 다중공선성 보고서 기반 조정 Shapley
        mc_analyzer2 = MulticollinearityAnalyzer()
        study_matrix = [
            [record.metric_scores.get(m, 0.5) for m in [
                "SDR","ECE","PA","ODR","WMUL",
                "PD","SCR","CA","GAR","AS",
                "LCR","HC","HR","IRT","SU",
            ]]
            for record in dataset.records
        ]
        study_metric_names = ["SDR","ECE","PA","ODR","WMUL","PD","SCR","CA","GAR","AS","LCR","HC","HR","IRT","SU"]
        mc_study_report = mc_analyzer2.analyze(study_matrix, study_metric_names)
        adj_weights = sa.shapley_with_correlation_adjustment(dataset, mc_study_report)
        ok("상관 조정 Shapley 완료")
        info("조정 source",  adj_weights.source)
        info("WMQ (조정)",   f"{adj_weights.wmq:.3f}")

        # 도메인별 부분 집단 분석
        subgroup = sa.domain_subgroup_analysis(dataset)
        ok(f"도메인별 분석 완료 ({len(subgroup.domain_results)}개 도메인)")
        info("전체 ρ",       f"{subgroup.overall_rho:.4f}")
        for dom, res in list(subgroup.domain_results.items())[:3]:
            sig = "*" if res.significant else " "
            info(f"  {dom[:20]}", f"ρ={res.rho:+.4f}{sig}")

    except Exception as e:
        fail("StudyAnalyzer / Shapley", str(e))
        failures.append("Step13-Shapley")

    # ── STEP 14: 드리프트 → Replay Debugger ──────────────────────
    section("STEP 14 · ReplayDebugger — 실패 에피소드 재생")
    try:
        from hachillesworld.operate.monitor import DriftMonitor
        from hachillesworld.operate.replay import ReplayDebugger

        mon = DriftMonitor(agent_name="replay-test-agent")
        rng3 = random.Random(1)
        for i in range(15):
            err = 0.05 + (0.15 if i > 8 else 0.0) + rng3.gauss(0, 0.01)
            mon.record(
                {"prediction_error": err},
                {"actual_error": err * rng3.uniform(0.9, 1.1)},
            )

        debugger, session = ReplayDebugger.from_drift_monitor(
            monitor=mon, episode_id="ep-debug-001", agent_name="replay-test-agent"
        )
        ok(f"ReplaySession 생성 완료 (프레임 {len(session.frames)}개)")
        info("에피소드 ID",       session.episode_id)
        info("에이전트명",        session.agent_name)

    except Exception as e:
        fail("ReplayDebugger", str(e))
        failures.append("Step14-Replay")

    # ── STEP 15: MetaHarness ─────────────────────────────────────
    section("STEP 15 · MetaHarness — 하네스 규칙 자동 학습")
    try:
        from hachillesworld.operate.meta_harness import MetaHarness
        from hachillesworld.optimize.harness_generator import HarnessRule

        harness = MetaHarness()
        rule = HarnessRule(
            rule_id="rule-drift-block-001",
            condition="sdr > 0.08",
            action="pause_and_alert",
            severity="high",
            source="meta_harness",
        )
        conflicts = harness.propose_rule(rule)
        pending = harness.get_pending_rules()
        ok(f"규칙 제안 완료 (pending={len(pending)}개, conflicts={len(conflicts)}개)")
        info("제안 규칙 ID",      pending[0].rule_id if pending else "없음")
        info("조건",              pending[0].condition if pending else "없음")

    except Exception as e:
        fail("MetaHarness", str(e))
        failures.append("Step15-MetaHarness")

    # ── STEP 16: SDK 버전 정보 최종 확인 ─────────────────────────
    section("STEP 16 · 패키지 버전 + 최종 검증")
    try:
        import importlib.metadata as meta
        version = meta.version("hachillesworld")
        ok(f"hachillesworld {version} 확인")
        info("패키지 버전",  version)

        # "자동 매핑" 잔존 확인
        from hachillesworld.compliance.eu_ai_act import EUAIActMapper as _M
        src = _M.generate_monitoring_report.__doc__ or ""
        assert "자동 매핑" not in src
        ok("D-1 법적 표현 수정 최종 확인 ✔")

        from hachillesworld.core.config import HAS_WEIGHTS
        total = sum(HAS_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-6
        ok(f"HAS_WEIGHTS 합계 1.0 확인 ✔ ({total:.6f})")

    except Exception as e:
        fail("최종 검증", str(e))
        failures.append("Step16-Final")

    # ════════════════════════════════════════════════════════════
    # 결과 요약
    # ════════════════════════════════════════════════════════════
    elapsed_total = time.perf_counter() - total_start
    total_steps = 16
    passed_steps = total_steps - len(failures)

    print(f"\n{BOLD}{'═'*60}")
    print(f"  전체 플로우 결과: {passed_steps}/{total_steps} PASS")
    print(f"  총 소요 시간: {elapsed_total:.2f}초")
    print(f"{'═'*60}{RESET}")

    if failures:
        print(f"\n{RED}{BOLD}실패 Step: {', '.join(failures)}{RESET}")
        return 1

    print(f"\n{GREEN}{BOLD}✔ 모든 플로우 정상 통과 — v2.1 릴리스 준비 완료!{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
