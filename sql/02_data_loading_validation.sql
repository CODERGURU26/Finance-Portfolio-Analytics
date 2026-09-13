-- ============================================================
-- FINANCE PORTFOLIO ANALYTICS
-- DATA LOADING AND VALIDATION
-- ============================================================
-- Purpose:
-- Load processed data into the database and validate the results.
-- ============================================================


-- ============================================================
-- 1. LOAD COMPANY UNIVERSE
-- ============================================================

INSERT INTO companies
    (symbol, company_name, sector)
VALUES
    ('RELIANCE', 'Reliance Industries', 'Energy'),
    ('HDFCBANK', 'HDFC Bank', 'Banking'),
    ('ICICIBANK', 'ICICI Bank', 'Banking'),
    ('SBIN', 'State Bank of India', 'Banking'),
    ('TCS', 'Tata Consultancy Services', 'IT'),
    ('INFY', 'Infosys', 'IT'),
    ('ITC', 'ITC', 'FMCG'),
    ('LT', 'Larsen & Toubro', 'Industrials'),
    ('TITAN', 'Titan Company', 'Consumer'),
    ('BAJFINANCE', 'Bajaj Finance', 'Financial Services');


-- ============================================================
-- 2. VALIDATE COMPANIES
-- ============================================================

SELECT
    company_id,
    symbol,
    company_name,
    sector
FROM companies
ORDER BY company_id;


SELECT
    COUNT(*) AS total_companies,
    COUNT(DISTINCT symbol) AS unique_symbols,
    COUNT(DISTINCT sector) AS total_sectors
FROM companies;


-- ============================================================
-- 3. CHECK PRICE IMPORT
-- ============================================================
-- price_import receives the processed stock CSV data.
-- Data is then transferred into the final prices table.
-- ============================================================

SELECT
    COUNT(*) AS total_import_rows
FROM price_import;


SELECT
    symbol,
    COUNT(*) AS rows
FROM price_import
GROUP BY symbol
ORDER BY symbol;


SELECT *
FROM price_import
LIMIT 5;


-- ============================================================
-- 4. LOAD STOCK PRICES
-- ============================================================

INSERT INTO prices (
    company_id,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    adjusted_open_price,
    adjusted_high_price,
    adjusted_low_price,
    adjusted_close_price,
    volume,
    daily_return,
    adjustment_factor_applied
)
SELECT
    c.company_id,
    p.trade_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.adjusted_open_price,
    p.adjusted_high_price,
    p.adjusted_low_price,
    p.adjusted_close_price,
    p.total_traded_quantity,
    p.adjusted_daily_return,
    p.adjustment_factor_applied
FROM price_import p
JOIN companies c
    ON p.symbol = c.symbol;


-- ============================================================
-- 5. VALIDATE STOCK PRICES
-- ============================================================

SELECT
    COUNT(*) AS total_rows
FROM prices;


SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT company_id) AS companies,
    COUNT(DISTINCT trade_date) AS trading_dates,
    COUNT(*) FILTER (
        WHERE adjusted_close_price IS NULL
    ) AS missing_adjusted_close,
    COUNT(*) FILTER (
        WHERE volume <= 0
    ) AS invalid_volume
FROM prices;


-- ============================================================
-- 6. VALIDATE BENCHMARK
-- ============================================================

SELECT
    COUNT(*) AS total_rows
FROM benchmarks;


SELECT
    MIN(trade_date) AS start_date,
    MAX(trade_date) AS end_date,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (
        WHERE close_price IS NULL
    ) AS missing_close,
    COUNT(*) FILTER (
        WHERE daily_return IS NULL
    ) AS missing_return
FROM benchmarks;


-- ============================================================
-- 7. VALIDATE INDIA VIX
-- ============================================================

SELECT
    COUNT(*) AS total_rows
FROM market_volatility;


SELECT
    MIN(trade_date) AS start_date,
    MAX(trade_date) AS end_date,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (
        WHERE close_value IS NULL
    ) AS missing_close,
    COUNT(*) FILTER (
        WHERE daily_return IS NULL
    ) AS missing_return
FROM market_volatility;


-- ============================================================
-- 8. VALIDATE PORTFOLIO HOLDINGS
-- ============================================================

SELECT
    COUNT(*) AS total_holdings,
    SUM(invested_amount) AS total_invested,
    SUM(unused_cash) AS total_unused_cash,
    SUM(allocated_capital) AS total_allocated
FROM portfolio_holdings;


-- ============================================================
-- 9. VALIDATE TRANSACTIONS
-- ============================================================

SELECT
    COUNT(*) AS total_transactions,
    SUM(quantity) AS total_shares,
    SUM(quantity * price) AS total_transaction_value
FROM transactions;


-- ============================================================
-- 10. RECONCILE HOLDINGS WITH TRANSACTIONS
-- ============================================================
-- Checks that the purchased quantity and price match
-- the corresponding portfolio holding.
-- Expected result: 0 rows.
-- ============================================================

SELECT
    c.symbol,
    ph.quantity AS holding_quantity,
    t.quantity AS transaction_quantity,
    ph.purchase_price,
    t.price AS transaction_price
FROM companies c
JOIN portfolio_holdings ph
    ON c.company_id = ph.company_id
JOIN transactions t
    ON ph.company_id = t.company_id
WHERE ph.quantity <> t.quantity
   OR ph.purchase_price <> t.price;