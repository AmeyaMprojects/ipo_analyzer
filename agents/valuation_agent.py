"""
Valuation agent — combines a deterministic ratio-threshold verdict with a
Gemini-generated peer-comparison explanation.

Design choice: the verdict itself (rich / fair / attractive) is computed
in plain code from the ratios, NOT decided by the LLM. Gemini's job is
purely to explain and contextualise a verdict it's handed — this stops
the LLM from silently drifting the recommendation away from the numbers
when phrased persuasively, and means the same inputs always produce the
same verdict.
"""
from __future__ import annotations

import json
import logging

from state import AnalysisState
from utils.gemini_client import get_llm, extract_text

logger = logging.getLogger(__name__)


def _rule_based_verdict(ratios: dict) -> str:
    pe = ratios.get("pe_ratio")
    pb = ratios.get("pb_ratio")
    roe_pct = ratios.get("roe_pct")
    roce_pct = ratios.get("roce_pct")
    if pe is None:
        if pb is not None:
            profitability = roe_pct if roe_pct is not None else roce_pct
            if profitability is not None and pb < 2.5 and profitability > 15:
                return "attractively_valued"
            if profitability is not None and pb > 6 and profitability < 10:
                return "richly_valued"
            if profitability is not None:
                return "fairly_valued"
        return "insufficient_data"
    if roe_pct is not None and roe_pct > 0:
        # Rough PEG-style sanity check: is the price reasonable given
        # how profitable the company actually is?
        if pe < 15 and roe_pct > 15:
            return "attractively_valued"
        if pe > 40 and roe_pct < 10:
            return "richly_valued"
    return "fairly_valued"


def _valuation_data_gaps(ratios: dict) -> list[str]:
    gaps: list[str] = []
    if ratios.get("pe_ratio") is None:
        gaps.append("P/E is unavailable because EPS was missing or non-positive in the disclosures.")
    if ratios.get("pb_ratio") is None:
        gaps.append("P/B is unavailable because book value per share was missing or non-positive.")
    if ratios.get("roe_pct") is None:
        gaps.append("ROE is unavailable because either net profit or net worth was missing.")
    if ratios.get("roce_pct") is None:
        gaps.append("ROCE is unavailable because either EBIT or capital employed was missing.")
    return gaps


def valuation_node(state: AnalysisState) -> dict:
    ratios = state.get("fundamentals_ratios", {})
    ipo = state["ipo"]
    verdict = _rule_based_verdict(ratios)
    data_gaps = _valuation_data_gaps(ratios)
    peer_names = ipo.peers[:5]

    llm = get_llm(temperature=0.3)
    prompt = f"""You are a valuation analyst explaining an Indian IPO's pricing to a
retail investor who wants to actually understand the mechanics, not just
be told what to do. Be precise and technical. Do not invent any numbers
that are not given below, and do not change the verdict — it was already
computed from the ratios by deterministic code.

Use only these verdicts: attractively_valued, fairly_valued, richly_valued.
Never output insufficient_data; if the data are sparse, explain exactly
which ratios are missing and keep the explanation cautious.

Company: {ipo.basic.name} ({ipo.basic.sector or "sector unknown"})
Price band: {ipo.basic.price_band_low}-{ipo.basic.price_band_high}
Computed ratios: {json.dumps(ratios)}
Known valuation data gaps: {json.dumps(data_gaps)}
Peer names from Chittorgarh comparison table: {json.dumps(peer_names)}
Rule-based verdict (fixed, do not change): {verdict}

Write 3-4 sentences explaining what these specific ratios mean for this
company, how it compares against the named peers if peer data is present,
why the verdict follows from them, and one concrete caveat an investor
should know about relying on this verdict. Plain text, no markdown
headers, no bullet points."""

    try:
        response = llm.invoke(prompt)
        explanation = extract_text(response)
    except Exception as exc:  # noqa: BLE001 - network/transport failures should not crash the graph
        logger.warning("Valuation Gemini call failed: %s", exc)
        explanation = (
            "Valuation explanation unavailable because Gemini could not be reached. "
            "The deterministic verdict is still based on the scraped ratios and can be reviewed below."
        )
        data_gaps.append(f"Gemini valuation explanation unavailable: {exc}")

    logger.info("Valuation verdict=%s gaps=%s", verdict, data_gaps)

    return {
        "valuation_verdict": {
            "verdict": verdict,
            "explanation": explanation,
            "ratios_used": ratios,
            "data_gaps": data_gaps,
        }
    }
