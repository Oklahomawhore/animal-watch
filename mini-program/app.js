// app.js
App({
  globalData: {
    userInfo: null,
    // 后端服务地址配置
    // 开发环境: http://localhost:5001/api/v2 (Flask后端)
    // 测试环境: http://47.111.141.55:5001/api/v2
    // 生产环境: https://ajppt.cn/linshe/api/v2
    apiBaseUrl: 'https://ajppt.cn/linshe/api/v2',
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
