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

## 微信小程序端

仓库里提供了一个只负责获取结果的小程序端，代码在：

```text
miniprogram/
```

它会调用后端的这些接口：

```text
POST /api/login
GET  /api/datasets
GET  /api/backtest
POST /api/logout
```

开发时先让电脑上的后端监听局域网地址：

```bash
trade web --host 0.0.0.0 --port 8765
```

然后在 `miniprogram/config.js` 里把 `baseUrl` 改成电脑的局域网地址，例如：

```js
baseUrl: "http://192.168.1.8:8765"
```

用微信开发者工具打开 `miniprogram/` 目录即可预览。项目配置里已关闭开发阶段的 URL 校验，方便连接本机服务。

真机调试或正式发布时，微信要求后端使用 HTTPS，并且域名需要在微信公众平台配置为合法 request 域名。电脑作为服务器时，可以用公网 IP/域名加 HTTPS 反向代理到本机的 `8765` 端口。

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
