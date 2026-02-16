// pages/monitor/monitor.js
Page({
  data: {
    currentShed: 'all',
    shedList: [
      { id: 1, name: '一号圈舍' },
      { id: 2, name: '二号圈舍' },
      { id: 3, name: '三号圈舍' },
      { id: 4, name: '四号圈舍' }
    ],
    cameraList: [
      {
        id: 1,
        name: '摄像头-01',
        shedId: 1,
        status: 'online',
        statusText: '在线',
        animalCount: 5,
        snapshotUrl: ''
      },
      {
        id: 2,
        name: '摄像头-02',
        shedId: 1,
        status: 'online',
        statusText: '在线',
        animalCount: 6,
        snapshotUrl: ''
      },
      {
        id: 3,
        name: '摄像头-03',
        shedId: 2,
        status: 'alert',
        statusText: '异常',
        animalCount: 4,
        alertType: '倒地检测',
        snapshotUrl: ''
      },
      {
        id: 4,
        name: '摄像头-04',
        shedId: 2,
        status: 'online',
        statusText: '在线',
        animalCount: 7,
        snapshotUrl: ''
      }
    ]
  },

  onLoad(options) {
    if (options.shedId) {
      this.setData({ currentShed: parseInt(options.shedId) });
    }
  },

  // 选择圈舍
  selectShed(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ currentShed: id });
    this.filterCameras(id);
  },

  // 筛选摄像头
  filterCameras(shedId) {
    // 实际项目中根据 shedId 筛选
    // 这里使用模拟数据
  },

  // 打开摄像头详情
  openCameraDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/monitor/detail?id=${id}`
    });
  },

  // 截图
  takeSnapshot() {
    wx.showToast({ title: '截图已保存', icon: 'success' });
  },

  // 开始录像
  startRecord() {
    wx.showToast({ title: '开始录像', icon: 'none' });
  },

  // 打开对讲
  openIntercom() {
    wx.showToast({ title: '对讲功能开发中', icon: 'none' });
  },

  // 打开设置
  openSettings() {
    wx.navigateTo({
      url: '/pages/profile/profile'
    });
  }
});
