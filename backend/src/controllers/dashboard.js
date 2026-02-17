const { pool } = require('../config/database');
const { createError } = require('../utils/errors');

/**
 * 仪表盘控制器
 */
class DashboardController {
  /**
   * 获取仪表盘摘要数据
   */
  async getSummary(req, res, next) {
    try {
      const { tenant_id } = req.user;
      
      // 获取统计数据
      const [stats] = await pool.execute(`
        SELECT 
          COUNT(DISTINCT s.id) as total_sheds,
          COUNT(DISTINCT c.id) as total_cameras,
          COUNT(DISTINCT c.id) as online_cameras,
          COUNT(DISTINCT a.id) as total_animals,
          COUNT(DISTINCT CASE WHEN a.status = 'healthy' THEN a.id END) as healthy_animals
        FROM sheds s
        LEFT JOIN cameras c ON s.id = c.shed_id AND c.status = 'online'
        LEFT JOIN animals a ON s.id = a.shed_id
        WHERE s.tenant_id = ?
      `, [tenant_id]);
      
      // 获取今日告警数
      const [alerts] = await pool.execute(`
        SELECT 
          COUNT(*) as total_alerts,
          COUNT(CASE WHEN status = 'unhandled' THEN 1 END) as unhandled_alerts,
          COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_alerts
        FROM alerts
        WHERE tenant_id = ? AND DATE(created_at) = CURDATE()
      `, [tenant_id]);
      
      // 获取今日平均活动量
      const [activity] = await pool.execute(`
        SELECT AVG(activity_score) as avg_activity
        FROM activity_records
        WHERE tenant_id = ? 
        AND DATE(record_time) = CURDATE()
        AND period = 'hour'
      `, [tenant_id]);
      
      res.json({
        success: true,
        data: {
          sheds: {
            total: stats[0].total_sheds,
          },
          cameras: {
            total: stats[0].total_cameras,
            online: stats[0].online_cameras || 0,
          },
          animals: {
            total: stats[0].total_animals,
            healthy: stats[0].healthy_animals || 0,
            health_rate: stats[0].total_animals > 0 
              ? ((stats[0].healthy_animals / stats[0].total_animals) * 100).toFixed(1)
              : 100
          },
          alerts: {
            today: alerts[0].total_alerts || 0,
            unhandled: alerts[0].unhandled_alerts || 0,
            critical: alerts[0].critical_alerts || 0
          },
          activity: {
            today_avg: parseFloat(activity[0].avg_activity || 0).toFixed(1),
            status: (activity[0].avg_activity || 0) > 30 ? 'normal' : 'low'
          }
        }
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取圈舍状态列表
   */
  async getShedsStatus(req, res, next) {
    try {
      const { tenant_id } = req.user;
      
      const [sheds] = await pool.execute(`
        SELECT 
          s.id,
          s.name,
          s.code,
          s.current_count,
          s.capacity,
          s.status,
          COUNT(DISTINCT c.id) as camera_count,
          COUNT(DISTINCT CASE WHEN c.status = 'online' THEN c.id END) as online_cameras,
          (SELECT AVG(activity_score) 
           FROM activity_records 
           WHERE shed_id = s.id 
           AND record_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
          ) as current_activity
        FROM sheds s
        LEFT JOIN cameras c ON s.id = c.shed_id
        WHERE s.tenant_id = ?
        GROUP BY s.id
        ORDER BY s.created_at DESC
      `, [tenant_id]);
      
      res.json({
        success: true,
        data: sheds.map(shed => ({
          ...shed,
          current_activity: parseFloat(shed.current_activity || 0).toFixed(1),
          camera_status: shed.camera_count > 0 && shed.online_cameras === shed.camera_count 
            ? 'online' 
            : 'warning'
        }))
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取活动量趋势
   */
  async getActivityTrend(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { days = 7 } = req.query;
      
      const [trend] = await pool.execute(`
        SELECT 
          DATE(record_time) as date,
          AVG(activity_score) as avg_score,
          MAX(activity_score) as max_score,
          MIN(activity_score) as min_score,
          SUM(event_count) as total_events
        FROM activity_records
        WHERE tenant_id = ?
        AND period = 'hour'
        AND record_time >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
        GROUP BY DATE(record_time)
        ORDER BY date ASC
      `, [tenant_id, parseInt(days)]);
      
      res.json({
        success: true,
        data: trend.map(row => ({
          date: row.date,
          avg_score: parseFloat(row.avg_score || 0).toFixed(1),
          max_score: parseFloat(row.max_score || 0).toFixed(1),
          min_score: parseFloat(row.min_score || 0).toFixed(1),
          total_events: row.total_events
        }))
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取告警摘要
   */
  async getAlertsSummary(req, res, next) {
    try {
      const { tenant_id } = req.user;
      
      const [summary] = await pool.execute(`
        SELECT 
          alert_type,
          severity,
          COUNT(*) as count
        FROM alerts
        WHERE tenant_id = ?
        AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY alert_type, severity
        ORDER BY count DESC
      `, [tenant_id]);
      
      // 按类型汇总
      const byType = {};
      summary.forEach(item => {
        if (!byType[item.alert_type]) {
          byType[item.alert_type] = { total: 0, critical: 0, warning: 0 };
        }
        byType[item.alert_type].total += item.count;
        byType[item.alert_type][item.severity] = item.count;
      });
      
      res.json({
        success: true,
        data: {
          total: summary.reduce((sum, item) => sum + item.count, 0),
          by_type: byType
        }
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 微信小程序摘要
   */
  async getWXSummary(req, res, next) {
    try {
      const { tenant_id } = req.user;
      
      // 简化版数据，适合小程序展示
      const [[summary]] = await pool.execute(`
        SELECT 
          (SELECT COUNT(*) FROM sheds WHERE tenant_id = ?) as shed_count,
          (SELECT COUNT(*) FROM cameras WHERE tenant_id = ? AND status = 'online') as online_cameras,
          (SELECT COUNT(*) FROM animals WHERE tenant_id = ? AND status = 'healthy') as healthy_animals,
          (SELECT COUNT(*) FROM alerts WHERE tenant_id = ? AND status = 'unhandled') as unhandled_alerts,
          (SELECT AVG(activity_score) FROM activity_records 
           WHERE tenant_id = ? AND record_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
          ) as current_activity
      `, [tenant_id, tenant_id, tenant_id, tenant_id, tenant_id]);
      
      res.json({
        success: true,
        data: {
          sheds: summary.shed_count || 0,
          online_cameras: summary.online_cameras || 0,
          healthy_animals: summary.healthy_animals || 0,
          unhandled_alerts: summary.unhandled_alerts || 0,
          current_activity: parseFloat(summary.current_activity || 0).toFixed(0),
          status: (summary.current_activity || 0) > 30 ? 'normal' : 'low'
        }
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new DashboardController();
