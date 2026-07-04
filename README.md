# Return Data Files

### Birju Patel

This project consolidates useful stock, bond, and currency return data.

Some returns are reported in excess of the risk-free rate.
An excess return represents the returns to a zero-cost strategy that borrows at a short-term interest rate to buy the target asset.

For an unhedged series, the strategy borrows in U.S. dollars and converts to foreign currency.
For a hedged series, the strategy borrows in the foreign currency.
All returns are measured in U.S. dollars.

## Equities

- ### `developed_ex_us.csv`
	- **Frequency:** Annual
    - **`ex_us_hedged_er`:** Currency hedged USD index excess return
    - **`ex_us_unhedged_er`:** Unhedged USD index excess return

Annual foreign equity index returns intended to approximate the MSCI EAFE Index.

##### Methodology

- **2015 to Present**
	- Uses returns from publicly traded index ETFs tracking the MSCI EAFE Index.
- **1975 to 2014**
	- Uses a weighted sum of currency-adjusted excess returns for developed-country
	equity markets excluding the United States and Canada.
	- Country weights are based on each country’s share of total equity market capitalization within the investable universe.
- **1950 to 1974**
	- Uses the average country weights from the 1975 to 2014 period.

## Bonds

- ### `sov_bonds.csv`
	- **Frequency:** Monthly
	- **`erHedgedUSD`:** Currency hedged long-term bond excess return
	- **`erHedgedUSD`:** Unhedged long-term bond excess return
	
Returns on 10-year developed-country sovereign bonds.

##### Methodology
The series approximates monthly returns by using changes in bond yields.

Yields are assumed to be par yields.
Return estimates are calculated using the method outlined in Swinkels (2019).
Additional implementation details are available on the [Portfolio Optimizer blog](https://portfoliooptimizer.io/blog/the-mathematics-of-bonds-simulating-the-returns-of-constant-maturity-government-bond-etfs).

Computed returns are not suitable for testing momentum-based strategies.
Monthly yields are measured as within-month averages, which mechanically smooths sharp yield changes across adjacent months.
This creates spurious autocorrelation in monthly returns and materially overstates the returns to momentum-based trading strategies.

- ### `yields3M.csv`
	- **Frequency:** Monthly
	- **`yield3M`:** Short-term interest rate
	
##### Methodology
The short-term interest rate is either the central bank policy rate or 3 month government bill yield, whichever has the most available data.

- ### `yields10Y.csv`
	- **Frequency:** Monthly
	- **`yield10Y`:** Long-term interest rate

##### Methodology
Long-term yields are 10-year sovereign bond par yields.
Monthly yields are reported as the average daily yield over that month.

## Currencies

- ### `fx_daily.csv`
	- **Frequency:** Daily
	- **`USDPerForeign`:** Value in USD of single unit of foreign currency
	- **`priceReturn`:** USD price return of foreign currency
	- **`fxExcessReturn`:** Excess return to borrowing in USD and lending in foreign currency.

Daily currency exchange rates, price fluctuations, and excess returns.

##### Methodology

Measurements are point-in-time estimates, recording market prices observed in the NYC FX market at 12:00 PM EST.
This series is suitable for testing momentum strategies.

## Macro

- ### `US_CPI.csv`
	- **Frequency:** Monthly
	- **`CPI`:** Unadjusted Consumer Price Index for All Urban Consumers

## Sources

- [**World Bank Group**](https://data.worldbank.org/)
  - Market capitalization of listed domestic companies, current US dollars: `CM.MKT.LCAP.CD`
- [**Organisation for Economic Co-operation and Development (OECD)**](https://www.oecd.org/en/data.html)
  - Long-term interest rates: `IRLT`
  - Short-term interest rates: `IR3TIB`, `IRSTCI`
- [**Federal Reserve**](https://fred.stlouisfed.org/)
  - Spot exchange rates (monthly): `EXUSEU`, `EXUSUK`, `EXUSAL`, `EXCAUS`, `EXJPUS`, `EXSZUS`, `EXFRUS`, `EXGEUS`
  - Spot exchange rates (daily): `DEXUSEU`, `DEXJPUS`, `DEXUSUK`, `DEXCAUS`, `DEXUSAL`, `DEXSZUS`, `DEXNOUS`, `DEXSDUS`, `DEXUSNZ`
- [**JST Macrohistory Database**](https://www.macrohistory.net/database/)
	- Equity total return: `eq_tr`
	- USD exchange rate: `xrusd`
	- Short term interest rate: `bill_rate`
- [**Bureau of Labor Statistics**](https://www.bls.gov/)
	- Unadjusted Consumer Price Index for All Urban Consumers: `CPIAUCNS`

## Licensing
This dataset is made available under the Creative Commons Zero v1.0 Universal Public Domain Dedication (CC0-1.0).

The datasets are approximations of the returns of target assets.
The data is provided as-is, with no guarantee of accuracy or completeness.

This dataset is provided for research and educational purposes only. It is not investment advice.