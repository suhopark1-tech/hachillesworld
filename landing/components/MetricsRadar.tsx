'use client';

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { MetricScore } from '@/lib/types';

interface Props {
  wm: MetricScore[];
  agency: MetricScore[];
  ops: MetricScore[];
}

function toRadarData(metrics: MetricScore[]): { metric: string; value: number }[] {
  return metrics.map((m) => ({
    metric: m.name.replace(' Rate', '').replace(' Error', ''),
    value: Math.round(
      m.status === 'ok' ? 80 + Math.random() * 20
      : m.status === 'warning' ? 50 + Math.random() * 30
      : 20 + Math.random() * 30,
    ),
  }));
}

export default function MetricsRadar({ wm, agency, ops }: Props) {
  const data = [...toRadarData(wm), ...toRadarData(agency), ...toRadarData(ops)];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
        <PolarGrid stroke="rgba(139,92,246,0.2)" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fill: '#94a3b8', fontSize: 10 }}
        />
        <Radar
          name="지표"
          dataKey="value"
          stroke="#8b5cf6"
          fill="#8b5cf6"
          fillOpacity={0.25}
        />
        <Tooltip
          contentStyle={{
            background: '#1a1a2e',
            border: '1px solid rgba(139,92,246,0.3)',
            borderRadius: 8,
            color: '#e2e8f0',
          }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
