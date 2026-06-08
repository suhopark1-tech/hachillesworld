'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import type { ConsentRecord } from '@/lib/types';
import { CONSENT_STORAGE_KEY } from '@/lib/types';

const CONSENT_VERSION = 'v1.0';

interface OptionalConsents {
  anonymous_benchmark: boolean;
  product_improvement: boolean;
  marketing_contact: boolean;
}

function Toggle({
  checked,
  onChange,
  id,
}: {
  checked: boolean;
  onChange: () => void;
  id: string;
}) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.4)] ${
        checked
          ? 'bg-[#8b5cf6] border-[#8b5cf6]'
          : 'bg-[#1a1a2e] border-[rgba(139,92,246,0.3)]'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-[2px]'
        }`}
      />
    </button>
  );
}

const OPTIONAL_ITEMS: {
  key: keyof OptionalConsents;
  label: string;
  badge: string;
  desc: string;
  benefit?: string;
}[] = [
  {
    key: 'anonymous_benchmark',
    label: '익명 벤치마크 기여',
    badge: '선택 A',
    desc: '진단 수치를 완전 익명화하여 도메인별 업계 평균 산출에 기여합니다.',
    benefit: '동의 시: 업계 상위 몇% 즉시 확인 · 취약 지표 자동 하이라이트',
  },
  {
    key: 'product_improvement',
    label: '서비스 개선 분석',
    badge: '선택 B',
    desc: '페이지 방문·스캔 완료 등 이용 패턴을 분석해 UX를 개선합니다.',
  },
  {
    key: 'marketing_contact',
    label: 'HAchilles Weekly 수신',
    badge: '선택 C',
    desc: 'AI 에이전트 실패 패턴·신기능 인사이트를 주 1회 이메일로 받습니다.',
  },
];

export default function ConsentBanner() {
  const [show, setShow] = useState(false);
  const [opts, setOpts] = useState<OptionalConsents>({
    anonymous_benchmark: false,
    product_improvement: false,
    marketing_contact: false,
  });
  const pathname = usePathname();

  useEffect(() => {
    try {
      const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
      if (!raw) setShow(true);
    } catch {
      setShow(true);
    }
  }, []);

  if (!show || pathname === '/privacy') return null;

  function toggle(key: keyof OptionalConsents) {
    setOpts((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function handleAccept() {
    const record: ConsentRecord = {
      version: CONSENT_VERSION,
      required: true,
      anonymous_benchmark: opts.anonymous_benchmark,
      product_improvement: opts.product_improvement,
      marketing_contact: opts.marketing_contact,
      public_case_study: false,
      consented_at: new Date().toISOString(),
      region: 'KR',
    };
    try {
      localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(record));
    } catch {
      // storage unavailable — proceed anyway
    }
    setShow(false);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      aria-modal="true"
      role="dialog"
      aria-labelledby="consent-title"
    >
      <div className="w-full max-w-lg rounded-2xl bg-[#0f0f1a] border border-[rgba(139,92,246,0.3)] shadow-2xl overflow-hidden">

        {/* 헤더 */}
        <div className="px-6 pt-6 pb-4 border-b border-[rgba(139,92,246,0.15)]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg text-[#8b5cf6] font-bold">⬡</span>
            <span className="text-xs text-[#94a3b8]">HAchillesWorld</span>
          </div>
          <h2 id="consent-title" className="text-base font-bold text-[#e2e8f0]">
            서비스 이용을 위한 동의 안내
          </h2>
          <p className="text-[10px] text-[#475569] mt-0.5">
            HAW-CNS-001 {CONSENT_VERSION} · 2026년 7월 1일 시행
          </p>
        </div>

        <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">

          {/* 필수 동의 */}
          <div className="rounded-xl bg-[#1a1a2e] border border-[rgba(139,92,246,0.25)] p-4">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(139,92,246,0.2)] text-[#a78bfa] shrink-0">
                필수
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#e2e8f0]">
                  서비스 이용을 위한 개인정보 수집·이용
                </p>
                <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                  이메일, 에이전트 진단 수치 데이터(15개 지표), 접속 기록을 수집합니다.
                  원문 텍스트·소스 코드는 수집하지 않습니다.
                </p>
              </div>
              {/* 필수 항목 — 항상 체크됨 */}
              <div className="mt-0.5 shrink-0 flex items-center justify-center w-5 h-5 rounded bg-[#8b5cf6]">
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12">
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
            <p className="text-[10px] text-[#475569] mt-2 pl-[52px]">
              이 항목에 동의하지 않으시면 서비스를 이용하실 수 없습니다.
            </p>
          </div>

          {/* 선택 동의 */}
          <div>
            <p className="text-xs font-semibold text-[#94a3b8] mb-2">
              서비스 개선에 참여하시겠어요?{' '}
              <span className="font-normal text-[#475569]">(선택 · 거부해도 서비스 이용 가능)</span>
            </p>
            <div className="space-y-2">
              {OPTIONAL_ITEMS.map((item) => (
                <div
                  key={item.key}
                  className="flex items-start gap-3 rounded-lg border border-[rgba(139,92,246,0.15)] bg-[rgba(255,255,255,0.02)] px-4 py-3"
                >
                  <span className="mt-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(139,92,246,0.1)] text-[#7c6bae] shrink-0">
                    {item.badge}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#cbd5e1]">{item.label}</p>
                    <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">{item.desc}</p>
                    {item.benefit && opts[item.key] && (
                      <p className="text-[10px] text-[#8b5cf6] mt-1">→ {item.benefit}</p>
                    )}
                  </div>
                  <Toggle
                    id={`consent-${item.key}`}
                    checked={opts[item.key]}
                    onChange={() => toggle(item.key)}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* 안내 메모 */}
          <p className="text-[10px] text-[#475569] leading-relaxed">
            선택 동의는 언제든지{' '}
            <span className="text-[#94a3b8]">대시보드 설정 → 동의 관리</span>
            에서 변경하실 수 있습니다.
          </p>
        </div>

        {/* 푸터 */}
        <div className="px-6 py-4 border-t border-[rgba(139,92,246,0.15)] flex items-center justify-between gap-3">
          <Link
            href="/privacy"
            className="text-xs text-[#8b5cf6] hover:underline no-underline"
          >
            개인정보처리방침 전문 →
          </Link>
          <button
            type="button"
            onClick={handleAccept}
            className="px-5 py-2 rounded-lg bg-[#8b5cf6] hover:bg-[#7c3aed] text-white text-sm font-semibold transition-colors"
          >
            동의하고 시작하기
          </button>
        </div>

      </div>
    </div>
  );
}
