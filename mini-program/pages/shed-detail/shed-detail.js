// pages/shed-detail/shed-detail.js
const app = getApp();

Page({
  data: {
    shedId: null,
    shedInfo: {},
    loading: true,
    
    // 实时数据
    realtimeData: {
      activityScore: 78,
      activityLevel: '活跃',
      eatingStatus: '进食中',
      lastEatingTime: '10分钟前',
      animalCount: 32,
      onlineCameras: 4,
      totalCameras: 4
    },
    
    // 活动趋势数据（24小时）
    activityTrend: {
      hours: ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', 
              '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'],
      values: [15, 12, 10, 25, 45, 62, 58, 65, 70, 55, 40, 25]
    },
    
    // 吃草记录
    eatingRecords: [
      { time: '08:30', duration: '15分钟', amount: '正常', status: 'normal' },
      { time: '12:45', duration: '22分钟', amount: '较多', status: 'good' },
      { time: '16:20', duration: '8分钟', amount: '较少', status: 'warning' }
    ],
    
    // 当前选中的时间范围
    timeRange: 'day', // day, week, month
    
    // 异常记录
    alerts: [
      { time: '06:15', type: 'activity_low', message: '活动量偏低', level: 'warning' },
      { time: '昨天 14:30', type: 'eating_abnormal', message: '进食时间异常', level: 'info' }
    ]
  },

  onLoad(options) {
    const { shedId } = options;
    this.setData({ shedId });
    this.loadShedDetail(shedId);
    this.initChart();
  },

  onReady() {
    this.renderActivityChart();
  },

  // 加载圈舍详情
  async loadShedDetail(shedId) {
    this.setData({ loading: true });
    
    try {
      // 实际项目中调用 API
      // const data = await app.request({ url: `/sheds/${shedId}/detail` });
      
      // 模拟数据
      await new Promise(resolve => setTimeout(resolve, 500));
      
      this.setData({
        shedInfo: {
          id: shedId,
          name: `${shedId}号圈舍`,
          temperature: 18,
          humidity: 65,
          area: '120㎡',
          manager: '张师傅'
        },
        loading: false
      });
    } catch (error) {
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
      this.setData({ loading: false });
    }
  },

  // 初始化图表
  initChart() {
    // 引入 echarts
    this.ecComponent = this.selectComponent('#activity-chart');
  },

  // 渲染活动趋势图
  renderActivityChart() {
    const { activityTrend, timeRange } = this.data;
    
    // 根据时间范围调整数据
    let data = activityTrend.values;
    let categories = activityTrend.hours;
    
    if (timeRange === 'week') {
      categories = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
      data = [45, 52, 48, 55, 60, 58, 50];
    } else if (timeRange === 'month') {
      categories = ['1日', '5日', '10日', '15日', '20日', '25日', '30日'];
      data = [50, 55, 48, 62, 58, 52, 55];
    }

    const option = {
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLine: { lineStyle: { color: '#E0E0E0' } },
        axisLabel: { color: '#666', fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#F0F0F0' } },
        axisLabel: { color: '#666', fontSize: 10 }
      },
      series: [{
        data: data,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#4CAF50',
          width: 2
        },
        itemStyle: {
          color: '#4CAF50',
          borderColor: '#fff',
          borderWidth: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(76, 175, 80, 0.3)' },
              { offset: 1, color: 'rgba(76, 175, 80, 0.05)' }
            ]
          }
        }
      }]
    };

    // 使用 echarts-for-weixin
    if (this.ecComponent) {
      this.ecComponent.init((canvas, width, height, dpr) => {
        const chart = echarts.init(canvas, null, {
          width: width,
          height: height,
          devicePixelRatio: dpr
        });
        chart.setOption(option);
        return chart;
      });
    }
  },

  // 切换时间范围
  switchTimeRange(e) {
    const { range } = e.currentTarget.dataset;
    this.setData({ timeRange: range }, () => {
      this.renderActivityChart();
    });
  },

  // 查看实时监控
  goToLiveMonitor() {
    wx.navigateTo({
      url: `/pages/monitor/monitor?shedId=${this.data.shedId}&mode=live`
    });
  },

  // 查看所有告警
  goToAlerts() {
    wx.switchTab({
      url: '/pages/alerts/alerts'
    });
  },

  // 刷新数据
  onPullDownRefresh() {
    this.loadShedDetail(this.data.shedId).finally(() => {
      wx.stopPullDownRefresh();
    });
  }
});
