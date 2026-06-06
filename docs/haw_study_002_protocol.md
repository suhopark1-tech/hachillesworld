# HAW-STUDY-002 연구 프로토콜 (설계)

**문서 번호**: HAW-PROTO-002  
**버전**: 1.0 (설계 초안)  
**작성일**: 2026-10-01  
**작성자**: 박성훈 (HAchillesWorld 연구팀)  
**근거**: HAW-STUDY-001 한계 분석 (Sprint 6-C, A-4, A-5)

---

## 1. 목적: HAW-STUDY-001 한계 극복

HAW-STUDY-001(n=50, 파일럿)의 주요 한계점을 극복하고
HAS 가중치·외부 타당도에 대한 충분한 통계적 검증력을 확보한다.

| 한계 | HAW-STUDY-001 | HAW-STUDY-002 목표 |
|------|--------------|------------------|
| 표본 크기 | n=50 (파일럿) | n=200+ (충분한 검증력) |
| 표본 방법 | Convenience sample | 층화 표본 (stratified) |
| 외부 타당도 | 미검증 | SWE-bench/GAIA 비교 |
| 다중공선성 | 15지표 공선성 미검증 | VIF 검증 후 대표 지표 선택 |

---

## 2. 표본 설계 (층화)

### 2.1 층화 기준

두 축(도메인 × 역량 레벨)으로 교차 층화:

| 계층 | 도메인 | n |
|------|--------|---|
| Physical | 로봇·제조·물류 | 50 |
| Digital | 코드·웹·데이터 | 50 |
| Social | 고객서비스·교육·헬스케어 | 50 |
| Scientific | 연구·분석·실험 | 50 |
| **합계** | | **200** |

| 역량 계층 | 레벨 | n |
|----------|------|---|
| L1 Predictor | 단순 예측 | 67 |
| L2 Planner | 다단계 계획 | 67 |
| L3 Evolver | 자기 개선 | 66 |
| **합계** | | **200** |

### 2.2 포함/제외 기준

**포함**:
- 공개 API 또는 내부 에이전트로 15개 HAS 지표 측정 가능
- 최소 100 에피소드 관측 데이터 보유
- 비즈니스 KPI 3개 이상 측정 가능

**제외**:
- 단독 LLM 추론 시스템 (에이전트 루프 없음)
- GDPR/PIPA 적용 대상 개인정보 처리 에이전트 (동의 없는 경우)

---

## 3. 외부 타당도 검증 (A-5)

### 3.1 동시 측정 설계

각 에이전트에 대해 세 가지 평가를 동시 실시:

1. **HAchillesWorld HAS** — 본 연구 측정 지표
2. **SWE-bench Verified** — 소프트웨어 엔지니어링 벤치마크
3. **GAIA** (General AI Assistant) — 범용 에이전트 벤치마크
4. **AgentBench** — 다중 환경 에이전트 평가

### 3.2 검증 분석

```
측정 → Pearson r(HAS, SWE-bench)
      → Spearman ρ(HAS, GAIA)
      → Spearman ρ(HAS, AgentBench)
```

**목표 기준**:
- HAS ↔ SWE-bench: ρ ≥ 0.50
- HAS ↔ GAIA: ρ ≥ 0.45
- HAS ↔ AgentBench: ρ ≥ 0.50

### 3.3 수렴 타당도 vs 변별 타당도

- **수렴 타당도**: HAS와 동종 벤치마크 간 높은 상관 (ρ > 0.5)
- **변별 타당도**: HAS와 단순 언어 이해 점수(MMLU) 간 중간 상관 (ρ < 0.5) — HAS는 순수 LLM 성능이 아닌 에이전트 특화 지표임을 입증

---

## 4. HAS 가중치 재검증 (A-3, A-4)

### 4.1 다중공선성 전처리

HAW-STUDY-001 분석(Sprint 6-C)에서 확인된 지표 공선성을 HAW-STUDY-002에서 해소:

1. 각 범주(WMQ·ALM·OHM) 내 주성분 분석 적용
2. 제1 주성분으로 범주를 대표하거나, 공선성이 낮은 대표 지표 선택
3. 선택 기준: VIF < 5이면서 Shapley 중요도 상위 1개

### 4.2 Owen Value 기반 Shapley 재산출

고상관 쌍을 연합(coalition)으로 묶어 Owen value 계산:
- WMQ 연합: {SDR, ECE, PA, ODR, WMUL}
- ALM 연합: {PD, SCR, CA, GAR, AS}
- OHM 연합: {LCR, HC, HR, IRT, SU}

```
Owen_WMQ = Shapley value of WMQ-coalition in {WMQ, ALM, OHM} game
```

---

## 5. 비즈니스 KPI 측정 프로토콜

### 5.1 핵심 KPI 3종

| KPI | 정의 | 측정 방법 |
|-----|------|-----------|
| 작업 완료율 (TCR) | 에이전트가 최종 목표를 달성한 비율 | 에피소드 로그 집계 |
| 오류율 감소 (ERR) | 배포 전 대비 에러 감소율 | A/B 비교 |
| 운영 비용 절감 (OCR) | 인건비 대비 자동화 절감액 | 재무 보고 |

### 5.2 KPI 종합 지수

```
KPI_composite = 0.40 × TCR + 0.35 × ERR + 0.25 × OCR
(가중치는 산업별로 조정 가능)
```

---

## 6. 윤리 및 컴플라이언스

- **IRB 승인**: 인간 참여자 없음 (에이전트 시스템 평가) → 내부 검토위 승인
- **데이터 익명화**: 에이전트 ID SHA-256 해시 처리 (16자리)
- **PII 필터**: 에피소드 로그 전 처리 시 HAchillesWorld PIIClassifier 적용
- **감사 로그**: 모든 수집 활동 AuditLogger에 기록

---

## 7. 일정

| 단계 | 내용 | 기간 |
|------|------|------|
| 모집 | 참여 에이전트 시스템 모집 | 2026-11 ~ 2027-01 |
| 데이터 수집 | HAS + 벤치마크 동시 측정 | 2027-02 ~ 2027-04 |
| 분석 | 다중공선성·Shapley·외부 타당도 | 2027-05 ~ 2027-06 |
| 논문 | HAW-TR-003 작성 및 arXiv 제출 | 2027-07 |

---

## 8. 기대 성과

1. **HAS 가중치 공식화**: n=200 기반 파라미터 범위 → 표준 권고값 갱신
2. **외부 타당도 확인**: HAS가 SWE-bench·GAIA와 수렴하면 국제 표준 제안 근거 강화
3. **TTA 표준 갱신**: HAW-STUDY-002 결과로 TTAS.KO-XX.XXXX §4.1 가중치 업데이트
4. **arXiv 논문**: HAW-TR-003 — *"HAchillesWorld HAS v2: Large-scale Validation with External Benchmark Convergence"*

---

*본 프로토콜은 HAW-STUDY-001 분석(Sprint 6-C) 결과를 반영한 설계 초안이다.  
데이터 수집 시작 전 최종 검토 후 확정한다.*
