# Indian IPO Analyzer

A multi-agent tool that pulls live and upcoming Indian IPOs (mainboard +
SME), computes real financial/valuation/sentiment metrics, and produces a
personalized, *explained* suitability report — not just a buy/avoid call.

Not financial advice. GMP, subscription data, and disclosed financials
change quickly and this tool's scraper can go stale — always cross-check
against the RHP/DRHP on SEBI/exchange sites before investing.

## Architecture

```
Streamlit UI (app.py)
   |
   v
Data collector (scrapers/chittorgarh_scraper.py) -- no LLM, pure scraping
   |
   v
LangGraph pipeline (agents/graph.py):

    fundamentals            <- deterministic ratio math, no LLM
        /      \
  valuation   sentiment     <- valuation uses Gemini to explain; sentiment is pure math
        \      /
    risk_profile            <- deterministic score + Gemini explains it for THIS user
          |
     synthesizer            <- Gemini combines everything into the final report
```

Six specialist agents, five of which are graph nodes (data collection runs
once, outside the graph, since it's I/O not reasoning):

| Agent | LLM? | Job |
|---|---|---|
| Data collector | No | Scrapes Chittorgarh for IPO list, financials, GMP, subscription data |
| Fundamentals | No | Computes P/E, P/B, ROE, ROCE, debt/equity, revenue CAGR, margins |
| Valuation | Yes (Gemini) | Explains what the ratios mean; the rich/fair/attractive **verdict itself is rule-based code**, not LLM output |
| Sentiment | No | Scores GMP trend + weighted QIB/NII/retail subscription momentum |
| Risk profiling | Yes (Gemini) | Deterministic risk score from concrete red flags; Gemini explains which factors matter for *this* user's stated profile |
| Synthesizer | Yes (Gemini) | Combines everything into the final report — explicitly instructed not to invent or override any upstream number |

**Why so much of this is non-LLM by design:** ratios, GMP math, and
subscription scoring are pure arithmetic. Making Gemini "explain" numbers
that code already computed — rather than asking Gemini to produce the
numbers itself — means the report can never silently drift from the
underlying data, and every number is independently unit-testable
(see `tests/test_financial_calcs.py`).

## Setup

```bash
cd ipo_analyzer
python -m venv venv && source venv/bin/activate   # or your preferred env tool
pip install -r requirements.txt
cp .env.example .env   # then add your GEMINI_API_KEY
streamlit run app.py
```

Toggle **"Use demo data"** in the sidebar to explore the whole pipeline
(UI, agents, ratio math) immediately with three sample IPOs, without
depending on live scraping working yet or spending Gemini API credits.

## Troubleshooting scraping

Chittorgarh (like any scraped site) changes its HTML periodically. All
CSS selectors live in one place: `SELECTORS` at the top of
`scrapers/chittorgarh_scraper.py`. If `fetch_ipo_list()` returns an empty
list:

1. Open `https://www.chittorgarh.com/ipo/ipo_list.asp` in your browser.
2. Right-click the IPO table -> Inspect -> find the current table/row class.
3. Update `SELECTORS["ipo_table_rows"]` (and the GMP/financials selectors
   similarly, using their respective pages) to match.

The rest of the pipeline doesn't need to change when selectors do — only
this dict.

**Not yet implemented:** direct NSE/BSE API scraping. NSE in particular
requires session-cookie bootstrapping and aggressively rate-limits/blocks
scripted access, which needs more hardening than fits here. Chittorgarh
aggregates NSE + BSE mainboard and SME data already, so it's the
practical single source for now; NSE/BSE direct integration is a natural
next step if you want official-source cross-verification.

## Metric glossary (also shown in-app, per your requirement to explain the mechanics)

- **P/E (Price-to-Earnings)** — price paid per rupee of annual profit.
  Only meaningful vs. sector peers.
- **P/B (Price-to-Book)** — price vs. net asset value per share. Matters
  more for asset-heavy businesses (banks, manufacturing) than asset-light
  ones (SaaS, services).
- **ROE (Return on Equity)** — profit per rupee of shareholder capital.
  \>15% is generally healthy for Indian mainboard companies, sector-dependent.
- **ROCE (Return on Capital Employed)** — profitability vs. *all* capital
  (equity + debt) — fairer than ROE for leveraged companies.
- **Debt-to-Equity** — >1 means the company owes more than shareholders
  invested; higher financial risk.
- **Revenue CAGR** — compound annual growth rate across disclosed fiscal years.
- **GMP (Grey Market Premium)** — an unofficial, unregulated secondary
  indicator of listing-day demand, traded outside SEBI's purview. It's a
  sentiment signal, not a valuation input, and can swing sharply or
  vanish before listing.
- **Subscription multiple (QIB/NII/Retail)** — how many times a category
  was subscribed. QIB (institutional) demand is weighted highest in this
  tool's sentiment score since QIBs typically do the deepest diligence.

## Project layout

```
app.py                       Streamlit entry point
state.py                     Shared LangGraph state schema
agents/
  graph.py                   LangGraph wiring (fan-out/fan-in pipeline)
  fundamentals_agent.py
  valuation_agent.py
  sentiment_agent.py
  risk_agent.py
  synthesizer_agent.py
scrapers/
  models.py                  Pydantic schemas for all IPO data
  chittorgarh_scraper.py     Live data source
  demo_data.py                Offline sample data for development
utils/
  financial_calcs.py         Pure, unit-tested ratio math
  gemini_client.py           LLM wrapper + typed-content-block handling
tests/
  test_financial_calcs.py    9 unit tests, all passing, no network needed
```

## Extending this

- **SME kostak-rate tracking**: `GMPRecord.kostak_rate` is already in the
  schema; wire it up once you've confirmed the selector on Chittorgarh's
  SME GMP page.
- **Anchor investor quality scoring**: `anchor_investors` is collected but
  not yet scored — a good next agent, weighting known large institutional
  names higher.
- **Sector peer P/E benchmarks**: currently the valuation agent only
  reasons over the single IPO's ratios. Scraping a small table of
  sector-median P/E (e.g. from screener.in) and passing it into
  `valuation_node` would make the rich/fair/cheap verdict sector-relative
  instead of using fixed thresholds.
- **NSE/BSE direct scraping** as an official-source cross-check (see
  Troubleshooting above).
