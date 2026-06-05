'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import useSWR from 'swr';
import { swrFetcher } from '@/lib/api';
import type { HasTimeseriesResponse } from '@/lib/types';

const HASGauge = dynamic(() => import('@/components/HASGauge'), { ssr: false });

// 데모 그룹 에이전트 (실제 운영 시 /v1/groups 엔드포인트로 대체)
const GROUP_AGENTS = [
  { agent_id: 'supply-chain-agent',     name: 'Supply Chain Agent',     domain: 'digital'    },
  { agent_id: 'customer-service-agent', name: 'Customer Service Agent', domain: 'social'     },
  { agent_id: 'research-agent',         name: 'Research Agent',         domain: 'scientific' },
];

// 데모 의존성 그래프 (Supply Chain → Customer Service → Research)
const DEMO_EDGES = [
  { from: 'Supply Chain Agent',     to: 'Customer Service Agent', weight: 0.9 },
  { from: 'Customer Service Agent', to: 'Research Agent',         weight: 0.7 },
];

function useAgentScore(agent_id: string) {
  const { data } = useSWR<HasTimeseriesResponse>(
    `/v1/agents/${agent_id}/has`,
    (url: string) => swrFetcher<HasTimeseriesResponse>(url),
    { refreshInterval: 5000, shouldRetryOnError: false },
  );
  const latest = data?.data_points.at(-1);
  return { score: latest?.has_score ?? 0, level: latest?.level ?? '—' };
}

function AgentRankRow({
  rank,
  name,
  agent_id,
  isWeakest,
}: {
  rank: number;
  name: string;
  agent_id: string;
  isWeakest: boolean;
}) {
  const { score, level } = useAgentScore(agent_id);
  const statusColor =
    score === 0
      ? 'text-muted'
      : score < 60
      ? 'text-red-400'
      : score < 80
      ? 'text-amber-400'
      : 'text-emerald-400';

  return (
    <Link
      href={`/dashboard/${agent_id}`}
      className="flex items-center gap-4 px-4 py-3 rounded-lg hover:bg-white/5 transition-colors group"
    >
      <span className="text-muted text-sm w-5 text-right shrink-0">#{rank}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#e2e8f0] group-hover:text-[#c4b5fd] transition-colors truncate">
          {name}
        </p>
        {level !== '—' && (
          <p className="text-xs text-muted font-mono mt-0.5">{level}</p>
        )}
      </div>
      {isWeakest && (
        <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/40 text-red-300 border border-red-700/40 shrink-0">
          최약
        </span>
      )}
      <span className={`text-sm font-bold font-mono shrink-0 ${statusColor}`}>
        {score > 0 ? `${score.toFixed(1)}` : '—'}
      </span>
    </Link>
  );
}

function DependencyGraph() {
  return (
    <div className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
      <h3 className="text-sm font-semibold text-[#e2e8f0] mb-4">의존성 그래프 (DAG)</h3>
      <div className="space-y-2">
        {DEMO_EDGES.map((edge, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="text-[#e2e8f0] text-xs bg-white/5 px-2 py-1 rounded font-mono">
              {edge.from}
            </span>
            <div className="flex items-center gap-1 text-muted">
              <span className="text-xs">──</span>
              <span className="text-xs text-accent2 font-mono">{edge.weight}</span>
              <span className="text-xs">──▶</span>
            </div>
            <span className="text-[#e2e8f0] text-xs bg-white/5 px-2 py-1 rounded font-mono">
              {edge.to}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted mt-3">
        * 사이클 자동 탐지 활성화 — 순환 의존성 추가 시 거부됨
      </p>
    </div>
  );
}

export default function GroupDashboardPage() {
  // 모든 에이전트 점수 수집
  const scores = GROUP_AGENTS.map((a) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const { score } = useAgentScore(a.agent_id);
    return { ...a, score };
  });

  const validScores = scores.filter((s) => s.score > 0);
  const groupHas =
    validScores.length > 0
      ? validScores.reduce((sum, s) => sum + s.score, 0) / validScores.length
      : 0;

  const sortedByScore = [...scores].sort((a, b) => b.score - a.score);
  const weakest = sortedByScore.at(-1);

  // 동시 드리프트 시뮬레이션 (실제 구현 시 CrossAgentDriftCorrelator 결과 사용)
  const simulDriftDetected = validScores.length >= 2 && groupHas > 0 && groupHas < 60;

  const groupLevel =
    validScores.length === 0
      ? '—'
      : groupHas >= 80
      ? 'L3'
      : groupHas >= 60
      ? 'L2'
      : 'L1';

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/dashboard" className="text-muted text-sm hover:text-[#c4b5fd] transition-colors">
              ← 에이전트 목록
            </Link>
          </div>
          <h1 className="text-xl font-bold text-[#e2e8f0]">그룹 HAS 대시보드</h1>
          <p className="text-sm text-muted mt-0.5">
            {GROUP_AGENTS.length}개 에이전트 · 실시간 집계
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted uppercase tracking-wide">그룹 레벨</p>
          <p className="text-lg font-bold text-accent2 font-mono">{groupLevel}</p>
        </div>
      </div>

      {/* 동시 드리프트 경보 */}
      {simulDriftDetected && (
        <div className="rounded-xl border border-red-700/40 bg-red-900/20 px-5 py-3 flex items-start gap-3">
          <span className="text-red-400 text-lg mt-0.5">⚠</span>
          <div>
            <p className="text-sm font-semibold text-red-300">동시 드리프트 감지</p>
            <p className="text-xs text-red-400/80 mt-0.5">
              다수 에이전트에서 동시에 성능 저하가 감지되었습니다.
              환경 레벨 변화 또는 공통 데이터 소스 문제일 수 있습니다.
              개별 에이전트 → Replay Debugger를 통해 근본 원인을 분석하세요.
            </p>
          </div>
        </div>
      )}

      {/* 그룹 HAS 게이지 + 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-6 flex flex-col items-center gap-3">
          <p className="text-sm text-muted uppercase tracking-wide">그룹 HAS</p>
          <HASGauge score={groupHas} size="lg" showLabel />
          {groupHas === 0 && (
            <p className="text-xs text-muted">스캔 데이터 대기 중…</p>
          )}
        </div>

        <div className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5 space-y-4">
          <h3 className="text-sm font-semibold text-[#e2e8f0]">그룹 요약</h3>
          <dl className="space-y-2">
            <div className="flex justify-between items-center">
              <dt className="text-xs text-muted">총 에이전트</dt>
              <dd className="text-sm font-mono text-[#e2e8f0]">{GROUP_AGENTS.length}개</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-xs text-muted">데이터 수집됨</dt>
              <dd className="text-sm font-mono text-[#e2e8f0]">{validScores.length}개</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-xs text-muted">최저 점수 (Weakest Link)</dt>
              <dd className="text-sm font-mono text-red-400 truncate max-w-[160px]">
                {weakest?.score && weakest.score > 0 ? weakest.name : '—'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-xs text-muted">동시 드리프트</dt>
              <dd className={`text-sm font-mono ${simulDriftDetected ? 'text-red-400' : 'text-emerald-400'}`}>
                {simulDriftDetected ? '감지됨 ⚠' : '정상'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-xs text-muted">의존성 엣지</dt>
              <dd className="text-sm font-mono text-[#e2e8f0]">{DEMO_EDGES.length}개</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* 에이전트 순위 */}
      <div className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
        <h3 className="text-sm font-semibold text-[#e2e8f0] mb-3">에이전트 순위 (HAS 높은 순)</h3>
        <div className="space-y-1">
          {sortedByScore.map((agent, i) => (
            <AgentRankRow
              key={agent.agent_id}
              rank={i + 1}
              name={agent.name}
              agent_id={agent.agent_id}
              isWeakest={agent.agent_id === weakest?.agent_id && (weakest?.score ?? 0) > 0}
            />
          ))}
        </div>
      </div>

      {/* 의존성 그래프 */}
      <DependencyGraph />

      {/* 드리프트 전파 위험도 테이블 */}
      {weakest && weakest.score > 0 && (
        <div className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-3">
            드리프트 전파 위험도 — Weakest: {weakest.name}
          </h3>
          <div className="space-y-2">
            {DEMO_EDGES
              .filter((e) => e.from === weakest.name)
              .map((edge, i) => {
                const risk = edge.weight * 0.8;
                const pct = Math.round(risk * 100);
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs text-muted w-40 truncate">{edge.to}</span>
                    <div className="flex-1 bg-white/10 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-[#e2e8f0] w-10 text-right">
                      {pct}%
                    </span>
                  </div>
                );
              })}
            {DEMO_EDGES.every((e) => e.from !== weakest.name) && (
              <p className="text-xs text-muted">
                {weakest.name}에서 출발하는 의존성 엣지가 없습니다.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
