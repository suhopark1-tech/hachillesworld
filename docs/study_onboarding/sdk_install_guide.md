# HAchillesWorld SDK 설치 가이드 (3단계)

> HAW-STUDY-001 참여를 위한 SDK 설치 및 초기 설정

---

## 시스템 요건

- Python 3.11+
- 네트워크: `ingest.hachillesworld.ai:443` 아웃바운드 허용
- 디스크: 최소 100MB (로그 폴백 공간)

---

## Step 1. SDK 설치

```bash
pip install hachillesworld
```

의존성 확인:

```bash
python -c "import hachillesworld; print(hachillesworld.__version__)"
# 2.0.0
```

방화벽 환경 (에어갭):

```bash
# 연구팀이 제공한 오프라인 패키지 사용
pip install --no-index --find-links ./offline_pkg hachillesworld
```

---

## Step 2. 등록 및 설정 파일 생성

```python
from hachillesworld import StudyClient

# 최초 1회만 실행
enrollment = StudyClient.enroll(
    org_name="귀사명",              # 내부적으로 SHA256 익명화 저장
    agent_type="your_agent_v1",
    domain="supply_chain",          # 운영 도메인
    consent=True,
)

print(f"study_id: {enrollment.study_id}")
print(f"설정 파일: {enrollment.config_path}")
```

실행 결과:
```
study_id: HAW-20260701-A3F2B1
설정 파일: .haw_study/haw_study_config.yaml
```

생성된 `haw_study_config.yaml` 예시:

```yaml
study_id: HAW-20260701-A3F2B1
org_hash: 3a7f9b2c1d4e5f6a
agent_type: your_agent_v1
domain: supply_chain
enrolled_at: 2026-07-01T09:00:00+00:00
ingest_url: https://ingest.hachillesworld.ai/v1
flush_interval_sec: 60
batch_size: 100
```

---

## Step 3. 에이전트 계측

연구팀에서 발급한 `api_key`를 사용합니다.

### 방법 A: @instrument 데코레이터 (권장)

```python
from hachillesworld import StudyClient

client = StudyClient(
    study_id="HAW-20260701-A3F2B1",  # Step 2에서 발급
    agent_id="anon-001",              # 임의 식별자
    domain="supply_chain",
    api_key="haw-YOUR_API_KEY",
)

@client.instrument
class SupplyChainAgent:
    def plan(self, state: dict, goal: str) -> list:
        # 기존 코드 그대로
        ...

    def execute(self, action: str) -> dict:
        # 기존 코드 그대로
        ...
```

**변경 없음**: 기존 에이전트 코드를 수정하지 않습니다.

### 방법 B: 컨텍스트 매니저 (세밀한 제어)

```python
with client.episode() as ep:
    ep.set_confidence(0.82)
    ep.set_predicted_state({"inventory": 820})

    result = agent.act(state)

    ep.set_actual_state({"inventory": 815})
    ep.set_goal(achieved=True)
    ep.add_tool("order_api")
```

### 방법 C: 수동 레코드 추가

```python
from hachillesworld.collect.episode import EpisodeRecord

record = EpisodeRecord(
    agent_id="anon-001",
    study_id="HAW-20260701-A3F2B1",
    domain="supply_chain",
    goal_achieved=True,
    episode_success=True,
    confidence=0.87,
    duration_ms=1240.5,
)
client.add(record)
```

---

## 동작 확인

```python
# 버퍼 즉시 전송 테스트
flushed = client.flush()
print(f"전송된 레코드: {flushed}건")

# 상태 확인
print(client.stats)
# {'total_added': 1, 'total_flushed': 1, 'buffered': 0}
```

---

## 종료 처리

```python
# 컨텍스트 매니저 사용 (권장)
with StudyClient(...) as client:
    # 에이전트 실행
    ...
# __exit__ 시 자동 flush + 스레드 종료

# 또는 명시적 종료
client.close()
```

---

## 문제 해결

| 증상 | 해결 방법 |
|------|-----------|
| `ConnectionError` | 방화벽 규칙 확인, `fallback_path` 설정 |
| 로그가 보이지 않음 | `flush_interval` 감소 또는 `client.flush()` 수동 호출 |
| `ImportError: hachillesworld` | Python 3.11+ 및 `pip install hachillesworld` 재실행 |
| KPI 저장 실패 | `.haw_study/kpi/` 디렉토리 쓰기 권한 확인 |

```python
# 디버그 로깅 활성화
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 지원

- 이메일: suhopark1@gmail.com
- GitHub: https://github.com/HAchillesWorld/sdk/issues
