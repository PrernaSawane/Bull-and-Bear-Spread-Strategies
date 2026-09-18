"""Abstract base class for vertical options spread strategies."""

from abc import ABC, abstractmethod
from typing import Dict, Union, Any
import numpy as np


class OptionStrategy(ABC):
    """Abstract interface defining standard vertical spread capabilities."""

    def __init__(
        self,
        S0: float,
        T: float,
        r: float,
        sigma: float,
        contracts: int = 1,
        multiplier: int = 100,
        commission_per_leg: float = 0.65
    ):
        self.S0 = float(S0)
        self.T = float(T)
        self.r = float(r)
        self.sigma = float(sigma)
        self.contracts = int(contracts)
        self.multiplier = int(multiplier)
        self.commission_per_leg = float(commission_per_leg)

    @property
    def total_commission(self) -> float:
        """Total commission for 2 legs (Long and Short)."""
        return 2.0 * self.commission_per_leg * self.contracts

    @property
    def total_shares(self) -> int:
        """Total underlying shares controlled."""
        return self.contracts * self.multiplier

    @abstractmethod
    def net_debit(self) -> float:
        """Net debit paid per share at inception."""
        pass

    @property
    def total_net_debit(self) -> float:
        """Total cash outflow for net debit across all contracts."""
        return self.net_debit() * self.total_shares

    @property
    def total_outlay_with_commissions(self) -> float:
        """Total cash required to enter trade including broker commissions."""
        return self.total_net_debit + self.total_commission

    @abstractmethod
    def payoff(self, ST: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Raw expiration payoff function per share."""
        pass

    @abstractmethod
    def profit(self, ST: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Expiration profit function per share (payoff - net debit)."""
        pass

    def total_profit(self, ST: Union[float, np.ndarray], include_commissions: bool = True) -> Union[float, np.ndarray]:
        """Total dollar profit/loss at expiration across all contracts."""
        raw_pnl = self.profit(ST) * self.total_shares
        if include_commissions:
            return raw_pnl - self.total_commission
        return raw_pnl

    @abstractmethod
    def max_profit(self) -> float:
        """Maximum possible profit per share at expiration."""
        pass

    @abstractmethod
    def max_loss(self) -> float:
        """Maximum possible loss per share at expiration (negative value)."""
        pass

    @abstractmethod
    def breakeven(self) -> float:
        """Stock price at which expiration profit is exactly zero."""
        pass

    def reward_to_risk(self) -> float:
        """Reward-to-risk ratio (Max Profit / |Max Loss|)."""
        loss = abs(self.max_loss())
        return self.max_profit() / loss if loss > 0 else 0.0

    @abstractmethod
    def greeks(self) -> Dict[str, float]:
        """Aggregate net position Greeks at inception."""
        pass

    @abstractmethod
    def summary(self) -> Dict[str, Any]:
        """Structured dictionary of key parameters and computed metrics."""
        pass
