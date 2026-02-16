// pages/alerts/alerts.js
Page({
  data: {
    currentFilter: 'all',
    alertList: [
      {
        id: 1,
        type: '活动异常检测',
        level: 'urgent',
        time: '10:23',
        shedName: '一号圈舍',
        cameraName: 'CAM-03',
        description: '灵麝 #128 活动量骤降，持续30分钟',
        status: 'unhandled',
        statusText: '未处理'
      },
      {
        id: 2,
        type: '离线提醒',
        level: 'warning',
        time: '09:45',
        shedName: '二号圈舍',
        cameraName: 'CAM-01',
        description: '设备离线超过5分钟',
        status: 'handled',
        statusText: '已恢复'
      },
      {
        id: 3,
        type: '活动量偏低',
        level: 'warning',
        time: '08:12',
        shedName: '三号圈舍',
        cameraName: 'CAM-05',
        description: '3只灵麝今日活动量低于平均值',
        status: 'handled',
        statusText: '已处理'
      }
    ]
  },

  onLoad() {
    this.loadAlerts();
  },

  // 切换筛选
  switchFilter(e) {
    const { filter } = e.currentTarget.dataset;
    this.setData({ currentFilter: filter });
    this.loadAlerts();
  },

  // 加载报警数据
  loadAlerts() {
    // 实际项目中调用 API
    // const { currentFilter } = this.data;
    // app.request({ url: `/alerts?filter=${currentFilter}` });
  },

  // 处理报警
  handleAlert(e) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '确认处理',
      content: '确定要标记此报警为已处理吗？',
      success: (res) => {
        if (res.confirm) {
          // 调用 API 更新状态
          wx.showToast({ title: '处理成功', icon: 'success' });
        }
      }
    });
  },

  // 查看详情
  viewDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/alerts/detail?id=${id}`
    });
  }
});
