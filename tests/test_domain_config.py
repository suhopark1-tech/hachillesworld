"""도메인 임계값 YAML + DomainConfig 테스트 — HAW-TR-001 §6.2."""

from __future__ import annotations

import pytest

from hachillesworld.collect.episode import EpisodeRecord
from hachillesworld.core.domain_config import (
    VALID_DOMAINS,
    DomainConfig,
    DriftConfig,
    ThresholdSpec,
)

# ── 픽스처 ────────────────────────────────────────────────────


@pytest.fixture(params=sorted(VALID_DOMAINS))
def domain_name(request):
    return request.param


def make_episode(domain: str = "", **meta) -> EpisodeRecord:
    ep = EpisodeRecord(agent_id="test")
    ep.domain = domain
    ep.metadata = meta
    return ep


# ── YAML 로드 테스트 ──────────────────────────────────────────


class TestYAMLLoadAllDomains:
    def test_all_domains_load_without_error(self, domain_name):
        """6개 도메인 YAML이 모두 오류 없이 로드되어야 한다."""
        cfg = DomainConfig.load(domain_name)
        assert cfg.domain == domain_name

    def test_all_domains_have_laws_type(self, domain_name):
        cfg = DomainConfig.load(domain_name)
        assert cfg.laws_type in ("physical", "digital", "social", "scientific")

    def test_all_domains_have_15_thresholds(self, domain_name):
        """15개 지표 임계값이 모두 정의되어야 한다."""
        cfg = DomainConfig.load(domain_name)
        expected = {
            "sdr",
            "ece",
            "pa",
            "odr",
            "wmul",
            "pd",
            "scr",
            "ca",
            "gar",
            "as_",
            "lcr",
            "hc",
            "hr",
            "irt",
            "su",
        }
        assert set(cfg.thresholds.keys()) == expected

    def test_all_domains_have_dahas_multiplier(self, domain_name):
        cfg = DomainConfig.load(domain_name)
        assert 0.0 < cfg.dahas_multiplier <= 1.0

    def test_all_domains_have_drift_config(self, domain_name):
        cfg = DomainConfig.load(domain_name)
        assert isinstance(cfg.drift_config, DriftConfig)
        assert 0.0 < cfg.drift_config.threshold < 1.0
        assert cfg.drift_config.window_size > 0

    def test_invalid_domain_falls_back_to_supply_chain(self):
        cfg = DomainConfig.load("nonexistent_domain")
        assert cfg.domain == "supply_chain"

    def test_healthcare_is_strictest_sdr(self):
        """Healthcare는 SDR ok 임계값이 가장 낮아야 한다 (가장 엄격)."""
        hc = DomainConfig.load("healthcare")
        sc = DomainConfig.load("supply_chain")
        assert hc.get_threshold("sdr", "ok") < sc.get_threshold("sdr", "ok")

    def test_healthcare_has_lowest_dahas_multiplier(self):
        """Healthcare는 가장 낮은 daHAS 승수를 가져야 한다."""
        multipliers = {d: DomainConfig.load(d).get_dahas_multiplier() for d in VALID_DOMAINS}
        assert multipliers["healthcare"] == min(multipliers.values())

    def test_finance_stricter_than_customer_service(self):
        """Finance는 customer_service보다 SDR ok 임계값이 낮아야 한다."""
        fin = DomainConfig.load("finance")
        cs = DomainConfig.load("customer_service")
        assert fin.get_threshold("sdr", "ok") < cs.get_threshold("sdr", "ok")

    def test_research_has_relaxed_sdr(self):
        """Research는 SDR ok 임계값이 가장 높아야 한다 (탐색적 허용)."""
        res = DomainConfig.load("research")
        sc = DomainConfig.load("supply_chain")
        assert res.get_threshold("sdr", "ok") > sc.get_threshold("sdr", "ok")


# ── 도메인 자동 감지 테스트 ────────────────────────────────────


class TestDomainAutoDetect:
    def test_detect_from_episode_domain_field(self):
        """episode.domain 필드에 유효한 도메인이 있으면 그것을 반환한다."""
        ep = make_episode(domain="healthcare")
        assert DomainConfig.auto_detect(ep) == "healthcare"

    def test_detect_from_metadata_domain(self):
        """episode.domain이 없고 metadata.domain이 있으면 그것을 반환한다."""
        ep = make_episode(domain="", domain_key="finance")
        ep.metadata = {"domain": "finance"}
        assert DomainConfig.auto_detect(ep) == "finance"

    def test_detect_from_keyword_medical(self):
        """metadata에 'medical' 키워드가 있으면 healthcare를 반환한다."""
        ep = make_episode(domain="", description="medical diagnosis agent")
        assert DomainConfig.auto_detect(ep) == "healthcare"

    def test_detect_from_keyword_trading(self):
        ep = make_episode(domain="", task="trading strategy")
        assert DomainConfig.auto_detect(ep) == "finance"

    def test_detect_from_keyword_logistics(self):
        ep = make_episode(domain="", system="logistics optimization")
        assert DomainConfig.auto_detect(ep) == "supply_chain"

    def test_detect_from_keyword_chatbot(self):
        ep = make_episode(domain="", type="chatbot")
        assert DomainConfig.auto_detect(ep) == "customer_service"

    def test_detect_from_keyword_code(self):
        ep = make_episode(domain="", task="code generation")
        assert DomainConfig.auto_detect(ep) == "code_generation"

    def test_detect_from_keyword_research(self):
        ep = make_episode(domain="", context="research experiment")
        assert DomainConfig.auto_detect(ep) == "research"

    def test_fallback_to_supply_chain(self):
        """매칭되는 키워드가 없으면 supply_chain을 반환한다."""
        ep = make_episode(domain="", task="unknown task xyz")
        assert DomainConfig.auto_detect(ep) == "supply_chain"

    def test_invalid_domain_field_uses_keywords(self):
        """episode.domain이 유효하지 않으면 키워드 추론으로 넘어간다."""
        ep = make_episode(domain="unknown", context="medical imaging")
        assert DomainConfig.auto_detect(ep) == "healthcare"

    def test_auto_detect_from_dict_valid_domain(self):
        """dict 에피소드에서 도메인 필드로 감지한다."""
        ep_dict = {"domain": "finance", "agent_id": "a1"}
        assert DomainConfig.auto_detect_from_dict(ep_dict) == "finance"

    def test_auto_detect_from_dict_keyword(self):
        ep_dict = {"agent_id": "banking-agent", "domain": ""}
        assert DomainConfig.auto_detect_from_dict(ep_dict) == "finance"

    def test_auto_detect_from_dict_fallback(self):
        ep_dict = {"agent_id": "general-agent"}
        assert DomainConfig.auto_detect_from_dict(ep_dict) == "supply_chain"


# ── daHAS 자동 적용 테스트 ─────────────────────────────────────


class TestDaHASAutoApply:
    def test_healthcare_multiplier_value(self):
        cfg = DomainConfig.load("healthcare")
        assert cfg.get_dahas_multiplier() == pytest.approx(0.85)

    def test_finance_multiplier_value(self):
        cfg = DomainConfig.load("finance")
        assert cfg.get_dahas_multiplier() == pytest.approx(0.90)

    def test_supply_chain_multiplier_value(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_dahas_multiplier() == pytest.approx(0.95)

    def test_customer_service_multiplier_value(self):
        cfg = DomainConfig.load("customer_service")
        assert cfg.get_dahas_multiplier() == pytest.approx(1.00)

    def test_code_generation_multiplier_value(self):
        cfg = DomainConfig.load("code_generation")
        assert cfg.get_dahas_multiplier() == pytest.approx(1.00)

    def test_research_multiplier_value(self):
        cfg = DomainConfig.load("research")
        assert cfg.get_dahas_multiplier() == pytest.approx(1.00)

    def test_dahas_calculation(self):
        """daHAS = HAS × multiplier 계산이 정확해야 한다."""
        cfg = DomainConfig.load("healthcare")
        has = 800
        dahas = round(has * cfg.get_dahas_multiplier())
        assert dahas == 680  # 800 × 0.85

    def test_dahas_strictest_healthcare(self):
        """동일 HAS에서 healthcare의 daHAS가 가장 낮아야 한다."""
        has = 750
        dahas = {d: round(has * DomainConfig.load(d).get_dahas_multiplier()) for d in VALID_DOMAINS}
        assert dahas["healthcare"] == min(dahas.values())


# ── 임계값 조회 테스트 ─────────────────────────────────────────


class TestThresholdLookup:
    def test_supply_chain_sdr_ok(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("sdr", "ok") == pytest.approx(0.05)

    def test_supply_chain_sdr_warn(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("sdr", "warn") == pytest.approx(0.08)

    def test_supply_chain_sdr_crit(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("sdr", "crit") == pytest.approx(0.15)

    def test_supply_chain_ca_l3(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("ca", "l3") == pytest.approx(0.78)

    def test_supply_chain_ca_l2(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("ca", "l2") == pytest.approx(0.73)

    def test_supply_chain_pd_l3(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("pd", "l3") == pytest.approx(22.0)

    def test_healthcare_ece_ok_stricter(self):
        hc = DomainConfig.load("healthcare")
        assert hc.get_threshold("ece", "ok") == pytest.approx(0.04)

    def test_missing_metric_returns_zero(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("nonexistent_metric", "ok") == pytest.approx(0.0)

    def test_missing_level_returns_zero(self):
        cfg = DomainConfig.load("supply_chain")
        assert cfg.get_threshold("sdr", "l5") == pytest.approx(0.0)

    def test_threshold_spec_dataclass(self):
        spec = ThresholdSpec(data={"ok": 0.05, "warn": 0.10})
        assert spec.get("ok") == pytest.approx(0.05)
        assert spec.get("warn") == pytest.approx(0.10)
        assert spec.get("missing", 99.0) == pytest.approx(99.0)

    def test_drift_config_supply_chain(self):
        cfg = DomainConfig.load("supply_chain")
        dc = cfg.drift_config
        assert dc.threshold == pytest.approx(0.15)
        assert dc.alert_rate == pytest.approx(0.20)
        assert dc.window_size == 20
        assert dc.abruptness_ratio == pytest.approx(2.0)

    def test_drift_config_healthcare_stricter(self):
        """Healthcare drift threshold는 supply_chain보다 낮아야 한다."""
        hc = DomainConfig.load("healthcare")
        sc = DomainConfig.load("supply_chain")
        assert hc.drift_config.threshold < sc.drift_config.threshold
