/**
 * 日报系统 API 服务
 * 提供日报、动物详情、诊疗记录、饲养记录等接口
 */

const app = getApp();

class DailyReportService {
  constructor() {
    this.baseUrl = '/mp';
  }

  /**
   * 获取日报列表
   * @param {Object} params - 查询参数
   * @param {string} params.shedId - 圈舍ID
   * @param {string} params.startDate - 开始日期 (YYYY-MM-DD)
   * @param {string} params.endDate - 结束日期 (YYYY-MM-DD)
   * @param {number} params.page - 页码
   * @param {number} params.pageSize - 每页数量
   */
  async getDailyReports(params = {}) {
    const { shedId, startDate, endDate, page = 1, pageSize = 7 } = params;
    const queryParams = new URLSearchParams();
    
    if (shedId) queryParams.append('shed_id', shedId);
    if (startDate) queryParams.append('start_date', startDate);
    if (endDate) queryParams.append('end_date', endDate);
    queryParams.append('page', page);
    queryParams.append('page_size', pageSize);

    return app.request({
      url: `${this.baseUrl}/daily-reports?${queryParams.toString()}`,
      method: 'GET'
    });
  }

  /**
   * 获取单日报详情
   * @param {string} reportId - 日报ID
   */
  async getDailyReportDetail(reportId) {
    return app.request({
      url: `${this.baseUrl}/daily-reports/${reportId}`,
      method: 'GET'
    });
  }

  /**
   * 获取动物基础信息
   * @param {string} animalId - 动物ID
   */
  async getAnimalInfo(animalId) {
    return app.request({
      url: `${this.baseUrl}/animals/${animalId}`,
      method: 'GET'
    });
  }

  /**
   * 获取动物每日数据看板
   * @param {string} animalId - 动物ID
   * @param {string} date - 日期 (YYYY-MM-DD)
   */
  async getAnimalDashboard(animalId, date) {
    const queryParams = new URLSearchParams();
    if (date) queryParams.append('date', date);

    return app.request({
      url: `${this.baseUrl}/animals/${animalId}/dashboard?${queryParams.toString()}`,
      method: 'GET'
    });
  }

  /**
   * 获取动物诊疗记录
   * @param {string} animalId - 动物ID
   * @param {Object} params - 查询参数
   */
  async getMedicalRecords(animalId, params = {}) {
    const { status, page = 1, pageSize = 10 } = params;
    const queryParams = new URLSearchParams();
    
    if (status) queryParams.append('status', status);
    queryParams.append('page', page);
    queryParams.append('page_size', pageSize);

    return app.request({
      url: `${this.baseUrl}/animals/${animalId}/medical-records?${queryParams.toString()}`,
      method: 'GET'
    });
  }

  /**
   * 获取动物饲养记录
   * @param {string} animalId - 动物ID
   * @param {string} date - 日期 (YYYY-MM-DD)
   */
  async getFeedingRecords(animalId, date) {
    const queryParams = new URLSearchParams();
    if (date) queryParams.append('date', date);

    return app.request({
      url: `${this.baseUrl}/animals/${animalId}/feeding-records?${queryParams.toString()}`,
      method: 'GET'
    });
  }

  /**
   * 添加饲养/诊疗记录
   * @param {string} animalId - 动物ID
   * @param {Object} data - 记录数据
   * @param {string} data.type - 记录类型: feeding, medical, observation
   * @param {string} data.content - 文本内容
   * @param {Array} data.images - 图片URL列表
   * @param {string} data.voiceUrl - 语音URL
   * @param {Object} data.metadata - 额外元数据
   */
  async addRecord(animalId, data) {
    return app.request({
      url: `${this.baseUrl}/animals/${animalId}/records`,
      method: 'POST',
      data
    });
  }

  /**
   * 上传图片
   * @param {string} filePath - 本地图片路径
   */
  async uploadImage(filePath) {
    const token = app.globalData.token;
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${app.globalData.apiBaseUrl}${this.baseUrl}/upload/image`,
        filePath,
        name: 'file',
        header: {
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        success: (res) => {
          if (res.statusCode === 200) {
            const data = JSON.parse(res.data);
            resolve(data);
          } else {
            reject(new Error('Upload failed'));
          }
        },
        fail: reject
      });
    });
  }

  /**
   * 上传语音
   * @param {string} filePath - 本地语音文件路径
   */
  async uploadVoice(filePath) {
    const token = app.globalData.token;
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${app.globalData.apiBaseUrl}${this.baseUrl}/upload/voice`,
        filePath,
        name: 'file',
        header: {
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        success: (res) => {
          if (res.statusCode === 200) {
            const data = JSON.parse(res.data);
            resolve(data);
          } else {
            reject(new Error('Upload failed'));
          }
        },
        fail: reject
      });
    });
  }

  /**
   * 获取圈舍动物列表
   * @param {string} shedId - 圈舍ID
   */
  async getShedAnimals(shedId) {
    return app.request({
      url: `${this.baseUrl}/sheds/${shedId}/animals`,
      method: 'GET'
    });
  }

  /**
   * 更新记录完成状态
   * @param {string} recordId - 记录ID
   * @param {boolean} completed - 是否完成
   */
  async updateRecordStatus(recordId, completed) {
    return app.request({
      url: `${this.baseUrl}/records/${recordId}/status`,
      method: 'PUT',
      data: { completed }
    });
  }
}

module.exports = new DailyReportService();
