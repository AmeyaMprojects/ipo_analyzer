"""
Scraper for chittorgarh.com — the most comprehensive free public source for
Indian IPO data (mainboard + SME): calendar, price band, lot size, GMP,
subscription figures, and RHP financial snapshots.

IMPORTANT — scraping is inherently fragile:
Chittorgarh, like any scraped site, changes its HTML periodically. If this
stops returning data, the fastest fix is almost always just updating the
CSS selectors in the SELECTORS dict below: open the live page in your
browser's devtools, find the new class/id on the element you need, and
swap it in here. Nothing else in the pipeline (agents, financial calcs,
Streamlit UI) needs to change when the site's markup changes.

This module could not be tested against the live site from the build
sandbox (network access there is restricted to package registries), so
treat first-run selector mismatches as expected, not a bug in the logic.
Use demo_mode in the Streamlit app to develop everything else while you
dial in the selectors against the real page.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, date as date_type
from typing import Optional

import requests
from bs4 import BeautifulSoup

from scrapers.models import (
    IPOBasicInfo, IPOCategory, IPOStatus, IPOFinancials,
    SubscriptionData, GMPRecord, IPOFullData,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.chittorgarh.com"
IPO_LIST_URL = f"{BASE_URL}/ipo/ipo_list.asp"
GMP_URL = f"{BASE_URL}/report/latest-ipo-gmp-grey-market-premium/13/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

# Centralised selectors so a site markup change only requires editing this
# one place. Verify/update these against the live page before first use.
SELECTORS = {
    "ipo_table_rows": "table.tb10Table.borderPrimary.tableComponent_table__h8fpS tbody tr, table.table-striped tbody tr",
    "gmp_table_rows": "table.tb10Table.borderPrimary tbody tr, table#gmp_table tbody tr, table.table-striped tbody tr",
    "detail_financials_table": "table#financialTable",
}

IPO_LIST_DATA_URL = "https://webnodejs.chittorgarh.com/cloud/report/data-read/82/1/7/{year}/{year}-27/0/all/0?search="
LIVE_GMP_JSONLD_RE = re.compile(
    r"Current GMP is ₹(?P<gmp>[\d.]+) with an estimated listing price of ₹(?P<listing>[\d.]+)",
    re.IGNORECASE,
)

_session = requests.Session()
_session.headers.update(HEADERS)


def _get(url: str, retries: int = 3, backoff: float = 1.5) -> Optional[BeautifulSoup]:
    for attempt in range(1, retries + 1):
        try:
            resp = _session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as exc:
            logger.warning("Fetch failed (%s/%s) for %s: %s", attempt, retries, url, exc)
            time.sleep(backoff * attempt)
    logger.error("Giving up on %s after %s attempts", url, retries)
    return None


def _parse_float(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", text)
    if cleaned in ("", "-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(text: str) -> Optional[int]:
    val = _parse_float(text)
    return int(val) if val is not None else None


def _parse_date(text: str) -> Optional[date_type]:
    text = (text or "").strip()
    for fmt in ("%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _fetch_report_rows(report_id: int, year: int) -> list[dict[str, str]]:
    url = IPO_LIST_DATA_URL.format(year=year) if report_id == 82 else f"https://webnodejs.chittorgarh.com/cloud/report/data-read/{report_id}/1/7/{year}/{year}-27/0/all/0?search="
    resp = _session.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("reportTableData", [])


def fetch_ipo_list(category: Optional[IPOCategory] = None) -> list[IPOBasicInfo]:
    """Live + upcoming (and recently closed) IPOs.
    Pass category=IPOCategory.SME or IPOCategory.MAINBOARD to filter, or
    leave as None to get both."""
    rows = _fetch_report_rows(82, datetime.now().year)
    results: list[IPOBasicInfo] = []

    for row in rows:
        try:
            company_html = row.get("Company", "")
            company_soup = BeautifulSoup(company_html, "lxml")
            link = company_soup.find("a")
            name = link.get_text(strip=True) if link else re.sub(r"\s+", " ", company_html).strip()
            href = link["href"] if link and link.has_attr("href") else ""
            slug = row.get("~URLRewrite_Folder_Name") or (href.strip("/").split("/")[-2] if href else name.lower().replace(" ", "-"))

            issue_category = (row.get("Issue Category") or "").strip().lower()
            row_category = IPOCategory.SME if issue_category == "sme" or "sme" in href.lower() else IPOCategory.MAINBOARD
            if category is not None and row_category != category:
                continue

            open_date = _parse_date(row.get("Opening Date", "")) or _parse_date(row.get("~Issue_Open_Date", ""))
            close_date = _parse_date(row.get("Closing Date", "")) or _parse_date(row.get("~IssueCloseDate", ""))
            price_text = row.get("Issue Price (Rs.)", "")
            issue_size = _parse_float(row.get("Issue Amount (Rs.cr.)", "")) or _parse_float(row.get("Total Issue Amount (Incl.Firm reservations) (Rs.cr.)", ""))
            lot_size = _parse_int(row.get("~Issue_Lot_Size", "")) or _parse_int(row.get("Lot Size", ""))

            price_low, price_high = None, None
            if "to" in price_text.lower():
                parts = re.split(r"\bto\b", price_text, flags=re.IGNORECASE)
                if len(parts) == 2:
                    price_low, price_high = _parse_float(parts[0]), _parse_float(parts[1])
            elif "-" in price_text:
                parts = price_text.split("-")
                if len(parts) == 2:
                    price_low, price_high = _parse_float(parts[0]), _parse_float(parts[1])
            else:
                price_low = price_high = _parse_float(price_text)

            today = datetime.now().date()
            listing_date = _parse_date(row.get("Listing Date", ""))
            if open_date and close_date:
                if today < open_date:
                    status = IPOStatus.UPCOMING
                elif open_date <= today <= close_date:
                    status = IPOStatus.OPEN
                else:
                    status = IPOStatus.CLOSED
            elif listing_date:
                status = IPOStatus.CLOSED if today > listing_date else IPOStatus.UPCOMING
            else:
                status = IPOStatus.UPCOMING

            results.append(IPOBasicInfo(
                name=name,
                slug=slug,
                category=row_category,
                status=status,
                open_date=open_date,
                close_date=close_date,
                price_band_low=price_low,
                price_band_high=price_high,
                lot_size=lot_size,
                issue_size_cr=issue_size,
                source_url=href if href.startswith("http") else (f"{BASE_URL}{href}" if href else None),
            ))
        except Exception as exc:  # noqa: BLE001 - one bad row shouldn't kill the batch
            logger.warning("Skipping malformed IPO row: %s", exc)
            continue

    return results


def fetch_gmp(slug: str) -> list[GMPRecord]:
    """Fetch the current GMP snapshot from Investorgain's live GMP page.

    Chittorgarh links to this source from the IPO detail page and the page
    exposes the current GMP and estimated listing price in its embedded JSON-LD
    metadata.
    """
    url = f"https://www.investorgain.com/gmp/{slug}-gmp/1940/"
    try:
        resp = _session.get(url, timeout=20)
        resp.raise_for_status()
        match = LIVE_GMP_JSONLD_RE.search(resp.text)
        if not match:
            return []
        return [GMPRecord(
            date=datetime.now().date(),
            gmp=_parse_float(match.group("gmp")),
            estimated_listing_price=_parse_float(match.group("listing")),
        )]
    except requests.RequestException as exc:
        logger.warning("Failed to fetch GMP for %s: %s", slug, exc)
        return []


def fetch_peer_comparison(detail_url: str, company_name: str) -> tuple[Optional[str], list[str]]:
    response = _session.get(detail_url.replace("/ipo/", "/ipo-recommendation/"), timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    if soup is None:
        return None, []

    sector = None
    match = re.search(r"Recently Listed IPOs in ([^<\\]+)", response.text, re.IGNORECASE)
    if match:
        sector = match.group(1).strip()

    peers: list[str] = []
    analysis = soup.find("table", id="analysisTable")
    if analysis:
        for row in analysis.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if not cells:
                continue
            peer_name = cells[0]
            if peer_name and peer_name != company_name and peer_name not in peers:
                peers.append(peer_name)

    return sector, peers


def fetch_subscription(slug: str, detail_url: str) -> Optional[SubscriptionData]:
    subscription_url = detail_url.replace("/ipo/", "/ipo_subscription/")
    soup = _get(subscription_url)
    if soup is None:
        return None

    qib = nii = retail = total = employee = None
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        if "subscription (times)" not in " ".join(header_cells) and "amt" not in " ".join(header_cells):
            continue

        for row in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            label = cells[0].lower()
            value = cells[-1]
            match = re.search(r"([\d.]+)\s*x", value, re.IGNORECASE)
            parsed = _parse_float(match.group(1)) if match else _parse_float(value)

            if "qualified institutional" in label or label == "qib":
                qib = parsed
            elif "non institutional" in label or label in {"nii", "bnii", "snii"}:
                nii = parsed
            elif "retail" in label:
                retail = parsed
            elif "employee" in label:
                employee = parsed
            elif "total subscription" in label or label == "total":
                total = parsed

    return SubscriptionData(
        qib_times=qib,
        nii_times=nii,
        retail_times=retail,
        employee_times=employee,
        total_times=total,
    )


def fetch_financials(detail_url: str, basic: Optional[IPOBasicInfo] = None) -> Optional[IPOFinancials]:
    soup = _get(detail_url)
    if soup is None:
        return None

    revenue, pat = [], []
    total_assets = None
    net_worth = None
    total_debt = None
    ebit_proxy = None
    eps_pre_ipo = None
    pb_value = None
    pe_value = None
    promoter_pre = None
    promoter_post = None

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if not cells:
                continue
            label = cells[0].lower()
            values = [v for c in cells[1:] if (v := _parse_float(c)) is not None]
            first_value = values[0] if values else None

            if ("revenue" in label or "total income" in label) and not revenue:
                revenue = values
            elif ("profit after tax" in label or re.search(r"\bpat\b", label)) and not pat:
                pat = values
            elif label == "assets" and total_assets is None:
                total_assets = first_value
            elif "net worth" in label and net_worth is None:
                net_worth = first_value
            elif "total borrowing" in label and total_debt is None:
                total_debt = first_value
            elif "ebitda" in label and ebit_proxy is None:
                ebit_proxy = first_value
            elif label.startswith("eps") and eps_pre_ipo is None:
                eps_pre_ipo = first_value
            elif (label.startswith("p/e") or label.startswith("pe")) and pe_value is None:
                pe_value = first_value
            elif "promoter holding" in label and promoter_pre is None:
                promoter_pre = values[0] if len(values) > 0 else None
                promoter_post = values[1] if len(values) > 1 else None
            elif ("price to book value" in label or label == "p/b" or "p/bv" in label) and pb_value is None:
                pb_value = first_value

    if basic is not None:
        issue_price = basic.price_band_high or basic.price_band_low
        if eps_pre_ipo is None and pe_value is not None and issue_price:
            eps_pre_ipo = round(issue_price / pe_value, 2)
        if pb_value is not None and issue_price:
            book_value_per_share = round(issue_price / pb_value, 2)
        else:
            book_value_per_share = None
    else:
        book_value_per_share = None

    capital_employed = (net_worth + total_debt) if net_worth is not None and total_debt is not None else None

    return IPOFinancials(
        revenue_cr=revenue,
        pat_cr=pat,
        total_assets_cr=total_assets,
        net_worth_cr=net_worth,
        total_debt_cr=total_debt,
        eps_pre_ipo=eps_pre_ipo,
        book_value_per_share=book_value_per_share,
        ebit_cr=ebit_proxy,
        capital_employed_cr=capital_employed,
        promoter_holding_pre_pct=promoter_pre,
        promoter_holding_post_pct=promoter_post,
    )


def fetch_full_ipo_data(basic: IPOBasicInfo) -> IPOFullData:
    """Aggregates financials + subscription + GMP for one IPO into a single
    record. This is the 'data collector' step feeding the agent pipeline."""
    detail_url = basic.source_url or f"{BASE_URL}/ipo/{basic.slug}/"
    sector, peers = fetch_peer_comparison(detail_url, basic.name)
    enriched_basic = basic.model_copy(update={"sector": sector or basic.sector})
    subscription = fetch_subscription(basic.slug, detail_url)
    if subscription is None and basic.status == IPOStatus.UPCOMING:
        subscription = SubscriptionData(as_of="IPO not open yet; live bidding data not available")
    elif subscription is not None and not any(
        [subscription.qib_times, subscription.nii_times, subscription.retail_times, subscription.total_times]
    ) and basic.status == IPOStatus.UPCOMING:
        subscription.as_of = "IPO not open yet; live bidding data not available"
    return IPOFullData(
        basic=enriched_basic,
        financials=fetch_financials(detail_url, enriched_basic),
        subscription=subscription,
        gmp_history=fetch_gmp(basic.slug),
        peers=peers,
    )
