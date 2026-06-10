import { v4 as uuidv4 } from 'uuid';
import type { PeriodKPIs, Scenario, ScenarioCard, ScenarioType } from '@/types/analysis';

// ---------------------------------------------------------------------------
// Lookup helpers
// ---------------------------------------------------------------------------

const catMap = (kpis: PeriodKPIs) =>
  Object.fromEntries(kpis.por_categoria.map((c) => [c.categoria, c]));

const branchMap = (kpis: PeriodKPIs) =>
  Object.fromEntries(kpis.por_sucursal.map((b) => [b.sucursal, b]));

// ---------------------------------------------------------------------------
// Five scenario formulas — mirror of scenario_builder.py
// ---------------------------------------------------------------------------

export function costoInsumo(kpis: PeriodKPIs, categoria: string, deltaPct: number): number {
  const cats = catMap(kpis);
  if (!cats[categoria]) throw new Error(`Categoría '${categoria}' not found`);
  return -deltaPct * cats[categoria].costo;
}

export function cierreSucursal(kpis: PeriodKPIs, sucursal: string): number {
  const branches = branchMap(kpis);
  if (!branches[sucursal]) throw new Error(`Sucursal '${sucursal}' not found`);
  return -branches[sucursal].ebitda;
}

export function shiftMix(
  kpis: PeriodKPIs,
  catFrom: string,
  catTo: string,
  deltaPct: number,
): number {
  const cats = catMap(kpis);
  if (!cats[catFrom]) throw new Error(`Categoría '${catFrom}' not found`);
  if (!cats[catTo]) throw new Error(`Categoría '${catTo}' not found`);
  const deltaRevenue = cats[catFrom].ingresos * deltaPct;
  return deltaRevenue * (cats[catTo].margen_bruto - cats[catFrom].margen_bruto);
}

export function reduccionNomina(kpis: PeriodKPIs, sucursal: string, deltaPct: number): number {
  const branches = branchMap(kpis);
  if (!branches[sucursal]) throw new Error(`Sucursal '${sucursal}' not found`);
  return branches[sucursal].nomina * deltaPct;
}

export function incrementoSalarial(kpis: PeriodKPIs, deltaPct: number): number {
  return -kpis.consolidado.nomina_total * deltaPct;
}

// ---------------------------------------------------------------------------
// Break-even solver
// ---------------------------------------------------------------------------

export function breakEvenTicket(
  kpis: PeriodKPIs,
  sucursal: string,
  targetEbitda: number,
): {
  sucursal: string;
  target_ebitda: number;
  current_ebitda: number;
  current_ticket: number;
  required_ticket: number;
  ticket_delta_pct: number;
  transacciones: number;
} {
  const b = branchMap(kpis)[sucursal];
  if (!b) throw new Error(`Sucursal '${sucursal}' not found`);
  const required =
    (targetEbitda + b.gastos_operativos + b.nomina) / (b.transacciones * b.margen_bruto);
  return {
    sucursal,
    target_ebitda: targetEbitda,
    current_ebitda: b.ebitda,
    current_ticket: b.ticket_promedio,
    required_ticket: required,
    ticket_delta_pct: (required - b.ticket_promedio) / b.ticket_promedio,
    transacciones: b.transacciones,
  };
}

// ---------------------------------------------------------------------------
// Dispatch: compute impact for any ScenarioCard
// ---------------------------------------------------------------------------

export function computeImpact(kpis: PeriodKPIs, card: ScenarioCard): number {
  const p = card.params;
  switch (card.type) {
    case 'costo_insumo':
      return costoInsumo(kpis, p.categoria!, p.delta_pct);
    case 'cierre_sucursal':
      return cierreSucursal(kpis, p.sucursal!);
    case 'shift_mix':
      return shiftMix(kpis, p.cat_from!, p.cat_to!, p.delta_pct);
    case 'reduccion_nomina':
      return reduccionNomina(kpis, p.sucursal!, p.delta_pct);
    case 'incremento_salarial':
      return incrementoSalarial(kpis, p.delta_pct);
  }
}

// ---------------------------------------------------------------------------
// Init scenario cards from server-returned scenarios
// ---------------------------------------------------------------------------

export function initScenarioCards(serverScenarios: Scenario[]): ScenarioCard[] {
  return serverScenarios.map((s) => {
    const type = s.variable as ScenarioType;
    const params: ScenarioCard['params'] = { delta_pct: s.delta_pct };

    if (type === 'costo_insumo') {
      params.categoria = s.affected_target;
    } else if (type === 'cierre_sucursal' || type === 'reduccion_nomina') {
      params.sucursal = s.affected_target;
    } else if (type === 'shift_mix') {
      const [catFrom, catTo] = s.affected_target.split('→');
      params.cat_from = catFrom;
      params.cat_to = catTo;
    }

    return {
      id: uuidv4(),
      type,
      label: s.name,
      params,
      active: true,
      impact: s.impact_on_ebitda,
    };
  });
}
