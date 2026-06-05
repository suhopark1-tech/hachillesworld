'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/dashboard', label: '에이전트 목록', icon: '⬡' },
  { href: '/dashboard/settings', label: '알림 설정', icon: '⚙' },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 bg-bg2 border-r border-[rgba(139,92,246,0.15)] min-h-screen px-4 py-6">
      <Link href="/dashboard" className="flex items-center gap-2 mb-8 no-underline">
        <span className="text-xl text-accent font-bold">⬡</span>
        <span className="text-sm font-semibold text-[#e2e8f0]">HAchillesWorld</span>
      </Link>
      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
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
      <div className="mt-auto pt-4 border-t border-[rgba(139,92,246,0.1)]">
        <p className="text-xs text-[#475569]">SDK v1.5</p>
        <p className="text-xs text-[#475569]">HAW Platform v2.0</p>
      </div>
    </aside>
  );
}
