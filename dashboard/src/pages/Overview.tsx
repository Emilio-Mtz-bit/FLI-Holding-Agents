import { useMemo } from 'react';
import { useAnalysisStore } from '@/store/analysis';
import MetricCard from '@/components/MetricCard';
import { compact, pct } from '@/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

export default function Overview() {
  const result = useAnalysisStore((s) => s.result);
  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const { consolidado, por_sucursal, pct_mix_categoria } = result.quant.kpis;

  const pieData = useMemo(
    () =>
      Object.entries(pct_mix_categoria).map(([name, value]) => ({
        name,
        value: Math.round(value * 100),
      })),
    [pct_mix_categoria],
  );

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{result.period}</h1>
        <p className="text-muted-foreground text-sm mt-1">Consolidated performance</p>
      </div>

      {/* Hero metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Ingresos" value={compact(consolidado.ingresos_total)} />
        <MetricCard
          title="EBITDA"
          value={compact(consolidado.ebitda_total)}
          sub={pct(consolidado.margen_ebitda_global) + ' margin'}
          trend={consolidado.ebitda_total > 0 ? 'up' : 'down'}
        />
        <MetricCard
          title="Margen Bruto"
          value={pct(consolidado.margen_bruto_global)}
          trend="neutral"
        />
        <MetricCard
          title="Nómina / Ingresos"
          value={pct(consolidado.pct_nomina_ingresos_global)}
          trend={consolidado.pct_nomina_ingresos_global > 0.25 ? 'down' : 'up'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Branch table */}
        <Card>
          <CardHeader><CardTitle>Por Sucursal</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="text-left py-2">Sucursal</th>
                    <th className="text-right py-2">Ingresos</th>
                    <th className="text-right py-2">EBITDA</th>
                    <th className="text-right py-2">M. Bruto</th>
                  </tr>
                </thead>
                <tbody>
                  {por_sucursal.map((b) => (
                    <tr key={b.sucursal} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-2 font-medium">{b.sucursal}</td>
                      <td className="py-2 text-right">{compact(b.ingresos)}</td>
                      <td className={`py-2 text-right font-semibold ${b.ebitda < 0 ? 'text-rose-500' : 'text-emerald-600'}`}>
                        {compact(b.ebitda)}
                      </td>
                      <td className="py-2 text-right">{pct(b.margen_bruto)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Category mix donut */}
        <Card>
          <CardHeader><CardTitle>Category Mix</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${v}%`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Quant narrative */}
      <Card>
        <CardHeader><CardTitle>Executive Summary</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{result.quant.narrative}</p>
        </CardContent>
      </Card>
    </div>
  );
}
