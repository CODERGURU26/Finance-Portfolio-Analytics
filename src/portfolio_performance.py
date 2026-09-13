from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PORTFOLIO_DIR = PROJECT_ROOT / "data" / "processed" / "portfolio"
ADJUSTED_STOCKS_DIR = PROJECT_ROOT / "data" / "processed" / "stocks_adjusted"

HOLDINGS_FILE = PORTFOLIO_DIR / "portfolio_holdings.csv"

START_DATE = pd.Timestamp("2025-09-12")

TRADING_DAYS_PER_YEAR = 252


# ============================================================
# LOAD PORTFOLIO HOLDINGS
# ============================================================

holdings = pd.read_csv(HOLDINGS_FILE)

holdings["purchase_date"] = pd.to_datetime(
    holdings["purchase_date"]
)

print("=" * 70)
print("PHASE 6 — PORTFOLIO PERFORMANCE ENGINE")
print("=" * 70)

print(f"\nPortfolio start date: {START_DATE.date()}")
print(f"Number of holdings: {len(holdings)}")


# ============================================================
# INITIAL PORTFOLIO INFORMATION
# ============================================================

initial_capital = holdings["allocated_capital"].sum()
initial_invested = holdings["invested_amount"].sum()
initial_cash = holdings["unused_cash"].sum()

print(f"Initial capital: ₹{initial_capital:,.2f}")
print(f"Initial invested: ₹{initial_invested:,.2f}")
print(f"Initial cash: ₹{initial_cash:,.2f}")

capital_check = initial_invested + initial_cash

if abs(capital_check - initial_capital) > 0.01:
    raise ValueError(
        "Capital validation failed: invested amount + cash "
        "does not equal initial capital."
    )


# ============================================================
# LOAD ADJUSTED STOCK PRICE DATA
# ============================================================

symbols = holdings["symbol"].tolist()

price_data = {}

print("\nLoading adjusted stock data...")

for symbol in symbols:

    file_path = (
        ADJUSTED_STOCKS_DIR /
        f"{symbol}_adjusted.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Adjusted stock file not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    df["trade_date"] = pd.to_datetime(
        df["trade_date"]
    )

    df = df[
        df["trade_date"] >= START_DATE
    ].copy()

    df = df.sort_values("trade_date")

    if df.empty:
        raise ValueError(
            f"No price data available for {symbol} "
            f"after {START_DATE.date()}."
        )

    df = df[
        [
            "trade_date",
            "adjusted_close_price"
        ]
    ].copy()

    df = df.rename(
        columns={
            "adjusted_close_price": symbol
        }
    )

    price_data[symbol] = df

    print(
        f"  {symbol:<12} "
        f"{len(df):>4} trading days | "
        f"{df['trade_date'].min().date()} → "
        f"{df['trade_date'].max().date()}"
    )


# ============================================================
# BUILD PRICE MATRIX
# ============================================================

print("\nBuilding portfolio price matrix...")

prices = None

for symbol, df in price_data.items():

    if prices is None:
        prices = df
    else:
        prices = prices.merge(
            df,
            on="trade_date",
            how="outer"
        )

prices = (
    prices
    .sort_values("trade_date")
    .reset_index(drop=True)
)


# ============================================================
# VALIDATE PRICE DATA
# ============================================================

price_columns = symbols

missing_prices = prices[price_columns].isna().sum()

print("\nMissing prices after start date:")

for symbol in symbols:
    print(
        f"  {symbol:<12}: "
        f"{missing_prices[symbol]}"
    )

if missing_prices.sum() > 0:
    raise ValueError(
        "Missing stock prices detected. "
        "We will not silently forward-fill portfolio prices."
    )


# ============================================================
# CALCULATE DAILY POSITION VALUES
# ============================================================

print("\nCalculating daily position values...")

for _, holding in holdings.iterrows():

    symbol = holding["symbol"]
    quantity = holding["quantity"]

    prices[f"{symbol}_value"] = (
        prices[symbol] * quantity
    )


# ============================================================
# TOTAL INVESTED POSITION VALUE
# ============================================================

position_value_columns = [
    f"{symbol}_value"
    for symbol in symbols
]

prices["invested_position_value"] = (
    prices[position_value_columns].sum(axis=1)
)


# ============================================================
# CASH BALANCE
# ============================================================

# No transactions occur after portfolio creation,
# therefore cash remains constant.

prices["cash_balance"] = initial_cash


# ============================================================
# TOTAL PORTFOLIO VALUE
# ============================================================

prices["portfolio_value"] = (
    prices["invested_position_value"]
    + prices["cash_balance"]
)


# ============================================================
# DAILY PORTFOLIO RETURN
# ============================================================

prices["daily_return"] = (
    prices["portfolio_value"]
    .pct_change()
)


# ============================================================
# CUMULATIVE PORTFOLIO RETURN
# ============================================================

prices["cumulative_return"] = (
    prices["portfolio_value"]
    / initial_capital
) - 1


# ============================================================
# PERFORMANCE PERIOD
# ============================================================

first_date = prices["trade_date"].min()
last_date = prices["trade_date"].max()

calendar_days = (
    last_date - first_date
).days

years = calendar_days / 365.25


# ============================================================
# ANNUALIZED RETURN
# ============================================================

ending_value = prices["portfolio_value"].iloc[-1]

if years > 0:

    annualized_return = (
        (ending_value / initial_capital)
        ** (1 / years)
    ) - 1

else:

    annualized_return = np.nan


# ============================================================
# ANNUALIZED VOLATILITY
# ============================================================

daily_returns = (
    prices["daily_return"]
    .dropna()
)

annualized_volatility = (
    daily_returns.std()
    * np.sqrt(TRADING_DAYS_PER_YEAR)
)


# ============================================================
# MONTHLY PERFORMANCE
# ============================================================

monthly = prices[
    [
        "trade_date",
        "portfolio_value"
    ]
].copy()

monthly["year_month"] = (
    monthly["trade_date"]
    .dt.to_period("M")
)

# Last portfolio value for each calendar month
monthly_end = (
    monthly
    .groupby("year_month")
    .agg(
        month_end_value=(
            "portfolio_value",
            "last"
        )
    )
    .reset_index()
)

# Previous month's ending value
monthly_end["previous_month_end_value"] = (
    monthly_end["month_end_value"].shift(1)
)

# For the first month, use the initial portfolio capital
monthly_end.loc[
    0,
    "previous_month_end_value"
] = initial_capital

# Monthly return
monthly_end["monthly_return"] = (
    monthly_end["month_end_value"]
    / monthly_end["previous_month_end_value"]
) - 1

# Convert Period to string for CSV / Power BI
monthly_end["year_month"] = (
    monthly_end["year_month"]
    .astype(str)
)

monthly_performance = monthly_end[
    [
        "year_month",
        "previous_month_end_value",
        "month_end_value",
        "monthly_return"
    ]
].copy()

# ============================================================
# INDIVIDUAL STOCK PERFORMANCE
# ============================================================

stock_performance = []

for symbol in symbols:

    start_price = prices[symbol].iloc[0]
    end_price = prices[symbol].iloc[-1]

    stock_return = (
        end_price / start_price
    ) - 1

    holding = holdings[
        holdings["symbol"] == symbol
    ].iloc[0]

    initial_position_value = (
        holding["invested_amount"]
    )

    ending_position_value = (
        prices[f"{symbol}_value"].iloc[-1]
    )

    stock_performance.append(
        {
            "symbol": symbol,
            "initial_price": start_price,
            "ending_price": end_price,
            "stock_return": stock_return,
            "initial_position_value": initial_position_value,
            "ending_position_value": ending_position_value
        }
    )

stock_performance = pd.DataFrame(
    stock_performance
)

stock_performance = stock_performance.sort_values(
    "stock_return",
    ascending=False
).reset_index(drop=True)


# ============================================================
# BEST / WORST STOCK
# ============================================================

best_stock = (
    stock_performance.iloc[0]
)

worst_stock = (
    stock_performance.iloc[-1]
)


# ============================================================
# SAVE DAILY PERFORMANCE
# ============================================================

daily_output_file = (
    PORTFOLIO_DIR /
    "portfolio_daily_performance.csv"
)

prices.to_csv(
    daily_output_file,
    index=False
)


# ============================================================
# SAVE MONTHLY PERFORMANCE
# ============================================================

monthly_output_file = (
    PORTFOLIO_DIR /
    "portfolio_monthly_performance.csv"
)

monthly_performance.to_csv(
    monthly_output_file,
    index=False
)


# ============================================================
# SAVE STOCK PERFORMANCE
# ============================================================

stock_output_file = (
    PORTFOLIO_DIR /
    "stock_performance.csv"
)

stock_performance.to_csv(
    stock_output_file,
    index=False
)


# ============================================================
# SAVE SUMMARY METRICS
# ============================================================

metrics = pd.DataFrame(
    [
        {
            "metric": "Initial Capital",
            "value": initial_capital
        },
        {
            "metric": "Initial Invested",
            "value": initial_invested
        },
        {
            "metric": "Initial Cash",
            "value": initial_cash
        },
        {
            "metric": "Ending Portfolio Value",
            "value": ending_value
        },
        {
            "metric": "Total Return",
            "value": prices["cumulative_return"].iloc[-1]
        },
        {
            "metric": "Annualized Return",
            "value": annualized_return
        },
        {
            "metric": "Annualized Volatility",
            "value": annualized_volatility
        },
        {
            "metric": "Best Stock Return",
            "value": best_stock["stock_return"]
        },
        {
            "metric": "Worst Stock Return",
            "value": worst_stock["stock_return"]
        }
    ]
)

metrics_output_file = (
    PORTFOLIO_DIR /
    "portfolio_performance_metrics.csv"
)

metrics.to_csv(
    metrics_output_file,
    index=False
)


# ============================================================
# VALIDATION
# ============================================================

first_day = prices.iloc[0]
last_day = prices.iloc[-1]

print("\n" + "=" * 70)
print("PERFORMANCE VALIDATION")
print("=" * 70)

print(
    f"\nFirst trading date: "
    f"{first_day['trade_date'].date()}"
)

print(
    f"Last trading date:  "
    f"{last_day['trade_date'].date()}"
)

print(
    f"Trading days:       "
    f"{len(prices)}"
)

print(
    f"\nStarting portfolio value: "
    f"₹{first_day['portfolio_value']:,.2f}"
)

print(
    f"Ending portfolio value:   "
    f"₹{last_day['portfolio_value']:,.2f}"
)

print(
    f"Total portfolio return:    "
    f"{last_day['cumulative_return']:.2%}"
)

print(
    f"Annualized return:         "
    f"{annualized_return:.2%}"
)

print(
    f"Annualized volatility:     "
    f"{annualized_volatility:.2%}"
)

print(
    f"\nBest stock: "
    f"{best_stock['symbol']} "
    f"({best_stock['stock_return']:.2%})"
)

print(
    f"Worst stock: "
    f"{worst_stock['symbol']} "
    f"({worst_stock['stock_return']:.2%})"
)

print(
    f"\nMinimum portfolio value: "
    f"₹{prices['portfolio_value'].min():,.2f}"
)

print(
    f"Maximum portfolio value: "
    f"₹{prices['portfolio_value'].max():,.2f}"
)


# ============================================================
# STARTING VALUE VALIDATION
# ============================================================

if abs(
    first_day["portfolio_value"]
    - initial_capital
) > 0.01:

    raise ValueError(
        "Starting portfolio value does not "
        "equal initial capital."
    )


# ============================================================
# OUTPUT FILES
# ============================================================

print("\nOutput files:")

print(
    f"  Daily performance:"
    f"\n  {daily_output_file}"
)

print(
    f"\n  Monthly performance:"
    f"\n  {monthly_output_file}"
)

print(
    f"\n  Stock performance:"
    f"\n  {stock_output_file}"
)

print(
    f"\n  Performance metrics:"
    f"\n  {metrics_output_file}"
)


print("\n" + "=" * 70)
print("PHASE 6.2 COMPLETED")
print("=" * 70)