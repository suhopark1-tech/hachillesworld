# HAchillesWorld — World Model 진단 및 최적화 플랫폼
## 프로그램 기획서 v1.0

> **"당신의 AI 에이전트는 세계를 얼마나 정확히 이해하고 있는가?"**  
> HAchillesWorld는 기업과 개인의 AI 에이전트 시스템을 진단하고, 최적화 로드맵을 제시하며, 실행을 지원하는 SaaS 플랫폼이다.

**작성일**: 2026년 6월 1일  
**작성자**: 박성훈  
**기반 이론**: 《Agentic World Modeling 2027》 Levels × Laws 프레임워크

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [시장 기회](#2-시장-기회)
3. [핵심 문제 정의](#3-핵심-문제-정의)
4. [솔루션 개요: HAchillesWorld](#4-솔루션-개요-hachillesworld)
5. [제품 구성 — 3개 모듈](#5-제품-구성--3개-모듈)
6. [핵심 기능 상세](#6-핵심-기능-상세)
7. [기술 아키텍처](#7-기술-아키텍처)
8. [비즈니스 모델](#8-비즈니스-모델)
9. [고객 세그먼트 & 페르소나](#9-고객-세그먼트--페르소나)
10. [개발 로드맵](#10-개발-로드맵)
11. [경쟁 분석](#11-경쟁-분석)
12. [리스크 & 대응](#12-리스크--대응)
13. [성공 지표 (KPI)](#13-성공-지표-kpi)

---

## 1. Executive Summary

### 한 줄 정의
**HAchillesWorld**는 AI 에이전트 시스템의 World Model 품질을 진단하고, Levels × Laws 기반 최적화 로드맵을 자동 생성하며, 하네스 엔지니어링 실행을 지원하는 **에이전트 운영 인텔리전스 플랫폼**이다.

### 핵심 가치 제안

```
기존 MLOps 도구      → 모델 성능을 측정한다
HAchillesWorld             → 에이전트가 세계를 얼마나 잘 이해하는지 진단한다
```

- **기업**: 배포된 AI 에이전트의 숨겨진 실패 위험을 사전에 발견하고 최적화 비용을 70% 절감
- **개인**: 자신이 만든 에이전트의 현재 Level을 진단하고 다음 단계로 도약하는 구체적 경로 제시

### 시장 규모

| 구분 | 2026 | 2028 | 2030 |
|------|------|------|------|
| AI 에이전트 플랫폼 시장 | $8.6B | $28B | $97B |
| AgentOps/모니터링 세부 시장 | $0.9B | $4.2B | $18B |
| HAchillesWorld 목표 점유율 | — | 2% ($84M) | 5% ($900M) |

---

## 2. 시장 기회

### 2.1 에이전트 배포 폭증, 운영 도구는 부재

2026년 현재 기업의 에이전트 도입 현황:
- Fortune 500 기업의 **68%**가 1개 이상의 AI 에이전트를 프로덕션 배포
- 그러나 에이전트 전용 운영 도구를 보유한 기업은 **12%** 미만
- 에이전트 관련 사고(실패, 오작동, 비용 폭발)로 인한 연간 손실: 기업당 평균 $2.3M

### 2.2 기존 도구의 구조적 한계

| 도구 유형 | 무엇을 측정하는가 | 무엇을 놓치는가 |
|-----------|-----------------|-----------------|
| 일반 MLOps (MLflow, W&B) | 모델 정확도, 훈련 손실 | 에이전트의 세계 이해 품질 |
| APM 도구 (Datadog, New Relic) | 응답시간, 에러율 | 의사결정 품질, Simulation Drift |
| LLM 평가 도구 (LangSmith) | 출력 품질, 토큰 비용 | World Model 캘리브레이션 |
| 없음 | — | Levels 진단, Laws 도메인 최적화 |

**HAchillesWorld가 채우는 공백**: 에이전트가 **"왜 그 결정을 내렸는가"**, **"World Model이 현실과 얼마나 괴리됐는가"**, **"지금 어느 Level이며 무엇을 해야 다음 Level로 가는가"**

### 2.3 개인 시장의 성장

- 2026년 AI 에이전트를 직접 개발하는 개인 개발자: 전 세계 약 3,200만 명 추정
- 이 중 자신의 에이전트를 체계적으로 진단할 방법을 가진 비율: 5% 미만
- 교육·자기계발 목적의 AI 도구 시장: 연 40% 성장 중

---

## 3. 핵심 문제 정의

### 기업이 겪는 3가지 핵심 고통

**고통 1: "우리 에이전트가 왜 실패했는지 모른다"**
```
현상: 에이전트가 예상과 다른 결정을 내림
원인: World Model의 Simulation Drift가 축적됐으나 감지 못함
결과: 실패 후 사후 대응, 재발 방지 불가
```

**고통 2: "L3 에이전트를 만들고 싶은데 어디서부터 시작해야 하는지 모른다"**
```
현상: AI 팀이 개선 방향을 잡지 못하고 표류
원인: 현재 시스템이 어느 Level인지, 무엇이 병목인지 진단 도구 부재
결과: 비효율적 투자, 낮은 ROI
```

**고통 3: "AI 비용이 폭발하는데 어디서 새는지 모른다"**
```
현상: LLM API 비용 예산 초과
원인: 라우팅 최적화 부재, 불필요한 대형 모델 과다 사용
결과: AI 도입 ROI 악화, 경영진 신뢰 하락
```

### 개인이 겪는 3가지 핵심 고통

**고통 1: "내 에이전트가 L1인지 L2인지 모른다"**
- 자신의 시스템 수준을 객관적으로 측정할 기준이 없음

**고통 2: "책이나 논문은 읽었는데 실제로 뭘 구현해야 하는지 모른다"**
- 이론과 실전 사이의 간극을 메워주는 가이드 부재

**고통 3: "내 코드가 제대로 작동하는지 확인할 방법이 없다"**
- 에이전트 코드의 정상 동작 여부를 자동으로 검증하는 도구 없음

---

## 4. 솔루션 개요: HAchillesWorld

### 4.1 제품 철학

> **"진단 없는 최적화는 도박이다."**

HAchillesWorld는 의료 진단의 방법론을 AI 에이전트에 적용한다:
- 의사는 치료 전에 반드시 진단한다
- 엔지니어도 최적화 전에 반드시 시스템을 진단해야 한다

### 4.2 핵심 프레임워크: Levels × Laws 진단 엔진

HAchillesWorld의 모든 분석은 《Agentic World Modeling 2027》의 **Levels × Laws 2차원 좌표계**를 기반으로 한다:

```
         Physical  Digital  Social  Scientific
         Laws      Laws     Laws    Laws
         ────────────────────────────────────
L1       ·         ·        ·       ·
Predictor│

L2       ·         ·        ·       ·
Simulator│

L3       ·         ·        ·       ·
Evolver  │
```

**HAchillesWorld가 하는 일**:
1. 사용자의 에이전트를 이 좌표계 어디에 위치시키는지 자동 진단
2. 현재 좌표에서의 핵심 병목 식별
3. 목표 좌표로 이동하는 최적화 로드맵 자동 생성
4. 실행 과정의 모니터링과 재진단

### 4.3 제품 라인업

```
┌─────────────────────────────────────────────────────────────┐
│                        HAchillesWorld                              │
├──────────────┬──────────────────┬──────────────────────────┤
│  HAchillesWorld     │  HAchillesWorld         │  HAchillesWorld                 │
│  Scan        │  Optimize        │  Operate                 │
│  (진단)      │  (최적화)        │  (운영)                  │
│              │                  │                          │
│  현재 Level  │  맞춤 로드맵     │  실시간 모니터링         │
│  Laws 도메인 │  하네스 설계     │  드리프트 경보           │
│  병목 분석   │  코드 생성 지원  │  Meta-Harness 자동화     │
│              │                  │                          │
│  개인·SMB    │  SMB·Enterprise  │  Enterprise              │
└──────────────┴──────────────────┴──────────────────────────┘
```

---

## 5. 제품 구성 — 3개 모듈

### Module 1: HAchillesWorld Scan — 진단 엔진

**핵심 기능**: 에이전트 시스템을 업로드하거나 연결하면 10분 안에 진단 리포트 생성

#### 진단 항목 (15개 지표)

**Category A: World Model 품질 (5개)**

| 지표 | 측정 방법 | 임계값 |
|------|-----------|--------|
| Prediction Error Rate | 예측-현실 괴리 평균 | < 0.15 |
| Calibration ECE | Expected Calibration Error | < 0.10 |
| Simulation Drift 발생률 | 드리프트 임계값 초과 빈도 | < 5% |
| Uncertainty Coverage | 불확실성이 실제 오차를 포괄하는 비율 | > 80% |
| Long-horizon Stability | N-step 롤아웃 후 오차 수준 | 도메인별 기준 |

**Category B: 에이전시 수준 (5개)**

| 지표 | L1 기준 | L2 기준 | L3 기준 |
|------|---------|---------|---------|
| 계획 깊이 (Planning Depth) | 1 스텝 | 5~50 스텝 | 동적 조정 |
| 자기 수정 능력 | 없음 | 룰 기반 | 자율 학습 |
| 목표 일관성 | — | 고정 목표 | 목표 추론 |
| 불확실성 인식 | 없음 | 임계값 기반 | 메타인지 |
| 환경 적응 속도 | 없음 | 수동 재학습 | 온라인 학습 |

**Category C: 운영 건전성 (5개)**

| 지표 | 정상 | 경고 | 위험 |
|------|------|------|------|
| 재보정(Recalibration) 빈도 | < 10% | 10~25% | > 25% |
| 비용 효율 (토큰/태스크) | 기준선 대비 ±20% | +20~50% | +50% 이상 |
| HITL 요청 빈도 | < 5% | 5~20% | > 20% |
| 하네스 위반 시도 | 0건 | 1~5건/일 | > 5건/일 |
| 체크포인트 복구 성공률 | > 98% | 90~98% | < 90% |

#### 진단 리포트 예시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HAchillesWorld Scan Report
  시스템: 고객사 공급망 최적화 에이전트
  진단일: 2026-06-01
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  현재 위치: L2 Simulator × Digital Laws
  목표 위치: L2 Simulator × Digital+Social Laws

  종합 점수: 67/100  ⚠️ 주의

  ┌──────────────────────────────────────┐
  │ World Model 품질        72/100  🟡   │
  │ 에이전시 수준           61/100  🟡   │
  │ 운영 건전성             68/100  🟡   │
  └──────────────────────────────────────┘

  🔴 즉시 조치 필요 (2건)
  ├─ Simulation Drift: 재보정 빈도 31% (기준: 10%)
  └─ 캘리브레이션 ECE: 0.23 (기준: 0.10)

  🟡 단기 개선 권장 (4건)
  ├─ 계획 깊이: 3스텝 → 15스텝 목표
  ├─ 불확실성 표현 미구현
  ├─ 하네스 규칙 6개만 정의 (권장: 20개+)
  └─ 비용: 예산 대비 143% 사용 중

  📋 최적화 로드맵 → HAchillesWorld Optimize에서 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Module 2: HAchillesWorld Optimize — 최적화 엔진

**핵심 기능**: Scan 결과를 기반으로 맞춤형 최적화 로드맵 자동 생성 + 실행 지원

#### 2.1 로드맵 자동 생성

진단 결과를 입력받아 다음을 자동 생성:

**① 우선순위 매트릭스** (영향도 × 구현 난이도)

```
                높음
        ────────────────────────────────
        │  즉시 실행        │  계획 필요  │
영향도  │  (High Impact,   │  (High     │
        │  Low Effort)     │  Impact,   │
        │                  │  High      │
        │  ──────────────  │  Effort)   │
        │  낮은 우선순위   │  재검토    │
        └──────────────────┴────────────
        낮음              높음
                      구현 난이도
```

**② 단계별 실행 계획** (4주 / 12주 / 24주)

```
Phase 1 (Week 1~4): 즉각적 안정화
├── 재보정 임계값 조정 (2일)
├── ECE 측정 파이프라인 구축 (3일)
├── 앙상블 불확실성 추가 (5일)
└── 비용 라우팅 최적화 (3일)
    예상 효과: 재보정 빈도 31% → 12%

Phase 2 (Week 5~12): 역량 강화
├── 계획 깊이 3→15스텝 확장
├── 하네스 규칙 6→20개 확장
├── HITL 트리거 정의 표준화
└── Replay Debugging 파이프라인 구축
    예상 효과: 에이전시 점수 61→78

Phase 3 (Week 13~24): L3 준비
├── 온라인 학습 루프 구현
├── Meta-Harness 초기 구축
└── Self-evolving 규칙 업데이트 파이프라인
    예상 효과: 종합 점수 67→87
```

#### 2.2 하네스 설계 자동화

진단된 실패 패턴으로부터 하네스 규칙 자동 제안:

```python
# HAchillesWorld Optimize가 자동 생성하는 하네스 규칙 예시

class GeneratedHarness:
    """HAchillesWorld Optimize가 진단 데이터 기반으로 자동 생성한 하네스."""

    # 진단: 재보정 빈도 31% → 드리프트 임계값이 너무 낮음
    DRIFT_THRESHOLD = 0.12  # 기존 0.08 → 0.12로 완화 (과잉 재보정 방지)

    # 진단: 비용 143% → 복잡도 추정 임계값 조정
    COMPLEXITY_ROUTING = {
        "simple":  {"max_tokens": 500,   "model": "haiku"},
        "medium":  {"max_tokens": 2000,  "model": "sonnet"},
        "complex": {"max_tokens": 8000,  "model": "opus"},
    }

    # 진단: 하네스 위반 3건/일 → 권한 범위 재정의
    FORBIDDEN_ACTIONS = [
        "external_api_write",    # 기존에 누락됨
        "bulk_delete",
        "config_override",
        "budget_bypass",         # 새로 추가: 비용 상한 우회 방지
    ]

    # 진단: HITL 12% → 자동 처리 범위 확대
    AUTO_APPROVE_IF = {
        "uncertainty": "< 0.15",
        "predicted_cost": "< $0.10",
        "reversible": True,
        "domain": ["read", "analyze", "report"],
    }
```

#### 2.3 코드 생성 지원

Laws 도메인에 맞는 보일러플레이트 코드 자동 생성:

```
사용자 입력: "물류 창고 로봇 에이전트, L2→L3 목표"

HAchillesWorld Optimize 출력:
├── PhysicsConstraintLayer 코드 (Physical Laws 준수)
├── EnsembleDynamics 코드 (불확실성 추정)
├── MCTSPlanner with horizon=20 (L2 적합 계획 깊이)
├── WorldModelAgent DEOR 루프
├── CircuitBreaker 설정 (로봇 안전용 임계값)
└── OpenTelemetry 계측 코드
```

---

### Module 3: HAchillesWorld Operate — 운영 인텔리전스

**핵심 기능**: 프로덕션 에이전트의 World Model 건전성 실시간 모니터링 + 자동 개선

#### 3.1 실시간 대시보드

```
┌─────────────────── HAchillesWorld Operate Dashboard ──────────────────────┐
│ 시스템: Production Agent v2.3    ■ 정상  마지막 업데이트: 3초 전     │
├──────────────┬─────────────────┬──────────────┬────────────────────┤
│ World Model  │ 예측 오차       │ 에이전시     │ 비용               │
│ 건전성       │                 │ 수준         │                    │
│              │ 0.09 ✅         │              │                    │
│  83/100      │ (기준: < 0.15)  │  L2.3/L3     │  $847 / $1,200     │
│  🟢          │                 │  🟡 진행중   │  70.6% 사용        │
└──────────────┴─────────────────┴──────────────┴────────────────────┘
│                                                                      │
│  ⚠️ 경보 (1건 활성)                                                  │
│  └─ [12:34] Simulation Drift 급증: 재보정 빈도 8% → 19% (1시간)    │
│     추정 원인: 환경 Non-stationarity 감지 → [자동 재보정 실행 중]  │
│                                                                      │
│  최근 24시간 트렌드                                                  │
│  Prediction Error: ─────────────────────────╮ 0.09               │
│  Recalibration:    ────────────────────╮╰───╯ 19% ⚠️             │
│  Token Cost:       ────────────────────────── $847                │
└──────────────────────────────────────────────────────────────────────┘
```

#### 3.2 Meta-Harness 자동화

운영 중 발견된 실패 패턴을 자동으로 하네스 규칙에 반영:

```
[HAchillesWorld Operate] 새 실패 패턴 감지
─────────────────────────────────────────────
발생: 2026-06-01 12:34:22
패턴: "inventory_api 응답 지연 > 3초 시 에이전트가
       이전 캐시 데이터로 계획 → 재고 과소 추정 → 주문 실패"
빈도: 17회/주 (이번 주 신규 패턴)

🤖 Meta-Harness 제안 규칙:
   IF api_response_time > 3s AND domain == "inventory"
   THEN use_fallback_conservative_estimate = True
        flag_for_human_review = True

승인하시겠습니까? [자동 적용] [검토 후 적용] [거부]
─────────────────────────────────────────────
```

#### 3.3 Replay Debugging

실패한 의사결정을 단계별로 재생:

```
[HAchillesWorld Operate] 실패 에피소드 재생

에피소드 ID: ep-20260601-3847
실패 유형: Goal Misalignment
발생 시각: 2026-06-01 09:12

Step 1/24: 초기 상태 인코딩
  World State: {"inventory": 847, "demand_forecast": 920}
  Uncertainty: 0.08 (낮음)

Step 12/24: 계획 분기점 ← 실패 원인
  예측: inventory = 820 (실제 환경: 620)
  Drift: 0.31 ← 임계값 0.15 초과! 재보정 누락
  선택된 행동: "주문량 축소" ← 잘못된 World Model 기반

Step 24/24: 실패 확정
  결과: 재고 부족으로 주문 이행 실패
  손실 추정: $12,400

⚡ 근본 원인: Step 12에서 Drift 임계값 초과 감지 실패
   → 재보정 트리거 미작동 (하네스 규칙 #7 버그)
   → 자동 수정 PR 생성됨: [PR #247 보기]
```

---

## 6. 핵심 기능 상세

### 6.1 Level 자동 진단 알고리즘

```python
class HAchillesWorldLevelDiagnostic:
    """
    에이전트 시스템의 Levels × Laws 위치를 자동 진단하는 엔진.
    로그, 코드 분석, 동적 프로빙 3가지 방법을 결합한다.
    """

    def diagnose(self, agent_config: dict, agent_logs: list, 
                 code_repo: str = None) -> DiagnosticReport:
        
        # 1. 정적 분석: 코드/설정 기반
        static_score = self._analyze_code(code_repo, agent_config)
        
        # 2. 동적 프로빙: 테스트 시나리오 실행
        dynamic_score = self._run_probing_scenarios(agent_config)
        
        # 3. 운영 로그 분석: 실제 운영 데이터
        log_score = self._analyze_logs(agent_logs)
        
        # 종합 Level 판정
        level = self._determine_level(static_score, dynamic_score, log_score)
        laws_domain = self._classify_laws_domain(agent_config, agent_logs)
        bottlenecks = self._identify_bottlenecks(level, laws_domain, log_score)
        
        return DiagnosticReport(
            level=level,           # "L1.7" (소수점: 전환 진행도)
            laws_domain=laws_domain,  # "Digital"
            score=self._composite_score(static_score, dynamic_score, log_score),
            bottlenecks=bottlenecks,
            recommendations=self._generate_recommendations(bottlenecks),
        )

    def _run_probing_scenarios(self, config: dict) -> dict:
        """
        표준화된 프로빙 시나리오로 에이전트 역량을 측정.
        - 1스텝 예측 정확도 (L1 지표)
        - N스텝 롤아웃 안정성 (L2 지표)  
        - 자기 수정 루프 존재 여부 (L3 지표)
        - 불확실성 인식 정확도
        """
        scenarios = [
            SingleStepPredictionScenario(),   # L1 측정
            MultiStepRolloutScenario(n=20),   # L2 측정
            SelfCorrectionScenario(),          # L3 측정
            OODGeneralizationScenario(),       # 일반화 능력
            UncertaintyCalibrationScenario(),  # 캘리브레이션
        ]
        return {s.name: s.evaluate(config) for s in scenarios}
```

### 6.2 개인용 Learning Path 엔진

개인 사용자를 위한 커리큘럼 자동 생성:

```
사용자 프로필: 백엔드 개발자, Python 3년, AI 경험 6개월
목표: "6개월 내에 L2 Simulator 구현 가능하게 되고 싶다"

HAchillesWorld Learning Path:

Week 1~2: 기반 이해
├── World Model 핵심 개념 (이론 5시간)
├── StateEncoder 직접 구현 (실습 8시간)
└── 진단: Prediction Error 측정 파이프라인 구축

Week 3~4: L1 완성
├── EnsembleDynamics 구현
├── 불확실성 시각화
└── 미니 프로젝트: GridWorld Agent

Week 5~8: L2 진입
├── MCTS 계획기 구현
├── N-step 롤아웃 디버깅
├── Simulation Drift 감지 추가
└── 미니 프로젝트: Web Navigation Agent

Week 9~12: L2 심화
├── 비용 최적화 (CostAwareRouter)
├── HITL 인터페이스 구현
├── 하네스 설계 패턴 5가지
└── 최종 프로젝트: 도메인 특화 L2 에이전트

현재 진행도: █████░░░░░░░ 42% (Week 5 진행 중)
다음 마일스톤: MCTS 계획기 구현 (3일 후)
```

### 6.3 비용 최적화 엔진

```
HAchillesWorld Cost Intelligence

이번 달 분석 (2026년 6월):
───────────────────────────────────────────
총 토큰 사용: 847M tokens  ($2,341)
최적화 전 예상: $3,890

절감 내역:
├─ 스마트 라우팅: $820 절감 (21%)
│   └ 복잡도 낮은 쿼리 82% → Haiku로 전환
├─ Semantic Cache 히트율 38%: $430 절감 (11%)
├─ Prompt Caching 활용: $290 절감 (7%)
└─ 배치 처리 전환: $9 절감 (0.2%)

ROI: 월 $1,549 절감 / 연 $18,588 절감
HAchillesWorld 구독료 대비 절감: 12.4배
```

---

## 7. 기술 아키텍처

### 7.1 전체 시스템 구조

```
┌──────────────────────────────────────────────────────────────┐
│                      HAchillesWorld Platform                        │
├──────────────────────────────────────────────────────────────┤
│  Web App (Next.js)    │  CLI (Python)  │  SDK (Python/TS)    │
├──────────────────────────────────────────────────────────────┤
│                    API Gateway (FastAPI)                      │
├─────────────┬────────────────┬─────────────────────────────┤
│  Scan       │  Optimize      │  Operate                    │
│  Engine     │  Engine        │  Engine                     │
│  (진단)     │  (최적화)      │  (운영)                     │
├─────────────┴────────────────┴─────────────────────────────┤
│              HAchillesWorld Core Intelligence Layer                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Levels×Laws  │  │  Harness     │  │  Cost            │  │
│  │ Classifier   │  │  Generator   │  │  Optimizer       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Drift        │  │  Replay      │  │  LLM Code        │  │
│  │ Detector     │  │  Debugger    │  │  Generator       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  PostgreSQL (메타) │ ClickHouse (시계열 메트릭) │ Redis (캐시) │
├──────────────────────────────────────────────────────────────┤
│  Telemetry Collection (OpenTelemetry Collector)              │
│  Agent → OTLP → Collector → ClickHouse → HAchillesWorld            │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 에이전트 연동 방식 (3가지 옵션)

**옵션 A: SDK 통합** (가장 정확, 5분 설정)

```python
from hachillesworld import HAchillesWorldClient, instrument

client = HAchillesWorldClient(api_key="haw-...")

@instrument(client, agent_name="supply-chain-agent")
class MyAgent:
    def plan(self, state, goal): ...
    def execute(self, action): ...
    # HAchillesWorld가 자동으로 모든 메서드 계측
```

**옵션 B: OpenTelemetry 브리지** (기존 계측 재활용)

```yaml
# otel-config.yaml에 추가
exporters:
  hachillesworld:
    endpoint: "https://ingest.hachillesworld.ai/v1"
    api_key: "${HACHILLESWORLD_API_KEY}"
```

**옵션 C: 로그 업로드** (레거시 시스템, 배치 분석)

```bash
hachillesworld scan --logs ./agent_logs/ --config ./agent_config.json
```

### 7.3 LLM 활용 전략

HAchillesWorld 자체도 AI를 사용하지만, 비용과 신뢰성을 위해 계층화:

| 기능 | 모델 | 이유 |
|------|------|------|
| 로그 분석·패턴 인식 | Claude Haiku | 반복 호출, 비용 최적화 |
| 하네스 규칙 생성 | Claude Sonnet | 품질과 비용 균형 |
| 복잡한 아키텍처 제안 | Claude Opus | 고품질 필요, 빈도 낮음 |
| 코드 생성 | Claude Sonnet + 검증 | 실행 가능성 보장 |
| Scan 리포트 서술 | Claude Haiku | 구조화된 출력 |

---

## 8. 비즈니스 모델

### 8.1 가격 구조

#### Individual 플랜 (개인 개발자)

| 플랜 | 가격 | 포함 내용 |
|------|------|-----------|
| **Free** | $0/월 | Scan 3회/월, 기본 진단 리포트, Community 접근 |
| **Starter** | $29/월 | Scan 무제한, Optimize 로드맵, Learning Path, 이메일 지원 |
| **Pro** | $79/월 | 전체 기능 + Operate (1개 에이전트), API 접근, 우선 지원 |

#### Enterprise 플랜

| 플랜 | 가격 | 포함 내용 |
|------|------|-----------|
| **Team** | $499/월 | 5개 에이전트, 팀 협업, SSO, Slack 통합 |
| **Business** | $1,999/월 | 25개 에이전트, 전용 지원, 커스텀 하네스 룰 |
| **Enterprise** | 협의 | 무제한 에이전트, On-premise 옵션, SLA, 컨설팅 |

#### 추가 수익원

| 항목 | 모델 | 예상 단가 |
|------|------|-----------|
| 컨설팅 | 프로젝트 기반 | $5,000~$50,000/프로젝트 |
| 교육 워크숍 | 1일 오프라인 | $500/인, 기업 단체 $8,000/회 |
| 인증 프로그램 | "HAchillesWorld Certified Engineer" | $299/인 |
| Marketplace | 하네스 룰 템플릿 판매 수수료 | 판매액의 30% |

### 8.2 수익 전망

```
Year 1 (2027):
├─ 목표 고객: 개인 2,000명, 기업 50개
├─ ARR 목표: $1.2M
└─ 핵심 지표: NRR > 110%

Year 2 (2028):
├─ 목표 고객: 개인 15,000명, 기업 400개
├─ ARR 목표: $8.5M
└─ 핵심 지표: CAC 회수 기간 < 8개월

Year 3 (2029):
├─ 목표 고객: 개인 80,000명, 기업 2,000개
├─ ARR 목표: $42M
└─ 핵심 지표: Logo NRR > 125%
```

### 8.3 단위 경제학

```
Enterprise Business 플랜 기준:

LTV 계산:
  ARPU: $1,999/월 × 12 = $23,988/년
  평균 계약 기간: 3.2년 (추정)
  LTV = $76,762

CAC 계산:
  마케팅비: $8,000/고객
  영업비: $4,000/고객
  CAC = $12,000

LTV:CAC = 6.4:1  ✅ (목표: > 3:1)
CAC 회수 기간: 6.0개월  ✅ (목표: < 12개월)
```

---

## 9. 고객 세그먼트 & 페르소나

### 페르소나 1: 기업 AI 아키텍트 — "진단이 필요한 이민혁"

```
이름: 이민혁 (38세)
직책: Senior AI Architect, 핀테크 스타트업 (직원 200명)
현황:
  - Claude API 기반 에이전트 3개 프로덕션 운영 중
  - 한 달에 한 번씩 이유 불명의 에이전트 오작동 발생
  - CTO가 "AI 비용이 왜 이렇게 많이 나오냐" 추궁
  - LLM 모니터링 도구는 있지만 에이전트 수준 진단은 없음

HAchillesWorld가 주는 가치:
  - 오작동 원인을 Replay Debugger로 10분 내 식별
  - 비용 절감 로드맵으로 CTO 설득 자료 확보
  - "현재 L2.1, 목표 L2.5" 명확한 로드맵으로 팀 정렬

구매 경로: 무료 Scan → 결과 공유 → CTO 설득 → Team 플랜
예상 구독: Team ($499/월)
```

### 페르소나 2: 스타트업 창업자 — "빠른 의사결정이 필요한 Sarah"

```
이름: Sarah Kim (32세)
직책: CTO & Co-founder, AI 에이전트 스타트업 (시드 단계)
현황:
  - 자사 에이전트가 경쟁사 대비 얼마나 좋은지 모름
  - 투자자 미팅에서 "기술 차별화가 무엇인가" 질문에 답 못함
  - 엔지니어 2명이 에이전트 개발 중, 방향 정렬 필요

HAchillesWorld가 주는 가치:
  - "우리 에이전트는 L2.3, 경쟁사 추정 L2.0" 객관적 비교
  - 투자자 피치에 사용 가능한 기술 지표 확보
  - 엔지니어링 로드맵을 HAchillesWorld 기준으로 정렬

구매 경로: Y Combinator 스타트업 네트워크 소개 → Starter
예상 구독: Business ($1,999/월)
```

### 페르소나 3: 개인 개발자 — "성장하고 싶은 박준우"

```
이름: 박준우 (27세)
직책: 주니어 백엔드 개발자, 사이드 프로젝트로 AI 에이전트 개발
현황:
  - YouTube와 블로그로 독학 중, 방향성이 없음
  - "내 코드가 맞는 건지" 확신이 없음
  - 포트폴리오에 AI 프로젝트를 넣고 싶음

HAchillesWorld가 주는 가치:
  - "현재 L1.4, Starter는 L2" 명확한 현재 위치
  - 주차별 Learning Path로 체계적 성장
  - HAchillesWorld Certified 자격증으로 이직 시 차별화

구매 경로: Free → 결과에 감동 → Pro ($79/월)
```

---

## 10. 개발 로드맵

### Phase 0: 검증 (2026년 7~9월, 3개월)

**목표**: 핵심 가설 검증 — "진단 리포트에 $50 이상의 가치를 느끼는가"

```
MVP 범위:
├── Scan Engine v0.1
│   ├── 15개 지표 중 7개 구현 (핵심 지표 우선)
│   ├── PDF 진단 리포트 자동 생성
│   └── CLI 도구 (API 연동 없음, 로컬 실행)
├── 베타 테스터 모집: 50명 (개인 30명, 기업 20개)
└── 성공 기준: NPS > 40, 월 $50 지불 의향 > 60%

기술 스택 선택:
├── Backend: Python + FastAPI
├── Frontend: Next.js (대시보드)
├── DB: PostgreSQL + ClickHouse
└── 인프라: AWS (ECS + RDS)
```

### Phase 1: Launch (2026년 10~12월, 3개월)

**목표**: 첫 유료 고객 100명 확보

```
제품:
├── HAchillesWorld Scan v1.0 (15개 지표 전체)
├── HAchillesWorld Optimize v0.5 (로드맵 생성)
├── Web 대시보드
├── Python SDK v1.0
└── Free / Starter / Pro 플랜 론칭

GTM:
├── 《Agentic World Modeling 2027》 독자 대상 얼리버드
├── ProductHunt 론칭
├── AI 엔지니어 커뮤니티 (Discord, Reddit) 진입
└── 콘텐츠 마케팅: "내 에이전트 Level 진단법" 시리즈
```

### Phase 2: Growth (2027년 1~6월, 6개월)

**목표**: ARR $1.2M, 기업 고객 50개

```
제품:
├── HAchillesWorld Operate v1.0 (실시간 모니터링)
├── Meta-Harness 자동화
├── Enterprise SSO + RBAC
├── Slack / Teams 알림 통합
└── Replay Debugger v1.0

파트너십:
├── Anthropic 파트너 프로그램 참여
├── AWS Marketplace 등록
└── 주요 클라우드 인프라 통합 (Azure, GCP)
```

### Phase 3: Scale (2027년 7월~2028년 6월, 12개월)

**목표**: ARR $8.5M, 글로벌 진출

```
제품:
├── Marketplace (하네스 룰 템플릿 생태계)
├── Multi-agent 진단 지원
├── On-premise 배포 옵션
├── API-first (화이트레이블)
└── 자동화된 L3 전환 지원 도구

글로벌:
├── 영어권 론칭 (미국·유럽)
├── 현지 파트너십 (SI, 컨설팅 펌)
└── 교육 기관 파트너십 (대학·부트캠프)
```

---

## 11. 경쟁 분석

### 11.1 직접 경쟁자

| 회사 | 포지셔닝 | 강점 | 약점 | HAchillesWorld 차별화 |
|------|---------|------|------|----------------|
| LangSmith | LLM 앱 추적·평가 | LangChain 생태계 | World Model 개념 없음 | Levels×Laws 진단, 최적화 |
| Langfuse | LLM 관측성 | 오픈소스, 가격 | 에이전트 특화 부족 | 에이전트 전용 깊이 |
| Weights & Biases | ML 실험 추적 | 강력한 시각화 | 에이전트 운영 약함 | 실시간 운영 지원 |
| Datadog AI | 인프라+AI 통합 | 기존 고객 기반 | AI 이해도 낮음 | World Model 전문성 |

### 11.2 간접 경쟁자

| 유형 | 예시 | HAchillesWorld가 이기는 이유 |
|------|------|----------------------|
| 컨설팅 펌 | Accenture AI Lab | 속도: 진단 10분 vs 수주 |
| 내부 개발 | 자체 모니터링 구축 | 비용: 구독료 vs 엔지니어링 시간 |
| 범용 APM | Datadog, New Relic | 깊이: 에이전트 전용 지표 |

### 11.3 방어 가능한 해자

1. **이론적 해자**: Levels × Laws 프레임워크는 이 책의 독점적 지식 자산
2. **데이터 해자**: 수만 개 에이전트 진단 데이터 → 벤치마크 DB → 진단 정확도 향상
3. **네트워크 효과**: 커뮤니티의 하네스 룰 공유 → Marketplace → 참여자 증가
4. **전환 비용**: 운영 통합이 깊어질수록 교체 비용 증가

---

## 12. 리스크 & 대응

| 리스크 | 발생 가능성 | 영향도 | 대응 전략 |
|--------|------------|--------|-----------|
| 대형 클라우드(AWS/Azure)의 유사 서비스 출시 | 중 | 높음 | 전문성 심화 + 파트너십 전환 |
| LLM API 비용 상승 | 높음 | 중 | 자체 소형 모델 파인튜닝, 캐싱 |
| 에이전트 시장 성장 둔화 | 낮음 | 높음 | 다각화: 교육·컨설팅 수익 비중 확대 |
| 데이터 보안 우려 | 중 | 높음 | On-premise 옵션, SOC2 인증 |
| 핵심 인력 이탈 | 중 | 중 | 지식 문서화, 에쿼티 구조 |
| 경쟁사의 빠른 카피 | 높음 | 중 | 실행 속도 + 데이터 해자 구축 |

---

## 13. 성공 지표 (KPI)

### 제품 지표

| 지표 | Phase 1 목표 | Phase 2 목표 | Phase 3 목표 |
|------|-------------|-------------|-------------|
| 월간 활성 사용자(MAU) | 500 | 8,000 | 60,000 |
| 유료 전환율 (Free→유료) | 8% | 12% | 15% |
| Net Revenue Retention | > 105% | > 115% | > 125% |
| 진단 정확도 (사용자 만족도) | > 75% | > 85% | > 90% |
| Scan → Optimize 전환율 | > 40% | > 55% | > 65% |

### 비즈니스 지표

| 지표 | 2027 | 2028 | 2029 |
|------|------|------|------|
| ARR | $1.2M | $8.5M | $42M |
| 고객 수 (기업) | 50 | 400 | 2,000 |
| 고객 수 (개인) | 2,000 | 15,000 | 80,000 |
| Gross Margin | 65% | 72% | 78% |
| NPS | > 40 | > 55 | > 65 |

### 이론 실현 지표

> 이 제품이 《Agentic World Modeling 2027》의 이론을 실제로 세상에 실현하는지 확인하는 지표

| 지표 | 측정 방법 | 목표 |
|------|-----------|------|
| L2→L3 전환 성공률 | HAchillesWorld 사용 고객의 Level 상승 추적 | > 30% (12개월 내) |
| 하네스 적용 후 실패율 감소 | Before/After 비교 | > 50% 감소 |
| 비용 절감 실현율 | 예측 대비 실제 절감 | 예측의 > 70% 실현 |
| "진단 없이 최적화" 사례 감소 | 커뮤니티 설문 | 연 20% 감소 |

---

## 부록 A. 기술 스택 상세

```
Frontend:     Next.js 14, TypeScript, Tailwind CSS, Recharts
Backend:      Python 3.12, FastAPI, Pydantic v2
AI Engine:    Claude Sonnet 4.6 (메인), Haiku 4.5 (배치)
Database:     PostgreSQL 16 (메타), ClickHouse (시계열), Redis 7 (캐시)
Telemetry:    OpenTelemetry Collector, Jaeger (추적)
Infrastructure: AWS (ECS Fargate, RDS, ElastiCache, S3)
Monitoring:   Prometheus + Grafana (HAchillesWorld 자체 모니터링)
CI/CD:        GitHub Actions, Docker
```

## 부록 B. 론칭 전 체크리스트

**제품**
- [ ] Scan Engine 15개 지표 전체 구현 및 검증
- [ ] SDK 설치 5분 이내 완료 가능한지 사용자 테스트
- [ ] 진단 리포트 PDF 생성 자동화
- [ ] 보안: SOC2 Type I 준비 시작

**GTM**
- [ ] 《Agentic World Modeling 2027》 독자 사전 등록 페이지
- [ ] 얼리버드 50% 할인 쿠폰 코드 준비
- [ ] ProductHunt 론칭 셋팅
- [ ] "내 에이전트 Level 진단하기" 무료 체험 캠페인

**법무·재무**
- [ ] 법인 설립 및 IP 등록
- [ ] 개인정보 처리방침 (GDPR, 개인정보보호법)
- [ ] 종자 자금 조달 계획

---

## 부록 C. 핵심 메시지 (카피라이팅)

**메인 슬로건**
> "당신의 AI가 세계를 얼마나 잘 이해하는지, 10분 만에 알 수 있습니다."

**엘리베이터 피치** (30초)
> "AI 에이전트를 배포한 기업의 88%는 에이전트가 왜 실패하는지 알 방법이 없습니다. HAchillesWorld는 에이전트의 World Model을 진단하고, 어디가 문제인지 찾아내고, 어떻게 고쳐야 하는지 알려줍니다. Levels × Laws 프레임워크로 현재 수준을 측정하고, 다음 단계로 가는 로드맵을 10분 안에 받아보세요."

**개인 개발자용**
> "내 에이전트가 L1인지 L2인지, 이제 측정할 수 있습니다."

**기업용**
> "에이전트 실패의 77%는 World Model 문제입니다. 배포 전에 진단하세요."

---

*HAchillesWorld 기획서 v1.0 — 2026년 6월 1일*  
*이 기획서는 《Agentic World Modeling 2027: The Architecture of Autonomous Intelligence》의 이론적 기반 위에 구축된 제품 아이디어입니다.*  
*저자: 박성훈*
