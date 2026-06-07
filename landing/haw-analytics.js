/**
 * HAchillesWorld Analytics Module v1.0
 *
 * 역할:
 *  1. Google Analytics 4 연동 (GA4_ID 설정 시 자동 활성화)
 *  2. localStorage 기반 자체 이벤트 기록 (GA4 없이도 동작)
 *  3. 블로그 체류시간·스크롤 깊이 자동 측정
 *  4. Scan 폼 이벤트, CTA 클릭 추적
 *
 * 설정:
 *  GA4_ID를 실제 측정 ID(G-XXXXXXXXXX)로 교체하면 GA4가 활성화됩니다.
 *  GA4 없이도 localStorage 기반 분석은 즉시 동작합니다.
 */

(function () {
  'use strict';

  /* ── 설정 ─────────────────────────────────────────────── */
  const CFG = {
    GA4_ID:     'G-XXXXXXXXXX',   // ← 실제 GA4 Measurement ID로 교체
    STORE_KEY:  'haw_evt',        // localStorage 키
    MAX_EVT:    1000,             // 최대 저장 이벤트 수
    PAGE:       location.pathname.replace(/.*\//, '') || 'index.html',
    IS_BLOG:    /^blog-/.test(location.pathname.replace(/.*\//, '')),
    IS_SCAN:    /scan\.html/.test(location.pathname),
  };

  /* ── localStorage 유틸 ───────────────────────────────── */
  const store = {
    get() {
      try { return JSON.parse(localStorage.getItem(CFG.STORE_KEY) || '[]'); }
      catch { return []; }
    },
    push(evt) {
      const arr = this.get();
      arr.push({ ts: Date.now(), ...evt });
      if (arr.length > CFG.MAX_EVT) arr.splice(0, arr.length - CFG.MAX_EVT);
      try { localStorage.setItem(CFG.STORE_KEY, JSON.stringify(arr)); }
      catch { /* storage full */ }
    },
    clear() { localStorage.removeItem(CFG.STORE_KEY); }
  };

  /* ── GA4 헬퍼 ────────────────────────────────────────── */
  function ga4(name, params) {
    if (typeof gtag === 'function' && CFG.GA4_ID !== 'G-XXXXXXXXXX') {
      gtag('event', name, params);
    }
  }

  /* ── 공통 이벤트: 페이지뷰 ───────────────────────────── */
  function trackPageView() {
    const ref = document.referrer ? new URL(document.referrer).hostname : 'direct';
    store.push({
      type: 'pageview',
      page: CFG.PAGE,
      ref,
      tz_offset: new Date().getTimezoneOffset(),
      hour: new Date().getHours(),
      ua: navigator.userAgent.slice(0, 120),
    });
  }

  /* ── 블로그 체류시간 + 스크롤 깊이 ──────────────────── */
  function trackBlogEngagement() {
    if (!CFG.IS_BLOG) return;

    const t0 = Date.now();
    let maxScroll = 0;
    const milestones = new Set();

    function onScroll() {
      const el   = document.documentElement;
      const pct  = Math.round((el.scrollTop / (el.scrollHeight - el.clientHeight)) * 100);
      if (pct > maxScroll) maxScroll = pct;

      [25, 50, 75, 90].forEach(m => {
        if (pct >= m && !milestones.has(m)) {
          milestones.add(m);
          store.push({ type: 'scroll', page: CFG.PAGE, depth: m });
          ga4('scroll', { page: CFG.PAGE, percent_scrolled: m });
        }
      });
    }

    function onLeave() {
      const sec = Math.round((Date.now() - t0) / 1000);
      store.push({
        type:       'engagement',
        page:       CFG.PAGE,
        duration_s: sec,
        max_scroll: maxScroll,
      });
      ga4('engagement', { page: CFG.PAGE, duration_s: sec, max_scroll: maxScroll });
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('beforeunload', onLeave);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') onLeave();
    });
  }

  /* ── Scan 폼 추적 ────────────────────────────────────── */
  function trackScanForm() {
    if (!CFG.IS_SCAN) return;

    // 폼 페이지 진입
    store.push({ type: 'scan_view', page: CFG.PAGE });
    ga4('scan_view', {});

    // 제출 버튼
    document.addEventListener('click', e => {
      const btn = e.target.closest('.btn-scan, [data-track="scan-submit"]');
      if (!btn) return;
      const form   = document.querySelector('form, .card');
      const domain = form?.querySelector('[name="domain"], #domain, input[type="text"]')?.value || '';
      store.push({ type: 'scan_submit', domain: domain.slice(0, 60) });
      ga4('scan_submit', { domain });
    });
  }

  /* ── CTA 클릭 추적 ───────────────────────────────────── */
  function trackCTA() {
    document.addEventListener('click', e => {
      const a = e.target.closest('a[href], button');
      if (!a) return;

      const href  = a.getAttribute('href') || '';
      const label = (a.textContent || '').trim().slice(0, 80);

      // GitHub 링크
      if (href.includes('github.com')) {
        store.push({ type: 'cta_github', page: CFG.PAGE, label });
        ga4('cta_github', { page: CFG.PAGE, label });
        return;
      }
      // 내부 CTA (scan, optimize 등)
      if (/\bscan\b|\boptimize\b|\boperate\b/i.test(href + label)) {
        store.push({ type: 'cta_internal', page: CFG.PAGE, href, label });
        ga4('cta_internal', { page: CFG.PAGE, href, label });
      }
    });
  }

  /* ── GA4 스크립트 동적 로드 ──────────────────────────── */
  function loadGA4() {
    if (CFG.GA4_ID === 'G-XXXXXXXXXX') return;
    const s = document.createElement('script');
    s.src   = `https://www.googletagmanager.com/gtag/js?id=${CFG.GA4_ID}`;
    s.async = true;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', CFG.GA4_ID, { send_page_view: true });
  }

  /* ── 공개 API (window.HAWAnalytics) ──────────────────── */
  window.HAWAnalytics = {
    track: (type, data) => {
      store.push({ type, ...data });
      ga4(type, data);
    },
    getEvents: () => store.get(),
    clear:     () => store.clear(),

    /** admin용: 페이지별 집계 */
    summary() {
      const evts = store.get();
      const pages = {};
      evts.forEach(e => {
        if (!e.page) return;
        if (!pages[e.page]) pages[e.page] = { views: 0, engagements: [], scrolls: [] };
        if (e.type === 'pageview')   pages[e.page].views++;
        if (e.type === 'engagement') pages[e.page].engagements.push(e.duration_s);
        if (e.type === 'scroll')     pages[e.page].scrolls.push(e.depth);
      });
      return pages;
    },

    /** admin용: 시간대별 방문 분포 (0~23시) */
    hourlyDist() {
      const dist = Array(24).fill(0);
      store.get()
        .filter(e => e.type === 'pageview')
        .forEach(e => { if (e.hour >= 0 && e.hour < 24) dist[e.hour]++; });
      return dist;
    },

    /** admin용: 최근 N일 일별 방문 */
    dailyDist(days = 14) {
      const map = {};
      const cutoff = Date.now() - days * 86400000;
      store.get()
        .filter(e => e.type === 'pageview' && e.ts >= cutoff)
        .forEach(e => {
          const d = new Date(e.ts).toISOString().slice(0, 10);
          map[d] = (map[d] || 0) + 1;
        });
      return map;
    },

    /** admin용: scan 제출 목록 */
    scanSubmits() {
      return store.get().filter(e => e.type === 'scan_submit');
    },

    /** admin용: 블로그 포스트별 평균 체류시간 (초) */
    blogStats() {
      const stats = {};
      store.get().forEach(e => {
        if (!e.page || !e.page.startsWith('blog-')) return;
        if (!stats[e.page]) stats[e.page] = { views: 0, durations: [], maxScrolls: [] };
        if (e.type === 'pageview')   stats[e.page].views++;
        if (e.type === 'engagement') stats[e.page].durations.push(e.duration_s);
        if (e.type === 'engagement') stats[e.page].maxScrolls.push(e.max_scroll || 0);
      });
      return Object.entries(stats).map(([page, s]) => ({
        page,
        views: s.views,
        avg_duration: s.durations.length
          ? Math.round(s.durations.reduce((a, b) => a + b, 0) / s.durations.length)
          : null,
        avg_scroll: s.maxScrolls.length
          ? Math.round(s.maxScrolls.reduce((a, b) => a + b, 0) / s.maxScrolls.length)
          : null,
      })).sort((a, b) => b.views - a.views);
    },
  };

  /* ── 초기화 ──────────────────────────────────────────── */
  function init() {
    loadGA4();
    trackPageView();
    trackBlogEngagement();
    trackScanForm();
    trackCTA();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
