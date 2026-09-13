-- ============================================================
-- FINANCE PORTFOLIO ANALYTICS
-- SQL ANALYTICS
-- ============================================================
-- Purpose:
-- Analyze stock performance, portfolio performance,
-- benchmark performance, and market behavior.
-- ============================================================


-- ============================================================
-- 1. STOCK PERFORMANCE
-- Calculate stock returns during the portfolio period.
-- ============================================================

WITH stock_prices AS (
    SELECT
        c.symbol,
        c.company_name,
        c.sector,
        p.trade_date,
        p.adjusted_close_price,

        FIRST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
        ) AS first_price,

        LAST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND UNBOUNDED FOLLOWING
        ) AS last_price

    FROM prices p
    JOIN companies c
        ON p.company_id = c.company_id

    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
)

SELECT DISTINCT
    symbol,
    company_name,
    sector,
    first_price,
    last_price,
    ROUND(
        ((last_price / first_price) - 1) * 100,
        2
    ) AS return_pct
FROM stock_prices
ORDER BY return_pct DESC;

-- Q2 Which stocks contributed the most and least to our portfolio's overall performance?

WITH stock_prices AS (
    SELECT
        ph.symbol,
        ph.quantity,
        ph.invested_amount,
        start_p.adjusted_close_price AS start_price,
        end_p.adjusted_close_price AS end_price
    FROM portfolio_holdings ph

    JOIN prices start_p
        ON ph.company_id = start_p.company_id
       AND start_p.trade_date = ph.purchase_date

    JOIN prices end_p
        ON ph.company_id = end_p.company_id
       AND end_p.trade_date = '2026-09-11'
),

stock_contribution AS (
    SELECT
        symbol,
        quantity,
        invested_amount,
        start_price,
        end_price,

        quantity * (end_price - start_price) AS profit_loss,

        (
            quantity * (end_price - start_price)
            / 1000000.0
        ) * 100 AS contribution_pct

    FROM stock_prices
)

SELECT
    symbol,
    quantity,
    invested_amount,
    ROUND(start_price, 2) AS start_price,
    ROUND(end_price, 2) AS end_price,
    ROUND(profit_loss, 2) AS profit_loss,
    ROUND(contribution_pct, 2) AS contribution_pct
FROM stock_contribution
ORDER BY contribution_pct DESC;

--Q3 Which sectors performed best and worst during our portfolio period?

WITH stock_returns AS (
    SELECT
        c.sector,
        c.symbol,
        FIRST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
        ) AS first_price,
        LAST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND UNBOUNDED FOLLOWING
        ) AS last_price
    FROM prices p
    JOIN companies c
        ON p.company_id = c.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
),

sector_returns AS (
    SELECT DISTINCT
        sector,
        symbol,
        ((last_price / first_price) - 1) * 100 AS stock_return
    FROM stock_returns
)

SELECT
    sector,
    COUNT(*) AS number_of_stocks,
    ROUND(AVG(stock_return), 2) AS average_return_pct
FROM sector_returns
GROUP BY sector
ORDER BY average_return_pct DESC;

--Q4 Which sectors contributed the most and least money to our portfolio?
WITH stock_contribution AS (
    SELECT
        c.sector,
        ph.symbol,
        ph.quantity,
        ph.invested_amount,
        ph.quantity * (
            end_p.adjusted_close_price - start_p.adjusted_close_price
        ) AS profit_loss
    FROM portfolio_holdings ph

    JOIN companies c
        ON ph.company_id = c.company_id

    JOIN prices start_p
        ON ph.company_id = start_p.company_id
       AND start_p.trade_date = ph.purchase_date

    JOIN prices end_p
        ON ph.company_id = end_p.company_id
       AND end_p.trade_date = '2026-09-11'
)

SELECT
    sector,
    COUNT(*) AS number_of_stocks,
    ROUND(SUM(invested_amount), 2) AS invested_amount,
    ROUND(SUM(profit_loss), 2) AS total_profit_loss,
    ROUND(
        (SUM(profit_loss) / 1000000.0) * 100,
        2
    ) AS portfolio_contribution_pct
FROM stock_contribution
GROUP BY sector
ORDER BY total_profit_loss DESC;

--Q5 What was the portfolio's starting value, ending value, and overall return?
WITH portfolio_value AS (
    SELECT
        SUM(
            ph.quantity * p.adjusted_close_price
        ) + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date = '2025-09-12'
)

SELECT
    ROUND(portfolio_value, 2) AS portfolio_value,
    '2025-09-12' AS valuation_date
FROM portfolio_value

UNION ALL

SELECT
    ROUND(
        SUM(
            ph.quantity * p.adjusted_close_price
        ) + SUM(ph.unused_cash),
        2
    ) AS portfolio_value,
    '2026-09-11' AS valuation_date
FROM portfolio_holdings ph
JOIN prices p
    ON ph.company_id = p.company_id
WHERE p.trade_date = '2026-09-11';

--Q6 What was the portfolio's total return during the investment period?
SELECT
    ROUND(
        (
            (890018.90 / 1000000.00) - 1
        ) * 100,
        2
    ) AS portfolio_return_pct;


-- Q7 How did the portfolio perform day by day throughout the investment period?
WITH daily_values AS (
    SELECT
        p.trade_date,
        SUM(
            ph.quantity * p.adjusted_close_price
        ) + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
)

SELECT
    trade_date,
    ROUND(portfolio_value, 2) AS portfolio_value,
    ROUND(
        (
            portfolio_value /
            LAG(portfolio_value) OVER (ORDER BY trade_date)
            - 1
        ) * 100,
        4
    ) AS daily_return_pct
FROM daily_values
ORDER BY trade_date;

-- Q8 How did the portfolio's cumulative return evolve over time?
WITH daily_values AS (
    SELECT
        p.trade_date,
        SUM(
            ph.quantity * p.adjusted_close_price
        ) + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
)

SELECT
    trade_date,
    ROUND(portfolio_value, 2) AS portfolio_value,
    ROUND(
        (
            (portfolio_value / FIRST_VALUE(portfolio_value)
                OVER (ORDER BY trade_date)) - 1
        ) * 100,
        2
    ) AS cumulative_return_pct
FROM daily_values
ORDER BY trade_date;

-- Q9 — What was the portfolio's monthly performance?
WITH daily_values AS (
    SELECT
        p.trade_date,
        SUM(
            ph.quantity * p.adjusted_close_price
        ) + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),

monthly_values AS (
    SELECT
        DATE_TRUNC('month', trade_date)::DATE AS month,
        FIRST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
        ) AS month_start_value,
        LAST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND UNBOUNDED FOLLOWING
        ) AS month_end_value
    FROM daily_values
)

SELECT DISTINCT
    month,
    ROUND(month_start_value, 2) AS month_start_value,
    ROUND(month_end_value, 2) AS month_end_value,
    ROUND(
        (
            (month_end_value / month_start_value) - 1
        ) * 100,
        2
    ) AS monthly_return_pct
FROM monthly_values
ORDER BY month;

-- Q10 — Which was the best and worst month?
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', trade_date) AS month,
        FIRST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
        ) AS start_value,
        LAST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS end_value
    FROM (
        SELECT
            p.trade_date,
            SUM(ph.quantity * p.adjusted_close_price)
                + SUM(ph.unused_cash) AS portfolio_value
        FROM portfolio_holdings ph
        JOIN prices p ON ph.company_id = p.company_id
        WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
        GROUP BY p.trade_date
    ) d
)
SELECT DISTINCT
    TO_CHAR(month, 'Month YYYY') AS month_name,
    ROUND(((end_value / start_value) - 1) * 100, 2) AS return_pct
FROM monthly
ORDER BY return_pct DESC;

-- Q11 — What is the portfolio's daily volatility?
WITH daily AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),
returns AS (
    SELECT
        trade_date,
        portfolio_value / LAG(portfolio_value)
            OVER (ORDER BY trade_date) - 1 AS daily_return
    FROM daily
)
SELECT
    ROUND(STDDEV(daily_return) * 100, 4) AS daily_volatility_pct
FROM returns
WHERE daily_return IS NOT NULL;

-- Q12 — Annualized volatility
SELECT
    ROUND((0.9261 * SQRT(252))::numeric, 2)
        AS annualized_volatility_pct;

--Q13 — What was the portfolio's maximum drawdown?
WITH daily AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),
drawdown AS (
    SELECT
        trade_date,
        portfolio_value,
        MAX(portfolio_value) OVER (
            ORDER BY trade_date
        ) AS peak_value
    FROM daily
)
SELECT
    ROUND(
        MIN((portfolio_value / peak_value - 1) * 100)::numeric,
        2
    ) AS maximum_drawdown_pct
FROM drawdown;

-- Q14 — Sharpe Ratio
WITH daily AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),
returns AS (
    SELECT
        portfolio_value / LAG(portfolio_value)
            OVER (ORDER BY trade_date) - 1 AS daily_return
    FROM daily
),
stats AS (
    SELECT
        AVG(daily_return) AS avg_daily_return,
        STDDEV(daily_return) AS daily_volatility
    FROM returns
    WHERE daily_return IS NOT NULL
)
SELECT
    ROUND(
        ((avg_daily_return / daily_volatility) * SQRT(252))::numeric,
        2
    ) AS sharpe_ratio
FROM stats;

-- Q15 — Value at Risk (VaR)
WITH daily AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),
returns AS (
    SELECT
        portfolio_value / LAG(portfolio_value)
            OVER (ORDER BY trade_date) - 1 AS daily_return
    FROM daily
)
SELECT
    ROUND(
        (PERCENTILE_CONT(0.05)
        WITHIN GROUP (ORDER BY daily_return) * 100)::numeric,
        2
    ) AS var_95_pct
FROM returns
WHERE daily_return IS NOT NULL;

-- Q16 — Risk Contributors
WITH stock_stats AS (
    SELECT
        ph.symbol,
        ph.invested_amount,
        ph.invested_amount / 1000000.0 AS weight,
        STDDEV(p.daily_return) AS volatility
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY ph.symbol, ph.invested_amount
)
SELECT
    symbol,
    ROUND((weight * 100)::numeric, 2) AS portfolio_weight_pct,
    ROUND((volatility * 100)::numeric, 2) AS annual_period_volatility_pct,
    ROUND((weight * volatility * 100)::numeric, 2) AS risk_contribution_pct
FROM stock_stats
ORDER BY risk_contribution_pct DESC;

-- Q17 — Actual Portfolio Weights
SELECT
    symbol,
    invested_amount,
    ROUND(
        (invested_amount / SUM(invested_amount) OVER ()) * 100,
        2
    ) AS actual_weight_pct
FROM portfolio_holdings
ORDER BY actual_weight_pct DESC;

-- Q18 — Sector Allocation
SELECT
    c.sector,
    ROUND(SUM(ph.invested_amount), 2) AS invested_amount,
    ROUND(
        SUM(ph.invested_amount)
        / SUM(SUM(ph.invested_amount)) OVER () * 100,
        2
    ) AS sector_weight_pct
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id
GROUP BY c.sector
ORDER BY sector_weight_pct DESC;

-- Q19 — Concentration Risk
WITH weights AS (
    SELECT
        invested_amount / SUM(invested_amount) OVER () AS weight
    FROM portfolio_holdings
)
SELECT
    ROUND(SUM(POWER(weight, 2))::numeric, 4) AS portfolio_hhi
FROM weights;

-- Q20 — Diversification
SELECT
    COUNT(*) AS number_of_stocks,
    COUNT(DISTINCT c.sector) AS number_of_sectors
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id;

-- Q21 — Portfolio vs NIFTY 50
WITH portfolio_daily AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
    GROUP BY p.trade_date
),
portfolio_return AS (
    SELECT
        (MAX(portfolio_value) FILTER (WHERE trade_date = '2026-09-11')
         / MAX(portfolio_value) FILTER (WHERE trade_date = '2025-09-12') - 1) * 100
         AS return_pct
    FROM portfolio_daily
),
nifty_return AS (
    SELECT
        (MAX(close_price) FILTER (WHERE trade_date = '2026-09-11')
         / MAX(close_price) FILTER (WHERE trade_date = '2025-09-12') - 1) * 100
         AS return_pct
    FROM benchmarks
)
SELECT
    ROUND(portfolio_return.return_pct::numeric, 2) AS portfolio_return_pct,
    ROUND(nifty_return.return_pct::numeric, 2) AS nifty_return_pct
FROM portfolio_return
CROSS JOIN nifty_return;

-- Q22 — Excess Return
SELECT
    ROUND((-11.00 - (-6.83))::numeric, 2) AS excess_return_pct;

-- Q23 — Stock Beta vs NIFTY 50
WITH market AS (
    SELECT
        trade_date,
        daily_return AS market_return
    FROM benchmarks
    WHERE daily_return IS NOT NULL
),
stock_market AS (
    SELECT
        c.symbol,
        p.trade_date,
        p.daily_return AS stock_return,
        m.market_return
    FROM prices p
    JOIN companies c
        ON p.company_id = c.company_id
    JOIN market m
        ON p.trade_date = m.trade_date
    WHERE p.daily_return IS NOT NULL
)
SELECT
    symbol,
    ROUND(
        (
            COVAR_SAMP(stock_return, market_return)
            / VAR_SAMP(market_return)
        )::numeric,
        2
    ) AS beta
FROM stock_market
GROUP BY symbol
ORDER BY beta DESC;

-- Q24 — VIX vs Portfolio
WITH portfolio AS (
    SELECT
        p.trade_date,
        SUM(ph.quantity * p.adjusted_close_price)
            + SUM(ph.unused_cash) AS portfolio_value
    FROM portfolio_holdings ph
    JOIN prices p
        ON ph.company_id = p.company_id
    GROUP BY p.trade_date
),
portfolio_returns AS (
    SELECT
        trade_date,
        portfolio_value / LAG(portfolio_value)
            OVER (ORDER BY trade_date) - 1 AS portfolio_return
    FROM portfolio
)
SELECT
    ROUND(
        CORR(pr.portfolio_return, v.daily_return)::numeric,
        2
    ) AS portfolio_vix_correlation
FROM portfolio_returns pr
JOIN market_volatility v
    ON pr.trade_date = v.trade_date
WHERE pr.portfolio_return IS NOT NULL
  AND v.daily_return IS NOT NULL;

-- Q25 — highest-volume trading days.
SELECT
    c.symbol,
    p.trade_date,
    p.volume
FROM prices p
JOIN companies c
    ON p.company_id = c.company_id
WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
ORDER BY p.volume DESC
LIMIT 10;

--Q26 — Unusual Price Movements
SELECT
    c.symbol,
    p.trade_date,
    ROUND((p.daily_return * 100)::numeric, 2) AS daily_return_pct,
    p.volume
FROM prices p
JOIN companies c
    ON p.company_id = c.company_id
WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
ORDER BY ABS(p.daily_return) DESC
LIMIT 10;