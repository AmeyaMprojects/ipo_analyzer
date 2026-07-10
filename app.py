"""
Indian IPO Analyzer — Streamlit dashboard.
Run with: streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from scrapers.chittorgarh_scraper import fetch_ipo_list, fetch_full_ipo_data
from scrapers.demo_data import DEMO_IPOS, DEMO_FULL_DATA
from scrapers.models import IPOCategory, IPOStatus
from agents.graph import analyze_ipo

st.set_page_config(page_title="Indian IPO Analyzer", layout="wide")

# ---------------------------------------------------------------- sidebar --
st.sidebar.header("Investor Profile")
demo_mode = st.sidebar.toggle("Use demo data", value=False)

investment_amount = st.sidebar.number_input(
    "Investment amount (INR)", min_value=1000, value=50000, step=1000
)
risk_appetite = st.sidebar.radio(
    "Risk appetite", ["conservative", "moderate", "aggressive"], index=1
)
horizon = st.sidebar.radio(
    "Primary goal",
    ["listing_gain", "short_term", "long_term"],
    format_func=lambda x: {
        "listing_gain": "Listing-day gains",
        "short_term": "Short-term (< 1 year)",
        "long_term": "Long-term holding",
    }[x],
)
sme_comfortable = st.sidebar.checkbox("Comfortable with SME IPOs", value=False)
experience = st.sidebar.selectbox("IPO experience", ["first_time", "some", "experienced"])

user_profile = {
    "investment_amount_inr": investment_amount,
    "risk_appetite": risk_appetite,
    "horizon": horizon,
    "sme_comfortable": sme_comfortable,
    "existing_ipo_experience": experience,
}

# ------------------------------------------------------------------ main --
st.title("Indian IPO Analyzer")

if demo_mode:
    ipo_list = DEMO_IPOS
else:
    with st.spinner("Fetching live IPO list..."):
        ipo_list = fetch_ipo_list()
    if not ipo_list:
        st.warning(
            "Live IPO data could not be loaded. Falling back to demo data."
        )
        ipo_list = DEMO_IPOS
        demo_mode = True

# Place filters side by side
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    status_filter = st.multiselect("Status", [s.value for s in IPOStatus], default=["open", "upcoming"])
with filter_col2:
    category_filter = st.multiselect("Category", [c.value for c in IPOCategory], default=["mainboard", "sme"])

filtered = [ipo for ipo in ipo_list if ipo.status.value in status_filter and ipo.category.value in category_filter]

# ------------------------------------------------------- Uniform Grid --
if filtered:
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        row_cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(filtered):
                ipo = filtered[i + j]
                with row_cols[j]:
                    with st.container(border=True, height=350):
                        st.subheader(ipo.name, anchor=False)
                        st.caption(f"{ipo.category.value.upper()} | {ipo.status.value.upper()}")
                        st.divider()
                        st.write(f"Price band: Rs {ipo.price_band_low}-{ipo.price_band_high}")
                        st.write(f"Lot size: {ipo.lot_size}")
                        st.write(f"Dates: {ipo.open_date} to {ipo.close_date}")
                        
                        if st.button("Analyze", key=f"analyze_{ipo.slug}", use_container_width=True):
                            st.session_state["selected_slug"] = ipo.slug
                            st.session_state["selected_ipo"] = ipo
else:
    st.info("No IPOs match the current filters.")

# ------------------------------------------------------------- analysis --
if "selected_ipo" in st.session_state:
    ipo = st.session_state["selected_ipo"]
    st.divider()
    st.header(f"Analysis: {ipo.name}")

    try:
        with st.spinner(
            "Running multi-agent analysis: fundamentals -> valuation + "
            "sentiment (parallel) -> risk profiling -> synthesis..."
        ):
            if demo_mode:
                full_data = DEMO_FULL_DATA[ipo.slug]
            else:
                full_data = fetch_full_ipo_data(ipo)
            result = analyze_ipo(full_data, user_profile)
    except EnvironmentError as exc:
        st.error(str(exc))
        st.stop()

    report = result.get("final_report", {})
    verdict = report.get("suitability_verdict", "unknown")
    verdict_colors = {"strong_fit": "green", "moderate_fit": "blue", "weak_fit": "orange", "avoid": "red"}
    st.markdown(f"### Suitability: :{verdict_colors.get(verdict, 'gray')}[{verdict.replace('_', ' ').title()}]")
    st.write(report.get("one_line_summary", ""))
    st.caption(f"Confidence: {report.get('confidence', 'unknown')}")

    diagnostics = result.get("errors", []) + report.get("data_gaps", []) + result.get("valuation_verdict", {}).get("data_gaps", [])
    if diagnostics:
        with st.expander("Diagnostics and missing data", expanded=False):
            st.write("These are the concrete gaps currently affecting analysis quality:")
            for item in diagnostics:
                st.write(f"- {item}")

    tabs = st.tabs([
        "Financial health", "Valuation", "Market sentiment",
        "Risk assessment", "Personalized reasoning", "Raw data",
    ])

    with tabs[0]:
        st.subheader("Financial health, explained")
        st.write(report.get("financial_health_explained", "No data."))
        st.json(result.get("fundamentals_ratios", {}))

    with tabs[1]:
        st.subheader("Valuation, explained")
        st.write(report.get("valuation_explained", "No data."))
        st.json(result.get("valuation_verdict", {}))

    with tabs[2]:
        st.subheader("Market sentiment (GMP and subscription), explained")
        st.write(report.get("market_sentiment_explained", "No data."))
        st.json(result.get("sentiment_analysis", {}))

    with tabs[3]:
        st.subheader("Risk assessment, explained")
        st.write(report.get("risk_explained", "No data."))
        st.json(result.get("risk_assessment", {}))

    with tabs[4]:
        st.subheader("Why this does (or doesn't) match you")
        st.write(report.get("personalized_reasoning", "No data."))
        if report.get("data_gaps"):
            st.warning("Data gaps affecting confidence: " + "; ".join(report["data_gaps"]))

    with tabs[5]:
        st.json(full_data.model_dump(mode="json"))