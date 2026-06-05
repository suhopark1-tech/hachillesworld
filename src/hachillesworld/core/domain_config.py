"""도메인별 진단 임계값 설정 로더 (HAW-TR-001 §6.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from hachillesworld.collect.episode import EpisodeRecord

DOMAINS_DIR = Path(__file__).parent.parent / "scan" / "domains"

VALID_DOMAINS: frozenset[str] = frozenset(
    {
        "supply_chain",
        "healthcare",
        "finance",
        "customer_service",
        "code_generation",
        "research",
    }
)

_DEFAULT_DOMAIN = "supply_chain"

# 키워드 → 도메인 추론 매핑 (우선순위: 사전 정의 순서)
_KEYWORD_MAP: tuple[tuple[str, str], ...] = (
    ("medical", "healthcare"),
    ("hospital", "healthcare"),
    ("patient", "healthcare"),
    ("clinical", "healthcare"),
    ("diagnosis", "healthcare"),
    ("health", "healthcare"),
    ("drug", "healthcare"),
    ("pharmacy", "healthcare"),
    ("financial", "finance"),
    ("trading", "finance"),
    ("banking", "finance"),
    ("investment", "finance"),
    ("payment", "finance"),
    ("fraud", "finance"),
    ("loan", "finance"),
    ("insurance", "finance"),
    ("logistics", "supply_chain"),
    ("inventory", "supply_chain"),
    ("warehouse", "supply_chain"),
    ("shipping", "supply_chain"),
    ("procurement", "supply_chain"),
    ("delivery", "supply_chain"),
    ("support", "customer_service"),
    ("helpdesk", "customer_service"),
    ("chatbot", "customer_service"),
    ("ticket", "customer_service"),
    ("customer", "customer_service"),
    ("coding", "code_generation"),
    ("programming", "code_generation"),
    ("developer", "code_generation"),
    ("software", "code_generation"),
    ("code", "code_generation"),
    ("research", "research"),
    ("experiment", "research"),
    ("scientific", "research"),
    ("hypothesis", "research"),
)


@dataclass
class ThresholdSpec:
    """단일 지표의 임계값 명세 (ok/warn/crit 또는 l1/l2/l3)."""

    data: dict[str, Any] = field(default_factory=dict)

    def get(self, level: str, default: float = 0.0) -> float:
        return float(self.data.get(level, default))


@dataclass
class DriftConfig:
    threshold: float = 0.15
    alert_rate: float = 0.20
    window_size: int = 20
    abruptness_ratio: float = 2.0


@dataclass
class DomainConfig:
    """도메인별 임계값·daHAS 승수·드리프트 설정 컨테이너."""

    domain: str
    laws_type: str
    thresholds: dict[str, ThresholdSpec]
    dahas_multiplier: float
    drift_config: DriftConfig

    # ── 로딩 ─────────────────────────────────────────────────────

    @classmethod
    def load(cls, domain: str) -> DomainConfig:
        """YAML 파일에서 도메인 설정을 로드한다.

        유효하지 않은 도메인은 supply_chain으로 fallback한다.
        """
        safe_domain = domain if domain in VALID_DOMAINS else _DEFAULT_DOMAIN
        yaml_path = DOMAINS_DIR / f"{safe_domain}.yaml"
        if not yaml_path.exists():
            yaml_path = DOMAINS_DIR / f"{_DEFAULT_DOMAIN}.yaml"

        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        thresholds = {k: ThresholdSpec(data=v) for k, v in data.get("thresholds", {}).items()}

        drift_raw = data.get("drift_config", {})
        drift = DriftConfig(
            threshold=float(drift_raw.get("threshold", 0.15)),
            alert_rate=float(drift_raw.get("alert_rate", 0.20)),
            window_size=int(drift_raw.get("window_size", 20)),
            abruptness_ratio=float(drift_raw.get("abruptness_ratio", 2.0)),
        )

        return cls(
            domain=str(data.get("domain", safe_domain)),
            laws_type=str(data.get("laws_type", "digital")),
            thresholds=thresholds,
            dahas_multiplier=float(data.get("dahas_multiplier", 1.0)),
            drift_config=drift,
        )

    # ── 자동 감지 ─────────────────────────────────────────────────

    @staticmethod
    def auto_detect(episode: EpisodeRecord) -> str:
        """EpisodeRecord에서 도메인을 자동 감지한다.

        우선순위:
        1. episode.domain 필드 (명시적 설정)
        2. episode.metadata["domain"]
        3. 메타데이터 값 키워드 추론
        4. fallback: "supply_chain"
        """
        if episode.domain and episode.domain in VALID_DOMAINS:
            return episode.domain

        meta_domain = episode.metadata.get("domain", "")
        if meta_domain and meta_domain in VALID_DOMAINS:
            return str(meta_domain)

        # 메타데이터 전체 텍스트 + domain 필드를 합쳐 키워드 추론
        text_parts = [episode.domain] if episode.domain else []
        text_parts.extend(str(v) for v in episode.metadata.values())
        meta_text = " ".join(text_parts).lower()

        for keyword, domain in _KEYWORD_MAP:
            if keyword in meta_text:
                return domain

        return _DEFAULT_DOMAIN

    @staticmethod
    def auto_detect_from_dict(episode_dict: dict[str, Any]) -> str:
        """dict 형태 에피소드에서 도메인을 자동 감지한다 (validation 모듈 호환)."""
        domain = episode_dict.get("domain", "")
        if domain and domain in VALID_DOMAINS:
            return str(domain)

        meta_domain = episode_dict.get("metadata", {}).get("domain", "")
        if meta_domain and meta_domain in VALID_DOMAINS:
            return str(meta_domain)

        text_parts: list[str] = []
        if domain:
            text_parts.append(domain)
        for key in ("agent_id", "domain", "study_id"):
            val = episode_dict.get(key, "")
            if val:
                text_parts.append(str(val))
        meta_text = " ".join(text_parts).lower()

        for keyword, matched_domain in _KEYWORD_MAP:
            if keyword in meta_text:
                return matched_domain

        return _DEFAULT_DOMAIN

    # ── 조회 ─────────────────────────────────────────────────────

    def get_threshold(self, metric: str, level: str) -> float:
        """지표의 특정 레벨 임계값을 반환한다.

        metric: "sdr", "ece", "pa", ... (15개 지표 약어)
        level:  "ok", "warn", "crit", "l1", "l2", "l3"
        """
        spec = self.thresholds.get(metric)
        if spec is None:
            return 0.0
        return spec.get(level)

    def get_dahas_multiplier(self) -> float:
        return self.dahas_multiplier
