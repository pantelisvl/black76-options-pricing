"""Cash totals for the calculator's saved option positions.

Positions use the existing dictionary fields from main.py. They are expected
to have passed the application's input validation and to use a common cash
currency. Interpret combined futures sensitivities within the same-underlying
scope used by the calculator.

Entry premium is positive for premium paid on longs and negative for premium
received on shorts. Modeled option value uses the same long/short sign.
Their difference is modeled P&L from entry, before trading costs.
"""

from pricing import black76_greeks, black76_price


def _signed_position_scale(position):
    """Return signed cash units per option premium point."""
    position_sign = 1 if position["position"] == "long" else -1
    return position_sign * position["contracts"] * position["multiplier"]


def calculate_portfolio_greeks(positions):
    """Return five signed cash Greek totals using the entered market inputs.

    An unavailable Greek on any position makes that portfolio total None.
    Other Greek totals remain available. An empty portfolio returns zeros.
    """
    totals = {
        "delta": 0.0,
        "gamma": 0.0,
        "vega": 0.0,
        "theta": 0.0,
        "rho": 0.0,
    }

    for position in positions:
        position_greeks = black76_greeks(
            position["selection"],
            position["futures_price"],
            position["strike"],
            position["dte"] / 365.0,
            position["iv"],
            position["rate_annualized"],
        )
        position_scale = _signed_position_scale(position)

        for greek_name in totals:
            if position_greeks is None or position_greeks[greek_name] is None:
                totals[greek_name] = None
            elif totals[greek_name] is not None:
                totals[greek_name] += position_greeks[greek_name] * position_scale

    return totals


def calculate_portfolio_summary(positions):
    """Return signed entry premium, modeled value and modeled P&L in cash.

    Use each position's original market inputs. Return None if any position
    cannot be priced, so a partial portfolio is never reported as complete.
    An empty portfolio returns three zero values.
    """
    entry_premium = 0.0
    model_value = 0.0

    for position in positions:
        model_price = black76_price(
            position["selection"],
            position["futures_price"],
            position["strike"],
            position["dte"] / 365.0,
            position["iv"],
            position["rate_annualized"],
        )

        if model_price is None:
            return None

        position_scale = _signed_position_scale(position)
        entry_premium += position["premium"] * position_scale
        model_value += model_price * position_scale

    return {
        "entry_premium": entry_premium,
        "model_value": model_value,
        "pnl": model_value - entry_premium,
    }


def calculate_portfolio_scenario(positions, futures_move, iv_change, days_elapsed):
    """Return cash P&L from entry and cash change from the original baseline.

    Apply the same futures-point move, decimal IV change and elapsed calendar
    days to each position. Inputs are finite numbers from main.py. Original
    position data is unchanged, so repeated scenarios are independent.

    Return None for negative elapsed days, days beyond any position's expiry,
    or an unavailable baseline or scenario price. Empty portfolios return
    zeros for nonnegative elapsed days.
    """
    if days_elapsed < 0:
        return None

    scenario_pnl = 0.0
    scenario_change = 0.0

    for position in positions:
        if days_elapsed > position["dte"]:
            return None

        scenario_price = black76_price(
            position["selection"],
            position["futures_price"] + futures_move,
            position["strike"],
            (position["dte"] - days_elapsed) / 365.0,
            position["iv"] + iv_change,
            position["rate_annualized"],
        )

        baseline_price = black76_price(
            position["selection"],
            position["futures_price"],
            position["strike"],
            position["dte"] / 365.0,
            position["iv"],
            position["rate_annualized"],
        )

        if scenario_price is None or baseline_price is None:
            return None

        position_scale = _signed_position_scale(position)
        scenario_pnl += (scenario_price - position["premium"]) * position_scale
        scenario_change += (scenario_price - baseline_price) * position_scale

    return {
        "pnl": scenario_pnl,
        "change_from_baseline": scenario_change,
    }
