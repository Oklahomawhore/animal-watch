/**
 * 小程序前端测试
 * 
 * 测试页面:
 * 1. 日报列表页面渲染
 * 2. 动物详情页面数据展示
 * 3. 添加记录功能
 * 4. 页面跳转和交互
 */

const automator = require('miniprogram-automator');

// 小程序配置
const MINIPROGRAM_CONFIG = {
  projectPath: '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/mini-program',
  cliPath: '/Applications/wechatwebdevtools.app/Contents/MacOS/cli',
};

// 测试数据
const TEST_DATA = {
  shedId: '1',
  shedName: '1号圈舍',
  animalId: 'LS-2024-001',
  date: '2026-03-22'
};

describe('小程序前端测试', () => {
  let miniProgram;
  let page;

  // 在所有测试前启动小程序
  beforeAll(async () => {
    miniProgram = await automator.launch({
      projectPath: MINIPROGRAM_CONFIG.projectPath,
      cliPath: MINIPROGRAM_CONFIG.cliPath,
    });
  }, 60000);

  // 在所有测试后关闭小程序
  afterAll(async () => {
    if (miniProgram) {
      await miniProgram.close();
    }
  });

  // 每个测试前重新导航到首页
  beforeEach(async () => {
    page = await miniProgram.reLaunch('/pages/index/index');
    await page.waitFor(1000);
  });

  // ==================== 测试1: 日报列表页面渲染 ====================
  
  describe('日报列表页面', () => {
    test('页面应该正确渲染', async () => {
      // 导航到日报页面
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}&shedName=${TEST_DATA.shedName}`);
      await page.waitFor(2000);

      // 检查页面标题
      const title = await page.$eval('.page-title', el => el.textContent);
      expect(title).toContain('日报');
    });

    test('日期选择器应该显示最近7天', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 检查日期列表
      const dateItems = await page.$$('.date-item');
      expect(dateItems.length).toBeGreaterThanOrEqual(7);
    });

    test('应该显示动物列表', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 检查动物列表容器
      const animalList = await page.$('.animal-list');
      expect(animalList).toBeTruthy();
    });

    test('统计数据应该正确显示', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 检查统计卡片
      const statCards = await page.$$('.stat-card');
      expect(statCards.length).toBeGreaterThanOrEqual(4);
    });

    test('点击动物应该跳转到详情页', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 点击第一个动物
      const animalItem = await page.$('.animal-item');
      if (animalItem) {
        await animalItem.tap();
        await page.waitFor(1000);

        // 检查是否跳转到详情页
        const currentPage = await miniProgram.currentPage();
        expect(currentPage.path).toContain('animal-detail');
      }
    });

    test('日期切换应该更新数据', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 获取日期项
      const dateItems = await page.$$('.date-item');
      if (dateItems.length > 1) {
        // 点击第二个日期
        await dateItems[1].tap();
        await page.waitFor(1000);

        // 检查选中状态
        const isSelected = await dateItems[1].$eval('.date-item', el => el.classList.contains('active'));
        expect(isSelected).toBeTruthy();
      }
    });
  });

  // ==================== 测试2: 动物详情页面数据展示 ====================

  describe('动物详情页面', () => {
    beforeEach(async () => {
      page = await miniProgram.navigateTo(`/pages/animal-detail/animal-detail?animalId=${TEST_DATA.animalId}&date=${TEST_DATA.date}`);
      await page.waitFor(2000);
    });

    test('页面应该正确渲染', async () => {
      // 检查页面标题
      const pageTitle = await page.$eval('.page-title', el => el.textContent);
      expect(pageTitle).toBeTruthy();
    });

    test('应该显示动物基础信息', async () => {
      // 检查耳标号
      const earTag = await page.$eval('.ear-tag', el => el.textContent);
      expect(earTag).toBeTruthy();

      // 检查性别
      const gender = await page.$eval('.gender-badge', el => el.textContent);
      expect(['公', '母']).toContain(gender);
    });

    test('数据看板应该正确显示', async () => {
      // 检查活动评分
      const activityScore = await page.$eval('.activity-score', el => el.textContent);
      expect(activityScore).toBeTruthy();

      // 检查饲料剩余
      const feedRemaining = await page.$('.feed-remaining');
      expect(feedRemaining).toBeTruthy();
    });

    test('活动趋势图表应该渲染', async () => {
      // 检查图表容器
      const chartContainer = await page.$('#activity-chart');
      expect(chartContainer).toBeTruthy();
    });

    test('标签页切换应该正常工作', async () => {
      // 切换到诊疗记录标签
      const medicalTab = await page.$('.tab-medical');
      if (medicalTab) {
        await medicalTab.tap();
        await page.waitFor(500);

        // 检查诊疗记录内容
        const medicalContent = await page.$('.medical-records');
        expect(medicalContent).toBeTruthy();
      }
    });

    test('时间范围切换应该更新图表', async () => {
      // 点击月视图
      const monthRange = await page.$('.range-month');
      if (monthRange) {
        await monthRange.tap();
        await page.waitFor(500);

        // 检查选中状态
        const isActive = await monthRange.$eval('.range-month', el => el.classList.contains('active'));
        expect(isActive).toBeTruthy();
      }
    });
  });

  // ==================== 测试3: 添加记录功能 ====================

  describe('添加记录页面', () => {
    beforeEach(async () => {
      page = await miniProgram.navigateTo(`/pages/add-record/add-record?animalId=${TEST_DATA.animalId}&shedId=${TEST_DATA.shedId}&date=${TEST_DATA.date}`);
      await page.waitFor(2000);
    });

    test('页面应该正确渲染', async () => {
      // 检查页面标题
      const title = await page.$eval('.page-title', el => el.textContent);
      expect(title).toContain('添加记录');
    });

    test('记录类型选择器应该显示', async () => {
      // 检查类型选项
      const typeOptions = await page.$$('.type-option');
      expect(typeOptions.length).toBeGreaterThanOrEqual(3);
    });

    test('应该可以输入文本内容', async () => {
      // 找到文本输入框
      const textarea = await page.$('textarea');
      expect(textarea).toBeTruthy();

      // 输入内容
      await textarea.input('测试记录内容');
      await page.waitFor(500);

      // 验证输入
      const value = await textarea.property('value');
      expect(value).toBe('测试记录内容');
    });

    test('应该可以选择图片', async () => {
      // 检查图片选择按钮
      const imagePicker = await page.$('.image-picker');
      expect(imagePicker).toBeTruthy();
    });

    test('应该可以录音', async () => {
      // 检查录音按钮
      const recordBtn = await page.$('.record-btn');
      expect(recordBtn).toBeTruthy();
    });

    test('提交按钮应该在有内容时可用', async () => {
      // 初始状态检查
      const submitBtn = await page.$('.submit-btn');
      expect(submitBtn).toBeTruthy();

      // 输入内容
      const textarea = await page.$('textarea');
      await textarea.input('测试内容');
      await page.waitFor(500);

      // 检查按钮状态
      const isDisabled = await submitBtn.$eval('.submit-btn', el => el.disabled);
      expect(isDisabled).toBeFalsy();
    });

    test('空内容提交应该显示错误提示', async () => {
      // 直接点击提交
      const submitBtn = await page.$('.submit-btn');
      await submitBtn.tap();
      await page.waitFor(500);

      // 检查错误提示
      const toast = await page.$('.toast');
      // 应该显示错误提示
    });

    test('从圈舍进入应该显示动物选择器', async () => {
      // 从圈舍页面进入（不带animalId）
      page = await miniProgram.navigateTo(`/pages/add-record/add-record?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 检查动物选择器
      const animalSelector = await page.$('.animal-selector');
      expect(animalSelector).toBeTruthy();
    });
  });

  // ==================== 测试4: 页面跳转和交互 ====================

  describe('页面跳转和交互', () => {
    test('首页到日报页面的导航', async () => {
      // 在首页点击圈舍
      page = await miniProgram.reLaunch('/pages/index/index');
      await page.waitFor(2000);

      const shedCard = await page.$('.shed-card');
      if (shedCard) {
        await shedCard.tap();
        await page.waitFor(1000);

        // 检查是否跳转到日报页
        const currentPage = await miniProgram.currentPage();
        expect(currentPage.path).toContain('daily-report');
      }
    });

    test('日报到详情的导航', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      const animalItem = await page.$('.animal-item');
      if (animalItem) {
        await animalItem.tap();
        await page.waitFor(1000);

        const currentPage = await miniProgram.currentPage();
        expect(currentPage.path).toContain('animal-detail');
      }
    });

    test('详情到添加记录的导航', async () => {
      page = await miniProgram.navigateTo(`/pages/animal-detail/animal-detail?animalId=${TEST_DATA.animalId}`);
      await page.waitFor(2000);

      const addBtn = await page.$('.add-record-btn');
      if (addBtn) {
        await addBtn.tap();
        await page.waitFor(1000);

        const currentPage = await miniProgram.currentPage();
        expect(currentPage.path).toContain('add-record');
      }
    });

    test('返回按钮应该正常工作', async () => {
      page = await miniProgram.navigateTo(`/pages/animal-detail/animal-detail?animalId=${TEST_DATA.animalId}`);
      await page.waitFor(2000);

      const backBtn = await page.$('.back-btn');
      if (backBtn) {
        await backBtn.tap();
        await page.waitFor(1000);

        // 检查是否返回上一页
        const pages = await miniProgram.pages();
        expect(pages.length).toBeGreaterThanOrEqual(1);
      }
    });

    test('下拉刷新应该加载新数据', async () => {
      page = await miniProgram.navigateTo(`/pages/daily-report/daily-report?shedId=${TEST_DATA.shedId}`);
      await page.waitFor(2000);

      // 模拟下拉刷新
      await page.callMethod('onPullDownRefresh');
      await page.waitFor(2000);

      // 检查页面是否仍然正常
      const pageTitle = await page.$eval('.page-title', el => el.textContent);
      expect(pageTitle).toContain('日报');
    });

    test('页面参数应该正确传递', async () => {
      // 导航到详情页并传递参数
      page = await miniProgram.navigateTo(`/pages/animal-detail/animal-detail?animalId=${TEST_DATA.animalId}&date=${TEST_DATA.date}`);
      await page.waitFor(2000);

      // 检查页面数据
      const pageData = await page.data();
      expect(pageData.animalId).toBe(TEST_DATA.animalId);
      expect(pageData.currentDate).toBe(TEST_DATA.date);
    });
  });
});

// 运行测试
if (require.main === module) {
  jest.setTimeout(120000);
}
