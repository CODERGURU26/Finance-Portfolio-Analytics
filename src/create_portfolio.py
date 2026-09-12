from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ADJUSTED_STOCKS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "stocks_adjusted"
)

PORTFOLIO_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "portfolio"
)

PORTFOLIO_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# PORTFOLIO CONFIGURATION
# ============================================================

INITIAL_CAPITAL = 1_000_000

PORTFOLIO_DATE = pd.Timestamp("2025-09-12")

TARGET_WEIGHTS = {
    "RELIANCE": 0.15,
    "HDFCBANK": 0.15,
    "ICICIBANK": 0.10,
    "SBIN": 0.05,
    "TCS": 0.15,
    "INFY": 0.10,
    "ITC": 0.05,
    "LT": 0.10,
    "TITAN": 0.05,
    "BAJFINANCE": 0.10,
}


# ============================================================
# LOAD PRICES
# ============================================================

print("=" * 70)
print("PORTFOLIO CONSTRUCTION")
print("=" * 70)

prices = []


for symbol, weight in TARGET_WEIGHTS.items():

    file_path = (
        ADJUSTED_STOCKS_DIR
        / f"{symbol}_adjusted.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Adjusted data not found for {symbol}:\n"
            f"{file_path}"
        )

    df = pd.read_csv(file_path)

    df.columns = df.columns.str.strip()

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce"
    )

    df["adjusted_close_price"] = pd.to_numeric(
        df["adjusted_close_price"],
        errors="coerce"
    )

    row = df[
        df["trade_date"] == PORTFOLIO_DATE
    ]

    if row.empty:
        raise ValueError(
            f"No price found for {symbol} "
            f"on {PORTFOLIO_DATE.date()}"
        )

    price = float(
        row["adjusted_close_price"].iloc[0]
    )

    allocated_capital = (
        INITIAL_CAPITAL * weight
    )

    quantity = int(
        allocated_capital // price
    )

    invested_amount = (
        quantity * price
    )

    prices.append(
        {
            "symbol": symbol,
            "portfolio_weight": weight,
            "allocated_capital": allocated_capital,
            "purchase_price": price,
            "quantity": quantity,
            "invested_amount": invested_amount,
            "unused_cash": (
                allocated_capital
                - invested_amount
            ),
        }
    )


# ============================================================
# CREATE HOLDINGS DATAFRAME
# ============================================================

holdings = pd.DataFrame(prices)

holdings.insert(
    0,
    "holding_id",
    range(1, len(holdings) + 1)
)

# Map company IDs
company_ids = {
    "RELIANCE": 1,
    "HDFCBANK": 2,
    "ICICIBANK": 3,
    "SBIN": 4,
    "TCS": 5,
    "INFY": 6,
    "ITC": 7,
    "LT": 8,
    "TITAN": 9,
    "BAJFINANCE": 10,
}

holdings.insert(
    1,
    "company_id",
    holdings["symbol"].map(company_ids)
)

holdings["purchase_date"] = (
    PORTFOLIO_DATE.date()
)


# ============================================================
# CALCULATE TOTALS
# ============================================================

total_invested = (
    holdings["invested_amount"].sum()
)

total_unused_cash = (
    holdings["unused_cash"].sum()
)

portfolio_total = (
    total_invested
    + total_unused_cash
)

actual_invested_weight = (
    holdings["invested_amount"]
    / INITIAL_CAPITAL
)


# ============================================================
# DISPLAY
# ============================================================

print(
    f"\nInitial capital: "
    f"₹{INITIAL_CAPITAL:,.2f}"
)

print(
    f"Portfolio date: "
    f"{PORTFOLIO_DATE.date()}"
)

print("\nPortfolio construction:")

print(
    holdings[
        [
            "symbol",
            "portfolio_weight",
            "purchase_price",
            "quantity",
            "allocated_capital",
            "invested_amount",
            "unused_cash",
        ]
    ].to_string(index=False)
)

print(
    f"\nTotal invested: "
    f"₹{total_invested:,.2f}"
)

print(
    f"Unused cash: "
    f"₹{total_unused_cash:,.2f}"
)

print(
    f"Total capital accounted for: "
    f"₹{portfolio_total:,.2f}"
)


# ============================================================
# SAVE HOLDINGS
# ============================================================

holdings_file = (
    PORTFOLIO_DIR
    / "portfolio_holdings.csv"
)

holdings.to_csv(
    holdings_file,
    index=False
)

print(
    f"\nHoldings saved to:\n"
    f"{holdings_file}"
)


# ============================================================
# CREATE TRANSACTIONS
# ============================================================

transactions = holdings[
    [
        "holding_id",
        "company_id",
        "symbol",
        "purchase_date",
        "quantity",
        "purchase_price",
    ]
].copy()

transactions = transactions.rename(
    columns={
        "holding_id": "transaction_id",
        "purchase_date": "transaction_date",
        "purchase_price": "price",
    }
)

transactions.insert(
    4,
    "transaction_type",
    "BUY"
)

transactions_file = (
    PORTFOLIO_DIR
    / "transactions.csv"
)

transactions.to_csv(
    transactions_file,
    index=False
)

print(
    f"Transactions saved to:\n"
    f"{transactions_file}"
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

print(
    f"\nTarget weight total: "
    f"{holdings['portfolio_weight'].sum():.2%}"
)

print(
    f"Number of holdings: "
    f"{len(holdings)}"
)

print(
    f"Total invested: "
    f"₹{total_invested:,.2f}"
)

print(
    f"Remaining cash: "
    f"₹{total_unused_cash:,.2f}"
)

print(
    f"Capital check: "
    f"₹{portfolio_total:,.2f}"
)

print("\n" + "=" * 70)
print("PORTFOLIO CONSTRUCTION COMPLETED")
print("=" * 70)