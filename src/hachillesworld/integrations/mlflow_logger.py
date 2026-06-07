"""MLflowHASLogger — MLflow run에 HAS 지표를 자동 로깅 (Sprint 6-A, C-8).

사용법:
    from hachillesworld.integrations import MLflowHASLogger

    logger = MLflowHASLogger()
    logger.log_report(report)                  # 새 run 자동 생성
    logger.log_report(report, run_id="abc123") # 기존 run에 추가
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hachillesworld.core.models import DiagnosticReport


class MLflowHASLogger:
    """MLflow run에 HAS 지표·파라미터를 자동 로깅.

    mlflow 패키지가 설치된 환경에서만 동작한다.
    미설치 시 ImportError를 발생시켜 명확한 오류 메시지를 제공한다.
    """

    def log_report(
        self,
        report: "DiagnosticReport",
        run_id: str | None = None,
        experiment_name: str = "hachillesworld",
    ) -> None:
        """DiagnosticReport 전체를 MLflow run에 기록한다.

        기록 항목:
        - Metrics: HAS 종합 + 3범주 점수 + 15개 개별 지표
        - Params: level, domain, has_version
        """
        try:
            import mlflow  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "MLflow가 설치되지 않았습니다. `pip install mlflow`를 실행하세요."
            ) from exc

        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_id=run_id):
            # ── 종합 점수 및 3범주 ─────────────────────────────
            mlflow.log_metric("has_score", round(report.composite_score, 4))
            mlflow.log_metric("wmq_score", round(report.world_model_quality.score, 4))
            mlflow.log_metric("alm_score", round(report.agency_level.score, 4))
            mlflow.log_metric("ohm_score", round(report.operational_health.score, 4))

            # ── 15개 개별 지표 ─────────────────────────────────
            all_metrics = (
                report.world_model_quality.metrics
                + report.agency_level.metrics
                + report.operational_health.metrics
            )
            for m in all_metrics:
                key = "haw_" + m.name.lower().replace(" ", "_").replace("-", "_")
                mlflow.log_metric(key, round(m.value, 6))

            # ── 파라미터 ───────────────────────────────────────
            mlflow.log_param("level", report.level_label)
            mlflow.log_param("domain", report.laws_domain.value)
            mlflow.log_param("has_version", report.has_score_version)
            mlflow.log_param("agent_name", report.agent_name)

            # ── HAS 신뢰구간 (존재 시) ─────────────────────────
            if report.has_confidence_interval is not None:
                lo, hi = report.has_confidence_interval
                mlflow.log_metric("has_ci_lower", round(lo, 4))
                mlflow.log_metric("has_ci_upper", round(hi, 4))
