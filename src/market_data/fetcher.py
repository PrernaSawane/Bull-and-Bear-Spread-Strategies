"""Market Data Fetcher & Historical Context Provider.

Retrieves historical OHLCV candle data and implied/realized volatility metrics
using yfinance, with seamless synthetic fallback for offline resilience and
academic benchmark testing (S0 = $100).
"""

from typing import Dict, Any, Tuple
import datetime as dt
import numpy as np
import pandas as pd

try:
    import yfinance as yf
    _YFINANCE_AVAILABLE = True
except ImportError:
    _YFINANCE_AVAILABLE = False


def generate_synthetic_history(
    S0: float = 100.0,
    days: int = 180,
    annual_vol: float = 0.20,
    seed: int = 42
) -> pd.DataFrame:
    """Generate realistic 6-month synthetic daily OHLCV data for offline/benchmark use."""
    rng = np.random.default_rng(seed)
    end_date = dt.date.today()
    date_range = pd.bdate_range(end=end_date, periods=days)

    dt_step = 1.0 / 252.0
    daily_vol = annual_vol * np.sqrt(dt_step)
    returns = rng.normal(0.0003, daily_vol, len(date_range))
    price_series = S0 * np.exp(np.cumsum(returns) - returns.sum())  # Anchor end near S0

    # Generate OHLC
    data = []
    for date, close in zip(date_range, price_series):
        noise = rng.uniform(0.002, 0.015) * close
        high = close + abs(noise)
        low = close - abs(noise)
        open_p = close + rng.uniform(-0.5, 0.5) * noise
        high = max(high, open_p, close)
        low = min(low, open_p, close)
        volume = int(rng.normal(50000000, 10000000))
        data.append({
            "Date": date,
            "Open": round(open_p, 2),
            "High": round(high, 2),
            "Low": round(low, 2),
            "Close": round(close, 2),
            "Volume": max(volume, 1000000)
        })

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    return df


def get_market_data(
    ticker: str = "AAPL",
    period: str = "6mo",
    fallback_s0: float = 100.0
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Fetch 6-month historical price data and summary indicators.

    Returns:
    - df: DataFrame with Open, High, Low, Close, Volume
    - meta: Metadata dictionary with spot price, 30-day realized volatility, etc.
    """
    ticker_clean = ticker.strip().upper()

    if ticker_clean in ["BENCHMARK", "THEORETICAL", "PAPER"]:
        df = generate_synthetic_history(S0=fallback_s0, days=130, annual_vol=0.20)
        spot = fallback_s0
        vol = 0.20
        return df, {
            "ticker": ticker_clean,
            "spot_price": spot,
            "realized_vol_30d": vol,
            "is_synthetic": True,
            "company_name": "Theoretical BSM Benchmark Asset"
        }

    if _YFINANCE_AVAILABLE:
        try:
            t = yf.Ticker(ticker_clean)
            df = t.history(period=period, interval="1d")
            if not df.empty and len(df) > 10:
                spot = float(df["Close"].iloc[-1])
                # Calculate 30-day annualized realized volatility
                log_rets = np.log(df["Close"] / df["Close"].shift(1)).dropna()
                vol_30d = float(log_rets.tail(30).std() * np.sqrt(252)) if len(log_rets) >= 20 else 0.25

                name = ticker_clean
                try:
                    info = t.info
                    name = info.get("shortName") or info.get("longName") or ticker_clean
                except Exception:
                    pass

                return df, {
                    "ticker": ticker_clean,
                    "spot_price": spot,
                    "realized_vol_30d": vol_30d if not np.isnan(vol_30d) else 0.25,
                    "is_synthetic": False,
                    "company_name": name
                }
        except Exception:
            pass  # Fall through to synthetic fallback

    # Fallback if network unavailable or ticker lookup fails
    df = generate_synthetic_history(S0=fallback_s0, days=130, annual_vol=0.22)
    return df, {
        "ticker": ticker_clean,
        "spot_price": float(df["Close"].iloc[-1]),
        "realized_vol_30d": 0.22,
        "is_synthetic": True,
        "company_name": f"{ticker_clean} (Simulated Market Data)"
    }
