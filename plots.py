"""Plot modeled portfolio P&L against the futures price.

Use the same saved position dictionaries as main.py and portfolio.py.
Positions should refer to the same underlying and cash currency, and this
chart requires a common original futures price.

Only the futures price varies. Each position's entered IV, interest rate and
days to expiry remain fixed. Earlier interactive scenarios do not change
this chart's baseline. Plotting libraries load only when a chart is requested.
"""

from portfolio import calculate_portfolio_scenario


def plot_portfolio_pnl(positions):
    """Show the existing P&L chart and return its Matplotlib figure.

    Return None with a message for an empty portfolio, different baseline
    futures prices or a grid point that cannot be priced for every position.
    The original position dictionaries are never changed.
    """
    if not positions:
        print("No positions stored.")
        return None

    baseline_futures = positions[0]["futures_price"]

    same_futures_price = all(
        saved_position["futures_price"] == baseline_futures
        for saved_position in positions
    )

    if not same_futures_price:
        print("This chart requires the same baseline futures price for all positions.")
        return None

    import numpy as np
    import matplotlib.pyplot as plt

    futures_grid = np.linspace(baseline_futures * 0.90, baseline_futures * 1.10, 101,)
    baseline_index = len(futures_grid) // 2
    futures_grid[baseline_index] = baseline_futures

    portfolio_pnl_grid = []

    for chart_futures_price in futures_grid:
        scenario_result = calculate_portfolio_scenario(
            positions,
            futures_move=float(chart_futures_price) - baseline_futures,
            iv_change=0.0,
            days_elapsed=0.0,
        )

        if scenario_result is None:
            print("Chart unavailable: one or more positions could not be priced.")
            return None

        portfolio_pnl_grid.append(scenario_result["pnl"])

    baseline_pnl = portfolio_pnl_grid[baseline_index]
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(futures_grid, portfolio_pnl_grid, label="Modeled portfolio P&L")
    ax.axhline(0, color="black", linewidth=1, label="Zero P&L")
    ax.axvline(
        baseline_futures,
        color="gray",
        linestyle="--",
        label="Baseline futures price",
    )
    ax.scatter(
        [baseline_futures],
        [baseline_pnl],
        color="black",
        zorder=3,
        label=f"Baseline P&L: {baseline_pnl:,.2f}",
    )

    ax.set_xlabel("Futures price (points)")
    ax.set_ylabel("Modeled P&L from entry (cash units)")
    ax.set_title("Portfolio P&L — entered IV, rate and DTE held fixed")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    plt.show()

    return fig
