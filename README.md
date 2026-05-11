# Trade Quant Starter

一个轻量级 Python 量化回测系统骨架，适合从本地 CSV 快速跑通策略验证。

## 功能

- CSV 行情数据读取
- 策略接口
- 示例双均线策略
- 单标的回测引擎
- 手续费、滑点
- 净值曲线、最大回撤、夏普比率等指标
- CLI 命令行入口

## 项目结构

```text
trade/
  data/
    sample_prices.csv
  src/trade/
    backtester.py
    cli.py
    metrics.py
    models.py
    data/
      loader.py
    strategies/
      base.py
      moving_average.py
  tests/
    test_backtester.py
```

## 安装

```bash
cd /Users/a/project/hu/trade
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 运行示例回测

```bash
trade backtest \
  --data data/sample_prices.csv \
  --strategy moving_average \
  --cash 100000 \
  --short-window 20 \
  --long-window 60
```

也可以直接运行模块：

```bash
python -m trade.cli backtest --data data/sample_prices.csv
```

## 启动可视化页面

```bash
trade web --port 8765
```

然后在浏览器打开：

```text
http://127.0.0.1:8765
```

页面带登录鉴权，默认账号为 `admin`，默认密码为 `trade123`。生产或共享环境建议在启动前设置：

```bash
export TRADE_WEB_USER="your-user"
export TRADE_WEB_PASSWORD="your-password"
export TRADE_WEB_SECRET="a-long-random-secret"
```

页面支持选择 CSV 数据、调整初始资金、均线窗口、手续费和滑点，并展示关键指标、净值曲线、价格曲线和回撤曲线。

## CSV 格式

至少需要这些列：

```text
date,open,high,low,close,volume
```

`date` 会被解析为时间索引。

## 下一步建议

- 加多标的组合回测
- 加调仓周期和目标权重
- 加 DuckDB/Parquet 数据层
- 加策略参数批量优化
- 加交易日历、涨跌停、成交量约束
- 接入模拟盘或券商 API
