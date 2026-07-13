import math

import pandas as pd


def _clean_equity(equity: pd.Series) -> pd.Series:
    clean = equity.dropna()
    if clean.empty:
        raise ValueError("equity series must contain at least one value.")
    if clean.iloc[0] <= 0:
        raise ValueError("equity series must start above 0.")
    return clean


def total_return(equity: pd.Series) -> float:
    clean = _clean_equity(equity)
    return float(clean.iloc[-1] / clean.iloc[0] - 1)


def annual_return(equity: pd.Series, annualization: int = 252) -> float:
    if annualization <= 0:
        raise ValueError("annualization must be greater than 0.")
    clean = _clean_equity(equity)
    periods = max(len(clean) - 1, 1)
    gross = clean.iloc[-1] / clean.iloc[0]
    return float(gross ** (annualization / periods) - 1)


def max_drawdown(equity: pd.Series) -> float:
    clean = _clean_equity(equity)
    high_watermark = clean.cummax()
    drawdown = clean / high_watermark - 1
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, annualization: int = 252) -> float:
    clean_returns = returns.dropna()
    std = clean_returns.std()
    if std == 0 or math.isnan(std):
        return 0.0
    return float(clean_returns.mean() / std * math.sqrt(annualization))
