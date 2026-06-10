import { describe, it, expect } from 'vitest';
import {
  costoInsumo,
  cierreSucursal,
  shiftMix,
  reduccionNomina,
  incrementoSalarial,
  breakEvenTicket,
  computeImpact,
  initScenarioCards,
} from '@/lib/scenarios';
import type { PeriodKPIs, ScenarioCard } from '@/types/analysis';

const mockKpis = (): PeriodKPIs => ({
  period: 'ENERO 2026',
  consolidado: {
    ingresos_total: 9_000_000,
    utilidad_bruta_total: 6_300_000,
    ebitda_total: 1_800_000,
    margen_bruto_global: 0.7,
    margen_ebitda_global: 0.2,
    nomina_total: 2_000_000,
    gastos_operativos_total: 2_500_000,
    pct_nomina_ingresos_global: 0.222,
  },
  por_sucursal: [
    {
      sucursal: 'ANT',
      ingresos: 4_000_000,
      costo_ventas: 1_200_000,
      utilidad_bruta: 2_800_000,
      margen_bruto: 0.7,
      gastos_operativos: 700_000,
      nomina: 800_000,
      ebitda: 1_300_000,
      pct_nomina_ingresos: 0.2,
      ticket_promedio: 10_000,
      transacciones: 400,
    },
    {
      sucursal: 'SOK',
      ingresos: 2_500_000,
      costo_ventas: 800_000,
      utilidad_bruta: 1_700_000,
      margen_bruto: 0.68,
      gastos_operativos: 600_000,
      nomina: 700_000,
      ebitda: 400_000,
      pct_nomina_ingresos: 0.28,
      ticket_promedio: 7_000,
      transacciones: 357,
    },
  ],
  top_productos: [],
  pct_mix_categoria: {},
  por_categoria: [
    { categoria: 'MAKIS', ingresos: 5_000_000, costo: 1_500_000, margen_bruto: 0.7, pct_total_ingresos: 0.56 },
    { categoria: 'POKE', ingresos: 2_000_000, costo: 800_000, margen_bruto: 0.6, pct_total_ingresos: 0.22 },
    { categoria: 'BEBIDAS', ingresos: 2_000_000, costo: 400_000, margen_bruto: 0.8, pct_total_ingresos: 0.22 },
  ],
});

describe('costoInsumo', () => {
  it('returns -delta * costo for given category', () => {
    expect(costoInsumo(mockKpis(), 'MAKIS', 0.15)).toBeCloseTo(-225_000);
  });
  it('throws for unknown category', () => {
    expect(() => costoInsumo(mockKpis(), 'UNKNOWN', 0.1)).toThrow();
  });
});

describe('cierreSucursal', () => {
  it('returns negative of branch EBITDA', () => {
    expect(cierreSucursal(mockKpis(), 'ANT')).toBe(-1_300_000);
  });
  it('throws for unknown sucursal', () => {
    expect(() => cierreSucursal(mockKpis(), 'ZZZ')).toThrow();
  });
});

describe('shiftMix', () => {
  it('computes margin differential on cat_from revenue', () => {
    // delta_revenue = 2_000_000 * 0.05 = 100_000
    // impact = 100_000 * (0.8 - 0.6) = 20_000
    expect(shiftMix(mockKpis(), 'POKE', 'BEBIDAS', 0.05)).toBeCloseTo(20_000);
  });
  it('returns negative when shifting to lower margin', () => {
    expect(shiftMix(mockKpis(), 'BEBIDAS', 'POKE', 0.05)).toBeLessThan(0);
  });
});

describe('reduccionNomina', () => {
  it('returns positive impact (saving)', () => {
    expect(reduccionNomina(mockKpis(), 'SOK', 0.10)).toBeCloseTo(70_000);
  });
});

describe('incrementoSalarial', () => {
  it('returns negative impact (cost increase)', () => {
    expect(incrementoSalarial(mockKpis(), 0.10)).toBeCloseTo(-200_000);
  });
});

describe('breakEvenTicket', () => {
  it('computes required ticket correctly', () => {
    // ANT: target=0, gastos=700k, nomina=800k, transacciones=400, margen=0.7
    // required = (0 + 700_000 + 800_000) / (400 * 0.7) = 1_500_000 / 280 = 5_357.14
    const result = breakEvenTicket(mockKpis(), 'ANT', 0);
    expect(result.required_ticket).toBeCloseTo(5_357.14, 1);
    expect(result.current_ticket).toBe(10_000);
  });
  it('reflects target_ebitda in result', () => {
    const result = breakEvenTicket(mockKpis(), 'ANT', 500_000);
    expect(result.target_ebitda).toBe(500_000);
  });
});

describe('computeImpact', () => {
  it('recomputes impact for a costo_insumo card', () => {
    const card: ScenarioCard = {
      id: '1',
      type: 'costo_insumo',
      label: 'test',
      params: { categoria: 'MAKIS', delta_pct: 0.15 },
      active: true,
      impact: 0,
    };
    expect(computeImpact(mockKpis(), card)).toBeCloseTo(-225_000);
  });
});

describe('initScenarioCards', () => {
  it('returns 5 cards from server scenarios', () => {
    const serverScenarios = [
      { name: 'Costo insumo MAKIS +15%', variable: 'costo_insumo', delta_pct: 0.15, affected_target: 'MAKIS', base_ebitda: 1_800_000, impact_on_ebitda: -225_000, ebitda_post: 1_575_000 },
      { name: 'Cierre sucursal ANT', variable: 'cierre_sucursal', delta_pct: 1.0, affected_target: 'ANT', base_ebitda: 1_800_000, impact_on_ebitda: -1_300_000, ebitda_post: 500_000 },
      { name: 'Mix shift 5%: POKE → BEBIDAS', variable: 'shift_mix', delta_pct: 0.05, affected_target: 'POKE→BEBIDAS', base_ebitda: 1_800_000, impact_on_ebitda: 20_000, ebitda_post: 1_820_000 },
      { name: 'Reducción nómina SOK -10%', variable: 'reduccion_nomina', delta_pct: 0.10, affected_target: 'SOK', base_ebitda: 1_800_000, impact_on_ebitda: 70_000, ebitda_post: 1_870_000 },
      { name: 'Incremento salarial +10%', variable: 'incremento_salarial', delta_pct: 0.10, affected_target: 'todas las sucursales', base_ebitda: 1_800_000, impact_on_ebitda: -200_000, ebitda_post: 1_600_000 },
    ];
    const cards = initScenarioCards(serverScenarios);
    expect(cards).toHaveLength(5);
    expect(cards[0].type).toBe('costo_insumo');
    expect(cards[0].params.categoria).toBe('MAKIS');
    expect(cards[2].params.cat_from).toBe('POKE');
    expect(cards[2].params.cat_to).toBe('BEBIDAS');
  });
});
