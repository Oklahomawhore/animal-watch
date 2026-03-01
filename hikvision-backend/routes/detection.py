#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测服务路由
"""

import logging
from flask import Blueprint, request, jsonify
from models import db, Detection, Device

logger = logging.getLogger(__name__)

detection_bp = Blueprint('detection', __name__)

# 全局检测状态
detection_status = {
    'running': False,
    'devices': []
}


@detection_bp.route('/status', methods=['GET'])
def get_status():
    """获取检测服务状态"""
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': detection_status
    })


@detection_bp.route('/start', methods=['POST'])
def start_detection():
    """开始检测"""
    try:
        data = request.get_json() or {}
        device_serials = data.get('deviceSerials', [])
        interval = data.get('interval', 1.0)  # 检测间隔(秒)
        
        if not device_serials:
            return jsonify({'code': 400, 'msg': 'No devices specified'}), 400
        
        # 更新状态
        detection_status['running'] = True
        detection_status['devices'] = device_serials
        detection_status['interval'] = interval
        
        # TODO: 启动后台检测任务
        # 1. 为每个设备启动一个线程
        # 2. 定期抓拍并分析
        
        logger.info(f"检测服务启动: devices={device_serials}, interval={interval}")
        
        return jsonify({
            'code': 0,
            'msg': 'Detection started',
            'data': detection_status
        })
        
    except Exception as e:
        logger.error(f"启动检测失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detection_bp.route('/stop', methods=['POST'])
def stop_detection():
    """停止检测"""
    try:
        detection_status['running'] = False
        detection_status['devices'] = []
        
        # TODO: 停止所有检测线程
        
        logger.info("检测服务停止")
        
        return jsonify({
            'code': 0,
            'msg': 'Detection stopped'
        })
        
    except Exception as e:
        logger.error(f"停止检测失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detection_bp.route('/records', methods=['GET'])
def get_records():
    """获取检测记录"""
    try:
        device_serial = request.args.get('deviceSerial')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        
        # 构建查询
        query = Detection.query
        
        if device_serial:
            device = Device.query.filter_by(device_serial=device_serial).first()
            if device:
                query = query.filter_by(device_id=device.id)
        
        # 时间范围筛选
        # TODO: 添加时间范围筛选
        
        # 分页
        total = query.count()
        records = query.order_by(Detection.timestamp.desc()) \
                      .offset((page - 1) * page_size) \
                      .limit(page_size) \
                      .all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': [r.to_dict() for r in records],
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
        
    except Exception as e:
        logger.error(f"获取检测记录失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@detection_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取检测统计"""
    try:
        device_serial = request.args.get('deviceSerial')
        hours = int(request.args.get('hours', 24))
        
        # TODO: 统计指定时间内的活动量
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'hours': hours,
                'stats': {
                    'totalDetections': 0,
                    'avgActivityScore': 0,
                    'maxAnimalCount': 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
