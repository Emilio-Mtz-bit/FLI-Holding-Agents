import { useState, useMemo } from 'react';
import { useAnalysisStore } from '@/store/analysis';
import ScenarioCard from '@/components/ScenarioCard';
import WaterfallChart from '@/components/WaterfallChart';
import BreakEvenCard from '@/components/BreakEvenCard';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { compact } from '@/lib/format';
import { computeImpact, breakEvenTicket } from '@/lib/scenarios';
import type { ScenarioCard as ScenarioCardType, ScenarioType } from '@/types/analysis';
import { Plus } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

const SCENARIO_TYPES: { value: ScenarioType; label: string }[] = [
  { value: 'costo_insumo', label: 'Costo insumo (+%)' },
  { value: 'cierre_sucursal', label: 'Cierre sucursal' },
  { value: 'shift_mix', label: 'Mix shift (cat → cat)' },
  { value: 'reduccion_nomina', label: 'Reducción nómina' },
  { value: 'incremento_salarial', label: 'Incremento salarial' },
];

export default function WhatIfLab() {
  const { result, scenarios, addScenario, breakEvenTarget, setBreakEvenTarget } = useAnalysisStore();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [newType, setNewType] = useState<ScenarioType>('costo_insumo');
  const [newParams, setNewParams] = useState<ScenarioCardType['params']>({ delta_pct: 0.1 });

  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const kpis = result.quant.kpis;
  const baseEbitda = kpis.consolidado.ebitda_total;
  const branches = kpis.por_sucursal.map((b) => b.sucursal);
  const categories = kpis.por_categoria.map((c) => c.categoria);

  const combinedEbitda = useMemo(
    () => baseEbitda + scenarios.filter((s) => s.active).reduce((sum, s) => sum + s.impact, 0),
    [baseEbitda, scenarios],
  );

  const breakEvenResults = useMemo(
    () => branches.map((s) => breakEvenTicket(kpis, s, breakEvenTarget)),
    [kpis, branches, breakEvenTarget],
  );

  const handleAddScenario = () => {
    const draft: ScenarioCardType = {
      id: uuidv4(),
      type: newType,
      label: SCENARIO_TYPES.find((t) => t.value === newType)!.label,
      params: {
        delta_pct: newParams.delta_pct,
        sucursal: newParams.sucursal ?? branches[0],
        categoria: newParams.categoria ?? categories[0],
        cat_from: newParams.cat_from ?? categories[0],
        cat_to: newParams.cat_to ?? (categories[1] ?? categories[0]),
      },
      active: true,
      impact: 0,
    };
    draft.impact = computeImpact(kpis, draft);
    addScenario(draft);
    setDrawerOpen(false);
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">What-If Lab</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Combined EBITDA:{' '}
            <span className={`font-semibold ${combinedEbitda < baseEbitda ? 'text-rose-500' : 'text-emerald-600'}`}>
              {compact(combinedEbitda)}
            </span>
            <span className="text-muted-foreground ml-2">(base: {compact(baseEbitda)})</span>
          </p>
        </div>
        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetTrigger>
            <Button variant="outline" size="sm">
              <Plus size={14} className="mr-1" /> Add Scenario
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>New Custom Scenario</SheetTitle>
            </SheetHeader>
            <div className="space-y-4 mt-6">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={newType} onValueChange={(v) => setNewType(v as ScenarioType)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SCENARIO_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {(newType === 'cierre_sucursal' || newType === 'reduccion_nomina') && (
                <div className="space-y-2">
                  <Label>Sucursal</Label>
                  <Select
                    value={newParams.sucursal ?? branches[0]}
                    onValueChange={(v) => {
                      setNewParams((p) => {
                        const updated = { ...p, sucursal: v };
                        return updated as typeof p;
                      });
                    }}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {branches.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {newType === 'costo_insumo' && (
                <div className="space-y-2">
                  <Label>Categoría</Label>
                  <Select
                    value={newParams.categoria ?? categories[0]}
                    onValueChange={(v) => {
                      setNewParams((p) => {
                        const updated = { ...p, categoria: v };
                        return updated as typeof p;
                      });
                    }}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {newType === 'shift_mix' && (
                <>
                  <div className="space-y-2">
                    <Label>From</Label>
                    <Select
                      value={newParams.cat_from ?? categories[0]}
                      onValueChange={(v) => {
                        setNewParams((p) => {
                          const updated = { ...p, cat_from: v };
                          return updated as typeof p;
                        });
                      }}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>To</Label>
                    <Select
                      value={newParams.cat_to ?? (categories[1] ?? categories[0])}
                      onValueChange={(v) => {
                        setNewParams((p) => {
                          const updated = { ...p, cat_to: v };
                          return updated as typeof p;
                        });
                      }}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}

              {newType !== 'cierre_sucursal' && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <Label>Delta</Label>
                    <span>{((newParams.delta_pct ?? 0.1) * 100).toFixed(0)}%</span>
                  </div>
                  <Slider
                    min={1} max={50} step={1}
                    value={[(newParams.delta_pct ?? 0.1) * 100]}
                    onValueChange={(v) => {
                      const val = Array.isArray(v) ? v[0] : v;
                      setNewParams((p) => ({ ...p, delta_pct: val / 100 }));
                    }}
                  />
                </div>
              )}

              <Button className="w-full mt-4" onClick={handleAddScenario}>Add Scenario</Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Scenarios + Waterfall */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {scenarios.map((card, i) => (
            <ScenarioCard
              key={card.id}
              card={card}
              kpis={kpis}
              removable={i >= 5}
            />
          ))}
        </div>
        <div className="sticky top-0">
          <WaterfallChart baseEbitda={baseEbitda} scenarios={scenarios} />
        </div>
      </div>

      {/* Break-Even section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Break-Even Ticket</h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Target EBITDA: {compact(breakEvenTarget)}</span>
            <div className="w-48">
              <Slider
                min={0}
                max={5_000_000}
                step={100_000}
                value={[breakEvenTarget]}
                onValueChange={(v) => setBreakEvenTarget(Array.isArray(v) ? v[0] : v)}
              />
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {breakEvenResults.map((r) => (
            <BreakEvenCard
              key={r.sucursal}
              sucursal={r.sucursal}
              currentTicket={r.current_ticket}
              requiredTicket={r.required_ticket}
              deltaPercent={r.ticket_delta_pct}
              currentEbitda={r.current_ebitda}
              targetEbitda={r.target_ebitda}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
