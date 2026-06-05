'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback } from 'react';
import useSWR from 'swr';
import { swrFetcher } from '@/lib/api';
import HarnessRuleList from '@/components/HarnessRuleList';
import type { HarnessPendingResponse, HasTimeseriesResponse } from '@/lib/types';

// 차트 컴포넌트는 SSR 비활성화 (recharts DOM 의존성)
const HASGauge = dynamic(() => import('@/components/HASGauge'), { ssr: false });
const MetricsRadar = dynamic(() => import('@/components/MetricsRadar'), {
  ssr: false,
  loading: () => <div className="h-64 flex items-center justify-center text-muted text-sm">차트 로딩중…</div>,
});
const DriftTimeline = dynamic(() => import('@/components/DriftTimeline'), {
  ssr: false,
  loading: () => <div className="h-40 flex items-center justify-center text-muted text-sm">로딩중…</div>,
});

// 15개 지표 데모 데이터 (실제 스캔 결과 없을 때 사용)
const DEMO_METRICS = {
  wm: [
    { name: 'Prediction Error', value: 0.08, threshold: 0.15, unit: '', status: 'ok' as const, description: '' },
    { name: 'Calibration ECE', value: 0.07, threshold: 0.10, unit: '', status: 'ok' as const, description: '' },
    { name: 'Simulation Drift', value: 0.12, threshold: 0.15, unit: '', status: 'ok' as const, description: '' },
    { name: 'ODR',             value: 0.82, threshold: 0.80, unit: '', status: 'ok' as const, description: '' },
    { name: 'Planning Depth',  value: 6,    threshold: 5,    unit: 'steps', status: 'ok' as const, description: '' },
  ],
  agency: [
    { name: 'SCR',  value: 0.35, threshold: 0.30, unit: '', status: 'ok' as const, description: '' },
    { name: 'CA',   value: 0.78, threshold: 0.70, unit: '', status: 'ok' as const, description: '' },
    { name: 'GAR',  value: 0.88, threshold: 0.80, unit: '', status: 'ok' as const, description: '' },
    { name: 'AS',   value: 72,   threshold: 70,   unit: '%', status: 'ok' as const, description: '' },
    { name: 'Harness Cov.', value: 0.65, threshold: 0.60, unit: '', status: 'ok' as const, description: '' },
  ],
  ops: [
    { name: 'WMUL', value: 1.8, threshold: 2.0, unit: 's', status: 'ok' as const, description: '' },
    { name: 'IRT',  value: 4.2, threshold: 5.0, unit: 'min', status: 'ok' as const, description: '' },
    { name: 'HITL', value: 0.05, threshold: 0.10, unit: '', status: 'ok' as const, description: '' },
    { name: 'HR',   value: 0.02, threshold: 0.05, unit: '', status: 'ok' as const, description: '' },
    { name: 'SU',   value: 0.92, threshold: 0.90, unit: '', status: 'ok' as const, description: '' },
  ],
};

interface Props {
  agentId: string;
}

export default function AgentDetailClient({ agentId }: Props) {
  const hasFetcher = (url: string) => swrFetcher<HasTimeseriesResponse>(url);
  const harnessFetcher = (url: string) => swrFetcher<HarnessPendingResponse>(url);

  const { data: hasData, mutate: mutateHas } = useSWR(
    `/v1/agents/${agentId}/has`,
    hasFetcher,
    { refreshInterval: 5000, shouldRetryOnError: false },
  );

  const { data: harnessData, mutate: mutateHarness } = useSWR(
    `/v1/agents/${agentId}/harness/pending`,
    harnessFetcher,
    { refreshInterval: 10000, shouldRetryOnError: false },
  );

  const onHarnessUpdate = useCallback(() => {
    void mutateHarness();
  }, [mutateHarness]);

  const latest = hasData?.data_points.at(-1);
  const score  = latest?.has_score ?? 0;
  const level  = latest?.level ?? 'L1.0';

  return (
    <div className="p-6 md:p-8 max-w-5xl space-y-8">
      {/* 브레드크럼 */}
      <nav className="text-sm text-muted">
        <Link href="/dashboard" className="hover:text-[#c4b5fd] no-underline">
          에이전트 목록
        </Link>
        <span className="mx-2 text-[#334155]">/</span>
        <span className="text-[#e2e8f0] font-mono">{agentId}</span>
      </nav>

      {/* 헤더 — HAS 게이지 */}
      <section className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <HASGauge score={score} size="lg" />
          <div>
            <h1 className="text-xl font-bold text-[#e2e8f0] font-mono break-all">
              {agentId}
            </h1>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-accent/15 text-[#c4b5fd] border border-accent/30">
                {level}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${
                  score >= 80
                    ? 'bg-emerald-900/30 text-emerald-300 border-emerald-700/30'
                    : score >= 60
                    ? 'bg-amber-900/30 text-amber-300 border-amber-700/30'
                    : 'bg-red-900/30 text-red-300 border-red-700/30'
                }`}
              >
                {score >= 80 ? '정상' : score >= 60 ? '경고' : '위험'}
              </span>
            </div>
            <p className="text-xs text-muted mt-2">
              마지막 갱신: {latest?.timestamp
                ? new Date(latest.timestamp).toLocaleString('ko-KR')
                : '데이터 없음'}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* HAS 시계열 */}
        <section className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
          <h2 className="text-sm font-semibold text-[#c4b5fd] mb-4">
            HAS 시계열 <span className="text-xs text-muted font-normal">(5초 자동 갱신)</span>
          </h2>
          <DriftTimeline dataPoints={hasData?.data_points ?? []} />
          <p className="text-xs text-muted mt-2">
            총 {hasData?.data_points.length ?? 0}개 데이터포인트
          </p>
        </section>

        {/* 15개 지표 레이더 */}
        <section className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
          <h2 className="text-sm font-semibold text-[#c4b5fd] mb-4">
            15개 지표 레이더 차트
          </h2>
          <MetricsRadar
            wm={DEMO_METRICS.wm}
            agency={DEMO_METRICS.agency}
            ops={DEMO_METRICS.ops}
          />
          <p className="text-xs text-muted mt-2">
            WMQ 5 · ALM 5 · OHM 5 지표 종합
          </p>
        </section>
      </div>

      {/* 지표 상세 테이블 */}
      <section className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-[#c4b5fd] mb-4">지표 상세</h2>
        <MetricsTable />
      </section>

      {/* 하네스 규칙 승인 */}
      <section className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[#c4b5fd]">
            하네스 규칙 승인 대기
          </h2>
          <span className="text-xs text-muted">
            {harnessData?.rules.length ?? 0}건
          </span>
        </div>
        <HarnessRuleList
          rules={harnessData?.rules ?? []}
          onUpdate={onHarnessUpdate}
        />
      </section>
    </div>
  );
}

function MetricsTable() {
  const all = [
    ...DEMO_METRICS.wm.map((m) => ({ ...m, category: 'WMQ' })),
    ...DEMO_METRICS.agency.map((m) => ({ ...m, category: 'ALM' })),
    ...DEMO_METRICS.ops.map((m) => ({ ...m, category: 'OHM' })),
  ];

  return (
    <table className="w-full text-xs text-left">
      <thead>
        <tr className="border-b border-[rgba(139,92,246,0.15)]">
          {['범주', '지표', '값', '기준', '상태'].map((h) => (
            <th key={h} className="pb-2 pr-4 text-muted font-semibold">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {all.map((m) => (
          <tr key={m.name} className="border-b border-[rgba(139,92,246,0.08)]">
            <td className="py-1.5 pr-4 text-[#475569] font-mono">{m.category}</td>
            <td className="py-1.5 pr-4 text-[#e2e8f0]">{m.name}</td>
            <td className="py-1.5 pr-4 font-mono text-accent2">
              {typeof m.value === 'number' ? m.value.toFixed(2) : m.value}
              {m.unit && <span className="text-muted ml-1">{m.unit}</span>}
            </td>
            <td className="py-1.5 pr-4 font-mono text-muted">{m.threshold}</td>
            <td className="py-1.5">
              <span
                className={`px-2 py-0.5 rounded-full font-semibold ${
                  m.status === 'ok'
                    ? 'bg-emerald-900/30 text-emerald-300'
                    : m.status === 'warning'
                    ? 'bg-amber-900/30 text-amber-300'
                    : 'bg-red-900/30 text-red-300'
                }`}
              >
                {m.status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
