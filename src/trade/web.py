import json
import os
import secrets
import time
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse


STATIC_DIR = Path(__file__).with_name("web_static")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_PATH = DATA_DIR / "backtest_history.jsonl"
SESSION_COOKIE = "trade_session"
SESSION_TTL_SECONDS = 60 * 60 * 8
AUTH_USER = os.environ.get("TRADE_WEB_USER", "admin")
AUTH_PASSWORD = os.environ.get("TRADE_WEB_PASSWORD", "trade123")
AUTH_SECRET = os.environ.get("TRADE_WEB_SECRET", secrets.token_hex(32))


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _json_cookie_response(
    handler: BaseHTTPRequestHandler,
    payload: dict,
    cookie: Optional[str] = None,
    status: int = 200,
) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    if cookie:
        handler.send_header("Set-Cookie", cookie)
    handler.end_headers()
    handler.wfile.write(body)


def _static_response(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    body = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _float(params: dict[str, list[str]], key: str, default: float) -> float:
    raw_value = params.get(key, [default])[0]
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")


def _int(params: dict[str, list[str]], key: str, default: int) -> int:
    raw_value = params.get(key, [default])[0]
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer.")


def _optional_str(params: dict[str, list[str]], key: str) -> Optional[str]:
    value = params.get(key, [""])[0].strip()
    return value or None


def _safe_data_path(raw_path: str) -> Path:
    path = (PROJECT_ROOT / raw_path).resolve()
    project_root = PROJECT_ROOT.resolve()
    if project_root not in path.parents and path != project_root:
        raise ValueError("Data path must stay inside the project directory.")
    if not path.exists():
        raise ValueError(f"Data file does not exist: {raw_path}")
    return path


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    body = handler.rfile.read(length).decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON body.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    return payload


def _cookie_value(handler: BaseHTTPRequestHandler, name: str) -> Optional[str]:
    raw_cookie = handler.headers.get("Cookie", "")
    for part in raw_cookie.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return None


def _session_signature(username: str, expires_at: int, nonce: str) -> str:
    message = f"{username}:{expires_at}:{nonce}".encode("utf-8")
    return hmac_new(AUTH_SECRET.encode("utf-8"), message, sha256).hexdigest()


def _create_session(username: str) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    nonce = secrets.token_urlsafe(16)
    signature = _session_signature(username, expires_at, nonce)
    return f"{username}:{expires_at}:{nonce}:{signature}"


def _valid_session(handler: BaseHTTPRequestHandler) -> Optional[str]:
    token = _cookie_value(handler, SESSION_COOKIE)
    if not token:
        return None
    try:
        username, raw_expires_at, nonce, signature = token.split(":", 3)
        expires_at = int(raw_expires_at)
    except ValueError:
        return None
    if expires_at < int(time.time()):
        return None
    expected = _session_signature(username, expires_at, nonce)
    if not compare_digest(signature, expected):
        return None
    return username


def _session_cookie(token: str) -> str:
    return (
        f"{SESSION_COOKIE}={token}; Max-Age={SESSION_TTL_SECONDS}; "
        "Path=/; HttpOnly; SameSite=Strict"
    )


def _clear_session_cookie() -> str:
    return f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict"


def _require_auth(handler: BaseHTTPRequestHandler) -> Optional[str]:
    username = _valid_session(handler)
    if username is None:
        _json_response(handler, {"error": "Unauthorized"}, status=401)
    return username


def _constant_time_equal(left: str, right: str) -> bool:
    return compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _money(value: float) -> str:
    return f"{value:,.2f}"


def list_csv_files() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return [
        str(path.relative_to(PROJECT_ROOT))
        for path in sorted(DATA_DIR.glob("*.csv"))
    ]


def list_strategy_specs() -> list[dict[str, str]]:
    from trade.strategies import available_strategies

    return [
        {
            "name": spec.name,
            "label": spec.label,
            "description": spec.description,
        }
        for spec in available_strategies()
    ]


def dataset_profile(raw_path: str) -> dict[str, Any]:
    from trade.data import CsvPriceProvider

    data_path = _safe_data_path(raw_path)
    prices = CsvPriceProvider(data_path).load()
    missing_values = int(prices.isna().sum().sum())
    first_date = prices.index.min().strftime("%Y-%m-%d")
    last_date = prices.index.max().strftime("%Y-%m-%d")
    close = prices["close"]
    total_return_value = float(close.iloc[-1] / close.iloc[0] - 1)
    daily_returns = close.pct_change().dropna()
    volatility = float(daily_returns.std() * (252 ** 0.5)) if not daily_returns.empty else 0.0

    return {
        "data": str(data_path.relative_to(PROJECT_ROOT)),
        "rows": int(len(prices)),
        "columns": list(prices.columns),
        "first_date": first_date,
        "last_date": last_date,
        "missing_values": missing_values,
        "close_min": round(float(close.min()), 4),
        "close_max": round(float(close.max()), 4),
        "close_start": round(float(close.iloc[0]), 4),
        "close_end": round(float(close.iloc[-1]), 4),
        "buy_and_hold_return": round(total_return_value, 6),
        "annualized_volatility": round(volatility, 6),
    }


def _build_report(payload: dict[str, Any]) -> str:
    result = payload["result"]
    meta = payload["meta"]
    profile = payload.get("profile", {})
    generated_at = meta["generated_at"]
    range_text = " ~ ".join(
        value for value in [meta.get("start") or profile.get("first_date"), meta.get("end") or profile.get("last_date")] if value
    )

    return "\n".join(
        [
            "# 回测研究报告",
            "",
            "## 摘要",
            "",
            f"- 生成时间: {generated_at}",
            f"- 数据文件: {meta['data']}",
            f"- 样本区间: {range_text or '未指定'}",
            f"- 策略: {meta['strategy']}",
            f"- 参数: MA({meta['short_window']}, {meta['long_window']}), 初始资金 {_money(meta['cash'])}",
            "",
            "## 核心指标",
            "",
            f"- 期末净值: {_money(result['final_equity'])}",
            f"- 总收益: {_pct(result['total_return'])}",
            f"- 年化收益: {_pct(result['annual_return'])}",
            f"- 最大回撤: {_pct(result['max_drawdown'])}",
            f"- 夏普比率: {result['sharpe_ratio']:.2f}",
            f"- 交易次数: {result['trades']}",
            "",
            "## 数据画像",
            "",
            f"- 行数: {profile.get('rows', meta['rows'])}",
            f"- 缺失值: {profile.get('missing_values', 0)}",
            f"- 收盘价范围: {profile.get('close_min', '-')} ~ {profile.get('close_max', '-')}",
            f"- 买入持有收益: {_pct(float(profile.get('buy_and_hold_return', 0)))}",
            f"- 年化波动率: {_pct(float(profile.get('annualized_volatility', 0)))}",
            "",
            "## 风险提示",
            "",
            "本报告仅用于研究和教育目的，不构成投资建议。历史回测不代表未来表现，实际交易还会受到滑点、流动性、停牌、涨跌停和执行延迟等因素影响。",
            "",
        ]
    )


def _series_to_csv(series: list[dict[str, Any]]) -> str:
    columns = ["date", "close", "equity", "drawdown", "position", "signal"]
    lines = [",".join(columns)]
    for row in series:
        lines.append(",".join(str(row[column]) for column in columns))
    return "\n".join(lines) + "\n"


def _history_summary(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload["result"]
    meta = payload["meta"]
    return {
        "id": meta["run_id"],
        "generated_at": meta["generated_at"],
        "data": meta["data"],
        "strategy": meta["strategy"],
        "short_window": meta["short_window"],
        "long_window": meta["long_window"],
        "cash": meta["cash"],
        "start": meta["start"],
        "end": meta["end"],
        "rows": meta["rows"],
        "final_equity": result["final_equity"],
        "total_return": result["total_return"],
        "annual_return": result["annual_return"],
        "max_drawdown": result["max_drawdown"],
        "sharpe_ratio": result["sharpe_ratio"],
        "trades": result["trades"],
    }


def _append_history(payload: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_history_summary(payload), ensure_ascii=False) + "\n")


def list_backtest_history(limit: int = 20) -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []

    rows: list[dict[str, Any]] = []
    with HISTORY_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(rows[-limit:]))


def run_backtest_from_params(params: dict[str, list[str]]) -> dict:
    from trade.backtester import Backtester
    from trade.data import CsvPriceProvider
    from trade.models import BacktestConfig
    from trade.strategies import build_strategy

    data_path = _safe_data_path(params.get("data", ["data/sample_prices.csv"])[0])
    strategy_name = params.get("strategy", ["moving_average"])[0]
    short_window = _int(params, "short_window", 20)
    long_window = _int(params, "long_window", 60)
    if short_window >= long_window:
        raise ValueError("short_window must be smaller than long_window.")
    start = _optional_str(params, "start")
    end = _optional_str(params, "end")
    cash = _float(params, "cash", 100_000.0)
    commission_rate = _float(params, "commission_rate", 0.0003)
    slippage_rate = _float(params, "slippage_rate", 0.0002)

    prices = CsvPriceProvider(data_path).load(start=start, end=end)
    strategy = build_strategy(
        strategy_name,
        short_window=short_window,
        long_window=long_window,
    )
    config = BacktestConfig(
        initial_cash=cash,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )

    frame, result = Backtester(config).run(prices, strategy)
    chart_frame = frame.reset_index()
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    run_id = secrets.token_hex(8)

    payload = {
        "result": asdict(result),
        "series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": round(float(row["close"]), 4),
                "equity": round(float(row["equity"]), 4),
                "drawdown": round(float(row["drawdown"]), 6),
                "position": int(row["position"]),
                "signal": int(row["signal"]),
            }
            for _, row in chart_frame.iterrows()
        ],
        "meta": {
            "run_id": run_id,
            "generated_at": generated_at,
            "data": str(data_path.relative_to(PROJECT_ROOT)),
            "rows": len(frame),
            "short_window": short_window,
            "long_window": long_window,
            "strategy": strategy_name,
            "start": start,
            "end": end,
            "cash": cash,
            "commission_rate": commission_rate,
            "slippage_rate": slippage_rate,
        },
    }
    payload["profile"] = dataset_profile(payload["meta"]["data"])
    payload["report_markdown"] = _build_report(payload)
    payload["series_csv"] = _series_to_csv(payload["series"])
    _append_history(payload)
    return payload


class TradeWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        try:
            if parsed.path == "/":
                return _static_response(self, STATIC_DIR / "index.html", "text/html; charset=utf-8")
            if parsed.path == "/app.js":
                return _static_response(self, STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            if parsed.path == "/styles.css":
                return _static_response(self, STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            if parsed.path == "/api/session":
                username = _valid_session(self)
                return _json_response(self, {"authenticated": username is not None, "username": username})
            if parsed.path == "/api/datasets":
                if _require_auth(self) is None:
                    return
                return _json_response(self, {"datasets": list_csv_files()})
            if parsed.path == "/api/strategies":
                if _require_auth(self) is None:
                    return
                return _json_response(self, {"strategies": list_strategy_specs()})
            if parsed.path == "/api/dataset-profile":
                if _require_auth(self) is None:
                    return
                params = parse_qs(parsed.query)
                data = params.get("data", ["data/sample_prices.csv"])[0]
                return _json_response(self, {"profile": dataset_profile(data)})
            if parsed.path == "/api/backtest-history":
                if _require_auth(self) is None:
                    return
                params = parse_qs(parsed.query)
                limit = _int(params, "limit", 20)
                return _json_response(self, {"history": list_backtest_history(limit=limit)})
            if parsed.path == "/api/backtest":
                if _require_auth(self) is None:
                    return
                return _json_response(self, run_backtest_from_params(parse_qs(parsed.query)))

            _json_response(self, {"error": "Not found"}, status=404)
        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        try:
            if parsed.path == "/api/login":
                payload = _read_json_body(self)
                username = str(payload.get("username", ""))
                password = str(payload.get("password", ""))
                if _constant_time_equal(username, AUTH_USER) and _constant_time_equal(password, AUTH_PASSWORD):
                    return _json_cookie_response(
                        self,
                        {"authenticated": True, "username": username},
                        cookie=_session_cookie(_create_session(username)),
                    )
                return _json_response(self, {"error": "用户名或密码错误"}, status=401)
            if parsed.path == "/api/logout":
                return _json_cookie_response(
                    self,
                    {"authenticated": False},
                    cookie=_clear_session_cookie(),
                )

            _json_response(self, {"error": "Not found"}, status=404)
        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=400)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), TradeWebHandler)
    print(f"Trade dashboard running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
