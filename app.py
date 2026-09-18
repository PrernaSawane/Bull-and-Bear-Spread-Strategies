"""Interactive Trading Terminal & Algorithmic Options Spread Engine.

Recreates and elevates the interactive dashboard described in Section 9
of the Financial Derivatives Project Report.
Features:
- Live/Historical Candlestick Chart with overlaid strike barriers (K1, K2)
- Real-time Black-Scholes pricing and dynamic risk metrics
- Expiration payoff and profit profile with breakeven annotations
- Net position Greeks breakdown
- 10,000-path Monte Carlo Geometric Brownian Motion (GBM) engine
- Empirical Probability of Profit (POP) and Algorithmic Recommendation Verdict
- Academic Baseline reproduction tab (matching Table 1, 2, 3, 4)
"""

import sys
from pathlib import Path
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure root directory is on Python path
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
    DEFAULT_COMMISSION_PER_LEG,
    DEFAULT_CONTRACT_MULTIPLIER,
    THEME
)
from src.strategies.bull_call_spread import BullCallSpread
from src.strategies.bear_put_spread import BearPutSpread
from src.simulation.monte_carlo import MonteCarloEngine, simulate_price_paths
from src.engine.verdict import StrategyVerdictEngine
from src.market_data.fetcher import get_market_data

# Page Setup
st.set_page_config(
    page_title="Options Spread Analytics | Bull & Bear Strategies",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Financial Terminal CSS
st.markdown("""
<style>
    .main {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    .metric-card {
        background: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .metric-title {
        color: #9E9E9E;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 1.45rem;
        font-weight: 700;
        font-family: 'SF Mono', 'Courier New', monospace;
    }
    .verdict-box {
        background: #1E222D;
        border-left: 5px solid #00E676;
        border-radius: 6px;
        padding: 16px;
        margin-top: 10px;
    }
    .verdict-box-warn {
        background: #1E222D;
        border-left: 5px solid #FF9100;
        border-radius: 6px;
        padding: 16px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR CONTROLS (Settings & Parameters)
# ==============================================================================
st.sidebar.markdown("## ⚙️ Strategy Settings")

ticker_input = st.sidebar.text_input(
    "Asset Ticker",
    value="AAPL",
    help="Enter any US equity/ETF ticker, or type 'BENCHMARK' to use academic paper baseline ($100)."
)

# Fetch Market Context
with st.spinner("Fetching market telemetry..."):
    hist_df, meta = get_market_data(ticker=ticker_input, fallback_s0=BASELINE_S0)

spot_price = float(meta["spot_price"])
st.sidebar.markdown(f"**Spot Price ($S_0$):** `${spot_price:.2f}`")
if meta.get("is_synthetic"):
    st.sidebar.caption("*(Running in Academic / Offline Simulation Mode)*")

strategy_choice = st.sidebar.radio(
    "Select Strategy",
    options=["Bull Call Spread", "Bear Put Spread"],
    help="Bull Call: Buy K1, Sell K2 (K2 > K1). Bear Put: Buy K2, Sell K1 (K1 < K2)."
)

st.sidebar.markdown("---")
st.sidebar.markdown("## 📊 Trade Parameters")

contracts = st.sidebar.number_input("Number of Contracts (100 shares each)", min_value=1, max_value=500, value=1, step=1)
commission = st.sidebar.number_input("Broker Commission ($ / per leg)", min_value=0.0, max_value=5.0, value=DEFAULT_COMMISSION_PER_LEG, step=0.05)
rate_pct = st.sidebar.slider("Risk-Free Interest Rate (%)", min_value=0.0, max_value=10.0, value=5.0, step=0.25)
vol_pct = st.sidebar.slider("Annualized Volatility (σ %)", min_value=5.0, max_value=100.0, value=round(meta["realized_vol_30d"] * 100, 1), step=1.0)
days_to_expiry = st.sidebar.slider("Days to Expiration (DTE)", min_value=5, max_value=365, value=182, step=1)

T_years = days_to_expiry / 365.0
r_rate = rate_pct / 100.0
sigma_vol = vol_pct / 100.0

st.sidebar.markdown("---")
st.sidebar.markdown("## 🎯 Strike Configuration")

# Dynamic Strike Defaults centered around Spot Price
grid_step = round(max(1.0, spot_price * 0.05), 1)
default_k1 = round((spot_price - (0.0 if strategy_choice == "Bull Call Spread" else grid_step * 2)) / 5) * 5
default_k2 = round((spot_price + (grid_step * 2 if strategy_choice == "Bull Call Spread" else 0.0)) / 5) * 5

if default_k1 >= default_k2:
    default_k2 = default_k1 + 10.0

k1_val = st.sidebar.number_input("Lower Strike (K1)", min_value=1.0, max_value=spot_price * 3.0, value=float(default_k1), step=1.0)
k2_val = st.sidebar.number_input("Higher Strike (K2)", min_value=k1_val + 0.5, max_value=spot_price * 3.0, value=float(default_k2), step=1.0)

# Instantiate selected strategy
if strategy_choice == "Bull Call Spread":
    strategy = BullCallSpread(
        S0=spot_price,
        K1=k1_val,
        K2=k2_val,
        T=T_years,
        r=r_rate,
        sigma=sigma_vol,
        contracts=contracts,
        commission_per_leg=commission
    )
    sentiment_tag = "Moderately Bullish (Debit Call Vertical)"
else:
    strategy = BearPutSpread(
        S0=spot_price,
        K1=k1_val,
        K2=k2_val,
        T=T_years,
        r=r_rate,
        sigma=sigma_vol,
        contracts=contracts,
        commission_per_leg=commission
    )
    sentiment_tag = "Moderately Bearish (Debit Put Vertical)"

summary = strategy.summary()
greeks = strategy.greeks()

# ==============================================================================
# MAIN DASHBOARD INTERFACE
# ==============================================================================
st.title(f"📈 {strategy_choice} Quantitative Terminal")
st.caption(f"**Asset:** {meta.get('company_name', ticker_input)} | **Outlook:** {sentiment_tag} | **Horizon:** {days_to_expiry} Days ({T_years:.2f} yr)")

# High Level Metric Ribbon
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Net Debit / Share</div><div class="metric-value">${summary['net_debit_per_share']:.2f}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Breakeven Price</div><div class="metric-value">${summary['breakeven']:.2f}</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Max Profit ($)</div><div class="metric-value" style="color:#00E676;">${summary['total_max_profit']:.2f}</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Max Loss ($)</div><div class="metric-value" style="color:#FF5252;">${summary['total_max_loss']:.2f}</div></div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Reward-to-Risk</div><div class="metric-value">{summary['reward_to_risk_ratio']:.2f}:1</div></div>""", unsafe_allow_html=True)
with c6:
    st.markdown(f"""<div class="metric-card"><div class="metric-title">Total Outlay</div><div class="metric-value">${summary['total_outlay']:.2f}</div></div>""", unsafe_allow_html=True)

# Tabs
tab_market, tab_payoff, tab_sim, tab_greeks, tab_report = st.tabs([
    "📊 Market Context & Strikes",
    "📈 Payoff & Profit Curve",
    "🎲 Monte Carlo & Algorithmic Verdict",
    "⚡ Greeks & Sensitivity Matrix",
    "📑 Academic Paper Benchmark"
])

# ------------------------------------------------------------------------------
# TAB 1: Market Context & Candlesticks
# ------------------------------------------------------------------------------
with tab_market:
    st.subheader(f"Historical Price Action vs. Strategy Strikes ({ticker_input.upper()})")
    
    fig_candle = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.8, 0.2])
    
    # Candlestick
    fig_candle.add_trace(
        go.Candlestick(
            x=hist_df.index,
            open=hist_df["Open"],
            high=hist_df["High"],
            low=hist_df["Low"],
            close=hist_df["Close"],
            name="OHLC",
            increasing_line_color=THEME["profit_green"],
            decreasing_line_color=THEME["loss_red"]
        ),
        row=1, col=1
    )
    
    # Strike lines
    fig_candle.add_hline(y=k1_val, line_dash="dash", line_color=THEME["accent_orange"],
                         annotation_text=f"K1 Strike: ${k1_val:.2f}", row=1, col=1)
    fig_candle.add_hline(y=k2_val, line_dash="dash", line_color=THEME["accent_teal"],
                         annotation_text=f"K2 Strike: ${k2_val:.2f}", row=1, col=1)
    fig_candle.add_hline(y=summary["breakeven"], line_dash="dot", line_color="#E0E0E0",
                         annotation_text=f"Breakeven: ${summary['breakeven']:.2f}", row=1, col=1)

    # Volume
    colors_vol = [THEME["profit_green"] if c >= o else THEME["loss_red"] for c, o in zip(hist_df["Close"], hist_df["Open"])]
    fig_candle.add_trace(
        go.Bar(x=hist_df.index, y=hist_df["Volume"], name="Volume", marker_color=colors_vol, opacity=0.6),
        row=2, col=1
    )

    fig_candle.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME["background"],
        plot_bgcolor=THEME["surface"],
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_rangeslider_visible=False,
        height=520
    )
    st.plotly_chart(fig_candle, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: Payoff & Profit Curve
# ------------------------------------------------------------------------------
with tab_payoff:
    st.subheader("Expiration Payoff and Net Profit Diagram")
    
    s_range = np.linspace(spot_price * 0.6, spot_price * 1.4, 400)
    payoff_curve = strategy.payoff(s_range)
    profit_curve = strategy.profit(s_range)
    total_profit_curve = strategy.total_profit(s_range, include_commissions=True)

    fig_payoff = go.Figure()

    # Raw Payoff
    fig_payoff.add_trace(go.Scatter(
        x=s_range, y=payoff_curve, mode="lines",
        name="Gross Payoff ($/sh)", line=dict(color="#9E9E9E", dash="dash", width=2)
    ))

    # Profit Curve
    fig_payoff.add_trace(go.Scatter(
        x=s_range, y=profit_curve, mode="lines",
        name="Net Profit ($/sh)", line=dict(color=THEME["profit_green"] if strategy_choice == "Bull Call Spread" else THEME["accent_blue"], width=3)
    ))

    # Breakeven vertical line
    fig_payoff.add_vline(x=summary["breakeven"], line_dash="dashdot", line_color=THEME["accent_orange"],
                         annotation_text=f"Breakeven (${summary['breakeven']:.2f})")
    fig_payoff.add_hline(y=0, line_color="#757575", line_width=1)

    # Shaded regions
    fig_payoff.add_trace(go.Scatter(
        x=s_range, y=np.maximum(profit_curve, 0), fill="tozeroy",
        fillcolor="rgba(0, 230, 118, 0.15)", line=dict(width=0), showlegend=False
    ))
    fig_payoff.add_trace(go.Scatter(
        x=s_range, y=np.minimum(profit_curve, 0), fill="tozeroy",
        fillcolor="rgba(255, 82, 82, 0.15)", line=dict(width=0), showlegend=False
    ))

    fig_payoff.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME["background"],
        plot_bgcolor=THEME["surface"],
        xaxis_title="Underlying Stock Price at Expiration ($)",
        yaxis_title="Profit / Loss ($ per share)",
        margin=dict(l=20, r=20, t=30, b=20),
        height=480,
        hovermode="x unified"
    )
    st.plotly_chart(fig_payoff, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: Monte Carlo & Algorithmic Engine
# ------------------------------------------------------------------------------
with tab_sim:
    st.subheader("🎲 10,000-Path Monte Carlo Simulation & Algorithmic Decision Engine")
    
    col_sim_ctrl1, col_sim_ctrl2 = st.columns([1, 3])
    with col_sim_ctrl1:
        sim_paths = st.slider("Simulation Paths", min_value=1000, max_value=25000, value=10000, step=1000)
        sim_seed = st.number_input("Random Seed", value=42, step=1)
        sim_drift = st.number_input("Expected Annual Drift Rate (μ %)", value=round(r_rate * 100, 2), step=0.5) / 100.0

        mc = MonteCarloEngine(strategy=strategy, num_paths=sim_paths, seed=sim_seed, custom_drift=sim_drift)
        mc_res = mc.run()

        # Algorithmic Verdict
        verdict = StrategyVerdictEngine(strategy=strategy, pop_pct=mc_res["probability_of_profit_pct"], iv_percentile=30.0).evaluate()

        st.markdown(f"""
        <div class="{ 'verdict-box' if verdict['composite_score'] >= 60 else 'verdict-box-warn' }">
            <h4 style="margin:0; color:#FFFFFF;">Algorithmic Verdict</h4>
            <div style="font-size:1.3rem; font-weight:800; color:{'#00E676' if verdict['composite_score'] >= 60 else '#FF9100'};">
                {verdict['rating']}
            </div>
            <p style="margin:6px 0 0 0; color:#E0E0E0; font-size:0.9rem;">
                Composite Quantitative Score: <b>{verdict['composite_score']} / 100</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Tactical Drivers:**")
        for driver in verdict["key_drivers"]:
            st.markdown(f"- {driver}")

    with col_sim_ctrl2:
        # Distribution Histogram of Outcomes
        pnl_data = mc_res["total_pnl"]
        fig_hist = go.Figure()

        # Split into loss and profit bins
        fig_hist.add_trace(go.Histogram(
            x=pnl_data[pnl_data < 0], name="Loss Paths",
            marker_color=THEME["loss_red"], opacity=0.75, nbinsx=40
        ))
        fig_hist.add_trace(go.Histogram(
            x=pnl_data[pnl_data >= 0], name="Profit Paths",
            marker_color=THEME["profit_green"], opacity=0.75, nbinsx=40
        ))

        fig_hist.add_vline(x=0, line_dash="dash", line_color=THEME["accent_orange"],
                           annotation_text="Breakeven ($0 PnL)")
        fig_hist.add_vline(x=mc_res["expected_total_pnl"], line_dash="dot", line_color=THEME["accent_teal"],
                           annotation_text=f"Expected PnL (${mc_res['expected_total_pnl']:.2f})")

        fig_hist.update_layout(
            barmode="overlay",
            template="plotly_dark",
            paper_bgcolor=THEME["background"],
            plot_bgcolor=THEME["surface"],
            xaxis_title="Total Dollar Profit / Loss at Expiration ($)",
            yaxis_title="Path Count",
            margin=dict(l=20, r=20, t=30, b=20),
            height=380,
            showlegend=True
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Statistical Metrics
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Probability of Profit (POP)", f"{mc_res['probability_of_profit_pct']:.1f}%")
        sc2.metric("Expected Total PnL", f"${mc_res['expected_total_pnl']:.2f}")
        sc3.metric("95% Value at Risk (VaR)", f"${mc_res['value_at_risk_95']:.2f}")
        sc4.metric("95% CVaR (Expected Shortfall)", f"${mc_res['conditional_var_95']:.2f}")

# ------------------------------------------------------------------------------
# TAB 4: Greeks & Sensitivity Matrix
# ------------------------------------------------------------------------------
with tab_greeks:
    st.subheader("⚡ Analytical Position Greeks & Sensitivity Matrix")
    
    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
    gc1.metric("Net Delta (Δ)", f"{greeks['delta']:+.4f}", help="Sensitivity to $1 underlying move")
    gc2.metric("Net Gamma (Γ)", f"{greeks['gamma']:+.4f}", help="Rate of change of delta")
    gc3.metric("Net Vega (ν)", f"{greeks['vega_per_1pct']:+.4f}", help="P&L per 1% move in volatility")
    gc4.metric("Daily Theta (Θ)", f"${greeks['theta_per_day']:+.4f}", help="Daily time decay")
    gc5.metric("Net Rho (ρ)", f"{greeks['rho']:+.4f}", help="Sensitivity to interest rates")

    st.markdown("---")
    st.markdown("### Sensitivity Grids (Vol vs. Time to Expiration)")
    sens_vol = [0.10, 0.20, 0.30, 0.40]
    sens_t = [0.25, 0.50, 0.75, 1.00]

    sens_records = []
    for s_vol in sens_vol:
        row = {"Volatility": f"{int(s_vol*100)}%"}
        for t_exp in sens_t:
            if strategy_choice == "Bull Call Spread":
                strat_temp = BullCallSpread(spot_price, k1_val, k2_val, t_exp, r_rate, s_vol)
            else:
                strat_temp = BearPutSpread(spot_price, k1_val, k2_val, t_exp, r_rate, s_vol)
            row[f"T={t_exp:.2f} yr"] = f"${strat_temp.net_debit():.2f} (Max: ${strat_temp.max_profit():.2f})"
        sens_records.append(row)

    st.table(pd.DataFrame(sens_records).set_index("Volatility"))

# ------------------------------------------------------------------------------
# TAB 5: Academic Paper Benchmark Reproduction
# ------------------------------------------------------------------------------
with tab_report:
    st.subheader("📑 Reproduction of Academic Report Baseline (Group 12)")
    st.markdown(r"""
    **Baseline Inputs from Report:**  
    $S_0 = \$100.00$, $T = 0.50\text{ yr}$, $r = 5.0\%$, $\sigma = 20.0\%$  
    - **Bull Call:** $K_1 = \$100.00, K_2 = \$110.00$  
    - **Bear Put:** $K_1 = \$90.00, K_2 = \$100.00$
    """)

    b_bull = BullCallSpread(BASELINE_S0, BULL_CALL_K1, BULL_CALL_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)
    b_bear = BearPutSpread(BASELINE_S0, BEAR_PUT_K1, BEAR_PUT_K2, BASELINE_T, BASELINE_R, BASELINE_SIGMA)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### Table 1: Bull Call Spread (Report vs. Computed)")
        t1 = pd.DataFrame([
            {"Metric": "Maximum Profit", "Formula": "K2 - K1 - D_bull", "Report Value": "$6.02", "Computed": f"${b_bull.max_profit():.4f}"},
            {"Metric": "Maximum Loss", "Formula": "-D_bull", "Report Value": "-$3.98", "Computed": f"-${b_bull.net_debit():.4f}"},
            {"Metric": "Breakeven", "Formula": "K1 + D_bull", "Report Value": "$103.98", "Computed": f"${b_bull.breakeven():.4f}"},
            {"Metric": "Reward:Risk", "Formula": "MaxP / |MaxL|", "Report Value": "1.51:1", "Computed": f"{b_bull.reward_to_risk():.2f}:1"}
        ])
        st.table(t1)

    with col_t2:
        st.markdown("#### Table 2: Bear Put Spread (Report vs. Computed)")
        t2 = pd.DataFrame([
            {"Metric": "Maximum Profit", "Formula": "K2 - K1 - D_bear", "Report Value": "$6.86", "Computed": f"${b_bear.max_profit():.4f}"},
            {"Metric": "Maximum Loss", "Formula": "-D_bear", "Report Value": "-$3.14", "Computed": f"-${b_bear.net_debit():.4f}"},
            {"Metric": "Breakeven", "Formula": "K2 - D_bear", "Report Value": "$96.86", "Computed": f"${b_bear.breakeven():.4f}"},
            {"Metric": "Reward:Risk", "Formula": "MaxP / |MaxL|", "Report Value": "2.18:1", "Computed": f"{b_bear.reward_to_risk():.2f}:1"}
        ])
        st.table(t2)

    st.markdown("#### Table 4: Side-by-Side Asymmetry Analysis")
    t4 = pd.DataFrame([
        {"Feature": "Market Outlook", "Bull Call Spread": "Moderately bullish", "Bear Put Spread": "Moderately bearish"},
        {"Feature": "Net Debit", "Bull Call Spread": f"${b_bull.net_debit():.2f}", "Bear Put Spread": f"${b_bear.net_debit():.2f}"},
        {"Feature": "Maximum Profit", "Bull Call Spread": f"${b_bull.max_profit():.2f}", "Bear Put Spread": f"${b_bear.max_profit():.2f}"},
        {"Feature": "Maximum Loss", "Bull Call Spread": f"-${b_bull.net_debit():.2f}", "Bear Put Spread": f"-${b_bear.net_debit():.2f}"},
        {"Feature": "Breakeven", "Bull Call Spread": f"${b_bull.breakeven():.2f}", "Bear Put Spread": f"${b_bear.breakeven():.2f}"},
        {"Feature": "Reward-to-Risk Ratio", "Bull Call Spread": "1.51:1", "Bear Put Spread": "2.18:1 (Superior)"},
        {"Feature": "Asymmetry Cause", "Bull Call Spread": "Costlier ATM call", "Bear Put Spread": "Discounted OTM put & interest drift"}
    ])
    st.table(t4)
