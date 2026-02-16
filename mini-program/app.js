// app.js
App({
  globalData: {
    userInfo: null,
    apiBaseUrl: 'https://api.linshe.com/v1', // 生产环境地址
    // apiBaseUrl: 'http://localhost:3000/v1', // 开发环境地址
    token: null
  },

  onLaunch() {
    // 检查登录状态
    this.checkLoginStatus();
    
    // 获取系统信息
    this.getSystemInfo();
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
    }
  },

  // 获取系统信息
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res;
      }
    });
  },

  // 全局请求方法
  request(options) {
    const { url, method = 'GET', data, header = {} } = options;
    const token = this.globalData.token;
    
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${this.globalData.apiBaseUrl}${url}`,
        method,
        data,
        header: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
          ...header
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else if (res.statusCode === 401) {
            // token 过期，跳转登录
            wx.navigateTo({ url: '/pages/login/login' });
            reject(new Error('Unauthorized'));
          } else {
            reject(new Error(res.data.message || 'Request failed'));
          }
        },
        fail: reject
      });
    });
  }
});
