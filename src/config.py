"""Configuration and baseline parameters for Bull and Bear Spread Analysis.

Matches the baseline parameters from the Financial Modelling Project Report
under Prof. Mithun Radhakrishna (Group 12):
- S0 = $100.00
- Bull Call Spread: K1 = $100.00, K2 = $110.00
- Bear Put Spread:  K1 = $90.00,  K2 = $100.00
- T = 0.5 years (6 months)
- r = 0.05 (5.0% risk-free rate)
- sigma = 0.20 (20.0% annualized volatility)
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ASSETS_DIR = BASE_DIR / "assets"
FIGURES_DIR = ASSETS_DIR / "figures"
DOCS_DIR = BASE_DIR / "docs"

# Ensure directories exist
for d in [DATA_DIR, PROCESSED_DATA_DIR, ASSETS_DIR, FIGURES_DIR, DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Baseline Parameters from Report
BASELINE_S0 = 100.00
BASELINE_T = 0.50
BASELINE_R = 0.05
BASELINE_SIGMA = 0.20

# Bull Call Spread Baseline Strikes
BULL_CALL_K1 = 100.00
BULL_CALL_K2 = 110.00

# Bear Put Spread Baseline Strikes
BEAR_PUT_K1 = 90.00
BEAR_PUT_K2 = 100.00

# Trading Parameters
DEFAULT_CONTRACT_MULTIPLIER = 100
DEFAULT_COMMISSION_PER_LEG = 0.65  # $0.65 per contract leg

# Sensitivity Analysis Grids
VOLATILITY_GRID = [0.10, 0.20, 0.30, 0.40]
MATURITY_GRID = [0.25, 0.50, 0.75, 1.00]

# Monte Carlo Defaults
DEFAULT_MC_PATHS = 10000
DEFAULT_MC_SEED = 42

# Dark Mode Institutional Theme Palette
THEME = {
    "background": "#0E1117",
    "surface": "#1E222D",
    "surface_light": "#2A2E39",
    "text": "#E0E0E0",
    "text_muted": "#9E9E9E",
    "profit_green": "#00E676",
    "loss_red": "#FF5252",
    "accent_blue": "#2979FF",
    "accent_purple": "#7C4DFF",
    "accent_orange": "#FF9100",
    "accent_teal": "#00B0FF",
    "grid": "#262B35",
    "border": "#363C4E"
}
