# HAchillesWorld 재해복구(DR) 절차서

**문서 번호**: HAW-DR-001  
**버전**: v1.0  
**작성일**: 2026년 6월 8일  
**작성자**: 박성훈 (대표, 개인정보 보호책임자)  
**검토 주기**: 연 1회 (매년 12월) + 중대 사고 발생 후  
**법적 근거**: 개인정보보호법 제29조 + 안전성 확보조치 기준 제12조  
**관련 문서**: HAW-POL-001 · HAW-CPL-001 (M-1 이행 항목)

---

## 1. 목적 및 적용 범위

이 절차서는 HAchillesWorld 플랫폼 운영 중 발생할 수 있는 인프라 장애·데이터 손상·자연재해 등의 재난 상황에서 서비스를 복구하기 위한 절차를 정의한다.

**적용 범위**: AWS 서울 리전 기반 전체 인프라 — RDS (PostgreSQL), S3 Cold Store, FastAPI 서버, Next.js 대시보드

---

## 2. 복구 목표 (RPO · RTO)

| 지표 | 목표 | 설명 |
|------|:----:|------|
| **RPO** (Recovery Point Objective) | **24시간** | 최대 24시간 이전 백업 시점으로 복구 허용 |
| **RTO** (Recovery Time Objective) | **4시간** | 사고 인지 후 4시간 이내 서비스 재개 목표 |

> 목표 미달 시 CPO가 개인정보보호위원회 및 영향받은 고객에게 지연 사유를 통보한다.

---

## 3. 백업 현황

### 3.1 RDS (PostgreSQL) 자동 백업

```
설정 목표:
  · 자동 백업: 활성화 (매일 02:00~04:00 KST 백업 윈도우)
  · 백업 보존 기간: 7일 이상
  · 스토리지 암호화: AWS KMS 키 적용 (StorageEncrypted = true)

확인 명령:
  aws rds describe-db-instances \
    --query 'DBInstances[].[DBInstanceIdentifier,BackupRetentionPeriod,StorageEncrypted]'

스냅샷 수동 백업: 월 1회 이상
  aws rds create-db-snapshot \
    --db-instance-identifier haw-prod-db \
    --db-snapshot-identifier haw-manual-$(date +%Y%m%d)
```

### 3.2 S3 Cold Store 버킷 설정

```
버킷 버전 관리 활성화 (실수 삭제 복구용):
  aws s3api put-bucket-versioning \
    --bucket haw-cold-store \
    --versioning-configuration Status=Enabled

확인:
  aws s3api get-bucket-versioning --bucket haw-cold-store
  → "Status": "Enabled" 확인 필수
```

### 3.3 백업 암호화 확인

| 대상 | 암호화 방법 | 상태 |
|------|-----------|------|
| RDS 스냅샷 | AWS KMS (AES-256) | 설정 필요 (M-1-② 이행 시 확인) |
| S3 객체 | SSE-KMS | S3 버킷 기본 암호화 정책 적용 |
| 전송 중 데이터 | TLS 1.3 | 적용 중 ✅ |

---

## 4. 재해 시나리오 및 대응 절차

### 시나리오 A: RDS 인스턴스 장애

**탐지**: AWS CloudWatch 알람 → CPO 이메일·SMS 알림 (5분 이내)

```
자동 대응:
  1. RDS Multi-AZ 페일오버 자동 실행 (수분 내)
  2. 애플리케이션 재연결 확인 (DATABASE_URL 변경 불필요)
  예상 RTO: 자동 15분

수동 복구 (자동 페일오버 실패 시):
  Step 1. AWS Console → RDS → 스냅샷 → 가장 최근 스냅샷 선택
  Step 2. "스냅샷에서 DB 복원" → 신규 인스턴스 생성
            인스턴스명: haw-prod-db-recovery-YYYYMMDD
  Step 3. 신규 엔드포인트 확인
            aws rds describe-db-instances \
              --db-instance-identifier haw-prod-db-recovery-YYYYMMDD \
              --query 'DBInstances[].Endpoint'
  Step 4. 환경변수 업데이트
            HAW_DATABASE_URL=postgresql://user:pass@{신규_엔드포인트}:5432/hawdb
  Step 5. FastAPI 서버 재기동
            systemctl restart hachillesworld-api
            # 또는 ECS/EC2 인스턴스 재시작
  Step 6. 연결 확인
            curl https://api.hachillesworld.ai/health
            → {"status": "ok"} 확인
  Step 7. 기존 손상 인스턴스 삭제 (확인 후)
  예상 RTO: 수동 2시간
```

### 시나리오 B: S3 Cold Store 데이터 손상

**탐지**: S3 버전 관리 이력 확인 또는 데이터 무결성 오류 알림

```
복구:
  Step 1. 손상 객체 확인
            aws s3api list-object-versions \
              --bucket haw-cold-store \
              --prefix {손상_객체_prefix}
  Step 2. 이전 버전 ID 확인
            aws s3api get-object \
              --bucket haw-cold-store \
              --key {object_key} \
              --version-id {version_id} \
              --outfile {복구_파일명}
  Step 3. 복구 확인 후 현재 버전으로 업로드
  예상 RTO: 파일당 10분
```

### 시나리오 C: 전체 서비스 중단 (AWS 서울 리전 광역 장애)

**탐지**: AWS Health Dashboard (health.aws.amazon.com) 모니터링

```
대응:
  T+0h  AWS 장애 확인 → hachillesworld.ai 상태 페이지 공지
          공지 문구: "현재 AWS 인프라 장애로 서비스가 일시 중단되었습니다.
                     복구 예정 시각: [AWS 복구 예상 시간]"
  T+Xh  AWS 복구 완료 → 서비스 재기동
          1. RDS 연결 확인
          2. FastAPI 서버 헬스체크
          3. Next.js 대시보드 정상 동작 확인
          4. 상태 페이지 "서비스 정상화" 업데이트
  예상 RTO: AWS 복구 시간 + 애플리케이션 재기동 30분

개인정보보호법 적용:
  · 서비스 중단이 개인정보 침해를 수반하는 경우 §12.2 신고 절차 적용
  · 단순 가용성 장애는 신고 의무 없음
```

### 시나리오 D: 개인정보 유출 의심 (보안 사고)

```
→ HAW-POL-001 §12.1·§12.2 사고 대응 절차 적용
→ 72시간 내 개인정보보호위원회 신고 (개인정보보호법 §34)
→ EU 고객 포함 시 해당 DPA 신고 (GDPR Art.33)
→ HAW-CPL-002 §3.7 72시간 대응 체크리스트 참조
```

---

## 5. DR 복구 체크리스트 (사고 발생 시 순서대로 실행)

```
□ Step 1. 사고 인지 시각 기록 (UTC 기준)
□ Step 2. CPO(박성훈) 즉시 보고
□ Step 3. 사고 유형 분류 (시나리오 A/B/C/D 중 해당)
□ Step 4. 고객 영향 범위 초기 파악 (몇 명, 어떤 서비스)
□ Step 5. 해당 시나리오 복구 절차 실행
□ Step 6. 서비스 복구 확인 (헬스체크 + 기능 테스트)
□ Step 7. AuditEvent: action="disaster.recovery.completed" 기록
□ Step 8. 개인정보 침해 여부 판단 → HAW-POL-001 §12.2 신고 절차 실행 여부 결정
□ Step 9. 사고 보고서 작성 (1주 이내) — 근본 원인 + 재발 방지 계획
□ Step 10. DR 절차서 개선 필요 항목 반영
```

---

## 6. 연락처

| 역할 | 담당자 | 연락처 |
|------|--------|--------|
| CPO / 전체 대응 책임 | 박성훈 | suhopark1@gmail.com |
| AWS 인프라 지원 | AWS Support | aws.amazon.com/support |
| 개인정보보호위원회 (신고) | — | privacy.go.kr / 182 |

---

## 7. DR 훈련 계획

```
연 1회 훈련 (매년 12월):
  · 가상 RDS 장애 시나리오 (시나리오 A) 수동 복구 실습
  · 스냅샷에서 신규 인스턴스 복원 → 복구 시간 측정
  · 훈련 결과 보고서 작성 후 이 문서에 부록으로 첨부

훈련 목표:
  · RTO 4시간 목표 달성 여부 검증
  · 복구 절차 개선 사항 도출
```

---

## 8. 버전 이력

| 버전 | 시행일 | 주요 내용 |
|------|--------|---------|
| v1.0 | 2026-06-08 | 최초 작성 (HAW-CPL-001 M-1 이행) |

---

*문서 번호: HAW-DR-001 | 버전: v1.0*  
*작성일: 2026년 6월 8일 | 다음 검토: 2026년 12월*  
*작성자: 박성훈 (대표, 개인정보 보호책임자)*  
*관련 문서: HAW-POL-001 §12 · HAW-CPL-001 §2 · HAW-CPL-002 §3.7*
