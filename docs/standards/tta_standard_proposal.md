# TTA 표준 제안서 초안
## TTAS.KO-XX.XXXX: AI 에이전트 World Model 품질 평가 표준

**문서 번호**: HAW-STD-001  
**버전**: 0.9 (WG 제출 초안)  
**작성일**: 2026-06-06  
**작성자**: 박성훈 (HAchillesWorld 연구팀)  
**근거 보고서**: HAW-TR-001, HAW-TR-002  

---

## 1. 제안 배경

### 1.1 AI 에이전트의 급속한 확산과 평가 공백

2025년 이후 LLM 기반 AI 에이전트가 산업 전반에 배포됨에 따라, 에이전트의 **World Model 품질** — 환경 인식·예측·계획·실행 역량 — 을 객관적으로 평가하고 비교할 수 있는 국내 표준이 부재하다.

현행 AI 관련 국내 표준(TTA TTAS.KO-10.xxxx 시리즈)은 주로 LLM 단독 모델의 성능 평가에 집중되어 있으며, **다단계 자율 계획·실행이 가능한 에이전트 시스템**에 특화된 품질 지표 체계가 없다.

### 1.2 HAW-TR-001 · HAW-TR-002 실증 근거

- **HAW-TR-001** (2026): *HAchillesWorld SDK v1.x — AI 에이전트 World Model 품질 측정 체계*  
  15개 지표의 측정 방법론, 임계값 도출 근거, L1~L3 역량 분류 체계를 제시

- **HAW-TR-002** (2026): *Shapley 가치 기반 HAS 가중치 재보정 실증 연구*  
  HAW-STUDY-001(n=50 에이전트)을 통해 WMQ:ALM:OHM = 0.45:0.35:0.20 가중치를 실증적으로 검증

본 제안서는 두 보고서의 실증 결과를 바탕으로 TTA 워킹그룹(WG) 제출용 표준 제안서를 작성한다.

---

## 2. 표준 범위 및 목적

### 2.1 목적

본 표준은 AI 에이전트 시스템의 World Model 품질을 **측정·평가·비교**하기 위한 15개 지표와 종합 점수(HAS) 산출 방법을 규정한다.

### 2.2 적용 범위

- **대상 시스템**: LLM 기반 자율 에이전트, 멀티에이전트 시스템, 로봇 제어 에이전트
- **역량 범위**: L1 Predictor부터 L3 Evolver까지
- **도메인**: Physical·Digital·Social·Scientific 4개 운용 도메인

### 2.3 제외 범위

- 단독 LLM 추론 성능 (MMLU, HumanEval 등 벤치마크로 별도 평가)
- 에이전트 보안·취약점 평가 (별도 표준 필요)

---

## 3. 15개 지표 표준화 제안

### 3.1 범주 I: World Model 품질 (WMQ, 5개 지표)

| 지표 코드 | 명칭 | 정의 | 단위 | 권장 임계값 |
|-----------|------|------|------|------------|
| WMQ-01 | SDR (Simulation Drift Rate) | 에이전트 시뮬레이션과 실제 환경 간 분포 차이율 | 0~1 | ≤ 0.05 |
| WMQ-02 | ECE (Expected Calibration Error) | 예측 확률과 실제 정확도의 차이 | 0~1 | ≤ 0.05 |
| WMQ-03 | PA (Prediction Accuracy) | 다음 상태 예측 정확도 | 0~1 | ≥ 0.80 |
| WMQ-04 | ODR (OOD Detection Rate) | 분포 외 입력 탐지 성공률 | 0~1 | ≥ 0.80 |
| WMQ-05 | WMUL (World Model Update Latency) | 새 관측 후 내부 모델 갱신 지연시간 | ms | ≤ 100 |

**측정 방법**:
- SDR: Jensen-Shannon Divergence D_JS(P_sim ∥ P_real)
- ECE: 신뢰도 구간 분할법 (M=10 bin)
- PA: 상태 공간 예측 정확도 (MSE 또는 분류 정확도)
- ODR: 에너지 점수(Energy Score) 기반 임계값 분류
- WMUL: 관측 수신 → 내부 상태 갱신 완료까지의 평균 지연

### 3.2 범주 II: 에이전시 수준 지표 (ALM, 5개 지표)

| 지표 코드 | 명칭 | 정의 | 단위 | 권장 임계값 |
|-----------|------|------|------|------------|
| ALM-01 | PD (Planning Depth) | 에이전트가 생성하는 계획의 평균 깊이 | 스텝 수 | ≥ 3 |
| ALM-02 | SCR (Subtask Completion Rate) | 다단계 과제 하위 작업 완료율 | 0~1 | ≥ 0.80 |
| ALM-03 | CA (Counterfactual Accuracy) | 반사실 시나리오에서의 행동 적절성 | 0~1 | ≥ 0.70 |
| ALM-04 | GAR (Goal Achievement Rate) | 최종 목표 달성률 | 0~1 | ≥ 0.80 |
| ALM-05 | AS (Adaptation Score) | 환경 변화에 대한 행동 적응 점수 | 0~1 | ≥ 0.70 |

**측정 방법**:
- PD: 계획 트리 최대 깊이 (BFS/DFS 탐색 깊이)
- SCR: 완료 하위 작업 수 / 전체 하위 작업 수
- CA: LLM-as-Judge 반사실 평가 (GPT-4o 또는 동급 모델)
- GAR: 목표 달성 에피소드 수 / 전체 에피소드 수
- AS: 환경 변화 후 성과 회복률

### 3.3 범주 III: 운영 건전성 지표 (OHM, 5개 지표)

| 지표 코드 | 명칭 | 정의 | 단위 | 권장 임계값 |
|-----------|------|------|------|------------|
| OHM-01 | LCR (Loop Completion Rate) | 에이전트 루프 정상 완료율 | 0~1 | ≥ 0.95 |
| OHM-02 | HC (Human Control Rate) | 인간 개입 통제 성공률 | 0~1 | ≥ 0.90 |
| OHM-03 | HR (Hallucination Rate) | 사실 오류 생성 비율 | 0~1 | ≤ 0.05 |
| OHM-04 | IRT (Incident Recovery Time) | 사고 발생 후 복구 완료 시간 | 초(s) | ≤ 60 |
| OHM-05 | SU (Safety Unwinding Rate) | 안전 해제 실패 비율 | 0~1 | ≤ 0.01 |

---

## 4. HAS 종합 점수 — 국가 표준 평가 지표 제안

### 4.1 HAS (Holistic Agent Score) 정의 및 가중치 산출 방법론

```
HAS = w_WMQ × WMQ_score + w_ALM × ALM_score + w_OHM × OHM_score
```

각 범주 점수는 소속 지표의 가중 평균 (0~100 정규화).

#### 가. 표준 권고값 (HAW-STUDY-001, n=50, 파일럿 기준)

> **주의**: 본 권고값은 파일럿 연구(n=50) 기반이며, HAW-STUDY-002(n=200 목표) 완료 후 갱신될 수 있다.

| 범주 | 권고 범위 | 중앙값 | 산출 근거 |
|------|----------|--------|----------|
| w_WMQ (World Model 품질) | 0.40 ~ 0.50 | 0.45 | HAW-TR-002 Shapley 분석 |
| w_ALM (에이전시 수준) | 0.30 ~ 0.40 | 0.35 | HAW-TR-002 Shapley 분석 |
| w_OHM (운영 건전성) | 0.15 ~ 0.25 | 0.20 | HAW-TR-002 Shapley 분석 |

#### 나. 조직별 맞춤 산출 (권장)

최소 n=100 자체 데이터로 Shapley 기반 가중치 산출 가능.
**HAS 버전 명시**로 시계열 비교가능성 확보 필수 (`HAS-v2.1` 형식).

```python
# HAchillesWorld SDK v2.1 — 가중치 재산출 예시
from hachillesworld.analyze.study_analysis import StudyAnalyzer

analyzer = StudyAnalyzer()
dataset = analyzer.load_study_data("YOUR-STUDY-ID")
weights = analyzer.shapley_recalibration(dataset)
print(weights.summary())  # → 조직별 Shapley 가중치
```

#### 다. 다중공선성 주의사항 (Sprint 6-C, A-3)

15개 지표는 범주 내 높은 상관(|r| ≈ 0.85~0.95)을 보이므로
**지표 레벨 Shapley 해석 시 다중공선성 검증 필수**:

```python
from hachillesworld.analyze.multicollinearity import MulticollinearityAnalyzer

mc = MulticollinearityAnalyzer()
report = mc.analyze(metric_matrix, metric_names)
# VIF > 10 지표 발견 시 대표 지표 선택 또는 PCA 적용 권고
```

### 4.2 도메인 조정 HAS (daHAS)

도메인별 지표 중요도 차이를 반영한 조정 점수:

```
daHAS = HAS × domain_adjustment_factor(domain)
```

| 도메인 | SDR 가중 | ECE 가중 | PD 가중 | IRT 가중 |
|--------|----------|----------|---------|---------|
| Physical | 높음(×1.3) | 보통 | 높음(×1.2) | 높음(×1.4) |
| Digital | 보통 | 높음(×1.3) | 보통 | 낮음(×0.8) |
| Social | 낮음(×0.8) | 높음(×1.2) | 높음(×1.3) | 보통 |
| Scientific | 높음(×1.2) | 높음(×1.3) | 매우높음(×1.5) | 낮음(×0.7) |

### 4.3 역량 등급 체계

| HAS 점수 | 등급 | 레이블 | 배포 권장 |
|----------|------|--------|----------|
| 90~100 | A+ | 우수 에이전트 | 전면 배포 가능 |
| 80~89 | A | 양호 에이전트 | 일반 배포 가능 |
| 70~79 | B | 보통 에이전트 | 제한적 배포 |
| 60~69 | C | 주의 필요 | 감독 하 운용 |
| 60 미만 | D | 미달 에이전트 | 배포 보류 권장 |

---

## 5. 측정 프레임워크 — HAchillesWorld SDK 참조 구현

본 표준의 참조 구현체로 **HAchillesWorld SDK v2.0**을 활용한다.

```python
# 참조 구현 예시
from hachillesworld import HAchillesClient

client = HAchillesClient(api_key="...")
report = client.scan(agent_logs=logs, agent_name="MyAgent")

print(f"HAS: {report.composite_score:.1f}")
print(f"역량 레벨: {report.level_label}")
```

SDK는 다음을 자동화한다:
- 15개 지표 자동 측정
- HAS/daHAS 자동 산출
- EU AI Act Art.13~15 모니터링 참고 자료 생성
- ISO/IEC 42001 체크리스트 참고 자료 생성

---

## 5-A. ISO/IEC 42001:2023 조항 해석 근거 (D-5)

본 표준에서 인용하는 ISO/IEC 42001 조항은 다음 공식 버전을 기준으로 한다.

| 인용 조항 | 내용 | 적용 맥락 |
|-----------|------|----------|
| §6.1 리스크 평가 | AI 시스템 리스크 식별·분석·평가 | HAS 등급 C 이하 에이전트 |
| §8.4 AI 시스템 개발 | 개발 수명주기 관리 요구사항 | 에이전트 배포 전 검증 |
| §9.1 모니터링 | AI 성과 모니터링 방법 | 실시간 HAS 추적 |
| §10.2 부적합 및 시정조치 | 성과 미달 시 조치 절차 | HAS 등급 D 에이전트 처리 |

> **면책 조항**: 본 문서의 ISO/IEC 42001 조항 해석은
> **ISO/IEC 42001:2023 (초판, 2023-12-15)** 기준이며,
> 표준 개정 시 재검토가 필요하다.
> 공식 법적 의무 여부는 인증 기관 또는 법률 전문가의 확인을 받을 것을 권고한다.

---

## 6. 표준 제안 절차 및 일정

| 단계 | 내용 | 예정 시기 |
|------|------|----------|
| WG 초안 제출 | 본 문서 TTA 워킹그룹 제출 | 2026년 9월 |
| 전문가 검토 | 산학연 검토 및 의견 수렴 | 2026년 10~11월 |
| 공개 초안 | 공개 의견 수렴 (60일) | 2026년 12월 |
| 표준 확정 | TTA 표준 확정 및 공시 | 2027년 3월 |

---

## 7. 참고 문헌

1. HAW-TR-001: *HAchillesWorld SDK — AI 에이전트 World Model 품질 측정 체계* (2026)
2. HAW-TR-002: *Shapley 가치 기반 HAS 가중치 재보정 실증 연구* (2026)
3. EU AI Act (Regulation (EU) 2024/1689), Art.13, 14, 15
4. ISO/IEC 42001:2023 — AI Management Systems
5. Guo et al. (2017). *On Calibration of Modern Neural Networks*. ICML.
6. LeCun, Y. (2022). *A Path Towards Autonomous Machine Intelligence*. OpenReview.

---

*본 문서는 TTA TTAS AI 에이전트 품질 평가 워킹그룹 제출용 초안이다.*  
*최종 표준 번호는 TTA 심의 후 부여된다.*
