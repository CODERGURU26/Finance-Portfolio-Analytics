from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
STOCKS_DIR = RAW_DIR / "Stocks"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_STOCKS_DIR = PROCESSED_DIR / "stocks"
PROCESSED_NIFTY_DIR = PROCESSED_DIR / "nifty50"
PROCESSED_VIX_DIR = PROCESSED_DIR / "india_vix"

REPORTS_DIR = PROJECT_ROOT / "reports"


# ============================================================
# EXPECTED STOCK COLUMNS
# ============================================================

STOCK_COLUMN_MAP = {
    "Symbol": "symbol",
    "Series": "series",
    "Date": "trade_date",
    "Prev Close": "prev_close",
    "Open Price": "open_price",
    "High Price": "high_price",
    "Low Price": "low_price",
    "Last Price": "last_price",
    "Close Price": "close_price",
    "Average Price": "average_price",
    "Total Traded Quantity": "total_traded_quantity",
    "Turnover ₹": "turnover_inr",
    "No. of Trades": "no_of_trades",
    "Deliverable Qty": "deliverable_qty",
    "% Dly Qt to Traded Qty": "deliverable_pct",
}


STOCK_NUMERIC_COLUMNS = [
    "prev_close",
    "open_price",
    "high_price",
    "low_price",
    "last_price",
    "close_price",
    "average_price",
    "total_traded_quantity",
    "turnover_inr",
    "no_of_trades",
    "deliverable_qty",
    "deliverable_pct",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_numeric(series):
    """
    Convert NSE formatted numeric values into numbers.

    Examples:
        '5,95,44,85,894.70' -> 5954485894.70
        '1,23,456'          -> 123456
        '100.50'            -> 100.50
    """

    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce"
    )


def validate_ohlc(df, open_col, high_col, low_col, close_col):
    """
    Validate basic OHLC relationships.
    """

    required_columns = [
        open_col,
        high_col,
        low_col,
        close_col
    ]

    if not all(
        column in df.columns
        for column in required_columns
    ):
        return {
            "bad_ohlc_rows": None,
            "non_positive_price_rows": None
        }

    bad_ohlc = (
        (df[high_col] < df[open_col])
        | (df[high_col] < df[close_col])
        | (df[high_col] < df[low_col])
        | (df[low_col] > df[open_col])
        | (df[low_col] > df[close_col])
        | (df[low_col] > df[high_col])
    )

    non_positive_prices = (
        (df[open_col] <= 0)
        | (df[high_col] <= 0)
        | (df[low_col] <= 0)
        | (df[close_col] <= 0)
    )

    return {
        "bad_ohlc_rows": int(bad_ohlc.sum()),
        "non_positive_price_rows": int(
            non_positive_prices.sum()
        )
    }


# ============================================================
# CLEAN STOCK DATA
# ============================================================

def clean_stock_file(file_path):

    print("\n" + "=" * 90)
    print(f"CLEANING STOCK: {file_path.name}")
    print("=" * 90)

    # --------------------------------------------------------
    # Read raw CSV
    # --------------------------------------------------------

    df = pd.read_csv(file_path)

    original_rows = len(df)

    # --------------------------------------------------------
    # Remove whitespace from headers
    #
    # NSE headers may contain trailing spaces:
    # 'Symbol  ' -> 'Symbol'
    # 'Date  '   -> 'Date'
    # --------------------------------------------------------

    df.columns = df.columns.str.strip()

    # --------------------------------------------------------
    # Rename columns
    # --------------------------------------------------------

    df = df.rename(
        columns=STOCK_COLUMN_MAP
    )

    # --------------------------------------------------------
    # Check expected columns
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in STOCK_COLUMN_MAP.values()
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Missing expected columns in "
            f"{file_path.name}: "
            f"{missing_columns}"
        )

    # --------------------------------------------------------
    # Parse date
    #
    # NSE format:
    # 11-Sep-2026
    # --------------------------------------------------------

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        format="%d-%b-%Y",
        errors="coerce"
    )

    invalid_dates = int(
        df["trade_date"].isna().sum()
    )

    # --------------------------------------------------------
    # Clean numeric columns
    # --------------------------------------------------------

    conversion_failures = {}

    for column in STOCK_NUMERIC_COLUMNS:

        before = df[column].notna().sum()

        df[column] = clean_numeric(
            df[column]
        )

        after = df[column].notna().sum()

        conversion_failures[column] = int(
            before - after
        )

    # --------------------------------------------------------
    # Clean text columns
    # --------------------------------------------------------

    df["symbol"] = (
        df["symbol"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["series"] = (
        df["series"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Keep only regular equity records.
    #
    # NSE data may contain multiple series such as:
    # EQ, BL, W3, T0, etc.
    #
    # For portfolio and risk analysis,
    # we use the regular EQ series.
    # --------------------------------------------------------

    rows_before_eq_filter = len(df)

    df = df[
        df["series"] == "EQ"
    ].copy()

    rows_removed_by_series_filter = (
        rows_before_eq_filter - len(df)
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        by=["symbol", "trade_date"]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Duplicate checks BEFORE removal
    # --------------------------------------------------------

    duplicate_rows = int(
        df.duplicated().sum()
    )

    duplicate_symbol_dates = int(
        df.duplicated(
            subset=[
                "symbol",
                "trade_date"
            ]
        ).sum()
    )

    # --------------------------------------------------------
    # Remove remaining duplicate symbol/date records
    # --------------------------------------------------------

    if duplicate_symbol_dates > 0:

        df = df.drop_duplicates(
            subset=[
                "symbol",
                "trade_date"
            ],
            keep="last"
        ).reset_index(
            drop=True
        )

    # --------------------------------------------------------
    # Daily return
    #
    # IMPORTANT:
    # Calculated AFTER:
    # 1. EQ filtering
    # 2. Duplicate removal
    # 3. Chronological sorting
    # --------------------------------------------------------

    df["daily_return"] = (
        df.groupby("symbol")[
            "close_price"
        ].pct_change()
    )

    # --------------------------------------------------------
    # Extreme daily returns
    #
    # We FLAG them.
    # We do NOT automatically remove them.
    #
    # Large movements may be caused by:
    # - corporate actions
    # - genuine market movements
    # - data problems
    # --------------------------------------------------------

    extreme_return_count = int(
        df["daily_return"]
        .abs()
        .gt(0.20)
        .sum()
    )

    # --------------------------------------------------------
    # OHLC validation
    # --------------------------------------------------------

    ohlc_results = validate_ohlc(
        df,
        "open_price",
        "high_price",
        "low_price",
        "close_price"
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    missing_cells = int(
        df.isna().sum().sum()
    )

    # --------------------------------------------------------
    # Negative / zero volume
    # --------------------------------------------------------

    non_positive_volume = int(
        (
            df["total_traded_quantity"] <= 0
        ).sum()
    )

    # --------------------------------------------------------
    # Output filename
    # --------------------------------------------------------

    symbol_values = (
        df["symbol"]
        .dropna()
        .unique()
    )

    if len(symbol_values) == 0:

        raise ValueError(
            f"No valid symbol found in "
            f"{file_path.name}"
        )

    symbol = symbol_values[0]

    output_file = (
        PROCESSED_STOCKS_DIR
        / f"{symbol}_clean.csv"
    )

    # --------------------------------------------------------
    # Save processed data
    # --------------------------------------------------------

    df.to_csv(
        output_file,
        index=False
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print(
        f"Symbol                  : {symbol}"
    )

    print(
        f"Original rows           : "
        f"{original_rows:,}"
    )

    print(
        f"Rows removed (non-EQ)   : "
        f"{rows_removed_by_series_filter:,}"
    )

    print(
        f"Final rows              : "
        f"{len(df):,}"
    )

    print(
        f"Date range              : "
        f"{df['trade_date'].min().date()} "
        f"→ "
        f"{df['trade_date'].max().date()}"
    )

    print(
        f"Invalid dates           : "
        f"{invalid_dates:,}"
    )

    print(
        f"Duplicate rows          : "
        f"{duplicate_rows:,}"
    )

    print(
        f"Duplicate symbol/dates  : "
        f"{duplicate_symbol_dates:,}"
    )

    print(
        f"Missing cells           : "
        f"{missing_cells:,}"
    )

    print(
        f"Bad OHLC rows           : "
        f"{ohlc_results['bad_ohlc_rows']}"
    )

    print(
        f"Non-positive prices     : "
        f"{ohlc_results['non_positive_price_rows']}"
    )

    print(
        f"Non-positive volume     : "
        f"{non_positive_volume:,}"
    )

    print(
        f"Extreme returns >20%    : "
        f"{extreme_return_count:,}"
    )

    # --------------------------------------------------------
    # Conversion warnings
    # --------------------------------------------------------

    failed_conversions = {
        column: count
        for column, count
        in conversion_failures.items()
        if count > 0
    }

    if failed_conversions:

        print("\nNumeric conversion issues:")

        for column, count in failed_conversions.items():

            print(
                f"  {column}: "
                f"{count:,}"
            )

    else:

        print(
            "Numeric conversion issues: None"
        )

    print(
        f"Saved to                : "
        f"{output_file}"
    )

    return {
        "dataset": symbol,
        "type": "stock",
        "rows": len(df),
        "start_date": df["trade_date"].min(),
        "end_date": df["trade_date"].max(),
        "invalid_dates": invalid_dates,
        "duplicate_rows": duplicate_rows,
        "duplicate_symbol_dates":
            duplicate_symbol_dates,
        "missing_cells": missing_cells,
        "bad_ohlc_rows":
            ohlc_results["bad_ohlc_rows"],
        "non_positive_price_rows":
            ohlc_results[
                "non_positive_price_rows"
            ],
        "non_positive_volume":
            non_positive_volume,
        "extreme_returns_over_20pct":
            extreme_return_count,
        "output_file": str(output_file),
    }


# ============================================================
# CLEAN NIFTY 50
# ============================================================

def clean_nifty_file(file_path):

    print("\n" + "=" * 90)
    print(
        f"CLEANING NIFTY 50: "
        f"{file_path.name}"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    df = pd.read_csv(file_path)

    original_rows = len(df)

    # Remove whitespace from headers
    df.columns = df.columns.str.strip()

    # --------------------------------------------------------
    # Rename
    # --------------------------------------------------------

    df = df.rename(
        columns={
            "Index Name": "index_name",
            "Date": "trade_date",
            "Open": "open_price",
            "High": "high_price",
            "Low": "low_price",
            "Close": "close_price",
        }
    )

    # --------------------------------------------------------
    # Parse date
    #
    # Example:
    # 11 Sep 2026
    # --------------------------------------------------------

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        format="%d %b %Y",
        errors="coerce"
    )

    invalid_dates = int(
        df["trade_date"].isna().sum()
    )

    # --------------------------------------------------------
    # Numeric columns
    # --------------------------------------------------------

    numeric_columns = [
        "open_price",
        "high_price",
        "low_price",
        "close_price",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = df.sort_values(
        "trade_date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    duplicate_rows = int(
        df.duplicated().sum()
    )

    duplicate_dates = int(
        df.duplicated(
            subset=["trade_date"]
        ).sum()
    )

    # --------------------------------------------------------
    # Daily return
    # --------------------------------------------------------

    df["daily_return"] = (
        df["close_price"].pct_change()
    )

    # --------------------------------------------------------
    # OHLC validation
    # --------------------------------------------------------

    ohlc_results = validate_ohlc(
        df,
        "open_price",
        "high_price",
        "low_price",
        "close_price"
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    missing_cells = int(
        df.isna().sum().sum()
    )

    # --------------------------------------------------------
    # Extreme returns
    # --------------------------------------------------------

    extreme_return_count = int(
        df["daily_return"]
        .abs()
        .gt(0.20)
        .sum()
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output_file = (
        PROCESSED_NIFTY_DIR
        / "nifty50_clean.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print(
        f"Original rows        : "
        f"{original_rows:,}"
    )

    print(
        f"Final rows           : "
        f"{len(df):,}"
    )

    print(
        f"Date range           : "
        f"{df['trade_date'].min().date()} "
        f"→ "
        f"{df['trade_date'].max().date()}"
    )

    print(
        f"Invalid dates        : "
        f"{invalid_dates:,}"
    )

    print(
        f"Duplicate rows       : "
        f"{duplicate_rows:,}"
    )

    print(
        f"Duplicate dates      : "
        f"{duplicate_dates:,}"
    )

    print(
        f"Missing cells        : "
        f"{missing_cells:,}"
    )

    print(
        f"Bad OHLC rows        : "
        f"{ohlc_results['bad_ohlc_rows']}"
    )

    print(
        f"Non-positive prices  : "
        f"{ohlc_results['non_positive_price_rows']}"
    )

    print(
        f"Extreme returns >20% : "
        f"{extreme_return_count:,}"
    )

    print(
        f"Saved to             : "
        f"{output_file}"
    )

    return {
        "dataset": "NIFTY 50",
        "type": "benchmark",
        "rows": len(df),
        "start_date": df["trade_date"].min(),
        "end_date": df["trade_date"].max(),
        "invalid_dates": invalid_dates,
        "duplicate_rows": duplicate_rows,
        "duplicate_symbol_dates":
            duplicate_dates,
        "missing_cells": missing_cells,
        "bad_ohlc_rows":
            ohlc_results["bad_ohlc_rows"],
        "non_positive_price_rows":
            ohlc_results[
                "non_positive_price_rows"
            ],
        "extreme_returns_over_20pct":
            extreme_return_count,
        "output_file": str(output_file),
    }


# ============================================================
# CLEAN INDIA VIX
# ============================================================

def clean_vix_file(file_path):

    print("\n" + "=" * 90)
    print(
        f"CLEANING INDIA VIX: "
        f"{file_path.name}"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    df = pd.read_csv(file_path)

    original_rows = len(df)

    # Remove trailing/leading spaces
    # from headers

    df.columns = df.columns.str.strip()

    # --------------------------------------------------------
    # Rename columns
    # --------------------------------------------------------

    df = df.rename(
        columns={
            "Date": "trade_date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Prev. Close": "prev_close",
            "Change": "change",
            "% Change": "pct_change",
        }
    )

    # --------------------------------------------------------
    # Check expected columns
    # --------------------------------------------------------

    expected_vix_columns = [
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "prev_close",
        "change",
        "pct_change",
    ]

    missing_columns = [
        column
        for column in expected_vix_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Missing expected VIX columns: "
            f"{missing_columns}"
        )

    # --------------------------------------------------------
    # Parse date
    #
    # Example:
    # 12-SEP-2025
    # --------------------------------------------------------

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        format="%d-%b-%Y",
        errors="coerce"
    )

    invalid_dates = int(
        df["trade_date"].isna().sum()
    )

    # --------------------------------------------------------
    # Numeric columns
    # --------------------------------------------------------

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "prev_close",
        "change",
        "pct_change",
    ]

    conversion_failures = {}

    for column in numeric_columns:

        before = df[column].notna().sum()

        df[column] = clean_numeric(
            df[column]
        )

        after = df[column].notna().sum()

        conversion_failures[column] = int(
            before - after
        )

    # --------------------------------------------------------
    # Sort by date
    # --------------------------------------------------------

    df = df.sort_values(
        "trade_date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Duplicate checks
    # --------------------------------------------------------

    duplicate_rows = int(
        df.duplicated().sum()
    )

    duplicate_dates = int(
        df.duplicated(
            subset=["trade_date"]
        ).sum()
    )

    # --------------------------------------------------------
    # Remove duplicate dates if any
    # --------------------------------------------------------

    if duplicate_dates > 0:

        df = df.drop_duplicates(
            subset=["trade_date"],
            keep="last"
        ).reset_index(
            drop=True
        )

    # --------------------------------------------------------
    # Daily VIX return
    # --------------------------------------------------------

    df["daily_return"] = (
        df["close"].pct_change()
    )

    # --------------------------------------------------------
    # OHLC validation
    # --------------------------------------------------------

    ohlc_results = validate_ohlc(
        df,
        "open",
        "high",
        "low",
        "close"
    )

    # --------------------------------------------------------
    # Missing
    # --------------------------------------------------------

    missing_cells = int(
        df.isna().sum().sum()
    )

    # --------------------------------------------------------
    # Extreme VIX returns
    #
    # VIX can move significantly during volatile
    # market periods, so this is only informational.
    # --------------------------------------------------------

    extreme_return_count = int(
        df["daily_return"]
        .abs()
        .gt(0.20)
        .sum()
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output_file = (
        PROCESSED_VIX_DIR
        / "india_vix_clean.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print(
        f"Original rows          : "
        f"{original_rows:,}"
    )

    print(
        f"Final rows             : "
        f"{len(df):,}"
    )

    print(
        f"Date range             : "
        f"{df['trade_date'].min().date()} "
        f"→ "
        f"{df['trade_date'].max().date()}"
    )

    print(
        f"Invalid dates          : "
        f"{invalid_dates:,}"
    )

    print(
        f"Duplicate rows         : "
        f"{duplicate_rows:,}"
    )

    print(
        f"Duplicate dates        : "
        f"{duplicate_dates:,}"
    )

    print(
        f"Missing cells          : "
        f"{missing_cells:,}"
    )

    print(
        f"Bad OHLC rows          : "
        f"{ohlc_results['bad_ohlc_rows']:,}"
    )

    print(
        f"Non-positive prices    : "
        f"{ohlc_results['non_positive_price_rows']:,}"
    )

    print(
        f"Extreme returns >20%   : "
        f"{extreme_return_count:,}"
    )

    # --------------------------------------------------------
    # Conversion warnings
    # --------------------------------------------------------

    failed_conversions = {
        column: count
        for column, count
        in conversion_failures.items()
        if count > 0
    }

    if failed_conversions:

        print("\nNumeric conversion issues:")

        for column, count in failed_conversions.items():

            print(
                f"  {column}: "
                f"{count:,}"
            )

    else:

        print(
            "Numeric conversion issues: None"
        )

    print(
        f"Saved to               : "
        f"{output_file}"
    )

    return {
        "dataset": "India VIX",
        "type": "risk_indicator",
        "rows": len(df),
        "start_date": df["trade_date"].min(),
        "end_date": df["trade_date"].max(),
        "invalid_dates": invalid_dates,
        "duplicate_rows": duplicate_rows,
        "duplicate_symbol_dates":
            duplicate_dates,
        "missing_cells": missing_cells,
        "bad_ohlc_rows":
            ohlc_results["bad_ohlc_rows"],
        "non_positive_price_rows":
            ohlc_results[
                "non_positive_price_rows"
            ],
        "extreme_returns_over_20pct":
            extreme_return_count,
        "output_file": str(output_file),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 90)
    print(
        "FINANCIAL PORTFOLIO ANALYTICS"
    )
    print(
        "RAW DATA CLEANING PIPELINE"
    )
    print("#" * 90)

    # --------------------------------------------------------
    # Create directories
    # --------------------------------------------------------

    PROCESSED_STOCKS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED_NIFTY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED_VIX_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find stock CSVs
    # --------------------------------------------------------

    stock_files = sorted(
        STOCKS_DIR.glob("*.csv")
    )

    print(
        f"\nStock files found: "
        f"{len(stock_files)}"
    )

    if len(stock_files) != 10:

        print(
            f"WARNING: Expected 10 stock "
            f"files, found "
            f"{len(stock_files)}."
        )

    results = []

    # --------------------------------------------------------
    # Clean stocks
    # --------------------------------------------------------

    for file_path in stock_files:

        try:

            result = clean_stock_file(
                file_path
            )

            results.append(result)

        except Exception as e:

            print(
                f"\nERROR cleaning "
                f"{file_path.name}:"
            )

            print(e)

    # --------------------------------------------------------
    # Find NIFTY
    # --------------------------------------------------------

    nifty_files = list(
        RAW_DIR.glob(
            "*NIFTY*50*.csv"
        )
    )

    if not nifty_files:

        print(
            "\nWARNING: NIFTY 50 CSV "
            "not found."
        )

    else:

        try:

            result = clean_nifty_file(
                nifty_files[0]
            )

            results.append(result)

        except Exception as e:

            print(
                "\nERROR cleaning "
                "NIFTY 50:"
            )

            print(e)

    # --------------------------------------------------------
    # Find India VIX
    # --------------------------------------------------------

    vix_files = list(
        RAW_DIR.glob(
            "*vix*.csv"
        )
    )

    if not vix_files:

        print(
            "\nWARNING: India VIX CSV "
            "not found."
        )

    else:

        try:

            result = clean_vix_file(
                vix_files[0]
            )

            results.append(result)

        except Exception as e:

            print(
                "\nERROR cleaning "
                "India VIX:"
            )

            print(e)

    # --------------------------------------------------------
    # Quality report
    # --------------------------------------------------------

    if results:

        report_df = pd.DataFrame(
            results
        )

        report_file = (
            REPORTS_DIR
            / "data_cleaning_quality_report.csv"
        )

        report_df.to_csv(
            report_file,
            index=False
        )

        print("\n\n" + "#" * 90)
        print(
            "CLEANING QUALITY REPORT"
        )
        print("#" * 90)

        print(
            report_df.to_string(
                index=False
            )
        )

        print(
            f"\nQuality report saved to:"
        )

        print(report_file)

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "#" * 90)
    print(
        "DATA CLEANING COMPLETE"
    )
    print("#" * 90)

    print(
        f"\nProcessed data location:"
    )

    print(PROCESSED_DIR)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()