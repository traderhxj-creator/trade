const form = document.querySelector("#backtest-form");
const loginForm = document.querySelector("#login-form");
const authScreen = document.querySelector("#auth-screen");
const loginStatusEl = document.querySelector("#login-status");
const logoutButton = document.querySelector("#logout-button");
const sessionUserEl = document.querySelector("#session-user");
const statusEl = document.querySelector("#status");
const metricsEl = document.querySelector("#metrics");
const metaEl = document.querySelector("#meta");
const dataSelect = document.querySelector("#data");
const equityCanvas = document.querySelector("#equity-chart");
const drawdownCanvas = document.querySelector("#drawdown-chart");

const pct = (value) => `${(value * 100).toFixed(2)}%`;
const money = (value) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);

function setAuthenticated(username) {
  document.body.classList.toggle("locked", !username);
  authScreen.classList.toggle("hidden", Boolean(username));
  sessionUserEl.textContent = username ? `已授权 · ${username}` : "未授权";
}

function renderMetrics(result) {
  const items = [
    ["期末净值", money(result.final_equity)],
    ["总收益", pct(result.total_return)],
    ["年化收益", pct(result.annual_return)],
    ["最大回撤", pct(result.max_drawdown)],
    ["夏普比率", result.sharpe_ratio.toFixed(2)],
    ["交易次数", result.trades],
  ];

  metricsEl.innerHTML = items
    .map(([label, value]) => `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`)
    .join("");
}

function normalize(values, height, padding) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values.map((value) => height - padding - ((value - min) / range) * (height - padding * 2));
}

function drawLineChart(canvas, series, definitions) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = 44;
  ctx.clearRect(0, 0, width, height);

  const grid = ctx.createLinearGradient(0, 0, width, height);
  grid.addColorStop(0, "rgba(78, 212, 255, 0.22)");
  grid.addColorStop(1, "rgba(139, 92, 246, 0.08)");
  ctx.strokeStyle = grid;
  ctx.lineWidth = 1;
  for (let x = padding; x <= width - padding; x += 84) {
    ctx.beginPath();
    ctx.moveTo(x, padding);
    ctx.lineTo(x, height - padding);
    ctx.stroke();
  }
  for (let y = padding; y <= height - padding; y += 58) {
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(164, 241, 255, 0.42)";
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, height - padding);
  ctx.lineTo(width - padding, height - padding);
  ctx.stroke();

  definitions.forEach((def) => {
    const values = series.map((row) => row[def.key]);
    const yValues = normalize(values, height, padding);
    const step = (width - padding * 2) / Math.max(series.length - 1, 1);

    ctx.beginPath();
    ctx.strokeStyle = def.color;
    ctx.lineWidth = def.width || 2;
    ctx.shadowColor = def.color;
    ctx.shadowBlur = 12;
    yValues.forEach((y, index) => {
      const x = padding + index * step;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;
  });

  const first = series[0]?.date || "";
  const last = series[series.length - 1]?.date || "";
  ctx.fillStyle = "#7dd3fc";
  ctx.font = "22px system-ui";
  ctx.fillText(first, padding, height - 12);
  ctx.textAlign = "right";
  ctx.fillText(last, width - padding, height - 12);
  ctx.textAlign = "left";
}

async function loadDatasets() {
  const response = await fetch("/api/datasets");
  const payload = await response.json();
  if (response.status === 401) {
    setAuthenticated(null);
    throw new Error("请先完成授权");
  }
  dataSelect.innerHTML = payload.datasets
    .map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)
    .join("");
}

async function runBacktest() {
  statusEl.textContent = "回测运行中...";
  const params = new URLSearchParams(new FormData(form));
  const response = await fetch(`/api/backtest?${params.toString()}`);
  const payload = await response.json();

  if (response.status === 401) {
    setAuthenticated(null);
    statusEl.textContent = "会话已失效，请重新授权";
    return;
  }

  if (!response.ok || payload.error) {
    statusEl.textContent = payload.error || "回测失败";
    return;
  }

  renderMetrics(payload.result);
  drawLineChart(equityCanvas, payload.series, [
    { key: "equity", color: "#22d3ee", width: 3 },
    { key: "close", color: "#f59e0b", width: 2 },
  ]);
  drawLineChart(drawdownCanvas, payload.series, [
    { key: "drawdown", color: "#fb7185", width: 3 },
  ]);
  metaEl.textContent = `${payload.meta.data} · ${payload.meta.rows} 行 · MA(${payload.meta.short_window}, ${payload.meta.long_window})`;
  statusEl.textContent = "回测完成";
}

async function bootstrap() {
  const response = await fetch("/api/session");
  const payload = await response.json();
  if (!payload.authenticated) {
    setAuthenticated(null);
    return;
  }
  setAuthenticated(payload.username);
  await loadDatasets();
  await runBacktest();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runBacktest();
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginStatusEl.textContent = "授权校验中...";
  const credentials = Object.fromEntries(new FormData(loginForm));
  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  const payload = await response.json();

  if (!response.ok || payload.error) {
    loginStatusEl.textContent = payload.error || "授权失败";
    return;
  }

  setAuthenticated(payload.username);
  loginStatusEl.textContent = "授权通过";
  await loadDatasets();
  await runBacktest();
});

logoutButton.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  setAuthenticated(null);
  statusEl.textContent = "会话已退出";
});

bootstrap().catch((error) => {
  statusEl.textContent = error.message;
  loginStatusEl.textContent = error.message;
});
