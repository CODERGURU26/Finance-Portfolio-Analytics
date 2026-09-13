-- ============================================================
-- View 1: Daily Portfolio Performance
-- ============================================================
-- Purpose:
-- Tracks daily portfolio value, daily return, and cumulative
-- return during the portfolio analysis period.
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_daily AS

-- Calculate total portfolio value for each trading day
WITH daily_values AS (
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

-- Calculate daily return using the previous trading day's value
daily_returns AS (
    SELECT
        trade_date,
        portfolio_value,
        portfolio_value
            / LAG(portfolio_value) OVER (ORDER BY trade_date)
            - 1 AS daily_return
    FROM daily_values
)

-- Final Power BI-ready output
SELECT
    trade_date,
    ROUND(portfolio_value, 2) AS portfolio_value,
    ROUND(daily_return * 100, 4) AS daily_return_pct,
    ROUND(
        (
            portfolio_value
            / FIRST_VALUE(portfolio_value)
              OVER (ORDER BY trade_date)
            - 1
        ) * 100,
        2
    ) AS cumulative_return_pct
FROM daily_returns;


-- Test the view
SELECT *
FROM vw_portfolio_daily
ORDER BY trade_date;
-- ============================================================
-- View 2: Monthly Portfolio Performance
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_monthly AS
WITH daily_values AS (
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
monthly_values AS (
    SELECT
        DATE_TRUNC('month', trade_date)::date AS month,
        FIRST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
        ) AS starting_value,
        LAST_VALUE(portfolio_value) OVER (
            PARTITION BY DATE_TRUNC('month', trade_date)
            ORDER BY trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS ending_value
    FROM daily_values
)
SELECT DISTINCT
    month,
    ROUND(starting_value, 2) AS starting_value,
    ROUND(ending_value, 2) AS ending_value,
    ROUND(
        ((ending_value / starting_value) - 1) * 100,
        2
    ) AS monthly_return_pct
FROM monthly_values
ORDER BY month;

SELECT *
FROM vw_portfolio_monthly
ORDER BY month;

-- ============================================================
-- View 3: Stock Performance
-- ============================================================

CREATE OR REPLACE VIEW vw_stock_performance AS
WITH stock_prices AS (
    SELECT
        c.company_id,
        c.symbol,
        c.company_name,
        c.sector,
        p.trade_date,
        p.adjusted_close_price,

        FIRST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
        ) AS starting_price,

        LAST_VALUE(p.adjusted_close_price) OVER (
            PARTITION BY p.company_id
            ORDER BY p.trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND UNBOUNDED FOLLOWING
        ) AS ending_price

    FROM prices p
    JOIN companies c
        ON p.company_id = c.company_id

    WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
)

SELECT DISTINCT
    company_id,
    symbol,
    company_name,
    sector,
    ROUND(starting_price, 2) AS starting_price,
    ROUND(ending_price, 2) AS ending_price,
    ROUND(
        ((ending_price / starting_price) - 1) * 100,
        2
    ) AS return_pct
FROM stock_prices;

SELECT *
FROM vw_stock_performance
ORDER BY return_pct DESC;


-- ============================================================
-- View 4: Stock Contribution to Portfolio
-- ============================================================

CREATE OR REPLACE VIEW vw_stock_contribution AS
WITH stock_values AS (
    SELECT
        ph.company_id,
        ph.symbol,
        ph.quantity,
        ph.invested_amount,
        start_p.adjusted_close_price AS starting_price,
        end_p.adjusted_close_price AS ending_price
    FROM portfolio_holdings ph
    JOIN prices start_p
        ON ph.company_id = start_p.company_id
        AND start_p.trade_date = ph.purchase_date
    JOIN prices end_p
        ON ph.company_id = end_p.company_id
        AND end_p.trade_date = '2026-09-11'
)
SELECT
    c.symbol,
    c.company_name,
    c.sector,
    sv.quantity,
    ROUND(sv.invested_amount, 2) AS invested_amount,
    ROUND(sv.starting_price, 2) AS starting_price,
    ROUND(sv.ending_price, 2) AS ending_price,

    ROUND(
        sv.quantity * (sv.ending_price - sv.starting_price),
        2
    ) AS profit_loss,

    ROUND(
        (
            sv.quantity * (sv.ending_price - sv.starting_price)
            / 1000000.0
        ) * 100,
        2
    ) AS portfolio_contribution_pct

FROM stock_values sv
JOIN companies c
    ON sv.company_id = c.company_id
ORDER BY profit_loss DESC;

SELECT *
FROM vw_stock_contribution
ORDER BY profit_loss DESC;

-- ============================================================
-- View 5: Sector Analysis
-- ============================================================

CREATE OR REPLACE VIEW vw_sector_analysis AS
SELECT
    c.sector,
    COUNT(*) AS number_of_stocks,
    ROUND(SUM(ph.invested_amount), 2) AS invested_amount,
    ROUND(
        SUM(
            ph.quantity * (
                end_p.adjusted_close_price
                - start_p.adjusted_close_price
            )
        ),
        2
    ) AS total_profit_loss,
    ROUND(
        (
            SUM(
                ph.quantity * (
                    end_p.adjusted_close_price
                    - start_p.adjusted_close_price
                )
            ) / 1000000.0
        ) * 100,
        2
    ) AS portfolio_contribution_pct
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id
JOIN prices start_p
    ON ph.company_id = start_p.company_id
    AND start_p.trade_date = ph.purchase_date
JOIN prices end_p
    ON ph.company_id = end_p.company_id
    AND end_p.trade_date = '2026-09-11'
GROUP BY c.sector
ORDER BY total_profit_loss DESC;

SELECT *
FROM vw_sector_analysis;

-- ============================================================
-- View 6: Actual Portfolio Weights
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_weights AS
SELECT
    ph.symbol,
    c.company_name,
    c.sector,
    ph.invested_amount,
    ROUND(
        (
            ph.invested_amount
            / SUM(ph.invested_amount) OVER ()
        ) * 100,
        2
    ) AS actual_weight_pct
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id
ORDER BY actual_weight_pct DESC;

SELECT *
FROM vw_portfolio_weights;

-- ============================================================
-- View 7: Sector Allocation
-- ============================================================

CREATE OR REPLACE VIEW vw_sector_allocation AS
SELECT
    c.sector,
    ROUND(
        SUM(ph.invested_amount),
        2
    ) AS invested_amount,
    ROUND(
        (
            SUM(ph.invested_amount)
            / SUM(SUM(ph.invested_amount)) OVER ()
        ) * 100,
        2
    ) AS sector_weight_pct
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id
GROUP BY c.sector
ORDER BY sector_weight_pct DESC;

SELECT *
FROM vw_sector_allocation;

-- ============================================================
-- View 8: Portfolio Concentration Risk (HHI)
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_hhi AS
WITH weights AS (
    SELECT
        invested_amount
        / SUM(invested_amount) OVER () AS weight
    FROM portfolio_holdings
)
SELECT
    ROUND(
        SUM(POWER(weight, 2))::numeric,
        4
    ) AS portfolio_hhi
FROM weights;

SELECT *
FROM vw_portfolio_hhi;

-- ============================================================
-- View 9: Portfolio Diversification Summary
-- ============================================================

CREATE OR REPLACE VIEW vw_diversification_summary AS
SELECT
    COUNT(*) AS number_of_stocks,
    COUNT(DISTINCT c.sector) AS number_of_sectors
FROM portfolio_holdings ph
JOIN companies c
    ON ph.company_id = c.company_id;

SELECT *
FROM vw_diversification_summary;

-- ============================================================
-- View 10: Portfolio vs NIFTY 50
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_vs_nifty AS
WITH portfolio_values AS (
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
portfolio_return AS (
    SELECT
        (
            MAX(portfolio_value)
            FILTER (WHERE trade_date = '2026-09-11')
            /
            MAX(portfolio_value)
            FILTER (WHERE trade_date = '2025-09-12')
            - 1
        ) * 100 AS return_pct
    FROM portfolio_values
),
nifty_return AS (
    SELECT
        (
            MAX(close_price)
            FILTER (WHERE trade_date = '2026-09-11')
            /
            MAX(close_price)
            FILTER (WHERE trade_date = '2025-09-12')
            - 1
        ) * 100 AS return_pct
    FROM benchmarks
)
SELECT
    ROUND(portfolio_return.return_pct::numeric, 2)
        AS portfolio_return_pct,
    ROUND(nifty_return.return_pct::numeric, 2)
        AS nifty_return_pct,
    ROUND(
        (
            portfolio_return.return_pct
            - nifty_return.return_pct
        )::numeric,
        2
    ) AS excess_return_pct
FROM portfolio_return
CROSS JOIN nifty_return;

SELECT *
FROM vw_portfolio_vs_nifty;

-- ============================================================
-- View 11: Stock Beta vs NIFTY 50
-- ============================================================

CREATE OR REPLACE VIEW vw_stock_beta AS
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

SELECT *
FROM vw_stock_beta;

-- ============================================================
-- View 12: Portfolio Return vs India VIX
-- ============================================================

CREATE OR REPLACE VIEW vw_portfolio_vix AS
WITH portfolio_values AS (
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
portfolio_returns AS (
    SELECT
        trade_date,
        portfolio_value
        / LAG(portfolio_value)
          OVER (ORDER BY trade_date)
        - 1 AS portfolio_return
    FROM portfolio_values
)
SELECT
    ROUND(
        CORR(
            pr.portfolio_return,
            v.daily_return
        )::numeric,
        2
    ) AS portfolio_vix_correlation
FROM portfolio_returns pr
JOIN market_volatility v
    ON pr.trade_date = v.trade_date
WHERE pr.portfolio_return IS NOT NULL
  AND v.daily_return IS NOT NULL;

SELECT *
FROM vw_portfolio_vix;

-- ============================================================
-- View 13: Highest-Volume Trading Days
-- ============================================================

CREATE OR REPLACE VIEW vw_highest_volume_days AS
SELECT
    c.symbol,
    c.company_name,
    p.trade_date,
    p.volume
FROM prices p
JOIN companies c
    ON p.company_id = c.company_id
WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
ORDER BY p.volume DESC
LIMIT 10;

SELECT *
FROM vw_highest_volume_days;

-- ============================================================
-- View 14: Unusual Price Movements
-- ============================================================

CREATE OR REPLACE VIEW vw_unusual_price_movements AS
SELECT
    c.symbol,
    c.company_name,
    p.trade_date,
    ROUND(
        (p.daily_return * 100)::numeric,
        2
    ) AS daily_return_pct,
    p.volume
FROM prices p
JOIN companies c
    ON p.company_id = c.company_id
WHERE p.trade_date BETWEEN '2025-09-12' AND '2026-09-11'
ORDER BY ABS(p.daily_return) DESC
LIMIT 10;

SELECT *
FROM vw_unusual_price_movements;