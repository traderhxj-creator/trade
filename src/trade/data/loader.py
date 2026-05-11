from pathlib import Path
from typing import Union

import pandas as pd


REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def load_price_csv(path: Union[str, Path]) -> pd.DataFrame:
    prices = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(prices.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required columns: {missing_cols}")

    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices.sort_values("date").set_index("date")

    numeric_cols = ["open", "high", "low", "close", "volume"]
    prices[numeric_cols] = prices[numeric_cols].apply(pd.to_numeric, errors="raise")
    return prices
