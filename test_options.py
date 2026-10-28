"""Standard-library checks for pricing, Greek units, and portfolio behavior.

Run from this folder with:
    python -m unittest -v test_options

Eight tests preserve the original pricing checks. Additional tests
cover the finite-difference conventions and the portfolio/scenario contracts.
They do not open plots or require NumPy or Matplotlib.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import math
import unittest

from pricing import black76_greeks, black76_price
from portfolio import (
    calculate_portfolio_greeks,
    calculate_portfolio_scenario,
    calculate_portfolio_summary,
)


GREEK_NAMES = ("delta", "gamma", "vega", "theta", "rho")


def sample_position(**changes):
    """Return a fresh copy of the worked example's position inputs."""
    position = {
        "selection": "call",
        "position": "long",
        "futures_price": 5000.0,
        "strike": 5000.0,
        "premium": 100.0,
        "dte": 30.0,
        "iv": 0.20,
        "rate_annualized": 0.05,
        "settlement": 5100.0,
        "contracts": 2,
        "multiplier": 5.0,
    }
    position.update(changes)
    return position


def analytical_benchmark_greeks(selection):
    """Independent closed-form sensitivities for F=620, K=600, T=0.5.

    Vega and rho are scaled to a one-percentage-point change. The application
    uses finite bumps, so its outputs approximate these derivatives.
    """
    futures, strike, years, iv, rate = 620.0, 600.0, 0.5, 0.2, 0.05
    discount = math.exp(-rate * years)
    d1 = (
        math.log(futures / strike) + 0.5 * iv**2 * years
    ) / (iv * math.sqrt(years))
    cdf = 0.5 * math.erfc(-d1 / math.sqrt(2.0))
    density = math.exp(-0.5 * d1**2) / math.sqrt(2.0 * math.pi)
    reference_prices = {
        "call": 44.186853312106605,
        "put": 24.680655071539952,
    }

    return {
        "delta": discount * (cdf if selection == "call" else cdf - 1.0),
        "gamma": discount * density / (futures * iv * math.sqrt(years)),
        "vega": 0.01 * discount * futures * density * math.sqrt(years),
        "rho": -0.01 * years * reference_prices[selection],
    }


class PricingTests(unittest.TestCase):
    """The eight original checks, plus the documented invalid-input contract."""

    def test_call_price_benchmark(self):
        actual = black76_price("call", 620, 600, 0.5, 0.2, 0.05)
        self.assertAlmostEqual(actual, 44.1868533121, places=8)

    def test_put_price_benchmark(self):
        actual = black76_price("put", 20, 20, 4 / 12, 0.25, 0.09)
        self.assertAlmostEqual(actual, 1.11664145656, places=8)

    def test_in_the_money_call_at_expiry(self):
        self.assertEqual(black76_price("call", 5100, 5000, 0, 0.2, 0.05), 100)

    def test_out_of_the_money_call_at_expiry(self):
        self.assertEqual(black76_price("call", 4900, 5000, 0, 0.2, 0.05), 0)

    def test_in_the_money_put_at_expiry(self):
        self.assertEqual(black76_price("put", 4900, 5000, 0, 0.2, 0.05), 100)

    def test_out_of_the_money_put_at_expiry(self):
        self.assertEqual(black76_price("put", 5100, 5000, 0, 0.2, 0.05), 0)

    def test_zero_volatility_discounts_intrinsic_value(self):
        years = 30 / 365.0
        actual = black76_price("call", 5100, 5000, years, 0, 0.05)
        self.assertAlmostEqual(actual, 100 * math.exp(-0.05 * years), places=10)

    def test_non_at_the_money_put_call_parity(self):
        futures, strike, years, iv, rate = 5100, 5000, 30 / 365, 0.20, 0.05
        call = black76_price("call", futures, strike, years, iv, rate)
        put = black76_price("put", futures, strike, years, iv, rate)
        self.assertIsNotNone(call)
        self.assertIsNotNone(put)
        expected = math.exp(-rate * years) * (futures - strike)
        self.assertAlmostEqual(call - put, expected, places=8)

    def test_invalid_pricing_inputs_return_none(self):
        cases = {
            "option type": ("other", 5000, 5000, 0.5, 0.2, 0.05),
            "futures price": ("call", 0, 5000, 0.5, 0.2, 0.05),
            "strike": ("call", 5000, 0, 0.5, 0.2, 0.05),
            "time": ("call", 5000, 5000, -0.5, 0.2, 0.05),
            "volatility": ("call", 5000, 5000, 0.5, -0.2, 0.05),
        }
        for name, inputs in cases.items():
            with self.subTest(input=name), redirect_stdout(io.StringIO()):
                self.assertIsNone(black76_price(*inputs))


class GreekTests(unittest.TestCase):
    def assert_analytical_greek(self, name, relative_tolerance):
        for selection in ("call", "put"):
            with self.subTest(selection=selection, greek=name):
                actual = black76_greeks(selection, 620, 600, 0.5, 0.2, 0.05)
                expected = analytical_benchmark_greeks(selection)[name]
                self.assertIsNotNone(actual)
                self.assertIsNotNone(actual[name])
                self.assertTrue(
                    math.isclose(
                        actual[name], expected,
                        rel_tol=relative_tolerance, abs_tol=1e-9,
                    ),
                    f"{selection} {name}: {actual[name]} versus {expected}",
                )

    # These tolerances allow truncation error from the existing fixed bumps;
    # they still distinguish the required units and signs decisively.
    def test_delta_matches_the_futures_price_derivative(self):
        self.assert_analytical_greek("delta", relative_tolerance=2e-5)

    def test_gamma_matches_analytical_curvature(self):
        self.assert_analytical_greek("gamma", relative_tolerance=2e-5)

    def test_vega_is_per_percentage_point_of_iv(self):
        self.assert_analytical_greek("vega", relative_tolerance=2e-4)

    def test_rho_is_per_percentage_point_with_futures_price_fixed(self):
        self.assert_analytical_greek("rho", relative_tolerance=1e-5)

    def test_theta_is_a_one_calendar_day_repricing_change(self):
        # Closed-form prices at T=0.5 and T=0.5-1/365 were evaluated with
        # high-precision arithmetic. These are finite one-day changes,
        # not the instantaneous theta derivative divided by 365.
        expected = {
            "call": -0.083362241898053597,
            "put": -0.086034506876485181,
        }
        for selection, one_day_change in expected.items():
            with self.subTest(selection=selection):
                actual = black76_greeks(selection, 620, 600, 0.5, 0.2, 0.05)
                self.assertAlmostEqual(actual["theta"], one_day_change, places=10)

    def test_unavailable_greeks_at_fixed_bump_boundaries(self):
        cases = {
            "small futures price": (("call", 1, 1, 0.5, 0.2, 0.05),
                                    {"delta", "gamma"}),
            "iv below one percent": (("call", 620, 600, 0.5, 0.005, 0.05),
                                     {"vega"}),
            "less than one day": (("call", 620, 600, 0.5 / 365, 0.2, 0.05),
                                  {"theta"}),
            "expiry": (("call", 620, 600, 0, 0.2, 0.05),
                       {"delta", "gamma", "theta"}),
            "zero iv": (("call", 620, 600, 0.5, 0, 0.05),
                        {"delta", "gamma", "vega"}),
        }
        for name, (inputs, expected_missing) in cases.items():
            with self.subTest(boundary=name):
                actual = black76_greeks(*inputs)
                self.assertIsNotNone(actual)
                missing = {name for name, value in actual.items() if value is None}
                self.assertEqual(missing, expected_missing)


class PortfolioTests(unittest.TestCase):
    def test_summary_respects_long_and_short_cash_signs(self):
        for direction, sign in (("long", 1), ("short", -1)):
            with self.subTest(position=direction):
                result = calculate_portfolio_summary([
                    sample_position(position=direction)
                ])
                self.assertAlmostEqual(result["entry_premium"], sign * 1000.0)
                self.assertAlmostEqual(
                    result["model_value"], sign * 1138.8853329922772, places=8
                )
                self.assertAlmostEqual(
                    result["pnl"], sign * 138.8853329922772, places=8
                )

    def test_cash_greeks_include_sign_quantity_and_multiplier(self):
        long_call = sample_position()
        short_put = sample_position(selection="put", position="short",
                                    contracts=3, multiplier=7.0)
        actual = calculate_portfolio_greeks([long_call, short_put])
        call_greeks = black76_greeks("call", 5000, 5000, 30 / 365, 0.2, 0.05)
        put_greeks = black76_greeks("put", 5000, 5000, 30 / 365, 0.2, 0.05)
        for name in GREEK_NAMES:
            with self.subTest(greek=name):
                expected = call_greeks[name] * 10 - put_greeks[name] * 21
                self.assertAlmostEqual(actual[name], expected, places=9)

    def test_identical_long_and_short_cancel(self):
        positions = [sample_position(), sample_position(position="short")]
        summary = calculate_portfolio_summary(positions)
        greeks = calculate_portfolio_greeks(positions)
        scenario = calculate_portfolio_scenario(positions, 100, 0.01, 1)
        for category, values in (("summary", summary), ("greeks", greeks),
                                 ("scenario", scenario)):
            for name, value in values.items():
                with self.subTest(category=category, value=name):
                    self.assertAlmostEqual(value, 0.0, places=9)

    def test_offsetting_greeks_do_not_erase_different_entry_premiums(self):
        positions = [sample_position(),
                     sample_position(position="short", premium=110.0)]
        summary = calculate_portfolio_summary(positions)
        self.assertAlmostEqual(summary["entry_premium"], -100.0, places=9)
        self.assertAlmostEqual(summary["model_value"], 0.0, places=9)
        self.assertAlmostEqual(summary["pnl"], 100.0, places=9)
        for value in calculate_portfolio_greeks(positions).values():
            self.assertAlmostEqual(value, 0.0, places=9)
        scenario = calculate_portfolio_scenario(positions, 100, 0.01, 1)
        self.assertAlmostEqual(scenario["pnl"], 100.0, places=9)
        self.assertAlmostEqual(scenario["change_from_baseline"], 0.0, places=9)

    def test_missing_greek_poisoning_is_order_independent(self):
        regular = sample_position()
        low_iv = sample_position(iv=0.005)
        regular_greeks = black76_greeks("call", 5000, 5000, 30 / 365, 0.2, 0.05)
        low_iv_greeks = black76_greeks("call", 5000, 5000, 30 / 365, 0.005, 0.05)
        for positions in ([regular, low_iv], [low_iv, regular]):
            with self.subTest(first_iv=positions[0]["iv"]):
                actual = calculate_portfolio_greeks(positions)
                self.assertIsNone(actual["vega"])
                for name in ("delta", "gamma", "theta", "rho"):
                    expected = (regular_greeks[name] + low_iv_greeks[name]) * 10
                    self.assertAlmostEqual(actual[name], expected, places=9)

    def test_invalid_leg_never_produces_partial_portfolio_totals(self):
        valid = sample_position()
        invalid = sample_position(futures_price=0.0)
        for positions in ([valid, invalid], [invalid, valid]):
            with self.subTest(first_futures=positions[0]["futures_price"]):
                with redirect_stdout(io.StringIO()):
                    self.assertIsNone(calculate_portfolio_summary(positions))
                    self.assertEqual(
                        calculate_portfolio_greeks(positions),
                        dict.fromkeys(GREEK_NAMES, None),
                    )
                    # The +100 move makes the invalid leg's scenario futures
                    # positive; its invalid original baseline must still fail.
                    self.assertIsNone(
                        calculate_portfolio_scenario(positions, 100, 0.01, 1)
                    )

    def test_empty_portfolio_returns_zero_totals(self):
        self.assertEqual(calculate_portfolio_greeks([]),
                         dict.fromkeys(GREEK_NAMES, 0.0))
        self.assertEqual(calculate_portfolio_summary([]),
                         {"entry_premium": 0.0, "model_value": 0.0, "pnl": 0.0})
        self.assertEqual(calculate_portfolio_scenario([], 100, 0.01, 1),
                         {"pnl": 0.0, "change_from_baseline": 0.0})


class ScenarioTests(unittest.TestCase):
    def test_shared_scenario_matches_the_worked_example(self):
        actual = calculate_portfolio_scenario([sample_position()], 100, 0.01, 1)
        self.assertAlmostEqual(actual["pnl"], 751.481657449955, places=8)
        self.assertAlmostEqual(
            actual["change_from_baseline"], 612.5963244576778, places=8
        )

    def test_zero_scenario_preserves_entry_pnl(self):
        actual = calculate_portfolio_scenario([sample_position()], 0, 0, 0)
        self.assertAlmostEqual(actual["pnl"], 138.8853329922772, places=8)
        self.assertAlmostEqual(actual["change_from_baseline"], 0.0, places=10)

    def test_horizon_at_first_expiry_keeps_later_option_live(self):
        first_expiry = sample_position(dte=1.0)
        later_expiry = sample_position(
            selection="put", position="short", strike=5200.0,
            premium=250.0, dte=30.0, iv=0.30, rate_annualized=0.03,
            contracts=1,
        )
        positions = [first_expiry, later_expiry]
        actual = calculate_portfolio_scenario(positions, 100, 0.01, 1)
        self.assertIsNotNone(actual)
        # The first call expires at intrinsic 100, matching its entry premium.
        # The second position retains 29 days; it must not become intrinsic.
        surviving_put = black76_price("put", 5100, 5200, 29 / 365, 0.31, 0.03)
        expected_pnl = (250.0 - surviving_put) * 5.0
        self.assertAlmostEqual(actual["pnl"], expected_pnl, places=8)
        baseline = calculate_portfolio_summary(positions)
        self.assertAlmostEqual(
            actual["change_from_baseline"], expected_pnl - baseline["pnl"],
            places=8,
        )

    def test_elapsed_days_stay_within_the_earliest_expiry(self):
        positions = [sample_position(dte=1.0), sample_position(dte=30.0)]
        for days in (-1.0, 1.01):
            for ordered in (positions, list(reversed(positions))):
                with self.subTest(days=days, first_dte=ordered[0]["dte"]):
                    self.assertIsNone(
                        calculate_portfolio_scenario(ordered, 100, 0.01, days)
                    )

    def test_invalid_scenario_price_prevents_partial_totals(self):
        regular = sample_position()
        low_iv = sample_position(iv=0.01)
        for positions in ([regular, low_iv], [low_iv, regular]):
            with self.subTest(first_iv=positions[0]["iv"]):
                with redirect_stdout(io.StringIO()):
                    self.assertIsNone(
                        calculate_portfolio_scenario(positions, 0, -0.02, 0)
                    )
        with self.subTest(scenario="nonpositive futures"), \
                redirect_stdout(io.StringIO()):
            self.assertIsNone(
                calculate_portfolio_scenario([regular], -5000, 0, 0)
            )

    def test_scenarios_do_not_mutate_inputs_or_accumulate(self):
        positions = [sample_position()]
        original = deepcopy(positions)
        baseline = calculate_portfolio_summary(positions)
        first = calculate_portfolio_scenario(positions, 100, 0.01, 1)
        different = calculate_portfolio_scenario(positions, -100, -0.01, 2)
        repeated = calculate_portfolio_scenario(positions, 100, 0.01, 1)
        self.assertNotEqual(first, different)
        self.assertEqual(first, repeated)
        self.assertEqual(positions, original)
        self.assertEqual(calculate_portfolio_summary(positions), baseline)


if __name__ == "__main__":
    unittest.main(verbosity=2)
