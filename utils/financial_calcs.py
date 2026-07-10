"""
Pure financial calculations used by the Fundamentals, Valuation, and
Sentiment agents. No network calls, no LLM calls — deterministic,
unit-testable math, so the numbers in the final report are never
something the LLM invented. Gemini only ever explains numbers computed
here; it never computes them itself.
"""
from __future__ import annotations
from typing import Optional


def pe_ratio(price: float, eps: float) -> Optional[float]:
    """Price-to-Earnings: rupees an investor pays per rupee of annual profit.
    Lower generally means cheaper, but it's only meaningful compared against
    sector peers — a 25 P/E can be expensive for a utility and cheap for a
    high-growth SaaS company."""
    if not eps or eps <= 0:
        return None
    return round(price / eps, 2)


def pb_ratio(price: float, book_value_per_share: float) -> Optional[float]:
    """Price-to-Book: price paid relative to net asset value per share.
    More meaningful for asset-heavy businesses (banks, NBFCs, manufacturing)
    than for asset-light tech/services companies, where most of the value
    is intangible (brand, IP, network effects) and won't show up here."""
    if not book_value_per_share or book_value_per_share <= 0:
        return None
    return round(price / book_value_per_share, 2)


def roe(net_profit_cr: float, net_worth_cr: float) -> Optional[float]:
    """Return on Equity (%): profit generated per rupee of shareholder
    capital. >15% is generally considered healthy for Indian mainboard
    companies, but this varies a lot by sector — compare within sector,
    not across."""
    if not net_worth_cr:
        return None
    return round((net_profit_cr / net_worth_cr) * 100, 2)


def roce(ebit_cr: float, capital_employed_cr: float) -> Optional[float]:
    """Return on Capital Employed (%): profitability relative to ALL
    capital used (equity + debt) — a fairer comparison than ROE for
    companies that use significant leverage, since ROE alone can be
    inflated by debt."""
    if not capital_employed_cr:
        return None
    return round((ebit_cr / capital_employed_cr) * 100, 2)


def debt_to_equity(total_debt_cr: float, net_worth_cr: float) -> Optional[float]:
    """>1 means the company owes more than shareholders have invested —
    higher financial risk, especially for cyclical or newer businesses
    that may struggle to service debt in a downturn."""
    if not net_worth_cr:
        return None
    return round(total_debt_cr / net_worth_cr, 2)


def revenue_cagr(revenues_most_recent_first: list[float]) -> Optional[float]:
    """Compound Annual Growth Rate (%) across the disclosed fiscal years.
    Input order: [FY_latest, FY_latest-1, FY_latest-2, ...]"""
    vals = [v for v in revenues_most_recent_first if v and v > 0]
    if len(vals) < 2:
        return None
    latest, earliest = vals[0], vals[-1]
    years = len(vals) - 1
    if earliest <= 0 or years <= 0:
        return None
    return round(((latest / earliest) ** (1 / years) - 1) * 100, 2)


def pat_margin(pat_cr: float, revenue_cr: float) -> Optional[float]:
    """Net profit margin (%): what fraction of revenue actually becomes
    profit, after all costs, interest, and tax."""
    if not revenue_cr:
        return None
    return round((pat_cr / revenue_cr) * 100, 2)


def implied_listing_gain_pct(gmp: float, issue_price: float) -> Optional[float]:
    """Estimated listing-day gain (%) implied by the current grey market
    premium. GMP is an unregulated, informal indicator traded outside
    SEBI's purview — it reflects speculative demand, not fundamental
    value, and can swing sharply (or vanish entirely) in the days before
    listing. Treat it as a sentiment signal, not a forecast."""
    if not issue_price:
        return None
    return round((gmp / issue_price) * 100, 2)


def subscription_momentum_score(
    qib: Optional[float], nii: Optional[float], retail: Optional[float]
) -> Optional[float]:
    """A 0-10 composite score from subscription multiples, weighted toward
    QIB ('smart money' institutional) demand since QIBs typically do the
    deepest diligence before bidding:
        QIB    -> 50% weight
        NII    -> 30% weight
        Retail -> 20% weight
    Each leg is capped at 10x before weighting so one runaway category
    (e.g. retail FOMO on a small-issue-size SME IPO) doesn't dominate."""
    legs = [(qib, 0.5), (nii, 0.3), (retail, 0.2)]
    total_weight = sum(w for v, w in legs if v is not None)
    if total_weight == 0:
        return None
    score = sum(min(v, 10) * w for v, w in legs if v is not None) / total_weight
    return round(score, 2)
