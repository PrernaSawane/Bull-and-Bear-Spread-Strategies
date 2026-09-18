"""Bear Put Spread (Debit Put Vertical) implementation.

Constructed by:
- Buying 1 Put at higher strike K2 (premium P2)
- Selling 1 Put at lower strike K1 < K2 (premium P1)
"""

from typing import Dict, Union, Any
import numpy as np
from src.strategies.base import OptionStrategy
from src.models.black_scholes import bsm_put_price, bsm_put_greeks


class BearPutSpread(OptionStrategy):
    """Bear Put Spread Strategy model."""

    def __init__(
        self,
        S0: float,
        K1: float,
        K2: float,
        T: float,
        r: float,
        sigma: float,
        contracts: int = 1,
        multiplier: int = 100,
        commission_per_leg: float = 0.65
    ):
        if K1 >= K2:
            raise ValueError(f"Bear Put Spread requires K1 < K2 (got K1={K1}, K2={K2})")
        super().__init__(S0, T, r, sigma, contracts, multiplier, commission_per_leg)
        self.K1 = float(K1)
        self.K2 = float(K2)

    @property
    def spread_width(self) -> float:
        """Width between strikes (K2 - K1)."""
        return self.K2 - self.K1

    @property
    def long_put_price(self) -> float:
        """BSM premium for the long put leg (K2)."""
        return float(bsm_put_price(self.S0, self.K2, self.T, self.r, self.sigma))

    @property
    def short_put_price(self) -> float:
        """BSM premium for the short put leg (K1)."""
        return float(bsm_put_price(self.S0, self.K1, self.T, self.r, self.sigma))

    def net_debit(self) -> float:
        """Net debit paid per share: D_bear = P2 - P1."""
        return self.long_put_price - self.short_put_price

    def payoff(self, ST: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Expiration payoff per share: max(K2 - ST, 0) - max(K1 - ST, 0)."""
        st = np.asarray(ST, dtype=float)
        payoff_vals = np.maximum(self.K2 - st, 0.0) - np.maximum(self.K1 - st, 0.0)
        return float(payoff_vals) if np.ndim(ST) == 0 else payoff_vals

    def profit(self, ST: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Expiration profit per share: Payoff(ST) - Net Debit."""
        return self.payoff(ST) - self.net_debit()

    def max_profit(self) -> float:
        """Maximum profit per share: (K2 - K1) - Net Debit."""
        return self.spread_width - self.net_debit()

    def max_loss(self) -> float:
        """Maximum loss per share: -Net Debit."""
        return -self.net_debit()

    def breakeven(self) -> float:
        """Underlying price at breakeven: K2 - Net Debit."""
        return self.K2 - self.net_debit()

    def greeks(self) -> Dict[str, float]:
        """Aggregate net position Greeks (Long K2 minus Short K1)."""
        g2 = bsm_put_greeks(self.S0, self.K2, self.T, self.r, self.sigma)
        g1 = bsm_put_greeks(self.S0, self.K1, self.T, self.r, self.sigma)

        return {
            "delta": g2["delta"] - g1["delta"],
            "gamma": g2["gamma"] - g1["gamma"],
            "vega": g2["vega"] - g1["vega"],
            "theta": g2["theta"] - g1["theta"],
            "rho": g2["rho"] - g1["rho"],
            "theta_per_day": g2["theta_per_day"] - g1["theta_per_day"],
            "vega_per_1pct": g2["vega_per_1pct"] - g1["vega_per_1pct"],
            "leg1_delta": -g1["delta"],  # Short K1 put
            "leg2_delta": g2["delta"],   # Long K2 put
            "leg1_price": self.short_put_price,
            "leg2_price": self.long_put_price
        }

    def summary(self) -> Dict[str, Any]:
        """Structured strategy summary metrics."""
        debit = self.net_debit()
        max_p = self.max_profit()
        max_l = self.max_loss()
        be = self.breakeven()
        rr = self.reward_to_risk()

        return {
            "strategy": "Bear Put Spread",
            "type": "Debit Vertical Spread",
            "sentiment": "Moderately Bearish",
            "S0": self.S0,
            "K1": self.K1,
            "K2": self.K2,
            "T": self.T,
            "r": self.r,
            "sigma": self.sigma,
            "contracts": self.contracts,
            "multiplier": self.multiplier,
            "spread_width": self.spread_width,
            "short_leg_premium": self.short_put_price,
            "long_leg_premium": self.long_put_price,
            "net_debit_per_share": debit,
            "max_profit_per_share": max_p,
            "max_loss_per_share": max_l,
            "breakeven": be,
            "reward_to_risk_ratio": rr,
            "total_net_debit": self.total_net_debit,
            "total_commission": self.total_commission,
            "total_outlay": self.total_outlay_with_commissions,
            "total_max_profit": max_p * self.total_shares - self.total_commission,
            "total_max_loss": max_l * self.total_shares - self.total_commission
        }
