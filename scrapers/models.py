"""Pydantic data models for IPO records — the shared schema every scraper,
agent, and the Streamlit UI all speak."""
from __future__ import annotations

from datetime import date as date_type
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IPOCategory(str, Enum):
    MAINBOARD = "mainboard"
    SME = "sme"


class IPOStatus(str, Enum):
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"
    LISTED = "listed"


class IPOBasicInfo(BaseModel):
    name: str
    slug: str  # URL-friendly identifier used to fetch the detail page
    category: IPOCategory
    status: IPOStatus
    open_date: Optional[date_type] = None
    close_date: Optional[date_type] = None
    listing_date: Optional[date_type] = None
    price_band_low: Optional[float] = None
    price_band_high: Optional[float] = None
    lot_size: Optional[int] = None
    issue_size_cr: Optional[float] = Field(None, description="Total issue size, INR crore")
    fresh_issue_cr: Optional[float] = None
    offer_for_sale_cr: Optional[float] = None
    exchange: Optional[str] = None  # NSE / BSE / NSE SME / BSE SME
    sector: Optional[str] = None
    source_url: Optional[str] = None


class IPOFinancials(BaseModel):
    """As disclosed in the RHP/DRHP. Lists are most-recent-fiscal-year first."""
    revenue_cr: list[float] = Field(default_factory=list)
    pat_cr: list[float] = Field(default_factory=list)  # profit after tax
    net_worth_cr: Optional[float] = None
    total_debt_cr: Optional[float] = None
    total_assets_cr: Optional[float] = None
    eps_pre_ipo: Optional[float] = None
    book_value_per_share: Optional[float] = None
    ebit_cr: Optional[float] = None
    capital_employed_cr: Optional[float] = None
    promoter_holding_pre_pct: Optional[float] = None
    promoter_holding_post_pct: Optional[float] = None


class SubscriptionData(BaseModel):
    qib_times: Optional[float] = None
    nii_times: Optional[float] = None
    retail_times: Optional[float] = None
    employee_times: Optional[float] = None
    total_times: Optional[float] = None
    as_of: Optional[str] = None  # e.g. "Day 3, 5:00 PM"


class GMPRecord(BaseModel):
    date: Optional[date_type] = None
    gmp: Optional[float] = None  # grey market premium, INR per share
    estimated_listing_price: Optional[float] = None
    kostak_rate: Optional[float] = None  # SME-specific: price for a full application


class IPOFullData(BaseModel):
    basic: IPOBasicInfo
    financials: Optional[IPOFinancials] = None
    subscription: Optional[SubscriptionData] = None
    gmp_history: list[GMPRecord] = Field(default_factory=list)
    anchor_investors: list[str] = Field(default_factory=list)
    peers: list[str] = Field(default_factory=list)
