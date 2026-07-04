import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
CUSTOM_DIR = ROOT / "custom"
CPI_PATHS = [ROOT / "US_CPI.csv", ROOT / "macro" / "US_CPI.csv"]
RISK_FREE_PATH = ROOT / "bonds" / "yields3M.csv"

EXCLUDE_DIRS = {"custom", ".git", ".agents", ".codex", "__pycache__"}
NON_RETURN_COLUMNS = {
    "date",
    "year",
    "country",
    "currency",
    "usdperforeign",
    "cpi",
    "yield3m",
    "yield10y",
}


@dataclass(frozen=True)
class ReturnCandidate:
    path: Path
    column: str
    frequency: str


def is_return_column(column: str) -> bool:
    name = column.lower()
    if name in NON_RETURN_COLUMNS:
        return False
    return "return" in name or name.startswith("er") or name.endswith("_er")


def is_excess_column(column: str) -> bool:
    name = column.lower()
    return "excess" in name or name.startswith("er") or name.endswith("_er")


def infer_frequency(df: pd.DataFrame) -> str:
    if "year" in df.columns and "date" not in df.columns:
        return "annual"
    if "date" not in df.columns:
        return "unknown"

    dates = pd.to_datetime(df["date"], errors="coerce").dropna().drop_duplicates().sort_values()
    if len(dates) < 2:
        return "unknown"

    median_days = dates.diff().dt.days.dropna().median()
    if median_days <= 10:
        return "daily"
    if median_days <= 45:
        return "monthly"
    return "annual"


def discover_return_series() -> list[ReturnCandidate]:
    candidates = []
    for path in sorted(ROOT.rglob("*.csv")):
        relative_parts = set(path.relative_to(ROOT).parts)
        if relative_parts & EXCLUDE_DIRS:
            continue
        try:
            sample = pd.read_csv(path, nrows=50)
        except Exception:
            continue
        for column in sample.columns:
            if is_return_column(column):
                candidates.append(ReturnCandidate(path, column, infer_frequency(sample)))
    return candidates


def prompt_choice(prompt: str, options: list[str]) -> int:
    print(prompt)
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")

    while True:
        choice = input("Select number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print(f"Enter a number from 1 to {len(options)}.")


def resolve_cpi_path() -> Path:
    for path in CPI_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find US_CPI.csv at repo root or macro/US_CPI.csv")


def time_column(df: pd.DataFrame) -> str:
    if "date" in df.columns:
        return "date"
    if "year" in df.columns:
        return "year"
    raise ValueError("Input file must contain either a date or year column")


def working_dates(df: pd.DataFrame) -> pd.Series:
    if "date" in df.columns:
        return pd.to_datetime(df["date"])
    return pd.to_datetime(df["year"].astype(str) + "-12-31")


def panel_keys(df: pd.DataFrame, return_column: str) -> list[str]:
    ignored = {return_column, "date", "year"}
    ignored.update(column for column in df.columns if is_return_column(column))
    return [
        column
        for column in df.columns
        if column not in ignored and not pd.api.types.is_numeric_dtype(df[column])
    ]


def period_days(df: pd.DataFrame, dates: pd.Series, frequency: str, return_column: str) -> pd.Series:
    if frequency == "monthly":
        return dates.dt.days_in_month.astype(float)
    if frequency == "annual":
        return np.where(dates.dt.is_leap_year, 366.0, 365.0)

    ordered = df.assign(_date=dates).sort_values(panel_keys(df, return_column) + ["_date"])
    keys = panel_keys(ordered, return_column)
    if keys:
        days = ordered.groupby(keys)["_date"].diff().dt.days
    else:
        days = ordered["_date"].diff().dt.days
    days = days.fillna(1).clip(lower=1)
    return days.reindex(df.index).astype(float)


def load_cpi() -> pd.DataFrame:
    cpi = pd.read_csv(resolve_cpi_path(), parse_dates=["date"])
    cpi = cpi.sort_values("date")
    cpi["month"] = cpi["date"].dt.to_period("M").dt.to_timestamp()
    cpi["year"] = cpi["date"].dt.year
    return cpi


def inflation_returns(df: pd.DataFrame, return_column: str, frequency: str) -> pd.Series:
    cpi = load_cpi()
    dates = working_dates(df)

    if frequency == "annual":
        annual_cpi = cpi.groupby("year")["CPI"].last()
        inflation = annual_cpi / annual_cpi.shift(1) - 1
        return dates.dt.year.map(inflation)

    cpi = cpi.assign(inflation=cpi["CPI"] / cpi["CPI"].shift(1) - 1)
    month_inflation = cpi.set_index("month")["inflation"]
    row_months = dates.dt.to_period("M").dt.to_timestamp()
    inflation = row_months.map(month_inflation)

    if frequency == "daily":
        days = period_days(df, dates, frequency, return_column)
        return (1 + inflation) ** (days / dates.dt.days_in_month) - 1
    return inflation


def risk_free_returns(df: pd.DataFrame, return_column: str, frequency: str) -> pd.Series:
    risk_free = pd.read_csv(RISK_FREE_PATH, parse_dates=["date"])
    risk_free = risk_free[risk_free["country"].eq("US")].sort_values("date").copy()
    risk_free["month"] = risk_free["date"].dt.to_period("M").dt.to_timestamp()
    risk_free["year"] = risk_free["date"].dt.year
    risk_free["monthReturn"] = (1 + risk_free["yield3M"]) ** (
        risk_free["date"].dt.days_in_month / 365
    ) - 1

    dates = working_dates(df)
    if frequency == "annual":
        annual_return = risk_free.groupby("year")["monthReturn"].apply(lambda x: (1 + x).prod() - 1)
        return dates.dt.year.map(annual_return)

    monthly_yield = risk_free.set_index("month")["yield3M"]
    row_months = dates.dt.to_period("M").dt.to_timestamp()
    yields = row_months.map(monthly_yield)
    days = period_days(df, dates, frequency, return_column)
    return (1 + yields) ** (days / 365) - 1


def total_return_column_name(column: str) -> str:
    if "ExcessReturn" in column:
        return column.replace("ExcessReturn", "TotalReturn")
    if "excessReturn" in column:
        return column.replace("excessReturn", "totalReturn")
    if column.startswith("er") and len(column) > 2 and column[2].isupper():
        return f"tr{column[2:]}"
    if column.endswith("_er"):
        return f"{column[:-3]}_tr"
    return f"{column}_total"


def transformed_column_name(column: str, transformation: str) -> str:
    total_column = total_return_column_name(column)
    if transformation == "real_total":
        return f"{total_column}_real"
    if transformation == "nominal_total":
        return total_column
    raise ValueError(f"Unknown transformation: {transformation}")


def output_path(input_path: Path, column: str, transformation: str) -> Path:
    safe_column = re.sub(r"[^A-Za-z0-9_]+", "_", column).strip("_")
    return CUSTOM_DIR / f"{input_path.stem}_{safe_column}_{transformation}.csv"


def nominal_total_returns(df: pd.DataFrame, return_column: str, frequency: str) -> pd.Series:
    if not is_excess_column(return_column):
        print(f"Warning: {return_column} does not look like an excess-return column.")
        return df[return_column]
    return df[return_column] + risk_free_returns(df, return_column, frequency)


def transform_series(candidate: ReturnCandidate, transformation: str) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(candidate.path)
    if candidate.column not in df.columns:
        raise ValueError(f"{candidate.column} is not a column in {candidate.path}")

    frequency = infer_frequency(df)
    new_column = transformed_column_name(candidate.column, transformation)
    nominal_total = nominal_total_returns(df, candidate.column, frequency)

    if transformation == "nominal_total":
        df[new_column] = nominal_total
    elif transformation == "real_total":
        inflation = inflation_returns(df, candidate.column, frequency)
        df[new_column] = (1 + nominal_total) / (1 + inflation) - 1
    else:
        raise ValueError(f"Unknown transformation: {transformation}")

    context_columns = [
        column
        for column in df.columns
        if column == new_column or not is_return_column(column)
    ]
    return df[context_columns], new_column


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform return series and write them to custom/.")
    parser.add_argument("--list", action="store_true", help="List available return series and exit.")
    parser.add_argument("--input", help="CSV path containing the return series.")
    parser.add_argument("--column", help="Return column to transform.")
    parser.add_argument(
        "--transform",
        choices=["real_total", "nominal_total"],
        help="Choose real_total or nominal_total.",
    )
    return parser.parse_args()


def select_candidate(candidates: list[ReturnCandidate], args: argparse.Namespace) -> ReturnCandidate:
    if args.input and args.column:
        input_path = (ROOT / args.input).resolve()
        for candidate in candidates:
            if candidate.path.resolve() == input_path and candidate.column == args.column:
                return candidate
        raise ValueError(f"No return series found for {args.input}::{args.column}")

    options = [
        f"{candidate.path.relative_to(ROOT)} :: {candidate.column} ({candidate.frequency})"
        for candidate in candidates
    ]
    return candidates[prompt_choice("Select return series to transform:", options)]


def main() -> None:
    args = parse_args()
    candidates = discover_return_series()
    if not candidates:
        raise ValueError("No return series found.")

    if args.list:
        for idx, candidate in enumerate(candidates, start=1):
            print(f"{idx}. {candidate.path.relative_to(ROOT)} :: {candidate.column} ({candidate.frequency})")
        return

    candidate = select_candidate(candidates, args)
    transformation = args.transform
    if transformation is None:
        choices = [
            "Real total return",
            "Nominal total return",
        ]
        transformation = ["real_total", "nominal_total"][prompt_choice("Select transformation:", choices)]

    out, new_column = transform_series(candidate, transformation)
    CUSTOM_DIR.mkdir(exist_ok=True)
    destination = output_path(candidate.path, candidate.column, transformation)
    out.to_csv(destination, index=False)
    print(f"Wrote {destination.relative_to(ROOT)} with transformed column {new_column}")


if __name__ == "__main__":
    main()
