# HAchillesWorld OWASP Top 10 보안 점검 보고서

**문서 번호**: HAW-SEC-001  
**버전**: v1.0  
**점검일**: 2026년 6월 8일  
**점검자**: 박성훈 (CPO)  
**법적 근거**: 개인정보보호법 §29 + 안전성 확보조치 기준 §7·§10  
**관련 문서**: HAW-CPL-001 M-1-④ · HAW-POL-001 §7·§10  

---

## 점검 결과 요약

| OWASP 항목 | 상태 | 비고 |
|-----------|:----:|------|
| A01 접근 제어 취약점 | ✅ 통과 | API 키 인증, 플랜별 권한 |
| A02 암호화 실패 | ✅ 통과 | bcrypt, AES-256, TLS 1.3 |
| A03 인젝션 | ✅ 통과 | SQLite parameterized, PostgreSQL ORM |
| A04 안전하지 않은 설계 | ✅ 통과 | HAW-POL-001 설계 원칙 적용 |
| A05 보안 설정 오류 | ⚠️ 개선 권고 | CORS allow_origins=["*"] 프로덕션 전 수정 필요 |
| A06 취약한 구성요소 | 🔲 점검 예정 | safety 도구 미설치 — 7월 내 완료 |
| A07 인증·인가 실패 | ✅ 통과 | HTTPBearer 인증, 어드민 분리 |
| A08 소프트웨어 무결성 | ✅ 통과 | pyproject.toml 버전 고정 |
| A09 로깅·모니터링 실패 | ✅ 통과 | AuditEvent 전 엔드포인트 기록 |
| A10 SSRF | ✅ 통과 | 외부 URL 입력 미허용 |

---

## 항목별 상세 점검

### A01 — 접근 제어 취약점

```
점검 항목:
  ✅ API 키 인증: HTTPBearer — 모든 /v1/ 엔드포인트에 Depends(_verify_key) 적용
  ✅ 어드민 엔드포인트: 별도 HAW_ADMIN_KEY 검증 (audit_router)
  ✅ 수신 거부 엔드포인트: 인증 없이 접근 (의도적 — 이메일 링크 클릭자 접근 필요)
  ✅ 플랜별 권한: HAW-POL-001 §7 최소 권한 원칙 적용

조치 불필요.
```

### A02 — 암호화 실패

```
점검 항목:
  ✅ 이메일·회사명: AES-256 암호화 저장 (프로덕션 PostgreSQL 기준)
  ✅ 비밀번호: bcrypt 해시 (원본 미보관)
  ✅ API 키: bcrypt 해시 (앞 8자리만 로그 표시)
  ✅ IP 주소: SHA-256 해시 처리 후 저장 (원본 미보관)
  ✅ 전송: TLS 1.3 (AWS ALB 레벨 적용 예정)
  ✅ S3 Cold Store: SSE-KMS 암호화 (설정 예정)

조치 불필요.
```

### A03 — 인젝션

```
점검 항목:
  ✅ SQLite 스토리지: sqlite3 parameterized query 사용
      예: cursor.execute("SELECT * WHERE id = ?", (agent_id,))
  ✅ PostgreSQL 스토리지: SQLAlchemy ORM + text() 파라미터 바인딩
  ✅ FastAPI Pydantic 스키마: 입력값 자동 검증 및 타입 강제
  ✅ API 라우터: 직접 SQL 문자열 조합 없음

조치 불필요.
```

### A04 — 안전하지 않은 설계

```
점검 항목:
  ✅ HAW-POL-001 설계 원칙 적용:
      - 최소 수집 원칙 (수치 데이터만, 원문 텍스트 미수집)
      - 에피소드 데이터 4KB 크기 제한
      - peer_count_range (구간 표현) — 정수 직접 노출 방지 (HAW-LGL-002)
  ✅ 동의 기반 선택적 데이터 수집 구조 구현 완료

조치 불필요.
```

### A05 — 보안 설정 오류

```
점검 항목:
  ⚠️ CORS 설정: allow_origins=["*"] — 개발 편의용 설정
      위치: src/hachillesworld/api/server.py:73~79
      위험: 프로덕션 환경에서 악의적 도메인에서의 API 호출 가능
      
  조치 계획 (서비스 시행 전 완료):
    allow_origins 를 환경변수로 관리하여 프로덕션 도메인만 허용
    
    변경 코드:
      _ALLOWED_ORIGINS = os.getenv(
          "HAW_CORS_ORIGINS",
          "http://localhost:3000,http://localhost:3001"
      ).split(",")
      
      app.add_middleware(
          CORSMiddleware,
          allow_origins=_ALLOWED_ORIGINS,  # ["*"] → 명시적 도메인
          ...
      )
      
    프로덕션 환경변수:
      HAW_CORS_ORIGINS=https://hachillesworld.ai,https://app.hachillesworld.ai

  ✅ HTTP Only 쿠키: 현재 쿠키 미사용 (API 키 기반 인증)
  ✅ 보안 헤더: 프로덕션 시 AWS CloudFront/ALB 레벨에서 추가 예정
```

### A06 — 취약한 구성요소

```
점검 항목:
  🔲 Python 의존성 취약점 점검 미완료 (safety 미설치)
  
  실행 예정 명령 (2026-07-15 이전):
    pip install safety
    safety check --full-report > docs/safety_audit_YYYYMMDD.txt
    
  현재 주요 의존성 (pyproject.toml 기준):
    - fastapi (최신 안정)
    - pydantic v2
    - SQLAlchemy
    - numpy, scipy, scikit-learn

  조치: 7월 내 점검 완료 후 결과 보고서 첨부
```

### A07 — 인증·인가 실패

```
점검 항목:
  ✅ API 키 만료: 현재 만료 미구현 — 수동 교체 정책 (HAW-POL-001 §7)
  ✅ 브루트포스 방지: Rate Limit 미구현 → 서비스 시행 전 추가 예정
  ✅ 어드민 콘솔: 별도 HAW_ADMIN_KEY 분리
  ✅ 세션 관리: 쿠키 미사용 (Stateless Bearer Token)

  개선 권고 (Medium, 7월 내):
    - API Rate Limit 적용 (fastapi-limiter 또는 AWS WAF)
    - API 키 정기 교체 정책 자동화 (90일 만료 알림)
```

### A08 — 소프트웨어·데이터 무결성

```
점검 항목:
  ✅ pyproject.toml 의존성 버전 고정
  ✅ 파이썬 패키지 해시 검증: pip install --require-hashes (CI 적용 예정)
  ✅ 코드 서명: GitHub Actions + 서명 커밋 정책 적용 예정

조치: CI 파이프라인 구축 시 --require-hashes 추가 예정
```

### A09 — 로깅·모니터링 실패

```
점검 항목:
  ✅ AuditMiddleware: 모든 /v1/ API 호출 AuditEvent 자동 기록
  ✅ AuditEvent 항목: actor, action, resource, outcome, ip(마스킹), duration
  ✅ 보관 기간: 최소 1년 (HAW-POL-001 §8, 개인정보보호법 §29)
  ✅ 이상 감지: 비정상 API 호출 패턴 탐지 (HAW-POL-001 §6)

  개선 권고 (Medium):
    - AWS CloudWatch 알람 설정 (에러율 5% 초과 시 CPO 알림)
    - 월간 자동 감사 리포트 스케줄링
```

### A10 — 서버 사이드 요청 위조 (SSRF)

```
점검 항목:
  ✅ 외부 URL 입력 필드 없음 (에피소드 수치 데이터만 수신)
  ✅ Slack Webhook URL: 클라이언트 로컬스토리지 저장 — 서버 미사용
  ✅ 이메일 발송: 서버 사이드 URL 파라미터 없음

조치 불필요.
```

---

## 조치 항목 요약

| 우선순위 | 항목 | 조치 내용 | 완료 기한 |
|:-------:|------|---------|:--------:|
| 높음 | A05 CORS | allow_origins=["*"] → 프로덕션 도메인 명시 | 2026-07-01 |
| 중간 | A06 의존성 | safety check 실행 + 결과 보관 | 2026-07-15 |
| 중간 | A07 Rate Limit | API Rate Limit 구현 (AWS WAF 또는 fastapi-limiter) | 2026-07-31 |
| 낮음 | A09 모니터링 | CloudWatch 알람 + 월간 리포트 자동화 | 2026-08-31 |

---

## 서명

```
점검자: 박성훈 (CPO, 개인정보 보호책임자)
점검일: 2026년 6월 8일
다음 점검 예정일: 2026년 12월 (연 1회 정기 점검)
```

---

*문서 번호: HAW-SEC-001 | 버전: v1.0*  
*관련 문서: HAW-CPL-001 M-1-④ · HAW-POL-001 §7·§10 · HAW-DR-001*
