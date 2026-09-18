"""CLI Pipeline Runner for Bull & Bear Spread Quantitative Analysis.

Replicates all numerical results, academic tables, sensitivity analyses,
and publication figures from the Financial Derivatives Project Report.
"""

import sys
from pathlib import Path
import sys
import csv
from pathlib import Path
import numpy as np

# Ensure root directory is on path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    BASELINE_S0,
    BASELINE_T,
    BASELINE_R,
    BASELINE_SIGMA,
    BULL_CALL_K1,
    BULL_CALL_K2,
    BEAR_PUT_K1,
    BEAR_PUT_K2,
    VOLATILITY_GRID,
    MATURITY_GRID,
    PROCESSED_DATA_DIR,
    FIGURES_DIR
)
from src.strategies.bull_call_spread import BullCallSpread
from src.strategies.bear_put_spread import BearPutSpread
from src.simulation.monte_carlo import MonteCarloEngine
from src.engine.verdict import StrategyVerdictEngine
from src.visualization.charts import (
    plot_bull_call_payoff,
    plot_bear_put_payoff,
    plot_combined_payoff_figure,
    plot_volatility_sensitivity,
    plot_maturity_sensitivity,
    plot_monte_carlo_distribution
)


def print_and_save_table(data, csv_path):
    """Print ASCII formatted table and save to CSV."""
    if not data:
        return
    headers = list(data[0].keys())
    # Compute column widths
    col_widths = {h: max(len(h), max(len(str(row.get(h, ""))) for row in data)) for h in headers}
    header_line = " | ".join(f"{h:<{col_widths[h]}}" for h in headers)
    sep_line = "-+-".join("-" * col_widths[h] for h in headers)
    print(header_line)
    print(sep_line)
    for row in data:
        print(" | ".join(f"{str(row.get(h, '')):<{col_widths[h]}}" for h in headers))
    # Write CSV
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def run_pipeline():
    print("=" * 76)
    print("  BULL AND BEAR SPREAD STRATEGIES IN OPTIONS MARKETS")
    print("  Financial Derivatives Quantitative Engine (Course Project Group 12)")
    print("=" * 76)

    # 1. Instantiate Strategies with Report Baseline Parameters
    bull = BullCallSpread(
        S0=BASELINE_S0,
        K1=BULL_CALL_K1,
        K2=BULL_CALL_K2,
        T=BASELINE_T,
        r=BASELINE_R,
        sigma=BASELINE_SIGMA
    )
    bear = BearPutSpread(
        S0=BASELINE_S0,
        K1=BEAR_PUT_K1,
        K2=BEAR_PUT_K2,
        T=BASELINE_T,
        r=BASELINE_R,
        sigma=BASELINE_SIGMA
    )

    # ------------------------------------------------------------------
    # TABLE 3: BSM Option Prices and Net Debits (Python Output)
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("  TABLE 3: BSM Option Prices and Net Debits (Python Output)")
    print("-" * 76)
    table3_data = [
        {"Strategy": "Bull Call Spread", "Leg": "Long", "Type": "Call", "Strike": f"${bull.K1:.0f}", "Premium ($)": f"{bull.long_call_price:.4f}"},
        {"Strategy": "Bull Call Spread", "Leg": "Short", "Type": "Call", "Strike": f"${bull.K2:.0f}", "Premium ($)": f"{bull.short_call_price:.4f}"},
        {"Strategy": "Bull Call Spread", "Leg": "Net", "Type": "Debit", "Strike": "-", "Premium ($)": f"{bull.net_debit():.4f}"},
        {"Strategy": "Bear Put Spread", "Leg": "Long", "Type": "Put", "Strike": f"${bear.K2:.0f}", "Premium ($)": f"{bear.long_put_price:.4f}"},
        {"Strategy": "Bear Put Spread", "Leg": "Short", "Type": "Put", "Strike": f"${bear.K1:.0f}", "Premium ($)": f"{bear.short_put_price:.4f}"},
        {"Strategy": "Bear Put Spread", "Leg": "Net", "Type": "Debit", "Strike": "-", "Premium ($)": f"{bear.net_debit():.4f}"}
    ]
    print_and_save_table(table3_data, PROCESSED_DATA_DIR / "table3_bsm_option_prices.csv")

    # ------------------------------------------------------------------
    # TABLE 1: Bull Call Spread Summary Statistics
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("  TABLE 1: Bull Call Spread — Summary Statistics")
    print("-" * 76)
    table1_data = [
        {"Metric": "Maximum Profit", "Formula": "K2 - K1 - D_bull", "Value (Computed)": f"${bull.max_profit():.2f}"},
        {"Metric": "Maximum Loss", "Formula": "-D_bull", "Value (Computed)": f"-${bull.net_debit():.2f}"},
        {"Metric": "Breakeven", "Formula": "K1 + D_bull", "Value (Computed)": f"${bull.breakeven():.2f}"},
        {"Metric": "Reward-to-Risk Ratio", "Formula": "Max Profit / |Max Loss|", "Value (Computed)": f"{bull.reward_to_risk():.2f}:1"}
    ]
    print_and_save_table(table1_data, PROCESSED_DATA_DIR / "table1_bull_call_summary.csv")

    # ------------------------------------------------------------------
    # TABLE 2: Bear Put Spread Summary Statistics
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("  TABLE 2: Bear Put Spread — Summary Statistics")
    print("-" * 76)
    table2_data = [
        {"Metric": "Maximum Profit", "Formula": "K2 - K1 - D_bear", "Value (Computed)": f"${bear.max_profit():.2f}"},
        {"Metric": "Maximum Loss", "Formula": "-D_bear", "Value (Computed)": f"-${bear.net_debit():.2f}"},
        {"Metric": "Breakeven", "Formula": "K2 - D_bear", "Value (Computed)": f"${bear.breakeven():.2f}"},
        {"Metric": "Reward-to-Risk Ratio", "Formula": "Max Profit / |Max Loss|", "Value (Computed)": f"{bear.reward_to_risk():.2f}:1"}
    ]
    print_and_save_table(table2_data, PROCESSED_DATA_DIR / "table2_bear_put_summary.csv")

    # ------------------------------------------------------------------
    # TABLE 4: Side-by-Side Comparison (Computed Values)
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("  TABLE 4: Side-by-Side Comparison (Computed Values)")
    print("-" * 76)
    table4_data = [
        {"Feature": "Market Outlook", "Bull Call Spread": "Moderately bullish", "Bear Put Spread": "Moderately bearish"},
        {"Feature": "Option types used", "Bull Call Spread": "Two calls", "Bear Put Spread": "Two puts"},
        {"Feature": "Cash flow at entry", "Bull Call Spread": "Debit", "Bear Put Spread": "Debit"},
        {"Feature": "Net Debit", "Bull Call Spread": f"${bull.net_debit():.2f}", "Bear Put Spread": f"${bear.net_debit():.2f}"},
        {"Feature": "Maximum Profit", "Bull Call Spread": f"${bull.max_profit():.2f}", "Bear Put Spread": f"${bear.max_profit():.2f}"},
        {"Feature": "Maximum Loss", "Bull Call Spread": f"-${bull.net_debit():.2f}", "Bear Put Spread": f"-${bear.net_debit():.2f}"},
        {"Feature": "Breakeven", "Bull Call Spread": f"${bull.breakeven():.2f}", "Bear Put Spread": f"${bear.breakeven():.2f}"},
        {"Feature": "Reward-to-Risk Ratio", "Bull Call Spread": f"{bull.reward_to_risk():.2f}:1", "Bear Put Spread": f"{bear.reward_to_risk():.2f}:1"},
        {"Feature": "Profit zone", "Bull Call Spread": f"ST > ${bull.breakeven():.2f}", "Bear Put Spread": f"ST < ${bear.breakeven():.2f}"},
        {"Feature": "Theta effect", "Bull Call Spread": "Negative (hurts)", "Bear Put Spread": "Negative (hurts)"},
        {"Feature": "Vega effect", "Bull Call Spread": "Positive (hurts on entry)", "Bear Put Spread": "Positive (hurts on entry)"}
    ]
    print_and_save_table(table4_data, PROCESSED_DATA_DIR / "table4_side_by_side_comparison.csv")

    # ------------------------------------------------------------------
    # MONTE CARLO SIMULATION (10,000 PATHS)
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("  MONTE CARLO SIMULATION (10,000 Geometric Brownian Motion Paths)")
    print("-" * 76)
    mc_bull = MonteCarloEngine(bull, num_paths=10000, seed=42).run()
    mc_bear = MonteCarloEngine(bear, num_paths=10000, seed=42).run()

    print(f"[*] Bull Call Spread: POP = {mc_bull['probability_of_profit_pct']:.2f}% | Exp PnL: ${mc_bull['expected_total_pnl']:.2f} | 95% VaR: ${mc_bull['value_at_risk_95']:.2f}")
    print(f"[*] Bear Put Spread:  POP = {mc_bear['probability_of_profit_pct']:.2f}% | Exp PnL: ${mc_bear['expected_total_pnl']:.2f} | 95% VaR: ${mc_bear['value_at_risk_95']:.2f}")

    # Algorithmic Verdicts
    v_bull = StrategyVerdictEngine(bull, mc_bull['probability_of_profit_pct'], iv_percentile=28.0).evaluate()
    v_bear = StrategyVerdictEngine(bear, mc_bear['probability_of_profit_pct'], iv_percentile=28.0).evaluate()

    print(f"\n[*] Bull Call Verdict: {v_bull['rating']} (Score: {v_bull['composite_score']}/100)")
    print(f"[*] Bear Put Verdict:  {v_bear['rating']} (Score: {v_bear['composite_score']}/100)")

    # ------------------------------------------------------------------
    # GENERATE & SAVE 300-DPI PUBLICATION FIGURES
    # ------------------------------------------------------------------
    print("\n[*] Generating 300 DPI publication figures in assets/figures/...")
    plot_bull_call_payoff(bull, save_path=FIGURES_DIR / "figure1a_bull_call_payoff.png")
    plot_bear_put_payoff(bear, save_path=FIGURES_DIR / "figure1b_bear_put_payoff.png")
    plot_combined_payoff_figure(bull, bear, save_path=FIGURES_DIR / "figure1_combined_spreads.png")
    plot_volatility_sensitivity(save_path=FIGURES_DIR / "figure2c_bull_volatility_sensitivity.png")
    plot_maturity_sensitivity(save_path=FIGURES_DIR / "figure2d_bear_maturity_sensitivity.png")
    plot_monte_carlo_distribution(mc_bull, strategy_name="Bull Call Spread", save_path=FIGURES_DIR / "figure3e_monte_carlo_bull.png")
    plot_monte_carlo_distribution(mc_bear, strategy_name="Bear Put Spread", save_path=FIGURES_DIR / "figure3e_monte_carlo_bear.png")

    print("[OK] All figures saved successfully.")
    print("[OK] Processed tables saved to data/processed/.")
    print("=" * 76)
    print("  EXECUTION COMPLETE: Pipeline ran successfully.")
    print("=" * 76)


if __name__ == "__main__":
    run_pipeline()
