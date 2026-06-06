# HAchillesWorld SDK — 데이터 흐름 및 개인정보 처리

## 1. SDK 내부 전용 처리 데이터

다음 데이터는 SDK 프로세스 내에서만 처리되며 외부로 전송되지 않습니다.

| 데이터 | 처리 위치 | 보존 방식 |
|--------|-----------|----------|
| 에이전트 실행 로그 (logs) | `scan/engine.py` | 인메모리 (기본) 또는 SQLite (Sprint 5-C) |
| EpisodeRecord (에피소드 기록) | `collect/episode.py` | 인메모리 |
| DiagnosticReport (진단 결과) | `core/models.py` | 인메모리 스토어 |
| Planning Depth 측정 결과 | `scan/planning_depth.py` | 인메모리 |
| OOD 에너지 점수 | `scan/ood_detector.py` | 인메모리 |
| 드리프트 분류 결과 | `operate/monitor.py` | 인메모리 |

## 2. Anthropic API로 전송되는 데이터 (CA 평가 시)

CA(Counterfactual Accuracy) 평가 시 `anthropic_api_key`를 제공하면
에피소드의 일부 필드가 Anthropic API 서버로 전송됩니다.

**전송되는 필드:**
- `predicted_next_state` (예측 상태)
- `actual_next_state` (실제 상태)
- `action_taken` (실행된 행동)
- `alternatives` (대안 행동 목록)

**전송되지 않는 필드 (PII 제거 후):**
- `user_id`, `session_id`, `ip_address` 등 개인 식별자
- `DataClassifier`가 PII로 분류한 모든 필드

전송 비활성화: `ScanEngine(config, anthropic_api_key=None)` 또는 로컬 Judge 사용.

## 3. 전송 전 익명화 처리 방법

```python
# src/hachillesworld/privacy/data_classifier.py
classifier = DataClassifier()
sanitized = classifier.sanitize(episode_data)
# PII 필드 자동 마스킹 후 API 전송
```

`DataClassifier`는 다음 패턴을 자동 감지하고 마스킹합니다:
- 이메일 주소 (`*@*.*`)
- 전화번호 패턴
- UUID 형식 ID 필드 (설정으로 제어)
- 한국 주민등록번호 패턴

## 4. GDPR/PIPL 준수 방법

| 요구사항 | HAchillesWorld 대응 |
|---------|-------------------|
| 최소 수집 원칙 | CA 평가 시만 외부 전송, 나머지 로컬 처리 |
| 사전 고지 | `CounterfactualEvaluator` 모듈 독스트링에 전송 사실 명시 |
| PII 보호 | `DataClassifier` 자동 마스킹 |
| 전송 제한 | `anthropic_api_key=None` 설정으로 완전 로컬 동작 가능 |
| 감사 로그 | Sprint 6-B `audit/logger.py`에서 모든 외부 전송 기록 |

**권장 설정 (규제 민감 환경):**
```python
engine = ScanEngine(config)          # anthropic_api_key 미제공 → 외부 전송 없음
# 또는 Sprint 5-D 로컬 Judge 사용:
# from hachillesworld.scan.judge import LocalJudge
```

## 5. Judge 백엔드별 데이터 전송 범위 (Sprint 5-D 이후)

| Judge | 외부 전송 | 전송 대상 | GDPR 위험 |
|-------|-----------|-----------|----------|
| `AnthropicJudge` | ✅ 있음 | Anthropic API 서버 | PII 자동 필터링 후 전송 |
| `LocalLLMJudge` | ❌ 없음 | localhost:11434 (Ollama) | 없음 |
| `RuleBasedJudge` | ❌ 없음 | 없음 (완전 오프라인) | 없음 |

**데이터 흐름 — LocalLLMJudge**:

```
에이전트 로그
    │
    ▼
CounterfactualEvaluator(judge_type="local")
    │ Ollama HTTP API (localhost only)
    ▼
CA 점수 산출 ─── (외부 전송 없음) ───→ DiagnosticReport
```

**데이터 흐름 — RuleBasedJudge**:

```
에이전트 로그
    │
    ▼
CounterfactualEvaluator(judge_type="rule")
    │ 순수 Python 규칙 평가 (네트워크 없음)
    ▼
CA 점수 산출 ─── (외부 전송 없음) ───→ DiagnosticReport
```

Judge 선택:

```python
# 완전 오프라인 (GDPR 최고 등급)
evaluator = CounterfactualEvaluator(judge_type="rule")

# 로컬 LLM — 재현 가능 (논문/연구)
evaluator = CounterfactualEvaluator(judge_type="local", model="llama3.1:8b")

# Anthropic API — 고정확도 (프로덕션, 데이터 전송 있음)
evaluator = CounterfactualEvaluator(anthropic_client=client, consent_acknowledged=True)
```

## 6. 감사 로그 데이터 흐름 (Sprint 6-B)

모든 API 호출은 `AuditMiddleware`에 의해 자동으로 `audit_events` 테이블에 기록됩니다.

```
HTTP 요청
    │
    ▼
AuditMiddleware (api/middleware.py)
    │ actor, action, resource, outcome, duration_ms 추출
    ▼
AuditLogger.log(AuditEvent) → Repository.save_audit_event()
    │
    ├── InMemoryRepository: _audit 리스트 (메모리)
    └── SQLiteRepository: audit_events 테이블 (영구)
```

감사 로그 조회: `GET /v1/audit/events` (admin API key 전용)

**감사 이벤트 포함 데이터**:
- `actor`: API key 앞 8자 (개인 식별자 최소화)
- `action`: "scan" | "interpret" | "drift.record" | "harness.approve" | ...
- `resource`: agent_id 또는 group_id
- `outcome`: "success" | "not_found" | "unauthorized" | "forbidden" | "error"
- `ip_address`, `duration_ms`, `request_size_bytes`

**감사 로그는 외부로 전송되지 않습니다.** 모든 기록은 로컬 스토리지(SQLite 또는 메모리)에만 보존됩니다.

## 관련 문서

- `NOTICE` — 오픈소스 라이선스 및 저작권 고지
- `src/hachillesworld/privacy/data_classifier.py` — PII 분류 구현
- `src/hachillesworld/audit/logger.py` — AuditLogger + AuditEvent
- `src/hachillesworld/api/middleware.py` — AuditMiddleware
- `src/hachillesworld/scan/counterfactual_evaluator.py` — CA 평가 및 전송 고지
- `docs/CA_MEASUREMENT_GUIDE.md` — Judge 선택 가이드 (Sprint 5-D)
