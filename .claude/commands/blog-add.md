# /blog-add — HAchillesWorld 블로그 포스트 추가 워크플로우

블로그 제목을 받아 포스트 HTML 파일 생성 → blog.html 카드 추가 → 커밋·푸시 → CI 결과 확인까지 전체 워크플로우를 실행합니다.

**사용법:** `/blog-add [블로그 제목]`

---

## 실행 단계

### STEP 1 — 입력 파싱 및 슬러그 생성

`$ARGUMENTS`에서 블로그 제목을 읽는다.

다음 정보를 확인하거나 유추한다:
- **title**: `$ARGUMENTS` (예: `AI 에이전트 비용 최적화 실전 가이드`)
- **slug**: 제목에서 자동 생성 (영문 소문자·하이픈, 예: `agent-cost-optimization`)
  - 한글 단어는 영문 약어로 변환 (AI에이전트→agent, 비용→cost, 최적화→optimization, 가이드→guide 등)
  - 특수문자 제거, 공백→하이픈
- **filename**: `landing/blog-{slug}.html`

현재 포스트 수를 확인해 다음 번호를 결정한다:
```powershell
(Get-ChildItem "landing\blog-*.html" | Where-Object { $_.Name -ne "blog.html" }).Count
```
→ 현재 개수 + 1 = 새 포스트 번호 (2자리, 예: 14)

슬러그와 번호를 확정하기 전에 사용자에게 다음을 확인한다:
- 생성할 파일명 (`landing/blog-{slug}.html`)
- 포스트 번호
- 블로그 카드에 들어갈 태그 목록 (기존 태그 참고: `#WorldModel`, `#MCTS`, `#AI기초`, `#AgenticAI`, `#실전케이스`, `#용어해설`, `#사용가이드`, `#비용최적화`, `#운영`, `#MultiAgent`, `#로드맵`, `#v3.0`, `#HAchillesWorld`, `#PlanningDepth`, `#Harness`, `#배포`, `#체크리스트`)
- 포스트 요약 설명 (2줄, 카드의 `post-desc`)
- 예상 분량 (예: "약 3,000자 · 12분 읽기")
- 부제 컬러 힌트 (실전/성과→green `var(--accent3)`, 기술/분석→cyan `var(--accent2)`, 연구/아카데믹→purple `#c4b5fd`, 전략→amber `#fbbf24`)

---

### STEP 2 — 블로그 포스트 HTML 생성

`landing/blog-{slug}.html` 파일을 생성한다. 기존 포스트(`landing/blog-world-model.html`)의 전체 구조를 템플릿으로 사용하되 다음 부분을 교체한다:

**`<head>` 교체:**
```html
<title>Blog — {제목} | HAchillesWorld</title>
<meta name="description" content="{요약 설명}" />
```

**Hero 교체:**
```html
<div class="blog-tag-row fade-up">
  <!-- 확정된 태그들을 span.blog-tag 으로 나열 -->
</div>
<h1 class="blog-title fade-up delay-1">{제목 (줄바꿈 적절히)}</h1>
<p class="blog-subtitle fade-up delay-2">{부제}</p>
```

**`blog-meta` 교체:**
```html
<div class="blog-author">
  <div class="author-avatar">박</div>박성훈
</div>
<span>{작성 날짜, 예: 2026년 6월}</span>
<span>{분량, 예: 약 3,000자 · 12분 읽기}</span>
```

**본문 (`article-body`):**
사용자가 본문 내용을 제공한 경우 삽입한다. 제공하지 않은 경우, 다음 구조의 **플레이스홀더 본문**을 삽입한다:

```html
<h2>들어가며</h2>
<p><!-- TODO: 작성 필요 --></p>

<h2>핵심 내용</h2>
<p><!-- TODO: 작성 필요 --></p>

<h2>실전 적용</h2>
<p><!-- TODO: 작성 필요 --></p>

<h2>마치며</h2>
<p><!-- TODO: 작성 필요 --></p>
```

**목차 (sidebar TOC):**
본문 h2 항목에 맞게 생성한다.

**Back 링크:** `<a href="blog.html">← 블로그 목록으로</a>` 유지

---

### STEP 3 — blog.html 카드 삽입

`landing/blog.html`의 `<!-- POST LIST -->` 블록 안, 기존 첫 번째 카드(현재 최신 포스트) **바로 위**에 새 카드를 삽입한다.

카드 HTML 패턴:
```html
      <!-- POST {번호} — {제목 요약} (최신) -->
      <a href="blog-{slug}.html" class="post-card post-card-featured fade-up delay-1">
        <div class="post-card-left">
          <div class="post-featured-badge">NEW</div>
          <div class="post-tag-row">
            <!-- 태그 span들 -->
          </div>
          <div class="post-title">{제목 (줄바꿈 포함)}</div>
          <div class="post-desc">{요약 설명}</div>
          <div class="post-meta">
            <div class="post-author">
              <div class="author-avatar-sm">박</div>
              박성훈
            </div>
            <span>{날짜}</span>
            <span>{분량}</span>
            <span style="color:{부제 컬러}">{부제 힌트}</span>
          </div>
        </div>
        <div class="post-card-right">
          <div class="post-num">{번호 2자리}</div>
          <div class="post-arrow">→</div>
        </div>
      </a>
```

기존 최신 포스트 카드에서 `post-card-featured` 클래스와 `post-featured-badge` 를 제거하고, `NEW` 배지도 제거한다 (단, arXiv 배지 등 특수 배지는 유지).

---

### STEP 4 — admin.html 업데이트

`landing/admin.html` 안의 세 곳을 수정한다.

**① BLOG_POSTS 배열 맨 앞에 새 항목 추가**

```javascript
const BLOG_POSTS = [
  { num:'{번호}', file:'blog-{slug}.html', title:'{제목 요약}' },  // ← 새 항목
  { num:'09', file:'blog-multi-agent-collaboration.html', title:'Multi-Agent 협업 실전' },
  // ... 기존 항목들
];
```

**② Blog 탭 KPI — 포스트 수 · 범위 업데이트**

```html
<!-- 변경 전 -->
<div class="kpi-num accent" id="b-total">9</div>
<div class="kpi-sub">POST 01 ~ 09</div>

<!-- 변경 후 -->
<div class="kpi-num accent" id="b-total">{새 총수}</div>
<div class="kpi-sub">POST 01 ~ {번호}</div>
```

**③ System 탭 — 현황 텍스트 업데이트**

```html
<!-- 변경 전 -->
<span class="sys-val">9개 (POST 01 ~ 09)</span>
...
<span class="badge-dim">/blog-add 스킬로 추가</span>  <!-- 다음 번호 -->

<!-- 변경 후 -->
<span class="sys-val">{새 총수}개 (POST 01 ~ {번호})</span>
...
<span class="badge-dim">/blog-add 스킬로 추가</span>  <!-- 다음 번호 +1 -->
```

System 탭의 "다음 블로그 포스트 번호" 값도 `{번호+1}`로 업데이트한다.

**④ docs/blog_add_workflow_prompt.md — 현황 표 업데이트**

표 맨 앞에 새 행 추가, 다음 포스트 번호 갱신:

```markdown
| {번호} | blog-{slug}.html | {제목} |   ← 새 행
| 10 | blog-v3-roadmap.html | HAchillesWorld v3.0 로드맵 |
...

> 다음 포스트 번호: **{번호+1}**
```

**⑤ docs/admin_operations_guide.md — Blog 탭 BLOG_POSTS 표 업데이트**

`Tab 2 — Blog` 섹션의 BLOG_POSTS 현황 표 맨 앞에 새 행 추가, 총수·다음 번호 갱신:

```markdown
| {번호} | blog-{slug}.html | {제목 요약} |   ← 새 행
| 10 | blog-v3-roadmap.html | HAchillesWorld v3.0 로드맵 |
...

> 다음 포스트 번호: **{번호+1}**
```

`총 블로그 포스트 수` 항목도 `**{새 총수}개** (POST 01~{번호})`로 업데이트한다.

**⑥ .claude/commands/blog-add.md (이 파일) — 다음 번호·태그 업데이트**

- `→ 현재 개수 + 1 = 새 포스트 번호 (2자리, 예: {번호+1})` 숫자 갱신
- 태그 목록에 이번 포스트에서 새로 사용한 태그가 있으면 추가

---

### STEP 5 — 변경 사항 확인

파일이 올바르게 생성/수정되었는지 점검한다:

```powershell
# 새 파일 존재 확인
Test-Path "landing\blog-{slug}.html"

# blog.html 링크 확인 (CI의 internal links check 사전 검증)
$links = Select-String -Path "landing\blog.html" -Pattern 'href="(blog-[^"]+\.html)"' -AllMatches |
  ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
foreach ($link in $links) {
  if (Test-Path "landing\$link") { Write-Host "OK: $link" }
  else { Write-Host "MISSING: $link"; exit 1 }
}
```

오류가 있으면 즉시 수정 후 진행한다.

---

### STEP 6 — Git 커밋 & 푸시

```powershell
git add landing/blog-{slug}.html landing/blog.html landing/admin.html `
        docs/blog_add_workflow_prompt.md `
        docs/admin_operations_guide.md `
        .claude/commands/blog-add.md
git status
```

스테이징 내용을 확인한 후 커밋:

```powershell
git commit -m "$(cat <<'EOF'
feat(blog): POST {번호} — {제목} 추가

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

커밋 성공 후 푸시:
```powershell
git push origin main
```

---

### STEP 7 — CI 실행 확인

푸시 후 GitHub Actions의 `pages.yml` 워크플로우가 자동 트리거된다. CI 상태를 확인한다:

```bash
# 최신 워크플로우 실행 목록 확인
gh run list --workflow=pages.yml --limit=3

# 가장 최근 실행 상세 보기 (실시간)
gh run watch $(gh run list --workflow=pages.yml --limit=1 --json databaseId -q '.[0].databaseId')
```

CI 단계별 결과를 보고한다:
- `validate` (HTML lint + internal links check)
- `deploy` (GitHub Pages 배포)

---

### STEP 8 — 결과 보고

CI 완료 후 다음 정보를 요약 보고한다:

```
✅ 블로그 포스트 추가 완료
──────────────────────────────────────────────────────────────
파일:                landing/blog-{slug}.html
카드:                blog.html POST {번호} 삽입
admin.html:          BLOG_POSTS · KPI · System 탭 업데이트
blog_add_prompt.md:  POST {번호} 행 추가, 다음 번호 {번호+1}
admin_guide.md:      Blog 탭 표 업데이트, 다음 번호 {번호+1}
blog-add.md:         예시 번호 · 태그 갱신
커밋:                {commit SHA 앞 7자리}
CI:                  validate ✅  deploy ✅
게시 URL:            https://suhopark1-tech.github.io/hachillesworld/blog-{slug}.html
──────────────────────────────────────────────────────────────
```

CI 실패 시:
- 실패 단계와 오류 메시지를 출력한다
- 가능한 경우 즉시 수정 후 재커밋·재푸시한다
- 수정 불가 시 원인과 해결 방법을 안내한다

---

## 주의 사항

- 새 파일을 커밋하기 전 반드시 **internal links check** (STEP 5)를 로컬에서 통과시킬 것
- `blog.html`에 카드를 추가하면서 `landing/blog-{slug}.html` 파일이 실제로 존재해야 CI가 통과됨
- 본문 TODO 플레이스홀더가 포함된 상태로 커밋·배포해도 무방 (페이지는 정상 표시)
- `git push`는 사용자 승인 후 실행 (기본 확인)
- STEP 4에서 이 파일(blog-add.md) 자신도 업데이트하므로, 수정 후 반드시 git add에 포함시킬 것
