import argparse
from pathlib import Path

from trade.web import serve


def format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def run_backtest(args: argparse.Namespace) -> None:
    from trade.backtester import Backtester
    from trade.data.loader import load_price_csv
    from trade.models import BacktestConfig
    from trade.strategies import MovingAverageCrossStrategy

    prices = load_price_csv(args.data)
    strategy = MovingAverageCrossStrategy(
        short_window=args.short_window,
        long_window=args.long_window,
    )
    config = BacktestConfig(
        initial_cash=args.cash,
        commission_rate=args.commission_rate,
        slippage_rate=args.slippage_rate,
    )

    frame, result = Backtester(config).run(prices, strategy)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output)

    print("Backtest finished")
    print(f"Final equity:   {result.final_equity:,.2f}")
    print(f"Total return:   {format_pct(result.total_return)}")
    print(f"Annual return:  {format_pct(result.annual_return)}")
    print(f"Max drawdown:   {format_pct(result.max_drawdown)}")
    print(f"Sharpe ratio:   {result.sharpe_ratio:.2f}")
    print(f"Trades:         {result.trades}")


def run_web(args: argparse.Namespace) -> None:
    serve(host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trade")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest = subparsers.add_parser("backtest", help="Run a single-symbol backtest.")
    backtest.add_argument("--data", required=True, help="Path to OHLCV CSV file.")
    backtest.add_argument("--strategy", default="moving_average", choices=["moving_average"])
    backtest.add_argument("--cash", type=float, default=100_000.0)
    backtest.add_argument("--commission-rate", type=float, default=0.0003)
    backtest.add_argument("--slippage-rate", type=float, default=0.0002)
    backtest.add_argument("--short-window", type=int, default=20)
    backtest.add_argument("--long-window", type=int, default=60)
    backtest.add_argument("--output", help="Optional path to save the equity curve CSV.")
    backtest.set_defaults(func=run_backtest)

    web = subparsers.add_parser("web", help="Start the local visual dashboard.")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    web.set_defaults(func=run_web)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
