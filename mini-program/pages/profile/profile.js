// pages/profile/profile.js
Page({
  data: {
    userInfo: {
      name: '张养殖场',
      role: '管理员',
      location: '陕西省凤县'
    },
    stats: {
      monthlyAlerts: 12,
      handleRate: '100%',
      avgResponse: '5分钟'
    }
  },

  onLoad() {
    this.loadUserInfo();
  },

  // 加载用户信息
  loadUserInfo() {
    // 实际项目中调用 API
  },

  // 消息通知
  goToNotifications() {
    wx.navigateTo({ url: '/pages/profile/notifications' });
  },

  // 设备管理
  goToDevices() {
    wx.navigateTo({ url: '/pages/profile/devices' });
  },

  // 人员管理
  goToStaff() {
    wx.showToast({ title: '功能开发中', icon: 'none' });
  },

  // 数据报表
  goToReports() {
    wx.navigateTo({ url: '/pages/profile/reports' });
  },

  // 帮助中心
  goToHelp() {
    wx.navigateTo({ url: '/pages/profile/help' });
  },

  // 关于我们
  goToAbout() {
    wx.navigateTo({ url: '/pages/profile/about' });
  },

  // 退出登录
  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync();
          wx.reLaunch({ url: '/pages/login/login' });
        }
      }
    });
  }
});
