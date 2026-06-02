# MCTS Planning Depth 완전 해설

> **대상 시스템**: HAchillesWorld `supply-chain-agent`  
> **프레임워크**: Levels × Laws — L2 Simulator → L3 Evolver 전환  
> **기준**: 《Agentic World Modeling 2027》 — 박성훈

---

## 1. Planning Depth란 무엇인가

Planning Depth는 **에이전트가 현재 시점에서 몇 단계 앞의 미래를 시뮬레이션할 수 있는가**를 나타낸다.

각 "Depth 1"은 에이전트의 DEOR 루프 한 사이클을 의미한다.

```
DEOR 1사이클 = Decide → Execute → Observe → Reflect
```

Depth N이라면 에이전트는 **현재 상태에서 N번의 의사결정이 연쇄될 때 어떤 결과가 나오는지** 미리 머릿속으로 펼쳐보고(rollout) 지금의 행동을 결정한다.

### MCTS가 Planning Depth를 늘리는 방법

```
현재 상태(root)
    ├── 행동 A
    │    ├── 결과 A1 → 행동 A1a → 결과 A1a1 → ... (Depth N까지)
    │    └── 결과 A2 → ...
    ├── 행동 B
    │    └── ...
    └── 행동 C
         └── ...
```

MCTS는 이 트리를 **n_simulations회(50→200회)** 반복 탐색해 각 행동의 장기 가치를 추정한다. Depth가 깊을수록 더 먼 미래의 결과가 반영된다.

---

## 2. Depth별 상세 설명

### Depth 1 — 반사적 반응 (Reflexive)

**"지금 가장 좋아 보이는 것을 한다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 현재 상태 → 다음 상태 1단계 |
| 의사결정 방식 | 탐욕적(greedy): 현재 보상만 최대화 |
| 공급망 예시 | "지금 재고가 부족하니까 즉시 발주한다" |
| 한계 | 발주 후 3일 뒤 대규모 수요 감소가 예정돼 있어도 모른다 |
| HAchillesWorld 판정 | L1 Predictor 하한 |

```python
# Depth 1: 현재 상태만 보고 greedy 선택
action = max(possible_actions, key=lambda a: immediate_reward(state, a))
```

---

### Depth 2–3 — 단기 예측 (Short-term Lookahead)

**"내 행동이 바로 다음에 어떤 영향을 주는지 본다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 2~3단계 앞 |
| 의사결정 방식 | 1~2회의 결과를 미리 계산하고 선택 |
| 공급망 예시 | "발주하면 → 3일 후 입고 → 재고 충족" 까지 본다 |
| 한계 | 입고 후 시장 가격이 급락하거나, 경쟁사 재고가 풀리는 상황은 보지 못한다 |
| HAchillesWorld 판정 | **진단 시작점 (Depth 3)** |

```python
# Depth 3: 3스텝 lookahead MCTS (초기 진단값)
planner = MCTSPlanner(max_depth=3, n_simulations=10)
# 공급망에서 약 3일치 의사결정 시뮬레이션
```

> **왜 3이 문제인가**: 공급망 발주 리드타임이 평균 7일이므로, 3스텝은 발주의 **결과가 실현되기 전에 계획이 끝난다**. 결과를 보지 못하고 결정하는 구조.

---

### Depth 4–5 — 결과 확인 가능 (Outcome-Aware)

**"내 행동의 1차 결과를 보고 나서 다음 행동을 계획한다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 4~5단계 앞 |
| 의사결정 방식 | 행동 → 1차 결과 → 2차 행동까지 계획 |
| 공급망 예시 | 발주 → 입고 → 재고 상태 확인 → 추가 발주 여부 판단 |
| 한계 | 주간 단위의 수요 변동이나 공급사 리드타임 변화는 아직 밖에 있다 |
| HAchillesWorld 판정 | Phase 2 초기 MCTS 파라미터 (`max_depth=5`) |

```python
planner = MCTSPlanner(
    max_depth=5,
    n_simulations=50,     # Phase 2 시작값
    rollout_policy="random"
)
```

---

### Depth 6–8 — 1차 연쇄 효과 (First-Order Cascade)

**"내 결정이 다음 결정에 어떻게 영향을 미치는지 본다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 6~8단계 앞 |
| 의사결정 방식 | 행동의 파급 효과(cascade)를 최초로 감지 |
| 공급망 예시 | 발주 → 입고 → 재고 → 가격 변동 → 다음 발주 규모 조정까지 연결 |
| 의미 | 공급망에서 약 1주~10일치 시뮬레이션 |
| HAchillesWorld 판정 | Phase 2 중반 달성 목표 |

> **핵심 전환점**: 이 구간부터 에이전트가 "내가 지금 대형 발주를 하면 공급사 납기가 늦어지고, 그 다음 발주도 영향을 받는다"는 연쇄를 인식하기 시작한다.

---

### Depth 9–11 — 조달 사이클 완성 (Full Procurement Cycle)

**"하나의 발주 사이클 전체를 내다본다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 9~11단계 앞 |
| 의사결정 방식 | 발주 → 생산 → 운송 → 입고 → 판매 → 재고 전 사이클 포함 |
| 공급망 예시 | 해외 조달의 경우 리드타임 10일을 전부 시뮬레이션 안에 포함 |
| 의미 | "이번 발주를 취소하면 다음 달 재고 부족이 발생하는가?"를 계산 가능 |
| HAchillesWorld 판정 | Phase 2 완료 기준 접근 구간 |

```python
# Depth 10: 조달 사이클 전체 시뮬레이션
# 해외 공급사 리드타임 10일 = Depth 10
planner = MCTSPlanner(
    max_depth=10,
    n_simulations=100,
)
```

---

### Depth 12–14 — 계절성·외부 요인 감지 (Seasonality-Aware)

**"시장 주기와 외부 충격을 계획에 포함한다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 12~14단계 앞 |
| 의사결정 방식 | 수요 계절성, 공급사 납기 패턴, 경쟁사 재고 변화를 World Model에 반영해 계획 |
| 공급망 예시 | "지금 발주하면 연말 성수기 전 입고가 가능한가?" |
| 의미 | 2주 이상의 공급망 시뮬레이션 — 외부 충격에 대한 사전 완충 가능 |
| HAchillesWorld 판정 | Phase 2 Week 14 달성 수준 |

> **Counterfactual 추론과 결합**: 이 구간부터 "대안 시나리오"와 "실제 선택"의 비교가 의미 있어진다. "14스텝 후 대형 발주 vs 분할 발주의 수익 차이"를 정량 비교할 수 있다.

---

### Depth 15 — Phase 2 목표 (L2 Simulator 완성)

**"중기 전략 수준의 계획이 가능해진다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 15단계 앞 (약 2~3주 공급망 사이클) |
| 의사결정 방식 | UCB1 탐색 + 50회 롤아웃으로 장기 최적 행동 선택 |
| 공급망 예시 | 원자재 가격 상승 예고 → 지금 대량 비축 vs 3주 후 소량 구매의 비용 비교 |
| MCTS 파라미터 | `max_depth=15, n_simulations=50, rollout_policy="random"` |
| HAchillesWorld 판정 | **Phase 2 완료 기준 (달성: 16스텝)** |

```python
# Phase 2 목표 달성 시점 파라미터
planner = MCTSPlanner(
    max_depth=15,
    n_simulations=50,
    exploration_c=1.414,    # UCB1 √2
    rollout_policy="random",
    discount_factor=0.95,
)

# 실제 달성: 16스텝 (목표 초과)
# 공급망 해석: 약 16일치 의사결정 시뮬레이션
# latency: 평균 91ms (실시간 운영 허용 범위)
```

---

### Depth 16–19 — L2→L3 전환 구간 (Transition Zone)

**"시스템 수준의 최적화가 시작된다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 16~19단계 앞 |
| 의사결정 방식 | Neural Rollout Policy로 random 롤아웃 대체 → 더 정밀한 장기 예측 |
| 공급망 예시 | 공급망 전체 네트워크 최적화: 창고 배치, 공급사 다변화, 계약 구조 |
| 의미 | 단일 에이전트를 넘어 공급망 생태계 전체를 시뮬레이션 |
| HAchillesWorld 판정 | Phase 3 초반 달성 (Neural Rollout 적용 후) |

```python
# Phase 3: neural rollout으로 업그레이드
planner = MCTSPlanner(
    max_depth=18,
    n_simulations=150,
    rollout_policy=NeuralRolloutPolicy(model=world_model),
    exploration_c=1.2,      # 활용 비중 증가
)
```

---

### Depth 20+ — L3 Evolver (자율 전략 계획)

**"환경이 바뀌어도 스스로 재계획한다"**

| 항목 | 내용 |
|------|------|
| 시뮬레이션 범위 | 20단계 이상 (약 1개월 이상 공급망 시뮬레이션) |
| 의사결정 방식 | Neural Rollout + 200회 시뮬레이션 + 온라인 학습으로 World Model 실시간 업데이트 |
| 공급망 예시 | 글로벌 공급망 충격(지정학적 리스크, 원자재 수급) → 자율 대응 전략 수립 |
| 핵심 능력 | Meta-Harness가 새 환경 규칙을 스스로 학습 → 계획 모델 자동 보정 |
| HAchillesWorld 판정 | **Phase 3 완료 · L3 인증 달성 (달성: 22스텝)** |

```python
# Phase 3 최종 파라미터 (L3 인증 달성 시점)
planner = MCTSPlanner(
    max_depth=22,                                          # 목표 20+ 초과
    n_simulations=200,                                     # Phase 2 대비 4배
    rollout_policy=NeuralRolloutPolicy(model=world_model), # 학습된 정책
    exploration_c=1.2,
    discount_factor=0.95,
)

# 온라인 학습과 연동: 환경 변화 → World Model 업데이트 → 계획 자동 재조정
# 평균 재조정 시간: 18h 이내 (L3 인증 기준 24h 이내)
```

---

## 3. Depth별 비교 요약표

| Depth | 명칭 | 공급망 해석 | MCTS 파라미터 | HAchillesWorld |
|-------|------|------------|--------------|----------------|
| 1 | 반사적 반응 | 즉각 대응만 가능 | 없음 (greedy) | L1 하한 |
| 2–3 | 단기 예측 | 발주 후 입고까지 | depth=3, sims=10 | **진단 시작점** |
| 4–5 | 결과 확인 | 발주 결과 1회 확인 | depth=5, sims=50 | Phase 2 초기 |
| 6–8 | 1차 연쇄 | 1주~10일 시뮬레이션 | depth=8, sims=80 | Phase 2 중반 |
| 9–11 | 조달 사이클 | 해외 리드타임 전체 포함 | depth=10, sims=100 | Phase 2 완료 접근 |
| 12–14 | 계절성 감지 | 2주 이상, 외부 충격 포함 | depth=14, sims=50 | Phase 2 Week 14 |
| **15** | **L2 완성** | **중기 전략 가능** | **depth=15, sims=50** | **Phase 2 목표** |
| 16–19 | L2→L3 전환 | 공급망 네트워크 최적화 | depth=18, sims=150 | Phase 3 초반 |
| **20+** | **L3 Evolver** | **자율 전략·자동 재계획** | **depth=22, sims=200** | **L3 인증 달성** |

---

## 4. Depth가 깊어질수록 달라지는 것

```
Depth 3   │ 발주 → 입고
          │ 3일치 미래
          │ "지금 재고 부족이니 발주"

Depth 8   │ 발주 → 입고 → 재고 변화 → 수요 반응 → 가격 변동 → 추가 발주
          │ 10일치 미래
          │ "발주하면 공급사 납기가 밀려서 다음 발주가 늦어진다"

Depth 15  │ 전체 조달-생산-판매 사이클 + 계절성
          │ 3주치 미래
          │ "성수기 전에 지금 대량 비축하는 게 3주 후 분할 구매보다 18% 유리하다"

Depth 22  │ 글로벌 공급망 시나리오 + 환경 변화 자동 감지
          │ 1개월+ 미래
          │ "원자재 수급 충격이 예상되니 공급사 다변화 계약을 지금 실행한다"
          │ → 환경이 바뀌면 World Model 자동 업데이트 후 재계획
```

---

## 5. 왜 Depth 3이 문제였는가 (진단 시점 분석)

진단 시점(Depth 3)에서 발생한 실제 실패 패턴:

```
[EP-2847 사례]
Depth 3 계획:
  S1. 재고 120 < 재주문점 150 → 발주 결정
  S2. 발주량 100개, 예상 비용 ₩4.82M
  S3. 입고 예정 3일 후
  ↑ 여기서 계획 종료 (Depth 3 한계)

실제로 일어난 일 (Depth 4~6):
  S4. [계획 밖] 시장 가격 +29.6% 급등 → 실제 비용 ₩6.25M
  S5. [계획 밖] 예산 초과 ₩1.43M 발생
  S6. [계획 밖] 다음 분기 재발주 예산 부족
```

**Depth 15 계획이었다면**:  
S4~S6의 시장 가격 급등 시나리오가 Counterfactual 시뮬레이션에 포함됐을 것이고,  
비용 예측 편차 게이트(Harness 규칙 15)가 이미 World Model에 반영돼 있었을 것이다.

---

## 6. MCTS Depth 업그레이드 전체 로드맵

```
진단 (Depth 3)
    │
    ├── Phase 2 초기 (Depth 5) ─── UCB1 탐색 도입
    │                              random rollout 50회
    │
    ├── Phase 2 중반 (Depth 10) ── 조달 사이클 완성
    │                              rollout 100회
    │
    ├── Phase 2 완료 (Depth 16) ── 목표(15) 초과 달성
    │                              Counterfactual 73%
    │
    ├── Phase 3 초반 (Depth 18) ── Neural Rollout 도입
    │                              rollout 150회
    │
    └── Phase 3 완료 (Depth 22) ── L3 인증
                                   Neural Rollout 200회
                                   온라인 학습 연동
                                   자동 재보정 평균 3.2분
```

---

## 7. 핵심 인사이트

> **Planning Depth는 단순한 숫자가 아니다.**  
> 에이전트가 **얼마나 멀리 보고 책임을 질 수 있는가**의 척도다.

- Depth 3: 에이전트는 자신의 행동이 3일 후에 끝난다고 생각한다.  
- Depth 15: 에이전트는 자신의 행동이 3주 뒤 공급망 전체에 어떤 파문을 만드는지 안다.  
- Depth 22: 에이전트는 환경이 바뀌어도 새 규칙을 학습해 다시 20스텝을 내다본다.

**L3 Evolver의 본질**: 더 깊이 보는 것만이 아니라, *깊이 볼 수 있는 World Model을 스스로 갱신하는 것*.

---

*이론적 기반: 《Agentic World Modeling 2027》 — 박성훈*  
*HAchillesWorld v1.0 · Levels × Laws 프레임워크*
