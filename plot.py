from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
EQUITIES = ROOT / "equities" / "developed_ex_us.csv"
BONDS = ROOT / "bonds" / "sov_bonds.csv"
CURRENCIES = ROOT / "currencies" / "fx_daily.csv"


@dataclass(frozen=True)
class Asset:
    path: Path
    column: str
    label: str
    filters: tuple[tuple[str, str], ...] = ()


def print_current_selection(selected: list[Asset]) -> None:
    print("\nCurrent selection:")
    if not selected:
        print("  None")
    else:
        for idx, asset in enumerate(selected, start=1):
            print(f"  {idx}. {asset.label}")
    print()


def prompt_choice(prompt: str, options: list[str], selected: list[Asset]) -> int:
    print_current_selection(selected)
    print(prompt)
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")

    while True:
        choice = input("Select number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print(f"Enter a number from 1 to {len(options)}.")


def plot_or_back_options(selected: list[Asset]) -> list[str]:
    options = []
    if selected:
        options.append("Plot")
    options.append("Back")
    return options


def maybe_finish(choice: str, selected: list[Asset]) -> bool:
    if choice == "Plot":
        plot_assets(selected)
        return True
    return False


def add_asset(selected: list[Asset], asset: Asset) -> None:
    if asset in selected:
        print(f"{asset.label} is already selected.")
        return
    selected.append(asset)
    print(f"Added: {asset.label}")


def choose_stock(selected: list[Asset]) -> bool:
    options = ["Foreign", "US"] + plot_or_back_options(selected)
    choice = options[prompt_choice("Select stock market:", options, selected)]
    if maybe_finish(choice, selected):
        return True
    if choice == "Back":
        return False
    if choice == "US":
        print("No U.S. stock return series is available in the current data files.")
        return False

    return choose_foreign_stock(selected)


def choose_foreign_stock(selected: list[Asset]) -> bool:
    if not EQUITIES.exists():
        print(f"Missing {EQUITIES.relative_to(ROOT)}")
        return False

    options = ["Hedged", "Unhedged"] + plot_or_back_options(selected)
    choice = options[prompt_choice("Select foreign stock return type:", options, selected)]
    if maybe_finish(choice, selected):
        return True
    if choice == "Back":
        return False

    column = {
        "Hedged": "ex_us_hedged_er",
        "Unhedged": "ex_us_unhedged_er",
    }[choice]
    add_asset(
        selected,
        Asset(
            path=EQUITIES,
            column=column,
            label=f"Foreign Stocks {choice}",
        ),
    )
    return False


def choose_bond(selected: list[Asset]) -> bool:
    if not BONDS.exists():
        print(f"Missing {BONDS.relative_to(ROOT)}")
        return False

    options = ["Hedged", "Unhedged"] + plot_or_back_options(selected)
    choice = options[prompt_choice("Select bond return type:", options, selected)]
    if maybe_finish(choice, selected):
        return True
    if choice == "Back":
        return False

    column = {
        "Hedged": "erHedgedUSD",
        "Unhedged": "erUnhedgedUSD",
    }[choice]
    return choose_country_asset(
        selected=selected,
        path=BONDS,
        column=column,
        label_prefix=f"{choice} Bonds",
        country_column="country",
    )


def choose_currency(selected: list[Asset]) -> bool:
    if not CURRENCIES.exists():
        print(f"Missing {CURRENCIES.relative_to(ROOT)}")
        return False

    options = ["Price Return", "Excess Return"] + plot_or_back_options(selected)
    choice = options[prompt_choice("Select currency return type:", options, selected)]
    if maybe_finish(choice, selected):
        return True
    if choice == "Back":
        return False

    column = {
        "Price Return": "priceReturn",
        "Excess Return": "fxExcessReturn",
    }[choice]
    return choose_country_asset(
        selected=selected,
        path=CURRENCIES,
        column=column,
        label_prefix=f"Currency {choice}",
        country_column="country",
        extra_label_column="currency",
    )


def choose_country_asset(
    selected: list[Asset],
    path: Path,
    column: str,
    label_prefix: str,
    country_column: str,
    extra_label_column: str | None = None,
) -> bool:
    df = pd.read_csv(path)
    if column not in df.columns:
        print(f"{column} is not available in {path.relative_to(ROOT)}")
        return False

    label_columns = [country_column]
    if extra_label_column and extra_label_column in df.columns:
        label_columns.insert(0, extra_label_column)

    groups = df[label_columns].drop_duplicates().sort_values(label_columns)
    country_options = [
        " ".join(str(row[column_name]) for column_name in label_columns)
        for _, row in groups.iterrows()
    ]
    options = country_options + plot_or_back_options(selected)
    choice = options[prompt_choice("Select country:", options, selected)]
    if maybe_finish(choice, selected):
        return True
    if choice == "Back":
        return False

    row = groups.iloc[country_options.index(choice)]
    filters = tuple((column_name, str(row[column_name])) for column_name in label_columns)
    add_asset(
        selected,
        Asset(
            path=path,
            column=column,
            label=f"{label_prefix} {choice}",
            filters=filters,
        ),
    )
    return False


def select_assets() -> list[Asset]:
    selected: list[Asset] = []

    while True:
        options = ["Stocks", "Bonds", "Currencies"]
        if selected:
            options.append("Plot")

        choice = options[prompt_choice("Select asset class:", options, selected)]
        if maybe_finish(choice, selected):
            return selected

        done = {
            "Stocks": choose_stock,
            "Bonds": choose_bond,
            "Currencies": choose_currency,
        }[choice](selected)
        if done:
            return selected


def asset_returns(asset: Asset) -> pd.DataFrame:
    df = pd.read_csv(asset.path)
    for column, value in asset.filters:
        df = df[df[column].astype(str).eq(value)]

    if "date" in df.columns:
        dates = pd.to_datetime(df["date"])
    else:
        dates = pd.to_datetime(df["year"].astype(str) + "-12-31")

    out = pd.DataFrame(
        {
            "date": dates,
            "return": pd.to_numeric(df[asset.column], errors="coerce"),
        }
    ).dropna()
    out = out.sort_values("date")
    out["cumulative"] = np.log1p(out["return"]).cumsum()
    return out


def plot_assets(assets: list[Asset]) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    plotted = False
    for asset in assets:
        returns = asset_returns(asset)
        if returns.empty:
            print(f"Skipping {asset.label}: no non-blank returns")
            continue
        plotted = True
        ax.plot(returns["date"], returns["cumulative"], label=asset.label)

    if not plotted:
        print("No selected assets had plottable returns.")
        return

    ax.set_title("Log Cumulative Nominal Returns")
    ax.set_xlabel("Date")
    ax.set_ylabel("Log cumulative return")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    plt.show()


def main() -> None:
    selected = select_assets()
    if selected:
        print_current_selection(selected)


if __name__ == "__main__":
    main()
