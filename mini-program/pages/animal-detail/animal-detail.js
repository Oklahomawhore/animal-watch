// pages/animal-detail/animal-detail.js
const app = getApp();
const dailyReportService = require('../../services/dailyReport');
const { formatDate, formatAge, getHealthStatusColor, getHealthStatusText, getRemainingDays, showLoading, hideLoading } = require('../../utils/util');

Page({
  data: {
    animalId: null,
    currentDate: formatDate(new Date()),
    loading: true,
    
    // 动物基础信息
    animalInfo: null,
    
    // 数据看板
    dashboard: {
      activityScore: 0,
      activityLevel: '',
      feedRemaining: 0,
      waterIntake: 0,
      eatingTimes: 0,
      restQuality: 0
    },
    
    // 诊疗记录
    medicalRecords: [],
    
    // 饲养记录
    feedingRecords: {
      today: [],
      tomorrow: []
    },
    
    // 活动趋势数据
    activityTrend: {
      dates: [],
      values: []
    },
    
    // 当前选中的标签页
    activeTab: 'overview', // overview, medical, feeding
    
    // 时间范围
    timeRange: 'week' // day, week, month
  },

  onLoad(options) {
    const { animalId, date } = options;
    this.setData({
      animalId: animalId || 'A001',
      currentDate: date || formatDate(new Date())
    });
    
    this.loadAllData();
  },

  onPullDownRefresh() {
    this.loadAllData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReady() {
    this.initChart();
  },

  // 加载所有数据
  async loadAllData() {
    this.setData({ loading: true });
    
    try {
      await Promise.all([
        this.loadAnimalInfo(),
        this.loadDashboard(),
        this.loadMedicalRecords(),
        this.loadFeedingRecords()
      ]);
      
      this.setData({ loading: false });
      
      // 渲染图表
      setTimeout(() => {
        this.renderActivityChart();
      }, 100);
    } catch (error) {
      console.error('加载数据失败:', error);
      this.setData({ loading: false });
      this.loadMockData();
    }
  },

  // 加载动物基础信息
  async loadAnimalInfo() {
    const { animalId } = this.data;
    
    try {
      const res = await dailyReportService.getAnimalInfo(animalId);
      
      if (res.data) {
        const info = res.data;
        this.setData({
          animalInfo: {
            id: info.id,
            earTag: info.ear_tag,
            name: info.name || info.ear_tag,
            gender: info.gender,
            genderText: info.gender === 'male' ? '公' : '母',
            age: info.age_months,
            ageText: formatAge(info.age_months),
            birthDate: info.birth_date,
            healthStatus: info.health_status || 'healthy',
            healthStatusText: getHealthStatusText(info.health_status),
            healthStatusColor: getHealthStatusColor(info.health_status),
            weight: info.weight,
            shedName: info.shed_name,
            photo: info.photo_url || '/images/default-animal.png'
          }
        });
      }
    } catch (error) {
      console.error('加载动物信息失败:', error);
      throw error;
    }
  },

  // 加载数据看板
  async loadDashboard() {
    const { animalId, currentDate } = this.data;
    
    try {
      const res = await dailyReportService.getAnimalDashboard(animalId, currentDate);
      
      if (res.data) {
        const data = res.data;
        this.setData({
          dashboard: {
            activityScore: data.activity_score || 0,
            activityLevel: this.getActivityLevelText(data.activity_score),
            feedRemaining: data.feed_remaining || 0,
            waterIntake: data.water_intake || 0,
            eatingTimes: data.eating_times || 0,
            restQuality: data.rest_quality || 0
          },
          activityTrend: {
            dates: data.trend_dates || [],
            values: data.trend_values || []
          }
        });
      }
    } catch (error) {
      console.error('加载数据看板失败:', error);
      throw error;
    }
  },

  // 加载诊疗记录
  async loadMedicalRecords() {
    const { animalId } = this.data;
    
    try {
      const res = await dailyReportService.getMedicalRecords(animalId, {
        status: 'active',
        pageSize: 5
      });
      
      if (res.data) {
        const records = res.data.map(record => ({
          id: record.id,
          diagnosis: record.diagnosis,
          diagnosisDate: record.diagnosis_date,
          status: record.status,
          statusText: this.getMedicalStatusText(record.status),
          medicines: record.medicines || [],
          remainingDays: getRemainingDays(record.end_date),
          veterinarian: record.veterinarian_name,
          notes: record.notes
        }));
        
        this.setData({ medicalRecords: records });
      }
    } catch (error) {
      console.error('加载诊疗记录失败:', error);
      throw error;
    }
  },

  // 加载饲养记录
  async loadFeedingRecords() {
    const { animalId, currentDate } = this.data;
    
    try {
      const res = await dailyReportService.getFeedingRecords(animalId, currentDate);
      
      if (res.data) {
        this.setData({
          feedingRecords: {
            today: (res.data.today || []).map(item => ({
              id: item.id,
              content: item.content,
              type: item.type,
              completed: item.completed,
              completedAt: item.completed_at,
              completedBy: item.completed_by_name
            })),
            tomorrow: (res.data.tomorrow || []).map(item => ({
              id: item.id,
              content: item.content,
              type: item.type
            }))
          }
        });
      }
    } catch (error) {
      console.error('加载饲养记录失败:', error);
      throw error;
    }
  },

  // 获取活动等级文字
  getActivityLevelText(score) {
    if (score >= 80) return '活跃';
    if (score >= 60) return '正常';
    if (score >= 40) return '偏低';
    return '异常';
  },

  // 获取诊疗状态文字
  getMedicalStatusText(status) {
    const texts = {
      active: '治疗中',
      completed: '已康复',
      chronic: '慢性病'
    };
    return texts[status] || '未知';
  },

  // 初始化图表
  initChart() {
    this.ecComponent = this.selectComponent('#activity-chart');
  },

  // 渲染活动趋势图
  renderActivityChart() {
    const { activityTrend, timeRange } = this.data;
    
    let data = activityTrend.values.length > 0 ? activityTrend.values : [65, 72, 68, 75, 80, 78, 82];
    let categories = activityTrend.dates.length > 0 ? activityTrend.dates : 
      ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

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

  // 切换标签页
  switchTab(e) {
    const { tab } = e.currentTarget.dataset;
    this.setData({ activeTab: tab });
  },

  // 切换时间范围
  switchTimeRange(e) {
    const { range } = e.currentTarget.dataset;
    this.setData({ timeRange: range }, () => {
      this.loadDashboard().then(() => {
        this.renderActivityChart();
      });
    });
  },

  // 更新记录完成状态
  async toggleRecordComplete(e) {
    const { recordId, completed } = e.currentTarget.dataset;
    
    try {
      await dailyReportService.updateRecordStatus(recordId, !completed);
      
      // 刷新饲养记录
      this.loadFeedingRecords();
      
      wx.showToast({
        title: completed ? '已取消' : '已完成',
        icon: 'success'
      });
    } catch (error) {
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      });
    }
  },

  // 添加记录
  goToAddRecord() {
    const { animalId } = this.data;
    wx.navigateTo({
      url: `/pages/add-record/add-record?animalId=${animalId}`
    });
  },

  // 返回
  goBack() {
    wx.navigateBack();
  },

  // 加载模拟数据
  loadMockData() {
    const mockAnimalInfo = {
      id: 'A001',
      earTag: 'LS-2024-001',
      name: '小白',
      gender: 'female',
      genderText: '母',
      age: 18,
      ageText: '1岁6个月',
      birthDate: '2023-09-01',
      healthStatus: 'healthy',
      healthStatusText: '健康',
      healthStatusColor: '#4CAF50',
      weight: 8.5,
      shedName: '1号圈舍',
      photo: '/images/default-animal.png'
    };

    const mockDashboard = {
      activityScore: 85,
      activityLevel: '活跃',
      feedRemaining: 10,
      waterIntake: 3.2,
      eatingTimes: 4,
      restQuality: 88
    };

    const mockMedicalRecords = [
      {
        id: 'M001',
        diagnosis: '轻微消化不良',
        diagnosisDate: '2026-03-20',
        status: 'active',
        statusText: '治疗中',
        medicines: [
          { name: '益生菌', dosage: '每日1次', unit: '袋' },
          { name: '消化酶', dosage: '每日2次', unit: '片' }
        ],
        remainingDays: 5,
        veterinarian: '李医生',
        notes: '注意观察进食情况'
      }
    ];

    const mockFeedingRecords = {
      today: [
        { id: 'F001', content: '早晨喂食精料 200g', type: 'feeding', completed: true, completedAt: '08:30', completedBy: '张师傅' },
        { id: 'F002', content: '检查饮水器', type: 'inspection', completed: true, completedAt: '09:00', completedBy: '张师傅' },
        { id: 'F003', content: '下午补充青饲料', type: 'feeding', completed: false }
      ],
      tomorrow: [
        { id: 'F004', content: '驱虫药投放', type: 'medical' },
        { id: 'F005', content: '圈舍消毒', type: 'maintenance' }
      ]
    };

    this.setData({
      animalInfo: mockAnimalInfo,
      dashboard: mockDashboard,
      medicalRecords: mockMedicalRecords,
      feedingRecords: mockFeedingRecords,
      activityTrend: {
        dates: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        values: [75, 78, 72, 80, 85, 82, 85]
      }
    });

    setTimeout(() => {
      this.renderActivityChart();
    }, 100);
  }
});
