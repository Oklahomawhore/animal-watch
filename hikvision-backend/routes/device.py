#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备管理路由
"""

import logging
from datetime import datetime
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
        
        # 获取 User Access Token
        data = request.get_json() or {}
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userId'}), 400
        
        # 从数据库获取用户 Token
        from models import UserAuth
        user_auth = UserAuth.query.filter_by(user_id=user_id).first()
        
        if not user_auth:
            return jsonify({'code': 401, 'msg': 'User not bound to Hikvision'}), 401
        
        if user_auth.status != 'active':
            return jsonify({'code': 401, 'msg': 'Token expired, please re-authenticate'}), 401
        
        # 调用海康云 API 进行抓拍
        from services.hikcloud import HikvisionCloudAPI
        from flask import current_app
        
        app_key = current_app.config.get('HIK_APP_KEY')
        app_secret = current_app.config.get('HIK_APP_SECRET')
        hik_api = HikvisionCloudAPI(app_key, app_secret)
        hik_api.set_user_token(user_auth.user_access_token)
        
        pic_url = hik_api.capture_device(device_serial, device.channel_no)
        
        if pic_url:
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'deviceSerial': device_serial,
                    'picUrl': pic_url,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
        else:
            return jsonify({
                'code': 500,
                'msg': 'Capture failed, please check device status'
            }), 500
        
    except Exception as e:
        logger.error(f"设备抓拍失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@device_bp.route('/cloud/list', methods=['GET'])
def get_cloud_devices():
    """从海康云获取设备列表"""
    try:
        # 获取 User Access Token
        user_id = request.args.get('userId')
        
        if not user_id:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userId'}), 400
        
        # 从数据库获取用户 Token
        from models import UserAuth
        user_auth = UserAuth.query.filter_by(user_id=user_id).first()
        
        if not user_auth:
            return jsonify({'code': 401, 'msg': 'User not bound to Hikvision'}), 401
        
        if user_auth.status != 'active':
            return jsonify({'code': 401, 'msg': 'Token expired, please re-authenticate'}), 401
        
        # 调用海康云 API 获取设备列表
        from services.hikcloud import HikvisionCloudAPI
        from flask import current_app
        
        app_key = current_app.config.get('HIK_APP_KEY')
        app_secret = current_app.config.get('HIK_APP_SECRET')
        hik_api = HikvisionCloudAPI(app_key, app_secret)
        hik_api.set_user_token(user_auth.user_access_token)
        
        devices = hik_api.get_device_list()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': devices,
                'total': len(devices)
            }
        })
        
    except Exception as e:
        logger.error(f"获取云端设备列表失败: {e}")
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
