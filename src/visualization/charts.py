"""Publication-grade visualization suite for options spread analysis.

Generates 300 DPI figures matching Figure 1, Figure 2, and Figure 3 from the
Financial Modelling project report (Prof. Mithun Radhakrishna, Group 12):
- Figure 1: Payoff and profit diagrams at expiration for Bull Call and Bear Put spreads
- Figure 2: Sensitivity analysis (Profit vs Volatility, Profit vs Time to Expiry)
- Figure 3: Monte Carlo simulation terminal PnL distribution and multi-path fan charts
Also provides interactive Plotly renderers for the Streamlit dashboard.
"""

from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from src.config import THEME, FIGURES_DIR
from src.strategies.bull_call_spread import BullCallSpread
from src.strategies.bear_put_spread import BearPutSpread
from src.simulation.monte_carlo import simulate_price_paths

# Set Matplotlib dark theme style defaults
plt.rcParams.update({
    "figure.facecolor": THEME["background"],
    "axes.facecolor": THEME["surface"],
    "axes.edgecolor": THEME["border"],
    "axes.labelcolor": THEME["text"],
    "xtick.color": THEME["text_muted"],
    "ytick.color": THEME["text_muted"],
    "grid.color": THEME["grid"],
    "grid.linestyle": "--",
    "grid.alpha": 0.5,
    "legend.facecolor": THEME["surface_light"],
    "legend.edgecolor": THEME["border"],
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 10
})


def plot_bull_call_payoff(
    bull: BullCallSpread,
    s_min: float = 60.0,
    s_max: float = 140.0,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate Figure 1(a): Bull Call Spread Payoff & Profit Diagram."""
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    st = np.linspace(s_min, s_max, 500)
    payoff = bull.payoff(st)
    profit = bull.profit(st)
    be = bull.breakeven()

    # Raw payoff (dashed grey)
    ax.plot(st, payoff, linestyle="--", color="#9E9E9E", linewidth=2.0, label="Payoff at expiration")

    # Profit / Loss (solid green)
    ax.plot(st, profit, color=THEME["profit_green"], linewidth=2.5, label="Profit / Loss")

    # Shaded Profit and Loss zones
    ax.fill_between(st, profit, 0, where=(profit >= 0), color=THEME["profit_green"], alpha=0.25, interpolate=True)
    ax.fill_between(st, profit, 0, where=(profit < 0), color=THEME["loss_red"], alpha=0.25, interpolate=True)

    # Breakeven vertical line
    ax.axvline(x=be, color=THEME["accent_orange"], linestyle="-.", linewidth=2.0, label=f"Breakeven (${be:.2f})")
    ax.axhline(0, color=THEME["text_muted"], linestyle=":", linewidth=1.0, alpha=0.7)

    # Strike markers
    ax.axvline(x=bull.K1, color=THEME["border"], linestyle=":", linewidth=1.2)
    ax.axvline(x=bull.K2, color=THEME["border"], linestyle=":", linewidth=1.2)
    ax.text(bull.K1, -bull.net_debit() - 1.2, f"$K_1$={bull.K1:.1f}", color=THEME["text_muted"], ha="center", fontsize=9)
    ax.text(bull.K2, bull.max_profit() + 0.8, f"$K_2$={bull.K2:.1f}", color=THEME["text_muted"], ha="center", fontsize=9)

    # Annotations
    ax.text(bull.K2 + 6.0, bull.max_profit() - 0.4, f"Max Profit\n${bull.max_profit():.2f}",
            color=THEME["profit_green"], fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=THEME["surface"], edgecolor=THEME["profit_green"], alpha=0.8))
    ax.text(bull.K1 - 6.0, bull.max_loss() + 0.4, f"Max Loss\n${bull.max_loss():.2f}",
            color=THEME["loss_red"], fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=THEME["surface"], edgecolor=THEME["loss_red"], alpha=0.8))

    ax.set_title("(a) Bull Call Spread", color=THEME["text"], fontsize=13, pad=12, fontweight="bold")
    ax.set_xlabel("Stock Price at Expiration ($)", color=THEME["text"], fontsize=11)
    ax.set_ylabel("Profit / Loss ($)", color=THEME["text"], fontsize=11)
    ax.set_xlim(s_min, s_max)
    ax.set_ylim(-6.0, 12.0)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.grid(True)
    ax.legend(loc="upper left", framealpha=0.85)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig


def plot_bear_put_payoff(
    bear: BearPutSpread,
    s_min: float = 60.0,
    s_max: float = 140.0,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate Figure 1(b): Bear Put Spread Payoff & Profit Diagram."""
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    st = np.linspace(s_min, s_max, 500)
    payoff = bear.payoff(st)
    profit = bear.profit(st)
    be = bear.breakeven()

    # Raw payoff (dashed grey)
    ax.plot(st, payoff, linestyle="--", color="#9E9E9E", linewidth=2.0, label="Payoff at expiration")

    # Profit / Loss (solid blue)
    ax.plot(st, profit, color=THEME["accent_blue"], linewidth=2.5, label="Profit / Loss")

    # Shaded Profit and Loss zones
    ax.fill_between(st, profit, 0, where=(profit >= 0), color=THEME["accent_blue"], alpha=0.25, interpolate=True)
    ax.fill_between(st, profit, 0, where=(profit < 0), color=THEME["loss_red"], alpha=0.25, interpolate=True)

    # Breakeven vertical line
    ax.axvline(x=be, color=THEME["accent_orange"], linestyle="-.", linewidth=2.0, label=f"Breakeven (${be:.2f})")
    ax.axhline(0, color=THEME["text_muted"], linestyle=":", linewidth=1.0, alpha=0.7)

    # Strike markers
    ax.axvline(x=bear.K1, color=THEME["border"], linestyle=":", linewidth=1.2)
    ax.axvline(x=bear.K2, color=THEME["border"], linestyle=":", linewidth=1.2)
    ax.text(bear.K1, bear.max_profit() + 0.8, f"$K_1$={bear.K1:.1f}", color=THEME["text_muted"], ha="center", fontsize=9)
    ax.text(bear.K2, -bear.net_debit() - 1.2, f"$K_2$={bear.K2:.1f}", color=THEME["text_muted"], ha="center", fontsize=9)

    # Annotations
    ax.text(bear.K1 - 6.0, bear.max_profit() - 0.4, f"Max Profit\n${bear.max_profit():.2f}",
            color=THEME["accent_blue"], fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=THEME["surface"], edgecolor=THEME["accent_blue"], alpha=0.8))
    ax.text(bear.K2 + 6.0, bear.max_loss() + 0.4, f"Max Loss\n${bear.max_loss():.2f}",
            color=THEME["loss_red"], fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=THEME["surface"], edgecolor=THEME["loss_red"], alpha=0.8))

    ax.set_title("(b) Bear Put Spread", color=THEME["text"], fontsize=13, pad=12, fontweight="bold")
    ax.set_xlabel("Stock Price at Expiration ($)", color=THEME["text"], fontsize=11)
    ax.set_ylabel("Profit / Loss ($)", color=THEME["text"], fontsize=11)
    ax.set_xlim(s_min, s_max)
    ax.set_ylim(-6.0, 12.0)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.grid(True)
    ax.legend(loc="upper right", framealpha=0.85)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig


def plot_combined_payoff_figure(
    bull: BullCallSpread,
    bear: BearPutSpread,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate side-by-side combined Figure 1 (matching report page 9)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=300)
    st = np.linspace(60.0, 140.0, 500)

    # --- (a) Bull Call ---
    p_bull = bull.profit(st)
    be_bull = bull.breakeven()
    ax1.plot(st, bull.payoff(st), "--", color="#9E9E9E", label="Payoff at expiration")
    ax1.plot(st, p_bull, color=THEME["profit_green"], lw=2.2, label="Profit / Loss")
    ax1.fill_between(st, p_bull, 0, where=(p_bull >= 0), color=THEME["profit_green"], alpha=0.25)
    ax1.fill_between(st, p_bull, 0, where=(p_bull < 0), color=THEME["loss_red"], alpha=0.25)
    ax1.axvline(be_bull, color=THEME["accent_orange"], ls="-.", label=f"Breakeven (${be_bull:.2f})")
    ax1.axhline(0, color=THEME["text_muted"], ls=":", alpha=0.6)
    ax1.text(113, bull.max_profit() - 0.5, f"Max Profit\n${bull.max_profit():.2f}", color=THEME["profit_green"],
             ha="center", bbox=dict(facecolor=THEME["surface"], edgecolor=THEME["profit_green"], boxstyle="round"))
    ax1.text(93, bull.max_loss() + 0.4, f"Max Loss\n${bull.max_loss():.2f}", color=THEME["loss_red"],
             ha="center", bbox=dict(facecolor=THEME["surface"], edgecolor=THEME["loss_red"], boxstyle="round"))
    ax1.text(bull.K1, -bull.net_debit() - 1.2, f"$K_1$={bull.K1:.1f}", color=THEME["text_muted"], ha="center")
    ax1.text(bull.K2, -bull.net_debit() - 1.2, f"$K_2$={bull.K2:.1f}", color=THEME["text_muted"], ha="center")
    ax1.set_title("(a) Bull Call Spread", color=THEME["text"], fontweight="bold")
    ax1.set_xlabel("Stock Price at Expiration ($)")
    ax1.set_ylabel("Profit / Loss ($)")
    ax1.set_xlim(60, 140)
    ax1.set_ylim(-6, 12)
    ax1.legend(loc="upper left")
    ax1.grid(True)

    # --- (b) Bear Put ---
    p_bear = bear.profit(st)
    be_bear = bear.breakeven()
    ax2.plot(st, bear.payoff(st), "--", color="#9E9E9E", label="Payoff at expiration")
    ax2.plot(st, p_bear, color=THEME["accent_blue"], lw=2.2, label="Profit / Loss")
    ax2.fill_between(st, p_bear, 0, where=(p_bear >= 0), color=THEME["accent_blue"], alpha=0.25)
    ax2.fill_between(st, p_bear, 0, where=(p_bear < 0), color=THEME["loss_red"], alpha=0.25)
    ax2.axvline(be_bear, color=THEME["accent_orange"], ls="-.", label=f"Breakeven (${be_bear:.2f})")
    ax2.axhline(0, color=THEME["text_muted"], ls=":", alpha=0.6)
    ax2.text(87, bear.max_profit() - 0.5, f"Max Profit\n${bear.max_profit():.2f}", color=THEME["accent_blue"],
             ha="center", bbox=dict(facecolor=THEME["surface"], edgecolor=THEME["accent_blue"], boxstyle="round"))
    ax2.text(107, bear.max_loss() + 0.4, f"Max Loss\n${bear.max_loss():.2f}", color=THEME["loss_red"],
             ha="center", bbox=dict(facecolor=THEME["surface"], edgecolor=THEME["loss_red"], boxstyle="round"))
    ax2.text(bear.K1, -bear.net_debit() - 1.2, f"$K_1$={bear.K1:.1f}", color=THEME["text_muted"], ha="center")
    ax2.text(bear.K2, -bear.net_debit() - 1.2, f"$K_2$={bear.K2:.1f}", color=THEME["text_muted"], ha="center")
    ax2.set_title("(b) Bear Put Spread", color=THEME["text"], fontweight="bold")
    ax2.set_xlabel("Stock Price at Expiration ($)")
    ax2.set_ylabel("Profit / Loss ($)")
    ax2.set_xlim(60, 140)
    ax2.set_ylim(-6, 12)
    ax2.legend(loc="upper right")
    ax2.grid(True)

    fig.suptitle("Bull Call Spread & Bear Put Spread — Payoff & Profit Diagrams",
                 color=THEME["text"], fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig


def plot_volatility_sensitivity(
    S0: float = 100.0,
    K1: float = 100.0,
    K2: float = 110.0,
    T: float = 0.5,
    r: float = 0.05,
    sigmas: Tuple[float, ...] = (0.10, 0.20, 0.30, 0.40),
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate Figure 2(c): Bull Call Spread — Profit vs Volatility."""
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    st = np.linspace(60.0, 140.0, 500)
    colors = ["#00B0FF", "#00E676", "#7C4DFF", "#FF5252"]

    for sigma, color in zip(sigmas, colors):
        b = BullCallSpread(S0=S0, K1=K1, K2=K2, T=T, r=r, sigma=sigma)
        p = b.profit(st)
        ax.plot(st, p, color=color, linewidth=2.0, label=f"$\\sigma$={int(sigma*100)}%")

    ax.axhline(0, color=THEME["text_muted"], linestyle=":", alpha=0.6)
    ax.axvline(K1, color=THEME["border"], linestyle=":", alpha=0.5)
    ax.axvline(K2, color=THEME["border"], linestyle=":", alpha=0.5)

    ax.set_title("(c) Bull Call Spread — Profit vs. Volatility", color=THEME["text"], fontsize=12, fontweight="bold")
    ax.set_xlabel("Stock Price at Expiration ($)")
    ax.set_ylabel("Profit / Loss ($)")
    ax.set_xlim(60, 140)
    ax.set_ylim(-5, 7)
    ax.grid(True)
    ax.legend(loc="upper left", framealpha=0.85)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig


def plot_maturity_sensitivity(
    S0: float = 100.0,
    K1: float = 90.0,
    K2: float = 100.0,
    sigma: float = 0.20,
    r: float = 0.05,
    maturities: Tuple[float, ...] = (0.25, 0.50, 0.75, 1.00),
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate Figure 2(d): Bear Put Spread — Profit vs Time to Expiry."""
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    st = np.linspace(60.0, 140.0, 500)
    colors = ["#FF9100", "#00E676", "#00B0FF", "#7C4DFF"]

    for mat, color in zip(maturities, colors):
        b = BearPutSpread(S0=S0, K1=K1, K2=K2, T=mat, r=r, sigma=sigma)
        p = b.profit(st)
        ax.plot(st, p, color=color, linewidth=2.0, label=f"T={mat:.2f} yr")

    ax.axhline(0, color=THEME["text_muted"], linestyle=":", alpha=0.6)
    ax.axvline(K1, color=THEME["border"], linestyle=":", alpha=0.5)
    ax.axvline(K2, color=THEME["border"], linestyle=":", alpha=0.5)

    ax.set_title("(d) Bear Put Spread — Profit vs. Time to Expiry", color=THEME["text"], fontsize=12, fontweight="bold")
    ax.set_xlabel("Stock Price at Expiration ($)")
    ax.set_ylabel("Profit / Loss ($)")
    ax.set_xlim(60, 140)
    ax.set_ylim(-5, 8)
    ax.grid(True)
    ax.legend(loc="upper right", framealpha=0.85)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig


def plot_monte_carlo_distribution(
    mc_results: dict,
    strategy_name: str = "Bull Call Spread",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """Generate Figure 3(e): Monte Carlo PnL Distribution & POP Overlay."""
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    pnl = mc_results["total_pnl"]
    pop = mc_results["probability_of_profit_pct"]
    exp_pnl = mc_results["expected_total_pnl"]

    # Histogram of simulated total PnL
    n, bins, patches = ax.hist(pnl, bins=60, density=True, alpha=0.75, edgecolor="none")

    # Color bins green for profit (>0) and red for loss (<=0)
    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge >= 0:
            patch.set_facecolor(THEME["profit_green"])
        else:
            patch.set_facecolor(THEME["loss_red"])

    # Zero PnL Breakeven marker
    ax.axvline(0, color=THEME["accent_orange"], linestyle="--", linewidth=2.0, label="Breakeven ($0 PnL)")
    # Expected PnL marker
    ax.axvline(exp_pnl, color=THEME["accent_teal"], linestyle="-.", linewidth=2.0, label=f"Expected PnL (${exp_pnl:.2f})")

    # Badge annotation
    ax.text(0.05, 0.85, f"Monte Carlo: 10,000 Paths\nPOP: {pop:.1f}%\nExpected PnL: ${exp_pnl:.2f}\n95% VaR: ${mc_results['value_at_risk_95']:.2f}",
            transform=ax.transAxes, fontsize=10, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=THEME["surface_light"], edgecolor=THEME["border"], alpha=0.9))

    ax.set_title(f"Monte Carlo Terminal Outcome Distribution: {strategy_name}",
                 color=THEME["text"], fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Total Strategy Profit / Loss ($)")
    ax.set_ylabel("Probability Density")
    ax.grid(True)
    ax.legend(loc="upper right", framealpha=0.85)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    return fig
