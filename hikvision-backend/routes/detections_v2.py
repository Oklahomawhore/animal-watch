#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 检测记录路由
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from models_v2 import db, Detection, Camera, Enclosure, UserStatus, VisibilityLevel
from utils.auth import login_required

logger = logging.getLogger(__name__)

detections_bp = Blueprint('detections_v2', __name__)


@detections_bp.route('', methods=['GET'])
@login_required
def list_detections():
    """
    获取检测记录列表
    
    查询参数:
        enclosureId: 圈ID
        cameraId: 摄像头ID
        startDate: 开始日期
        endDate: 结束日期
        minAnimalCount: 最小动物数
        page: 页码
        size: 每页数量
    """
    try:
        query = Detection.query.filter_by(client_id=g.client_id)
        
        # 应用筛选
        enclosure_id = request.args.get('enclosureId', type=int)
        if enclosure_id:
            query = query.filter_by(enclosure_id=enclosure_id)
        
        camera_id = request.args.get('cameraId', type=int)
        if camera_id:
            query = query.filter_by(camera_id=camera_id)
        
        start_date = request.args.get('startDate')
        if start_date:
            query = query.filter(Detection.timestamp >= start_date)
        
        end_date = request.args.get('endDate')
        if end_date:
            query = query.filter(Detection.timestamp <= end_date)
        
        min_count = request.args.get('minAnimalCount', type=int)
        if min_count is not None:
            query = query.filter(Detection.animal_count >= min_count)
        
        # 权限过滤（饲养员）
        if g.user.role.value == 'breeder':
            if g.user.visibility_level == VisibilityLevel.ENCLOSURE:
                query = query.filter(Detection.enclosure_id.in_(g.user.visibility_scope_ids or []))
            elif g.user.visibility_level == VisibilityLevel.AREA:
                enclosures = Enclosure.query.filter(
                    Enclosure.area_id.in_(g.user.visibility_scope_ids or [])
                ).all()
                enclosure_ids = [e.id for e in enclosures]
                query = query.filter(Detection.enclosure_id.in_(enclosure_ids))
        
        # 分页
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        
        pagination = query.order_by(Detection.timestamp.desc()).paginate(
            page=page, per_page=size, error_out=False
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'items': [d.to_dict() for d in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size
            }
        })
        
    except Exception as e:
        logger.error(f"获取检测记录失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detections_bp.route('/<int:detection_id>', methods=['GET'])
@login_required
def get_detection(detection_id):
    """获取检测记录详情"""
    try:
        detection = Detection.query.filter_by(
            id=detection_id,
            client_id=g.client_id
        ).first()
        
        if not detection:
            return jsonify({'code': 404, 'msg': 'Detection not found'}), 404
        
        # 权限检查
        if g.user.role.value == 'breeder':
            if detection.enclosure_id not in (g.user.visibility_scope_ids or []):
                return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
        result = detection.to_dict()
        if detection.camera:
            result['camera'] = detection.camera.to_dict()
        if detection.enclosure:
            result['enclosure'] = detection.enclosure.to_dict()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取检测详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detections_bp.route('/stats', methods=['GET'])
@login_required
def get_detection_stats():
    """获取检测统计"""
    try:
        # 今日检测次数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = Detection.query.filter(
            Detection.client_id == g.client_id,
            Detection.timestamp >= today_start
        ).count()
        
        # 总检测次数
        total_count = Detection.query.filter_by(client_id=g.client_id).count()
        
        # 平均动物数（今日）
        today_avg = db.session.query(
            db.func.avg(Detection.animal_count)
        ).filter(
            Detection.client_id == g.client_id,
            Detection.timestamp >= today_start
        ).scalar() or 0
        
        # 按圈统计
        enclosure_stats = db.session.query(
            Detection.enclosure_id,
            db.func.count(Detection.id),
            db.func.avg(Detection.animal_count)
        ).filter_by(client_id=g.client_id).group_by(Detection.enclosure_id).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'todayCount': today_count,
                'totalCount': total_count,
                'todayAvgAnimalCount': round(float(today_avg), 2),
                'byEnclosure': [
                    {
                        'enclosureId': eid,
                        'count': c,
                        'avgAnimalCount': round(float(avg), 2)
                    } for eid, c, avg in enclosure_stats
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"获取检测统计失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detections_bp.route('/timeline', methods=['GET'])
@login_required
def get_detection_timeline():
    """获取检测时间线（按小时统计）"""
    try:
        hours = request.args.get('hours', 24, type=int)
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 按小时分组统计
        timeline = db.session.query(
            db.func.strftime('%Y-%m-%d %H:00', Detection.timestamp),
            db.func.count(Detection.id),
            db.func.avg(Detection.animal_count),
            db.func.avg(Detection.activity_score)
        ).filter(
            Detection.client_id == g.client_id,
            Detection.timestamp >= start_time
        ).group_by(
            db.func.strftime('%Y-%m-%d %H:00', Detection.timestamp)
        ).order_by(
            db.func.strftime('%Y-%m-%d %H:00', Detection.timestamp)
        ).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [
                {
                    'time': t,
                    'count': c,
                    'avgAnimalCount': round(float(avg_count), 2) if avg_count else 0,
                    'avgActivityScore': round(float(avg_activity), 2) if avg_activity else 0
                } for t, c, avg_count, avg_activity in timeline
            ]
        })
        
    except Exception as e:
        logger.error(f"获取时间线失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
