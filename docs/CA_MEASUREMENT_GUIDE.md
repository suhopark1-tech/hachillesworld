# CA 측정 가이드 — Counterfactual Accuracy Judge 선택 기준

**Sprint 5-D** | HAchillesWorld SDK v2.1

---

## 개요

Counterfactual Accuracy(CA)는 에이전트가 반사실("만약 다른 행동을 했다면?") 상황을
얼마나 정확히 예측하는지를 측정하는 지표다(HAW-TR-001 §4.2).

v2.1부터 CA 측정에 세 가지 Judge 백엔드를 지원한다.
각 Judge는 **재현성**, **비용**, **정확도** 측면에서 다른 트레이드오프를 갖는다.

---

## Judge 비교

| Judge | 재현성 | 비용 | 정확도 | GDPR 안전 | 추천 용도 |
|-------|--------|------|--------|-----------|---------|
| `AnthropicJudge` | ❌ 비결정적 | 유료 (API) | 높음 | ⚠️ 외부 전송 | 프로덕션 모니터링 |
| `LocalLLMJudge` | ✅ 결정론적 | 무료 (Ollama) | 중간 | ✅ 로컬 전용 | 논문 재현, 연구 |
| `RuleBasedJudge` | ✅ 결정론적 | 무료 | 낮음 | ✅ 완전 오프라인 | CI/CD, 오프라인 |

---

## 각 Judge 상세

### 1. AnthropicJudge (기본)

Anthropic API (`claude-sonnet-4-6`)를 사용하는 LLM judge.

**특징**:
- 가장 높은 정확도 — 복잡한 시나리오에서도 우수한 평가
- `is_deterministic = False` — 동일 입력에도 결과가 달라질 수 있음
- 에피소드 데이터가 Anthropic 서버로 전송됨 (PII 자동 필터링 적용)

**사용 시 주의**:
- 논문 재현에 부적합 (비결정성)
- 규제 민감 환경에서는 데이터 전송 전 확인 필요

```python
from hachillesworld.scan.judge import AnthropicJudge
from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

evaluator = CounterfactualEvaluator(
    anthropic_client=client,       # Anthropic SDK 클라이언트
    consent_acknowledged=True,     # 전송 동의 확인 후 경고 제거
)
```

---

### 2. LocalLLMJudge (Ollama)

로컬 Ollama 서버를 통해 오픈소스 LLM으로 평가한다.

**특징**:
- `is_deterministic = True` — `seed=42, temperature=0`으로 결정론적
- 외부 네트워크 전송 없음 — GDPR 규제 환경에 적합
- 비용 무료 (로컬 GPU/CPU 사용)

**사전 조건**:
```bash
# Ollama 설치 및 모델 다운로드
ollama pull llama3.1:8b
ollama serve   # localhost:11434 기본 포트
```

```python
evaluator = CounterfactualEvaluator(
    judge_type="local",
    model="llama3.1:8b",          # 기본값, 변경 가능
    host="http://localhost:11434", # 기본값
)
```

---

### 3. RuleBasedJudge (완전 오프라인)

외부 의존성 없는 규칙·휴리스틱 기반 judge.

**특징**:
- `is_deterministic = True` — 순수 Python, 완전 결정론적
- 네트워크 호출 없음 — 에어갭 환경에서도 동작
- 정확도는 낮지만 CI/CD에서 빠른 스모크 테스트에 적합

**평가 로직**:
1. **구조적 유사성** (40%): 예측과 실제 결과의 공통 토큰 비율
2. **목표 달성 키워드** (40%): success, correct, optimal 등 탐지
3. **반사실 일관성** (20%): if, would, 만약, 했다면 등 조건절 포함 여부

```python
evaluator = CounterfactualEvaluator(judge_type="rule")
```

---

## 선택 가이드

```
연구·논문 재현이 목적인가?
  ├─ YES → LocalLLMJudge (결정론적 + 무료)
  └─ NO
       ├─ CI/CD 또는 오프라인 환경인가?
       │    └─ YES → RuleBasedJudge (의존성 없음)
       └─ 프로덕션 모니터링인가?
              └─ YES → AnthropicJudge (최고 정확도)
```

---

## 직접 주입 방식

커스텀 Judge 구현체를 직접 주입할 수 있다.

```python
from hachillesworld.scan.judge.base import JudgeBackend

class MyCustomJudge:
    is_deterministic = True

    def evaluate(self, scenario: str, response_a: str, response_b: str) -> float:
        # 커스텀 평가 로직
        return 0.7

evaluator = CounterfactualEvaluator(judge=MyCustomJudge())
```

---

## 관련 문서

- `docs/DATA_FLOW.md` — 각 Judge 데이터 전송 범위
- `src/hachillesworld/scan/judge/` — Judge 구현체 소스
- `tests/test_judge_backends.py` — 단위 테스트
- HAW-TR-001 §4.2 — CA 지표 정의
