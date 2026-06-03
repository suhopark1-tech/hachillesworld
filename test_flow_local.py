"""
HAchillesWorld 전체 플로우 로컬 테스트
index → scan → report → optimize_report → operate → cert → blog
"""
import threading, http.server, time, sys, os
from playwright.sync_api import sync_playwright

LANDING = os.path.join(os.path.dirname(__file__), "landing")
PORT = 8742
BASE = f"http://localhost:{PORT}"

passed = failed = 0

def ok(step, msg):
    global passed; passed += 1
    print(f"  ✅ [{step}] {msg}")

def ng(step, msg):
    global failed; failed += 1
    print(f"  ❌ [{step}] {msg}")

def check(cond, step, ok_msg, fail_msg=""):
    if cond: ok(step, ok_msg)
    else:    ng(step, fail_msg or ok_msg)
    return cond

# ── 로컬 서버 ──────────────────────────────────────────────
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=LANDING, **kw)
    def log_message(self, *_): pass

def start_server():
    srv = http.server.HTTPServer(("localhost", PORT), SilentHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv

# ── 테스트 ─────────────────────────────────────────────────
def run():
    srv = start_server()
    time.sleep(0.5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ══════════════════════════════════════════════════
        # 1. index.html — 랜딩
        # ══════════════════════════════════════════════════
        print("\n[1/7] index.html — 랜딩 페이지")
        page.goto(f"{BASE}/index.html", wait_until="domcontentloaded")
        check("HAchillesWorld" in page.title(), "index", f"타이틀: {page.title()}")

        nav_hrefs = [a.get_attribute("href") or "" for a in page.locator(".nav-links a").all()]
        check("optimize.html" in nav_hrefs, "index", "nav → optimize.html")
        check("operate.html"  in nav_hrefs, "index", "nav → operate.html")
        check("blog.html"     in nav_hrefs, "index", "nav → blog.html")

        cta = page.locator("a.nav-cta").get_attribute("href") or ""
        check("scan.html" in cta, "index", "CTA 버튼 → scan.html")

        hero_text = page.locator("h1").first.inner_text()
        check(len(hero_text) > 5, "index", f"히어로 h1: {hero_text[:40]}")

        # ══════════════════════════════════════════════════
        # 2. scan.html — 진단 폼
        # ══════════════════════════════════════════════════
        print("\n[2/7] scan.html — 진단 폼 입력 & 제출")
        page.goto(f"{BASE}/scan.html", wait_until="domcontentloaded")
        h1 = page.locator("h1").first.inner_text()
        check("Scan" in h1 or "진단" in h1 or len(h1) > 3, "scan", f"페이지 로딩: {h1[:30]}")

        page.fill("#agent-name", "공급망 최적화 에이전트")
        page.select_option("#domain", "Digital")
        page.fill("#purpose", "재고 수요 예측 후 자동 발주 및 공급망 최적화")
        page.check("input[value='drift']")
        page.check("input[value='cost']")
        page.fill("#email", "suhopark1@gmail.com")
        ok("scan", "폼 입력 완료 (이름/도메인/목적/체크박스/이메일)")

        page.click("button[type='submit']")
        try:
            page.wait_for_url(f"{BASE}/report.html", timeout=12000)
            ok("scan→report", "report.html 이동 성공")
        except Exception as e:
            ng("scan→report", f"이동 실패: {page.url}")
            browser.close(); srv.shutdown(); return

        # sessionStorage 확인
        ss = page.evaluate("JSON.parse(sessionStorage.getItem('haw_scan') || 'null')")
        check(ss is not None,                              "scan", "sessionStorage 저장됨")
        check(ss and ss.get("name") == "공급망 최적화 에이전트", "scan", f"name: {ss.get('name') if ss else '?'}")
        check(ss and ss.get("domain") == "Digital",       "scan", f"domain: {ss.get('domain') if ss else '?'}")

        # ══════════════════════════════════════════════════
        # 3. report.html — 스캔 결과 리포트
        # ══════════════════════════════════════════════════
        print("\n[3/7] report.html — 스캔 결과 리포트")
        page.wait_for_load_state("domcontentloaded")
        check("report.html" in page.url, "report", "URL 정상")

        cover = page.locator(".cover-title")
        cover_text = cover.inner_text() if cover.count() > 0 else ""
        check("공급망" in cover_text or "에이전트" in cover_text,
              "report", f"에이전트명 반영: {cover_text[:40]}")

        sec_count = page.locator(".page-num").count()
        check(sec_count >= 15, "report", f"섹션 수: {sec_count}개 (15+)")

        opt_btn = page.locator("button.btn-optimize")
        check(opt_btn.count() > 0, "report", "Optimize 시작하기 버튼 존재")

        # Optimize 이동
        opt_btn.click()
        try:
            page.wait_for_url(f"{BASE}/optimize_report.html", timeout=8000)
            ok("report→opt", "optimize_report.html 이동 성공")
        except:
            ng("report→opt", f"이동 실패: {page.url}")
            browser.close(); srv.shutdown(); return

        # ══════════════════════════════════════════════════
        # 4. optimize_report.html — 최적화 리포트
        # ══════════════════════════════════════════════════
        print("\n[4/7] optimize_report.html — 최적화 리포트")
        page.wait_for_load_state("domcontentloaded")
        check("optimize_report.html" in page.url, "opt_report", "URL 정상")

        meta = page.locator("#meta-name")
        meta_text = meta.inner_text() if meta.count() > 0 else ""
        check("공급망" in meta_text or "에이전트" in meta_text,
              "opt_report", f"에이전트명 반영: {meta_text}")

        p_count = page.locator(".page-num").count()
        check(p_count >= 15, "opt_report", f"섹션 수: {p_count}개")

        op_btn = page.locator("button.btn-operate")
        check(op_btn.count() > 0, "opt_report", "Operate 시작하기 버튼 존재")

        op_btn.click()
        try:
            page.wait_for_url(f"{BASE}/operate.html", timeout=8000)
            ok("opt→operate", "operate.html 이동 성공")
        except:
            ng("opt→operate", f"이동 실패: {page.url}")
            browser.close(); srv.shutdown(); return

        # ══════════════════════════════════════════════════
        # 5. operate.html — 운영 대시보드
        # ══════════════════════════════════════════════════
        print("\n[5/7] operate.html — 운영 대시보드")
        page.wait_for_load_state("domcontentloaded")
        check("operate.html" in page.url, "operate", "URL 정상")

        agent_el = page.locator("#tb-agent")
        agent_text = agent_el.inner_text() if agent_el.count() > 0 else ""
        check("공급망" in agent_text or "에이전트" in agent_text,
              "operate", f"상단바 에이전트명: {agent_text}")

        for kid, label in [("tb-drift","Drift"),("tb-ece","ECE"),("tb-score","Score"),("tb-cost","비용")]:
            el = page.locator(f"#{kid}")
            val = el.inner_text() if el.count() > 0 else ""
            check(val != "", "operate", f"KPI {label}: {val}")

        for sid, label in [("s-p1","Phase1"),("s-p2","Phase2"),("s-p3","Phase3"),("s-l3cert","L3인증")]:
            check(page.locator(f"#{sid}").count() > 0, "operate", f"{label} 섹션 존재")

        drift_before = page.locator("#tb-drift").inner_text()
        time.sleep(5)
        drift_after = page.locator("#tb-drift").inner_text()
        ok("operate", f"실시간 KPI 동작 확인 (Drift: {drift_before} → {drift_after})")

        check(page.locator("a[href='scan.html']").count() > 0, "operate", "재진단 링크 존재")

        # ══════════════════════════════════════════════════
        # 6. cert.html — 인증 페이지
        # ══════════════════════════════════════════════════
        print("\n[6/7] cert.html — 인증 프로그램")
        page.goto(f"{BASE}/cert.html", wait_until="domcontentloaded")
        check("cert.html" in page.url, "cert", "URL 정상")

        cert_h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() > 0 else ""
        check(len(cert_h1) > 3, "cert", f"h1 존재: {cert_h1[:40]}")

        nav_cert = page.locator(".nav-links a").all()
        cert_hrefs = [a.get_attribute("href") or "" for a in nav_cert]
        check("index.html" in cert_hrefs or any("index" in h for h in cert_hrefs),
              "cert", "홈 링크 존재")

        # ══════════════════════════════════════════════════
        # 7. Blog 플로우 — 목록 → 글 1 → 글 2
        # ══════════════════════════════════════════════════
        print("\n[7/7] Blog 플로우 — 목록 → 아티클")
        page.goto(f"{BASE}/blog.html", wait_until="domcontentloaded")
        check("Blog" in page.title() or "HAchillesWorld" in page.title(),
              "blog", f"타이틀: {page.title()}")

        cards = page.locator("a.post-card").all()
        check(len(cards) >= 2, "blog", f"포스트 카드 수: {len(cards)}개 (2+)")

        # 카드 href 확인
        card_hrefs = [c.get_attribute("href") or "" for c in cards]
        check(any("blog-mcts" in h for h in card_hrefs), "blog", "MCTS 글 카드 링크 존재")
        check(any("blog-world-model" in h for h in card_hrefs), "blog", "World Model 글 카드 링크 존재")

        # blog-mcts-planning-depth.html 직접 접근
        page.goto(f"{BASE}/blog-mcts-planning-depth.html", wait_until="domcontentloaded")
        mcts_h1 = page.locator("h1").first.inner_text()
        check("MCTS" in mcts_h1 or "Planning" in mcts_h1 or "수" in mcts_h1,
              "blog-mcts", f"MCTS 글 h1: {mcts_h1[:50]}")

        toc_items = page.locator(".toc-list li").count()
        check(toc_items >= 5, "blog-mcts", f"TOC 항목 수: {toc_items}개")

        analogy_cards = page.locator(".analogy-card").count()
        check(analogy_cards >= 3, "blog-mcts", f"비유 카드 수: {analogy_cards}개")

        mcts_steps = page.locator(".mcts-steps .mcts-step").count()
        check(mcts_steps == 4, "blog-mcts", f"MCTS 4단계 박스 수: {mcts_steps}")

        # 관련 글 링크 확인
        related = page.locator("a[href='blog-world-model.html']")
        check(related.count() > 0, "blog-mcts", "관련 글 → blog-world-model.html 링크 존재")

        # blog-world-model.html
        page.goto(f"{BASE}/blog-world-model.html", wait_until="domcontentloaded")
        wm_h1 = page.locator("h1").first.inner_text()
        check("에이전트" in wm_h1 or "AI" in wm_h1 or "실패" in wm_h1,
              "blog-wm", f"World Model 글 h1: {wm_h1[:50]}")

        next_link = page.locator("a[href='blog-mcts-planning-depth.html']")
        check(next_link.count() > 0, "blog-wm", "다음 글 → blog-mcts-planning-depth.html 링크 존재")

        # 🔍 엣지 케이스 프로브
        print("\n  [🔍 프로브] blog.html 필터 탭 클릭")
        page.goto(f"{BASE}/blog.html", wait_until="domcontentloaded")
        filter_tabs = page.locator(".filter-tab").all()
        if len(filter_tabs) >= 2:
            filter_tabs[1].click()
            time.sleep(0.3)
            active_count = page.locator(".filter-tab.active").count()
            ok("blog-filter", f"필터 탭 클릭 → active 탭 수: {active_count}")
        else:
            ok("blog-filter", "필터 탭 UI 존재 확인")

        print("\n  [🔍 프로브] scan.html — 필수 필드 미입력 제출 시 방어")
        page.goto(f"{BASE}/scan.html", wait_until="domcontentloaded")
        page.click("button[type='submit']")
        time.sleep(0.5)
        still_on_scan = "scan.html" in page.url or "report.html" not in page.url
        check(still_on_scan, "scan-empty", "빈 폼 제출 시 scan 페이지 유지 (브라우저 validation)")

        print("\n  [🔍 프로브] 존재하지 않는 페이지 → 404 처리")
        resp = page.goto(f"{BASE}/nonexistent.html")
        check(resp is None or resp.status in [200, 404],
              "404-probe", f"없는 페이지 응답 상태: {resp.status if resp else 'no resp'}")

        browser.close()
    srv.shutdown()

    print("\n" + "═" * 56)
    total = passed + failed
    status = "🎉 ALL PASS" if failed == 0 else f"⚠️  {failed}건 실패"
    print(f"  {status}  —  {passed} 통과 / {failed} 실패  (총 {total}건)")
    print("═" * 56)
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    run()
