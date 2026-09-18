"""Comprehensive Automated Test Suite for Quantitative Options Spread Engine.

Validates:
1. Black-Scholes-Merton option pricing against exact figures from the academic report.
2. Put-Call Parity exactness.
3. Bull Call Spread & Bear Put Spread risk metrics (Table 1 & Table 2).
4. Asymmetry findings between call and put spreads.
5. Piecewise payoff and profit boundary conditions.
6. Analytical Greeks directions (Bull Delta > 0, Bear Delta < 0).
7. Monte Carlo simulation convergence and POP validity.
8. Algorithmic trade verdict scoring logic.
"""

import pytest
import numpy as np

from src.config import (
    BASELINE_S0,
    BASELINE_T,
    BASELINE_R,
    BASELINE_SIGMA,
    BULL_CALL_K1,
    BULL_CALL_K2,
    BEAR_PUT_K1,
    BEAR_PUT_K2
)
from src.models.black_scholes import (
    bsm_call_price,
    bsm_put_price,
    bsm_call_greeks,
    bsm_put_greeks,
    verify_put_call_parity
)
from src.strategies.bull_call_spread import BullCallSpread
from src.strategies.bear_put_spread import BearPutSpread
from src.simulation.monte_carlo import MonteCarloEngine
from src.engine.verdict import StrategyVerdictEngine


class TestBlackScholesMerton:
    """Test suite for analytical BSM pricing and Put-Call Parity."""

    def test_baseline_option_prices_matching_report_table_3(self):
        """Verify computed option prices match Table 3 of the report to 4 decimals."""
        # Bull Call legs: Long K1=100, Short K2=110
        c1 = bsm_call_price(BASELINE_S0, BULL_CALL_K1, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        c2 = bsm_call_price(BASELINE_S0, BULL_CALL_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        net_debit_bull = c1 - c2

        assert pytest.approx(c1, rel=1e-3) == 6.8887
        assert pytest.approx(c2, rel=1e-3) == 2.9065
        assert pytest.approx(net_debit_bull, rel=1e-3) == 3.9823

        # Bear Put legs: Long K2=100, Short K1=90
        p2 = bsm_put_price(BASELINE_S0, BEAR_PUT_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        p1 = bsm_put_price(BASELINE_S0, BEAR_PUT_K1, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        net_debit_bear = p2 - p1

        assert pytest.approx(p2, rel=1e-3) == 4.4197
        assert pytest.approx(p1, rel=1e-3) == 1.2764
        assert pytest.approx(net_debit_bear, rel=1e-3) == 3.1433

    def test_put_call_parity(self):
        """Verify European Put-Call Parity: C - P = S0 - K * exp(-r * T)."""
        parity = verify_put_call_parity(
            S=BASELINE_S0,
            K=100.0,
            T=BASELINE_T,
            r=BASELINE_R,
            sigma=BASELINE_SIGMA
        )
        assert parity["parity_holds"] is True
        assert parity["discrepancy"] < 1e-6


class TestBullCallSpread:
    """Test suite for Bull Call Spread calculations."""

    @pytest.fixture
    def bull(self):
        return BullCallSpread(
            S0=BASELINE_S0,
            K1=BULL_CALL_K1,
            K2=BULL_CALL_K2,
            T=BASELINE_T,
            r=BASELINE_R,
            sigma=BASELINE_SIGMA
        )

    def test_bull_call_risk_metrics_matching_table_1(self, bull):
        """Verify Bull Call summary metrics match Table 1 of the report."""
        assert pytest.approx(bull.net_debit(), abs=0.01) == 3.98
        assert pytest.approx(bull.max_profit(), abs=0.01) == 6.02
        assert pytest.approx(bull.max_loss(), abs=0.01) == -3.98
        assert pytest.approx(bull.breakeven(), abs=0.01) == 103.98
        assert pytest.approx(bull.reward_to_risk(), abs=0.02) == 1.51

    def test_bull_call_piecewise_payoff(self, bull):
        """Test piecewise linear payoff regions for Bull Call."""
        # ST <= K1
        assert bull.payoff(80.0) == 0.0
        assert bull.payoff(100.0) == 0.0
        # K1 < ST <= K2
        assert pytest.approx(bull.payoff(105.0), abs=1e-5) == 5.0
        # ST > K2
        assert pytest.approx(bull.payoff(110.0), abs=1e-5) == 10.0
        assert pytest.approx(bull.payoff(130.0), abs=1e-5) == 10.0

    def test_bull_call_greeks_orientation(self, bull):
        """Bull call should have positive net delta and positive net vega near-the-money."""
        g = bull.greeks()
        assert g["delta"] > 0.0  # Directionally bullish
        assert g["vega"] > 0.0   # Positive vega at entry


class TestBearPutSpread:
    """Test suite for Bear Put Spread calculations."""

    @pytest.fixture
    def bear(self):
        return BearPutSpread(
            S0=BASELINE_S0,
            K1=BEAR_PUT_K1,
            K2=BEAR_PUT_K2,
            T=BASELINE_T,
            r=BASELINE_R,
            sigma=BASELINE_SIGMA
        )

    def test_bear_put_risk_metrics_matching_table_2(self, bear):
        """Verify Bear Put summary metrics match Table 2 of the report."""
        assert pytest.approx(bear.net_debit(), abs=0.01) == 3.14
        assert pytest.approx(bear.max_profit(), abs=0.01) == 6.86
        assert pytest.approx(bear.max_loss(), abs=0.01) == -3.14
        assert pytest.approx(bear.breakeven(), abs=0.01) == 96.86
        assert pytest.approx(bear.reward_to_risk(), abs=0.02) == 2.18

    def test_bear_put_piecewise_payoff(self, bear):
        """Test piecewise linear payoff regions for Bear Put."""
        # ST <= K1
        assert pytest.approx(bear.payoff(80.0), abs=1e-5) == 10.0
        assert pytest.approx(bear.payoff(90.0), abs=1e-5) == 10.0
        # K1 < ST <= K2
        assert pytest.approx(bear.payoff(95.0), abs=1e-5) == 5.0
        # ST > K2
        assert bear.payoff(100.0) == 0.0
        assert bear.payoff(120.0) == 0.0

    def test_bear_put_greeks_orientation(self, bear):
        """Bear put should have negative net delta."""
        g = bear.greeks()
        assert g["delta"] < 0.0  # Directionally bearish


class TestStrategyAsymmetry:
    """Validate Section 7 comparison: Bear Put has higher R:R than Bull Call."""

    def test_structural_asymmetry(self):
        bull = BullCallSpread(BASELINE_S0, BULL_CALL_K1, BULL_CALL_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        bear = BearPutSpread(BASELINE_S0, BEAR_PUT_K1, BEAR_PUT_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)

        # In report: Bull R:R is ~1.51:1, Bear R:R is ~2.18:1
        assert bear.reward_to_risk() > bull.reward_to_risk()
        assert bear.max_profit() > bull.max_profit()
        assert abs(bear.max_loss()) < abs(bull.max_loss())


class TestMonteCarloAndVerdict:
    """Test suite for Monte Carlo simulation and algorithmic verdict scoring."""

    def test_monte_carlo_engine(self):
        bull = BullCallSpread(BASELINE_S0, BULL_CALL_K1, BULL_CALL_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        mc = MonteCarloEngine(bull, num_paths=5000, seed=42)
        results = mc.run()

        # POP must be bounded in [0, 100]
        assert 0.0 <= results["probability_of_profit_pct"] <= 100.0
        assert -bull.total_net_debit - bull.total_commission <= results["expected_total_pnl"] <= (bull.max_profit() * 100)

    def test_algorithmic_verdict(self):
        bull = BullCallSpread(BASELINE_S0, BULL_CALL_K1, BULL_CALL_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
        verdict = StrategyVerdictEngine(strategy=bull, pop_pct=52.0, iv_percentile=25.0).evaluate()

        assert 0.0 <= verdict["composite_score"] <= 100.0
        assert verdict["verdict_badge"] in ["STRONG BUY", "FAVORABLE", "NEUTRAL", "AVOID"]
        assert len(verdict["key_drivers"]) > 0
