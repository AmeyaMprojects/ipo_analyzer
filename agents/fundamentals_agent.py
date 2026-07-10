"""
Fundamentals agent — deterministic, no LLM call.

Converts the raw disclosed financials (from the RHP/DRHP, as scraped) into
the standard ratios used to judge IPO quality: growth, profitability,
leverage. This is the node every downstream agent (valuation, risk) reads
from, so it runs first and never involves the LLM — we want these numbers
to be exactly reproducible, not subject to model sampling.
"""
from __future__ import annotations

from state import AnalysisState
from utils.financial_calcs import (
    pe_ratio, pb_ratio, roe, roce, debt_to_equity, revenue_cagr, pat_margin,
)


def fundamentals_node(state: AnalysisState) -> dict:
    ipo = state["ipo"]
    fin = ipo.financials
    basic = ipo.basic
    errors = list(state.get("errors", []))

    if fin is None:
        errors.append("No financial disclosures found for this IPO — ratios unavailable.")
        return {"fundamentals_ratios": {}, "errors": errors}

    upper_price = basic.price_band_high or basic.price_band_low
    latest_pat = fin.pat_cr[0] if fin.pat_cr else None
    latest_revenue = fin.revenue_cr[0] if fin.revenue_cr else None

    ratios = {
        "pe_ratio": pe_ratio(upper_price, fin.eps_pre_ipo) if upper_price and fin.eps_pre_ipo else None,
        "pb_ratio": pb_ratio(upper_price, fin.book_value_per_share) if upper_price and fin.book_value_per_share else None,
        "roe_pct": roe(latest_pat, fin.net_worth_cr) if latest_pat and fin.net_worth_cr else None,
        "roce_pct": roce(fin.ebit_cr, fin.capital_employed_cr) if fin.ebit_cr and fin.capital_employed_cr else None,
        "debt_to_equity": debt_to_equity(fin.total_debt_cr, fin.net_worth_cr)
                           if fin.total_debt_cr is not None and fin.net_worth_cr else None,
        "revenue_cagr_pct": revenue_cagr(fin.revenue_cr),
        "pat_margin_pct": pat_margin(latest_pat, latest_revenue) if latest_pat and latest_revenue else None,
        "promoter_dilution_pct": (
            round(fin.promoter_holding_pre_pct - fin.promoter_holding_post_pct, 2)
            if fin.promoter_holding_pre_pct is not None and fin.promoter_holding_post_pct is not None
            else None
        ),
    }
    return {"fundamentals_ratios": ratios, "errors": errors}
