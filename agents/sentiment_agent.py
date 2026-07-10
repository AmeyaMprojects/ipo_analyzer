"""
Sentiment agent — deterministic scoring from GMP and subscription data.
No LLM call: these are weighted calculations, not judgment calls. Kept as
its own node (rather than folded into fundamentals) so it can run in
parallel with the valuation agent and stay independently testable.
"""
from __future__ import annotations

from state import AnalysisState
from scrapers.models import IPOStatus
from utils.financial_calcs import implied_listing_gain_pct, subscription_momentum_score


def sentiment_node(state: AnalysisState) -> dict:
    ipo = state["ipo"]
    errors = list(state.get("errors", []))

    latest_gmp = ipo.gmp_history[-1].gmp if ipo.gmp_history else None
    issue_price = ipo.basic.price_band_high or ipo.basic.price_band_low
    implied_gain = (
        implied_listing_gain_pct(latest_gmp, issue_price)
        if latest_gmp is not None and issue_price else None
    )

    sub = ipo.subscription
    sub_score = None
    subscription_note = None
    if sub:
        sub_score = subscription_momentum_score(sub.qib_times, sub.nii_times, sub.retail_times)
    elif ipo.basic.status == IPOStatus.UPCOMING:
        subscription_note = "Subscription data is not expected yet because this IPO has not opened."
    else:
        errors.append("Missing subscription data for an IPO that is open or closed.")

    gmp_trend = "unknown"
    vals = [r.gmp for r in ipo.gmp_history if r.gmp is not None]
    if len(vals) >= 2:
        gmp_trend = "rising" if vals[-1] > vals[0] else ("falling" if vals[-1] < vals[0] else "flat")

    return {
        "sentiment_analysis": {
            "latest_gmp": latest_gmp,
            "implied_listing_gain_pct": implied_gain,
            "gmp_trend": gmp_trend,
            "subscription_score": sub_score,
            "subscription_raw": sub.model_dump() if sub else None,
            "subscription_note": subscription_note,
        },
        "errors": errors,
    }
