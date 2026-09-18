"""Algorithmic Decision Engine & Trade Verdict Generator.

Systematically synthesizes Probability of Profit (POP), Reward-to-Risk (R:R) ratio,
Implied Volatility (IV) regime, and expected edge to produce institutional-grade
trade grading and tactical execution verdicts.
"""

from typing import Dict, Any, List
from src.strategies.base import OptionStrategy


class StrategyVerdictEngine:
    """Evaluates option strategies against quantitative risk-reward benchmarks."""

    def __init__(self, strategy: OptionStrategy, pop_pct: float, iv_percentile: float = 30.0):
        self.strategy = strategy
        self.pop_pct = pop_pct
        self.iv_percentile = iv_percentile  # 0-100% IV Rank/Percentile

    def evaluate(self) -> Dict[str, Any]:
        """Compute holistic strategy score and qualitative investment recommendation."""
        rr = self.strategy.reward_to_risk()
        max_profit = self.strategy.max_profit()
        max_loss = abs(self.strategy.max_loss())
        p_win = self.pop_pct / 100.0
        p_loss = 1.0 - p_win

        # Theoretical mathematical edge ($ per share)
        # Simplified binary approximation (win max vs lose max)
        expected_edge = (p_win * max_profit) - (p_loss * max_loss)

        # Quantitative scoring components (0 to 100 total)
        # 1. POP Score (weight 40%)
        # 50% POP maps to 20 pts, 70% maps to 40 pts
        pop_score = max(0.0, min(40.0, (self.pop_pct - 30.0) * (40.0 / 40.0)))

        # 2. Reward-to-Risk Score (weight 35%)
        # 1.0:1 maps to 15 pts, 2.5:1 maps to 35 pts
        rr_score = max(0.0, min(35.0, (rr - 0.5) * (35.0 / 2.0)))

        # 3. IV Regime Score (weight 25%)
        # For debit spreads, lower IV at entry is superior (cheaper premium)
        # IV percentile < 30 gets 25 pts, > 80 gets 5 pts
        iv_score = max(0.0, min(25.0, 25.0 * (1.0 - (self.iv_percentile / 100.0))))

        composite_score = round(pop_score + rr_score + iv_score, 1)

        # Categorical Verdict
        if composite_score >= 75.0:
            rating = "HIGH CONVICTION (STRONG DEPLOY)"
            color = "profit_green"
            verdict_badge = "STRONG BUY"
        elif composite_score >= 60.0:
            rating = "FAVORABLE RISK/REWARD (DEPLOY)"
            color = "accent_teal"
            verdict_badge = "FAVORABLE"
        elif composite_score >= 45.0:
            rating = "NEUTRAL (EXERCISE CAUTION)"
            color = "accent_orange"
            verdict_badge = "NEUTRAL"
        else:
            rating = "UNFAVORABLE (AVOID / RESTRUCTURE)"
            color = "loss_red"
            verdict_badge = "AVOID"

        # Construct analytical rationales
        reasons: List[str] = []
        if self.pop_pct >= 50.0:
            reasons.append(f"Favorable probability of profit ({self.pop_pct:.1f}%), indicating positive statistical drift.")
        else:
            reasons.append(f"Sub-50% probability of profit ({self.pop_pct:.1f}%), requiring directional impulse.")

        if rr >= 1.8:
            reasons.append(f"Attractive asymmetric payout with Reward-to-Risk ratio of {rr:.2f}:1.")
        elif rr >= 1.3:
            reasons.append(f"Moderate Reward-to-Risk ratio ({rr:.2f}:1) in line with standard vertical spreads.")
        else:
            reasons.append(f"Compressed Reward-to-Risk ratio ({rr:.2f}:1), leaving little buffer for risk taken.")

        if self.iv_percentile <= 35.0:
            reasons.append(f"Low implied volatility environment (IV Rank {self.iv_percentile:.0f}%) makes debit options cost-efficient to purchase.")
        elif self.iv_percentile >= 70.0:
            reasons.append(f"High implied volatility (IV Rank {self.iv_percentile:.0f}%) inflates debit paid; consider credit spreads instead.")
        else:
            reasons.append(f"Neutral volatility backdrop (IV Rank {self.iv_percentile:.0f}%).")

        return {
            "composite_score": composite_score,
            "verdict_badge": verdict_badge,
            "rating": rating,
            "color": color,
            "probability_of_profit": self.pop_pct,
            "reward_to_risk": rr,
            "expected_edge_per_share": expected_edge,
            "iv_percentile": self.iv_percentile,
            "score_breakdown": {
                "pop_component": round(pop_score, 1),
                "risk_reward_component": round(rr_score, 1),
                "iv_regime_component": round(iv_score, 1)
            },
            "key_drivers": reasons
        }
