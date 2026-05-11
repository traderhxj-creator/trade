App({
  globalData: {
    sessionCookie: wx.getStorageSync("tradeSessionCookie") || "",
  },

  setSessionCookie(cookie) {
    this.globalData.sessionCookie = cookie || "";
    if (cookie) {
      wx.setStorageSync("tradeSessionCookie", cookie);
    } else {
      wx.removeStorageSync("tradeSessionCookie");
    }
  },
});
