import math

import pandas as pd


def total_return(equity: pd.Series) -> float:
    return float(equity.iloc[-1] / equity.iloc[0] - 1)


def annual_return(equity: pd.Series, annualization: int = 252) -> float:
    periods = max(len(equity) - 1, 1)
    gross = equity.iloc[-1] / equity.iloc[0]
    return float(gross ** (annualization / periods) - 1)


def max_drawdown(equity: pd.Series) -> float:
    high_watermark = equity.cummax()
    drawdown = equity / high_watermark - 1
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, annualization: int = 252) -> float:
    clean_returns = returns.dropna()
    std = clean_returns.std()
    if std == 0 or math.isnan(std):
        return 0.0
    return float(clean_returns.mean() / std * math.sqrt(annualization))
