/**
 * Quantitative Options Spread Terminal - Core Engine
 * Black-Scholes-Merton Analytics, Monte Carlo Simulation & Interactive Visualizations
 * Financial Derivatives - Group 12
 */

(function () {
    "use strict";

    // --- State Management ---
    const state = {
        strategy: "Bull Call Spread", // or "Bear Put Spread"
        S0: 100.0,
        K1: 100.0,
        K2: 110.0,
        dte: 182,
        T: 182 / 365.0,
        r: 0.05,
        sigma: 0.20,
        contracts: 1,
        multiplier: 100,
        commissionPerLeg: 0.65,
        mcPaths: 10000,
        ticker: "BENCHMARK"
    };

    // Chart instances
    let chartPayoff = null;
    let chartMonteCarlo = null;
    let chartCandle = null;

    // =========================================================================
    // 1. BLACK-SCHOLES-MERTON ANALYTICAL MATH ENGINE
    // =========================================================================

    /**
     * Error function approximation with high precision (Abramowitz & Stegun 7.1.26)
     * Maximum error < 1.5e-7
     */
    function erf(x) {
        const sign = x >= 0 ? 1 : -1;
        x = Math.abs(x);
        const a1 = 0.254829592;
        const a2 = -0.284496736;
        const a3 = 1.421413741;
        const a4 = -1.453152027;
        const a5 = 1.061405429;
        const p = 0.3275911;

        const t = 1.0 / (1.0 + p * x);
        const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
        return sign * y;
    }

    function normCdf(x) {
        return 0.5 * (1.0 + erf(x / Math.SQRT2));
    }

    function normPdf(x) {
        return Math.exp(-0.5 * x * x) / Math.sqrt(2.0 * Math.PI);
    }

    function bsmD1(S, K, T, r, sigma) {
        if (T <= 0 || sigma <= 0) return 0.0;
        return (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
    }

    function bsmD2(S, K, T, r, sigma) {
        if (T <= 0 || sigma <= 0) return 0.0;
        return bsmD1(S, K, T, r, sigma) - sigma * Math.sqrt(T);
    }

    function bsmCallPrice(S, K, T, r, sigma) {
        if (T <= 0) return Math.max(S - K, 0.0);
        const d1 = bsmD1(S, K, T, r, sigma);
        const d2 = bsmD2(S, K, T, r, sigma);
        return S * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2);
    }

    function bsmPutPrice(S, K, T, r, sigma) {
        if (T <= 0) return Math.max(K - S, 0.0);
        const d1 = bsmD1(S, K, T, r, sigma);
        const d2 = bsmD2(S, K, T, r, sigma);
        return K * Math.exp(-r * T) * normCdf(-d2) - S * normCdf(-d1);
    }

    function bsmCallGreeks(S, K, T, r, sigma) {
        if (T <= 0 || sigma <= 0) {
            return { delta: S > K ? 1 : 0, gamma: 0, vega: 0, theta: 0, rho: 0 };
        }
        const d1 = bsmD1(S, K, T, r, sigma);
        const d2 = bsmD2(S, K, T, r, sigma);
        const pdfD1 = normPdf(d1);
        const cdfD1 = normCdf(d1);
        const cdfD2 = normCdf(d2);

        const delta = cdfD1;
        const gamma = pdfD1 / (S * sigma * Math.sqrt(T));
        const vega = S * Math.sqrt(T) * pdfD1;
        const theta = - (S * pdfD1 * sigma) / (2.0 * Math.sqrt(T)) - r * K * Math.exp(-r * T) * cdfD2;
        const rho = K * T * Math.exp(-r * T) * cdfD2;

        return { delta, gamma, vega, theta, rho, thetaDay: theta / 365.0, vega1Pct: vega / 100.0 };
    }

    function bsmPutGreeks(S, K, T, r, sigma) {
        if (T <= 0 || sigma <= 0) {
            return { delta: S < K ? -1 : 0, gamma: 0, vega: 0, theta: 0, rho: 0 };
        }
        const d1 = bsmD1(S, K, T, r, sigma);
        const d2 = bsmD2(S, K, T, r, sigma);
        const pdfD1 = normPdf(d1);
        const cdfNegD2 = normCdf(-d2);

        const delta = normCdf(d1) - 1.0;
        const gamma = pdfD1 / (S * sigma * Math.sqrt(T));
        const vega = S * Math.sqrt(T) * pdfD1;
        const theta = - (S * pdfD1 * sigma) / (2.0 * Math.sqrt(T)) + r * K * Math.exp(-r * T) * cdfNegD2;
        const rho = - K * T * Math.exp(-r * T) * cdfNegD2;

        return { delta, gamma, vega, theta, rho, thetaDay: theta / 365.0, vega1Pct: vega / 100.0 };
    }

    // =========================================================================
    // 2. STRATEGY COMPUTATION & RISK METRICS
    // =========================================================================

    function calculateStrategyMetrics() {
        const S0 = state.S0;
        const K1 = state.K1;
        const K2 = state.K2;
        const T = state.T;
        const r = state.r;
        const sigma = state.sigma;
        const contracts = state.contracts;
        const mult = state.multiplier;
        const totalShares = contracts * mult;
        const totalCommissions = 2.0 * state.commissionPerLeg * contracts;

        let leg1Price = 0, leg2Price = 0, netDebit = 0;
        let maxProfitPerShare = 0, maxLossPerShare = 0, breakeven = 0;
        let greeksNet = {};
        const spreadWidth = K2 - K1;

        if (state.strategy === "Bull Call Spread") {
            // Long Call K1, Short Call K2
            leg1Price = bsmCallPrice(S0, K1, T, r, sigma);
            leg2Price = bsmCallPrice(S0, K2, T, r, sigma);
            netDebit = leg1Price - leg2Price;

            maxProfitPerShare = spreadWidth - netDebit;
            maxLossPerShare = -netDebit;
            breakeven = K1 + netDebit;

            const g1 = bsmCallGreeks(S0, K1, T, r, sigma);
            const g2 = bsmCallGreeks(S0, K2, T, r, sigma);
            greeksNet = {
                delta: g1.delta - g2.delta,
                gamma: g1.gamma - g2.gamma,
                vega: g1.vega - g2.vega,
                theta: g1.theta - g2.theta,
                rho: g1.rho - g2.rho,
                thetaDay: g1.thetaDay - g2.thetaDay,
                vega1Pct: g1.vega1Pct - g2.vega1Pct,
                leg1Greeks: g1,
                leg2Greeks: g2
            };
        } else {
            // Bear Put Spread: Long Put K2, Short Put K1
            leg1Price = bsmPutPrice(S0, K1, T, r, sigma); // Short K1
            leg2Price = bsmPutPrice(S0, K2, T, r, sigma); // Long K2
            netDebit = leg2Price - leg1Price;

            maxProfitPerShare = spreadWidth - netDebit;
            maxLossPerShare = -netDebit;
            breakeven = K2 - netDebit;

            const g1 = bsmPutGreeks(S0, K1, T, r, sigma); // Short
            const g2 = bsmPutGreeks(S0, K2, T, r, sigma); // Long
            greeksNet = {
                delta: g2.delta - g1.delta,
                gamma: g2.gamma - g1.gamma,
                vega: g2.vega - g1.vega,
                theta: g2.theta - g1.theta,
                rho: g2.rho - g1.rho,
                thetaDay: g2.thetaDay - g1.thetaDay,
                vega1Pct: g2.vega1Pct - g1.vega1Pct,
                leg1Greeks: g1,
                leg2Greeks: g2
            };
        }

        const totalNetDebit = netDebit * totalShares;
        const totalOutlay = totalNetDebit + totalCommissions;
        const totalMaxProfit = maxProfitPerShare * totalShares - totalCommissions;
        const totalMaxLoss = maxLossPerShare * totalShares - totalCommissions;
        const rewardToRisk = Math.abs(maxLossPerShare) > 0 ? maxProfitPerShare / Math.abs(maxLossPerShare) : 0;

        return {
            leg1Price,
            leg2Price,
            netDebit,
            maxProfitPerShare,
            maxLossPerShare,
            breakeven,
            rewardToRisk,
            totalShares,
            totalCommissions,
            totalNetDebit,
            totalOutlay,
            totalMaxProfit,
            totalMaxLoss,
            greeksNet,
            spreadWidth
        };
    }

    function calculatePayoff(ST, metrics) {
        const K1 = state.K1;
        const K2 = state.K2;
        let payoff = 0;

        if (state.strategy === "Bull Call Spread") {
            payoff = Math.max(ST - K1, 0) - Math.max(ST - K2, 0);
        } else {
            payoff = Math.max(K2 - ST, 0) - Math.max(K1 - ST, 0);
        }

        const profit = payoff - metrics.netDebit;
        return { payoff, profit };
    }

    // =========================================================================
    // 3. MONTE CARLO SIMULATION ENGINE (10,000 Paths)
    // =========================================================================

    function runMonteCarloSimulation(numPaths = 10000) {
        const S0 = state.S0;
        const T = state.T;
        const r = state.r;
        const sigma = state.sigma;
        const metrics = calculateStrategyMetrics();

        const pnlOutcomes = new Float64Array(numPaths);
        let winCount = 0;
        let sumPnl = 0;

        // Vectorized simulation using Box-Muller normal generation
        for (let i = 0; i < numPaths; i += 2) {
            const u1 = Math.random() || 1e-10;
            const u2 = Math.random();
            const r_bm = Math.sqrt(-2.0 * Math.log(u1));
            const theta_bm = 2.0 * Math.PI * u2;
            const z1 = r_bm * Math.cos(theta_bm);
            const z2 = r_bm * Math.sin(theta_bm);

            // Path 1
            const st1 = S0 * Math.exp((r - 0.5 * sigma * sigma) * T + sigma * Math.sqrt(T) * z1);
            const pnl1 = calculatePayoff(st1, metrics).profit * metrics.totalShares - metrics.totalCommissions;
            pnlOutcomes[i] = pnl1;
            sumPnl += pnl1;
            if (pnl1 > 0) winCount++;

            // Path 2
            if (i + 1 < numPaths) {
                const st2 = S0 * Math.exp((r - 0.5 * sigma * sigma) * T + sigma * Math.sqrt(T) * z2);
                const pnl2 = calculatePayoff(st2, metrics).profit * metrics.totalShares - metrics.totalCommissions;
                pnlOutcomes[i + 1] = pnl2;
                sumPnl += pnl2;
                if (pnl2 > 0) winCount++;
            }
        }

        const popPct = (winCount / numPaths) * 100.0;
        const expectedPnl = sumPnl / numPaths;

        // 95% Historical Value at Risk
        const sortedPnl = Array.from(pnlOutcomes).sort((a, b) => a - b);
        const varIndex = Math.floor(numPaths * 0.05);
        const var95 = sortedPnl[varIndex];

        return {
            numPaths,
            pnlOutcomes,
            popPct,
            expectedPnl,
            var95
        };
    }

    // =========================================================================
    // 4. ALGORITHMIC DECISION ENGINE
    // =========================================================================

    function evaluateStrategyVerdict(metrics, popPct) {
        const rr = metrics.rewardToRisk;
        const ivRank = 30.0; // Moderate IV assumption

        const popScore = Math.max(0, Math.min(40, (popPct - 30) * (40 / 40)));
        const rrScore = Math.max(0, Math.min(35, (rr - 0.5) * (35 / 2.0)));
        const ivScore = Math.max(0, Math.min(25, 25 * (1 - (ivRank / 100))));
        const totalScore = Math.round(popScore + rrScore + ivScore);

        let title = "NEUTRAL";
        let color = "var(--amber-warning)";
        let drivers = [];

        if (totalScore >= 75) {
            title = "HIGH CONVICTION (DEPLOY)";
            color = "var(--green-profit)";
        } else if (totalScore >= 60) {
            title = "FAVORABLE RISK/REWARD";
            color = "var(--cyan-accent)";
        } else if (totalScore >= 45) {
            title = "NEUTRAL / MODERATE EDGE";
            color = "var(--amber-warning)";
        } else {
            title = "UNFAVORABLE (AVOID)";
            color = "var(--red-loss)";
        }

        if (popPct >= 48) {
            drivers.push(`Favorable statistical win probability (${popPct.toFixed(1)}%).`);
        } else {
            drivers.push(`Sub-50% probability (${popPct.toFixed(1)}%) requires directional impulse.`);
        }

        if (rr >= 1.8) {
            drivers.push(`Strong asymmetric payout with Reward-to-Risk ratio of ${rr.toFixed(2)}:1.`);
        } else {
            drivers.push(`Standard vertical spread payout ratio of ${rr.toFixed(2)}:1.`);
        }

        drivers.push(`Low-to-moderate IV backdrop makes entry debit capital-efficient.`);

        return { totalScore, title, color, drivers };
    }

    // =========================================================================
    // 5. CHART VISUALIZATION RENDERERS
    // =========================================================================

    function renderPayoffChart(metrics) {
        const ctx = document.getElementById("chartPayoff").getContext("2d");
        const S0 = state.S0;
        const sMin = Math.max(10, S0 * 0.6);
        const sMax = S0 * 1.4;
        const steps = 120;
        const stepSize = (sMax - sMin) / steps;

        const labels = [];
        const payoffData = [];
        const profitData = [];

        for (let i = 0; i <= steps; i++) {
            const st = sMin + i * stepSize;
            labels.push(st.toFixed(1));
            const calc = calculatePayoff(st, metrics);
            payoffData.push(calc.payoff);
            profitData.push(calc.profit);
        }

        const isBull = state.strategy === "Bull Call Spread";
        const accentColor = isBull ? "#00E676" : "#2979FF";

        if (chartPayoff) chartPayoff.destroy();

        chartPayoff = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Gross Payoff ($/sh)",
                        data: payoffData,
                        borderColor: "#94A3B8",
                        borderDash: [6, 6],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: "Net Profit / Loss ($/sh)",
                        data: profitData,
                        borderColor: accentColor,
                        borderWidth: 3,
                        pointRadius: 0,
                        fill: {
                            target: { value: 0 },
                            above: "rgba(0, 230, 118, 0.15)",
                            below: "rgba(255, 82, 82, 0.15)"
                        }
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false
                },
                plugins: {
                    legend: {
                        labels: { color: "#F0F4F8", font: { family: "Outfit", size: 12 } }
                    },
                    tooltip: {
                        backgroundColor: "#1B2232",
                        titleColor: "#00E5FF",
                        bodyColor: "#FFFFFF",
                        borderColor: "#3A4660",
                        borderWidth: 1,
                        callbacks: {
                            title: (ctx) => `Stock Price: $${ctx[0].label}`,
                            label: (ctx) => `${ctx.dataset.label}: $${Number(ctx.raw).toFixed(2)}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", font: { family: "JetBrains Mono" }, maxTicksLimit: 12 },
                        title: { display: true, text: "Underlying Stock Price at Expiration ($)", color: "#94A3B8" }
                    },
                    y: {
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", font: { family: "JetBrains Mono" } },
                        title: { display: true, text: "Profit / Loss ($ per share)", color: "#94A3B8" }
                    }
                }
            }
        });
    }

    function renderMonteCarloChart(mcResults, metrics) {
        const ctx = document.getElementById("chartMonteCarlo").getContext("2d");
        const pnl = mcResults.pnlOutcomes;

        // Create 35 histogram bins
        const minPnl = metrics.totalMaxLoss * 1.05;
        const maxPnl = metrics.totalMaxProfit * 1.05;
        const binCount = 35;
        const binWidth = (maxPnl - minPnl) / binCount;

        const binLabels = [];
        const lossCounts = new Array(binCount).fill(0);
        const profitCounts = new Array(binCount).fill(0);

        for (let b = 0; b < binCount; b++) {
            const center = minPnl + (b + 0.5) * binWidth;
            binLabels.push(`$${center.toFixed(0)}`);
        }

        for (let i = 0; i < pnl.length; i++) {
            const val = pnl[i];
            let bIndex = Math.floor((val - minPnl) / binWidth);
            bIndex = Math.max(0, Math.min(binCount - 1, bIndex));

            if (val >= 0) {
                profitCounts[bIndex]++;
            } else {
                lossCounts[bIndex]++;
            }
        }

        if (chartMonteCarlo) chartMonteCarlo.destroy();

        chartMonteCarlo = new Chart(ctx, {
            type: "bar",
            data: {
                labels: binLabels,
                datasets: [
                    {
                        label: "Loss Trajectories (< $0)",
                        data: lossCounts,
                        backgroundColor: "rgba(255, 82, 82, 0.75)",
                        borderRadius: 3
                    },
                    {
                        label: "Profit Trajectories (>= $0)",
                        data: profitCounts,
                        backgroundColor: "rgba(0, 230, 118, 0.75)",
                        borderRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: "#F0F4F8", font: { family: "Outfit" } }
                    },
                    tooltip: {
                        backgroundColor: "#1B2232",
                        borderColor: "#3A4660",
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", font: { family: "JetBrains Mono" }, maxTicksLimit: 12 },
                        title: { display: true, text: "Total Profit / Loss Outcome ($)", color: "#94A3B8" }
                    },
                    y: {
                        stacked: true,
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", font: { family: "JetBrains Mono" } },
                        title: { display: true, text: "Simulation Paths Count", color: "#94A3B8" }
                    }
                }
            }
        });
    }

    function renderMarketContextChart(metrics) {
        const ctx = document.getElementById("chartCandle").getContext("2d");
        const S0 = state.S0;
        const days = 120;
        const labels = [];
        const priceSeries = [];

        // Generate realistic historical daily trajectory leading up to S0
        let currentP = S0 * 0.92;
        const dt_step = 1.0 / 252.0;
        const dailyVol = state.sigma * Math.sqrt(dt_step);

        for (let d = days; d >= 0; d--) {
            const date = new Date();
            date.setDate(date.getDate() - d);
            labels.push(date.toLocaleDateString("en-US", { month: "short", day: "numeric" }));
            const shock = (Math.random() - 0.48) * dailyVol * currentP;
            currentP += shock;
            if (d === 0) currentP = S0; // Anchor today to S0
            priceSeries.push(currentP);
        }

        const k1Series = new Array(days + 1).fill(state.K1);
        const k2Series = new Array(days + 1).fill(state.K2);
        const beSeries = new Array(days + 1).fill(metrics.breakeven);

        if (chartCandle) chartCandle.destroy();

        chartCandle = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `${state.ticker} Price Action`,
                        data: priceSeries,
                        borderColor: "#F0F4F8",
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: {
                            target: "origin",
                            above: "rgba(255, 255, 255, 0.03)"
                        }
                    },
                    {
                        label: `K1 Strike ($${state.K1.toFixed(1)})`,
                        data: k1Series,
                        borderColor: "rgba(255, 179, 0, 0.8)",
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: `K2 Strike ($${state.K2.toFixed(1)})`,
                        data: k2Series,
                        borderColor: "rgba(0, 229, 255, 0.8)",
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: `Breakeven ($${metrics.breakeven.toFixed(2)})`,
                        data: beSeries,
                        borderColor: "rgba(255, 255, 255, 0.6)",
                        borderDash: [2, 4],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: "#F0F4F8", font: { family: "Outfit" } }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", maxTicksLimit: 10 }
                    },
                    y: {
                        grid: { color: "#1B2232" },
                        ticks: { color: "#94A3B8", font: { family: "JetBrains Mono" } }
                    }
                }
            }
        });
    }

    // =========================================================================
    // 6. UI UPDATE ORCHESTRATION
    // =========================================================================

    function updateUI() {
        const metrics = calculateStrategyMetrics();

        // 1. KPI Ribbon
        document.getElementById("kpiNetDebit").textContent = `$${metrics.netDebit.toFixed(2)}`;
        document.getElementById("kpiDebitSub").textContent = `Total: $${metrics.totalNetDebit.toFixed(2)}`;

        document.getElementById("kpiBreakeven").textContent = `$${metrics.breakeven.toFixed(2)}`;
        const diffPct = ((metrics.breakeven - state.S0) / state.S0) * 100;
        document.getElementById("kpiBreakevenSub").textContent = `${diffPct >= 0 ? "+" : ""}${diffPct.toFixed(2)}% from Spot`;

        document.getElementById("kpiMaxProfit").textContent = `+$${metrics.totalMaxProfit.toFixed(2)}`;
        document.getElementById("kpiProfitSub").textContent = `$${metrics.maxProfitPerShare.toFixed(2)} / share`;

        document.getElementById("kpiMaxLoss").textContent = `-$${Math.abs(metrics.totalMaxLoss).toFixed(2)}`;
        document.getElementById("kpiLossSub").textContent = `-$${Math.abs(metrics.maxLossPerShare).toFixed(2)} / share`;

        document.getElementById("kpiRR").textContent = `${metrics.rewardToRisk.toFixed(2)} : 1`;
        document.getElementById("kpiRRSub").textContent = `Width: $${metrics.spreadWidth.toFixed(2)}`;

        document.getElementById("kpiOutlay").textContent = `$${metrics.totalOutlay.toFixed(2)}`;

        // 2. Greeks Table & BSM Breakdown
        const g = metrics.greeksNet;
        const gBody = document.getElementById("greeksTableBody");
        const isBull = state.strategy === "Bull Call Spread";

        gBody.innerHTML = `
            <tr>
                <td>Delta</td><td>Δ</td>
                <td>${isBull ? g.leg1Greeks.delta.toFixed(4) : (-g.leg1Greeks.delta).toFixed(4)}</td>
                <td>${isBull ? (-g.leg2Greeks.delta).toFixed(4) : g.leg2Greeks.delta.toFixed(4)}</td>
                <td style="color:${g.delta >= 0 ? 'var(--green-profit)' : 'var(--red-loss)'}; font-weight:700;">${g.delta.toFixed(4)}</td>
                <td>${g.delta >= 0 ? 'Directionally Bullish' : 'Directionally Bearish'}</td>
            </tr>
            <tr>
                <td>Gamma</td><td>Γ</td>
                <td>${g.leg1Greeks.gamma.toFixed(4)}</td>
                <td>${(-g.leg2Greeks.gamma).toFixed(4)}</td>
                <td>${g.gamma.toFixed(4)}</td>
                <td>Curvature / delta acceleration</td>
            </tr>
            <tr>
                <td>Vega (per 1%)</td><td>ν</td>
                <td>${g.leg1Greeks.vega1Pct.toFixed(4)}</td>
                <td>${(-g.leg2Greeks.vega1Pct).toFixed(4)}</td>
                <td style="color:${g.vega1Pct >= 0 ? 'var(--cyan-accent)' : 'var(--red-loss)'}">${g.vega1Pct.toFixed(4)}</td>
                <td>${g.vega1Pct >= 0 ? 'Long Volatility Bias' : 'Short Volatility'}</td>
            </tr>
            <tr>
                <td>Daily Theta</td><td>Θ</td>
                <td>$${g.leg1Greeks.thetaDay.toFixed(4)}</td>
                <td>$${(-g.leg2Greeks.thetaDay).toFixed(4)}</td>
                <td style="color:var(--red-loss);">$${g.thetaDay.toFixed(4)}</td>
                <td>Erosion per calendar day</td>
            </tr>
            <tr>
                <td>Rho (per 1%)</td><td>ρ</td>
                <td>${(g.leg1Greeks.rho / 100).toFixed(4)}</td>
                <td>${(-g.leg2Greeks.rho / 100).toFixed(4)}</td>
                <td>${(g.rho / 100).toFixed(4)}</td>
                <td>Interest rate sensitivity</td>
            </tr>
        `;

        if (isBull) {
            document.getElementById("leg1Title").textContent = `Long Call (K1 = $${state.K1.toFixed(0)})`;
            document.getElementById("leg2Title").textContent = `Short Call (K2 = $${state.K2.toFixed(0)})`;
        } else {
            document.getElementById("leg1Title").textContent = `Short Put (K1 = $${state.K1.toFixed(0)})`;
            document.getElementById("leg2Title").textContent = `Long Put (K2 = $${state.K2.toFixed(0)})`;
        }
        document.getElementById("leg1Price").textContent = `$${metrics.leg1Price.toFixed(4)}`;
        document.getElementById("leg2Price").textContent = `$${metrics.leg2Price.toFixed(4)}`;
        document.getElementById("legNetPrice").textContent = `$${metrics.netDebit.toFixed(4)}`;

        // 3. Render Charts
        renderPayoffChart(metrics);
        renderMarketContextChart(metrics);

        // 4. Run Monte Carlo
        const mcRes = runMonteCarloSimulation(state.mcPaths);
        renderMonteCarloChart(mcRes, metrics);

        document.getElementById("simPopVal").textContent = `${mcRes.popPct.toFixed(1)}%`;
        document.getElementById("simExpPnl").textContent = `${mcRes.expectedPnl >= 0 ? "+" : ""}$${mcRes.expectedPnl.toFixed(2)}`;
        document.getElementById("simVarVal").textContent = `$${mcRes.var95.toFixed(2)}`;

        // 5. Algorithmic Verdict Box
        const verdict = evaluateStrategyVerdict(metrics, mcRes.popPct);
        const vBox = document.getElementById("verdictBox");
        const vTitle = document.getElementById("verdictTitle");
        const vScore = document.getElementById("verdictScoreVal");
        const vList = document.getElementById("verdictDrivers");

        vTitle.textContent = verdict.title;
        vTitle.style.color = verdict.color;
        vBox.style.borderLeftColor = verdict.color;
        vScore.textContent = `${verdict.totalScore} / 100`;

        vList.innerHTML = verdict.drivers.map(d => `<li>${d}</li>`).join("");
    }

    // =========================================================================
    // 7. EVENT LISTENERS & PRESETS
    // =========================================================================

    function setupEventListeners() {
        // Strategy Toggle
        const btnBull = document.getElementById("btnSelectBull");
        const btnBear = document.getElementById("btnSelectBear");

        btnBull.addEventListener("click", () => {
            state.strategy = "Bull Call Spread";
            btnBull.classList.add("active");
            btnBear.classList.remove("active");
            // Set typical bull strikes if on benchmark
            if (state.ticker === "BENCHMARK") {
                state.K1 = 100.0;
                state.K2 = 110.0;
                document.getElementById("inputK1").value = "100.00";
                document.getElementById("inputK2").value = "110.00";
            }
            updateUI();
        });

        btnBear.addEventListener("click", () => {
            state.strategy = "Bear Put Spread";
            btnBear.classList.add("active");
            btnBull.classList.remove("active");
            // Set typical bear strikes if on benchmark
            if (state.ticker === "BENCHMARK") {
                state.K1 = 90.0;
                state.K2 = 100.0;
                document.getElementById("inputK1").value = "90.00";
                document.getElementById("inputK2").value = "100.00";
            }
            updateUI();
        });

        // Sliders & Number Inputs
        document.getElementById("inputSpot").addEventListener("input", (e) => {
            state.S0 = parseFloat(e.target.value) || 100.0;
            updateUI();
        });

        document.getElementById("inputVol").addEventListener("input", (e) => {
            state.sigma = (parseFloat(e.target.value) || 20.0) / 100.0;
            updateUI();
        });

        document.getElementById("inputK1").addEventListener("input", (e) => {
            state.K1 = parseFloat(e.target.value) || 100.0;
            updateUI();
        });

        document.getElementById("inputK2").addEventListener("input", (e) => {
            state.K2 = parseFloat(e.target.value) || 110.0;
            updateUI();
        });

        const sliderDte = document.getElementById("sliderDte");
        sliderDte.addEventListener("input", (e) => {
            state.dte = parseInt(e.target.value, 10);
            state.T = state.dte / 365.0;
            document.getElementById("dteLabel").textContent = `${state.dte} Days (${state.T.toFixed(2)} yr)`;
            updateUI();
        });

        const sliderRate = document.getElementById("sliderRate");
        sliderRate.addEventListener("input", (e) => {
            state.r = parseFloat(e.target.value) / 100.0;
            document.getElementById("rateLabel").textContent = `${(state.r * 100).toFixed(2)}%`;
            updateUI();
        });

        document.getElementById("inputContracts").addEventListener("input", (e) => {
            state.contracts = parseInt(e.target.value, 10) || 1;
            updateUI();
        });

        document.getElementById("inputComm").addEventListener("input", (e) => {
            state.commissionPerLeg = parseFloat(e.target.value) || 0.65;
            updateUI();
        });

        // Re-run simulation button
        document.getElementById("btnRunSimulation").addEventListener("click", () => {
            updateUI();
        });

        document.getElementById("mcPathsSelect").addEventListener("change", (e) => {
            state.mcPaths = parseInt(e.target.value, 10);
            updateUI();
        });

        // Ticker Presets
        document.getElementById("tickerSelect").addEventListener("change", (e) => {
            const val = e.target.value;
            state.ticker = val;
            if (val === "BENCHMARK") {
                state.S0 = 100.0;
                state.sigma = 0.20;
                if (state.strategy === "Bull Call Spread") {
                    state.K1 = 100.0;
                    state.K2 = 110.0;
                } else {
                    state.K1 = 90.0;
                    state.K2 = 100.0;
                }
            } else if (val === "AAPL") {
                state.S0 = 222.0;
                state.sigma = 0.24;
                state.K1 = 220.0;
                state.K2 = 235.0;
            } else if (val === "SPY") {
                state.S0 = 560.0;
                state.sigma = 0.14;
                state.K1 = 555.0;
                state.K2 = 575.0;
            } else if (val === "QQQ") {
                state.S0 = 480.0;
                state.sigma = 0.18;
                state.K1 = 475.0;
                state.K2 = 495.0;
            } else if (val === "NVDA") {
                state.S0 = 116.0;
                state.sigma = 0.45;
                state.K1 = 115.0;
                state.K2 = 130.0;
            } else if (val === "TSLA") {
                state.S0 = 230.0;
                state.sigma = 0.48;
                state.K1 = 225.0;
                state.K2 = 250.0;
            }

            document.getElementById("inputSpot").value = state.S0.toFixed(2);
            document.getElementById("inputVol").value = (state.sigma * 100).toFixed(1);
            document.getElementById("inputK1").value = state.K1.toFixed(2);
            document.getElementById("inputK2").value = state.K2.toFixed(2);
            updateUI();
        });

        // Paper Baseline Preset Button
        document.getElementById("btnPresetPaper").addEventListener("click", () => {
            state.ticker = "BENCHMARK";
            document.getElementById("tickerSelect").value = "BENCHMARK";
            state.S0 = 100.0;
            state.sigma = 0.20;
            state.dte = 182;
            state.T = 0.50;
            state.r = 0.05;
            state.contracts = 1;
            state.commissionPerLeg = 0.65;

            if (state.strategy === "Bull Call Spread") {
                state.K1 = 100.0;
                state.K2 = 110.0;
            } else {
                state.K1 = 90.0;
                state.K2 = 100.0;
            }

            document.getElementById("inputSpot").value = "100.00";
            document.getElementById("inputVol").value = "20.0";
            document.getElementById("inputK1").value = state.K1.toFixed(2);
            document.getElementById("inputK2").value = state.K2.toFixed(2);
            document.getElementById("sliderDte").value = "182";
            document.getElementById("dteLabel").textContent = "182 Days (0.50 yr)";
            document.getElementById("sliderRate").value = "5.0";
            document.getElementById("rateLabel").textContent = "5.0%";
            document.getElementById("inputContracts").value = "1";
            document.getElementById("inputComm").value = "0.65";

            updateUI();
        });

        // Tab Navigation
        const tabBtns = document.querySelectorAll(".tab-btn");
        const tabPanes = document.querySelectorAll(".tab-pane");

        tabBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                tabBtns.forEach(b => b.classList.remove("active"));
                tabPanes.forEach(p => p.classList.remove("active"));

                btn.classList.add("active");
                const targetId = btn.getAttribute("data-tab");
                const pane = document.getElementById(targetId);
                if (pane) pane.classList.add("active");

                // Trigger chart redraw when tab becomes visible
                if (targetId === "tab-payoff" && chartPayoff) chartPayoff.resize();
                if (targetId === "tab-sim" && chartMonteCarlo) chartMonteCarlo.resize();
                if (targetId === "tab-market" && chartCandle) chartCandle.resize();
            });
        });
    }

    // Initialize
    window.addEventListener("DOMContentLoaded", () => {
        setupEventListeners();
        updateUI();
    });
})();
