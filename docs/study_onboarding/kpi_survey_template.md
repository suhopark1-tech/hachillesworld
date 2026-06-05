# HAW-STUDY-001 비즈니스 KPI 수집 설문지

> **제출 주기**: 월 1회 (매월 마지막 영업일)  
> **제출 방법**: `client.submit_kpi(kpi_data)` 또는 이메일 (suhopark1@gmail.com)  
> **참고**: HAchillesWorld 업그레이드 계획서 Table 6 기준

---

## 기본 정보

- **study_id**: ______________________________
- **제출 월**: ________년 ________월
- **에이전트 도메인**: ☐ supply_chain ☐ customer_service ☐ code_generation ☐ finance ☐ healthcare
- **에피소드 총 실행 횟수 (해당 월)**: ________회

---

## Part A. 에이전트 효율성 지표 (Efficiency KPIs)

### A1. 작업 완료율 (Task Completion Rate)

에이전트가 사람 개입 없이 목표 작업을 완료한 비율

```
task_completion_rate = 자동 완료 건수 / 전체 요청 건수
```

**값**: ________ (0.00 ~ 1.00)  
예시: 870건/1,000건 → 0.870

측정 방법:
- [ ] 자동화된 로깅 시스템
- [ ] 수동 집계
- [ ] 기타: ______________________

---

### A2. 시간 절감률 (Time Savings %)

AI 에이전트 도입 후 동일 작업 수행 시간의 절감 비율

```
time_savings_pct = (기존 소요 시간 - 현재 소요 시간) / 기존 소요 시간 × 100
```

**값**: ________ % (0 ~ 100)  
예시: 120분 → 92분 → 23.3%

기준 (베이스라인): ☐ 도입 전 평균 ☐ 직전 분기 ☐ 사람 수행 시간

---

### A3. 오류율 (Error Rate)

에이전트 출력 오류 발생 비율

```
error_rate = 오류 발생 에피소드 / 전체 에피소드
```

**값**: ________ (0.00 ~ 1.00)  
예시: 30건/1,000건 → 0.030

오류 정의: ☐ 사람이 수정한 케이스 ☐ 시스템 예외 발생 ☐ 비즈니스 룰 위반

---

## Part B. 비용·생산성 지표 (Cost & Productivity KPIs)

### B1. 비용 절감률 (Cost Reduction %)

AI 에이전트 도입으로 인한 운영 비용 절감 비율

```
cost_reduction_pct = (기존 비용 - 현재 비용) / 기존 비용 × 100
```

**값**: ________ % (음수 허용 — 비용 증가 시)  
예시: 1,000만원 → 880만원 → 12.0%

비용 범위: ☐ 인건비 ☐ 외부 서비스 비용 ☐ 전체 운영비

---

### B2. 처리량 증가율 (Throughput Increase %)

동일 기간 동안 처리한 작업 건수의 증가 비율

```
throughput_increase_pct = (현재 처리량 - 기준 처리량) / 기준 처리량 × 100
```

**값**: ________ % (0 이상)  
예시: 500건 → 650건 → 30.0%

---

## Part C. 품질·만족도 지표 (Quality & Satisfaction KPIs)

### C1. 고객 만족도 점수 (CSAT Score)

에이전트 사용자의 만족도 평균 점수

**값**: ________ (1.0 ~ 5.0)  
예시: 4.2 (5점 만점)

측정 방법: ☐ 사후 설문 ☐ NPS ☐ 별점 평가 ☐ 기타

---

### C2. 재작업율 (Rework Rate)

에이전트 출력을 사람이 재처리한 비율

```
rework_rate = 재처리 건수 / 전체 에이전트 출력 건수
```

**값**: ________ (0.00 ~ 1.00)

---

## Part D. 운영 안정성 지표 (Operational Stability KPIs)

### D1. 에이전트 가용률 (Agent Availability %)

계획된 운영 시간 대비 정상 서비스 시간

```
availability_pct = 정상 운영 시간 / 계획 운영 시간 × 100
```

**값**: ________ % (0 ~ 100)  
예시: 99.5%

---

### D2. 사람 개입 비율 (Human Intervention Rate)

에이전트가 사람의 승인 또는 수정을 요청한 비율

```
hitl_rate = HITL 요청 건수 / 전체 에피소드
```

**값**: ________ (0.00 ~ 1.00)

---

## Part E. 도메인별 특화 지표

### 해당 도메인만 응답하세요.

#### E1. [supply_chain] 재고 예측 정확도

```
inventory_forecast_accuracy = 1 - |예측값 - 실제값| / 실제값 평균
```

**값**: ________ (0.00 ~ 1.00)

---

#### E2. [customer_service] 첫 접촉 해결율 (FCR)

```
fcr_rate = 1회 상호작용으로 해결된 케이스 / 전체 케이스
```

**값**: ________ (0.00 ~ 1.00)

---

#### E3. [code_generation] 코드 수락율

```
code_acceptance_rate = PR 머지 건수 / AI 생성 PR 전체
```

**값**: ________ (0.00 ~ 1.00)

---

#### E4. [finance] 규정 준수율

```
compliance_rate = 규정 준수 트랜잭션 / 전체 트랜잭션
```

**값**: ________ (0.00 ~ 1.00)

---

## SDK 자동 제출 코드

```python
client.submit_kpi({
    # Part A
    "task_completion_rate": 0.87,
    "time_savings_pct": 23.3,
    "error_rate": 0.030,
    # Part B
    "cost_reduction_pct": 12.0,
    "throughput_increase_pct": 30.0,
    # Part C
    "csat_score": 4.2,
    "rework_rate": 0.05,
    # Part D
    "availability_pct": 99.5,
    "hitl_rate": 0.08,
    # Part E (도메인별)
    "inventory_forecast_accuracy": 0.91,   # supply_chain
})
```

---

## 작성 지침

1. **모르는 항목은 빈칸**으로 두어도 됩니다 (일부 항목만 제출해도 유효)
2. **추정값**도 괜찮습니다. 정밀도보다 일관성이 중요합니다
3. **이전 달과 측정 방법이 바뀐 경우** 비고란에 기재해 주세요

**비고**: _______________________________________________________________

---

*이 설문지는 HAchillesWorld SDK v2.0 업그레이드 계획서 Table 6 기준으로 작성되었습니다.*  
*문의: suhopark1@gmail.com*
