from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
YIELDS = ROOT / "bonds" / "yields3M.csv"
FX_DAILY = ROOT / "currencies" / "fx_daily.csv"
OUTPUT = ROOT / "currencies" / "fx_excess_daily.csv"

RATE_COUNTRY = {
    "EUR": "Germany",
}


def plot_log_cumulative_returns(out: pd.DataFrame) -> None:
    plot_data = out.sort_values(["currency", "date"]).copy()
    plot_data["logExcessReturn"] = plot_data.groupby("currency")["fxExcessReturn"].transform(
        lambda x: np.log1p(x).cumsum()
    )
    plot_data["logPriceReturn"] = plot_data.groupby("currency")["priceReturn"].transform(
        lambda x: np.log1p(x).cumsum()
    )

    for column, title, ylabel in [
        ("logExcessReturn", "Log Cumulative FX Excess Return", "Log cumulative excess return"),
        ("logPriceReturn", "Log Cumulative FX Price Return", "Log cumulative price return"),
    ]:
        fig, ax = plt.subplots(figsize=(11, 6))
        for currency, currency_data in plot_data.groupby("currency"):
            ax.plot(currency_data["date"], currency_data[column], label=currency)
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.legend(title="Currency")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

    plt.show()


def main() -> None:
    yields = pd.read_csv(YIELDS, parse_dates=["date"])
    fx = pd.read_csv(FX_DAILY, parse_dates=["date"])

    yields["month"] = yields["date"].dt.to_period("M").dt.to_timestamp()
    fx["month"] = fx["date"].dt.to_period("M").dt.to_timestamp()
    fx["rateCountry"] = fx["currency"].map(RATE_COUNTRY).fillna(fx["country"])
    fx["accrualDays"] = fx.groupby("currency")["date"].diff().dt.days.fillna(1)

    short_rates = yields[["month", "country", "yield3M"]]
    usd_rates = short_rates[short_rates["country"].eq("US")][["month", "yield3M"]]

    out = fx.merge(
        short_rates.rename(columns={"country": "rateCountry", "yield3M": "foreignYield3M"}),
        on=["month", "rateCountry"],
        how="left",
    ).merge(
        usd_rates.rename(columns={"yield3M": "usdYield3M"}),
        on="month",
        how="left",
    )

    has_rates = out["foreignYield3M"].notna() & out["usdYield3M"].notna()
    unsupported = sorted(set(fx["currency"]) - set(out.loc[has_rates, "currency"]))
    if unsupported:
        print(f"No excess returns for currencies with no short-rate coverage: {', '.join(unsupported)}")
    if len(out) > has_rates.sum():
        print(f"Left excess returns blank for {len(out) - has_rates.sum():,} rows without matching foreign or USD rates")

    out["foreignRateReturn"] = (1 + out["foreignYield3M"]) ** (out["accrualDays"] / 365) - 1
    out["usdFundingReturn"] = (1 + out["usdYield3M"]) ** (out["accrualDays"] / 365) - 1
    out["fxExcessReturn"] = (
        (1 + out["priceReturn"]) * (1 + out["foreignRateReturn"])
        - (1 + out["usdFundingReturn"])
    )

    out = out[
        [
            "date",
            "currency",
            "country",
            "USDPerForeign",
            "priceReturn",
            "fxExcessReturn",
        ]
    ]
    out.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(out):,} rows to {OUTPUT.relative_to(ROOT)}")
    plot_log_cumulative_returns(out)


if __name__ == "__main__":
    main()
