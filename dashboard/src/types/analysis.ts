export interface Consolidado {
  ingresos_total: number;
  utilidad_bruta_total: number;
  ebitda_total: number;
  margen_bruto_global: number;
  margen_ebitda_global: number;
  nomina_total: number;
  gastos_operativos_total: number;
  pct_nomina_ingresos_global: number;
  gastos_financieros?: number;
  utilidad_neta?: number;
}

export interface BranchKPI {
  sucursal: string;
  ingresos: number;
  costo_ventas: number;
  utilidad_bruta: number;
  margen_bruto: number;
  gastos_operativos: number;
  nomina: number;
  ebitda: number;
  pct_nomina_ingresos: number;
  ticket_promedio: number;
  transacciones: number;
}

export interface CategoryKPI {
  categoria: string;
  ingresos: number;
  costo: number;
  margen_bruto: number;
  pct_total_ingresos: number;
}

export interface ProductKPI {
  sku: string;
  categoria: string;
  sucursal: string;
  ingresos: number;
  contribucion_marginal: number;
  margen_bruto: number;
  cantidad: number;
}

export interface PeriodKPIs {
  period: string;
  consolidado: Consolidado;
  por_sucursal: BranchKPI[];
  top_productos: ProductKPI[];
  pct_mix_categoria: Record<string, number>;
  por_categoria: CategoryKPI[];
}

export interface QuantOutput {
  period: string;
  kpis: PeriodKPIs;
  alerts: Alert[];
  narrative: string;
  top_products: ProductKPI[];
}

export interface Alert {
  level: 'red' | 'warning';
  tipo: string;
  sucursal: string | null;
  sku: string | null;
  mensaje: string;
  valor: number | null;
}

export interface Signal {
  rank: number;
  titulo: string;
  evidencia_quant: string;
  evidencia_qual: string;
  recomendacion: string;
  impacto: 'alto' | 'medio' | 'bajo';
  facilidad: 'alta' | 'media' | 'baja';
}

export interface QualOutput {
  signals: Signal[];
  summary: string;
}

export interface Scenario {
  name: string;
  variable: string;
  delta_pct: number;
  affected_target: string;
  base_ebitda: number;
  impact_on_ebitda: number;
  ebitda_post: number;
}

export interface BreakEvenResult {
  sucursal: string;
  target_ebitda: number;
  current_ebitda: number;
  current_ticket: number;
  required_ticket: number;
  ticket_delta_pct: number;
  transacciones: number;
}

export interface SynthOutput {
  signals: Signal[];
  scenarios: Scenario[];
  break_even_results: BreakEvenResult[];
  recommendations: Recommendation[];
  next_steps: string;
  memo_html: string;
  memo_pdf_path: string;
}

export interface Recommendation {
  accion: string;
  impacto: 'alto' | 'medio' | 'bajo';
  facilidad: 'alta' | 'media' | 'baja';
  fuente: string;
}

export interface AnalysisResult {
  period: string;
  quant: QuantOutput;
  qual: QualOutput;
  synth: SynthOutput;
}

export type ScenarioType =
  | 'costo_insumo'
  | 'cierre_sucursal'
  | 'shift_mix'
  | 'reduccion_nomina'
  | 'incremento_salarial';

export interface ScenarioCard {
  id: string;
  type: ScenarioType;
  label: string;
  params: {
    categoria?: string;
    sucursal?: string;
    cat_from?: string;
    cat_to?: string;
    delta_pct: number;
  };
  active: boolean;
  impact: number;
}

export type JobStatus = 'idle' | 'pending' | 'running' | 'done' | 'error';
