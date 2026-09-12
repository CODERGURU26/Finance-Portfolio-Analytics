from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_STOCKS_DIR = PROJECT_ROOT / "data" / "processed" / "stocks"
CORPORATE_ACTIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "corporate_actions"
    / "corporate_actions.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "stocks_adjusted"
REPORTS_DIR = PROJECT_ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

PRICE_COLUMNS = [
    "open_price",
    "high_price",
    "low_price",
    "close_price",
]

OPTIONAL_PRICE_COLUMNS = [
    "last_price",
    "average_price",
    "prev_close",
]


# ============================================================
# LOAD CORPORATE ACTIONS
# ============================================================

print("=" * 70)
print("CORPORATE ACTION ADJUSTMENT PIPELINE")
print("=" * 70)

print("\nLoading corporate actions...")

if not CORPORATE_ACTIONS_FILE.exists():
    raise FileNotFoundError(
        f"Corporate actions file not found:\n{CORPORATE_ACTIONS_FILE}"
    )

corporate_actions = pd.read_csv(CORPORATE_ACTIONS_FILE)

# Clean column names
corporate_actions.columns = corporate_actions.columns.str.strip()

required_columns = {
    "Symbol",
    "Ex-Date",
    "Action",
    "Adjustment Factor",
}

missing_columns = required_columns - set(corporate_actions.columns)

if missing_columns:
    raise ValueError(
        f"Missing columns in corporate_actions.csv: {missing_columns}"
    )

# Standardize values
corporate_actions["Symbol"] = (
    corporate_actions["Symbol"]
    .astype(str)
    .str.strip()
    .str.upper()
)

corporate_actions["Ex-Date"] = pd.to_datetime(
    corporate_actions["Ex-Date"],
    errors="coerce",
)

corporate_actions["Action"] = (
    corporate_actions["Action"]
    .astype(str)
    .str.strip()
)

corporate_actions["Adjustment Factor"] = pd.to_numeric(
    corporate_actions["Adjustment Factor"],
    errors="coerce",
)

# Validate corporate actions
if corporate_actions["Ex-Date"].isna().any():
    raise ValueError("Invalid Ex-Date found in corporate_actions.csv")

if corporate_actions["Adjustment Factor"].isna().any():
    raise ValueError(
        "Invalid Adjustment Factor found in corporate_actions.csv"
    )

if (corporate_actions["Adjustment Factor"] <= 0).any():
    raise ValueError(
        "Adjustment Factor must be greater than zero."
    )

corporate_actions = corporate_actions.sort_values(
    ["Symbol", "Ex-Date"]
).reset_index(drop=True)

print("\nCorporate actions loaded:")
print(corporate_actions.to_string(index=False))


# ============================================================
# PROCESS STOCK FILES
# ============================================================

stock_files = sorted(PROCESSED_STOCKS_DIR.glob("*_clean.csv"))

if not stock_files:
    raise FileNotFoundError(
        f"No cleaned stock files found in:\n{PROCESSED_STOCKS_DIR}"
    )

print(f"\nFound {len(stock_files)} cleaned stock files.")

adjustment_report = []


for stock_file in stock_files:

    symbol = stock_file.stem.replace("_clean", "").upper()

    print("\n" + "-" * 70)
    print(f"Processing: {symbol}")
    print("-" * 70)

    # --------------------------------------------------------
    # Load cleaned stock data
    # --------------------------------------------------------

    df = pd.read_csv(stock_file)

    df.columns = df.columns.str.strip()

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_stock_columns = {
        "symbol",
        "trade_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
    }

    missing_stock_columns = (
        required_stock_columns - set(df.columns)
    )

    if missing_stock_columns:
        raise ValueError(
            f"{symbol}: missing columns {missing_stock_columns}"
        )

    # --------------------------------------------------------
    # Parse dates
    # --------------------------------------------------------

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce",
    )

    if df["trade_date"].isna().any():
        raise ValueError(
            f"{symbol}: invalid trade_date found."
        )

    # --------------------------------------------------------
    # Sort data
    # --------------------------------------------------------

    df = df.sort_values("trade_date").reset_index(drop=True)

    # --------------------------------------------------------
    # Store original values for validation
    # --------------------------------------------------------

    original_close = df["close_price"].copy()

    # --------------------------------------------------------
    # Create cumulative adjustment factor
    #
    # Factor = 1 means no adjustment.
    #
    # For example:
    #
    # BAJFINANCE:
    # 2:1 split + 4:1 bonus
    # combined factor = 10
    #
    # Historical prices BEFORE the ex-date are divided by 10.
    # --------------------------------------------------------

    df["adjustment_factor_applied"] = 1.0

    symbol_actions = corporate_actions[
        corporate_actions["Symbol"] == symbol
    ].copy()

    if symbol_actions.empty:

        print("No corporate actions found.")

    else:

        print("\nCorporate actions applied:")

        for _, action in symbol_actions.iterrows():

            ex_date = action["Ex-Date"]
            factor = float(action["Adjustment Factor"])
            action_name = action["Action"]

            print(
                f"  {ex_date.date()} | "
                f"{action_name} | "
                f"Factor: {factor}"
            )

            # IMPORTANT:
            # Only dates BEFORE the ex-date are adjusted.
            #
            # The ex-date price is already trading on the
            # post-corporate-action basis.
            mask = df["trade_date"] < ex_date

            df.loc[
                mask,
                "adjustment_factor_applied"
            ] *= factor

    # --------------------------------------------------------
    # Create adjusted OHLC prices
    # --------------------------------------------------------

    for column in PRICE_COLUMNS:

        adjusted_column = f"adjusted_{column}"

        df[adjusted_column] = (
            df[column]
            / df["adjustment_factor_applied"]
        )

    # --------------------------------------------------------
    # Adjust optional price columns if present
    # --------------------------------------------------------

    for column in OPTIONAL_PRICE_COLUMNS:

        if column in df.columns:

            adjusted_column = f"adjusted_{column}"

            df[adjusted_column] = (
                df[column]
                / df["adjustment_factor_applied"]
            )

    # --------------------------------------------------------
    # Calculate adjusted daily return
    # --------------------------------------------------------

    df["adjusted_daily_return"] = (
        df["adjusted_close_price"]
        .pct_change()
    )

    # --------------------------------------------------------
    # Identify corporate-action dates
    # --------------------------------------------------------

    df["corporate_action_date"] = False

    for _, action in symbol_actions.iterrows():

        ex_date = action["Ex-Date"]

        df.loc[
            df["trade_date"] == ex_date,
            "corporate_action_date"
        ] = True

    # --------------------------------------------------------
    # Identify large raw returns
    # --------------------------------------------------------

    if "daily_return" in df.columns:

        df["raw_extreme_return"] = (
            df["daily_return"].abs() > 0.20
        )

    else:

        df["raw_extreme_return"] = False

    # --------------------------------------------------------
    # Identify large adjusted returns
    # --------------------------------------------------------

    df["adjusted_extreme_return"] = (
        df["adjusted_daily_return"].abs() > 0.20
    )

    # --------------------------------------------------------
    # Count extreme returns before / after adjustment
    # --------------------------------------------------------

    raw_extreme_count = int(
        df["raw_extreme_return"].sum()
    )

    adjusted_extreme_count = int(
        df["adjusted_extreme_return"].sum()
    )

    # --------------------------------------------------------
    # Check whether adjusted prices are valid
    # --------------------------------------------------------

    invalid_adjusted_prices = int(
        (
            df["adjusted_close_price"] <= 0
        ).sum()
    )

    # --------------------------------------------------------
    # Save adjusted dataset
    # --------------------------------------------------------

    output_file = OUTPUT_DIR / f"{symbol}_adjusted.csv"

    df.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nSaved: {output_file}"
    )

    # --------------------------------------------------------
    # Show corporate-action verification
    # --------------------------------------------------------

    if not symbol_actions.empty:

        print("\nCorporate-action verification:")

        for _, action in symbol_actions.iterrows():

            ex_date = action["Ex-Date"]

            event_rows = df[
                df["trade_date"].between(
                    ex_date - pd.Timedelta(days=3),
                    ex_date + pd.Timedelta(days=3),
                )
            ][
                [
                    "trade_date",
                    "close_price",
                    "adjusted_close_price",
                    "daily_return",
                    "adjusted_daily_return",
                    "adjustment_factor_applied",
                ]
            ]

            print(
                f"\nEvent: {action['Action']} "
                f"| Ex-Date: {ex_date.date()}"
            )

            print(
                event_rows.to_string(index=False)
            )

    # --------------------------------------------------------
    # Add report row
    # --------------------------------------------------------

    adjustment_report.append(
        {
            "symbol": symbol,
            "rows": len(df),
            "corporate_actions": len(symbol_actions),
            "raw_extreme_returns": raw_extreme_count,
            "adjusted_extreme_returns": adjusted_extreme_count,
            "invalid_adjusted_prices": invalid_adjusted_prices,
            "min_adjustment_factor": df[
                "adjustment_factor_applied"
            ].min(),
            "max_adjustment_factor": df[
                "adjustment_factor_applied"
            ].max(),
            "output_file": str(output_file),
        }
    )


# ============================================================
# SAVE ADJUSTMENT REPORT
# ============================================================

report_df = pd.DataFrame(adjustment_report)

report_file = (
    REPORTS_DIR
    / "corporate_action_adjustment_report.csv"
)

report_df.to_csv(
    report_file,
    index=False,
)

print("\n" + "=" * 70)
print("ADJUSTMENT PIPELINE COMPLETED")
print("=" * 70)

print("\nSummary:")
print(
    report_df[
        [
            "symbol",
            "corporate_actions",
            "raw_extreme_returns",
            "adjusted_extreme_returns",
            "min_adjustment_factor",
            "max_adjustment_factor",
        ]
    ].to_string(index=False)
)

print(f"\nReport saved to:")
print(report_file)

print("\nAdjusted files saved to:")
print(OUTPUT_DIR)