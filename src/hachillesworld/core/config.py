"""HAchillesWorld 설정 관리."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# ── HAS 카테고리 가중치 ─────────────────────────────────────────────
# 기본값: HAW-TR-001 이론 기반 (WMQ:ALM:OHM = 0.40:0.35:0.25)
# HAW-STUDY-001 완료 후 StudyAnalyzer.sdk_weight_update()로 실증 기반 갱신 가능.
# 세 값의 합계는 반드시 1.0 이어야 한다.
HAS_WEIGHTS: dict[str, float] = {
    "wmq": 0.40,
    "alm": 0.35,
    "ohm": 0.25,
}

# 초기화용 기본값 스냅샷 (sdk_weight_update 후 롤백 가능)
_DEFAULT_HAS_WEIGHTS: dict[str, float] = dict(HAS_WEIGHTS)


def reset_has_weights() -> None:
    """HAS 가중치를 이론 기본값으로 복원한다."""
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
