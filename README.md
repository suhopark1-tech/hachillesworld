# HAchillesWorld

[![Version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)](https://github.com/suhopark1-tech/hachillesworld/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen?style=flat-square&logo=pytest&logoColor=white)](https://github.com/suhopark1-tech/hachillesworld/tree/main/tests)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey?style=flat-square)](https://github.com/suhopark1-tech/hachillesworld)
[![Anthropic](https://img.shields.io/badge/Powered%20by-Claude%20Sonnet%204.6-D97706?style=flat-square&logo=anthropic&logoColor=white)](https://www.anthropic.com)
[![Framework](https://img.shields.io/badge/Framework-Levels%20%C3%97%20Laws-8B5CF6?style=flat-square)](https://github.com/suhopark1-tech/hachillesworld/blob/main/docs/HAchillesWorld_%EA%B8%B0%ED%9A%8D%EC%84%9C.md)

> **"당신의 AI 에이전트는 세계를 얼마나 정확히 이해하고 있는가?"**

World Model 진단 및 최적화 플랫폼. 기업과 개인의 AI 에이전트 시스템을 Levels × Laws 프레임워크로 진단하고, 최적화 로드맵을 생성하며, 실시간 운영을 지원한다.

이론적 기반: 《Agentic World Modeling 2027: The Architecture of Autonomous Intelligence》 — 박성훈

---

## 3개 모듈

| 모듈 | 기능 |
|------|------|
| **Scan** | Levels × Laws 자동 진단, 15개 지표, 리포트 생성 |
| **Optimize** | 맞춤 로드맵 자동 생성, 하네스 코드 생성, 비용 절감 계획 |
| **Operate** | 실시간 Drift 감지, Replay 디버깅, Meta-Harness 자동화 |

---

## 빠른 시작

### 설치

```bash
pip install hachillesworld
```

### SDK 통합 (5분)

```python
from hachillesworld import HAchillesWorldClient, instrument

client = HAchillesWorldClient(api_key="haw-...")

@instrument(client, agent_name="my-agent")
class MyAgent:
    def plan(self, state, goal): ...
    def execute(self, action): ...
```

### CLI 진단

```bash
hachillesworld scan --logs ./agent_logs/ --config ./agent_config.json
```

### OpenTelemetry 브리지

```yaml
exporters:
  hachillesworld:
    endpoint: "https://ingest.hachillesworld.ai/v1"
    api_key: "${HACHILLESWORLD_API_KEY}"
```

---

## 프로젝트 구조

```
HAchillesWorld/
├── docs/                          # 문서
│   └── HAchillesWorld_기획서.md
├── src/hachillesworld/
│   ├── core/                      # 공통 코어 (모델, 클라이언트, 설정)
│   ├── scan/                      # Module 1: 진단 엔진
│   ├── optimize/                  # Module 2: 최적화 엔진
│   ├── operate/                   # Module 3: 운영 인텔리전스
│   └── cli.py                     # CLI 진입점
├── tests/                         # 테스트
├── examples/                      # 사용 예제
├── pyproject.toml
└── requirements.txt
```

---

## 개발 환경 설정

```bash
git clone https://github.com/suhopark1-tech/hachillesworld
cd HAchillesWorld
pip install -e ".[dev]"
pytest
```

---

*HAchillesWorld v0.1.0 — 2026년 6월*
