"""Black-76 pricing and finite-difference Greeks for options on futures.

Use years for time to expiry and decimals for annual volatility and interest
rates. Prices and Greeks are for one option, before position sizing:

- Price: option premium points.
- Delta: option premium points per futures point.
- Gamma: option premium points per futures point squared.
- Vega: option premium points per one percentage-point change in IV.
- Theta: option premium change after one calendar day, other inputs fixed.
- Rho: option premium points per one percentage-point change in interest rate.

Invalid pricing inputs return None after printing the existing validation
message. Individual unavailable Greeks are None. This module contains no
interactive input or portfolio state.
"""

import math
from statistics import NormalDist


def black76_price(selection, futures_price, strike, years, iv, rate_annualized):
    if selection != "call" and selection != "put":
        print("Selection must be a call or a put")
        return None

    if futures_price <= 0 or strike <= 0:
        print("Futures price and strike must be greater than zero")
        return None

    if years < 0 or iv < 0:
        print("Days to expiry and implied volatility cannot be negative")
        return None

    discount_factor = math.exp(-rate_annualized * years)

    if years == 0 or iv == 0:
        if selection == "call":
            intrinsic_value = max(futures_price - strike, 0.0)
        else:
            intrinsic_value = max(strike - futures_price, 0.0)

        return discount_factor * intrinsic_value

    d1 = (
        math.log(futures_price / strike) + 0.5 * iv**2 * years
    ) / (iv * math.sqrt(years))
    d2 = d1 - iv * math.sqrt(years)

    normal = NormalDist()
    nd1 = normal.cdf(d1)
    nd2 = normal.cdf(d2)

    if selection == "call":
        return discount_factor * (futures_price * nd1 - strike * nd2)

    return discount_factor * (
        strike * (1 - nd2) - futures_price * (1 - nd1)
    )


def black76_greeks(selection, futures_price, strike, years, iv, rate_annualized):
    option_price = black76_price(
        selection, futures_price, strike, years, iv, rate_annualized
    )

    if option_price is None:
        return None

    delta = None
    gamma = None
    vega = None
    theta = None
    rho = None

    if years > 0 and iv > 0 and futures_price > 1:
        price_up = black76_price(
            selection, futures_price + 1, strike, years, iv, rate_annualized
        )
        price_down = black76_price(
            selection, futures_price - 1, strike, years, iv, rate_annualized
        )
        delta = (price_up - price_down) / 2.0
        gamma = price_up + price_down - 2 * option_price

    if iv >= 0.01:
        price_iv_up = black76_price(
            selection, futures_price, strike, years, iv + 0.01, rate_annualized
        )
        price_iv_down = black76_price(
            selection, futures_price, strike, years, iv - 0.01, rate_annualized
        )
        vega = (price_iv_up - price_iv_down) / 2.0

    if years >= 1 / 365.0:
        price_one_day_later = black76_price(
            selection,
            futures_price,
            strike,
            years - 1 / 365.0,
            iv,
            rate_annualized,
        )
        if price_one_day_later is not None:
            theta = price_one_day_later - option_price

    price_rate_up = black76_price(
        selection, futures_price, strike, years, iv, rate_annualized + 0.01
    )
    price_rate_down = black76_price(
        selection, futures_price, strike, years, iv, rate_annualized - 0.01
    )

    if price_rate_up is not None and price_rate_down is not None:
        rho = (price_rate_up - price_rate_down) / 2.0

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
    }
