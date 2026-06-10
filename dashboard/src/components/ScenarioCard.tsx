import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { compact } from '@/lib/format';
import { computeImpact } from '@/lib/scenarios';
import { useAnalysisStore } from '@/store/analysis';
import type { ScenarioCard as ScenarioCardType, PeriodKPIs } from '@/types/analysis';
import { X } from 'lucide-react';

interface Props {
  card: ScenarioCardType;
  kpis: PeriodKPIs;
  removable?: boolean;
}

export default function ScenarioCard({ card, kpis, removable = false }: Props) {
  const { updateScenario, removeScenario } = useAnalysisStore();

  const recompute = (patch: Partial<ScenarioCardType['params']>) => {
    const newParams = { ...card.params, ...patch };
    const newCard = { ...card, params: newParams };
    const impact = computeImpact(kpis, newCard);
    updateScenario(card.id, { params: newParams, impact });
  };

  const branches = kpis.por_sucursal.map((b) => b.sucursal);
  const categories = kpis.por_categoria.map((c) => c.categoria);

  const showBranch = card.type === 'cierre_sucursal' || card.type === 'reduccion_nomina';
  const showCategory = card.type === 'costo_insumo';
  const showShiftMix = card.type === 'shift_mix';
  const showDelta = card.type !== 'cierre_sucursal';

  return (
    <Card className={`transition-opacity ${card.active ? '' : 'opacity-50'}`}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Switch
            checked={card.active}
            onCheckedChange={(v) => updateScenario(card.id, { active: v })}
          />
          <span className="text-sm font-medium leading-tight">{card.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={card.impact >= 0 ? 'default' : 'destructive'}>
            {card.impact >= 0 ? '+' : ''}{compact(card.impact)}
          </Badge>
          {removable && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeScenario(card.id)}>
              <X size={12} />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {showBranch && card.params.sucursal !== undefined && (
          <div className="space-y-1">
            <Label className="text-xs">Sucursal</Label>
            <Select value={card.params.sucursal as string} onValueChange={(v: string | null) => v && recompute({ sucursal: v })}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                {branches.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {showCategory && card.params.categoria !== undefined && (
          <div className="space-y-1">
            <Label className="text-xs">Categoría</Label>
            <Select value={card.params.categoria as string} onValueChange={(v: string | null) => v && recompute({ categoria: v })}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {showShiftMix && card.params.cat_from !== undefined && card.params.cat_to !== undefined && (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">From</Label>
              <Select value={card.params.cat_from as string} onValueChange={(v: string | null) => v && recompute({ cat_from: v })}>
                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">To</Label>
              <Select value={card.params.cat_to as string} onValueChange={(v: string | null) => v && recompute({ cat_to: v })}>
                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {showDelta && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Delta</span>
              <span>{(card.params.delta_pct * 100).toFixed(0)}%</span>
            </div>
            <Slider
              min={1}
              max={50}
              step={1}
              value={[card.params.delta_pct * 100]}
              onValueChange={(v: any) => {
                const val = Array.isArray(v) ? v[0] : v;
                recompute({ delta_pct: val / 100 });
              }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
