#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 告警管理路由
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from models_v2 import db, AlarmRecord, Camera, Enclosure, UserStatus, UserRole, VisibilityLevel
from utils.auth import login_required, manager_required
from services.wechat_provider import notification_service

logger = logging.getLogger(__name__)

alarms_bp = Blueprint('alarms_v2', __name__)


@alarms_bp.route('', methods=['GET'])
@login_required
def list_alarms():
    """
    获取告警列表（带权限过滤）
    
    查询参数:
        status: unhandled/handled/ignored
        alarmType: 告警类型
        enclosureId: 圈ID
        startDate: 开始日期
        endDate: 结束日期
        page: 页码
        size: 每页数量
    """
    try:
        query = AlarmRecord.query.filter_by(client_id=g.client_id)
        
        # 应用筛选
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        alarm_type = request.args.get('alarmType')
        if alarm_type:
            query = query.filter_by(alarm_type=alarm_type)
        
        enclosure_id = request.args.get('enclosureId', type=int)
        if enclosure_id:
            query = query.filter_by(enclosure_id=enclosure_id)
        
        # 日期范围
        start_date = request.args.get('startDate')
        if start_date:
            query = query.filter(AlarmRecord.alarm_time >= start_date)
        
        end_date = request.args.get('endDate')
        if end_date:
            query = query.filter(AlarmRecord.alarm_time <= end_date)
        
        # 权限过滤（饲养员）
        if g.user.role.value == 'breeder':
            if g.user.visibility_level == VisibilityLevel.ENCLOSURE:
                query = query.filter(AlarmRecord.enclosure_id.in_(g.user.visibility_scope_ids or []))
            elif g.user.visibility_level == VisibilityLevel.AREA:
                from models_v2 import Enclosure
                enclosures = Enclosure.query.filter(
                    Enclosure.area_id.in_(g.user.visibility_scope_ids or [])
                ).all()
                enclosure_ids = [e.id for e in enclosures]
                query = query.filter(AlarmRecord.enclosure_id.in_(enclosure_ids))
        
        # 分页
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        
        pagination = query.order_by(AlarmRecord.alarm_time.desc()).paginate(
            page=page, per_page=size, error_out=False
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'items': [a.to_dict() for a in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size,
                'unhandledCount': AlarmRecord.query.filter_by(
                    client_id=g.client_id, status='unhandled'
                ).count()
            }
        })
        
    except Exception as e:
        logger.error(f"获取告警列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@alarms_bp.route('/<int:alarm_id>', methods=['GET'])
@login_required
def get_alarm(alarm_id):
    """获取告警详情"""
    try:
        alarm = AlarmRecord.query.filter_by(
            id=alarm_id,
            client_id=g.client_id
        ).first()
        
        if not alarm:
            return jsonify({'code': 404, 'msg': 'Alarm not found'}), 404
        
        # 权限检查
        if g.user.role.value == 'breeder':
            if alarm.enclosure_id not in (g.user.visibility_scope_ids or []):
                return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
        result = alarm.to_dict()
        if alarm.camera:
            result['camera'] = alarm.camera.to_dict()
        if alarm.enclosure:
            result['enclosure'] = alarm.enclosure.to_dict()
        if alarm.handler:
            result['handler'] = {
                'id': alarm.handler.id,
                'nickname': alarm.handler.nickname
            }
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取告警详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@alarms_bp.route('/<int:alarm_id>/handle', methods=['POST'])
@login_required
def handle_alarm(alarm_id):
    """
    处理告警
    
    请求参数:
        status: handled/ignored
        remark: 处理备注
    """
    try:
        alarm = AlarmRecord.query.filter_by(
            id=alarm_id,
            client_id=g.client_id
        ).first()
        
        if not alarm:
            return jsonify({'code': 404, 'msg': 'Alarm not found'}), 404
        
        data = request.get_json() or {}
        status = data.get('status', 'handled')
        remark = data.get('remark', '')
        
        alarm.status = status
        alarm.handled_by = g.user.id
        alarm.handled_at = datetime.utcnow()
        alarm.handle_remark = remark
        
        db.session.commit()
        
        logger.info(f"告警 {alarm_id} 被 {g.user.username} 处理为 {status}")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': alarm.to_dict()
        })
        
    except Exception as e:
        logger.error(f"处理告警失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@alarms_bp.route('/stats', methods=['GET'])
@login_required
def get_alarm_stats():
    """获取告警统计"""
    try:
        # 今日告警
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_alarms = AlarmRecord.query.filter(
            AlarmRecord.client_id == g.client_id,
            AlarmRecord.alarm_time >= today_start
        ).count()
        
        # 未处理告警
        unhandled = AlarmRecord.query.filter_by(
            client_id=g.client_id,
            status='unhandled'
        ).count()
        
        # 本周告警
        week_start = datetime.utcnow() - timedelta(days=7)
        week_alarms = AlarmRecord.query.filter(
            AlarmRecord.client_id == g.client_id,
            AlarmRecord.alarm_time >= week_start
        ).count()
        
        # 按类型统计
        type_stats = db.session.query(
            AlarmRecord.alarm_type,
            db.func.count(AlarmRecord.id)
        ).filter_by(client_id=g.client_id).group_by(AlarmRecord.alarm_type).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'today': today_alarms,
                'unhandled': unhandled,
                'week': week_alarms,
                'byType': {t: c for t, c in type_stats}
            }
        })
        
    except Exception as e:
        logger.error(f"获取告警统计失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@alarms_bp.route('/batch-handle', methods=['POST'])
@manager_required
def batch_handle_alarms():
    """批量处理告警"""
    try:
        data = request.get_json() or {}
        alarm_ids = data.get('alarmIds', [])
        status = data.get('status', 'handled')
        
        if not alarm_ids:
            return jsonify({'code': 400, 'msg': 'Missing alarmIds'}), 400
        
        count = AlarmRecord.query.filter(
            AlarmRecord.id.in_(alarm_ids),
            AlarmRecord.client_id == g.client_id
        ).update({
            'status': status,
            'handled_by': g.user.id,
            'handled_at': datetime.utcnow()
        }, synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {'handledCount': count}
        })
        
    except Exception as e:
        logger.error(f"批量处理告警失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
