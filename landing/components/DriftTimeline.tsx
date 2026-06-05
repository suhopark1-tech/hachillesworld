'use client';

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { HasDataPoint } from '@/lib/types';

interface Props {
  dataPoints: HasDataPoint[];
}

export default function DriftTimeline({ dataPoints }: Props) {
  if (dataPoints.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted text-sm">
        데이터 없음 — 먼저 스캔을 실행하세요
      </div>
    );
  }

  const chartData = dataPoints.map((p) => ({
    t: new Date(p.timestamp).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    score: p.has_score,
    level: p.level,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke="rgba(139,92,246,0.1)" strokeDasharray="4 4" />
        <XAxis dataKey="t" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            background: '#1a1a2e',
            border: '1px solid rgba(139,92,246,0.3)',
            borderRadius: 8,
            color: '#e2e8f0',
          }}
          formatter={(v: number) => [`${v}점`, 'HAS']}
        />
        <ReferenceLine y={80} stroke="#10b981" strokeDasharray="4 2" label={{ value: 'L2', fill: '#10b981', fontSize: 10 }} />
        <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '경고', fill: '#f59e0b', fontSize: 10 }} />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#8b5cf6"
          strokeWidth={2}
          dot={{ fill: '#8b5cf6', r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
