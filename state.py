"""Shared state passed between LangGraph nodes. Each agent reads what it
needs and returns a partial update, which LangGraph merges into the
running state."""
from __future__ import annotations
from typing import TypedDict

from scrapers.models import IPOFullData


class UserRiskProfile(TypedDict, total=False):
    investment_amount_inr: float
    risk_appetite: str            # "conservative" | "moderate" | "aggressive"
    horizon: str                  # "listing_gain" | "short_term" | "long_term"
    sme_comfortable: bool
    existing_ipo_experience: str  # "first_time" | "some" | "experienced"


class AnalysisState(TypedDict, total=False):
    ipo: IPOFullData
    user_profile: UserRiskProfile

    # populated by agents as the graph runs
    fundamentals_ratios: dict
    valuation_verdict: dict     # {"verdict", "explanation", "ratios_used"}
    sentiment_analysis: dict    # {"latest_gmp", "implied_listing_gain_pct", "gmp_trend", "subscription_score", ...}
    risk_assessment: dict       # {"risk_score", "risk_factors", "explanation"}
    final_report: dict          # synthesizer output, see agents/synthesizer_agent.py

    errors: list[str]
