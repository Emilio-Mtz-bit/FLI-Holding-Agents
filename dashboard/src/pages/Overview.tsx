import { useMemo } from 'react';
import { useAnalysisStore } from '@/store/analysis';
import MetricCard from '@/components/MetricCard';
import { compact, pct } from '@/lib/format';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { QualSignals } from '@/types/analysis';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sentimentLabel(score: number): string {
  if (score > 0.2) return 'Perspectiva Favorable';
  if (score < -0.2) return 'Perspectiva Desfavorable';
  return 'Perspectiva Neutral';
}

function splitFactor(factor: string): { title: string; desc: string } {
  const breakIdx = factor.search(/[,.]/);
  if (breakIdx > 0 && breakIdx <= 45) {
    return {
      title: factor.slice(0, breakIdx).trim().toUpperCase(),
      desc: factor.slice(breakIdx + 1).trim(),
    };
  }
  const words = factor.split(' ');
  return {
    title: words.slice(0, 3).join(' ').toUpperCase(),
    desc: words.slice(3).join(' '),
  };
}

function hasQualData(signals: QualSignals): boolean {
  return !!(
    signals.tipo_empresa ||
    signals.posicionamiento ||
    signals.fortalezas?.length ||
    signals.riesgos?.length ||
    signals.factores_crecimiento?.length ||
    signals.sentiment_score != null
  );
}

// ---------------------------------------------------------------------------
// Sub-sections
// ---------------------------------------------------------------------------

function SentimentGauge({ score }: { score: number }) {
  const normalized = (score + 1) / 2; // -1..1 → 0..1
  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Sentiment Score</p>
      <div className="text-4xl font-bold tabular-nums">{score.toFixed(2)}</div>
      <p className="text-sm text-muted-foreground">{sentimentLabel(score)} — Escala −1 a 1</p>
      <div className="relative h-2 rounded-full overflow-visible"
        style={{ background: 'linear-gradient(to right, #b91c1c, #ca8a04 50%, #15803d)' }}>
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-foreground border-2 border-background shadow"
          style={{ left: `calc(${normalized * 100}% - 8px)` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Negativo</span><span>Neutro</span><span>Positivo</span>
      </div>
    </div>
  );
}

function ContextBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t-2 border-yellow-700 pt-3 space-y-1">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="text-sm font-mono leading-relaxed">{value}</p>
    </div>
  );
}

function BulletList({ items, color }: { items: string[]; color: 'green' | 'red' }) {
  return (
    <ul className="space-y-1 mt-1">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm leading-relaxed">
          <span className={color === 'green' ? 'text-emerald-600' : 'text-rose-600'}>•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function FactorCard({ factor }: { factor: string }) {
  const { title, desc } = splitFactor(factor);
  return (
    <div className="border rounded-lg p-4 space-y-1 bg-card">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
        <p className="text-xs font-bold tracking-wide">{title}</p>
      </div>
      {desc && <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>}
    </div>
  );
}

function SenalesEstrategicas({ signals, sentiment }: { signals: QualSignals; sentiment: number }) {
  if (!hasQualData(signals)) return null;
  const score = signals.sentiment_score ?? sentiment;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Señales</h2>
        <p className="text-xl italic text-yellow-700">Estratégicas</p>
      </div>

      {/* Top row: sentiment + context */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardContent className="pt-6">
            <SentimentGauge score={score} />
          </CardContent>
        </Card>

        <div className="space-y-4">
          {signals.tipo_empresa && (
            <Card>
              <CardContent className="pt-4">
                <ContextBox label="Tipo de Empresa" value={signals.tipo_empresa} />
              </CardContent>
            </Card>
          )}
          {signals.posicionamiento && (
            <Card>
              <CardContent className="pt-4">
                <ContextBox label="Posicionamiento" value={signals.posicionamiento} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Fortalezas / Riesgos */}
      {((signals.fortalezas?.length ?? 0) > 0 || (signals.riesgos?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(signals.fortalezas?.length ?? 0) > 0 && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                  Fortalezas Identificadas
                </p>
                <BulletList items={signals.fortalezas!} color="green" />
              </CardContent>
            </Card>
          )}
          {(signals.riesgos?.length ?? 0) > 0 && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs font-bold uppercase tracking-wider text-rose-700">
                  Riesgos Identificados
                </p>
                <BulletList items={signals.riesgos!} color="red" />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Factores de crecimiento */}
      {(signals.factores_crecimiento?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Factores de Crecimiento
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {signals.factores_crecimiento!.map((f, i) => (
              <FactorCard key={i} factor={f} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

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

      {/* Qual signals */}
      <SenalesEstrategicas
        signals={result.qual.signals}
        sentiment={result.qual.sentiment}
      />
    </div>
  );
}
