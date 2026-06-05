# HAW-STUDY-001 참여 기업 온보딩 가이드

> **HAchillesWorld 횡단 타당도 연구 (HAW-STUDY-001)**  
> AI 에이전트 품질 지표(HAS)와 실제 비즈니스 성과 간 상관관계 검증

---

## 연구 개요

| 항목 | 내용 |
|------|------|
| 연구명 | HAW-STUDY-001: HAS 횡단 타당도 연구 |
| 연구 기간 | 2026년 7월 ~ 2026년 10월 (30일 데이터 수집) |
| 참여 규모 | n ≥ 10개 기업 |
| 주요 가설 | H1: ρ(HAS, Q_composite) ≥ 0.60, p < 0.01 |
| 담당 연구자 | 박성훈 (suhopark1@gmail.com) |

---

## 참여 요건

- **에이전트 운영 규모**: 월 500회 이상 에이전트 에피소드 실행
- **운영 기간**: 연구 기간 중 연속 30일 데이터 수집 가능
- **도메인**: supply_chain, customer_service, code_generation, finance, healthcare 중 하나
- **NDA 서명**: 연구 참여 전 데이터 동의서 서명 필수 (`data_consent_template.md` 참조)

---

## 참여 3단계 요약

```
1. 등록 (1일)       → StudyClient.enroll() 호출 → study_id 발급
2. 수집 (30일)      → SDK @instrument 데코레이터로 자동 로깅
3. KPI 제출 (월1회) → client.submit_kpi() 로 비즈니스 지표 제출
```

자세한 설치 방법은 [`sdk_install_guide.md`](sdk_install_guide.md)를 참조하세요.

---

## 단계별 상세 안내

### 1단계: 등록

```python
from hachillesworld import StudyClient

enrollment = StudyClient.enroll(
    org_name="귀사 명칭",          # 내부적으로 SHA256 익명화
    agent_type="your_agent_v1",   # 에이전트 유형 식별자
    domain="supply_chain",         # 운영 도메인
    consent=True,                  # 데이터 수집 동의
)

print(enrollment.study_id)        # HAW-20260701-A3F2B1
# → haw_study_config.yaml 자동 생성
```

### 2단계: 에이전트 계측

```python
client = StudyClient(
    study_id=enrollment.study_id,
    agent_id="anon-001",           # 임의 식별자 (실명 불필요)
    domain="supply_chain",
    api_key="haw-...",             # 연구팀에서 발급
)

@client.instrument
class YourAgent:
    def plan(self, state, goal): ...
    def execute(self, action): ...
    def observe(self, result): ...
```

### 3단계: KPI 월별 제출

```python
# 매월 말일 또는 연구팀 요청 시
client.submit_kpi({
    "task_completion_rate": 0.87,   # 작업 완료율 (0~1)
    "time_savings_pct": 23.5,       # 시간 절감률 (%)
    "error_rate": 0.03,             # 오류율 (0~1)
    "cost_reduction_pct": 12.0,     # 비용 절감률 (%)
    "csat_score": 4.2,              # 고객 만족도 (1~5)
})
```

---

## 데이터 수집 범위

수집되는 데이터:

| 데이터 종류 | 내용 | 민감도 |
|------------|------|--------|
| 에피소드 성공/실패 | bool | 낮음 |
| 확신도(confidence) | 0~1 float | 낮음 |
| 계획 깊이(PD) | 정수 | 낮음 |
| 도구 호출 목록 | 문자열 목록 | 낮음 |
| 실행 시간 | 밀리초 | 낮음 |
| KPI 지표 | 제출한 값 | 중간 |

수집되지 않는 데이터: 사용자 개인정보, 프롬프트 원문, 비즈니스 기밀, 고객 데이터

모든 `agent_id`는 전송 전 SHA256 해시로 익명화됩니다.

---

## 중간 보고서 확인

```python
report = client.generate_interim_report()
print(report.summary())
# HAW-STUDY 중간 보고서 (HAW-20260701-A3F2B1)
#   에피소드: 2,847건
#   수집 기간: 28일 (커버리지 93.3%)
#   HAS 평균: 0.8421  σ: 0.1203
#   KPI 제출 월수: 1
#   ρ(HAS, KPI) = 0.72  p = 0.008  [PASS]
```

---

## FAQ

**Q: SDK 설치가 기존 시스템에 영향을 주나요?**  
A: `@instrument` 데코레이터는 비침투적이며 에러 발생 시 원래 동작을 보장합니다.

**Q: 데이터 전송이 실패하면 어떻게 되나요?**  
A: `.haw_study/logs/fallback/`에 로컬 JSONL로 자동 저장됩니다.

**Q: 연구 중 이탈할 수 있나요?**  
A: 언제든 `client.close()`로 수집을 중단할 수 있습니다. 수집된 데이터는 동의서 조건에 따라 처리됩니다.

**Q: 문의처**  
A: suhopark1@gmail.com / GitHub Issues
