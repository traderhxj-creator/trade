import json
import os
import secrets
import time
from dataclasses import asdict
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


STATIC_DIR = Path(__file__).with_name("web_static")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
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
    try:
        return float(params.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def _int(params: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(params.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


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


def list_csv_files() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return [
        str(path.relative_to(PROJECT_ROOT))
        for path in sorted(DATA_DIR.glob("*.csv"))
    ]


def run_backtest_from_params(params: dict[str, list[str]]) -> dict:
    from trade.backtester import Backtester
    from trade.data.loader import load_price_csv
    from trade.models import BacktestConfig
    from trade.strategies import MovingAverageCrossStrategy

    data_path = _safe_data_path(params.get("data", ["data/sample_prices.csv"])[0])
    short_window = _int(params, "short_window", 20)
    long_window = _int(params, "long_window", 60)

    prices = load_price_csv(data_path)
    strategy = MovingAverageCrossStrategy(short_window=short_window, long_window=long_window)
    config = BacktestConfig(
        initial_cash=_float(params, "cash", 100_000.0),
        commission_rate=_float(params, "commission_rate", 0.0003),
        slippage_rate=_float(params, "slippage_rate", 0.0002),
    )

    frame, result = Backtester(config).run(prices, strategy)
    chart_frame = frame.reset_index()

    return {
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
            "data": str(data_path.relative_to(PROJECT_ROOT)),
            "rows": len(frame),
            "short_window": short_window,
            "long_window": long_window,
        },
    }


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
