"""HAchillesWorld 설정 관리."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # 진단 기본값
    scan_drift_threshold: float = 0.15
    scan_ece_threshold: float = 0.10
    scan_recalibration_threshold: float = 0.05  # 5% 이하 정상

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
