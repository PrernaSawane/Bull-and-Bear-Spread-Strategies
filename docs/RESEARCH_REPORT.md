# Bull and Bear Spread Strategies in Options Markets
## Comprehensive Quantitative Research Report & Mathematical Foundations
**Financial Modelling Course Project — Mentored by Prof. Mithun Radhakrishna**  
**Research Team (Group 12):** Jash Bharat Pasad, Jatin Agarwal, Kalabandi Pramith Joy, Sawane Prerna Bharat, Shrey Agarwal  

---

## Executive Summary

Vertical option spreads are among the most widely deployed structural instruments in equity derivatives markets, offering retail and institutional market participants bounded risk profiles, reduced capital entry requirements, and defined maximum payoffs. This research report presents a theoretical derivation, numerical pricing under the Black-Scholes-Merton (BSM) framework, sensitivity analysis, and empirical Monte Carlo validation of two foundational debit vertical spreads:
1. **The Bull Call Spread** (Debit Call Vertical)
2. **The Bear Put Spread** (Debit Put Vertical)

For the baseline asset environment ($S_0 = \$100.00, T = 0.50\text{ yr}, r = 5.0\%, \sigma = 20.0\%$):
- The **Bull Call Spread** ($K_1=\$100, K_2=\$110$) requires a net debit outlay of **\$3.9823** per share, yielding a maximum profit of **\$6.0177** (breakeven at **\$103.9823**) with a Reward-to-Risk ratio of **1.51:1**.
- The **Bear Put Spread** ($K_1=\$90, K_2=\$100$) requires a net debit outlay of **\$3.1433** per share, yielding a maximum profit of **\$6.8567** (breakeven at **\$96.8567**) with a Reward-to-Risk ratio of **2.18:1**.

Our analysis reveals a critical structural asymmetry: **the Bear Put spread delivers a 44% superior reward-to-risk ratio** under identical absolute strike widths and moneyness deltas. We trace this asymmetry to the positive forward drift of the risk-free rate ($S_0 e^{rT}$) and differential time-value decay across moneyness spectrums.

---

## 1. Mathematical Framework & Pricing Engine

### 1.1 Underlying Dynamics (Geometric Brownian Motion)
Under the Black-Scholes-Merton risk-neutral framework, the underlying asset price follows a Geometric Brownian Motion (GBM):
$$dS_t = r S_t dt + \sigma S_t dW_t$$
where $r$ is the continuously compounded risk-free interest rate, $\sigma$ is annualized implied volatility, and $W_t$ is a standard Wiener process.

### 1.2 Closed-Form European Option Premiums
At time $t = 0$, European call ($C$) and put ($P$) premiums with strike $K$ and expiration $T$ are given by:
$$C(S_0, K, T, r, \sigma) = S_0 N(d_1) - K e^{-rT} N(d_2)$$
$$P(S_0, K, T, r, \sigma) = K e^{-rT} N(-d_2) - S_0 N(-d_1)$$

where $N(\cdot)$ is the cumulative standard normal distribution function:
$$N(x) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{x} e^{-\frac{u^2}{2}} du$$
and the dimensionless parameters $d_1$ and $d_2$ are:
$$d_1 = \frac{\ln(S_0 / K) + \left(r + \frac{1}{2}\sigma^2\right)T}{\sigma \sqrt{T}}$$
$$d_2 = d_1 - \sigma \sqrt{T}$$

### 1.3 Put-Call Parity Verification
Arbitrage-free pricing enforces European Put-Call Parity for non-dividend-paying underlyings:
$$C - P = S_0 - K e^{-rT}$$
For $S_0 = \$100, K = \$100, T = 0.5, r = 0.05, \sigma = 0.20$:
$$C = \$6.8887, \quad P = \$4.4197 \implies C - P = \$2.4690$$
$$S_0 - K e^{-rT} = 100 - 100 e^{-0.025} = 100 - 97.53099 = \$2.46901$$
The theoretical identity holds within floating-point precision ($|LHS - RHS| < 10^{-6}$).

---

## 2. Strategy Architectures

### 2.1 The Bull Call Spread
A Bull Call Spread is established by simultaneously:
- Purchasing 1 European Call at lower strike $K_1$ for premium $C_1$.
- Writing 1 European Call at higher strike $K_2 > K_1$ for premium $C_2 < C_1$.

**Cash Flow at Initiation:**
$$D_{\text{bull}} = C_1 - C_2 > 0 \quad \text{(Net Debit)}$$

**Piecewise Expiration Payoff:**
$$\Pi_{\text{bull}}(S_T) = \max(S_T - K_1, 0) - \max(S_T - K_2, 0) = \begin{cases} 0 & S_T \le K_1 \\ S_T - K_1 & K_1 < S_T \le K_2 \\ K_2 - K_1 & S_T > K_2 \end{cases}$$

**Profit Profile & Risk Metrics:**
$$\text{Profit}_{\text{bull}}(S_T) = \Pi_{\text{bull}}(S_T) - D_{\text{bull}}$$
- **Maximum Profit:** $(K_2 - K_1) - D_{\text{bull}} = \$10.00 - \$3.9823 = \$6.0177$
- **Maximum Loss:** $-D_{\text{bull}} = -\$3.9823$
- **Breakeven Threshold:** $S_T^* = K_1 + D_{\text{bull}} = \$100.00 + \$3.9823 = \$103.9823$
- **Reward-to-Risk Ratio:** $\frac{\$6.0177}{\$3.9823} = 1.51:1$

---

### 2.2 The Bear Put Spread
A Bear Put Spread is established by simultaneously:
- Purchasing 1 European Put at higher strike $K_2$ for premium $P_2$.
- Writing 1 European Put at lower strike $K_1 < K_2$ for premium $P_1 < P_2$.

**Cash Flow at Initiation:**
$$D_{\text{bear}} = P_2 - P_1 > 0 \quad \text{(Net Debit)}$$

**Piecewise Expiration Payoff:**
$$\Pi_{\text{bear}}(S_T) = \max(K_2 - S_T, 0) - \max(K_1 - S_T, 0) = \begin{cases} K_2 - K_1 & S_T \le K_1 \\ K_2 - S_T & K_1 < S_T \le K_2 \\ 0 & S_T > K_2 \end{cases}$$

**Profit Profile & Risk Metrics:**
$$\text{Profit}_{\text{bear}}(S_T) = \Pi_{\text{bear}}(S_T) - D_{\text{bear}}$$
- **Maximum Profit:** $(K_2 - K_1) - D_{\text{bear}} = \$10.00 - \$3.1433 = \$6.8567$
- **Maximum Loss:** $-D_{\text{bear}} = -\$3.1433$
- **Breakeven Threshold:** $S_T^* = K_2 - D_{\text{bear}} = \$100.00 - \$3.1433 = \$96.8567$
- **Reward-to-Risk Ratio:** $\frac{\$6.8567}{\$3.1433} = 2.18:1$

---

## 3. Analytical Greeks Derivation

Position Greeks define the sensitivity of the spread portfolio to underlying parameter variations:

| Greek | Mathematical Definition | Bull Call Net Profile | Bear Put Net Profile | Tactical Implication |
| :--- | :--- | :--- | :--- | :--- |
| **Delta ($\Delta$)** | $\frac{\partial V}{\partial S}$ | $N(d_{1, K1}) - N(d_{1, K2}) > 0$ | $N(d_{1, K2}) - N(d_{1, K1}) < 0$ | Directional bias (positive for Bull, negative for Bear) |
| **Gamma ($\Gamma$)** | $\frac{\partial^2 V}{\partial S^2}$ | $\frac{\phi(d_{1, K1})}{S\sigma\sqrt{T}} - \frac{\phi(d_{1, K2})}{S\sigma\sqrt{T}}$ | $\frac{\phi(d_{1, K2})}{S\sigma\sqrt{T}} - \frac{\phi(d_{1, K1})}{S\sigma\sqrt{T}}$ | Curvature acceleration near strikes |
| **Vega ($\mathcal{V}$)** | $\frac{\partial V}{\partial \sigma}$ | $S\sqrt{T}[\phi(d_{1, K1}) - \phi(d_{1, K2})] > 0$ | $S\sqrt{T}[\phi(d_{1, K2}) - \phi(d_{1, K1})] > 0$ | Positive near money; higher IV hurts entry cost |
| **Theta ($\Theta$)** | $\frac{\partial V}{\partial t}$ | $\Theta_{C1} - \Theta_{C2} < 0$ | $\Theta_{P2} - \Theta_{P1} < 0$ | Time decay erosion if underlying stagnates |
| **Rho ($\rho$)** | $\frac{\partial V}{\partial r}$ | $\rho_{C1} - \rho_{C2} > 0$ | $\rho_{P2} - \rho_{P1} < 0$ | Interest rate drift sensitivity |

---

## 4. Empirical Sensitivity Dynamics

### 4.1 Volatility Impact ($\sigma \in [10\%, 40\%]$)
As implied volatility expands:
1. The ATM option ($K_1=100$) gains time value faster than the OTM wing ($K_2=110$).
2. The net debit $D_{\text{bull}}$ expands from $\$2.71$ ($\sigma=10\%$) to $\$4.78$ ($\sigma=40\%$).
3. Maximum potential profit drops from $\$7.29$ to $\$5.22$, reducing the Reward-to-Risk ratio from **2.69:1 down to 1.09:1**.
4. **Takeaway:** Vertical debit spreads should strictly be initiated in **low-to-moderate IV environments**.

### 4.2 Expiration Maturity Impact ($T \in [0.25, 1.00]\text{ yr}$)
As time to expiration extends for the Bear Put spread:
1. The net debit decreases marginally ($D_{\text{bear}}$ drops from $\$3.40$ at $3$ months to $\$2.90$ at $12$ months).
2. Time to expiration has a second-order effect compared to volatility, confirming that directional timing and volatility regime are the primary drivers of trade profitability.

---

## 5. Monte Carlo Simulation Framework (10,000 Paths)

To assess realistic terminal distributions under continuous-time stochastic calculus, we execute a $10,000$-path vectorized Geometric Brownian Motion simulation:
$$S_T^{(i)} = S_0 \exp\left(\left(\mu - \frac{1}{2}\sigma^2\right)T + \sigma \sqrt{T} Z^{(i)}\right), \quad Z^{(i)} \sim \text{i.i.d. } \mathcal{N}(0, 1)$$

### Simulation Findings:
- **Bull Call Probability of Profit (POP):** $42.74\%$ under risk-neutral drift.
- **Bear Put Probability of Profit (POP):** $36.88\%$ under risk-neutral drift.
- **Why POP < 50%:** In an upward-drifting risk-neutral world ($r=5\%$), the underlying expected terminal value is $S_0 e^{rT} = \$102.53$. Because the Bull Call breakeven is $\$103.98$, the underlying must appreciate beyond the expected mean for the position to achieve net profitability. Conversely, the Bear Put requires counter-drift downward movement ($<\$96.86$).

---

## 6. Strategic Conclusions & Implementation Rules

1. **Defined Risk Superiority:** Both vertical spreads eliminate tail risk exposure, ensuring loss never exceeds the entry net debit.
2. **Structural Advantage of Bear Puts:** Due to interest rate drift, Bear Put spreads frequently offer superior Reward-to-Risk ratios (2.18:1 vs 1.51:1) for equivalent strike distances.
3. **Execution Protocol:**
   - Deploy **Bull Call Spreads** when IV Rank $< 35\%$ prior to anticipated positive fundamental catalysts.
   - Deploy **Bear Put Spreads** as cost-effective downside portfolio hedges when systemic volatility is underpriced.

---

## 7. Academic Course Context & Acknowledgments

This research paper and mathematical codebase were prepared for the **Financial Modelling** course under the course mentorship of **Prof. Mithun Radhakrishna**.

- **Course:** Financial Modelling
- **Faculty Mentor:** Prof. Mithun Radhakrishna
- **Authors & Research Team (Group 12):**
  - Jash Bharat Pasad
  - Jatin Agarwal
  - Kalabandi Pramith Joy
  - Sawane Prerna Bharat
  - Shrey Agarwal
