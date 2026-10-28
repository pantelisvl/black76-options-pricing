# Black–76 Options on Futures Calculator

A Python command-line calculator for European calls and puts on futures. It
calculates theoretical premiums, finite-difference Greeks, expiry P&L, portfolio
totals, optional scenarios and a portfolio P&L chart.

## Project files

Keep these five Python files in the same folder:

| File | Responsibility |
| --- | --- |
| `main.py` | Input helpers, position entry, printed results and optional scenario/chart prompts. Run this file to use the calculator. |
| `pricing.py` | Black–76 prices and the five Greeks for one option. |
| `portfolio.py` | Signed cash totals and shared scenarios across saved positions. |
| `plots.py` | The portfolio P&L chart, using the portfolio calculation functions. |
| `test_options.py` | Automated checks that run separately from the interactive calculator. |

`main.py` keeps the interactive application together. It uses a `main()` function
and an entry-point guard, so importing the module does not start input prompts.
The eight original pricing checks have moved into the test file, alongside
checks for Greeks, portfolio calculations and scenarios.

The supporting files are `requirements.txt`, this README and `.gitignore`.

## Setup and use

Open the project folder in VS Code and use the same Python interpreter that you
use to run the calculator. In a terminal opened in that folder, install the chart
dependencies if needed:

```powershell
python -m pip install -r requirements.txt
```

Run the automated tests:

```powershell
python test_options.py
```

Then start the calculator:

```powershell
python main.py
```

You can also open either file in VS Code and use **Run Python File in Terminal**.
Running `test_options.py` checks the calculations and exits. Running `main.py`
starts with position entry; it no longer prints the test results first.

NumPy and Matplotlib are used for the chart. The pricing and portfolio
calculations use Python's standard library. Plotting dependencies are loaded
when a chart is requested.

Finish the existing run, or close its chart window, before starting another run.
In PowerShell, a `PS ...>` prompt indicates that the terminal is ready for a
command. A prompt such as `Enter futures contract price:` is waiting for a number.

## Input units

| Input | Meaning |
| --- | --- |
| Futures price and strike | Prices in the underlying futures contract's quoted points. Both must be greater than zero for this model. |
| Call or put | The option type. |
| Long or short | The position direction. |
| Trade premium | Entry premium in **option premium points per contract**; nonnegative. |
| Days to expiry | Calendar-day input converted to model years as `days / 365.0`; nonnegative. |
| Volatility | Annual volatility as a decimal: `0.20` means 20%. |
| Annual interest rate | Annual continuously compounded rate as a decimal: `0.05` means 5%. Negative rates are permitted. |
| Settlement price | A hypothetical expiry settlement price, used for the expiry payoff and expiry P&L. |
| Number of contracts | A positive whole number. |
| Cash value per option point per contract | The contract's premium multiplier. |

An IV change of `0.01` means **one percentage point**, for example from 20% to
21%. A futures change of `100` means 100 futures price points.

The cash currency comes from the multiplier you enter. A multiplier measured in
dollars produces dollar results; a multiplier measured in euros produces euro
results. The application stores no currency field and performs no FX conversion.
Aggregate positions only within the same underlying and cash currency.

## What the monetary results mean

Each position has the signed cash scale:

```text
scale = position sign × contracts × multiplier
position sign = +1 for long, −1 for short
```

The portfolio report calculates:

```text
Net entry premium = sum(entry premium × scale)
Net modeled option value = sum(theoretical premium × scale)
Modeled P&L from entry = net modeled option value − net entry premium
```

For the entry-premium report, premium paid for a long position is positive and
premium received for a short position is negative. This is the cost convention
used in the P&L calculation. Modeled option value is positive for a long asset
and negative for a short liability.

Modeled P&L can be positive or negative immediately because the entered trade
premium can differ from the model's premium. It is a theoretical valuation
difference, not realized profit, an executable market quote or a broker account
balance. These P&L calculations exclude fees, spreads and financing of the entry
premium.

Expiry payoff is `max(settlement − strike, 0)` for a call and
`max(strike − settlement, 0)` for a put. Expiry cash P&L is
`(payoff − entry premium) × scale`.

## Reproducible example

Enter one position with these values:

| Input | Value |
| --- | ---: |
| Futures price | 5000 |
| Option type | call |
| Position | long |
| Strike | 5000 |
| Trade premium | 100 |
| Days to expiry | 30 |
| Volatility | 0.20 |
| Annual interest rate | 0.05 |
| Settlement price | 5100 |
| Contracts | 2 |
| Multiplier | 5 |

The theoretical premium is approximately **113.8885332992 option points**.
The position scale is `2 × 5 = 10` cash units per option premium point.

| Result | Cash units |
| --- | ---: |
| Net entry premium | 1,000.00 |
| Net modeled option value | 1,138.89 |
| Baseline modeled P&L | +138.89 |
| Expiry P&L at settlement 5100 | 0.00 |

Choose `yes` for a whole-portfolio scenario and enter futures move `100`, IV
change `0.01` and days passed `1`. The scenario premium is approximately
175.148165745 option points. The resulting cash P&L from entry is **751.48**, and
the cash change from the original modeled baseline is **612.60**.

Calculations retain full precision until display. Adding independently rounded
display amounts can differ by a cent from rounding the full-precision total.

## Scenarios and the chart

Both individual-position scenarios and whole-portfolio scenarios are optional.
Enter `yes` to continue at these prompts; other answers skip or end them.

A shared portfolio scenario applies the same additive futures move, decimal IV
change and elapsed days to every saved position. Interest rates remain at their
entered values. Days passed must be between zero and the shortest original DTE,
including the exact earliest-expiry day. The calculator does not model how
expired positions settle while later-expiry positions continue.

Each scenario starts from the original saved inputs. Scenarios do not accumulate
and do not modify the saved position dictionaries. If any position cannot be
priced, the entire scenario result is unavailable.

The chart varies only the futures price over 101 points from 90% to 110% of the
original futures price. Entered IV, rate and DTE remain fixed. It plots modeled
P&L **from entry**, with a zero-P&L line and a marker for the original baseline.
Earlier scenarios do not change the chart. The chart requires the same original
futures price for every included position and is unavailable if any grid point
cannot be priced for the complete portfolio.

With the example above, the x-axis runs from 4500 to 5500 and the baseline marker
is at futures price 5000 with P&L approximately 138.89. This is a current-DTE
valuation curve, not an expiry payoff curve unless the entered DTE is zero.

## Pricing model and Greek conventions

`black76_price()` uses the European Black–76 formula with discount factor
`exp(-rate × years)`, positive futures price and strike, and a lognormal futures
model. At zero time or zero volatility, it uses discounted intrinsic value.
The put-call parity relationship used by the tests is:

```text
call price − put price = exp(-rate × years) × (futures price − strike)
```

The Greeks are finite-difference estimates. Let `V` denote option premium points
before position sizing. The displayed position and portfolio Greeks multiply
these estimates by the signed cash scale.

| Greek | Calculation convention | Displayed cash unit |
| --- | --- | --- |
| Delta | Central futures-price bump of ±1 point | Cash per futures point |
| Gamma | Second difference using the same ±1-point bump | Cash per futures point squared |
| Vega | Half the price difference between IV +0.01 and IV −0.01 | Cash per one percentage point of IV |
| Theta | Price with one fewer calendar day minus current price | Cash change over one day |
| Rho | Half the price difference between rate +0.01 and rate −0.01 | Cash per one percentage point of rate |

Theta is the modeled one-day repricing change; it is not an instantaneous time
derivative. Vega and rho are deliberately scaled per percentage point rather
than per 1.0 decimal change. For rho, the entered futures price is held fixed
while the discount rate changes.

Delta and gamma are unavailable when time or IV is zero, or when the futures
price is at most 1. Vega is unavailable below IV 0.01 because the symmetric bump
would use negative volatility. Theta is unavailable with less than one day to
expiry. These cases return `None` for the affected Greeks. If one position has
an unavailable Greek, that entire portfolio Greek total is reported unavailable;
the other available Greek totals can still be reported.

## Scope and validation

The calculator is scoped to European options on futures. It does not implement
early exercise, contract-specific settlement or margin rules, a volatility
surface, live market data, or persistent position storage. Positions are held in
memory for one run.

Interactive number entry rejects nonnumeric and nonfinite values. The pricing
function checks the option type, positive futures price/strike, and nonnegative
time/IV, printing a message and returning `None` for these validation failures.
The calculation functions expect position dictionaries that have passed the
application's validation. They do not provide comprehensive protection against
nonfinite values supplied directly by other code, extreme-value overflow or all
floating-point precision limits.

## Tests and references

The test file retains the original eight checks: two published price benchmarks,
four call/put expiry cases, zero volatility and put-call parity. Additional checks
cover the Greek conventions, signed portfolio calculations and scenario
behavior. Run them after changing calculation code.

- [vollib reference Black pricing examples](https://vollib.org/documentation/1.0.3/autoapi/py_vollib/ref_python/black/index.html) — source of the call and put benchmark examples.
- [Python unittest documentation](https://docs.python.org/3/library/unittest.html) — the standard-library test runner used by this project.

