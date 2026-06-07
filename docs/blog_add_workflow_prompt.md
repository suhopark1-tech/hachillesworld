# HAchillesWorld 블로그 포스트 추가 워크플로우 프롬프트

이 파일은 새 블로그 포스트를 추가할 때 Claude Code에 붙여넣는 **트리거 프롬프트 템플릿**입니다.  
블로그 제목을 넣어 `/blog-add` 스킬을 실행합니다.

---

## 빠른 사용법

Claude Code 프롬프트 창에 다음을 입력합니다:

```
/blog-add [블로그 제목]
```

**예시:**
```
/blog-add AI 에이전트 비용 최적화 실전 가이드
```

스킬이 자동으로 다음 워크플로우를 진행합니다:
1. 슬러그·번호 확인 (사용자 승인 요청)
2. `landing/blog-{slug}.html` 생성
3. `landing/blog.html` 카드 삽입
4. Internal links 로컬 검증
5. `git commit` + `git push`
6. GitHub Actions `pages.yml` CI 모니터링
7. 완료 보고 (배포 URL 포함)

---

## 본문 내용을 미리 준비한 경우

슬러그 확인 후 사용자 승인 단계에서 다음 형식으로 본문을 제공하면 플레이스홀더 없이 완성된 HTML로 생성됩니다:

```
/blog-add [블로그 제목]

---본문---
## 들어가며
(내용)

## 핵심 개념
(내용)

## 실전 적용
(내용)

## 마치며
(내용)
```

---

## 추가 메타데이터를 함께 지정하는 경우

```
/blog-add [블로그 제목]

태그: #WorldModel, #실전케이스, #AI기초
요약: (카드에 표시될 2줄 요약)
분량: 약 3,500자 · 13분 읽기
부제힌트: 실전 케이스 포함
```

---

## 워크플로우 파일 위치

| 파일 | 역할 |
|------|------|
| `.claude/commands/blog-add.md` | 스킬 정의 (Claude Code 자동 로드) |
| `landing/blog-{slug}.html` | 새로 생성되는 포스트 HTML |
| `landing/blog.html` | 카드가 추가되는 블로그 목록 |
| `.github/workflows/pages.yml` | CI — HTML 검증 + GitHub Pages 배포 |
| `.github/workflows/ci.yml` | CI — Python 테스트·린트 (블로그 변경엔 미트리거) |

---

## CI 수동 확인 명령어

푸시 후 CI 상태를 직접 확인하려면:

```bash
# pages.yml 최근 실행 목록
gh run list --workflow=pages.yml --limit=5

# 가장 최근 실행 실시간 보기
gh run watch $(gh run list --workflow=pages.yml --limit=1 --json databaseId -q '.[0].databaseId')

# 실패한 경우 로그 보기
gh run view --log-failed $(gh run list --workflow=pages.yml --limit=1 --json databaseId -q '.[0].databaseId')
```

---

## 체크리스트 (스킬 없이 수동 진행 시)

```
[ ] 1. landing/blog-{slug}.html 생성
[ ] 2. landing/blog.html 상단에 카드 삽입 (post-card-featured + NEW 배지)
[ ] 3. 이전 최신 카드에서 post-card-featured / NEW 배지 제거
[ ] 4. 로컬 링크 검증: blog.html의 모든 href가 파일로 존재하는지 확인
[ ] 5. git add landing/blog-{slug}.html landing/blog.html
[ ] 6. git commit -m "feat(blog): POST {번호} — {제목} 추가"
[ ] 7. git push origin main
[ ] 8. gh run watch (pages.yml CI 확인)
[ ] 9. 배포 URL 접속하여 렌더링 확인
```

---

## 현재 블로그 포스트 현황

| # | 파일 | 제목 |
|---|------|------|
| 13 | blog-deployment-checklist.html | AI 에이전트 배포 전 체크리스트 15 |
| 12 | blog-harness-guide.html | HAchillesWorld Harness 완전 가이드 |
| 11 | blog-planning-depth-cost.html | Planning Depth와 비용의 상관관계 |
| 10 | blog-v3-roadmap.html | HAchillesWorld v3.0 로드맵 공개 |
| 09 | blog-multi-agent-collaboration.html | Multi-Agent 협업 실전: 에이전트들이 서로 충돌할 때 |
| 08 | blog-agent-cost-optimization.html | AI 에이전트 비용 최적화 실전 가이드 |
| 07 | blog-user-guide.html | HAchillesWorld 완전 사용 가이드 v2.1 |
| 06 | blog-glossary.html | HAchillesWorld 플랫폼 용어 완전 해설 |
| 05 | blog-recognition-certification.html | AI 에이전트 — 인정과 인증 |
| 04 | blog-arxiv-paper.html | AI 에이전트에도 "신용 점수"가 필요하다 |
| 03 | blog-why-world-model.html | World Model, 기업이 반드시 도입해야 하는 이유 |
| 02 | blog-mcts-planning-depth.html | AI는 몇 수 앞을 보는가? MCTS Planning Depth |
| 01 | blog-world-model.html | 당신의 AI 에이전트, 왜 실패하는지 알고 있나요? |

> 다음 포스트 번호: **14**
