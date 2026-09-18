"""Black-Scholes-Merton (BSM) Analytical Pricing Engine & Greeks.

Derives closed-form European call and put prices, along with first- and
second-order option sensitivities (Greeks): Delta, Gamma, Vega, Theta, Rho.
Also provides verification routines for European Put-Call Parity.
"""

from typing import Dict, Union
import numpy as np

try:
    from scipy.stats import norm
    _CDF = norm.cdf
    _PDF = norm.pdf
except ImportError:
    import math
    def _CDF(x):
        return 0.5 * (1.0 + np.vectorize(math.erf)(x / np.sqrt(2.0)))
    def _PDF(x):
        return np.exp(-0.5 * x**2) / np.sqrt(2.0 * np.pi)


def bsm_d1(
    S: Union[float, np.ndarray],
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Union[float, np.ndarray]:
    """Calculate d1 in the Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return np.zeros_like(S, dtype=float) if isinstance(S, np.ndarray) else 0.0
    return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def bsm_d2(
    S: Union[float, np.ndarray],
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Union[float, np.ndarray]:
    """Calculate d2 in the Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return np.zeros_like(S, dtype=float) if isinstance(S, np.ndarray) else 0.0
    return bsm_d1(S, K, T, r, sigma) - sigma * np.sqrt(T)


def bsm_call_price(
    S: Union[float, np.ndarray],
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Union[float, np.ndarray]:
    """Compute European Call option premium via BSM.

    C = S * N(d1) - K * exp(-r * T) * N(d2)
    """
    if T <= 0:
        return np.maximum(S - K, 0.0)
    d1 = bsm_d1(S, K, T, r, sigma)
    d2 = bsm_d2(S, K, T, r, sigma)
    return S * _CDF(d1) - K * np.exp(-r * T) * _CDF(d2)


def bsm_put_price(
    S: Union[float, np.ndarray],
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Union[float, np.ndarray]:
    """Compute European Put option premium via BSM.

    P = K * exp(-r * T) * N(-d2) - S * N(-d1)
    """
    if T <= 0:
        return np.maximum(K - S, 0.0)
    d1 = bsm_d1(S, K, T, r, sigma)
    d2 = bsm_d2(S, K, T, r, sigma)
    return K * np.exp(-r * T) * _CDF(-d2) - S * _CDF(-d1)


def bsm_call_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Dict[str, float]:
    """Compute first and second order analytical Greeks for a European Call."""
    if T <= 0 or sigma <= 0:
        return {
            "delta": 1.0 if S > K else (0.5 if S == K else 0.0),
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho": 0.0,
            "theta_per_day": 0.0,
            "vega_per_1pct": 0.0
        }

    d1 = bsm_d1(S, K, T, r, sigma)
    d2 = bsm_d2(S, K, T, r, sigma)
    pdf_d1 = _PDF(d1)
    cdf_d1 = _CDF(d1)
    cdf_d2 = _CDF(d2)

    delta = float(cdf_d1)
    gamma = float(pdf_d1 / (S * sigma * np.sqrt(T)))
    vega = float(S * np.sqrt(T) * pdf_d1)
    theta = float(- (S * pdf_d1 * sigma) / (2.0 * np.sqrt(T)) - r * K * np.exp(-r * T) * cdf_d2)
    rho = float(K * T * np.exp(-r * T) * cdf_d2)

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
        "theta_per_day": theta / 365.0,
        "vega_per_1pct": vega / 100.0
    }


def bsm_put_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Dict[str, float]:
    """Compute first and second order analytical Greeks for a European Put."""
    if T <= 0 or sigma <= 0:
        return {
            "delta": -1.0 if S < K else (-0.5 if S == K else 0.0),
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0,
            "rho": 0.0,
            "theta_per_day": 0.0,
            "vega_per_1pct": 0.0
        }

    d1 = bsm_d1(S, K, T, r, sigma)
    d2 = bsm_d2(S, K, T, r, sigma)
    pdf_d1 = _PDF(d1)
    cdf_neg_d1 = _CDF(-d1)
    cdf_neg_d2 = _CDF(-d2)

    delta = float(_CDF(d1) - 1.0)  # N(d1) - 1 = -N(-d1)
    gamma = float(pdf_d1 / (S * sigma * np.sqrt(T)))
    vega = float(S * np.sqrt(T) * pdf_d1)
    theta = float(- (S * pdf_d1 * sigma) / (2.0 * np.sqrt(T)) + r * K * np.exp(-r * T) * cdf_neg_d2)
    rho = float(- K * T * np.exp(-r * T) * cdf_neg_d2)

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
        "theta_per_day": theta / 365.0,
        "vega_per_1pct": vega / 100.0
    }


def verify_put_call_parity(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    tolerance: float = 1e-6
) -> Dict[str, Union[float, bool]]:
    """Verify European Put-Call Parity: C - P = S - K * exp(-r * T)."""
    c = float(bsm_call_price(S, K, T, r, sigma))
    p = float(bsm_put_price(S, K, T, r, sigma))
    lhs = c - p
    rhs = S - K * np.exp(-r * T)
    discrepancy = abs(lhs - rhs)
    return {
        "call_price": c,
        "put_price": p,
        "lhs_c_minus_p": lhs,
        "rhs_s_minus_discounted_k": rhs,
        "discrepancy": discrepancy,
        "parity_holds": bool(discrepancy < tolerance)
    }
