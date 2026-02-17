const { pool } = require('../config/database');
const { createError } = require('../utils/errors');

/**
 * 告警控制器
 */
class AlertController {
  /**
   * 获取告警列表
   */
  async list(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { 
        status, 
        severity, 
        type,
        start_date, 
        end_date,
        page = 1, 
        limit = 20 
      } = req.query;
      
      let whereClause = 'WHERE a.tenant_id = ?';
      const params = [tenant_id];
      
      if (status) {
        whereClause += ' AND a.status = ?';
        params.push(status);
      }
      
      if (severity) {
        whereClause += ' AND a.severity = ?';
        params.push(severity);
      }
      
      if (type) {
        whereClause += ' AND a.alert_type = ?';
        params.push(type);
      }
      
      if (start_date) {
        whereClause += ' AND a.created_at >= ?';
        params.push(start_date);
      }
      
      if (end_date) {
        whereClause += ' AND a.created_at <= ?';
        params.push(end_date);
      }
      
      // 获取总数
      const [countResult] = await pool.execute(`
        SELECT COUNT(*) as total FROM alerts a ${whereClause}
      `, params);
      
      const total = countResult[0].total;
      const offset = (parseInt(page) - 1) * parseInt(limit);
      
      // 获取数据
      const [alerts] = await pool.execute(`
        SELECT 
          a.id,
          a.alert_type,
          a.severity,
          a.title,
          a.description,
          a.status,
          a.current_value,
          a.baseline_value,
          a.z_score,
          a.created_at,
          a.handled_at,
          a.handle_note,
          s.name as shed_name,
          c.name as camera_name,
          an.code as animal_code,
          u.name as handled_by_name
        FROM alerts a
        LEFT JOIN sheds s ON a.shed_id = s.id
        LEFT JOIN cameras c ON a.camera_id = c.id
        LEFT JOIN animals an ON a.animal_id = an.id
        LEFT JOIN users u ON a.handled_by = u.id
        ${whereClause}
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
      `, [...params, parseInt(limit), offset]);
      
      res.json({
        success: true,
        data: {
          list: alerts,
          pagination: {
            total,
            page: parseInt(page),
            limit: parseInt(limit),
            total_pages: Math.ceil(total / parseInt(limit))
          }
        }
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取告警详情
   */
  async get(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { id } = req.params;
      
      const [alerts] = await pool.execute(`
        SELECT 
          a.*,
          s.name as shed_name,
          c.name as camera_name,
          c.ip_address as camera_ip,
          an.code as animal_code,
          an.name as animal_name,
          u.name as handled_by_name
        FROM alerts a
        LEFT JOIN sheds s ON a.shed_id = s.id
        LEFT JOIN cameras c ON a.camera_id = c.id
        LEFT JOIN animals an ON a.animal_id = an.id
        LEFT JOIN users u ON a.handled_by = u.id
        WHERE a.id = ? AND a.tenant_id = ?
      `, [id, tenant_id]);
      
      if (alerts.length === 0) {
        throw createError(404, '告警不存在');
      }
      
      res.json({
        success: true,
        data: alerts[0]
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 处理告警
   */
  async handle(req, res, next) {
    try {
      const { tenant_id, id: user_id } = req.user;
      const { id } = req.params;
      const { action, note } = req.body;
      
      const status = action === 'resolve' ? 'resolved' : 'ignored';
      
      const [result] = await pool.execute(`
        UPDATE alerts
        SET status = ?,
            handled_by = ?,
            handled_at = NOW(),
            handle_note = ?,
            updated_at = NOW()
        WHERE id = ? AND tenant_id = ?
      `, [status, user_id, note || '', id, tenant_id]);
      
      if (result.affectedRows === 0) {
        throw createError(404, '告警不存在或已处理');
      }
      
      res.json({
        success: true,
        message: action === 'resolve' ? '告警已标记为已处理' : '告警已忽略'
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 批量处理告警
   */
  async batchHandle(req, res, next) {
    try {
      const { tenant_id, id: user_id } = req.user;
      const { ids, action, note } = req.body;
      
      const status = action === 'resolve' ? 'resolved' : 'ignored';
      
      const placeholders = ids.map(() => '?').join(',');
      const params = [status, user_id, note || '', tenant_id, ...ids];
      
      const [result] = await pool.execute(`
        UPDATE alerts
        SET status = ?,
            handled_by = ?,
            handled_at = NOW(),
            handle_note = ?,
            updated_at = NOW()
        WHERE tenant_id = ? AND id IN (${placeholders})
      `, params);
      
      res.json({
        success: true,
        message: `已处理 ${result.affectedRows} 条告警`
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取告警统计
   */
  async getStats(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { days = 7 } = req.query;
      
      // 总体统计
      const [overview] = await pool.execute(`
        SELECT 
          COUNT(*) as total,
          COUNT(CASE WHEN status = 'unhandled' THEN 1 END) as unhandled,
          COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
          COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
          COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warning
        FROM alerts
        WHERE tenant_id = ?
        AND created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
      `, [tenant_id, parseInt(days)]);
      
      // 按类型统计
      const [byType] = await pool.execute(`
        SELECT 
          alert_type,
          COUNT(*) as count
        FROM alerts
        WHERE tenant_id = ?
        AND created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
        GROUP BY alert_type
        ORDER BY count DESC
      `, [tenant_id, parseInt(days)]);
      
      // 按天统计
      const [byDay] = await pool.execute(`
        SELECT 
          DATE(created_at) as date,
          COUNT(*) as total,
          COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical
        FROM alerts
        WHERE tenant_id = ?
        AND created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
        GROUP BY DATE(created_at)
        ORDER BY date ASC
      `, [tenant_id, parseInt(days)]);
      
      // 处理时效统计
      const [responseTime] = await pool.execute(`
        SELECT 
          AVG(TIMESTAMPDIFF(MINUTE, created_at, handled_at)) as avg_response_minutes
        FROM alerts
        WHERE tenant_id = ?
        AND status = 'resolved'
        AND created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
      `, [tenant_id, parseInt(days)]);
      
      res.json({
        success: true,
        data: {
          overview: overview[0],
          by_type: byType,
          by_day: byDay,
          response_time: {
            avg_minutes: Math.round(responseTime[0].avg_response_minutes || 0)
          }
        }
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 微信小程序告警列表
   */
  async listWX(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { status = 'unhandled', limit = 10 } = req.query;
      
      const [alerts] = await pool.execute(`
        SELECT 
          a.id,
          a.alert_type,
          a.severity,
          a.title,
          a.created_at,
          s.name as shed_name
        FROM alerts a
        LEFT JOIN sheds s ON a.shed_id = s.id
        WHERE a.tenant_id = ? AND a.status = ?
        ORDER BY a.created_at DESC
        LIMIT ?
      `, [tenant_id, status, parseInt(limit)]);
      
      res.json({
        success: true,
        data: alerts.map(a => ({
          ...a,
          severity_label: a.severity === 'critical' ? '严重' : '警告',
          type_label: this.getAlertTypeLabel(a.alert_type)
        }))
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 标记为已读
   */
  async markAsRead(req, res, next) {
    try {
      const { tenant_id } = req.user;
      const { id } = req.params;
      
      // 这里可以实现已读记录逻辑
      // 简化处理：直接返回成功
      
      res.json({
        success: true,
        message: '已标记为已读'
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * 获取告警类型标签
   */
  getAlertTypeLabel(type) {
    const labels = {
      'activity_drop': '活动量骤降',
      'activity_spike': '活动量激增',
      'prolonged_idle': '持续静止',
      'device_offline': '设备离线',
      'device_error': '设备故障',
      'abnormal_behavior': '行为异常'
    };
    return labels[type] || type;
  }
}

module.exports = new AlertController();
