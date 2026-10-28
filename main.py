"""Interactive Black-76 calculator for individual options and portfolios.

Run this file to enter positions, review P&L and try optional scenarios/charts.
Run test_options.py separately to check pricing, Greeks and portfolio math.
"""

import math

from pricing import black76_price, black76_greeks
from portfolio import (
    calculate_portfolio_greeks,
    calculate_portfolio_summary,
    calculate_portfolio_scenario,
)
from plots import plot_portfolio_pnl


def read_number(prompt):
    while True:
        try:
            value = float(input(prompt))
        except ValueError:
            print("Enter a number")
            continue

        if not math.isfinite(value):
            print("Enter a finite number")
            continue

        return value


def read_selection(prompt):
    while True:
        selection = input(prompt).strip().lower()

        if selection == "call" or selection == "put":
            return selection

        print("Selection must be call or put.")


def expiry_payoff(selection, settlement, strike):
    if selection == "call":
        payoff = max(settlement - strike, 0.0)
    elif selection == "put":
        payoff = max(strike - settlement, 0.0)
    else:
        print("Invalid input")
        return None

    print("Expiry payoff (points): =", payoff)
    return payoff


def main():
    """Run one interactive portfolio session. Positions stay in memory."""
    portfolio = []

    while True:
        # Inputs
        futures_price = read_number("Enter futures contract price:")
        selection = read_selection("Call or Put:")

        position = input("Long or short:").strip().lower()
        while position != "long" and position != "short":
            print("Position must be long or short.")
            position = input("Long or short:").strip().lower()

        if position == "long":
            position_sign = 1
        else:
            position_sign = -1

        strike = read_number("Enter strike price:")

        premium = read_number("Enter trade premium price:")
        while premium < 0:
            print("Premium cannot be negative.")
            premium = read_number("Enter trade premium (points):")

        dte = read_number("Enter days to expiry:")
        iv = read_number("Enter volatility:")
        rate_annualized = read_number("Enter annual interest rate:")
        settlement = read_number("Enter settlement price:")
        years = dte / 365.0

        contracts = read_number("Enter number of contracts:")
        while contracts <= 0 or not contracts.is_integer():
            print("Enter a positive whole number of contracts.")
            contracts = read_number("Enter number of contracts:")
        contracts = int(contracts)

        multiplier = read_number("Enter cash value per option point per contract:")
        while multiplier <= 0:
            print("Multiplier must be greater than zero.")
            multiplier = read_number("Enter cash value per option point per contract:")

        position_scale = position_sign * contracts * multiplier

        option_price = black76_price(
            selection, futures_price, strike, years, iv, rate_annualized
        )

        if option_price is not None:
            print("Theoretical premium (points):", option_price)

            position_data = {
                "futures_price": futures_price,
                "selection": selection,
                "position": position,
                "strike": strike,
                "premium": premium,
                "dte": dte,
                "iv": iv,
                "rate_annualized": rate_annualized,
                "settlement": settlement,
                "contracts": contracts,
                "multiplier": multiplier,
            }
            portfolio.append(position_data)
            print("Positions stored:", len(portfolio))

            greeks = black76_greeks(
                selection, futures_price, strike, years, iv, rate_annualized
            )

            # Delta and gamma
            if (
                greeks is not None
                and greeks["delta"] is not None
                and greeks["gamma"] is not None
            ):
                position_delta = greeks["delta"] * position_scale
                position_gamma = greeks["gamma"] * position_scale
                print("Position delta (cash per futures point):", position_delta)
                print("Position gamma (cash per futures point squared):", position_gamma)
            else:
                print("Delta and gamma skipped for these inputs.")

            # Vega
            if greeks is not None and greeks["vega"] is not None:
                position_vega = greeks["vega"] * position_scale
                print("Position vega (cash per percentage point of IV):", position_vega)
            else:
                print("Vega skipped for these inputs.")

            # Theta
            if greeks is not None and greeks["theta"] is not None:
                position_theta = greeks["theta"] * position_scale
                print("Position theta (cash per day):", position_theta)
            else:
                print("Theta skipped for these inputs.")

            # Rho
            if greeks is not None and greeks["rho"] is not None:
                position_rho = greeks["rho"] * position_scale
                print(
                    "Position rho (cash per percentage point of interest rate):",
                    position_rho,
                )
            else:
                print("Rho skipped for these inputs.")

            # Expiry payoff and P&L
            payoff = expiry_payoff(selection, settlement, strike)

            if payoff is not None:
                pnl = position_sign * (payoff - premium)
                expiry_cash_pnl = pnl * contracts * multiplier
                print("Expiry P&L (points):", pnl)
                print("Expiry P&L (cash):", expiry_cash_pnl)

            # Optional scenarios for the current position
            while input("Run a scenario for this position? (yes/no):").strip().lower() == "yes":
                scenario_move = read_number("Enter futures price change in points:")
                iv_change = read_number("Enter IV change:")
                days_elapsed = read_number("Enter days passed:")

                while days_elapsed < 0 or days_elapsed > dte:
                    print("Days must be between zero and the original days to expiry")
                    days_elapsed = read_number("Enter days passed:")

                scenario_futures_price = futures_price + scenario_move
                scenario_iv = iv + iv_change
                scenario_years = (dte - days_elapsed) / 365.0

                scenario_price = black76_price(
                    selection,
                    scenario_futures_price,
                    strike,
                    scenario_years,
                    scenario_iv,
                    rate_annualized,
                )

                if scenario_price is not None:
                    scenario_value_change = scenario_price - option_price
                    scenario_pnl = position_sign * (scenario_price - premium)
                    scenario_cash_pnl = scenario_pnl * contracts * multiplier

                    print("Scenario futures price:", scenario_futures_price)
                    print("Scenario theoretical premium (points):", scenario_price)
                    print("Option premium change (points):", scenario_value_change)
                    print("Modeled scenario P&L (points):", scenario_pnl)
                    print("Modeled scenario P&L (cash):", scenario_cash_pnl)


        another_position = input("Add another position? (yes to continue):").strip().lower()
        if another_position != "yes":
            break

    print("Total positions stored:", len(portfolio))


    # Combined portfolio cash Greeks
    portfolio_greeks = calculate_portfolio_greeks(portfolio)

    print("\nPortfolio cash Greeks:")

    greek_labels = {
        "delta": "Delta (cash per futures point)",
        "gamma": "Gamma (cash per futures point squared)",
        "vega": "Vega (cash per percentage point of IV)",
        "theta": "Theta (cash per day)",
        "rho": "Rho (cash per percentage point of interest rate)",
    }

    for greek_name, total in portfolio_greeks.items():
        if total is None:
            print(greek_labels[greek_name] + ": unavailable for one or more positions")
        else:
            print(greek_labels[greek_name] + ":", round(total, 6))


    # Baseline portfolio summary
    portfolio_summary = calculate_portfolio_summary(portfolio)

    portfolio_entry_premium = None
    portfolio_model_value = None
    portfolio_baseline_pnl = None

    if not portfolio:
        print("\nNo positions stored.")
    elif portfolio_summary is None:
        print("\nPortfolio summary unavailable for one or more positions.")
    else:
        portfolio_entry_premium = portfolio_summary["entry_premium"]
        portfolio_model_value = portfolio_summary["model_value"]
        portfolio_baseline_pnl = portfolio_summary["pnl"]

        print("\nBaseline portfolio summary:")
        print(f"Net entry premium (cash): {portfolio_entry_premium:,.2f}")
        print(f"Net modeled option value (cash): {portfolio_model_value:,.2f}")
        print(f"Baseline modeled portfolio P&L (cash): {portfolio_baseline_pnl:+,.2f}")


    # Optional scenarios for the whole portfolio
    if portfolio:
        shortest_dte = min(
            saved_position["dte"] for saved_position in portfolio
        )

        while input("Run a scenario for the whole portfolio? (yes/no):").strip().lower() == "yes":
            portfolio_move = read_number("Portfolio futures price change in points:")
            portfolio_iv_change = read_number(
                "Portfolio IV change (0.01 = +1 percentage point):"
            )
            portfolio_days = read_number("Portfolio days passed:")

            while portfolio_days < 0 or portfolio_days > shortest_dte:
                print("Days must be between 0 and", shortest_dte)
                portfolio_days = read_number("Portfolio days passed:")

            scenario_result = calculate_portfolio_scenario(
                portfolio,
                portfolio_move,
                portfolio_iv_change,
                portfolio_days,
            )

            if scenario_result is None:
                print("Scenario could not be calculated for every position.")
            else:
                print(
                    "Portfolio scenario P&L from entry (cash):",
                    round(scenario_result["pnl"], 2),
                )
                print(
                    "Portfolio scenario change from baseline (cash):",
                    round(scenario_result["change_from_baseline"], 2),
                )


    # Optional portfolio P&L chart
    if portfolio and input("Show portfolio P&L chart? (yes/no):").strip().lower() == "yes":
        plot_portfolio_pnl(portfolio)


if __name__ == "__main__":
    main()
