"""
Synthesizer agent — the only node that sees the full picture, and produces
the final report shown in the UI.

Per your requirement, this is explicitly instructed to explain the
technical reasoning alongside the recommendation, not just deliver a
buy/avoid call — and it is told not to override or invent any of the
upstream agents' numbers, only to synthesise and explain them.
"""
from __future__ import annotations

import json

from state import AnalysisState
from utils.gemini_client import get_llm, extract_json

ALLOWED_VERDICTS = {"strong_fit", "moderate_fit", "weak_fit", "avoid"}
DEFAULT_REPORT = {
    "suitability_verdict": "weak_fit",
    "one_line_summary": "Analysis completed with limited confidence.",
    "financial_health_explained": "",
    "valuation_explained": "",
    "market_sentiment_explained": "",
    "risk_explained": "",
    "personalized_reasoning": "",
    "confidence": "low",
    "data_gaps": [],
}

SYSTEM_INSTRUCTIONS = """You are the final-report writer for a personal IPO
analysis tool used by a retail investor. You are given pre-computed,
deterministic data from specialist agents (fundamentals, valuation,
sentiment, risk) — you must not contradict their numbers or invent new
ones. Your job is synthesis and EXPLANATION.

Requirements:
1. Explain the technical reasoning behind the suitability call, not just
   the call itself. Assume the reader wants to learn the mechanics, not
   just be told what to do.
2. Be explicit about what data was missing or unreliable and how that
   limits confidence in the verdict.
3. Give a suitability_verdict from exactly one of: "strong_fit",
   "moderate_fit", "weak_fit", "avoid" — based on how well the IPO's
   risk/return profile matches THIS user's stated profile, not a generic
   "good IPO" rating. A fundamentally strong IPO can still be a weak_fit
   for a conservative first-timer, and a risky IPO can be a strong_fit
   for an aggressive investor chasing listing gains.
 4. Never use "insufficient_data" as the final verdict. If the inputs are
     sparse, choose the closest supported verdict, lower confidence, and
     explain the missing data in "data_gaps".
4. Output ONLY valid JSON, no markdown code fences, matching exactly this
   schema:
{
  "suitability_verdict": "strong_fit|moderate_fit|weak_fit|avoid",
  "one_line_summary": "...",
  "financial_health_explained": "...",
  "valuation_explained": "...",
  "market_sentiment_explained": "...",
  "risk_explained": "...",
  "personalized_reasoning": "...",
  "confidence": "high|medium|low",
  "data_gaps": ["..."]
}"""


def synthesizer_node(state: AnalysisState) -> dict:
    llm = get_llm(temperature=0.2)
    payload = {
        "ipo_name": state["ipo"].basic.name,
        "category": state["ipo"].basic.category.value,
        "user_profile": state.get("user_profile", {}),
        "fundamentals_ratios": state.get("fundamentals_ratios", {}),
        "valuation": state.get("valuation_verdict", {}),
        "sentiment": state.get("sentiment_analysis", {}),
        "risk": state.get("risk_assessment", {}),
        "known_data_gaps": state.get("errors", []),
    }

    try:
        response = llm.invoke([
            ("system", SYSTEM_INSTRUCTIONS),
            ("human", json.dumps(payload)),
        ])
    except Exception as exc:  # noqa: BLE001 - network/transport failures should not crash the graph
        report = dict(DEFAULT_REPORT)
        report["one_line_summary"] = "Report generation failed because Gemini could not be reached."
        report["financial_health_explained"] = ""
        report["valuation_explained"] = ""
        report["market_sentiment_explained"] = ""
        report["risk_explained"] = ""
        report["personalized_reasoning"] = ""
        report["confidence"] = "low"
        report["data_gaps"] = state.get("errors", []) + [f"Gemini transport error: {exc}"]
        report["error"] = str(exc)
        return {"final_report": report}

    try:
        report = extract_json(response)
    except ValueError as exc:
        report = dict(DEFAULT_REPORT)
        report["one_line_summary"] = "Report generation failed — see error below."
        report["financial_health_explained"] = "Report generation failed before the narrative could be assembled."
        report["data_gaps"] = state.get("errors", []) + ["Gemini returned invalid JSON: " + str(exc)]
        report["error"] = str(exc)

    verdict = report.get("suitability_verdict")
    if verdict not in ALLOWED_VERDICTS:
        report.setdefault("data_gaps", [])
        report["data_gaps"].append(f"Gemini returned unsupported verdict '{verdict}', normalized to weak_fit.")
        report["suitability_verdict"] = "weak_fit"
        report["confidence"] = "low"

    for key, value in DEFAULT_REPORT.items():
        report.setdefault(key, value if not isinstance(value, list) else list(value))

    return {"final_report": report}
