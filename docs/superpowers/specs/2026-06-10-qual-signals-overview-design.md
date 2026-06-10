# Qual Signals — Overview Page Design Spec
**Date:** 2026-06-10
**Status:** Approved

---

## Overview

Add a "Señales Estratégicas" section to the Overview page that surfaces the QualAgent output. Fix the broken TypeScript `QualOutput` type to match the actual Python model, then render the qual signals in a visually rich section below the existing content.

---

## Type Fix: `QualOutput` in `analysis.ts`

Current TS type is wrong. Replace with:

```ts
export interface QualSignals {
  tipo_empresa?: string;
  posicionamiento?: string;
  fortalezas?: string[];
  riesgos?: string[];
  factores_crecimiento?: string[];
  temas_topicos?: string[];
  sentiment_score?: number;   // range: -1.0 to 1.0
}

export interface QualOutput {
  signals: QualSignals;
  sentiment: number;          // same as signals.sentiment_score, range -1 to 1
  hypotheses: string[];
  summary: string;
  chunks_stored: number;
}
```

---

## New Section: Señales Estratégicas

Added at the bottom of `Overview.tsx`, below the existing Executive Summary card.

**Visibility:** Only render if `result.qual.signals` has at least one non-null field. If qual docs were not uploaded, the signals dict will be empty — hide the entire section.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Señales Estratégicas                                        │
├───────────────────────────────┬─────────────────────────────┤
│  SENTIMENT SCORE              │  TIPO DE EMPRESA            │
│  [gauge 0-1, dot on track]   │  [text box]                 │
│  label + description          ├─────────────────────────────┤
│                               │  POSICIONAMIENTO            │
│                               │  [text box]                 │
├───────────────────────────────┴─────────────────────────────┤
│  FORTALEZAS (green)           │  RIESGOS (red)              │
│  • bullet                     │  • bullet                   │
│  • bullet                     │  • bullet                   │
├─────────────────────────────────────────────────────────────┤
│  FACTORES DE CRECIMIENTO                                     │
│  [card]  [card]  [card]  …                                  │
└─────────────────────────────────────────────────────────────┘
```

### Sentiment Gauge

- Normalize `signals.sentiment_score` from `-1..1` → `0..1` for display: `pct = (score + 1) / 2`
- Visual: full-width track, colored dot positioned at `pct * 100%`
  - Track: gradient from `#b91c1c` (left) → `#ca8a04` (center) → `#15803d` (right)
  - Dot: `w-4 h-4 rounded-full bg-foreground border-2 border-background`
- Labels below track: "Negativo" (left), "Neutro" (center), "Positivo" (right)
- Large score display: `score.toFixed(2)` in `text-4xl font-bold`
- Description text: "Perspectiva Favorable — Escala −1 a 1" (or "Desfavorable" / "Neutral" based on score)

### Tipo de Empresa / Posicionamiento

- Two stacked text boxes on the right column
- Label: small uppercase tracking-wide (`text-xs uppercase tracking-widest text-muted-foreground`)
- Content: `text-sm font-mono leading-relaxed`
- Separated by a colored top-border (olive/gold: `border-t-2 border-yellow-700`)
- Only rendered if the field is non-empty

### Fortalezas / Riesgos

- Two-column grid
- Section heading: `text-xs font-bold uppercase tracking-wider`
  - Fortalezas: `text-emerald-700`
  - Riesgos: `text-rose-700`
- Bullet list: `•` prefix, `text-sm`, `leading-relaxed`
- Only rendered if the array is non-empty

### Factores de Crecimiento

- Horizontal grid of small cards (`grid-cols-2 md:grid-cols-3 lg:grid-cols-4`)
- Each card: amber dot indicator + uppercase bold title (first ~3 words) + description text (rest)
- Title extracted as: first sentence or first 40 chars up to a comma/period
- Only rendered if array is non-empty

---

## Files

| File | Action |
|------|--------|
| `dashboard/src/types/analysis.ts` | Modify — fix `QualOutput` type |
| `dashboard/src/pages/Overview.tsx` | Modify — add Señales Estratégicas section |

---

## Out of Scope

- Editing or re-running the qual agent from the UI
- Showing `hypotheses` or `temas_topicos` fields
- Localization of labels
