// pages/index/index.js
const app = getApp();

Page({
  data: {
    activeCount: 156,
    totalCount: 160,
    systemStatus: 'normal',
    statusText: '系统运行正常',
    loading: false,
    shedList: [
      {
        id: 1,
        name: '一号圈舍',
        temperature: 18,
        humidity: 65,
        animalCount: 32,
        status: 'normal',
        statusText: '正常',
        alertCount: 0
      },
      {
        id: 2,
        name: '二号圈舍',
        temperature: 19,
        humidity: 62,
        animalCount: 28,
        status: 'warning',
        statusText: '需关注',
        alertCount: 3,
        alertType: '活动偏低'
      },
      {
        id: 3,
        name: '三号圈舍',
        temperature: 17,
        humidity: 70,
        animalCount: 45,
        status: 'normal',
        statusText: '正常',
        alertCount: 0
      },
      {
        id: 4,
        name: '四号圈舍',
        temperature: 20,
        humidity: 58,
        animalCount: 51,
        status: 'normal',
        statusText: '正常',
        alertCount: 0
      }
    ]
  },

  onLoad() {
    this.loadData();
  },

  onPullDownRefresh() {
    this.loadData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 加载数据
  async loadData() {
    this.setData({ loading: true });
    
    try {
      // 实际项目中调用 API
      // const data = await app.request({ url: '/dashboard/summary' });
      // this.setData({ ...data });
      
      // 模拟数据加载
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  // 跳转到监控页面
  goToMonitor() {
    wx.switchTab({
      url: '/pages/monitor/monitor'
    });
  },

  // 跳转到报表页面
  goToReport() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    });
  },

  // 跳转到设备管理
  goToDevice() {
    wx.navigateTo({
      url: '/pages/profile/profile'
    });
  },

  // 跳转到圈舍详情
  goToShedDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/monitor/monitor?shedId=${id}`
    });
  }
});
