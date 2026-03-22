/**
 * 工具函数集合
 */

/**
 * 格式化日期
 * @param {Date|string} date - 日期对象或字符串
 * @param {string} format - 格式模板，默认 'YYYY-MM-DD'
 */
function formatDate(date, format = 'YYYY-MM-DD') {
  const d = date instanceof Date ? date : new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}

/**
 * 获取相对日期描述
 * @param {string} dateStr - 日期字符串 (YYYY-MM-DD)
 */
function getRelativeDateDesc(dateStr) {
  const today = formatDate(new Date());
  const yesterday = formatDate(new Date(Date.now() - 86400000));
  const tomorrow = formatDate(new Date(Date.now() + 86400000));

  if (dateStr === today) return '今天';
  if (dateStr === yesterday) return '昨天';
  if (dateStr === tomorrow) return '明天';

  const date = new Date(dateStr);
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  return weekDays[date.getDay()];
}

/**
 * 获取最近7天的日期数组
 * @param {Date} centerDate - 中心日期，默认今天
 */
function getRecent7Days(centerDate = new Date()) {
  const dates = [];
  const center = new Date(centerDate);
  center.setHours(0, 0, 0, 0);

  // 获取中心日期前后3天，共7天
  for (let i = -3; i <= 3; i++) {
    const date = new Date(center);
    date.setDate(date.getDate() + i);
    dates.push({
      date: formatDate(date),
      day: date.getDate(),
      weekDay: ['日', '一', '二', '三', '四', '五', '六'][date.getDay()],
      isToday: i === 0
    });
  }

  return dates;
}

/**
 * 根据健康状态获取颜色
 * @param {string} status - 健康状态: healthy, warning, danger
 */
function getHealthStatusColor(status) {
  const colors = {
    healthy: '#4CAF50',  // 绿色
    warning: '#FFC107',  // 黄色
    danger: '#F44336',   // 红色
    unknown: '#9E9E9E'   // 灰色
  };
  return colors[status] || colors.unknown;
}

/**
 * 根据健康状态获取文字
 * @param {string} status - 健康状态
 */
function getHealthStatusText(status) {
  const texts = {
    healthy: '健康',
    warning: '需关注',
    danger: '异常',
    unknown: '未知'
  };
  return texts[status] || texts.unknown;
}

/**
 * 防抖函数
 * @param {Function} fn - 要执行的函数
 * @param {number} delay - 延迟时间(ms)
 */
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 节流函数
 * @param {Function} fn - 要执行的函数
 * @param {number} interval - 间隔时间(ms)
 */
function throttle(fn, interval = 300) {
  let lastTime = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
}

/**
 * 显示加载提示
 * @param {string} title - 提示文字
 */
function showLoading(title = '加载中...') {
  wx.showLoading({
    title,
    mask: true
  });
}

/**
 * 隐藏加载提示
 */
function hideLoading() {
  wx.hideLoading();
}

/**
 * 显示成功提示
 * @param {string} title - 提示文字
 * @param {number} duration - 持续时间
 */
function showSuccess(title = '操作成功', duration = 1500) {
  wx.showToast({
    title,
    icon: 'success',
    duration
  });
}

/**
 * 显示错误提示
 * @param {string} title - 提示文字
 */
function showError(title = '操作失败') {
  wx.showToast({
    title,
    icon: 'error'
  });
}

/**
 * 显示确认对话框
 * @param {Object} options - 配置选项
 */
function showConfirm(options) {
  const { title = '提示', content, confirmText = '确定', cancelText = '取消' } = options;
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmText,
      cancelText,
      success: (res) => {
        resolve(res.confirm);
      }
    });
  });
}

/**
 * 计算年龄（月）
 * @param {string} birthDate - 出生日期
 */
function calculateAge(birthDate) {
  const birth = new Date(birthDate);
  const now = new Date();
  const months = (now.getFullYear() - birth.getFullYear()) * 12 + 
                 (now.getMonth() - birth.getMonth());
  return months;
}

/**
 * 格式化年龄显示
 * @param {number} months - 月数
 */
function formatAge(months) {
  if (months < 12) {
    return `${months}个月`;
  }
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  if (remainingMonths === 0) {
    return `${years}岁`;
  }
  return `${years}岁${remainingMonths}个月`;
}

/**
 * 计算剩余天数
 * @param {string} endDate - 结束日期
 */
function getRemainingDays(endDate) {
  const end = new Date(endDate);
  const now = new Date();
  const diff = end - now;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

module.exports = {
  formatDate,
  getRelativeDateDesc,
  getRecent7Days,
  getHealthStatusColor,
  getHealthStatusText,
  debounce,
  throttle,
  showLoading,
  hideLoading,
  showSuccess,
  showError,
  showConfirm,
  calculateAge,
  formatAge,
  getRemainingDays
};
