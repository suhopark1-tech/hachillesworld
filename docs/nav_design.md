# HAchillesWorld 플랫폼 네비게이션 설계서
**버전**: 1.0 | **작성일**: 2026-06-07 | **작성자**: 박성훈

---

## 1. 사이트맵 (전체 페이지 목록)

```
HAchillesWorld 웹사이트
│
├── 🌐 공개 (비로그인 포함)
│   ├── /index.html          홈 (한국어)
│   ├── /index-en.html       Home (English)
│   ├── /blog.html           블로그 홈
│   ├── /blog-world-model.html
│   ├── /blog-mcts-planning-depth.html
│   ├── /blog-why-world-model.html
│   ├── /blog-arxiv-paper.html
│   ├── /blog-recognition-certification.html
│   ├── /cert.html           L3 인증 안내 (읽기만)
│   └── /scan.html           무료 스캔 폼 ← 전환 페이지
│
├── 🔵 유료 이용자 (Pro 이상)
│   ├── /report.html         진단 보고서 (풀 리포트)
│   ├── /optimize.html       최적화 계획
│   ├── /optimize_report.html 최적화 보고서
│   └── /operate.html        운용 모니터링 대시보드
│
├── 🟢 연구자 (Researcher)
│   ├── /dashboard           Next.js 에이전트 목록
│   ├── /dashboard/[id]      에이전트 상세
│   └── /dashboard/settings  알림 설정
│       + API 직접 접근 (http://localhost:8001/docs)
│
└── 🔴 관리자 (Admin)
    └── /admin.html          관리자 패널 (로그인 필수)
```

---

## 2. 사용자 유형별 접근 권한

| 페이지 | 비로그인 | 무료 | 유료(Pro) | 연구자 | 관리자 |
|--------|----------|------|----------|--------|--------|
| index.html / index-en.html | ✅ | ✅ | ✅ | ✅ | ✅ |
| blog.html + 블로그 포스트 5개 | ✅ | ✅ | ✅ | ✅ | ✅ |
| cert.html (읽기) | ✅ | ✅ | ✅ | ✅ | ✅ |
| scan.html (무료 진단 1회) | ✅ | ✅ | ✅ | ✅ | ✅ |
| report.html | ❌ | ❌ | ✅ | ✅ | ✅ |
| optimize.html | ❌ | ❌ | ✅ | ✅ | ✅ |
| optimize_report.html | ❌ | ❌ | ✅ | ✅ | ✅ |
| operate.html | ❌ | ❌ | ✅ | ✅ | ✅ |
| /dashboard (Next.js) | ❌ | ❌ | ❌ | ✅ | ✅ |
| /dashboard/[agent_id] | ❌ | ❌ | ❌ | ✅ | ✅ |
| /dashboard/settings | ❌ | ❌ | ❌ | ✅ | ✅ |
| admin.html | ❌ | ❌ | ❌ | ❌ | ✅ |
| API /v1/* | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 3. 이용 흐름 (User Journey)

### 3-A. 무료 이용자 흐름
```
방문 → index.html
          ↓ CTA
      scan.html (무료 진단 폼 작성)
          ↓ 제출
      report.html (기본 리포트 미리보기)
          ↓ 업그레이드 유도
      → [가격 안내 / 유료 전환]
```

### 3-B. 유료 이용자 핵심 흐름
```
index.html
    ↓
scan.html ──────────────────────────────────┐
    ↓                                       │
report.html (진단 보고서 20페이지)           │ 재진단
    ↓                                       │
optimize.html (최적화 계획 수립)             │
    ↓                                       │
optimize_report.html (최적화 보고서)         │
    ↓                                       │
operate.html (운용 모니터링)  ───────────────┘
    ↓ (L3 달성 시)
cert.html (L3 인증 신청)
```

### 3-C. 연구자 흐름
```
index.html
    ↓
scan.html → report.html → optimize → operate
                                  +
/dashboard (에이전트 목록)
/dashboard/[agent_id] (상세 지표, HAS 게이지, 드리프트 그래프)
/dashboard/settings (알림 임계값)
API http://localhost:8001/docs (직접 API 호출)
```

### 3-D. 관리자 흐름
```
index.html
    ↓
admin.html (로그인)
    ↓
관리 대시보드 (GitHub API 연동, 사용자 관리, 리포트 조회)
    + 유료/연구자 모든 기능 접근 가능
```

---

## 4. 전역 네비게이션 규칙

### 4-1. 모든 페이지 공통 헤더 (Global Nav)

모든 정적 HTML 페이지는 아래 항목을 **반드시** 포함해야 한다.

```
[⬡ HAchillesWorld 로고] | 홈 | 스캔 | 최적화 | 운용 | 인증 | 블로그 | 대시보드 | [무료 진단 CTA]
```

| 항목 | 링크 | 표시 조건 |
|------|------|----------|
| ⬡ HAchillesWorld (로고) | index.html | 항상 |
| 홈 | index.html | 항상 |
| 스캔 | scan.html | 항상 |
| 최적화 | optimize.html | 항상 (미접근 페이지는 흐리게) |
| 운용 | operate.html | 항상 |
| 인증 | cert.html | 항상 |
| 블로그 | blog.html | 항상 |
| 대시보드 | /dashboard | 항상 |
| 무료 진단 (CTA) | scan.html | 스캔 페이지 제외 |

### 4-2. 뒤로가기/브레드크럼 규칙

선형 흐름 페이지(report, optimize_report, operate)는 **전역 nav 외에** 페이지 내 컨텍스트 네비게이션을 유지한다.

| 현재 페이지 | 이전 페이지 | 다음 페이지 |
|------------|------------|------------|
| scan.html | index.html | report.html |
| report.html | scan.html | optimize_report.html |
| optimize.html | report.html | optimize_report.html |
| optimize_report.html | report.html | operate.html |
| operate.html | optimize_report.html | cert.html |
| cert.html | operate.html | — (신청) |

### 4-3. 블로그 페이지 규칙

모든 블로그 포스트(blog-*.html)는:
- 상단 전역 nav 포함
- 포스트 끝에 **"블로그 목록으로"** 링크 → blog.html
- 관련 포스트 2개 이상 표시

### 4-4. admin.html 규칙

- 로그인 화면: "← 사이트 홈으로" 링크 필수
- 로그인 후 대시보드: 로고 클릭 → index.html
- 로그아웃 → 로그인 화면으로 (사이트 홈 링크 유지)

---

## 5. 접근 제어 구현 방안 (현재 → 목표)

| 현황 | 목표 |
|------|------|
| 모든 페이지 공개 (인증 없음) | JWT 세션 기반 접근 제어 |
| 무료/유료 구분 없음 | 로그인 후 플랜에 따라 리다이렉트 |
| admin.html 프론트 패스워드만 | 서버 사이드 인증 + RBAC |

**단계적 구현 로드맵:**
1. **즉시** (현재): 전역 nav + 뒤로가기 링크 추가 (이번 작업)
2. **v2.2** (2027-Q1): 로그인 미들웨어 + 유료/무료 페이지 분리
3. **v3.0** (2027-Q3): RBAC + SSO + 감사 로그 연동

---

## 6. 404 / 에러 페이지 규칙

- 없는 URL 접근 시 → index.html로 리다이렉트 (Next.js `not-found.tsx`)
- API 인증 실패 (401) → scan.html (재시작 유도)
- API 서버 다운 → 대시보드 대신 정적 report.html 표시

---

## 7. 모바일 네비게이션 규칙

화면 너비 ≤ 640px:
- 전역 nav의 중간 항목(최적화, 운용, 인증, 블로그) 숨김 (`data-hide`)
- 로고 + 무료 진단 CTA만 표시
- 햄버거 메뉴는 v2.2에서 추가 예정

---

## 8. URL 구조 표준

| URL 패턴 | 용도 | 서버 |
|---------|------|------|
| `http://localhost:3000/` | 홈 → `/dashboard` 리다이렉트 | Next.js |
| `http://localhost:3000/dashboard` | 에이전트 목록 | Next.js |
| `http://localhost:3000/dashboard/[id]` | 에이전트 상세 | Next.js |
| `http://localhost:3000/*.html` | 정적 HTML 페이지 | Next.js (public/) |
| `http://localhost:8001/v1/*` | REST API | FastAPI |
| `http://localhost:8001/docs` | Swagger UI | FastAPI |

---

*본 문서는 HAchillesWorld v2.1 기준이며, 인증 기능 구현(v2.2) 시 갱신 예정.*
