#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理路由
"""

import logging
from flask import Blueprint, request, jsonify
from models import db, Device
from services.hikcloud import HikvisionCloudAPI

logger = logging.getLogger(__name__)

device_bp = Blueprint('device', __name__)


@device_bp.route('', methods=['GET'])
def get_devices():
    """获取设备列表"""
    try:
        # 先从本地数据库获取
        devices = Device.query.all()
        
        # 如果数据库为空，尝试从海康云获取
        if not devices:
            # TODO: 调用海康云API获取设备列表
            pass
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': [d.to_dict() for d in devices],
                'total': len(devices)
            }
        })
        
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('', methods=['POST'])
def add_device():
    """添加设备"""
    try:
        data = request.get_json() or {}
        
        device_serial = data.get('deviceSerial')
        device_name = data.get('deviceName')
        
        if not device_serial:
            return jsonify({'code': 400, 'msg': 'Missing deviceSerial'}), 400
        
        # 检查是否已存在
        existing = Device.query.filter_by(device_serial=device_serial).first()
        if existing:
            return jsonify({'code': 400, 'msg': 'Device already exists'}), 400
        
        # 创建设备
        device = Device(
            device_serial=device_serial,
            device_name=device_name,
            channel_no=data.get('channelNo', 1),
            location_x=data.get('location', {}).get('x'),
            location_y=data.get('location', {}).get('y'),
            trough_id=data.get('troughId')
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': device.to_dict()
        })
        
    except Exception as e:
        logger.error(f"添加设备失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('/<device_serial>/capture', methods=['POST'])
def capture_device(device_serial):
    """设备抓拍"""
    try:
        # 查找设备
        device = Device.query.filter_by(device_serial=device_serial).first()
        if not device:
            return jsonify({'code': 404, 'msg': 'Device not found'}), 404
        
        # TODO: 调用海康云API进行抓拍
        # 需要确认正确的API路径
        
        return jsonify({
            'code': 0,
            'msg': 'Capture request sent',
            'data': {
                'deviceSerial': device_serial,
                'status': 'processing'
            }
        })
        
    except Exception as e:
        logger.error(f"设备抓拍失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('/<device_serial>', methods=['GET'])
def get_device_detail(device_serial):
    """获取设备详情"""
    try:
        device = Device.query.filter_by(device_serial=device_serial).first()
        if not device:
            return jsonify({'code': 404, 'msg': 'Device not found'}), 404
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': device.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取设备详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('/<device_serial>', methods=['PUT'])
def update_device(device_serial):
    """更新设备信息"""
    try:
        device = Device.query.filter_by(device_serial=device_serial).first()
        if not device:
            return jsonify({'code': 404, 'msg': 'Device not found'}), 404
        
        data = request.get_json() or {}
        
        if 'deviceName' in data:
            device.device_name = data['deviceName']
        if 'location' in data:
            device.location_x = data['location'].get('x')
            device.location_y = data['location'].get('y')
        if 'troughId' in data:
            device.trough_id = data['troughId']
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': device.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新设备失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('/<device_serial>', methods=['DELETE'])
def delete_device(device_serial):
    """删除设备"""
    try:
        device = Device.query.filter_by(device_serial=device_serial).first()
        if not device:
            return jsonify({'code': 404, 'msg': 'Device not found'}), 404
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'Device deleted'
        })
        
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
