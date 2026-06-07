"""HAchillesWorld 설정 관리."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# ── HAS 가중치 버전 레지스트리 ──────────────────────────────────────
# HAW-STUDY-001 실증 결과(WMQ:ALM:OHM = 0.45:0.35:0.20)를 v2.0부터 반영.
# 새 버전 추가 시 HAS_CURRENT_VERSION만 변경하면 된다.
HAS_WEIGHT_VERSIONS: dict[str, dict[str, object]] = {
    "2.0": {"wmq": 0.45, "alm": 0.35, "ohm": 0.20, "released": "2026-06-06"},
    "2.1": {"wmq": 0.45, "alm": 0.35, "ohm": 0.20, "released": "2026-10-01"},
}
HAS_CURRENT_VERSION: str = "2.1"


def get_weights_for_version(version: str) -> dict[str, float]:
    """지정 버전의 HAS 가중치를 반환한다. 없는 버전이면 ValueError."""
    if version not in HAS_WEIGHT_VERSIONS:
        available = ", ".join(sorted(HAS_WEIGHT_VERSIONS.keys()))
        raise ValueError(f"알 수 없는 HAS 가중치 버전: '{version}'. 사용 가능: {available}")
    entry = HAS_WEIGHT_VERSIONS[version]
    return {k: float(v) for k, v in entry.items() if k != "released"}  # type: ignore[arg-type]


HAS_WEIGHTS: dict[str, float] = get_weights_for_version(HAS_CURRENT_VERSION)

# 초기화용 기본값 스냅샷 (sdk_weight_update 후 롤백 가능)
_DEFAULT_HAS_WEIGHTS: dict[str, float] = dict(HAS_WEIGHTS)


def reset_has_weights() -> None:
    """HAS 가중치를 현재 버전 기본값으로 복원한다."""
    HAS_WEIGHTS.update(_DEFAULT_HAS_WEIGHTS)


class HAchillesWorldSettings(BaseSettings):
    """환경 변수에서 자동 로드되는 설정."""

    model_config = SettingsConfigDict(
        env_prefix="HACHILLESWORLD_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API 인증
    api_key: str = ""
    api_base_url: str = "https://api.hachillesworld.ai/v1"

    # 수집 엔드포인트
    ingest_endpoint: str = "https://ingest.hachillesworld.ai/v1"

    # 진단 기본값 — 도메인별 임계값은 scan/domains/{domain}.yaml 참조
    default_domain: str = "supply_chain"  # 자동 감지 실패 시 fallback 도메인

    # 비용 관련
    monthly_budget_usd: float = 0.0  # 0 = 무제한

    # LLM 설정 (내부 AI 엔진용)
    anthropic_api_key: str = ""
    analysis_model: str = "claude-haiku-4-5-20251001"  # 배치 분석용
    generation_model: str = "claude-sonnet-4-6"  # 로드맵 생성용

    # 로컬 개발
    debug: bool = False
    log_level: str = "INFO"


settings = HAchillesWorldSettings()
