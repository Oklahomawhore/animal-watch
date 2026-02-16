const express = require('express');
const router = express.Router();
const { Alert, Shed, Camera } = require('../models');
const { auth } = require('../middleware/auth');

// 获取报警列表
router.get('/', auth, async (req, res) => {
  try {
    const { filter = 'all', page = 1, limit = 20 } = req.query;
    
    let query = {};
    if (filter === 'unhandled') query.status = 'unhandled';
    if (filter === 'activity') query.type = { $in: ['activity_low', 'activity_high'] };
    if (filter === 'disease') query.type = { $in: ['fall_detected', 'fight_detected'] };
    
    const alerts = await Alert.find(query)
      .populate('shedId', 'name')
      .populate('cameraId', 'name')
      .sort({ createdAt: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));
    
    const total = await Alert.countDocuments(query);
    
    res.json({
      data: alerts,
      pagination: { page: parseInt(page), limit: parseInt(limit), total }
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// 获取报警统计
router.get('/stats', auth, async (req, res) => {
  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const stats = await Alert.aggregate([
      {
        $match: {
          createdAt: { $gte: today }
        }
      },
      {
        $group: {
          _id: null,
          total: { $sum: 1 },
          unhandled: {
            $sum: { $cond: [{ $eq: ['$status', 'unhandled'] }, 1, 0] }
          },
          urgent: {
            $sum: { $cond: [{ $eq: ['$level', 'urgent'] }, 1, 0] }
          }
        }
      }
    ]);
    
    res.json(stats[0] || { total: 0, unhandled: 0, urgent: 0 });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// 处理报警
router.post('/:id/handle', auth, async (req, res) => {
  try {
    const { id } = req.params;
    const { action, note } = req.body;
    
    const alert = await Alert.findByIdAndUpdate(
      id,
      {
        status: action === 'ignore' ? 'ignored' : 'handled',
        handledBy: req.user._id,
        handledAt: new Date(),
        note
      },
      { new: true }
    );
    
    if (!alert) {
      return res.status(404).json({ message: 'Alert not found' });
    }
    
    res.json({ message: 'Alert handled successfully', data: alert });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
