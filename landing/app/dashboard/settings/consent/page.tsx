'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { ConsentRecord } from '@/lib/types';
import { CONSENT_STORAGE_KEY } from '@/lib/types';

const CONSENT_VERSION = 'v1.0';

const OPTIONAL_ITEMS: {
  key: keyof Pick<
    ConsentRecord,
    'anonymous_benchmark' | 'product_improvement' | 'marketing_contact' | 'public_case_study'
  >;
  label: string;
  badge: string;
  desc: string;
  withdrawalNote?: string;
}[] = [
  {
    key: 'anonymous_benchmark',
    label: '익명 벤치마크 기여',
    badge: '선택 A',
    desc: '진단 수치를 완전 익명화하여 도메인별 업계 평균 산출에 기여합니다. 동의 시 "업계 상위 몇%" 비교 데이터를 즉시 제공받으실 수 있습니다.',
    withdrawalNote:
      '철회 시 이후 진단 결과는 집계에서 제외됩니다. 이미 집계된 익명 통계값은 재식별이 불가능하여 소급 삭제할 수 없습니다.',
  },
  {
    key: 'product_improvement',
    label: '서비스 개선 분석',
    badge: '선택 B',
    desc: '페이지 방문·스캔 완료 등 서비스 이용 패턴을 분석하여 UI/UX를 개선합니다. 수집 데이터는 1년 보관 후 자동 파기됩니다.',
  },
  {
    key: 'marketing_contact',
    label: 'HAchilles Weekly 수신',
    badge: '선택 C',
    desc: 'AI 에이전트 실패 패턴·신기능 인사이트를 주 1회 이메일로 받습니다. 월 최대 8회를 초과하지 않습니다.',
    withdrawalNote:
      '수신 거부는 이메일 하단 링크 또는 이 페이지에서 즉시 처리됩니다.',
  },
  {
    key: 'public_case_study',
    label: '공개 케이스스터디 활용',
    badge: '선택 D',
    desc: '에이전트 개선 사례를 공식 케이스스터디로 게재하는 것에 동의합니다. HAS 점수가 유의미하게 향상된 고객에게 별도 제안 후 개별 동의를 받습니다.',
    withdrawalNote:
      '게재 후 철회 요청 시 14일 내 삭제 처리됩니다.',
  },
];

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.4)] disabled:opacity-40 disabled:cursor-not-allowed ${
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

export default function ConsentSettingsPage() {
  const [consent, setConsent] = useState<ConsentRecord | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
      if (raw) {
        setConsent(JSON.parse(raw) as ConsentRecord);
      } else {
        // 동의 기록 없음 — 기본값 설정
        const defaults: ConsentRecord = {
          version: CONSENT_VERSION,
          required: true,
          anonymous_benchmark: false,
          product_improvement: false,
          marketing_contact: false,
          public_case_study: false,
          consented_at: new Date().toISOString(),
          region: 'KR',
        };
        setConsent(defaults);
      }
    } catch {
      // ignore
    }
  }, []);

  function toggle(
    key: keyof Pick<
      ConsentRecord,
      'anonymous_benchmark' | 'product_improvement' | 'marketing_contact' | 'public_case_study'
    >,
  ) {
    setConsent((prev) => {
      if (!prev) return prev;
      return { ...prev, [key]: !prev[key] };
    });
    setDirty(true);
    setSaved(false);
  }

  function handleSave() {
    if (!consent) return;
    const updated: ConsentRecord = {
      ...consent,
      consented_at: new Date().toISOString(),
    };
    try {
      localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // storage unavailable
    }
    setConsent(updated);
    setDirty(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  const formattedDate = consent?.consented_at
    ? new Date(consent.consented_at).toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';

  return (
    <div className="p-6 md:p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-[#e2e8f0] mb-2">동의 관리</h1>
      <p className="text-[#94a3b8] text-sm mb-1">
        개인정보 수집·이용에 관한 동의 현황을 확인하고 선택 동의를 변경합니다.
      </p>
      <p className="text-xs text-[#475569] mb-8">
        문서: HAW-CNS-001 {CONSENT_VERSION} ·{' '}
        <Link href="/privacy" className="text-[#8b5cf6] hover:underline">
          개인정보처리방침 전문
        </Link>
      </p>

      {/* 필수 동의 현황 */}
      <div className="mb-6 rounded-xl border border-[rgba(139,92,246,0.2)] bg-[#0f0f1a] p-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] mb-3">
          필수 동의 현황
        </p>
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex items-center justify-center w-5 h-5 rounded bg-[#8b5cf6] shrink-0">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12">
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-[#e2e8f0]">
              서비스 이용을 위한 개인정보 수집·이용
            </p>
            <p className="text-xs text-[#64748b] mt-1 leading-relaxed">
              이메일, 에이전트 진단 수치 데이터(15개 지표), 접속 기록 · 법적 근거: 계약 이행
            </p>
            <p className="text-[10px] text-[#475569] mt-1">
              서비스 이용의 필수 조건으로 변경할 수 없습니다.{' '}
              <span className="text-[#94a3b8]">
                (탈퇴 시 30일 내 파기 — <Link href="/privacy#s6" className="text-[#8b5cf6] hover:underline">파기 절차 안내</Link>)
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* 선택 동의 */}
      <div className="mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] mb-3">
          선택 동의
        </p>
        <div className="space-y-3">
          {OPTIONAL_ITEMS.map((item) => {
            const checked = consent ? consent[item.key] : false;
            return (
              <div
                key={item.key}
                className="rounded-xl border border-[rgba(139,92,246,0.15)] bg-[#0f0f1a] p-4"
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(139,92,246,0.1)] text-[#7c6bae]">
                      {item.badge}
                    </span>
                    <span className="text-sm font-semibold text-[#cbd5e1]">{item.label}</span>
                  </div>
                  <Toggle checked={checked} onChange={() => toggle(item.key)} />
                </div>
                <p className="text-xs text-[#64748b] leading-relaxed">{item.desc}</p>
                {item.withdrawalNote && !checked && consent?.[item.key] === false && (
                  <p className="text-[10px] text-[#475569] mt-2 leading-relaxed">
                    ⚠ {item.withdrawalNote}
                  </p>
                )}
                {item.withdrawalNote && !checked && dirty && (
                  <p className="text-[10px] text-amber-500/70 mt-2 leading-relaxed">
                    ⚠ {item.withdrawalNote}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 저장 */}
      <div className="flex items-center gap-4 mb-8">
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty}
          className="px-6 py-2.5 rounded-lg bg-[rgba(139,92,246,0.15)] text-[#c4b5fd] border border-[rgba(139,92,246,0.3)] hover:bg-[rgba(139,92,246,0.25)] font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          변경 저장
        </button>
        {saved && (
          <span className="text-sm text-emerald-400 font-semibold">✓ 저장되었습니다</span>
        )}
      </div>

      {/* 동의 이력 */}
      <div className="rounded-xl border border-[rgba(139,92,246,0.15)] bg-[#0f0f1a] p-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] mb-3">
          동의 이력
        </p>
        <dl className="text-xs space-y-1.5">
          {[
            ['동의 문서 버전', consent?.version ?? '—'],
            ['최종 동의·변경 일시', formattedDate],
            ['이용 지역', consent?.region ?? '—'],
          ].map(([label, value]) => (
            <div key={label} className="flex gap-4">
              <dt className="w-36 text-[#64748b] shrink-0">{label}</dt>
              <dd className="text-[#94a3b8]">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* 권리 행사 안내 */}
      <div className="mt-6 rounded-xl border border-[rgba(239,68,68,0.15)] bg-[rgba(239,68,68,0.03)] p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#7f1d1d] mb-2">
          개인정보 권리 행사
        </p>
        <p className="text-xs text-[#94a3b8] leading-relaxed">
          열람·정정·삭제·이동·처리정지 등 권리 행사:{' '}
          <a
            href="mailto:privacy@hachillesworld.ai"
            className="text-[#8b5cf6] hover:underline"
          >
            privacy@hachillesworld.ai
          </a>
          {' '}(10일 이내 처리) ·{' '}
          <Link href="/privacy#s7" className="text-[#8b5cf6] hover:underline">
            권리 행사 상세 안내
          </Link>
        </p>
      </div>
    </div>
  );
}
