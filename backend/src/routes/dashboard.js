const express = require('express');
const router = express.Router();
const { Shed, Camera, Alert, Animal } = require('../models');
const { auth } = require('../middleware/auth');

// 获取仪表盘摘要数据
router.get('/summary', auth, async (req, res) => {
  try {
    // 统计总数
    const totalAnimals = await Animal.countDocuments();
    const totalSheds = await Shed.countDocuments();
    const onlineCameras = await Camera.countDocuments({ status: 'online' });
    const totalCameras = await Camera.countDocuments();
    
    // 今日报警
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayAlerts = await Alert.countDocuments({ createdAt: { $gte: today } });
    const unhandledAlerts = await Alert.countDocuments({ status: 'unhandled' });
    
    // 健康率计算
    const healthyAnimals = await Animal.countDocuments({ status: 'healthy' });
    const healthRate = totalAnimals > 0 ? (healthyAnimals / totalAnimals * 100).toFixed(1) : 100;
    
    res.json({
      totalAnimals,
      totalSheds,
      onlineCameras,
      totalCameras,
      todayAlerts,
      unhandledAlerts,
      healthRate,
      activeAnimals: healthyAnimals
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// 获取圈舍列表及状态
router.get('/sheds', auth, async (req, res) => {
  try {
    const sheds = await Shed.find()
      .populate('cameras', 'status')
      .sort({ createdAt: -1 });
    
    const data = sheds.map(shed => ({
      id: shed._id,
      name: shed.name,
      code: shed.code,
      animalCount: shed.currentCount,
      capacity: shed.capacity,
      temperature: shed.temperature,
      humidity: shed.humidity,
      status: shed.status,
      cameraCount: shed.cameras.length,
      onlineCameras: shed.cameras.filter(c => c.status === 'online').length
    }));
    
    res.json({ data });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// 获取活动趋势数据
router.get('/activity-trend', auth, async (req, res) => {
  try {
    const { days = 7 } = req.query;
    
    // 生成最近 N 天的模拟数据
    const data = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      data.push({
        date: date.toISOString().split('T')[0],
        avgActivity: Math.floor(1200 + Math.random() * 400),
        totalAnimals: 160
      });
    }
    
    res.json({ data });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
