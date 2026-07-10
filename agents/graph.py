"""
LangGraph orchestration.

    fundamentals
        /      \\
  valuation   sentiment
        \\      /
    risk_profile
          |
     synthesizer

Valuation and sentiment both only depend on fundamentals' output, so they
run as a fan-out/fan-in stage in parallel — same pattern as your
code-review-agent project. Fundamentals runs first because both
downstream branches (and risk_profile) read its ratios; risk_profile
fans back in after both branches finish; synthesizer runs last, once
every other agent's output is available.

Data collection (scraping) intentionally happens OUTSIDE this graph, in
scrapers/chittorgarh_scraper.py, since it's a one-shot I/O operation
triggered directly by the Streamlit UI, not part of the reasoning chain.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from state import AnalysisState
from agents.fundamentals_agent import fundamentals_node
from agents.valuation_agent import valuation_node
from agents.sentiment_agent import sentiment_node
from agents.risk_agent import risk_profile_node
from agents.synthesizer_agent import synthesizer_node


def build_graph():
    graph = StateGraph(AnalysisState)

    graph.add_node("fundamentals", fundamentals_node)
    graph.add_node("valuation", valuation_node)
    graph.add_node("sentiment", sentiment_node)
    graph.add_node("risk_profile", risk_profile_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "fundamentals")
    graph.add_edge("fundamentals", "valuation")
    graph.add_edge("fundamentals", "sentiment")
    graph.add_edge("valuation", "risk_profile")
    graph.add_edge("sentiment", "risk_profile")
    graph.add_edge("risk_profile", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def analyze_ipo(ipo_full_data, user_profile: dict) -> dict:
    app = build_graph()
    return app.invoke({
        "ipo": ipo_full_data,
        "user_profile": user_profile,
        "errors": [],
    })
