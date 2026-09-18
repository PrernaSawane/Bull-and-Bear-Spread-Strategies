"""Monte Carlo Simulation Engine for Options Spreads.

Simulates terminal stock price paths under Geometric Brownian Motion (GBM):
    S_T = S_0 * exp((mu - 0.5 * sigma^2) * T + sigma * sqrt(T) * Z)
Calculates empirical Probability of Profit (POP), Expected PnL,
Value-at-Risk (VaR), and Conditional Value-at-Risk (CVaR).
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from src.strategies.base import OptionStrategy


def simulate_terminal_prices(
    S0: float,
    T: float,
    sigma: float,
    mu: Optional[float] = None,
    r: float = 0.05,
    num_paths: int = 10000,
    seed: Optional[int] = 42
) -> np.ndarray:
    """Vectorized simulation of terminal stock prices at expiration T.

    Parameters:
    - S0: Current stock price
    - T: Time to expiration in years
    - sigma: Annualized volatility
    - mu: Drift rate (defaults to risk-free rate r if None)
    - r: Risk-free interest rate
    - num_paths: Number of Monte Carlo trajectories
    - seed: Random seed for reproducibility
    """
    drift = r if mu is None else mu
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(num_paths)
    st = S0 * np.exp((drift - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)
    return st


def simulate_price_paths(
    S0: float,
    T: float,
    sigma: float,
    mu: Optional[float] = None,
    r: float = 0.05,
    num_steps: int = 50,
    num_paths: int = 100,
    seed: Optional[int] = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """Simulate complete multi-step price trajectories for fan-chart plotting.

    Returns:
    - time_grid: 1D array of time steps from 0 to T
    - paths: 2D array of shape (num_paths, num_steps + 1)
    """
    drift = r if mu is None else mu
    dt = T / num_steps
    time_grid = np.linspace(0, T, num_steps + 1)

    rng = np.random.default_rng(seed)
    # Brownian increments
    increments = rng.standard_normal((num_paths, num_steps))
    log_returns = (drift - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * increments

    # Accumulate log returns
    log_paths = np.zeros((num_paths, num_steps + 1))
    log_paths[:, 0] = np.log(S0)
    log_paths[:, 1:] = np.log(S0) + np.cumsum(log_returns, axis=1)

    paths = np.exp(log_paths)
    return time_grid, paths


class MonteCarloEngine:
    """Quantitative risk engine evaluating strategy performance across simulated distributions."""

    def __init__(
        self,
        strategy: OptionStrategy,
        num_paths: int = 10000,
        seed: Optional[int] = 42,
        custom_drift: Optional[float] = None
    ):
        self.strategy = strategy
        self.num_paths = int(num_paths)
        self.seed = seed
        self.drift = strategy.r if custom_drift is None else float(custom_drift)

    def run(self) -> Dict[str, Any]:
        """Execute simulation and return comprehensive risk/return distribution metrics."""
        st_sim = simulate_terminal_prices(
            S0=self.strategy.S0,
            T=self.strategy.T,
            sigma=self.strategy.sigma,
            mu=self.drift,
            r=self.strategy.r,
            num_paths=self.num_paths,
            seed=self.seed
        )

        # Profits per share and total dollar PnL
        pnl_per_share = self.strategy.profit(st_sim)
        total_pnl = self.strategy.total_profit(st_sim, include_commissions=True)

        # Empirical Probability of Profit (POP)
        profitable_mask = total_pnl > 0.0
        pop_pct = float(np.mean(profitable_mask) * 100.0)

        # Maximum capped outcomes
        max_pnl_hit = np.isclose(pnl_per_share, self.strategy.max_profit(), atol=1e-3)
        max_loss_hit = np.isclose(pnl_per_share, self.strategy.max_loss(), atol=1e-3)
        prob_max_profit = float(np.mean(max_pnl_hit) * 100.0)
        prob_max_loss = float(np.mean(max_loss_hit) * 100.0)

        # Statistical Moments & Risk Measures
        expected_pnl = float(np.mean(total_pnl))
        median_pnl = float(np.median(total_pnl))
        std_pnl = float(np.std(total_pnl))

        # 95% Historical Simulation VaR and CVaR
        var_95 = float(-np.percentile(total_pnl, 5.0))
        cvar_mask = total_pnl <= -var_95
        cvar_95 = float(-np.mean(total_pnl[cvar_mask])) if np.any(cvar_mask) else var_95

        return {
            "num_paths": self.num_paths,
            "drift_used": self.drift,
            "seed": self.seed,
            "terminal_prices": st_sim,
            "pnl_per_share": pnl_per_share,
            "total_pnl": total_pnl,
            "probability_of_profit_pct": pop_pct,
            "probability_max_profit_pct": prob_max_profit,
            "probability_max_loss_pct": prob_max_loss,
            "expected_total_pnl": expected_pnl,
            "median_total_pnl": median_pnl,
            "std_total_pnl": std_pnl,
            "value_at_risk_95": var_95,
            "conditional_var_95": cvar_95
        }
