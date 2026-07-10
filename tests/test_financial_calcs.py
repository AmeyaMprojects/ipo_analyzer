import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.financial_calcs import (
    pe_ratio, pb_ratio, roe, roce, debt_to_equity, revenue_cagr,
    pat_margin, implied_listing_gain_pct, subscription_momentum_score,
)


def test_pe_ratio():
    assert pe_ratio(100, 5) == 20.0
    assert pe_ratio(100, 0) is None
    assert pe_ratio(100, -2) is None


def test_pb_ratio():
    assert pb_ratio(200, 50) == 4.0
    assert pb_ratio(200, 0) is None


def test_roe():
    assert roe(50, 250) == 20.0
    assert roe(50, 0) is None


def test_roce():
    assert roce(80, 400) == 20.0
    assert roce(80, 0) is None


def test_debt_to_equity():
    assert debt_to_equity(150, 100) == 1.5
    assert debt_to_equity(0, 100) == 0.0
    assert debt_to_equity(100, 0) is None


def test_revenue_cagr():
    # 100 -> 121 over 2 years = 10% CAGR
    assert revenue_cagr([121, 110, 100]) == 10.0
    assert revenue_cagr([100]) is None
    assert revenue_cagr([]) is None


def test_pat_margin():
    assert pat_margin(20, 200) == 10.0
    assert pat_margin(20, 0) is None


def test_implied_listing_gain_pct():
    assert implied_listing_gain_pct(40, 400) == 10.0
    assert implied_listing_gain_pct(40, 0) is None


def test_subscription_momentum_score():
    # all equal at 5x -> weighted score should be 5.0
    assert subscription_momentum_score(5, 5, 5) == 5.0
    # cap at 10x: a 50x retail frenzy shouldn't blow past the 0-10 scale
    score = subscription_momentum_score(2, 3, 50)
    assert 0 <= score <= 10
    assert subscription_momentum_score(None, None, None) is None
    # partial data still produces a score using only available legs
    assert subscription_momentum_score(8, None, None) == 8.0
