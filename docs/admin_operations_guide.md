# HAchillesWorld Admin 운용 가이드

> 최종 업데이트: 2026-06-07 (POST 10 반영)  
> 관리자: 박성훈

---

## 1. Admin 페이지 접속

### URL

```
https://suhopark1-tech.github.io/hachillesworld/admin.html
```

사이트 어느 페이지에서든 **푸터 최하단 `HAchilles Labs`** 링크를 클릭해도 접속됩니다.

### 로그인

| 항목 | 값 |
|---|---|
| 비밀번호 | `1234` |
| 비밀번호 변경 방법 | `admin.html`의 `PASS_HASH`를 새 비밀번호의 SHA-256 해시로 교체 |

SHA-256 해시 생성 (브라우저 콘솔):
```javascript
crypto.subtle.digest('SHA-256', new TextEncoder().encode('새비밀번호'))
  .then(b => console.log([...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')))
```

---

## 2. GitHub Personal Access Token (PAT)

Traffic API 연동에 필요합니다. 최초 1회 입력하면 브라우저 localStorage에 저장되어 이후 자동 입력됩니다.

### 발급

1. `https://github.com/settings/tokens/new` 접속
2. Note: `HAchillesWorld Admin`
3. Scopes: `repo` 체크
4. **Generate token** → `ghp_...` 형식의 토큰 복사

### 등록

Admin 로그인 → 토큰 입력란에 붙여넣기 → **연결** 클릭  
이후 재방문 시 토큰은 자동으로 채워집니다.

### 보안 주의

- 토큰은 브라우저 localStorage에만 저장되며 소스코드에는 없습니다
- 토큰이 외부에 노출됐을 경우 GitHub에서 즉시 삭제 후 재발급하세요
  - `https://github.com/settings/tokens` → 해당 토큰 Delete

---

## 3. 대시보드 4탭 설명

### Tab 1 — Traffic (방문자 현황)

| 항목 | 데이터 소스 | 제한 |
|---|---|---|
| 14일 총 방문 · 유니크 방문자 | GitHub Traffic API | 최근 14일만 제공 |
| 일별 방문 추이 차트 | GitHub Traffic API | 최근 14일 |
| 상위 추천 경로 (Referrers) | GitHub Traffic API | 상위 10개 |
| 상위 페이지 (Paths) | GitHub Traffic API | 상위 10개 |
| **시간대별 히트맵** (0~23시) | localStorage (haw-analytics.js) | 이 기기 누적 |

> GitHub Traffic API는 저장소 소유자/협업자 권한의 PAT가 필요합니다.

### Tab 2 — Blog (블로그 현황)

| 항목 | 데이터 소스 |
|---|---|
| 총 블로그 포스트 수 | **12개** (POST 01~12, admin.html BLOG_POSTS 배열 하드코딩) |
| 추적된 블로그 방문 수 | localStorage |
| 평균 체류시간 (초) | localStorage (페이지 이탈 시 기록) |
| 평균 스크롤 깊이 (%) | localStorage (25·50·75·90% 마일스톤) |
| 포스트별 방문·체류·스크롤 표 | localStorage |
| GitHub Views (포스트별) | GitHub Traffic API (Traffic 탭 연결 후 표시) |

**BLOG_POSTS 배열 현황** (`landing/admin.html` 기준):

| # | 파일 | 제목 |
|---|------|------|
| 12 | blog-harness-guide.html | HAchillesWorld Harness 완전 가이드 |
| 11 | blog-planning-depth-cost.html | Planning Depth와 비용의 상관관계 |
| 10 | blog-v3-roadmap.html | HAchillesWorld v3.0 로드맵 |
| 09 | blog-multi-agent-collaboration.html | Multi-Agent 협업 실전 |
| 08 | blog-agent-cost-optimization.html | AI 에이전트 비용 최적화 |
| 07 | blog-user-guide.html | 완전 사용 가이드 v2.1 |
| 06 | blog-glossary.html | 플랫폼 용어 완전 해설 |
| 05 | blog-recognition-certification.html | AI 에이전트 인정과 인증 |
| 04 | blog-arxiv-paper.html | AI 에이전트 신용 점수 |
| 03 | blog-why-world-model.html | World Model 기업 도입 이유 |
| 02 | blog-mcts-planning-depth.html | MCTS Planning Depth |
| 01 | blog-world-model.html | AI 에이전트 왜 실패하는가 |

> 다음 포스트 번호: **13** — `/blog-add` 스킬 실행 시 자동 업데이트됨

### Tab 3 — Scan 진단

| 항목 | 데이터 소스 |
|---|---|
| Scan 전환 퍼널 (방문→제출) | localStorage |
| 총 제출 수 · 최근 7일 · 오늘 | localStorage |
| 전환율 (CVR) | localStorage 계산 |
| 제출 도메인 목록 | localStorage |

> `haw-analytics.js`가 `scan.html`에 삽입되어 자동 기록됩니다.

### Tab 4 — System

| 항목 | 내용 |
|---|---|
| GitHub Pages CI 상태 | `pages.yml` 최근 실행 결과 |
| Python CI 상태 | `ci.yml` 최근 실행 결과 |
| haw-analytics.js 로드 여부 | 런타임 감지 |
| GA4 Measurement ID | `G-E78PZ2H8FG` (설정됨) |
| localStorage 이벤트 수 | 누적 이벤트 수 + 초기화 버튼 |
| 블로그 포스트 수 / 다음 번호 | 10개 (POST 01~10) / 다음 번호: 11 |
| GA4 설정 5단계 가이드 | 연동 방법 안내 |
| Docker 스택 포트 안내 | 로컬 개발 참고 |

---

## 4. Google Analytics 4 (GA4)

### 설정 현황

| 항목 | 값 |
|---|---|
| Measurement ID | `G-E78PZ2H8FG` |
| 속성명 | HAchillesWorld |
| 스트림 URL | `suhopark1-tech.github.io/hachillesworld` |
| 설정 파일 | `landing/haw-analytics.js` |

### GA4 대시보드 접속

```
https://analytics.google.com
```

**주요 리포트 경로:**

| 확인 항목 | 경로 |
|---|---|
| 실시간 방문자 | 보고서 → 실시간 |
| 지역별 방문자 | 보고서 → 사용자 → 인구통계 세부정보 |
| 시간대별 분포 | 탐색 → 빈 양식 → 시간 측정기준 추가 |
| 블로그 체류시간 | 보고서 → 참여도 → 페이지 및 화면 |
| 유입 채널 | 보고서 → 획득 → 트래픽 획득 |
| 기기·브라우저 | 보고서 → 기술 → 기술 세부정보 |

### GA4로 수집되는 커스텀 이벤트

| 이벤트명 | 발생 시점 |
|---|---|
| `scroll` | 블로그 25·50·75·90% 스크롤 도달 |
| `engagement` | 블로그 페이지 이탈 시 (체류시간·스크롤 포함) |
| `scan_view` | scan.html 진입 |
| `scan_submit` | Scan 제출 버튼 클릭 |
| `cta_github` | GitHub 링크 클릭 |
| `cta_internal` | Scan·Optimize 등 내부 CTA 클릭 |

---

## 5. haw-analytics.js 트래킹 모듈

### 위치

```
landing/haw-analytics.js
```

### 삽입된 페이지

모든 블로그 포스트, `index.html`, `blog.html`, `scan.html` 의 `</body>` 직전에 삽입되어 있습니다.

### 공개 API

브라우저 콘솔에서 직접 조회 가능합니다:

```javascript
// 페이지별 집계
HAWAnalytics.summary()

// 시간대별 방문 분포 (배열 24개)
HAWAnalytics.hourlyDist()

// 최근 14일 일별 방문
HAWAnalytics.dailyDist(14)

// Scan 제출 목록
HAWAnalytics.scanSubmits()

// 블로그 포스트별 체류시간·스크롤
HAWAnalytics.blogStats()

// localStorage 이벤트 전체 조회
HAWAnalytics.getEvents()

// localStorage 초기화
HAWAnalytics.clear()
```

### 데이터 저장 위치

브라우저 localStorage 키 `haw_evt`, 최대 1,000개 이벤트 순환 저장

---

## 6. 데이터 수집 한계 및 보완

| 한계 | 원인 | 보완 방법 |
|---|---|---|
| GitHub Traffic API 14일 제한 | API 스펙 | GA4로 장기 데이터 확인 |
| localStorage는 이 기기만 | 클라이언트 한정 | GA4로 전체 방문자 확인 |
| 지역별 방문자 미표시 | localStorage 불가 | GA4 인구통계 리포트 |
| 실시간 방문자 수 미표시 | localStorage 불가 | GA4 실시간 리포트 |

---

## 7. Docker 스택 (고급·로컬 전용)

```bash
docker compose up
```

| 서비스 | URL | 용도 |
|---|---|---|
| FastAPI | `http://localhost:8000` | 진단 API |
| Prometheus | `http://localhost:9090` | 메트릭 수집 |
| Grafana | `http://localhost:3000` | 시각화 (admin/admin) |
| ClickHouse | `http://localhost:8123` | OLAP 이벤트 DB |
| Redis | `localhost:6379` | 캐시 |

> Docker 스택은 로컬 개발 전용입니다. GitHub Pages 정적 사이트와는 별도로 동작합니다.

---

## 8. 정기 운용 체크리스트

### 매주

```
[ ] GA4 대시보드에서 방문자 추이 확인
[ ] Admin Traffic 탭 → 상위 페이지 확인
[ ] Admin Blog 탭 → 체류시간 낮은 포스트 파악
[ ] Admin Scan 탭 → 전환율 확인
```

### 블로그 포스트 추가 시

`/blog-add [제목]` 스킬이 아래 항목을 **모두 자동** 처리합니다 (STEP 4 + STEP 6):

```
[자동] landing/blog-{slug}.html 생성
[자동] landing/blog.html 카드 삽입
[자동] landing/admin.html — BLOG_POSTS · KPI · System 탭
[자동] docs/blog_add_workflow_prompt.md — 현황 표·다음 번호
[자동] docs/admin_operations_guide.md — Blog 탭 표·다음 번호 (이 파일)
[자동] .claude/commands/blog-add.md — 예시 번호·태그
[자동] git commit + git push (6개 파일 일괄)
[자동] CI (pages.yml) 모니터링 및 결과 보고
```

### GitHub PAT 만료 시

```
[ ] https://github.com/settings/tokens 에서 재발급
[ ] Admin 로그인 → 새 토큰 입력 → 연결
[ ] (자동으로 localStorage 갱신됨)
```

---

## 9. 관련 파일 위치

| 파일 | 역할 |
|---|---|
| `landing/admin.html` | Admin 대시보드 (4탭) |
| `landing/haw-analytics.js` | 트래킹 모듈 (GA4 + localStorage) |
| `.github/workflows/pages.yml` | CI — HTML 검증 + GitHub Pages 배포 |
| `.github/workflows/ci.yml` | CI — Python 테스트·린트 |
| `.claude/commands/blog-add.md` | 블로그 추가 커스텀 커맨드 |
| `docs/blog_add_workflow_prompt.md` | 블로그 추가 트리거 프롬프트 (포스트 현황 포함) |
| `docs/admin_operations_guide.md` | Admin 운용 가이드 (이 파일) |
