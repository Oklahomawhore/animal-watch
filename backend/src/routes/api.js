const express = require('express');
const router = express.Router();
const { body, validationResult } = require('express-validator');
const { auth, requireRole } = require('../middleware/auth');
const DashboardController = require('../controllers/dashboard');
const ShedController = require('../controllers/shed');
const CameraController = require('../controllers/camera');
const AnimalController = require('../controllers/animal');
const AlertController = require('../controllers/alert');
const ReportController = require('../controllers/report');

// 错误处理辅助函数
const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  next();
};

// ============================================
// Dashboard 仪表盘
// ============================================
router.get('/dashboard/summary', auth, DashboardController.getSummary);
router.get('/dashboard/sheds', auth, DashboardController.getShedsStatus);
router.get('/dashboard/activity-trend', auth, DashboardController.getActivityTrend);
router.get('/dashboard/alerts-summary', auth, DashboardController.getAlertsSummary);

// ============================================
// Sheds 圈舍管理
// ============================================
router.get('/sheds', auth, ShedController.list);
router.get('/sheds/:id', auth, ShedController.get);
router.post('/sheds', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('name').notEmpty().trim(),
  body('farm_id').notEmpty(),
  body('capacity').optional().isInt({ min: 1 }),
  handleValidationErrors
], ShedController.create);
router.put('/sheds/:id', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('name').optional().trim(),
  body('capacity').optional().isInt({ min: 1 }),
  handleValidationErrors
], ShedController.update);
router.delete('/sheds/:id', [auth, requireRole(['admin', 'super_admin'])], ShedController.delete);

// 圈舍活动量
router.get('/sheds/:id/activity', auth, ShedController.getActivity);
router.get('/sheds/:id/animals', auth, ShedController.getAnimals);

// ============================================
// Cameras 摄像头管理
// ============================================
router.get('/cameras', auth, CameraController.list);
router.get('/cameras/:id', auth, CameraController.get);
router.post('/cameras', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('name').notEmpty().trim(),
  body('farm_id').notEmpty(),
  body('ip_address').isIP(),
  body('port').optional().isInt({ min: 1, max: 65535 }),
  handleValidationErrors
], CameraController.create);
router.put('/cameras/:id', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('name').optional().trim(),
  body('status').optional().isIn(['online', 'offline', 'maintenance']),
  handleValidationErrors
], CameraController.update);
router.delete('/cameras/:id', [auth, requireRole(['admin', 'super_admin'])], CameraController.delete);

// 摄像头控制
router.post('/cameras/:id/restart', [auth, requireRole(['admin'])], CameraController.restart);
router.get('/cameras/:id/snapshot', auth, CameraController.getSnapshot);
router.get('/cameras/:id/events', auth, CameraController.getEvents);

// ============================================
// Animals 林麝管理
// ============================================
router.get('/animals', auth, AnimalController.list);
router.get('/animals/:id', auth, AnimalController.get);
router.post('/animals', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('code').notEmpty().trim(),
  body('name').optional().trim(),
  body('gender').optional().isIn(['male', 'female']),
  handleValidationErrors
], AnimalController.create);
router.put('/animals/:id', [
  auth,
  requireRole(['admin', 'super_admin']),
  body('name').optional().trim(),
  body('status').optional().isIn(['healthy', 'warning', 'sick', 'isolated']),
  handleValidationErrors
], AnimalController.update);
router.delete('/animals/:id', [auth, requireRole(['admin', 'super_admin'])], AnimalController.delete);

// 林麝活动历史
router.get('/animals/:id/activity-history', auth, AnimalController.getActivityHistory);
router.get('/animals/:id/health-report', auth, AnimalController.getHealthReport);

// ============================================
// Alerts 告警管理
// ============================================
router.get('/alerts', auth, AlertController.list);
router.get('/alerts/stats', auth, AlertController.getStats);
router.get('/alerts/:id', auth, AlertController.get);
router.post('/alerts/:id/handle', [
  auth,
  body('action').isIn(['resolve', 'ignore']),
  body('note').optional().trim(),
  handleValidationErrors
], AlertController.handle);
router.post('/alerts/batch-handle', [
  auth,
  requireRole(['admin']),
  body('ids').isArray(),
  body('action').isIn(['resolve', 'ignore']),
  handleValidationErrors
], AlertController.batchHandle);

// ============================================
// Reports 报表
// ============================================
router.get('/reports/daily', auth, ReportController.getDailyReport);
router.get('/reports/weekly', auth, ReportController.getWeeklyReport);
router.get('/reports/activity', auth, ReportController.getActivityReport);
router.get('/reports/anomalies', auth, ReportController.getAnomalyReport);
router.get('/reports/export', auth, ReportController.exportReport);

// ============================================
// 微信小程序专用接口
// ============================================
router.get('/wx/dashboard', auth, DashboardController.getWXSummary);
router.get('/wx/sheds', auth, ShedController.listWX);
router.get('/wx/alerts', auth, AlertController.listWX);
router.post('/wx/alerts/:id/read', auth, AlertController.markAsRead);

module.exports = router;
