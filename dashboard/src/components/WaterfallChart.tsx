import { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { compact } from '@/lib/format';
import type { ScenarioCard } from '@/types/analysis';

interface Props {
  baseEbitda: number;
  scenarios: ScenarioCard[];
}

interface WaterfallEntry {
  name: string;
  base: number;
  delta: number;
  total: number;
  isNeg?: boolean;
}

export default function WaterfallChart({ baseEbitda, scenarios }: Props) {
  const data: WaterfallEntry[] = useMemo(() => {
    const entries: WaterfallEntry[] = [
      { name: 'Base', base: 0, delta: baseEbitda, total: baseEbitda },
    ];
    let running = baseEbitda;
    scenarios.filter((s) => s.active).forEach((s) => {
      const start = running;
      const delta = s.impact;
      running += delta;
      entries.push({
        name: s.label.length > 20 ? s.label.slice(0, 18) + '…' : s.label,
        base: delta < 0 ? running : start,
        delta: Math.abs(delta),
        total: running,
        isNeg: delta < 0,
      });
    });
    entries.push({ name: 'Combined', base: 0, delta: running, total: running });
    return entries;
  }, [baseEbitda, scenarios]);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
        <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
        <YAxis tickFormatter={(v) => compact(v)} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: any) => {
            if (typeof value === 'number') {
              return [compact(value), 'Impact'];
            }
            return '';
          }}
          labelFormatter={(label: any) => String(label)}
        />
        <ReferenceLine y={0} stroke="hsl(var(--border))" />
        <Bar dataKey="base" stackId="stack" fill="transparent" />
        <Bar dataKey="delta" stackId="stack" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => {
            const isBase = i === 0;
            const isCombined = i === data.length - 1;
            const isNeg = !!entry.isNeg;
            const color =
              isBase || isCombined
                ? 'hsl(var(--primary))'
                : isNeg
                ? '#f43f5e'
                : '#10b981';
            return <Cell key={i} fill={color} />;
          })}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  );
}
