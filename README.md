# HAchillesWorld

[![CI](https://img.shields.io/github/actions/workflow/status/suhopark1-tech/hachillesworld/ci.yml?branch=main&style=flat-square&label=CI&logo=githubactions&logoColor=white&cacheSeconds=60)](https://github.com/suhopark1-tech/hachillesworld/actions/workflows/ci.yml)
[![Security](https://img.shields.io/github/actions/workflow/status/suhopark1-tech/hachillesworld/ci.yml?branch=main&style=flat-square&label=security%20scan&logo=shieldsdotio&logoColor=white&cacheSeconds=60)](https://github.com/suhopark1-tech/hachillesworld/actions/workflows/ci.yml)
[![Pages](https://img.shields.io/github/actions/workflow/status/suhopark1-tech/hachillesworld/pages.yml?branch=main&style=flat-square&label=Pages&logo=githubpages&logoColor=white&cacheSeconds=60)](https://github.com/suhopark1-tech/hachillesworld/actions/workflows/pages.yml)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen?style=flat-square&logo=pytest&logoColor=white)](https://github.com/suhopark1-tech/hachillesworld/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-2.1.0-blue?style=flat-square)](https://github.com/suhopark1-tech/hachillesworld/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](./LICENSE)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20Sonnet%204.6-D97706?style=flat-square&logo=anthropic&logoColor=white)](https://www.anthropic.com)

> **AI 에이전트의 "World Model 품질"을 측정하는 첫 번째 표준화 SDK**

---

## 이런 문제가 있으신가요?

- 에이전트가 왜 실패하는지 모르겠다
- 에이전트를 배포해도 되는지 판단 기준이 없다
- AI 에이전트 성능을 팀원·투자자에게 설명하기 어렵다
- 논문 재현을 해야 하는데 LLM-as-Judge가 비결정적이다

---

## HAchillesWorld가 해결합니다

```bash
pip install hachillesworld
```

```python
from hachillesworld import HAchillesWorldClient

client = HAchillesWorldClient()
report = client.scan(agent_logs=my_logs, agent_name="MyAgent")

print(report.summary())
```

출력 예시:
```
🟡 [MyAgent] L2.3 × Digital Laws
   종합 점수: 73/100 (B등급 — 개선 필요, 상위 50%) | 감독 하 운용
   즉시 조치: Simulation Drift Rate=0.18 (임계 초과) → DriftCausalClassifier 실행 → 원인별 RecalibrationExecutor 적용
```

다음 조치가 궁금하다면:

```python
from hachillesworld.interpret import HASInterpreter

interp = HASInterpreter().interpret(report)

for action in interp.next_actions:
    print(f"[우선순위 {action.priority}] {action.metric}: {action.action}")
    print(f"  → 예상 HAS 상승: +{action.estimated_has_gain}점")
```

---

## 왜 HAchillesWorld인가?

| 기능 | HAchillesWorld | Evidently AI | Arthur AI | Arize AI |
|------|:-:|:-:|:-:|:-:|
| World Model 품질 진단 | ✅ | ❌ | ❌ | ❌ |
| Levels × Laws 역량 분류 | ✅ | ❌ | ❌ | ❌ |
| 즉시 실행 가능한 액션 아이템 | ✅ | ❌ | △ | △ |
| 오프라인 CA 측정 (GDPR 안전) | ✅ | ❌ | ❌ | ❌ |
| 논문 재현 가능한 Judge | ✅ | ❌ | ❌ | ❌ |
| HAS 신뢰구간 (95% CI) | ✅ | △ | ❌ | ❌ |
| MLflow 연동 | ✅ | ✅ | ✅ | ✅ |

---

## 아키텍처

```
에이전트 로그 / EpisodeRecord
        │
        ▼
   ScanEngine
        │ 15개 지표 자동 측정
        ├── World Model 품질 (WMQ, 45%)
        │   Prediction Error Rate · Calibration ECE · Simulation Drift Rate
        │   OOD Detection Rate · Planning Depth
        ├── 에이전시 수준 (ALM, 35%)
        │   Self-Correction Rate · Counterfactual Accuracy · Goal Consistency
        │   Env Adaptation Speed · Harness Coverage
        └── 운영 건전성 (OHM, 20%)
            WM Update Latency · Incident Recovery Time · HITL Trigger Rate
            Harness Violation Attempts · Checkpoint Recovery Rate
        │
        ▼
 DiagnosticReport
  ├── composite_score  (HAS 0~100)
  ├── has_confidence_interval  (95% CI)
  ├── summary()        ← 1줄 CLI 출력
        │
        ▼
  HASInterpreter
  ├── grade            A+ / A / B / C / D
  ├── deployment_status
  ├── percentile       상위 몇% (Study-001 기반)
  └── next_actions     즉시 실행 가능한 액션 아이템 Top 3
```

---

## 핵심 기능

### 1. Scan — 15개 지표 자동 진단

```python
from hachillesworld.scan.engine import ScanEngine

engine = ScanEngine(config={"laws_domain": "digital"})
report = engine.run(logs=agent_logs, agent_name="MyAgent")

print(f"HAS: {report.composite_score:.1f}/100")
print(f"95% CI: {report.has_confidence_interval}")
```

### 2. Interpret — 즉시 실행 가능한 액션 아이템

```python
from hachillesworld.interpret import HASInterpreter

interp = HASInterpreter().interpret(report)

print(f"등급: {interp.grade} ({interp.grade_label})")
print(f"배포 상태: {interp.deployment_status}")
print(f"예상 개선폭: +{interp.estimated_improvement:.1f}점")

for action in interp.next_actions:
    print(f"  [{action.priority}순위] {action.metric} → {action.action}")
```

### 3. 오프라인 CA 측정 — GDPR 안전

```python
from hachillesworld.scan.counterfactual_evaluator import CounterfactualEvaluator

# 완전 오프라인 (외부 전송 없음)
evaluator = CounterfactualEvaluator(judge_type="rule")

# 로컬 LLM (Ollama, 재현 가능)
evaluator = CounterfactualEvaluator(judge_type="local", model="llama3.1:8b")

# Anthropic API (고정확도, 외부 전송)
evaluator = CounterfactualEvaluator(anthropic_client=client, consent_acknowledged=True)
```

### 4. MLflow 연동

```python
from hachillesworld.integrations import MLflowHASLogger

MLflowHASLogger().log_report(report)
# → MLflow에 has_score, wmq_score, alm_score, ohm_score + 15개 지표 자동 기록
```

### 5. REST API

```bash
# 서버 시작
uvicorn hachillesworld.api.server:app --reload

# 진단
curl -X POST http://localhost:8000/v1/scan \
  -H "Authorization: Bearer dev-key-insecure" \
  -d '{"agent_name": "MyAgent", "logs": [...], "config": {}}'

# HAS 해석
curl -X POST http://localhost:8000/v1/agents/MyAgent/interpret \
  -H "Authorization: Bearer dev-key-insecure" -d '{}'

# 다음 액션 목록
curl http://localhost:8000/v1/agents/MyAgent/next-actions \
  -H "Authorization: Bearer dev-key-insecure"
```

---

## 설치

```bash
# 기본 설치
pip install hachillesworld

# 로컬 Judge (Ollama) 사용 시
pip install hachillesworld[local]

# MLflow 연동 시
pip install hachillesworld mlflow

# PostgreSQL 스토리지 사용 시
pip install hachillesworld[postgres]
```

---

## 개발 환경

```bash
git clone https://github.com/suhopark1-tech/hachillesworld
cd HAchillesWorld
pip install -e ".[dev]"
pytest                    # 전체 테스트
pytest tests/test_interpreter.py  # 해석 엔진 테스트만
```

---

## 라이선스

이 저장소는 **이중 라이선스(Dual License)** 구조를 채택합니다.

| 구성 요소 | 라이선스 | 범위 |
|---------|--------|------|
| **`validation/`** | Apache License 2.0 | HAS 계산 참조 구현 — 자유롭게 사용·수정·배포 가능 |
| **`src/hachillesworld/`** | Proprietary | 상용 플랫폼 코드 — 별도 상용 라이선스 필요 |

Apache 2.0 전문: [LICENSE](./LICENSE) | NOTICE: [NOTICE](./NOTICE)

상용 플랫폼 라이선스 문의: suhopark1@gmail.com

> **특허 고지**: HAchillesWorld는 이 소프트웨어에 구현된 일부 알고리즘에 대해
> 특허를 출원하였거나 출원 예정입니다. Apache 2.0 Section 3에 따라, `validation/`
> 배포본을 그대로 사용하는 경우 해당 특허에 대한 허가가 부여됩니다.

---

이론적 기반: 《Agentic World Modeling 2027: The Architecture of Autonomous Intelligence》 — 박성훈

*HAchillesWorld SDK v2.1 — 2026년 6월*
