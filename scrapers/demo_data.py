"""
Realistic sample data so you can develop and test the whole pipeline (UI,
agents, financial calcs) without depending on live scraping working yet.
Toggle 'Use demo data' in the Streamlit sidebar to use this.

Numbers are illustrative, not real disclosures.
"""
from __future__ import annotations

from datetime import date, timedelta

from scrapers.models import (
    IPOBasicInfo, IPOCategory, IPOStatus, IPOFinancials,
    SubscriptionData, GMPRecord, IPOFullData,
)

_today = date.today()

DEMO_IPOS: list[IPOBasicInfo] = [
    IPOBasicInfo(
        name="Bharat Precision Components Ltd",
        slug="bharat-precision-components",
        category=IPOCategory.MAINBOARD,
        status=IPOStatus.OPEN,
        open_date=_today - timedelta(days=1),
        close_date=_today + timedelta(days=2),
        price_band_low=410, price_band_high=432,
        lot_size=34, issue_size_cr=850.0,
        exchange="NSE, BSE", sector="Industrial components",
    ),
    IPOBasicInfo(
        name="Nimbus Cloud Logistics Ltd",
        slug="nimbus-cloud-logistics",
        category=IPOCategory.MAINBOARD,
        status=IPOStatus.UPCOMING,
        open_date=_today + timedelta(days=6),
        close_date=_today + timedelta(days=9),
        price_band_low=118, price_band_high=125,
        lot_size=120, issue_size_cr=420.0,
        exchange="NSE, BSE", sector="Logistics tech",
    ),
    IPOBasicInfo(
        name="Suryoday Craft Foods SME",
        slug="suryoday-craft-foods",
        category=IPOCategory.SME,
        status=IPOStatus.OPEN,
        open_date=_today - timedelta(days=2),
        close_date=_today + timedelta(days=1),
        price_band_low=68, price_band_high=72,
        lot_size=1600, issue_size_cr=32.5,
        exchange="NSE SME", sector="FMCG - foods",
    ),
]

DEMO_FULL_DATA: dict[str, IPOFullData] = {
    "bharat-precision-components": IPOFullData(
        basic=DEMO_IPOS[0],
        financials=IPOFinancials(
            revenue_cr=[612.0, 498.0, 401.0],
            pat_cr=[58.0, 41.0, 22.0],
            net_worth_cr=340.0,
            total_debt_cr=210.0,
            eps_pre_ipo=14.8,
            book_value_per_share=112.0,
            ebit_cr=88.0,
            capital_employed_cr=520.0,
            promoter_holding_pre_pct=78.0,
            promoter_holding_post_pct=61.0,
        ),
        subscription=SubscriptionData(
            qib_times=3.2, nii_times=5.8, retail_times=2.1,
            total_times=3.6, as_of="Day 2, 5:00 PM",
        ),
        gmp_history=[
            GMPRecord(date=_today - timedelta(days=2), gmp=28, estimated_listing_price=460),
            GMPRecord(date=_today - timedelta(days=1), gmp=35, estimated_listing_price=467),
            GMPRecord(date=_today, gmp=41, estimated_listing_price=473),
        ],
        anchor_investors=["ABC Mutual Fund", "XYZ Life Insurance"],
        peers=["Precision Forge Ltd", "MetalCraft India Ltd"],
    ),
    "nimbus-cloud-logistics": IPOFullData(
        basic=DEMO_IPOS[1],
        financials=IPOFinancials(
            revenue_cr=[210.0, 140.0, 78.0],
            pat_cr=[-12.0, -18.0, -25.0],
            net_worth_cr=95.0,
            total_debt_cr=140.0,
            eps_pre_ipo=None,
            book_value_per_share=31.0,
            ebit_cr=-9.0,
            capital_employed_cr=235.0,
            promoter_holding_pre_pct=54.0,
            promoter_holding_post_pct=39.0,
        ),
        subscription=None,
        gmp_history=[
            GMPRecord(date=_today - timedelta(days=1), gmp=6, estimated_listing_price=131),
            GMPRecord(date=_today, gmp=4, estimated_listing_price=129),
        ],
        anchor_investors=[],
        peers=["Delhivery Ltd", "TCI Express Ltd"],
    ),
    "suryoday-craft-foods": IPOFullData(
        basic=DEMO_IPOS[2],
        financials=IPOFinancials(
            revenue_cr=[42.0, 33.0, 24.0],
            pat_cr=[4.1, 2.8, 1.5],
            net_worth_cr=18.0,
            total_debt_cr=9.0,
            eps_pre_ipo=5.2,
            book_value_per_share=22.0,
            ebit_cr=5.5,
            capital_employed_cr=27.0,
            promoter_holding_pre_pct=92.0,
            promoter_holding_post_pct=68.0,
        ),
        subscription=SubscriptionData(
            qib_times=1.1, nii_times=12.4, retail_times=18.9,
            total_times=14.2, as_of="Day 2, 3:00 PM",
        ),
        gmp_history=[
            GMPRecord(date=_today - timedelta(days=1), gmp=18, estimated_listing_price=90),
            GMPRecord(date=_today, gmp=22, estimated_listing_price=94),
        ],
        anchor_investors=[],
        peers=["Regional Foods Ltd (SME)"],
    ),
}
