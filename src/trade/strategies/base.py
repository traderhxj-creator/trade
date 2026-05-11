from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """Return target position signals: 1 for long, 0 for flat."""
