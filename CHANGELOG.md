# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] — 2026-10-31

### Fixed / Improved

- **D-1** EU AI Act 표현 전면 수정: "자동 매핑" → "모니터링 참고 자료"로 변경
- **D-1** `generate_compliance_report` → `generate_monitoring_report` 메서드명 변경
- **D-1** HTML 보고서에 법적 면책 배너 삽입 (경고 색상 `#fef3c7`)
- **B-2** `import anthropic` optional dependency로 전환 (anthropic 미설치 시에도 SDK 작동)
- **B-3** 하드코딩 연도 `assert dt.year == 2026` 제거, 동적 연도 처리
- **B-1** `validation/agency_level.py` deprecated 마킹, SDK로 이전 완료

### Added

- **A-1, A-2** HAS 신뢰구간(CI) + 오차 전파 (`HASWithCI` 모델)
- **A-7** HAS 가중치 버전 관리: `HAS_WEIGHTS_V20`, `HAS_WEIGHTS_V21`, `get_weights_for_version()`
- **A-9** 측정 불가 지표 처리 정책 명시화 (`NOT_MEASURED_POLICY`: exclude / neutral / penalty)
- **A-3** `MulticollinearityAnalyzer`: VIF + Spearman 상관 행렬, 15개 지표 다중공선성 검증
- **B-4, C-2** SQLite / PostgreSQL 영구 스토리지 (`storage/sqlite.py`, `storage/postgres.py`)
- **A-6, D-3** `LocalLLMJudge` (Ollama), `RuleBasedJudge` — 오프라인 Judge, 외부 API 호출 없음
- **E-1, E-2** `HASInterpreter`: A+~D 등급 + 구체적 액션 아이템 (지표별 즉시 실행 가능 조치)
- **C-8** MLflow 연동 모듈 (`integrations/mlflow_logger.py`)
- **C-7** `AuditLogger` + `AuditMiddleware` — 모든 API 호출 감사 로그 기록
- **D-3, D-4** `DataClassifier` PII 필터링 — Anthropic API 전송 전 자동 sanitize
- **A-4, A-5** HAW-STUDY-002 연구 프로토콜: n=200 층화 표본 + 외부 타당도 설계

### Documentation

- **E-5** README 전면 개편: 30초 이해 가능 구조, 실행 예제 포함
- **F-1** `CONTRIBUTING.md` 신규 작성
- **D-4** `docs/DATA_FLOW.md` 완전한 데이터 흐름 문서 (내부/외부 전송 경계 명시)
- **D-6** TTA 제안서 §4.1 가중치 표현: 고정값 → 범위 + 산출 방법론
- **D-5** ISO/IEC 42001:2023 조항 해석 근거 출처 및 면책 조항 추가
- `docs/haw_study_002_protocol.md` 연구 프로토콜 설계 문서
- `docs/analysis/multicollinearity_study001.md` 다중공선성 분석 결과

### Tests

- 611개 테스트 (0 failures) — Sprint별 신규 추가:
  - `test_has_reliability.py` (Sprint 5-B, 신뢰구간)
  - `test_storage.py` (Sprint 5-C, SQLite/PostgreSQL)
  - `test_judge_backends.py` (Sprint 5-D, 로컬 Judge)
  - `test_interpreter.py` (Sprint 6-A, HAS 해석)
  - `test_audit.py` (Sprint 6-B, 감사 로그)
  - `test_privacy.py` (Sprint 6-B, PII 분류)
  - `test_multicollinearity.py` (Sprint 6-C, 다중공선성)

### Quality

- `ruff format --check` + `ruff check` → 0 errors
- `mypy src/ --strict` → 0 errors
- 커버리지 80%+

---

## [2.0.0] — 2026-06-06

### Added

- HAS (Holistic Agent Score) 15개 지표 자동 측정 체계
- L1/L2/L3 역량 레벨 분류
- EU AI Act Art.13~15 모니터링 참고 자료 생성
- ISO/IEC 42001:2023 체크리스트 참고 자료 생성
- FastAPI REST API 서버 (`/v1/scan`, `/v1/interpret` 등)
- HAW-STUDY-001 (n=25 파일럿) 실증 연구 지원
- Shapley 가중치 재보정 (`StudyAnalyzer`)
- SQLite 기반 영구 스토리지 (초기 버전)
- Planning Depth 행동 프로빙 측정

### Initial Release

- SDK v2.0 공개 릴리스
- Apache 2.0 라이선스 (validation/), Proprietary (src/)
