// pages/daily-report/daily-report.js
const app = getApp();
const dailyReportService = require('../../services/dailyReport');
const { formatDate, getRecent7Days, getRelativeDateDesc, showLoading, hideLoading, showError } = require('../../utils/util');

Page({
  data: {
    shedId: null,
    shedName: '',
    loading: true,
    
    // 日期选择器数据
    dateList: [],
    currentDateIndex: 3, // 默认选中中间（今天）
    currentDate: formatDate(new Date()),
    
    // 日报数据
    dailyReport: null,
    
    // 动物列表
    animalList: [],
    
    // 统计数据
    statistics: {
      totalAnimals: 0,
      healthyCount: 0,
      warningCount: 0,
      dangerCount: 0,
      avgActivityScore: 0
    }
  },

  onLoad(options) {
    const { shedId, shedName } = options;
    this.setData({ 
      shedId: shedId || '1',
      shedName: shedName || '1号圈舍'
    });
    
    // 初始化日期列表
    this.initDateList();
    
    // 加载数据
    this.loadDailyReport();
    this.loadShedAnimals();
  },

  onPullDownRefresh() {
    Promise.all([
      this.loadDailyReport(),
      this.loadShedAnimals()
    ]).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 初始化日期列表（最近7天）
  initDateList() {
    const dateList = getRecent7Days();
    this.setData({ dateList });
  },

  // 加载日报数据
  async loadDailyReport() {
    const { shedId, currentDate } = this.data;
    
    try {
      showLoading();
      
      // 调用 API 获取日报数据
      const res = await dailyReportService.getDailyReports({
        shedId,
        startDate: currentDate,
        endDate: currentDate,
        pageSize: 1
      });

      if (res.data && res.data.length > 0) {
        const dailyReport = res.data[0];
        this.setData({
          dailyReport,
          statistics: this.calculateStatistics(dailyReport)
        });
      } else {
        // 如果没有数据，使用空状态
        this.setData({
          dailyReport: null,
          statistics: {
            totalAnimals: 0,
            healthyCount: 0,
            warningCount: 0,
            dangerCount: 0,
            avgActivityScore: 0
          }
        });
      }
      
      hideLoading();
      this.setData({ loading: false });
    } catch (error) {
      console.error('加载日报失败:', error);
      hideLoading();
      this.setData({ loading: false });
      
      // 使用模拟数据作为 fallback
      this.loadMockData();
    }
  },

  // 加载圈舍动物列表
  async loadShedAnimals() {
    const { shedId } = this.data;
    
    try {
      const res = await dailyReportService.getShedAnimals(shedId);
      
      if (res.data) {
        this.setData({
          animalList: res.data.map(animal => ({
            id: animal.id,
            earTag: animal.ear_tag,
            name: animal.name || animal.ear_tag,
            gender: animal.gender,
            age: animal.age_months,
            healthStatus: animal.health_status || 'healthy',
            activityScore: animal.activity_score || 85,
            feedRemaining: animal.feed_remaining || 10,
            waterIntake: animal.water_intake || 2.5
          }))
        });
      }
    } catch (error) {
      console.error('加载动物列表失败:', error);
      // 使用模拟数据
      this.setMockAnimalList();
    }
  },

  // 计算统计数据
  calculateStatistics(dailyReport) {
    const animals = dailyReport.animals || [];
    const total = animals.length;
    const healthy = animals.filter(a => a.health_status === 'healthy').length;
    const warning = animals.filter(a => a.health_status === 'warning').length;
    const danger = animals.filter(a => a.health_status === 'danger').length;
    const avgActivity = total > 0 
      ? Math.round(animals.reduce((sum, a) => sum + (a.activity_score || 0), 0) / total)
      : 0;

    return {
      totalAnimals: total,
      healthyCount: healthy,
      warningCount: warning,
      dangerCount: danger,
      avgActivityScore: avgActivity
    };
  },

  // 日期切换
  onDateChange(e) {
    const { index } = e.currentTarget.dataset;
    const { dateList } = this.data;
    
    this.setData({
      currentDateIndex: index,
      currentDate: dateList[index].date
    }, () => {
      this.loadDailyReport();
    });
  },

  // 日期滑动切换
  onDateSwipe(e) {
    const { current, source } = e.detail;
    if (source === 'touch') {
      const { dateList } = this.data;
      this.setData({
        currentDateIndex: current,
        currentDate: dateList[current].date
      }, () => {
        this.loadDailyReport();
      });
    }
  },

  // 查看动物详情
  goToAnimalDetail(e) {
    const { animalId } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/animal-detail/animal-detail?animalId=${animalId}&date=${this.data.currentDate}`
    });
  },

  // 添加记录
  goToAddRecord() {
    const { shedId, currentDate } = this.data;
    wx.navigateTo({
      url: `/pages/add-record/add-record?shedId=${shedId}&date=${currentDate}`
    });
  },

  // 返回圈舍详情
  goBack() {
    wx.navigateBack();
  },

  // 加载模拟数据（fallback）
  loadMockData() {
    const mockData = {
      date: this.data.currentDate,
      summary: {
        totalAnimals: 32,
        healthyCount: 28,
        warningCount: 3,
        dangerCount: 1,
        avgActivityScore: 82
      },
      highlights: [
        { type: 'good', text: '整体活动量正常' },
        { type: 'warning', text: '3号林麝进食量偏少' },
        { type: 'info', text: '今日完成驱虫记录' }
      ]
    };

    this.setData({
      dailyReport: mockData,
      statistics: mockData.summary
    });
    
    this.setMockAnimalList();
  },

  // 模拟动物列表
  setMockAnimalList() {
    const mockAnimals = [
      { id: 'A001', earTag: 'LS-2024-001', name: '小白', gender: 'female', age: 18, healthStatus: 'healthy', activityScore: 92, feedRemaining: 5, waterIntake: 3.2 },
      { id: 'A002', earTag: 'LS-2024-002', name: '大黄', gender: 'male', age: 24, healthStatus: 'healthy', activityScore: 88, feedRemaining: 8, waterIntake: 2.8 },
      { id: 'A003', earTag: 'LS-2024-003', name: '花花', gender: 'female', age: 12, healthStatus: 'warning', activityScore: 65, feedRemaining: 25, waterIntake: 1.5 },
      { id: 'A004', earTag: 'LS-2024-004', name: '小黑', gender: 'male', age: 30, healthStatus: 'healthy', activityScore: 85, feedRemaining: 10, waterIntake: 2.5 },
      { id: 'A005', earTag: 'LS-2024-005', name: '豆豆', gender: 'female', age: 8, healthStatus: 'danger', activityScore: 45, feedRemaining: 40, waterIntake: 0.8 }
    ];

    this.setData({ animalList: mockAnimals });
  }
});
