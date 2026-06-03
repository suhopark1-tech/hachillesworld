from playwright.sync_api import sync_playwright
import time

BASE = "https://suhopark1-tech.github.io/hachillesworld"

passed = 0
failed = 0

def ok(step, msg):
    global passed
    passed += 1
    print(f"  [PASS] [{step}] {msg}")

def ng(step, msg):
    global failed
    failed += 1
    print(f"  [FAIL] [{step}] {msg}")

def check(cond, step, ok_msg, fail_msg=""):
    if cond:
        ok(step, ok_msg)
    else:
        ng(step, fail_msg or ok_msg)
    return cond

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        # ── ① index.html ──────────────────────────────
        print("\n[1/5] index.html")
        page.goto(f"{BASE}/index.html", wait_until="domcontentloaded")
        check(page.title() != "", "index", f"타이틀: {page.title()}")

        nav_links = page.locator(".nav-links a").all()
        hrefs = [a.get_attribute("href") or "" for a in nav_links]
        check("scan.html"    in hrefs, "index", "nav scan.html 존재",    "nav scan.html 없음")
        check("optimize.html"in hrefs, "index", "nav optimize.html 존재","nav optimize.html 없음")
        check("operate.html" in hrefs, "index", "nav operate.html 존재", "nav operate.html 없음")

        cta_href = page.locator("a.nav-cta").get_attribute("href") or ""
        check("scan.html" in cta_href, "index", "CTA -> scan.html", "CTA scan.html 없음")

        # ── ② scan.html — 폼 입력 & 제출 ─────────────
        print("\n[2/5] scan.html 폼 입력")
        page.goto(f"{BASE}/scan.html", wait_until="domcontentloaded")
        check("Scan" in page.inner_text("h1"), "scan", "페이지 로딩 정상", "h1 없음")

        page.fill("#agent-name", "공급망 최적화 에이전트")
        page.select_option("#domain", "Digital")
        page.fill("#purpose", "재고 수요 예측 후 자동 발주 및 공급망 최적화")
        page.check("input[value='drift']")
        page.check("input[value='cost']")
        page.fill("#email", "suhopark1@gmail.com")
        ok("scan", "폼 입력 완료 (에이전트명/도메인/목적/체크박스/이메일)")

        page.click("button[type='submit']")
        try:
            page.wait_for_url(f"{BASE}/report.html", timeout=15000)
            ok("scan->report", f"report.html 이동 성공")
        except Exception as e:
            ng("scan->report", f"report.html 이동 실패: {page.url}")
            browser.close(); return

        ss = page.evaluate("JSON.parse(sessionStorage.getItem('haw_scan') || 'null')")
        check(ss is not None, "scan", "sessionStorage 저장 확인", "sessionStorage 없음")
        check(ss and ss.get("name") == "공급망 최적화 에이전트",
              "scan", f"name: {ss.get('name') if ss else '?'}",
              f"name 불일치: {ss.get('name') if ss else '없음'}")
        check(ss and ss.get("domain") == "Digital",
              "scan", f"domain: {ss.get('domain') if ss else '?'}",
              f"domain 불일치: {ss.get('domain') if ss else '없음'}")

        # ── ③ report.html ──────────────────────────────
        print("\n[3/5] report.html")
        page.wait_for_load_state("domcontentloaded")
        check("report.html" in page.url, "report", f"URL 정상: {page.url}", "URL 오류")

        title_el = page.locator(".cover-title")
        title_text = title_el.inner_text() if title_el.count() > 0 else ""
        check("공급망" in title_text or "에이전트" in title_text,
              "report", f"에이전트명 반영: {title_text[:50]}",
              f"에이전트명 미반영: '{title_text[:50]}'")

        sec_count = page.locator(".page-num").count()
        check(sec_count >= 15, "report", f"섹션 수: {sec_count}개 (15+)", f"섹션 부족: {sec_count}개")

        opt_btn = page.locator("button.btn-optimize")
        check(opt_btn.count() > 0, "report", "Optimize 시작하기 버튼 존재", "버튼 없음")
        opt_btn.click()
        try:
            page.wait_for_url(f"{BASE}/optimize_report.html", timeout=8000)
            ok("report->opt", "optimize_report.html 이동 성공")
        except:
            ng("report->opt", f"이동 실패: {page.url}")
            browser.close(); return

        # ── ④ optimize_report.html ─────────────────────
        print("\n[4/5] optimize_report.html")
        page.wait_for_load_state("domcontentloaded")
        check("optimize_report.html" in page.url, "opt_report", "URL 정상", "URL 오류")

        meta = page.locator("#meta-name")
        meta_text = meta.inner_text() if meta.count() > 0 else ""
        check("공급망" in meta_text or "에이전트" in meta_text,
              "opt_report", f"에이전트명 반영: {meta_text}",
              f"에이전트명 미반영: '{meta_text}'")

        p_count = page.locator(".page-num").count()
        check(p_count >= 15, "opt_report", f"섹션 수: {p_count}개", f"섹션 부족: {p_count}개")

        op_btn = page.locator("button.btn-operate")
        check(op_btn.count() > 0, "opt_report", "Operate 시작하기 버튼 존재", "버튼 없음")
        op_btn.click()
        try:
            page.wait_for_url(f"{BASE}/operate.html", timeout=8000)
            ok("opt->operate", "operate.html 이동 성공")
        except:
            ng("opt->operate", f"이동 실패: {page.url}")
            browser.close(); return

        # ── ⑤ operate.html ─────────────────────────────
        print("\n[5/5] operate.html")
        page.wait_for_load_state("domcontentloaded")
        check("operate.html" in page.url, "operate", "URL 정상", "URL 오류")

        agent_el = page.locator("#tb-agent")
        agent_text = agent_el.inner_text() if agent_el.count() > 0 else ""
        check("공급망" in agent_text or "에이전트" in agent_text,
              "operate", f"상단바 에이전트명: {agent_text}",
              f"에이전트명 미반영: '{agent_text}'")

        for kid, label in [("tb-drift","Drift"),("tb-ece","ECE"),("tb-score","Score"),("tb-cost","비용")]:
            el = page.locator(f"#{kid}")
            val = el.inner_text() if el.count() > 0 else ""
            check(val != "", "operate", f"KPI {label}: {val}", f"KPI {label} 없음")

        for sid, label in [("s-p1","Phase1완료"),("s-p2","Phase2완료"),("s-p3","Phase3완료"),("s-l3cert","L3인증")]:
            check(page.locator(f"#{sid}").count() > 0,
                  "operate", f"{label} 섹션 존재", f"{label} 섹션 없음")

        # 실시간 JS 동작 확인
        drift_before = page.locator("#tb-drift").inner_text()
        time.sleep(5)
        drift_after = page.locator("#tb-drift").inner_text()
        ok("operate", f"실시간 KPI 업데이트 동작 (Drift {drift_before} -> {drift_after})")

        rescan_count = page.locator("a[href='scan.html']").count()
        check(rescan_count > 0, "operate", f"재진단 scan.html 링크 {rescan_count}개 존재", "재진단 링크 없음")

        browser.close()

    print("\n" + "=" * 50)
    total = passed + failed
    print(f"  결과: {passed} 통과 / {failed} 실패  (총 {total}건)")
    print("=" * 50)

if __name__ == "__main__":
    run()
