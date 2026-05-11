const { baseUrl } = require("../../config");

const app = getApp();

const defaultForm = {
  username: "admin",
  password: "trade123",
  data: "data/sample_prices.csv",
  cash: "100000",
  short_window: "20",
  long_window: "60",
  commission_rate: "0.0003",
  slippage_rate: "0.0002",
};

const metricLabels = {
  final_equity: "期末净值",
  total_return: "总收益",
  annual_return: "年化收益",
  max_drawdown: "最大回撤",
  sharpe_ratio: "夏普比率",
  trades: "交易次数",
};

function formatMoney(value) {
  const number = Number(value || 0);
  return number.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatPct(value) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`;
}

function normalizePath(path, params) {
  const query = Object.keys(params || {})
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join("&");
  return `${baseUrl}${path}${query ? `?${query}` : ""}`;
}

Page({
  data: {
    baseUrl,
    form: defaultForm,
    authenticated: false,
    username: "",
    datasets: [],
    metrics: [],
    metaText: "",
    latestRows: [],
    status: "请先连接后端服务",
    loading: false,
  },

  onLoad() {
    this.checkSession();
  },

  request(path, options = {}) {
    const header = {
      "Content-Type": "application/json",
      ...(options.header || {}),
    };
    if (app.globalData.sessionCookie) {
      header.Cookie = app.globalData.sessionCookie;
    }

    return new Promise((resolve, reject) => {
      wx.request({
        url: normalizePath(path, options.params),
        method: options.method || "GET",
        data: options.data,
        header,
        success: (response) => {
          const setCookie = response.header["Set-Cookie"] || response.header["set-cookie"];
          if (setCookie) {
            app.setSessionCookie(setCookie.split(";")[0]);
          }
          if (response.statusCode >= 400) {
            const message = response.data && response.data.error ? response.data.error : "请求失败";
            reject(new Error(message));
            return;
          }
          resolve(response.data);
        },
        fail: () => reject(new Error("无法连接后端服务")),
      });
    });
  },

  async checkSession() {
    try {
      const payload = await this.request("/api/session");
      if (payload.authenticated) {
        this.setData({
          authenticated: true,
          username: payload.username,
          status: "已连接",
        });
        await this.loadDatasets();
      } else {
        this.setData({ status: "请登录后端账号" });
      }
    } catch (error) {
      this.setData({ status: error.message });
    }
  },

  onInput(event) {
    const key = event.currentTarget.dataset.key;
    this.setData({
      [`form.${key}`]: event.detail.value,
    });
  },

  onDatasetChange(event) {
    const index = Number(event.detail.value);
    const data = this.data.datasets[index];
    this.setData({
      "form.data": data,
    });
  },

  async login() {
    this.setData({ loading: true, status: "登录中..." });
    try {
      const payload = await this.request("/api/login", {
        method: "POST",
        data: {
          username: this.data.form.username,
          password: this.data.form.password,
        },
      });
      this.setData({
        authenticated: true,
        username: payload.username,
        status: "登录成功",
      });
      await this.loadDatasets();
      await this.runBacktest();
    } catch (error) {
      this.setData({ status: error.message });
    } finally {
      this.setData({ loading: false });
    }
  },

  async logout() {
    try {
      await this.request("/api/logout", { method: "POST" });
    } catch (error) {
      this.setData({ status: error.message });
    }
    app.setSessionCookie("");
    this.setData({
      authenticated: false,
      username: "",
      metrics: [],
      metaText: "",
      latestRows: [],
      status: "已退出",
    });
  },

  async loadDatasets() {
    const payload = await this.request("/api/datasets");
    const datasets = payload.datasets || [];
    this.setData({
      datasets,
      "form.data": datasets[0] || this.data.form.data,
    });
  },

  buildBacktestParams() {
    return {
      data: this.data.form.data,
      cash: this.data.form.cash,
      short_window: this.data.form.short_window,
      long_window: this.data.form.long_window,
      commission_rate: this.data.form.commission_rate,
      slippage_rate: this.data.form.slippage_rate,
    };
  },

  renderResult(payload) {
    const result = payload.result || {};
    const metrics = [
      { label: metricLabels.final_equity, value: formatMoney(result.final_equity) },
      { label: metricLabels.total_return, value: formatPct(result.total_return) },
      { label: metricLabels.annual_return, value: formatPct(result.annual_return) },
      { label: metricLabels.max_drawdown, value: formatPct(result.max_drawdown) },
      { label: metricLabels.sharpe_ratio, value: Number(result.sharpe_ratio || 0).toFixed(2) },
      { label: metricLabels.trades, value: String(result.trades || 0) },
    ];
    const meta = payload.meta || {};
    const series = payload.series || [];
    const latestRows = series.slice(-6).reverse().map((row) => ({
      date: row.date,
      close: formatMoney(row.close),
      equity: formatMoney(row.equity),
      drawdown: formatPct(row.drawdown),
      signal: row.signal > 0 ? "买入" : row.signal < 0 ? "卖出" : "观望",
    }));

    this.setData({
      metrics,
      latestRows,
      metaText: `${meta.data || "-"} · ${meta.rows || 0} 行 · MA(${meta.short_window || "-"}, ${meta.long_window || "-"})`,
      status: "回测完成",
    });
  },

  async runBacktest() {
    if (!this.data.authenticated) {
      this.setData({ status: "请先登录" });
      return;
    }
    this.setData({ loading: true, status: "回测运行中..." });
    try {
      const payload = await this.request("/api/backtest", {
        params: this.buildBacktestParams(),
      });
      this.renderResult(payload);
    } catch (error) {
      this.setData({ status: error.message });
    } finally {
      this.setData({ loading: false });
    }
  },
});
