-- ============================================================
-- FINANCE PORTFOLIO ANALYTICS
-- DATABASE TABLE SETUP
-- ============================================================
-- Purpose:
-- Create the PostgreSQL tables used by the analytics platform.
--
-- Tables:
-- 1. companies
-- 2. prices
-- 3. price_import
-- 4. benchmarks
-- 5. market_volatility
-- 6. portfolio_holdings
-- 7. transactions
-- ============================================================


-- ============================================================
-- 1. COMPANIES
-- Stores the stock universe and sector information.
-- ============================================================

CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(100) NOT NULL,
    sector VARCHAR(100) NOT NULL
);


-- ============================================================
-- 2. PRICES
-- Stores historical stock prices and adjusted prices.
-- One record per company per trading day.
-- ============================================================

CREATE TABLE prices (
    company_id INTEGER NOT NULL,
    trade_date DATE NOT NULL,

    -- Raw NSE prices
    open_price NUMERIC(15, 2),
    high_price NUMERIC(15, 2),
    low_price NUMERIC(15, 2),
    close_price NUMERIC(15, 2),

    -- Corporate-action-adjusted prices
    adjusted_open_price NUMERIC(15, 2),
    adjusted_high_price NUMERIC(15, 2),
    adjusted_low_price NUMERIC(15, 2),
    adjusted_close_price NUMERIC(15, 2),

    -- Trading volume
    volume BIGINT,

    -- Daily return based on adjusted price
    daily_return NUMERIC(12, 8),

    -- Corporate-action adjustment factor
    adjustment_factor_applied NUMERIC(12, 4) DEFAULT 1.0,

    PRIMARY KEY (company_id, trade_date),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 3. PRICE IMPORT
-- Temporary/import layer matching the processed CSV structure.
-- Raw imported data is loaded here before inserting into prices.
-- ============================================================

CREATE TABLE price_import (
    symbol VARCHAR(20),
    series VARCHAR(10),
    trade_date DATE,
    prev_close NUMERIC,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    last_price NUMERIC,
    close_price NUMERIC,
    average_price NUMERIC,
    total_traded_quantity BIGINT,
    turnover_inr NUMERIC,
    no_of_trades BIGINT,
    deliverable_qty BIGINT,
    deliverable_pct NUMERIC,
    daily_return NUMERIC,
    adjustment_factor_applied NUMERIC,
    adjusted_open_price NUMERIC,
    adjusted_high_price NUMERIC,
    adjusted_low_price NUMERIC,
    adjusted_close_price NUMERIC,
    adjusted_last_price NUMERIC,
    adjusted_average_price NUMERIC,
    adjusted_prev_close NUMERIC,
    adjusted_daily_return NUMERIC,
    corporate_action_date BOOLEAN,
    raw_extreme_return BOOLEAN,
    adjusted_extreme_return BOOLEAN
);


-- ============================================================
-- 4. BENCHMARKS
-- Stores NIFTY 50 historical index data.
-- ============================================================

CREATE TABLE benchmarks (
    index_name VARCHAR(50) NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(15, 2),
    high_price NUMERIC(15, 2),
    low_price NUMERIC(15, 2),
    close_price NUMERIC(15, 2),
    daily_return NUMERIC(12, 8),

    UNIQUE (index_name, trade_date)
);


-- ============================================================
-- 5. MARKET VOLATILITY
-- Stores India VIX historical data.
-- ============================================================

CREATE TABLE market_volatility (
    trade_date DATE NOT NULL,
    open_value NUMERIC(15, 4),
    high_value NUMERIC(15, 4),
    low_value NUMERIC(15, 4),
    close_value NUMERIC(15, 4),
    prev_close NUMERIC(15, 4),
    daily_change NUMERIC(15, 4),
    pct_change NUMERIC(12, 4),
    daily_return NUMERIC(12, 8),

    UNIQUE (trade_date)
);


-- ============================================================
-- 6. PORTFOLIO HOLDINGS
-- Stores the initial portfolio allocation and share quantities.
-- ============================================================

CREATE TABLE portfolio_holdings (
    holding_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    portfolio_weight NUMERIC(8, 6) NOT NULL,
    allocated_capital NUMERIC(15, 2) NOT NULL,
    purchase_price NUMERIC(15, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    invested_amount NUMERIC(15, 2) NOT NULL,
    unused_cash NUMERIC(15, 2) NOT NULL,
    purchase_date DATE NOT NULL,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 7. TRANSACTIONS
-- Stores portfolio buy/sell transactions.
-- ============================================================

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC(15, 2) NOT NULL,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);