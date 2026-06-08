'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

/* ── 내부 Next.js 라우트 ─────────────────────────── */
const NAV_INTERNAL = [
  { href: '/dashboard',          label: '에이전트 목록', icon: '⬡' },
  { href: '/dashboard/settings', label: '알림 설정',     icon: '⚙' },
  { href: '/privacy',            label: '개인정보처리방침', icon: '🔒' },
];

/* ── 정적 HTML 페이지 ────────────────────────────── */
const NAV_SECTIONS = [
  {
    group: '플랫폼',
    items: [
      { href: '/index.html',    label: '홈 (한국어)',   icon: '🏠' },
      { href: '/index-en.html', label: 'Home (EN)',     icon: '🌐' },
      { href: '/scan.html',     label: '스캔 / 진단',   icon: '🔬' },
      { href: '/report.html',   label: '진단 보고서',   icon: '📊' },
    ],
  },
  {
    group: '운영 · 최적화',
    items: [
      { href: '/operate.html',          label: 'Operate',         icon: '🔧' },
      { href: '/optimize.html',         label: '최적화',           icon: '⚡' },
      { href: '/optimize_report.html',  label: '최적화 보고서',    icon: '📈' },
      { href: '/cert.html',             label: 'L3 인증',          icon: '🏅' },
      { href: '/admin.html',            label: '어드민',           icon: '🛡️' },
    ],
  },
  {
    group: '블로그',
    items: [
      { href: '/blog.html',                       label: '블로그 홈',        icon: '✍️' },
      { href: '/blog-world-model.html',           label: 'World Model이란?', icon: '🧠' },
      { href: '/blog-mcts-planning-depth.html',   label: 'MCTS & Planning', icon: '🌳' },
      { href: '/blog-why-world-model.html',       label: '왜 WM인가',        icon: '💡' },
      { href: '/blog-arxiv-paper.html',           label: 'arXiv 논문',       icon: '📄' },
      { href: '/blog-recognition-certification.html', label: '인증 안내',    icon: '🎖️' },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 bg-bg2 border-r border-[rgba(139,92,246,0.15)] min-h-screen px-4 py-6 overflow-y-auto">
      {/* 로고 */}
      <Link href="/dashboard" className="flex items-center gap-2 mb-6 no-underline">
        <span className="text-xl text-accent font-bold">⬡</span>
        <span className="text-sm font-semibold text-[#e2e8f0]">HAchillesWorld</span>
      </Link>

      {/* 대시보드 내부 라우트 */}
      <nav className="flex flex-col gap-1 mb-4">
        {NAV_INTERNAL.map((item) => {
          const active = path === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm no-underline transition-colors ${
                active
                  ? 'bg-accent/20 text-[#c4b5fd] font-semibold'
                  : 'text-muted hover:text-[#e2e8f0] hover:bg-white/5'
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* 구분선 */}
      <div className="border-t border-[rgba(139,92,246,0.1)] mb-4" />

      {/* 섹션별 정적 페이지 */}
      {NAV_SECTIONS.map((section) => (
        <div key={section.group} className="mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] px-3 mb-1">
            {section.group}
          </p>
          <div className="flex flex-col gap-0.5">
            {section.items.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs no-underline text-muted hover:text-[#e2e8f0] hover:bg-white/5 transition-colors"
              >
                <span className="text-sm">{item.icon}</span>
                {item.label}
              </a>
            ))}
          </div>
        </div>
      ))}

      {/* 하단 버전 정보 */}
      <div className="mt-auto pt-4 border-t border-[rgba(139,92,246,0.1)]">
        <p className="text-[10px] text-[#475569]">SDK v2.1 · Platform v2.1</p>
      </div>
    </aside>
  );
}
