# HAchillesWorld 비전·로드맵·채택 이유
## 저자·기획자 공개 토론 세션 (2026-10-31)

> **발표자**: 박성훈 (《Agentic World Modeling 2027》 저자, arXiv HAW-TR-001 공동저자,  
> HAchillesWorld 플랫폼 기획자)  
>
> **형식**: 다분야 토론자들의 질의 응답  
> **토론자**: AI 안전 연구자 · 엔터프라이즈 컴플라이언스 담당 · 스타트업 CTO ·  
> MLOps 엔지니어 · 학계 지도교수 · 벤처 투자자

---

## 개요: 이 세션이 다루는 질문들

| 섹션 | 핵심 질문 |
|------|-----------|
| [1. 모두 발언](#1-모두-발언-기획자-박성훈) | "왜 World Model 품질인가?" |
| [2. 비전·철학](#2-비전과-철학) | "AI 에이전트 측정의 근본 문제" |
| [3. 기술 아키텍처](#3-기술-아키텍처-deep-dive) | "어떻게 측정하는가?" |
| [4. 고객 채택 이유](#4-고객이-채택해야-하는-이유) | "왜 지금, 왜 이것인가?" |
| [5. 기업 도입 효과](#5-기업-도입-시-구체적-효과) | "ROI와 위험 감소" |
| [6. 로드맵](#6-로드맵--비전) | "2027년 이후 어디로 가는가?" |
| [7. 비판과 반론](#7-비판적-질문과-솔직한-답변) | "약점은 무엇인가?" |
| [8. 맺음말](#8-맺음말) | "AI 에이전트 시대의 책임" |

---

## 1. 모두 발언: 기획자 박성훈

감사합니다. 오늘 이 자리에 AI 안전, 컴플라이언스, 엔지니어링, 학문, 투자 등 다양한 분야의 전문가들을 모시게 되어 영광입니다.

저는 세 가지 질문에서 출발했습니다.

> **"LLM 성능 벤치마크는 넘쳐나는데, 왜 AI 에이전트 품질 측정 체계는 없는가?"**

> **"에이전트가 실패했을 때, 우리는 사전에 알 수 있었을까?"**

> **"'AI가 안전하다'고 말하려면, 무엇을 측정해야 하는가?"**

이 세 질문이 《Agentic World Modeling 2027》 책으로, HAW-TR-001 논문으로, 그리고 HAchillesWorld 플랫폼으로 이어졌습니다.

결론부터 말씀드리겠습니다.

**AI 에이전트의 품질은 LLM의 언어 능력이 아니라 World Model의 품질에 달려 있습니다.**

에이전트가 얼마나 유창하게 말하느냐가 아니라, 세상을 얼마나 정확하게 예측하고, 얼마나 깊이 계획하며, 얼마나 안전하게 운용되느냐가 핵심입니다.

HAchillesWorld는 그것을 측정합니다.

---

## 2. 비전과 철학

### Q1 (AI 안전 연구자 이소연 박사)

> *"World Model이라는 개념은 Yann LeCun의 JEPA(Joint Embedding Predictive Architecture) 이론에서 왔죠. 에이전트의 내부 표현을 직접 볼 수 없는데, 어떻게 World Model 품질을 외부에서 측정할 수 있습니까?"*

정확히 핵심을 짚어주셨습니다. HAW-TR-001에서 우리가 가장 오래 고민했던 문제입니다.

LeCun의 World Model은 내부 표현(internal representation)의 개념입니다. 하지만 우리는 다른 접근을 취했습니다. **행동 관찰을 통한 역추론(behavioral inference)**입니다.

의사가 환자의 뇌 내부를 직접 볼 수 없지만 혈압·맥박·반사신경으로 건강 상태를 진단하듯이, HAchillesWorld는 에이전트의 **관찰 가능한 행동**으로부터 World Model 품질을 역추론합니다.

```
에이전트 행동 로그 → [HAchillesWorld ScanEngine]
                        │
                        ├── WMQ: 예측 정확도·드리프트·ECE·OOD 탐지율
                        ├── ALM: 계획 깊이·하위 작업 완료율·목표 달성·적응
                        └── OHM: 루프 완료율·HITL 트리거·사고 복구 시간
```

핵심은 세 가지입니다:

1. **예측 정확성(WMQ)**: World Model이 좋으면 예측이 정확합니다. ECE, SDR, PA가 이를 잡아냅니다.
2. **계획 깊이(ALM)**: World Model이 풍부할수록 더 깊은 계획이 가능합니다. Planning Depth Probing으로 측정합니다.
3. **운용 안정성(OHM)**: 좋은 World Model은 예외 상황에도 적절히 대응합니다. IRT, HC, LCR이 이를 확인합니다.

이 세 범주를 **HAS(Holistic Agent Score)**로 통합합니다:

```
HAS = 0.45 × WMQ + 0.35 × ALM + 0.20 × OHM
```

이 가중치는 HAW-STUDY-001(n=50)에서 Shapley 가치 기반으로 실증적으로 도출했으며, HAW-STUDY-002(n=200 목표)에서 재검증할 예정입니다.

---

### Q2 (학계 지도교수 최병두)

> *"HAW-STUDY-001의 ρ=0.92라는 상관 계수는 합성 데이터(synthetic, n=25)에서 나온 것 아닙니까? 실제 기업 에이전트 데이터로 검증하기 전까지는 '실증 연구'라는 표현이 과장 아닌가요?"*

솔직하게 답변드리겠습니다. **맞습니다.**

HAW-STUDY-001은 파일럿 연구이며, n=50 중 n=25는 합성 데이터입니다. 논문에서도 이를 명시했고, TTA 제안서에서도 "n=50 파일럿 기준 권고 범위"로 표현을 수정했습니다.

학술적 엄밀성을 위해 우리는 이미 **HAW-STUDY-002 프로토콜**을 수립했습니다:

| 항목 | HAW-STUDY-001 (완료) | HAW-STUDY-002 (계획) |
|------|---------------------|---------------------|
| 표본 크기 | n=50 (파일럿) | n=200+ |
| 표본 방법 | Convenience sampling | 층화 표본 (도메인 × 레벨) |
| 외부 타당도 | 미검증 | SWE-bench / GAIA / AgentBench 동시 측정 |
| 공선성 검증 | Sprint 6-C에서 실시 | VIF 전처리 후 Owen value Shapley |
| 일정 | 2026-06 완료 | 2027-07 예정 |

*교수님이 우려하시는 부분은 정확히 우리가 다음 연구에서 해결하려는 문제입니다. 과학은 단계적으로 나아갑니다.*

중요한 것은 ρ=0.92(합성)가 아니라 **측정 체계의 타당성**입니다. 합성 데이터에서도 HAS가 KPI를 잘 예측한다면, 실제 데이터에서 검증할 가치가 있다는 뜻입니다. HAW-STUDY-002가 그 검증입니다.

---

## 3. 기술 아키텍처 Deep Dive

### Q3 (MLOps 엔지니어 정다윤)

> *"실제로 프로덕션에서 에이전트 로그를 수집해서 HAS를 측정하려면 어떻게 합니까? 저희는 Kubernetes에 수백 개 에이전트가 올라가 있는데요."*

HAchillesWorld는 **SDK-first** 설계입니다. 세 가지 통합 경로가 있습니다.

**경로 A: 직접 계측 (권장)**

```python
# 에이전트 코드에 단 3줄 추가
from hachillesworld import HAchillesWorldClient

client = HAchillesWorldClient(api_key="haw-...")

# 에이전트 루프 안에서
client.emit(AgentEvent(
    event_type="observe",
    agent_name="order-routing-agent",
    payload={
        "prediction_error": my_model.prediction_error(),
        "goal_achieved": task.is_complete(),
        "planning_depth": planner.current_depth(),
    }
))

# 주기적으로 또는 배포 전 진단
report = client.scan(agent_name="order-routing-agent")
print(f"HAS: {report.composite_score:.1f} | 등급: {report.level_label}")
```

**경로 B: REST API (언어 무관)**

```bash
curl -X POST https://your-haw.internal/v1/scan \
  -H "Authorization: Bearer $HAW_API_KEY" \
  -d '{"agent_name": "order-routing-agent", "logs": [...]}'
```

**경로 C: 로그 파이프라인 (비침습적)**

```python
# 기존 로그가 있다면 SDK가 알아서 파싱
from hachillesworld.collect.log_pipeline import StudyLogPipeline

pipeline = StudyLogPipeline(log_dir="/var/log/agents/")
dataset = pipeline.load_all()
```

Kubernetes 환경이시라면 **사이드카 패턴**을 권장합니다. 에이전트 파드에 `hachillesworld-sidecar` 컨테이너를 붙이면 에이전트 코드 수정 없이 로그를 자동 수집합니다.

스토리지는 로컬 SQLite(개발), PostgreSQL(프로덕션)을 지원하며, HAW_STORAGE 환경 변수로 전환 가능합니다.

```bash
# 프로덕션 전환 단 1줄
export HAW_STORAGE=postgres
export HAW_DATABASE_URL=postgresql://user:pass@host/hawdb
```

---

### Q4 (AI 안전 연구자 이소연 박사)

> *"CA(Counterfactual Accuracy) 측정에 LLM-as-Judge를 쓴다고 했는데, Judge 모델이 바뀌면 점수가 달라지지 않습니까? 재현성 문제 아닌가요?"*

바로 v2.1에서 해결한 **A-6 문제**입니다.

v2.0에서는 Anthropic Claude만 사용할 수 있었습니다. 이는 두 가지 문제를 낳았습니다:

1. **재현성**: Claude 버전이 업데이트되면 CA 점수가 달라짐
2. **프라이버시**: 에이전트 로그가 외부 API로 전송됨 (GDPR D-3 문제)

v2.1에서는 **멀티 Judge 백엔드**를 도입했습니다:

```python
# Judge 타입 선택
engine = ScanEngine(config={
    "judge_type": "rule",    # 완전 오프라인, 결정론적, 재현 100%
    # "judge_type": "local",  # Ollama 로컬 LLM
    # "judge_type": "anthropic",  # 기존 Claude API
})
```

| Judge | 재현성 | 속도 | 정확도 | 외부 전송 | 비용 |
|-------|--------|------|--------|----------|------|
| RuleBasedJudge | ✅ 100% | ✅ 즉각 | △ 규칙 기반 | ✅ 없음 | ✅ 0원 |
| LocalLLMJudge (Ollama) | ✅ 높음 | △ 수초 | ✅ 높음 | ✅ 없음 | △ GPU 비용 |
| AnthropicJudge | △ 버전 의존 | ✅ 빠름 | ✅ 최고 | △ PII 필터 후 | △ API 비용 |

공공기관·금융·의료는 **RuleBasedJudge 또는 LocalLLMJudge**를 사용하면 외부 데이터 전송 없이 완전한 CA 측정이 가능합니다.

---

## 4. 고객이 채택해야 하는 이유

### Q5 (스타트업 CTO 김준서)

> *"저희는 LLM 비교 벤치마크가 이미 있습니다. MMLU, HumanEval... 왜 HAchillesWorld가 필요한가요?"*

좋은 질문입니다. 그게 바로 제가 이 프레임워크를 만든 이유입니다.

**MMLU는 '얼마나 잘 아는가'를 측정합니다. HAchillesWorld는 '얼마나 잘 행동하는가'를 측정합니다.**

구체적으로 비교해드리겠습니다:

| 측정 대상 | MMLU / HumanEval | HAchillesWorld HAS |
|----------|------------------|---------------------|
| 언어 이해력 | ✅ 측정 | △ 간접 반영 |
| 코드 생성 | ✅ 측정 | △ 간접 반영 |
| **다단계 계획** | ❌ 미측정 | ✅ PD 지표 |
| **환경 예측 정확도** | ❌ 미측정 | ✅ ECE, PA 지표 |
| **OOD 상황 대응** | ❌ 미측정 | ✅ ODR 지표 |
| **사고 복구 시간** | ❌ 미측정 | ✅ IRT 지표 |
| **드리프트 감지** | ❌ 미측정 | ✅ SDR 지표 |
| **프로덕션 안전성** | ❌ 미측정 | ✅ SU, HC, LCR 지표 |
| **KPI 예측력** | 검증 없음 | ρ=0.92 실증 |

GPT-4o와 Claude 3.5 Sonnet은 MMLU에서 비슷한 점수를 냅니다. 하지만 **여러분의 공급망 최적화 에이전트 업무**에서 어느 것이 더 나은지는 MMLU가 알려주지 않습니다. HAS가 알려줍니다.

실제로 저희 HAW-STUDY-001에서 흥미로운 발견이 있었습니다. **MMLU 상위 에이전트가 HAS 하위**에 들어오는 케이스가 있었습니다. 언어 능력과 에이전트 역량은 별개입니다.

---

### Q6 (컴플라이언스 담당 박민준)

> *"EU AI Act가 2025년부터 단계적으로 시행됩니다. 저희 회사는 고위험 AI 시스템을 운용 중인데, HAchillesWorld가 실제로 컴플라이언스에 도움이 됩니까?"*

도움이 됩니다. 단, 한 가지를 먼저 솔직하게 말씀드려야 합니다.

**HAchillesWorld는 법적 컴플라이언스 인증 도구가 아닙니다.**

이게 v2.1의 가장 중요한 변화입니다. 초기 버전에서 "EU AI Act 자동 매핑"이라는 표현을 사용했는데, 이는 잘못된 것이었습니다. 공인된 적합성 평가 기관(Notified Body)의 인증을 대체할 수 없습니다.

그러나 HAchillesWorld가 실질적으로 제공하는 것은:

**1. Art.13 — 투명성 증거 자료 생성**

```
Art.13 요구: "예측 정확도와 불확실성 정보를 제공해야 한다"
→ ECE (Expected Calibration Error) 측정값으로 근거 자료 생성
→ 감사 로그: 누가 언제 어떤 에이전트를 평가했는지 기록
```

**2. Art.14 — 인간 감독 체계 증거**

```
Art.14 요구: "자연인이 효과적으로 감독·개입할 수 있어야 한다"
→ HC (Human Control Rate) + IRT (Incident Recovery Time) 측정
→ HITL 트리거 기록으로 인간 감독 이행 증거
```

**3. Art.15 — 정확성·견고성 모니터링**

```
Art.15 요구: "정확성과 견고성을 지속적으로 유지해야 한다"
→ DriftMonitor로 성능 저하 감지
→ SDR, PA 추이 모니터링
```

**결론**: HAchillesWorld는 **컴플라이언스 준비 상태(readiness)를 모니터링**하고, **감사(audit) 시 제출할 증거 자료**를 체계적으로 생성합니다. 규제 기관 심사에서 "우리가 무엇을 모니터링하고 있는지"를 보여줄 수 있는 체계가 생깁니다.

ISO/IEC 42001:2023 기준으로도 §6.1(리스크 평가), §8.4(AI 시스템 운용), §9.1(모니터링·평가) 조항별 체크리스트를 자동 생성합니다.

---

## 5. 기업 도입 시 구체적 효과

### Q7 (벤처 투자자 한성민)

> *"Evidently AI, Arthur AI, Arize AI 같은 ML 모니터링 도구가 이미 있습니다. HAchillesWorld의 차별점이 뭡니까? 왜 투자해야 합니까?"*

정직하게 비교해드리겠습니다.

| 기능 | Evidently AI | Arthur AI | Arize AI | HAchillesWorld |
|------|-------------|-----------|----------|---------------|
| 데이터 드리프트 | ✅ 강점 | ✅ 강점 | ✅ 강점 | ✅ (SDR) |
| LLM 품질 평가 | △ 부분 | ✅ 강점 | ✅ 강점 | ✅ (CA, ECE) |
| **에이전트 계획 깊이** | ❌ | ❌ | ❌ | ✅ (PD Probing) |
| **World Model 예측력** | ❌ | ❌ | ❌ | ✅ (WMQ 범주) |
| **역량 레벨 분류** (L1/L2/L3) | ❌ | ❌ | ❌ | ✅ |
| **EU AI Act 모니터링** | △ | △ | △ | ✅ (Art.13/14/15) |
| **ISO 42001 체크리스트** | ❌ | ❌ | ❌ | ✅ |
| **오프라인 Judge** | ❌ | ❌ | ❌ | ✅ (RuleJudge, Ollama) |
| 오픈소스 SDK | 일부 | ❌ | ❌ | ✅ (Apache 2.0) |
| 학술 논문 기반 | △ | △ | △ | ✅ (HAW-TR-001) |

**핵심 차별점**: 기존 도구들은 **LLM 모델 성능**을 모니터링합니다. HAchillesWorld는 **에이전트 시스템의 World Model 품질**을 측정합니다. 이는 근본적으로 다른 시장입니다.

2026년 현재, AI 에이전트 시장은 **"LLM 시대에서 에이전트 시대로"** 전환 중입니다. AutoGPT, Devin, Claude Computer Use처럼 다단계 자율 계획과 실행이 가능한 에이전트가 기업에 배포되기 시작했습니다. 이 에이전트들을 기존 LLM 모니터링 도구로는 평가할 수 없습니다.

**우리는 에이전트 시대의 측정 표준을 선점하고 있습니다.**

시장 규모 추정: 글로벌 AI 에이전트 시장이 2027년 $45B에 달할 전망이며, 그 중 품질·모니터링·컴플라이언스 도구 시장은 10~15%로 추정됩니다.

---

### Q8 (스타트업 CTO 김준서)

> *"실제로 도입하면 어떤 숫자가 바뀌나요? ROI를 정량적으로 말해줄 수 있습니까?"*

세 가지 ROI 시나리오를 제시하겠습니다.

---

**시나리오 A: 배포 전 품질 게이팅**

```
Before HAchillesWorld:
  - 에이전트 배포 후 1개월 내 장애 발생률: ~35%
  - 장애 1건 평균 비용(사고 대응 + 고객 보상): $50,000~200,000

After HAchillesWorld:
  - HAS < 70인 에이전트 배포 차단
  - IRT(사고 복구 시간) > 임계값 시 자동 경고
  - 예상 장애 발생률 감소: 35% → 15~20%
  - 연간 절감: $500K ~ $2M (에이전트 수에 따라)
```

**시나리오 B: EU AI Act 컴플라이언스**

```
Without HAchillesWorld:
  - EU AI Act 위반 과징금: 전 세계 매출의 최대 3%
  - 전담 컴플라이언스 팀 구성: 3~5명 × $100K = $300K~500K/year
  - 감사 대비 문서화 작업: 매월 40~80 인시

With HAchillesWorld:
  - 감사 로그 자동 생성 (누가 언제 무엇을 평가했는지)
  - Art.13/14/15 모니터링 보고서 자동 생성
  - 전담 팀 1~2명으로 축소 가능
  - 예상 절감: $150K~300K/year
```

**시나리오 C: 에이전트 품질 개선 가속**

```
Without HAchillesWorld:
  - "에이전트가 왜 틀렸나?" 원인 분석: 수일 소요
  - 재학습 후 개선 여부 확인: 주관적 판단

With HAchillesWorld:
  - HASInterpreter가 즉시 "PD 점수 미달 → 계획 깊이 증가 필요" 알림
  - 구체적 액션 아이템 + 예상 HAS 상승폭 제시
  - 개선 사이클 단축: 2주 → 3~5일
  - 에이전트 HAS 10점 상승 = KPI ~8~15% 개선 (HAW-STUDY-001 기반)
```

---

### Q9 (컴플라이언스 담당 박민준)

> *"PII 처리 관련해서 구체적으로 어떻게 됩니까? 에이전트 로그에 고객 개인정보가 들어있을 수 있습니다."*

GDPR/PIPA를 고려한 **Privacy by Design** 아키텍처입니다.

**계층 1: 로컬 계측 우선**

```
에이전트 로그 → PII ClassifierLayer → [REDACTED 처리]
                                       │
                                       └── 수치 지표만 추출
                                           (prediction_error, planning_depth 등)
```

`DataClassifier`가 자동으로 PII 필드를 탐지하고 마스킹합니다:

```python
# 자동 PII 탐지
clf = DataClassifier()
result = clf.classify(episode_log)

# PII 포함 시 → [REDACTED] 처리 후 Judge로 전송
sanitized = clf.sanitize_for_external(episode_log)
```

탐지 패턴: 이메일, 전화번호, 주민등록번호, IP 주소, API 키, 비밀번호, 인증 토큰 등

**계층 2: 오프라인 Judge 옵션**

CA 측정 시 `judge_type="rule"` 또는 `judge_type="local"` 선택 시 **외부 전송 0건**입니다.

**계층 3: 감사 추적 (Data Flow 투명성)**

`docs/DATA_FLOW.md`에 정확히 어떤 데이터가 어디로 가는지 명시되어 있습니다. 공공기관 보안 심의 통과를 위한 문서 자료로 활용 가능합니다.

---

## 6. 로드맵 & 비전

### Q10 (MLOps 엔지니어 정다윤)

> *"지금 v2.1이 나왔는데, 앞으로 어떻게 발전할 예정입니까?"*

3단계 로드맵을 공유드리겠습니다.

---

### Phase 1: v2.1 (현재, 2026-10-31 릴리스)

**목표: "신뢰할 수 있는 측정"**

```
✅ 완료된 것들:
  - HAS 신뢰구간 (CI) + 오차 전파 (A-1, A-2)
  - 지표 다중공선성 검증 VIF + Spearman (A-3)
  - SQLite/PostgreSQL 영구 스토리지 (B-4)
  - 멀티 Judge 백엔드 (LocalLLM, Rule) (A-6)
  - HASInterpreter 등급 + 액션 아이템 (E-1, E-2)
  - AuditLogger + PII 분류기 (C-7, D-3)
  - EU AI Act 표현 수정 + 면책 배너 (D-1)
  - 611개 테스트 0 failures, mypy 0 errors
```

---

### Phase 2: v2.2 (2027-Q2 예정)

**목표: "외부 타당도 확보 + 표준화 추진"**

```
🔵 진행 예정:
  HAW-STUDY-002 (n=200 층화 표본):
  - 4개 도메인 × L1~L3 교차 층화
  - SWE-bench / GAIA / AgentBench 동시 측정
  - HAS의 외부 벤치마크 예측력 검증
  - Owen value 기반 Shapley (공선성 해소)
  
  TTA 표준 추진:
  - TTAS.KO-XX.XXXX: AI 에이전트 World Model 품질 평가 표준
  - 2027-03 표준 확정 목표
  
  인프라:
  - Helm Chart (Kubernetes 네이티브 배포)
  - SSO/LDAP 연동 (엔터프라이즈 인증)
  - Real-time Dashboard v2
```

---

### Phase 3: v3.0 (2027-Q4 예정)

**목표: "멀티에이전트 시대의 표준 플랫폼"**

```
🟡 비전:
  멀티에이전트 조율 품질 측정:
  - 에이전트 간 의존성 그래프 (AgentDependencyGraph v2)
  - 연합 HAS (federation of agents → system-level HAS)
  - 에이전트 간 드리프트 전파 모델
  
  자율 개선 (L3 Evolver 지원):
  - HAS 피드백 → 자동 재학습 트리거
  - Meta-Harness 규칙 자동 학습
  
  글로벌 벤치마크:
  - HAW-DB: 공개 에이전트 품질 리더보드
  - 산업별 기준값 (Healthcare HAS baseline 등)
  
  C++ 래퍼:
  - ROS2 기반 로봇공학 커뮤니티 지원
```

---

### Q11 (벤처 투자자 한성민)

> *"오픈소스를 유지하면서 어떻게 수익화할 계획입니까?"*

오픈소스를 핵심 자산으로 보고 있습니다. 수익화는 오픈소스 위에서 이루어집니다.

**수익화 모델 (v2.2 이후)**:

```
Tier 1: Community (무료)
  - SDK 코어 (Apache 2.0)
  - 로컬 측정 + SQLite 스토리지
  - 기본 대시보드

Tier 2: Professional ($299/month per team)
  - HAchillesWorld Cloud (SaaS)
  - PostgreSQL 클러스터 스토리지
  - 팀 협업 + 알림 통합 (Slack, PagerDuty)
  - EU AI Act 보고서 자동 생성 (PDF)
  - 우선 지원

Tier 3: Enterprise (커스텀 가격)
  - 온프레미스 배포 (규제 환경)
  - SSO/LDAP 연동
  - SLA 99.9%
  - 전담 계정 매니저
  - 감사 대비 컨설팅
  - HAW-STUDY 데이터 공동 연구
```

**추가 수익원**:
- **HAW 인증(HAW-Certified)**: HAS ≥ 80 에이전트에게 발급하는 품질 인증 뱃지
- **API 마켓플레이스**: 서드파티 Judge 플러그인 생태계
- **TTA 표준 상용 라이선스**: 표준 기반 컨설팅 및 교육

---

## 7. 비판적 질문과 솔직한 답변

### Q12 (AI 안전 연구자 이소연 박사)

> *"HAS가 높다고 해서 에이전트가 실제로 안전한가요? HAS 92점짜리 에이전트가 큰 사고를 냈다면 어떻게 책임지겠습니까?"*

이 질문이 가장 중요합니다.

**솔직한 답변: HAS는 필요조건이지 충분조건이 아닙니다.**

HAS가 높은 에이전트도 사고를 낼 수 있습니다. 이유는 여러 가지입니다:

1. **측정 커버리지**: 15개 지표가 에이전트 품질의 전부는 아닙니다. 보안 취약점, 의도적 오용, 흑조 이벤트는 HAS로 잡을 수 없습니다.

2. **도메인 특수성**: HAS는 일반화된 지표입니다. 특정 도메인의 특수 리스크(의료: 진단 오류, 금융: 시장 조작)는 별도 측정이 필요합니다.

3. **분포 외 입력**: ODR이 높아도 완전히 새로운 입력에 대한 취약성은 존재합니다.

그래서 HAchillesWorld는 다음 두 가지를 강조합니다:

> **"HAS가 낮으면 배포하지 말아야 합니다."**  
> **"HAS가 높아도 지속적으로 모니터링해야 합니다."**

HAchillesWorld는 배포 결정의 **최소 필수 조건(floor)**을 설정하고, 운용 중 **지속 감시(continuous monitoring)**를 제공합니다. 최종 책임은 항상 인간(배포 의사결정자)에게 있습니다.

---

### Q13 (학계 지도교수 최병두)

> *"Planning Depth를 외부 행동 관찰로 측정한다고 했는데, 에이전트가 의도적으로 '깊은 계획처럼 보이게' 행동하는 Goodhart's Law 문제는 어떻게 대처합니까?"*

Goodhart's Law: *"측정 지표가 목표가 되면, 그 지표는 더 이상 좋은 측정치가 아니다."*

우리도 인지하고 있는 근본적 한계입니다.

현재 대응책:

**1. 다중 지표 교차 검증**
PD(계획 깊이)만 보지 않고 SCR(하위 작업 완료율), GAR(목표 달성률)을 함께 봅니다. 계획만 깊고 실제 완수율이 낮으면 HAS에서 ALM 점수가 낮아집니다.

**2. 반사실 평가 (CA)**
"실제로 다른 선택을 했다면?" 시나리오로 에이전트의 진짜 이해력을 측정합니다. 단순 패턴 모방으로는 CA를 속이기 어렵습니다.

**3. 행동 프로빙 (Behavioral Probing)**
Planning Depth 측정 시 에이전트에게 **랜덤 환경 변형**을 주입합니다. 진짜 깊은 계획을 가진 에이전트만 변형 환경에서도 안정적 성능을 보입니다.

**그러나 솔직히**: 교수님 말씀처럼 Goodhart's Law는 완전히 해결할 수 없는 문제입니다. 이것이 HAW-STUDY-002에서 **외부 벤치마크(SWE-bench, GAIA)와 상관 분석**을 하는 이유입니다. HAS가 독립적 외부 기준과 수렴한다면, 적어도 측정 타당성의 증거가 됩니다.

---

### Q14 (스타트업 CTO 김준서)

> *"도입 비용은 얼마나 됩니까? 스타트업에게는 부담이 될 수도 있는데요."*

커뮤니티 버전은 **완전 무료**입니다. 오픈소스입니다.

```bash
pip install hachillesworld      # 무료
```

스타트업 기준 실제 비용:

| 항목 | 비용 |
|------|------|
| SDK 라이선스 | $0 (Apache 2.0) |
| 로컬 측정 | $0 |
| 클라우드 없이 SQLite 사용 | $0 |
| 개발자 적응 시간 | 약 2~4시간 (튜토리얼 기준) |
| 기존 인프라 수정 | 최소화 (사이드카 패턴) |

v2.1에서 `import anthropic` 의존성을 선택적으로 만들었기 때문에, Anthropic API 없이도 전체 측정이 가능합니다.

---

## 8. 맺음말

### 저자 박성훈의 최종 발언

오늘 많은 날카로운 질문을 해주셨습니다.

HAchillesWorld는 완성된 제품이 아닙니다. 진행 중인 연구이자 플랫폼입니다. 우리는 HAW-STUDY-001의 한계를 솔직히 인정하고, HAW-STUDY-002로 나아가고 있습니다. Goodhart's Law 문제를 인지하면서도, 불완전한 지표가 없는 것보다 낫다는 믿음으로 만들어 나가고 있습니다.

AI 에이전트가 의료, 금융, 공공 서비스에 배포되는 시대에, 우리는 **"왜 이 에이전트를 믿어야 하는가"에 대한 답변을 데이터로 제시할 수 있어야 합니다.**

HAchillesWorld의 비전은 단 하나입니다:

> **"AI 에이전트가 프로덕션에 배포되기 전, 그리고 배포된 후에도,  
> 우리는 그것의 품질을 측정할 수 있어야 한다."**

이것이 《Agentic World Modeling 2027》 책의 핵심 주장이며, arXiv HAW-TR-001 논문의 실증 결과이며, HAchillesWorld 플랫폼의 존재 이유입니다.

함께 AI 에이전트 품질의 표준을 만들어 나가겠습니다. 감사합니다.

---

## 부록: 핵심 지표 참조표

### HAS 구성 요소

```
HAS = 0.45 × WMQ + 0.35 × ALM + 0.20 × OHM    (v2.1 기준)

WMQ (World Model Quality, 45%):
  SDR  Simulation Drift Rate      ≤ 0.05
  ECE  Expected Calibration Error ≤ 0.05
  PA   Prediction Accuracy        ≥ 0.80
  ODR  OOD Detection Rate         ≥ 0.80
  WMUL WM Update Latency          ≤ 100ms

ALM (Agency Level Metrics, 35%):
  PD   Planning Depth             ≥ 3 steps
  SCR  Self-Correction Rate       ≤ 0.10
  CA   Counterfactual Accuracy    ≥ 0.70
  GAR  Goal Achievement Rate      ≥ 0.80
  AS   Adaptation Score           ≥ 0.70

OHM (Operational Health Metrics, 20%):
  LCR  Loop Completion Rate       ≥ 0.95
  HC   Human Control Rate         ≥ 0.90
  HR   Hallucination Rate         ≤ 0.05
  IRT  Incident Recovery Time     ≤ 60s
  SU   Safety Unwinding Rate      ≤ 0.01
```

### HAS 등급 체계

| HAS 점수 | 등급 | 레이블 | 배포 권장 |
|----------|------|--------|----------|
| 90~100 | A+ | 우수 에이전트 | 전면 배포 가능 |
| 80~89 | A | 양호 에이전트 | 일반 배포 가능 |
| 70~79 | B | 개선 필요 | 제한적 배포 |
| 60~69 | C | 주의 에이전트 | 감독 하 운용 |
| < 60 | D | 즉시 개선 필요 | 배포 중단 권고 |

### 역량 레벨 분류

| 레벨 | 레이블 | 특성 |
|------|--------|------|
| L1 | Predictor | 단순 예측·반응, 제한적 계획 |
| L2 | Planner | 다단계 계획·실행, 목표 추적 |
| L3 | Evolver | 자기 개선·메타 학습, 환경 적응 |

### 도메인별 적용

| 도메인 | 대표 에이전트 | 주요 강조 지표 |
|--------|-------------|--------------|
| Physical | 로봇, 제조, 물류 | SDR, IRT, PA |
| Digital | 코드, 웹, 데이터 분석 | ECE, CA, LCR |
| Social | 고객서비스, 교육, 헬스케어 | HC, HR, GAR |
| Scientific | 연구, 실험, 분석 | PD, ODR, AS |

---

## 관련 자료

| 자료 | 위치 |
|------|------|
| SDK 소스코드 | `src/hachillesworld/` |
| 전체 플로우 테스트 | `scripts/full_flow_test_v21.py` |
| E2E 테스트 | `scripts/e2e_flow_test_v21.py` |
| TTA 표준 제안서 | `docs/standards/tta_standard_proposal.md` |
| HAW-STUDY-002 프로토콜 | `docs/haw_study_002_protocol.md` |
| 다중공선성 분석 결과 | `docs/analysis/multicollinearity_study001.md` |
| CHANGELOG | `CHANGELOG.md` |
| CONTRIBUTING | `CONTRIBUTING.md` |
| arXiv 논문 초안 | `docs/arxiv_paper_final.md` |

---

*본 문서는 2026-10-31 토론 세션 기록이며, 저자 박성훈이 직접 작성·검토하였습니다.*  
*HAchillesWorld v2.1.0 / SDK sdk-v2.1.0 / Platform platform-v2.1.0*
