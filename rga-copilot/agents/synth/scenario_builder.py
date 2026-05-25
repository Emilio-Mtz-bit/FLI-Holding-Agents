"""
Deterministic what-if scenario calculations. No LLM.

All functions receive a QuantOutput (or duck-typed object with .kpis dict)
and return a Scenario model.

Scenario 1 — costo_insumo:
    A cost increase of delta_pct on all COGS in a category.
    impact = -delta_pct * costo_categoria

Scenario 2 — cierre_sucursal:
    Permanently close a branch.
    impact = -branch.ebitda  (losing that branch's EBITDA contribution)
    Note: if branch EBITDA is negative, closure is positive impact.

Scenario 3 — shift_mix:
    Shift delta_pct of total revenue from cat_from → cat_to.
    impact = delta_pct * ingresos_total * (margin_to - margin_from)
"""

from __future__ import annotations

from agents.synth.models import Scenario


def build_scenario_costo_insumo(
    quant,
    categoria: str,
    delta_pct: float = 0.15,
) -> Scenario:
    """Raise cost of inputs for `categoria` by `delta_pct`."""
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]

    cat_map = {c["categoria"]: c for c in kpis["por_categoria"]}
    if categoria not in cat_map:
        raise ValueError(f"Categoría '{categoria}' not found in por_categoria. "
                         f"Available: {list(cat_map)}")

    costo_categoria = cat_map[categoria]["costo"]
    impact = -delta_pct * costo_categoria

    return Scenario(
        name=f"Costo insumo {categoria} +{delta_pct:.0%}",
        variable="costo_insumo",
        delta_pct=delta_pct,
        affected_target=categoria,
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_scenario_cierre_sucursal(
    quant,
    sucursal: str,
) -> Scenario:
    """Close branch `sucursal` — remove its EBITDA contribution."""
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]

    branch_map = {b["sucursal"]: b for b in kpis["por_sucursal"]}
    if sucursal not in branch_map:
        raise ValueError(f"Sucursal '{sucursal}' not found. Available: {list(branch_map)}")

    branch_ebitda = branch_map[sucursal]["ebitda"]
    impact = -branch_ebitda

    return Scenario(
        name=f"Cierre sucursal {sucursal}",
        variable="cierre_sucursal",
        delta_pct=1.0,
        affected_target=sucursal,
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_scenario_shift_mix(
    quant,
    cat_from: str,
    cat_to: str,
    delta_pct: float = 0.05,
) -> Scenario:
    """
    Shift delta_pct of total revenue from cat_from → cat_to.
    Revenue is constant; only the margin difference matters for EBITDA.
    """
    kpis = quant.kpis
    base_ebitda = kpis["consolidado"]["ebitda_total"]
    ingresos_total = kpis["consolidado"]["ingresos_total"]

    cat_map = {c["categoria"]: c for c in kpis["por_categoria"]}
    for cat in (cat_from, cat_to):
        if cat not in cat_map:
            raise ValueError(f"Categoría '{cat}' not found. Available: {list(cat_map)}")

    margin_from = cat_map[cat_from]["margen_bruto"]
    margin_to   = cat_map[cat_to]["margen_bruto"]
    delta_revenue = ingresos_total * delta_pct
    impact = delta_revenue * (margin_to - margin_from)

    return Scenario(
        name=f"Mix shift {delta_pct:.0%}: {cat_from} → {cat_to}",
        variable="shift_mix",
        delta_pct=delta_pct,
        affected_target=f"{cat_from}→{cat_to}",
        base_ebitda=base_ebitda,
        impact_on_ebitda=impact,
        ebitda_post=base_ebitda + impact,
    )


def build_default_scenarios(quant) -> list[Scenario]:
    """
    Build three predefined scenarios using real data to pick relevant targets:
    1. Raise cost of the highest-cost category by 15%.
    2. Close the branch with the lowest (possibly negative) EBITDA.
    3. Shift 5% of revenue from lowest-margin category → highest-margin category.
    """
    kpis = quant.kpis
    cats = kpis["por_categoria"]
    branches = kpis["por_sucursal"]

    if not cats:
        raise ValueError("Cannot build scenarios: por_categoria is empty for this period.")
    if not branches:
        raise ValueError("Cannot build scenarios: por_sucursal is empty for this period.")

    # Scenario 1: highest-cost category
    highest_cost_cat = max(cats, key=lambda c: c["costo"])["categoria"]
    sc1 = build_scenario_costo_insumo(quant, categoria=highest_cost_cat, delta_pct=0.15)

    # Scenario 2: worst EBITDA branch
    worst_branch = min(branches, key=lambda b: b["ebitda"])["sucursal"]
    sc2 = build_scenario_cierre_sucursal(quant, sucursal=worst_branch)

    # Scenario 3: shift from lowest-margin → highest-margin category
    sorted_by_margin = sorted(cats, key=lambda c: c["margen_bruto"])
    cat_from = sorted_by_margin[0]["categoria"]
    cat_to   = sorted_by_margin[-1]["categoria"]
    if cat_from == cat_to:
        cat_from, cat_to = cats[0]["categoria"], cats[-1]["categoria"]
    sc3 = build_scenario_shift_mix(quant, cat_from=cat_from, cat_to=cat_to, delta_pct=0.05)

    return [sc1, sc2, sc3]
