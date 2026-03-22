// pages/add-record/add-record.js
const app = getApp();
const dailyReportService = require('../../services/dailyReport');
const { formatDate, showLoading, hideLoading, showSuccess, showError } = require('../../utils/util');

Page({
  data: {
    // 页面参数
    animalId: null,
    shedId: null,
    date: formatDate(new Date()),
    
    // 记录类型
    recordType: 'observation', // observation, feeding, medical
    recordTypes: [
      { value: 'observation', label: '观察记录', icon: '👁️' },
      { value: 'feeding', label: '饲养记录', icon: '🌿' },
      { value: 'medical', label: '诊疗记录', icon: '💊' }
    ],
    
    // 表单数据
    formData: {
      content: '',
      images: [],
      voiceUrl: '',
      voiceDuration: 0
    },
    
    // 语音录制状态
    isRecording: false,
    recordingTime: 0,
    recordTimer: null,
    
    // 上传状态
    uploading: false,
    
    // 动物选择（如果从圈舍进入）
    animalList: [],
    selectedAnimals: [],
    showAnimalSelector: false
  },

  onLoad(options) {
    const { animalId, shedId, date } = options;
    
    this.setData({
      animalId: animalId || null,
      shedId: shedId || null,
      date: date || formatDate(new Date())
    });

    // 如果从圈舍进入，加载动物列表供选择
    if (shedId && !animalId) {
      this.loadShedAnimals(shedId);
    }
  },

  onUnload() {
    // 清理录音定时器
    if (this.data.recordTimer) {
      clearInterval(this.data.recordTimer);
    }
    // 停止录音
    if (this.data.isRecording) {
      this.stopRecord();
    }
  },

  // 加载圈舍动物列表
  async loadShedAnimals(shedId) {
    try {
      const res = await dailyReportService.getShedAnimals(shedId);
      if (res.data) {
        this.setData({
          animalList: res.data.map(animal => ({
            id: animal.id,
            earTag: animal.ear_tag,
            name: animal.name || animal.ear_tag,
            selected: false
          }))
        });
      }
    } catch (error) {
      console.error('加载动物列表失败:', error);
      // 使用模拟数据
      this.setData({
        animalList: [
          { id: 'A001', earTag: 'LS-2024-001', name: '小白', selected: false },
          { id: 'A002', earTag: 'LS-2024-002', name: '大黄', selected: false },
          { id: 'A003', earTag: 'LS-2024-003', name: '花花', selected: false }
        ]
      });
    }
  },

  // 切换记录类型
  switchRecordType(e) {
    const { type } = e.currentTarget.dataset;
    this.setData({ recordType: type });
  },

  // 输入内容
  onContentInput(e) {
    this.setData({
      'formData.content': e.detail.value
    });
  },

  // 选择图片
  chooseImage() {
    const { formData } = this.data;
    const remainCount = 9 - formData.images.length;
    
    if (remainCount <= 0) {
      wx.showToast({ title: '最多9张图片', icon: 'none' });
      return;
    }

    wx.chooseMedia({
      count: remainCount,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newImages = res.tempFiles.map(file => file.tempFilePath);
        this.setData({
          'formData.images': [...formData.images, ...newImages]
        });
      }
    });
  },

  // 预览图片
  previewImage(e) {
    const { index } = e.currentTarget.dataset;
    const { images } = this.data.formData;
    
    wx.previewImage({
      current: images[index],
      urls: images
    });
  },

  // 删除图片
  deleteImage(e) {
    const { index } = e.currentTarget.dataset;
    const { images } = this.data.formData;
    
    images.splice(index, 1);
    this.setData({
      'formData.images': images
    });
  },

  // 开始录音
  startRecord() {
    // 检查权限
    wx.getSetting({
      success: (res) => {
        if (!res.authSetting['scope.record']) {
          wx.authorize({
            scope: 'scope.record',
            success: () => {
              this.doStartRecord();
            },
            fail: () => {
              wx.showModal({
                title: '需要录音权限',
                content: '请在设置中开启录音权限',
                success: (res) => {
                  if (res.confirm) {
                    wx.openSetting();
                  }
                }
              });
            }
          });
        } else {
          this.doStartRecord();
        }
      }
    });
  },

  // 执行开始录音
  doStartRecord() {
    this.setData({ isRecording: true, recordingTime: 0 });
    
    // 开始录音
    wx.startRecord({
      success: () => {
        console.log('开始录音');
      }
    });

    // 计时器
    const timer = setInterval(() => {
      const newTime = this.data.recordingTime + 1;
      this.setData({ recordingTime: newTime });
      
      // 最多录制60秒
      if (newTime >= 60) {
        this.stopRecord();
      }
    }, 1000);

    this.setData({ recordTimer: timer });
  },

  // 停止录音
  stopRecord() {
    const { recordTimer } = this.data;
    
    if (recordTimer) {
      clearInterval(recordTimer);
    }

    wx.stopRecord({
      success: (res) => {
        const tempFilePath = res.tempFilePath;
        this.setData({
          isRecording: false,
          'formData.voiceUrl': tempFilePath,
          recordTimer: null
        });
      },
      fail: () => {
        this.setData({
          isRecording: false,
          recordTimer: null
        });
      }
    });
  },

  // 播放语音
  playVoice() {
    const { voiceUrl } = this.data.formData;
    if (voiceUrl) {
      wx.playVoice({ filePath: voiceUrl });
    }
  },

  // 删除语音
  deleteVoice() {
    this.setData({
      'formData.voiceUrl': '',
      'formData.voiceDuration': 0,
      recordingTime: 0
    });
  },

  // 格式化录音时间
  formatRecordTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  },

  // 显示动物选择器
  showAnimalSelector() {
    this.setData({ showAnimalSelector: true });
  },

  // 隐藏动物选择器
  hideAnimalSelector() {
    this.setData({ showAnimalSelector: false });
  },

  // 切换动物选择
  toggleAnimalSelection(e) {
    const { index } = e.currentTarget.dataset;
    const { animalList } = this.data;
    
    animalList[index].selected = !animalList[index].selected;
    this.setData({ animalList });
  },

  // 确认动物选择
  confirmAnimalSelection() {
    const selectedAnimals = this.data.animalList.filter(a => a.selected);
    this.setData({
      selectedAnimals,
      showAnimalSelector: false
    });
  },

  // 提交表单
  async submitForm() {
    const { animalId, shedId, date, recordType, formData, selectedAnimals } = this.data;
    
    // 验证
    if (!formData.content && formData.images.length === 0 && !formData.voiceUrl) {
      showError('请填写内容或上传图片/语音');
      return;
    }

    // 如果从圈舍进入，需要选择动物
    if (shedId && !animalId && selectedAnimals.length === 0) {
      showError('请选择至少一只动物');
      return;
    }

    try {
      showLoading('提交中...');
      this.setData({ uploading: true });

      // 上传图片
      const uploadedImages = [];
      if (formData.images.length > 0) {
        for (const imagePath of formData.images) {
          const res = await dailyReportService.uploadImage(imagePath);
          uploadedImages.push(res.url);
        }
      }

      // 上传语音
      let uploadedVoiceUrl = '';
      if (formData.voiceUrl) {
        const res = await dailyReportService.uploadVoice(formData.voiceUrl);
        uploadedVoiceUrl = res.url;
      }

      // 准备提交数据
      const submitData = {
        type: recordType,
        content: formData.content,
        images: uploadedImages,
        voice_url: uploadedVoiceUrl,
        voice_duration: formData.voiceDuration,
        record_date: date
      };

      // 确定目标动物
      let targetAnimals = [];
      if (animalId) {
        targetAnimals = [animalId];
      } else {
        targetAnimals = selectedAnimals.map(a => a.id);
      }

      // 提交记录
      for (const targetAnimalId of targetAnimals) {
        await dailyReportService.addRecord(targetAnimalId, submitData);
      }

      hideLoading();
      this.setData({ uploading: false });
      
      showSuccess('添加成功');
      
      // 返回上一页
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);

    } catch (error) {
      console.error('提交失败:', error);
      hideLoading();
      this.setData({ uploading: false });
      showError('提交失败，请重试');
    }
  },

  // 取消
  cancel() {
    wx.navigateBack();
  }
});
