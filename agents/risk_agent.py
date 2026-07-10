"""
Risk profiling agent — matches IPO-specific risk factors against the
user's declared risk profile.

Risk score (0-10, higher = riskier) is computed deterministically from
concrete red flags. Gemini's job is only to explain, in plain language,
which of those factors matter most for THIS particular user — someone
aggressive and experienced should get a different emphasis than a
first-time conservative investor looking at the same IPO.
"""
from __future__ import annotations

import json

from state import AnalysisState
from utils.gemini_client import get_llm, extract_text


def _compute_risk_factors(state: AnalysisState) -> tuple[float, list[str]]:
    ipo = state["ipo"]
    ratios = state.get("fundamentals_ratios", {})
    score = 0.0
    factors: list[str] = []

    if ipo.basic.category.value == "sme":
        score += 3
        factors.append(
            "SME IPO: lower liquidity, wider bid-ask spreads, and a higher "
            "minimum lot value (often ₹1-2L) than mainboard IPOs."
        )

    de = ratios.get("debt_to_equity")
    if de is not None and de > 1.5:
        score += 2
        factors.append(f"High leverage: debt-to-equity of {de} adds financial risk in a downturn.")

    dilution = ratios.get("promoter_dilution_pct")
    if dilution is not None and dilution > 20:
        score += 1.5
        factors.append(
            f"Large promoter dilution ({dilution} percentage points) — reduces "
            "promoter 'skin in the game' immediately post-listing."
        )

    cagr = ratios.get("revenue_cagr_pct")
    if cagr is not None and cagr < 5:
        score += 1.5
        factors.append(f"Low revenue growth ({cagr}% CAGR) relative to typical high-growth IPO candidates.")

    if not ipo.financials or not ipo.financials.revenue_cr:
        score += 2
        factors.append("Limited or no financial disclosure data available for independent verification.")

    latest_pat = ipo.financials.pat_cr[0] if ipo.financials and ipo.financials.pat_cr else None
    if latest_pat is not None and latest_pat < 0:
        score += 2
        factors.append("Company is currently loss-making (negative PAT in the latest disclosed year).")

    return round(min(score, 10), 1), factors


def risk_profile_node(state: AnalysisState) -> dict:
    risk_score, factors = _compute_risk_factors(state)
    profile = state.get("user_profile", {})

    llm = get_llm(temperature=0.3)
    prompt = f"""A retail investor with this profile is considering an Indian IPO:
{json.dumps(profile)}

Computed IPO risk factors (composite score {risk_score}/10, higher = riskier):
{json.dumps(factors)}

In 2-3 sentences, explain specifically how THIS user's risk appetite,
investment horizon, and experience level interact with these particular
risk factors — not generic IPO risk advice. Be direct about any mismatch
between what the IPO offers and what this user says they want."""

    try:
        response = llm.invoke(prompt)
        explanation = extract_text(response)
    except Exception as exc:  # noqa: BLE001 - network/transport failures should not crash the graph
        explanation = (
            "Risk explanation unavailable because Gemini could not be reached. "
            "The risk score and risk factors are still computed deterministically from the IPO data and user profile."
        )
        factors.append(f"Gemini risk explanation unavailable: {exc}")

    return {
        "risk_assessment": {
            "risk_score": risk_score,
            "risk_factors": factors,
            "explanation": explanation,
        }
    }
