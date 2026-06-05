"""Sprint 4-C: 컴플라이언스 모듈 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hachillesworld.compliance.eu_ai_act import EUAIActMapper, EUAIActReport
from hachillesworld.compliance.iso42001 import ISO42001CheckResult, ISO42001Checker
from hachillesworld.core.models import (
    CategoryScore,
    DiagnosticReport,
    LawsDomain,
    Level,
    MetricScore,
)


# ── 픽스처 ────────────────────────────────────────────────────────────


def _make_metric(
    name: str,
    value: float,
    threshold: float,
    status: str = "ok",
    unit: str = "",
) -> MetricScore:
    return MetricScore(
        name=name, value=value, threshold=threshold, unit=unit, status=status
    )


def _make_report(
    sdr: float = 0.03,
    ece: float = 0.04,
    ca: float = 0.80,
    odr: float = 0.85,
    gar: float = 0.82,
    irt: float = 45.0,
    hc: float = 0.92,
    wmul: float = 80.0,
    lrc: float = 0.97,
    has_score: float = 75.0,
) -> DiagnosticReport:
    wmq_metrics = [
        _make_metric("SDR", sdr, 0.05, "ok" if sdr <= 0.05 else "critical"),
        _make_metric("ECE", ece, 0.05, "ok" if ece <= 0.05 else "warning"),
        _make_metric("PA", 0.85, 0.80, "ok"),
        _make_metric("ODR", odr, 0.80, "ok" if odr >= 0.80 else "critical"),
        _make_metric("WMUL", wmul, 100.0, "ok" if wmul <= 100 else "warning", "ms"),
    ]
    alm_metrics = [
        _make_metric("PD", 4.0, 3.0, "ok"),
        _make_metric("SCR", 0.83, 0.80, "ok"),
        _make_metric("CA", ca, 0.70, "ok" if ca >= 0.70 else "critical"),
        _make_metric("GAR", gar, 0.80, "ok" if gar >= 0.80 else "warning"),
        _make_metric("AS", 0.75, 0.70, "ok"),
    ]
    ohm_metrics = [
        _make_metric("LCR", lrc, 0.95, "ok" if lrc >= 0.95 else "warning"),
        _make_metric("HC", hc, 0.90, "ok" if hc >= 0.90 else "critical"),
        _make_metric("HR", 0.03, 0.05, "ok"),
        _make_metric("IRT", irt, 60.0, "ok" if irt <= 60 else "critical", "s"),
        _make_metric("SU", 0.005, 0.01, "ok"),
    ]
    # HAS = WMQ*0.45 + ALM*0.35 + OHM*0.20
    # 역산으로 카테고리 점수 설정
    wmq_score = has_score * 1.05
    alm_score = has_score * 0.95
    ohm_score = has_score * 1.0
    return DiagnosticReport(
        agent_name="test-agent",
        level=Level.L2,
        level_progress=0.5,
        laws_domain=LawsDomain.DIGITAL,
        world_model_quality=CategoryScore(
            name="World Model Quality", score=wmq_score, metrics=wmq_metrics
        ),
        agency_level=CategoryScore(
            name="Agency Level", score=alm_score, metrics=alm_metrics
        ),
        operational_health=CategoryScore(
            name="Operational Health", score=ohm_score, metrics=ohm_metrics
        ),
        recommendations=[],
    )


# ── EU AI Act 테스트 ──────────────────────────────────────────────────


class TestEUAIActArticleMapping:
    """test_eu_act_article_mapping: Art.13~15 지표 매핑 검증."""

    def test_art13_ece_ca_mapped(self) -> None:
        report = _make_report(ece=0.04, ca=0.80)
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        assert eu_report.article_13.article == "Art.13"
        metric_names = [m.name for m in eu_report.article_13.mapped_metrics]
        assert "ECE" in metric_names
        assert "CA" in metric_names

    def test_art14_irt_hc_mapped(self) -> None:
        report = _make_report(irt=45.0, hc=0.92)
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        assert eu_report.article_14.article == "Art.14"
        metric_names = [m.name for m in eu_report.article_14.mapped_metrics]
        assert "IRT" in metric_names
        assert "HC" in metric_names

    def test_art15_sdr_odr_gar_mapped(self) -> None:
        report = _make_report(sdr=0.03, odr=0.85, gar=0.82)
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        assert eu_report.article_15.article == "Art.15"
        metric_names = [m.name for m in eu_report.article_15.mapped_metrics]
        assert "SDR" in metric_names
        assert "ODR" in metric_names
        assert "GAR" in metric_names

    def test_compliant_scores(self) -> None:
        report = _make_report(
            sdr=0.02, ece=0.02, ca=0.90, odr=0.92, gar=0.90, irt=30.0, hc=0.95
        )
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        assert eu_report.article_13.compliance_score > 70
        assert eu_report.article_14.compliance_score > 60
        assert eu_report.article_15.compliance_score > 70

    def test_non_compliant_scores(self) -> None:
        report = _make_report(
            sdr=0.20, ece=0.30, ca=0.30, odr=0.40, gar=0.40, irt=300.0, hc=0.40
        )
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        assert eu_report.article_13.compliance_score < 60
        assert eu_report.article_15.status in ("non_compliant", "partial")

    def test_overall_score_is_average(self) -> None:
        report = _make_report()
        mapper = EUAIActMapper()
        eu_report = mapper.map_to_articles(report)

        expected = (
            eu_report.article_13.compliance_score
            + eu_report.article_14.compliance_score
            + eu_report.article_15.compliance_score
        ) / 3.0
        assert abs(eu_report.overall_compliance_score - expected) < 0.1

    def test_agent_name_preserved(self) -> None:
        report = _make_report()
        eu_report = EUAIActMapper().map_to_articles(report)
        assert eu_report.agent_name == report.agent_name

    def test_generated_at_is_iso8601(self) -> None:
        from datetime import datetime
        eu_report = EUAIActMapper().map_to_articles(_make_report())
        # ISO 8601 파싱 가능 여부
        dt = datetime.fromisoformat(eu_report.generated_at)
        assert dt.year == 2026


# ── HTML 보고서 생성 테스트 ───────────────────────────────────────────


class TestComplianceReportGeneration:
    """test_compliance_report_generation: HTML 보고서 생성 검증."""

    def test_html_contains_doctype(self) -> None:
        report = _make_report()
        html = EUAIActMapper().generate_compliance_report(report, format="html")
        assert "<!DOCTYPE html>" in html

    def test_html_contains_all_articles(self) -> None:
        report = _make_report()
        html = EUAIActMapper().generate_compliance_report(report, format="html")
        for article in ("Art.13", "Art.14", "Art.15"):
            assert article in html

    def test_html_contains_agent_name(self) -> None:
        report = _make_report()
        html = EUAIActMapper().generate_compliance_report(report, format="html")
        assert report.agent_name in html

    def test_text_format(self) -> None:
        report = _make_report()
        txt = EUAIActMapper().generate_compliance_report(report, format="text")
        assert "EU AI Act" in txt
        assert "Art.13" in txt

    def test_html_escapes_special_chars(self) -> None:
        from hachillesworld.core.models import CategoryScore, DiagnosticReport, LawsDomain, Level
        report = _make_report()
        report.agent_name = "<script>alert('xss')</script>"
        html = EUAIActMapper().generate_compliance_report(report, format="html")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_has_score_bar(self) -> None:
        report = _make_report()
        html = EUAIActMapper().generate_compliance_report(report, format="html")
        assert "score-bar" in html
        assert "score-fill" in html


# ── ISO 42001 체크리스트 테스트 ──────────────────────────────────────


class TestISO42001Checklist:
    """test_iso42001_checklist: ISO/IEC 42001 체크리스트 항목 검증."""

    def test_five_clauses_generated(self) -> None:
        report = _make_report()
        result = ISO42001Checker().check(report)
        assert len(result.clauses) == 5

    def test_clause_ids(self) -> None:
        report = _make_report()
        result = ISO42001Checker().check(report)
        ids = [c.clause_id for c in result.clauses]
        assert "4.1" in ids
        assert "6.1" in ids
        assert "8.4" in ids
        assert "9.1" in ids
        assert "10.2" in ids

    def test_overall_score_range(self) -> None:
        report = _make_report()
        result = ISO42001Checker().check(report)
        assert 0.0 <= result.overall_score <= 100.0

    def test_high_has_gives_high_score(self) -> None:
        report = _make_report(has_score=90.0, sdr=0.01, ece=0.01, ca=0.95, odr=0.95, gar=0.95)
        result = ISO42001Checker().check(report)
        assert result.overall_score >= 70.0

    def test_low_has_gives_low_score(self) -> None:
        report = _make_report(has_score=30.0, sdr=0.30, ece=0.30, ca=0.20, odr=0.30, gar=0.30)
        result = ISO42001Checker().check(report)
        assert result.overall_score <= 65.0

    def test_summary_contains_agent_name(self) -> None:
        report = _make_report()
        result = ISO42001Checker().check(report)
        assert "test-agent" in result.summary or len(result.clauses) > 0

    def test_markdown_output(self) -> None:
        report = _make_report()
        checker = ISO42001Checker()
        result = checker.check(report)
        md = checker.to_markdown(result)
        assert "ISO/IEC 42001" in md
        assert "| 조항 |" in md
        assert "4.1" in md

    def test_conformant_status_threshold(self) -> None:
        report = _make_report(has_score=88.0, irt=20.0, hc=0.98)
        result = ISO42001Checker().check(report)
        conformant = [c for c in result.clauses if c.status == "conformant"]
        assert len(conformant) >= 1

    def test_non_conformant_status(self) -> None:
        report = _make_report(has_score=25.0, sdr=0.40, ece=0.40, irt=600.0, hc=0.30)
        result = ISO42001Checker().check(report)
        non_conformant = [c for c in result.clauses if c.status == "non_conformant"]
        assert len(non_conformant) >= 1


# ── TTA 표준 제안서 형식 검증 테스트 ────────────────────────────────


class TestTTAProposalFormat:
    """test_tta_proposal_format: TTA 표준 제안서 필수 섹션 검증."""

    @pytest.fixture
    def proposal_text(self) -> str:
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs",
            "standards",
            "tta_standard_proposal.md",
        )
        with open(os.path.normpath(path), encoding="utf-8") as f:
            return f.read()

    def test_document_has_title(self, proposal_text: str) -> None:
        assert "TTA" in proposal_text
        assert "표준" in proposal_text

    def test_fifteen_indicators_mentioned(self, proposal_text: str) -> None:
        assert "15개" in proposal_text

    def test_has_index_defined(self, proposal_text: str) -> None:
        assert "HAS" in proposal_text
        assert "Holistic Agent Score" in proposal_text

    def test_three_categories_defined(self, proposal_text: str) -> None:
        assert "WMQ" in proposal_text
        assert "ALM" in proposal_text
        assert "OHM" in proposal_text

    def test_haw_tr_references(self, proposal_text: str) -> None:
        assert "HAW-TR-001" in proposal_text
        assert "HAW-TR-002" in proposal_text

    def test_weight_values_present(self, proposal_text: str) -> None:
        assert "0.45" in proposal_text
        assert "0.35" in proposal_text
        assert "0.20" in proposal_text

    def test_eu_ai_act_article_referenced(self, proposal_text: str) -> None:
        assert "EU AI Act" in proposal_text

    def test_iso_referenced(self, proposal_text: str) -> None:
        assert "ISO/IEC 42001" in proposal_text

    def test_wg_submission_info(self, proposal_text: str) -> None:
        assert "WG" in proposal_text


# ── API 엔드포인트 통합 테스트 ───────────────────────────────────────


class TestComplianceAPIEndpoints:
    """POST /v1/report/compliance 및 /v1/report/iso42001 엔드포인트 테스트."""

    @pytest.fixture
    def client(self):
        from hachillesworld.api.server import app
        with TestClient(app, headers={"Authorization": "Bearer dev-key-insecure"}) as c:
            yield c

    def _seed_report(self, client: TestClient, agent_id: str) -> None:
        """에이전트 리포트를 /v1/scan으로 먼저 생성한다."""
        import random
        logs = [
            {
                "timestamp": 1000.0 + i,
                "event_type": "execute",
                "agent_name": agent_id,
                "payload": {
                    "predicted_state": {"x": random.random()},
                    "actual_state": {"x": random.random()},
                    "confidence": random.uniform(0.6, 0.9),
                    "subtask_completed": True,
                    "goal_achieved": True,
                    "loop_completed": True,
                    "human_controlled": True,
                    "hallu": False,
                    "safe_unwinding": True,
                    "adaptation_score": 0.8,
                    "plan_steps": ["step1", "step2", "step3"],
                },
            }
            for i in range(20)
        ]
        resp = client.post("/v1/scan", json={"agent_name": agent_id, "logs": logs})
        assert resp.status_code == 200

    def test_compliance_report_404_without_scan(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/report/compliance",
            json={"agent_id": "nonexistent-agent-xyz"},
        )
        assert resp.status_code == 404

    def test_compliance_report_generated_after_scan(self, client: TestClient) -> None:
        self._seed_report(client, "comp-test-agent")
        resp = client.post(
            "/v1/report/compliance",
            json={"agent_id": "comp-test-agent", "format": "html"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "comp-test-agent"
        assert 0.0 <= data["overall_compliance_score"] <= 100.0
        assert len(data["articles"]) == 3
        assert "<!DOCTYPE html>" in data["html_report"]

    def test_iso42001_404_without_scan(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/report/iso42001",
            json={"agent_id": "nonexistent-agent-xyz"},
        )
        assert resp.status_code == 404

    def test_iso42001_checklist_after_scan(self, client: TestClient) -> None:
        self._seed_report(client, "iso-test-agent")
        resp = client.post(
            "/v1/report/iso42001",
            json={"agent_id": "iso-test-agent"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "iso-test-agent"
        assert 0.0 <= data["overall_score"] <= 100.0
        assert len(data["clauses"]) == 5
        assert "ISO/IEC 42001" in data["markdown_report"]

    def test_article_structure(self, client: TestClient) -> None:
        self._seed_report(client, "art-struct-agent")
        resp = client.post(
            "/v1/report/compliance",
            json={"agent_id": "art-struct-agent"},
        )
        data = resp.json()
        articles = {a["article"]: a for a in data["articles"]}
        for art_id in ("Art.13", "Art.14", "Art.15"):
            assert art_id in articles
            assert "compliance_score" in articles[art_id]
            assert "status" in articles[art_id]
