from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
STOCKS_DIR = RAW_DIR / "Stocks"


# ============================================================
# HELPER FUNCTION
# ============================================================

def inspect_csv(file_path: Path):
    print("\n" + "=" * 90)
    print(f"FILE: {file_path.name}")
    print("=" * 90)

    try:
        df = pd.read_csv(file_path)

        print(f"Rows       : {len(df):,}")
        print(f"Columns    : {len(df.columns)}")

        print("\nColumns:")
        for column in df.columns:
            print(f"  - {column}")

        print("\nData Types:")
        print(df.dtypes.to_string())

        # ----------------------------------------------------
        # Try to identify date column
        # ----------------------------------------------------
        possible_date_columns = [
            col for col in df.columns
            if any(keyword in col.lower()
                   for keyword in ["date", "timestamp", "time"])
        ]

        if possible_date_columns:
            date_col = possible_date_columns[0]

            dates = pd.to_datetime(
                df[date_col],
                errors="coerce",
                dayfirst=True
            )

            valid_dates = dates.dropna()

            if len(valid_dates) > 0:
                print(f"\nDate Column : {date_col}")
                print(f"Start Date  : {valid_dates.min().date()}")
                print(f"End Date    : {valid_dates.max().date()}")
                print(f"Valid Dates : {len(valid_dates):,}")
                print(f"Invalid Dates: {dates.isna().sum():,}")

        # ----------------------------------------------------
        # Missing values
        # ----------------------------------------------------
        missing = df.isna().sum()
        missing = missing[missing > 0]

        print("\nMissing Values:")
        if len(missing) == 0:
            print("  None")
        else:
            print(missing.to_string())

        # ----------------------------------------------------
        # Duplicate rows
        # ----------------------------------------------------
        duplicates = df.duplicated().sum()

        print(f"\nDuplicate Rows: {duplicates:,}")

        # ----------------------------------------------------
        # First 3 rows
        # ----------------------------------------------------
        print("\nFirst 3 Rows:")
        print(df.head(3).to_string(index=False))

        # ----------------------------------------------------
        # Last 3 rows
        # ----------------------------------------------------
        print("\nLast 3 Rows:")
        print(df.tail(3).to_string(index=False))

        return df

    except Exception as e:
        print(f"\nERROR reading file:")
        print(e)
        return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 90)
    print("FINANCIAL PORTFOLIO ANALYTICS - RAW DATA VALIDATION")
    print("#" * 90)

    print(f"\nProject Root : {PROJECT_ROOT}")
    print(f"Raw Data     : {RAW_DIR}")
    print(f"Stocks       : {STOCKS_DIR}")

    # --------------------------------------------------------
    # Find all CSV files
    # --------------------------------------------------------

    stock_files = sorted(STOCKS_DIR.glob("*.csv"))

    other_files = [
        file
        for file in RAW_DIR.glob("*.csv")
    ]

    all_files = stock_files + sorted(other_files)

    print(f"\nStock CSVs found : {len(stock_files)}")
    print(f"Other CSVs found : {len(other_files)}")
    print(f"Total CSVs       : {len(all_files)}")

    if len(stock_files) != 10:
        print(
            f"\nWARNING: Expected 10 stock CSVs, "
            f"but found {len(stock_files)}."
        )

    if len(other_files) != 2:
        print(
            f"\nWARNING: Expected 2 benchmark/risk CSVs, "
            f"but found {len(other_files)}."
        )

    # --------------------------------------------------------
    # Inspect every file
    # --------------------------------------------------------

    results = []

    for file in all_files:

        df = inspect_csv(file)

        if df is not None:

            results.append({
                "file": file.name,
                "rows": len(df),
                "columns": len(df.columns),
                "duplicates": int(df.duplicated().sum()),
                "missing_cells": int(df.isna().sum().sum())
            })

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n\n" + "#" * 90)
    print("VALIDATION SUMMARY")
    print("#" * 90)

    if results:

        summary_df = pd.DataFrame(results)

        print(
            summary_df.to_string(index=False)
        )

        # Save summary
        output_file = PROJECT_ROOT / "reports" / "raw_data_validation.csv"

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        summary_df.to_csv(
            output_file,
            index=False
        )

        print(
            f"\nValidation summary saved to:\n"
            f"{output_file}"
        )

    print("\nValidation complete.")


if __name__ == "__main__":
    main()