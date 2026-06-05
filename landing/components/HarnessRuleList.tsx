'use client';

import { useState } from 'react';
import { approveHarnessRule } from '@/lib/api';
import type { HarnessRule } from '@/lib/types';

interface Props {
  rules: HarnessRule[];
  onUpdate?: () => void;
}

export default function HarnessRuleList({ rules, onUpdate }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [done, setDone] = useState<Set<string>>(new Set());

  async function handle(ruleId: string, approved: boolean) {
    setLoading(ruleId);
    try {
      await approveHarnessRule(ruleId, approved);
      setDone((prev) => new Set([...prev, ruleId]));
      onUpdate?.();
    } catch {
      // ignore — rule may already be processed
    } finally {
      setLoading(null);
    }
  }

  const pending = rules.filter((r) => !done.has(r.rule_id));

  if (pending.length === 0) {
    return (
      <p className="text-muted text-sm py-4 text-center">
        승인 대기 규칙 없음
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {pending.map((rule) => (
        <li
          key={rule.rule_id}
          className="rounded-lg border border-[rgba(139,92,246,0.2)] bg-bg3 p-4 text-sm"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <span
                className={`inline-block text-xs px-2 py-0.5 rounded-full mb-2 font-semibold ${
                  rule.severity === 'hard'
                    ? 'bg-red-900/40 text-red-300 border border-red-700/40'
                    : 'bg-amber-900/40 text-amber-300 border border-amber-700/40'
                }`}
              >
                {rule.severity.toUpperCase()}
              </span>
              <p className="text-[#c4b5fd] font-mono text-xs truncate">
                {rule.condition}
              </p>
              <p className="text-muted text-xs mt-1 truncate">{rule.action}</p>
              <p className="text-xs text-[#475569] mt-1">출처: {rule.source}</p>
            </div>
            <div className="flex flex-col gap-2 shrink-0">
              <button
                onClick={() => handle(rule.rule_id, true)}
                disabled={loading === rule.rule_id}
                className="px-3 py-1.5 rounded-md text-xs font-semibold bg-accent/20 text-[#c4b5fd] border border-accent/30 hover:bg-accent/30 disabled:opacity-50 transition-colors"
              >
                {loading === rule.rule_id ? '처리중…' : '승인'}
              </button>
              <button
                onClick={() => handle(rule.rule_id, false)}
                disabled={loading === rule.rule_id}
                className="px-3 py-1.5 rounded-md text-xs font-semibold bg-danger/10 text-red-400 border border-danger/30 hover:bg-danger/20 disabled:opacity-50 transition-colors"
              >
                거부
              </button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
