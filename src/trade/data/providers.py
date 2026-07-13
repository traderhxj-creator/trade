from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Union

import pandas as pd

from trade.data.loader import load_price_csv


class PriceProvider(Protocol):
    def load(
        self,
        symbol: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjust: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return OHLCV prices indexed by date."""


@dataclass(frozen=True)
class CsvPriceProvider:
    path: Union[str, Path]

    def load(
        self,
        symbol: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjust: Optional[str] = None,
    ) -> pd.DataFrame:
        prices = load_price_csv(self.path)
        if start:
            prices = prices.loc[prices.index >= pd.Timestamp(start)]
        if end:
            prices = prices.loc[prices.index <= pd.Timestamp(end)]
        return prices
