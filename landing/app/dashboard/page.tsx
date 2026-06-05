'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import useSWR from 'swr';
import { swrFetcher } from '@/lib/api';
import type { HasTimeseriesResponse } from '@/lib/types';

const HASGauge = dynamic(() => import('@/components/HASGauge'), { ssr: false });

// 데모 에이전트 목록 (실제 운영 시 /v1/agents 엔드포인트로 대체)
const DEMO_AGENTS = [
  { agent_id: 'supply-chain-agent',    name: 'Supply Chain Agent',    domain: 'digital'     },
  { agent_id: 'customer-service-agent', name: 'Customer Service Agent', domain: 'social'     },
  { agent_id: 'research-agent',        name: 'Research Agent',         domain: 'scientific'  },
];

function AgentCard({ agent_id, name, domain }: (typeof DEMO_AGENTS)[0]) {
  const hasFetcher = (url: string) => swrFetcher<HasTimeseriesResponse>(url);
  const { data } = useSWR(
    `/v1/agents/${agent_id}/has`,
    hasFetcher,
    { refreshInterval: 5000, shouldRetryOnError: false },
  );

  const latest = data?.data_points.at(-1);
  const score = latest?.has_score ?? 0;
  const level = latest?.level ?? '—';
  const isCritical = score > 0 && score < 60;
  const isWarning  = score >= 60 && score < 80;

  return (
    <Link
      href={`/dashboard/${agent_id}`}
      className="block rounded-xl border bg-surface p-5 no-underline hover:border-accent/50 transition-colors group"
      style={{ borderColor: isCritical ? 'rgba(239,68,68,0.4)' : 'rgba(139,92,246,0.2)' }}
    >
      {isCritical && (
        <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-red-900/40 text-red-300 border border-red-700/40 mb-3 font-semibold">
          ⚠ 위험 — 즉시 조치
        </span>
      )}
      {isWarning && (
        <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-amber-900/30 text-amber-300 border border-amber-700/30 mb-3 font-semibold">
          경고
        </span>
      )}

      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="font-semibold text-[#e2e8f0] group-hover:text-[#c4b5fd] transition-colors">
            {name}
          </h3>
          <p className="text-xs text-muted mt-0.5 uppercase tracking-wide">{domain}</p>
          {level !== '—' && (
            <p className="text-xs text-accent2 mt-1 font-mono">{level}</p>
          )}
        </div>
        <HASGauge score={score} size="sm" showLabel={false} />
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const critical = DEMO_AGENTS.filter((a) => {
    // ordering: just show all, critical ones will self-sort via the card
    return a;
  });

  return (
    <div className="p-6 md:p-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#e2e8f0]">에이전트 모니터링</h1>
        <p className="text-muted text-sm mt-1">
          HAS 점수가 5초마다 자동 갱신됩니다.{' '}
          <span className="text-red-400">빨간 카드</span>는 즉시 조치가 필요한 에이전트입니다.
        </p>
      </div>

      {/* Agent grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {critical.map((agent) => (
          <AgentCard key={agent.agent_id} {...agent} />
        ))}
      </div>

      {/* Quick actions */}
      <div className="mt-8 rounded-xl border border-[rgba(139,92,246,0.2)] bg-bg2 p-5">
        <h2 className="text-sm font-semibold text-[#c4b5fd] mb-3">빠른 스캔</h2>
        <p className="text-xs text-muted mb-4">
          에이전트 ID와 도메인을 입력하면 즉시 HAW 진단을 실행합니다.
        </p>
        <QuickScanForm />
      </div>
    </div>
  );
}

function QuickScanForm() {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const fd = new FormData(e.currentTarget);
        const id = fd.get('agent_id') as string;
        if (id) window.location.href = `/dashboard/${id}`;
      }}
      className="flex flex-col sm:flex-row gap-2"
    >
      <input
        name="agent_id"
        placeholder="agent_id (예: my-agent)"
        required
        className="flex-1 rounded-lg px-3 py-2 bg-bg3 border border-[rgba(139,92,246,0.25)] text-[#e2e8f0] text-sm placeholder-[#475569] focus:outline-none focus:border-accent"
      />
      <button
        type="submit"
        className="px-4 py-2 rounded-lg bg-accent/20 text-[#c4b5fd] border border-accent/30 hover:bg-accent/30 text-sm font-semibold transition-colors"
      >
        상세 보기 →
      </button>
    </form>
  );
}
